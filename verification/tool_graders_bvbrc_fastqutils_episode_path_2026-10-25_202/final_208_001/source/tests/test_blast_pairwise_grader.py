"""Synthetic arithmetic/geometry examples; these tests execute no BLAST job."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.blast_pairwise_grader import (
    alignment_components, build_pairwise_sheet,
)


def hsp(query="ACDE", reference="ACDE", **changes):
    row = {"bit_score": 18.5, "score": 40, "evalue": 0,
           "qseq": query, "hseq": reference, "align_len": len(query),
           "identity": sum(a == b and a != "-" for a, b in zip(query, reference)),
           "gaps": query.count("-") + reference.count("-"),
           "query_from": 1, "query_to": len(query.replace("-", "")),
           "hit_from": 1, "hit_to": len(reference.replace("-", ""))}
    row.update(changes)
    return row


def normalized(hsps, *, length=10, reference_length=10, program="blastp"):
    return {"schema": "blast_normalized_result_v1", "mode": "pairwise",
            "resource": "local", "format": "json2",
            "query": {"id": "synthetic_query", "title": None, "length": length},
            "search": {"program": program, "version": "synthetic",
                       "database": None, "parameters": {}, "statistics": {},
                       "request": {}, "hit_array_present": True, "reported_hit_count": 1},
            "hits": [{"hit_index": 0, "length": reference_length,
                      "descriptions": [{"accession": "synthetic_subject"}],
                      "unpaired_metadata": {}, "hsps": hsps}],
            "native": {}, "issues": []}


def codes(value):
    return {row["code"] for row in value["issues"]}


def test_gap_resolved_numerical_components_and_residue_correspondence():
    native = hsp("ACD-EFG", "ACTVE-G", query_from=2, query_to=7, hit_from=4, hit_to=9)
    value = alignment_components(native, program="blastp", query_length=10, reference_length=12)
    assert value["native_scores"] == {"bit_score": 18.5, "score": 40, "evalue": 0}
    assert value["counts"] == {"alignment_columns": 7, "paired_columns": 5,
        "identical_pairs": 4, "query_gap_columns": 1, "reference_gap_columns": 1,
        "paired_query_positions": 5, "paired_reference_positions": 5}
    assert value["fractions"] == {"query_paired_coverage": .5,
        "reference_paired_coverage": 5/12, "paired_identity": 4/5,
        "alignment_identity": 4/7}
    assert value["pairs"] == [
        {"query_start": 1, "query_end": 2, "reference_start": 3, "reference_end": 4, "identical": True},
        {"query_start": 2, "query_end": 3, "reference_start": 4, "reference_end": 5, "identical": True},
        {"query_start": 3, "query_end": 4, "reference_start": 5, "reference_end": 6, "identical": False},
        {"query_start": 4, "query_end": 5, "reference_start": 7, "reference_end": 8, "identical": True},
        {"query_start": 6, "query_end": 7, "reference_start": 8, "reference_end": 9, "identical": True}]
    assert value["geometry_available"] and value["traceback_available"]
    assert value["issues"] == []


def test_reverse_strand_nucleotide_coordinates_are_not_reversed_strings():
    native = hsp("AC-GT", "ATCGT", hit_from=9, hit_to=5, hit_strand="Minus")
    value = alignment_components(native, program="blastn", query_length=8, reference_length=12)
    assert [(p["query_start"], p["reference_start"]) for p in value["pairs"]] == [(0, 8), (1, 7), (2, 5), (3, 4)]
    assert value["counts"]["identical_pairs"] == 3
    assert value["fractions"]["query_paired_coverage"] == .5
    assert value["coordinate_units"] == {"query": "nt", "reference": "nt", "alignment": "nt"}


@pytest.mark.parametrize("reverse", [False, True])
def test_blastx_maps_aligned_amino_acids_to_original_query_codons(reverse):
    native = hsp("A-CD", "ATCD", query_from=11 if reverse else 2,
                 query_to=3 if reverse else 10, query_frame=-2 if reverse else 2)
    value = alignment_components(native, program="blastx", query_length=12, reference_length=8)
    expected = [(8, 11), (5, 8), (2, 5)] if reverse else [(1, 4), (4, 7), (7, 10)]
    assert [(p["query_start"], p["query_end"]) for p in value["pairs"]] == expected
    assert [p["reference_start"] for p in value["pairs"]] == [0, 2, 3]
    assert value["fractions"]["query_paired_coverage"] == .75
    assert value["fractions"]["reference_paired_coverage"] == 3/8
    assert value["counts"]["paired_columns"] == 3
    assert value["counts"]["paired_query_positions"] == 9
    assert value["issues"] == []


def test_tblastn_and_tblastx_use_original_units_for_each_operand():
    native = hsp("ACD", "ACD", query_from=2, query_to=4,
                 hit_from=11, hit_to=3, hit_frame=-2)
    value = alignment_components(native, program="tblastn", query_length=5, reference_length=12)
    assert value["fractions"]["query_paired_coverage"] == 3/5
    assert value["fractions"]["reference_paired_coverage"] == 9/12
    assert value["pairs"][0] == {"query_start": 1, "query_end": 2,
        "reference_start": 8, "reference_end": 11, "identical": True}
    native.update(query_from=3, query_to=11, query_frame=3, hit_from=13, hit_to=5, hit_frame=-3)
    value = alignment_components(native, program="tblastx", query_length=15, reference_length=15)
    assert value["pairs"][0] == {"query_start": 2, "query_end": 5,
        "reference_start": 10, "reference_end": 13, "identical": True}
    assert value["counts"]["paired_query_positions"] == value["counts"]["paired_reference_positions"] == 9
    assert value["issues"] == []


def test_reported_counts_survive_missing_traceback_without_fabricated_mapping():
    native = {"align_len": 10, "identity": 6, "gaps": 2, "bit_score": 20,
              "query_from": 1, "query_to": 10, "hit_from": 1, "hit_to": 10}
    value = alignment_components(native, program="blastp", query_length=20, reference_length=20)
    assert value["counts"]["paired_columns"] == 8
    assert value["fractions"]["paired_identity"] == .75
    assert value["fractions"]["alignment_identity"] == .6
    assert value["fractions"]["query_paired_coverage"] is None
    assert value["pairs"] == [] and not value["geometry_available"]
    assert "traceback_not_reported" in codes(value)


def test_missing_lengths_do_not_erase_known_residue_pairs():
    value = alignment_components(hsp(), program="blastp", query_length=None, reference_length=None)
    assert len(value["pairs"]) == 4 and value["geometry_available"]
    assert value["fractions"]["query_paired_coverage"] is None
    assert value["fractions"]["reference_paired_coverage"] is None
    assert value["fractions"]["paired_identity"] == 1


@pytest.mark.parametrize("changes,code", [
    ({"query_to": 9}, "traceback_coordinate_span_conflict"),
    ({"query_from": 8, "query_to": 11}, "coordinates_outside_operand"),
    ({"query_from": 4, "query_to": 1}, "reverse_protein_coordinates"),
    ({"query_from": True}, "invalid_integer"),
    ({"query_from": 0}, "invalid_integer"),
    ({"query_strand": "Minus"}, "strand_coordinate_conflict"),
])
def test_invalid_geometry_preserves_valid_traceback_counts(changes, code):
    value = alignment_components(hsp(**changes), program="blastp", query_length=10, reference_length=10)
    assert value["counts"]["paired_columns"] == 4
    assert value["fractions"]["paired_identity"] == 1
    assert value["fractions"]["query_paired_coverage"] is None
    assert value["pairs"] == [] and value["traceback_available"] and not value["geometry_available"]
    assert code in codes(value)


@pytest.mark.parametrize("frame,code", [(0, "invalid_translation_frame"),
    (-1, "frame_coordinate_direction_conflict"), (2, "frame_coordinate_phase_conflict"),
    (True, "invalid_frame")])
def test_translated_frame_geometry_conflicts_are_explicit(frame, code):
    native = hsp("AC", "AC", query_to=6, query_frame=frame)
    value = alignment_components(native, program="blastx", query_length=9, reference_length=4)
    assert code in codes(value) and value["pairs"] == []
    assert value["counts"]["paired_columns"] == 2


@pytest.mark.parametrize("field,value", [("bit_score", float("nan")), ("score", float("inf")),
    ("evalue", -1), ("evalue", True), ("bit_score", "1.0")])
def test_invalid_native_scores_do_not_erase_valid_geometry(field, value):
    components = alignment_components(hsp(**{field: value}), program="blastp", query_length=10, reference_length=10)
    assert components["native_scores"][field] is None
    assert components["geometry_available"]
    assert {"code": "invalid_number", "field": field} in components["issues"]
    json.dumps(components, allow_nan=False)


def test_discrepant_reported_identity_is_separate_from_calculated_identity():
    value = alignment_components(hsp(identity=2), program="blastp", query_length=10, reference_length=10)
    assert value["reported_counts"]["identity"] == 2
    assert value["counts"]["identical_pairs"] == 4
    assert value["fractions"]["paired_identity"] == 1
    assert {"code": "reported_count_traceback_conflict", "field": "identity",
            "reported": 2, "calculated": 4} in value["issues"]


def test_contradictory_positive_count_is_retained_with_relationship_issue():
    value = alignment_components(hsp(positive=1), program="blastp", query_length=10, reference_length=10)
    assert value["reported_counts"]["positive"] == 1
    assert value["counts"]["identical_pairs"] == 4
    assert "reported_positive_below_identity" in codes(value)


def test_large_finite_integer_native_score_is_not_cast_to_float():
    native = hsp(score=10**400)
    value = alignment_components(native, program="blastp", query_length=10, reference_length=10)
    assert value["native_scores"]["score"] == 10**400
    assert value["issues"] == []
    json.dumps(value, allow_nan=False)


@pytest.mark.parametrize("native,code", [
    ({"qseq": "AC", "hseq": "ACD"}, "invalid_traceback_strings"),
    ({"qseq": "A.C", "hseq": "AAC"}, "invalid_traceback_strings"),
    ({"qseq": "A-C", "hseq": "A-C"}, "double_gap_alignment_column"),
    ({"qseq": "AC", "hseq": None}, "invalid_traceback_strings"),
])
def test_malformed_traceback_does_not_fabricate_pairs(native, code):
    value = alignment_components(native, program="blastp", query_length=10, reference_length=10)
    assert code in codes(value)
    assert value["pairs"] == [] and not value["traceback_available"]


def test_unknown_program_retains_scores_without_guessing_coordinates():
    value = alignment_components(hsp(), program="not_blast", query_length=10, reference_length=10)
    assert value["native_scores"]["bit_score"] == 18.5
    assert value["pairs"] == [] and "unsupported_blast_program" in codes(value)


def test_lowercase_masked_symbols_are_case_insensitive_for_identity():
    value = alignment_components(hsp("acDE", "ACde", identity=4), program="blastp", query_length=4, reference_length=4)
    assert value["counts"]["identical_pairs"] == 4 and value["issues"] == []


def test_duplicate_and_overlapping_hsps_count_coordinates_once():
    first = hsp()
    second = hsp("DEFG", "DEFG", query_from=3, query_to=6, hit_from=3, hit_to=6, bit_score=22)
    source = normalized([first, deepcopy(first), second])
    original = deepcopy(source)
    sheet = build_pairwise_sheet(source)
    assert source == original
    assert sheet["union"]["counts"]["distinct_residue_pairs"] == 6
    assert sheet["union"]["counts"]["paired_query_positions"] == 6
    assert sheet["union"]["fractions"]["query_paired_coverage"] == .6
    assert sheet["union"]["fractions"]["paired_identity"] == 1
    assert sheet["union"]["identical_mapping_hsp_groups"] == [[0, 1]]
    assert sheet["union"]["pairs"][2]["hsp_indices"] == [0, 1, 2]
    assert sheet["union"]["conflicts"] == []
    assert [row["components"]["native_scores"]["bit_score"] for row in sheet["hsps"]] == [18.5, 18.5, 22]
    assert "bit_score" not in sheet["union"]
    sheet["input"]["query"]["length"] = 999
    assert source == original


def test_alternative_maps_are_kept_and_not_collapsed_to_aggregate_identity():
    first = hsp()
    shifted = hsp(hit_from=2, hit_to=5)
    sheet = build_pairwise_sheet(normalized([first, shifted]))
    assert sheet["union"]["counts"]["distinct_residue_pairs"] == 8
    assert sheet["union"]["counts"]["paired_query_positions"] == 4
    assert sheet["union"]["counts"]["paired_reference_positions"] == 5
    assert sheet["union"]["fractions"]["query_paired_coverage"] == .4
    assert sheet["union"]["fractions"]["paired_identity"] is None
    assert sheet["status"] == "partial"
    assert {row["operand"] for row in sheet["union"]["conflicts"]} == {"query", "reference"}


def test_conflicting_letters_at_same_coordinates_are_exposed():
    sheet = build_pairwise_sheet(normalized([hsp(), hsp("ACDE", "ACDF")]))
    assert sheet["union"]["counts"]["identical_residue_pairs"] is None
    assert sheet["union"]["fractions"]["paired_identity"] is None
    assert sheet["union"]["pairs"][-1]["identical"] is None
    assert sheet["union"]["conflicts"] == [{"code": "identity_at_correspondence_conflicts",
        "pair_index": 3, "hsp_indices": [0, 1]}]


def test_partially_known_mapping_reports_measured_union_and_missing_hsp():
    unknown = {"bit_score": 27, "align_len": 5, "identity": 3}
    sheet = build_pairwise_sheet(normalized([hsp(), unknown]))
    assert sheet["union"]["counts"]["hsps_without_geometry"] == 1
    assert not sheet["union"]["complete_for_reported_hsps"]
    assert sheet["union"]["fractions"]["query_paired_coverage"] == .4
    assert sheet["status"] == "partial"


def test_zero_hit_pairwise_result_does_not_assign_zero_identity():
    source = normalized([])
    source["hits"] = []
    source["search"]["reported_hit_count"] = 0
    source["search"]["request"] = {"subject": "selected_subject"}
    sheet = build_pairwise_sheet(source)
    assert sheet["status"] == "no_reported_alignment"
    assert sheet["reference"] is None
    assert sheet["input"]["search"]["request"] == {"subject": "selected_subject"}
    assert sheet["union"]["fractions"]["paired_identity"] is None
    assert sheet["union"]["fractions"]["query_paired_coverage"] is None
    source["search"]["hit_array_present"] = False
    assert build_pairwise_sheet(source)["status"] == "alignment_report_unavailable"


def test_aliases_are_one_reference_but_two_reported_hits_are_not_pairwise():
    source = normalized([hsp()])
    source["hits"][0]["descriptions"].append({"accession": "another_alias"})
    assert len(build_pairwise_sheet(source)["reference"]["descriptions"]) == 2
    source["hits"].append(deepcopy(source["hits"][0]))
    with pytest.raises(ValueError, match="single_pairwise_reference_required"):
        build_pairwise_sheet(source)


def test_pairwise_requires_correct_mode_and_json_input():
    source = normalized([hsp()])
    source["mode"] = "database"
    with pytest.raises(ValueError, match="pairwise_blast_mode_required"):
        build_pairwise_sheet(source)
    source["mode"] = "pairwise"
    source["native"]["invalid"] = float("nan")
    with pytest.raises(ValueError, match="finite_json_blast_result_required"):
        build_pairwise_sheet(source)


def test_translated_overlapping_different_frames_keep_conflicting_codon_mappings():
    a = hsp("AC", "AC", query_from=1, query_to=6, query_frame=1)
    b = hsp("AC", "AC", query_from=2, query_to=7, query_frame=2)
    sheet = build_pairwise_sheet(normalized([a, b], length=9, reference_length=3, program="blastx"))
    assert sheet["union"]["counts"]["paired_query_positions"] == 7
    assert sheet["union"]["fractions"]["query_paired_coverage"] == 7/9
    assert sheet["union"]["fractions"]["paired_identity"] is None
    assert sheet["union"]["conflicts"]
