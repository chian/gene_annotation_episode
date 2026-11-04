"""Actual tiny translations and explicitly labelled damaged-result fixtures."""
from copy import deepcopy
from importlib.metadata import version
import builtins
import io
import json
from pathlib import Path
import socket
import subprocess
import warnings

from Bio.Data import CodonTable
from Bio.Seq import Seq
import pytest

from gene_annotation_episode import sequence_ops
from gene_annotation_episode.sequence_mapping import VERSION
from gene_annotation_episode.sequence_translation_grader import (
    SHEET_SCHEMA, build_translation_sheet, calculate_translation_scores, grade_translation,
)


def snapshot(code):
    table = CodonTable.unambiguous_dna_by_id[code]
    return {"code": code, "names": list(table.names), "start_codons": list(table.start_codons),
        "stop_codons": list(table.stop_codons), "forward_table": dict(table.forward_table),
        "biopython_version": version("biopython")}


def segment(start, end, subject="reference:original", strand="+", unit="nt"):
    return {"subject_ref": subject, "start": start, "end": end, "unit": unit, "strand": strand}


def mapping(length, path=None):
    return {"version": VERSION, "units_per_symbol": 1, "symbol_length": length,
        "path": path if path is not None else [segment(0, length)]}


def actual(sequence="ATGTAGAAATAACC", **parameters):
    request = {"code": 1, "strand": "+", "frame": 0, "start": 0, "end": len(sequence), "cds": False, **parameters}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        native = sequence_ops.translate(sequence, **request)
    return native, {"input_sequence": sequence, "subject_ref": "product:supplied-view",
        "parent_mapping": mapping(len(sequence)), "request": request, "genetic_code": snapshot(request["code"])}


def without_native_snapshot(native):
    native.pop("genetic_code_snapshot", None)


def test_independently_counted_native_stops_trailing_and_numerical_definitions():
    native, operands = actual()
    result = grade_translation(native, **operands)
    assert native["sequence"] == "M*K*"
    assert result["scores"]["summary"] == {
        "input_length_nt": 14, "selected_length_nt": 14, "frame_skipped_nt": 0,
        "translated_length_nt": 12, "trailing_untranslated_bases": 2, "translated_codon_count": 4,
        "output_symbol_count": 4, "amino_acid_symbol_count": 2, "internal_stop_count": 1,
        "terminal_stop_symbol_count": 1, "omitted_terminal_stop_codon_count": 0,
        "ambiguous_codon_count": 0, "ambiguous_output_symbol_count": 0, "mapped_output_symbol_count": 4,
        "compatible_codon_count": 4, "incompatible_codon_count": 0, "unknown_codon_count": 0,
        "selected_input_fraction": 1.0, "selected_input_fraction_denominator_nt": 14,
        "invalid_output_symbol_count": 0}
    assert result["sheet"]["geometry"]["trailing_interval"] == [12, 14]
    assert result["sheet"]["geometry"]["trailing_source_intervals"] == [segment(12, 14)]
    assert result["scores"]["status"] == "complete"
    assert set(result["scores"]["summary"]) <= result["scores"]["definitions"].keys()


@pytest.mark.parametrize("strand,frame,protein,span,first,skipped,trailing", [
    ("+", 0, "MK*P", [2, 14], [2, 5], [2, 2], [14, 14]),
    ("+", 1, "*NN", [3, 12], [3, 6], [2, 3], [12, 14]),
    ("+", 2, "EIT", [4, 13], [4, 7], [2, 4], [13, 14]),
    ("-", 0, "GLFH", [2, 14], [11, 14], [14, 14], [2, 2]),
    ("-", 1, "GYF", [4, 13], [10, 13], [13, 14], [2, 4]),
    ("-", 2, "VIS", [3, 12], [9, 12], [12, 14], [2, 3]),
])
def test_all_six_frames_on_actual_native_outputs(strand, frame, protein, span, first, skipped, trailing):
    native, operands = actual("CCATGAAATAACCCGG", strand=strand, frame=frame, start=2, end=14)
    grading = grade_translation(native, **operands)
    sheet, scores = grading["sheet"], grading["scores"]["summary"]
    assert native["sequence"] == protein
    assert sheet["geometry"]["translated_interval"] == span
    assert sheet["geometry"]["frame_skipped_interval"] == skipped
    assert sheet["geometry"]["trailing_interval"] == trailing
    assert sheet["codons"][0]["parent_interval"] == first
    assert sheet["codons"][0]["original_source_intervals"] == [segment(*first, strand=strand)]
    assert scores["compatible_codon_count"] == len(protein)
    assert scores["mapped_output_symbol_count"] == len(protein)
    assert scores["selected_input_fraction"] == 12/16
    assert scores["selected_input_fraction_denominator_nt"] == 16


