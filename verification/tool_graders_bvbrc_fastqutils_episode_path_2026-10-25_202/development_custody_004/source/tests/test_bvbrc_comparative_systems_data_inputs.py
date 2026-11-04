"""Synthetic supplied-data checks; true fixture flags are not host admission."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import urllib.request

import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.bvbrc_data_calculators import calculate_page_counts
from gene_annotation_episode.bvbrc_data_fields import FIELD_REGISTRY
from gene_annotation_episode.bvbrc_data_query import encode_native_query
from gene_annotation_episode.bvbrc_data_readers import _decode_native_payload, parse_data_snapshot
from gene_annotation_episode.bvbrc_comparative_systems_handoff_contracts import canonical_sha256
from gene_annotation_episode.bvbrc_comparative_systems_data_contracts import (
    validate_data_population_selection, validate_supplied_record_sets,
)
from gene_annotation_episode.bvbrc_comparative_systems_data_inputs import extract_comparative_systems_data_inputs
from gene_annotation_episode.execution_contracts import digest

FIXTURES = Path(__file__).parent / "fixtures" / "bvbrc_comparative_systems_data_inputs"
WRAPPER = json.loads((FIXTURES / "qualified_data_wrapper.json").read_text())["value"]
SELECTION = json.loads((FIXTURES / "data_population_selection.json").read_text())["value"]
RAW = (FIXTURES / "SYNTHETIC_DATA_RESPONSE_001.json").read_bytes()
DOCS = json.loads(RAW)["response"]["docs"]
_DEFAULT = object()


def _page(docs, *, offset=0, start=_DEFAULT, total=_DEFAULT, exact=True, partial=None,
          complete=True, source="page_a", collection="pathway", fields=None, filters=None,
          raw=None, legacy=False, sort=None, limit=100, http_status=200):
    request = deepcopy(WRAPPER["qualified_result"]["grading"]["prepared"]["original_request"])
    request.update(collection=collection, offset=offset, limit=limit)
    if fields is not None:
        request["fields"] = fields
    if filters is not None:
        request["filters"] = filters
    request["sort"] = sort or [{"field": FIELD_REGISTRY[collection]["unique_key"], "direction": "asc"}]
    prepared = encode_native_query(request, base_url="https://www.bv-brc.org/api")
    body = {"responseHeader": {"status": 0}, "response": {"start": offset if start is _DEFAULT else start,
            "numFound": len(docs) if total is _DEFAULT else total, "docs": docs}}
    if exact is not None:
        body["response"]["numFoundExact"] = exact
    if partial is not None:
        body["responseHeader"]["partialResults"] = partial
    if raw is None:
        raw = json.dumps(docs if legacy else body, separators=(",", ":"), ensure_ascii=False).encode()
    snapshot = SourceSnapshot("bvbrc_data", prepared["native_request"]["url"], prepared["effective_request"],
        "SYNTHETIC_NOT_ACQUIRED", raw, "application/json" if legacy else "application/solr+json", {
            "request": {key: prepared["native_request"][key] for key in ("method", "url", "headers", "body")},
            "effective_url": prepared["native_request"]["url"], "automatic_redirects": False,
            "response": {"status": http_status, "headers": [], "body_complete": complete}})
    parsed = (_decode_native_payload(snapshot, prepared=prepared) if legacy else
              parse_data_snapshot(snapshot, prepared=prepared))
    wrapper = deepcopy(WRAPPER)
    q = wrapper["qualified_result"]
    grading = q["grading"]
    grading.update(prepared=prepared, parse_result=parsed, page_components=None if parsed["sheet"] is None else
                   calculate_page_counts(parsed["sheet"]))
    q["binding"].update(source_ref=source, native_artifact_ref=source + "_bytes", native_sha256=hashlib.sha256(raw).hexdigest(),
                        grading_artifact_ref=source + "_grade", collection=collection,
                        selector_sha256=digest(grading["selector"]))
    wrapper["raw_binding"] = {"source_ref": source, "raw_artifact_ref": source + "_bytes",
        "sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw), "bytes_key": source + "_bytes"}
    return wrapper, raw


def _selection(pages, *, annotation="exact_PATRIC", genomes=None):
    result = deepcopy(SELECTION)
    selected = result["record_sets"][0]
    first = pages[0][0]["qualified_result"]["grading"]["prepared"]
    collection = first["effective_request"]["collection"]
    selected.update(collection=collection, source_refs=[w["qualified_result"]["binding"]["source_ref"] for w, _ in pages],
                    query_population_key=first["query_population"]["population_key"],
                    selected_fields=first["effective_request"]["fields"], sort=first["effective_request"]["sort"],
                    annotation_filter=annotation, snapshot_evidence={"kind": "unknown", "snapshot_id": None, "source_locations": []},
                    roles=[{"genome": "genome_records", "genome_feature": "family_feature_records", "pathway": "pathway_records",
                            "subsystem": "subsystem_records", "protein_family_ref": "family_reference",
                            "pathway_ref": "pathway_reference", "subsystem_ref": "subsystem_reference"}[collection]])
    if genomes is not None:
        population = selected["declared_genome_population"]
        population["members"] = genomes
        population["raw_occurrence_count"]["value"] = len(genomes)
        population["distinct_valid_member_count"]["value"] = len(set(genomes))
    return result


def _extract(pages, selection=None, **kwargs):
    selected = _selection(pages, **kwargs) if selection is None else selection
    return extract_comparative_systems_data_inputs(tuple(w for w, _ in pages),
        artifact_bytes={w["raw_binding"]["bytes_key"]: raw for w, raw in pages}, selection=selected)


def _set(result):
    return result["record_sets"][0]


def _codes(result):
    return {row["code"] for row in result["diagnostics"]}


def test_reviewed_example_has_five_records_three_genomes_and_four_pairs():
    w, s = deepcopy(WRAPPER), deepcopy(SELECTION)
    before = deepcopy((w, s))
    result = extract_comparative_systems_data_inputs((w,), artifact_bytes={w["raw_binding"]["bytes_key"]: RAW}, selection=s)
    record = _set(result)
    assert (w, s) == before
    assert record["original_query_record_count"]["value"] == 5
    assert record["locally_included_record_count"]["value"] == 5
    assert record["population"]["raw_occurrence_count"]["value"] == 5
    assert record["population"]["distinct_valid_member_count"]["value"] == 5
    assert record["population"]["completeness"] == "complete_for_declared_population"
    assert record["population"]["relationship_to_original_task"] == "later_selected_snapshot"
    ids = [row["association"]["identifiers"] for row in record["rows"]]
    assert len({row["ec_number"] for row in ids}) == 3
    assert len({(row["genome_id"], row["ec_number"]) for row in ids}) == 4
    assert 100 * 4 / (3 * 3) == pytest.approx(44.44444444444444)
    assert 100 * 3 / (2 * 2) == 75  # Separate historical native population.
    assert validate_supplied_record_sets(result) == result
    assert result is not validate_supplied_record_sets(result)


def test_broad_count_local_exact_filter_and_excluded_rows():
    docs = deepcopy(DOCS)
    docs[1]["annotation"] = "patric"
    docs[2]["annotation"] = "RefSeq"
    docs[3]["annotation"] = ""
    result = _extract([_page(docs)])
    record = _set(result)
    assert record["original_query_record_count"]["value"] == 5
    assert record["locally_included_record_count"]["value"] == 2
    assert record["population"]["raw_occurrence_count"]["value"] == 5
    assert len(record["rows"]) == 5
    assert record["population"]["members"] == ["pw_f1", "pw_lost"]
    assert record["population"]["completeness"] == "complete_for_declared_population"
    assert "unsupported_server_filter" in _codes(result)
    assert sum(r["filter_state"] == "excluded_by_explicit_filter" for r in record["rows"]) == 3


@pytest.mark.parametrize("annotation", [None, ["PATRIC"], {"label": "PATRIC"}])
def test_uncertain_filter_cell_preserved(annotation):
    docs = deepcopy(DOCS)
    docs[0]["annotation"] = annotation
    page = _page(docs)
    result = _extract([page])
    record = _set(result)
    assert record["rows"][0]["filter_state"] == "filter_undetermined"
    assert record["rows"][0]["native_row"] == page[0]["qualified_result"]["grading"]["parse_result"]["sheet"]["rows"][0]
    assert record["locally_included_record_count"]["state"] == "missing"
    assert record["population"]["completeness"] == "partial"


def test_complete_empty_query_is_zero_missing_failed_and_partial_are_not():
    complete = _set(_extract([_page([])]))
    assert complete["page_coverage"] == "complete"
    assert complete["original_query_record_count"]["value"] == complete["locally_included_record_count"]["value"] == 0
    assert complete["population"]["completeness"] == "complete_for_declared_population"
    page = _page([], raw=b'{"response":')
    failed = _set(_extract([page]))
    assert failed["population"]["raw_occurrence_count"]["state"] == "failed"
    assert failed["locally_included_record_count"]["value"] is None
    s = _selection([page])
    missing = _set(extract_comparative_systems_data_inputs((), artifact_bytes={}, selection=s))
    assert missing["population"]["raw_occurrence_count"]["state"] == "missing"
    partial = _set(_extract([_page([], total=4)]))
    assert partial["page_coverage"] == "partial"
    assert partial["original_query_record_count"]["value"] == 4
    assert partial["locally_included_record_count"]["value"] == 0
    assert partial["population"]["completeness"] == "partial"
    http_failed = _set(_extract([_page([], http_status=500)]))
    assert http_failed["original_query_record_count"]["state"] == "failed"
    assert http_failed["population"]["completeness"] != "complete_for_declared_population"


@pytest.mark.parametrize("change,coverage,state", [
    ({"exact": None}, "unknown", "missing"), ({"exact": False}, "unknown", "missing"),
    ({"total": -1}, "incompatible", "incompatible"), ({"total": True}, "incompatible", "incompatible"),
    ({"total": 5.0}, "incompatible", "incompatible"), ({"partial": True}, "partial", "missing"),
    ({"complete": False}, "partial", "truncated"), ({"start": 1}, "incompatible", "incompatible"),
])
def test_exactness_transport_and_population_metadata(change, coverage, state):
    record = _set(_extract([_page(DOCS, **change)]))
    assert record["page_coverage"] == coverage
    assert record["original_query_record_count"]["state"] == state
    assert len(record["rows"]) == 5
    assert record["population"]["completeness"] != "complete_for_declared_population"


def test_pages_cover_total_but_have_unknown_snapshot():
    pages = [_page(DOCS[:2], total=5), _page(DOCS[2:], offset=2, total=5, source="page_b")]
    record = _set(_extract(pages))
    assert record["page_coverage"] == "complete"
    assert record["snapshot_consistency"] == "unknown"
    assert record["population"]["completeness"] == "unknown"
    assert record["original_query_record_count"]["value"] == 5
    assert record["locally_included_record_count"]["value"] == 5
    selection = _selection(pages)
    selection["record_sets"][0]["snapshot_evidence"] = {
        "kind": "immutable_snapshot", "snapshot_id": "caller-label-is-not-proof", "source_locations": []}
    result = _extract(pages, selection)
    assert _set(result)["snapshot_consistency"] == "unknown"
    assert "snapshot_consistency_unknown" in {r["code"] for r in result["requirements"]}
    assert result["selection"] == selection


def test_gap_repeat_overlap_and_conflicting_repeated_positions():
    repeat = [_page(DOCS[:2], total=5), _page(DOCS[:2], total=5, source="repeat")]
    result = _extract(repeat)
    assert _set(result)["page_coverage"] == "partial"
    assert _set(result)["population"]["raw_occurrence_count"]["value"] == 4
    assert _set(result)["locally_included_record_count"]["value"] == 2
    assert {"page_overlap", "page_gap", "duplicate_identical_representation"} <= _codes(result)
    gap = [_page(DOCS[:2], total=5), _page(DOCS[3:], offset=3, total=5, source="gap")]
    assert _set(_extract(gap))["page_coverage"] == "partial"
    overlap = [_page(DOCS[:3], total=5), _page(DOCS[2:], offset=2, total=5, source="overlap")]
    record = _set(_extract(overlap))
    assert record["page_coverage"] == "complete"
    assert record["snapshot_consistency"] == "unknown"
    assert record["population"]["raw_occurrence_count"]["value"] == 6
    assert record["locally_included_record_count"]["value"] == 5
    changed = deepcopy(DOCS[2:])
    changed[0]["ec_number"] = "9.9.9.9"
    conflict = _extract([overlap[0], _page(changed, offset=2, total=5, source="conflict")])
    assert _set(conflict)["page_coverage"] == "incompatible"
    assert _set(conflict)["snapshot_consistency"] == "conflicting"
    assert _set(conflict)["locally_included_record_count"]["state"] == "incompatible"
    assert sum(row["duplicate_state"] == "conflicting_repeat" for row in _set(conflict)["rows"]) == 2


def test_repeated_unique_id_at_different_offsets_does_not_fill_population():
    record = _set(_extract([_page([DOCS[0], DOCS[0]], total=2)]))
    assert len(record["rows"]) == 2
    assert record["page_coverage"] == "incompatible"
    assert record["population"]["raw_occurrence_count"]["value"] == 2
    assert record["locally_included_record_count"]["value"] == 1


def test_inconsistent_totals_and_wrong_native_sort_are_incompatible():
    pages = [_page(DOCS[:2], total=5), _page(DOCS[2:], offset=2, total=6, source="later")]
    assert _set(_extract(pages))["page_coverage"] == "incompatible"
    assert _set(_extract([_page(list(reversed(DOCS)))]))["page_coverage"] == "incompatible"


@pytest.mark.parametrize("mutation,code", [
    (lambda w: w["raw_binding"].update(sha256="0" * 64), "raw_binding_mismatch"),
    (lambda w: w["raw_binding"].update(source_ref="wrong"), "raw_binding_mismatch"),
    (lambda w: w["raw_binding"].update(bytes_key="wrong"), "raw_binding_mismatch"),
    (lambda w: w["raw_binding"].update(byte_count=1), "byte_identity_mismatch"),
    (lambda w: w["qualified_result"]["binding"].update(collection="subsystem"), "binding_collection_mismatch"),
    (lambda w: w["qualified_result"]["grading"]["selector"].update(page={"offset": 4, "limit": 5}), "original_page_selection_mismatch"),
    (lambda w: w["qualified_result"]["grading"]["prepared"]["native_request"].update(url="https://example.invalid"), "prepared_request_mismatch"),
    (lambda w: w["qualified_result"]["grading"]["parse_result"]["sheet"]["rows"][0]["cells"][0]["atoms"][0].update(string_value="changed"), "native_parse_correspondence_mismatch"),
])
def test_supplied_byte_value_and_original_selection_tampering(mutation, code):
    page = _page(DOCS)
    selection = _selection([page])
    mutation(page[0])
    with pytest.raises(ValueError, match=code):
        _extract([page], selection)


@pytest.mark.parametrize("field,value,code", [
    ("query_population_key", "0" * 64, "selected_query_population_mismatch"),
    ("selected_fields", ["id"], "selected_fields_or_sort_mismatch"),
    ("sort", [{"field": "id", "direction": "desc"}], "selected_fields_or_sort_mismatch"),
])
def test_record_selection_must_match_saved_query(field, value, code):
    page = _page(DOCS)
    selection = _selection([page])
    selection["record_sets"][0][field] = value
    with pytest.raises(ValueError, match=code):
        _extract([page], selection)


def test_wrong_declared_genomes_extra_source_false_flags_and_scope():
    page = _page(DOCS)
    selection = _selection([page], genomes=["unrelated"])
    with pytest.raises(ValueError, match="declared_genome_query_mismatch"):
        _extract([page], selection)
    with pytest.raises(ValueError, match="source_not_selected"):
        _extract([page, _page([], source="unselected")], _selection([page]))
    page[0]["qualified_result"]["host_qualification"]["receiver_possession_verified"] = False
    with pytest.raises(ValueError, match="shape_invalid"):
        _extract([page])
    pages = [_page(DOCS[:2], total=5), _page(DOCS[2:], offset=2, total=5, source="other")]
    pages[1][0]["qualified_result"]["host_qualification"]["scope_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="access_scope_mismatch"):
        _extract(pages)


def test_absent_bytes_is_specific_missing_requirement():
    page = _page(DOCS)
    result = extract_comparative_systems_data_inputs((page[0],), artifact_bytes={}, selection=_selection([page]))
    assert {r["code"] for r in result["requirements"]} >= {"data_input_unavailable"}
    assert _set(result)["population"]["raw_occurrence_count"]["value"] is None


def test_original_history_label_and_unknown_group_expansion_stay_unverified():
    pages = [_page(DOCS)]
    selection = _selection(pages)
    s = selection["record_sets"][0]
    s["relationship_to_original_task"] = "original_execution_snapshot"
    p = s["declared_genome_population"]
    p["completeness"] = "unknown"
    p["unresolved_members"] = ["/group/original-expansion-unknown"]
    result = _extract(pages, selection)
    assert result["selection"] == selection
    assert _set(result)["population"]["relationship_to_original_task"] == "unverified"
    assert {"group_membership_unknown", "data_input_binding_mismatch"} <= _codes(result)
    assert any(r["required_input_role"] == "original_genome_population" for r in result["requirements"])


def test_invalid_row_occurrences_and_identifiers_are_not_absence():
    docs = deepcopy(DOCS)
    docs[0]["genome_id"] = 292462.10
    docs[1]["id"] = None
    docs[2] = ["invalid", "native", "row"]
    result = _extract([_page(docs)])
    record = _set(result)
    assert len(record["rows"]) == 5
    assert record["population"]["raw_occurrence_count"]["value"] == 5
    assert record["rows"][0]["association"]["identifiers"]["genome_id"] is None
    assert record["rows"][2]["association"] is None
    assert record["population"]["completeness"] == "partial"


def test_feature_identity_shared_sequence_and_lengths_are_preserved():
    docs = [{"feature_id": "f1", "genome_id": "292462.10", "plfam_id": "PL_1", "pgfam_id": "PG_9",
             "aa_length": 100, "aa_sequence_md5": "same", "feature_type": "CDS", "annotation": "PATRIC", "start": 1, "end": 300},
            {"feature_id": "f2", "genome_id": "292462.1", "plfam_id": "PL_2", "pgfam_id": "PG_9",
             "aa_length": 200, "aa_sequence_md5": "same", "feature_type": "misc_feature", "annotation": "PATRIC", "start": 2, "end": 601}]
    pages = [_page(docs, collection="genome_feature", fields=list(docs[0]),
                   filters=[{"field": "genome_id", "operator": "in", "value": ["292462.10", "292462.1"]}])]
    record = _set(_extract(pages, genomes=["292462.10", "292462.1"]))
    assert record["population"]["distinct_valid_member_count"]["value"] == 2
    assert {r["association"]["identifiers"]["genome_id"] for r in record["rows"]} == {"292462.10", "292462.1"}
    assert {r["association"]["identifiers"]["plfam_id"] for r in record["rows"]} == {"PL_1", "PL_2"}
    assert {r["association"]["identifiers"]["pgfam_id"] for r in record["rows"]} == {"PG_9"}
    assert all(r["association"]["coordinate_convention"] == "one_based_inclusive" for r in record["rows"])
    assert [r["native_row"]["numerical_cells"][0]["value"] for r in record["rows"]] == [100, 200]
    assert record["population"]["completeness"] == "complete_for_declared_population"


@pytest.mark.parametrize("length", [-1, "not-a-length", None])
def test_invalid_or_missing_family_lengths_do_not_disappear(length):
    docs = [{"feature_id": "f1", "genome_id": "1.1", "plfam_id": "PL_1", "pgfam_id": None,
             "aa_length": length, "annotation": "PATRIC"}]
    page = _page(docs, collection="genome_feature", fields=list(docs[0]))
    record = _set(_extract([page]))
    assert len(record["rows"]) == 1
    assert record["population"]["raw_occurrence_count"]["value"] == 1
    assert record["population"]["completeness"] == "partial"
    assert record["rows"][0]["native_row"] == page[0]["qualified_result"]["grading"]["parse_result"]["sheet"]["rows"][0]


def test_subsystem_categories_and_independent_reference_arrays():
    docs = [{"id": "s1", "subsystem_id": "S", "role_id": ["r1", "r2"], "role_name": ["name2", "name1", "extra"]}]
    pages = [_page(docs, collection="subsystem_ref", fields=list(docs[0]),
                   filters=[{"field": "subsystem_id", "operator": "eq", "value": "S"}])]
    record = _set(_extract(pages, annotation="none", genomes=[]))
    row = record["rows"][0]
    assert row["association"]["identifiers"]["role_id"] is None
    assert {f["name"]: f["raw_text"] for f in row["association"]["fields"]}["role_id"] == '["r1","r2"]'
    assert record["population"]["completeness"] == "complete_for_declared_population"
    assert "reference_release_unknown" in record["population"]["qualification_codes"]
    docs = [{"id": "s1", "genome_id": "1.1", "feature_id": "f1", "subsystem_id": "S", "role_id": "r1", "active": "active"},
            {"id": "s2", "genome_id": "1.1", "feature_id": "f1", "subsystem_id": "S", "role_id": "r1", "active": "likely"}]
    pages = [_page(docs, collection="subsystem", fields=list(docs[0]))]
    assert {r["association"]["active_category"] for r in _set(_extract(pages, annotation="none"))["rows"]} == {"active", "likely"}


def test_reference_context_and_namespaces_survive_without_completion_claim():
    docs = [{"id": "r1", "pathway_id": "P", "ec_number": "1.1.1.1", "map_name": "M1", "map_type": "A"},
            {"id": "r2", "pathway_id": "P", "ec_number": "1.1.1.1", "map_name": "M2", "map_type": "B"}]
    pages = [_page(docs, collection="pathway_ref", fields=list(docs[0]), filters=[{"field": "pathway_id", "operator": "eq", "value": "P"}])]
    record = _set(_extract(pages, annotation="none", genomes=[]))
    assert [next(f["raw_text"] for f in r["association"]["fields"] if f["name"] == "map_name") for r in record["rows"]] == ["M1", "M2"]
    docs = [{"family_id": "PL_1", "family_type": "PLFAM", "family_product": "context"},
            {"family_id": "PG_1", "family_type": "PGFAM", "family_product": "other"}]
    docs.sort(key=lambda r: r["family_id"])
    pages = [_page(docs, collection="protein_family_ref", fields=list(docs[0]),
        filters=[{"field": "family_id", "operator": "in", "value": ["PL_1", "PG_1"]}])]
    assert _set(_extract(pages, annotation="none", genomes=[]))["population"]["members"] == ["PG_1", "PL_1"]


def test_legacy_array_remains_unknown_population():
    record = _set(_extract([_page(DOCS, legacy=True)]))
    assert len(record["rows"]) == 5
    assert record["page_coverage"] == "unknown"
    assert record["original_query_record_count"]["state"] == "missing"
    assert record["population"]["completeness"] == "unknown"
    assert record["population"]["source_locations"][0]["json_pointer"] == ""


def test_reviewed_saved_example_is_accepted_without_rewriting():
    value = json.loads((FIXTURES / "supplied_record_sets.json").read_text())["value"]
    assert validate_supplied_record_sets(value) == value


def test_query_genome_conflict_retains_the_row_but_invalidates_population():
    docs = deepcopy(DOCS)
    docs[0]["genome_id"] = "unexpected.100"
    record = _set(_extract([_page(docs)]))
    assert len(record["rows"]) == 5
    assert record["rows"][0]["association"]["identifiers"]["genome_id"] == "unexpected.100"
    assert record["population"]["completeness"] == "incompatible"
    assert record["original_query_record_count"]["state"] == "incompatible"


def test_complex_unselected_fields_and_number_lexemes_survive():
    docs = deepcopy(DOCS)
    docs[0]["extra_native_field"] = {"nested": ["α", None, True, {"q": 2.5}]}
    docs[0]["annotation"] = ["PATRIC", {"x": 1}]
    page = _page(docs)
    raw = page[1].replace(b'"q":2.5', b'"q":2.500e+0')
    page = _page(docs, raw=raw)
    row = _set(_extract([page]))["rows"][0]
    fields = {f["name"]: f for f in row["association"]["fields"]}
    assert fields["extra_native_field"]["raw_text"] == '{"nested":["α",null,true,{"q":2.500e+0}]}'
    assert fields["extra_native_field"]["location"]["json_pointer"] == "/response/docs/0/extra_native_field"
    assert fields["annotation"]["raw_text"] == '["PATRIC",{"x":1}]'
    assert row["filter_state"] == "filter_undetermined"
    assert row["native_row"] == page[0]["qualified_result"]["grading"]["parse_result"]["sheet"]["rows"][0]


@pytest.mark.parametrize("target,code", [
    ("raw_text", "association_field_value_mismatch"),
    ("active_category", "association_category_mismatch"),
    ("coordinate_convention", "association_coordinate_mismatch"),
    ("field_pointer", "association_location_mismatch"),
    ("count_pointer", "count_reference_missing"),
    ("population_location", "population_location_mismatch"),
    ("diagnostic_source", "diagnostic_source_mismatch"),
])
def test_saved_correspondence_rejects_changed_normalization_and_pointers(target, code):
    value = _extract([_page(DOCS)])
    record = _set(value)
    association = record["rows"][0]["association"]
    if target == "raw_text":
        association["fields"][0]["raw_text"] = "invented"
    elif target == "active_category":
        association["active_category"] = "active"
    elif target == "coordinate_convention":
        association["coordinate_convention"] = "one_based_inclusive"
    elif target == "field_pointer":
        association["fields"][0]["location"]["json_pointer"] = "/response/docs/1/id"
    elif target == "count_pointer":
        record["population"]["raw_occurrence_count"]["input_refs"][0]["pointer"] = "/rows/99"
    elif target == "diagnostic_source":
        value["diagnostics"][0]["source_refs"] = ["unselected"]
    else:
        record["population"]["source_locations"][0]["raw_artifact_ref"] = "different"
    with pytest.raises(ValueError, match=code):
        validate_supplied_record_sets(value)


def test_saved_complete_label_cannot_override_page_evidence():
    value = _extract([_page(DOCS[:2], total=5)])
    _set(value)["page_coverage"] = "complete"
    with pytest.raises(ValueError, match="complete_coverage_total_mismatch"):
        validate_supplied_record_sets(value)
    pages = [_page(DOCS[:2], total=5), _page(DOCS[2:], offset=2, total=5, source="second")]
    value = _extract(pages)
    _set(value)["snapshot_consistency"] = "single_response"
    with pytest.raises(ValueError, match="single_response_identity_mismatch"):
        validate_supplied_record_sets(value)


def test_saved_facades_reject_tampered_counts_ids_and_reference_relationships():
    result = _extract([_page(DOCS)])
    for path, value, code in [
        (("population", "raw_occurrence_count", "value"), 0, "count_value_mismatch"),
        (("population", "population_id"), "different", "count_population_mismatch"),
        (("locally_included_record_count", "value"), 9, "local_count_mismatch"),
        (("snapshot_consistency",), "proven_same_snapshot", "complete_population_evidence_missing"),
    ]:
        changed = deepcopy(result)
        cursor = _set(changed)
        for key in path[:-1]:
            cursor = cursor[key]
        cursor[path[-1]] = value
        with pytest.raises(ValueError, match=code):
            validate_supplied_record_sets(changed)
    changed = deepcopy(result)
    _set(changed)["rows"][0]["association"]["identifiers"]["ec_number"] = "invented"
    with pytest.raises(ValueError, match="association_identifier_mismatch"):
        validate_supplied_record_sets(changed)
    s = deepcopy(SELECTION)
    s["record_sets"][0]["declared_genome_population"]["raw_occurrence_count"]["value"] = True
    with pytest.raises(ValueError, match="comparative_systems_shape_invalid"):
        validate_data_population_selection(s)


def test_snapshot_pointer_must_resolve_exact_selected_bytes():
    page = _page(DOCS)
    s = _selection([page])
    s["record_sets"][0]["snapshot_evidence"]["source_locations"] = [{
        "source_ref": "page_a", "raw_artifact_ref": "page_a_bytes", "document_id": None,
        "json_pointer": "/invented/snapshot", "table": None, "row_ordinal": None,
        "column_ordinal": None, "native_field": None}]
    with pytest.raises(ValueError, match="snapshot_pointer_invalid"):
        _extract([page], s)


def test_pure_extraction_and_saved_validation_forbid_external_work(monkeypatch):
    import builtins
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.providers import ModelConnection, _SessionConnection
    from gene_annotation_episode.api_bvbrc import BVBRCDataClient
    from gene_annotation_episode.acquisition import PublicClients
    pages = [_page(DOCS)]
    selection = _selection(pages)
    before = deepcopy((pages, selection))
    def forbidden(*args, **kwargs):
        raise AssertionError("external work forbidden during supplied-data extraction")
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(Store, "get", forbidden)
    monkeypatch.setattr(Store, "get_artifact", forbidden)
    monkeypatch.setattr(ModelConnection, "complete", forbidden)
    monkeypatch.setattr(_SessionConnection, "complete", forbidden)
    monkeypatch.setattr(BVBRCDataClient, "query", forbidden)
    monkeypatch.setattr(BVBRCDataClient, "query_prepared", forbidden)
    monkeypatch.setattr(PublicClients, "_skill", forbidden)
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(builtins, "open", forbidden)
    result = _extract(pages, selection)
    from gene_annotation_episode import bvbrc_comparative_systems_data_inputs as extraction
    from gene_annotation_episode import bvbrc_data_readers as data_readers
    monkeypatch.setattr(extraction, "extract_comparative_systems_data_inputs", forbidden)
    monkeypatch.setattr(extraction, "parse_data_snapshot", forbidden)
    monkeypatch.setattr(extraction, "_decode_native_payload", forbidden)
    monkeypatch.setattr(data_readers, "parse_data_snapshot", forbidden)
    monkeypatch.setattr(data_readers, "_decode_native_payload", forbidden)
    assert validate_supplied_record_sets(result) == result
    assert (pages, selection) == before
    assert _set(result)["locally_included_record_count"]["value"] == 5
