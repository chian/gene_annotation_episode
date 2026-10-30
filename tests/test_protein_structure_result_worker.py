"""Retained actual C/B synthetic native results, bounded files and real CLI.

All scientific fixtures were produced in the source packets' local_jobs runs.
No fixture is presented as a measured biological structure or Store authority.
"""
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys

import numpy as np
import pytest

from gene_annotation_episode import protein_structure_result_worker as worker
from gene_annotation_episode import protein_structure_calculations as calculations
from gene_annotation_episode import protein_structure_sheet as sheets
from gene_annotation_episode import protein_structure_sequences as sequences
from gene_annotation_episode import protein_structure_metadata as metadata
from gene_annotation_episode import protein_structure_formats as formats
from gene_annotation_episode import native_protein_structure_worker as native_worker
from gene_annotation_episode import sequence_ops
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.protein_structure_contracts import issue, same

REPO = Path(__file__).resolve().parents[1]
PACKET = REPO / "verification/tool_graders_protein_structure_result_worker_2026-10-27_393"
FIXTURES = PACKET / "fixtures"


def _bytes(value):
    return canonical(value).encode("utf-8")


def _identity(raw, format):
    sha = hashlib.sha256(raw).hexdigest()
    return {"artifact_ref": "artifact_" + sha, "sha256": sha, "byte_length": len(raw), "format": format}


def _retain(path, raw, format):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {"file_identity": _identity(raw, format), "path": str(path)}


def _native_plan(tmp_path, label="held_out"):
    raw = (FIXTURES / (label + ".json")).read_bytes()
    native = json.loads(raw)
    retained = _retain(tmp_path / "retained/native.json", raw, native["version"])
    plan = {"version": "protein_structure_result_worker_plan_v1", "mode": "original_native_result",
        "directory": str(tmp_path / "output"), "expected_request": deepcopy(native["request"]),
        "expected_software": deepcopy(native["producer"]), "native_result": retained}
    return plan, native


def _saved_plan(tmp_path):
    # B's retained example is value-identical canonical JSON plus a trailing
    # newline. Test input preparation explicitly serializes that unchanged
    # value into the no-newline retained-file contract. The worker never repairs
    # supplied noncanonical bytes; the original B artifact remains untouched.
    sheet = json.loads((FIXTURES / "saved_sheet.json").read_bytes())
    sheet_raw = _bytes(sheet)
    original_raw = (FIXTURES / "original_components.json").read_bytes()
    plan = {"version": "protein_structure_result_worker_plan_v1", "mode": "saved_sheet_recalculation",
        "directory": str(tmp_path / "output"),
        "sheet": _retain(tmp_path / "retained/sheet.json", sheet_raw, "protein_structure_comparison_sheet_v1"),
        "original_components": _retain(tmp_path / "retained/original.json", original_raw, "protein_structure_components_v1"),
        "parameters": deepcopy(sheet["native_request"])}
    return plan, sheet


def _replace(plan, key, value):
    original = plan[key]
    plan[key] = _retain(Path(original["path"]), _bytes(value), original["file_identity"]["format"])


def _output(plan, result, field):
    row = result[field]
    raw = (Path(plan["directory"]) / row["relative_path"]).read_bytes()
    assert row["file_identity"] == _identity(raw, row["file_identity"]["format"])
    value = json.loads(raw)
    assert raw == _bytes(value) and not raw.endswith(b"\n")
    return value


def _result_bytes(plan, result):
    raw = (Path(plan["directory"]) / "worker-result.json").read_bytes()
    assert raw == _bytes(result)
    assert worker.validate_protein_structure_result_worker_result(json.loads(raw)) == result


def _forbid(*args, **kwargs):
    raise AssertionError("forbidden acquisition, execution, refit or model operation")


def _no_acquisition(monkeypatch):
    monkeypatch.setattr(socket, "socket", _forbid)
    monkeypatch.setattr(socket, "create_connection", _forbid)
    monkeypatch.setattr(subprocess, "Popen", _forbid)
    monkeypatch.setattr(os, "system", _forbid)
    monkeypatch.setattr(native_worker, "execute_protein_structure_request", _forbid)
    monkeypatch.setattr(native_worker, "check_selected_software", _forbid)
    monkeypatch.setattr(sequence_ops, "align_pair", _forbid)
    monkeypatch.setattr(formats, "parse_pdb_structure", _forbid)
    monkeypatch.setattr(formats, "parse_mmcif_structure", _forbid)


