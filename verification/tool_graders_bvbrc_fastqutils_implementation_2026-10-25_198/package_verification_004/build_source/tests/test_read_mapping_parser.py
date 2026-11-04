"""Synthetic PAF fixtures: no model, provider, mapper, or biological truth data.

The format meanings come from the pinned minimap2 2.31 minimap2.1 OUTPUT
FORMAT section. Coordinates are zero-based, half-open, and original-strand;
255 is missing MAPQ. Site expectations below describe the manually specified
gapped alignment, rather than using another mapper as an oracle.
"""

import json
import sqlite3

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.read_mapping import (
    compare_paf_sites,
    parse_paf_line,
    project_output,
)


def synthetic_paf(*, query_name="q1", query_length=4, query_start=0,
                  query_end=4, strand="+", reference_name="r1",
                  reference_length=4, reference_start=0, reference_end=4,
                  matching_bases=4, block_length=4, mapq=60,
                  tags=("tp:A:P", "cg:Z:4M", "cs:Z:=ACGT")):
    """Render an explicitly synthetic row; no alignment computation is hidden."""
    fields = [query_name, query_length, query_start, query_end, strand,
              reference_name, reference_length, reference_start, reference_end,
              matching_bases, block_length, mapq, *tags]
    return "\t".join(map(str, fields)) + "\n"


@pytest.mark.parametrize("mapq,available", [(0, True), (60, True), (254, True), (255, False)])
def test_native_mapq_preserves_missing_value_without_quality_threshold(mapq, available):
    row = parse_paf_line(synthetic_paf(mapq=mapq).encode("ascii"))
    assert row["mapping_quality"] == mapq
    assert row["mapping_quality_available"] is available


def test_native_secondary_placement_and_typed_tags_are_preserved():
    tags = ("tp:A:S", "cg:Z:4M", "cs:Z:=ACGT", "AS:i:-9", "dv:f:0.125")
    row = parse_paf_line(synthetic_paf(tags=tags))
    assert row["native_alignment_type"] == "S"
    assert row["tags"] == [
        {"name": "tp", "type": "A", "value": "S"},
        {"name": "cg", "type": "Z", "value": "4M"},
        {"name": "cs", "type": "Z", "value": "=ACGT"},
        {"name": "AS", "type": "i", "value": "-9"},
        {"name": "dv", "type": "f", "value": "0.125"},
    ]


def test_approximate_placement_survives_without_inventing_site_path():
    row = parse_paf_line(synthetic_paf(tags=("tp:A:P",)))
    assert row["base_alignment_available"] is False
    assert row["cigar"] is None
    with pytest.raises(ContractError, match="native_base_alignment_unavailable"):
        compare_paf_sites(row, [0], query="ACGT", reference="ACGT")


@pytest.mark.parametrize("changes", [
    {"query_start": -1},
    {"query_start": 4},
    {"query_end": 5},
    {"query_length": 0},
    {"reference_start": -1},
    {"reference_start": 4},
    {"reference_end": 5},
    {"reference_length": 0},
    {"strand": "?"},
    {"mapq": -1},
    {"mapq": 256},
    {"matching_bases": -1},
    {"matching_bases": 5},
    {"block_length": 0},
])
def test_native_coordinate_and_numeric_domains_are_representation_checks(changes):
    with pytest.raises(ContractError, match="invalid_native_paf_row"):
        parse_paf_line(synthetic_paf(**changes))


@pytest.mark.parametrize("tags,error", [
    (("cg:Z:3M",), "native_paf_cigar_extent_mismatch"),
    (("cs:Z:=ACG",), "native_paf_cs_extent_mismatch"),
    (("cg:Z:0M",), "invalid_native_paf_cigar"),
    (("cs:Z::0",), "invalid_native_paf_cs"),
    (("cg:i:4",), "invalid_native_paf_cigar"),
    (("cg:Z:4M", "cg:Z:4M"), "invalid_native_paf_row"),
    (("dv:f:nan",), "invalid_native_paf_row"),
])
def test_invalid_base_paths_and_duplicate_or_nonfinite_tags_are_explicit(tags, error):
    with pytest.raises(ContractError, match=error):
        parse_paf_line(synthetic_paf(tags=tags))


