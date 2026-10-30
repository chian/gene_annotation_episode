"""Private contract and observer noninterference checks; no substitute fitter."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from gene_annotation_episode import molecular_sequence_native as native
from gene_annotation_episode import molecular_sequence_driver as driver
from test_protease_kinetics_measurements import supplied_fixture
from gene_annotation_episode.protease_kinetics_measurements import populate_protease_kinetics_sheet


def observation():
    return {"state": "not_started", "reason": None, "selected_call_count": 0,
        "selected_terminal_event_count": 0, "profile_restored": None, "locals": {}, "failures": []}


def test_passive_observer_preserves_return_and_captures_true_locals():
    calls = []
    def selected():
        calls.append("called")
        params = [1.234567891, 2.]
        covariance = [[4., 1.], [1., 1.]]
        return "original return"
    observed = observation()
    assert native._call_with_return_observer(selected, {}, observed) == "original return"
    assert calls == ["called"]
    assert observed["locals"]["params"] == [1.234567891, 2.]
    assert observed["locals"]["covariance"] == [[4., 1.], [1., 1.]]
    assert observed["selected_call_count"] == observed["selected_terminal_event_count"] == 1
    assert observed["profile_restored"] is True


def test_serialization_failure_never_changes_native_exception(monkeypatch):
    calls = []
    original = ValueError("original native error")
    def selected():
        calls.append("called")
        params = [1., 2.]
        raise original
    def recorder_failure(value):
        raise RuntimeError("recorder failed")
    monkeypatch.setattr(native, "_observed_json", recorder_failure)
    observed = observation()
    with pytest.raises(ValueError) as failure:
        native._call_with_return_observer(selected, {}, observed)
    assert failure.value is original
    assert calls == ["called"]
    assert observed["failures"][0]["stage"] == "serialize:params"


def test_existing_profile_is_preserved_without_composing_callbacks():
    previous = sys.getprofile()
    calls = []
    def existing(frame, event, arg):
        return None
    def selected():
        calls.append("called")
        return 7
    sys.setprofile(existing)
    try:
        observed = observation()
        assert native._call_with_return_observer(selected, {}, observed) == 7
        assert sys.getprofile() is existing
        assert observed["reason"] == "existing_profile_preserved"
        assert observed["profile_restored"] is None
    finally:
        sys.setprofile(previous)
    assert calls == ["called"]


def test_cleanup_failure_is_recorded_without_replacing_return_or_rerunning(monkeypatch):
    previous = sys.getprofile()
    actual_setprofile = sys.setprofile
    calls = []
    failed = False
    def selected():
        calls.append("called")
        return "unchanged"
    def setprofile(profile):
        nonlocal failed
        if profile is previous and not failed:
            failed = True
            raise RuntimeError("cleanup failed")
        return actual_setprofile(profile)
    monkeypatch.setattr(sys, "setprofile", setprofile)
    try:
        observed = observation()
        assert native._call_with_return_observer(selected, {}, observed) == "unchanged"
        assert observed["profile_restored"] is False
        assert observed["failures"][0]["stage"] == "cleanup"
        assert calls == ["called"]
    finally:
        actual_setprofile(previous)


@pytest.mark.parametrize("version", [native.REQUEST_VERSION, native.REQUEST_VERSION_V2])
def test_legacy_native_profiles_do_not_accept_protease(version):
    capture = native.execute_molecular_sequence_request({"version": version, "operation": "analyze_protease_kinetics",
        "arguments": {}, "deployment": {}})
    assert capture["native_call_state"] == "not_started"
    assert capture["failure"]["code"] == "molecular_sequence_operation_not_supported"


def test_legacy_driver_remains_closed_to_protease():
    request = {"version": driver.REQUEST_VERSION, "mode": "saved_sheet", "attempt_identity":
        {k: "fixture" for k in driver._IDENTITY_FIELDS}, "selection": {"operation": "analyze_protease_kinetics"},
        "scientific_context": None}
    with pytest.raises(ValueError, match="operation_required"):
        driver._request(request)


def test_native_output_declarations_bind_exact_selected_bytes(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    output = workspace / "native"
    output.mkdir()
    text = b"Vmax: 12.0000\n"
    image = b"\x89PNG\r\n\x1a\nretained-test-bytes"
    (output / "selected_results.txt").write_bytes(text)
    (output / "selected_mm_plot.png").write_bytes(image)
    selection = {"output_workspace": str(workspace), "arguments": {"output_dir": str(output), "output_prefix": "selected"}}
    result = driver._protease_native_declarations(workspace, selection)
    assert result["native_results"]["sha256"] == hashlib.sha256(text).hexdigest()
    assert result["native_plot"]["size_bytes"] == len(image)
    assert result["native_results"]["state"] == "present"
    (output / "selected_mm_plot.png").unlink()
    assert driver._protease_native_declarations(workspace, selection)["native_plot"]["state"] == "absent"


def test_native_output_symlink_is_not_followed(tmp_path):
    target = tmp_path / "outside.txt"
    target.write_text("outside")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "selected_results.txt").symlink_to(target)
    selection = {"output_workspace": str(workspace), "arguments": {"output_dir": str(workspace), "output_prefix": "selected"}}
    with pytest.raises(OSError):
        driver._protease_native_declarations(workspace, selection)


def test_saved_driver_preserves_original_sheet_bytes_and_never_calls_native(tmp_path, monkeypatch):
    measurements, capture, context = supplied_fixture()
    sheet = populate_protease_kinetics_sheet(measurements=measurements, native_capture=capture, assay_context=context)
    raw_sheet = (json.dumps(sheet, indent=3) + "\n").encode()
    sheet_path = tmp_path / "original-sheet.json"
    sheet_path.write_bytes(raw_sheet)
    pin = {"path": str(sheet_path), "sha256": hashlib.sha256(raw_sheet).hexdigest(), "size_bytes": len(raw_sheet)}
    request = {"version": driver.REQUEST_VERSION_V2, "mode": "saved_sheet", "attempt_identity":
        {k: "constructed-fixture" for k in driver._IDENTITY_FIELDS}, "selection":
        {"operation": "analyze_protease_kinetics", "sheet_file": pin}, "scientific_context": None}
    raw = json.dumps(request).encode()
    request_path = tmp_path / "request.json"
    request_path.write_bytes(raw)
    def no_native(*args, **kwargs):
        raise AssertionError("saved calculation called native")
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", no_native)
    output = tmp_path / "saved"
    result = driver.run_molecular_sequence_driver(request_file={"path": str(request_path),
        "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}, output_directory=str(output))
    assert result["version"] == driver.DECLARATION_VERSION_V2
    assert result["driver_failure"] is None
    assert result["native_call_state"] == "not_requested"
    assert (output / "sheet.json").read_bytes() == raw_sheet
    assert set(result["files"]) == {"capture", "sheet", "components"}


@pytest.fixture(scope="module")
def genuine_cli_deployment():
    """Opt in only with root's explicit pinned deployment in a bounded run."""
    filename = os.environ.get("HMMER_NATIVE_ORACLE_PROTEASE_CLI_DEPLOYMENT")
    if filename is None:
        pytest.skip("genuine CLI controls require an explicitly selected pinned deployment")
    deployment = json.loads(Path(filename).read_bytes())
    assert deployment["version"] == "molecular_sequence_deployment_v3"
    return deployment