def _no_refit(monkeypatch):
    monkeypatch.setattr(worker, "calculate_protein_structure_components", _forbid)
    monkeypatch.setattr(calculations, "calculate_protein_structure_components", _forbid)
    monkeypatch.setattr(calculations, "fit_ca_transform", _forbid)
    monkeypatch.setattr(np.linalg, "svd", _forbid)


@pytest.mark.parametrize("label", ["inspect", "extract", "extract_unavailable", "held_out", "supplied", "zero_available", "mixed_partial"])
def test_original_actual_native_records_are_unchanged_without_refit(tmp_path, monkeypatch, label):
    plan, native = _native_plan(tmp_path, label)
    before = deepcopy(plan)
    _no_acquisition(monkeypatch)
    _no_refit(monkeypatch)
    if native["request"]["operation"] != "compare":
        monkeypatch.setattr(sequences, "inspect_structure", _forbid)
        monkeypatch.setattr(sequences, "extract_structure_sequence", _forbid)
        monkeypatch.setattr(metadata, "extract_native_structure_metadata", _forbid)
        monkeypatch.setattr(sheets, "extract_structure_sequence", _forbid)
    result = worker.run_protein_structure_result_worker(plan)
    assert same(plan, before)
    assert result["state"] == native["state"] and same(result["issues"], native["issues"])
    assert same(_output(plan, result, "native_result_file"), native)
    assert (Path(plan["directory"]) / "native-result.json").read_bytes() == Path(plan["native_result"]["path"]).read_bytes()
    if native["request"]["operation"] == "compare":
        assert same(_output(plan, result, "sheet_file"), native["sheet"])
        assert same(_output(plan, result, "components_file"), native["sheet"]["native_baseline"])
    else:
        assert result["sheet_file"] is None and result["components_file"] is None
        assert set(p.name for p in Path(plan["directory"]).iterdir()) == {"native-result.json", "worker-result.json"}
        if label == "extract_unavailable":
            assert native["sequence"]["alignment_sequence"] is None
            assert not (Path(plan["directory"]) / "sequence.txt").exists()
    _result_bytes(plan, result)


def test_held_out_and_supplied_native_numerical_values_and_zero_unknown(tmp_path):
    plan, native = _native_plan(tmp_path / "held")
    result = worker.run_protein_structure_result_worker(plan)
    components = _output(plan, result, "components_file")
    assert components["counts"]["fit_used_count"]["value"] == 4
    assert components["counts"]["evaluation_used_count"]["value"] == 1
    assert components["evaluation"]["evaluation_sse"]["value"] == 3.9999999999999982
    assert components["evaluation"]["evaluation_rmsd"]["value"] == 1.9999999999999996
    assert components["evaluation"]["evaluation_rmsd"]["value"] == pytest.approx(2.0)
    assert components["site_measurements"][0]["in_fit"] is False
    plan, _ = _native_plan(tmp_path / "supplied", "supplied")
    result = worker.run_protein_structure_result_worker(plan)
    components = _output(plan, result, "components_file")
    assert components["evaluation"]["evaluation_rmsd"]["value"] == 0.0
    assert components["evaluation"]["evaluation_rmsd"]["state"] == "present"
    assert components["fit"]["fit_rmsd"]["value"] is None
    assert components["fit"]["fit_rmsd"]["state"] == "not_applicable"
    plan, _ = _native_plan(tmp_path / "zero", "zero_available")
    result = worker.run_protein_structure_result_worker(plan)
    components = _output(plan, result, "components_file")
    assert components["counts"]["available_pair_count"]["value"] == 0
    assert components["counts"]["mapped_pair_count"]["value"] == 4
    assert components["evaluation"]["evaluation_rmsd"]["value"] is None
    assert components["evaluation"]["evaluation_rmsd"]["state"] == "unavailable"


@pytest.mark.parametrize("state", ["invalid", "unavailable", "partial"])
def test_null_native_sheet_preserves_actual_state_and_issues(tmp_path, monkeypatch, state):
    plan, native = _native_plan(tmp_path)
    native.update(sheet=None, state=state, issues=[issue("native_result_missing", stage="native", artifact_role="native_result")])
    _replace(plan, "native_result", native)
    _no_refit(monkeypatch)
    result = worker.run_protein_structure_result_worker(plan)
    assert result["state"] == state and result["issues"] == native["issues"]
    assert result["native_result_file"] is not None
    assert result["sheet_file"] is None and result["components_file"] is None