@pytest.mark.parametrize("code,protein,stops", [(1, "I*R", 1), (2, "MW*", 0)])
def test_code_reassignment_uses_frozen_native_table(code, protein, stops):
    native, operands = actual("ATATGAAGA", code=code)
    result = grade_translation(native, **operands)
    assert native["sequence"] == protein
    assert result["scores"]["summary"]["compatible_codon_count"] == 3
    assert result["scores"]["summary"]["internal_stop_count"] == stops


def test_alternative_cds_start_and_split_omitted_stop_remain_separate():
    native, operands = actual("GTGAAAGGGTAA", code=11, cds=True)
    operands["parent_mapping"] = mapping(12, [segment(100, 110, "reference:a"), segment(20, 22, "reference:b")])
    grading = grade_translation(native, **operands)
    sheet, scores = grading["sheet"], grading["scores"]["summary"]
    assert native["sequence"] == "MKG"
    assert scores["translated_codon_count"] == 4
    assert scores["output_symbol_count"] == scores["amino_acid_symbol_count"] == 3
    assert scores["terminal_stop_symbol_count"] == scores["internal_stop_count"] == 0
    assert scores["omitted_terminal_stop_codon_count"] == 1
    assert scores["compatible_codon_count"] == 4
    assert scores["mapped_output_symbol_count"] == 3
    assert sheet["codons"][0]["table_operands"]["forward_symbols"] == ["V"]
    assert sheet["codons"][0]["table_operands"]["expected_symbol"] == "M"
    omitted = sheet["codons"][-1]
    assert omitted["output_position"] is None and omitted["product_symbol"] is None
    assert omitted["original_source_intervals"] == [segment(109, 110, "reference:a"), segment(20, 22, "reference:b")]


@pytest.mark.parametrize("code,sequence,protein,internal", [
    (27, "ATGTGATGA", "MW", "W"), (28, "ATGTAATGA", "MQ", "Q"), (31, "ATGTAATAG", "ME", "E")])
def test_dual_coding_stops_use_actual_context(code, sequence, protein, internal):
    native, operands = actual(sequence, code=code, cds=True)
    result = grade_translation(native, **operands)
    assert native["sequence"] == protein
    assert result["scores"]["summary"]["compatible_codon_count"] == 3
    assert result["scores"]["summary"]["omitted_terminal_stop_codon_count"] == 1
    assert result["sheet"]["codons"][1]["table_operands"]["expected_symbol"] == internal
    assert result["sheet"]["codons"][1]["table_operands"]["dual_coding_codons"] == [sequence[3:6]]
    ordinary_native, ordinary_operands = actual(sequence, code=code)
    ordinary = grade_translation(ordinary_native, **ordinary_operands)
    assert ordinary["scores"]["summary"]["compatible_codon_count"] == 3
    assert ordinary["scores"]["summary"]["omitted_terminal_stop_codon_count"] == 0
    assert ordinary["scores"]["summary"]["terminal_stop_symbol_count"] == 0


def test_ambiguous_codons_include_resolved_residues_b_z_j_possible_stops_and_x():
    native, operands = actual("GCNRAYSARWTAATNTARTANNNN")
    result = grade_translation(native, **operands)
    assert native["sequence"] == "ABZJX*XX"
    assert result["scores"]["summary"]["ambiguous_codon_count"] == 8
    assert result["scores"]["summary"]["ambiguous_output_symbol_count"] == 6
    assert result["scores"]["summary"]["compatible_codon_count"] == 8
    assert result["scores"]["summary"]["internal_stop_count"] == 1
    assert result["sheet"]["codons"][5]["table_operands"]["expanded_codons"] == ["TAA", "TAG"]


