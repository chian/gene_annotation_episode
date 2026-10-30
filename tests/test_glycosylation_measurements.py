"""Explicit log controls; whole genuine module execution is opt-in under529."""
from copy import deepcopy
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import sys
import traceback

import pytest

from gene_annotation_episode.glycosylation_measurements import (
    SOURCE_SHA256, build_glycosylation_sheet, calculate_glycosylation_components,
)
from gene_annotation_episode.sequence_mapping import VERSION as MAPPING_VERSION


N = "find_n_glycosylation_motifs"
O = "predict_o_glycosylation_hotspots"
N_TITLE = "# N-linked glycosylation sequon scan (N-X-[S/T], X≠P)"
O_TITLE = "# Heuristic O-glycosylation hotspot prediction (S/T density based)"
NOTE = "Note: For state-of-the-art O-glycosite prediction, use NetOGlyc 4.0 (web service)."


def n_log(length, total, rows=(), remaining=None):
    """Explicit parser fixtures; not an invoked source or scientific output."""
    lines = [N_TITLE, f"Sequence length: {length}", f"Total sequons found: {total}"]
    lines += ["", "Positions (1-based):", *rows] if total else ["No canonical N-linked sequons detected."]
    if remaining is not None:
        lines.append(f"... and {remaining} more")
    return "\n".join(lines)


def o_log(length, total, rows=(), *, window=7, threshold=0.4, remaining=None):
    lines = [O_TITLE, f"Sequence length: {length} | window={window} | threshold={threshold}",
        f"Total candidate sites: {total}"]
    lines += ["", "Top candidates:", *rows] if total else ["No candidate O-glycosylation hotspots met the heuristic threshold."]
    if remaining is not None:
        lines.append(f"... and {remaining} more")
    return "\n".join([*lines, "", NOTE])


def measured(operation, log, sequence, parameters=None, **kwargs):
    sheet = build_glycosylation_sheet(operation, log, sequence=sequence,
        parameters={} if parameters is None else parameters, **kwargs)
    return sheet, calculate_glycosylation_components(sheet)


def mapping(length):
    return {"version": MAPPING_VERSION, "units_per_symbol": 1, "symbol_length": length,
        "path": [{"subject_ref": "source:explicit-control", "start": 10, "end": 10 + length,
            "unit": "aa", "strand": "+"}]}


def test_n_overlap_policy_and_explicit_original_coordinate_mapping():
    _, default = measured(N, n_log(4, 1, ["- 1: NNS"]), "nnst")
    sheet, overlap = measured(N, n_log(4, 2, ["- 1: NNS", "- 2: NST"]), "nnst",
        {"allow_overlap": True}, input_ref="supplied:protein", input_mapping=mapping(4))
    assert default["summary"]["native_reported_total_count"] == 1
    assert default["summary"]["native_report_complete"] is True
    assert overlap["summary"]["usable_checked_row_count"] == 2
    assert overlap["rows"][1]["cells"]["processed_interval"] == [1, 4]
    assert overlap["rows"][1]["cells"]["source_intervals"] == [
        {"subject_ref": "source:explicit-control", "start": 11, "end": 14, "unit": "aa", "strand": "+"}]
    assert overlap["supplied_protein_composition"]["symbol_counts"] == {"N": 2, "S": 1, "T": 1}
    assert sheet["inputs"]["sequence"] == "nnst"
    assert sheet["parameters"]["supplied"] == {"allow_overlap": True}
    _, incompatible = measured(N, sheet["inputs"]["native_log"], "nnst")
    assert incompatible["rows"][1]["cells"]["order_compatible"] is False
    assert incompatible["summary"]["usable_checked_row_count"] == 1
    assert incompatible["summary"]["native_report_complete"] is False


