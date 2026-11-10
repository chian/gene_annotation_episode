"""Bounded synthetic native bytes, real worker/lifecycle, explicit failure probes."""
from copy import deepcopy
from importlib import import_module
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_protein_structure_contracts import (
    POLICY, RUN_PLAN_FILENAME, BUNDLE_FILENAME, OWNER_FILENAME, STARTED_FILENAME,
    validate_protein_structure_bundle, requested_job_from_protein_structure,
    validate_native_protein_structure_result, compile_protein_structure_job,
)
from gene_annotation_episode.native_protein_structure_worker import execute_protein_structure_request
from gene_annotation_episode.native_protein_structure_driver import (
    run_protein_structure_driver, _strict_json, _immutable, confined_file,
)
from gene_annotation_episode.native_protein_structure_local import prepare_local_protein_structure, local_protein_structure_plan
_f = import_module("verification.tool_graders_protein_structure_execution_2026-10-27_390.fixture_helpers")
_a = import_module("verification.tool_graders_protein_structure_inputs_2026-10-27_386.fixture_helpers")


@pytest.mark.parametrize("kind", ["inspect", "extract_sequence", "compare"])
def test_actual_supplied_byte_worker(tmp_path, kind):
    request, inputs = _f.requests(kind)
    result = execute_protein_structure_request(request, input_bytes=inputs, software=_f.software())
    assert result["request"] == request
    validate_native_protein_structure_result(result)
    (tmp_path / (kind + "-native.json")).write_text(canonical(result))
    if kind == "inspect":
        assert result["inventory"]["chains"][0]["atom_count"] == 4
    elif kind == "extract_sequence":
        assert result["sequence"]["alignment_sequence"] == "AGST"
        assert len(result["sequence"]["residues"]) == 4
    else:
        sheet = result["sheet"]
        assert sheet is not None, result["issues"]
        c = sheet["native_baseline"]
        assert c["counts"]["mapped_pair_count"]["value"] == 4
        assert c["evaluation"]["evaluation_rmsd"]["value"] == pytest.approx(0, abs=1e-14)
        assert c["coverage"]["fixed_correspondence_coverage"]["value"] == 1


def test_bytes_digest_failure_is_not_zero_result():
    request, inputs = _f.requests()
    inputs[0]["data"] = b"wrong"
    with pytest.raises(ValueError, match="input_digest_mismatch"):
        execute_protein_structure_request(request, input_bytes=inputs, software=_f.software())


def test_supplied_transform_and_held_out_native_values(tmp_path):
    def native_example(label, request, inputs):
        selected = _f.job(tmp_path / label, request=request, inputs=inputs)
        plan = _f.plan(tmp_path / label, selected)
        bundle = run_protein_structure_driver(plan)
        assert bundle["native_status"] == "complete", bundle["failures"]
        return _strict_json(Path(plan["attempt_directory"]) / "result.json")
    fixed = [[3, -2, 5], [3, -1, 5], [2, -2, 5], [3, -2, 6]]
    request, inputs = _f.requests(fixed_kwargs={"coordinates": fixed})
    parameters = request["parameters"]
    parameters.update(mode="evaluate_declared_transform_ca", fit_selection=None, declared_transform={
        "version": "protein_structure_transform_v1", "direction": "moving_to_fixed", "convention": "row_vector_y_R_plus_t",
        "rotation": [[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]], "translation_A": [3.0, -2.0, 5.0],
        "fixed_selection": deepcopy(request["fixed_selection"]), "moving_selection": deepcopy(request["moving_selection"]),
        "origin": "supplied", "received_from": None})
    supplied = native_example("supplied", request, inputs)
    assert supplied["sheet"] is not None, supplied["issues"]
    c = supplied["sheet"]["native_baseline"]
    assert c["evaluation"]["evaluation_rmsd"]["value"] == 0
    assert c["fit"]["fit_rmsd"]["state"] == "not_applicable"
    request, inputs = _f.requests(fixed_kwargs={"sequence": "AGSTA", "coordinates": _a.DEFAULT_XYZ + [[1, 1, 1]]},
        moving_kwargs={"sequence": "AGSTA", "coordinates": _a.DEFAULT_XYZ + [[1, 1, 3]]})
    request["parameters"]["fit_selection"] = {"kind": "explicit", "members": [{"kind": "correspondence_id", "correspondence_id": "map_" + str(i)} for i in range(4)]}
    request["parameters"]["evaluation_selection"] = {"kind": "explicit", "members": [{"kind": "sequence_position", "structure_role": "moving", "position_0based": 4}]}
    held = native_example("held-out", request, inputs)
    assert held["sheet"] is not None, held["issues"]
    c = held["sheet"]["native_baseline"]
    assert c["evaluation"]["evaluation_sse"]["value"] == pytest.approx(4)
    assert c["evaluation"]["evaluation_rmsd"]["value"] == pytest.approx(2)
    assert c["site_measurements"][0]["in_fit"] is False
    (tmp_path / "supplied-transform-native.json").write_text(canonical(supplied))
    (tmp_path / "held-out-native.json").write_text(canonical(held))


