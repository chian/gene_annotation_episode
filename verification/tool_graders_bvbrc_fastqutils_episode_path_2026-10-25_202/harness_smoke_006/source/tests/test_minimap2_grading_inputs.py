"""Hand-authored PAF examples, separate from retained real minimap2 outputs."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.minimap2_grading_inputs import (
    PRESETS, build_minimap2_placement_sheet, parse_minimap2_paf_row,
)


def paf(*, qlen=4, qs=0, qe=4, strand="+", rlen=4, rs=0, re=4,
        matches=4, block=4, mapq=60, qname="q", rname="r",
        tags=("cg:Z:4M", "cs:Z:=ACGT", "tp:A:P")):
    return "\t".join(map(str, [qname, qlen, qs, qe, strand, rname, rlen, rs, re,
                               matches, block, mapq, *tags]))+"\n"


def build(line=None, **kwargs):
    return build_minimap2_placement_sheet(parse_minimap2_paf_row(line or paf()),
        preset=kwargs.pop("preset", "map-ont"), native_version="2.31-r1302", **kwargs)


@pytest.mark.parametrize("preset", PRESETS)
def test_all_selected_presets_retain_separate_identity(preset):
    sheet = build(preset=preset)
    assert sheet["preset"] == preset
    assert sheet["native_version"] == "2.31-r1302"
    assert sheet["schema"] == "minimap2_placement_sheet_v1"
    assert sheet["native_result"]["native_line"] == paf().rstrip("\n")


@pytest.mark.parametrize("tags,geometry,equality,base_available", [
    ((), False, False, False), (("cg:Z:4M",), True, False, True),
    (("cs:Z::4",), True, True, False), (("cs:Z:=ACGT",), True, True, False),
    (("cg:Z:4M", "cs:Z::4"), True, True, True),
])
def test_paths_have_separate_availability(tags, geometry, equality, base_available):
    row = parse_minimap2_paf_row(paf(tags=tags).encode("ascii"))
    assert row["base_alignment_available"] is base_available
    sheet = build_minimap2_placement_sheet(row, preset="sr", native_version=None)
    assert sheet["availability"]["geometry"] is geometry
    assert sheet["availability"]["cs_equality"] is equality
    assert sheet["measured_counts"]["paired_positions"] == (4 if geometry else None)
    assert sheet["measured_counts"]["cs_equal_positions"] == (4 if equality else None)


def test_hand_checked_gapped_path_retains_compact_exact_correspondence():
    sheet = build(paf(qlen=7, qs=1, qe=6, rlen=10, rs=2, re=8, matches=3, block=7,
        tags=("cg:Z:2M1I2D2M", "cs:Z:=C*gt+g-tc=GT")),
        query_metadata={"name": "q", "length": 7, "sequence": "NCTGGTN"},
        reference_metadata={"name": "r", "length": 10, "sequence": "AACGTCGTAA"})
    assert sheet["measured_counts"] == {"paired_positions": 4, "inserted_bases": 1,
        "deleted_bases": 2, "query_gap_columns": 2, "reference_gap_columns": 1,
        "reference_skipped_bases": 0, "alignment_columns": 7,
        "cs_equal_positions": 3, "cs_substituted_positions": 1}
    assert [p["query_interval"] for p in sheet["correspondence"]] == [[1, 3], [3, 4], [4, 4], [4, 6]]
    assert [p["reference_interval"] for p in sheet["correspondence"]] == [[2, 4], [4, 4], [4, 6], [6, 8]]
    assert sheet["original_symbols"]["equal_positions"] == 3
    assert sheet["original_symbols"]["substituted_positions"] == 1


def test_reverse_strand_original_query_positions_descend_and_gaps_are_boundaries():
    sheet = build(paf(qlen=8, qs=1, qe=7, strand="-", rlen=10, rs=2, re=8, matches=4, block=8,
        tags=("cg:Z:2M2I2D2M", "cs:Z:=TC+gt-aa=GT", "tp:A:S")),
        query_metadata={"name": "q", "length": 8, "sequence": "NACACGAN"},
        reference_metadata={"name": "r", "length": 10, "sequence": "AATCAAGTAA"})
    assert [p["query_first"] for p in sheet["correspondence"]] == [6, 4, None, 2]
    assert [p["query_step"] for p in sheet["correspondence"]] == [-1, -1, None, -1]
    assert [p["query_interval"] for p in sheet["correspondence"]] == [[5, 7], [3, 5], [3, 3], [1, 3]]
    assert sheet["original_symbols"]["equal_positions"] == 4
    assert sheet["native_alignment_type"] == "S"


def test_skips_are_reference_spans_but_not_alignment_columns():
    sheet = build(paf(rlen=14, re=14, tags=("cg:Z:2M10N2M", "cs:Z:=AC~gt10ag=GT", "nn:i:0")))
    assert sheet["measured_counts"]["alignment_columns"] == 4
    assert sheet["measured_counts"]["reference_skipped_bases"] == 10
    assert sheet["correspondence"][1]["column_interval"] == [2, 2]
    assert sheet["count_relationship"]["status"] == "verified"


def test_ambiguous_paired_symbols_preserve_native_cs_and_original_counts():
    sheet = build(paf(matches=2, block=2,
        tags=("cg:Z:4M", "cs:Z:=AN*cn=T", "nn:i:2", "NM:i:2")),
        query_metadata={"name": "q", "length": 4, "sequence": "ARNT"},
        reference_metadata={"name": "r", "length": 4, "sequence": "ANCT"})
    assert sheet["native_facts"]["block_length"] == 2
    assert sheet["measured_counts"]["alignment_columns"] == 4
    assert sheet["measured_counts"]["cs_equal_positions"] == 3
    assert sheet["original_symbols"]["equal_positions"] == 2
    assert sheet["native_tag_quantities"]["nn"] == 2


def test_ambiguity_in_inserted_and_deleted_bases_is_in_nn_not_blen():
    sheet = build(paf(qlen=5, qe=5, rlen=5, re=5,
        tags=("cg:Z:2M1I1D2M", "cs:Z:=AC+n-n=GT", "nn:i:2")))
    assert sheet["measured_counts"]["alignment_columns"] == 6
    assert sheet["native_facts"]["block_length"] == 4
    assert sheet["native_tag_quantities"]["nn"] == 2


def test_missing_nn_is_never_invented_and_relationship_is_only_checked_when_possible():
    sheet = build(paf(matches=3, block=3, tags=("cg:Z:4M",)))
    assert sheet["native_tag_quantities"]["nn"] is None
    assert sheet["count_relationship"]["status"] == "unavailable"
    explicit = build(paf(matches=3, block=3, tags=("cg:Z:4M", "cs:Z:=ACGN")))
    assert explicit["native_tag_quantities"]["nn"] is None
    assert explicit["count_relationship"] == {"status": "verified", "reason": None,
        "ambiguity_source": "fully_explicit_cs_symbols"}
    short = build(paf(matches=3, block=3, tags=("cs:Z::4", "nn:i:1")))
    assert short["measured_counts"]["cs_equal_positions"] == 4
    assert short["native_facts"]["matching_bases"] == 3


@pytest.mark.parametrize("changes,code", [
    ({"qs": -1}, "invalid_native_paf_row"), ({"qe": 5}, "invalid_native_paf_row"),
    ({"mapq": 256}, "invalid_native_paf_row"), ({"strand": "*"}, "invalid_native_paf_row"),
    ({"tags": ("cg:Z:3M",)}, "native_paf_cigar_extent_mismatch"),
    ({"tags": ("cs:Z:=ACG",)}, "native_paf_cs_extent_mismatch"),
    ({"tags": ("cg:Z:0M",)}, "invalid_native_paf_cigar"),
    ({"tags": ("cs:Z::0",)}, "invalid_native_paf_cs"),
    ({"tags": ("cs:Z:=ACGR",)}, "invalid_native_paf_cs"),
    ({"tags": ("cg:i:4",)}, "invalid_native_paf_cigar"),
    ({"tags": ("cg:Z:4M", "cg:Z:4M")}, "native_paf_duplicate_tag:cg"),
    ({"tags": ("dv:f:nan",)}, "invalid_native_paf_tag_value"),
    ({"tags": ("dv:f:0_1",)}, "invalid_native_paf_tag_value"),
    ({"tags": ("AS:i:bad",)}, "invalid_native_paf_tag_value"),
    ({"tags": ("zz:B:c,256",)}, "invalid_native_paf_tag_value"),
    ({"tags": ("zz:H:ABC",)}, "invalid_native_paf_tag_value"),
    ({"tags": ("tp:A:SS",)}, "invalid_native_paf_tag_value"),
    ({"tags": ("cg:Z:4M", "cs:Z:=AC-gt+ta"), "matches": 2}, "native_paf_base_path_mismatch"),
    ({"tags": ("cg:Z:4M", "nn:i:1")}, "native_paf_block_length_mismatch"),
    ({"tags": ("cs:Z:=ACGT",), "matches": 3}, "native_paf_matching_bases_mismatch"),
])
def test_malformed_and_contradictory_native_rows_have_specific_failures(changes, code):
    with pytest.raises(ValueError, match=code):
        parse_minimap2_paf_row(paf(**changes))


@pytest.mark.parametrize("line", [b"bad\trow\n", b"\xff\n", paf()+paf(), paf().replace("\t4\t", "\t4.0\t", 1)])
def test_bad_row_encoding_truncation_and_multiple_rows_are_rejected(line):
    with pytest.raises(ValueError, match="invalid_native_paf_row"):
        parse_minimap2_paf_row(line)


def test_optional_semantic_errors_preserve_all_raw_tags_and_valid_scientific_values():
    sheet = build(paf(tags=("cg:Z:4M", "AS:i:-9", "ms:i:-1", "dv:f:0.125", "nn:i:-1", "NM:Z:unknown")))
    assert sheet["native_tag_quantities"]["AS"] == -9
    assert sheet["native_tag_quantities"]["ms"] == -1
    assert sheet["native_tag_quantities"]["dv"] == 0.125
    assert sheet["native_tag_quantities"]["nn"] is None
    assert sheet["native_tag_quantities"]["NM"] is None
    assert len(sheet["native_result"]["tags"]) == 6
    assert {issue["code"] for issue in sheet["issues"]} == {"native_tag_value_out_of_domain", "native_tag_type_mismatch"}


@pytest.mark.parametrize("metadata", [{"name": "wrong", "length": 4}, {"name": "q", "length": 5},
    {"length": 4}, {"name": "q", "length": True}])
def test_incorrect_metadata_cannot_reassign_actual_native_operand(metadata):
    sheet = build(query_metadata=metadata)
    assert sheet["metadata"]["query"]["status"] == "invalid"
    assert sheet["metadata"]["query"]["length"] is None
    assert sheet["native_facts"]["query_name"] == "q"
    assert sheet["native_facts"]["query_length"] == 4
    assert sheet["measured_counts"]["paired_positions"] == 4
    assert sheet["metadata"]["query"]["supplied"] == metadata


def test_nonfinite_storage_rejected_and_caller_data_unchanged():
    native = parse_minimap2_paf_row(paf())
    before = deepcopy(native)
    sheet = build_minimap2_placement_sheet(native, preset="lr:hq", native_version=None)
    assert native == before
    sheet["native_result"]["query_name"] = "changed"
    assert native == before
    with pytest.raises(ValueError, match="finite_json_minimap2_native_required"):
        build_minimap2_placement_sheet({**native, "extra": float("inf")}, preset="sr", native_version=None)
    json.dumps(sheet, allow_nan=False)


def test_partial_parsed_record_retains_valid_native_fields_and_no_geometry():
    native = {"query_name": "q", "query_length": 7, "query_interval": [1, 6], "matching_bases": 3,
              "block_length": 7, "strand": "+"}
    sheet = build_minimap2_placement_sheet(native, preset="sr", native_version=None)
    assert sheet["status"] == "invalid"
    assert sheet["native_facts"]["query_length"] == 7
    assert sheet["native_facts"]["matching_bases"] == 3
    assert sheet["measured_counts"]["paired_positions"] is None
    assert sheet["issues"][0]["code"] == "minimap2_native_field_missing"


def test_huge_path_is_compact_and_no_per_residue_allocation_occurs():
    sheet = build(paf(qlen=10**9, qe=10**9, rlen=10**9, re=10**9, matches=10**9, block=10**9,
        tags=("cg:Z:1000000000M",)))
    assert len(sheet["correspondence"]) == 1
    assert sheet["measured_counts"]["paired_positions"] == 10**9


def test_eqx_cigar_preserves_paired_geometry_without_inventing_cs_counts():
    sheet = build(paf(matches=3, tags=("cg:Z:2=1X1=", "nn:i:0")))
    assert sheet["measured_counts"]["paired_positions"] == 4
    assert sheet["measured_counts"]["cs_equal_positions"] is None
    assert sheet["cg_operations"] == [{"operation": "=", "length": 2},
        {"operation": "X", "length": 1}, {"operation": "=", "length": 1}]


def test_wrong_supplied_sequence_invalidates_affected_join_and_preserves_native_path():
    sheet = build(query_metadata={"name": "q", "length": 4, "sequence": "AGCT"})
    assert sheet["metadata"]["query"]["sequence_status"] == "incompatible"
    assert sheet["metadata"]["query"]["length"] is None
    assert sheet["metadata"]["reference"]["length"] == 4
    assert sheet["measured_counts"]["cs_equal_positions"] == 4
    assert sheet["original_symbols"]["equal_positions"] is None
    assert sheet["issues"] == [{"code": "operand_sequence_cs_mismatch", "operand": "query"}]


def test_partial_record_salvages_valid_tags_without_duplicate_last_value_wins():
    native = parse_minimap2_paf_row(paf(tags=("AS:i:-9", "NM:i:0")))
    del native["reference_length"]
    native["tags"] += [{"name": "AS", "type": "i", "value": "100"}]
    sheet = build_minimap2_placement_sheet(native, preset="sr", native_version=None)
    assert sheet["native_tag_quantities"]["AS"] is None
    assert sheet["native_tag_quantities"]["NM"] == 0
    assert sheet["native_result"] == native


@pytest.mark.parametrize("field,value", [("strand", []), ("query_interval", "bad"), ("query_length", True),
    ("tags", {}), ("cigar", "bad")])
def test_finite_malformed_parsed_values_return_a_retained_invalid_sheet(field, value):
    native = parse_minimap2_paf_row(paf())
    native[field] = value
    sheet = build_minimap2_placement_sheet(native, preset="sr", native_version=None)
    assert sheet["status"] == "invalid"
    assert sheet["native_result"] == native
