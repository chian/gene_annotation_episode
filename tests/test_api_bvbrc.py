"""BV-BRC native protocol and source-publication checks, not model science."""
from copy import deepcopy
from dataclasses import replace
from email.message import Message
import http.client
import io
import json
from urllib.error import HTTPError

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, SourceSnapshot
from gene_annotation_episode.api_bvbrc import (
    BVBRCDataClient, BVBRCDataService, DEFAULT_BASE_URL, QUERY_OPERATION,
    RESULT_OPERATION, SERVICE, request_url,
)
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


# Values captured from an unauthenticated public GET on 2026-10-23 at
# 17:00:40 UTC. JSON is reserialized here; this is a semantic fixture rather
# than a claim that these are the original HTTP entity's byte positions.
FEATURE_ROWS = [
    {"feature_id": "PATRIC.562.67264.AP022533.CDS.3368331.3369092.fwd",
     "product": "Endonuclease/exonuclease/phosphatase family protein",
     "pgfam_id": "PGF_03781125", "genome_id": "562.67264",
     "genome_name": "Escherichia coli strain THO-006", "gene": "ybhP",
     "start": 3368331, "accession": "AP022533", "strand": "+",
     "plfam_id": "PLF_561_00003070", "refseq_locus_tag": "THOESC006_31400",
     "end": 3369092},
    {"feature_id": "RefSeq.1090929.3.AHAW01000084.CDS.132605.133366.fwd",
     "product": "putative metal-dependent hydrolase", "genome_id": "1090929.3",
     "genome_name": "Escherichia coli O127:H27 str. C43/90", "gene": "ybhP",
     "start": 132605, "accession": "AHAW01000084", "protein_id": "EMS02283.1",
     "strand": "+", "refseq_locus_tag": "C4390_46240", "end": 133366},
]


def request():
    return {"collection": "genome_feature",
        "filters": [{"field": "gene", "operator": "eq", "value": "ybhP"}],
        "fields": ["feature_id", "genome_id", "genome_name", "gene", "product",
                   "protein_id", "refseq_locus_tag", "pgfam_id", "plfam_id",
                   "accession", "start", "end", "strand"], "limit": 2}


def snapshot(prepared, rows=None, *, content_range="items 0-2/88287"):
    headers = {} if content_range is None else {"content-range": content_range}
    return SourceSnapshot(SERVICE, request_url(DEFAULT_BASE_URL, prepared["request"]),
        deepcopy(prepared["request"]), "2026-10-23T17:00:40.560099+00:00",
        json.dumps(FEATURE_ROWS if rows is None else rows).encode(), "application/json",
        {"status": 200, "headers": headers,
         "representation": "captured_native_values_reserialized_fixture"})


class Client:
    def __init__(self):
        self.requests = []

    def query(self, request):
        self.requests.append(deepcopy(request))
        return snapshot({"request": request})


def prepare(service, original=None, *, operation=QUERY_OPERATION, selector=None, scope=None):
    return service.prepare(operation, request() if original is None else original, {},
        scope=scope, previous_events=[], selector=selector)


def test_original_assignment_omissions_survive_and_preparation_makes_no_request():
    client = Client()
    service = BVBRCDataService(None, client=client)
    original = {"collection": "genome_feature", "filters": []}
    assert service.capabilities()[0]["name"] == QUERY_OPERATION
    validated = service.validate_request(original, None)
    assert validated == original and validated is not original
    command = prepare(service, original)
    assert client.requests == []
    assert original == {"collection": "genome_feature", "filters": []}
    assert command["request"] == {"collection": "genome_feature", "filters": [],
        "fields": [], "sort": [], "offset": 0, "limit": 25}
    assert command["operation"] == QUERY_OPERATION and command["mutates_remote"] is False


@pytest.mark.parametrize("invalid", [
    {"collection": "not_a_bound_collection", "filters": []},
    {"collection": "genome", "filters": [], "url": "https://elsewhere.invalid"},
    {"collection": "genome", "filters": [], "limit": 0},
    {"collection": "genome", "filters": [], "offset": -1},
    {"collection": "genome", "filters": [], "fields": ["id)&limit(999)"]},
    {"collection": "genome", "filters": [{"field": "genome_id", "operator": "in", "value": "x"}]},
    {"collection": "genome", "filters": [{"field": "genome_id", "operator": "eq", "value": ["x"]}]},
    {"collection": "genome", "filters": [{"field": "taxon_id", "operator": "gt", "value": True}]},
])
def test_requests_cannot_change_endpoint_or_inject_rql_operators(invalid):
    with pytest.raises(ContractError):
        BVBRCDataService(None).validate_request(invalid, None)