def _pin_file(path):
    raw = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _cli_arguments(request_file, output):
    pin = _pin_file(request_file)
    return ["--request-file", pin["path"], "--request-sha256", pin["sha256"],
        "--request-size-bytes", str(pin["size_bytes"]), "--output-directory", str(output)]


def _cli_environment(workspace, config):
    return {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]), "PYTHONDONTWRITEBYTECODE": "1",
        "MPLBACKEND": "Agg", "MPLCONFIGDIR": str(config), "XDG_CACHE_HOME": str(workspace / "cache")}


def _actual_cli_case(directory, deployment, *, case):
    directory.mkdir()
    workspace = directory / "output"
    time_points = list(range(10))
    substrates = [1., 2., 4., 8., 16.]
    deviations = [.013, .037, -.021, .009, -.017]
    slopes = [12*s/(3+s) + d for s, d in zip(substrates, deviations)]
    curves = [[7+i+rate*t for t in time_points] for i, rate in enumerate(slopes)]
    if case == "missing_curve":
        curves.pop()
    elif case == "pre_fit_exception":
        curves[1] = curves[1][:2]
    _, _, assay_context = supplied_fixture()
    assay_context["sample_key"] = "constructed-genuine-cli-control"
    assay_context["calibration"]["curve_ordinals"] = list(range(len(substrates)))
    prefix = "selected"
    native_output = workspace / "native"
    # Intentional OS failure: config creation makes the exact plot destination a
    # directory. The unchanged source then fits before its real savefig fails.
    config = native_output / (prefix + "_mm_plot.png") if case == "post_fit_write_error" else workspace / "config"
    selection = {"version": native.REQUEST_VERSION_V3, "operation": "analyze_protease_kinetics",
        "arguments": {"time_points": time_points, "fluorescence_data": curves,
            "substrate_concentrations": substrates, "enzyme_concentration": .5,
            "output_prefix": prefix, "output_dir": str(native_output)}, "deployment": deployment,
        "output_workspace": str(workspace), "environment": {"MPLBACKEND": "Agg", "MPLCONFIGDIR": str(config),
            "XDG_CACHE_HOME": str(workspace / "cache")}}
    request = {"version": driver.REQUEST_VERSION_V2, "mode": "native", "attempt_identity":
        {name: "constructed-genuine-cli-control-" + case for name in driver._IDENTITY_FIELDS},
        "selection": selection, "scientific_context": {"assay_context": assay_context}}
    path = directory / "request.json"
    path.write_text(json.dumps(request))
    command = [deployment["runtime"]["executable"]["path"], "-B", "-m", "gene_annotation_episode.molecular_sequence_driver",
        *_cli_arguments(path, workspace)]
    process = subprocess.run(command, cwd=directory, env=_cli_environment(workspace, config),
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (directory / "driver.stdout").write_bytes(process.stdout)
    (directory / "driver.stderr").write_bytes(process.stderr)
    declaration = json.loads((workspace / "declaration.json").read_bytes())
    assert declaration["driver_failure"] is None, declaration
    capture = json.loads((workspace / "capture.json").read_bytes())
    assert capture["observer"]["selected_call_count"] == 1
    assert capture["observer"]["selected_terminal_event_count"] == 1
    assert capture["observer"]["profile_restored"] is True
    assert capture["observer"]["failures"] == []
    assert capture["verification_failures"] == [], capture["verification_failures"]
    assert capture["execution_receipt"]["matplotlib_environment"]["config_directory"] == str(config)
    assert {row["module_name"] for row in capture["execution_receipt"]["libraries"]} == {"numpy", "scipy", "matplotlib"}
    components = json.loads((workspace / "components.json").read_bytes())
    return {"directory": directory, "workspace": workspace, "request": request, "declaration": declaration,
        "capture": capture, "components": components, "returncode": process.returncode}


@pytest.fixture(scope="module")
def genuine_complete_cli_case(tmp_path_factory, genuine_cli_deployment):
    return _actual_cli_case(tmp_path_factory.mktemp("protease-native-parent") / "complete",
        genuine_cli_deployment, case="complete")


def test_genuine_fresh_cli_preserves_full_fit_and_original_native_files(genuine_complete_cli_case):
    case = genuine_complete_cli_case
    capture, components, declaration = case["capture"], case["components"], case["declaration"]
    assert case["returncode"] == 0
    assert capture["native_record"]["outcome"] == "completed"
    values = components["native_values"]
    assert len(values["initial_velocities"]) == 5
    assert len(values["covariance"]) == 2 and all(len(row) == 2 for row in values["covariance"])
    assert any(point != round(point, 4) for point in values["params"])
    original = case["workspace"] / declaration["files"]["native_results"]["relative_path"]
    text = original.read_text()
    assert f"Vmax: {values['params'][0]:.4f}" in text
    assert f"KM: {values['params'][1]:.4f}" in text
    for role in ("native_results", "native_plot"):
        saved = declaration["files"][role]
        assert saved["state"] == "present"
        assert _pin_file(case["workspace"] / saved["relative_path"])["sha256"] == saved["sha256"]


@pytest.mark.parametrize("case_name", ["missing_curve", "pre_fit_exception", "post_fit_write_error"])
def test_genuine_fresh_cli_partial_and_failure_controls(tmp_path, genuine_cli_deployment, case_name):
    case = _actual_cli_case(tmp_path / case_name, genuine_cli_deployment, case=case_name)
    capture, components, declaration = case["capture"], case["components"], case["declaration"]
    if case_name == "missing_curve":
        assert capture["native_record"]["outcome"] == "completed"
        assert components["native_values"]["initial_velocities"][-1] == 0
        assert components["population"]["rows"][-1]["curve_state"] == "curve_missing"
        assert components["fit_components"]["vmax"]["state"] == "present"
        assert components["physical_components"]["product_vmax"]["reason"] == "native_fit_population_incompatible"
    elif case_name == "pre_fit_exception":
        assert capture["native_call_state"] == "raised"
        assert capture["failure"]["stage"] == "call"
        assert components["fit_components"]["vmax"]["value"] is None
        assert declaration["files"]["native_results"]["state"] == "absent"
        assert declaration["files"]["native_plot"]["state"] == "absent"
    else:
        assert capture["native_call_state"] == "returned"
        assert capture["native_record"]["result_kind"] == "source_error_string"
        assert capture["native_record"]["result"].startswith("Error during analysis:")
        assert components["fit_components"]["vmax"]["state"] == "present"
        assert declaration["native_output_completion"] == "source_error"
        assert declaration["files"]["native_plot"]["state"] == "absent"
        assert any(row.get("role") == "native_plot" for row in declaration["verification_failures"])


def test_genuine_saved_cli_uses_no_native_source_or_scipy(genuine_complete_cli_case, genuine_cli_deployment):
    case = genuine_complete_cli_case
    request = {"version": driver.REQUEST_VERSION_V2, "mode": "saved_sheet", "attempt_identity":
        {name: "constructed-saved-cli-control" for name in driver._IDENTITY_FIELDS}, "selection":
        {"operation": "analyze_protease_kinetics", "sheet_file": _pin_file(case["workspace"] / "sheet.json")},
        "scientific_context": None}
    path = case["directory"] / "saved-request.json"
    path.write_text(json.dumps(request))
    output = case["directory"] / "saved-output"
    # Deny execution of the actual source code object, without replacing a
    # scientific callable. Denying SciPy import also detects a hidden refit.
    script = '''import sys
source = sys.argv[1]
def deny_source(event, arguments):
    if event == "exec" and getattr(arguments[0], "co_filename", None) == source:
        raise AssertionError("saved calculation executed native source")
sys.addaudithook(deny_source)
sys.modules["scipy"] = None
from gene_annotation_episode.molecular_sequence_driver import main
raise SystemExit(main(sys.argv[2:]))
'''
    command = [genuine_cli_deployment["runtime"]["executable"]["path"], "-B", "-c", script,
        genuine_cli_deployment["module"]["path"], *_cli_arguments(path, output)]
    process = subprocess.run(command, cwd=case["directory"], env=_cli_environment(output, output / "config"),
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert process.returncode == 0, process.stderr.decode()
    declaration = json.loads((output / "declaration.json").read_bytes())
    assert declaration["native_call_state"] == "not_requested"
    assert (output / "sheet.json").read_bytes() == (case["workspace"] / "sheet.json").read_bytes()
    assert json.loads((output / "components.json").read_bytes()) == case["components"]
