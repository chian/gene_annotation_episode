"""Real tiny helper outputs and deliberately corrupted supplied-data fixtures."""
from copy import deepcopy
import builtins
import io
import json
from pathlib import Path
import socket
import subprocess

import pytest
from Bio.Seq import Seq

from gene_annotation_episode import sequence_views
from gene_annotation_episode.sequence_extraction_grader import (
    SHEET_SCHEMA, build_extraction_sheet, calculate_extraction_scores, grade_extraction,
)
from gene_annotation_episode.sequence_mapping import VERSION, translation_mapping
from gene_annotation_episode.sequence_ops import translate


def part(start, end, ref="source:a", unit="nt", strand="+"):
    return {"subject_ref": ref, "start": start, "end": end, "unit": unit, "strand": strand}


def mapping(length, *, scale=1, path=None, unit="nt"):
    return {"version": VERSION, "units_per_symbol": scale, "symbol_length": length,
            "path": path or [part(0, length * scale, unit=unit)]}


def example(sequence="ACGTTGCAA", *, molecule="dna", segments=None, orientation="as_is", parent=None):
    request = {"molecule": molecule, "segments": segments or [{"start": 0, "end": len(sequence)}],
               "orientation": orientation}
    native = sequence_views.view_sequence(sequence, **request)
    operands = {"input_sequence": sequence, "subject_ref": "product:parent",
                "parent_mapping": parent if parent is not None else mapping(len(sequence)), "request": request}
    return native, operands


@pytest.mark.parametrize("sequence,molecule,unit", [
    ("aCGTn?*", "dna", "nt"), ("aCGUn?*", "rna", "nt"),
    ("MaG*?", "protein", "aa"), ("MaG*?", "protein", "symbol"),
])
def test_as_is_native_preserves_case_unusual_symbols_and_explicit_identity(sequence, molecule, unit):
    native, operands = example(sequence, molecule=molecule, parent=mapping(len(sequence), unit=unit))
    original = deepcopy((native, operands))
    result = grade_extraction(native, **operands)
    sheet, scores = result["sheet"], result["scores"]
    assert (native, operands) == original
    assert sheet["schema"] == SHEET_SCHEMA and sheet["native_result"] == native
    assert sheet["input_sequence"] == sequence
    assert scores["status"] == "complete"
    for field in ("input_symbol_count", "output_symbol_count", "selected_symbol_occurrence_count",
                  "distinct_selected_input_symbol_count", "compared_symbol_count", "matching_symbol_count",
                  "mapped_output_symbol_count"):
        assert scores["summary"][field] == len(sequence)
    assert scores["summary"]["mismatching_symbol_count"] == scores["summary"]["unmapped_output_symbol_count"] == 0
    assert scores["summary"]["selected_input_fraction"] == 1.0
    assert scores["output_source_coverage"][0]["unit"] == unit
    assert sheet["native_result"]["molecule_assignment"] == "not_performed"
    assert scores["definitions"]["combination"] is None


@pytest.mark.parametrize("molecule,expected", [
    ("dna", "nBdHvKmWsRyAaCgT"), ("rna", "nBdHvKmWsRyAaCgU"),
])
def test_native_reverse_complement_all_ambiguity_case_and_mixed_tu(molecule, expected):
    native, operands = example("AcGtUrYsWkMbDhVn", molecule=molecule, orientation="reverse_complement")
    assert native["sequence"] == expected
    scores = grade_extraction(native, **operands)["scores"]
    assert scores["summary"]["matching_symbol_count"] == 16
    assert scores["summary"]["mismatching_symbol_count"] == 0
    assert scores["verified_output_source_path"] == [part(0, 16, strand="-")]
    assert scores["segments"][0]["actual_output_symbols"] == expected


SEGMENTS = [{"start": 4, "end": 7}, {"start": 0, "end": 3},
            {"start": 4, "end": 7}, {"start": 2, "end": 5}]


