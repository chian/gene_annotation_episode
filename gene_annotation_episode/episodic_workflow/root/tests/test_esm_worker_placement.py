"""Changed ESM deployment, private worker identity and actual Root dispatch.

The existing engineering fixture supplies metadata only. Runtime verification
and the model-import port are controlled in worker tests; no ESM inference,
physical deployment validation or publication success is claimed.
"""
import asyncio
import builtins
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import test_esm_gene_embeddings as fixtures

from gene_annotation_episode import esm_gene_embedding_contracts as original_contracts
from gene_annotation_episode import esm_gene_embedding_worker as original_worker
from gene_annotation_episode.episodic_workflow.root.library import esm_gene_embedding_contracts as contracts
from gene_annotation_episode.episodic_workflow.root.library import esm_gene_embedding_tools as tools
from gene_annotation_episode.episodic_workflow.root.library import esm_gene_embedding_worker as worker
from gene_annotation_episode.episodic_workflow.root.library.esm_worker_ports import ESMWorkerPorts
from gene_annotation_episode.episodic_workflow.root import tool_native_sequence


LEGACY = "gene_annotation_episode."
CURRENT = "gene_annotation_episode.episodic_workflow.root.library."


def current_deployment():
    value = fixtures.deployment()
    for pin in value["driver"]["implementation_files"]:
        pin["module"] = CURRENT + pin["module"].removeprefix(LEGACY)
    return value


def request(deployment, path="/engineering/input.fa"):
    return dict(version=contracts.REQUEST_VERSION,
        input=dict(path=path, file=fixtures.supplied()["file"], source_ref=None),
        genes=fixtures.genes(), parameters=fixtures.parameters(), deployment=deployment)


def test_saved_deployment_retains_exact_original_validation_and_pins():
    value = fixtures.deployment()
    before = deepcopy(value)
    assert contracts.validate_esm_deployment(value) == original_contracts.validate_esm_deployment(value) == before
    assert value == before
    assert contracts.esm_worker_module(value["driver"]) == LEGACY + "esm_gene_embedding_worker"
    arguments = dict(request=request(value))
    ports = ESMWorkerPorts(arguments)
    assert ports.module("esm_gene_embedding") == LEGACY + "esm_gene_embedding_worker"
    # A tampered saved command cannot select a different worker; the unchanged
    # custodian will compare its entire vector with this supplied-deployment choice.
    assert ports.recorded_module("esm_gene_embedding", {"command": ["python", "-m", CURRENT + "esm_gene_embedding_worker"]}) == LEGACY + "esm_gene_embedding_worker"


def test_current_deployment_uses_actual_pair_without_rewriting_supplied_pins():
    value = current_deployment()
    before = deepcopy(value)
    assert contracts.validate_esm_deployment(value) == before
    assert value == before
    supplied = request(value)
    ports = ESMWorkerPorts(dict(request=supplied))
    assert ports.module("esm_gene_embedding") == CURRENT + "esm_gene_embedding_worker"
    checked, environment, implementation = ports.esm_validation_owners()
    assert checked is contracts.validate_esm_worker_request
    assert environment is tools.esm_worker_environment
    assert implementation is tools.esm_worker_implementation_files
    pins = implementation(supplied)
    for entry in value["driver"]["implementation_files"]:
        expected = dict(path=str(Path(value["driver"]["module_root"]) / (entry["module"].replace(".", "/") + ".py")), sha256=entry["sha256"])
        assert expected in pins
    assert all(pin["sha256"] in {"1" * 64, "2" * 64} for pin in pins)


