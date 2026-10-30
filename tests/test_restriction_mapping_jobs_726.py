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
from gene_annotation_episode.tools import ToolRegistry
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
        "software": software, "policy": {"memory_bytes": 20 * 1024**3,
            "scratch_bytes": 4 * 1024**3, "wall_seconds": None}}
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
    assert meta["verified_cgroup"]["runtime_max"] == "infinity"
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


def test_prepared_state_has_no_execution_proof_or_dispatch(prepared_engineering, monkeypatch):
    _, jobs, args, reservation = prepared_engineering
    monkeypatch.setattr(module.native, "resume_start", forbid)
    monkeypatch.setattr(module.native, "wait_job", forbid)
    state = jobs.publication_state(args["operation_key"])
    assert state["execution_proof"] is None and state["execution_proof_artifact_ref"] is None
    assert not Path(reservation["output_directory"]).exists()
    assert module.native.NativeJobHandle(Path(reservation["handle_path"])).read()["stage"] == "prepared"


@pytest.mark.parametrize("role", ["request", "handle", "control", "input"])
def test_labelled_pre_dispatch_mutations_fail_without_dispatch(prepared_engineering, monkeypatch, role):
    store, jobs, args, reservation = prepared_engineering
    monkeypatch.setattr(module.native, "resume_start", forbid)
    monkeypatch.setattr(module.native, "wait_job", forbid)
    handle = module.native.NativeJobHandle(Path(reservation["handle_path"]))
    if role == "request":
        path = Path(reservation["request_file"]["path"])
    elif role == "handle":
        path = handle.path
    elif role == "control":
        path = Path(handle.read()["paths"]["request"])
    else:
        source = store.get(args["input_source_ref"])
        digest = source["artifact_ref"].removeprefix("artifact_")
        path = store.path / "artifacts" / digest[:2] / digest
    original = path.read_bytes()
    try:
        if role == "handle":
            body = json.loads(original)
            body["unit"] = "wrong-selected-unit.service"
            path.write_text(json.dumps(body))
        else:
            path.write_bytes(original + b" ")
        with pytest.raises((ContractError, ValueError)):
            asyncio.run(jobs.run_async(args["operation_key"]))
    finally:
        path.write_bytes(original)
    assert jobs.publication_state(args["operation_key"])["execution_proof"] is None


def test_labelled_unknown_execution_is_retained_without_substitution(prepared_engineering, monkeypatch):
    store, jobs, args, reservation = prepared_engineering
    real_status = module.native.status
    handle = module.native.NativeJobHandle(Path(reservation["handle_path"]))
    unknown = real_status(handle)
    unknown.update(state="execution_unknown", terminal=False, quiescent=True)
    monkeypatch.setattr(module.native, "status", lambda selected: deepcopy(unknown))
    calls = []
    def unavailable(selected, *, cancel_event):
        calls.append(str(selected.path))
        raise module.AcquisitionError("local_job_execution_unknown", phase="local_execution",
            operational=unknown["metadata"])
    monkeypatch.setattr(module.native, "resume_start", unavailable)
    monkeypatch.setattr(module.native, "wait_job", forbid)
    with pytest.raises(module.AcquisitionError, match="local_job_execution_unknown"):
        asyncio.run(jobs.run_async(args["operation_key"]))
    assert calls == [reservation["handle_path"]]
    row = jobs._row(args["operation_key"])
    failure = json.loads(store.get_artifact(row["failure_artifact_ref"]))
    assert failure["code"] == "local_job_execution_unknown"
    assert failure["original_view"]["state"] == "execution_unknown"
    assert row["execution_proof_artifact_ref"] is None
    assert not Path(reservation["output_directory"]).exists()


def test_labelled_preparation_interruption_preserves_original_reservation(tmp_path, monkeypatch):
    if os.environ.get("HMMER_NATIVE_ORACLE_RESTRICTION726_PHASE") not in {"faults", "followup"}:
        pytest.skip("explicit separate fault-only followup")
    store, jobs, args = engineering_arguments(tmp_path)
    original_prepare = module.native.prepare_job
    calls = []
    def interrupted(*operands, **selected):
        calls.append(selected["handle_path"])
        raise module.AcquisitionError("local_job_boundary_unavailable", phase="local_preflight",
            operational={"reason": "labelled engineering interruption before handle publication"})
    monkeypatch.setattr(module.native, "prepare_job", interrupted)
    with pytest.raises(module.AcquisitionError):
        jobs.reserve(**args)
    row = jobs._row(args["operation_key"])
    assert row["prepared_handle_artifact_ref"] is None
    assert row["failure_artifact_ref"] is not None
    assert jobs._reservation(row)["policy"] == args["policy"]
    assert jobs.publication_state(args["operation_key"])["execution_proof"] is None
    changed = deepcopy(args)
    changed["policy"]["wall_seconds"] = 1
    with pytest.raises(ContractError, match="operation_conflict"):
        jobs.reserve(**changed)
    monkeypatch.setattr(module.native, "prepare_job", original_prepare)
    reservation = jobs.reserve(**args)
    assert Path(reservation["handle_path"]).is_file()
    assert jobs.publication_state(args["operation_key"])["execution_proof"] is None
    assert len(calls) == 1 and not Path(reservation["output_directory"]).exists()
    store.close()