def test_ambiguous_cds_start_and_stop_membership_is_all_expansions():
    native, operands = actual("HTGAAATAR", code=11, cds=True)
    result = grade_translation(native, **operands)
    assert native["sequence"] == "MK"
    assert result["scores"]["summary"]["ambiguous_codon_count"] == 2
    assert result["scores"]["summary"]["ambiguous_output_symbol_count"] == 0
    assert result["scores"]["summary"]["compatible_codon_count"] == 3
    assert result["sheet"]["codons"][0]["table_operands"]["start_membership"] == [True, True, True]


def test_lowercase_rna_preserves_original_symbols_before_normalization():
    native, operands = actual("augAAAuaa")
    result = grade_translation(native, **operands)
    assert result["sheet"]["input_sequence"] == "augAAAuaa"
    assert result["sheet"]["codons"][0]["parent_symbols"] == "aug"
    assert result["sheet"]["codons"][0]["codon"] == "ATG"
    assert result["scores"]["summary"]["compatible_codon_count"] == 3


@pytest.mark.parametrize("strand,split_index,expected_paths", [
    ("+", 1, [segment(103, 104, "source:a"), segment(26, 28, "source:b", "-")]),
    ("-", 2, [segment(26, 28, "source:b"), segment(103, 104, "source:a", "-")])])
def test_explicit_split_reversed_ancestry_keeps_source_identity_and_order(strand, split_index, expected_paths):
    native, operands = actual("ATGAAAGGGTAA", strand=strand)
    # Synthetic supplied ancestry with independent physical strings. Translation
    # itself is native; no identity or mapping is inferred from matching lengths.
    operands["parent_mapping"] = mapping(12, [segment(100, 104, "source:a"), segment(20, 28, "source:b", "-")])
    result = grade_translation(native, **operands)
    row = result["sheet"]["codons"][split_index]
    assert row["original_source_intervals"] == expected_paths
    assert row["codon"] == ("AAA" if strand == "+" else "TTT")
    assert result["scores"]["summary"]["mapped_output_symbol_count"] == 4
    assert result["sheet"]["subject_ref"] == "product:supplied-view"


def test_missing_mapping_never_uses_subject_name_or_equal_lengths_to_invent_ancestry():
    native, operands = actual()
    operands["parent_mapping"] = None
    result = grade_translation(native, **operands)
    assert result["scores"]["summary"]["mapped_output_symbol_count"] is None
    assert result["scores"]["summary"]["compatible_codon_count"] == 4
    assert all(row["original_source_intervals"] is None for row in result["sheet"]["codons"])
    assert result["scores"]["component_status"]["parent_mapping"]["state"] == "missing"


@pytest.mark.parametrize("damaged", [
    {"version": "wrong"},
    {"version": VERSION, "units_per_symbol": 1, "symbol_length": 3, "path": [segment(0, 3)]},
    {"version": VERSION, "units_per_symbol": 3, "symbol_length": 14, "path": [segment(0, 42)]},
    {"version": VERSION, "units_per_symbol": 1, "symbol_length": 14, "path": [segment(0, 14, unit="aa")]},
    {"version": VERSION, "units_per_symbol": 1, "symbol_length": 14, "path": [segment(0, 14, unit=[])]},
])
def test_labelled_invalid_mapping_preserves_other_valid_numbers(damaged):
    native, operands = actual()
    operands["parent_mapping"] = damaged
    result = grade_translation(native, **operands)
    assert result["scores"]["summary"]["mapped_output_symbol_count"] is None
    assert result["scores"]["component_status"]["parent_mapping"]["state"] == "incompatible"
    assert result["scores"]["summary"]["output_symbol_count"] == 4