def test_o_clipping_actual_denominator_proline_exclusion_and_native_window_fallback():
    log = o_log(3, 1, ["- pos 1 (S): S/T fraction=0.667 in window 1-3"])
    sheet, result = measured(O, log, "STP", {"window": 2})
    cells = result["rows"][0]["cells"]
    assert sheet["parameters"]["requested_with_defaults"]["window"] == 2
    assert sheet["parameters"]["effective"]["window"] == 7
    assert sheet["parameters"]["source_defaults"]["window"] == 7
    assert cells["expected_clipped_window_interval"] == cells["native_window_interval"] == [0, 3]
    assert cells["st_count"] == 2 and cells["window_denominator_symbols"] == 3
    assert cells["calculated_st_fraction"] == 2 / 3
    assert cells["source_rounded_st_fraction"] == result["rows"][0]["native_values"]["st_fraction"] == .667
    assert result["summary"]["native_report_complete"] is True
    # A displayed extra T row has its own real local arithmetic, but it is
    # incompatible with the requested immediate-following-P exclusion.
    _, conflict = measured(O, o_log(3, 2, [
        "- pos 1 (S): S/T fraction=0.667 in window 1-3",
        "- pos 2 (T): S/T fraction=0.667 in window 1-3"]), "STP")
    assert conflict["rows"][1]["cells"]["calculated_st_fraction"] == 2 / 3
    assert conflict["rows"][1]["cells"]["following_proline"] is True
    assert conflict["rows"][1]["cells"]["following_proline_allowed"] is False
    assert conflict["rows"][1]["source_compatible"] is False


def test_o_threshold_compares_unrounded_fraction_and_keeps_printed_conflicts():
    log = o_log(3, 1, ["- pos 2 (S): S/T fraction=0.333 in window 1-3"], window=3, threshold=.3333)
    _, lower = measured(O, log, "ASA", {"window": 3, "min_st_fraction": .3333})
    assert lower["rows"][0]["cells"]["calculated_st_fraction"] == 1 / 3
    assert lower["rows"][0]["cells"]["unrounded_threshold_satisfied"] is True
    assert lower["rows"][0]["native_values"]["st_fraction"] < .3333
    assert lower["summary"]["native_report_complete"] is True
    _, higher = measured(O, log.replace("threshold=0.3333", "threshold=0.3334"), "ASA",
        {"window": 3, "min_st_fraction": .3334})
    assert higher["rows"][0]["cells"]["unrounded_threshold_satisfied"] is False
    assert higher["summary"]["usable_checked_row_count"] == 0
    _, wrong = measured(O, log.replace("fraction=0.333", "fraction=0.334"), "ASA",
        {"window": 3, "min_st_fraction": .3333})
    assert wrong["rows"][0]["native_values"]["st_fraction"] == .334
    assert wrong["rows"][0]["cells"]["source_rounded_st_fraction"] == .333
    assert wrong["rows"][0]["cells"]["printed_fraction_matches_calculation"] is False


def test_original_null_empty_missing_failed_and_partial_are_distinct():
    _, empty = measured(N, n_log(0, 0), "")
    sheet, unknown = measured(N, n_log(0, 0), None)
    _, missing = measured(N, None, "")
    _, blank = measured(N, "", "")
    _, failed = measured(N, n_log(0, 0), "", native_outcome="failed")
    _, partial = measured(N, n_log(0, 0), "", native_outcome="partial")
    assert empty["summary"]["native_report_complete"] is True
    assert empty["summary"]["original_symbol_count"] == empty["supplied_protein_composition"]["length"] == 0
    assert sheet["source_normalization"]["processed_sequence"] == ""
    assert unknown["summary"]["original_symbol_count"] is None
    assert unknown["supplied_protein_composition"] is None
    assert unknown["summary"]["native_report_complete"] is False
    assert missing["summary"]["native_reported_total_count"] is None
    assert missing["summary"]["retained_printed_row_count"] is None
    assert blank["summary"]["native_reported_total_count"] is None
    assert blank["summary"]["retained_printed_row_count"] == 0
    assert failed["summary"]["native_reported_total_count"] == 0
    assert failed["summary"]["retained_printed_row_count"] == 0
    assert failed["status"] == "failed"
    assert failed["summary"]["native_report_complete"] is partial["summary"]["native_log_complete"] is False


def test_noncanonical_literal_middle_and_unicode_expansion_are_not_alphabet_repair():
    _, literal = measured(N, n_log(3, 1, ["- 1: N?T"]), "N?T")
    assert literal["rows"][0]["cells"]["literal_sequon"] is True
    assert literal["summary"]["usable_checked_row_count"] == 1
    assert literal["status"] == "partial"
    sheet, expanded = measured(N, n_log(4, 1, ["- 1: NSS"]), "NßT", input_mapping=mapping(3))
    assert sheet["source_normalization"]["processed_sequence"] == "NSST"
    assert expanded["summary"]["original_symbol_count"] == 3
    assert expanded["summary"]["processed_symbol_count"] == 4
    assert expanded["supplied_protein_composition"]["symbol_counts"] == {"N": 1, "T": 1, "ß": 1}
    assert expanded["rows"][0]["cells"]["source_intervals"] is None
    assert sheet["mapping"]["reason"] == "unicode_uppercase_expansion"


