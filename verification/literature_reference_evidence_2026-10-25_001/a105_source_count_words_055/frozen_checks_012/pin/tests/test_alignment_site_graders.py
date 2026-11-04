"""Pure reference-site examples; synthetic fixtures are separate from native PAFs."""
from copy import deepcopy
import builtins
import io
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.alignment_site_calculators import calculate_reference_site_components
from gene_annotation_episode.alignment_site_inputs import (
    extract_biopython_reference_sites, extract_minimap2_reference_sites, extract_phmmer_reference_sites,
)
from gene_annotation_episode.alignment_site_mapping import map_operand_interval
from gene_annotation_episode.minimap2_grading_inputs import PRESETS, parse_minimap2_paf_row
from gene_annotation_episode.read_mapping import compare_paf_sites
from gene_annotation_episode.sequence_mapping import extract_path, translation_mapping
from gene_annotation_episode.sequence_ops import compare_sites


ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "verification/tool_graders_minimap2_2026-10-24"


def operand(length, unit="aa", subject="input:query", molecule=None):
    return {"subject_ref": subject, "length": length, "unit": unit,
            "alignment_unit": "aa" if unit == "aa" else "nt",
            "molecule": molecule or ("protein" if unit == "aa" else "dna")}


def operands(qlen=10, rlen=12, unit="aa", molecule=None):
    return {"query": operand(qlen, unit, molecule=molecule),
            "reference": operand(rlen, unit, "reference:reference", molecule=molecule)}


def source(provider="biopython.alignment", version="synthetic", locator=None):
    return {"alignment_ref": "observation:alignment", "source_ref": "source:native",
        "native_artifact_ref": "artifact:native", "provider": provider,
        "format": {"biopython.alignment": "biopython_pairwise_json", "native.phmmer.alignment": "native_phmmer_alignment_json",
                   "minimap2.mapping": "minimap2_paf_row"}[provider],
        "native_version": version, "native_locator": locator or ({"line_number": 1, "row_start": 0, "row_end": 100}
            if provider == "minimap2.mapping" else {})}


def selection(positions):
    return {"kind": "reference_positions", "positions": positions}


def synthetic_gapped():
    return {"aligned": True, "native_score": 17.5, "query_length": 10,
        "reference_length": 12, "mode": "local", "matrix": "BLOSUM62", "gap_open": -2,
        "gap_extend": -.5, "biopython_version": "synthetic", "paired_positions": 5,
        "identical_positions": 4, "identity_fraction": 4/5, "query_coverage": 6/10,
        "reference_coverage": 6/12, "query_interval": [1, 7], "reference_interval": [3, 9],
        "coordinates": [[1, 4, 4, 5, 6, 7], [3, 6, 7, 8, 8, 9]],
        "aligned_query": "ACD-EFG", "aligned_reference": "ACTVE-G",
        "extra_native_metadata": {"retained": ["complete", 9]}}


def bio(native=None, positions=None, **kwargs):
    return extract_biopython_reference_sites(native or synthetic_gapped(), molecule="protein",
        selection=selection(positions or [3, 4, 5, 6, 7, 8, 0, 5]), operands=operands(), source=source(), **kwargs)


def phmmer_native():
    return {"query_length": 10, "reference_length": 12, "query_aligned": "acd.efg", "reference_aligned": "actve-g",
        "query_interval_aa_zero_based_half_open": [1, 7], "reference_interval_aa_zero_based_half_open": [3, 9],
        "paired_intervals": {"query": [[1, 5], [6, 7]], "reference": [[3, 6], [7, 9]]},
        "domain_bitscore": 0, "independent_domain_evalue": 0, "sequence_bitscore": -2.5,
        "native_inclusion_flag": False, "paired_residues": 5, "identical_paired_residues": 4}


def phmmer(native=None):
    return extract_phmmer_reference_sites(native or phmmer_native(), selection=selection([3, 4, 5, 6, 7, 8, 0, 5]),
        operands=operands(), source=source("native.phmmer.alignment"))