@pytest.mark.parametrize("kind", ["inspect", "extract_sequence", "compare"])
def test_driver_real_worker_seals_every_declared_file_and_replays(tmp_path, monkeypatch, kind):
    selected = _f.job(tmp_path, kind=kind)
    plan = _f.plan(tmp_path, selected)
    result = run_protein_structure_driver(plan)
    assert result["native_status"] == "complete", result["failures"]
    assert result["returncode"] == 0
    assert result["driver_argv"][0] == selected["software"]["python_executable"]
    assert result["worker_argv"][0] == selected["software"]["python_executable"]
    assert result["driver_argv"] != result["worker_argv"]
    assert result["measured_duration"]["kind"] == "worker_wall"
    assert result["measured_duration"]["seconds"] > 0
    assert all(row["state"] == "present" for row in result["files"])
    root = Path(plan["attempt_directory"])
    for row in result["files"]:
        raw = (root / row["relative_path"]).read_bytes()
        assert len(raw) == row["byte_length"] and hashlib.sha256(raw).hexdigest() == row["sha256"]
    assert (root / RUN_PLAN_FILENAME).read_bytes() == (root.parent / RUN_PLAN_FILENAME).read_bytes()
    if kind == "extract_sequence": assert (root / "sequence.txt").read_bytes() == b"AGST"
    import gene_annotation_episode.native_protein_structure_driver as driver
    monkeypatch.setattr(driver.subprocess, "Popen", lambda *a, **k: pytest.fail("replay launched work"))
    assert run_protein_structure_driver(plan) == result
    altered = deepcopy(result)
    altered["files"][0]["byte_length"] = 0
    with pytest.raises(ValueError): validate_protein_structure_bundle(altered, plan=plan)
    (root / "result.json").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="input_digest_mismatch"): run_protein_structure_driver(plan)


def test_staging_rejects_changed_bytes_and_retains_failure(tmp_path):
    selected = _f.job(tmp_path, kind="inspect")
    plan = _f.plan(tmp_path, selected)
    Path(selected["inputs"][0]["path"]).write_bytes(b"changed-input")
    result = run_protein_structure_driver(plan)
    assert result["native_status"] == "failed"
    assert result["worker_argv"] is None and result["returncode"] is None
    assert result["measured_duration"]["kind"] == "driver_wall"
    assert any(i["code"] == "input_digest_mismatch" for i in result["failures"])
    row = next(r for r in result["files"] if r["kind"] == "input")
    assert row["state"] == "absent" and row["byte_length"] is None
    assert b"Y2hhbmdlZC1pbnB1dA==" in (Path(plan["attempt_directory"]) / "stderr.log").read_bytes()
    assert run_protein_structure_driver(plan) == result


