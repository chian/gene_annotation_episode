"""Selected-column arithmetic and retained formats; these tests run no BLAST.

Synthetic expected values are independently specified below. Retained local
pairwise and API ZIP bytes are parsed in their true modes; neither is submitted
to the host RID-bound reader by these pure component tests.
"""
from copy import deepcopy
import builtins
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.blast_grading_inputs import parse_blast_json
from gene_annotation_episode.blast_hsp_site_calculators import calculate_blast_hsp_column_components
from gene_annotation_episode.blast_hsp_site_inputs import extract_blast_hsp_columns
from gene_annotation_episode.blast_pairwise_grader import alignment_components, blast_hsp_column_correspondence
from gene_annotation_episode.blast_search import PROGRAM_UNITS


ROOT = Path(__file__).resolve().parents[1]
COLUMN_KEYS = {"column", "query_symbol", "reference_symbol", "query_interval", "reference_interval",
    "query_unit", "reference_unit", "alignment_unit", "query_direction", "reference_direction",
    "query_frame", "reference_frame", "query_strand", "reference_strand", "relationship",
    "query_original_intervals", "reference_original_intervals", "query_mapping_status",
    "reference_mapping_status", "query_mapping_reason", "reference_mapping_reason"}
SUMMARY_KEYS = {"window_alignment_columns", "paired_columns", "identical_pairs", "substituted_pairs",
    "query_gap_columns", "reference_gap_columns", "paired_identity", "alignment_identity",
    "query_paired_units", "reference_paired_units", "query_paired_coverage", "reference_paired_coverage"}


def native(query="MKG", reference="MKG", **changes):
    result = {"query_from": 1, "query_to": 3, "hit_from": 1, "hit_to": 3,
        "qseq": query, "hseq": reference, "align_len": len(query), "identity": 3,
        "bit_score": 0, "score": 12, "evalue": 0}
    result.update(changes)
    return result


def source(**changes):
    result = {"alignment_ref": "synthetic_hsp", "source_ref": "synthetic_source",
        "native_artifact_ref": "synthetic_supplied_hsp", "provider": "ncbi_blast",
        "format": "ncbi_blast_json_hsp", "native_version": "synthetic",
        "native_locator": {"report_ordinal": 0, "hit_ordinal": 0, "hsp_ordinal": 0}}
    result.update(changes)
    return result


def operands(program="blastp", qlength=5, rlength=5):
    qunit, runit, aunit = PROGRAM_UNITS[program]
    return {role: {"subject_ref": "synthetic_" + role, "length": length,
                   "unit": unit, "alignment_unit": aunit, "molecule": "protein" if unit == "aa" else "dna"}
            for role, length, unit in (("query", qlength, qunit), ("reference", rlength, runit))}


def extract(hsp=None, *, program="blastp", qlength=5, rlength=5, offset=0, limit=4096,
            original_mappings=None, source_input=None, operands_input=None):
    return extract_blast_hsp_columns(hsp if hsp is not None else native(), program=program,
        query_length=qlength, reference_length=rlength, column_offset=offset, column_limit=limit,
        operands=operands_input if operands_input is not None else operands(program, qlength, rlength),
        source=source_input if source_input is not None else source(), original_mappings=original_mappings)


def codes(sheet):
    return {row["code"] for row in sheet["issues"]}


