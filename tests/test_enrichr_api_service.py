"""Engineered protocol/publication fixtures and loopback HTTP, never live Enrichr.

Manual protocol assembly here proves adapter consistency only. Original selected
action authentication and issued-stage recovery belong to APIServiceExecution.
"""
import base64
from copy import deepcopy
from dataclasses import asdict, replace
from email.parser import BytesParser
from email.policy import default
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import threading
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
import urllib.request

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, SourceSnapshot
from gene_annotation_episode.api_enrichr import (EnrichrService, PROTOCOL_VERSION, QUERY,
    RESULT, WIRE_PROFILE, validate_enrichr_configuration)
from gene_annotation_episode import api_enrichr
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def request(profile="standard_enrichr_v1", *, supplied=False):
    return {"version": "enrichr_request_v1", "protocol_profile": profile,
        "library": "Literal library / α", "genes": ["ENSG000001.7", "X", "X"],
        "identifier_policy": "literal_no_mapping", "species_context": None,
        "description": "Literal description\nsecond line α",
        "background": {"policy": "supplied" if supplied else "service_native",
            "genes": ["X", "Y", "X"] if supplied else None},
        "native_statistic_profile": "documented_odds_v1"}


def configuration(profile="standard_enrichr_v1", *, base=None):
    return {"kind": "api", "service": "enrichr", "protocol_profile": profile,
        "base_url": base or ("https://example.invalid/Enrichr" if profile == "standard_enrichr_v1"
            else "https://example.invalid/speedrichr/api"),
        "timeout": 0.75, "response_byte_limit": 4096}


SELECTOR = {"version": "enrichr_selector_v1", "offset": 0, "limit": 10}


def native(stage, content, *, status=200, complete=True):
    """Explicit engineering HTTP capture; no independent producer assertion."""
    http = stage["http"]
    headers = {"Accept": http["accept"]}
    if http["content_type"] is not None:
        headers["Content-Type"] = http["content_type"]
    wire = {"method": http["method"], "url": http["url"], "headers": headers}
    if http["body_base64"] is not None:
        body = base64.b64decode(http["body_base64"])
        wire.update(body_base64=http["body_base64"], body_sha256=hashlib.sha256(body).hexdigest())
    return SourceSnapshot("enrichr", http["url"], deepcopy(stage),
        "2026-10-30T00:00:00+00:00", content, "application/json",
        {"status": status, "request": wire, "headers": {"content-type": "application/json"},
            "effective_url": http["url"], "body_complete": complete,
            "request_policy": {"timeout_seconds": http["timeout_seconds"], "automatic_redirects": False}})


class HTTPFixture:
    def __init__(self, *, error=False):
        self.calls = []
        self.error = error

    def _http(self, service, url, params, media_type, **kwargs):
        self.calls.append((service, url, params, media_type, deepcopy(kwargs)))
        wire = {"method": "POST" if kwargs["body"] is not None else "GET", "url": url,
            "headers": {"Accept": kwargs["accept"]}}
        if kwargs["body"] is not None:
            wire["headers"]["Content-Type"] = kwargs["content_type"]
            wire.update(body_base64=base64.b64encode(kwargs["body"]).decode(),
                body_sha256=hashlib.sha256(kwargs["body"]).hexdigest())
        snapshot = SourceSnapshot(service, url, params, "2026-10-30T00:00:00+00:00",
            b'{"userListId":21}', media_type, {"status": 503 if self.error else 200,
                "request": wire, "headers": {}, "body_complete": True,
                "request_policy": {"timeout_seconds": kwargs["timeout_seconds"],
                                   "automatic_redirects": kwargs["follow_redirects"]}})
        if self.error:
            raise AcquisitionError("provider_http_503", snapshot=snapshot,
                phase="http_response", retry_after=2, diagnostic={"fixture": "actual_error_port"})
        return snapshot


def service_without_store(profile="standard_enrichr_v1", *, client=None):
    return EnrichrService(SimpleNamespace(clients=client or HTTPFixture()), configuration(profile))


@pytest.mark.parametrize("profile,supplied,length", [
    ("standard_enrichr_v1", False, 2), ("speedrichr_v1", False, 2),
    ("speedrichr_v1", True, 3)])