@pytest.mark.parametrize("orientation,expected,order,intervals", [
    ("as_is", "TGCACGTGCGTT", [0, 1, 2, 3], [[0, 3], [3, 6], [6, 9], [9, 12]]),
    ("reverse_complement", "AACGCACGTGCA", [3, 2, 1, 0], [[9, 12], [6, 9], [3, 6], [0, 3]]),
])
def test_ordered_repeated_overlapping_selection_has_three_different_populations(orientation, expected, order, intervals):
    native, operands = example(segments=SEGMENTS, orientation=orientation)
    assert native["sequence"] == expected
    result = grade_extraction(native, **operands)
    scores = result["scores"]
    assert scores["summary"]["input_symbol_count"] == 9 and scores["summary"]["requested_segment_count"] == 4
    assert scores["summary"]["selected_symbol_occurrence_count"] == scores["summary"]["output_symbol_count"] == 12
    assert scores["summary"]["distinct_selected_input_symbol_count"] == 7
    assert scores["summary"]["repeated_selected_input_symbol_count"] == 5
    assert scores["summary"]["selected_input_fraction"] == 7 / 9
    assert scores["summary"]["selected_input_fraction_denominator_symbols"] == 9
    assert scores["output_segment_order"] == order
    assert [row["actual_output_interval"] for row in scores["segments"]] == intervals
    assert [row["request_ordinal"] for row in scores["segments"]] == [0, 1, 2, 3]
    assert scores["summary"]["source_segment_count"] == 4
    assert scores["output_source_coverage"] == [{"subject_ref": "source:a", "unit": "nt",
        "intervals": [[0, 7]], "distinct_source_position_count": 7,
        "source_position_occurrence_count": 12, "repeated_source_position_count": 5}]


def test_parent_repeated_path_distinguishes_input_union_from_physical_source_union():
    parent = mapping(8, path=[part(10, 14), part(10, 14)])
    native, operands = example("ACGTACGT", parent=parent)
    scores = grade_extraction(native, **operands)["scores"]
    assert scores["summary"]["distinct_selected_input_symbol_count"] == 8
    assert scores["summary"]["repeated_selected_input_symbol_count"] == 0
    assert scores["summary"]["source_segment_count"] == 2
    assert scores["output_source_coverage"][0]["distinct_source_position_count"] == 4
    assert scores["output_source_coverage"][0]["source_position_occurrence_count"] == 8


def test_source_coverage_never_unions_across_source_identity_or_unit():
    parent = mapping(12, path=[part(0, 4, "source:a", "nt"), part(0, 4, "source:b", "nt"),
                              part(0, 4, "source:a", "symbol")])
    native, operands = example("ACGTACGTACGT", parent=parent)
    scores = grade_extraction(native, **operands)["scores"]
    assert scores["summary"]["distinct_selected_input_symbol_count"] == 12
    assert [(row["subject_ref"], row["unit"], row["distinct_source_position_count"])
            for row in scores["output_source_coverage"]] == [
        ("source:a", "nt", 4), ("source:a", "symbol", 4), ("source:b", "nt", 4)]


def test_reverse_multisource_paths_preserve_identities_and_each_unit():
    parent = mapping(8, path=[part(10, 14, "source:z", "nt"),
                             part(10, 14, "reference:a", "symbol", "-")])
    native, operands = example("AACCGGTT", parent=parent,
        segments=[{"start": 1, "end": 7}, {"start": 0, "end": 2}], orientation="reverse_complement")
    assert native["sequence"] == "TTACCGGT"
    scores = grade_extraction(native, **operands)["scores"]
    assert scores["verified_output_source_path"] == [part(10, 12, "source:z", "nt", "-"),
        part(11, 14, "reference:a", "symbol", "+"), part(11, 14, "source:z", "nt", "-")]
    assert [(r["subject_ref"], r["unit"], r["distinct_source_position_count"],
             r["source_position_occurrence_count"]) for r in scores["output_source_coverage"]] == [
        ("reference:a", "symbol", 3, 3), ("source:z", "nt", 4, 5)]
    assert scores["summary"]["distinct_selected_input_symbol_count"] == 7
    assert scores["summary"]["repeated_selected_input_symbol_count"] == 1