def test_c_valid_native_with_bad_arithmetic_is_diagnostic_only(tmp_path, monkeypatch):
    plan, native = _native_plan(tmp_path)
    native["sheet"]["native_baseline"]["evaluation"]["evaluation_rmsd"]["value"] = 19.0
    _replace(plan, "native_result", native)
    _no_refit(monkeypatch)
    result = worker.run_protein_structure_result_worker(plan)
    assert result["state"] == "invalid"
    assert result["issues"][-1]["code"] == "numeric_inconsistency"
    assert same(_output(plan, result, "native_result_file"), native)
    assert result["sheet_file"] is None and result["components_file"] is None
    # Host must not publish comparison numbers or a descriptor from this file.
    _result_bytes(plan, result)


def test_saved_recalculation_changes_only_separate_components_once(tmp_path, monkeypatch):
    plan, sheet = _saved_plan(tmp_path)
    plan["parameters"]["evaluation_selection"] = {"kind": "all_mapped_pairs"}
    plan["parameters"]["distance_threshold_A"] = 1.5
    original_sheet_bytes = Path(plan["sheet"]["path"]).read_bytes()
    original_components_bytes = Path(plan["original_components"]["path"]).read_bytes()
    calls = []
    calculate = worker.calculate_protein_structure_components

    def counted(value, *, parameters):
        calls.append(deepcopy(parameters))
        return calculate(value, parameters=parameters)

    monkeypatch.setattr(worker, "calculate_protein_structure_components", counted)
    _no_acquisition(monkeypatch)
    real_open = os.open
    permitted = {plan["sheet"]["path"], plan["original_components"]["path"]}

    def confined_open(path, flags, *args, **kwargs):
        name = str(path)
        assert name in permitted or Path(name).is_relative_to(plan["directory"]), name
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", confined_open)
    result = worker.run_protein_structure_result_worker(plan)
    assert calls == [plan["parameters"]]
    assert result["mode"] == "saved_sheet_recalculation" and result["operation"] == "compare"
    assert result["native_result_file"] is None and result["state"] == "complete"
    components = _output(plan, result, "components_file")
    assert components["counts"]["fit_used_count"]["value"] == 4
    assert components["counts"]["evaluation_used_count"]["value"] == 5
    assert components["evaluation"]["evaluation_sse"]["value"] == pytest.approx(4)
    assert components["evaluation"]["evaluation_rmsd"]["value"] == pytest.approx(math.sqrt(4 / 5))
    assert components["evaluation"]["evaluation_mean_distance"]["value"] == pytest.approx(0.4)
    assert components["evaluation"]["above_threshold_count"]["value"] == 1
    assert components["calculation_id"] != sheet["native_baseline"]["calculation_id"]
    assert same(_output(plan, result, "sheet_file"), sheet)
    assert (Path(plan["directory"]) / "sheet.json").read_bytes() == original_sheet_bytes
    assert Path(plan["sheet"]["path"]).read_bytes() == original_sheet_bytes
    assert Path(plan["original_components"]["path"]).read_bytes() == original_components_bytes
    _result_bytes(plan, result)


def test_saved_explicit_new_fit_selection(tmp_path):
    plan, sheet = _saved_plan(tmp_path)
    plan["parameters"]["fit_selection"] = {"kind": "all_mapped_pairs"}
    result = worker.run_protein_structure_result_worker(plan)
    components = _output(plan, result, "components_file")
    assert components["counts"]["fit_used_count"]["value"] == 5
    assert sheet["native_baseline"]["counts"]["fit_used_count"]["value"] == 4
    assert same(_output(plan, result, "sheet_file"), sheet)


