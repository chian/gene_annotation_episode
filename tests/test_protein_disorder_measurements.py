"""Supplied-data controls; engineered whole-wrapper controls require bounded529.

Engineered score strings test postprocessing, not IUPred scientific execution.
"""
from copy import deepcopy
import csv
import hashlib
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path
import sys
import traceback

import pytest

from gene_annotation_episode.protein_disorder_measurements import (
    SOURCE_SHA256, CALLABLE_SHA256, build_disorder_sheet, calculate_disorder_components,
)
from gene_annotation_episode.sequence_mapping import VERSION as MAPPING_VERSION


def csv_text(rows):
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["Position", "Amino_Acid", "Disorder_Score", "Is_Disordered"])
    writer.writerows(rows)
    return buffer.getvalue()


def log_text(count, hits, percent, regions, threshold=.5):
    # Explicit source-format fixture strings, not an invoked prediction.
    lines = ["", "Intrinsically Disordered Region (IDR) Prediction Research Log:",
        "=============================================================", "Analysis performed using IUPred2A algorithm (long disorder mode)",
        f"Protein sequence length: {count} amino acids", f"Disorder threshold: {threshold}", "",
        "Results Summary:", f"- {hits} residues ({percent}%) predicted as disordered",
        f"- {len(regions)} distinct disordered regions identified", "", "Disordered Regions:"]
    lines.extend([f"- Region {start}-{end} (length: {end-start+1} residues)" for start, end in regions]
        if regions else ["- No significant disordered regions found"])
    return "\n".join([*lines, "", "Detailed per-residue scores saved to: explicit-control.csv"])


def measured(response=None, *, sequence="ACDE", threshold=.5, table=None, log=None, **kwargs):
    sheet = build_disorder_sheet(table, protein_sequence=sequence, threshold=threshold,
        native_response=response, native_log=log, **kwargs)
    return sheet, calculate_disorder_components(sheet)


def mapping(length):
    return {"version": MAPPING_VERSION, "units_per_symbol": 1, "symbol_length": length,
        "path": [{"subject_ref": "source:explicit-original-characters", "start": 100,
            "end": 100 + length, "unit": "aa", "strand": "+"}]}


def test_cleaning_case_native_denominator_singletons_and_explicit_mapping():
    response = "# engineered score control\n1 A 0.5\n2 C 0.8\n3 D 0.1\n4 E 0.9\n"
    table = csv_text([(1, "A", "0.5", "Yes"), (2, "C", "0.8", "Yes"),
        (3, "D", "0.1", "No"), (4, "E", "0.9", "Yes")])
    original = " A-c\nD2E"
    sheet, result = measured(response, sequence=original, table=table,
        log=log_text(4, 3, "75.00", [(1, 2)]), input_mapping=mapping(len(original)))
    assert sheet["cleaning"]["cleaned_sequence"] == "AcDE"
    assert sheet["cleaning"]["original_character_indices"] == [1, 3, 5, 7]
    assert sheet["inputs"]["protein_sequence"] == original
    assert result["response_csv_join"]["state"] == "compatible"
    assert result["rows"][1]["cells"]["exact_case_match"] is False
    assert result["rows"][1]["cells"]["ascii_case_compatible"] is True
    assert result["rows"][1]["cells"]["source_intervals"] == [
        {"subject_ref": "source:explicit-original-characters", "start": 103, "end": 104, "unit": "aa", "strand": "+"}]
    source = result["source_equivalent"]
    assert source["parsed_row_denominator"] == 4 and source["thresholded_row_count"] == 3
    assert source["disordered_percentage"] == 75 and source["expected_percentage_display"] == "75.00"
    region, = source["regions"]
    assert region["member_row_ordinals"] == [0, 1]
    assert region["cleaned_interval"] == [0, 2]
    assert region["original_character_intervals"] == [[1, 2], [3, 4]]
    assert [(row["start"], row["end"]) for row in region["source_intervals"]] == [(101, 102), (103, 104)]
    assert result["summary"]["descriptive_score_sum"] == pytest.approx(2.3)
    assert result["summary"]["descriptive_mean_denominator_rows"] == 4
    assert result["summary"]["descriptive_mean_score"] == pytest.approx(.575)
    assert result["summary"]["unique_input_coverage"] == 1
    assert all(value is True for value in result["log_checks"].values())