def test_missing_table_keeps_geometry_product_stops_and_cds_omission():
    native, operands = actual("GTGAAATAA", code=11, cds=True)
    operands["genetic_code"] = None
    result = grade_translation(native, **operands)
    summary = result["scores"]["summary"]
    assert summary["translated_length_nt"] == 9 and summary["output_symbol_count"] == 2
    assert summary["terminal_stop_symbol_count"] == 0
    assert summary["omitted_terminal_stop_codon_count"] == 1
    assert summary["compatible_codon_count"] == summary["incompatible_codon_count"] == 0
    assert summary["unknown_codon_count"] == 3 and summary["mapped_output_symbol_count"] == 2


def test_incomplete_table_only_invalidates_dependent_codons():
    native, operands = actual("ATGAAATAA")
    without_native_snapshot(native)
    del operands["genetic_code"]["forward_table"]["AAA"]
    result = grade_translation(native, **operands)
    assert result["scores"]["summary"]["compatible_codon_count"] == 2
    assert result["scores"]["summary"]["unknown_codon_count"] == 1
    assert result["sheet"]["codons"][1]["compatibility_reason"] == "codon_reference_entry_unavailable"
    assert result["scores"]["component_status"]["genetic_code"]["state"] == "incomplete"


@pytest.mark.parametrize("field,unknown", [("start_codons", 1), ("stop_codons", 1), ("forward_table", 1)])
def test_missing_table_parts_preserve_independent_cds_contexts(field, unknown):
    native, operands = actual("GTGAAATAA", code=11, cds=True)
    without_native_snapshot(native)
    del operands["genetic_code"][field]
    result = grade_translation(native, **operands)
    assert result["scores"]["summary"]["unknown_codon_count"] == unknown
    assert result["scores"]["summary"]["compatible_codon_count"] == 3 - unknown
    assert result["scores"]["summary"]["output_symbol_count"] == 2


def test_repeated_physical_source_path_is_retained_as_two_output_occurrences():
    native, operands = actual("ATGATG")
    operands["parent_mapping"] = mapping(6, [segment(10, 13), segment(10, 13)])
    result = grade_translation(native, **operands)
    assert [row["original_source_intervals"] for row in result["sheet"]["codons"]] == [
        [segment(10, 13)], [segment(10, 13)]]
    assert result["scores"]["summary"]["mapped_output_symbol_count"] == 2
    assert result["scores"]["summary"]["translated_length_nt"] == 6


@pytest.mark.parametrize("corrupt,states", [
    ("AAAAAATAA", ["incompatible", "compatible", "compatible"]),
    ("GTGTAATAA", ["compatible", "incompatible", "compatible"]),
    ("GTGAAAAAA", ["compatible", "compatible", "incompatible"]),
])
def test_labelled_impossible_cds_inputs_do_not_pass_context_checks(corrupt, states):
    native, operands = actual("GTGAAATAA", code=11, cds=True)
    operands["input_sequence"] = corrupt  # Explicit incompatible source/native pairing.
    result = grade_translation(native, **operands)
    assert [row["compatibility"] for row in result["sheet"]["codons"]] == states
    assert result["scores"]["summary"]["incompatible_codon_count"] == 1
    if states[-1] == "incompatible":
        assert result["scores"]["summary"]["omitted_terminal_stop_codon_count"] is None


def test_unrelated_native_snapshot_does_not_override_explicit_execution_reference():
    native, operands = actual("ATGAAA")
    native["genetic_code_snapshot"] = snapshot(2)
    result = grade_translation(native, **operands)
    assert result["scores"]["summary"]["unknown_codon_count"] == 2
    assert result["scores"]["component_status"]["genetic_code"]["reason"] == "native_genetic_code_snapshot_conflict"


@pytest.mark.parametrize("field,value", [("code", 2), ("biopython_version", "not-the-executed-version")])
def test_wrong_reference_identity_or_version_never_uses_current_table(field, value):
    native, operands = actual("ATGAAATAA")
    operands["genetic_code"][field] = value
    result = grade_translation(native, **operands)
    assert result["scores"]["summary"]["unknown_codon_count"] == 3
    assert result["scores"]["summary"]["output_symbol_count"] == 3
    assert result["scores"]["component_status"]["genetic_code"]["state"] == "incompatible"