def paf(line="q\t7\t1\t6\t+\tr\t10\t2\t8\t3\t7\t0\tcg:Z:2M1I2D2M\tcs:Z:=C*gt+g-tc=GT"):
    return parse_minimap2_paf_row(line)


def minimap(row=None, query="ACTGGTA", reference="AACGTCGTAA", positions=None, **kwargs):
    row = row or paf()
    return extract_minimap2_reference_sites(row, preset="map-ont", native_version="synthetic",
        selection=selection(positions or list(range(row["reference_interval"][0], row["reference_interval"][1]))),
        query_metadata={"subject_ref": "read_subject:member1", "name": row["query_name"], "length": len(query), "sequence": query},
        reference_metadata={"subject_ref": "reference:reference", "name": row["reference_name"], "length": len(reference), "sequence": reference},
        source=source("minimap2.mapping"), **kwargs)


def segment(start, end, strand="+", subject="input:original", unit="nt"):
    return {"subject_ref": subject, "start": start, "end": end, "strand": strand, "unit": unit}


def test_reviewed_gapped_positions_duplicates_and_insertion_denominators():
    native = synthetic_gapped()
    sheet = bio(native)
    scores = calculate_reference_site_components(sheet)
    summary = scores["summary"]
    assert sheet["native_input"] == native and sheet["requested_positions"] == [3, 4, 5, 6, 7, 8, 0, 5]
    assert sheet["unique_requested_positions"] == [3, 4, 5, 6, 7, 8, 0]
    assert {key: summary[key] for key in ("requested_position_count", "unique_requested_position_count", "duplicate_requested_position_count",
        "identical_positions", "substituted_positions", "paired_positions", "query_gap_positions", "outside_alignment_positions")} == {
        "requested_position_count": 8, "unique_requested_position_count": 7, "duplicate_requested_position_count": 1,
        "identical_positions": 4, "substituted_positions": 1, "paired_positions": 5, "query_gap_positions": 1, "outside_alignment_positions": 1}
    assert summary["selected_paired_identity"] == 4/5
    assert scores["ratios"]["selected_alignment_identity"] == {"numerator": 4, "denominator": 7, "value": 4/7}
    assert summary["selected_reference_paired_fraction"] == 5/7
    assert summary["selected_reference_aligned_fraction"] == 6/7
    assert summary["selected_query_paired_coverage"] == 5/10
    assert summary["selected_reference_paired_coverage"] == 5/12
    insertion = sheet["insertions"][0]
    assert insertion["reference_boundary"] == 8 and insertion["query_interval"] == [5, 6]
    assert insertion["query_sequence"] == "F" and insertion["alignment_column_interval"] == [5, 6]
    assert insertion["query_original_intervals"] is None
    assert sheet["sites"][3]["query_original_intervals"] == []
    for old, new in zip(compare_sites(native, sheet["requested_positions"]), sheet["sites"]):
        assert old["query_position"] == new["query_position"]
        assert old["reference_residue"] == new["reference_symbol"]
        assert old["query_residue"] == new["query_symbol"]
    assert sheet["inherited_native_measurements"]["native_score"] == 17.5
    assert "native_score" not in summary


