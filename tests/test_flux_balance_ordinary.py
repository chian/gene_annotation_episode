"""Ordinary FBA compiler and engineered lifecycle ports; no native solve.

Software records are explicitly uninstalled metadata controls. Legacy
materialization is only a whole-request oracle, not an ordinary commission or
permission proof. Lifecycle methods are controlled ports: no systemd job,
Cobra model, scientific capture, optimization or new Workflow is executed.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode import flux_balance_ordinary as ordinary
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.flux_balance_request_binding import _files, _materialize, _resolve_file
from gene_annotation_episode.flux_balance_worker_contracts import build_saved_flux_balance_worker_plan
from gene_annotation_episode.local_jobs import LocalJobPolicy, LocalJobResult
from gene_annotation_episode.molecular_measurement_tools import MolecularOperationUnpublished
from gene_annotation_episode.native_flux_balance_contracts import (POLICY, ATTEMPT_DIRECTORY_NAME,
    STARTED_FILENAME, bind_flux_balance_environment, flux_balance_output_files, validate_flux_balance_run_plan)
from test_flux_balance_execution_inputs_704 import selected
from test_flux_balance_operands_694 import software
from test_flux_balance_resource_registration_707 import _compact


def binding(sw=None):
    return {"version": "flux_balance_local_binding_v1", "operation": "perform_flux_balance_analysis",
        "mode": "steady_state_linear_fba", "software": software() if sw is None else deepcopy(sw),
        "model_formats": ["sbml", "cobra_json"]}


def explicit_request():
    return {"version": "flux_balance_scientific_request_v1", "operation": "perform_flux_balance_analysis",
        "mode": "steady_state_linear_fba", "model_input": {"file": {"witness_ref": "artifact_" + "b" * 64,
            "version": None, "artifact_field": None, "format": "cobra_json"},
            "original_loader_selection": "json_file", "repository_identifier": None, "acquisition_receipt_file": None},
        "constraints": None, "objective": {"kind": "model_default", "reaction_id": None},
        "solver_options": {"feasibility_tolerance": None, "optimality_tolerance": None, "integrality_tolerance": None}}


def explicit_files(request):
    return [{"selection": deepcopy(request["model_input"]["file"]), "file": {
        "artifact_ref": "artifact_" + "b" * 64, "sha256": "b" * 64, "size_bytes": 9, "format": "cobra_json"},
        "path": "/engineered/store/artifacts/bb/" + "b" * 64}]


@pytest.mark.parametrize("variant", ["source_default", "artifact_sbml", "repository_receipt", "prior_zero_bounds", "empty_constraints"])
def test_pure_compiler_whole_job_parity_with_original_materializer(selected, monkeypatch, variant):
    f = selected
    compact = _compact(f)
    request = compact["request"]
    witnesses = {f.source: f.store.get(f.source)}
    if variant == "artifact_sbml":
        request["model_input"]["file"].update(witness_ref=f.artifact, artifact_field=None, format="sbml")
        request["model_input"]["original_loader_selection"] = "sbml_file"
        witnesses[f.artifact] = f.store.get(f.artifact)
    elif variant in {"repository_receipt", "prior_zero_bounds"}:
        artifact = f.store.artifact(b"engineered explicit provenance; never parsed")
        record = f.store.put("source", {"provider": "engineered_ordinary_input", "accession": None,
            "artifact_ref": artifact, "text_ref": None, "request_ref": None, "uri": None,
            "version": None, "retrieved_at": None}, origin="tool", scope=f.records.scope)
        witnesses[record["id"]] = record
        chosen = {"witness_ref": record["id"], "version": None, "artifact_field": "artifact_ref", "format": "application/json"}
        if variant == "repository_receipt":
            request["model_input"].update(original_loader_selection="repository_identifier",
                repository_identifier="literal selected repository identifier", acquisition_receipt_file=chosen)
        else:
            request["constraints"] = [{"reaction_id": "explicit-hypothetical-reaction", **{side: {
                "kind": "finite", "value": 0, "native_token": "0", "float_hex": None,
                "source": {"file": deepcopy(chosen), "pointer": "/bounds/" + side}}
                for side in ("lower", "upper")}}]
            request["objective"] = {"kind": "single_reaction", "reaction_id": "explicit-hypothetical-reaction"}
            request["solver_options"]["feasibility_tolerance"] = 1e-8
    elif variant == "empty_constraints": request["constraints"] = []
    selected_binding = binding(f.assignment["requested_job"]["native_flux_balance"]["software"])
    assignment_id = "compiler-oracle"
    lifecycle = str(f.workspace / ".fba-selected-runtime" / assignment_id)
    resolved = []
    for selection in _files(request):
        file = _resolve_file(f.store, selection, witnesses)
        resolved.append({"selection": deepcopy(selection), "file": file,
            "path": str(f.store.path / "artifacts" / file["sha256"][:2] / file["sha256"])})
    row = {"selection": compact, "binding": selected_binding,
        "witness_records": [{"reference": ref, "record": record} for ref, record in witnesses.items()],
        "workspace": str(f.workspace), "assignment_id": assignment_id, "resource_id": "selected-local"}
    before = canonical({"request": request, "resolved": resolved, "binding": selected_binding})
    def forbidden(*args, **kwargs): raise AssertionError("compiler read bytes or acquired data")
    monkeypatch.setattr(f.store, "get_artifact", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    expected = _materialize(f.store, row)["requested_job"]
    actual = ordinary.compile_flux_balance_requested_job(request, binding=selected_binding,
        resolved_files=resolved, lifecycle_directory=lifecycle)
    assert canonical(actual) == canonical(expected)
    assert canonical({"request": request, "resolved": resolved, "binding": selected_binding}) == before
    assert actual["native_flux_balance"]["model_input"]["original_loader_selection"] == request["model_input"]["original_loader_selection"]
    assert actual["native_flux_balance"]["model_input"]["repository_identifier"] == request["model_input"]["repository_identifier"]


@pytest.mark.parametrize("fault", ["missing", "unselected", "conflicting_duplicate", "bad_hash", "bool_size",
    "relative_path", "format_conflict", "request_extra", "unbound_format", "software_interface"])
def test_compiler_rejects_selection_conflicts_without_io(monkeypatch, fault):
    request = explicit_request(); resolved = explicit_files(request); chosen = binding()
    if fault == "missing": resolved = []
    elif fault == "unselected": resolved[0]["selection"]["witness_ref"] = "artifact_" + "c" * 64
    elif fault == "conflicting_duplicate":
        resolved.append(deepcopy(resolved[0])); resolved[1]["path"] = "/different/path"
    elif fault == "bad_hash": resolved[0]["file"]["artifact_ref"] = "artifact_" + "0" * 64
    elif fault == "bool_size": resolved[0]["file"]["size_bytes"] = True
    elif fault == "relative_path": resolved[0]["path"] = "relative"
    elif fault == "format_conflict": resolved[0]["file"]["format"] = "sbml"
    elif fault == "request_extra": request["download"] = True
    elif fault == "unbound_format": chosen["model_formats"] = ["sbml"]
    else: chosen["software"]["solver_interface"] = "other"
    def forbidden(*args, **kwargs): raise AssertionError("invalid compilation attempted I/O")
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    with pytest.raises(ValueError):
        ordinary.compile_flux_balance_requested_job(request, binding=chosen, resolved_files=resolved,
            lifecycle_directory="/engineered/lifecycle")


def test_compiler_keeps_consistent_repeated_selections_and_detaches_output():
    request = explicit_request(); resolved = explicit_files(request)
    request["model_input"]["acquisition_receipt_file"] = deepcopy(request["model_input"]["file"])
    resolved.append(deepcopy(resolved[0]))
    result = ordinary.compile_flux_balance_requested_job(request, binding=binding(), resolved_files=resolved,
        lifecycle_directory="/engineered/lifecycle")
    assert result["native_flux_balance"]["model_input"]["acquisition_receipt_file"] == resolved[0]["file"]
    result["native_flux_balance"]["model_input"]["acquisition_receipt_file"]["size_bytes"] = 0
    assert resolved[0]["file"]["size_bytes"] == 9


@pytest.fixture
def lifecycle_case(tmp_path, monkeypatch):
    request = explicit_request(); chosen = binding()
    run_id, episode_id, key = "engineered-run", "engineered-episode", "engineered-run:engineered-episode:0"
    workspace = tmp_path / "work"; workspace.mkdir()
    root = workspace / ".episode-operations" / digest({"run": run_id, "episode": episode_id}) / digest(key)
    root.mkdir(parents=True)
    job = ordinary.compile_flux_balance_requested_job(request, binding=chosen,
        resolved_files=explicit_files(request), lifecycle_directory=str(root))
    selection = {"version": ordinary.SELECTION_VERSION, "mode": "solve", "resource_id": "explicit-local",
        "resource_kind": "local", "binding_ordinal_0based": 0, "workspace": str(workspace),
        "requested_job": job, "constraints": {"allocation": deepcopy(POLICY)},
        "native_flux_balance_execution": {"version": "flux_balance_execution_selection_v1",
            "environment_realization": "operation_scoped_tmp_and_cache_v1"}}
    owner = {"run_id": run_id, "episode_id": episode_id, "resource_id": selection["resource_id"],
        "execution_id": str(root / "native.json"), "attempt_id": digest(key), "operation_key": key,
        "requested_job_sha256": digest(job), "assignment_sha256": digest(selection)}
    plan = validate_flux_balance_run_plan({"version": "flux_balance_run_plan_v2", "identity": owner,
        "requested_job": job, "attempt_directory": str(root / ATTEMPT_DIRECTORY_NAME), "policy": deepcopy(POLICY),
        "outputs": flux_balance_output_files(job["native_flux_balance"]), "environment_binding": bind_flux_balance_environment(
            job, execution_id=owner["execution_id"], attempt_directory=str(root / ATTEMPT_DIRECTORY_NAME),
            selection=selection["native_flux_balance_execution"])})
    body = {"version": ordinary.native.VERSION, "unit": "engineered-existing-unit", "stage": "prepared"}
    handle = ordinary.native.NativeJobHandle(root / "native.json")
    handle.path.write_text(canonical(body))
    calls = []
    view = {"terminal": False, "quiescent": False, "metadata": {"policy": deepcopy(POLICY), "native_returncode": None}}
    def prepare(*args, **kwargs):
        calls.append(("prepare", args, kwargs)); return handle
    def plan_reader(*args):
        calls.append(("plan", args)); return deepcopy(plan)
    def status(selected):
        assert selected.path == handle.path; calls.append(("status", str(selected.path))); return deepcopy(view)
    def resume(selected, **kwargs):
        assert selected.path == handle.path; calls.append(("resume", str(selected.path), kwargs))
    def collect(selected):
        assert selected.path == handle.path; calls.append(("collect", str(selected.path)))
        return LocalJobResult(view["metadata"]["native_returncode"], root / "stdout", root / "stderr", deepcopy(view["metadata"]))
    def wait(selected, **kwargs):
        assert selected.path == handle.path; calls.append(("wait", str(selected.path), kwargs))
        view.update(terminal=True, quiescent=True); view["metadata"]["native_returncode"] = 0
        return LocalJobResult(0, root / "stdout", root / "stderr", deepcopy(view["metadata"]))
    monkeypatch.setattr(ordinary, "prepare_selected_local_flux_balance", prepare)
    monkeypatch.setattr(ordinary, "local_flux_balance_plan", plan_reader)
    for name, port in [("status", status), ("resume_start", resume), ("wait_job", wait), ("collect", collect)]:
        monkeypatch.setattr(ordinary.native, name, port)
    return SimpleNamespace(root=root, selection=selection, plan=plan, handle=handle, body=body, view=view, calls=calls,
        arguments={"run_id": run_id, "episode_id": episode_id, "root": root, "policy": LocalJobPolicy(**POLICY),
            "input_binding_receipt": {"engineered": "caller-authenticated-control"},
            "input_binding_file": {"engineered": "caller-retained-control"}}, key=key)


def run(case, **kwargs):
    return ordinary.run_selected_flux_balance_native(case.selection, case.key, **{**case.arguments, **kwargs})


def test_engineered_recovery_collects_same_handle_without_another_dispatch(lifecycle_case):
    case = lifecycle_case
    original = case.handle.path.read_bytes()
    event = object()
    first = run(case, cancel_event=event)
    second = run(case, cancel_event=event)
    assert first == second and first["failure"] is None and first["returncode"] == 0
    assert first["terminal"] is first["quiescent"] is True
    assert first["driver_started"] is None and "model_optimize_call_count" not in first
    assert [row[0] for row in case.calls].count("resume") == [row[0] for row in case.calls].count("wait") == 1
    assert [row[0] for row in case.calls].count("collect") == 1
    assert case.handle.path.read_bytes() == original
    preparation = [row for row in case.calls if row[0] == "prepare"]
    assert len(preparation) == 2 and all(row[1] == (case.selection, case.key) for row in preparation)
    assert all(row[2]["input_binding_receipt"] is case.arguments["input_binding_receipt"] for row in preparation)
    assert all(row[2]["cancel_event"] is event for row in case.calls if row[0] in {"resume", "wait"})


@pytest.mark.parametrize("mode", ["inspect", "edit", "read_stored", "calculate_saved", None])
def test_engineered_non_solve_modes_never_prepare_or_dispatch(lifecycle_case, mode):
    case = lifecycle_case; case.selection["mode"] = mode
    with pytest.raises(ValueError, match="selected_solve_required"): run(case)
    assert case.calls == []


@pytest.mark.parametrize("started", [False, True])
def test_engineered_start_marker_is_observed_or_unknown_never_inferred_zero(lifecycle_case, started):
    case = lifecycle_case
    if started:
        path = case.root / ATTEMPT_DIRECTORY_NAME / STARTED_FILENAME
        path.parent.mkdir(); path.write_text("engineered already-authenticated marker")
    value = run(case)
    assert value["driver_started"] is (True if started else None)
    assert not any("optimiz" in key or "solve_call" in key for key in value)


@pytest.mark.parametrize("step", ["resume", "wait"])
def test_engineered_unconfirmed_attempt_uses_unpublished_signal_without_replacement(lifecycle_case, monkeypatch, step):
    case = lifecycle_case
    original = case.handle.path.read_bytes()
    def failed(selected, **kwargs):
        assert selected.path == case.handle.path
        raise AcquisitionError("local_job_execution_unknown", phase="local_execution", operational={"original": "unknown"})
    monkeypatch.setattr(ordinary.native, "resume_start" if step == "resume" else "wait_job", failed)
    with pytest.raises(MolecularOperationUnpublished, match="original_attempt_unconfirmed"): run(case)
    assert [row[0] for row in case.calls].count("prepare") == 1
    assert case.handle.path.read_bytes() == original
    assert not any(row[0] == "collect" for row in case.calls)


@pytest.mark.parametrize("code,returncode", [("local_job_resource_limit", -9), ("local_job_execution_error", None)])
def test_engineered_known_terminal_failure_preserves_original_metadata(lifecycle_case, monkeypatch, code, returncode):
    case = lifecycle_case
    case.view.update(terminal=True, quiescent=True)
    case.view["metadata"].update(native_returncode=returncode, original_terminal_fact="retained")
    error = AcquisitionError(code, phase="local_execution", diagnostic={"original_private_control": "retained"},
        operational={"resource": "memory_bytes", "limit": POLICY["memory_bytes"]})
    def failed(selected):
        assert selected.path == case.handle.path
        raise error
    monkeypatch.setattr(ordinary.native, "collect", failed)
    value = run(case)
    assert value["returncode"] == returncode and value["metadata"] == case.view["metadata"]
    assert value["failure"] == {"code": error.code, "phase": error.phase,
        "diagnostic": error.diagnostic, "operational": error.operational}
    assert value["handle"] == case.body and value["driver_started"] is None
    assert not any(row[0] in {"resume", "wait"} for row in case.calls)


def test_engineered_nonzero_native_return_is_retained_for_qualified_capture(lifecycle_case):
    case = lifecycle_case
    case.view.update(terminal=True, quiescent=True); case.view["metadata"]["native_returncode"] = 2
    value = run(case)
    assert value["returncode"] == 2 and value["failure"] is None
    assert value["metadata"]["native_returncode"] == 2
    assert not any(row[0] in {"resume", "wait"} for row in case.calls)


def saved_plan(tmp_path):
    file = {"artifact_ref": "artifact_" + "c" * 64, "sha256": "c" * 64, "size_bytes": 3, "format": "flux_balance_sheet_v1"}
    selector = {"version": "flux_balance_result_selector_v1", "mode": "saved_sheet_recalculation", "saved_sheet_file": file,
        "calculation_parameters": {"version": "fba_calculation_parameters_v1", "reaction_bound_tolerances": [],
            "constraint_tolerances": [], "active_flux_thresholds": [], "objective_absolute_tolerance": None,
            "variable_bound_tolerances": [], "reaction_flux_tolerances": [], "constraint_activity_tolerances": []},
        "projection": {"version": "flux_balance_projection_selector_v1", "view": "run_diagnostics", "fields": ["native_run"],
            "row_window": {"offset": 0, "limit": 1}}}
    return build_saved_flux_balance_worker_plan(directory=str(tmp_path / "worker/output"),
        sheet={"file": file, "path": "/engineered/store/artifacts/cc/" + "c" * 64}, selector=selector)


def test_result_worker_forwards_explicit_selected_software_on_caller_thread(tmp_path, monkeypatch):
    import threading
    plan = saved_plan(tmp_path); selected = software(); store = object(); sentinel = object(); calls = []
    def prepare(received_store, **kwargs):
        calls.append((received_store, kwargs, threading.get_ident())); return sentinel
    monkeypatch.setattr(ordinary, "prepare_flux_balance_result_worker", prepare)
    policy = LocalJobPolicy(**POLICY)
    actual = ordinary.run_selected_flux_balance_result_worker(store, plan=plan, software=selected, policy=policy)
    assert actual is sentinel
    assert calls == [(store, {"plan": plan, "software": selected, "policy": policy}, threading.get_ident())]


@pytest.mark.parametrize("bad", [None, {}, "default"])
def test_result_worker_refuses_absent_or_invalid_selected_software_before_preparation(tmp_path, monkeypatch, bad):
    def forbidden(*args, **kwargs): raise AssertionError("invalid software reached worker preparation")
    monkeypatch.setattr(ordinary, "prepare_flux_balance_result_worker", forbidden)
    with pytest.raises(ValueError):
        ordinary.run_selected_flux_balance_result_worker(object(), plan=saved_plan(tmp_path), software=bad,
            policy=LocalJobPolicy(**POLICY))


def test_engineered_native_result_requires_the_original_explicit_software(monkeypatch):
    selected = software()
    # A metadata-only wrapper control; the existing worker-plan validator and
    # scientific capture are deliberately outside this port-matching assertion.
    plan = {"mode": "native_result", "original_plan": {"requested_job": {"native_flux_balance": {"software": selected}}}}
    monkeypatch.setattr(ordinary, "validate_flux_balance_worker_plan", lambda value: value)
    changed = deepcopy(selected); changed["python_version"] = "different explicit selection"
    def forbidden(*args, **kwargs): raise AssertionError("conflicting native software reached preparation")
    monkeypatch.setattr(ordinary, "prepare_flux_balance_result_worker", forbidden)
    with pytest.raises(ValueError, match="result_software_conflict"):
        ordinary.run_selected_flux_balance_result_worker(object(), plan=plan, software=changed, policy=LocalJobPolicy(**POLICY))