def test_protein_view_of_actual_translation_preserves_three_base_split_codon_ancestry():
    # Actual helper translations on synthetic material; explicit source path has
    # a codon split between separate sources, not a fabricated genomic span.
    translated = translate("ATGAAAGGGTAA", code=11)
    parent = translation_mapping([part(20, 24, "contig:z"), part(50, 58, "contig:a", strand="-")],
        start=0, end=12, strand="+", protein_length=4)
    native, operands = example(translated["sequence"], molecule="protein", parent=parent,
        segments=[{"start": 1, "end": 3}, {"start": 1, "end": 2}])
    assert native["sequence"] == "KGK"
    scores = grade_extraction(native, **operands)["scores"]
    assert scores["summary"]["output_symbol_count"] == scores["summary"]["matching_symbol_count"] == 3
    assert scores["summary"]["distinct_selected_input_symbol_count"] == 2
    assert scores["summary"]["repeated_selected_input_symbol_count"] == 1
    assert scores["verified_output_source_path"] == [part(23, 24, "contig:z"),
        part(53, 58, "contig:a", strand="-"), part(23, 24, "contig:z"),
        part(56, 58, "contig:a", strand="-")]
    assert [(r["unit"], r["distinct_source_position_count"], r["source_position_occurrence_count"])
            for r in scores["output_source_coverage"]] == [("nt", 5, 7), ("nt", 1, 2)]
    assert scores["summary"]["source_segment_count"] == 4


def test_wrong_same_length_native_result_is_detected_symbol_by_symbol():
    native, operands = example("aCGT")
    native["sequence"] = "ACGA"  # Explicit corruption: wrong case and wrong final symbol.
    scores = grade_extraction(native, **operands)["scores"]
    assert scores["summary"]["output_length_difference"] == 0
    assert scores["summary"]["compared_symbol_count"] == 4
    assert scores["summary"]["matching_symbol_count"] == scores["summary"]["mismatching_symbol_count"] == 2
    assert scores["summary"]["mapped_output_symbol_count"] == scores["summary"]["unmapped_output_symbol_count"] == 2
    assert scores["verified_output_source_path"] == [part(1, 3)]
    assert scores["requested_source_path"] == [part(0, 4)]
    assert scores["status"] == "partial"


@pytest.mark.parametrize("actual,compared,matching,difference,unmapped", [
    ("AC", 2, 2, -2, 0), ("ACGTAA", 4, 4, 2, 2), ("", 0, 0, -4, 0),
])
def test_partial_or_extra_output_preserves_exact_compared_denominator(actual, compared, matching, difference, unmapped):
    native, operands = example("ACGT")
    native["sequence"], native["output_length"] = actual, len(actual)
    scores = grade_extraction(native, **operands)["scores"]
    assert scores["summary"]["compared_symbol_count"] == compared
    assert scores["summary"]["matching_symbol_count"] == matching and scores["summary"]["mismatching_symbol_count"] == 0
    assert scores["summary"]["output_length_difference"] == difference
    assert scores["summary"]["unmapped_output_symbol_count"] == unmapped


@pytest.mark.parametrize("field,value", [
    ("orientation", "reverse_complement"), ("molecule_model", "rna"),
    ("input_length", True), ("output_length", 99),
    ("input_segments", [{"start": 1, "end": 4}]),
    ("coordinate_system", "one_based_closed"), ("molecule_assignment", "dna"),
])
def test_native_metadata_conflicts_do_not_erase_independent_symbol_measurements(field, value):
    native, operands = example("ACGT")
    native[field] = value
    scores = grade_extraction(native, **operands)["scores"]
    assert scores["summary"]["input_symbol_count"] == scores["summary"]["output_symbol_count"] == 4
    assert scores["summary"]["matching_symbol_count"] == 4
    assert scores["summary"]["source_segment_count"] is None
    assert scores["summary"]["unmapped_output_symbol_count"] == 4
    assert scores["component_status"]["native_result." + field] == "incompatible"


@pytest.mark.parametrize("removed", ["sequence", "input_segments", "operation_version"])
def test_missing_native_fields_remain_missing_while_selected_geometry_survives(removed):
    native, operands = example("ACGT")
    del native[removed]
    scores = grade_extraction(native, **operands)["scores"]
    assert scores["summary"]["input_symbol_count"] == scores["summary"]["selected_symbol_occurrence_count"] == 4
    assert scores["summary"]["source_segment_count"] is None
    assert scores["summary"]["output_symbol_count"] == (None if removed == "sequence" else 4)
    assert scores["summary"]["matching_symbol_count"] == (None if removed == "sequence" else 4)