@pytest.mark.parametrize("molecule,mode", [(m, mode) for m in ("protein", "dna", "rna") for mode in ("local", "global")])
def test_declared_models_and_local_global_normalized_symbols(molecule, mode):
    # Explicit synthetic native adapter data; no new Biopython execution.
    start, length = (0, 4) if mode == "global" else (2, 8)
    q, r = ("ACDE", "ACNE") if molecule == "protein" else ("ATGC", "ATAC")
    native = {"aligned": True, "query_length": length, "reference_length": length, "mode": mode,
        "matrix": "synthetic", "gap_open": -2, "gap_extend": -1, "native_score": 3,
        "paired_positions": 4, "identical_positions": 3, "identity_fraction": .75,
        "query_coverage": 4/length, "reference_coverage": 4/length,
        "query_interval": [start, start+4], "reference_interval": [start, start+4],
        "coordinates": [[start, start+4], [start, start+4]], "aligned_query": q, "aligned_reference": r}
    sheet = extract_biopython_reference_sites(native, molecule=molecule, selection=selection(list(range(length))),
        operands=operands(length, length, "aa" if molecule == "protein" else "nt", molecule), source=source())
    score = calculate_reference_site_components(sheet)["summary"]
    assert score["identical_positions"] == 3 and score["substituted_positions"] == 1
    assert score["selected_query_paired_coverage"] == 4/length
    if molecule == "rna":
        assert sheet["symbol_interpretation"]["native_nucleotide_normalization"] == "U_to_T_before_alignment"
        assert sheet["sites"][start+1]["query_symbol"] == "T"
        assert sheet["sites"][start+1]["query_original_symbol"] is None


def test_phmmer_keeps_native_sequence_mode_and_does_not_invent_biopython_metadata():
    sheet = phmmer()
    scores = calculate_reference_site_components(sheet)
    assert sheet["mode"] == "native_phmmer_sequence_alignment"
    assert scores["summary"] == calculate_reference_site_components(bio())["summary"]
    assert sheet["inherited_native_measurements"]["domain_bitscore"] == 0
    assert sheet["inherited_native_measurements"]["sequence_bitscore"] == -2.5
    assert sheet["inherited_native_measurements"]["native_inclusion_flag"] is False
    assert "native_score" not in sheet["inherited_native_measurements"]
    assert sheet["native_parameters"] == {"program": "phmmer"}


@pytest.mark.parametrize("field,value", [("query_aligned", "ACD"), ("reference_aligned", "---.---"),
    ("query_interval_aa_zero_based_half_open", [7, 1]), ("paired_intervals", {"query": [[0, 5]], "reference": [[3, 8]]})])
def test_invalid_phmmer_geometry_is_unavailable(field, value):
    native = phmmer_native(); native[field] = value
    sheet = phmmer(native)
    assert sheet["status"] == "unavailable"
    assert calculate_reference_site_components(sheet)["summary"]["paired_positions"] is None


def test_reviewed_paf_hand_geometry_and_compatibility_projection():
    sheet = minimap()
    summary = calculate_reference_site_components(sheet)["summary"]
    assert summary["paired_positions"] == 4 and summary["identical_positions"] == 3
    assert summary["substituted_positions"] == 1 and summary["query_gap_positions"] == 2
    assert summary["selected_paired_identity"] == 3/4 and summary["selected_alignment_identity"] == 3/7
    assert summary["selected_query_paired_coverage"] == 4/7 and summary["selected_reference_paired_coverage"] == 4/10
    insertion = sheet["insertions"][0]
    assert insertion["reference_boundary"] == 4 and insertion["query_interval"] == [3, 4] and insertion["query_sequence"] == "G"
    old = compare_paf_sites(paf(), list(range(2, 8)), query="ACTGGTA", reference="AACGTCGTAA")
    for before, after in zip(old["sites"], sheet["sites"]):
        assert before["query_position"] == after["query_position"]
        assert before["reference_residue"] == after["reference_symbol"]
        assert before["query_residue"] == after["query_symbol"]
        assert {"gap": "query_gap"}.get(before["relationship"], before["relationship"]) == after["relationship"]


@pytest.mark.parametrize("encoding,scores,scale", [("phred33", [20, 0], "phred"), ("unspecified", [None, None], None),
    ("phred64", [20, 0], "phred"), ("solexa64", [20, -5], "solexa_log_odds")])
