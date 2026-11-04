"""Native-byte fixtures plus clearly synthetic transport and fault cases.

Retained arrays are decoded with their actual legacy transports, never claimed
as newly qualified v2 acquisitions. V2 transport fixtures are synthetic bindings
around either unchanged retained native bytes or explicitly synthetic bodies.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote

import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.bvbrc_data_fields import FIELD_REGISTRY
from gene_annotation_episode.bvbrc_data_query import encode_native_query
from gene_annotation_episode.bvbrc_data_readers import (
    NUMERIC_TEXT_GRAMMARS, _decode_native_payload, extract_collection_rows, parse_data_snapshot,
    validate_data_sheet,
)

EVIDENCE = Path(__file__).resolve().parents[1] / "verification/tool_graders_bvbrc_data_contract_2026-10-24"
EXAMPLES = json.loads((EVIDENCE / "FILLED_EXAMPLES.json").read_text())
BASE = "https://www.bv-brc.org/api"


def prepared(collection="genome", fields=None, mode="page", **kwargs):
    request = dict(version="bvbrc_data_request_v2", collection=collection, mode=mode, filters=[])
    if fields is not None:
        request["fields"] = fields
    request.update(kwargs)
    return encode_native_query(request, base_url=BASE)


def snapshot(binding, body, *, headers=(), **transport):
    """A synthetic transport fixture, not evidence of a live v2 invocation."""
    native = binding["native_request"]
    transport = {"status": 200, "body_complete": True, "automatic_redirects": False,
                 "effective_url": native["url"], "request": deepcopy(native),
                 "header_items": list(headers), **transport}
    return SourceSnapshot("bvbrc_data", native["url"], deepcopy(binding["effective_request"]),
                          "2026-10-24T20:00:00+00:00", body if type(body) is bytes else body.encode(),
                          "application/solr+json; charset=utf-8", transport)


def envelope(docs, *, total=None, start=0, exact=True, **extra):
    response = dict(numFound=len(docs) if total is None else total, start=start, docs=docs)
    if exact is not None:
        response["numFoundExact"] = exact
    return json.dumps(dict(responseHeader={"status": 0}, response=response, **extra))


def parse_docs(collection="genome", fields=None, docs=None, **kwargs):
    binding = prepared(collection, fields)
    return parse_data_snapshot(snapshot(binding, envelope(docs or [], **kwargs)), prepared=binding)


def retained(name, binding):
    metadata = json.loads((EVIDENCE / (name + ".meta.json")).read_text())
    content = (EVIDENCE / (name + ".body")).read_bytes()
    assert len(content) == metadata["byte_count"]
    assert hashlib.sha256(content).hexdigest() == metadata["sha256"]
    media = next(value for key, value in metadata["headers"] if key.lower() == "content-type")
    transport = dict(status=metadata["status"], header_items=metadata["headers"],
                     effective_url=metadata["effective_url"], automatic_redirects=False,
                     request={"method": metadata.get("method", "GET"), "url": metadata["url"],
                              "headers": metadata["request_headers"]})
    if "body_complete" in metadata:
        transport["body_complete"] = metadata["body_complete"]
    source = SourceSnapshot("bvbrc_data", metadata["url"], {}, metadata["retrieved_at"],
                            content, media, transport)
    return source, _decode_native_payload(source, prepared=binding)


def numeric(row, field):
    return next(cell for cell in row["numerical_cells"] if cell["field"] == field)


def native(row, field):
    return next(cell for cell in row["cells"] if cell["field"] == field)


def test_retained_native_count_two_with_zero_docs():
    binding = deepcopy(EXAMPLES["qualified_result_fixture"]["grading"]["prepared"])
    request = deepcopy(binding["original_request"])
    request["mode"] = "count"
    del request["facet"]
    binding = encode_native_query(request, base_url=BASE)
    source, result = retained("feature_count_solr", binding)
    assert result["sheet"]["page"]["returned_row_count"] == 0
    assert result["sheet"]["population"]["reported_total"] == 2
    assert result["sheet"]["population"]["native_location"] == "/response/numFound"
    assert result["sheet"]["qualification"]["request_matches"] is False
    assert parse_data_snapshot(source, prepared=binding)["status"] == "failed"


def test_retained_facet_with_synthetic_v2_binding_matches_entire_frozen_expected_sheet():
    binding = EXAMPLES["qualified_result_fixture"]["grading"]["prepared"]
    meta = json.loads((EVIDENCE / "feature_facet_solr_zero.meta.json").read_text())
    source = snapshot(binding, (EVIDENCE / "feature_facet_solr_zero.body").read_bytes(), headers=meta["headers"])
    source = replace(source, retrieved_at=meta["retrieved_at"])
    result = parse_data_snapshot(source, prepared=binding)
    assert result["status"] == "complete"
    assert result["sheet"] == EXAMPLES["facet_expected_sheet"]


def test_retained_array_genome_and_zero_are_exact_and_not_v2_qualified():
    binding = prepared(fields=["genome_id", "genome_length", "gc_content", "plasmids"])
    source, result = retained("genome_page", binding)
    row = result["sheet"]["rows"][0]
    assert numeric(row, "genome_length")["value"] == 4639675
    assert numeric(row, "gc_content")["value"] == 50.8
    assert numeric(row, "plasmids")["value"] == 0
    assert numeric(row, "plasmids")["status"] == "reported"
    assert result["sheet"]["population"]["exactness"] == "provider_reported"
    assert result["sheet"]["page"]["population_coverage"] == "unknown"
    # This older capture does not explicitly attest body_complete. Status200
    # and valid bytes are deliberately not upgraded into that missing fact.
    assert result["sheet"]["transport"]["body_complete"] is False
    extraction = extract_collection_rows(result["sheet"], fields=("genome_id", "genome_length", "gc_content", "plasmids"))
    assert extraction["rows"] == EXAMPLES["genome_page_expected_extraction"]["rows"]
    assert parse_data_snapshot(source, prepared=binding)["sheet"] is None


def test_retained_array_facet_uses_header_location_not_body():
    binding = prepared("genome_feature", mode="facet", facet=dict(field="annotation", offset=0,
        limit=2, min_count=1, sort="index", include_missing=True))
    _, result = retained("feature_facet_array", binding)
    facet = result["sheet"]["facets"][0]
    assert facet["native_location"] == "/headers/facet_counts/facet_fields/annotation"
    assert [bucket["count"] for bucket in facet["buckets"]] == [1, 1, 0]
    assert facet["buckets"][2]["is_missing_bucket"] is True
    assert facet["buckets"][2]["term"]["kind"] == "null"
    assert result["sheet"]["population"]["exactness"] == "provider_reported"


def test_retained_native_negative_measurements_and_missing_values():
    fields = ["id", "feature_id", "genome_id", "log2_fc", "z_score", "counts", "tpm", "p_value"]
    _, result = retained("expression_page", prepared("bioset_result", fields))
    rows = result["sheet"]["rows"]
    assert [numeric(row, "log2_fc")["value"] for row in rows] == [-0.132, -0.129]
    assert [numeric(row, "z_score")["value"] for row in rows] == [-0.544, -0.556]
    assert [native(row, "log2_fc")["atoms"][0]["number_lexeme"] for row in rows] == ["-0.132", "-0.129"]
    for row in rows:
        for field in ("counts", "tpm", "p_value"):
            assert numeric(row, field)["value"] is None
            assert numeric(row, field)["reason"] == "native_field_absent"
    assert result["sheet"]["page"]["population_coverage"] == "subset"
    assert result["sheet"]["page"]["next_offset"] == 2


def test_retained_bioset_integer_text_and_native_empty_duration():
    _, result = retained("bioset_page", prepared("bioset", ["bioset_id", "entity_count", "treatment_duration"]))
    rows = result["sheet"]["rows"]
    assert [numeric(row, "entity_count")["value"] for row in rows] == [3879, 3930]
    assert native(rows[1], "treatment_duration")["atoms"][0]["string_value"] == ""
    assert native(rows[0], "entity_count")["atoms"][0]["string_value"] == "3879"


def test_retained_protein_evalue_and_ppi_observed_exception_have_unknown_scale():
    _, protein = retained("protein_feature_page", prepared("protein_feature", ["id", "score", "e_value"]))
    row = protein["sheet"]["rows"][0]
    assert numeric(row, "e_value")["value"] == 1.25e-9
    assert native(row, "e_value")["atoms"][0]["string_value"] == "1.25E-9"
    assert numeric(row, "score")["value"] == 8.431318
    _, ppi = retained("ppi_page", prepared("ppi", ["id", "score"]))
    row = ppi["sheet"]["rows"][0]
    assert numeric(row, "score")["value"] == 7.9219284
    assert numeric(row, "score")["unit_code"] is None
    assert numeric(row, "score")["denominator_value"] is None
    assert native(row, "score")["field_schema_status"] == "observed_exception"
    assert row["status"] == "valid"


@pytest.mark.parametrize("score", [["string:0.9", "other:4"], []])
def test_ppi_string_arrays_preserved_without_number_finding(score):
    result = parse_docs("ppi", ["id", "score"], [{"id": "p1", "score": score}])
    row = result["sheet"]["rows"][0]
    assert [a["string_value"] for a in native(row, "score")["atoms"]] == score
    assert numeric(row, "score")["value"] is None
    assert numeric(row, "score")["reason"] == "native_format_unverified"
    assert result["status"] == "complete"


@pytest.mark.parametrize("token", ["1e-9999", "1e9999", "-1e-9999"])
def test_finite_unrepresentable_native_numbers_retain_token_and_not_zero(token):
    binding = prepared("bioset_result", ["id", "counts", "log2_fc"])
    body = '{"response":{"numFound":1,"start":0,"numFoundExact":true,"docs":[{"id":"r","counts":'+token+',"log2_fc":-2.5}]}}'
    result = parse_data_snapshot(snapshot(binding, body), prepared=binding)
    row = result["sheet"]["rows"][0]
    assert native(row, "counts")["atoms"][0]["number_lexeme"] == token
    assert native(row, "counts")["atoms"][0]["number_value"] is None
    assert numeric(row, "counts")["reason"] == "unrepresentable_numeric_value"
    assert numeric(row, "log2_fc")["value"] == -2.5
    assert result["status"] == "partial"


@pytest.mark.parametrize("text,reason", [("1e-9999", "unrepresentable_numeric_value"),
    ("1e9999", "unrepresentable_numeric_value"), ("-1", "native_value_invalid"),
    (" 1.2", "native_value_invalid"), ("1.2 trailing", "native_value_invalid"),
    ("1.2\n", "native_value_invalid"), ("NaN", "native_value_invalid")])
def test_numeric_text_full_grammar_and_finite_projection(text, reason):
    result = parse_docs("protein_feature", ["id", "e_value"], [{"id": "a", "e_value": text}])
    row = result["sheet"]["rows"][0]
    assert native(row, "e_value")["atoms"][0]["string_value"] == text
    assert numeric(row, "e_value")["reason"] == reason
    assert result["status"] == "partial"


@pytest.mark.parametrize("text,number", [("0", 0), ("001", 1), ("123", 123)])
def test_decimal_integer_text_preserves_literal(text, number):
    row = parse_docs("bioset", ["bioset_id", "entity_count"], [{"bioset_id": "a", "entity_count": text}])["sheet"]["rows"][0]
    assert numeric(row, "entity_count")["value"] == number
    assert type(numeric(row, "entity_count")["value"]) is int
    assert native(row, "entity_count")["atoms"][0]["string_value"] == text


@pytest.mark.parametrize("bad", [True, 3.0, "3", [3], {"count": 3}])
def test_invalid_integer_field_keeps_other_fields_and_row_occurrence(bad):
    result = parse_docs("genome", ["genome_id", "genome_length", "gc_content"],
        [{"genome_id": "a", "genome_length": 10, "gc_content": 25},
         {"genome_id": "b", "genome_length": bad, "gc_content": 50}])
    sheet = result["sheet"]
    assert sheet["page"]["returned_row_count"] == 2
    assert sheet["page"]["valid_row_count"] == sheet["page"]["invalid_row_count"] == 1
    assert sheet["page"]["response_complete"] is True
    assert sheet["page"]["population_coverage"] == "unknown"
    assert numeric(sheet["rows"][1], "gc_content")["value"] == 50
    assert any(issue["row_index"] == 1 and issue["field"] == "genome_length"
               for issue in result["failures"])


def test_absent_null_unselected_zero_and_empty_array_are_different():
    result = parse_docs("genome", ["genome_id", "plasmids", "contigs", "chromosomes", "taxon_lineage_ids"],
        [{"genome_id": "a", "plasmids": 0, "contigs": None, "taxon_lineage_ids": []}])
    extraction = extract_collection_rows(result["sheet"], fields=("plasmids", "contigs", "chromosomes", "cds", "taxon_lineage_ids"))
    row = extraction["rows"][0]
    assert [native(row, f)["presence"] for f in ("plasmids", "contigs", "chromosomes", "cds")] == ["present", "null", "absent", "unselected"]
    assert [numeric(row, f)["reason"] for f in ("plasmids", "contigs", "chromosomes", "cds")] == [None, "native_null", "native_field_absent", "not_selected"]
    assert native(row, "taxon_lineage_ids")["native_shape"] == "array"
    assert native(row, "taxon_lineage_ids")["atoms"] == []
    assert native(row, "taxon_lineage_ids")["status"] == "valid"


def test_invalid_complex_array_is_not_flattened_or_replaced_with_null():
    result = parse_docs("genome", ["genome_id", "taxon_lineage_ids", "plasmids"],
        [{"genome_id": "a", "taxon_lineage_ids": ["1", {"bad": "2"}, "3"], "plasmids": 0}])
    row = result["sheet"]["rows"][0]
    cell = native(row, "taxon_lineage_ids")
    assert cell["native_shape"] == "array" and cell["atoms"] == [] and cell["status"] == "invalid"
    assert cell["native_path"] == "/response/docs/0/taxon_lineage_ids"
    assert numeric(row, "plasmids")["value"] == 0


@pytest.mark.parametrize("body", ['{"response":{"docs":[],"docs":[],"numFound":0,"start":0}}',
    '{"response":{"docs":[{"genome_id":"a","plasmids":NaN}],"numFound":1,"start":0}}',
    '{"response":{"docs":[{"genome_id":"a","plasmids":Infinity}],"numFound":1,"start":0}}',
    '{"response":', '<html>error</html>'])
def test_malformed_json_and_non_json_numbers_fail_without_invented_rows(body):
    binding = prepared()
    result = parse_data_snapshot(snapshot(binding, body), prepared=binding)
    assert result["sheet"] is None
    assert result["failures"][0]["code"] == "bvbrc_invalid_json_response"


@pytest.mark.parametrize("field,value", [("service", "other"), ("url", "https://wrong.invalid"),
    ("media_type", "application/json"), ("request", {})])
def test_actual_v2_identity_and_profile_are_required(field, value):
    binding = prepared()
    source = snapshot(binding, envelope([]))
    source = replace(source, **{field: value})
    result = parse_data_snapshot(source, prepared=binding)
    assert result["status"] == "failed" and result["sheet"] is None


@pytest.mark.parametrize("change", ["effective", "population", "native_url", "headers"])
def test_prepared_record_must_be_reproducible(change):
    binding = prepared()
    source = snapshot(binding, envelope([]))
    if change == "effective":
        binding["effective_request"]["limit"] = 1
    elif change == "population":
        binding["query_population"]["population_key"] = "f" * 64
    elif change == "native_url":
        binding["native_request"]["url"] += "&rows=2"
    else:
        binding["native_request"]["headers"].append({"name": "Authorization", "value": "bad"})
    assert parse_data_snapshot(source, prepared=binding)["sheet"] is None


@pytest.mark.parametrize("body_complete", [False, None])
def test_explicit_body_completeness_required_but_valid_partial_rows_survive(body_complete):
    binding = prepared(fields=["genome_id", "plasmids"])
    source = snapshot(binding, envelope([{"genome_id": "a", "plasmids": 0}]), body_complete=body_complete)
    result = parse_data_snapshot(source, prepared=binding)
    assert result["status"] == "partial"
    assert numeric(result["sheet"]["rows"][0], "plasmids")["value"] == 0
    assert result["sheet"]["count"]["reason"] == "transport_incomplete"
    assert result["sheet"]["page"]["response_complete"] is False


def test_failed_http_retains_digest_without_successful_counts():
    binding = prepared(mode="count")
    result = parse_data_snapshot(snapshot(binding, b'{"error":"unavailable"}', status=503), prepared=binding)
    assert result["sheet"] is None
    assert result["failures"] == [dict(code="bvbrc_provider_http_error", phase="transport", row_index=None,
                                       field=None, native_path=None, http_status=503)]


@pytest.mark.parametrize("total,start,docs,coverage,next_offset", [
    (2, 0, [{"genome_id": "a"}, {"genome_id": "b"}], "complete", None),
    (5, 2, [{"genome_id": "c"}, {"genome_id": "d"}], "subset", 4),
    (2, 10, [], "subset", None), (0, 0, [], "complete", None)])
def test_page_boundaries_and_population_coverage(total, start, docs, coverage, next_offset):
    binding = prepared(offset=start, limit=2)
    result = parse_data_snapshot(snapshot(binding, envelope(docs, total=total, start=start),
        headers=[("Content-Range", f"items {start}-{start+len(docs)}/{total}")]), prepared=binding)
    assert result["status"] == "complete"
    assert result["sheet"]["page"]["population_coverage"] == coverage
    assert result["sheet"]["page"]["next_offset"] == next_offset


@pytest.mark.parametrize("range_value", ["items 0-1/2", "items 0-2/3", "items 1-3/2", "malformed"])
def test_native_range_conflicts_never_select_a_skipping_offset(range_value):
    binding = prepared()
    result = parse_data_snapshot(snapshot(binding, envelope([{"genome_id": "a"}, {"genome_id": "b"}]),
        headers=[("Content-Range", range_value)]), prepared=binding)
    assert result["status"] == "partial"
    assert result["sheet"]["page"]["next_offset"] is None
    assert result["sheet"]["page"]["native_content_range"] == range_value
    assert result["sheet"]["count"]["reason"] == "population_conflict"


@pytest.mark.parametrize("value", [True, 2.0, -1, "2", None])
def test_invalid_native_count_is_not_zero(value):
    binding = prepared(mode="count")
    body = json.dumps({"response": {"start": 0, "numFound": value, "numFoundExact": True, "docs": []}})
    result = parse_data_snapshot(snapshot(binding, body), prepared=binding)
    assert result["status"] == "partial"
    assert result["sheet"]["population"]["reported_total"] is None
    assert result["sheet"]["count"]["reason"] == "native_value_invalid"


def test_finite_float_counts_not_rounded_and_numeric_ids_remain_metadata():
    result = parse_docs("bioset_result", ["id", "counts", "taxon_id"],
        [{"id": "r", "counts": -1.25, "taxon_id": 511145}])
    assert [cell["field"] for cell in result["sheet"]["rows"][0]["numerical_cells"]] == ["counts"]
    assert numeric(result["sheet"]["rows"][0], "counts")["value"] == -1.25


def test_unreviewed_numeric_looking_strings_are_not_parsed():
    result = parse_docs("structured_assertion", ["id", "score"], [{"id": "a", "score": "9.8"}])
    assert result["sheet"]["rows"][0]["numerical_cells"] == []
    assert native(result["sheet"]["rows"][0], "score")["atoms"][0]["string_value"] == "9.8"


def test_unknown_native_fields_remain_in_raw_bytes_without_becoming_supported_cells():
    binding = prepared(fields=["genome_id"])
    source = snapshot(binding, envelope([{"genome_id": "a", "unknown_measure": {"entire": [1, 2, 3]}}]))
    result = parse_data_snapshot(source, prepared=binding)
    assert [cell["field"] for cell in result["sheet"]["rows"][0]["cells"]] == ["genome_id"]
    assert result["retained_native_sha256"] == hashlib.sha256(source.content).hexdigest()
    assert json.loads(source.content)["response"]["docs"][0]["unknown_measure"] == {"entire": [1, 2, 3]}


def test_nonobject_row_and_missing_identity_preserve_all_occurrences():
    result = parse_docs("genome", ["genome_id", "plasmids"],
                        [{"genome_id": "a", "plasmids": 1}, 7, {"plasmids": 0}])
    assert result["sheet"]["page"]["returned_row_count"] == 3
    assert [row["status"] for row in result["sheet"]["rows"]] == ["valid", "invalid", "partial"]
    assert numeric(result["sheet"]["rows"][2], "plasmids")["value"] == 0


def test_extract_rejects_cross_collection_fields_and_corrupt_numeric_association():
    sheet = parse_docs("genome", ["genome_id", "plasmids"], [{"genome_id": "a", "plasmids": 1}])["sheet"]
    with pytest.raises(ValueError):
        extract_collection_rows(sheet, fields=("e_value",))
    sheet["rows"][0]["numerical_cells"][0]["value"] = 99
    with pytest.raises(ValueError):
        extract_collection_rows(sheet, fields=("plasmids",))


@pytest.mark.parametrize("change", ["row_path", "row_status", "cell_key", "atom_extra", "integer_to_float", "field_type"])
def test_saved_native_cell_integrity_is_checked_before_extraction(change):
    sheet = parse_docs("genome", ["genome_id", "plasmids"], [{"genome_id": "a", "plasmids": 1}])["sheet"]
    row = sheet["rows"][0]
    cell = native(row, "plasmids")
    if change == "row_path":
        row["native_path"] = "/response/docs/99"
    elif change == "row_status":
        row["status"] = "partial"
        sheet["page"].update(valid_row_count=0, invalid_row_count=1)
        sheet["qualification"]["requested_fields_valid"] = False
    elif change == "cell_key":
        cell["cell_key"] += "other"
    elif change == "atom_extra":
        cell["atoms"][0]["string_value"] = "one"
    elif change == "integer_to_float":
        cell["atoms"][0]["number_value"] = 1.0
    else:
        cell["atoms"][0] = dict(kind="string", string_value="1", number_value=None,
                               boolean_value=None, number_lexeme=None)
        numeric(row, "plasmids").update(value=None, status="incompatible",
                                       reason="native_format_unverified", origin="unavailable")
    with pytest.raises(ValueError):
        extract_collection_rows(sheet, fields=("plasmids",))


def test_array_unknown_total_has_forward_candidate_without_fabricated_count():
    binding = prepared(fields=["genome_id"], offset=4, limit=2)
    source = replace(snapshot(binding, '[{"genome_id":"a"},{"genome_id":"b"}]'), media_type="application/json")
    result = _decode_native_payload(source, prepared=binding)
    assert result["sheet"]["population"]["reported_total"] is None
    assert result["sheet"]["page"]["next_offset"] == 6
    assert result["sheet"]["page"]["next_offset_basis"] == "total_unknown"


@pytest.mark.parametrize("mutation", ["status", "q", "fq", "rows", "content_type", "content_length"])
def test_native_error_echo_and_transport_contradictions_are_explicit(mutation):
    binding = prepared(fields=["genome_id", "plasmids"])
    payload = json.loads(envelope([{"genome_id": "a", "plasmids": 0}]))
    headers = []
    if mutation == "status":
        payload["responseHeader"]["status"] = 1
    elif mutation in ("q", "fq", "rows"):
        payload["responseHeader"]["params"] = {mutation: "wrong"}
    elif mutation == "content_type":
        headers = [("Content-Type", "application/json")]
    else:
        headers = [("Content-Length", "100000")]
    result = parse_data_snapshot(snapshot(binding, json.dumps(payload), headers=headers), prepared=binding)
    assert result["status"] == "partial"
    assert numeric(result["sheet"]["rows"][0], "plasmids")["value"] == 0
    assert result["sheet"]["count"]["availability"] == "unavailable"
    assert result["sheet"]["page"]["response_complete"] is False


def test_public_saved_sheet_validator_preserves_partial_data_and_detaches():
    sheet = parse_docs("genome", ["genome_id", "plasmids"],
                       [{"genome_id": "a", "plasmids": 0}, {"genome_id": "b", "plasmids": True}])["sheet"]
    result = validate_data_sheet(sheet)
    assert result == sheet and result is not sheet
    result["rows"].clear()
    assert len(sheet["rows"]) == 2


def test_saved_prepared_request_replays_when_native_compiler_is_unavailable(monkeypatch):
    from gene_annotation_episode import bvbrc_data_query
    binding = prepared("genome", ["genome_id", "plasmids"], filters=[
        {"field": "genome_id", "operator": "eq", "value": "α;beta"}])
    source = snapshot(binding, envelope([{"genome_id": "α;beta", "plasmids": 0}]))
    before = deepcopy(binding)

    def prohibited(*_args, **_kwargs):
        raise AssertionError("saved publication must not invoke the native compiler")

    monkeypatch.setattr(bvbrc_data_query, "encode_native_query", prohibited)
    monkeypatch.setattr(bvbrc_data_query, "_expression", prohibited)
    result = parse_data_snapshot(source, prepared=binding)
    assert result["status"] == "complete"
    assert numeric(result["sheet"]["rows"][0], "plasmids")["value"] == 0
    assert binding == before
