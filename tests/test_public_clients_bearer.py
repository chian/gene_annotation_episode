"""Engineered HTTPS transport; actual shared HTTP capture and Source publication."""
from collections import deque
from dataclasses import asdict
from email.message import Message
import hashlib
from http.client import IncompleteRead
import io
import json
from types import SimpleNamespace
import traceback
import urllib.error
import urllib.request
from urllib.response import addinfourl

import pytest

from gene_annotation_episode import acquisition
from gene_annotation_episode.acquisition import AcquisitionError, PublicClients
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


URL = "https://selected.example.test/graphql"
ADDRESS = URL + "?page=2"
TOKEN = "engineering-opaque.bearer_9Q+7/=="
AUTHENTICATION = {"scheme": "Bearer", "credential_value_retained": False}
NOW = "2026-11-01T12:00:00+00:00"
RAW = b'{"native":[0,null,0.0000],"next":"literal"}\n'


def forbidden(*args, **kwargs):
    raise AssertionError("real network or unexpected response construction")


@pytest.fixture
def https(monkeypatch):
    """Only the HTTPS handler is engineered; urllib owns request/error/redirect handling."""
    pending, calls = deque(), []

    class Interrupted(io.BytesIO):
        def read(self, size=-1):
            raise IncompleteRead(self.getvalue(), 7)

    class SelectedHTTPS(urllib.request.HTTPSHandler):
        def https_open(self, request):
            calls.append(request)
            assert pending, "unexpected additional HTTP request"
            item = pending.popleft()
            if isinstance(item, Exception):
                raise item
            raw, status, extra, effective, interrupted, message = item
            headers = Message()
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(raw) + (7 if interrupted else 0))
            for key, value in extra:
                if key in headers:
                    del headers[key]
                headers[key] = value
            stream = Interrupted(raw) if interrupted else io.BytesIO(raw)
            response = addinfourl(stream, headers, effective or request.full_url, status)
            response.msg = message
            return response

    original = urllib.request.build_opener
    monkeypatch.setattr(urllib.request, "build_opener",
        lambda *handlers: original(SelectedHTTPS(), *handlers))
    monkeypatch.setattr(urllib.request, "urlopen",
        lambda request, *, timeout: original(SelectedHTTPS()).open(request, timeout=timeout))
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr(acquisition, "_now", lambda: NOW)

    def respond(raw=RAW, *, status=200, headers=(), effective=None, interrupted=False,
                message="engineered response"):
        pending.append((raw, status, headers, effective, interrupted, message))

    return SimpleNamespace(respond=respond, fail=pending.append, calls=calls, pending=pending)


def selected(client, **options):
    return client._http("engineering", URL, {"page": 2}, "application/json",
        max_bytes=4096, follow_redirects=False, bearer_token=TOKEN, **options)


def assert_not_retained(value):
    encoded = json.dumps(value, ensure_ascii=False, default=str)
    assert TOKEN not in encoded
    assert "<redacted>" not in encoded