def test_reviewed_reverse_nucleotide_window_and_native_zero():
    hsp = native("ACG-TAGG", "ACGT-AGG", query_from=3, query_to=9, hit_from=11, hit_to=5,
        query_strand="Plus", hit_strand="Minus", identity=6, gaps=2, midline="|||  |||")
    original = deepcopy(hsp)
    sheet = extract(hsp, program="blastn", qlength=12, rlength=18, offset=2, limit=4)
    scores = calculate_blast_hsp_column_components(sheet)
    assert sheet["native_input"] == original == hsp
    assert sheet["inherited_native_measurements"]["native_scores"] == {"bit_score": 0, "score": 12, "evalue": 0}
    assert sheet["inherited_native_measurements"]["scope"] == "whole_hsp"
    assert sheet["requested_window"] == {"column_offset": 2, "column_limit": 4}
    assert sheet["realized_window"] == {"column_offset": 2, "column_end": 6}
    assert sheet["total_columns"] == 8 and sheet["next_column_offset"] == 6
    rows = sheet["columns"]
    assert all(set(row) == COLUMN_KEYS for row in rows)
    assert [row["column"] for row in rows] == [2, 3, 4, 5]
    assert [(row["query_interval"], row["reference_interval"]) for row in rows] == [
        ([4, 5], [8, 9]), (None, [7, 8]), ([5, 6], None), ([6, 7], [6, 7])]
    assert "".join(row["query_symbol"] for row in rows) == "G-TA"
    assert "".join(row["reference_symbol"] for row in rows) == "GT-A"
    assert [row["reference_direction"] for row in rows] == [-1] * 4
    assert [row["reference_strand"] for row in rows] == ["Minus"] * 4
    assert rows[0]["reference_original_intervals"] is None
    assert rows[0]["reference_mapping_status"] == "unavailable"
    assert rows[1]["query_original_intervals"] == []
    assert rows[1]["query_mapping_status"] == "not_applicable"
    assert scores["summary"] == {"window_alignment_columns": 4, "paired_columns": 2,
        "identical_pairs": 2, "substituted_pairs": 0, "query_gap_columns": 1,
        "reference_gap_columns": 1, "paired_identity": 1, "alignment_identity": .5,
        "query_paired_units": 2, "reference_paired_units": 2,
        "query_paired_coverage": 2/12, "reference_paired_coverage": 2/18}
    assert scores["ratios"]["alignment_identity"] == {"numerator": 2, "denominator": 4, "value": .5}
    assert scores["ratios"]["query_paired_coverage"] == {"numerator": 2, "denominator": 12, "value": 2/12}


@pytest.mark.parametrize("program,qlength,rlength,changes,qp,rp", [
    ("blastn", 5, 6, {"qseq": "ACG", "hseq": "ACG", "query_from": 2, "query_to": 4,
        "hit_from": 4, "hit_to": 2, "hit_strand": "Minus"}, [[1, 2], [2, 3], [3, 4]], [[3, 4], [2, 3], [1, 2]]),
    ("blastp", 5, 5, {"query_from": 2, "query_to": 4}, [[1, 2], [2, 3], [3, 4]], [[0, 1], [1, 2], [2, 3]]),
    ("blastx", 12, 5, {"query_from": 12, "query_to": 4, "query_frame": -1,
        "hit_from": 2, "hit_to": 4}, [[9, 12], [6, 9], [3, 6]], [[1, 2], [2, 3], [3, 4]]),
    ("tblastn", 5, 12, {"query_from": 2, "query_to": 4, "hit_from": 12,
        "hit_to": 4, "hit_frame": -1}, [[1, 2], [2, 3], [3, 4]], [[9, 12], [6, 9], [3, 6]]),
    ("tblastx", 12, 12, {"query_from": 1, "query_to": 9, "query_frame": 1,
        "hit_from": 12, "hit_to": 4, "hit_frame": -1}, [[0, 3], [3, 6], [6, 9]], [[9, 12], [6, 9], [3, 6]]),
])
def test_all_five_programs_native_units_and_reverse_translated_geometry(program, qlength, rlength, changes, qp, rp):
    sheet = extract(native(**changes), program=program, qlength=qlength, rlength=rlength)
    scores = calculate_blast_hsp_column_components(sheet)
    assert [row["query_interval"] for row in sheet["columns"]] == qp
    assert [row["reference_interval"] for row in sheet["columns"]] == rp
    assert scores["summary"]["paired_columns"] == scores["summary"]["identical_pairs"] == 3
    assert scores["summary"]["paired_identity"] == scores["summary"]["alignment_identity"] == 1
    qunits = 9 if program in ("blastx", "tblastx") else 3
    runits = 9 if program in ("tblastn", "tblastx") else 3
    assert scores["summary"]["query_paired_units"] == qunits
    assert scores["summary"]["reference_paired_units"] == runits
    assert scores["summary"]["query_paired_coverage"] == qunits / qlength
    assert scores["summary"]["reference_paired_coverage"] == runits / rlength
    assert scores["definitions"]["query_paired_units"]["unit"] == PROGRAM_UNITS[program][0]
    assert sheet["columns"][0]["query_strand"] is None  # No inferred native strand.
    assert set(scores["summary"]) == set(scores["definitions"]) == set(scores["component_status"]) == SUMMARY_KEYS


