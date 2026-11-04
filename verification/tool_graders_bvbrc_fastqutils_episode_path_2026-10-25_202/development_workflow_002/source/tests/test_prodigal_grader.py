"""Numerical fixtures and real native modes; none asserts biological truth."""
from copy import deepcopy
import json
from pathlib import Path
import socket

import pytest

from gene_annotation_episode.prodigal_grader import (
    build_prodigal_sheet, calculate_prodigal_scores, grade_prodigal,
)


DATA = Path(__file__).resolve().parents[1] / "verification/tool_graders_batch_001/prodigal"


def candidate(**changes):
    return {"start": 0, "end": 9, "strand": "+", "code": 11,
            "partial_begin": False, "partial_end": False,
            "protein_sequence": "MK*", "native_confidence": 90.,
            "native_score": 10., **changes}


def native(candidates=None, **changes):
    return {"candidates": [candidate()] if candidates is None else candidates,
            "mode": "meta", "translation_code": 11, "pyrodigal_version": "synthetic_fixture",
            "coordinate_system": "zero_based_half_open", **changes}


def test_overlap_duplicate_reverse_strand_and_parent_offset_have_checkable_numbers():
    source = native([candidate(), candidate(start=6, end=15, strand="-", protein_sequence="M**",
                                           partial_end=True, native_score=-2., native_confidence=0.),
                     candidate()])
    graded = grade_prodigal(source, input_length=20, input_start=100)
    sheet, scores = graded["sheet"], graded["scores"]
    assert sheet["native_result"] == source
    assert sheet["candidates"][1]["parent_interval"] == [106, 115]
    assert sheet["candidates"][1]["relative_interval"] == [6, 15]
    summary = scores["summary"]
    assert summary["reported_candidate_count"] == summary["valid_interval_candidate_count"] == 3
    assert summary["relative_coding_intervals"] == [[0, 15]]
    assert summary["union_coding_bases"] == 15  # not 27, and not duplicate-deduped candidate count
    assert summary["coding_coverage"] == .75
    assert summary["coding_coverage_denominator_nt"] == 20
    assert summary["coverage_complete_for_reported_candidates"] is True
    assert summary["partial_candidate_count"] == 1
    assert summary["partial_status_known_candidate_count"] == 3
    assert summary["invalid_component_count"] == summary["missing_component_count"] == 0
    first, second, duplicate = scores["candidates"]
    assert first["interval_length_nt"] == 9
    assert first["translated_symbol_count"] == 3
    assert first["protein_length_aa"] == 2
    assert first["native_confidence_percent"] == 90.
    assert first["internal_stop_count"] == 0 and first["terminal_stop_count"] == 1
    assert second["protein_length_aa"] == 1
    assert second["internal_stop_positions"] == [1] and second["internal_stop_count"] == 1
    assert second["native_score"] == -2. and second["native_confidence_percent"] == 0.
    assert second["strand"] == "-" and second["partial_begin"] is False
    assert duplicate["native_score"] == first["native_score"]
    assert "overall_score" not in scores and "annotation_confidence" not in scores


def test_missing_components_are_unknown_and_labels_do_not_fill_them():
    row = {"start": 1, "end": 10, "protein_sequence": "MK*", "start_type": "Edge"}
    result = grade_prodigal(native([row]), input_length=10)
    scores = result["scores"]["candidates"][0]
    assert scores["interval_length_nt"] == 9
    assert scores["terminal_stop"] is True
    assert scores["partial"] is scores["partial_begin"] is scores["partial_end"] is None
    assert scores["native_score"] is scores["native_confidence_percent"] is None
    assert scores["strand"] is scores["translation_code"] is None
    assert result["sheet"]["candidates"][0]["native_frame"] is None
    summary = result["scores"]["summary"]
    assert summary["coding_coverage"] == .9
    assert summary["missing_component_count"] == 6
    assert summary["partial_candidate_count"] == 0
    assert summary["partial_status_unknown_candidate_count"] == 1