@pytest.mark.parametrize("change", ["worker_only", "contracts_only", "both_pairs"])
def test_mixed_or_ambiguous_deployment_pairs_are_not_reinterpreted(change):
    value = fixtures.deployment()
    pins = value["driver"]["implementation_files"]
    if change == "both_pairs":
        pins.extend(current_deployment()["driver"]["implementation_files"])
    else:
        index = 0 if change == "worker_only" else 1
        pins[index]["module"] = CURRENT + pins[index]["module"].removeprefix(LEGACY)
    before = deepcopy(value)
    with pytest.raises(ValueError, match="esm_gene_embedding_selected_worker_module_conflict"):
        contracts.validate_esm_deployment(value)
    assert value == before


@pytest.mark.parametrize("case", ["original_legacy", "current_legacy", "current_current"])
def test_actual_running_worker_identity_precedes_model_import(case, tmp_path, monkeypatch):
    selected_worker = original_worker if case == "original_legacy" else worker
    deployment = current_deployment() if case == "current_current" else fixtures.deployment()
    # Use the actual staged module root. No source/hash verification is claimed:
    # verify_driver_runtime is the single explicit physical-deployment test port.
    module_root = Path(worker.__file__).resolve().parents[4]
    deployment["driver"]["module_root"] = str(module_root)
    input_path = tmp_path / "input.fa"
    input_path.write_bytes(fixtures.RAW)
    supplied = request(deployment, str(input_path))
    runtime_calls = []
    monkeypatch.setattr(selected_worker, "verify_driver_runtime", lambda value: runtime_calls.append(deepcopy(value)))
    monkeypatch.setattr(selected_worker, "_infer", lambda *args: pytest.fail("model port must stop before inference"))
    imports = []
    original_import = builtins.__import__

    def import_port(name, *args, **kwargs):
        if name in {"torch", "esm"}:
            imports.append(name)
            raise RuntimeError("controlled_model_import_port")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_port)
    result = selected_worker.run_esm_gene_embedding_request(supplied, output_directory=tmp_path)
    document = json.loads((tmp_path / result["result_document_file"]["path"]).read_bytes())
    identity_matches = case != "current_legacy"
    assert runtime_calls == [deployment["driver"]]
    assert document["execution"]["runtime_verified"] is identity_matches
    assert imports == (["torch"] if identity_matches else [])
    assert document["execution"]["model_forward_calls"] == 0
    assert document["execution"]["state"] == "failed"
    assert result["vector_file"] is None and document["observed_model"] is None
    assert len(document["proteins"]) == 5 and len(document["isoforms"]) == 7 and len(document["gene_rows"]) == 3
    assert all(row["mean_vector"] is None for row in document["gene_rows"])


def test_actual_root_dispatch_binds_private_esm_ports_at_original_custodian_seam(tmp_path, monkeypatch):
    from gene_annotation_episode.molecular_measurement_tools import run_owned_molecular_worker
    calls = []
    # Deliberately invalid arguments: Root dispatch must pass them unchanged to
    # the original custodian's validation point, never validate them prematurely.
    arguments = {"engineering_invalid_envelope": True}
    policy = object()
    registry = SimpleNamespace(store=SimpleNamespace(db=SimpleNamespace(in_transaction=False)), local_job_policy=policy)

    async def captured(function, operation, supplied, **kwargs):
        assert function is run_owned_molecular_worker
        assert operation == "esm_gene_embedding" and supplied is arguments
        assert kwargs["directory"] == kwargs["owned_directory"] == tmp_path
        assert kwargs["policy"] is policy
        assert isinstance(kwargs["worker_ports"], ESMWorkerPorts)
        assert kwargs["worker_ports"].arguments is arguments
        calls.append(kwargs)
        return tmp_path / "controlled-result.json", {"controlled_custodian_port": True}

    monkeypatch.setattr(tool_native_sequence, "run_cancellable_native", captured)
    result = asyncio.run(tool_native_sequence.ToolNativeSequence._sequence_worker_async(
        registry, "esm_gene_embedding", arguments, directory=tmp_path, owned_directory=tmp_path))
    assert len(calls) == 1
    assert result.output_path == tmp_path / "controlled-result.json"
    assert result.metadata == {"controlled_custodian_port": True}
