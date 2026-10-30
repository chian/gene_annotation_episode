from copy import deepcopy

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.rfam_batch_contracts import (
    RFAM_HIT_METRICS, RFAM_QUERY_STRAND_METRICS, query_strand_record_key,
    rfam_digest, validate_rfam_result_selector)
from gene_annotation_episode.rfam_batch_views import project_rfam_batch_result
from test_rfam_batch_inputs import native_example, parse
from test_rfam_batch_grader import calculate


def bindings(sheet, calculation):
    return {"source_ref": sheet["source_context"]["capture"]["source_ref"], "sheet_ref": "fixture:sheet",
        "calculation_ref": "fixture:calculation", "sheet_digest": rfam_digest(sheet), "calculation_digest": rfam_digest(calculation)}


def view(sheet, *, family="hit", rows=None, metrics=None):
    calculation = calculate(sheet)
    return project_rfam_batch_result(sheet, calculation, projection={"family": family,
        "rows": rows or {"offset": 0, "limit": 12}, "metrics": list(metrics or (RFAM_HIT_METRICS if family == "hit" else RFAM_QUERY_STRAND_METRICS))},
        artifact_bindings=bindings(sheet, calculation))


def test_each_requested_metric_exactly_once_with_closed_units_or_missing_reason():
    result = view(parse()["sheet"])
    assert result["selected_row_count"] == result["available_row_count"] == 1
    assert result["more_rows"] is False and result["population_complete"] is True
    row = result["rows"][0]
    assert len(row["measured"]) + len(row["unavailable"]) == len(RFAM_HIT_METRICS)
    measured = {r["name"]: (r["value"], r["unit"]) for r in row["measured"]}
    missing = {r["name"]: r["reason"] for r in row["unavailable"]}
    assert measured["native_score_bits"] == (104.9, "bits")
    assert measured["native_evalue"] == (4.5e-24, "expected_hits")
    assert measured["query_span_fraction"] == (1., "fraction")
    assert missing["model_length_positions"] == "model_length_unavailable"
    assert missing["represented_model_positions"] == "alignment_not_parsed"


def test_requested_preview_does_not_replace_full_saved_population():
    sheet = parse(fixture="synthetic-duplicate-hits.json")["sheet"]
    result = view(sheet, rows={"offset": 1, "limit": 1}, metrics=["query_span_nt"])
    assert result["available_row_count"] == 2 and result["selected_row_count"] == 1 and result["more_rows"]
    assert result["rows"][0]["record_key"] == sheet["hits"][1]["hit_id"]
    assert len(sheet["hits"]) == 2


def test_query_strand_key_selection_has_exact_original_query_denominator():
    sheet = parse()["sheet"]
    key = query_strand_record_key(sheet["source_context"]["input_identity"]["query_occurrence_key"], "-")
    result = view(sheet, family="query_strand", rows={"record_keys": [key]})
    assert result["rows"][0]["family_accession"] is None
    measured = {r["name"]: r["value"] for r in result["rows"][0]["measured"]}
    assert measured["query_length_nt"] == 119
    assert measured["query_strand_union_span_nt"] == 0


@pytest.mark.parametrize("change", ["sheet_digest", "calculation_digest", "source_ref", "extra"])
def test_artifact_binding_tamper_is_rejected(change):
    sheet = parse()["sheet"]
    calculation = calculate(sheet)
    b = bindings(sheet, calculation)
    b[change] = "changed"
    with pytest.raises(ContractError, match="rfam_projection_reference_conflict"):
        project_rfam_batch_result(sheet, calculation, projection={"family": "hit", "rows": {"offset": 0, "limit": 1}, "metrics": ["native_score_bits"]}, artifact_bindings=b)


@pytest.mark.parametrize("rows", [{"record_keys": ["foreign:row"]}, {"record_keys": ["x", "x"]},
    {"offset": True, "limit": 1}, {"offset": 0, "limit": 0}, {"offset": 0, "limit": 1, "record_keys": ["x"]}])
def test_invalid_or_foreign_selection_rejected(rows):
    with pytest.raises(ContractError):
        view(parse()["sheet"], rows=rows)


def test_foreign_calculation_row_cannot_be_authenticated_with_new_digest():
    sheet = parse()["sheet"]
    calculation = calculate(sheet)
    calculation["hits"][0]["query_occurrence_key"] = "another:query"
    with pytest.raises(ContractError, match="rfam_projection_reference_conflict"):
        project_rfam_batch_result(sheet, calculation,
            projection={"family": "hit", "rows": {"offset": 0, "limit": 1}, "metrics": ["native_score_bits"]},
            artifact_bindings=bindings(sheet, calculation))


def test_invalid_family_is_explicit_unavailable_not_score_for_claimed_family():
    native = native_example()
    native["hits"]["5S_rRNA"][0]["acc"] = "BAD"
    result = view(parse(native)["sheet"])
    assert result["rows"][0]["family_accession"] is None
    assert result["rows"][0]["measured"] == []
    assert {r["reason"] for r in result["rows"][0]["unavailable"]} == {"identity_rejected"}


def test_selector_restricts_text_to_artifacts_and_metrics_to_family():
    selector = {"version": "rfam_batch_result_selector_v1", "representation": "out", "model_metadata_ref": None, "projection": None}
    assert validate_rfam_result_selector(selector) == selector
    selector["projection"] = {"family": "hit", "rows": {"offset": 0, "limit": 1}, "metrics": ["native_score_bits"]}
    with pytest.raises(ContractError, match="rfam_text_format_unverified"):
        validate_rfam_result_selector(selector)
    with pytest.raises(ContractError):
        view(parse()["sheet"], family="query_strand", metrics=["native_score_bits"])