def test_saved_explicit_mode_change_without_svd(tmp_path, monkeypatch):
    plan, sheet = _saved_plan(tmp_path)
    plan["parameters"].update(mode="evaluate_declared_transform_ca", fit_selection=None,
        declared_transform={"version": "protein_structure_transform_v1", "direction": "moving_to_fixed",
            "convention": "row_vector_y_R_plus_t", "rotation": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
            "translation_A": [0, 0, 0], "fixed_selection": deepcopy(sheet["sequences"]["fixed"]["selection"]),
            "moving_selection": deepcopy(sheet["sequences"]["moving"]["selection"]), "origin": "supplied", "received_from": None})
    monkeypatch.setattr(np.linalg, "svd", _forbid)
    _no_acquisition(monkeypatch)
    result = worker.run_protein_structure_result_worker(plan)
    components = _output(plan, result, "components_file")
    assert components["parameters"]["mode"] == "evaluate_declared_transform_ca"
    assert components["evaluation"]["evaluation_rmsd"]["value"] == 2.0
    assert components["fit"]["fit_rmsd"]["state"] == "not_applicable"
    assert same(_output(plan, result, "sheet_file"), sheet)
    assert sheet["native_request"]["mode"] == "fit_then_evaluate_ca"


@pytest.mark.parametrize("failure", ["missing_baseline", "different_baseline", "invalid_arithmetic", "wrong_original_parameters", "missing_components"])
def test_saved_failure_keeps_diagnostic_sheet_without_calculation(tmp_path, monkeypatch, failure):
    plan, sheet = _saved_plan(tmp_path)
    original = json.loads(Path(plan["original_components"]["path"]).read_bytes())
    if failure == "missing_baseline":
        sheet["native_baseline"] = None
        _replace(plan, "sheet", sheet)
    elif failure == "different_baseline":
        original["evaluation"]["evaluation_rmsd"]["value"] = 999.0
        _replace(plan, "original_components", original)
    elif failure == "invalid_arithmetic":
        original["evaluation"]["evaluation_rmsd"]["value"] = 999.0
        sheet["native_baseline"] = deepcopy(original)
        _replace(plan, "sheet", sheet)
        _replace(plan, "original_components", original)
    elif failure == "wrong_original_parameters":
        sheet["native_request"]["distance_threshold_A"] = 17.0
        _replace(plan, "sheet", sheet)
    else:
        Path(plan["original_components"]["path"]).unlink()
    _no_refit(monkeypatch)
    result = worker.run_protein_structure_result_worker(plan)
    assert result["state"] == ("unavailable" if failure == "missing_components" else "invalid")
    assert same(_output(plan, result, "sheet_file"), sheet)
    assert result["components_file"] is None and result["native_result_file"] is None
    assert result["issues"][-1]["artifact_role"] is None
    # Independently structural-valid sheet_file is diagnostic, not a usable
    # saved-sheet descriptor or authority to project numbers after this failure.
    _result_bytes(plan, result)


@pytest.mark.parametrize("failure, expected", [("absent", "native_result_missing"), ("missing", "retained_artifact_missing"),
    ("changed", "input_digest_mismatch"), ("length", "input_digest_mismatch"), ("format", "unsupported_format"),
    ("request", "original_commission_mismatch"), ("software", "software_identity_mismatch")])
def test_native_input_failure_distinctions(tmp_path, failure, expected):
    plan, _ = _native_plan(tmp_path, "inspect")
    if failure == "absent":
        plan["native_result"] = None
    elif failure == "missing":
        Path(plan["native_result"]["path"]).unlink()
    elif failure == "changed":
        Path(plan["native_result"]["path"]).write_bytes(b"changed")
    elif failure == "length":
        plan["native_result"]["file_identity"]["byte_length"] += 1
    elif failure == "format":
        plan["native_result"]["file_identity"]["format"] = "text"
    elif failure == "request":
        plan["expected_request"]["inventory"]["include"] = ["models"]
    else:
        plan["expected_software"]["python_sha256"] = "0" * 64
    result = worker.run_protein_structure_result_worker(plan)
    assert result["issues"][-1]["code"] == expected
    assert result["state"] == ("unavailable" if failure in ("absent", "missing") else "invalid")
    assert all(result[field] is None for field in ("native_result_file", "sheet_file", "components_file"))
    _result_bytes(plan, result)