def test_duplicate_occurrences_stay_in_means_but_unique_coverage_has_own_denominator():
    _, result = measured("1 A .2\n1 A .8\n2 C .9", sequence="AC",
        log=log_text(3, 2, "66.67", [(1, 2)]))
    assert [row["native_values"]["position_1based"] for row in result["rows"]] == [1, 1, 2]
    assert result["summary"]["source_parsed_row_count"] == 3
    assert result["summary"]["descriptive_mean_denominator_rows"] == 3
    assert result["summary"]["descriptive_score_sum"] == pytest.approx(1.9)
    assert result["summary"]["descriptive_mean_score"] == pytest.approx(1.9 / 3)
    assert result["summary"]["unique_usable_input_position_count"] == 2
    assert result["summary"]["input_coverage_denominator_symbols"] == 2
    assert result["summary"]["duplicate_native_position_count"] == 1
    assert result["summary"]["duplicate_native_position_occurrence_count"] == 2
    assert result["rows"][0]["cells"]["conflicting_native_position"] is True
    assert result["source_equivalent"]["regions"][0]["member_row_ordinals"] == [1, 2]
    _, overlap = measured("1 A .8\n2 C .8\n2 C .8\n3 D .8", sequence="ACD")
    assert [(row["start_1based"], row["end_1based"]) for row in overlap["source_equivalent"]["regions"]] == [(1, 2), (2, 3)]


def test_unsorted_native_positions_are_not_sorted_into_another_region():
    _, result = measured("3 D .8\n1 A .7\n2 C .9", sequence="ACD")
    assert [row["native_values"]["position_1based"] for row in result["rows"]] == [3, 1, 2]
    assert result["summary"]["unique_usable_input_positions_1based"] == [3, 1, 2]
    assert result["rows"][1]["cells"]["position_order_increasing"] is False
    assert [(row["start_1based"], row["end_1based"]) for row in result["source_equivalent"]["regions"]] == [(1, 2)]


def test_nonfinite_tokens_have_native_comparison_but_no_scientific_number_or_mean():
    response = "1 A NaN\n2 C +Infinity\n3 D -inf\n4 E 1.2\n5 F .8"
    table = csv_text([(1, "A", "nan", "No"), (2, "C", "inf", "Yes"),
        (3, "D", "-inf", "No"), (4, "E", "1.2", "Yes"), (5, "F", "0.8", "Yes")])
    _, result = measured(response, sequence="ACDEF", table=table)
    assert result["response_csv_join"]["state"] == "compatible"
    assert [row["cells"]["native_threshold_comparison"] for row in result["rows"]] == [False, True, False, True, True]
    assert [row["native_values"]["score"]["finite_value"] for row in result["rows"][:3]] == [None, None, None]
    assert result["rows"][0]["native_values"]["score"]["token"] == "NaN"
    assert result["rows"][3]["native_values"]["score"]["finite_value"] == 1.2
    assert result["source_equivalent"]["parsed_row_denominator"] == 5
    assert result["source_equivalent"]["thresholded_row_count"] == 3
    assert result["source_equivalent"]["disordered_percentage"] == 60
    assert [(r["start_1based"], r["end_1based"]) for r in result["source_equivalent"]["regions"]] == [(4, 5)]
    assert result["summary"]["descriptive_mean_denominator_rows"] == 1
    assert result["summary"]["descriptive_mean_score"] == .8
    assert result["summary"]["unique_input_coverage"] == .2
    json.dumps(result, allow_nan=False)