@pytest.mark.parametrize("program,role,prefix", [("blastx", "query", "query"),
    ("tblastn", "reference", "hit"), ("tblastx", "query", "query"), ("tblastx", "reference", "hit")])
@pytest.mark.parametrize("reverse", [False, True])
def test_forward_and_reverse_translated_phase_two(program, role, prefix, reverse):
    values = {"query_to": 9, "query_frame": 1} if program in ("blastx", "tblastx") else {}
    if program in ("tblastn", "tblastx"):
        values.update(hit_to=9, hit_frame=1)
    values.update({prefix + "_from": 11 if reverse else 2,
                   prefix + "_to": 3 if reverse else 10, prefix + "_frame": -2 if reverse else 2})
    sheet = extract(native(**values), program=program, qlength=12, rlength=12)
    expected = [[8, 11], [5, 8], [2, 5]] if reverse else [[1, 4], [4, 7], [7, 10]]
    assert [row[role + "_interval"] for row in sheet["columns"]] == expected
    assert [row[role + "_direction"] for row in sheet["columns"]] == [-1 if reverse else 1] * 3


def test_translated_gap_consumes_no_codon_and_native_symbols_are_not_backtranslated():
    sheet = extract(native("M-KG", "MARG", query_from=12, query_to=4, query_frame=-1,
        hit_to=4, identity=2, gaps=1), program="blastx", qlength=12)
    rows = sheet["columns"]
    assert [row["query_interval"] for row in rows] == [[9, 12], None, [6, 9], [3, 6]]
    assert [row["query_symbol"] for row in rows] == list("M-KG")
    scores = calculate_blast_hsp_column_components(sheet)
    assert scores["summary"]["paired_columns"] == 3
    assert scores["summary"]["identical_pairs"] == 2
    assert scores["summary"]["substituted_pairs"] == 1
    assert scores["summary"]["query_gap_columns"] == 1
    assert scores["summary"]["query_paired_units"] == 9
    assert scores["summary"]["paired_identity"] == 2/3
    assert scores["summary"]["alignment_identity"] == .5


@pytest.mark.parametrize("changes,code", [
    ({"query_to": 9}, "traceback_coordinate_span_conflict"),
    ({"query_from": 5, "query_to": 7}, "coordinates_outside_operand"),
    ({"query_from": 3, "query_to": 1}, "reverse_protein_coordinates"),
    ({"query_strand": "Minus"}, "strand_coordinate_conflict"),
    ({"query_from": True}, "invalid_integer"),
    ({"query_from": None}, "coordinate_endpoints_unavailable"),
    ({"align_len": 9}, "site_native_geometry_conflict"),
    ({"midline": "MM"}, "site_native_geometry_conflict"),
])
def test_invalid_whole_hsp_geometry_keeps_string_counts_not_positions(changes, code):
    sheet = extract(native(**changes), offset=1, limit=1)
    scores = calculate_blast_hsp_column_components(sheet)
    assert code in codes(sheet)
    assert sheet["status"] == "partial" and sheet["availability"]["geometry"] == "incompatible"
    assert scores["summary"]["paired_columns"] == scores["summary"]["identical_pairs"] == 1
    assert scores["summary"]["paired_identity"] == 1
    assert scores["summary"]["query_paired_units"] is None
    assert scores["summary"]["reference_paired_coverage"] is None
    assert scores["component_status"]["query_paired_coverage"] == "incompatible"
    assert sheet["columns"][0]["query_interval"] is None
    assert sheet["columns"][0]["query_direction"] is None
    assert sheet["columns"][0]["query_mapping_status"] == "unavailable"
    assert sheet["columns"][0]["query_original_intervals"] is None