def test_empty_native_object_is_missing_output_not_measured_zero():
    _, operands = example("ACGT")
    scores = grade_extraction({}, **operands)["scores"]
    assert scores["summary"]["input_symbol_count"] == 4
    assert scores["summary"]["selected_symbol_occurrence_count"] == 4
    assert scores["summary"]["output_symbol_count"] is None
    assert scores["summary"]["matching_symbol_count"] is None
    assert scores["component_status"]["native_result.sequence"] == "missing"


@pytest.mark.parametrize("parent", [None, {}, mapping(3),
    mapping(4, scale=3, unit="aa"), mapping(4, path=[part(0, 3)]),
    mapping(4, path=[dict(part(0, 4), subject_ref="")]),
])
def test_unknown_or_wrong_mapping_never_fabricates_original_coordinates(parent):
    native, operands = example("ACGT")
    operands["parent_mapping"] = parent
    scores = grade_extraction(native, **operands)["scores"]
    assert scores["summary"]["matching_symbol_count"] == 4
    assert scores["summary"]["mapped_output_symbol_count"] == 0 and scores["summary"]["unmapped_output_symbol_count"] == 4
    assert scores["summary"]["source_segment_count"] is None
    assert scores["requested_source_path"] is scores["output_source_coverage"] is None


@pytest.mark.parametrize("sequence", [None, 12])
def test_missing_or_invalid_input_keeps_actual_output_count(sequence):
    native, operands = example("ACGT")
    operands["input_sequence"] = sequence
    scores = grade_extraction(native, **operands)["scores"]
    assert scores["summary"]["input_symbol_count"] is scores["summary"]["compared_symbol_count"] is None
    assert scores["summary"]["output_symbol_count"] == scores["summary"]["unmapped_output_symbol_count"] == 4


def test_missing_selected_interval_does_not_shift_later_output_positions():
    native, operands = example("ACGT", segments=[{"start": 0, "end": 2}, {"start": 2, "end": 4}])
    operands["request"]["segments"].insert(1, {"start": None, "end": 2})
    scores = grade_extraction(native, **operands)["scores"]
    assert scores["summary"]["requested_segment_count"] == 3
    assert scores["summary"]["selected_symbol_occurrence_count"] is None
    assert scores["summary"]["compared_symbol_count"] == scores["summary"]["matching_symbol_count"] == 2
    assert scores["segments"][0]["actual_output_interval"] == [0, 2]
    assert scores["segments"][2]["actual_output_interval"] is None


@pytest.mark.parametrize("field,value", [
    ("molecule", "unspecified"), ("orientation", None),
    ("segments", []), ("segments", [{"start": False, "end": 3}]),
    ("segments", [{"start": 0, "end": 9}]),
])
def test_malformed_request_components_preserve_observed_native_lengths(field, value):
    native, operands = example("ACGT")
    operands["request"][field] = value
    scores = grade_extraction(native, **operands)["scores"]
    assert scores["summary"]["output_symbol_count"] == 4
    assert scores["status"] == "partial"


def test_impossible_protein_reverse_and_invalid_nucleotide_symbols_are_not_complemented():
    native, operands = example("M?GT", molecule="protein")
    for molecule in ("protein", "dna"):
        operands["request"].update(molecule=molecule, orientation="reverse_complement")
        scores = grade_extraction(native, **operands)["scores"]
        assert scores["summary"]["compared_symbol_count"] is None
        assert scores["summary"]["output_symbol_count"] == 4


@pytest.mark.parametrize("corruption", [float("nan"), float("inf"), b"ACGT", {"x"}, (1, 2), {1: "x"}])
def test_nonfinite_or_nonjson_nested_values_raise_specific_value_error(corruption):
    native, operands = example("ACGT")
    native["unrecognized_native_metadata"] = corruption
    with pytest.raises(ValueError, match="sequence_extraction_finite_json_required"):
        grade_extraction(native, **operands)