def test_exact_selected_protocol_wire_encodings(profile, supplied, length):
    service = service_without_store(profile)
    selected = request(profile, supplied=supplied)
    main = service.prepare(QUERY, selected, {}, scope=None, previous_events=[])
    assert service.protocol_length(main) == length
    upload = service.protocol_request(main, stage=0, retained_responses=[])
    assert upload["http"]["url"] == configuration(profile)["base_url"] + "/addList"
    assert "/api/api/" not in upload["http"]["url"]
    multipart = BytesParser(policy=default).parsebytes(("Content-Type: "
        + upload["http"]["content_type"] + "\r\nMIME-Version: 1.0\r\n\r\n").encode()
        + base64.b64decode(upload["http"]["body_base64"]))
    parts = list(multipart.iter_parts())
    assert [p.get_param("name", header="Content-Disposition") for p in parts] == ["list", "description"]
    assert all(p.get_filename() is None for p in parts)
    assert [p.get_payload(decode=True).decode() for p in parts] == [
        "ENSG000001.7\nX\nX", selected["description"]]
    prefix = [native(upload, b'{"userListId":21,"shortId":"unused"}')]
    if supplied:
        background = service.protocol_request(main, stage=1, retained_responses=prefix)
        assert background["http"]["url"].endswith("/speedrichr/api/addbackground")
        assert background["http"]["content_type"] == "application/x-www-form-urlencoded"
        assert parse_qs(base64.b64decode(background["http"]["body_base64"]).decode()) == {
            "background": ["X\nY\nX"]}
        prefix.append(native(background, b'{"backgroundid":"opaque+/ ="}'))
    enrichment = service.protocol_request(main, stage=length-1, retained_responses=prefix)
    http = enrichment["http"]
    expected = {"userListId": ["21"], "backgroundType": [selected["library"]]}
    if supplied:
        expected["backgroundid"] = ["opaque+/ ="]
        assert http["method"] == "POST" and http["url"].endswith("/backgroundenrich")
        assert parse_qs(base64.b64decode(http["body_base64"]).decode()) == expected
    else:
        assert http["method"] == "GET" and urlsplit(http["url"]).path.endswith("/enrich")
        assert parse_qs(urlsplit(http["url"]).query) == expected
        assert http["body_base64"] is None
    assert enrichment["prior_response_sha256"] == [s.sha256 for s in prefix]
    assert main["request"] == selected  # No ID conversion, sorting, deduplication or species default.


@pytest.mark.parametrize("content", [b'{}', b'{"userListId":null}', b'{"userListId":true}',
    b'{"userListId":"21"}', b'{"userListId":-1}', b'{"userListId":[]}',
    b'{"userListId":21,"userListId":22}', b'not-json', b'\xff'])
def test_invalid_native_upload_id_never_constructs_next_request(content):
    service = service_without_store()
    main = service.prepare(QUERY, request(), {}, scope=None, previous_events=[])
    upload = service.protocol_request(main, stage=0, retained_responses=[])
    with pytest.raises(ValueError, match="enrichr_upload_"):
        service.protocol_request(main, stage=1, retained_responses=[native(upload, content)])
    assert service.client.calls == []


@pytest.mark.parametrize("content", [b'{}', b'{"backgroundid":null}', b'{"backgroundid":3}',
    b'{"backgroundid":""}', b'{"backgroundid":"\\ud800"}'])
def test_invalid_native_background_id_never_constructs_enrichment(content):
    service = service_without_store("speedrichr_v1")
    main = service.prepare(QUERY, request("speedrichr_v1", supplied=True), {}, scope=None, previous_events=[])
    upload = service.protocol_request(main, stage=0, retained_responses=[])
    prefix = [native(upload, b'{"userListId":21}')]
    background = service.protocol_request(main, stage=1, retained_responses=prefix)
    with pytest.raises(ValueError, match="enrichr_upload_"):
        service.protocol_request(main, stage=2, retained_responses=[*prefix, native(background, content)])
    assert service.client.calls == []


@pytest.mark.parametrize("change", ["incomplete", "http_failed", "foreign_request", "wire_url", "wire_body",
    "wire_content_type", "wire_timeout", "wire_redirect_bool_alias", "wire_timeout_bool_alias",
    "wrong_prefix_length"])