@pytest.mark.parametrize("raw", [b"{", b"[]", b'{"version":1,"version":2}', b'{"x":NaN}',
    b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":1e400}', b'{"x":"\\ud800"}', b"\xff"])
def test_malformed_retained_json_becomes_invalid_result(tmp_path, raw):
    plan, _ = _native_plan(tmp_path, "inspect")
    plan["native_result"] = _retain(Path(plan["native_result"]["path"]), raw, plan["native_result"]["file_identity"]["format"])
    result = worker.run_protein_structure_result_worker(plan)
    assert result["state"] == "invalid" and result["native_result_file"] is None
    assert result["issues"][-1]["code"] in ("invalid_schema", "unsupported_format")
    _result_bytes(plan, result)


@pytest.mark.parametrize("mutation", ["newline", "pretty", "duplicate", "boolean_count", "float_count", "extra", "version"])
def test_native_canonical_format_and_strict_types(tmp_path, mutation):
    plan, native = _native_plan(tmp_path, "inspect")
    raw = _bytes(native)
    if mutation == "newline": raw += b"\n"
    elif mutation == "pretty": raw = json.dumps(native, indent=2).encode()
    elif mutation == "duplicate": raw = b'{"version":"duplicate",' + raw[1:]
    elif mutation in ("boolean_count", "float_count"):
        native["inventory"]["models"][0]["atom_count"] = True if mutation == "boolean_count" else 4.0
        raw = _bytes(native)
    elif mutation == "extra":
        native["extra"] = "unapproved"
        raw = _bytes(native)
    else:
        native["version"] = "protein_structure_native_v1"
        raw = _bytes(native)
    plan["native_result"] = _retain(Path(plan["native_result"]["path"]), raw, plan["native_result"]["file_identity"]["format"])
    result = worker.run_protein_structure_result_worker(plan)
    assert result["state"] == "invalid" and result["native_result_file"] is None


@pytest.mark.parametrize("key", ["sheet", "original_components"])
def test_saved_wrong_format_and_missing_bytes_are_typed(tmp_path, key):
    plan, _ = _saved_plan(tmp_path / "format")
    plan[key]["file_identity"]["format"] = "text"
    result = worker.run_protein_structure_result_worker(plan)
    assert result["state"] == "invalid" and result["issues"][-1]["code"] == "unsupported_format"
    plan, _ = _saved_plan(tmp_path / "missing")
    Path(plan[key]["path"]).unlink()
    result = worker.run_protein_structure_result_worker(plan)
    assert result["state"] == "unavailable" and result["issues"][-1]["code"] == "retained_artifact_missing"


def test_original_b_example_newline_is_not_silently_repaired(tmp_path, monkeypatch):
    plan, _ = _saved_plan(tmp_path)
    raw = (FIXTURES / "saved_sheet.json").read_bytes()
    assert raw.endswith(b"\n")
    plan["sheet"] = _retain(Path(plan["sheet"]["path"]), raw, plan["sheet"]["file_identity"]["format"])
    _no_refit(monkeypatch)
    result = worker.run_protein_structure_result_worker(plan)
    assert result["state"] == "invalid" and result["sheet_file"] is None
    assert result["issues"][-1]["code"] == "invalid_schema"
    assert Path(plan["sheet"]["path"]).read_bytes() == raw


def test_pure_validators_are_detached_and_do_no_io_or_science(tmp_path, monkeypatch):
    native_plan, _ = _native_plan(tmp_path / "native", "inspect")
    saved_plan, _ = _saved_plan(tmp_path / "saved")
    result = worker.run_protein_structure_result_worker(native_plan)
    _no_acquisition(monkeypatch)
    _no_refit(monkeypatch)
    monkeypatch.setattr(worker, "parse_native_protein_comparison", _forbid)
    monkeypatch.setattr(worker, "validate_recorded_protein_structure_components", _forbid)
    monkeypatch.setattr(os, "open", _forbid)
    monkeypatch.setattr(Path, "open", _forbid)
    monkeypatch.setattr(Path, "resolve", _forbid)
    monkeypatch.setattr(Path, "stat", _forbid)
    for plan in (native_plan, saved_plan):
        detached = worker.validate_protein_structure_result_worker_plan(plan)
        assert same(plan, detached) and detached is not plan
        detached["directory"] = "/changed"
        assert detached["directory"] != plan["directory"]
    detached = worker.validate_protein_structure_result_worker_result(result)
    assert same(detached, result) and detached is not result
    detached["native_result_file"]["file_identity"]["byte_length"] = 1
    assert detached != result


@pytest.mark.parametrize("mutation", ["extra", "missing", "relative", "overlap", "nonfinite", "boolean_count", "float_count", "unknown_mode", "tuple"])
def test_malformed_plan_raises_before_work(tmp_path, mutation):
    plan, _ = _native_plan(tmp_path, "inspect")
    if mutation == "extra": plan["extra"] = 1
    elif mutation == "missing": del plan["expected_software"]
    elif mutation == "relative": plan["directory"] = "output"
    elif mutation == "overlap": plan["directory"] = str(Path(plan["native_result"]["path"]).parent)
    elif mutation == "nonfinite": plan["native_result"]["file_identity"]["byte_length"] = float("inf")
    elif mutation == "boolean_count": plan["native_result"]["file_identity"]["byte_length"] = True
    elif mutation == "float_count": plan["native_result"]["file_identity"]["byte_length"] = float(plan["native_result"]["file_identity"]["byte_length"])
    elif mutation == "unknown_mode": plan["mode"] = "refit_original"
    else: plan["expected_request"]["inventory"]["include"] = ("models",)
    with pytest.raises(ValueError):
        worker.run_protein_structure_result_worker(plan)
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("mutation", ["extra", "wrong_name", "wrong_format", "boolean_count", "float_count", "bad_relation", "bad_issue", "unknown_state", "missing_native"])
def test_closed_output_validation_rejects_conflicting_fields(tmp_path, mutation):
    plan, _ = _native_plan(tmp_path, "inspect")
    result = worker.run_protein_structure_result_worker(plan)
    if mutation == "extra": result["extra"] = 1
    elif mutation == "wrong_name": result["native_result_file"]["relative_path"] = "../result.json"
    elif mutation == "wrong_format": result["native_result_file"]["file_identity"]["format"] = "text"
    elif mutation == "boolean_count": result["native_result_file"]["file_identity"]["byte_length"] = True
    elif mutation == "float_count": result["native_result_file"]["file_identity"]["byte_length"] = 1.0
    elif mutation == "bad_relation": result["mode"] = "saved_sheet_recalculation"
    elif mutation == "bad_issue": result["issues"] = [dict(issue("invalid_schema"), narrative="unapproved")]
    elif mutation == "unknown_state": result["state"] = "successful"
    else: result["native_result_file"] = None
    with pytest.raises(ValueError):
        worker.validate_protein_structure_result_worker_result(result)


@pytest.mark.parametrize("case", ["file_symlink", "parent_symlink", "directory_input", "fifo"])
def test_nonregular_or_symlink_retained_inputs_are_rejected(tmp_path, case):
    plan, _ = _native_plan(tmp_path, "inspect")
    path = Path(plan["native_result"]["path"])
    target = path.with_name("target.json")
    if case == "file_symlink":
        path.rename(target)
        path.symlink_to(target)
    elif case == "parent_symlink":
        alias = tmp_path / "alias"
        alias.symlink_to(path.parent, target_is_directory=True)
        plan["native_result"]["path"] = str(alias / path.name)
    elif case == "directory_input":
        path.unlink()
        path.mkdir()
    else:
        path.unlink()
        os.mkfifo(path)
    result = worker.run_protein_structure_result_worker(plan)
    assert result["state"] == "invalid" and result["issues"][-1]["code"] == "invalid_output_path"


def test_output_symlinks_and_hardlinked_input_overlap_raise(tmp_path):
    plan, _ = _native_plan(tmp_path, "inspect")
    directory = Path(plan["directory"])
    directory.symlink_to(tmp_path / "retained", target_is_directory=True)
    with pytest.raises(ValueError, match="invalid_output_path"):
        worker.run_protein_structure_result_worker(plan)
    directory.unlink()
    directory.mkdir()
    os.link(plan["native_result"]["path"], directory / "native-result.json")
    with pytest.raises(ValueError, match="invalid_output_path"):
        worker.run_protein_structure_result_worker(plan)


def test_immutable_exact_replay_and_conflicting_reuse_do_not_rewrite(tmp_path):
    plan, _ = _native_plan(tmp_path, "inspect")
    result = worker.run_protein_structure_result_worker(plan)
    directory = Path(plan["directory"])
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns, stat.S_IMODE(p.stat().st_mode)) for p in directory.iterdir()}
    assert worker.run_protein_structure_result_worker(plan) == result
    after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns, stat.S_IMODE(p.stat().st_mode)) for p in directory.iterdir()}
    assert before == after and all(mode == 0o444 for _, _, mode in before.values())
    plan["native_result"] = None
    with pytest.raises(ValueError, match="original_commission_mismatch"):
        worker.run_protein_structure_result_worker(plan)
    assert {p.name: p.read_bytes() for p in directory.iterdir()} == {name: item[0] for name, item in before.items()}