@pytest.mark.parametrize("frame,code", [(2, "frame_coordinate_phase_conflict"),
    (1, "frame_coordinate_direction_conflict"), (0, "invalid_translation_frame"), (True, "invalid_frame")])
def test_translated_reverse_frame_conflicts_preserve_identity(frame, code):
    sheet = extract(native(query_from=12, query_to=4, query_frame=-2 if frame == 2 else frame),
        program="blastx", qlength=12)
    scores = calculate_blast_hsp_column_components(sheet)
    assert code in codes(sheet)
    assert scores["summary"]["paired_identity"] == 1
    assert scores["summary"]["query_paired_coverage"] is None
    assert scores["summary"]["reference_paired_units"] is None


def test_empty_terminal_page_is_available_zero_with_null_identity():
    sheet = extract(offset=3, limit=2)
    scores = calculate_blast_hsp_column_components(sheet)
    assert sheet["columns"] == [] and sheet["total_columns"] == 3
    assert sheet["realized_window"] == {"column_offset": 3, "column_end": 3}
    assert sheet["next_column_offset"] is None
    assert all(value == 0 for value in sheet["measured_counts"].values())
    assert scores["ratios"]["paired_identity"] == {"numerator": 0, "denominator": 0, "value": None}
    assert scores["component_status"]["paired_identity"] == "not_applicable"
    assert scores["summary"]["query_paired_coverage"] == 0
    with pytest.raises(ValueError, match="blast_alignment_window_out_of_bounds"):
        extract(offset=4)


def test_gap_only_window_has_zero_paired_coverage_and_defined_alignment_identity():
    sheet = extract(native("M-KG", "MARG", query_to=3, hit_to=4, identity=2), offset=1, limit=1)
    scores = calculate_blast_hsp_column_components(sheet)
    assert scores["summary"]["paired_columns"] == scores["summary"]["identical_pairs"] == 0
    assert scores["summary"]["paired_identity"] is None
    assert scores["summary"]["alignment_identity"] == 0
    assert scores["summary"]["query_paired_coverage"] == scores["summary"]["reference_paired_coverage"] == 0


@pytest.mark.parametrize("strings,code", [
    ({"qseq": None, "hseq": None}, "traceback_not_reported"),
    ({"qseq": "MK", "hseq": "MKG"}, "invalid_traceback_strings"),
    ({"qseq": "M-K", "hseq": "M-G"}, "double_gap_alignment_column"),
    ({"qseq": "M.K", "hseq": "MKG"}, "invalid_traceback_strings"),
    ({"qseq": "", "hseq": ""}, "invalid_traceback_strings"),
])
def test_missing_or_malformed_traceback_never_invents_window_counts(strings, code):
    sheet = extract(native(**strings), offset=100)
    scores = calculate_blast_hsp_column_components(sheet)
    assert sheet["status"] == "unavailable"
    assert sheet["columns"] == [] and sheet["realized_window"] is None
    assert sheet["total_columns"] is None and sheet["next_column_offset"] is None
    assert all(value is None for value in scores["summary"].values())
    assert sheet["inherited_native_measurements"]["reported_counts"]["align_len"] == 3
    assert sheet["inherited_native_measurements"]["native_scores"]["evalue"] == 0
    assert code in codes(sheet)


def test_native_counts_and_scores_are_retained_but_unused_in_window_formula():
    sheet = extract(native(identity=1, bit_score=5000, evalue=1e-50, score=-3))
    scores = calculate_blast_hsp_column_components(sheet)
    assert sheet["inherited_native_measurements"]["reported_counts"]["identity"] == 1
    assert "reported_count_traceback_conflict" in codes(sheet)
    assert scores["summary"]["identical_pairs"] == 3 and scores["summary"]["paired_identity"] == 1
    assert sheet["availability"]["geometry"] == "available"
    assert sheet["inherited_native_measurements"]["native_scores"]["score"] == -3
    assert "evalue" not in scores["summary"]


