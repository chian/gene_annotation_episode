"""Private contract and observer noninterference checks; no substitute fitter."""
import hashlib
import json
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


