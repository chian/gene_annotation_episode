"""Engineered confirmations for the bounded provider getters.

Pure controls preserve legacy DTOs and literal native representations. Publisher
controls use real Store custody without HTTP, model decisions or runtime rows.
They establish acquisition identity/transfer only, not scientific inference.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import molecular_provider_acquisition as provider
from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.data_acquisition_receipts import acquisition_receipt_schema
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_molecular_provider_acquisition import (
    ARGUMENTS, IDS, KEGG_TEXT, NATIVE, PUBCHEM_IDENTITY_FAILURES, SOURCE, snapshot,
)


OPERATIONS = tuple(ARGUMENTS)
STRING, KEGG, REACTOME, QUICKGO, PUBCHEM, HPA = OPERATIONS


def _forbidden(*args, **kwargs):
    raise AssertionError("provider receipt controls attempted transport or scientific work")


def _value(capture, operation):
    return provider.provider_value(operation, capture,
        artifact_ref="artifact_" + hashlib.sha256(capture.content).hexdigest())


def _native(operation, native):
    return snapshot(operation, raw=json.dumps(native, allow_nan=False).encode())


def _transport(capture, **changes):
    return replace(capture, transport={**deepcopy(capture.transport), **changes})


def _receipt(capture, operation):
    return provider.provider_receipt(_value(capture, operation), source_ref=SOURCE)


def _failure(code):
    return provider.failed_provider_receipt("molecular_provider_" + code, source_ref=SOURCE)


@pytest.fixture
def publisher(tmp_path, monkeypatch):
    monkeypatch.setattr(PublicClients, "_http", _forbidden)
    monkeypatch.setattr("socket.create_connection", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", _forbidden)
    with Store(tmp_path / "store") as store:
        yield store, ToolRegistry(store)


def _publish(registry, operation, capture, *, arguments=None):
    token = registry._publications.set([])
    try:
        return provider.publish_molecular_provider_request(registry, operation,
            capture.request if arguments is None else arguments, capture)
    finally:
        registry._publications.reset(token)


def test_receipt_uses_common_closed_four_fields_and_source_free_failure(publisher, monkeypatch):
    store, registry = publisher
    assert provider.provider_receipt_schema() == acquisition_receipt_schema(
        failure_codes=provider.PROVIDER_FAILURE_CODES)
    assert len(provider.PROVIDER_FAILURE_CODES) == len(set(provider.PROVIDER_FAILURE_CODES))
    before = list(store.list("source"))
    monkeypatch.setattr(store, "artifact", _forbidden)
    monkeypatch.setattr(registry, "_source", _forbidden)
    failure = provider.failed_provider_receipt("data_acquisition_failed")
    assert failure == dict(acquired=False, source_ref=None, data_ref=None,
        failure_code="data_acquisition_failed")
    assert Draft202012Validator(provider.provider_receipt_schema()).is_valid(failure)
    assert provider.validate_provider_receipt(failure) == failure
    assert provider.validate_provider_receipt(failure) is not failure
    assert list(store.list("source")) == before
    with pytest.raises(ContractError, match="molecular_provider_receipt_invalid"):
        provider.failed_provider_receipt("literal_provider_exception_or_diagnostic")


@pytest.mark.parametrize("change", [
    {"acquired": 1}, {"extra": None}, {"source_ref": None}, {"data_ref": None},
    {"source_ref": SOURCE + "\n"}, {"data_ref": "artifact_" + "f" * 63},
    {"failure_code": "data_acquisition_failed"},
    {"acquired": False, "failure_code": "data_acquisition_failed"},
])
def test_receipt_rejects_types_references_and_crossfield_contradictions(change):
    value = dict(acquired=True, source_ref=SOURCE, data_ref="artifact_" + "f" * 64, failure_code=None)
    with pytest.raises(ContractError, match="molecular_provider_receipt_invalid"):
        provider.validate_provider_receipt({**value, **change})


@pytest.mark.parametrize("operation", OPERATIONS)
def test_source_free_value_and_actual_source_legacy_wrapper_preserve_complete_native(operation):
    capture = snapshot(operation)
    value = _value(capture, operation)
    saved = deepcopy(value)
    assert "source_ref" not in value and value["version"] == "molecular_provider_value_v1"
    assert "source_ref" not in provider.provider_value_schema()["properties"]
    assert Draft202012Validator(provider.provider_value_schema()).is_valid(value)
    assert provider.validate_provider_value(value) == value
    legacy = provider.provider_result_from_value(value, source_ref=SOURCE)
    assert legacy == provider.provider_result(operation, capture, source_ref=SOURCE,
        artifact_ref=value["raw_artifact_ref"])
    public = {key: child for key, child in value.items() if key != "observed_transfer"}
    assert legacy == {**public, "version": "molecular_provider_result_v1", "source_ref": SOURCE}
    assert provider.validate_provider_result(legacy) == legacy
    assert legacy["representation_state"] == "complete" and legacy["issues"] == []
    assert legacy["population_coverage"] == "selected_response_only"
    assert legacy["requested"] == ARGUMENTS[operation]
    assert legacy["response"] == dict(request_url=capture.transport["request"]["url"],
        media_type=capture.media_type, http_status=200, content_type=capture.media_type,
        body_complete=True, retained_bytes=len(capture.content),
        reported_retained_bytes=len(capture.content), observed_body_bytes=len(capture.content),
        declared_body_bytes=len(capture.content),
        response_byte_limit=ARGUMENTS[operation]["max_bytes"], capture_failure=None)
    if operation == KEGG:
        assert legacy["parse_state"] == "kegg_text" and legacy["native_text"] == KEGG_TEXT
        assert [block["field"] for block in legacy["native_fields"]] == [
            "ENTRY", "NAME", "EQUATION", "ORTHOLOGY", "UNKNOWN", "NAME", "///"]
        assert "".join(line["text"] for block in legacy["native_fields"] for line in block["lines"]) == KEGG_TEXT
    else:
        assert legacy["parse_state"] == "json" and legacy["native_json"] == NATIVE[operation]
    assert provider.provider_receipt(value, source_ref=SOURCE) == dict(acquired=True,
        source_ref=SOURCE, data_ref=value["raw_artifact_ref"], failure_code=None)
    legacy["requested"]["max_bytes"] = 1
    assert value == saved


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("field,raw_value,response_field", [
    ("declared_body_bytes", float("nan"), "declared_body_bytes"),
    ("body_capture_failure", b"bad", "capture_failure"),
])
def test_legacy_normalizes_nonjson_optional_transport_without_private_value_coercion(
        operation, field, raw_value, response_field):
    capture = snapshot(operation)
    artifact_ref = "artifact_" + hashlib.sha256(capture.content).hexdigest()
    expected = provider.provider_result(operation, capture, source_ref=SOURCE, artifact_ref=artifact_ref)
    expected["response"][response_field] = None
    malformed = _transport(capture, **{field: raw_value})
    legacy = provider.provider_result(operation, malformed, source_ref=SOURCE, artifact_ref=artifact_ref)
    assert legacy == expected and legacy["response"][response_field] is None
    assert legacy["issues"] == [] and legacy["representation_state"] == "complete"
    assert "observed_transfer" not in legacy
    assert provider.validate_provider_result(legacy) == legacy
    assert json.loads(json.dumps(legacy, allow_nan=False)) == legacy
    with pytest.raises(ValueError, match="molecular_provider_value_invalid"):
        provider.provider_value(operation, malformed, artifact_ref=artifact_ref)


@pytest.mark.parametrize("change", [
    {"source_ref": SOURCE}, {"version": "molecular_provider_result_v1"},
    {"raw_artifact_ref": "artifact_" + "a" * 63}, {"service": "kegg"},
    {"issues": []}, {"representation_state": "complete"},
])
def test_value_rejects_source_invention_and_legacy_qualification_tampering(change):
    native = deepcopy(NATIVE[STRING])
    native[0]["ncbiTaxonId"] = "9606"
    value = _value(_native(STRING, native), STRING)
    with pytest.raises(ValueError):
        provider.validate_provider_value({**value, **change})


@pytest.mark.parametrize("native,code", [
    ({}, "native_id_missing"), ({"stId": None}, "native_id_invalid"),
    ({"stId": False}, "native_id_invalid"), ({"stId": ""}, "native_id_invalid"),
    ({"stId": "R-HSA-141409.1"}, "native_id_differs_from_request"),
    ({"nested": {"stId": "R-HSA-141409"}}, "native_id_missing"),
])
def test_reactome_confirms_only_exact_native_stable_id(native, code):
    assert _receipt(_native(REACTOME, native), REACTOME) == _failure(code)


@pytest.mark.parametrize("native,code", [
    ({"results": []}, "empty_lookup"), ({}, "native_results_missing"),
    ({"results": None}, "native_results_not_array"),
    ({"results": [{"id": "GO:0000001"}, None]}, "native_row_not_object"),
    ({"results": [{"id": "GO:0000001"}, {"id": "GO:0000002"}]}, "native_id_differs_from_request"),
    ({"results": [{}]}, "native_id_missing"), ({"results": [{"id": None}]}, "native_id_invalid"),
])
def test_quickgo_empty_or_any_nonmatching_row_does_not_confirm_the_requested_term(native, code):
    value = _value(_native(QUICKGO, native), QUICKGO)
    assert provider.provider_receipt(value, source_ref=SOURCE) == _failure(code)
    if native == {"results": []}:
        assert value["representation_state"] == "complete" and value["issues"] == []


def test_quickgo_preserves_all_exact_duplicate_rows_and_pagination_without_exhaustiveness_claim():
    native = {"results": [{"id": "GO:0000001", "isObsolete": True, "replacedBy": "GO:0000002"},
        {"id": "GO:0000001", "children": [{"id": "GO:0000003", "relation": "part_of"}]}],
        "numberOfHits": 51, "pageInfo": {"current": 1, "total": 9}}
    value = _value(_native(QUICKGO, native), QUICKGO)
    assert value["native_json"] == native and value["population_coverage"] == "selected_response_only"
    assert provider.provider_receipt(value, source_ref=SOURCE)["acquired"] is True


@pytest.mark.parametrize("taxon,code", [
    (9606, None), ("9606", None), (9606.0, "native_taxon_invalid"),
    (True, "native_taxon_invalid"), (None, "native_taxon_invalid"),
    ("09606", "native_taxon_invalid"), ("9606 ", "native_taxon_invalid"),
    (10090, "native_taxon_differs_from_request"), ("10090", "native_taxon_invalid"),
])
def test_string_taxon_matches_exact_integer_or_observed_decimal_string_without_coercion(taxon, code):
    native = deepcopy(NATIVE[STRING])
    native[0]["ncbiTaxonId"] = taxon
    value = _value(_native(STRING, native), STRING)
    receipt = provider.provider_receipt(value, source_ref=SOURCE)
    if code is not None:
        assert receipt == _failure(code)
    else:
        assert receipt["acquired"] is True
    assert value["native_json"] == native
    if type(taxon) is str:
        assert value["issues"] == [dict(code="native_taxon_invalid",
            pointer="/native_json/0/ncbiTaxonId", line_number=None)]


@pytest.mark.parametrize("native,code", [
    ({}, "json_root_not_array"), ([None], "native_row_not_object"),
    ([{"stringId_A": IDS[0], "ncbiTaxonId": "9606"}], "native_id_missing"),
    ([{"stringId_A": IDS[0], "stringId_B": "9606.UNREQUESTED", "ncbiTaxonId": "9606"}],
        "native_edge_outside_request"),
])
def test_string_never_accepts_unrequested_or_unidentified_edge_endpoints(native, code):
    assert _receipt(_native(STRING, native), STRING) == _failure(code)


def test_string_empty_requested_network_is_acquired_and_original_occurrences_remain_ordered():
    empty = _value(_native(STRING, []), STRING)
    assert provider.provider_receipt(empty, source_ref=SOURCE)["acquired"] is True
    assert empty["native_json"] == [] and empty["issues"] == []
    rows = deepcopy(NATIVE[STRING]) * 2
    rows.append({"stringId_A": IDS[1], "stringId_B": IDS[0], "ncbiTaxonId": "9606", "score": None})
    value = _value(_native(STRING, rows), STRING)
    assert value["native_json"] == rows and provider.provider_receipt(value, source_ref=SOURCE)["acquired"]


def test_string_observed_string_taxon_and_mime_qualifications_remain_literal_on_success():
    rows = deepcopy(NATIVE[STRING])
    rows[0]["ncbiTaxonId"] = "9606"
    capture = _transport(_native(STRING, rows), headers={"content-type": "text/html; charset=utf-8"})
    value = _value(capture, STRING)
    assert value["representation_state"] == "partial"
    assert value["issues"] == [
        dict(code="content_type_mismatch", pointer="/response/content_type", line_number=None),
        dict(code="native_taxon_invalid", pointer="/native_json/0/ncbiTaxonId", line_number=None)]
    legacy = provider.provider_result_from_value(value, source_ref=SOURCE)
    assert legacy["issues"] == value["issues"] and legacy["representation_state"] == "partial"
    assert provider.provider_receipt(value, source_ref=SOURCE)["acquired"] is True


@pytest.mark.parametrize("raw,code", [
    (b"ENTRY       R00259 Reaction\n", "kegg_terminator_count"),
    (b"ENTRY       R00259 Reaction\nENTRY       R00259 Reaction\n///\n", "kegg_entry_count"),
    (b"ENTRY       R00001 Reaction\n///\n", "native_id_differs_from_request"),
    (b"ENTRY       \n///\n", "native_id_missing"),
    (b"ENTRY       R00259 Reaction\n///\nNAME        late\n", "kegg_trailing_data"),
    (b"            orphan\nENTRY       R00259 Reaction\n///\n", "kegg_orphan_continuation"),
])
def test_kegg_requires_one_exact_entry_and_complete_native_field_grammar(raw, code):
    assert _receipt(snapshot(KEGG, raw=raw), KEGG) == _failure(code)


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("changes,code", [
    ({"status": None}, "transport_metadata_unavailable"),
    ({"status": True}, "transport_metadata_unavailable"),
    ({"status": 404}, "http_not_success"), ({"status": 302}, "http_redirect"),
    ({"body_complete": False}, "response_incomplete"),
    ({"body_complete": None}, "response_incomplete"),
    ({"retained_body_bytes": False}, "transport_metadata_unavailable"),
    ({"retained_body_bytes": 0}, "transport_count_conflict"),
    ({"observed_body_bytes": None}, "transport_metadata_unavailable"),
    ({"declared_body_bytes": 0}, "transport_count_conflict"),
    ({"declared_body_bytes": False}, "transport_metadata_unavailable"),
    ({"body_capture_failure": False}, "transport_metadata_unavailable"),
    ({"response_byte_limit": 9999}, "transport_count_conflict"),
    ({"body_capture_failure": "interrupted"}, "response_capture_failure"),
])
def test_confirmation_requires_known_complete_successful_transfer_and_literal_counts(operation, changes, code):
    value = _value(_transport(snapshot(operation), **changes), operation)
    assert value["representation_state"] == "complete"
    assert provider.provider_receipt(value, source_ref=SOURCE) == _failure(code)


@pytest.mark.parametrize("operation", OPERATIONS)
def test_chunked_response_without_declared_length_preserves_confirmed_native(operation):
    capture = _transport(snapshot(operation), declared_body_bytes=None)
    assert _receipt(capture, operation)["acquired"] is True


@pytest.mark.parametrize("raw,code", [
    (b"\xff", "invalid_native_utf8"), (b"null", "json_root_not_object"),
    (b' {"stId":"R-HSA-141409","stId":"R-HSA-141409"}', "invalid_native_json"),
    (b'{"stId":"R-HSA-141409","x":1e-999}', "invalid_native_json"),
    (b'{"stId":"R-HSA-141409","x":NaN}', "invalid_native_json"),
])
def test_invalid_native_representation_never_becomes_selected_item_success(raw, code):
    assert _receipt(snapshot(REACTOME, raw=raw), REACTOME) == _failure(code)


@pytest.mark.parametrize("operation", OPERATIONS)
def test_direct_publisher_retains_raw_primary_and_one_source_free_value_before_source(publisher, monkeypatch, operation):
    store, registry = publisher
    capture = snapshot(operation)
    original_source = registry._source
    def source_after_evidence(*args, **kwargs):
        references = kwargs["auxiliary_artifact_refs"]
        assert len(references) == 1
        value = json.loads(store.get_artifact(references[0]))
        assert provider.validate_provider_value(value) == _value(capture, operation)
        assert "source_ref" not in value
        return original_source(*args, **kwargs)
    monkeypatch.setattr(registry, "_source", source_after_evidence)
    receipt, refs = _publish(registry, operation, capture)
    source = store.get(receipt["source_ref"])
    assert receipt == dict(acquired=True, source_ref=source["id"], data_ref=source["artifact_ref"], failure_code=None)
    assert refs == [source["id"], source["artifact_ref"]]
    assert source["provider"] == capture.service and source["origin"] == "external" and source["version"] is None
    if operation == PUBCHEM:
        assert source["accession"] == str(ARGUMENTS[PUBCHEM]["cid"])
    assert source["uri"] == capture.transport["request"]["url"]
    assert store.get_artifact(source["artifact_ref"]) == capture.content
    assert json.loads(store.get_artifact(source["request_ref"])) == {
        "request": capture.request, "transport": capture.transport}
    evidence_ref, = source["auxiliary_artifact_refs"]
    assert evidence_ref not in refs and source["request_ref"] not in refs
    evidence = json.loads(store.get_artifact(evidence_ref))
    assert evidence == _value(capture, operation) and evidence["raw_artifact_ref"] == source["artifact_ref"]
    assert store.get_artifact(evidence_ref) == canonical(evidence).encode()
    assert store.db.execute("SELECT count(*) FROM records WHERE record_type='source'").fetchone()[0] == 1
    tables = {row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table in ("tool_operations", "runtime_episodes", "runtime_actions", "runtime_model_calls", "runtime_observations"):
        if table in tables:
            assert store.db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0


@pytest.mark.parametrize("case", ["url", "service", "method", "wire_query", "policy", "request_type"])
def test_contradictory_snapshot_keeps_literal_source_and_request_without_data_or_invented_value(publisher, case):
    store, registry = publisher
    capture = snapshot(STRING)
    arguments = deepcopy(capture.request)
    if case == "url":
        capture = replace(capture, url=capture.url + "/other")
    elif case == "service":
        capture = replace(capture, service="engineered_other_service")
    elif case == "method":
        capture = _transport(capture, request={**capture.transport["request"], "method": "POST"})
    elif case == "wire_query":
        capture = _transport(capture, request={**capture.transport["request"],
            "url": capture.transport["request"]["url"] + "&add_nodes=1"})
    elif case == "policy":
        capture = _transport(capture, request_policy={"timeout_seconds": 90, "automatic_redirects": True})
    else:
        capture = replace(capture, request={**arguments, "max_bytes": 10000.0})
    receipt, refs = _publish(registry, STRING, capture, arguments=arguments)
    source = store.get(receipt["source_ref"])
    assert receipt == provider.failed_provider_receipt("molecular_provider_request_conflict", source_ref=source["id"])
    assert refs == [source["id"]] and source["uri"] == capture.url
    assert store.get_artifact(source["artifact_ref"]) == capture.content
    assert json.loads(store.get_artifact(source["request_ref"])) == {
        "request": capture.request, "transport": capture.transport}
    witness_ref, = source["auxiliary_artifact_refs"]
    witness = json.loads(store.get_artifact(witness_ref))
    assert witness == dict(version="molecular_provider_failure_witness_v1",
        observed_snapshot_service=capture.service, observed_snapshot_url=capture.url,
        failure_code="molecular_provider_request_conflict")
    assert source["provider"] == "string" and witness_ref not in refs


@pytest.mark.parametrize("operation", OPERATIONS)
def test_selected_arguments_cannot_relabel_a_different_authenticated_capture(publisher, operation):
    store, registry = publisher
    selected = deepcopy(ARGUMENTS[operation])
    observed = {**selected, "max_bytes": 20000}
    capture = snapshot(operation, arguments=observed)
    receipt, refs = _publish(registry, operation, capture, arguments=selected)
    source = store.get(receipt["source_ref"])
    assert receipt == provider.failed_provider_receipt("molecular_provider_selected_request_conflict", source_ref=source["id"])
    assert refs == [source["id"]] and source["uri"] == capture.url
    evidence_ref, = source["auxiliary_artifact_refs"]
    evidence = json.loads(store.get_artifact(evidence_ref))
    assert evidence["requested"] == observed and evidence["requested"] != selected
    assert store.get_artifact(source["artifact_ref"]) == capture.content


@pytest.mark.parametrize("case,code", [
    ("native_identity", "native_id_differs_from_request"), ("empty_lookup", "empty_lookup"),
    ("http_error", "http_not_success"), ("partial", "response_incomplete"),
    ("malformed", "invalid_native_json"),
])
def test_captured_failure_keeps_raw_source_and_private_qualifications_without_data(publisher, case, code):
    store, registry = publisher
    if case == "native_identity":
        operation, capture = REACTOME, _native(REACTOME, {"stId": "R-HSA-000000"})
    elif case == "empty_lookup":
        operation, capture = QUICKGO, _native(QUICKGO, {"results": []})
    elif case == "malformed":
        operation, capture = REACTOME, snapshot(REACTOME, raw=b'{"stId":')
    else:
        operation = STRING
        capture = _transport(snapshot(STRING), **({"status": 404} if case == "http_error" else
            {"body_complete": False, "observed_body_bytes": 5000}))
    receipt, refs = _publish(registry, operation, capture)
    source = store.get(receipt["source_ref"])
    assert receipt == provider.failed_provider_receipt("molecular_provider_" + code, source_ref=source["id"])
    assert refs == [source["id"]] and store.get_artifact(source["artifact_ref"]) == capture.content
    evidence_ref, = source["auxiliary_artifact_refs"]
    assert json.loads(store.get_artifact(evidence_ref)) == _value(capture, operation)


@pytest.mark.parametrize("case", ["operation", "arguments", "no_response"])
def test_invalid_selected_input_or_absent_snapshot_does_not_publish(publisher, monkeypatch, case):
    store, registry = publisher
    monkeypatch.setattr(registry, "_source", _forbidden)
    monkeypatch.setattr(store, "artifact", _forbidden)
    operation, arguments, capture = REACTOME, ARGUMENTS[REACTOME], snapshot(REACTOME)
    if case == "operation":
        operation = "public.reactome.unselected"
    elif case == "arguments":
        arguments = {**arguments, "max_bytes": True}
    else:
        capture = None
    with pytest.raises(ValueError):
        provider.publish_molecular_provider_request(registry, operation, arguments, capture)
    assert list(store.list("source")) == []


@pytest.mark.parametrize("native,code,pointer", PUBCHEM_IDENTITY_FAILURES)
def test_pubchem_every_native_compound_must_confirm_the_exact_selected_cid(native, code, pointer):
    value = _value(_native(PUBCHEM, native), PUBCHEM)
    assert value["native_json"] == native
    assert value["issues"] == [dict(code=code, pointer=pointer, line_number=None)]
    assert provider.provider_receipt(value, source_ref=SOURCE) == _failure(code)


def test_pubchem_empty_native_lookup_is_observed_empty_but_does_not_acquire_a_compound():
    native = {"PC_Compounds": [], "unknown": {"zero": 0, "null": None}}
    value = _value(_native(PUBCHEM, native), PUBCHEM)
    assert value["native_json"] == native
    assert value["representation_state"] == "complete" and value["issues"] == []
    assert provider.provider_receipt(value, source_ref=SOURCE) == _failure("empty_lookup")


def test_pubchem_duplicate_exact_identities_remain_individual_native_occurrences():
    native = deepcopy(NATIVE[PUBCHEM])
    native["PC_Compounds"].append(deepcopy(native["PC_Compounds"][0]))
    value = _value(_native(PUBCHEM, native), PUBCHEM)
    assert value["native_json"] == native and len(value["native_json"]["PC_Compounds"]) == 3
    assert value["population_coverage"] == "selected_response_only"
    receipt = provider.provider_receipt(value, source_ref=SOURCE)
    assert receipt == dict(acquired=True, source_ref=SOURCE, data_ref=value["raw_artifact_ref"], failure_code=None)


@pytest.mark.parametrize("native,code", [
    ({"PC_Compounds": []}, "empty_lookup"),
    ({"PC_Compounds": [{"id": {"id": {"cid": "2244"}}}]}, "native_id_invalid"),
    ({"PC_Compounds": [{"id": {"id": {"cid": 2244}}},
        {"id": {"id": {"cid": 2245}}}]}, "native_id_differs_from_request"),
])
def test_pubchem_failed_confirmation_keeps_exact_raw_source_and_private_value(publisher, native, code):
    store, registry = publisher
    capture = _native(PUBCHEM, native)
    receipt, refs = _publish(registry, PUBCHEM, capture)
    source = store.get(receipt["source_ref"])
    assert receipt == provider.failed_provider_receipt("molecular_provider_" + code, source_ref=source["id"])
    assert refs == [source["id"]] and source["accession"] == "2244"
    assert source["artifact_ref"] == "artifact_" + hashlib.sha256(capture.content).hexdigest()
    assert store.get_artifact(source["artifact_ref"]) == capture.content
    assert json.loads(store.get_artifact(source["request_ref"])) == {
        "request": capture.request, "transport": capture.transport}
    value_ref, = source["auxiliary_artifact_refs"]
    assert value_ref not in refs and source["artifact_ref"] not in refs
    assert json.loads(store.get_artifact(value_ref)) == _value(capture, PUBCHEM)