def test_prefix_conflicts_fail_before_any_next_http(change):
    service = service_without_store()
    if change == "wire_timeout_bool_alias":
        service.configuration["timeout"] = 1
    main = service.prepare(QUERY, request(), {}, scope=None, previous_events=[])
    stage = service.protocol_request(main, stage=0, retained_responses=[])
    snapshot = native(stage, b'{"userListId":21}')
    transport = deepcopy(snapshot.transport)
    if change == "incomplete":
        transport["body_complete"] = False
    elif change == "http_failed":
        transport["status"] = 503
    elif change == "foreign_request":
        altered = deepcopy(stage)
        altered["request"]["genes"] = ["foreign"]
        snapshot = replace(snapshot, request=altered)
    elif change == "wire_url":
        transport["request"]["url"] += "/foreign"
    elif change == "wire_body":
        transport["request"]["body_base64"] = "eA=="
    elif change == "wire_content_type":
        transport["request"]["headers"]["Content-Type"] = "application/json"
    elif change == "wire_timeout":
        transport["request_policy"]["timeout_seconds"] = 99
    elif change == "wire_redirect_bool_alias":
        transport["request_policy"]["automatic_redirects"] = 0
    elif change == "wire_timeout_bool_alias":
        transport["request_policy"]["timeout_seconds"] = True
    snapshot = replace(snapshot, transport=transport)
    with pytest.raises(ValueError, match="enrichr_"):
        service.protocol_request(main, stage=1,
            retained_responses=[] if change == "wrong_prefix_length" else [snapshot])
    assert service.client.calls == []


@pytest.mark.parametrize("field,value", [("timeout", True), ("timeout", 0), ("timeout", float("inf")),
    ("timeout", float("nan")), ("timeout", 10**1000), ("response_byte_limit", True),
    ("response_byte_limit", 0), ("base_url", "https://x.invalid/Enrichr/"),
    ("base_url", "https://x.invalid/Enrichr?alternate=1"), ("base_url", "https://u:p@x.invalid/Enrichr"),
    ("protocol_profile", "unknown"), ("extra", "not-allowed")])
def test_configuration_invalid_before_http(field, value):
    selected = configuration()
    selected[field] = value
    with pytest.raises(ValueError, match="enrichr_"):
        validate_enrichr_configuration(selected)


def test_unsupported_standard_supplied_and_fresh_profile_conflict_preflight():
    service = service_without_store()
    with pytest.raises(ValueError, match="background_protocol_conflict"):
        service.prepare(QUERY, request(supplied=True), {}, scope=None, previous_events=[])
    with pytest.raises(ValueError, match="configuration_profile_conflict"):
        service.prepare(QUERY, request("speedrichr_v1"), {}, scope=None, previous_events=[])
    assert service.client.calls == []


@pytest.mark.parametrize("error", [False, True])
def test_invoke_is_one_exact_bounded_http_stage_and_preserves_error_bytes(error):
    client = HTTPFixture(error=error)
    service = service_without_store(client=client)
    main = service.prepare(QUERY, request(), {}, scope=None, previous_events=[])
    stage = service.protocol_request(main, stage=0, retained_responses=[])
    if error:
        with pytest.raises(AcquisitionError) as caught:
            service.invoke(stage)
        assert caught.value.code == "provider_http_503" and caught.value.retry_after == 2
        assert caught.value.phase == "http_response"
        assert caught.value.diagnostic == {"fixture": "actual_error_port"}
        snapshot = caught.value.snapshot
    else:
        snapshot = service.invoke(stage)
    assert snapshot.content == b'{"userListId":21}' and snapshot.request == stage
    assert len(client.calls) == 1
    service_name, url, params, media, kwargs = client.calls[0]
    assert (service_name, url, params, media) == ("enrichr", stage["http"]["url"], {}, "application/json")
    assert kwargs == {"body": base64.b64decode(stage["http"]["body_base64"]),
        "content_type": stage["http"]["content_type"], "accept": "application/json",
        "max_bytes": 4096, "timeout_seconds": 0.75, "follow_redirects": False}


@pytest.fixture
def harness(tmp_path):
    with Store(tmp_path/"state") as store:
        store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
        client = HTTPFixture()
        tools = ToolRegistry(store, clients=client)
        yield SimpleNamespace(store=store, tools=tools, client=client, scope=store.validate_scope(None),
            service=EnrichrService(tools, configuration()))