def test_reverse_read_quality_uses_original_member_indices(encoding, scores, scale):
    row = paf("q\t4\t0\t4\t-\tr\t4\t0\t4\t4\t4\t255\tcg:Z:4M\tcs:Z:=ACGT")
    quality = "!I?5" if encoding in ("phred33", "unspecified") else "@II T".replace(" ", "") if encoding == "phred64" else ";IIT"
    sheet = minimap(row, "ACGT", "ACGT", [0, 3], quality=quality, quality_encoding=encoding)
    a, b = sheet["sites"]
    assert [a["query_position"], b["query_position"]] == [3, 0]
    assert [a["query_symbol"], b["query_symbol"]] == ["A", "T"]
    assert [a["query_original_symbol"], b["query_original_symbol"]] == ["T", "A"]
    assert [a["query_quality_character"], b["query_quality_character"]] == [quality[3], quality[0]]
    assert [a["query_quality_score"], b["query_quality_score"]] == scores
    assert a["quality_scale"] == scale
    summary = calculate_reference_site_components(sheet)["summary"]
    assert summary["paired_positions"] == summary["identical_positions"] == 2
    assert summary["selected_query_paired_coverage"] == summary["selected_reference_paired_coverage"] == .5
    assert sheet["inherited_native_measurements"]["mapping_quality"] == 255
    assert sheet["inherited_native_measurements"]["usable_mapping_quality"] is None


def test_reference_skip_is_neither_deletion_nor_alignment_column():
    row = paf("q\t4\t0\t4\t+\tr\t7\t0\t7\t4\t4\t0\tcg:Z:2M3N2M")
    sheet = minimap(row, "ACGT", "ACNNNGT")
    scores = calculate_reference_site_components(sheet)
    assert scores["summary"]["paired_positions"] == 4
    assert scores["summary"]["reference_skip_positions"] == 3
    assert scores["summary"]["query_gap_positions"] == 0
    assert scores["ratios"]["selected_alignment_identity"]["denominator"] == 4
    assert scores["summary"]["selected_query_paired_coverage"] == 1
    assert scores["summary"]["selected_reference_paired_coverage"] == 4/7
    assert [r["alignment_column"] for r in sheet["sites"]] == [0, 1, None, None, None, 2, 3]
    assert sheet["availability"]["native_cs_equality"] is False
    assert sheet["inherited_native_measurements"]["usable_mapping_quality"] == 0


@pytest.mark.parametrize("positions,events", [([0], 1), ([1], 1), ([0, 1, 0], 2)])
def test_leading_trailing_insertions_selected_once_at_adjacent_boundaries(positions, events):
    row = paf("q\t6\t0\t6\t+\tr\t2\t0\t2\t2\t6\t20\tcg:Z:1I1I2M2I\tcs:Z:+tt=AC+gg")
    sheet = minimap(row, "TTACGG", "AC", positions)
    summary = calculate_reference_site_components(sheet)["summary"]
    assert summary["selected_insertion_events"] == events
    assert summary["inserted_query_positions"] == 2*events
    assert len(sheet["insertions"]) == events
    if events == 2:
        assert [r["alignment_column_interval"] for r in sheet["insertions"]] == [[0, 2], [4, 6]]


def test_reverse_insertion_keeps_ascending_bounds_and_oriented_symbols_and_quality():
    row = paf("q\t6\t0\t6\t-\tr\t2\t0\t2\t2\t6\t20\tcg:Z:2I2M2I\tcs:Z:+tt=AC+gg")
    sheet = minimap(row, "CCGTAA", "AC", [0, 1], quality="!5?IJK", quality_encoding="phred33")
    assert [r["query_interval"] for r in sheet["insertions"]] == [[4, 6], [0, 2]]
    assert [r["query_sequence"] for r in sheet["insertions"]] == ["TT", "GG"]
    assert [r["query_quality_characters"] for r in sheet["insertions"]] == ["KJ", "5!"]


def test_original_ambiguity_symbols_are_not_normalized_cs_identity():
    row = paf("q\t1\t0\t1\t+\tr\t1\t0\t1\t0\t0\t0\tcg:Z:1M\tcs:Z:=N\tnn:i:1")
    sheet = minimap(row, "Y", "R")
    summary = calculate_reference_site_components(sheet)["summary"]
    assert summary["identical_positions"] == 0 and summary["substituted_positions"] == 1
    assert sheet["sites"][0]["query_symbol"] == "Y" and sheet["sites"][0]["reference_symbol"] == "R"


