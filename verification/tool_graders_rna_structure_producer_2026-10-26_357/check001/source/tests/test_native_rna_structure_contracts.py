from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import platform
import sys

import pytest

from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.native_rna_structure_contracts import (
    ATTEMPT_DIRECTORY_NAME, POLICY, compile_rna_structure_job, requested_job_from_rna_structure,
    validate_rna_structure_job, validate_rna_structure_requested_job, validate_rna_structure_run_plan,
    validate_rna_structure_bindings)
from gene_annotation_episode.native_rna_structure_tool_info import rna_structure_tool_contracts, rna_structure_tool_information

REPO = Path(__file__).resolve().parents[1]
PACKET = REPO / "verification/tool_graders_rna_structure_producer_2026-10-26_357"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def model():
    return {"schema": "vienna_rna_model_spec_v1", "temperature_c": 37.0, "dangles": 2,
        "noLP": False, "noGU": False, "noGUclosure": False, "special_hp": True, "logML": False,
        "min_loop_size": 3, "max_bp_span": -1, "circ": False, "gquad": False,
        "hard_constraints": None, "soft_constraints": None, "parameters": {"kind": "turner2004", "operand_role": None}}


def parameters():
    return {"schema": "rna_calculation_parameters_v1", "topology": {"long_stem_min_pairs": 3,
        "include_exterior_in_loop_size_statistics": False}, "pair_composition": {
        "accepted_ordered_pair_types": ["AU", "UA", "GC", "CG", "GU", "UG"], "denominator": "unambiguous_pairs"},
        "energy": {"normalization": "per_nt"}}


def rna_input(*, prediction=False, energy=False):
    value = {"schema": "rna_prediction_input_v1" if prediction else "rna_feature_input_v1",
        "record_key": "original-record", "sequence_id": "Example RNA", "sequence": "GGGAAACCC",
        "normalization": "exact", "subject_binding": None}
    if not prediction:
        value.update(structure_id="Supplied hairpin", dot_bracket="(((...)))", structure_origin="supplied_unknown",
            structure_source_ref=None, energy_mode="viennarna_evaluate" if energy else "none")
    return value


def software(*, native=False):
    result = {"python_executable": sys.executable, "python_sha256": sha(sys.executable),
        "python_version": platform.python_version(), "worker_module": "gene_annotation_episode.native_rna_structure_worker",
        "worker_source_sha256": sha(REPO / "gene_annotation_episode/native_rna_structure_worker.py"),
        "viennarna_distribution_version": None, "rna_module_sha256": None, "rna_extension_sha256": None}
    if native:
        observed = json.loads((PACKET / "probe001/probe.json").read_bytes())
        result.update(viennarna_distribution_version=observed["distribution_version"],
            rna_module_sha256=observed["module_sha256"], rna_extension_sha256=observed["extension_sha256"])
    return result


def job(tmp_path, *, prediction=False, energy=False, native=False, raw=None, parameter_file=None):
    request = rna_input(prediction=prediction, energy=energy)
    path = tmp_path / "supplied-input.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((canonical(request) + "\n").encode() if raw is None else raw)
    selected_model = model() if prediction or energy else None
    operands = [{"role": "input", "path": str(path), "format": "rna_input_json_v1", "sha256": sha(path),
        "size_bytes": path.stat().st_size, "artifact_ref": None}]
    if parameter_file is not None:
        selected_model["parameters"] = {"kind": "supplied_parameter_file", "operand_role": "model_parameter_input"}
        operands.append({"role": "model_parameter_input", "path": str(parameter_file), "format": "viennarna_parameter_file",
            "sha256": sha(parameter_file), "size_bytes": parameter_file.stat().st_size, "artifact_ref": None})
    outputs = [{"role": "native_result", "format": "rna_native_record_json_v1", "relative_path": "native-result.json"},
        {"role": "stdout", "format": "text", "relative_path": "stdout.txt"},
        {"role": "stderr", "format": "text", "relative_path": "stderr.txt"}]
    if selected_model is not None:
        outputs += [{"role": "model", "format": "vienna_model_json_v1", "relative_path": "model.json"},
            {"role": "effective_parameters", "format": "viennarna_parameter_file", "relative_path": "effective-parameters.par"}]
    return {"version": "native_rna_structure_job_v1", "program": "rna_structure_python",
        "operation": "predict_rna_secondary_structure" if prediction else "analyze_rna_secondary_structure_features",
        "mode": "mfe_prediction" if prediction else "supplied_features", "record_key": request["record_key"],
        "software": software(native=native), "model": selected_model, "operands": operands, "outputs": outputs,
        "environment": {"PYTHONPATH": str(PACKET / "native-site") + os.pathsep + str(REPO) if native else str(REPO)},
        "grading_parameters": parameters()}