@pytest.mark.parametrize("kind", ["complete", "http_error", "limited", "interrupted"])
def test_actual_wire_header_and_literal_captured_source_exclude_credential(tmp_path, https, kind):
    client = PublicClients(ncbi_email=None, timeout=3)
    if kind == "limited":
        # Choose the explicit cap directly, without a second request.
        https.respond()
        call = lambda: client._http("engineering", URL, {"page": 2}, "application/json",
            max_bytes=9, follow_redirects=False, bearer_token=TOKEN)
        expected, code = RAW[:9], "provider_response_byte_limit"
    else:
        https.respond(status=503 if kind == "http_error" else 200,
            interrupted=kind == "interrupted")
        call = lambda: selected(client)
        expected = RAW
        code = {"http_error": "provider_http_503", "interrupted": "provider_body_capture_failed"}.get(kind)
    if code is None:
        snapshot = call()
    else:
        with pytest.raises(AcquisitionError) as caught:
            call()
        error = caught.value
        assert error.code == code and error.phase == "http_response"
        assert error.__cause__ is None
        snapshot = error.snapshot
    assert len(https.calls) == 1 and not https.pending
    wire = https.calls[0]
    assert wire.full_url == ADDRESS and wire.get_method() == "GET"
    assert wire.get_header("Authorization") == "Bearer " + TOKEN
    assert snapshot.content == expected
    retained = snapshot.transport["request"]
    assert retained["url"] == ADDRESS and retained["method"] == "GET"
    assert retained["authentication"] == AUTHENTICATION
    assert all(key.lower() != "authorization" for key in retained["headers"])
    assert retained["headers"] == {key: value for key, value in wire.header_items()
        if key.lower() != "authorization"}
    assert snapshot.transport["request_policy"] == {"timeout_seconds": 3, "automatic_redirects": False}
    if kind == "limited":
        assert snapshot.transport["observed_body_bytes"] == 10
        assert snapshot.transport["retained_body_bytes"] == 9
        assert snapshot.transport["declared_body_bytes"] == len(RAW)
    elif kind == "interrupted":
        assert snapshot.transport["body_capture_error"] == "IncompleteRead"
        assert snapshot.transport["observed_body_bytes"] == len(RAW)
        assert snapshot.transport["declared_body_bytes"] == len(RAW) + 7
    assert snapshot.transport["body_complete"] is (kind in {"complete", "http_error"})
    assert_not_retained(asdict(snapshot))
    with Store(tmp_path / "store") as store:
        registry = ToolRegistry(store, clients=client)
        token = registry._publications.set([])
        try:
            with store.transaction():
                source = registry._source("engineering.http.bearer", None, snapshot=snapshot,
                    software_version="engineered-transport-only")
        finally:
            registry._publications.reset(token)
        assert store.get_artifact(source["artifact_ref"]) == expected
        control_bytes = store.get_artifact(source["request_ref"])
        assert TOKEN.encode() not in control_bytes
        control = json.loads(control_bytes)
        assert control == json.loads(json.dumps({"request": snapshot.request, "transport": snapshot.transport}))
        assert_not_retained(source)
        assert_not_retained(control)
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 0
        assert store.count("observation") == 0


def test_authenticated_json_post_preserves_selected_body_and_actual_added_headers(https):
    query = {"query": "query Selected { literal }", "variables": {"start": 0}}
    https.respond()
    snapshot = selected(PublicClients(ncbi_email=None, timeout=3), json_body=query)
    assert len(https.calls) == 1
    wire = https.calls[0]
    assert wire.get_method() == "POST" and wire.data == json.dumps(query).encode()
    assert wire.get_header("Authorization") == "Bearer " + TOKEN
    assert snapshot.request == query
    assert snapshot.transport["request"]["headers"] == {
        "Host": "selected.example.test", "Content-length": str(len(wire.data)),
        "User-agent": "gene-annotation-episode/0.2", "Accept": "application/json", "Content-type": "application/json"}
    assert snapshot.transport["request"]["authentication"] == AUTHENTICATION
    assert_not_retained(asdict(snapshot))


@pytest.mark.parametrize("token", ["Bearer", "null"])
def test_fixed_authentication_words_are_not_misclassified_as_response_echoes(https, token):
    raw = b'{"ok":1}'
    https.respond(raw)
    snapshot = PublicClients(ncbi_email=None, timeout=3)._http("engineering", URL, {}, "application/json",
        max_bytes=4096, follow_redirects=False, bearer_token=token)
    assert snapshot.content == raw
    assert snapshot.transport["request"]["authentication"] == AUTHENTICATION
    assert "Authorization" not in snapshot.transport["request"]["headers"]


def test_authenticated_redirect_is_one_captured_response_without_second_request(https):
    raw = b"literal native redirect response"
    https.respond(raw, status=302, headers=[("Location", "https://unselected.example.test/next")])
    with pytest.raises(AcquisitionError) as caught:
        selected(PublicClients(ncbi_email=None, timeout=3))
    assert len(https.calls) == 1 and not https.pending
    error = caught.value
    assert error.code == "provider_http_302" and error.snapshot.content == raw
    assert error.snapshot.transport["status"] == 302
    assert error.snapshot.transport["request"]["authentication"] == AUTHENTICATION
    assert_not_retained(asdict(error.snapshot))


