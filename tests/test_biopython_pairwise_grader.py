"""Native tiny pairwise runs and explicitly synthetic malformed/geometry cases."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.biopython_pairwise_grader import (
    build_biopython_pairwise_sheet,
    calculate_biopython_pairwise_scores,
    grade_biopython_pairwise,
)
from gene_annotation_episode.sequence_ops import align_pair, compare_sites


def synthetic_gapped_result():
    """Hand-checkable columns; the declared score is a synthetic native fixture."""
    return {"aligned": True, "native_score": 17.5, "query_length": 10,
        "reference_length": 12, "mode": "local", "matrix": "BLOSUM62",
        "gap_open": -2, "gap_extend": -0.5, "biopython_version": "synthetic",
        "paired_positions": 5, "identical_positions": 4, "identity_fraction": 4/5,
        "query_coverage": 6/10, "reference_coverage": 6/12,
        "query_interval": [1, 7], "reference_interval": [3, 9],
        "coordinates": [[1, 4, 4, 5, 6, 7], [3, 6, 7, 8, 8, 9]],
        "aligned_query": "ACD-EFG", "aligned_reference": "ACTVE-G",
        "extra_native_metadata": {"retained": ["complete", 9]}}


def issue_codes(sheet):
    return {issue["code"] for issue in sheet["issues"]}


def test_hand_checked_substitution_both_gap_axes_and_unaligned_flanks():
    native = synthetic_gapped_result()
    result = grade_biopython_pairwise(native, molecule="protein")
    sheet, scores = result["sheet"], result["scores"]
    assert sheet["native_result"] == native
    assert sheet["status"] == "complete" and sheet["issues"] == []
    assert sheet["measured_column_counts"] == {"alignment_columns": 7,
        "paired_positions": 5, "identical_positions": 4, "substituted_positions": 1,
        "query_gap_columns": 1, "reference_gap_columns": 1,
        "query_aligned_positions": 6, "reference_aligned_positions": 6}
    assert scores["paired_identity"] == 4/5
    assert scores["alignment_identity"] == 4/7
    assert scores["query_paired_coverage"] == 5/10
    assert scores["reference_paired_coverage"] == 5/12
    assert scores["query_aligned_coverage"] == 6/10
    assert scores["reference_aligned_coverage"] == 6/12
    assert scores["native_score"] == 17.5
    assert scores["denominators"] == {"paired_identity": 5, "alignment_identity": 7,
        "query_paired_coverage": 10, "reference_paired_coverage": 12,
        "query_aligned_coverage": 10, "reference_aligned_coverage": 12}
    assert [(row["query_position"], row["reference_position"], row["relationship"])
            for row in sheet["residue_correspondence"]] == [
        (1, 3, "identical"), (2, 4, "identical"), (3, 5, "substituted"),
        (None, 6, "query_gap"), (4, 7, "identical"), (5, None, "reference_gap"), (6, 8, "identical")]
    assert sheet["geometry"]["coordinate_system"] == "zero_based_half_open"
    assert sheet["geometry"]["query_interval"] == [1, 7]
    assert len(scores["definitions"]) == 15
    assert not any(key in scores for key in ("evalue", "confidence", "combined_score"))


@pytest.mark.parametrize("molecule,query,reference,mode,options,expected", [
    ("dna", "ACGTT", "ACTT", "global", {"gap_open": -2}, (5, 4, 4, 1, 1, 6)),
    ("dna", "GGACGTCC", "TTACGTAA", "local", {}, (4, 4, 4, .5, .5, 8)),
    ("rna", "AUGC", "AUAC", "global", {}, (4, 4, 3, 1, 1, 5)),
    ("rna", "GGAUGCCC", "AAAUGCUU", "local", {}, (4, 4, 4, .5, .5, 8)),
    ("protein", "ACDE", "ACE", "global", {"gap_open": -2}, (4, 3, 3, 1, 1, 16)),
    ("protein", "WWACDEWW", "GGACDEGG", "local", {}, (4, 4, 4, .5, .5, 24)),
])
def test_real_tiny_native_local_and_global_modes(molecule, query, reference, mode, options, expected):
    native = align_pair(query, reference, molecule=molecule, mode=mode, **options)
    result = grade_biopython_pairwise(native, molecule=molecule)
    sheet, scores = result["sheet"], result["scores"]
    columns, pairs, identical, qcoverage, rcoverage, score = expected
    assert sheet["molecule"] == molecule and sheet["mode"] == mode
    assert sheet["native_result"] == native and sheet["issues"] == []
    assert scores["alignment_columns"] == columns
    assert scores["paired_positions"] == pairs and scores["identical_positions"] == identical
    assert scores["query_aligned_coverage"] == qcoverage
    assert scores["reference_aligned_coverage"] == rcoverage
    assert scores["query_paired_coverage"] == pairs/len(query)
    assert scores["reference_paired_coverage"] == pairs/len(reference)
    assert scores["native_score"] == score
    # Verify the same selected reference sites as the existing native consumer.
    selected = compare_sites(native, list(range(len(reference))))
    for row in sheet["residue_correspondence"]:
        if row["reference_position"] is not None:
            site = selected[row["reference_position"]]
            assert site["query_position"] == row["query_position"]
            assert site["reference_residue"] == row["reference_symbol"]
            assert site["query_residue"] == row["query_symbol"]
    if molecule == "rna":
        assert "U" not in sheet["traceback"]["query"]
        assert sheet["symbol_interpretation"]["native_nucleotide_normalization"] == "U_to_T_before_alignment"


def test_real_zero_pair_global_alignment_does_not_invent_paired_identity():
    native = align_pair("A", "C", molecule="dna", mode="global", gap_open=-.1, gap_extend=-.1)
    result = grade_biopython_pairwise(native, molecule="dna")
    assert result["sheet"]["issues"] == []
    assert "identity_fraction" not in native
    assert result["sheet"]["reported_measurements"]["identity_fraction"] is None
    scores = result["scores"]
    assert scores["alignment_columns"] == 2 and scores["paired_positions"] == 0
    assert scores["paired_identity"] is None and scores["alignment_identity"] == 0
    assert scores["query_paired_coverage"] == 0 and scores["query_aligned_coverage"] == 1
    assert scores["native_score"] == pytest.approx(-.2)


def test_real_no_alignment_has_zero_positions_but_unknown_native_score_and_identity():
    native = align_pair("AAA", "CCC", molecule="dna", mode="local")
    result = grade_biopython_pairwise(native, molecule="dna")
    sheet, scores = result["sheet"], result["scores"]
    assert native["aligned"] is False and sheet["status"] == "no_alignment"
    assert sheet["issues"] == []
    assert scores["alignment_columns"] == scores["paired_positions"] == 0
    assert scores["query_paired_coverage"] == scores["reference_aligned_coverage"] == 0
    assert scores["paired_identity"] is scores["alignment_identity"] is scores["native_score"] is None
    assert sheet["native_parameters"]["gap_open"] == -10.0


def test_missing_traceback_is_not_a_zero_alignment_even_with_reported_counts():
    native = synthetic_gapped_result()
    del native["aligned_query"], native["aligned_reference"]
    result = grade_biopython_pairwise(native, molecule="protein")
    assert result["sheet"]["status"] == "alignment_data_unavailable"
    assert result["sheet"]["reported_measurements"]["paired_positions"] == 5
    assert result["scores"]["paired_positions"] is None
    assert result["scores"]["query_paired_coverage"] is None
    assert result["scores"]["native_score"] == 17.5


@pytest.mark.parametrize("changes,code", [
    ({"coordinates": None}, "coordinate_path_missing"),
    ({"coordinates": [[1, 7], [3, True]]}, "coordinate_path_invalid"),
    ({"coordinates": [[1, 7], [3]]}, "coordinate_path_invalid"),
    ({"coordinates": [[7, 1], [3, 9]]}, "coordinate_step_invalid"),
    ({"coordinates": [[1, 4, 4, 7], [3, 6, 6, 9]]}, "coordinate_step_invalid"),
    ({"coordinates": [[1, 7], [3, 8]]}, "coordinate_step_invalid"),
    ({"coordinates": [[1, 7], [3, 9]]}, "coordinate_traceback_length_conflict"),
    ({"coordinates": [[1, 3, 3, 5, 6, 7], [3, 5, 6, 8, 8, 9]]}, "coordinate_traceback_gap_conflict"),
    ({"query_interval": [2, 8]}, "coordinate_interval_conflict"),
    ({"query_interval": None}, "alignment_interval_invalid"),
    ({"query_length": 6}, "coordinates_outside_operand"),
    ({"mode": "global"}, "global_alignment_operand_span_conflict"),
])
def test_invalid_geometry_preserves_string_measurements_but_not_coverage(changes, code):
    native = synthetic_gapped_result()
    native.update(changes)
    result = grade_biopython_pairwise(native, molecule="protein")
    assert code in issue_codes(result["sheet"])
    assert result["sheet"]["status"] == "partial"
    assert result["sheet"]["residue_correspondence"] == []
    assert not result["sheet"]["geometry"]["available"]
    assert result["scores"]["paired_positions"] == 5
    assert result["scores"]["paired_identity"] == 4/5
    assert all(result["scores"][field] is None for field in (
        "query_paired_coverage", "reference_paired_coverage", "query_aligned_coverage", "reference_aligned_coverage"))


@pytest.mark.parametrize("changes,code", [
    ({"aligned_query": "AC", "aligned_reference": "ACD"}, "traceback_strings_invalid"),
    ({"aligned_query": "A-C", "aligned_reference": "A-C"}, "double_gap_alignment_column"),
    ({"aligned_query": "A C", "aligned_reference": "ACC"}, "traceback_strings_invalid"),
    ({"aligned_query": "", "aligned_reference": ""}, "traceback_strings_invalid"),
    ({"aligned_query": None}, "traceback_strings_invalid"),
])
def test_malformed_strings_preserve_native_fields_without_fabricating_counts(changes, code):
    native = synthetic_gapped_result()
    native.update(changes)
    result = grade_biopython_pairwise(native, molecule="protein")
    assert code in issue_codes(result["sheet"])
    assert result["sheet"]["native_result"] == native
    assert result["scores"]["alignment_columns"] is None
    assert result["scores"]["paired_identity"] is None


def test_reported_counts_and_fractions_are_not_silently_substituted_for_traceback():
    native = synthetic_gapped_result()
    native.update(paired_positions=20, identical_positions=21, identity_fraction=.2, query_coverage=.1)
    result = grade_biopython_pairwise(native, molecule="protein")
    sheet, scores = result["sheet"], result["scores"]
    assert sheet["reported_measurements"]["identical_positions"] == 21
    assert scores["identical_positions"] == 4
    assert scores["paired_identity"] == .8 and scores["query_aligned_coverage"] == .6
    assert {"reported_count_traceback_conflict", "reported_fraction_traceback_conflict",
            "reported_identity_exceeds_paired_positions"} <= issue_codes(sheet)


@pytest.mark.parametrize("field,value", [("native_score", "17.5"), ("native_score", True),
    ("paired_positions", -1), ("paired_positions", 5.0), ("identity_fraction", 2), ("gap_open", "-2")])
def test_invalid_finite_measurement_does_not_erase_unrelated_valid_data(field, value):
    native = synthetic_gapped_result()
    native[field] = value
    result = grade_biopython_pairwise(native, molecule="protein")
    assert result["sheet"]["native_result"][field] == value
    assert {"code": "measurement_invalid", "field": field} in result["sheet"]["issues"]
    assert result["scores"]["query_paired_coverage"] == .5
    if field == "native_score":
        assert result["scores"]["native_score"] is None
    json.dumps(result, allow_nan=False)


def test_missing_operand_length_keeps_mapping_and_other_operand_coverage():
    native = synthetic_gapped_result()
    del native["query_length"]
    result = grade_biopython_pairwise(native, molecule="protein")
    assert result["sheet"]["geometry"]["available"]
    assert result["sheet"]["geometry"]["operand_bounds_checked"] == {"query": False, "reference": True}
    assert result["scores"]["query_aligned_coverage"] is None
    assert result["scores"]["reference_aligned_coverage"] == .5
    assert result["scores"]["denominators"]["query_paired_coverage"] is None


def test_literal_case_normalization_does_not_resolve_ambiguity_symbols():
    native = align_pair("ANN", "ANA", molecule="dna", mode="global")
    native["aligned_query"] = native["aligned_query"].lower()
    result = grade_biopython_pairwise(native, molecule="dna")
    assert result["scores"]["identical_positions"] == 2
    assert result["scores"]["substituted_positions"] == 1
    assert result["scores"]["paired_identity"] == 2/3
    assert result["sheet"]["native_result"]["aligned_query"] == "ann"
    assert result["sheet"]["traceback"]["query"] == "ANN"


@pytest.mark.parametrize("score", [0, -3.5, 10**400])
def test_native_scores_keep_zero_sign_and_integer_precision(score):
    native = synthetic_gapped_result()
    native["native_score"] = score
    result = grade_biopython_pairwise(native, molecule="protein")
    assert result["scores"]["native_score"] == score
    assert result["sheet"]["issues"] == []
    json.dumps(result, allow_nan=False)


def test_false_alignment_flag_with_alignment_data_does_not_manufacture_zero():
    native = synthetic_gapped_result()
    native["aligned"] = False
    result = grade_biopython_pairwise(native, molecule="protein")
    assert result["sheet"]["alignment_state"] == "conflicting"
    assert "no_alignment_has_alignment_data" in issue_codes(result["sheet"])
    assert result["scores"]["paired_positions"] is None
    assert result["scores"]["query_aligned_coverage"] is None


def test_zero_length_denominators_remain_null_for_explicit_empty_fixture():
    native = {"aligned": False, "query_length": 0, "reference_length": 0,
              "mode": "local", "matrix": "match_2_mismatch_minus_1"}
    # align_pair rejects empty inputs: this is an explicit synthetic boundary case.
    result = grade_biopython_pairwise(native, molecule="dna")
    assert result["scores"]["alignment_columns"] == 0
    assert result["scores"]["query_aligned_coverage"] is None
    assert result["scores"]["paired_identity"] is None


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), {1, 2}, (1, 2)])
def test_nonfinite_or_non_json_native_input_is_rejected_not_lossily_rewritten(value):
    native = synthetic_gapped_result()
    native["extra_native_metadata"] = value
    with pytest.raises(ValueError, match="finite_json_biopython_pairwise_native_required"):
        build_biopython_pairwise_sheet(native, molecule="protein")


@pytest.mark.parametrize("native,molecule,code", [
    ([], "dna", "biopython_pairwise_native_object_required"),
    ({"aligned": True, "mode": "local"}, "unspecified", "biopython_pairwise_molecule_required"),
    ({"mode": "local"}, "dna", "biopython_pairwise_aligned_boolean_required"),
    ({"aligned": 1, "mode": "local"}, "dna", "biopython_pairwise_aligned_boolean_required"),
    ({"aligned": True, "mode": "overlap"}, "dna", "biopython_pairwise_mode_required"),
])
def test_top_level_contract_errors_are_specific(native, molecule, code):
    with pytest.raises(ValueError, match=code):
        build_biopython_pairwise_sheet(native, molecule=molecule)


def test_saved_sheet_recalculation_and_both_public_functions_do_not_mutate(tmp_path, monkeypatch):
    native = synthetic_gapped_result()
    before = deepcopy(native)
    result = grade_biopython_pairwise(native, molecule="protein")
    assert native == before
    path = tmp_path / "sheet.json"
    path.write_text(json.dumps(result["sheet"], allow_nan=False))
    saved = json.loads(path.read_text())
    original_sheet = deepcopy(saved)
    from gene_annotation_episode import sequence_ops
    def forbidden(*args, **kwargs):
        raise AssertionError("saved-sheet calculation must not execute an alignment")
    monkeypatch.setattr(sequence_ops, "align_pair", forbidden)
    assert calculate_biopython_pairwise_scores(saved) == result["scores"]
    assert saved == original_sheet
    result["sheet"]["native_result"]["extra_native_metadata"]["retained"].append("changed")
    result["scores"]["definitions"]["paired_identity"]["formula"] = "changed"
    assert native == before
    assert calculate_biopython_pairwise_scores(saved)["definitions"]["paired_identity"]["formula"] != "changed"


@pytest.mark.parametrize("change", ["count", "mapping", "coordinates", "length", "native_score"])
def test_calculator_rejects_corrupted_saved_components(change):
    sheet = build_biopython_pairwise_sheet(synthetic_gapped_result(), molecule="protein")
    if change == "count":
        sheet["measured_column_counts"]["identical_positions"] = 50
    elif change == "mapping":
        sheet["residue_correspondence"][0]["reference_position"] = 11
    elif change == "coordinates":
        sheet["geometry"]["coordinates"][0][0] = 2
    elif change == "length":
        sheet["lengths"]["query"] = 3
    else:
        sheet["native_score"] = "17.5"
    with pytest.raises(ValueError, match="biopython_pairwise_sheet_components_invalid"):
        calculate_biopython_pairwise_scores(sheet)


def test_retained_native_examples_recalculate_without_native_execution():
    directory = Path(__file__).parents[1] / "verification/tool_graders_batch_001/biopython_pairwise"
    examples = json.loads((directory / "native_examples.json").read_text())
    filled = json.loads((directory / "filled_examples.json").read_text())
    assert len(examples) == len(filled) == 8
    for source, saved in zip(examples, filled):
        assert source["name"] == saved["name"]
        assert grade_biopython_pairwise(source["native"], molecule=source["arguments"]["molecule"]) == saved["grading"]
        assert calculate_biopython_pairwise_scores(saved["grading"]["sheet"]) == saved["grading"]["scores"]