def test_native_lowercase_and_ambiguity_are_literal_symbol_equality():
    sheet = extract(native("aNX", "ANy", identity=2))
    scores = calculate_blast_hsp_column_components(sheet)
    assert sheet["columns"][0]["query_symbol"] == "a"
    assert scores["summary"]["identical_pairs"] == 2 and scores["summary"]["substituted_pairs"] == 1
    assert scores["summary"]["paired_identity"] == 2/3


@pytest.mark.parametrize("strand,direction", [("Minus", -1), ("Plus", 1), (None, None)])
def test_single_nucleotide_direction_requires_actual_reported_strand(strand, direction):
    sheet = extract(native("A", "A", query_from=2, query_to=2, hit_from=3, hit_to=3,
        query_strand=strand, identity=1), program="blastn")
    row = sheet["columns"][0]
    assert row["query_interval"] == [1, 2] and row["reference_interval"] == [2, 3]
    assert row["query_direction"] == direction and row["reference_direction"] is None
    assert row["query_strand"] == strand
    assert calculate_blast_hsp_column_components(sheet)["summary"]["query_paired_coverage"] == 1/5


def test_lengths_unknown_are_not_zero_and_valid_local_coordinates_survive():
    sheet = extract(qlength=None, rlength=None)
    scores = calculate_blast_hsp_column_components(sheet)
    assert scores["summary"]["query_paired_units"] == 3
    assert scores["ratios"]["query_paired_coverage"] == {"numerator": 3, "denominator": None, "value": None}
    assert scores["component_status"]["query_paired_coverage"] == "unavailable"
    zero = calculate_blast_hsp_column_components(extract(qlength=0))
    assert zero["summary"]["paired_columns"] == 3
    assert zero["summary"]["query_paired_units"] is None
    assert zero["summary"]["query_paired_coverage"] is None


def mapping(path, length=4, scale=3):
    return {"version": "oriented_source_subject_path_v2", "units_per_symbol": scale,
            "symbol_length": length, "path": path}


def segment(start, end, strand="+"):
    return {"subject_ref": "synthetic_original_dna", "start": start, "end": end, "unit": "nt", "strand": strand}


@pytest.mark.parametrize("reverse", [False, True])
def test_split_original_codon_preserves_order_orientation_and_independent_local_coordinates(reverse):
    path = [segment(0, 4), segment(8, 16)]
    if reverse:
        path = [segment(8, 16, "-"), segment(0, 4, "-")]
    # Forward amino acid 1 spans the join; reverse amino acid 2 spans it.
    offset = 2 if reverse else 1
    sheet = extract(native("MKG*", "MKG*", query_to=4, hit_to=4, identity=4),
        qlength=4, rlength=4, offset=offset, limit=1,
        original_mappings={"query": mapping(path), "reference": None})
    row = sheet["columns"][0]
    expected = [segment(8, 10, "-"), segment(3, 4, "-")] if reverse else [segment(3, 4), segment(8, 10)]
    assert row["query_original_intervals"] == expected
    assert row["query_interval"] == [offset, offset + 1]
    assert row["query_mapping_status"] == "available"
    assert row["reference_original_intervals"] is None
    scores = calculate_blast_hsp_column_components(sheet)
    assert scores["summary"]["query_paired_units"] == 1
    assert scores["summary"]["query_paired_coverage"] == .25


def test_repeated_original_segments_are_not_merged_or_double_counted_as_local_units():
    m = mapping([segment(0, 3), segment(0, 3), segment(7, 10)], length=3)
    sheet = extract(qlength=3, original_mappings={"query": m, "reference": None})
    assert [row["query_original_intervals"] for row in sheet["columns"]] == [[segment(0, 3)], [segment(0, 3)], [segment(7, 10)]]
    assert calculate_blast_hsp_column_components(sheet)["summary"]["query_paired_units"] == 3