def test_source_caps100_without_filling_native_sites_and_checks_only_a_bound():
    rows = [f"- {3 * index + 1}: NAT" for index in range(100)]
    sheet, result = measured(N, n_log(315, 105, rows, 5), "NAT" * 105)
    summary = result["summary"]
    assert summary["native_reported_total_count"] == 105
    assert summary["retained_printed_row_count"] == summary["usable_checked_row_count"] == len(result["rows"]) == 100
    assert summary["native_reported_remaining_count"] == summary["unretained_reported_row_count"] == 5
    assert summary["native_log_complete"] is True and summary["native_report_complete"] is False
    assert summary["scan_exhaustiveness_verified"] is False
    assert max(row["native_values"]["position_1based"] for row in result["rows"]) == 298
    assert sheet["inputs"]["native_log"].endswith("... and 5 more")
    _, truncated = measured(N, n_log(315, 105, rows), "NAT" * 105)
    assert truncated["summary"]["usable_checked_row_count"] == 100
    assert truncated["summary"]["native_reported_remaining_count"] is None
    assert truncated["summary"]["native_log_complete"] is False
    # No scan is used to discover omitted positions. Only an impossible total
    # above the simple length bound can be rejected from this same shown log.
    _, impossible = measured(N, n_log(300, 105, rows, 5), "NAT" * 100)
    assert impossible["summary"]["native_total_operand_upper_bound"] == 100
    assert impossible["summary"]["native_total_within_operand_upper_bound"] is False
    assert impossible["summary"]["native_log_complete"] is False


def test_malformed_duplicate_and_disordered_rows_preserve_every_original_ordinal():
    log = n_log(6, 4, ["- 1: NAT", "- malformed", "- 1: NAT", "- 4: NAT"])
    sheet, result = measured(N, log, "NATNAT")
    assert [row["row_ordinal"] for row in result["rows"]] == [0, 1, 2, 3]
    assert [row["native_line"] for row in result["rows"]] == ["- 1: NAT", "- malformed", "- 1: NAT", "- 4: NAT"]
    assert result["rows"][1]["native_values"] is None
    assert result["rows"][2]["cells"]["order_compatible"] is None
    assert result["rows"][3]["cells"]["literal_sequon"] is True
    assert result["summary"]["malformed_row_count"] == 1
    assert result["summary"]["usable_checked_row_count"] == 2
    assert sheet["inputs"]["native_log"] == log
    _, disorder = measured(N, n_log(6, 2, ["- 4: NAT", "- 1: NAT"]), "NATNAT")
    assert disorder["rows"][1]["cells"]["order_compatible"] is False


def test_finite_out_of_domain_thresholds_are_source_arithmetic_not_native_rejections():
    sheet, high = measured(O, o_log(1, 0, threshold=2), "S", {"min_st_fraction": 2})
    assert sheet["parameters"]["effective"]["min_st_fraction"] == 2
    assert high["summary"]["native_reported_total_count"] == 0
    assert high["summary"]["native_report_complete"] is True
    assert any(row["code"] == "glycosylation_threshold_outside_documented_domain" for row in high["issues"])
    _, low = measured(O, o_log(1, 1, ["- pos 1 (S): S/T fraction=1.0 in window 1-1"], threshold=-1),
        "S", {"min_st_fraction": -1})
    assert low["rows"][0]["cells"]["unrounded_threshold_satisfied"] is True


@pytest.mark.parametrize("parameters", [{"allow_overlap": 1}, {"allow_overlap": None}, {"unknown": True}])
def test_incompatible_parameters_retain_native_counts_and_independent_literal_work(parameters):
    sheet, result = measured(N, n_log(3, 1, ["- 1: NAT"]), "NAT", parameters)
    assert sheet["parameters"]["supplied"] == parameters
    assert sheet["parameters"]["compatible"] is False
    assert result["summary"]["native_reported_total_count"] == 1
    assert result["rows"][0]["cells"]["literal_sequon"] is True
    assert result["summary"]["native_report_complete"] is False