def test_wrong_same_length_sequence_is_not_accepted_from_normal_geometry():
    sheet = minimap(query="AGTGGTA")
    scores = calculate_reference_site_components(sheet)
    assert sheet["status"] == "unavailable" and scores["summary"]["unavailable_positions"] == 6
    assert scores["summary"]["identical_positions"] is None
    assert scores["summary"]["selected_query_paired_coverage"] is None
    assert {"code": "site_operand_identity_conflict"} in sheet["issues"]
    assert scores["observed_subset_counts"]["paired_positions"] == 0


@pytest.mark.parametrize("quality,encoding,code", [("!", "phred33", "site_quality_length_conflict"),
    ("!!!!!!!", "phred64", "site_quality_character_conflict")])
def test_invalid_quality_does_not_erase_valid_sequence_correspondence(quality, encoding, code):
    sheet = minimap(quality=quality, quality_encoding=encoding)
    assert {"code": code} in sheet["issues"]
    assert all(row["query_quality_score"] is None for row in sheet["sites"])
    assert calculate_reference_site_components(sheet)["summary"]["paired_positions"] == 4


def test_unknown_quality_encoding_is_structural_error():
    with pytest.raises(ValueError, match="site_quality_encoding_invalid"):
        minimap(quality_encoding="guess")


def test_split_codon_order_reverse_and_repeated_segments_are_preserved():
    path = extract_path([segment(0, 16)], [{"start": 0, "end": 4}, {"start": 8, "end": 16}])
    mapping = translation_mapping(path, start=0, end=12, strand="+", protein_length=4)
    assert map_operand_interval(operand(4), mapping, [1, 2]) == {
        "status": "available", "intervals": [segment(3, 4), segment(8, 10)], "reason": None}
    reverse = translation_mapping(path, start=0, end=12, strand="-", protein_length=4)
    assert map_operand_interval(operand(4), reverse, [2, 3])["intervals"] == [segment(8, 10, "-"), segment(3, 4, "-")]
    repeated = {"version": "oriented_source_subject_path_v2", "units_per_symbol": 1,
        "symbol_length": 4, "path": [segment(10, 12), segment(10, 12)]}
    assert map_operand_interval(operand(4, "nt"), repeated, [0, 4])["intervals"] == repeated["path"]


def test_mapping_missing_incompatible_and_gap_states_are_separate():
    assert map_operand_interval(operand(3), None, None) == {"status": "not_applicable", "intervals": [], "reason": None}
    assert map_operand_interval(operand(3), None, [1, 2]) == {"status": "unavailable", "intervals": None,
        "reason": "site_original_mapping_unavailable"}
    mapping = translation_mapping([segment(0, 12)], start=0, end=12, strand="+", protein_length=4)
    assert map_operand_interval(operand(3), mapping, [1, 2])["status"] == "incompatible"
    assert map_operand_interval(operand(4, "nt"), mapping, [1, 2])["status"] == "incompatible"
    original = deepcopy(mapping)
    map_operand_interval(operand(4), mapping, [0, 4])
    assert mapping == original
    sheet = bio(original_mappings={"query": None, "reference": None})
    assert calculate_reference_site_components(sheet)["summary"]["selected_query_paired_coverage"] == .5


def test_attached_original_mapping_uses_actual_derived_protein_length():
    mapping = translation_mapping([segment(0, 4), segment(8, 34)], start=0, end=30, strand="+", protein_length=10)
    sheet = bio(original_mappings={"query": mapping, "reference": None})
    assert sheet["sites"][0]["query_original_intervals"] == [segment(3, 4), segment(8, 10)]
    assert sheet["sites"][0]["query_mapping_status"] == "available"
    assert sheet["sites"][0]["reference_original_intervals"] is None