@pytest.mark.parametrize("changes,component,issue", [
    ({"start": True}, "interval", "candidate_interval_requires_integers"),
    ({"end": 9.0}, "interval", "candidate_interval_requires_integers"),
    ({"start": -1}, "interval", "candidate_interval_outside_input"),
    ({"start": 9}, "interval", "candidate_interval_outside_input"),
    ({"end": 21}, "interval", "candidate_interval_outside_input"),
    ({"strand": 1}, "strand", "invalid_candidate_strand"),
    ({"partial_begin": 0}, "partial_begin", "invalid_partial_flag"),
    ({"partial_end": "false"}, "partial_end", "invalid_partial_flag"),
    ({"native_score": "10"}, "native_score", "invalid_native_score"),
    ({"native_score": True}, "native_score", "invalid_native_score"),
    ({"native_confidence": -1}, "native_confidence", "native_confidence_outside_percent_range"),
    ({"native_confidence": 100.01}, "native_confidence", "native_confidence_outside_percent_range"),
    ({"native_confidence": False}, "native_confidence", "native_confidence_outside_percent_range"),
    ({"protein_sequence": "M K"}, "protein_sequence", "invalid_protein_sequence"),
    ({"protein_sequence": 5}, "protein_sequence", "invalid_protein_sequence"),
    ({"code": True}, "code", "invalid_candidate_translation_code"),
    ({"code": 4}, "code", "candidate_translation_code_conflict"),
])
def test_invalid_finite_candidate_component_preserves_other_rows_and_native(changes, component, issue):
    raw = native([candidate(**changes), candidate(start=9, end=18)])
    result = grade_prodigal(raw, input_length=20)
    sheet, scores = result["sheet"], result["scores"]
    assert sheet["native_result"] == raw
    assert sheet["candidates"][0]["native_candidate"] == raw["candidates"][0]
    assert scores["candidates"][0]["component_status"][component] == "invalid"
    assert issue in {item["code"] for item in scores["candidates"][0]["issues"]}
    assert scores["candidates"][1]["native_score"] == 10.
    assert scores["candidates"][1]["interval_length_nt"] == 9
    assert scores["summary"]["invalid_component_count"] == 1
    if component == "interval":
        assert scores["summary"]["union_coding_bases"] == 9
        assert scores["summary"]["coverage_complete_for_reported_candidates"] is False
    else:
        assert scores["summary"]["union_coding_bases"] == 18


def test_all_invalid_intervals_are_unknown_but_empty_native_candidates_are_measured_zero():
    bad = grade_prodigal(native([candidate(end=90), "malformed candidate"]), input_length=20)
    assert bad["scores"]["summary"]["union_coding_bases"] is None
    assert bad["scores"]["summary"]["coding_coverage"] is None
    assert bad["scores"]["summary"]["valid_interval_candidate_count"] == 0
    assert bad["sheet"]["candidates"][1]["native_candidate"] == "malformed candidate"
    empty = grade_prodigal(native([]), input_length=20)
    assert empty["sheet"]["status"] == "no_reported_candidates"
    assert empty["scores"]["summary"]["union_coding_bases"] == 0
    assert empty["scores"]["summary"]["coding_coverage"] == 0
    assert empty["scores"]["summary"]["coverage_complete_for_reported_candidates"] is True
    zero_length = grade_prodigal(native([]), input_length=0)
    assert zero_length["scores"]["summary"]["union_coding_bases"] == 0
    assert zero_length["scores"]["summary"]["coding_coverage"] is None


def test_partial_unknown_boundary_and_empty_translation_are_not_inferred_from_flags():
    result = grade_prodigal(native([candidate(partial_begin=True, partial_end=None),
                                   candidate(protein_sequence="")]), input_length=20)
    first, second = result["scores"]["candidates"]
    assert first["partial"] is True and first["partial_end"] is None
    assert second["protein_length_aa"] == second["translated_symbol_count"] == 0
    assert second["internal_stop_count"] == second["terminal_stop_count"] == 0
    assert second["span_symbol_length_delta_nt"] == 9
    assert second["partial"] is False
    assert {x["code"] for x in second["issues"]} == {"translation_span_symbol_count_conflict"}


def test_missing_metadata_stays_partial_without_changing_candidate_data():
    result = grade_prodigal({"candidates": [candidate()]}, input_length=20)
    assert result["sheet"]["mode"] is result["sheet"]["translation_code"] is None
    assert result["sheet"]["pyrodigal_version"] is None
    assert result["scores"]["status"] == "partial"
    assert result["scores"]["candidates"][0]["native_score"] == 10.
    assert len(result["scores"]["issues"]) == 4


@pytest.mark.parametrize("raw,kwargs,code", [
    ([], {}, "prodigal_native_object_required"),
    ({}, {}, "prodigal_candidates_list_required"),
    (native(candidates={}), {}, "prodigal_candidates_list_required"),
    (native(mode="auto"), {}, "invalid_prodigal_mode"),
    (native(coordinate_system="one_based_inclusive"), {}, "incompatible_prodigal_coordinate_system"),
    (native(translation_code=True), {}, "invalid_prodigal_translation_code"),
    (native(), {"input_length": True}, "invalid_prodigal_input_length"),
    (native(), {"input_length": -1}, "invalid_prodigal_input_length"),
    (native(), {"input_start": -1}, "invalid_prodigal_input_start"),
    (native(), {"input_start": 1.0}, "invalid_prodigal_input_start"),
])
def test_top_level_contract_errors_are_specific(raw, kwargs, code):
    with pytest.raises(ValueError, match="^" + code + "$"):
        grade_prodigal(raw, **{"input_length": 20, **kwargs})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), {1}, object()])