def engineered_protocol(h, content, *, complete=True):
    """Manual retained stages, explicitly not an authenticated original action."""
    main = h.service.prepare(QUERY, request(), {}, scope=h.scope, previous_events=[])
    upload = h.service.protocol_request(main, stage=0, retained_responses=[])
    prefix = [native(upload, b'{"userListId":21}')]
    final = h.service.protocol_request(main, stage=1, retained_responses=prefix)
    prefix.append(native(final, content, complete=complete))
    stages = []
    for ordinal, snapshot in enumerate(prefix):
        metadata = asdict(snapshot)
        metadata.pop("content")
        metadata["content_ref"] = h.store.artifact(snapshot.content, snapshot.media_type)
        stages.append({"ordinal": ordinal, "stage_code": snapshot.request["stage_code"], "snapshot": metadata})
    transport = deepcopy(prefix[-1].transport)
    transport["enrichr_protocol"] = {"version": PROTOCOL_VERSION, "wire_profile": WIRE_PROFILE,
        "prepared": main, "stages": stages}
    return main, replace(prefix[-1], transport=transport)


def table_body(rows):
    return json.dumps({request()["library"]: rows}, ensure_ascii=False).encode()


def test_decode_no_scientific_parse_and_publication_replay_precedes_calculator(harness, monkeypatch):
    h = harness
    body = ("{" + json.dumps(request()["library"], ensure_ascii=False)
        + ':[[1,"Literal term",0.1234567891234567890123456789,2.5,7.0,["X","X"],0.5,0,0]]}').encode()
    main, snapshot = engineered_protocol(h, body)
    parse, calculate = api_enrichr.parse_enrichr_response, api_enrichr.calculate_enrichr_components
    calls = {"parse": 0, "calculate": 0}
    def forbidden(*args, **kwargs):
        raise AssertionError("decode/replay must not parse or calculate")
    monkeypatch.setattr(api_enrichr, "parse_enrichr_response", forbidden)
    monkeypatch.setattr(api_enrichr, "calculate_enrichr_components", forbidden)
    decoded = h.service.decode(main, snapshot)
    assert decoded["handoff_ready"] and decoded["result_available"]
    assert decoded["facts"]["response_complete"] and decoded["facts"]["native_response_retained"]
    def observed_parse(*args, **kwargs):
        calls["parse"] += 1
        return parse(*args, **kwargs)
    def observed_calculate(*args, **kwargs):
        calls["calculate"] += 1
        return calculate(*args, **kwargs)
    monkeypatch.setattr(api_enrichr, "parse_enrichr_response", observed_parse)
    monkeypatch.setattr(api_enrichr, "calculate_enrichr_components", observed_calculate)
    published = h.service.publish(request(), SELECTOR, snapshot, h.scope, "publication")
    assert published["status"] == "completed" and calls == {"parse": 1, "calculate": 1}
    source = h.store.get(published["result"]["source_ref"])
    assert source["provider"] == "enrichr" and source["version"] is None
    assert h.store.get_artifact(source["artifact_ref"]) == body
    grades = [json.loads(h.store.get_artifact(ref)) for ref in source["auxiliary_artifact_refs"]]
    grade = next(value["grading"] for value in grades if value.get("schema") == "tool_grading_artifact_v1")
    assert grade["version"] == "enrichr_grade_v1"
    returned = published["result"]["execution_enrichr_rows"][0]
    assert {key: value for key, value in returned.items() if key not in ("source_ref", "version")} == grade["components"]["rows"][0]
    assert returned["statistics"]["p_value"]["number_lexeme"] == "0.1234567891234567890123456789"
    assert returned["overlap"]["entries"][0]["value"] == returned["overlap"]["entries"][1]["value"] == "X"
    assert "raw_base64" not in json.dumps(published["result"])
    count = h.store.count("source")
    monkeypatch.setattr(api_enrichr, "parse_enrichr_response", forbidden)
    monkeypatch.setattr(api_enrichr, "calculate_enrichr_components", forbidden)
    assert h.service.publish(request(), SELECTOR, snapshot, h.scope, "publication") == published
    assert h.store.count("source") == count and h.client.calls == []