@pytest.mark.parametrize("case", ["body", "error_body", "header", "error_header", "effective_uri",
    "http_message", "connection", "timeout", "unexpected", "partial_body", "limited_body"])
def test_literal_echo_rejected_before_snapshot_without_mutating_native_data(https, monkeypatch, case):
    client = PublicClients(ncbi_email=None, timeout=3)
    raw = ("literal response " + TOKEN).encode()
    options = {}
    if case == "body": https.respond(raw)
    elif case == "error_body": https.respond(raw, status=503)
    elif case == "header": https.respond(headers=[("X-Native-Echo", TOKEN)])
    elif case == "error_header": https.respond(status=503, headers=[("X-Native-Echo", TOKEN)])
    elif case == "effective_uri": https.respond(effective=ADDRESS + "&echo=" + TOKEN)
    elif case == "http_message": https.respond(status=503, message=TOKEN)
    elif case == "connection": https.fail(urllib.error.URLError(TOKEN))
    elif case == "timeout": https.fail(TimeoutError(TOKEN))
    elif case == "unexpected": https.fail(RuntimeError(TOKEN))
    elif case == "partial_body": https.respond(raw, interrupted=True)
    else:
        https.respond(raw + b" remaining bytes")
        options = {"max_bytes": len(raw)}
    monkeypatch.setattr(acquisition, "SourceSnapshot", forbidden)
    with pytest.raises(AcquisitionError) as caught:
        client._http("engineering", URL, {"page": 2}, "application/json",
            max_bytes=options.get("max_bytes", 4096), follow_redirects=False, bearer_token=TOKEN)
    error = caught.value
    assert len(https.calls) == 1 and not https.pending
    assert error.code == "provider_authentication_echo_rejected"
    assert error.snapshot is None and error.__cause__ is None and error.__suppress_context__
    assert error.diagnostic["authentication"] == AUTHENTICATION
    assert set(error.diagnostic) <= {"authentication", "http_status", "captured_body_bytes",
        "captured_body_sha256", "observed_body_bytes", "exception_type", "message_retained"}
    if case in {"body", "error_body", "partial_body", "limited_body"}:
        assert error.diagnostic["captured_body_bytes"] == len(raw)
        assert error.diagnostic["captured_body_sha256"] == hashlib.sha256(raw).hexdigest()
    assert_not_retained(error.diagnostic)
    assert TOKEN not in "".join(traceback.format_exception(error))


@pytest.mark.parametrize("error,code", [(urllib.error.URLError("unretained connection detail"), "provider_connection_failed"),
    (TimeoutError("unretained timeout detail"), "provider_request_timeout"),
    (RuntimeError("unretained unexpected detail"), "provider_authenticated_request_failed")])
def test_authenticated_error_diagnostics_do_not_retain_messages_or_exception_chains(https, error, code):
    https.fail(error)
    with pytest.raises(AcquisitionError) as caught:
        selected(PublicClients(ncbi_email=None, timeout=3))
    result = caught.value
    assert result.code == code and result.snapshot is None and result.__cause__ is None
    assert result.diagnostic["message_retained"] is False
    assert result.diagnostic["authentication"] == AUTHENTICATION
    assert "unretained" not in json.dumps(result.diagnostic)
    assert "unretained" not in "".join(traceback.format_exception(result))
    assert len(https.calls) == 1


@pytest.mark.parametrize("token", ["", " ", "a b", "a\tb", "a\rb", "a\nb", "a\r\nInjected: x",
    "a\x00b", "a\x7fb", "\u0080", "\U0001f511", False, 1, b"opaque"])
def test_invalid_bearer_is_rejected_before_transport(https, token):
    with pytest.raises(ValueError, match="^invalid_http_bearer_token$"):
        PublicClients(ncbi_email=None)._http("engineering", URL, {}, "application/json",
            max_bytes=99, follow_redirects=False, bearer_token=token)
    assert https.calls == []