def test_cg_and_cs_with_equal_spans_but_conflicting_paths_are_not_site_evidence():
    # cg has four paired columns; cs has two paired columns, a deletion, then
    # an insertion. Equal query/reference totals cannot make both paths true.
    with pytest.raises(ContractError, match="native_paf_base_path_mismatch"):
        parse_paf_line(synthetic_paf(
            matching_bases=2, block_length=4,
            tags=("cg:Z:4M", "cs:Z:=AC-gt+ta")))


def test_explicit_unambiguous_alignment_block_matches_its_columns():
    # This cs string contains four explicit unambiguous equal bases. Its block
    # count cannot be five. Ambiguous columns have different native semantics.
    with pytest.raises(ContractError, match="native_paf_block_length_mismatch"):
        parse_paf_line(synthetic_paf(matching_bases=4, block_length=5))


def test_cigar_m_and_cs_substitution_share_one_paired_path():
    row = parse_paf_line(synthetic_paf(
        matching_bases=3, tags=("cg:Z:4M", "cs:Z:=AC*gt=T")))
    sites = compare_paf_sites(row, [2], query="ACTT", reference="ACGT")["sites"]
    assert sites[0]["relationship"] == "substituted"
    assert sites[0]["query_residue"] == "T"
    assert sites[0]["reference_residue"] == "G"


def test_plus_sites_preserve_gaps_insertions_outside_and_requested_order():
    # Reference:       C G - T C G T  (r[2,8))
    # Query:           C T G - - G T  (q[1,6))
    # The insertion belongs to boundary 4, not residue 4; the two deleted
    # reference residues have neither query coordinates nor quality values.
    row = parse_paf_line(synthetic_paf(
        query_length=7, query_start=1, query_end=6,
        reference_length=10, reference_start=2, reference_end=8,
        matching_bases=3, block_length=7,
        tags=("cg:Z:2M1I2D2M", "cs:Z:=C*gt+g-tc=GT")))
    result = compare_paf_sites(row, [8, 7, 2, 4, 3, 6, 0, 6],
        query="NCTGGTN", reference="AACGTCGTAA", quality="ABCDEFG")
    assert [s["reference_position"] for s in result["sites"]] == [8, 7, 2, 4, 3, 6, 0, 6]
    assert [s["relationship"] for s in result["sites"]] == [
        "outside_alignment", "identical", "identical", "gap",
        "substituted", "identical", "outside_alignment", "identical"]
    deleted = result["sites"][3]
    assert deleted["reference_residue"] == "T"
    assert deleted["native_operation"] == "D"
    assert all(deleted[key] is None for key in (
        "query_position", "query_original_residue", "query_residue",
        "query_quality_character", "query_quality_score"))
    substituted = result["sites"][4]
    assert (substituted["query_position"], substituted["query_residue"],
            substituted["reference_residue"]) == (2, "T", "G")
    assert result["insertions"] == [{
        "reference_boundary": 4, "query_interval": [3, 4], "query_strand": "+",
        "query_sequence": "G", "query_quality_characters": "D",
        "quality_encoding": "unspecified", "native_operation": "I"}]


def test_reverse_sites_keep_original_coordinates_and_orient_symbols_and_quality():
    # Query original q[1,7) ACACGA, reverse complement TCGTGT.
    # Reference:       T C - - A A G T
    # Query oriented:  T C G T - - G T
    row = parse_paf_line(synthetic_paf(
        query_length=8, query_start=1, query_end=7, strand="-",
        reference_length=10, reference_start=2, reference_end=8,
        matching_bases=4, block_length=8,
        tags=("tp:A:S", "cg:Z:2M2I2D2M", "cs:Z:=TC+gt-aa=GT")))
    result = compare_paf_sites(row, [2, 3, 4, 5, 6, 7],
        query="NACACGAN", reference="AATCAAGTAA", quality="ABCDEFGH")
    sites = result["sites"]
    assert [s["query_position"] for s in sites] == [6, 5, None, None, 2, 1]
    assert [s["query_residue"] for s in sites] == ["T", "C", None, None, "G", "T"]
    assert [s["query_original_residue"] for s in sites] == ["A", "G", None, None, "C", "A"]
    assert [s["query_quality_character"] for s in sites] == ["G", "F", None, None, "C", "B"]
    assert [s["relationship"] for s in sites] == ["identical", "identical", "gap", "gap", "identical", "identical"]
    assert result["native_alignment_type"] == "S"
    assert result["insertions"] == [{
        "reference_boundary": 4, "query_interval": [3, 5], "query_strand": "-",
        "query_sequence": "GT", "query_quality_characters": "ED",
        "quality_encoding": "unspecified", "native_operation": "I"}]


