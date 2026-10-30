"""C3 bounded native/worker evidence; synthetic source matrices remain labeled.

Run via packet444/run_bounded.py. Actual local native lifecycle and complete
Store capture are used; source/action authority labels in fixture plans do not
claim episode communication or full Workflow verification.
"""
from copy import deepcopy
import asyncio
import json
import os
from pathlib import Path
import shutil
import sys
import time

import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_file_capture import capture_native_file, capture_declared_native_files, retained_native_file
from gene_annotation_episode.state import Store
from gene_annotation_episode.native_chromatin_interaction_contracts import (
    POLICY, ATTEMPT_DIRECTORY_NAME, RUN_PLAN_FILENAME, digest, chromatin_output_files,
    requested_job_from_chromatin, validate_chromatin_requested_job, validate_chromatin_run_plan,
    chromatin_driver_argv, chromatin_environment, validate_chromatin_population_seal,
    _dependency_roots,
)
from gene_annotation_episode.native_chromatin_interaction_driver import _immutable, _read_control, run_chromatin_interaction_driver
from gene_annotation_episode.native_chromatin_interaction_preparation import (
    freeze_chromatin_software_binding, build_native_chromatin_worker_plan, build_saved_chromatin_worker_plan,
    prepare_chromatin_result_worker,
)
from gene_annotation_episode.chromatin_interaction_result_worker import run_chromatin_result_worker, validate_chromatin_result_worker_plan

REPO = Path(os.environ["C3_ORIGINAL_REPO"])
PACKET = Path(os.environ["C3_PACKET"])
ATTEMPT = Path(os.environ["C3_ATTEMPT"])
NATIVE_FIXTURES = REPO / "verification/tool_graders_chromatin_native_prerequisites_2026-10-27_440/fixture_generation/fixtures"
WORKED = {r["example_key"]: r["record"] for r in json.loads((REPO / "verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/WORKED_RECORDS.json").read_text())["records"]}


@pytest.fixture(scope="session")
def software():
    import gene_annotation_episode.native_chromatin_interaction_driver as driver
    result = freeze_chromatin_software_binding(module_root=str(Path(driver.__file__).parents[1]),
        snapshot_directory=str(ATTEMPT / "selected_software"), python_executable=sys.executable)
    (ATTEMPT / "SOFTWARE_BINDING.json").write_text(json.dumps(result, indent=2) + "\n")
    assert {r["distribution"]: r["version"] for r in result["dependencies"]}["numpy"] == "2.5.0"
    assert {r["distribution"]: r["version"] for r in result["dependencies"]}["h5py"] == "3.16.0"
    assert {"typing-extensions", "idna", "jsonpointer"} <= {row["distribution"] for row in result["dependencies"]}
    return result