def test_symlink_staging_and_budget_preflight_are_failures(tmp_path, monkeypatch):
    selected = _f.job(tmp_path, kind="inspect")
    source = Path(selected["inputs"][0]["path"])
    target = source.with_name("other")
    source.rename(target)
    source.symlink_to(target)
    plan = _f.plan(tmp_path, selected)
    result = run_protein_structure_driver(plan)
    assert any(i["code"] == "invalid_output_path" for i in result["failures"])


def test_unknown_started_attempt_never_relaunches(tmp_path, monkeypatch):
    selected = _f.job(tmp_path, kind="inspect")
    plan = _f.plan(tmp_path, selected)
    root = Path(plan["attempt_directory"])
    root.mkdir()
    _immutable(root / OWNER_FILENAME, plan)
    _immutable(root / STARTED_FILENAME, {"started": True})
    with pytest.raises(ValueError, match="native_process_failed"): run_protein_structure_driver(plan)
    assert not (root / "result.json").exists()


def test_wrong_software_retains_original_controls(tmp_path):
    selected = _f.job(tmp_path, kind="inspect")
    selected["software"]["python_sha256"] = "0" * 64
    plan = _f.plan(tmp_path, selected)
    result = run_protein_structure_driver(plan)
    assert result["worker_argv"] is None
    assert any(i["code"] == "software_identity_mismatch" for i in result["failures"])
    assert all(r["state"] == "present" for r in result["files"] if r["kind"] == "control")


def test_actual_partial_science_is_separate_from_native_success(tmp_path):
    selected = _f.job(tmp_path, moving_kwargs={"occupancy": "0.00"})
    plan = _f.plan(tmp_path, selected)
    bundle = run_protein_structure_driver(plan)
    assert bundle["native_status"] == "complete", bundle["failures"]
    result = _strict_json(Path(plan["attempt_directory"]) / "result.json")
    assert result["sheet"] is not None, result["issues"]
    components = result["sheet"]["native_baseline"]
    assert components["counts"]["available_pair_count"]["value"] == 0
    assert components["evaluation"]["evaluation_rmsd"]["value"] is None
    assert components["state"] != "complete"


def test_actual_native_failure_keeps_present_inputs(tmp_path):
    selected = _f.job(tmp_path, kind="inspect")
    selected["software"]["numpy_version"] = "wrong-selected-version"
    plan = _f.plan(tmp_path, selected)
    bundle = run_protein_structure_driver(plan)
    assert bundle["returncode"] != 0 and bundle["worker_argv"] is not None
    assert bundle["native_status"] == "failed"
    assert all(r["state"] == "present" for r in bundle["files"] if r["kind"] in ("input", "control"))
    assert b"software_identity_mismatch" in (Path(plan["attempt_directory"]) / "stderr.log").read_bytes()