def plan(tmp_path, selected_job=None, **options):
    selected_job = selected_job or job(tmp_path, **options)
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    operation_key = "selected-operation"
    root = workspace / ".episode-operations" / digest({"run": "run", "episode": "local"}) / digest(operation_key)
    request = requested_job_from_rna_structure(selected_job)
    value = {"version": "native_rna_structure_run_plan_v1", "identity": {"run_id": "run", "episode_id": "local",
        "resource_id": "local-resource", "execution_id": str(root / "native.json"), "attempt_id": digest(operation_key),
        "operation_key": operation_key, "requested_job_sha256": digest(request)}, "requested_job": request,
        "attempt_directory": str(root / ATTEMPT_DIRECTORY_NAME), "policy": deepcopy(POLICY)}
    assignment = {"requested_job": request, "workspace": str(workspace), "resource_kind": "local", "resource_id": "local-resource"}
    return value, assignment, root


@pytest.mark.parametrize("prediction,energy", [(False, False), (False, True), (True, False)])
def test_compiled_argv_preserves_explicit_job_and_staged_paths(tmp_path, prediction, energy):
    original = job(tmp_path, prediction=prediction, energy=energy)
    original["record_key"] = "opaque; $(never executed)"
    request = requested_job_from_rna_structure(original)
    assert validate_rna_structure_requested_job(request) == request
    assert request["argv"][request["argv"].index("--software-json") + 1] == canonical(original["software"])
    assert request["argv"][request["argv"].index("--model-json") + 1] == canonical(original["model"])
    staged = compile_rna_structure_job(original, input_paths={"input": str(tmp_path / "staged/input.json")}, output_directory=str(tmp_path / "staged"))
    assert staged["argv"] != request["argv"]
    assert request["argv"][request["argv"].index("--input-json") + 1] == original["operands"][0]["path"]
    assert staged["argv"][staged["argv"].index("--input-json") + 1] == str(tmp_path / "staged/input.json")
    assert original == request["native_rna_structure"]


@pytest.mark.parametrize("path", ["bundle.json", "bundle.json/child", "input.json", "model-parameter-input.par", "../outside",
    "/outside", "a/../b", "a//b", "./out", "tmp/a", "cache/a", ".native-rna-structure-owner.json", ".local-job-abc"])
def test_output_collision_and_traversal_rejected(tmp_path, path):
    value = job(tmp_path)
    value["outputs"][0]["relative_path"] = path
    with pytest.raises(ValueError, match="rna_output_path_conflict"):
        validate_rna_structure_job(value)


@pytest.mark.parametrize("mutate", [
    lambda x: x["outputs"].append(deepcopy(x["outputs"][0])),
    lambda x: x["operands"].append(deepcopy(x["operands"][0])),
    lambda x: x["outputs"][0].update(format="text"),
    lambda x: x.update(operation="predict_rna_secondary_structure"),
    lambda x: x["grading_parameters"]["topology"].update(long_stem_min_pairs=True),
    lambda x: x["operands"][0].update(size_bytes=True),
    lambda x: x["software"].update(worker_module="other.module"),
    lambda x: x.update(extra=True),
])
def test_closed_identity_role_and_type_contracts(tmp_path, mutate):
    value = job(tmp_path)
    mutate(value)
    with pytest.raises(ValueError):
        validate_rna_structure_job(value)


@pytest.mark.parametrize("name", ["TMPDIR", "TMP", "TEMP", "XDG_CACHE_HOME", "PIP_CACHE_DIR", "PYTHONHOME", "HOME"])
def test_caller_cannot_redirect_temporary_or_cache_storage(tmp_path, name):
    value = job(tmp_path)
    value["environment"][name] = "/elsewhere"
    with pytest.raises(ValueError, match="rna_output_path_conflict"):
        validate_rna_structure_job(value)


def test_requests_are_compiled_not_independently_editable(tmp_path):
    request = requested_job_from_rna_structure(job(tmp_path))
    request["argv"] += ["--unselected-native-action"]
    with pytest.raises(ValueError, match="rna_input_identity_mismatch"):
        validate_rna_structure_requested_job(request)


@pytest.mark.parametrize("mutate", [lambda x: x["identity"].update(attempt_id="a" * 64),
    lambda x: x["identity"].update(requested_job_sha256="a" * 64),
    lambda x: x["policy"].update(wall_seconds=60), lambda x: x["policy"].update(memory_bytes=1024),
    lambda x: x.update(attempt_directory=x["attempt_directory"] + "-other")])
def test_plan_pins_policy_selected_attempt_and_exact_locator(tmp_path, mutate):
    value, _, _ = plan(tmp_path)
    assert validate_rna_structure_run_plan(value) == value
    mutate(value)
    with pytest.raises(ValueError):
        validate_rna_structure_run_plan(value)


def test_four_information_fields_and_child_route(tmp_path):
    binding = [{key: job(tmp_path)[key] for key in ("operation", "mode", "software")}]
    contracts = rna_structure_tool_contracts(binding, resource_kind="local", resource_id="local-resource")
    information = rna_structure_tool_information(binding, resource_kind="local", resource_id="local-resource")
    assert set(information[0]) == {"name", "description", "resources", "instructions"}
    assert contracts[0]["invocation_route"]["routes"] == [{"entry_role": "launch", "resource_id": "local-resource", "resource_role": "launch_local"}]
    assert "eval_structure" in information[0]["instructions"] and "energy_mode=none" in information[0]["instructions"]
    with pytest.raises(ValueError):
        validate_rna_structure_bindings(binding + binding)