def test_stale_output_conflict_is_detected_before_any_publication(tmp_path):
    plan, _ = _native_plan(tmp_path, "inspect")
    directory = Path(plan["directory"])
    directory.mkdir()
    (directory / "components.json").write_bytes(b"unrelated original file")
    with pytest.raises(ValueError, match="original_commission_mismatch"):
        worker.run_protein_structure_result_worker(plan)
    assert set(p.name for p in directory.iterdir()) == {"components.json"}
    assert (directory / "components.json").read_bytes() == b"unrelated original file"


@pytest.mark.parametrize("mode", ["native", "saved", "failure"])
def test_real_cli_and_output_bytes(tmp_path, mode):
    if mode == "saved":
        plan, sheet = _saved_plan(tmp_path)
        plan["parameters"]["evaluation_selection"] = {"kind": "all_mapped_pairs"}
    else:
        plan, native = _native_plan(tmp_path)
        if mode == "failure": plan["native_result"] = None
    plan_file = tmp_path / "plan.json"
    plan_file.write_bytes(_bytes(plan))
    command = [sys.executable, "-B", "-m", "gene_annotation_episode.protein_structure_result_worker", str(plan_file)]
    completed = subprocess.run(command, cwd=tmp_path, capture_output=True, check=False)
    (tmp_path / "cli-command.json").write_bytes(_bytes(command))
    (tmp_path / "cli-stdout.txt").write_bytes(completed.stdout)
    (tmp_path / "cli-stderr.txt").write_bytes(completed.stderr)
    assert completed.returncode == 0, completed.stderr.decode()
    result = json.loads((Path(plan["directory"]) / "worker-result.json").read_bytes())
    _result_bytes(plan, result)
    if mode == "failure":
        assert result["state"] == "unavailable" and result["native_result_file"] is None
    else:
        components = _output(plan, result, "components_file")
        assert components["evaluation"]["evaluation_rmsd"]["value"] == pytest.approx(math.sqrt(4 / 5) if mode == "saved" else 2)
        assert same(_output(plan, result, "sheet_file"), sheet if mode == "saved" else native["sheet"])