@pytest.mark.parametrize("change", [lambda n: n.update(coordinates=None),
    lambda n: n.update(coordinates=[[7, 1], [3, 9]]), lambda n: n.update(aligned_query="ACD"),
    lambda n: n.update(aligned_query="A--DEFG", aligned_reference="A--DEFG")])
def test_missing_or_conflicting_geometry_never_becomes_zero_sites(change):
    native = synthetic_gapped(); change(native)
    sheet = bio(native)
    scores = calculate_reference_site_components(sheet)
    assert sheet["status"] == "unavailable"
    assert scores["summary"]["unavailable_positions"] == 7
    assert scores["summary"]["paired_positions"] is None
    assert scores["summary"]["selected_paired_identity"] is None
    assert sheet["native_input"]["native_score"] == 17.5
    assert all(row["query_original_intervals"] is None for row in sheet["sites"])


def test_no_alignment_and_outside_only_are_known_zero_with_undefined_identity():
    native = {"aligned": False, "mode": "local", "matrix": "BLOSUM62", "query_length": 10, "reference_length": 12}
    sheet = bio(native)
    score = calculate_reference_site_components(sheet)
    assert sheet["status"] == "no_alignment" and score["summary"]["outside_alignment_positions"] == 7
    assert score["summary"]["paired_positions"] == 0 and score["summary"]["selected_query_paired_coverage"] == 0
    assert score["summary"]["selected_paired_identity"] is None
    assert score["component_status"]["selected_paired_identity"] == "not_applicable"
    outside = calculate_reference_site_components(bio(positions=[0, 11]))
    assert outside["summary"]["outside_alignment_positions"] == 2 and outside["summary"]["paired_positions"] == 0


@pytest.mark.parametrize("selected", [selection([True]), selection([-1]), selection([12]), selection([]),
    {"kind": "reference_window", "start": 4, "end": 4}, {"kind": "reference_window", "start": 0, "end": 13},
    {"kind": "reference_positions", "positions": [0], "extra": 1}])
def test_invalid_selector_rejected(selected):
    with pytest.raises(ValueError):
        extract_biopython_reference_sites(synthetic_gapped(), molecule="protein", selection=selected,
            operands=operands(), source=source())


def test_window_request_is_preserved_not_replaced_with_positions():
    selected = {"kind": "reference_window", "start": 3, "end": 9}
    sheet = extract_biopython_reference_sites(synthetic_gapped(), molecule="protein", selection=selected,
        operands=operands(), source=source())
    assert sheet["selection"] == selected and sheet["requested_positions"] == list(range(3, 9))
    assert calculate_reference_site_components(sheet)["summary"]["duplicate_requested_position_count"] == 0


@pytest.mark.parametrize("change", [lambda s: s["sites"][0].update(reference_position=4),
    lambda s: s["sites"][0].update(request_ordinal=1), lambda s: s["sites"][0].update(query_interval=[2, 3]),
    lambda s: s["sites"][0].update(relationship="substituted"), lambda s: s["selection"]["positions"].reverse(),
    lambda s: s["insertions"][0].update(reference_boundary=7), lambda s: s["measured_counts"].update(paired_positions=6),
    lambda s: s.update(requested_positions=[3])])
def test_saved_sheet_tampering_rejected(change):
    sheet = bio(); change(sheet)
    with pytest.raises(ValueError, match="reference_site_sheet_components_invalid"):
        calculate_reference_site_components(sheet)


@pytest.mark.parametrize("change", [lambda s: s["sites"][0].update(request_ordinal=False),
    lambda s: s["sites"][0].update(reference_position=3.0),
    lambda s: s["measured_counts"].update(duplicate_requested_position_count=True)])
def test_saved_sheet_validation_does_not_equate_booleans_integers_or_floats(change):
    sheet = bio(); change(sheet)
    with pytest.raises(ValueError, match="reference_site_sheet_components_invalid"):
        calculate_reference_site_components(sheet)