@pytest.mark.parametrize("field,value", [("code", 2), ("strand", "-"), ("frame", 1), ("cds", True),
    ("input_interval", [1, 9]), ("translated_interval", [0, 6])])
def test_labelled_native_setting_contradictions_are_not_resolved_by_trusting_result(field, value):
    native, operands = actual("ATGAAATAA")
    native[field] = value  # Explicit synthetic corruption of a real native result.
    result = grade_translation(native, **operands)
    assert result["scores"]["summary"]["unknown_codon_count"] == 3
    assert result["scores"]["summary"]["output_symbol_count"] == 3
    assert result["sheet"]["request"] == operands["request"]
    assert result["sheet"]["native_result"][field] == value
    assert result["sheet"]["native_checks"][field]["state"] == "incompatible"


@pytest.mark.parametrize("field", ["code", "strand", "frame", "cds", "input_interval", "translated_interval"])
def test_missing_native_settings_remain_missing(field):
    native, operands = actual("ATGAAA")
    del native[field]
    result = grade_translation(native, **operands)
    assert result["sheet"]["native_checks"][field]["state"] == "missing"
    assert result["scores"]["summary"]["unknown_codon_count"] == 2
    assert result["scores"]["summary"]["output_symbol_count"] == 2


@pytest.mark.parametrize("corrupt,compatible,incompatible,invalid", [("MQ", 1, 1, 0), ("M?", 1, 1, 1)])
def test_labelled_same_length_product_corruption_checks_symbols(corrupt, compatible, incompatible, invalid):
    native, operands = actual("ATGAAA")
    native["sequence"] = corrupt
    result = grade_translation(native, **operands)
    summary = result["scores"]["summary"]
    assert summary["compatible_codon_count"] == compatible and summary["incompatible_codon_count"] == incompatible
    assert summary["invalid_output_symbol_count"] == invalid
    assert summary["output_symbol_count"] == 2


@pytest.mark.parametrize("corrupt,state", [("M", "incomplete"), ("", "incomplete"), ("MKK", "incompatible")])
def test_labelled_short_or_long_product_does_not_invent_prefix_correspondence(corrupt, state):
    native, operands = actual("ATGAAA")
    native["sequence"] = corrupt
    result = grade_translation(native, **operands)
    summary = result["scores"]["summary"]
    assert summary["output_symbol_count"] == len(corrupt)
    assert summary["internal_stop_count"] == summary["terminal_stop_symbol_count"] == 0
    assert summary["mapped_output_symbol_count"] is None
    assert summary["unknown_codon_count"] == 2
    assert result["scores"]["component_status"]["product"]["state"] == state


def test_missing_product_is_not_measured_zero_and_stop_metadata_does_not_replace_symbols():
    native, operands = actual("ATGAAA")
    del native["sequence"]
    result = grade_translation(native, **operands)
    for field in ("output_symbol_count", "amino_acid_symbol_count", "internal_stop_count", "terminal_stop_symbol_count"):
        assert result["scores"]["summary"][field] is None
    assert result["scores"]["summary"]["translated_codon_count"] == 2
    assert result["scores"]["summary"]["trailing_untranslated_bases"] == 0


def test_native_stop_metadata_conflicts_keep_literal_measured_counts():
    native, operands = actual()
    native.update(internal_stop_positions=[], terminal_stop=False, trailing_untranslated_bases=0)
    result = grade_translation(native, **operands)
    summary = result["scores"]["summary"]
    assert summary["internal_stop_count"] == summary["terminal_stop_symbol_count"] == 1
    assert summary["trailing_untranslated_bases"] is None
    assert result["scores"]["status"] == "partial"


@pytest.mark.parametrize("section,key,value", [
    ("geometry", "translated_length_nt", 900), ("observed", "output_symbol_count", True),
    ("observed", "internal_stop_count", 100)])