@pytest.mark.parametrize("url,options,code", [
    ("http://selected.example.test/graphql", {}, "authenticated_http_requires_https"),
    ("https://user:pass@selected.example.test/graphql", {}, "authenticated_http_requires_https"),
    (URL + "#fragment", {}, "authenticated_http_requires_https"),
    (URL, {"follow_redirects": True}, "authenticated_http_redirects_forbidden"),
    (URL, {"max_bytes": None}, "authenticated_http_byte_limit_required")])
def test_authenticated_policy_is_explicit_before_transport(https, url, options, code):
    with pytest.raises(ValueError, match="^" + code + "$"):
        PublicClients(ncbi_email=None)._http("engineering", url, {}, "application/json",
            bearer_token=TOKEN, **{"max_bytes": 99, "follow_redirects": False, **options})
    assert https.calls == []


@pytest.mark.parametrize("case", ["json_value", "json_key", "json_nested", "json_numeric_scalar", "json_null_scalar",
    "raw_body", "params_value", "params_key", "params_nested", "service", "url", "accept", "content_type"])
def test_literal_request_conflict_is_rejected_before_request_or_transport(https, monkeypatch, case):
    service, url, params, token = "engineering", URL, {"page": 2}, TOKEN
    options = {}
    if case == "json_value": options["json_body"] = {"query": TOKEN}
    elif case == "json_key": options["json_body"] = {TOKEN: "literal"}
    elif case == "json_nested": options["json_body"] = {"variables": [{"literal": TOKEN}]}
    elif case == "json_numeric_scalar":
        token = "12345"
        options["json_body"] = {"selected": [12345]}
    elif case == "json_null_scalar":
        token = "null"
        options["json_body"] = {"selected": [None]}
    elif case == "raw_body": options.update(body=b"literal=" + TOKEN.encode(), content_type="application/octet-stream")
    elif case == "params_value": params = {"selected": TOKEN}
    elif case == "params_key": params = {TOKEN: "literal"}
    elif case == "params_nested": params = {"selected": [{"literal": TOKEN}]}
    elif case == "service": service = TOKEN
    elif case == "url": url += "/" + TOKEN
    elif case == "accept": options["accept"] = TOKEN
    else: options.update(body=b"literal", content_type=TOKEN)
    monkeypatch.setattr(urllib.request, "Request", forbidden)
    monkeypatch.setattr(acquisition, "SourceSnapshot", forbidden)
    with pytest.raises(ValueError, match="^http_bearer_request_conflict$") as caught:
        PublicClients(ncbi_email=None)._http(service, url, params, "application/json",
            max_bytes=4096, follow_redirects=False, bearer_token=token, **options)
    assert str(caught.value) == "http_bearer_request_conflict"
    assert token not in str(caught.value)
    assert https.calls == [] and not https.pending


@pytest.mark.parametrize("bounded", [False, True])
def test_no_auth_complete_snapshot_matches_literal_original_envelope(https, bounded):
    client = PublicClients(ncbi_email=None, timeout=3)
    options = {"max_bytes": 99, "timeout_seconds": 5, "follow_redirects": False} if bounded else {}
    expected_transport = {"status": 200, "representation": "http_response_bytes",
        "headers": {"content-type": "application/json"}, "effective_url": ADDRESS,
        "header_items": [("Content-Type", "application/json"), ("Content-Length", str(len(RAW)))],
        "request": {"method": "GET", "url": ADDRESS, "headers": {
            "Host": "selected.example.test", "User-agent": "gene-annotation-episode/0.2", "Accept": "application/json"}}}
    if bounded:
        expected_transport.update(request_policy={"timeout_seconds": 5, "automatic_redirects": False},
            body_complete=True, response_byte_limit=99, observed_body_bytes=len(RAW),
            retained_body_bytes=len(RAW), declared_body_bytes=len(RAW))
    expected = {"service": "engineering", "url": URL, "request": {"page": 2}, "retrieved_at": NOW,
        "content": RAW, "media_type": "application/json", "transport": expected_transport}
    for explicit_none in (False, True):
        https.respond()
        snapshot = client._http("engineering", URL, {"page": 2}, "application/json",
            **options, **({"bearer_token": None} if explicit_none else {}))
        assert asdict(snapshot) == expected
        assert https.calls[-1].get_header("Authorization") is None
    assert len(https.calls) == 2 and not https.pending


