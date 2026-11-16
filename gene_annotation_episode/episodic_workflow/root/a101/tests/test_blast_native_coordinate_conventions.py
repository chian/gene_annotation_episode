"""Retained BLAST+ 2.17.0 coordinate evidence and labeled synthetic edge cases.

No searches run here. Database/Homology envelopes below are test projections of
actual paired measurements, not claims of executed database or BV-BRC jobs.
"""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.root.a101.library.blast_pairwise_grader import alignment_components, blast_hsp_column_correspondence
from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_homology_inputs import _reported_bit_score_agrees


def test_synthetic_both_axes_reverse_with_gaps_uses_one_orientation_algorithm():
    hsp = {"query_from": 3, "query_to": 11, "query_frame": -3,
        "hit_from": 4, "hit_to": 12, "hit_frame": -2, "qseq": "M-KG", "hseq": "MA-G",
        "align_len": 4, "identity": 2, "gaps": 2}
    before = deepcopy(hsp)
    view = blast_hsp_column_correspondence(hsp, program="tblastx", query_length=13,
        reference_length=13, coordinate_convention="blast_json2")
    assert [row["query_interval"] for row in view["columns"]] == [[8, 11], None, [5, 8], [2, 5]]
    assert [row["reference_interval"] for row in view["columns"]] == [[9, 12], [6, 9], None, [3, 6]]
    assert all(row["query_direction"] == row["reference_direction"] == -1 for row in view["columns"])
    counts = alignment_components(hsp, program="tblastx", query_length=13,
        reference_length=13, coordinate_convention="blast_json2")
    assert counts["counts"]["paired_query_positions"] == counts["counts"]["paired_reference_positions"] == 6
    assert counts["fractions"]["query_paired_coverage"] == counts["fractions"]["reference_paired_coverage"] == 6 / 13
    descending = {**hsp, "query_from": 11, "query_to": 3, "hit_from": 12, "hit_to": 4}
    for convention in ("directional", "blast_json2"):
        assert alignment_components(descending, program="tblastx", query_length=13,
            reference_length=13, coordinate_convention=convention) == counts
    assert hsp == before


def test_negative_nt_frame_does_not_override_untranslated_native_strand():
    hsp = {"query_from": 2, "query_to": 4, "query_frame": -1, "query_strand": "Plus",
           "hit_from": 5, "hit_to": 3, "hit_strand": "Minus", "qseq": "ACG", "hseq": "ACG"}
    view = blast_hsp_column_correspondence(hsp, program="blastn", query_length=6, reference_length=6,
        coordinate_convention="blast_json2")
    assert [row["query_interval"] for row in view["columns"]] == [[1, 2], [2, 3], [3, 4]]
    assert [row["reference_interval"] for row in view["columns"]] == [[4, 5], [3, 4], [2, 3]]
    assert all(row["query_direction"] == 1 and row["reference_direction"] == -1 for row in view["columns"])


@pytest.mark.parametrize("convention", [None, "json15", "api", "unknown", {}, []])
@pytest.mark.parametrize("calculator", [alignment_components, blast_hsp_column_correspondence])
def test_unsupported_convention_is_an_explicit_caller_error(calculator, convention):
    with pytest.raises(ValueError, match="unsupported_blast_coordinate_convention"):
        calculator({}, program="blastx", query_length=244, reference_length=80,
                   coordinate_convention=convention)


@pytest.mark.parametrize("native,lexeme,agrees", [
    (99.9, "99.9", True), (99.9, "99", False),
    (99.90001, "99", True), (99.90001, "100", False),
    (170.629, "170", True), (170.629, "171", False),
    (170.629, "169", False), (170.629, "170.629", False),
    (200.846, "200", True), (200.846, "201", False),
    (99999, "99999", True), (99999, "99998", False),
    (99999.0001, "1.000e+05", True), (99999.0001, "1.001e+05", False),
    (18.021, "18.0", True), (18.021, "18.1", False),
    (None, "0", False), (float("nan"), "0", False),
    (170.629, "NaN", False), (170.629, "invalid", False),
])
def test_native_bit_score_truncation_has_exact_boundaries_and_no_widened_tolerance(native, lexeme, agrees):
    assert _reported_bit_score_agrees(lexeme, native) is agrees


