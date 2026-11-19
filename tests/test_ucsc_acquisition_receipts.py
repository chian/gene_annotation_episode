"""Engineered UCSC confirmations using the existing native contract authority.

No live HTTP, sequence conversion, scientific calculation or runtime history is
invented. Direct publisher controls use real Source/Artifact custody only.
"""
import hashlib

import pytest

from gene_annotation_episode import ucsc_acquisition as ucsc
from gene_annotation_episode.domain import ContractError
from test_ucsc_acquisition import HUB, SOURCE, arguments, native, snapshot


def value(capture):
    return ucsc.ucsc_value(capture, arguments=capture.request,
        artifact_ref="artifact_" + hashlib.sha256(capture.content).hexdigest())


def receipt(capture):
    return ucsc.ucsc_receipt(value(capture), source_ref=SOURCE)


def failure(code):
    return ucsc.failed_ucsc_receipt("ucsc_" + code, source_ref=SOURCE)


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