def test_literals_are_encoded_individually_and_real_query_operators_remain():
    query = {"collection": "genome_feature",
        "filters": [{"field": "gene", "operator": "eq", "value": "A&B),limit(999)"},
                    {"field": "genome_id", "operator": "in", "value": ["562.1", "562.2"]},
                    {"field": "public", "operator": "eq", "value": True}],
        "fields": ["feature_id", "gene"],
        "sort": [{"field": "feature_id", "direction": "asc"}], "limit": 2, "offset": 4}
    url = request_url(DEFAULT_BASE_URL, query)
    assert "eq(gene,A%26B%29%2Climit%28999%29)" in url
    assert "in(genome_id,(562.1,562.2))" in url
    assert "eq(public,true)" in url
    assert "select(feature_id,gene)&sort(+feature_id)&limit(2,4)" in url
    assert "%28gene%2C" not in url  # the whole query was not URL-encoded


def test_one_selected_request_returns_immediate_response_without_remote_job():
    client = Client()
    service = BVBRCDataService(None, client=client)
    command = prepare(service)
    native = service.invoke(command)
    event = service.decode(command, native)
    assert len(client.requests) == 1
    assert event["kind"] == "response" and event["state"] == "completed"
    assert event["native_handle"] == {} and event["handoff_ready"] is True
    assert event["result_available"] is True and event["failure_code"] is None
    assert "rows" not in event["facts"] and "product" not in event["facts"]
    assert service.prepare_observation(request(), {}, scope=None) is None
    assert len(client.requests) == 1


@pytest.mark.parametrize("header,total,next_offset", [
    ("items 0-2/88287", 88287, 2),
    ("items 0-2/2", 2, None),
    ("items 0-2/*", None, 2),
    (None, None, 2),
])
def test_pagination_uses_actual_row_count_not_inclusive_native_range_end(header, total, next_offset):
    service = BVBRCDataService(None)
    command = prepare(service)
    facts = service.decode(command, snapshot(command, content_range=header))["facts"]
    assert facts["returned_count"] == 2
    assert facts["content_range"] == header and facts["reported_total"] == total
    assert facts["next_offset"] == next_offset


def test_empty_result_is_completed_query_not_biological_failure_or_fake_job():
    service = BVBRCDataService(None)
    command = prepare(service)
    event = service.decode(command, snapshot(command, [], content_range="items 0-0/0"))
    assert event["handoff_ready"] and event["result_available"]
    assert event["facts"]["returned_count"] == 0 and event["facts"]["next_offset"] is None
    assert event["failure_code"] is None and event["native_handle"] == {}


def test_original_page_is_reused_but_changed_selector_is_one_new_request():
    client = Client()
    service = BVBRCDataService(None, client=client)
    first = prepare(service, operation=RESULT_OPERATION, selector={})
    assert first["cache_original"] is True and client.requests == []
    with pytest.raises(ContractError, match="bvbrc_original_response_required"):
        service.invoke(first)
    later = prepare(service, operation=RESULT_OPERATION, selector={"offset": 2})
    assert later["cache_original"] is False
    assert later["request"]["offset"] == 2 and later["request"]["limit"] == 2
    service.invoke(later)
    assert client.requests == [later["request"]]
    assert request().get("offset") is None


def test_wrong_query_and_invalid_native_payload_cannot_complete_handoff():
    service = BVBRCDataService(None)
    command = prepare(service)
    native = snapshot(command)
    changed_request = deepcopy(native.request)
    changed_request["filters"][0]["value"] = "otherGene"
    wrong = service.decode(command, replace(native, request=changed_request))
    assert wrong["state"] == "failed" and not wrong["handoff_ready"]
    assert wrong["failure_code"] == "bvbrc_response_request_mismatch"
    invalid = service.decode(command, replace(native, content=b'{"error":"query failed"}'))
    assert invalid["failure_code"] == "bvbrc_expected_native_row_array"
    malformed = service.decode(command, replace(native, content=b'[{'))
    assert malformed["failure_code"] == "bvbrc_invalid_json_response"


