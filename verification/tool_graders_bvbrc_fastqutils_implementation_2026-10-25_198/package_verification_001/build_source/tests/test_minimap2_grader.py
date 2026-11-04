"""Numerical component, overlap and offline recalculation tests for minimap2."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.minimap2_grading_inputs import parse_minimap2_paf_row
from gene_annotation_episode.minimap2_grader import (
    calculate_minimap2_placement_scores, calculate_minimap2_query_scores, grade_minimap2_placement,
)
from test_minimap2_grading_inputs import paf


def grade(line=None, **kwargs):
    return grade_minimap2_placement(parse_minimap2_paf_row(line or paf()),
        preset=kwargs.pop("preset", "map-hifi"), native_version="2.31-r1302", **kwargs)


def test_hand_checked_numerical_fixture():
    result = grade(paf(qlen=7, qs=1, qe=6, rlen=10, rs=2, re=8, matches=3, block=7,
        tags=("cg:Z:2M1I2D2M", "cs:Z:=C*gt+g-tc=GT", "AS:i:-9")))
    scores = result["scores"]
    expected = {"query_length": 7, "reference_length": 10, "query_span": 5, "reference_span": 6,
        "native_matching_bases": 3, "native_block_length": 7, "native_alignment_identity": 3/7,
        "paired_positions": 4, "inserted_bases": 1, "deleted_bases": 2, "query_gap_columns": 2,
        "reference_gap_columns": 1, "reference_skipped_bases": 0, "alignment_columns": 7,
        "cs_equal_positions": 3, "cs_substituted_positions": 1, "native_ambiguity_count": None,
        "query_span_coverage": 5/7, "reference_span_coverage": 6/10,
        "query_paired_coverage": 4/7, "reference_paired_coverage": 4/10,
        "query_aligned_coverage": 5/7, "reference_aligned_coverage": 6/10, "mapping_quality": 60}
    assert {name: scores[name] for name in expected} == expected
    assert scores["native_tag_quantities"]["AS"] == -9
    assert scores["denominators"]["query_paired_coverage"] == 7
    assert scores["definitions"]["native_tag_quantities.AS"]["units"] == "native_DP_alignment_score"


@pytest.mark.parametrize("mapq,expected", [(0, 0), (60, 60), (255, None)])
def test_mapping_quality_missing_and_zero_are_distinct(mapq, expected):
    result = grade(paf(mapq=mapq))
    assert result["sheet"]["native_facts"]["mapping_quality"] == mapq
    assert result["scores"]["mapping_quality"] == expected


def test_mandatory_only_approximate_native_identity_is_not_invented_geometry():
    scores = grade(paf(tags=()))["scores"]
    assert scores["native_alignment_identity"] == 1
    assert scores["native_alignment_identity_kind"] == "approximate_chaining"
    assert scores["query_span_coverage"] == 1
    assert scores["query_paired_coverage"] is None
    assert scores["paired_positions"] is None
    assert scores["cs_equal_positions"] is None
    assert scores["native_ambiguity_count"] is None


def test_normalized_N_equality_is_not_original_symbol_equality():
    result = grade(paf(matches=3, block=3, tags=("cg:Z:4M", "cs:Z:=ACGN", "nn:i:1")))
    assert result["scores"]["native_alignment_identity"] == 1
    assert result["scores"]["alignment_columns"] == 4
    assert result["scores"]["cs_equal_positions"] == 4
    assert result["scores"]["original_symbol_equal_positions"] is None
    assert result["scores"]["native_ambiguity_count"] == 1


def test_zero_denominators_return_null_and_never_nonfinite_values():
    result = grade(paf(matches=0, block=0, tags=("cg:Z:4M", "cs:Z:=NNNN", "nn:i:4")))
    assert result["scores"]["native_alignment_identity"] is None
    assert result["scores"]["query_paired_coverage"] == 1
    query = calculate_minimap2_query_scores([], query_metadata={"name": "q", "length": 0}, output_complete=True)
    assert query["reported_placement_count"] == 0
    assert query["query_span_union_coverage"] is None
    json.dumps([result, query], allow_nan=False)


def test_bad_query_metadata_leaves_native_counts_and_reference_coverage_available():
    scores = grade(query_metadata={"name": "wrong", "length": 4})["scores"]
    assert scores["query_length"] == 4
    assert scores["paired_positions"] == 4
    assert scores["query_span_coverage"] is None
    assert scores["query_paired_coverage"] is None
    assert scores["reference_paired_coverage"] == 1


def test_saved_sheet_recalculation_requires_no_native_or_network_access_and_does_not_mutate(monkeypatch):
    result = grade(paf(tags=("cg:Z:4M", "cs:Z:=ACGT", "tp:A:I", "nn:i:0", "AS:i:8")))
    saved = json.loads(json.dumps(result["sheet"]))
    before = deepcopy(saved)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved-sheet recalculation cannot execute or acquire")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    import gene_annotation_episode.minimap2_grading_inputs as readers
    monkeypatch.setattr(readers, "parse_minimap2_paf_row", forbidden)
    assert calculate_minimap2_placement_scores(saved) == result["scores"]
    assert saved == before


def test_saved_sheet_internal_numeric_conflicts_are_rejected():
    sheet = grade()["sheet"]
    sheet["measured_counts"]["paired_positions"] = 3
    with pytest.raises(ValueError, match="minimap2_sheet_components_invalid"):
        calculate_minimap2_placement_scores(sheet)


def test_query_summaries_count_overlaps_duplicates_alternatives_and_exact_reference_unions():
    first = grade(paf(qlen=8, qe=4, rlen=10, re=4,
        tags=("cg:Z:4M", "cs:Z:=ACGT", "tp:A:P")))["sheet"]
    duplicate = deepcopy(first)
    duplicate["native_result"].update(line_number=2, row_start=100, row_end=200)
    overlap = grade(paf(qlen=8, qs=2, qe=6, rlen=10, rs=2, re=6,
        tags=("cg:Z:4M", "cs:Z:=GTAC", "tp:A:P")))["sheet"]
    other = grade(paf(qlen=8, qs=2, qe=6, rlen=12, rs=4, re=8, rname="r2",
        tags=("cg:Z:4M", "cs:Z:=GTAC", "tp:A:S")))["sheet"]
    before = deepcopy([first, duplicate, overlap, other])
    result = calculate_minimap2_query_scores(iter([first, duplicate, overlap, other]),
        query_metadata={"name": "q", "length": 8}, output_complete=True)
    assert result["reported_placement_count"] == 4
    assert result["counts_by_native_alignment_type"] == {"P": 3, "S": 1}
    assert result["counts_by_strand"] == {"+": 4}
    assert result["distinct_reference_count"] == 2
    assert result["query_span_intervals"] == result["query_paired_intervals"] == [[0, 6]]
    assert result["query_paired_union_coverage"] == 6/8
    assert result["exact_duplicate_row_groups"] == [{"row_indices": [0, 1], "count": 2}]
    assert result["exact_duplicate_row_count"] == 1
    assert result["paired_position_observation_count"] == 16
    assert result["distinct_correspondence_count"] == 10
    assert result["repeated_correspondence_count"] == 6
    assert result["repeated_correspondence_positions"] == 4
    assert result["alternative_correspondence_positions"] == 4
    assert result["per_reference"][0]["paired_union_positions"] == 6
    assert result["per_reference"][1]["paired_union_positions"] == 4
    assert [first, duplicate, overlap, other] == before


def test_secondary_and_inversion_types_remain_categories_without_supplementary_inference():
    sheets = [grade(paf(strand=strand, tags=("cg:Z:4M", "tp:A:"+tp)))["sheet"]
              for tp, strand in (("P", "+"), ("S", "-"), ("I", "+"), ("i", "-"))]
    result = calculate_minimap2_query_scores(sheets, query_metadata={"name": "q", "length": 4}, output_complete=True)
    assert result["counts_by_native_alignment_type"] == {"P": 1, "S": 1, "I": 1, "i": 1}
    assert result["counts_by_strand"] == {"+": 2, "-": 2}
    assert result["alternative_correspondence_positions"] == 4
    assert not any("supplementary" in key or "confidence" in key for key in result)


@pytest.mark.parametrize("complete", [True, False, None])
def test_empty_output_retains_declared_completeness_without_absence_claim(complete):
    result = calculate_minimap2_query_scores([], query_metadata={"name": "q", "length": 4}, output_complete=complete)
    assert result["reported_placement_count"] == 0
    assert result["output_complete"] is complete
    if complete is True:
        assert result["result_meaning"] == "complete_output_has_zero_reported_placements_not_biological_absence"
    else:
        assert "partial_or_unknown" in result["result_meaning"]


def test_invalid_missing_and_incomplete_geometry_do_not_become_zero_measurements():
    approximate = grade(paf(tags=()))["sheet"]
    wrong_query = grade(paf(qname="other"))["sheet"]
    result = calculate_minimap2_query_scores([approximate, None, {"bad": "sheet"}, wrong_query],
        query_metadata={"name": "q", "length": 4}, output_complete=False)
    assert result["reported_placement_count"] == 1
    assert result["invalid_sheet_count"] == 2
    assert result["missing_sheet_count"] == 1
    assert result["geometry_missing_count"] == 1
    assert result["query_span_union_positions"] == 4
    assert result["query_paired_union_coverage"] is None
    assert result["query_paired_union_positions"] is None
    assert result["observed_query_paired_union_positions"] == 0
    assert result["repeated_correspondence_count"] is None
    assert result["alternative_correspondence_positions"] is None


def test_query_union_uses_original_reverse_positions_and_excludes_insertions_from_paired_union():
    sheet = grade(paf(qlen=8, qs=1, qe=7, strand="-", rlen=10, rs=2, re=8, matches=4, block=8,
        tags=("cg:Z:2M2I2D2M", "cs:Z:=TC+gt-aa=GT")))["sheet"]
    result = calculate_minimap2_query_scores([sheet], query_metadata={"name": "q", "length": 8}, output_complete=True)
    assert result["query_paired_intervals"] == [[1, 3], [5, 7]]
    assert result["query_paired_union_positions"] == 4
    assert result["query_span_union_positions"] == 6
    assert result["per_reference"][0]["paired_intervals"] == [[2, 4], [6, 8]]


def test_same_reference_name_with_inconsistent_lengths_is_not_silently_merged():
    sheets = [grade(paf(rlen=n))["sheet"] for n in (4, 5)]
    result = calculate_minimap2_query_scores(sheets, query_metadata={"name": "q", "length": 4}, output_complete=True)
    assert result["distinct_reference_count"] == 2
    assert result["issues"] == [{"code": "reference_name_has_multiple_lengths", "reference_name": "r", "lengths": [4, 5]}]


def test_query_sweep_uses_compressed_segments_for_large_intervals():
    sheet = grade(paf(qlen=10**9, qe=10**9, rlen=10**9, re=10**9, matches=10**9, block=10**9,
        tags=("cg:Z:1000000000M",)))["sheet"]
    result = calculate_minimap2_query_scores([sheet, deepcopy(sheet)],
        query_metadata={"name": "q", "length": 10**9}, output_complete=True)
    assert result["paired_position_observation_count"] == 2*10**9
    assert result["repeated_correspondence_count"] == 10**9
    assert result["alternative_correspondence_positions"] == 0


@pytest.mark.parametrize("preset", ["map-ont", "map-pb", "map-hifi", "lr:hq", "map-iclr", "sr"])
def test_retained_actual_native_output_and_saved_sheet_recalculation(preset, monkeypatch):
    directory = Path(__file__).resolve().parents[1]/"verification/tool_graders_minimap2_2026-10-24"/(
        "native_"+preset.replace(":", "_"))
    receipt = json.loads((directory/"receipt.json").read_text())
    assert receipt["returncode"] == 0
    assert receipt["metadata"]["policy"] == {"memory_bytes": 20*1024**3, "scratch_bytes": 4*1024**3, "wall_seconds": None}
    assert receipt["metadata"]["enforcement"]["memory"] == "systemd_cgroup_v2_memory_max"
    lines = (directory/"mappings.paf").read_bytes().splitlines()
    grades = [json.loads(line) for line in (directory/"placements.jsonl").read_text().splitlines()]
    assert len(lines) == len(grades) == 3
    for raw, graded in zip(lines, grades):
        row = parse_minimap2_paf_row(raw, native_version="2.31-r1302")
        assert row == graded["sheet"]["native_result"]
        assert graded["sheet"]["preset"] == preset
        expected = graded["scores"]
        if row["query_name"] in {"forward", "reverse"}:
            assert row["cigar"] == "1700M1I399M3D298M"
            fields = ("paired_positions", "inserted_bases", "deleted_bases", "alignment_columns",
                      "native_block_length", "native_matching_bases", "native_ambiguity_count",
                      "cs_equal_positions", "cs_substituted_positions", "original_symbol_equal_positions")
            assert [expected[field] for field in fields] == [2397, 1, 3, 2401, 2399, 2392, 2, 2393, 4, 2392]
        else:
            assert expected["alignment_columns"] == 2000
            assert expected["native_block_length"] == 1999
            assert expected["native_ambiguity_count"] == 1
    def forbidden(*args, **kwargs):
        raise AssertionError("retained sheet verification cannot execute or acquire")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    for graded in grades:
        before = deepcopy(graded["sheet"])
        assert calculate_minimap2_placement_scores(graded["sheet"]) == graded["scores"]
        assert graded["sheet"] == before