def test_skipped_response_rows_extra_tokens_and_bad_correspondence_are_retained():
    response = "# header\nbroken\n1 A .5 extra\nx C .6\n2 C nope\n0 D .8\n4 Z .9\n"
    sheet, result = measured(response, sequence="ACD")
    assert [row["row_ordinal"] for row in result["rows"]] == list(range(6))
    assert [row["source_parser_index"] for row in result["rows"]] == [None, 0, None, None, 1, 2]
    assert result["rows"][1]["raw_tokens"] == ["1", "A", ".5", "extra"]
    assert [row["line_ordinal"] for row in sheet["response"]["lines"]] == list(range(8))
    assert result["summary"]["source_parsed_row_count"] == 3
    assert result["source_equivalent"]["thresholded_row_count"] == 3
    assert result["source_equivalent"]["region_count"] == 0
    assert result["summary"]["descriptive_mean_denominator_rows"] == 1
    assert result["summary"]["descriptive_mean_score"] == .5
    assert result["rows"][4]["cells"]["input_correspondence"] is False


def test_csv_response_conflict_never_falls_back_or_changes_original_ordinals():
    table = csv_text([(1, "A", ".9", "Yes"), (2, "C", ".9", "Yes")])
    sheet, result = measured("01 A 5e-1\n2 C .6", sequence="AC", table=table)
    assert sheet["authority"] == "response"
    assert result["response_csv_join"]["state"] == "conflict"
    assert result["rows"][0]["native_values"]["score"]["finite_value"] == .5
    assert sheet["csv"]["rows"][0]["native_values"]["score"]["finite_value"] == .9
    assert result["summary"]["descriptive_mean_score"] == pytest.approx(.55)
    _, equivalent = measured("01 A 5e-1", sequence="A", table=csv_text([(1, "A", "0.5", "Yes")]))
    assert equivalent["response_csv_join"]["state"] == "compatible"
    _, case_conflict = measured("1 a .5", sequence="a", table=csv_text([(1, "A", "0.5", "Yes")]))
    assert case_conflict["response_csv_join"]["state"] == "conflict"


def test_partial_csv_preserves_usable_arithmetic_without_inventing_a_repaired_run():
    text = csv_text([(1, "A", ".8", "Yes")]) + "malformed\r\n" + "2,C,.9,Yes\r\n"
    sheet, result = measured(sequence="AC", table=text)
    assert result["authority"] == "csv" and len(result["rows"]) == 3
    assert result["rows"][1]["raw_tokens"] == ["malformed"]
    assert result["summary"]["source_parsed_row_count"] == 2
    assert result["summary"]["descriptive_mean_score"] == pytest.approx(.85)
    assert result["source_equivalent"]["stage"] == "retained_partial_csv_arithmetic"
    assert result["source_equivalent"]["regions"] is None
    assert result["source_equivalent"]["region_count"] is None
    broken = text + '3,"unterminated'
    partial, _ = measured(sequence="ACD", table=broken)
    assert partial["csv"]["parser_tail_complete"] is False
    assert partial["csv"]["rows"][-1]["raw_record"] == '3,"unterminated'
    assert sheet["inputs"]["native_csv"] == text


def test_missing_empty_early_return_unknown_threshold_and_out_of_domain_threshold():
    _, missing = measured(sequence=None, threshold=None)
    assert missing["summary"]["source_parsed_row_count"] is None
    assert missing["summary"]["cleaned_symbol_count"] is None
    sheet, empty = measured("# no scores\n", sequence="ACD", log="No valid prediction data was returned from the server.")
    assert empty["summary"]["source_parsed_row_count"] == 0
    assert empty["summary"]["cleaned_symbol_count"] == 3
    assert empty["source_equivalent"]["thresholded_row_count"] is None
    assert empty["source_equivalent"]["disordered_percentage"] is None
    assert empty["source_equivalent"]["regions"] is None
    assert sheet["status"] == "partial"
    _, header_only = measured(sequence="", table=csv_text([]))
    assert header_only["summary"]["source_parsed_row_count"] == 0
    assert header_only["source_equivalent"]["region_count"] is None
    assert header_only["summary"]["unique_input_coverage"] is None
    _, unknown = measured("1 A .8", sequence="A", threshold=None)
    assert unknown["source_equivalent"]["thresholded_row_count"] is None
    assert unknown["summary"]["descriptive_mean_score"] == .8
    _, outside = measured("1 A .8", sequence="A", threshold=2)
    assert outside["source_equivalent"]["thresholded_row_count"] == 0
    assert outside["source_equivalent"]["disordered_percentage"] == 0
    assert outside["source_equivalent"]["region_count"] == 0


