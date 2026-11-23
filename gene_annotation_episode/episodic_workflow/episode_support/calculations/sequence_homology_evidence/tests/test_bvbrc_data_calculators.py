"""Hand-checked arithmetic, unavailable denominators and offline recalculation."""
import json

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.calculations.sequence_homology_evidence.bvbrc_data_calculators import calculate_facet_fractions, calculate_page_counts
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_and_context_sources.sequence_homology_evidence.bvbrc_data_readers import parse_data_snapshot
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_and_context_sources.sequence_homology_evidence.tests.test_bvbrc_data_readers import envelope, parse_docs, prepared, snapshot

POLICY = "same_response_exact_document_count"


def facet_sheet(pairs=None, *, total=2, exact=True, offset=0, limit=2, min_count=1,
                missing=True, partial=None, headers=(), **kwargs):
    binding = prepared("genome_feature", mode="facet", facet=dict(field="annotation", offset=offset,
        limit=limit, min_count=min_count, sort="index", include_missing=missing))
    payload = json.loads(envelope([], total=total, exact=exact))
    if partial is not None:
        payload["responseHeader"]["partialResults"] = partial
    payload["facet_counts"] = {"facet_fields": {"annotation": ["PATRIC", 1, "RefSeq", 1, None, 0] if pairs is None else pairs}}
    result = parse_data_snapshot(snapshot(binding, json.dumps(payload), headers=headers, **kwargs), prepared=binding)
    return result["sheet"]


def fractions(sheet):
    return calculate_facet_fractions(sheet, denominator_policy=POLICY)["fractions"]


def test_empty_docs_do_not_become_zero_population():
    sheet = facet_sheet()
    assert calculate_page_counts(sheet) == {
        "version": "bvbrc_data_page_components", "native_row_count": 0,
        "valid_row_count": 0, "invalid_row_count": 0,
        "reported_population_count": 2, "population_exactness": "exact"}


def test_count_all_rows_with_partial_invalid_rows_and_no_new_scientific_score():
    sheet = parse_docs("genome", ["genome_id", "plasmids"],
        [{"genome_id": "a", "plasmids": 0}, {"genome_id": "b", "plasmids": True}], total=10)["sheet"]
    assert calculate_page_counts(sheet) == {
        "version": "bvbrc_data_page_components", "native_row_count": 2,
        "valid_row_count": 1, "invalid_row_count": 1,
        "reported_population_count": 10, "population_exactness": "exact"}


def test_zero_population_is_unavailable_not_zero_over_zero():
    result = fractions(facet_sheet([None, 0], total=0))[0]
    assert result["numerator"] == result["denominator"] == 0
    assert result["fraction"] is None and result["reason"] == "empty_population"


@pytest.mark.parametrize("exact", [False, None])
def test_inexact_or_unreported_exactness_cannot_supply_denominator(exact):
    result = fractions(facet_sheet(exact=exact))
    assert all(item["fraction"] is None and item["reason"] == "inexact_population" for item in result)
    assert all(item["denominator"] == 2 for item in result)


@pytest.mark.parametrize("change", ["native_header", "count_key", "facet_key", "count_value", "exactness"])
def test_conflicting_population_is_unavailable(change):
    sheet = facet_sheet(headers=[("Content-Range", "items 0-0/9")]) if change == "native_header" else facet_sheet()
    if change == "count_key":
        sheet["count"]["population_key"] = "f" * 64
    elif change == "facet_key":
        sheet["facets"][0]["population_key"] = "f" * 64
    elif change == "count_value":
        sheet["count"]["reported_value"] = 9
    elif change == "exactness":
        sheet["count"]["exactness"] = "inexact"
    assert all(item["fraction"] is None and item["reason"] == "population_conflict" for item in fractions(sheet))


def test_missing_population_is_unavailable_without_length_docs_fallback():
    sheet = facet_sheet()
    sheet["population"].update(reported_total=None, native_num_found_exact=None, exactness="unknown")
    sheet["count"].update(reported_value=None, exactness="unknown", availability="unavailable", reason="unknown_denominator")
    sheet["page"].update(reported_total=None, count_exactness="unknown")
    assert all(item["denominator"] is None and item["fraction"] is None and item["reason"] == "unknown_denominator" for item in fractions(sheet))


@pytest.mark.parametrize("partial", [True, "omitted"])
def test_partial_native_result_is_never_an_exact_denominator(partial):
    sheet = facet_sheet(partial=partial)
    assert all(item["reason"] == "native_partial_results" for item in fractions(sheet))
    assert sheet["facets"][0]["all_categories_complete"] is False