def test_mapping_length_conflict_is_separate_from_valid_local_geometry():
    m = mapping([segment(0, 9)], length=3)
    sheet = extract(qlength=5, original_mappings={"query": m, "reference": None})
    assert sheet["columns"][0]["query_mapping_status"] == "incompatible"
    assert sheet["columns"][0]["query_mapping_reason"] == "site_original_mapping_conflict"
    assert sheet["columns"][0]["query_original_intervals"] is None
    assert calculate_blast_hsp_column_components(sheet)["summary"]["query_paired_coverage"] == 3/5


@pytest.mark.parametrize("offset,limit", [(True, 1), (-1, 1), (0, False), (0, 0), (0, 4097)])
def test_structural_window_rejections(offset, limit):
    with pytest.raises(ValueError, match="bounded_blast_alignment_window_required"):
        extract(offset=offset, limit=limit)


@pytest.mark.parametrize("field,value", [("bit_score", float("nan")), ("evalue", float("inf")),
    ("qseq", ("M", "K")), ("extra", {1: "non_json_key"})])
def test_nonfinite_and_non_json_native_payload_rejected(field, value):
    with pytest.raises(ValueError, match="site_finite_json_required"):
        extract(native(**{field: value}))


def test_explicit_operand_identity_units_and_locator_validation():
    bad = operands()
    bad["query"]["length"] = 6
    with pytest.raises(ValueError, match="site_operand_identity_conflict"):
        extract(operands_input=bad)
    bad = operands()
    bad["query"]["unit"] = "nt"
    with pytest.raises(ValueError, match="site_operand_identity_conflict"):
        extract(operands_input=bad)
    bad = operands()
    bad["query"]["subject_ref"] = ""
    with pytest.raises(ValueError, match="site_operand_invalid"):
        extract(operands_input=bad)
    with pytest.raises(ValueError, match="site_source_invalid"):
        extract(source_input=source(provider="bvbrc"))
    with pytest.raises(ValueError, match="site_source_locator_invalid"):
        extract(source_input=source(native_locator={"report_ordinal": 0, "hit_ordinal": 0, "hsp_ordinal": True}))


def test_unknown_material_descriptor_keeps_native_program_coordinate_units():
    unknown = operands()
    unknown["query"].update(unit="symbol", molecule="unknown")
    sheet = extract(operands_input=unknown)
    assert sheet["operands"]["query"]["unit"] == "symbol"
    assert sheet["columns"][0]["query_unit"] == "aa"
    assert calculate_blast_hsp_column_components(sheet)["definitions"]["query_paired_units"]["unit"] == "aa"


@pytest.mark.parametrize("program,length,scale,end,status", [
    ("blastp", 5, 3, 15, "available"),
    ("blastx", 12, 1, 12, "available"),
    ("blastx", 12, 3, 36, "incompatible"),
])
def test_unknown_material_ancestry_uses_actual_native_coordinate_units(program, length, scale, end, status):
    unknown = operands(program, length, 5)
    unknown["query"].update(unit="symbol", molecule="unknown")
    hsp = native(query_to=9, query_frame=1) if program == "blastx" else native()
    sheet = extract(hsp, program=program, qlength=length, operands_input=unknown,
        original_mappings={"query": mapping([segment(0, end)], length=length, scale=scale), "reference": None})
    row = sheet["columns"][0]
    assert sheet["operands"]["query"]["unit"] == "symbol"
    assert row["query_mapping_status"] == status
    assert row["query_original_intervals"] == ([segment(0, 3)] if status == "available" else None)
    assert calculate_blast_hsp_column_components(sheet)["summary"]["query_paired_units"] == (9 if program == "blastx" else 3)