def test_saved_numerical_corruption_is_unavailable_not_silently_repaired(section, key, value):
    native, operands = actual()
    sheet = build_translation_sheet(native, **operands)
    sheet[section][key] = value
    scores = calculate_translation_scores(sheet)
    assert scores["summary"][key] is None
    assert scores["summary"]["selected_length_nt"] == 14
    assert scores["component_status"][key]["state"] == "incompatible"


def test_saved_wrong_source_row_is_rejected_even_when_lengths_match():
    native, operands = actual()
    sheet = build_translation_sheet(native, **operands)
    sheet["codons"][0]["original_source_intervals"][0]["subject_ref"] = "unrelated:same-length"
    scores = calculate_translation_scores(sheet)
    assert scores["summary"]["compatible_codon_count"] == 3
    assert scores["summary"]["unknown_codon_count"] == 1
    assert scores["summary"]["mapped_output_symbol_count"] is None
    assert scores["summary"]["output_symbol_count"] == 4
    assert scores["codons"][0]["saved_row"]["original_source_intervals"][0]["subject_ref"] == "unrelated:same-length"


def reverse_keys(value):
    if isinstance(value, dict):
        return {key: reverse_keys(value[key]) for key in reversed(list(value))}
    if isinstance(value, list):
        return [reverse_keys(child) for child in value]
    return value


def test_saved_canonical_and_reversed_json_recalculate_with_native_tables_and_io_forbidden(tmp_path, monkeypatch):
    native, operands = actual("HTGAAATAR", code=11, cds=True)
    grading = grade_translation(native, **operands)
    canonical_path, reversed_path = tmp_path / "canonical.json", tmp_path / "reversed.json"
    canonical_path.write_text(json.dumps(grading["sheet"], sort_keys=True, allow_nan=False))
    reversed_path.write_text(json.dumps(reverse_keys(grading["sheet"]), allow_nan=False))
    saved = [json.loads(path.read_text()) for path in (canonical_path, reversed_path)]

    def forbidden(*args, **kwargs):
        raise AssertionError("recalculation attempted I/O, installed-table lookup or native execution")

    class ForbiddenTables(dict):
        __getitem__ = forbidden
        get = forbidden
        __iter__ = forbidden
        items = forbidden

    monkeypatch.setattr(sequence_ops, "translate", forbidden)
    monkeypatch.setattr(Seq, "translate", forbidden)
    for name in ("unambiguous_dna_by_id", "ambiguous_generic_by_id", "ambiguous_dna_by_id"):
        monkeypatch.setattr(CodonTable, name, ForbiddenTables())
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(io, "open", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    for sheet in saved:
        before = deepcopy(sheet)
        assert calculate_translation_scores(sheet) == grading["scores"]
        assert sheet == before


@pytest.mark.parametrize("value", [float("nan"), float("inf"), ("tuple",), b"bytes", {1: "not-a-json-key"}])
def test_nonfinite_or_non_json_operands_raise_specific_errors(value):
    native, operands = actual()
    native["unusable_extra"] = value
    with pytest.raises(ValueError, match="translation_finite_json_required"):
        grade_translation(native, **operands)


def test_incompatible_top_level_shapes_and_requests_raise_specific_errors():
    native, operands = actual()
    with pytest.raises(ValueError, match="translation_native_result_object_required"):
        grade_translation([], **operands)
    with pytest.raises(ValueError, match="translation_saved_sheet_required"):
        calculate_translation_scores({"schema": "wrong"})
    del operands["request"]["frame"]
    with pytest.raises(ValueError, match="translation_effective_request_required"):
        grade_translation(native, **operands)


def test_source_operands_and_frozen_snapshot_are_owned_copies():
    native, operands = actual()
    original = deepcopy((native, operands))
    result = grade_translation(native, **operands)
    assert (native, operands) == original
    operands["genetic_code"]["forward_table"]["ATG"] = "K"
    native["sequence"] = "fake"
    assert result["sheet"]["genetic_code"]["forward_table"]["ATG"] == "M"
    assert result["sheet"]["native_result"]["sequence"] == "M*K*"
    assert result["sheet"]["schema"] == SHEET_SCHEMA