def test_real_durable_reservation_start_status_restart(tmp_path):
    selected = _f.job(tmp_path, kind="extract_sequence")
    request = requested_job_from_protein_structure(selected)
    assignment = {"resource_kind": "local", "resource_id": "local", "workspace": str(tmp_path),
        "requested_job": request, "constraints": {"allocation": deepcopy(POLICY)}}
    # C adapter unit uses the state-owned fields. Shared PracticalState schema
    # registration/episode commission is explicitly root's integration lane.
    state = SimpleNamespace(assignment=assignment, run_id="synthetic-run", episode_id="synthetic-local")
    root = tmp_path / ".episode-operations" / digest({"run": state.run_id, "episode": state.episode_id}) / digest("start")
    handle = prepare_local_protein_structure(state, "start", root=root, policy=LocalJobPolicy(**POLICY))
    original = handle.read()
    assert native.status(handle)["state"] == "prepared"
    assert not (root / "protein-structure-attempt").exists()
    assert original["command"][0] == selected["software"]["python_executable"]
    assert prepare_local_protein_structure(state, "start", root=root, policy=LocalJobPolicy(**POLICY)).read() == original
    native.start_prepared(handle)
    completed = native.wait_job(handle)
    assert completed.returncode == 0
    saved = local_protein_structure_plan(assignment, str(handle.path))
    bundle = _strict_json(Path(saved["attempt_directory"]) / BUNDLE_FILENAME)
    before = (Path(saved["attempt_directory"]) / BUNDLE_FILENAME).read_bytes()
    reopened = native.NativeJobHandle(handle.path)
    assert native.status(reopened)["terminal"]
    assert local_protein_structure_plan(assignment, str(handle.path)) == saved
    assert native.collect(reopened).returncode == 0
    assert (Path(saved["attempt_directory"]) / BUNDLE_FILENAME).read_bytes() == before
    assert bundle["native_status"] == "complete"
    cgroup = completed.metadata["verified_cgroup"]
    assert cgroup["memory_max"] == 21474836480 and cgroup["memory_swap_max"] == 0 and 'runtime_max' not in cgroup


@pytest.mark.parametrize("orientation", ["fixed_is_query", "fixed_is_reference"])
def test_retained_real_alignment_byte_inputs_without_worker_alignment(tmp_path, monkeypatch, orientation):
    request, inputs = _f.retained_request(orientation=orientation)
    import gene_annotation_episode.sequence_ops as alignment
    monkeypatch.setattr(alignment, "align_pair", lambda *a, **k: pytest.fail("comparison worker aligned sequences"))
    result = execute_protein_structure_request(request, input_bytes=inputs, software=_f.software())
    assert result["sheet"] is not None, result["issues"]
    sheet = result["sheet"]
    assert sheet["correspondence"]["population_available"]
    assert sheet["native_baseline"]["counts"]["mapped_pair_count"]["value"] == 4
    assert sheet["native_baseline"]["evaluation"]["evaluation_rmsd"]["value"] == pytest.approx(0, abs=1e-14)
    (tmp_path / "retained-native.json").write_text(canonical(result))
    # The complete independently produced grading artifact is required; an A
    # sheet alone must not masquerade as the full received outer artifact.
    broken = deepcopy(inputs)
    row = next(r for r in broken if r["role"] == "alignment_grading")
    outer = json.loads(row["data"])
    row["data"] = canonical(outer["grading"]["sheet"]).encode()
    row["file_identity"] = _a.identity(row["data"], "tool_grading_artifact_v1")
    request["correspondence"]["alignment"]["grading_file"] = row["file_identity"]
    unavailable = execute_protein_structure_request(request, input_bytes=broken, software=_f.software())
    assert unavailable["sheet"] is None and unavailable["state"] == "invalid"


def test_mixed_format_real_retained_alignment_and_missing_ca(tmp_path):
    request, inputs = _f.retained_request(mixed_format=True)
    request["parameters"]["missing_coordinate_policy"] = "use_available"
    selected = _f.job(tmp_path, request=request, inputs=inputs)
    plan = _f.plan(tmp_path, selected)
    bundle = run_protein_structure_driver(plan)
    assert bundle["native_status"] == "complete", bundle["failures"]
    result = _strict_json(Path(plan["attempt_directory"]) / "result.json")
    assert result["sheet"] is not None, result["issues"]
    assert result["sheet"]["sequences"]["moving"]["selection"]["sequence_basis"] == "mmcif_declared_polymer"
    assert result["sheet"]["native_baseline"]["counts"]["mapped_pair_count"]["value"] > 0