def test_publication_preserves_reference_subjects_missing_fields_and_native_coordinates(tmp_path):
    with Store(tmp_path) as store:
        problem = store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
        scope = {"subject_refs": problem["subject_refs"]}
        tools = ToolRegistry(store)
        service = BVBRCDataService(tools)
        source_count_before = len(store.list("source"))
        command = prepare(service, scope=scope)
        native = snapshot(command)
        first = service.publish(request(), {}, native, scope, "first-result")
        assert first["status"] == "completed" and first["result"]["rows"] == FEATURE_ROWS
        assert "pgfam_id" not in first["result"]["rows"][1]
        assert first["result"]["rows"][0]["start"] == 3368331
        source = store.get(first["result"]["source_ref"])
        assert source["provider"] == SERVICE and source["origin"] == "external"
        assert store.get_artifact(source["artifact_ref"]) == native.content
        provenance = json.loads(store.get_artifact(source["request_ref"]))
        assert provenance["request"] == command["request"]
        assert provenance["transport"]["headers"]["content-range"] == "items 0-2/88287"
        assert not store.list("observation") and not store.list("assessment")
        assert not store.list("annotation") and not store.list("feature")
        repeated = service.publish(request(), {}, native, scope, "replayed-result")
        assert repeated["record_refs"] == first["record_refs"]
        assert repeated["changed_record_refs"] == []
        assert len(store.list("source")) == source_count_before + 1
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 0


class Response:
    status = 200

    def __init__(self, body=b"[]", *, read_error=None):
        self.body, self.read_error = body, read_error
        self.headers = Message()
        self.headers["Content-Type"] = "application/json"
        self.headers["Content-Range"] = "items 0-0/0"
        self.headers["Set-Cookie"] = "must-not-be-retained"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return "https://www.bv-brc.org/api/genome_feature/"

    def read(self):
        if self.read_error is not None:
            raise self.read_error
        return self.body


def test_native_transport_is_one_get_and_keeps_page_headers_without_credentials(monkeypatch):
    calls = []
    class Opener:
        def open(self, request, timeout):
            calls.append((request, timeout))
            return Response()
    monkeypatch.setattr("gene_annotation_episode.api_bvbrc.urllib.request.build_opener", lambda handler: Opener())
    native = BVBRCDataClient(timeout=3).query(request())
    assert len(calls) == 1 and calls[0][0].get_method() == "GET" and calls[0][1] == 3
    assert native.transport["headers"]["content-range"] == "items 0-0/0"
    assert native.transport["headers"]["set-cookie"] == "<redacted>"
    assert native.transport["automatic_redirects"] is False
    assert native.transport["request"]["headers"]["Accept"] == "application/json"
    assert "must-not-be-retained" not in json.dumps(native.transport)


@pytest.mark.parametrize("status,expected", [(429, "provider_http_429"), (302, "provider_redirect_not_followed")])
def test_http_failure_retains_actual_bytes_and_does_not_retry(monkeypatch, status, expected):
    calls = []
    class Opener:
        def open(self, request, timeout):
            calls.append(request)
            headers = Message()
            headers["Content-Type"] = "text/html"
            headers["Retry-After"] = "3"
            raise HTTPError(request.full_url, status, "native failure", headers, io.BytesIO(b"native failed body"))
    monkeypatch.setattr("gene_annotation_episode.api_bvbrc.urllib.request.build_opener", lambda handler: Opener())
    with pytest.raises(AcquisitionError) as captured:
        BVBRCDataClient().query(request())
    assert captured.value.code == expected and captured.value.snapshot.content == b"native failed body"
    assert captured.value.snapshot.transport["status"] == status
    assert captured.value.retry_after == 3 and len(calls) == 1


def test_incomplete_success_response_preserves_partial_bytes_but_never_completes(monkeypatch):
    class Opener:
        def open(self, request, timeout):
            return Response(read_error=http.client.IncompleteRead(b"[]", 10))
    monkeypatch.setattr("gene_annotation_episode.api_bvbrc.urllib.request.build_opener", lambda handler: Opener())
    with pytest.raises(AcquisitionError) as captured:
        BVBRCDataClient().query(request())
    assert captured.value.snapshot.content == b"[]"
    assert captured.value.snapshot.transport["body_complete"] is False
    service = BVBRCDataService(None)
    event = service.decode(prepare(service), captured.value.snapshot)
    assert not event["handoff_ready"] and event["failure_code"] == "bvbrc_response_body_incomplete"


@pytest.mark.parametrize("configuration", [
    {"service": "another_service"}, {"kind": "local"}, {"token": "not-supported"},
    {"base_url": "https://example.invalid/api?secret=value"},
    {"base_url": "https://user:password@example.invalid/api"}, {"timeout": False},
])
def test_configuration_is_caller_owned_and_cannot_smuggle_credentials(configuration):
    with pytest.raises(ContractError):
        BVBRCDataService(None, configuration)