def test_nonfinite_or_non_json_input_rejects_at_native_worker_boundary(value):
    with pytest.raises(ValueError, match="^finite_json_prodigal_native_required$"):
        grade_prodigal(native([candidate(native_score=value)]), input_length=20)


def test_saved_sheet_recalculation_is_offline_and_does_not_mutate_or_alias(monkeypatch):
    source = native([candidate(), candidate(start=6, end=15, strand="-")])
    original = deepcopy(source)
    graded = grade_prodigal(source, input_length=20, input_start=7)
    assert source == original
    saved = json.loads(json.dumps(graded["sheet"], allow_nan=False))
    before = deepcopy(saved)
    from gene_annotation_episode import sequence_ops
    monkeypatch.setattr(sequence_ops, "predict_genes", lambda *a, **k: pytest.fail("native rerun"))
    monkeypatch.setattr(socket, "socket", lambda *a, **k: pytest.fail("network access"))
    assert calculate_prodigal_scores(saved) == graded["scores"]
    assert saved == before
    graded["scores"]["candidates"][0]["relative_interval"][0] = 17
    graded["sheet"]["candidates"][0]["native_candidate"]["start"] = 5
    assert saved == before and source == original


@pytest.mark.parametrize("change", ["interval", "component", "schema", "nan"])
def test_corrupted_saved_sheet_cannot_silently_change_calculations(change):
    saved = build_prodigal_sheet(native(), input_length=20)
    if change == "interval":
        saved["candidates"][0]["relative_interval"] = [0, 20]
    elif change == "component":
        saved["candidates"][0]["native_score"] = 100.
    elif change == "schema":
        saved["schema"] = "other"
    else:
        saved["candidates"][0]["native_score"] = float("nan")
    with pytest.raises(ValueError):
        calculate_prodigal_scores(saved)


@pytest.mark.parametrize("mode,count,length,covered", [
    ("meta", 1, 306, 303), ("single", 103, 100000, None),
])
def test_retained_native_output_and_complete_input_are_numerically_verifiable(mode, count, length, covered):
    raw = json.loads((DATA / f"{mode}.native.json").read_text())
    result = grade_prodigal(raw, input_length=length)
    summary = result["scores"]["summary"]
    assert result["sheet"]["status"] == "complete"
    assert result["sheet"]["mode"] == mode
    assert summary["reported_candidate_count"] == count
    assert summary["coverage_complete_for_reported_candidates"] is True
    if covered is not None:
        assert summary["union_coding_bases"] == covered
        assert summary["coding_coverage"] == covered / length
    # Independent position-set oracle for the small retained input; production
    # uses a sorted interval union without allocating one object per base.
    covered_positions = {p for row in raw["candidates"] for p in range(row["start"], row["end"])}
    assert summary["union_coding_bases"] == len(covered_positions)
    assert summary["invalid_component_count"] == summary["missing_component_count"] == 0
    for row, scores in zip(raw["candidates"], result["scores"]["candidates"]):
        assert scores["native_score"] == row["native_score"]
        assert scores["native_confidence_percent"] == row["native_confidence"]
        assert scores["span_symbol_length_delta_nt"] == 0


@pytest.mark.parametrize("mode", ["meta", "single"])
def test_actual_native_mode_using_retained_meaningful_input(mode):
    from gene_annotation_episode.sequence_ops import predict_genes
    lines = (DATA / f"{mode}.input.fna").read_text().splitlines()
    sequence = "".join(line for line in lines if not line.startswith(">"))
    assert len(sequence) == (306 if mode == "meta" else 100000)
    raw = predict_genes(sequence, code=11, mode=mode)
    result = grade_prodigal(raw, input_length=len(sequence), input_start=13)
    assert result["sheet"]["status"] == "complete"
    assert result["scores"]["summary"]["reported_candidate_count"] > 0
    assert result["scores"]["summary"]["coverage_complete_for_reported_candidates"] is True
    assert all(row["parent_interval"][0] == row["relative_interval"][0] + 13
               for row in result["scores"]["candidates"])
    if mode == "single":
        assert {row["strand"] for row in result["scores"]["candidates"]} == {"+", "-"}
