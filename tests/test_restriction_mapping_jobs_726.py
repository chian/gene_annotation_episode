"""One genuine selected job; remaining cases inspect that retained job only."""
import asyncio
import builtins
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry
from gene_annotation_episode.restriction_mapping_inputs import restriction_sequence_witness
from gene_annotation_episode.restriction_mapping_publication import retain_restriction_input
from gene_annotation_episode.restriction_mapping_bound_contracts import restriction_native_request
from gene_annotation_episode import restriction_mapping_jobs as module


pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ, reason="requires bounded529")


def pin(path):
    path = Path(path).resolve(strict=True)
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size}


def save(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def forbid(*args, **kwargs):
    raise AssertionError("native dispatch/refresh forbidden in retained replay")


@pytest.fixture(scope="module")
def actual_job():
    # A failed assertion never creates another search: explicit followup selector
    # reopens this exact original Store. The first run writes its selector before
    # dispatch and every closed proof/output before any scientific assertion.
    if os.environ.get("HMMER_NATIVE_ORACLE_RESTRICTION726_PHASE") in {"faults", "retire", "followup"}:
        pytest.skip("original native assertions already passed; selected followup has no new search")
    reuse = os.environ.get("HMMER_NATIVE_ORACLE_RESTRICTION726_RETAINED_SELECTOR")
    if reuse:
        selector_path = Path(reuse)
        selector = json.loads(selector_path.read_bytes())
        store = Store(selector["store_path"])
        jobs = module.RestrictionMappingJobs(store)
        args = selector["reservation_arguments"]
        result = jobs.publication_state(args["operation_key"])
        yield store, jobs, args, result, selector_path
        store.close()
        return
    directory = Path(os.environ["HMMER529_ATTEMPT"]) / "retained-restriction726"
    directory.mkdir(exist_ok=False)
    store = Store(directory / "store")
    store.create_problem(raw_sequence="AAAAGAATTCTTTT", molecule="dna")
    subject, = store.targets()
    tools = ToolRegistry(store)
    witness = restriction_sequence_witness(store, subject["id"], namespace="subject", scope=None,
        permitted_record_refs=[subject["id"]], sequence_reader=tools._sequence,
        check_operand=tools._check_sequence_operand)
    operation_key = "restriction726-selected-EcoRI-linear"
    arguments = {"mode": "native", "sequence_ref": subject["id"],
        "enzyme_names": ["EcoRI"], "topology": "linear"}
    retained = retain_restriction_input(store, operation_key=operation_key,
        tool_name="find_restriction_sites", arguments=arguments, scope=witness["scope"], witness=witness)
    job_directory = module.restriction_operation_directory(store, operation_key)
    source_root = Path(module.__file__).resolve().parent
    bio = next(Path(entry) / "Bio" for entry in sys.path if entry and
        (Path(entry) / "Bio/Restriction/Restriction.py").is_file())
    software = {"python": pin(sys.executable),
        "implementation_files": [pin(path) for path in sorted(source_root.glob("restriction_mapping_*.py"))],
        "biopython_version": "1.88", "native_source_file": pin(bio / "Restriction/Restriction.py"),
        "dictionary_file": pin(bio / "Restriction/Restriction_Dictionary.py"),
        "environment": {"PATH": "/usr/bin:/bin", "PYTHONHOME": sys.prefix,
            "PYTHONPATH": str(source_root.parent), "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(job_directory),
            "TMP": str(job_directory), "TEMP": str(job_directory),
            "XDG_CACHE_HOME": str(job_directory / "cache")}}
    args = {"operation_key": operation_key, "tool_name": "find_restriction_sites",
        "arguments": arguments, "scope": witness["scope"], **retained,
        "worker_request": restriction_native_request("find_restriction_sites", arguments,
            sequence=witness["sequence"], sequence_binding=retained["sequence_binding"]),
        "software": software, "policy": {'memory_bytes': 20 * 1024 ** 3, 'scratch_bytes': 4 * 1024 ** 3}}
    jobs = module.RestrictionMappingJobs(store)
    selector_path = directory / "selector.json"
    selector = {"store_path": str(store.path), "operation_key": operation_key,
        "reservation_arguments": args, "native_searches_authorized": 1,
        "publication_fixture": "original Store/job; do not copy or rerun"}
    save(selector_path, selector)
    reservation = jobs.reserve(**args)
    save(directory / "reservation.json", reservation)
    # The genuine run is confined to this first setup. Its exact handle is reused.
    proof = asyncio.run(jobs.run_async(operation_key))
    save(directory / "execution-proof.json", proof)
    state = jobs.publication_state(operation_key)
    save(directory / "publication-state.json", state)
    selector.update(handle_path=reservation["handle_path"], output_directory=reservation["output_directory"],
        reservation_artifact_ref=state["reservation_artifact_ref"],
        execution_proof_artifact_ref=state["execution_proof_artifact_ref"],
        output_pins=[pin(path) for path in sorted(Path(reservation["output_directory"]).iterdir())
            if path.is_file()])
    save(selector_path, selector)
    yield store, jobs, args, state, selector_path
    store.close()


def test_original_native_proof_and_complete_outputs(actual_job):
    store, jobs, args, state, selector_path = actual_job
    proof = state["execution_proof"]
    assert proof["returncode"] == 0 and proof["failure_code"] is None
    assert proof["original_view"]["terminal"] and proof["original_view"]["quiescent"]
    meta = proof["original_view"]["metadata"]
    assert meta["policy"] == args["policy"]
    assert meta["verified_cgroup"]["memory_max"] == 20 * 1024**3
    assert meta["verified_cgroup"]["memory_swap_max"] == 0
    assert 'runtime_max' not in meta["verified_cgroup"]
    output = Path(state["reservation"]["output_directory"])
    native = json.loads((output / "native.json").read_bytes())
    mapping = json.loads((output / "mapping.json").read_bytes())
    assert native["batch_state"] == "returned"
    assert native["enzyme_searches"][0]["native_search_positions_1based"] == [6]
    assert mapping["enzyme_rows"][0]["returned_position_count"] == 1
    assert mapping["enzyme_rows"][0]["positions"][0]["watson_boundary_0based"] == 5
    assert mapping["enzyme_rows"][0]["positions"][0]["crick_boundary_0based"] == 9
    assert json.loads(selector_path.read_bytes())["output_pins"]


def test_same_terminal_handle_replay_freezes_timing_and_never_dispatches(actual_job, monkeypatch):
    _, jobs, args, state, _ = actual_job
    monkeypatch.setattr(module.native, "resume_start", forbid)
    monkeypatch.setattr(module.native, "wait_job", forbid)
    monkeypatch.setattr(module.native, "status", forbid)
    assert asyncio.run(jobs.run_async(args["operation_key"])) == state["execution_proof"]
    assert jobs.reserve(**args) == state["reservation"]
    assert jobs.publication_state(args["operation_key"])["execution_proof"] == state["execution_proof"]


@pytest.mark.parametrize("field", ["tool_name", "arguments", "scope", "input_source_ref",
    "sequence_binding", "worker_request", "software", "policy"])
def test_repeat_reservation_rejects_changed_original_selection(actual_job, field):
    _, jobs, original, state, _ = actual_job
    args = deepcopy(original)
    if field == "tool_name":
        args[field] = "find_restriction_enzymes"
    elif field == "arguments":
        args[field]["topology"] = "circular"
    elif field == "scope":
        args[field] = {"subject_refs": []}
    elif field == "input_source_ref":
        args[field] = "source_changed"
    elif field == "sequence_binding":
        args[field]["sequence_version"] = 99
    elif field == "worker_request":
        args[field]["sequence"] = "T" * 14
    elif field == "software":
        args[field]["python"]["sha256"] = "0" * 64
    else:
        args[field]["wall_seconds"] = 1
    with pytest.raises((ContractError, ValueError)):
        jobs.reserve(**args)
    assert jobs.publication_state(original["operation_key"])["execution_proof"] == state["execution_proof"]


def test_unknown_operation_has_no_authority(actual_job):
    _, jobs, args, _, _ = actual_job
    with pytest.raises(ContractError, match="operation_missing"):
        jobs.publication_state(args["operation_key"] + "-wrong")


def test_premature_retirement_preserves_complete_original_job(actual_job):
    _, jobs, args, state, _ = actual_job
    with pytest.raises(ContractError, match="retirement_requires_committed_publication"):
        jobs.retire(args["operation_key"])
    assert Path(state["reservation"]["handle_path"]).is_file()
    assert Path(state["reservation"]["output_directory"]).is_dir()


def test_record_publication_requires_callers_transaction(actual_job):
    _, jobs, args, _, _ = actual_job
    with pytest.raises(ContractError, match="publication_requires_active_store_transaction"):
        jobs.record_publication(args["operation_key"], source_ref="source_forged", outcome={})


def test_saved_proof_artifact_mutation_rejected_and_restored(actual_job):
    store, jobs, args, state, _ = actual_job
    reference = state["execution_proof_artifact_ref"]
    digest = reference.removeprefix("artifact_")
    path = store.path / "artifacts" / digest[:2] / digest
    original = path.read_bytes()
    try:
        path.write_bytes(original + b" ")
        with pytest.raises(ContractError, match="artifact_digest_mismatch"):
            jobs.publication_state(args["operation_key"])
    finally:
        path.write_bytes(original)
    assert jobs.publication_state(args["operation_key"]) == state


def test_forged_row_with_original_artifacts_wrong_key_is_rejected(actual_job):
    store, jobs, args, state, _ = actual_job
    key = args["operation_key"] + "-forged"
    with store.transaction():
        store.db.execute("INSERT INTO restriction_mapping_operations(operation_key,reservation_artifact_ref,prepared_handle_artifact_ref,execution_proof_artifact_ref) SELECT ?,reservation_artifact_ref,prepared_handle_artifact_ref,execution_proof_artifact_ref FROM restriction_mapping_operations WHERE operation_key=?", (key, args["operation_key"]))
        with pytest.raises(ContractError, match="operation_conflict"):
            jobs.publication_state(key)
        store.db.execute("DELETE FROM restriction_mapping_operations WHERE operation_key=?", (key,))


def test_no_tool_operation_or_scientific_publication_was_fabricated(actual_job):
    store, jobs, args, state, _ = actual_job
    assert store.db.execute("SELECT COUNT(*) FROM tool_operations").fetchone()[0] == 0
    assert state["published_source_ref"] is None and state["published_outcome"] is None
    assert store.db.execute("SELECT COUNT(*) FROM records WHERE record_type='source' AND json_extract(data,'$.provider')='episode.restriction_result'").fetchone()[0] == 0


def engineering_arguments(directory):
    """Actual supplied engineering input and preparation only; never execute."""
    store = Store(directory / "store")
    store.create_problem(raw_sequence="AAAAGAATTCTTTT", molecule="dna")
    subject, = store.targets()
    tools = ToolRegistry(store)
    witness = restriction_sequence_witness(store, subject["id"], namespace="subject", scope=None,
        permitted_record_refs=[subject["id"]], sequence_reader=tools._sequence,
        check_operand=tools._check_sequence_operand)
    key = "restriction726-labelled-no-dispatch-engineering"
    arguments = {"mode": "native", "sequence_ref": subject["id"], "enzyme_names": ["EcoRI"], "topology": "linear"}
    retained = retain_restriction_input(store, operation_key=key, tool_name="find_restriction_sites",
        arguments=arguments, scope=witness["scope"], witness=witness)
    selected = json.loads(Path(os.environ["HMMER_NATIVE_ORACLE_RESTRICTION726_RETAINED_SELECTOR"]).read_bytes())
    software = deepcopy(selected["reservation_arguments"]["software"])
    root = Path(module.__file__).resolve().parent
    software["python"] = pin(sys.executable)
    software["implementation_files"] = [pin(path) for path in sorted(root.glob("restriction_mapping_*.py"))]
    job = module.restriction_operation_directory(store, key)
    software["environment"].update(PYTHONHOME=sys.prefix, PYTHONPATH=str(root.parent),
        TMPDIR=str(job), TMP=str(job), TEMP=str(job), XDG_CACHE_HOME=str(job / "cache"))
    args = {"operation_key": key, "tool_name": "find_restriction_sites", "arguments": arguments,
        "scope": witness["scope"], **retained, "worker_request": restriction_native_request(
            "find_restriction_sites", arguments, sequence=witness["sequence"], sequence_binding=retained["sequence_binding"]),
        "software": software, "policy": selected["reservation_arguments"]["policy"]}
    return store, module.RestrictionMappingJobs(store), args


@pytest.fixture(scope="module")
def prepared_engineering():
    if os.environ.get("HMMER_NATIVE_ORACLE_RESTRICTION726_PHASE") not in {"faults", "followup"}:
        pytest.skip("explicit separate fault-only followup")
    directory = Path(os.environ["HMMER529_ATTEMPT"]) / "labelled-no-native-engineering"
    directory.mkdir()
    store, jobs, args = engineering_arguments(directory)
    reservation = jobs.reserve(**args)
    save(directory / "reservation.json", reservation)
    yield store, jobs, args, reservation
    store.close()