def test_native_header_window_nonfinite_display_and_mapping_conflicts_remain_partial():
    log = o_log(3, 1, ["- pos 2 (S): S/T fraction=nan in window 1-3"])
    sheet, result = measured(O, log, "ASA", {"window": True}, input_mapping={"bad": "mapping"})
    assert sheet["parameters"]["effective"]["window"] is None
    assert result["rows"][0]["native_values"]["st_fraction"] is None
    assert result["rows"][0]["native_values"]["st_fraction_token"] == "nan"
    assert result["rows"][0]["cells"]["calculated_st_fraction"] == 1 / 3
    assert sheet["mapping"]["available"] is False
    assert result["summary"]["native_report_complete"] is False
    json.dumps(result, allow_nan=False)
    _, duplicate_header = measured(N, n_log(3, 1, ["- 1: NAT"]).replace(
        "Total sequons found: 1", "Total sequons found: 1\nTotal sequons found: 1"), "NAT")
    assert duplicate_header["summary"]["native_reported_total_count"] is None
    assert duplicate_header["summary"]["usable_checked_row_count"] == 1
    _, wrong_window = measured(O, o_log(3, 1, ["- pos 2 (S): S/T fraction=0.5 in window 1-2"], window=3),
        "ASA", {"window": 3})
    cells = wrong_window["rows"][0]["cells"]
    assert cells["native_window_interval"] == [0, 2] and cells["expected_clipped_window_interval"] == [0, 3]
    assert cells["st_count"] == 1 and cells["window_denominator_symbols"] == 2
    assert cells["calculated_st_fraction"] == .5
    assert cells["window_matches_source_clipping"] is False
    assert wrong_window["summary"]["usable_checked_row_count"] == 0


def test_saved_recalculation_is_pure_and_corrupt_cells_are_not_repaired(monkeypatch):
    import builtins
    import socket
    import subprocess
    sheet, expected = measured(O, o_log(3, 1, ["- pos 2 (S): S/T fraction=0.333 in window 1-3"],
        window=3, threshold=.3333), "ASA", {"window": 3, "min_st_fraction": .3333})
    saved = json.loads(json.dumps(sheet));before = deepcopy(saved)

    def forbidden(*args, **kwargs):
        raise AssertionError("saved glycosylation calculation attempted external work")

    with monkeypatch.context() as guarded:
        guarded.setattr(builtins, "open", forbidden)
        guarded.setattr(Path, "read_bytes", forbidden)
        guarded.setattr(socket, "socket", forbidden)
        guarded.setattr(subprocess, "Popen", forbidden)
        actual = calculate_glycosylation_components(saved)
    assert actual == expected and saved == before
    broken = deepcopy(saved);broken["rows"][0]["cells"]["st_count"] = 999
    with pytest.raises(ValueError, match="glycosylation_saved_sheet_conflict:/rows/0/cells/st_count"):
        calculate_glycosylation_components(broken)
    assert broken["rows"][0]["cells"]["st_count"] == 999 and saved == before
    with pytest.raises(ValueError, match="glycosylation_finite_json_required:/parameters/min_st_fraction"):
        build_glycosylation_sheet(O, None, sequence="S", parameters={"min_st_fraction": float("nan")})


