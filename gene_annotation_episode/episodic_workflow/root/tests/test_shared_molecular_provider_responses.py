"""Reader-only contracts: original HPA fixture; other operands are synthetic protocols."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from jsonschema import Draft202012Validator
import pytest
from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.molecular_provider_acquisition import OPERATIONS, provider_request_spec, provider_result, provider_result_schema, validate_provider_result, provider_value, provider_receipt


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


@pytest.mark.parametrize("reference", ["artifact_" + "0" * 64, True, "source_" + "a" * 64])
def test_artifact_ref_must_identify_actual_response_bytes(reference):
    operation = "public.reactome.record"
    with pytest.raises(ValueError):
        provider_result(operation, snapshot(operation), source_ref=SOURCE, artifact_ref=reference)


@pytest.mark.parametrize('policy', [None, {}, {'automatic_redirects': 0}, {'automatic_redirects': True}],
    ids=['missing-policy', 'missing-redirect', 'integer-redirect', 'enabled-redirect'])
def test_absence_does_not_relax_original_no_redirect_authentication(policy):
    capture = snapshot('public.quickgo.term')
    capture.transport['request_policy'] = policy
    with pytest.raises(ValueError, match='transport_policy_conflict'):
        result(capture, 'public.quickgo.term')


@pytest.mark.parametrize('change,code', [('status', 'molecular_provider_http_not_success'),
    ('body_complete', 'molecular_provider_response_incomplete'), ('identity', 'molecular_provider_native_id_differs_from_request')])
def test_failed_reader_receipts_keep_literal_bytes_without_acquired_data(change, code):
    operation = 'public.reactome.record'
    capture = snapshot(operation, raw=b'{"stId":"R-MMU-141409"}') if change == 'identity' else snapshot(operation)
    capture.transport['request_policy'].pop('timeout_seconds')
    if change == 'status':
        capture.transport['status'] = 500
    if change == 'body_complete':
        capture.transport['body_complete'] = False
    artifact = 'artifact_' + hashlib.sha256(capture.content).hexdigest()
    value = provider_value(operation, capture, artifact_ref=artifact)
    assert value['raw_artifact_ref'] == artifact
    assert provider_receipt(value, source_ref=SOURCE) == {
        'acquired': False, 'source_ref': SOURCE, 'data_ref': None, 'failure_code': code}