def test_unspecified_quality_preserves_characters_without_guessing_an_offset():
    row = parse_paf_line(synthetic_paf(mapq=255))
    result = compare_paf_sites(row, [0, 2], query="ACGT", reference="ACGT", quality="I@+;")
    assert [site["query_quality_character"] for site in result["sites"]] == ["I", "+"]
    assert [site["query_quality_score"] for site in result["sites"]] == [None, None]
    assert result["quality_encoding"] == "unspecified"
    assert result["mapping_quality"] == 255
    assert result["mapping_quality_available"] is False


@pytest.mark.parametrize("encoding,character,expected", [
    ("phred33", "I", 40), ("phred64", "h", 40), ("solexa64", ";", -5)])
def test_declared_quality_encoding_decodes_its_own_score_not_a_guessed_accuracy(encoding, character, expected):
    row = parse_paf_line(synthetic_paf())
    site = compare_paf_sites(row, [1], query="ACGT", reference="ACGT",
        quality=character*4, quality_encoding=encoding)["sites"][0]
    assert site["query_quality_character"] == character
    assert site["query_quality_score"] == expected
    assert site["quality_encoding"] == encoding


@pytest.mark.parametrize("arguments,error", [
    ({"query": "ACG", "reference": "ACGT"}, "native_alignment_operand_length_changed"),
    ({"query": "ACGT", "reference": "ACG"}, "native_alignment_operand_length_changed"),
    ({"query": "ACGT", "reference": "ACGT", "quality": "III"}, "native_query_quality_length_mismatch"),
    ({"query": "ACGT", "reference": "ACGT", "quality_encoding": "guessed33"}, "unknown_quality_encoding"),
])
def test_site_inspection_reports_changed_operands_or_unsupported_representation(arguments, error):
    row = parse_paf_line(synthetic_paf())
    with pytest.raises(ContractError, match=error):
        compare_paf_sites(row, [0], **arguments)


@pytest.mark.parametrize("positions", [[-1], [4], [True], [1.0]])
def test_site_request_must_use_actual_integer_reference_coordinates(positions):
    row = parse_paf_line(synthetic_paf())
    with pytest.raises(ContractError, match="invalid_reference_site"):
        compare_paf_sites(row, positions, query="ACGT", reference="ACGT")


def test_projection_keeps_valid_siblings_raw_rows_and_exact_failure_locators(tmp_path):
    # Each line is a separate synthetic native record. A damaged record, an
    # unknown operand, and a wrong length must not erase either valid sibling.
    lines = [
        synthetic_paf().encode("ascii"),
        b"damaged\tnative\trow\n",
        synthetic_paf(mapq=255, strand="-", tags=("tp:A:S", "cg:Z:4M", "cs:Z:=ACGT")).encode("ascii"),
        synthetic_paf(query_name="not-an-input").encode("ascii"),
        synthetic_paf(reference_length=5).encode("ascii"),
    ]
    raw = b"".join(lines)
    (tmp_path/"mappings.paf").write_bytes(raw)
    with sqlite3.connect(tmp_path/"operands.sqlite") as connection:
        connection.execute("CREATE TABLE operands(role TEXT, subject_ref TEXT, length INTEGER)")
        connection.executemany("INSERT INTO operands VALUES(?,?,?)", [("query", "q1", 4), ("reference", "r1", 4)])
    project_output(tmp_path)
    assert (tmp_path/"mappings.paf").read_bytes() == raw
    placements = [json.loads(line) for line in (tmp_path/"placements.jsonl").read_text().splitlines()]
    errors = [json.loads(line) for line in (tmp_path/"projection-errors.jsonl").read_text().splitlines()]
    assert [row["line_number"] for row in placements] == [1, 3]
    assert placements[1]["native_alignment_type"] == "S"
    assert placements[1]["mapping_quality_available"] is False
    assert [row["line_number"] for row in errors] == [2, 4, 5]
    assert [row["code"] for row in errors] == [
        "invalid_native_paf_row", "native_paf_operand_identity_mismatch",
        "native_paf_operand_identity_mismatch"]
    assert errors[1]["detail"] == {"role": "query", "subject_ref": "not-an-input"}
    assert errors[2]["detail"] == {"role": "reference", "subject_ref": "r1"}
    for record in placements + errors:
        assert raw[record["row_start"]:record["row_end"]] == lines[record["line_number"]-1]