def test_genuine_whole_glyco_module_outputs_feed_the_same_numerical_authority():
    if os.environ.get("HMMER_NATIVE_ORACLE_GLYCOSYLATION") != "1":
        pytest.skip("explicit bounded whole genuine glyco module verification only")
    source = Path(os.environ["HMMER_NATIVE_ORACLE_GLYCOSYLATION_SOURCE"]).resolve(strict=True)
    raw = source.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA256
    name = "_selected_whole_glycoengineering"
    previous, bytecode = sys.modules.get(name), sys.dont_write_bytecode
    capture = {"schema": "glycosylation_whole_source_verification_v1",
        "qualification": "genuine selected whole-module controls; no production installation, public operation, transport or child-return proof",
        "source_file": {"path": str(source), "sha256": SOURCE_SHA256, "size_bytes": len(raw)},
        "runtime": {"executable": str(Path(sys.executable).resolve()), "version": sys.version},
        "module_load": "not_started", "observed_callables": [], "cases": []}
    verification_error = None
    try:
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location(name, source)
        whole = importlib.util.module_from_spec(spec)
        sys.modules[name] = whole
        capture["module_load"] = "loading"
        spec.loader.exec_module(whole)
        capture["module_load"] = "loaded"
        callable_pins = {N: "d574294b1088dfb22b6f4242cc0c94b17de4999e86330e07620a83a0b4754c61",
            O: "dac5fa5bd182e0f7d4154ad72289c9adae173864e07e6392ae32d1e1102b2ca6"}
        for operation, pin in callable_pins.items():
            function = getattr(whole, operation)
            assert Path(function.__code__.co_filename).resolve() == source
            observed_pin = hashlib.sha256(inspect.getsource(function).rstrip("\n").encode()).hexdigest()
            assert observed_pin == pin
            capture["observed_callables"].append({"name": function.__name__, "module": function.__module__,
                "code_filename": function.__code__.co_filename, "sha256": observed_pin})
        controls = [("n_default", N, "NNST", {}), ("n_overlap", N, "NNST", {"allow_overlap": True}),
            ("n_empty", N, "", {}), ("n_null", N, None, {}), ("n_literal", N, "N?T", {}),
            ("n_unicode", N, "NßT", {}), ("n_capped", N, "NAT" * 105, {}),
            ("o_clipped", O, "STP", {}), ("o_fallback", O, "STP", {"window": 2}),
            ("o_rounding_pass", O, "ASA", {"window": 3, "min_st_fraction": .3333}),
            ("o_rounding_fail", O, "ASA", {"window": 3, "min_st_fraction": .3334}),
            ("o_outside_domain", O, "S", {"min_st_fraction": 2}),
            ("o_unicode", O, "ß", {}), ("o_native_error", O, "SSSS", {"window": 3.5})]
        for label, operation, sequence, parameters in controls:
            row = {"case": label, "operation": operation, "sequence": sequence,
                "parameters": parameters, "native_log": None, "native_error": None}
            capture["cases"].append(row)
            try:
                row["native_log"] = getattr(whole, operation)(sequence, **parameters)
            except Exception as error:
                row["native_error"] = {"exception_type": type(error).__name__, "message": str(error),
                    "traceback": traceback.format_exc()}
            supplied_mapping = mapping(len(sequence)) if type(sequence) is str and sequence else None
            row["sheet"], row["components"] = measured(operation, row["native_log"], sequence, parameters,
                native_outcome="failed" if row["native_error"] is not None else "completed",
                input_ref="supplied:explicit-control", input_mapping=supplied_mapping)
            assert row["sheet"]["inputs"]["native_log"] == row["native_log"]
            assert row["sheet"]["inputs"]["sequence"] == sequence
        by = {row["case"]: row for row in capture["cases"]}
        assert by["n_default"]["components"]["summary"]["native_reported_total_count"] == 1
        assert by["n_overlap"]["components"]["summary"]["usable_checked_row_count"] == 2
        assert by["n_capped"]["components"]["summary"]["native_reported_total_count"] == 105
        assert by["n_capped"]["components"]["summary"]["retained_printed_row_count"] == 100
        assert by["n_capped"]["components"]["summary"]["native_log_complete"] is True
        assert by["n_capped"]["components"]["summary"]["native_report_complete"] is False
        assert by["n_unicode"]["sheet"]["mapping"]["reason"] == "unicode_uppercase_expansion"
        assert by["n_literal"]["components"]["summary"]["usable_checked_row_count"] == 1
        assert by["n_empty"]["components"]["summary"]["native_report_complete"] is True
        assert by["n_null"]["components"]["summary"]["original_symbol_count"] is None
        assert by["o_clipped"]["components"]["rows"][0]["cells"]["calculated_st_fraction"] == 2 / 3
        assert by["o_fallback"]["sheet"]["parameters"]["effective"]["window"] == 7
        assert by["o_rounding_pass"]["components"]["rows"][0]["native_values"]["st_fraction"] == .333
        assert by["o_rounding_fail"]["components"]["summary"]["native_reported_total_count"] == 0
        assert by["o_outside_domain"]["components"]["summary"]["native_reported_total_count"] == 0
        assert by["o_unicode"]["components"]["summary"]["usable_checked_row_count"] == 2
        assert by["o_native_error"]["native_error"]["exception_type"] == "TypeError"
        assert by["o_native_error"]["components"]["summary"]["native_reported_total_count"] is None
        assert all(row["components"]["summary"]["scan_exhaustiveness_verified"] is False for row in capture["cases"])
    except BaseException as error:
        verification_error = {"exception_type": type(error).__name__, "message": str(error),
            "traceback": traceback.format_exc()}
        raise
    finally:
        sys.dont_write_bytecode = bytecode
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
        capture["verification_error"] = verification_error
        (Path(os.environ["HMMER529_ATTEMPT"]) / "glycosylation-whole-source.json").write_text(
            json.dumps(capture, allow_nan=False, indent=2))
