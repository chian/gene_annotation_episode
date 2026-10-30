"""Shared numeric authority checks using explicit synthetic cells and saved data."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.infernal_search_cells import (
    populate_infernal_search_cells, upgrade_saved_infernal_search_sheet)
from gene_annotation_episode.infernal_search_contracts import (
    SHEET_SCHEMA, SCORE_SCHEMA, sheet_digest, validate_infernal_search_sheet,
    validate_infernal_search_scores)
from gene_annotation_episode.infernal_search_grader import calculate_infernal_search_scores


FIXTURE = Path(__file__).parents[1] / "verification/tool_graders_infernal_shared_core_2026-10-28_582/SYNTHETIC_COMMON_INPUT.json"


def supplied():
    return json.loads(FIXTURE.read_text())


def calculate(data=None, **parameters):
    sheet = populate_infernal_search_cells(**(supplied() if data is None else data))
    return sheet, calculate_infernal_search_scores(sheet, parameters=parameters)


def duplicate(data, *, pointer="/hits/SYNTHETIC/1"):
    row = deepcopy(data["hits"][0])
    row["locator"]["json_pointer"] = pointer
    row["hit_id"] = row["locator"]["artifact_id"] + pointer
    row["attribution"]["source_locators"] = [deepcopy(row["locator"])]
    row["source_details"]["native_json_pointer"] = pointer
    data["hits"].append(row)
    data["sequence_populations"][0]["reported_row_count"] += 1
    return row


def test_nullable_name_source_bound_correspondence_and_declared_empty_population():
    sheet, scores = calculate()
    assert sheet["schema"] == SHEET_SCHEMA and scores["schema"] == SCORE_SCHEMA
    assert sheet["hits"][0]["sequence"]["name"] is None
    assert sheet["hits"][0]["sequence"]["identity"] == {"kind": "supplied_sequence_metadata", "metadata_index": 0}
    row = scores["hits"][0]
    cells = row["components"]
    assert cells["sequence_span_length"] == 2 and cells["sequence_span_fraction"] == 1
    assert cells["represented_model_positions"] == cells["represented_query_positions"] == 2
    assert cells["model_consensus_equal_count"] == cells["model_consensus_compared_count"] == 2
    assert cells["model_consensus_equal_fraction"] == 1
    assert cells["consensus_length"] is cells["represented_model_fraction"] is None
    assert sheet["operation"]["program"] is row["algorithm"] is row["inclusion"] is None
    assert row["components"] == row["attributed_components"]
    for aggregate in scores["sequence_strand_aggregates"][2:]:
        assert aggregate["hit_count"] == aggregate["valid_geometry_count"] == 0
        assert aggregate["span_sum"] == aggregate["union_numerator"] == aggregate["overlap_excess"] == 0
        assert aggregate["union_span_fraction"] == 0 and aggregate["complete_for_selected_population"]


def test_overlapping_spans_share_one_sum_union_excess_calculation():
    data = supplied()
    data["sequence_metadata"][0].update(sequence="A" * 100, length=100)
    data["sequence_populations"][0]["length"].update(supplied=100, value=100)
    first = data["hits"][0]
    first.update(sequence_from=1, sequence_to=60, correspondence=None)
    second = duplicate(data)
    second.update(sequence_from=40, sequence_to=100)
    _, scores = calculate(data)
    aggregate = scores["sequence_strand_aggregates"][0]
    assert [h["components"]["sequence_span_length"] for h in scores["hits"]] == [60, 61]
    assert (aggregate["span_sum"], aggregate["union_numerator"], aggregate["overlap_excess"]) == (121, 100, 21)
    assert aggregate["union_span_fraction"] == 1
    assert aggregate["overlap_memberships"][0]["overlap_length"] == 21


def test_exact_source_duplicate_is_distinct_from_geometric_and_scientific_duplicates():
    data = supplied()
    second = duplicate(data)
    second["duplicate_of"] = data["hits"][0]["hit_id"]
    _, scores = calculate(data)
    aggregate = scores["sequence_strand_aggregates"][0]
    assert (aggregate["span_sum"], aggregate["union_numerator"], aggregate["overlap_excess"]) == (4, 2, 2)
    assert aggregate["exact_source_duplicate_row_count"] == 1
    assert len(aggregate["duplicate_representation_memberships"]) == len(aggregate["identical_interval_memberships"]) == 1
    assert scores["sequence_populations"][0]["reported_row_count"] == 2
    assert scores["sequence_populations"][1]["reported_row_count"] == 0


def test_partial_valid_rows_survive_while_absent_population_stays_unknown():
    data = supplied()
    for population in data["sequence_populations"]:
        population["reported_set_complete"] = False
    data["sequence_populations"][1]["reported_row_count"] = None
    data["hits"][0]["population_complete"] = False
    _, scores = calculate(data)
    assert scores["hits"][0]["components"]["sequence_span_fraction"] == 1
    observed = scores["sequence_strand_aggregates"][0]
    assert observed["hit_count"] == 1 and observed["span_sum"] == observed["union_numerator"] == 2
    assert observed["union_span_fraction"] is None and not observed["complete_for_selected_population"]
    absent = scores["sequence_strand_aggregates"][2]
    assert absent["union_denominator"] == 2
    assert all(absent[k] is None for k in ("hit_count", "valid_geometry_count", "span_sum", "union_numerator", "overlap_excess", "union_span_fraction"))


def test_unknown_strand_qualifies_both_declared_axes_without_double_counting():
    data = supplied()
    row = duplicate(data)
    row.update(strand=None, correspondence=None)
    _, scores = calculate(data)
    plus, minus = scores["sequence_strand_aggregates"][:2]
    assert plus["hit_count"] == 1 and plus["union_numerator"] == 2
    assert minus["hit_count"] is minus["union_numerator"] is None
    assert plus["union_span_fraction"] is minus["union_span_fraction"] is None
    assert not plus["complete_for_selected_population"] and not minus["complete_for_selected_population"]
    assert scores["sequence_populations"][0]["hit_count"] == 2
    assert scores["hits"][1]["components"]["sequence_from"] == 1
    assert scores["hits"][1]["components"]["sequence_span_length"] is None


def test_unknown_inclusion_never_becomes_included_or_complete_empty_union():
    _, scores = calculate(hit_scope="included")
    aggregate = scores["sequence_strand_aggregates"][0]
    assert scores["hits"][0]["selected_for_aggregate"] is None
    assert aggregate["unknown_selection_count"] == 1
    assert aggregate["union_numerator"] is aggregate["union_span_fraction"] is None
    assert not aggregate["complete_for_selected_population"]


def test_failed_attribution_retains_native_cells_without_attributed_geometry():
    data = supplied()
    data["hits"][0]["attribution"]["model"] = "conflict"
    _, scores = calculate(data)
    row = scores["hits"][0]
    assert row["components"]["bitscore"] == 4 and row["components"]["sequence_span_length"] == 2
    assert all(value is None for value in row["attributed_components"].values())
    aggregate = scores["sequence_strand_aggregates"][0]
    assert aggregate["valid_geometry_count"] == 0
    assert aggregate["span_sum"] is aggregate["union_numerator"] is aggregate["overlap_excess"] is None


def test_zero_determinate_pairs_and_partial_unrepresented_omission_are_distinct():
    data = supplied()
    data["sequence_metadata"][0]["sequence"] = "NN"
    cor = data["hits"][0]["correspondence"]
    for pair in cor["paired_positions"]:
        pair.update(consensus_symbol="N", query_symbol="N")
    cor["segments"][0].update(model_text="NN", query_text="NN")
    cor.update(model_consensus_compared_count=0, model_consensus_equal_count=0)
    _, scores = calculate(data)
    cells = scores["hits"][0]["components"]
    assert cells["represented_model_positions"] == 2
    assert cells["model_consensus_compared_count"] == cells["model_consensus_equal_count"] == 0
    assert cells["model_consensus_equal_fraction"] is None
    cor.update(status="partial", paired_positions=[], aligned_model_intervals=[], aligned_query_intervals=[],
        segments=[dict(kind="local_end", model_interval=[0,2], query_interval=[0,2], model_text="*[2]*",
            query_text="*[2]*", model_count=2, query_count=2, correspondence_represented=False)],
        local_end_model_omitted_count=2, local_end_query_count=2)
    _, partial = calculate(data)
    cells = partial["hits"][0]["components"]
    assert cells["represented_model_positions"] is cells["represented_query_positions"] is None
    assert cells["local_end_model_omitted_count"] == cells["local_end_query_count"] == 2
    assert cells["consensus_length"] is None


def test_source_relationship_geometry_failure_preserves_observed_endpoints():
    data = supplied()
    data["hits"][0]["source_details"]["query_coordinates_valid"] = False
    _, scores = calculate(data)
    values = scores["hits"][0]["components"]
    assert values["sequence_from"] == 1 and values["sequence_to"] == 2
    assert values["bitscore"] == 4 and values["sequence_span_length"] is None


def test_saved_v2_recalculation_and_validation_call_no_parser_io_or_process(monkeypatch):
    sheet, expected = calculate()
    saved = json.loads(json.dumps(sheet))
    before = deepcopy(saved)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved-only calculation performed external work")
    monkeypatch.setattr("gene_annotation_episode.infernal_search_cells.populate_infernal_search_cells", forbidden)
    monkeypatch.setattr("gene_annotation_episode.infernal_search_inputs.populate_infernal_search_sheet", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    assert calculate_infernal_search_scores(saved) == expected
    assert validate_infernal_search_scores(expected, sheet=saved) == expected
    assert saved == before


@pytest.mark.parametrize("sort_keys", [False, True])
def test_saved_json_object_order_does_not_change_missing_component_membership(sort_keys):
    sheet, scores = calculate()
    saved_sheet = json.loads(json.dumps(sheet, sort_keys=sort_keys))
    saved_scores = json.loads(json.dumps(scores, sort_keys=sort_keys))
    assert validate_infernal_search_scores(saved_scores, sheet=saved_sheet) == scores
    assert calculate_infernal_search_scores(saved_sheet) == scores
    missing = saved_scores["hits"][0]["unavailable_components"]
    assert missing
    for incorrect in (missing[:-1], missing + [missing[0]], missing + ["bitscore"]):
        wrong = deepcopy(saved_scores)
        wrong["hits"][0]["unavailable_components"] = incorrect
        with pytest.raises(ValueError, match="infernal_search_scores_invalid"):
            validate_infernal_search_scores(wrong, sheet=saved_sheet)


@pytest.mark.parametrize("change", ["hit_id", "occurrence", "metadata_index", "source_digest", "attributed_copy",
    "native_value", "complete_count", "interval", "valid_count", "aggregate_order", "native_name", "algorithm", "aggregate_denominator"])
def test_saved_source_and_projection_relationship_tampering_rejected(change):
    sheet, scores = calculate()
    if change == "hit_id":
        sheet["hits"][0]["hit_id"] = "changed"
    elif change == "occurrence":
        sheet["hits"][0]["query_occurrence_key"] = "wrong-occurrence"
    elif change == "metadata_index":
        sheet["hits"][0]["sequence"]["identity"]["metadata_index"] = 1
    elif change == "source_digest":
        sheet["artifacts"][0]["source_descriptor"].update(byte_hash_verified=True, source_sha256="0" * 64, source_byte_length=18)
    elif change == "native_value":
        scores["hits"][0]["components"]["bitscore"] = scores["hits"][0]["attributed_components"]["bitscore"] = 5
    elif change == "complete_count":
        sheet["sequence_populations"][0]["reported_row_count"] = 2
    elif change == "interval":
        sheet["hits"][0]["sequence_interval"] = [0, 1]
    elif change == "valid_count":
        scores["sequence_strand_aggregates"][0]["valid_geometry_count"] = 2
    elif change == "aggregate_order":
        scores["sequence_strand_aggregates"].reverse()
    elif change == "native_name":
        sheet["hits"][0]["sequence"]["name"] = "not-a-reported-name"
    elif change == "algorithm":
        sheet["hits"][0]["algorithm"] = "invented"
    elif change == "aggregate_denominator":
        scores["sequence_strand_aggregates"][0]["union_denominator"] = 1
    else:
        scores["hits"][0]["attributed_components"]["bitscore"] = 5
    with pytest.raises(ValueError):
        validate_infernal_search_scores(scores, sheet=sheet)


def test_explicit_v1_conversion_keeps_original_cells_and_lineage(monkeypatch):
    from test_infernal_search_graders import populate
    current = populate()
    # Synthetic legacy-shaped saved cells from retained actual native bytes;
    # this is an upgrade unit fixture, not a rewritten historical receipt.
    legacy = deepcopy(current)
    legacy["schema"] = "infernal_search_sheet_v1"
    for key in ("sequence_populations", "source_context", "lineage"):
        legacy.pop(key)
    for artifact in legacy["artifacts"]:
        artifact.pop("source_descriptor")
    for hit in legacy["hits"]:
        for key in ("source_details", "attribution", "query_occurrence_key", "native_rank", "native_alignment_accuracy",
                    "native_model_boundary", "native_sequence_boundary", "correspondence", "duplicate_of"):
            hit.pop(key)
    saved = deepcopy(legacy)
    def forbidden(*args, **kwargs):
        raise AssertionError("explicit saved conversion parsed/acquired data")
    monkeypatch.setattr("gene_annotation_episode.infernal_search_inputs.populate_infernal_search_sheet", forbidden)
    monkeypatch.setattr("gene_annotation_episode.infernal_search_cells.populate_infernal_search_cells", forbidden)
    upgraded = upgrade_saved_infernal_search_sheet(legacy)
    assert legacy == saved
    assert upgraded["lineage"] == {"source_sheet_schema": "infernal_search_sheet_v1", "source_sheet_digest": sheet_digest(saved)}
    assert upgraded["hits"][0]["native_tokens"] == legacy["hits"][0]["native_tokens"]
    assert upgraded["hits"][0]["sequence_interval"] == legacy["hits"][0]["sequence_interval"]
    assert calculate_infernal_search_scores(upgraded)["hits"][0]["components"]["bitscore"] == 71.4
    with pytest.raises(ValueError, match="sheet_required"):
        calculate_infernal_search_scores(legacy)


def test_authentic_saved_native_v1_conversion_preserves_recorded_calculation(monkeypatch):
    directory = Path(__file__).parents[1] / (
        "verification/tool_graders_infernal_publication_2026-10-26_225/run_003/pytest/"
        "test_host_no_full_dataset_or_s0/grading/native-infernal-grading")
    sheet_bytes = (directory / "sheet.json").read_bytes()
    score_bytes = (directory / "scores.json").read_bytes()
    assert hashlib.sha256(sheet_bytes).hexdigest() == "71e44e3894b71ada18dabcb0853e008bef218b28e2ef556ae0bbc9153531ea18"
    old_sheet, old_scores = json.loads(sheet_bytes), json.loads(score_bytes)
    before_sheet, before_scores = deepcopy(old_sheet), deepcopy(old_scores)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved native v1 conversion performed acquisition or parsing")
    monkeypatch.setattr("gene_annotation_episode.infernal_search_inputs.populate_infernal_search_sheet", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    upgraded = upgrade_saved_infernal_search_sheet(old_sheet)
    recalculated = calculate_infernal_search_scores(upgraded)
    assert upgraded["lineage"]["source_sheet_digest"] == sheet_digest(old_sheet)
    assert upgraded["publication_inputs"] == old_sheet["publication_inputs"]
    for previous, current in zip(old_scores["hits"], recalculated["hits"]):
        assert all(current["components"][name] == value for name, value in previous["components"].items())
    assert recalculated["hits"][0]["components"]["evalue"] == 3.6e-22
    assert old_sheet == before_sheet and old_scores == before_scores