def test_incompatible_top_level_schemas_fail_without_silently_adapting_other_tools():
    native, operands = example("ACGT")
    for broken in ([], {**native, "operation_version": "different_native_mode"}, {**native, "schema": "other_tool"}):
        with pytest.raises(ValueError, match="sequence_extraction_native_schema_required"):
            grade_extraction(broken, **operands)
    with pytest.raises(ValueError, match="sequence_extraction_effective_request_required"):
        grade_extraction(native, **{**operands, "request": {"molecule": "dna"}})
    with pytest.raises(ValueError, match="sequence_extraction_sheet_schema_required"):
        calculate_extraction_scores({"schema": "other"})


@pytest.mark.parametrize("field,number", [("input_symbol_count", 99), ("selected_symbol_occurrence_count", True)])
def test_saved_numerical_cell_conflict_is_not_silently_repaired(field, number):
    native, operands = example("ACGT")
    sheet = build_extraction_sheet(native, **operands)
    sheet["measurements"][field] = number
    scores = calculate_extraction_scores(sheet)
    assert scores["summary"][field] is None
    assert scores["summary"]["output_symbol_count"] == scores["summary"]["matching_symbol_count"] == 4
    assert any(issue["code"] == "saved_cell_conflicts_with_retained_operands" for issue in scores["issues"])


def test_saved_path_or_row_corruption_cannot_create_verified_source_coverage():
    native, operands = example("ACGT")
    for field in ("verified_output_source_path", "segments"):
        sheet = build_extraction_sheet(native, **operands)
        if field == "segments":
            sheet[field][0]["actual_output_symbols"] = "TTTT"
        else:
            sheet[field][0]["subject_ref"] = "wrong:reference"
        scores = calculate_extraction_scores(sheet)
        assert scores["summary"]["output_symbol_count"] == 4
        assert scores["output_source_coverage"] is None
        assert scores["summary"]["unmapped_output_symbol_count"] == 4


def test_conflicting_saved_row_preserves_other_rows_comparison_denominator():
    native, operands = example("ACGT", segments=[{"start": 0, "end": 2}, {"start": 2, "end": 4}])
    sheet = build_extraction_sheet(native, **operands)
    sheet["segments"][0]["matching_symbol_count"] = 99
    scores = calculate_extraction_scores(sheet)
    assert scores["summary"]["output_symbol_count"] == 4
    assert scores["summary"]["compared_symbol_count"] == 2
    assert scores["summary"]["matching_symbol_count"] == 2
    assert scores["summary"]["mismatching_symbol_count"] == 0
    assert scores["segments"][1]["actual_output_interval"] == [2, 4]


def reversed_keys(value):
    if isinstance(value, dict):
        return {key: reversed_keys(item) for key, item in reversed(list(value.items()))}
    if isinstance(value, list):
        return [reversed_keys(item) for item in value]
    return value


def test_saved_canonical_and_reversed_json_recalculates_with_native_store_io_network_forbidden(tmp_path, monkeypatch):
    native, operands = example(segments=SEGMENTS, orientation="reverse_complement")
    result = grade_extraction(native, **operands)
    path = tmp_path / "saved.json"
    path.write_text(json.dumps(result["sheet"], sort_keys=True))
    canonical = json.loads(path.read_text())
    path.write_text(json.dumps(reversed_keys(result["sheet"])))
    reversed_saved = json.loads(path.read_text())
    from gene_annotation_episode.state import Store
    from gene_annotation_episode import sequence_ops
    def forbidden(*args, **kwargs):
        raise AssertionError("calculator must not perform native/Store/I/O/network work")
    for owner, name in [(builtins, "open"), (io, "open"), (Path, "open"), (Path, "read_text"),
                        (Path, "read_bytes"), (socket, "socket"), (subprocess, "Popen"),
                        (Store, "__init__"), (sequence_views, "view_sequence"),
                        (sequence_ops, "translate"), (Seq, "reverse_complement"),
                        (Seq, "reverse_complement_rna")]:
        monkeypatch.setattr(owner, name, forbidden)
    before = deepcopy(result["sheet"])
    assert calculate_extraction_scores(canonical) == result["scores"]
    assert calculate_extraction_scores(reversed_saved) == result["scores"]
    assert result["sheet"] == before
