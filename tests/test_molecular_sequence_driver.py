"""Private writer boundaries; genuine selected-source joins require explicit opt-in."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from gene_annotation_episode import molecular_sequence_driver as driver
from gene_annotation_episode.glycosylation_measurements import build_glycosylation_sheet
from gene_annotation_episode.native_file_capture import _declaration


N_OPERATION = "find_n_glycosylation_motifs"
O_OPERATION = "predict_o_glycosylation_hotspots"
N_LOG = ("# N-linked glycosylation sequon scan (N-X-[S/T], X≠P)\n"
    "Sequence length: 3\nTotal sequons found: 1\n\nPositions (1-based):\n- 1: NAT")


def file_pin(path):
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    return file_pin(path)


def selected_request(selection=None, context=None, *, mode="native"):
    if selection is None:
        selection = {"version": "molecular_sequence_request_v2", "operation": N_OPERATION,
            "arguments": {"sequence": "NAT", "allow_overlap": False}, "deployment": {}}
    if context is None and mode == "native":
        context = {"input_ref": None, "input_mapping": None}
    return {"version": driver.REQUEST_VERSION, "mode": mode,
        "attempt_identity": {"run_id": "engineering-control-run", "episode_id": "engineering-control-episode",
            "resource_id": "explicit-control-resource", "operation_key": "explicit-control-action",
            "execution_id": "explicit-control-execution"},
        "selection": deepcopy(selection), "scientific_context": deepcopy(context)}


def forbid_helper(*args, **kwargs):
    raise AssertionError("this driver path must not invoke a native helper")


def run_request(tmp_path, request, *, label="output"):
    request_path = tmp_path / (label + "-request.json")
    pin = write_json(request_path, request)
    before = request_path.read_bytes()
    output = tmp_path / label
    result = driver.run_molecular_sequence_driver(request_file=pin, output_directory=str(output))
    assert request_path.read_bytes() == before
    return result, output, pin


def check_declarations(result, output, present):
    assert set(result["files"]) == {"capture", "sheet", "components"}
    for role, declared in result["files"].items():
        assert _declaration(declared) == declared  # Actual existing capture-consumer contract.
        path = output / declared["relative_path"]
        assert declared["relative_path"] == role + ".json" and declared["format"] == "json"
        assert (declared["state"] == "present") is (role in present)
        if role in present:
            raw = path.read_bytes()
            assert declared["sha256"] == hashlib.sha256(raw).hexdigest()
            assert declared["size_bytes"] == len(raw)
        else:
            assert not path.exists() and declared["sha256"] is declared["size_bytes"] is None
    assert json.loads((output / "declaration.json").read_bytes()) == result
    assert "not authenticated producing-attempt custody" in result["qualification"]
    assert "does not authenticate full driver/calculator" in result["qualification"]


@pytest.mark.parametrize("change", ["digest", "size"])
def test_request_pin_conflict_stops_before_helper_and_declares_no_artifacts(tmp_path, monkeypatch, change):
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", forbid_helper)
    pin = write_json(tmp_path / "request.json", selected_request())
    before = (tmp_path / "request.json").read_bytes()
    pin["sha256" if change == "digest" else "size_bytes"] = "0" * 64 if change == "digest" else pin["size_bytes"] + 1
    output = tmp_path / "output"
    result = driver.run_molecular_sequence_driver(request_file=pin, output_directory=str(output))
    assert result["request_file_pin_verified"] is False
    assert result["driver_failure"]["stage"] == "read_request"
    assert result["native_call_state"] is result["native_failure"] is None
    assert (tmp_path / "request.json").read_bytes() == before
    check_declarations(result, output, set())


@pytest.mark.parametrize("raw", [b'{"version":1,"version":2}', b'{"invalid":NaN}', b'{"invalid":1e999}'])
def test_selected_json_rejection_keeps_verified_pin_without_execution(tmp_path, monkeypatch, raw):
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", forbid_helper)
    path = tmp_path / "request.json";path.write_bytes(raw)
    output = tmp_path / "output"
    result = driver.run_molecular_sequence_driver(request_file=file_pin(path), output_directory=str(output))
    assert result["request_file_pin_verified"] is True
    assert result["driver_failure"]["stage"] == "parse_request"
    assert result["native_call_state"] is result["native_failure"] is None
    check_declarations(result, output, set())


def test_unknown_scientific_context_is_not_silently_dropped(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", forbid_helper)
    request = selected_request();request["scientific_context"]["substitute_sequence"] = "AAA"
    result, output, _ = run_request(tmp_path, request)
    assert result["driver_failure"]["stage"] == "validate_request"
    assert result["native_call_state"] is None
    check_declarations(result, output, set())


def test_unexpected_helper_exception_is_a_driver_failure_with_native_state_unknown(tmp_path, monkeypatch):
    def broken(value):
        raise RuntimeError("engineered helper-boundary interruption")

    monkeypatch.setattr(driver, "execute_molecular_sequence_request", broken)
    result, output, _ = run_request(tmp_path, selected_request())
    assert result["native_call_state"] == "unknown" and result["native_failure"] is None
    assert result["driver_failure"] == {"stage": "invoke_helper", "exception_type": "RuntimeError",
        "message": "engineered helper-boundary interruption"}
    check_declarations(result, output, set())


def supplied_saved_sheet(tmp_path, *, corrupt=False):
    sheet = build_glycosylation_sheet(N_OPERATION, N_LOG, sequence="NAT", parameters={"allow_overlap": False})
    if corrupt:
        sheet["rows"][0]["cells"]["operand_symbols"] = "AAA"
    path = tmp_path / "supplied-sheet.json"
    # Deliberately distinct formatting proves the original bytes are retained.
    path.write_text(json.dumps(sheet, ensure_ascii=True, separators=(",", ":")) + "\n\n")
    return path, selected_request({"operation": N_OPERATION, "sheet_file": file_pin(path)}, mode="saved_sheet")


def test_saved_only_uses_authoritative_sheet_without_native_call_or_parameter_changes(tmp_path, monkeypatch):
    path, request = supplied_saved_sheet(tmp_path)
    before = path.read_bytes()
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", forbid_helper)
    result, output, _ = run_request(tmp_path, request)
    assert result["native_call_state"] == "not_requested"
    assert result["driver_failure"] is result["native_failure"] is None
    assert path.read_bytes() == (output / "sheet.json").read_bytes() == before
    components = json.loads((output / "components.json").read_bytes())
    assert components["parameters"]["supplied"] == {"allow_overlap": False}
    assert components["summary"]["native_reported_total_count"] == 1
    check_declarations(result, output, {"sheet", "components"})


def test_corrupt_saved_sheet_is_retained_without_repair_or_new_native_work(tmp_path, monkeypatch):
    path, request = supplied_saved_sheet(tmp_path, corrupt=True)
    before = path.read_bytes()
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", forbid_helper)
    result, output, _ = run_request(tmp_path, request)
    assert result["native_call_state"] == "not_requested" and result["native_failure"] is None
    assert result["driver_failure"]["stage"] == "calculate"
    assert result["driver_failure"]["message"].startswith("glycosylation_saved_sheet_conflict:")
    assert path.read_bytes() == (output / "sheet.json").read_bytes() == before
    check_declarations(result, output, {"sheet"})


def test_saved_operation_conflict_cannot_relabel_a_sheet(tmp_path, monkeypatch):
    path, request = supplied_saved_sheet(tmp_path)
    request["selection"]["operation"] = O_OPERATION
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", forbid_helper)
    result, output, _ = run_request(tmp_path, request)
    assert result["driver_failure"]["stage"] == "validate_saved_sheet"
    assert result["driver_failure"]["message"] == "molecular_sequence_driver_saved_sheet_operation_conflict"
    assert (output / "sheet.json").read_bytes() == path.read_bytes()
    check_declarations(result, output, {"sheet"})


def test_existing_output_directory_is_never_reexecuted_or_overwritten(tmp_path, monkeypatch):
    path, request = supplied_saved_sheet(tmp_path)
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", forbid_helper)
    result, output, pin = run_request(tmp_path, request)
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    with pytest.raises(FileExistsError):
        driver.run_molecular_sequence_driver(request_file=pin, output_directory=str(output))
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before
    assert result["driver_failure"] is None


def test_cli_processes_one_pinned_saved_sheet_with_exact_declarations(tmp_path):
    path, request = supplied_saved_sheet(tmp_path)
    pin = write_json(tmp_path / "cli-request.json", request)
    output = tmp_path / "cli-output"
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(dict.fromkeys([str(Path(__file__).resolve().parents[1]),
        *(value for value in sys.path if value and Path(value).is_absolute())]))
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run([sys.executable, "-B", "-S", "-m", "gene_annotation_episode.molecular_sequence_driver",
        "--request-file", pin["path"], "--request-sha256", pin["sha256"],
        "--request-size-bytes", str(pin["size_bytes"]), "--output-directory", str(output)],
        cwd=Path(__file__).resolve().parents[1], env=environment, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    result = json.loads(completed.stdout)
    assert result["request_file_pin_verified"] is True and result["native_call_state"] == "not_requested"
    assert (output / "sheet.json").read_bytes() == path.read_bytes()
    check_declarations(result, output, {"sheet", "components"})