def test_complete_native_facts_and_supplied_inputs_are_copied_without_mutation():
    hsp = native(extra_native_metadata={"zero": 0, "unknown": None, "values": [1, 2, 3]})
    supplied_source = source()
    supplied_operands = operands()
    supplied_mappings = {"query": None, "reference": None}
    before = deepcopy([hsp, supplied_source, supplied_operands, supplied_mappings])
    sheet = extract(hsp, source_input=supplied_source, operands_input=supplied_operands,
                    original_mappings=supplied_mappings)
    assert [hsp, supplied_source, supplied_operands, supplied_mappings] == before
    sheet["native_input"]["extra_native_metadata"]["values"].append(4)
    sheet["source"]["native_locator"]["hit_ordinal"] = 9
    sheet["operands"]["query"]["length"] = 9
    sheet["original_mapping_inputs"]["query"] = "changed_copy"
    assert [hsp, supplied_source, supplied_operands, supplied_mappings] == before


@pytest.mark.parametrize("mutate", [
    lambda s: s["columns"][0].update(query_interval=[1, 2]),
    lambda s: s["columns"][0].update(column=1),
    lambda s: s["columns"][0].update(relationship="substituted"),
    lambda s: s["columns"].reverse(),
    lambda s: s["requested_window"].update(column_offset=1),
    lambda s: s["measured_counts"].update(paired_columns=True),
    lambda s: s["measured_counts"].update(paired_columns=3.0),
    lambda s: s["availability"].update(geometry="unavailable"),
    lambda s: s["inherited_native_measurements"]["native_scores"].update(score=999),
    lambda s: s.update(extra="not_in_contract"),
])
def test_saved_sheet_rejects_tampered_selector_rows_geometry_and_counts(mutate):
    sheet = extract()
    mutate(sheet)
    with pytest.raises(ValueError, match="blast_hsp_column_sheet_conflict"):
        calculate_blast_hsp_column_components(sheet)


def test_saved_sheet_recalculation_has_no_file_network_subprocess_or_model_calls(monkeypatch):
    sheet = json.loads(json.dumps(extract()))
    before = deepcopy(sheet)
    expected = calculate_blast_hsp_column_components(sheet)
    def forbidden(*args, **kwargs):
        raise AssertionError("pure_calculation_attempted_external_operation")
    with monkeypatch.context() as m:
        m.setattr(builtins, "open", forbidden)
        m.setattr(Path, "read_bytes", forbidden)
        m.setattr(Path, "read_text", forbidden)
        m.setattr(socket, "socket", forbidden)
        m.setattr(subprocess, "Popen", forbidden)
        assert calculate_blast_hsp_column_components(sheet) == expected
    assert sheet == before
    assert set(expected) == {"schema", "status", "summary", "ratios", "component_status", "issues", "definitions"}


def test_helper_does_not_change_existing_whole_hsp_counts_or_geometry():
    hsp = native(align_len=99)
    before = alignment_components(hsp, program="blastp", query_length=5, reference_length=5)
    view = blast_hsp_column_correspondence(hsp, program="blastp", query_length=5, reference_length=5)
    after = alignment_components(hsp, program="blastp", query_length=5, reference_length=5)
    assert before == after and before["geometry_available"]
    assert view["geometry_status"] == "incompatible" and len(view["columns"]) == 3


def retained_sheets(path, mode, resource):
    parsed = parse_blast_json(path.read_bytes(), mode=mode, resource=resource)
    # Recover actual native ordinals from the retained report, not filtered hsp arrays.
    outputs = parsed["native"]["document"]["BlastOutput2"]
    report = (outputs[0] if isinstance(outputs, list) else outputs)["report"]
    search = report["results"]["bl2seq"][0] if mode == "pairwise" else report["results"]["search"]
    result = []
    for hi, hit in enumerate(search["hits"]):
        for si, hsp in enumerate(hit["hsps"]):
            src = source(alignment_ref=f"retained_{mode}_hit_{hi}_hsp_{si}",
                source_ref=f"retained_{mode}_{resource}", native_artifact_ref=str(path.relative_to(ROOT)),
                native_version=report["version"], native_locator={"report_ordinal": 0, "hit_ordinal": hi, "hsp_ordinal": si})
            bound = operands(report["program"], search["query_len"], hit["len"])
            bound["query"]["subject_ref"] = f"retained_{mode}_query:{search['query_id']}"
            bound["reference"]["subject_ref"] = f"retained_{mode}_hit:{hi}"
            result.append(extract(hsp, program=report["program"], qlength=search["query_len"],
                rlength=hit["len"], source_input=src, operands_input=bound))
    return parsed, result