def test_phmmer_malformed_native_measurement_preserves_local_correspondence():
    native = phmmer_native(); native["domain_bitscore"] = "unavailable"
    native["paired_residues"] = True
    sheet = phmmer(native)
    assert sheet["inherited_native_measurements"]["domain_bitscore"] is None
    assert sheet["inherited_native_measurements"]["paired_residues"] is None
    assert sheet["native_input"] == native
    assert calculate_reference_site_components(sheet)["summary"]["paired_positions"] == 5


def test_finite_boundary_source_identity_and_operand_lengths_are_checked():
    native = synthetic_gapped(); native["native_score"] = float("inf")
    with pytest.raises(ValueError, match="site_finite_json_required"):
        bio(native)
    bad = operands(); bad["query"]["length"] = 11
    with pytest.raises(ValueError, match="site_operand_identity_conflict"):
        extract_biopython_reference_sites(synthetic_gapped(), molecule="protein", selection=selection([3]), operands=bad, source=source())
    badsource = source(); badsource["provider"] = "foreign"
    with pytest.raises(ValueError, match="site_source_invalid"):
        extract_biopython_reference_sites(synthetic_gapped(), molecule="protein", selection=selection([3]), operands=operands(), source=badsource)


def test_missing_operand_length_keeps_local_counts_but_not_coverage_denominator():
    bound = operands(); bound["query"]["length"] = None
    sheet = extract_biopython_reference_sites(synthetic_gapped(), molecule="protein", selection=selection([3, 4]),
        operands=bound, source=source())
    scores = calculate_reference_site_components(sheet)
    assert scores["summary"]["paired_positions"] == 2
    assert scores["ratios"]["selected_query_paired_coverage"] == {"numerator": 2, "denominator": None, "value": None}
    assert scores["summary"]["selected_reference_paired_coverage"] == 2/12


@pytest.mark.parametrize("change,code", [
    (lambda args: args["query_metadata"].update(name="same_length_wrong_name"), "site_operand_identity_conflict"),
    (lambda args: args["source"]["native_locator"].update(row_end=0), "site_native_locator_invalid"),
    (lambda args: args["source"]["native_locator"].update(line_number=True), "site_native_locator_invalid"),
    (lambda args: args["query_metadata"].update(subject_ref=""), "site_operand_metadata_invalid"),
    (lambda args: args["source"].update(native_version="other"), "site_native_version_conflict"),
])
def test_mapping_names_locators_and_versions_are_not_guessed(change, code):
    args = {"native_row": paf(), "preset": "map-ont", "native_version": "synthetic", "selection": selection([2]),
        "query_metadata": {"subject_ref": "read_subject:member1", "name": "q", "length": 7, "sequence": "ACTGGTA"},
        "reference_metadata": {"subject_ref": "reference:reference", "name": "r", "length": 10, "sequence": "AACGTCGTAA"},
        "source": source("minimap2.mapping")}
    change(args)
    with pytest.raises(ValueError, match=code):
        extract_minimap2_reference_sites(**args)


def test_explicit_read_member_identity_stays_separate_when_native_names_repeat():
    first = minimap()
    data = deepcopy(first["native_input"])
    data["query_metadata"]["subject_ref"] = "read_subject:member2"
    second = extract_minimap2_reference_sites(**data, preset="map-ont", native_version="synthetic",
        selection=first["selection"], source=first["source"])
    assert first["operands"]["query"]["subject_ref"] == "read_subject:member1"
    assert second["operands"]["query"]["subject_ref"] == "read_subject:member2"
    # Authentication of that supplied member and its quality bytes is the host's
    # responsibility; the pure function never joins or merges by repeated title.
    assert calculate_reference_site_components(first)["summary"] == calculate_reference_site_components(second)["summary"]


def test_native_cg_cs_conflict_and_missing_traceback_keep_unavailable_rows():
    row = paf(); row["tags"][0]["value"] = "5M"
    sheet = minimap(row)
    assert sheet["status"] == "unavailable"
    assert calculate_reference_site_components(sheet)["summary"]["paired_positions"] is None
    row = paf(); row["tags"] = []; row.pop("native_line"); row.pop("cigar"); row.pop("cs"); row.pop("base_alignment_available")
    sheet = minimap(row)
    assert {"code": "site_native_geometry_unavailable"} in sheet["issues"]