def test_selected_interpreter_is_actually_used(tmp_path):
    selected = _f.job(tmp_path, kind="inspect")
    executable = str(Path(sys.executable).with_name("python3"))
    assert executable != sys.executable and Path(executable).is_file()
    selected["software"]["python_executable"] = executable
    selected["software"]["python_sha256"] = hashlib.sha256(Path(executable).read_bytes()).hexdigest()
    plan = _f.plan(tmp_path, selected)
    bundle = run_protein_structure_driver(plan)
    assert bundle["native_status"] == "complete", bundle["failures"]
    observation = json.loads((Path(plan["attempt_directory"]) / "stdout.log").read_text().splitlines()[0])
    assert observation["software"]["python_executable"] == executable
    assert bundle["worker_argv"][0] == bundle["driver_argv"][0] == executable


def test_real_nonzero_exit_after_valid_output_keeps_that_output(tmp_path):
    selected = _f.job(tmp_path, kind="inspect")
    fault = tmp_path / "injected-exit-fault"
    fault.mkdir()
    # Deliberate test fault: CPython exits nonzero at shutdown after the real
    # worker has published its result. The source and selected environment stay
    # in this retained test directory. This is not a native biology failure.
    (fault / "sitecustomize.py").write_text("import atexit, os\natexit.register(lambda: os._exit(9))\n")
    selected["environment"]["PYTHONPATH"] = str(fault) + ":" + str(_f.REPO)
    plan = _f.plan(tmp_path, selected)
    bundle = run_protein_structure_driver(plan)
    assert bundle["returncode"] == 9 and bundle["native_status"] == "partial"
    assert any(i["code"] == "native_process_failed" for i in bundle["failures"])
    assert all(r["state"] == "present" for r in bundle["files"])
    native_result = _strict_json(Path(plan["attempt_directory"]) / "result.json")
    validate_native_protein_structure_result(native_result)
    assert native_result["inventory"]["chains"][0]["atom_count"] == 4
    assert run_protein_structure_driver(plan) == bundle


def test_unavailable_sequence_is_absent_not_empty_and_capture_partial(tmp_path):
    selected = _f.job(tmp_path, kind="extract_sequence", fixed_kwargs={"sequence": "XGST"})
    plan = _f.plan(tmp_path, selected)
    bundle = run_protein_structure_driver(plan)
    assert bundle["returncode"] == 0 and bundle["native_status"] == "partial"
    sequence = next(r for r in bundle["files"] if r["role"] == "sequence")
    assert sequence["state"] == "absent" and sequence["byte_length"] is None and sequence["sha256"] is None
    root = Path(plan["attempt_directory"])
    assert not (root / "sequence.txt").exists() and (root / "residue-map.json").exists()
    result = _strict_json(root / "result.json")
    assert result["sequence"]["alignment_sequence"] is None


def test_resource_budget_failure_retains_controls_without_start(tmp_path, monkeypatch):
    import gene_annotation_episode.native_protein_structure_driver as driver
    from gene_annotation_episode.acquisition import AcquisitionError
    selected = _f.job(tmp_path, kind="inspect")
    plan = _f.plan(tmp_path, selected)
    def no_capacity(*a, **k):
        raise AcquisitionError("injected_scratch_budget_failure")
    monkeypatch.setattr(driver, "check_scratch_budget", no_capacity)
    monkeypatch.setattr(driver.subprocess, "Popen", lambda *a, **k: pytest.fail("budget failure launched work"))
    bundle = run_protein_structure_driver(plan)
    assert bundle["worker_argv"] is None and bundle["returncode"] is None
    assert any(i["code"] == "resource_budget_exceeded" for i in bundle["failures"])
    assert all(r["state"] == "present" for r in bundle["files"] if r["kind"] == "control")


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}'])
def test_malformed_json_is_rejected_before_use(raw):
    from gene_annotation_episode.native_protein_structure_worker import strict_json
    with pytest.raises(ValueError): strict_json(raw)