@pytest.mark.parametrize("body,complete,status,table_state", [
    (table_body([]), True, "completed", "empty"), (b'{"unselected":[]}', True, "partial", "missing"),
    (table_body(None), True, "completed", "null"),
    (b'{broken', True, "partial", "unavailable"), (table_body([]), False, "partial", "empty"),
    (table_body([[1, "native null", None, None, None, [], None, None, None]]), True, "completed", "rows"),
    (table_body([[1, "valid", 0.2, 1, 2, ["X"], 0.5, 0, 0], "malformed"]), True, "partial", "rows"),
    (table_body([[1]]), True, "partial", "rows"),
    (table_body([[1, 17, 0.2, 1, 2, ["X"], 0.5, 0, 0]]), True, "partial", "rows"),
    (table_body([[1, "bad overlap", 0.2, 1, 2, "X", 0.5, 0, 0]]), True, "partial", "rows"),
    (table_body([[1, "valid legacy", 0.2, 1, 2, ["X"], 0.5]]), True, "completed", "rows"),
    (table_body([[1, "valid nine", 0.2, 1, 2, ["X"], 0.5, 0, 0]]), True, "completed", "rows")])
def test_actual_final_partial_malformed_zero_and_null_remain_distinct(harness, body, complete, status, table_state):
    h = harness
    main, snapshot = engineered_protocol(h, body, complete=complete)
    event = h.service.decode(main, snapshot)
    assert event["handoff_ready"] and event["facts"]["response_complete"] == complete
    result = h.service.publish(request(), SELECTOR, snapshot, h.scope, "partial")
    assert result["status"] == status
    table, = result["result"]["execution_enrichr_tables"]
    assert table["table_state"] == table_state and table["response_complete"] == complete
    assert h.store.get_artifact(h.store.get(result["result"]["source_ref"])["artifact_ref"]) == body
    if table_state == "empty":
        assert table["captured_returned_row_count"] == 0
    if table_state in ("missing", "unavailable", "null"):
        assert table["captured_returned_row_count"] is None
    if b"native null" in body:
        assert result["result"]["execution_enrichr_rows"][0]["statistics"]["p_value"]["state"] == "null"
    if table_state == "rows":
        returned = result["result"]["execution_enrichr_rows"]
        assert len(returned) == table["captured_returned_row_count"]
        if b"[[1]]" in body:
            assert returned[0]["native_width"] == 1 and returned[0]["term"]["state"] == "missing"
            assert returned[0]["native_cells"][0]["number_value"] == 1
            assert {error["code"] for error in result["result"]["projection_errors"]} >= {
                "unexpected_native_width", "invalid_term", "invalid_overlap"}
        if b"bad overlap" in body:
            assert returned[0]["overlap"]["native_kind"] == "string"
            assert returned[0]["native_cells"][5]["string_value"] == "X"
            assert any(error["code"] == "invalid_overlap" for error in result["result"]["projection_errors"])
        if b'[[1, 17,' in body:
            assert returned[0]["native_cells"][1]["number_value"] == 17
            assert any(error["code"] == "invalid_term" for error in result["result"]["projection_errors"])
        if b"valid legacy" in body:
            assert returned[0]["native_width"] == 7
            assert returned[0]["statistics"]["old_p_value"]["state"] == "missing"
            assert "projection_errors" not in result["result"]
        if b"valid nine" in body:
            assert returned[0]["native_width"] == 9 and "projection_errors" not in result["result"]


def test_original_frozen_configuration_survives_current_service_changes(harness):
    h = harness
    _, snapshot = engineered_protocol(h, table_body([]))
    h.service.configuration = configuration("speedrichr_v1", base="https://changed.invalid/api")
    prepared = h.service.prepare(RESULT, request(), {}, scope=h.scope, previous_events=[], selector=SELECTOR)
    assert prepared["configuration"] is None and prepared["cache_original"]
    assert h.service.decode(prepared, snapshot)["facts"]["protocol_profile"] == "standard_enrichr_v1"
    assert h.service.publish(request(), SELECTOR, snapshot, h.scope, "old-cfg")["status"] == "completed"
    with pytest.raises(ValueError, match="configuration_profile_conflict"):
        h.service.prepare(QUERY, request(), {}, scope=h.scope, previous_events=[])
    with pytest.raises(ValueError, match="stage_invalid"):
        h.service.invoke(prepared)
    assert h.client.calls == []