def test_incomplete_transport_keeps_native_count_but_not_fraction():
    sheet = facet_sheet(body_complete=False)
    assert calculate_page_counts(sheet)["reported_population_count"] == 2
    assert all(item["reason"] == "transport_incomplete" for item in fractions(sheet))


def test_unsupported_denominator_policy_does_not_renormalize_top_buckets():
    sheet = facet_sheet(["a", 3, "b", 2], total=10)
    assert [item["fraction"] for item in fractions(sheet)] == [0.3, 0.2]
    for policy in ("sum_buckets", "returned_rows", "", None):
        with pytest.raises(ValueError):
            calculate_facet_fractions(sheet, denominator_policy=policy)


def test_overlapping_multivalue_buckets_are_not_renormalized():
    sheet = facet_sheet(["a", 4, "b", 4], total=5)
    assert [item["fraction"] for item in fractions(sheet)] == [0.8, 0.8]


@pytest.mark.parametrize("pairs", [["good", 1, "bad", True], ["good", 1, "bad", 1.0],
    ["good", 1, "bad", -1], ["good", 1, "bad"], ["good", 1, {"bad": 2}, 1]])
def test_invalid_buckets_do_not_erase_independent_valid_counts(pairs):
    sheet = facet_sheet(pairs)
    assert fractions(sheet)[0]["fraction"] == 0.5
    assert fractions(sheet)[1]["fraction"] is None
    assert fractions(sheet)[1]["reason"] == "native_value_invalid"
    assert sheet["facets"][0]["bucket_window_status"] == "invalid"
    if type(pairs[2]) is dict:
        assert sheet["facets"][0]["buckets"][1]["term"] is None
        assert sheet["facets"][0]["buckets"][1]["is_missing_bucket"] is None


def test_a_bucket_larger_than_exact_population_is_unavailable():
    result = fractions(facet_sheet(["a", 3], total=2))[0]
    assert result["numerator"] == 3 and result["denominator"] == 2
    assert result["fraction"] is None and result["reason"] == "population_conflict"


@pytest.mark.parametrize("offset,limit,min_count,missing,complete,window", [
    (0, 3, 1, True, True, "exhausted_window"),
    (0, 2, 1, True, False, "more_unknown"),
    (1, 3, 1, True, False, "exhausted_window"),
    (0, 3, 2, True, False, "exhausted_window"),
    (0, 3, 1, False, False, "exhausted_window")])
def test_exact_bucket_limit_is_not_all_categories(offset, limit, min_count, missing, complete, window):
    pairs = ["a", 1, "b", 1] + ([None, 0] if missing else [])
    facet = facet_sheet(pairs, offset=offset, limit=limit, min_count=min_count, missing=missing)["facets"][0]
    assert facet["all_categories_complete"] is complete
    assert facet["bucket_window_status"] == window


def test_contradictory_duplicate_header_preserves_original_envelope_and_unavailable_fraction():
    sheet = facet_sheet(headers=[("facet_counts", '{"facet_fields":{"annotation":["other",2]}}')])
    assert sheet["facets"][0]["buckets"][0]["term"]["string_value"] == "PATRIC"
    assert all(item["reason"] == "population_conflict" for item in fractions(sheet))
    assert sheet["qualification"]["population_metadata_valid"] is False
    assert sheet["count"]["reason"] == "population_conflict"


def test_duplicate_native_terms_keep_both_conflicting_occurrences_unavailable():
    sheet = facet_sheet(["a", 1, "a", 2])
    assert [bucket["count"] for bucket in sheet["facets"][0]["buckets"]] == [1, 2]
    assert [bucket["status"] for bucket in sheet["facets"][0]["buckets"]] == ["invalid", "invalid"]
    assert all(item["reason"] == "native_value_invalid" for item in fractions(sheet))


@pytest.mark.parametrize("mutation", ["key", "term", "missing", "count", "window", "complete"])
def test_forged_saved_bucket_relationships_are_rejected(mutation):
    sheet = facet_sheet()
    facet = sheet["facets"][0]
    bucket = facet["buckets"][0]
    if mutation == "key":
        bucket["bucket_key"] += "other"
    elif mutation == "term":
        bucket["term"]["number_value"] = 4
    elif mutation == "missing":
        bucket["is_missing_bucket"] = True
    elif mutation == "count":
        facet["returned_nonmissing_bucket_count"] = 99
    elif mutation == "window":
        facet["bucket_window_status"] = "exhausted_window"
    else:
        facet["all_categories_complete"] = True
    with pytest.raises(ValueError):
        fractions(sheet)

