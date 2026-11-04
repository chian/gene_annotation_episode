"""Engineered UCSC confirmations using the existing native contract authority.

No live HTTP, sequence conversion, scientific calculation or runtime history is
invented. Direct publisher controls use real Source/Artifact custody only.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import ucsc_acquisition as ucsc
from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.data_acquisition_receipts import acquisition_receipt_schema
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_ucsc_acquisition import HUB, SOURCE, arguments, native, snapshot


def forbidden(*args, **kwargs):
    raise AssertionError("UCSC receipt controls attempted HTTP or scientific work")


def value(capture):
    return ucsc.ucsc_value(capture, arguments=capture.request,
        artifact_ref="artifact_" + hashlib.sha256(capture.content).hexdigest())


def receipt(capture):
    return ucsc.ucsc_receipt(value(capture), source_ref=SOURCE)


def failure(code):
    return ucsc.failed_ucsc_receipt("ucsc_" + code, source_ref=SOURCE)


@pytest.fixture
def publisher(tmp_path, monkeypatch):
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    with Store(tmp_path / "store") as store:
        registry = ToolRegistry(store)
        def record_materialization(result, source):
            # This recorder proves invocation/operands only. It does not create
            # a Reference; actual availability/admission belongs to host tests.
            record_materialization.calls.append((deepcopy(result), deepcopy(source)))
            return None
        record_materialization.calls = []
        monkeypatch.setattr(registry, "_publish_ucsc_sequence_reference", record_materialization)
        yield store, registry


def publish(registry, selected, capture):
    token = registry._publications.set([])
    try:
        return ucsc.publish_ucsc_request(registry, selected, capture)
    finally:
        registry._publications.reset(token)


def test_common_four_field_schema_and_no_response_failure_create_neither_reference(publisher, monkeypatch):
    store, registry = publisher
    monkeypatch.setattr(store, "artifact", forbidden)
    monkeypatch.setattr(registry, "_source", forbidden)
    assert ucsc.ucsc_receipt_schema() == acquisition_receipt_schema(failure_codes=ucsc.UCSC_FAILURE_CODES)
    assert len(ucsc.UCSC_FAILURE_CODES) == len(set(ucsc.UCSC_FAILURE_CODES))
    result = ucsc.failed_ucsc_receipt("data_acquisition_failed")
    assert result == dict(acquired=False, source_ref=None, data_ref=None, failure_code="data_acquisition_failed")
    assert Draft202012Validator(ucsc.ucsc_receipt_schema()).is_valid(result)
    assert ucsc.validate_ucsc_receipt(result) == result and ucsc.validate_ucsc_receipt(result) is not result
    assert list(store.list("source")) == []
    with pytest.raises(ContractError, match="ucsc_receipt_invalid"):
        ucsc.failed_ucsc_receipt("literal_unregistered_diagnostic")


@pytest.mark.parametrize("change", [
    {"acquired": 1}, {"source_ref": None}, {"data_ref": None}, {"extra": None},
    {"source_ref": SOURCE + "\n"}, {"data_ref": "reference_" + "a" * 24},
    {"failure_code": "data_acquisition_failed"},
    {"acquired": False, "failure_code": "data_acquisition_failed"},
])
def test_receipt_rejects_shape_types_and_source_data_contradictions(change):
    result = dict(acquired=True, source_ref=SOURCE, data_ref="artifact_" + "a" * 64, failure_code=None)
    with pytest.raises(ContractError, match="ucsc_receipt_invalid"):
        ucsc.validate_ucsc_receipt({**result, **change})


@pytest.mark.parametrize("operation", ucsc.OPERATIONS)
def test_source_free_value_and_real_source_wrapper_preserve_exact_legacy_json(operation):
    capture = snapshot(arguments(operation))
    private = value(capture)
    before = deepcopy(private)
    assert private["version"] == "ucsc_acquisition_value_v1" and "source_ref" not in private
    assert "source_ref" not in ucsc.ucsc_value_schema()["properties"]
    assert Draft202012Validator(ucsc.ucsc_value_schema()).is_valid(private)
    legacy = ucsc.ucsc_result(capture, arguments=capture.request, source_ref=SOURCE,
        artifact_ref=private["raw_artifact_ref"])
    public = {key: child for key, child in private.items() if key != "observed_transfer"}
    assert legacy == {**public, "version": "ucsc_acquisition_result_v1", "source_ref": SOURCE}
    assert ucsc.ucsc_result_from_value(private, source_ref=SOURCE) == legacy
    assert ucsc.validate_ucsc_result(legacy) == legacy
    assert private["native_json"] == native(operation) and private["native_document"] is None
    assert private["population_coverage"] == "selected_response_only" and private["issues"] == []
    assert ucsc.ucsc_receipt(private, source_ref=SOURCE) == dict(acquired=True,
        source_ref=SOURCE, data_ref=private["raw_artifact_ref"], failure_code=None)
    legacy["requested"]["max_bytes"] = 1
    assert private == before


@pytest.mark.parametrize("field,raw,response_field", [
    ("declared_body_bytes", False, "declared_body_bytes"),
    ("declared_body_bytes", -1, "declared_body_bytes"),
    ("declared_body_bytes", "0", "declared_body_bytes"),
    ("body_capture_failure", False, "capture_failure"),
    ("body_capture_failure", 0, "capture_failure"),
])
def test_optional_malformed_transfer_stays_literal_privately_and_normalized_in_legacy(field, raw, response_field):
    selected = arguments("sequence")
    capture = snapshot(selected, **{field: raw})
    private = value(capture)
    expected = ucsc.ucsc_result(snapshot(selected), arguments=selected, source_ref=SOURCE,
        artifact_ref=private["raw_artifact_ref"])
    expected["response"][response_field] = None
    legacy = ucsc.ucsc_result(capture, arguments=selected, source_ref=SOURCE, artifact_ref=private["raw_artifact_ref"])
    assert legacy == expected and legacy["response"][response_field] is None and legacy["issues"] == []
    assert private["observed_transfer"][field] == raw
    assert type(private["observed_transfer"][field]) is type(raw)
    assert ucsc.ucsc_result_from_value(private, source_ref=SOURCE) == legacy
    assert ucsc.ucsc_receipt(private, source_ref=SOURCE) == failure("transport_metadata_unavailable")


@pytest.mark.parametrize("field,raw", [
    ("declared_body_bytes", float("nan")), ("body_capture_failure", b"bad")])
def test_nonjson_transport_remains_rejected_by_the_original_whole_transport_authority(field, raw):
    selected = arguments("sequence")
    capture = snapshot(selected, **{field: raw})
    artifact = "artifact_" + hashlib.sha256(capture.content).hexdigest()
    with pytest.raises(ValueError):
        ucsc.ucsc_result(capture, arguments=selected, source_ref=SOURCE, artifact_ref=artifact)
    with pytest.raises(ValueError):
        ucsc.ucsc_value(capture, arguments=selected, artifact_ref=artifact)


@pytest.mark.parametrize("changes,code", [
    ({"status": None}, "transport_metadata_unavailable"), ({"status": True}, "transport_metadata_unavailable"),
    ({"status": 404}, "http_not_success"), ({"status": 302}, "http_redirect"),
    ({"body_complete": False}, "response_incomplete"), ({"body_complete": None}, "response_incomplete"),
    ({"retained_body_bytes": False}, "transport_metadata_unavailable"),
    ({"retained_body_bytes": 0}, "transport_count_conflict"),
    ({"observed_body_bytes": None}, "transport_metadata_unavailable"),
    ({"observed_body_bytes": 0}, "transport_count_conflict"),
    ({"declared_body_bytes": 0}, "transport_count_conflict"),
    ({"response_byte_limit": 1}, "transport_count_conflict"),
    ({"body_capture_failure": "interrupted"}, "response_capture_failure"),
])
def test_transfer_confirmation_is_independent_of_complete_native_representation(changes, code):
    private = value(snapshot(arguments("sequence"), **changes))
    assert private["representation_state"] == "complete"
    assert ucsc.ucsc_receipt(private, source_ref=SOURCE) == failure(code)


def test_no_declared_content_length_is_valid_without_inventing_a_count():
    private = value(snapshot(arguments("sequence"), declared_body_bytes=None))
    assert private["response"]["declared_body_bytes"] is None
    assert ucsc.ucsc_receipt(private, source_ref=SOURCE)["acquired"] is True


@pytest.mark.parametrize("operation,status", [("track", 206), ("genark_genomes", 200)])
def test_known_item_caps_confirm_only_the_bounded_selected_response(operation, status):
    selected = arguments(operation)
    if operation == "genark_genomes":
        selected["genome"] = "literal-selected-registry-filter"
    payload = {**native(operation), "maxItemsLimit": True, "dataDownloadUrl": "https://example.org/unselected.gz"}
    private = value(snapshot(selected, payload, status=status))
    assert private["native_item_cap"]["state"] == "reached"
    assert private["population_coverage"] == "selected_response_only"
    assert private["native_json"] == payload
    assert ucsc.ucsc_receipt(private, source_ref=SOURCE)["acquired"] is True
    if operation == "genark_genomes":
        assert private["native_counts"]["totalAssemblies"]["meaning"] == "genark_registry_assemblies"
        assert private["reported_identity"]["genome"]["state"] == "missing"


@pytest.mark.parametrize("operation", [name for name in ucsc.OPERATIONS if name != "sequence"])
def test_empty_correct_listing_containers_are_data_not_missing_or_a_population_absence_claim(operation):
    payload = native(operation)
    container = {"ucsc_genomes": "ucscGenomes", "genark_genomes": "genarkGenomes",
        "public_hubs": "publicHubs", "hub_genomes": "genomes", "tracks": "hg38",
        "chromosomes": "chromosomes", "schema": "columnTypes", "track": "genes"}[operation]
    payload[container] = [] if operation in {"public_hubs", "schema", "track"} else {}
    if operation in {"track", "genark_genomes"}:
        payload["itemsReturned"] = 0
    if operation == "chromosomes":
        payload["chromCount"] = 0
    private = value(snapshot(arguments(operation), payload))
    assert private["native_json"] == payload and private["population_coverage"] == "selected_response_only"
    assert ucsc.ucsc_receipt(private, source_ref=SOURCE)["acquired"] is True


def test_missing_count_and_reported_zero_remain_distinct_with_the_same_empty_data_confirmation():
    payload = {**native("track"), "genes": []}
    payload.pop("itemsReturned")
    missing = value(snapshot(arguments("track"), payload))
    zero = value(snapshot(arguments("track"), {**payload, "itemsReturned": 0}))
    assert missing["native_counts"]["itemsReturned"]["state"] == "missing"
    assert missing["native_counts"]["itemsReturned"]["value"] is None
    assert zero["native_counts"]["itemsReturned"]["value"] == 0
    assert zero["native_counts"]["itemsReturned"]["number_token"] == "0"
    assert ucsc.ucsc_receipt(missing, source_ref=SOURCE)["acquired"]
    assert ucsc.ucsc_receipt(zero, source_ref=SOURCE)["acquired"]


@pytest.mark.parametrize("native_type,meaning", [("bigWig", "bigwig_valid_covered_bases"),
    ("genePred", "whole_track_records"), ("newNativeType", "native_count_unspecified")])
def test_native_count_meanings_and_qualified_schema_scope_are_not_reinterpreted(native_type, meaning):
    payload = {**native("schema"), "type": native_type}
    private = value(snapshot(arguments("schema"), payload))
    assert private["native_counts"]["itemCount"]["meaning"] == meaning
    assert ucsc.ucsc_receipt(private, source_ref=SOURCE)["acquired"]
    qualified = value(snapshot(arguments("schema"), {**payload, "splitTable": True, "itemCount": 0}))
    assert qualified["native_counts"]["itemCount"]["value"] == 0
    assert qualified["native_counts"]["itemCount"]["meaning"] == "native_count_unspecified"
    assert "native_count_scope_qualified" in {row["code"] for row in qualified["issues"]}
    assert ucsc.ucsc_receipt(qualified, source_ref=SOURCE)["acquired"]


def test_duplicate_number_and_mime_qualifications_keep_original_document_and_legacy_interval_policy():
    raw = b'{"genome":"hg38","chrom":"chr1","start":10,"end":14,"dna":"AcgN","extra":0,"extra":1e-9999}'
    capture = snapshot(arguments("sequence"), raw=raw, headers={"content-type": "text/plain"})
    private = value(capture)
    assert private["parse_state"] == "json_document" and private["native_json"] is None
    assert [row["value"]["token"] for row in private["native_document"]["members"] if row["name"] == "extra"] == ["0", "1e-9999"]
    assert {row["code"] for row in private["issues"]} == {
        "native_duplicate_member", "native_number_token_required", "content_type_mismatch"}
    assert ucsc.ucsc_receipt(private, source_ref=SOURCE)["acquired"]
    legacy = ucsc.ucsc_result_from_value(private, source_ref=SOURCE)
    assert legacy["issues"] == private["issues"] and ucsc.ucsc_sequence_interval(legacy) is None


@pytest.mark.parametrize("operation,change,code", [
    ("sequence", {"genome": "mm39"}, "native_identity_differs_from_request"),
    ("sequence", {"chrom": "chr2"}, "native_identity_differs_from_request"),
    ("sequence", {"start": 11}, "native_interval_differs_from_request"),
    ("sequence", {"end": 15}, "native_interval_differs_from_request"),
    ("sequence", {"revComp": True}, "native_orientation_differs_from_request"),
    ("sequence", {"dna": "ACG"}, "native_sequence_length_conflict"),
    ("sequence", {"dna": ""}, "native_sequence_invalid"),
    ("sequence", {"dna": None}, "native_sequence_invalid"),
    ("track", {"itemsReturned": 2}, "native_count_conflict"),
    ("track", {"itemsReturned": None}, "native_count_invalid"),
    ("track", {"genes": [None]}, "native_row_shape_invalid"),
    ("schema", {"columnTypes": [None]}, "native_column_context_invalid"),
])
def test_native_contradictions_are_not_success_even_when_http_capture_is_complete(operation, change, code):
    private = value(snapshot(arguments(operation), {**native(operation), **change}))
    assert private["response"]["body_complete"] is True
    assert ucsc.ucsc_receipt(private, source_ref=SOURCE) == failure(code)


def test_native_array_columns_require_their_original_names_arity_and_types():
    selected = arguments("track", json_output_arrays=True)
    payload = {**native("track"), "genes": [["chr1", 5]], "columnTypes": {"genes": [
        {"name": "chrom", "sqlType": "varchar", "jsonType": "string"},
        {"name": "start", "sqlType": "int", "jsonType": "number"}]}}
    private = value(snapshot(selected, payload))
    assert ucsc.ucsc_receipt(private, source_ref=SOURCE)["acquired"]
    payload["genes"][0][1] = False
    assert receipt(snapshot(selected, payload)) == failure("native_column_type_conflict")
    payload["genes"] = [["chr1"]]
    assert receipt(snapshot(selected, payload)) == failure("native_column_arity_conflict")
    payload.pop("columnTypes")
    assert receipt(snapshot(selected, payload)) == failure("native_column_context_missing")


def test_critical_duplicate_identity_and_missing_206_cap_signal_fail_without_choosing_a_winner():
    raw = b'{"genome":"hg38","genome":"mm39","chrom":"chr1","start":10,"end":14,"dna":"AcgN"}'
    private = value(snapshot(arguments("sequence"), raw=raw))
    assert private["reported_identity"]["genome"]["state"] == "ambiguous"
    assert ucsc.ucsc_receipt(private, source_ref=SOURCE) == failure("native_identity_ambiguous")
    assert receipt(snapshot(arguments("track"), status=206)) == failure("native_item_cap_signal_missing")


def test_supplied_hub_and_reverse_orientation_require_their_literal_native_associations():
    selected = arguments("sequence", hub_url=HUB, rev_comp=True)
    payload = {**native("sequence"), "hubUrl": HUB, "revComp": True, "dna": "NcGt"}
    private = value(snapshot(selected, payload))
    assert private["reported_identity"]["hub_url"]["value"] == HUB
    assert private["native_orientation"]["requested"] == "reverse_complement"
    assert ucsc.ucsc_receipt(private, source_ref=SOURCE)["acquired"]
    missing_hub = {key: child for key, child in payload.items() if key != "hubUrl"}
    assert receipt(snapshot(selected, missing_hub)) == failure("native_identity_missing")
    assert receipt(snapshot(selected, {**payload, "hubUrl": "https://example.org/other/hub.txt"})) == failure(
        "native_identity_differs_from_request")
    missing_orientation = {key: child for key, child in payload.items() if key != "revComp"}
    assert receipt(snapshot(selected, missing_orientation)) == failure("native_orientation_missing")


def test_native_error_envelope_is_not_data_but_a_track_literally_named_error_remains_data():
    body = {"error": "Native diagnostic", "statusCode": 403, "statusMessage": "Forbidden"}
    private = value(snapshot(arguments("sequence"), body))
    assert private["native_response_state"] == "error" and private["native_json"] == body
    assert ucsc.ucsc_receipt(private, source_ref=SOURCE) == failure("native_error_response")
    payload = native("track")
    payload["error"], payload["track"] = payload.pop("genes"), "error"
    assert receipt(snapshot(arguments("track", track="error"), payload))["acquired"]


@pytest.mark.parametrize("raw,code", [(b"\xff", "invalid_native_utf8"), (b"{", "invalid_native_json"),
    (b"null", "json_root_not_object"), (b"[]", "json_root_not_object"),
    (b'{"ucscGenomes":{},"x":NaN}', "invalid_native_json")])
def test_invalid_native_representation_retains_its_raw_artifact_identity_without_confirmation(raw, code):
    private = value(snapshot(arguments("ucsc_genomes"), raw=raw))
    assert private["raw_artifact_ref"] == "artifact_" + hashlib.sha256(raw).hexdigest()
    assert ucsc.ucsc_receipt(private, source_ref=SOURCE) == failure(code)


@pytest.mark.parametrize("damage", ["source", "version", "identity", "count_bool", "cap", "transfer"])
def test_private_value_rejects_invented_source_and_native_or_transfer_crossfield_tampering(damage):
    private = value(snapshot(arguments("track")))
    if damage == "source": private["source_ref"] = SOURCE
    elif damage == "version": private["version"] = ucsc.VERSION
    elif damage == "identity": private["reported_identity"]["genome"]["value"] = "mm39"
    elif damage == "count_bool": private["native_counts"]["itemsReturned"]["value"] = True
    elif damage == "cap": private["native_item_cap"]["state"] = "reached"
    else: private["observed_transfer"]["declared_body_bytes"] = 0
    with pytest.raises(ValueError): ucsc.validate_ucsc_value(private)


def test_saved_private_value_confirmation_and_legacy_wrapping_require_no_original_bytes_or_parser(monkeypatch):
    capture = snapshot(arguments("sequence"))
    private = json.loads(canonical(value(capture)))
    legacy = ucsc.ucsc_result_from_value(private, source_ref=SOURCE)
    expected = ucsc.ucsc_receipt(private, source_ref=SOURCE)
    monkeypatch.setattr(ucsc, "_parse", forbidden)
    monkeypatch.setattr(ucsc, "_snapshot_response", forbidden)
    monkeypatch.setattr(ucsc, "ucsc_value", forbidden)
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    assert ucsc.ucsc_receipt(private, source_ref=SOURCE) == expected
    assert ucsc.ucsc_result_from_value(private, source_ref=SOURCE) == legacy


@pytest.mark.parametrize("operation", ucsc.OPERATIONS)
def test_publisher_keeps_raw_json_refs_and_requests_sequence_materialization_without_receipt_grant(publisher, monkeypatch, operation):
    store, registry = publisher
    capture = snapshot(arguments(operation))
    original_source = registry._source
    def source_after_private_value(*args, **kwargs):
        private_ref, = kwargs["auxiliary_artifact_refs"]
        assert ucsc.validate_ucsc_value(json.loads(store.get_artifact(private_ref))) == value(capture)
        return original_source(*args, **kwargs)
    monkeypatch.setattr(registry, "_source", source_after_private_value)
    result, refs = publish(registry, capture.request, capture)
    source = store.get(result["source_ref"])
    assert result == dict(acquired=True, source_ref=source["id"], data_ref=source["artifact_ref"], failure_code=None)
    assert refs == [source["id"], source["artifact_ref"]]
    assert source["provider"] == "ucsc" and source["origin"] == "external"
    assert source["version"] is source["accession"] is None
    assert source["uri"] == capture.transport["request"]["url"]
    assert store.get_artifact(source["artifact_ref"]) == capture.content
    assert json.loads(store.get_artifact(source["request_ref"])) == {
        "request": capture.request, "transport": capture.transport}
    private_ref, = source["auxiliary_artifact_refs"]
    assert private_ref not in refs and source["request_ref"] not in refs
    assert json.loads(store.get_artifact(private_ref)) == value(capture)
    calls = registry._publish_ucsc_sequence_reference.calls
    assert calls == ([(ucsc.ucsc_result_from_value(value(capture), source_ref=source["id"]), source)]
        if operation == "sequence" else [])
    # The callback above is a recorder, not evidence of native DNA availability.
    assert list(store.list("reference")) == []
    assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 0


@pytest.mark.parametrize("damage", ["service", "uri", "wire", "effective", "redirects", "media", "selected_type"])
def test_contradictory_capture_retains_literal_bytes_uri_controls_and_private_failure_witness(publisher, damage):
    store, registry = publisher
    selected = arguments("sequence")
    capture = snapshot(selected)
    if damage == "service": capture = replace(capture, service="engineered_other_service")
    elif damage == "uri": capture = replace(capture, url="https://example.org/unselected")
    elif damage == "media": capture = replace(capture, media_type="text/plain")
    elif damage == "selected_type": capture = replace(capture, request={**selected, "start": 10.0})
    elif damage == "wire": capture.transport["request"]["url"] += "&unselected=1"
    elif damage == "effective": capture.transport["effective_url"] = "https://example.org/unselected"
    else: capture.transport["request_policy"]["automatic_redirects"] = True
    result, refs = publish(registry, selected, capture)
    source = store.get(result["source_ref"])
    assert result == ucsc.failed_ucsc_receipt("ucsc_request_conflict", source_ref=source["id"])
    assert refs == [source["id"]] and source["uri"] == capture.url
    assert store.get_artifact(source["artifact_ref"]) == capture.content
    assert json.loads(store.get_artifact(source["request_ref"])) == {
        "request": capture.request, "transport": capture.transport}
    private_ref, = source["auxiliary_artifact_refs"]
    assert json.loads(store.get_artifact(private_ref)) == dict(version="ucsc_acquisition_failure_witness_v1",
        observed_snapshot_service=capture.service, observed_snapshot_url=capture.url, failure_code="ucsc_request_conflict")
    assert source["provider"] == "ucsc" and list(store.list("reference")) == []
    assert registry._publish_ucsc_sequence_reference.calls == []


def test_an_authentic_different_interval_is_retained_without_relabelling_it_as_the_selected_data(publisher):
    store, registry = publisher
    selected = arguments("sequence")
    observed = {**selected, "start": 11, "end": 15}
    capture = snapshot(observed, {**native("sequence"), "start": 11, "end": 15})
    result, refs = publish(registry, selected, capture)
    source = store.get(result["source_ref"])
    assert result == ucsc.failed_ucsc_receipt("ucsc_selected_request_conflict", source_ref=source["id"])
    assert refs == [source["id"]] and source["uri"] == capture.url
    private_ref, = source["auxiliary_artifact_refs"]
    assert ucsc.validate_ucsc_value(json.loads(store.get_artifact(private_ref)))["requested"] == observed
    assert list(store.list("reference")) == []
    assert registry._publish_ucsc_sequence_reference.calls == []


@pytest.mark.parametrize("case,code", [("html", "http_not_success"), ("partial", "response_incomplete"),
    ("native", "native_identity_differs_from_request"), ("metadata", "transport_metadata_unavailable")])
def test_failed_captured_response_publishes_source_only_and_preserves_native_or_malformed_evidence(publisher, case, code):
    store, registry = publisher
    selected = arguments("sequence")
    if case == "html": capture = snapshot(selected, raw=b"<html>Original denial</html>", status=403,
        headers={"content-type": "text/html"})
    elif case == "partial": capture = snapshot(selected, body_complete=False, body_capture_failure="interrupted")
    elif case == "metadata": capture = snapshot(selected, declared_body_bytes=False)
    else: capture = snapshot(selected, {**native("sequence"), "genome": "mm39"})
    result, refs = publish(registry, selected, capture)
    source = store.get(result["source_ref"])
    assert result == ucsc.failed_ucsc_receipt("ucsc_" + code, source_ref=source["id"])
    assert refs == [source["id"]] and store.get_artifact(source["artifact_ref"]) == capture.content
    private_ref, = source["auxiliary_artifact_refs"]
    assert ucsc.validate_ucsc_value(json.loads(store.get_artifact(private_ref))) == value(capture)
    assert list(store.list("reference")) == []
    assert registry._publish_ucsc_sequence_reference.calls == []


@pytest.mark.parametrize("case", ["arguments", "snapshot"])
def test_invalid_selection_or_no_snapshot_publishes_nothing(publisher, monkeypatch, case):
    store, registry = publisher
    selected = arguments("sequence")
    capture = snapshot(selected)
    if case == "arguments": selected["max_bytes"] = True
    else: capture = None
    monkeypatch.setattr(registry, "_source", forbidden)
    monkeypatch.setattr(store, "artifact", forbidden)
    with pytest.raises(ValueError): ucsc.publish_ucsc_request(registry, selected, capture)
    assert list(store.list("source")) == []
