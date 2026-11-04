"""Pure acquisition contracts; no transport or scientific worker is invoked."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.molecular_provider_acquisition import (
    MAX_RESPONSE_BYTES, OPERATIONS, PROVIDER_ARGUMENTS_SCHEMAS,
    provider_request_spec, provider_result, provider_result_schema,
    validate_provider_arguments, validate_provider_result,
)


SOURCE = "source_" + "a" * 24
IDS = ["9606.ENSP00000269305", "9606.ENSP00000266970"]
HPA_RAW = (Path(__file__).parent / "fixtures/hpa/ENSG00000141510.json").read_bytes()
assert len(HPA_RAW) == 9225 and hashlib.sha256(HPA_RAW).hexdigest() == "ab75a8987ac2754757cd4f11406b535a1e33c8cae6823c387b9eb63310842146"
ARGUMENTS = {
    "public.string.network": {"string_ids": IDS, "taxon_id": 9606,
        "required_score": 400, "max_bytes": 10000},
    "public.kegg.reaction": {"reaction_id": "R00259", "max_bytes": 10000},
    "public.reactome.record": {"stable_id": "R-HSA-141409", "max_bytes": 10000},
    "public.quickgo.term": {"term_id": "GO:0000001", "max_bytes": 10000},
    "public.pubchem.compound": {"cid": 2244, "max_bytes": 10000},
    "public.hpa.gene": {"gene_id": "ENSG00000141510", "max_bytes": 16384},
}
NATIVE = {
    "public.string.network": [{"stringId_A": IDS[0], "stringId_B": IDS[1],
        "ncbiTaxonId": 9606, "score": 0, "escore": None, "unknown": {"empty": [], "false": False}}],
    "public.reactome.record": {"stId": "R-HSA-141409", "dbId": 141409,
        "species": [{"taxId": "9606"}], "input": [{"stId": "R-HSA-141433", "stoichiometry": None}],
        "output": [{"dbId": 141441}], "isInferred": False, "unknown": {"zero": 0, "empty": ""}},
    "public.quickgo.term": {"numberOfHits": 1, "pageInfo": {"current": 1, "total": 1},
        "results": [{"id": "GO:0000001", "isObsolete": False, "synonyms": [],
            "definition": {"text": "literal definition", "xrefs": ["GO_REF:0000001"]},
            "children": [{"id": "GO:0000002", "relation": "is_a"}], "unknown": None}]},
    "public.pubchem.compound": {"PC_Compounds": [
        {"id": {"id": {"cid": 2244}}, "props": [{"urn": {"label": "literal label"},
            "value": {"sval": "caller-selected compound"}}],
            "unknown": {"zero": 0, "null": None, "false": False, "empty": []}},
        {"id": {"id": {"cid": 2244}}, "unknown": {"occurrence": "second"}}],
        "unknown_envelope": {"native": "retained"}},
    "public.hpa.gene": json.loads(HPA_RAW),
}
KEGG_TEXT = (
    "ENTRY       R00259                      Reaction\r\n"
    "NAME        first name;\r\n"
    "            second name\r\n"
    "EQUATION    C00024 + C00025 <=> C00010 + C00624\r\n"
    "ORTHOLOGY   K00618  supplied relationship\r\n"
    "UNKNOWN     0; null; not a parsed measurement\r\n"
    "NAME        repeated name field\r\n"
    "///\r\n"
)


def snapshot(operation, *, raw=None, arguments=None, status=200, caller="configured_app"):
    arguments = deepcopy(ARGUMENTS[operation] if arguments is None else arguments)
    spec = provider_request_spec(operation, arguments, string_caller_identity=caller)
    if raw is None:
        if operation == "public.hpa.gene":
            raw = HPA_RAW
        else:
            raw = KEGG_TEXT.encode() if operation == "public.kegg.reaction" else json.dumps(NATIVE[operation]).encode()
    address = spec["url"] + ("?" + urlencode(spec["params"], doseq=True) if spec["params"] else "")
    transport = {"status": status, "headers": {"content-type": spec["media_type"]},
        "request": {"method": "GET", "url": address},
        "request_policy": {"timeout_seconds": 90, "automatic_redirects": False},
        "body_complete": True, "retained_body_bytes": len(raw),
        "observed_body_bytes": len(raw), "declared_body_bytes": len(raw),
        "response_byte_limit": arguments["max_bytes"]}
    return SourceSnapshot(spec["service"], spec["url"], arguments, "2026-10-31T00:00:00Z",
        raw, spec["media_type"], transport)


def result(capture, operation):
    return provider_result(operation, capture, source_ref=SOURCE,
        artifact_ref="artifact_" + hashlib.sha256(capture.content).hexdigest())


def codes(value):
    return {issue["code"] for issue in value["issues"]}


@pytest.mark.parametrize("operation", OPERATIONS)
def test_exact_fixed_request_and_owned_schema(operation):
    original = deepcopy(ARGUMENTS[operation])
    spec = provider_request_spec(operation, original, string_caller_identity="configured_app")
    assert spec["service"] == operation.split(".")[1]
    assert spec["max_bytes"] == original["max_bytes"] and spec["follow_redirects"] is False
    assert original == ARGUMENTS[operation]
    assert validate_provider_arguments(operation, original) == original
    assert Draft202012Validator(PROVIDER_ARGUMENTS_SCHEMAS[operation]).is_valid(original)
    expected = {
        "public.string.network": "https://version-12-5.string-db.org/api/json/network",
        "public.kegg.reaction": "https://rest.kegg.jp/get/rn:R00259",
        "public.reactome.record": "https://reactome.org/ContentService/data/query/R-HSA-141409",
        "public.quickgo.term": "https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/GO%3A0000001",
        "public.pubchem.compound": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2244/JSON",
        "public.hpa.gene": "https://www.proteinatlas.org/ENSG00000141510.json",
    }
    assert spec["url"] == expected[operation]
    if operation == "public.string.network":
        assert spec["params"] == {"identifiers": "\r".join(IDS), "species": 9606,
            "required_score": 400, "network_type": "functional", "add_nodes": 0,
            "caller_identity": "configured_app"}
    else:
        assert spec["params"] == {}
    assert spec["media_type"] == ("text/plain" if operation == "public.kegg.reaction" else "application/json")


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("limit", [True, False, 0, -1, 1.0, "100", None, MAX_RESPONSE_BYTES + 1])
def test_mandatory_strict_byte_limit(operation, limit):
    arguments = {**ARGUMENTS[operation], "max_bytes": limit}
    with pytest.raises(ValueError):
        validate_provider_arguments(operation, arguments)
    arguments.pop("max_bytes")
    with pytest.raises(ValueError):
        validate_provider_arguments(operation, arguments)


@pytest.mark.parametrize("field,value", [("taxon_id", True), ("taxon_id", 9606.0),
    ("taxon_id", 10090), ("required_score", False), ("required_score", 400.0),
    ("required_score", -1), ("required_score", 1001), ("string_ids", [IDS[0]]),
    ("string_ids", [IDS[0], IDS[0]]), ("string_ids", [IDS[0], "TP53"]),
    ("string_ids", [IDS[0], IDS[1] + "\n"])])
def test_string_scope_cannot_silently_map_or_change_species(field, value):
    with pytest.raises(ValueError):
        validate_provider_arguments("public.string.network", {**ARGUMENTS["public.string.network"], field: value})


@pytest.mark.parametrize("operation,key,value", [
    ("public.kegg.reaction", "reaction_id", "rn:R00259"),
    ("public.kegg.reaction", "reaction_id", "R00259\n"),
    ("public.kegg.reaction", "reaction_id", "R00259+R00001"),
    ("public.reactome.record", "stable_id", "data/query/R-HSA-141409"),
    ("public.reactome.record", "stable_id", "R-HSA-141409.1"),
    ("public.quickgo.term", "term_id", "GO:0000001,GO:0000002"),
    ("public.quickgo.term", "term_id", "ECO:0000269"),
])
def test_literal_identifier_scope(operation, key, value):
    with pytest.raises(ValueError):
        provider_request_spec(operation, {**ARGUMENTS[operation], key: value})


@pytest.mark.parametrize("caller", [None, "", True, " app", "app ", "app\nother"])
def test_string_requires_configured_transport_identity(caller):
    with pytest.raises(ValueError):
        provider_request_spec("public.string.network", ARGUMENTS["public.string.network"],
            string_caller_identity=caller)


@pytest.mark.parametrize("operation", OPERATIONS)
def test_arguments_are_closed_and_have_no_arbitrary_url(operation):
    for extra in ("url", "endpoint", "species", "page", "caller_identity"):
        with pytest.raises(ValueError):
            validate_provider_arguments(operation, {**ARGUMENTS[operation], extra: "selected_elsewhere"})
    with pytest.raises(ValueError):
        validate_provider_arguments(operation, tuple(ARGUMENTS[operation].items()))
    with pytest.raises(ValueError):
        validate_provider_arguments("public.arbitrary.get", ARGUMENTS[operation])


@pytest.mark.parametrize("operation", OPERATIONS)
def test_full_native_and_independent_completeness_scopes(operation):
    capture = snapshot(operation)
    before = deepcopy(capture)
    value = result(capture, operation)
    assert capture == before
    assert value["source_ref"] == SOURCE
    assert value["raw_artifact_ref"] == "artifact_" + hashlib.sha256(capture.content).hexdigest()
    assert value["requested"] == ARGUMENTS[operation]
    assert value["response"]["body_complete"] is True
    assert value["response"]["observed_body_bytes"] == len(capture.content)
    assert value["representation_state"] == "complete"
    assert value["population_coverage"] == "selected_response_only"
    assert value["issues"] == []
    assert validate_provider_result(value) == value
    assert Draft202012Validator(provider_result_schema()).is_valid(value)
    if operation == "public.kegg.reaction":
        assert value["native_json"] is None and value["native_text"] == KEGG_TEXT
        assert [block["field"] for block in value["native_fields"]] == [
            "ENTRY", "NAME", "EQUATION", "ORTHOLOGY", "UNKNOWN", "NAME", "///"]
        name = value["native_fields"][1]
        assert [line["line_number"] for line in name["lines"]] == [2, 3]
        assert name["lines"][1]["text"] == "            second name\r\n"
    else:
        assert value["native_json"] == NATIVE[operation]
        assert value["native_text"] is None and value["native_fields"] == []


def test_caller_identity_is_preserved_from_actual_transport_without_model_argument():
    operation = "public.string.network"
    capture = snapshot(operation, caller="configured caf\u00e9")
    value = result(capture, operation)
    assert "caller_identity" not in value["requested"]
    assert "caller_identity=configured+caf%C3%A9" in value["response"]["request_url"]
    assert validate_provider_result(value) == value


@pytest.mark.parametrize("raw", [b"null", b"0", b"false", b'""', b"[]"])
def test_json_null_zero_empty_and_wrong_root_are_retained(raw):
    operation = "public.reactome.record"
    value = result(snapshot(operation, raw=raw), operation)
    assert value["parse_state"] == "json" and value["decode_error"] is None
    assert value["native_json"] == json.loads(raw)
    assert value["representation_state"] == "invalid"
    assert codes(value) == {"json_root_not_object"}


@pytest.mark.parametrize("raw,error", [(b"\xff", "invalid_native_utf8"),
    (b'{"stId":', "invalid_native_json"), (b'{"x":1,"x":2}', "invalid_native_json"),
    (b'{"stId":"R-HSA-141409","x":NaN}', "invalid_native_json"),
    (b'{"x":1e999}', "invalid_native_json"), (b'{"x":"\\ud800"}', "invalid_native_json")])
def test_invalid_bytes_and_nonfinite_or_ambiguous_json_are_qualified(raw, error):
    operation = "public.reactome.record"
    value = result(snapshot(operation, raw=raw), operation)
    assert value["parse_state"] == "decode_failed" and value["decode_error"] == error
    assert value["native_json"] is None and value["native_text"] is None
    assert value["representation_state"] == "invalid" and error in codes(value)
    assert value["raw_artifact_ref"] == "artifact_" + hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("operation", tuple(NATIVE))
@pytest.mark.parametrize("token", ["1e-999", "-1E-999", "0." + "0" * 400 + "1"])
def test_nonzero_native_numbers_cannot_silently_underflow_to_observed_zero(operation, token):
    native = deepcopy(NATIVE[operation])
    owner = native[0] if isinstance(native, list) else native
    owner["unknown_numeric"] = {"nested": ["original_number_token"]}
    raw = json.dumps(native).replace('"original_number_token"', token).encode()
    capture = snapshot(operation, raw=raw)
    value = result(capture, operation)
    assert capture.content == raw and value["response"]["body_complete"] is True
    assert value["parse_state"] == "decode_failed" and value["decode_error"] == "invalid_native_json"
    assert value["native_json"] is None and value["representation_state"] == "invalid"
    assert codes(value) == {"invalid_native_json"}
    assert value["raw_artifact_ref"] == "artifact_" + hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("operation", tuple(NATIVE))
@pytest.mark.parametrize("token", ["0e999", "-0.0e-999", "1e-308", "-1e-308", "5e-324"])
def test_literal_zero_and_representable_tiny_native_numbers_remain_available(operation, token):
    native = deepcopy(NATIVE[operation])
    owner = native[0] if isinstance(native, list) else native
    owner["unknown_numeric"] = {"nested": ["original_number_token"]}
    raw = json.dumps(native).replace('"original_number_token"', token).encode()
    value = result(snapshot(operation, raw=raw), operation)
    returned = value["native_json"][0] if isinstance(value["native_json"], list) else value["native_json"]
    number, = returned["unknown_numeric"]["nested"]
    assert number == float(token) and type(number) is float
    assert value["parse_state"] == "json" and value["representation_state"] == "complete"
    assert value["issues"] == []


@pytest.mark.parametrize("status", [301, 404, 500])
def test_http_error_and_redirect_are_distinct_from_valid_native_representation(status):
    operation = "public.string.network"
    capture = snapshot(operation, status=status)
    # HTTPError snapshots from the existing transport use the full request URL.
    capture = replace(capture, url=capture.transport["request"]["url"])
    value = result(capture, operation)
    assert value["response"]["http_status"] == status
    assert value["representation_state"] == "complete" and value["parse_state"] == "json"
    assert "http_not_success" in codes(value)
    assert ("http_redirect" in codes(value)) == (status == 301)


def test_cap_failure_retains_valid_json_without_claiming_complete_response():
    operation = "public.reactome.record"
    raw = b'{"stId":"R-HSA-141409"}'
    arguments = {**ARGUMENTS[operation], "max_bytes": len(raw)}
    capture = snapshot(operation, raw=raw, arguments=arguments)
    capture.transport.update(body_complete=False, observed_body_bytes=len(raw) + 1,
        declared_body_bytes=len(raw) + 100, body_capture_failure="provider_response_byte_limit")
    value = result(capture, operation)
    assert value["representation_state"] == "complete"
    assert value["response"]["body_complete"] is False
    assert value["response"]["observed_body_bytes"] == len(raw) + 1
    assert codes(value) == {"response_incomplete", "response_capture_failure", "response_byte_limit_exceeded"}


def test_unknown_transport_observations_are_not_zero_or_inferred_complete():
    operation = "public.string.network"
    capture = snapshot(operation, raw=b"[]")
    for key in ("status", "body_complete", "observed_body_bytes", "declared_body_bytes",
            "retained_body_bytes", "response_byte_limit"):
        capture.transport.pop(key)
    value = result(capture, operation)
    assert value["native_json"] == [] and value["representation_state"] == "complete"
    assert value["response"]["retained_bytes"] == 2
    assert value["response"]["http_status"] is None
    assert value["response"]["observed_body_bytes"] is None
    assert value["response"]["declared_body_bytes"] is None
    assert value["response"]["body_complete"] is None
    assert "response_incomplete" in codes(value)


def test_genuine_empty_body_zero_counts_stays_separate_from_missing_capture():
    operation = "public.quickgo.term"
    value = result(snapshot(operation, raw=b""), operation)
    assert value["response"]["observed_body_bytes"] == 0
    assert value["response"]["declared_body_bytes"] == 0
    assert value["response"]["retained_bytes"] == 0
    assert value["response"]["body_complete"] is True
    assert value["parse_state"] == "decode_failed"


@pytest.mark.parametrize("field,value", [("retained_body_bytes", 999),
    ("observed_body_bytes", 1), ("declared_body_bytes", 999), ("response_byte_limit", 1)])
def test_reported_capture_counter_conflicts_are_retained_and_attributable(field, value):
    operation = "public.reactome.record"
    capture = snapshot(operation)
    capture.transport[field] = value
    view = result(capture, operation)
    assert "transport_count_conflict" in codes(view)
    assert view["response"]["retained_bytes"] == len(capture.content)


def test_capture_boolean_counts_are_unavailable_not_integer_observations():
    operation = "public.reactome.record"
    capture = snapshot(operation)
    capture.transport.update(status=True, observed_body_bytes=False, retained_body_bytes=True)
    value = result(capture, operation)
    assert value["response"]["http_status"] is None
    assert value["response"]["observed_body_bytes"] is None
    assert value["response"]["reported_retained_bytes"] is None


def test_capture_failure_cannot_silently_agree_with_reported_complete_body():
    operation = "public.reactome.record"
    capture = snapshot(operation)
    capture.transport["body_capture_failure"] = "provider_body_capture_failed"
    value = result(capture, operation)
    assert value["response"]["body_complete"] is True
    assert {"response_capture_failure", "transport_count_conflict"} <= codes(value)
    assert any(issue["pointer"] == "/response/body_complete" for issue in value["issues"])


def test_native_media_mismatch_does_not_destroy_the_retained_json():
    operation = "public.reactome.record"
    capture = snapshot(operation)
    capture.transport["headers"]["content-type"] = "text/html"
    capture = replace(capture, media_type="text/html")
    value = result(capture, operation)
    assert value["response"]["content_type"] == "text/html"
    assert value["native_json"] == NATIVE[operation]
    assert "content_type_mismatch" in codes(value)


def test_returned_native_identifiers_taxa_and_ordinals_are_not_filtered():
    operation = "public.string.network"
    rows = deepcopy(NATIVE[operation]) + [None, {"stringId_A": "10090.other", "stringId_B": IDS[1],
        "ncbiTaxonId": 10090, "score": 0}]
    value = result(snapshot(operation, raw=json.dumps(rows).encode()), operation)
    assert value["native_json"] == rows
    assert value["representation_state"] == "partial"
    assert "native_row_not_object" in codes(value)
    assert "native_edge_outside_request" in codes(value)
    assert "native_taxon_differs_from_request" in codes(value)
    assert any(issue["pointer"] == "/native_json/2/stringId_A" for issue in value["issues"])


@pytest.mark.parametrize("operation,native,expected", [
    ("public.reactome.record", {}, "native_id_missing"),
    ("public.reactome.record", {"stId": None}, "native_id_invalid"),
    ("public.reactome.record", {"stId": "R-MMU-141409"}, "native_id_differs_from_request"),
    ("public.quickgo.term", {"results": None}, "native_results_not_array"),
    ("public.quickgo.term", {"results": [{"id": "GO:0000002"}]}, "native_id_differs_from_request"),
])
def test_native_identity_and_envelope_failures_remain_available(operation, native, expected):
    value = result(snapshot(operation, raw=json.dumps(native).encode()), operation)
    assert value["native_json"] == native and expected in codes(value)


@pytest.mark.parametrize("text,expected", [
    ("            orphan\n", "kegg_orphan_continuation"),
    ("ENTRY       R00259\nNAME        a\n", "kegg_terminator_count"),
    ("ENTRY       R00001\n///\n", "native_id_differs_from_request"),
    ("ENTRY       R00259\n///\nENTRY       R00001\n///\n", "kegg_entry_count"),
    ("ENTRY       R00259\n///\nUNKNOWN     trailing\n", "kegg_trailing_data"),
])
def test_kegg_partial_and_wrong_entry_preserve_every_original_line(text, expected):
    operation = "public.kegg.reaction"
    value = result(snapshot(operation, raw=text.encode()), operation)
    assert value["native_text"] == text and expected in codes(value)
    assert "".join(line["text"] for block in value["native_fields"] for line in block["lines"]) == text
    assert [line["line_number"] for block in value["native_fields"] for line in block["lines"]] == list(
        range(1, len(text.splitlines()) + 1))


def test_kegg_unicode_text_separators_do_not_invent_native_line_identities():
    operation = "public.kegg.reaction"
    text = "ENTRY       R00259\nNAME        a\u2028b\u0085c\n///\n"
    value = result(snapshot(operation, raw=text.encode()), operation)
    assert value["native_text"] == text
    assert value["native_fields"][1]["lines"] == [{"line_number": 2, "text": "NAME        a\u2028b\u0085c\n"}]
    assert value["representation_state"] == "complete"


@pytest.mark.parametrize("change", ["service", "url", "request_url", "request_method", "logical_args", "redirect", "timeout"])
def test_snapshot_custody_and_selected_request_conflicts_are_rejected(change):
    operation = "public.quickgo.term"
    capture = snapshot(operation)
    if change == "service":
        capture = replace(capture, service="reactome")
    elif change == "url":
        capture = replace(capture, url="https://example.org/GO:0000001")
    elif change == "request_url":
        capture.transport["request"]["url"] += "?page=2"
    elif change == "request_method":
        capture.transport["request"]["method"] = "POST"
    elif change == "logical_args":
        capture.request["term_id"] = "GO:0000002"
    elif change == "redirect":
        capture.transport["request_policy"]["automatic_redirects"] = True
    else:
        capture.transport["request_policy"]["timeout_seconds"] = False
    with pytest.raises(ValueError):
        result(capture, operation)


def test_string_actual_transport_identity_cannot_be_omitted_or_duplicated():
    operation = "public.string.network"
    for suffix in ("&caller_identity=second", "&extra=parameter"):
        capture = snapshot(operation)
        capture.transport["request"]["url"] += suffix
        with pytest.raises(ValueError):
            result(capture, operation)
    capture = snapshot(operation)
    capture.transport["request"]["url"] = capture.url
    with pytest.raises(ValueError):
        result(capture, operation)


@pytest.mark.parametrize("reference", ["artifact_" + "0" * 64, True, "source_" + "a" * 64])
def test_artifact_ref_must_identify_actual_response_bytes(reference):
    operation = "public.reactome.record"
    with pytest.raises(ValueError):
        provider_result(operation, snapshot(operation), source_ref=SOURCE, artifact_ref=reference)


@pytest.mark.parametrize("reference", [True, "artifact_" + "a" * 64, SOURCE + "\n"])
def test_source_reference_namespace_and_full_match_are_required(reference):
    operation = "public.reactome.record"
    capture = snapshot(operation)
    with pytest.raises(ValueError):
        provider_result(operation, capture, source_ref=reference,
            artifact_ref="artifact_" + hashlib.sha256(capture.content).hexdigest())


@pytest.mark.parametrize("mutation", ["issues", "representation", "parse", "coverage", "operation", "native_nonfinite", "counter_bool", "extra"])
def test_closed_dto_and_semantic_disagreement_are_rejected(mutation):
    operation = "public.reactome.record"
    value = result(snapshot(operation), operation)
    if mutation == "issues":
        value["issues"] = [{"code": "http_not_success", "pointer": "/response/http_status", "line_number": None}]
    elif mutation == "representation":
        value["representation_state"] = "partial"
    elif mutation == "parse":
        value["parse_state"] = "decode_failed"
    elif mutation == "coverage":
        value["population_coverage"] = "exhaustive"
    elif mutation == "operation":
        value["operation"] = "public.quickgo.term"
    elif mutation == "native_nonfinite":
        value["native_json"]["bad"] = float("nan")
    elif mutation == "counter_bool":
        value["response"]["retained_bytes"] = True
    else:
        value["unexpected"] = "not admitted"
    if mutation in {"issues", "representation", "parse"}:
        assert Draft202012Validator(provider_result_schema()).is_valid(value)
    with pytest.raises(ValueError):
        validate_provider_result(value)


@pytest.mark.parametrize("mutation", ["ordinal", "text", "order", "native_text", "native_json"])
def test_kegg_dto_field_views_cannot_disagree_with_exact_native_text(mutation):
    operation = "public.kegg.reaction"
    value = result(snapshot(operation), operation)
    if mutation == "ordinal":
        value["native_fields"][1]["lines"][0]["line_number"] = 99
    elif mutation == "text":
        value["native_fields"][1]["lines"][0]["text"] = "NAME        changed\r\n"
    elif mutation == "order":
        value["native_fields"].reverse()
    elif mutation == "native_text":
        value["native_text"] = value["native_text"].replace("second name", "third name!")
    else:
        value["native_json"] = {}
    assert Draft202012Validator(provider_result_schema()).is_valid(value)
    with pytest.raises(ValueError):
        validate_provider_result(value)


def test_returned_values_and_schema_are_independent_copies():
    operation = "public.reactome.record"
    value = result(snapshot(operation), operation)
    validated = validate_provider_result(value)
    validated["native_json"]["unknown"]["zero"] = 999
    assert value["native_json"]["unknown"]["zero"] == 0
    schema = provider_result_schema()
    schema["properties"]["population_coverage"]["const"] = "changed"
    assert provider_result_schema()["properties"]["population_coverage"]["const"] == "selected_response_only"


@pytest.mark.parametrize("cid", [True, False, 0, -1, 2244.0, "2244", None, [2244], {"cid": 2244}])
def test_pubchem_selected_cid_is_a_positive_literal_integer(cid):
    operation = "public.pubchem.compound"
    with pytest.raises(ValueError):
        provider_request_spec(operation, {**ARGUMENTS[operation], "cid": cid})
    missing = deepcopy(ARGUMENTS[operation])
    missing.pop("cid")
    with pytest.raises(ValueError):
        validate_provider_arguments(operation, missing)


PUBCHEM_IDENTITY_FAILURES = [
    ([], "json_root_not_object", "/native_json"),
    ({}, "native_results_missing", "/native_json/PC_Compounds"),
    ({"PC_Compounds": None}, "native_results_not_array", "/native_json/PC_Compounds"),
    ({"PC_Compounds": {}}, "native_results_not_array", "/native_json/PC_Compounds"),
    ({"PC_Compounds": [None]}, "native_row_not_object", "/native_json/PC_Compounds/0"),
    ({"PC_Compounds": [{}]}, "native_id_missing", "/native_json/PC_Compounds/0/id"),
    ({"PC_Compounds": [{"id": None}]}, "native_id_invalid", "/native_json/PC_Compounds/0/id"),
    ({"PC_Compounds": [{"id": []}]}, "native_id_invalid", "/native_json/PC_Compounds/0/id"),
    ({"PC_Compounds": [{"id": {}}]}, "native_id_missing", "/native_json/PC_Compounds/0/id/id"),
    ({"PC_Compounds": [{"id": {"id": 2244}}]}, "native_id_invalid", "/native_json/PC_Compounds/0/id/id"),
    ({"PC_Compounds": [{"id": {"id": {}}}]}, "native_id_missing", "/native_json/PC_Compounds/0/id/id/cid"),
    *[({"PC_Compounds": [{"id": {"id": {"cid": cid}}}]}, "native_id_invalid",
        "/native_json/PC_Compounds/0/id/id/cid") for cid in (True, False, 0, -1, 2244.0, "2244", None)],
    ({"PC_Compounds": [{"cid": 2244, "other": {"id": {"id": {"cid": 2244}}}}]},
        "native_id_missing", "/native_json/PC_Compounds/0/id"),
    ({"PC_Compounds": [{"id": {"id": {"cid": 2244}}}, {"id": {"id": {"cid": 2245}}}]},
        "native_id_differs_from_request", "/native_json/PC_Compounds/1/id/id/cid"),
]


@pytest.mark.parametrize("native,code,pointer", PUBCHEM_IDENTITY_FAILURES)
def test_pubchem_native_identity_failures_preserve_literal_envelopes_and_occurrence_paths(native, code, pointer):
    operation = "public.pubchem.compound"
    capture = snapshot(operation, raw=json.dumps(native).encode())
    value = result(capture, operation)
    assert value["native_json"] == native and value["parse_state"] == "json"
    assert value["issues"] == [{"code": code, "pointer": pointer, "line_number": None}]
    assert value["representation_state"] in {"partial", "invalid"}
    assert value["raw_artifact_ref"] == "artifact_" + hashlib.sha256(capture.content).hexdigest()


def test_pubchem_duplicate_compounds_unknown_fields_and_original_json_bytes_are_not_collapsed():
    operation = "public.pubchem.compound"
    raw = (b'{\n "PC_Compounds":[{"id":{"id":{"cid":2244}},"unknown":null},\n'
        b' {"id":{"id":{"cid":2244}},"unknown":{"zero":0,"empty":[],"false":false}}],'
        b'"unrecognized":{"cid":"not an identity assertion"}\n}\n')
    value = result(snapshot(operation, raw=raw), operation)
    assert value["native_json"] == json.loads(raw)
    assert len(value["native_json"]["PC_Compounds"]) == 2
    assert value["issues"] == [] and value["representation_state"] == "complete"
    assert value["population_coverage"] == "selected_response_only"
    assert value["response"]["retained_bytes"] == len(raw)
    assert value["raw_artifact_ref"] == "artifact_" + hashlib.sha256(raw).hexdigest()
    validated = validate_provider_result(value)
    validated["native_json"]["PC_Compounds"][0]["unknown"] = "changed detached copy"
    assert value["native_json"]["PC_Compounds"][0]["unknown"] is None


@pytest.mark.parametrize("suffix", ["?cid=2245", "?page=2", "/", "?format=JSON"])
def test_pubchem_snapshot_cannot_relabel_or_extend_the_fixed_selected_endpoint(suffix):
    operation = "public.pubchem.compound"
    capture = snapshot(operation)
    capture.transport["request"]["url"] += suffix
    with pytest.raises(ValueError, match="molecular_provider_snapshot_request_conflict"):
        result(capture, operation)