@pytest.mark.parametrize("mutation", ["clock_kind", "clock_value", "unknown_file", "missing_file", "wrong_mode", "wrong_software", "float_manifest_count"])
def test_bundle_rejects_different_attempt_facts(tmp_path, mutation):
    selected = _f.job(tmp_path, kind="inspect")
    plan = _f.plan(tmp_path, selected)
    # Exercise failed staging without another native invocation; failure clocks
    # must say driver_wall and the original request remains fully retained.
    Path(selected["inputs"][0]["path"]).write_bytes(b"bad")
    bundle = run_protein_structure_driver(plan)
    if mutation == "clock_kind": bundle["measured_duration"]["kind"] = "worker_wall"
    elif mutation == "clock_value": bundle["measured_duration"]["seconds"] = None
    elif mutation == "unknown_file": bundle["files"].append(deepcopy(bundle["files"][-1]))
    elif mutation == "missing_file": bundle["files"].pop()
    elif mutation == "wrong_mode": bundle["requested_job"]["native_protein_structure"]["request"]["operation"] = "compare"
    elif mutation == "float_manifest_count":
        row = next(r for r in bundle["files"] if r["kind"] == "control")
        row["byte_length"] = float(row["byte_length"])
    else: bundle["software"]["python_sha256"] = "0" * 64
    with pytest.raises(ValueError): validate_protein_structure_bundle(bundle, plan=plan)


def test_received_fitted_transform_uses_retained_values_without_refit(tmp_path, monkeypatch):
    request, inputs = _f.requests()
    fitted = execute_protein_structure_request(request, input_bytes=inputs, software=_f.software())
    sheet = fitted["sheet"]
    assert sheet is not None, fitted["issues"]
    components = sheet["native_baseline"]
    raw_sheet, raw_components = canonical(sheet).encode(), canonical(components).encode()
    sheet_file = _a.identity(raw_sheet, "protein_structure_comparison_sheet_v1")
    components_file = _a.identity(raw_components, "protein_structure_components_v1")
    saved = {"version": "protein_structure_saved_sheet_v1", "custody": _a.synthetic_custody(),
        "sheet_file": sheet_file, "original_components_file": components_file,
        "operation": "compare_protein_structures", "original_mode": "fit_then_evaluate_ca", "allowed_uses": ["use_transform"]}
    request["parameters"].update(mode="evaluate_declared_transform_ca", fit_selection=None, declared_transform={
        "version": "protein_structure_transform_v1", "direction": "moving_to_fixed", "convention": "row_vector_y_R_plus_t",
        "rotation": deepcopy(components["transform"]["rotation"]["value"]),
        "translation_A": deepcopy(components["transform"]["translation"]["value"]),
        "fixed_selection": deepcopy(request["fixed_selection"]), "moving_selection": deepcopy(request["moving_selection"]),
        "origin": "received_fitted", "received_from": {"saved_sheet": saved, "components_file": components_file,
            "calculation_id": components["calculation_id"], "calculation_custody": _a.synthetic_custody()}})
    for role, raw, file in [("received_transform_components", raw_components, components_file), ("received_transform_sheet", raw_sheet, sheet_file)]:
        inputs.append({"input_id": "input_" + str(len(inputs)), "role": role, "file_identity": file, "data": raw})
    import numpy as np
    monkeypatch.setattr(np.linalg, "svd", lambda *a, **k: pytest.fail("received fitted transform was refit"))
    result = execute_protein_structure_request(request, input_bytes=inputs, software=_f.software())
    assert result["sheet"] is not None, result["issues"]
    assert result["sheet"]["native_baseline"]["transform"]["rotation"]["value"] == components["transform"]["rotation"]["value"]
    assert result["sheet"]["native_baseline"]["fit"]["state"] == "not_applicable"
    (tmp_path / "received-transform-native.json").write_text(canonical(result))
    bad = deepcopy(request)
    bad["parameters"]["declared_transform"]["translation_A"][0] += 1
    rejected = execute_protein_structure_request(bad, input_bytes=inputs, software=_f.software())
    assert rejected["sheet"] is None and rejected["issues"][0]["code"] == "invalid_transform"

