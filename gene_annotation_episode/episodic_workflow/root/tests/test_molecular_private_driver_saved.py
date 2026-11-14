"""Private writer boundaries; genuine selected-source joins require explicit opt-in."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from gene_annotation_episode.episodic_workflow.root.library import molecular_sequence_driver as driver
from gene_annotation_episode.episodic_workflow.root.library.glycosylation_measurements import build_glycosylation_sheet
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

