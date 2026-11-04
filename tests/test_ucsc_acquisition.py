"""Pure UCSC contract controls; no client, network, Store or scientific job."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import math
from urllib.parse import urlencode

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.ucsc_acquisition import (
    ARGUMENTS_SCHEMA, MAX_ITEMS_OUTPUT, MAX_RESPONSE_BYTES, OPERATIONS, ORIGIN, TOOL,
    ucsc_request_spec, ucsc_result, ucsc_result_schema, ucsc_sequence_interval,
    validate_ucsc_arguments, validate_ucsc_result,
)


SOURCE = "source_" + "a" * 64
HUB = "https://example.org/selected/hub.txt?literal=one&other=two"
CASES = [
    ({"operation": "ucsc_genomes"}, "/list/ucscGenomes", {}),
    ({"operation": "genark_genomes", "genome": None, "max_items_output": 3},
        "/list/genarkGenomes", {"maxItemsOutput": 3}),
    ({"operation": "public_hubs"}, "/list/publicHubs", {}),
    ({"operation": "hub_genomes", "hub_url": HUB}, "/list/hubGenomes", {"hubUrl": HUB}),
    ({"operation": "tracks", "genome": "hg38", "hub_url": None, "track_leaves_only": False},
        "/list/tracks", {"genome": "hg38"}),
    ({"operation": "chromosomes", "genome": "hg38", "hub_url": None, "track": None},
        "/list/chromosomes", {"genome": "hg38"}),
    ({"operation": "schema", "genome": "hg38", "hub_url": None, "track": "genes"},
        "/list/schema", {"genome": "hg38", "track": "genes"}),
    ({"operation": "track", "genome": "hg38", "hub_url": None, "track": "genes", "chrom": "chr1",
        "start": 10, "end": 20, "max_items_output": 3, "json_output_arrays": False},
        "/getData/track", {"genome": "hg38", "track": "genes", "chrom": "chr1", "start": 10,
            "end": 20, "maxItemsOutput": 3}),
    ({"operation": "sequence", "genome": "hg38", "hub_url": None, "chrom": "chr1", "start": 10,
        "end": 14, "rev_comp": False}, "/getData/sequence",
        {"genome": "hg38", "chrom": "chr1", "start": 10, "end": 14}),
]


def arguments(selected_operation, **changes):
    selected = next(deepcopy(row) for row, _, _ in CASES if row["operation"] == selected_operation)
    return {**selected, "max_bytes": 16_384, **changes}


def native(operation):
    return deepcopy({
        "ucsc_genomes": {"ucscGenomes": {"hg38": {"description": "Native assembly",
            "unknown": {"cells": [None, False, 0], "nativePath": "/gbdb/native"}}}},
        "genark_genomes": {"genarkGenomes": {"GCF_000001405.40": {
            "hubUrl": "GCF/000/001/405/GCF_000001405.40/hub.txt", "asmName": "GRCh38.p14"}},
            "hubUrlPrefix": "https://hgdownload.soe.ucsc.edu/hubs", "itemsReturned": 1,
            "totalAssemblies": 700_000},
        "public_hubs": {"publicHubs": [{"hubUrl": HUB, "shortLabel": "Literal hub", "extra": [0, None]}]},
        "hub_genomes": {"hubUrl": HUB, "genomes": {"callerAssembly": {
            "twoBitPath": "https://example.org/native.2bit", "defaultPos": "chr1:1-10", "extra": []}}},
        "tracks": {"hg38": {"container": {"compositeContainer": "TRUE", "genes": {
            "type": "genePred", "parent": "container", "extra": {"nested": True}}}}},
        "chromosomes": {"genome": "hg38", "chromCount": 2, "chromosomes": {"chr1": 1000, "chrM": 20}},
        "schema": {"genome": "hg38", "track": "genes", "type": "genePred", "itemCount": 500,
            "columnTypes": [{"name": "txStart", "sqlType": "int", "jsonType": "number", "description": "start"},
                {"name": "unknown", "sqlType": "longblob", "jsonType": "string", "description": None}]},
        "track": {"genome": "hg38", "track": "genes", "chrom": "chr1", "start": 10, "end": 20,
            "trackType": "genePred", "sqlTable": "all_genes", "itemsReturned": 1,
            "genes": [{"chrom": "chr1", "txStart": 5, "txEnd": 22, "strand": "-", "score": 0,
                "exonStarts": "5,18,", "exonEnds": "12,22,", "unknown": [False, None]}]},
        "sequence": {"genome": "hg38", "chrom": "chr1", "start": 10, "end": 14,
            "dna": "AcgN", "unknown": {"native": [None, False, 0]}},
    }[operation])


def snapshot(selected, payload=None, *, raw=None, status=200, **transport_changes):
    if raw is None:
        raw = json.dumps(native(selected["operation"]) if payload is None else payload,
            ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    spec = ucsc_request_spec(selected)
    address = spec["url"] + ("?" + urlencode(spec["params"]) if spec["params"] else "")
    transport = {"status": status, "headers": {"content-type": "application/json"},
        "request": {"method": "GET", "url": address, "headers": {"Accept": "application/json"}},
        "effective_url": address, "request_policy": {"timeout_seconds": 30, "automatic_redirects": False},
        "body_complete": True, "retained_body_bytes": len(raw), "observed_body_bytes": len(raw),
        "declared_body_bytes": len(raw), "response_byte_limit": selected["max_bytes"], **transport_changes}
    return SourceSnapshot("ucsc", spec["url"], deepcopy(selected), "2026-10-31T00:00:00+00:00",
        raw, "application/json", transport)


def result(selected, payload=None, *, raw=None, **transport_changes):
    retained = snapshot(selected, payload, raw=raw, **transport_changes)
    return ucsc_result(retained, arguments=selected, source_ref=SOURCE,
        artifact_ref="artifact_" + hashlib.sha256(retained.content).hexdigest())


def codes(value):
    return {row["code"] for row in value["issues"]}


def pointer(value, path):
    for token in path.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


@pytest.mark.parametrize("case,path,params", CASES, ids=OPERATIONS)
def test_each_tagged_request_has_one_fixed_native_path(case, path, params):
    selected = {**deepcopy(case), "max_bytes": 1234}
    before = deepcopy(selected)
    assert validate_ucsc_arguments(selected) == selected
    spec = ucsc_request_spec(selected)
    assert spec == {"service": "ucsc", "url": ORIGIN + path, "params": params,
        "media_type": "application/json", "max_bytes": 1234, "follow_redirects": False}
    assert selected == before


def test_native_flags_and_resource_urls_are_literal_encoded_operands():
    selected = arguments("track", hub_url=HUB, json_output_arrays=True)
    spec = ucsc_request_spec(selected)
    assert spec["params"]["hubUrl"] == HUB and spec["params"]["jsonOutputArrays"] == 1
    retained = snapshot(selected)
    address = retained.transport["request"]["url"]
    assert address.startswith(ORIGIN + "/getData/track?")
    assert "hubUrl=https%3A%2F%2Fexample.org%2Fselected%2Fhub.txt%3Fliteral%3Done%26other%3Dtwo" in address
    assert "trackLeavesOnly" not in address and "revComp" not in address
    assert ucsc_request_spec(arguments("tracks", track_leaves_only=True))["params"]["trackLeavesOnly"] == 1
    assert ucsc_request_spec(arguments("sequence", rev_comp=True))["params"]["revComp"] == 1
    assert ucsc_request_spec(arguments("genark_genomes", genome="GCA_001698545.1"))["params"]["genome"] == "GCA_001698545.1"


@pytest.mark.parametrize("operation,changes", [
    ("ucsc_genomes", {"max_bytes": True}), ("ucsc_genomes", {"max_bytes": 0}),
    ("ucsc_genomes", {"max_bytes": MAX_RESPONSE_BYTES + 1}),
    ("ucsc_genomes", {"endpoint": "https://example.org/data"}),
    ("ucsc_genomes", {"prompt": "Choose an endpoint"}), ("ucsc_genomes", {"genome": "hg38"}),
    ("track", {"max_items_output": True}), ("track", {"max_items_output": -1}),
    ("track", {"max_items_output": MAX_ITEMS_OUTPUT + 1}), ("track", {"start": False}),
    ("track", {"start": -1}), ("track", {"start": 10.0}), ("track", {"end": 10}),
    ("track", {"end": 9}), ("track", {"track": "genes,other"}), ("track", {"genome": " hg38"}),
    ("track", {"chrom": "chr1\n"}), ("hub_genomes", {"hub_url": "file:///tmp/hub.txt"}),
    ("hub_genomes", {"hub_url": "https://user:password@example.org/hub.txt"}),
    ("hub_genomes", {"hub_url": "https://example.org/hub.txt#fragment"}),
    ("hub_genomes", {"hub_url": "https://example.org/hub name.txt"}),
    ("sequence", {"json_output_arrays": True}), ("sequence", {"max_items_output": 1}),
    ("tracks", {"start": 0, "end": 1}), ("genark_genomes", {"operation": "unregistered"}),
])
def test_closed_arguments_reject_unselected_endpoints_and_invalid_scalar_types(operation, changes):
    with pytest.raises(ValueError):
        validate_ucsc_arguments(arguments(operation, **changes))


@pytest.mark.parametrize("operation", OPERATIONS)
def test_full_native_unknown_fields_and_associations_are_retained(operation):
    selected, payload = arguments(operation), native(operation)
    retained = snapshot(selected, payload)
    before = deepcopy((selected, payload, retained))
    value = ucsc_result(retained, arguments=selected, source_ref=SOURCE,
        artifact_ref="artifact_" + hashlib.sha256(retained.content).hexdigest())
    assert value["operation"] == TOOL and value["service"] == "ucsc"
    assert value["native_json"] == payload and value["native_document"] is None
    assert value["parse_state"] == "json" and value["decode_error"] is None
    assert value["representation_state"] == "complete" and value["native_response_state"] == "data"
    assert value["population_coverage"] == "selected_response_only" and value["issues"] == []
    assert value["source_ref"] == SOURCE and value["requested"] == selected
    assert value["response"]["body_complete"] is True
    assert value["response"]["retained_bytes"] == len(retained.content)
    assert validate_ucsc_result(value) == value
    assert (selected, payload, retained) == before


@pytest.mark.parametrize("damage", ["selected", "selected_boolean", "service", "url", "media_type", "effective", "method",
    "transport_url", "body", "redirects", "timeout_boolean", "timeout_zero", "timeout_huge", "artifact", "source"])
def test_constructor_binds_actual_selected_request_transport_policy_and_original_bytes(damage):
    selected = arguments("sequence")
    retained = snapshot(selected)
    artifact = "artifact_" + hashlib.sha256(retained.content).hexdigest()
    source = SOURCE
    if damage.startswith("selected"):
        retained = replace(retained, request={**selected, "start": True if damage == "selected_boolean" else 11})
    elif damage == "service":
        retained = replace(retained, service="other")
    elif damage == "url":
        retained = replace(retained, url="https://example.org/getData/sequence")
    elif damage == "media_type":
        retained = replace(retained, media_type="text/plain")
    elif damage == "effective":
        retained.transport["effective_url"] = "https://example.org/data"
    elif damage == "method":
        retained.transport["request"]["method"] = "POST"
    elif damage == "transport_url":
        retained.transport["request"]["url"] += "&unselected=1"
    elif damage == "body":
        retained.transport["request"]["body_base64"] = "e30="
    elif damage == "redirects":
        retained.transport["request_policy"]["automatic_redirects"] = True
    elif damage.startswith("timeout"):
        retained.transport["request_policy"]["timeout_seconds"] = {
            "timeout_boolean": True, "timeout_zero": 0, "timeout_huge": 10 ** 500}[damage]
    elif damage == "artifact":
        artifact = "artifact_" + "0" * 64
    else:
        source = "artifact_" + "a" * 64
    with pytest.raises(ValueError):
        ucsc_result(retained, arguments=selected, source_ref=source, artifact_ref=artifact)


def test_constructor_rejects_actual_body_beyond_selected_engineering_byte_limit():
    selected = arguments("ucsc_genomes", max_bytes=4)
    with pytest.raises(ValueError, match="byte_limit_conflict"):
        result(selected, raw=b'{"ucscGenomes":{}}')


def test_duplicate_object_members_have_no_covert_first_or_last_winner():
    raw = (b'{"genome":"hg38","track":"genes","chrom":"chr1","start":10,"end":20,'
        b'"sqlTable":"all_genes","sqlTable":"different_table",'
        b'"genes":[{"score":0,"score":1}],"itemsReturned":1}')
    value = result(arguments("track"), raw=raw)
    assert value["parse_state"] == "json_document" and value["native_json"] is None
    members = value["native_document"]["members"]
    assert [row["value"]["value"] for row in members if row["name"] == "sqlTable"] == ["all_genes", "different_table"]
    row = next(row["value"] for row in members if row["name"] == "genes")["items"][0]
    assert [member["value"]["token"] for member in row["members"]] == ["0", "1"]
    located = [pointer(value, row["pointer"]) for row in value["issues"] if row["code"] == "native_duplicate_member"]
    assert [row["name"] for row in located] == ["sqlTable", "score"]
    assert value["representation_state"] == "complete"
    assert validate_ucsc_result(value) == value


def test_duplicate_critical_identity_and_count_fields_remain_ambiguous():
    raw = (b'{"genome":"hg38","genome":"mm39","chrom":"chr1","start":10,"end":14,'
        b'"dna":"AcgN","itemsReturned":0,"itemsReturned":1}')
    value = result(arguments("sequence"), raw=raw)
    assert value["reported_identity"]["genome"]["state"] == "ambiguous"
    assert value["reported_identity"]["genome"]["value"] is None
    assert value["native_counts"]["itemsReturned"]["state"] == "ambiguous"
    assert value["native_counts"]["itemsReturned"]["value"] is None
    assert {"native_identity_ambiguous", "native_count_invalid"} <= codes(value)
    assert ucsc_sequence_interval(value) is None


@pytest.mark.parametrize("token", ["1e-9999", "-1e-9999", "1e9999", "-0", "9007199254740993",
    "0.10000000000000001", "1E+2", "9" * 5000])
def test_original_number_tokens_survive_underflow_overflow_precision_and_lexical_loss(token):
    raw = ('{"ucscGenomes":{},"unknown_number":' + token + '}').encode()
    value = result(arguments("ucsc_genomes"), raw=raw)
    assert value["parse_state"] == "json_document" and value["native_json"] is None
    number = value["native_document"]["members"][1]["value"]
    assert number == {"kind": "number", "token": token}
    located = next(row for row in value["issues"] if row["code"] == "native_number_token_required")
    assert pointer(value, located["pointer"]) == number
    assert value["representation_state"] == "complete" and validate_ucsc_result(value) == value


def test_representable_native_json_keeps_false_null_zero_and_signed_float_zero_distinct():
    raw = b'{"ucscGenomes":{},"false":false,"missing":null,"zero":0,"negative_zero":-0.0,"number":0.125}'
    value = result(arguments("ucsc_genomes"), raw=raw)
    assert value["parse_state"] == "json" and value["native_document"] is None
    data = value["native_json"]
    assert data["false"] is False and data["missing"] is None
    assert type(data["zero"]) is int and data["zero"] == 0
    assert type(data["negative_zero"]) is float and math.copysign(1, data["negative_zero"]) == -1
    assert data["number"] == 0.125


@pytest.mark.parametrize("raw,error", [(b'\xff', "invalid_native_utf8"), (b'{', "invalid_native_json"),
    (b'{"ucscGenomes":{},"n":NaN}', "invalid_native_json"),
    (b'{"ucscGenomes":{},"n":Infinity}', "invalid_native_json"),
    (b'{"ucscGenomes":{},"text":"\\ud800"}', "invalid_native_unicode")])
def test_failed_decoding_keeps_complete_raw_identity_and_capture_metadata(raw, error):
    value = result(arguments("ucsc_genomes"), raw=raw)
    assert value["parse_state"] == "decode_failed" and value["decode_error"] == error
    assert value["native_json"] is None and value["native_document"] is None
    assert value["raw_artifact_ref"] == "artifact_" + hashlib.sha256(raw).hexdigest()
    assert value["response"]["body_complete"] is True and value["response"]["retained_bytes"] == len(raw)
    assert value["native_response_state"] == "unavailable" and value["representation_state"] == "invalid"


def test_wrong_json_root_is_retained_and_is_not_a_successful_empty_response():
    value = result(arguments("ucsc_genomes"), payload=[])
    assert value["native_json"] == [] and value["parse_state"] == "json"
    assert value["representation_state"] == "invalid" and "json_root_not_object" in codes(value)


def test_missing_native_count_and_reported_zero_are_separate_from_capture_completeness():
    payload = native("track")
    payload["genes"] = []
    del payload["itemsReturned"]
    absent = result(arguments("track"), payload)
    assert absent["native_counts"]["itemsReturned"] == {"state": "missing", "value": None,
        "number_token": None, "pointer": None, "meaning": "returned_items"}
    assert absent["native_item_cap"]["state"] == "not_reported"
    assert absent["response"]["body_complete"] is True and absent["issues"] == []
    payload["itemsReturned"] = 0
    zero = result(arguments("track"), payload)
    assert zero["native_counts"]["itemsReturned"]["state"] == "present"
    assert zero["native_counts"]["itemsReturned"]["value"] == 0
    assert zero["native_counts"]["itemsReturned"]["number_token"] == "0"
    assert zero["population_coverage"] == "selected_response_only"


@pytest.mark.parametrize("operation,status", [("track", 206), ("genark_genomes", 200)])
def test_native_item_cap_is_separate_from_http_and_matching_population(operation, status):
    payload = native(operation)
    payload["maxItemsLimit"] = True
    payload["dataDownloadUrl"] = "http://example.org/unselected/full-data.gz"
    value = result(arguments(operation), payload, status=status)
    assert value["response"]["http_status"] == status and value["response"]["body_complete"] is True
    assert value["native_item_cap"]["state"] == "reached" and "native_item_cap_reached" in codes(value)
    assert "http_not_success" not in codes(value) and value["representation_state"] == "complete"
    assert value["native_json"]["dataDownloadUrl"] == payload["dataDownloadUrl"]
    assert value["population_coverage"] == "selected_response_only"
    if operation == "genark_genomes":
        assert value["native_counts"]["totalAssemblies"]["meaning"] == "genark_registry_assemblies"
        assert value["native_counts"]["itemsReturned"]["value"] == 1
        assert "native_count_conflict" not in codes(value)


def test_registry_and_whole_track_counts_are_never_interval_denominators():
    registry = result(arguments("genark_genomes", genome="GCF_000001405.40"))
    assert registry["native_counts"]["totalAssemblies"]["value"] == 700_000
    for native_type, meaning in [("bigWig", "bigwig_valid_covered_bases"), ("bigBed 6", "whole_track_records"),
            ("genePred", "whole_track_records"), ("newNativeType", "native_count_unspecified")]:
        payload = {**native("schema"), "type": native_type}
        value = result(arguments("schema"), payload)
        assert value["native_counts"]["itemCount"]["meaning"] == meaning
        assert value["native_counts"]["itemCount"]["value"] == 500
        assert value["population_coverage"] == "selected_response_only"


@pytest.mark.parametrize("qualification", ["splitTable", "protectedData"])
def test_explicit_unavailable_count_context_does_not_turn_native_zero_into_a_measured_total(qualification):
    payload = {**native("schema"), qualification: True, "itemCount": 0}
    value = result(arguments("schema"), payload)
    assert value["native_json"] == payload
    assert value["native_counts"]["itemCount"]["value"] == 0
    assert value["native_counts"]["itemCount"]["meaning"] == "native_count_unspecified"
    assert "native_count_scope_qualified" in codes(value)


@pytest.mark.parametrize("reported", [True, "1", 1.0, None, -1])
def test_invalid_native_counts_are_retained_without_coercion_or_zero_fill(reported):
    payload = {**native("track"), "itemsReturned": reported}
    value = result(arguments("track"), payload)
    assert type(value["native_json"]["itemsReturned"]) is type(reported)
    assert value["native_json"]["itemsReturned"] == reported
    assert value["native_counts"]["itemsReturned"]["value"] is None
    assert "native_count_invalid" in codes(value)


def test_count_conflicts_and_native_counts_beyond_the_selected_cap_are_qualified():
    value = result(arguments("track"), {**native("track"), "itemsReturned": 4})
    assert {"native_count_conflict", "native_count_exceeds_requested_cap"} <= codes(value)
    assert value["native_json"]["itemsReturned"] == 4 and len(value["native_json"]["genes"]) == 1
    missing_cap = result(arguments("track"), status=206)
    assert missing_cap["native_item_cap"]["state"] == "not_reported"
    assert "native_item_cap_signal_missing" in codes(missing_cap)


@pytest.mark.parametrize("field", ["genome", "track", "chrom", "start", "end"])
def test_track_interval_context_is_required_without_discarding_native_rows(field):
    payload = native("track")
    del payload[field]
    value = result(arguments("track"), payload)
    assert value["native_json"] == payload
    # The exact native data member supplies the track identity when no separate
    # root track field is emitted, as the native hub operation does.
    if field == "track":
        assert value["reported_identity"]["track"]["basis"] == "object_member_name"
        assert value["issues"] == []
    else:
        assert value["representation_state"] == "partial" and value["issues"]


def test_track_rows_and_native_column_positions_are_not_clipped_or_relabelled():
    ordinary = result(arguments("track"))
    assert ordinary["native_json"]["genes"][0]["txStart"] == 5
    assert ordinary["native_json"]["genes"][0]["txEnd"] == 22
    selected = arguments("track", json_output_arrays=True)
    payload = {**native("track"), "genes": [["chr1", 5, 22, 0, None]],
        "columnTypes": {"genes": [{"name": name, "sqlType": "nativeType", "jsonType": kind, "native_extra": None}
            for name, kind in (("chrom", "string"), ("txStart", "number"), ("txEnd", "number"),
                ("score", "number"), ("unknown", "string"))]}}
    arrays = result(selected, payload)
    assert arrays["native_json"] == payload and arrays["issues"] == []
    payload["genes"][0][3] = False
    mismatch = result(selected, payload)
    located = next(row for row in mismatch["issues"] if row["code"] == "native_column_type_conflict")
    assert pointer(mismatch, located["pointer"]) is False
    payload["genes"] = [["chr1"]]
    short = result(selected, payload)
    located = next(row for row in short["issues"] if row["code"] == "native_column_arity_conflict")
    assert pointer(short, located["pointer"]) == ["chr1"]
    del payload["columnTypes"]
    assert "native_column_context_missing" in codes(result(selected, payload))


def test_invalid_native_column_context_is_retained_without_inventing_field_names():
    payload = {**native("schema"), "columnTypes": [{"name": None, "jsonType": False}]}
    value = result(arguments("schema"), payload)
    assert value["native_json"] == payload and "native_column_context_invalid" in codes(value)
    for issue in value["issues"]:
        if issue["code"] == "native_column_context_invalid":
            pointer(value, issue["pointer"])


@pytest.mark.parametrize("reverse", [False, True])
def test_only_exact_returned_sequence_intervals_support_the_existing_reference_importer(reverse):
    selected, payload = arguments("sequence", rev_comp=reverse), native("sequence")
    if reverse:
        payload["revComp"] = True
        payload["dna"] = "NcGt"
    value = result(selected, payload)
    interval = ucsc_sequence_interval(value)
    assert interval == {"genome": "hg38", "hub_url": None, "chrom": "chr1", "start": 10, "end": 14,
        "rev_comp": reverse, "dna": payload["dna"], "length": 4, "dna_pointer": "/native_json/dna",
        "source_ref": SOURCE, "raw_artifact_ref": value["raw_artifact_ref"]}
    assert pointer(value, interval["dna_pointer"]) == payload["dna"]
    assert value["native_orientation"]["reported"]["state"] == ("present" if reverse else "missing")
    assert "scope" not in interval and "mapping" not in interval


def test_noncritical_duplicate_metadata_keeps_the_exact_sequence_cell_available():
    raw = b'{"genome":"hg38","chrom":"chr1","start":10,"end":14,"dna":"AcgN","extra":0,"extra":1e-9999}'
    value = result(arguments("sequence"), raw=raw)
    interval = ucsc_sequence_interval(value)
    assert interval["dna"] == "AcgN" and pointer(value, interval["dna_pointer"]) == "AcgN"
    assert value["parse_state"] == "json_document" and value["representation_state"] == "complete"


def test_first_base_is_the_exact_zero_based_half_open_interval_without_a_coordinate_shift():
    selected = arguments("sequence", start=0, end=1)
    payload = {"genome": "hg38", "chrom": "chr1", "start": 0, "end": 1, "dna": "n"}
    value = result(selected, payload)
    assert ucsc_request_spec(selected)["params"]["start"] == 0
    interval = ucsc_sequence_interval(value)
    assert (interval["start"], interval["end"], interval["length"], interval["dna"]) == (0, 1, 1, "n")


@pytest.mark.parametrize("changes", [{"genome": "mm39"}, {"chrom": "chr2"}, {"start": 11}, {"end": 15},
    {"dna": "ACG"}, {"dna": None}, {"dna": "A-CG"}, {"revComp": True}, {"revComp": None}])
def test_unselected_identity_geometry_orientation_and_sequence_qualifications_are_not_silently_accepted(changes):
    payload = {**native("sequence"), **changes}
    value = result(arguments("sequence"), payload)
    assert value["native_json"] == payload and value["issues"]
    assert ucsc_sequence_interval(value) is None


def test_required_native_orientation_bounds_and_hub_association_remain_explicit():
    assert ucsc_sequence_interval(result(arguments("sequence", rev_comp=True))) is None
    payload = native("sequence")
    del payload["start"]
    assert ucsc_sequence_interval(result(arguments("sequence"), payload)) is None
    selected = arguments("sequence", hub_url=HUB)
    assert ucsc_sequence_interval(result(selected)) is None
    payload = {**native("sequence"), "hubUrl": HUB}
    value = result(selected, payload)
    assert ucsc_sequence_interval(value)["hub_url"] == HUB
    assert value["reported_identity"]["hub_url"]["value"] == HUB


@pytest.mark.parametrize("status", [301, 400, 403, 404, 415, 429, 500])
def test_complete_native_error_bodies_and_http_status_are_retained_separately(status):
    payload = {"error": "Original provider diagnostic", "statusCode": status,
        "statusMessage": "Native status wording", "unknown": {"complete": [False, 0, None]}}
    value = result(arguments("sequence"), payload, status=status,
        headers={"content-type": "application/json", "retry-after": "30"})
    assert value["native_json"] == payload and value["native_response_state"] == "error"
    assert value["representation_state"] == "complete" and value["response"]["body_complete"] is True
    assert value["response"]["retry_after"] == "30" and {"http_not_success", "native_error_response"} <= codes(value)
    assert ucsc_sequence_interval(value) is None
    if status == 301:
        assert "http_redirect" in codes(value)


def test_native_error_under_http_success_is_not_a_successful_data_response():
    payload = {"error": "Native denial", "statusCode": 403, "statusMessage": "Forbidden"}
    value = result(arguments("sequence"), payload)
    assert value["native_response_state"] == "error"
    assert {"native_error_response", "native_status_conflict"} <= codes(value)
    assert value["response"]["http_status"] == 200 and value["native_json"]["statusCode"] == 403


def test_a_literal_track_named_error_is_data_rather_than_an_error_envelope():
    payload = native("track")
    payload["error"] = payload.pop("genes")
    payload["track"] = "error"
    value = result(arguments("track", track="error"), payload)
    assert value["native_response_state"] == "data" and value["native_json"] == payload
    assert "native_error_response" not in codes(value) and value["issues"] == []


def test_parse_and_byte_capture_states_do_not_substitute_for_each_other():
    selected = arguments("sequence")
    retained = snapshot(selected)
    incomplete = result(selected, body_complete=False, body_capture_failure="provider_body_capture_failed")
    assert incomplete["parse_state"] == "json" and incomplete["native_json"] == native("sequence")
    assert {"response_incomplete", "response_capture_failure"} <= codes(incomplete)
    assert ucsc_sequence_interval(incomplete) is None
    conflict = result(selected, retained_body_bytes=0, observed_body_bytes=len(retained.content) - 1)
    assert "transport_count_conflict" in codes(conflict)
    assert conflict["response"]["retained_bytes"] == len(retained.content)
    assert ucsc_sequence_interval(conflict) is None
    limited = result(selected, observed_body_bytes=selected["max_bytes"] + 1,
        body_complete=False, body_capture_failure="provider_response_byte_limit")
    assert "response_byte_limit_exceeded" in codes(limited)


@pytest.mark.parametrize("damage", ["top_field", "source_namespace", "file_namespace", "identity", "count_boolean",
    "count_token", "qualification", "collapse_document", "number_token"])
def test_closed_dto_and_derived_native_qualifications_reject_tampering(damage):
    value = result(arguments("track"))
    if damage == "top_field":
        value["unregistered"] = True
    elif damage == "source_namespace":
        value["source_ref"] = "artifact_" + "a" * 64
    elif damage == "file_namespace":
        value["raw_artifact_ref"] = SOURCE
    elif damage == "identity":
        value["reported_identity"]["genome"]["value"] = "mm39"
    elif damage == "count_boolean":
        value["native_counts"]["itemsReturned"]["value"] = True
    elif damage == "count_token":
        value["native_counts"]["itemsReturned"]["number_token"] = "2"
    elif damage == "qualification":
        value["population_coverage"] = "matching_population_complete"
    else:
        value = result(arguments("ucsc_genomes"), raw=b'{"ucscGenomes":{},"x":0,"x":1e-9999}')
        if damage == "collapse_document":
            value["native_document"]["members"] = value["native_document"]["members"][:2]
        else:
            value["native_document"]["members"][2]["value"]["token"] = "NaN"
    with pytest.raises(ValueError):
        validate_ucsc_result(value)


def test_schema_declarations_are_detached_and_preserve_closed_reference_namespaces():
    Draft202012Validator.check_schema(ARGUMENTS_SCHEMA)
    schema = ucsc_result_schema()
    Draft202012Validator.check_schema(schema)
    assert schema["properties"]["source_ref"]["x-reference-namespace"] == "source"
    assert schema["properties"]["raw_artifact_ref"]["x-reference-namespace"] == "artifact"
    schema["properties"]["source_ref"] = {"type": "number"}
    assert ucsc_result_schema()["properties"]["source_ref"]["type"] == "string"
    assert ucsc_sequence_interval(result(arguments("ucsc_genomes"))) is None


@pytest.mark.parametrize("pair_type", [tuple, list], ids=["runtime_tuple", "retained_json_array"])
def test_actual_transport_header_pairs_preserve_order_without_mutating_original_metadata(pair_type):
    selected = arguments("sequence")
    retained = snapshot(selected)
    retained.transport["header_items"] = [pair_type(row) for row in (
        ("Content-Type", "application/json"), ("X-Native", "first"), ("X-Native", "second"))]
    original = deepcopy(retained.transport)
    value = ucsc_result(retained, arguments=selected, source_ref=SOURCE,
        artifact_ref="artifact_" + hashlib.sha256(retained.content).hexdigest())
    assert value["representation_state"] == "complete" and value["issues"] == []
    assert ucsc_sequence_interval(value)["dna"] == "AcgN"
    assert retained.transport == original
    assert all(type(row) is pair_type for row in retained.transport["header_items"])
    assert [row[1] for row in retained.transport["header_items"][1:]] == ["first", "second"]