def test_labelled_async_cancellation_retains_adapter_failure(prepared_engineering, monkeypatch):
    store, jobs, args, reservation = prepared_engineering
    async def cancellation(function, handle, *, completed):
        completed["failure"] = {"code": "local_job_cancelled", "phase": "local_execution",
            "operational": {"reason": "labelled adapter cancellation, no native dispatch"}}
        raise asyncio.CancelledError()
    monkeypatch.setattr(module, "run_cancellable_native", cancellation)
    monkeypatch.setattr(module.native, "resume_start", forbid)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(jobs.run_async(args["operation_key"]))
    row = jobs._row(args["operation_key"])
    failure = json.loads(store.get_artifact(row["failure_artifact_ref"]))
    assert failure["code"] == "local_job_cancelled"
    assert row["execution_proof_artifact_ref"] is None
    assert not Path(reservation["output_directory"]).exists()


def test_dependent_original_published_fixture_retires_without_native(monkeypatch):
    if os.environ.get("HMMER_NATIVE_ORACLE_RESTRICTION726_PHASE") not in {"retire", "followup"}:
        pytest.skip("depends on725 publication and committed original ToolRegistry save")
    selected = json.loads(Path(os.environ["HMMER_NATIVE_ORACLE_RESTRICTION726_RETAINED_SELECTOR"]).read_bytes())
    store = Store(selected["store_path"])
    jobs = module.RestrictionMappingJobs(store)
    key = selected["operation_key"]
    state = jobs.publication_state(key)
    save(Path(os.environ["HMMER529_ATTEMPT"]) / "before-retirement.json", state)
    assert state["published_source_ref"] is not None
    # Exact original-operation save follows725's earlier publication commit.
    # This fixture verifies this custody join; it is not an atomic Workflow run.
    tools = ToolRegistry(store)
    original_row = store.db.execute("SELECT 1 FROM tool_operations WHERE operation_key=?", (key,)).fetchone()
    if original_row is None:
        with store.transaction():
            reservation = state["reservation"]
            tools._save(key, reservation["tool_name"], reservation["arguments"],
                reservation["scope"], deepcopy(state["published_outcome"]))
    # Labelled rollback checks Tools' raw default scope at the exact authority
    # join. The original committed operation remains unchanged.
    class RollbackDefaultScope(Exception):
        pass
    try:
        with store.transaction():
            store.db.execute("UPDATE tool_operations SET scope='null' WHERE operation_key=?", (key,))
            jobs._original_operation(state)
            raise RollbackDefaultScope()
    except RollbackDefaultScope:
        pass
    from gene_annotation_episode import restriction_mapping_readers, restriction_mapping_worker
    monkeypatch.setattr(restriction_mapping_readers, "read_restriction_mapping", forbid)
    monkeypatch.setattr(restriction_mapping_worker, "read_restriction_mapping", forbid)
    original_import = builtins.__import__
    def controlled_import(name, *args, **kwargs):
        if name == "Bio" or name.startswith("Bio.") or name.endswith("restriction_mapping_native"):
            raise AssertionError("native import forbidden in dependent saved-only retirement")
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", controlled_import)
    monkeypatch.setattr(module.native, "resume_start", forbid)
    monkeypatch.setattr(module.native, "prepare_job", forbid)
    monkeypatch.setattr(module.native, "wait_job", forbid)
    with store.transaction():
        with pytest.raises(ContractError, match="retirement_requires_committed_publication"):
            jobs.retire(key)
    original_release = module.native.release
    def cleanup_unavailable(handle):
        raise module.AcquisitionError("local_job_boundary_unavailable", phase="local_execution",
            operational={"reason": "labelled cleanup failure before deletion"})
    monkeypatch.setattr(module.native, "release", cleanup_unavailable)
    with pytest.raises(module.AcquisitionError, match="local_job_boundary_unavailable"):
        jobs.retire(key)
    assert jobs.publication_state(key) == state
    failure = json.loads(store.get_artifact(jobs._row(key)["failure_artifact_ref"]))
    assert failure["phase"] == "cleanup" and Path(state["reservation"]["output_directory"]).is_dir()
    monkeypatch.setattr(module.native, "release", original_release)
    original_remove = module.shutil.rmtree
    def removal_interrupted(directory):
        raise OSError("labelled interruption after original native controls released")
    monkeypatch.setattr(module.shutil, "rmtree", removal_interrupted)
    with pytest.raises(OSError, match="labelled interruption"):
        jobs.retire(key)
    assert jobs.publication_state(key) == state
    assert not Path(state["reservation"]["handle_path"]).exists()
    assert Path(state["reservation"]["output_directory"]).is_dir()
    monkeypatch.setattr(module.shutil, "rmtree", original_remove)
    monkeypatch.setattr(module.native, "status", forbid)
    jobs.retire(key)
    assert not Path(state["reservation"]["directory"]).exists()
    monkeypatch.setattr(module.native, "status", forbid)
    assert jobs.publication_state(key) == state
    assert asyncio.run(jobs.run_async(key)) == state["execution_proof"]
    jobs.retire(key)
    save(Path(os.environ["HMMER529_ATTEMPT"]) / "after-retirement.json", jobs.publication_state(key))
    row = dict(store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (key,)).fetchone())
    save(Path(os.environ["HMMER529_ATTEMPT"]) / "closed-selector.json", {
        "store_path": str(store.path), "operation_key": key,
        "published_source_ref": state["published_source_ref"],
        "published_outcome": state["published_outcome"], "original_tool_operation": row,
        "reservation_artifact_ref": state["reservation_artifact_ref"],
        "execution_proof_artifact_ref": state["execution_proof_artifact_ref"],
        "retired": bool(jobs._row(key)["retired"]),
        "original_selector_sha256": pin(Path(os.environ["HMMER_NATIVE_ORACLE_RESTRICTION726_RETAINED_SELECTOR"]))["sha256"],
        "new_native_searches": 0, "reader719_calls": 0,
        "qualification": "725 publication committed before this original ToolRegistry save; not atomic Workflow proof"})
    store.close()