def test_logged_counts_rounding_and_csv_flags_cannot_overwrite_calculated_values():
    table = csv_text([(1, "A", ".8", "No"), (2, "C", ".1", "No"), (3, "D", ".2", "No")])
    sheet, result = measured("1 A .8\n2 C .1\n3 D .2", sequence="ACD", table=table,
        log=log_text(3, 2, "66.67", [(1, 2)]))
    assert result["rows"][0]["reported_csv_flag_at_ordinal"] == "No"
    assert result["rows"][0]["cells"]["native_threshold_comparison"] is True
    assert result["rows"][0]["cells"]["native_csv_flag_matches_comparison"] is False
    assert result["source_equivalent"]["thresholded_row_count"] == 1
    assert result["source_equivalent"]["expected_percentage_display"] == "33.33"
    assert result["native_log"]["selected"]["disordered"]["count"] == 2
    assert result["log_checks"]["thresholded_count_matches"] is False
    assert result["log_checks"]["percentage_display_matches"] is False
    assert result["log_checks"]["regions_match"] is False
    assert sheet["inputs"]["native_log"].find("66.67") >= 0


def test_ambiguous_ascii_domain_and_fasta_like_cleaning_are_explicit_not_prediction_accuracy():
    sheet, result = measured("1 X .9", sequence="Xß-", input_mapping=mapping(3))
    assert sheet["cleaning"]["cleaned_sequence"] == "X"
    assert sheet["cleaning"]["original_character_indices"] == [0]
    assert result["summary"]["descriptive_mean_score"] == .9
    assert any(row["code"] == "protein_disorder_predictor_domain_unestablished" for row in result["issues"])
    fasta, _ = measured("1 p .6", sequence=">prot\nA")
    assert fasta["cleaning"]["cleaned_sequence"] == "protA"
    assert fasta["cleaning"]["original_character_indices"] == [1, 2, 3, 4, 6]


def test_saved_calculation_is_pure_and_corrupt_cells_reject_without_repair(monkeypatch):
    import builtins
    import socket
    import subprocess
    sheet, expected = measured("1 A .5\n2 C .8", sequence="AC")
    saved = json.loads(json.dumps(sheet));before = deepcopy(saved)

    def forbidden(*args, **kwargs):
        raise AssertionError("saved disorder calculation attempted external work")

    with monkeypatch.context() as guarded:
        guarded.setattr(builtins, "open", forbidden)
        guarded.setattr(Path, "read_bytes", forbidden)
        guarded.setattr(socket, "socket", forbidden)
        guarded.setattr(subprocess, "Popen", forbidden)
        actual = calculate_disorder_components(saved)
    assert actual == expected and saved == before
    corrupt = deepcopy(saved);corrupt["rows"][0]["cells"]["usable_for_descriptive_mean"] = False
    with pytest.raises(ValueError, match="protein_disorder_saved_sheet_conflict:/rows/0/cells/usable_for_descriptive_mean"):
        calculate_disorder_components(corrupt)
    assert corrupt["rows"][0]["cells"]["usable_for_descriptive_mean"] is False
    with pytest.raises(ValueError, match="protein_disorder_finite_json_required:/threshold"):
        measured("1 A .5", sequence="A", threshold=float("nan"))