def make_plan(directory, software, *, case="raw", populations=1, population_ends=None, negative_native=False):
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / "supplied"
    source.mkdir()
    request = deepcopy(WORKED[case + ".request"])
    native_name = "six-bin-all-full-windows.cool" if case == "insulation" else "four-bin-raw-weighted.cool"
    shutil.copyfile(NATIVE_FIXTURES / native_name, source / "contact.cool")
    if negative_native:
        import h5py
        with h5py.File(source / "contact.cool", "r+") as stream:
            stream["pixels/count"][1] = -3
    bindings = []
    with Store(directory / "store") as store:
        identity = capture_native_file(store, directory=str(source), relative_path="contact.cool", format="cooler_hdf5_v3")
        request["contact"]["file"] = identity
        bindings.append({"input_key": request["contact"]["input_key"], "file": identity, "path": str(source / "contact.cool")})
        if request["elements"] is not None:
            (source / "elements.bed").write_bytes(b"chrA\t0\t2\tE\nchrA\t20\t23\tP\nchrA\t30\t33\tQ\n")
            identity = capture_native_file(store, directory=str(source), relative_path="elements.bed", format="bed_outer_span_v1")
            request["elements"]["file"] = identity
            bindings.append({"input_key": request["elements"]["input_key"], "file": identity, "path": str(source / "elements.bed")})
    request["populations"] = [{**request["populations"][0], "population_key": f"p{i}"} for i in range(populations)]
    if population_ends is not None:
        assert len(population_ends) == populations
        for population, end in zip(request["populations"], population_ends):
            population["end_bp"] = end
    request["output_prefix"] = "selected-output"
    roots = _dependency_roots(software)
    environment = {"PYTHONPATH": os.pathsep.join([software["module_root"], *roots]), "PYTHONHOME": sys.base_prefix,
        "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "TMPDIR": str(directory / "tmp"), "TMP": str(directory / "tmp"), "TEMP": str(directory / "tmp"),
        "XDG_CACHE_HOME": str(directory / "cache"), "PIP_CACHE_DIR": str(directory / "cache/pip"),
        "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
    requested = requested_job_from_chromatin({"request": request, "software": software, "input_bindings": bindings}, environment=environment)
    run, episode, operation = "c3-fixture-run", "local-child", "selected-start"
    root = directory / ".episode-operations" / digest({"run": run, "episode": episode}) / digest(operation)
    plan = validate_chromatin_run_plan({"version": "chromatin_interaction_run_plan_v1", "identity": {
        "run_id": run, "episode_id": episode, "resource_id": "selected-local", "execution_id": str(root / "native.json"),
        "operation_key": operation, "attempt_id": digest(operation), "requested_job_sha256": digest(requested),
        "assignment_sha256": digest({"fixture": "native component, no episode authority"})},
        "requested_job": requested, "attempt_directory": str(root / ATTEMPT_DIRECTORY_NAME), "policy": POLICY,
        "outputs": chromatin_output_files(request)})
    root.mkdir(parents=True)
    _immutable(root / RUN_PLAN_FILENAME, plan)
    return plan


def launch(plan):
    root = Path(plan["identity"]["execution_id"]).parent
    handle = native.prepare_job(chromatin_driver_argv(plan), cwd=root, policy=LocalJobPolicy(**POLICY),
        handle_path=root / "native.json", env=chromatin_environment(plan["requested_job"]["native_chromatin_interactions"],
            attempt_directory=plan["attempt_directory"], environment=plan["requested_job"]["environment"]))
    native.resume_start(handle)
    return handle


def complete(plan):
    handle = launch(plan)
    outcome = native.wait_job(handle)
    assert native.status(handle)["terminal"] and native.status(handle)["quiescent"]
    if outcome.returncode:
        pytest.fail(outcome.stderr_path.read_text() + outcome.stdout_path.read_text())
    return _read_control(Path(plan["attempt_directory"]) / plan["outputs"][-1]["relative_path"])


def capture_plan(directory, plan, selector, *, interrupted=False):
    native_dir = Path(plan["attempt_directory"])
    bundle = None if interrupted else _read_control(native_dir / plan["outputs"][-1]["relative_path"])
    with Store(directory / "capture-store") as store:
        rows = []
        declarations = {r["specification"]["file_key"]: r["declaration"] for r in bundle["outputs"]} if bundle else {}
        for spec in plan["outputs"][:-1]:
            if spec["file_key"] in declarations:
                capture = capture_declared_native_files(store, directory=str(native_dir), declarations=[declarations[spec["file_key"]]])[0]
                identity, origin = capture["observed"], "bundle"
            else:
                capture, identity, origin = None, None, "none"
                path = native_dir / spec["relative_path"]
                if path.exists():
                    identity = capture_native_file(store, directory=str(native_dir), relative_path=spec["relative_path"], format=spec["format"])
                if spec["role"] in ("bins", "contacts", "weights", "cell_states", "dense_values"):
                    ordinal = next(i for i, p in enumerate(plan["requested_job"]["native_chromatin_interactions"]["request"]["populations"]) if p["population_key"] == spec["population_key"])
                    seal_path = native_dir / next(r["relative_path"] for r in plan["outputs"] if r["file_key"] == f"p{ordinal}.population_manifest")
                    if seal_path.exists():
                        seal = _read_control(seal_path)
                        declared = next(r["declaration"] for r in seal["tables"] if r["draft"]["role"] == spec["role"])
                        capture = capture_declared_native_files(store, directory=str(native_dir), declarations=[declared])[0]
                        identity, origin = capture["observed"], "population"
            rows.append({"specification": spec, "declaration_source": origin, "capture": capture,
                "retained": {"file": identity, "path": str(retained_native_file(store, identity))} if identity else None})
        bundle_retained = None
        if bundle:
            identity = capture_native_file(store, directory=str(native_dir), relative_path=plan["outputs"][-1]["relative_path"], format="chromatin_interaction_native_bundle_v1")
            bundle_retained = {"file": identity, "path": str(retained_native_file(store, identity))}
        result = build_native_chromatin_worker_plan(directory=str(directory / "worker"), original_plan=plan, bundle=bundle_retained,
            files=rows, selector=selector, source_action_receipt_ref="fixture:original-action", writer_closure_receipt_ref="fixture:actual-terminal-closure",
            driver_state="unsealed_attempt" if interrupted else "sealed_bundle", failures=[])
    return result


def saved_plan(directory, worker_plan, *, fold=1):
    with Store(directory / "saved-store") as store:
        output = Path(worker_plan["directory"])
        sheet_identity = capture_native_file(store, directory=str(output), relative_path="sheet.json", format="chromatin_interaction_sheet_v1")
        sheet = _read_control(output / "sheet.json")
        worker_result = _read_control(output / "worker-result.json")
        tables = []
        for row in worker_result["outputs"][4:]:
            if row["declaration"]["state"] == "absent":
                continue
            identity = capture_native_file(store, directory=str(output), relative_path=row["declaration"]["relative_path"], format=row["declaration"]["format"])
            tables.append({"file": identity, "path": str(retained_native_file(store, identity))})
        bundle = {"sheet": {"file": sheet_identity, "path": str(retained_native_file(store, sheet_identity))}, "tables": tables}
        selector = deepcopy(worker_plan["selector"])
        selector.update(mode="saved_sheet_recalculation", saved_sheet_bundle={"sheet": sheet_identity, "tables": [r["file"] for r in tables]})
        if selector["parameters"]["contact"]:
            selector["parameters"]["contact"]["fold_threshold"] = fold
        return build_saved_chromatin_worker_plan(directory=str(directory / "saved-worker"), sheet_bundle=bundle, selector=selector)


@pytest.mark.parametrize("case", ["raw", "weighted", "insulation"])
def test_real440_native_producer_and_c1_c2_worker(tmp_path, software, case):
    plan = make_plan(tmp_path, software, case=case)
    bundle = complete(plan)
    assert bundle["extraction"]["populations"][0]["extent"] == "complete"
    assert all(r["specification"]["relative_path"].startswith("selected-output/") for r in bundle["outputs"])
    worker_plan = capture_plan(tmp_path, plan, deepcopy(WORKED[case + ".selector"]))
    result = run_chromatin_result_worker(worker_plan)
    assert result["state"] == "produced", result
    components = _read_control(Path(worker_plan["directory"]) / "components.json")
    (ATTEMPT / (case + "-components.json")).write_text(json.dumps(components, indent=2) + "\n")
    projection = _read_control(Path(worker_plan["directory"]) / "projection.json")
    expected = WORKED[case + ".projection"]
    expected = deepcopy(expected)
    if case == "insulation":
        # Actual440 file plus insulation-only request supply no element-side
        # reference assertion; the historical symbolic example did.
        for row in expected["rows"]:
            row["qualifications"]["reference_relation"] = "unknown"
    #439 uses symbolic display-based pair keys; C1 keys actual BED occurrences.
    assert len(projection["rows"]) == len(expected["rows"])
    for actual, wanted in zip(projection["rows"], expected["rows"]):
        assert {k: v for k, v in actual.items() if k not in ("pair_key", "domain_key", "fields")} == {
            k: v for k, v in wanted.items() if k not in ("pair_key", "domain_key", "fields")}
        for key, measure in actual["fields"].items():
            assert set(measure) == set(wanted["fields"][key])
            for field, expected_value in wanted["fields"][key].items():
                assert measure[field] == (pytest.approx(expected_value) if type(expected_value) in (float, int) else expected_value)
    assert result["source_sheet_sha256"] == components["source_sheet_sha256"]


def test_actual_saved_parameter_change_without_original_input(tmp_path, software):
    plan = make_plan(tmp_path, software, case="weighted")
    complete(plan)
    worker_plan = capture_plan(tmp_path, plan, deepcopy(WORKED["weighted.selector"]))
    assert run_chromatin_result_worker(worker_plan)["state"] == "produced"
    saved = saved_plan(tmp_path, worker_plan, fold=0.5)
    original_sheet = (Path(worker_plan["directory"]) / "sheet.json").read_bytes()
    shutil.rmtree(tmp_path / "supplied")
    shutil.rmtree(plan["attempt_directory"])
    with Store(tmp_path / "saved-store") as store:
        captured = prepare_chromatin_result_worker(store, plan=saved, policy=LocalJobPolicy(**POLICY))
    result = captured["result"]
    assert result["state"] == "produced"
    assert (Path(saved["directory"]) / "sheet.json").read_bytes() == original_sheet
    assert result["parameters"]["contact"]["fold_threshold"] == 0.5
    assert set(saved) == {"version", "mode", "directory", "sheet_bundle", "selector"}
    for forbidden in ("original_plan", "input_bindings", "software", "bundle", "files"):
        changed = deepcopy(saved)
        changed[forbidden] = {}
        with pytest.raises(ValueError):
            validate_chromatin_result_worker_plan(changed)
    missing = deepcopy(saved)
    missing["directory"] = str(tmp_path / "missing-table-worker")
    Path(missing["sheet_bundle"]["tables"][0]["path"]).unlink()
    partial = run_chromatin_result_worker(missing)
    assert partial["state"] == "partial"
    assert any(f["code"] == "input_unavailable" for f in partial["failures"])
    assert partial["outputs"][1]["declaration"]["state"] == "absent"
    assert len(partial["outputs"][4:]) == len(_read_control(Path(saved["directory"]) / "sheet.json")["data_tables"])
    assert partial["outputs"][4]["declaration"]["state"] == "absent"
    assert any(row["declaration"]["state"] == "present" for row in partial["outputs"][5:])
    assert (Path(saved["directory"]) / "sheet.json").read_bytes() == original_sheet


def test_worker_preparation_actual_lifecycle_and_replay(tmp_path, software):
    plan = make_plan(tmp_path, software)
    complete(plan)
    worker_plan = capture_plan(tmp_path, plan, deepcopy(WORKED["raw.selector"]))
    with Store(tmp_path / "capture-store") as store:
        result = prepare_chromatin_result_worker(store, plan=worker_plan, policy=LocalJobPolicy(**POLICY))
        assert result["result"]["state"] == "produced", result
        handle = json.loads((Path(worker_plan["directory"]) / "worker.handle.json").read_text())
        assert prepare_chromatin_result_worker(store, plan=worker_plan, policy=LocalJobPolicy(**POLICY)) == result
        assert json.loads((Path(worker_plan["directory"]) / "worker.handle.json").read_text())["unit"] == handle["unit"]


@pytest.mark.parametrize("change", ["missing", "changed"])
def test_original_input_failure_has_no_zero_matrix(tmp_path, software, change):
    plan = make_plan(tmp_path, software)
    source = Path(plan["requested_job"]["native_chromatin_interactions"]["input_bindings"][0]["path"])
    source.unlink() if change == "missing" else source.write_bytes(b"changed")
    outcome = native.wait_job(launch(plan))
    assert outcome.returncode == 1
    bundle = _read_control(Path(plan["attempt_directory"]) / plan["outputs"][-1]["relative_path"])
    population = bundle["extraction"]["populations"][0]
    assert population["extent"] == "unavailable" and population["bin_count"] is None
    assert population["raw_cell_population"]["directed_cells"] is None
    assert any(f["code"] == ("input_unavailable" if change == "missing" else "input_digest_mismatch") for f in bundle["failures"])


@pytest.mark.parametrize("which", ["python", "dependency"])
def test_actual_producer_rejects_wrong_selected_software_pin(tmp_path, software, which):
    changed = deepcopy(software)
    if which == "python":
        changed["python_sha256"] = "0" * 64
    else:
        changed["dependencies"][0]["files"][0]["sha256"] = "0" * 64
    plan = make_plan(tmp_path, changed)
    outcome = native.wait_job(launch(plan))
    assert outcome.returncode == 1
    bundle = _read_control(Path(plan["attempt_directory"]) / plan["outputs"][-1]["relative_path"])
    assert any(f["code"] == "native_dependency_unavailable" for f in bundle["failures"])
    population = bundle["extraction"]["populations"][0]
    assert population["extent"] == "unavailable" and population["raw_cell_population"]["directed_cells"] is None
    assert all(row["declaration"]["state"] == "absent" for row in bundle["outputs"][:5])


def test_actual_negative_native_rows_and_source_locations_survive_worker(tmp_path, software):
    import numpy as np
    plan = make_plan(tmp_path, software, negative_native=True)
    outcome = native.wait_job(launch(plan))
    # The native read completed; a retained invalid measurement is a separate
    # scientific qualification, not a fabricated execution failure.
    assert outcome.returncode == 0
    bundle = _read_control(Path(plan["attempt_directory"]) / plan["outputs"][-1]["relative_path"])
    located = [f for f in bundle["extraction"]["failures"] if f["code"] == "native_value_negative"]
    assert located and all(f["locator"]["kind"] == "native_row" and f["locator"]["value"]["row_index"] == 1 for f in located)
    worker = capture_plan(tmp_path, plan, deepcopy(WORKED["raw.selector"]))
    result = run_chromatin_result_worker(worker)
    assert result["state"] == "produced", result
    sheet = _read_control(Path(worker["directory"]) / "sheet.json")
    assert any(f["code"] == "native_value_negative" for f in sheet["failures"])
    table = next(row for row in result["outputs"] if row["table_key"] == next(
        d["table_key"] for d in sheet["data_tables"] if d["role"] == "contacts"))
    records = np.load(Path(worker["directory"]) / table["declaration"]["relative_path"], allow_pickle=False)
    row = records[records["source_row"] == 1]
    assert len(row) == 1 and row[0]["value"] == -3 and row[0]["source_block"] == -1


def test_strict_plan_joins_and_no_scope_expansion(tmp_path, software):
    plan = make_plan(tmp_path, software)
    for mutate in (lambda p: p["outputs"].reverse(), lambda p: p["identity"].update(attempt_id="a" * 64),
            lambda p: p["requested_job"]["native_chromatin_interactions"]["input_bindings"][0].update(input_key="foreign"),
            lambda p: p["requested_job"]["argv"].insert(1, "-c")):
        changed = deepcopy(plan)
        mutate(changed)
        with pytest.raises(ValueError):
            validate_chromatin_run_plan(changed)
    changed = deepcopy(plan)
    changed["policy"]["wall_seconds"] = 1
    with pytest.raises(ValueError):
        validate_chromatin_run_plan(changed)
    changed = deepcopy(plan["requested_job"])
    changed["native_chromatin_interactions"]["request"]["contact"]["format"] = "hic_binary_v9"
    with pytest.raises(ValueError):
        validate_chromatin_requested_job(changed)


def test_tool_information_binds_real_commission_schema(tmp_path, software):
    from jsonschema import Draft202012Validator, ValidationError
    from gene_annotation_episode.native_chromatin_interaction_tool_info import (
        chromatin_interaction_tool_contracts, chromatin_interaction_tool_information)
    plan = make_plan(tmp_path, software)
    bindings = [{"operation": "analyze_chromatin_interactions", "resource_kind": "local", "software": software,
        "supported_formats": ["cooler_hdf5_v3"], "analysis_modes": ["cis_anchor_contact_enrichment"]}]
    contracts = chromatin_interaction_tool_contracts(bindings, resource_kind="local", resource_id="selected-local")
    assert contracts[0]["invocation_route"] == {"kind": "commission", "routes": [
        {"entry_role": "launch", "resource_id": "selected-local", "resource_role": "launch_local"}]}
    information = chromatin_interaction_tool_information(bindings, resource_kind="local", resource_id="selected-local")
    assert set(information[0]) == {"name", "description", "resources", "instructions"}
    validator = Draft202012Validator(contracts[0]["input_schema"])
    validator.validate(plan["requested_job"])
    changed = deepcopy(plan["requested_job"])
    changed["native_chromatin_interactions"]["software"]["python_sha256"] = "0" * 64
    with pytest.raises(ValidationError):
        validator.validate(changed)


def test_real_practical_state_reservation_recovery(tmp_path, software, monkeypatch):
    from gene_annotation_episode.practical_execution_state import PracticalState
    from gene_annotation_episode.native_chromatin_interaction_local import prepare_local_chromatin_interaction, local_chromatin_interaction_plan
    plan = make_plan(tmp_path, software)
    assignment = {"version": "practical_assignment_v1", "assignment_id": "c3-actual-practical-reservation", "resource_kind": "local",
        "resource_id": "selected-local", "workspace": str(tmp_path), "endpoint": "usable_handoff", "requested_job": plan["requested_job"],
        "progress_requirements": [{"key": "handoff", "credit": 1, "predicate": {"kind": "requested_job_handoff"}}],
        "completion_keys": ["handoff"], "initial_context": {"revision": 0, "cwd": str(tmp_path), "environment": {}},
        "inventory_snapshot": {}, "constraints": {"allocation": deepcopy(POLICY)}}
    state = PracticalState(tmp_path / "practical-state", "actual-reservation-run", "actual-local-child", assignment)
    operation = "actual-selected-start"
    root = tmp_path / ".episode-operations" / digest({"run": state.run_id, "episode": state.episode_id}) / digest(operation)
    with pytest.raises(ValueError, match="selected_pending_start_required"):
        prepare_local_chromatin_interaction(state, operation, root=root, policy=LocalJobPolicy(**POLICY))
    state.begin(operation, "practical.job.start", {})
    handle = prepare_local_chromatin_interaction(state, operation, root=root, policy=LocalJobPolicy(**POLICY))
    assert handle.read()["stage"] == "prepared"
    original = local_chromatin_interaction_plan(assignment, str(handle.path))
    assert original["identity"]["assignment_sha256"] == digest(assignment)
    monkeypatch.setattr(native, "prepare_job", lambda *args, **kwargs: pytest.fail("reservation repeated"))
    Path(assignment["requested_job"]["native_chromatin_interactions"]["input_bindings"][0]["path"]).unlink()
    assert prepare_local_chromatin_interaction(state, operation, root=root, policy=LocalJobPolicy(**POLICY)).path == handle.path
    assert local_chromatin_interaction_plan(assignment, str(handle.path)) == original


def test_shared_local_operations_original_start_observe_collect(tmp_path, software, monkeypatch):
    from gene_annotation_episode.practical_execution_state import PracticalState
    from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
    from gene_annotation_episode.practical_execution_records import assess_validations
    from gene_annotation_episode.native_chromatin_interaction_local import local_chromatin_interaction_plan
    seed = make_plan(tmp_path, software)
    assignment = {"version": "practical_assignment_v1", "assignment_id": "c3-shared-local-execution", "resource_kind": "local",
        "resource_id": "selected-local", "workspace": str(tmp_path), "endpoint": "usable_handoff", "requested_job": seed["requested_job"],
        "progress_requirements": [{"key": "handoff", "credit": 1, "predicate": {"kind": "requested_job_handoff"}}],
        "completion_keys": ["handoff"], "initial_context": {"revision": 0, "cwd": str(tmp_path), "environment": {}},
        "inventory_snapshot": {}, "constraints": {"allocation": deepcopy(POLICY)}}
    binding = {"operation": "analyze_chromatin_interactions", "resource_kind": "local", "software": software, "supported_formats": ["cooler_hdf5_v3"],
        "analysis_modes": assignment["requested_job"]["native_chromatin_interactions"]["request"]["analysis_modes"]}
    configuration = {"kind": "local", "workspace": str(tmp_path), "policy": POLICY, "native_chromatin_interactions": [binding]}
    operations = LocalPracticalOperations(configuration)
    state = PracticalState(tmp_path / "shared-state", "shared-component-run", "original-local-child", assignment)
    operation = "original-selected-start"
    state.begin(operation, "practical.job.start", {})
    outcome, after = asyncio.run(operations.execute(state, "practical.job.start", {}, operation))
    receipt = state.finish(operation, outcome, assess_validations(assignment, outcome, state.context(), tool_name="practical.job.start"), after)
    execution = receipt["outcome"]["facts"]["requested_job"]["execution_id"]
    handle = native.NativeJobHandle(Path(execution))
    unit = handle.read()["unit"]
    original = local_chromatin_interaction_plan(assignment, execution)
    assert original["identity"]["assignment_sha256"] == digest(assignment)
    assert original["identity"]["run_id"] == state.run_id and original["identity"]["episode_id"] == state.episode_id
    assert receipt["outcome"]["native_outcome"]["attempt_operation_key"] == operation
    assert receipt["outcome"]["native_outcome"]["attempt_id"] == original["identity"]["attempt_id"]
    assert receipt["outcome"]["facts"]["requested_job"]["output_paths"] == sorted(
        str(Path(original["attempt_directory"]) / row["relative_path"]) for row in original["outputs"])
    reopened = PracticalState(tmp_path / "shared-state", state.run_id, state.episode_id, assignment)
    monkeypatch.setattr(native, "prepare_job", lambda *args, **kwargs: pytest.fail("reopened execution prepared again"))
    monkeypatch.setattr(native, "start_prepared", lambda *args, **kwargs: pytest.fail("reopened execution dispatched again"))
    replay, _ = asyncio.run(operations.execute(reopened, "practical.job.start", {}, operation))
    assert replay["facts"]["requested_job"]["execution_id"] == execution and handle.read()["unit"] == unit
    # These operations inspect the original handoff; this component test does
    # not invent additional episode observations or a scientific completion.
    status, _ = asyncio.run(operations.execute(reopened, "practical.job.status", {}, "component-status"))
    assert status["native_outcome"]["attempt_id"] == original["identity"]["attempt_id"]
    result = native.wait_job(handle)
    assert result.returncode == 0, result.stderr_path.read_text()
    collected, _ = asyncio.run(operations.execute(reopened, "practical.job.collect", {}, "component-collect"))
    assert collected["facts"]["requested_job"]["status"] == "completed"
    identity = {"run_id": state.run_id, "origin_episode_id": state.episode_id, "original_operation_key": operation,
        "attempt_id": original["identity"]["attempt_id"], "resource_id": assignment["resource_id"]}
    observed = operations.observe_execution(assignment, execution, **identity)
    assert observed["state"] == "completed" and observed["result_available"]
    assert observed["logs"] and all(row["writer_closed"] for row in observed["outputs"] if row["available"])
    log = next(row for row in observed["logs"] if row["role"] == "stdout")
    window = operations.read_output(assignment, execution, path=log["path"], offset=0, limit=1024, **identity)
    assert 0 < window["returned_bytes"] <= 1024
    with pytest.raises(ValueError, match="original_output_path_required"):
        operations.read_output(assignment, execution, path=str(tmp_path / "supplied/contact.cool"), offset=0, limit=20, **identity)
    with pytest.raises(ValueError, match="original_attempt_mismatch"):
        operations.observe_execution(assignment, execution, **{**identity, "origin_episode_id": "different-child"})
    unbound = deepcopy(configuration)
    unbound["native_chromatin_interactions"][0]["analysis_modes"] = ["cross_window_insulation_heuristic"]
    with pytest.raises(ValueError, match="format_modes_software_not_bound"):
        LocalPracticalOperations(unbound).validate_assignment(assignment)
    unbound = deepcopy(configuration)
    unbound["native_chromatin_interactions"][0]["software"]["python_sha256"] = "a" * 64
    with pytest.raises(ValueError, match="format_modes_software_not_bound"):
        LocalPracticalOperations(unbound).validate_assignment(assignment)


@pytest.mark.parametrize("role,when", [("bins", "after_capture"), ("contacts", "after_capture"),
    ("weights", "after_capture"), ("contacts", "before_capture")])
def test_captured_table_loss_preserves_independent_population(tmp_path, software, role, when):
    plan = make_plan(tmp_path, software, case="weighted", populations=2, population_ends=[40, 30])
    complete(plan)
    selector = deepcopy(WORKED["weighted.selector"])
    selector["population_keys"] = ["p0", "p1"]
    if when == "before_capture":
        selected_path = next(row["relative_path"] for row in plan["outputs"] if row["file_key"] == "p1." + role)
        (Path(plan["attempt_directory"]) / selected_path).unlink()
    worker = capture_plan(tmp_path, plan, selector)
    original = deepcopy(worker["original_plan"])
    selected = next(row for row in worker["files"] if row["specification"]["file_key"] == "p1." + role)
    if when == "after_capture":
        Path(selected["retained"]["path"]).unlink()
    else:
        assert selected["capture"]["outcome"] == "unavailable" and selected["retained"] is None
    result = run_chromatin_result_worker(worker)
    assert result["state"] == "produced", result
    sheet = _read_control(Path(worker["directory"]) / "sheet.json")
    assert sheet["populations"][0]["extent"] == "complete"
    first, second = sheet["populations"]
    assert first["normalization"]["availability"] == "available"
    assert second["normalization"]["specification"]["kind"] == "precomputed_weighted"
    if role == "weights":
        assert second["extent"] == "complete" and second["normalization"]["availability"] == "missing"
        assert second["normalization"]["vector_table_key"] is None
    else:
        assert second["extent"] == "partial"
        assert second["read_evidence"]["implicit_zero_semantics"] == "not_established"
    assert worker["original_plan"] == original
    assert any(f["code"] == "input_unavailable" and f["population_key"] == "p1" for f in result["failures"])
    assert len(result["outputs"]) == 4 + 5 * 2
    missing = next(row for row in result["outputs"][4:] if row["table_key"] == next(
        d["table_key"] for d in sheet["data_tables"] if d["population_key"] == "p1" and d["role"] == role))
    assert missing["declaration"]["state"] == "absent"


def test_sealed_populations_survive_actual_interruption(tmp_path, software):
    plan = make_plan(tmp_path, software, populations=30)
    handle = launch(plan)
    first = Path(plan["attempt_directory"]) / next(r["relative_path"] for r in plan["outputs"] if r["file_key"] == "p0.population_manifest")
    deadline = time.monotonic() + 30
    while not first.exists() and not native.status(handle)["terminal"] and time.monotonic() < deadline:
        time.sleep(0.01)
    assert first.exists()
    original_bytes = first.read_bytes()
    log_path = Path(plan["attempt_directory"]) / next(r["relative_path"] for r in plan["outputs"] if r["file_key"] == "stdout")
    deadline = time.monotonic() + 5
    while (not log_path.exists() or log_path.stat().st_size == 0) and time.monotonic() < deadline:
        time.sleep(0.01)
    assert log_path.stat().st_size > 0
    native.cancel(handle)
    view = native.status(handle)
    assert view["terminal"] and view["quiescent"]
    assert first.read_bytes() == original_bytes
    seal = validate_chromatin_population_seal(_read_control(first), plan=plan,
        population=plan["requested_job"]["native_chromatin_interactions"]["request"]["populations"][0])
    assert seal["population"]["extent"] == "complete"
    assert not (Path(plan["attempt_directory"]) / plan["outputs"][-1]["relative_path"]).exists()
    with pytest.raises(ValueError, match="unsealed_native_attempt"):
        run_chromatin_interaction_driver(plan)
    worker_plan = capture_plan(tmp_path, plan, deepcopy(WORKED["raw.selector"]), interrupted=True)
    result = run_chromatin_result_worker(worker_plan)
    assert result["state"] == "produced", result
    sheet = _read_control(Path(worker_plan["directory"]) / "sheet.json")
    assert sheet["populations"][0]["extent"] == "complete"
    assert any(p["extent"] == "unavailable" for p in sheet["populations"][1:])