def fasta(path):
    result, name = {}, None
    for line in path.read_text().splitlines():
        if line.startswith(">"):
            name = line[1:].split()[0]; result[name] = ""
        else:
            result[name] += line
    return result


def retained_native_sheets(preset):
    directory = NATIVE / ("native_"+preset.replace(":", "_"))
    queries, references = fasta(directory/"queries.fasta"), fasta(directory/"references.fasta")
    version = (NATIVE/"version/stdout").read_text().strip()
    offset = 0
    for ordinal, line in enumerate((directory/"mappings.paf").read_bytes().splitlines(keepends=True), 1):
        row = parse_minimap2_paf_row(line, native_version=version)
        locator = {"line_number": ordinal, "row_start": offset, "row_end": offset+len(line)}
        offset += len(line)
        q, r = queries[row["query_name"]], references[row["reference_name"]]
        yield extract_minimap2_reference_sites(row, preset=preset, native_version=version,
            selection={"kind": "reference_window", "start": row["reference_interval"][0], "end": row["reference_interval"][1]},
            query_metadata={"subject_ref": "input:"+row["query_name"], "name": row["query_name"], "length": len(q), "sequence": q},
            reference_metadata={"subject_ref": "reference:"+row["reference_name"], "name": row["reference_name"], "length": len(r), "sequence": r},
            source=source("minimap2.mapping", version, locator))


@pytest.mark.parametrize("preset", PRESETS)
def test_retained_actual_native_pafs_all_six_presets_without_execution(preset):
    sheets = list(retained_native_sheets(preset))
    assert len(sheets) == 3
    for sheet in sheets:
        scores = calculate_reference_site_components(sheet)
        summary = scores["summary"]
        row = sheet["native_input"]["native_row"]
        assert sheet["native_parameters"]["preset"] == preset
        assert sheet["source"]["native_version"] == "2.31-r1302"
        if row["query_name"] == "exact":
            assert summary["paired_positions"] == summary["identical_positions"] == 2000
            assert summary["query_gap_positions"] == summary["inserted_query_positions"] == 0
        else:
            assert summary["paired_positions"] == 2397 and summary["identical_positions"] == 2392
            assert summary["substituted_positions"] == 5 and summary["query_gap_positions"] == 3
            assert summary["inserted_query_positions"] == summary["selected_insertion_events"] == 1
            assert scores["ratios"]["selected_alignment_identity"]["denominator"] == 2401
            assert summary["selected_query_paired_coverage"] == 2397/2398
            assert summary["selected_reference_paired_coverage"] == 2397/3200
            ambiguous = next(site for site in sheet["sites"] if site["reference_position"] == 1400)
            assert ambiguous["reference_symbol"] == "R" and ambiguous["query_symbol"] == "Y"
            assert ambiguous["relationship"] == "substituted"
        assert len(sheet["sites"]) > 12
        assert row["native_line"].count("\t") >= 11


def test_saved_sheets_recalculate_without_file_network_subprocess_or_aligner(monkeypatch):
    sheets = [bio(), phmmer(), minimap(), *retained_native_sheets("map-ont")]
    sheets = json.loads(json.dumps(sheets))
    before = deepcopy(sheets)
    expected = [calculate_reference_site_components(sheet) for sheet in sheets]
    def forbidden(*args, **kwargs):
        raise AssertionError("calculation must use saved data only")
    from gene_annotation_episode import sequence_ops
    with monkeypatch.context() as blocked:
        for obj, name in ((builtins, "open"), (io, "open"), (socket, "socket"), (socket, "create_connection"),
                          (subprocess, "run"), (subprocess, "Popen"), (sequence_ops, "align_pair")):
            blocked.setattr(obj, name, forbidden)
        actual = [calculate_reference_site_components(sheet) for sheet in sheets]
    assert actual == expected and sheets == before