def test_cli_rejects_extra_arguments_and_noncanonical_plan(tmp_path):
    plan, _ = _native_plan(tmp_path, "inspect")
    plan_file = tmp_path / "plan.json"
    plan_file.write_bytes(_bytes(plan) + b"\n")
    base = [sys.executable, "-B", "-m", "gene_annotation_episode.protein_structure_result_worker"]
    for arguments in ([], [str(plan_file)], [str(plan_file), "extra"]):
        result = subprocess.run(base + arguments, cwd=tmp_path, capture_output=True, check=False)
        assert result.returncode != 0 and b"ValueError" in result.stderr
    assert not Path(plan["directory"]).exists()


def test_oversized_real_in_native_input_is_a_typed_failure(tmp_path):
    plan, native = _native_plan(tmp_path)
    native["sheet"]["native_baseline"]["evaluation"]["evaluation_rmsd"]["value"] = 10 ** 400
    _replace(plan, "native_result", native)
    result = worker.run_protein_structure_result_worker(plan)
    assert result["state"] == "invalid" and result["issues"][-1]["code"] == "invalid_schema"
    assert result["native_result_file"] is None
    _result_bytes(plan, result)


def test_oversized_real_in_request_is_a_typed_plan_error(tmp_path):
    plan, _ = _native_plan(tmp_path)
    plan["expected_request"]["parameters"]["distance_threshold_A"] = 10 ** 400
    with pytest.raises(ValueError, match="invalid_schema"):
        worker.validate_protein_structure_result_worker_plan(plan)
    assert not Path(plan["directory"]).exists()


def test_unfinished_publication_conflict_is_typed_and_not_overwritten(tmp_path):
    plan, _ = _native_plan(tmp_path, "inspect")
    directory = Path(plan["directory"])
    directory.mkdir()
    marker = directory / ".native-result.json.writing"
    marker.write_bytes(b"unfinished prior publication")
    with pytest.raises(ValueError, match="invalid_output_path"):
        worker.run_protein_structure_result_worker(plan)
    assert marker.read_bytes() == b"unfinished prior publication"
    assert not (directory / "worker-result.json").exists()