def test_retained_local_pairwise_native_json_has_checked_253_column_example():
    parsed, sheets = retained_sheets(ROOT / "tests/fixtures/blast_grading_inputs/native_pair_result.json", "pairwise", "local")
    assert parsed["mode"] == "pairwise" and len(sheets) == 1
    sheet = sheets[0]
    scores = calculate_blast_hsp_column_components(sheet)
    assert scores["summary"] == {"window_alignment_columns": 253, "paired_columns": 243,
        "identical_pairs": 238, "substituted_pairs": 5, "query_gap_columns": 0,
        "reference_gap_columns": 10, "query_paired_units": 243, "reference_paired_units": 243,
        "paired_identity": 238/243, "alignment_identity": 238/253,
        "query_paired_coverage": 243/253, "reference_paired_coverage": 1}
    assert sheet["source"]["native_version"] == "BLASTP 2.17.0+"
    assert sheet["inherited_native_measurements"]["native_scores"] == {"bit_score": 486.878, "score": 1252, "evalue": 0}


def test_retained_api_zip_preserves_all_native_hsp_ordinals_and_independent_counts():
    path = ROOT / "verification/w04_blast_graders_2026-10-24_001/live_api/result.body"
    parsed, sheets = retained_sheets(path, "database", "api")
    assert parsed["mode"] == "database"
    assert parsed["native"]["archive_member"] == {"ordinal": 1, "name": "DTKE1D4G016_1.json"}
    assert len(sheets) == 7
    # Hand-checked against each full native qseq/hseq and reported coordinates.
    expected = [(253, 253, 253, 0, 0, 0), (86, 71, 31, 40, 4, 11),
        (125, 101, 38, 63, 7, 17), (61, 52, 23, 29, 2, 7),
        (36, 36, 15, 21, 0, 0), (65, 45, 22, 23, 16, 4), (65, 45, 22, 23, 16, 4)]
    names = ("window_alignment_columns", "paired_columns", "identical_pairs", "substituted_pairs", "query_gap_columns", "reference_gap_columns")
    for index, (sheet, values) in enumerate(zip(sheets, expected)):
        scores = calculate_blast_hsp_column_components(sheet)
        assert tuple(scores["summary"][name] for name in names) == values
        assert sheet["source"]["native_locator"] == {"report_ordinal": 0, "hit_ordinal": index, "hsp_ordinal": 0}
        assert sheet["availability"]["geometry"] == "available"
        assert scores["ratios"]["query_paired_coverage"]["denominator"] == 253
    assert sheets[5]["source"] != sheets[6]["source"]  # Repeated strings remain separate selected HSPs.


def test_selected_native_hsp_ordinal_is_not_a_filtered_array_index():
    selected = native()
    report = {"BlastOutput2": [{"report": {"program": "blastp", "results": {"search": {
        "query_len": 5, "query_id": "synthetic_query", "hits": [{"len": 5,
            "description": [{"accession": "synthetic_reference"}], "hsps": [None, selected]}]}}}}]}
    parsed = parse_blast_json(json.dumps(report).encode(), mode="database", resource="api")
    assert len(parsed["hits"][0]["hsps"]) == 1
    selected_native = parsed["native"]["document"]["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["hsps"][1]
    source_with_gap = source(native_locator={"report_ordinal": 0, "hit_ordinal": 0, "hsp_ordinal": 1})
    sheet = extract(selected_native, source_input=source_with_gap)
    assert sheet["source"]["native_locator"]["hsp_ordinal"] == 1
    assert sheet["native_input"] == selected
    # The pure leaf accepts exactly the host-selected HSP; it never indexes a hit array.
    assert calculate_blast_hsp_column_components(sheet)["summary"]["paired_columns"] == 3