@pytest.mark.parametrize("representation", ["json", "bytes"])
def test_no_auth_post_snapshot_matches_literal_original_body_envelope(https, representation):
    query = {"selected": [0, None]}
    body = json.dumps(query).encode() if representation == "json" else b"native=literal&n=0"
    options = {"json_body": query} if representation == "json" else {"body": body, "content_type": "application/x-www-form-urlencoded"}
    https.respond()
    snapshot = PublicClients(ncbi_email=None, timeout=3)._http("engineering", URL, {"page": 2}, "application/json", **options)
    request = {"method": "POST", "url": ADDRESS, "headers": {
        "Host": "selected.example.test", "Content-length": str(len(body)),
        "User-agent": "gene-annotation-episode/0.2", "Accept": "application/json",
        "Content-type": "application/json" if representation == "json" else "application/x-www-form-urlencoded"}}
    if representation == "bytes":
        request.update(body_base64="bmF0aXZlPWxpdGVyYWwmbj0w", body_sha256=hashlib.sha256(body).hexdigest())
    assert asdict(snapshot) == {"service": "engineering", "url": URL,
        "request": query if representation == "json" else {"page": 2}, "retrieved_at": NOW,
        "content": RAW, "media_type": "application/json", "transport": {
            "status": 200, "representation": "http_response_bytes", "headers": {"content-type": "application/json"},
            "effective_url": ADDRESS, "header_items": [("Content-Type", "application/json"), ("Content-Length", str(len(RAW)))],
            "request": request}}
    assert len(https.calls) == 1 and https.calls[0].data == body


def test_no_auth_http_error_snapshot_and_diagnostics_match_original(https):
    https.respond(status=503, headers=[("Retry-After", "7")])
    with pytest.raises(AcquisitionError) as caught:
        PublicClients(ncbi_email=None, timeout=3)._http("engineering", URL, {"page": 2}, "application/json")
    error = caught.value
    assert error.code == "provider_http_503" and error.phase == "http_response" and error.retry_after == 7.0
    assert error.diagnostic is None and isinstance(error.__cause__, urllib.error.HTTPError)
    assert asdict(error.snapshot) == {"service": "engineering", "url": ADDRESS, "request": {"page": 2},
        "retrieved_at": NOW, "content": RAW, "media_type": "application/json", "transport": {
            "status": 503, "representation": "http_error_response_bytes",
            "headers": {"content-type": "application/json", "content-length": str(len(RAW)), "retry-after": "7"},
            "header_items": [("Content-Type", "application/json"), ("Content-Length", str(len(RAW))), ("Retry-After", "7")],
            "request": {"method": "GET", "url": ADDRESS, "headers": {
                "Host": "selected.example.test", "User-agent": "gene-annotation-episode/0.2", "Accept": "application/json"}},
            "body_complete": True}}


@pytest.mark.parametrize("error,code,message", [(urllib.error.URLError("original reason"), "provider_connection_failed", "<urlopen error original reason>"),
    (TimeoutError("original timeout"), "provider_request_timeout", "original timeout")])
def test_no_auth_exception_message_and_cause_remain_literal(https, error, code, message):
    https.fail(error)
    with pytest.raises(AcquisitionError) as caught:
        PublicClients(ncbi_email=None)._http("engineering", URL, {}, "application/json")
    result = caught.value
    assert result.code == code and result.phase == "http_request" and result.snapshot is None
    assert result.diagnostic == {"exception_type": type(error).__name__, "message": message}
    assert result.__cause__ is error


def test_no_auth_default_still_follows_original_redirect_policy(https):
    destination = "https://redirect.example.test/native"
    https.respond(b"redirect bytes", status=302, headers=[("Location", destination)])
    https.respond()
    snapshot = PublicClients(ncbi_email=None, timeout=3)._http("engineering", URL, {}, "application/json")
    assert [request.full_url for request in https.calls] == [URL, destination]
    assert snapshot.url == URL and snapshot.content == RAW
    assert snapshot.transport["effective_url"] == destination
    assert "request_policy" not in snapshot.transport
    assert "authentication" not in snapshot.transport["request"]