@pytest.mark.parametrize("change", ["bytes", "status_numeric_alias"])
def test_final_protocol_conflicts_never_publish_substituted_bytes(harness, change):
    h = harness
    main, snapshot = engineered_protocol(h, table_body([]))
    if change == "bytes":
        altered = replace(snapshot, content=b'{"foreign":[]}')
    else:
        transport = deepcopy(snapshot.transport)
        assert type(transport["status"]) is int and transport["status"] == 200
        transport["status"] = 200.0
        altered = replace(snapshot, transport=transport)
    with pytest.raises(ValueError, match="final_response_conflict"):
        h.service.decode(main, altered)
    before = h.store.count("source")
    with pytest.raises(ValueError, match="final_response_conflict"):
        h.service.publish(request(), SELECTOR, altered, h.scope, "foreign")
    assert h.store.count("source") == before


@pytest.fixture
def local_http():
    counts = {"redirect": 0, "target": 0, "large": 0}
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path.endswith("/addList"):
                counts["redirect"] += 1
                body = b"retained redirect body"
                self.send_response(302)
                self.send_header("Location", "/target")
            else:
                counts["target"] += 1
                body = b"should not follow"
                self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def do_GET(self):
            key = "large" if self.path == "/large" else "target"
            counts[key] += 1
            body = b"0123456789"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *_):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port), counts
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()


def test_actual_loopback_redirect_is_retained_without_target_request(local_http, monkeypatch):
    base, counts = local_http
    client = PublicClients(ncbi_email=None, timeout=9)
    service = EnrichrService(SimpleNamespace(clients=client), configuration(base=base + "/Enrichr"))
    main = service.prepare(QUERY, request(), {}, scope=None, previous_events=[])
    stage = service.protocol_request(main, stage=0, retained_responses=[])
    build = urllib.request.build_opener
    actual_timeouts = []
    def observed_builder(*handlers):
        opener = build(*handlers)
        class Observed:
            def open(self, selected, *, timeout):
                actual_timeouts.append(timeout)
                return opener.open(selected, timeout=timeout)
        return Observed()
    monkeypatch.setattr(urllib.request, "build_opener", observed_builder)
    with pytest.raises(AcquisitionError) as caught:
        service.invoke(stage)
    assert caught.value.code == "provider_http_302"
    assert caught.value.snapshot.content == b"retained redirect body"
    assert caught.value.snapshot.request == stage and caught.value.snapshot.transport["body_complete"]
    assert counts == {"redirect": 1, "target": 0, "large": 0} and actual_timeouts == [0.75]
    assert caught.value.snapshot.transport["request_policy"] == {
        "timeout_seconds": 0.75, "automatic_redirects": False}


def test_actual_loopback_bounded_reader_preserves_prefix(local_http):
    base, counts = local_http
    client = PublicClients(ncbi_email=None)
    with pytest.raises(AcquisitionError) as caught:
        client._http("enrichr", base + "/large", {}, "application/json", max_bytes=4,
                     timeout_seconds=0.75, follow_redirects=False)
    assert caught.value.code == "provider_response_byte_limit"
    assert caught.value.snapshot.content == b"0123"
    assert caught.value.snapshot.transport["body_complete"] is False
    assert caught.value.snapshot.transport["observed_body_bytes"] == 5
    assert counts == {"redirect": 0, "target": 0, "large": 1}


def test_legacy_http_default_keeps_urlopen_timeout_and_metadata(monkeypatch):
    calls = []
    class Response(io.BytesIO):
        status = 200
        headers = {"Content-Type": "application/json"}
        def geturl(self):
            return "https://example.invalid/legacy?q=literal"
    def opened(selected, *, timeout):
        calls.append((selected.full_url, timeout))
        return Response(b'{"legacy":true}')
    def forbidden(*args, **kwargs):
        raise AssertionError("legacy path must retain urlopen")
    monkeypatch.setattr(urllib.request, "urlopen", opened)
    monkeypatch.setattr(urllib.request, "build_opener", forbidden)
    result = PublicClients(ncbi_email=None, timeout=7)._http("legacy",
        "https://example.invalid/legacy", {"q": "literal"}, "application/json")
    assert calls == [("https://example.invalid/legacy?q=literal", 7)]
    assert result.content == b'{"legacy":true}' and result.request == {"q": "literal"}
    assert result.transport == {"status": 200, "representation": "http_response_bytes",
        "headers": {"content-type": "application/json"},
        "effective_url": "https://example.invalid/legacy?q=literal",
        "header_items": [("Content-Type", "application/json")],
        "request": {"method": "GET", "url": "https://example.invalid/legacy?q=literal",
            "headers": {"User-agent": "gene-annotation-episode/0.2", "Accept": "application/json"}}}
