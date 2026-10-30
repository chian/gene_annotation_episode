"""Actual retained batch arithmetic and explicit synthetic population changes."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.infernal_search_grader import calculate_infernal_search_scores
from gene_annotation_episode.rfam_batch_contracts import rfam_digest
from gene_annotation_episode.rfam_batch_table_grader import calculate_rfam_batch_table_components
from gene_annotation_episode.rfam_batch_table_views import project_rfam_batch_table_result
from test_rfam_batch_table import native_case, parse, synthetic_table, native_rows


def calculate(parsed):
    return calculate_rfam_batch_table_components(parsed, parameters={"hit_scope": "reported"})


def project(parsed, calculation, *, family="hit", metrics=None, rows=None):
    metrics = metrics or ["native_score_bits", "native_evalue", "query_span_fraction", "model_coverage_fraction"]
    return project_rfam_batch_table_result(parsed, calculation,
        projection={"family": family, "rows": rows or {"offset": 0, "limit": 20}, "metrics": metrics},
        artifact_bindings={"source_ref": (parsed["sheet"]["source_context"]["capture"] if parsed["version"] == "rfam_batch_parse_result_v2" else parsed["capture"])["source_ref"], "sheet_ref": "retained-sheet",
            "calculation_ref": "retained-calculation", "sheet_digest": rfam_digest(parsed["sheet"]),
            "calculation_digest": rfam_digest(calculation)})


def test_actual_native_batch_retains_original_math_and_distinct_query_occurrences():
    parsed = parse(native_case())
    result = calculate(parsed)
    assert result == calculate_infernal_search_scores(parsed["sheet"], parameters={"hit_scope": "reported"})
    assert result["sheet_digest"] == rfam_digest(parsed["sheet"])
    assert result["schema"] == "infernal_search_scores_v2"
    assert [row["components"]["bitscore"] for row in result["hits"]] == [104.6, 104.6, 104.6, 51.3, 95.5, 95.2]
    assert [row["components"]["sequence_span_length"] for row in result["hits"]] == [119, 119, 119, 70, 120, 118]
    assert all(row["components"]["sequence_span_fraction"] == 1 for row in result["hits"])
    assert len({row["query_occurrence_key"] for row in result["hits"]}) == 6
    assert len(result["sequence_strand_aggregates"]) == 12
    assert result["hits"][2]["strand"] == "-"
    assert result["hits"][2]["components"]["sequence_from"] == 119 and result["hits"][2]["components"]["sequence_to"] == 1
    assert all(row["components"]["consensus_length"] is None and row["components"]["represented_model_positions"] is None for row in result["hits"])
    view = project(parsed, result)
    assert view["population_complete"] and view["selected_row_count"] == 6
    assert view["rows"][0]["measured"] == [
        {"name": "native_score_bits", "value": 104.6, "unit": "bits"},
        {"name": "native_evalue", "value": 1.4e-24, "unit": "expected_hits"},
        {"name": "query_span_fraction", "value": 1, "unit": "fraction"}]
    assert view["rows"][0]["unavailable"] == [{"name": "model_coverage_fraction", "reason": "model_length_unavailable"}]


def test_empty_complete_queries_and_empty_partial_population_are_different():
    case = native_case()
    zero = b"\n".join(line for line in case[0].splitlines() if line.startswith(b"#")) + b"\n"
    parsed = parse(synthetic_table(case, zero))
    result = calculate(parsed)
    assert result["hits"] == [] and project(parsed, result)["population_complete"]
    assert all(row["union_numerator"] == 0 and row["union_span_fraction"] == 0
               and row["hit_count"] == 0 for row in result["sequence_strand_aggregates"])
    assert project(parsed, result)["available_row_count"] == 0
    partial = parse(synthetic_table(case, zero.replace(b"# [ok]", b"# interrupted")))
    scores = calculate(partial)
    assert not project(partial, scores)["population_complete"]
    assert all(row["union_numerator"] is None and row["union_span_fraction"] is None
               and row["hit_count"] is None for row in scores["sequence_strand_aggregates"])


def test_duplicate_representations_affect_multiplicity_not_union():
    case = native_case()
    first = native_rows(case[0])[0]
    duplicate = case[0].replace(first, first + b"\n" + first, 1)
    parsed = parse(synthetic_table(case, duplicate))
    scores = calculate(parsed)
    row = scores["sequence_strand_aggregates"][0]
    assert row["hit_count"] == 2
    assert row["span_sum"] == 238
    assert row["union_numerator"] == 119
    assert row["overlap_excess"] == 119
    assert scores["sequence_strand_aggregates"][2]["hit_count"] == 1  # Repeated input is separate.


def test_reordering_native_rows_does_not_reorder_original_occurrence_bindings():
    case = native_case()
    rows = iter(reversed(native_rows(case[0])))
    raw = b"\n".join(next(rows) if line.strip() and not line.startswith(b"#") else line
        for line in case[0].splitlines()) + b"\n"
    parsed = parse(synthetic_table(case, raw))
    scores = calculate(parsed)
    assert scores["hits"][0]["query_occurrence_key"] == parsed["sheet"]["source_context"]["input_identity"]["queries"][5]["query_occurrence_key"]
    selected = project(parsed, scores, rows={"record_keys": [scores["hits"][2]["hit_id"]]}, metrics=["query_span_nt"])
    assert selected["rows"][0]["measured"][0]["value"] == 70
    assert selected["more_rows"] and selected["selected_row_count"] == 1


@pytest.mark.parametrize("mutation", [
    lambda p: p["sheet"]["source_context"]["occurrence_bindings"][0].update(sequence_metadata_index=1),
    lambda p: p["sheet"]["source_context"]["query_population"][0].update(submitted_length_nt=1),
    lambda p: p["sheet"]["sequence_metadata"][0].update(name="foreign"),
])
def test_broken_original_occurrence_mapping_cannot_receive_numbers(mutation):
    parsed = parse(native_case())
    mutation(parsed)
    with pytest.raises(ValueError):
        calculate(parsed)


def test_foreign_native_query_has_no_fabricated_original_identity():
    case = native_case()
    raw = case[0].replace(b"rfam_example_original", b"foreign_query", 1)
    parsed = parse(synthetic_table(case, raw))
    scores = calculate(parsed)
    assert scores["hits"][0]["query_occurrence_key"] is None
    assert scores["hits"][0]["attributed_components"]["bitscore"] is None
    assert scores["hits"][0]["components"]["bitscore"] == 104.6
    view = project(parsed, scores)
    assert not view["population_complete"] and view["rows"][0]["measured"] == []
    assert all(cell["reason"] == "identity_rejected" for cell in view["rows"][0]["unavailable"])


def test_saved_recalculation_and_projection_do_no_io(monkeypatch):
    parsed = json.loads(json.dumps(parse(native_case())))
    expected = calculate(parsed)
    before = deepcopy(parsed)
    def forbidden(*args, **kwargs):
        pytest.fail("unexpected acquisition or execution")
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    actual = calculate(parsed)
    assert actual == expected and parsed == before
    assert project(parsed, actual)["selected_row_count"] == 6


def test_projection_rejects_changed_digest_or_foreign_row_selection():
    parsed = parse(native_case())
    calculated = calculate(parsed)
    changed = deepcopy(calculated)
    changed["sheet_digest"] = "0" * 64
    with pytest.raises(ValueError, match="rfam_projection_reference_conflict"):
        project(parsed, changed)
    with pytest.raises(ValueError, match="rfam_projection_reference_conflict"):
        project(parsed, calculated, rows={"record_keys": ["foreign"]})


def test_native_model_span_and_bias_are_available_without_inventing_alignment_or_length():
    parsed = parse(native_case())
    calculated = calculate(parsed)
    view = project(parsed, calculated, metrics=["native_bias_bits", "native_model_from_1i",
        "native_model_to_1i", "native_model_span_positions", "native_model_span_fraction",
        "represented_model_positions"])
    assert [row["components"]["model_span_length"] for row in calculated["hits"]] == [120, 120, 120, 71, 120, 120]
    prefix = view["rows"][3]
    assert prefix["measured"] == [
        {"name": "native_bias_bits", "value": 0.0, "unit": "bits"},
        {"name": "native_model_from_1i", "value": 1, "unit": "model_position_1i"},
        {"name": "native_model_to_1i", "value": 71, "unit": "model_position_1i"},
        {"name": "native_model_span_positions", "value": 71, "unit": "model_positions"}]
    assert prefix["unavailable"] == [
        {"name": "native_model_span_fraction", "reason": "model_length_unavailable"},
        {"name": "represented_model_positions", "reason": "not_reported"}]


def test_old_saved_table_calculation_keeps_its_original_requested_view(monkeypatch):
    directory = Path(__file__).resolve().parents[1] / "verification/tool_graders_rfam_live_workflow_2026-10-26_243/live_001"
    parsed = json.loads((directory / "parse.json").read_text())
    original = json.loads((directory / "calculation.json").read_text())
    expected = json.loads((directory / "publication.json").read_text())["projection"]
    assert parsed["version"] == "rfam_batch_tblout_parse_result_v1"
    assert original["version"] == "rfam_batch_table_calculation_v1"
    def forbidden(*args, **kwargs):
        raise AssertionError("Historical table projection attempted new numerical work")
    for path in (
        "rfam_batch_table.populate_rfam_batch_tblout_sheet",
        "rfam_batch_table_grader.calculate_rfam_batch_table_components",
        "infernal_search_grader.calculate_infernal_search_scores",
        "infernal_search_cells.upgrade_saved_infernal_search_sheet",
        "rfam_batch_infernal.upgrade_saved_rfam_search_sheet",
    ):
        monkeypatch.setattr("gene_annotation_episode." + path, forbidden)
    actual = project_rfam_batch_table_result(parsed, original, projection=expected["selection"],
        artifact_bindings={**{key: expected[key] for key in ("source_ref", "sheet_ref", "calculation_ref")},
            "sheet_digest": rfam_digest(parsed["sheet"]), "calculation_digest": rfam_digest(original)})
    assert actual == expected
