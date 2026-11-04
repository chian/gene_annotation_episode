"""Engineered ordinary SCREEN acquisition; no real key or service requests.

The actual bounded HTTP client uses an in-memory HTTPS handler. Registry tests
use real Store/actions/receipts, without model calls, children or invented SQL
completion. Native response examples are engineered observations, not evidence
of a current SCREEN service population or release.
"""
import asyncio
import base64
from copy import deepcopy
from dataclasses import replace
from email.message import Message
import hashlib
import io
import json
from types import SimpleNamespace
import urllib.error
import urllib.request
from urllib.response import addinfourl

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients
from gene_annotation_episode import screen_tools as screen
from gene_annotation_episode.communication import validate_closed_schema, validate_form
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.waiting import validate_pending
from gene_annotation_episode.runtime import ActionFailure, Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


KEY = "engineered-private-SCREEN-token-not-a-credential"
ACCESSIONS = {"assembly": "grch38", "accessions": ["EH38E1310345", "EH38E1310345"],
    "coordinates": None, "fields": list(screen.FIELDS), "max_bytes": 65536}
COORDINATES = {**ACCESSIONS, "accessions": None,
    "coordinates": [{"chromosome": "chr1", "start": 1000000, "end": 1001000}]}
ROW = b'{"accession":"EH38E1310345","chromosome":null,"start":1000000,"stop":1001000,"ccre_group":"dELS","atac_max_zscore":0.000,"ctcf_max_zscore":-1e-9999,"dnase_max_zscore":null,"h3k27ac_max_zscore":2.50,"h3k4me3_max_zscore":0,"nearestgenes":[null,{"distance":-5,"gene":"native-gene-label"}]}'
DATA = b'{"data":{"getmaxZScoresQuery":[' + ROW + b',null,' + ROW + b']},"extensions":{"native":"retained"}}'


def forbidden(*args, **kwargs):
    raise AssertionError("unselected network, key lookup, model, native program or calculation")


class NoModel:
    complete = staticmethod(forbidden)
    release = staticmethod(forbidden)


def neutral(*args, **kwargs):
    return 0


@pytest.fixture
def host(tmp_path, monkeypatch):
    http = SimpleNamespace(raw=DATA, status=200, extra_headers=[], error=None, calls=[])
    class SelectedHTTPS(urllib.request.HTTPSHandler):
        def https_open(self, request):
            http.calls.append(request)
            if http.error is not None:
                raise http.error
            headers = Message()
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(http.raw))
            for key, value in http.extra_headers:
                headers[key] = value
            response = addinfourl(io.BytesIO(http.raw), headers, request.full_url, http.status)
            response.msg = "engineered response"
            return response
    build_opener = urllib.request.build_opener
    monkeypatch.setattr(urllib.request, "build_opener", lambda *handlers: build_opener(SelectedHTTPS(), *handlers))
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    with Store(tmp_path / "store") as store:
        subject, = store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]
        resolutions = []
        def resolve():
            resolutions.append("fresh-request")
            return KEY
        client = PublicClients(ncbi_email=None, timeout=3, screen_key_resolver=resolve)
        tools = ToolRegistry(store, clients=client)
        yield SimpleNamespace(store=store, tools=tools, client=client, http=http,
            resolutions=resolutions, scope={"subject_refs": [subject]}, tmp_path=tmp_path)


def publish(host, arguments, snapshot):
    token = host.tools._publications.set([])
    try:
        with host.store.transaction():
            return screen.publish_screen_request(host.tools, arguments, snapshot)
    finally:
        host.tools._publications.reset(token)


def workflow(host):
    flow = Workflow(host.store, host.tools, NoModel(), host.tmp_path / "run", "ordinary-screen",
        forbidden, neutral, root_role="improvement", episode_binding_factories=(),
        episode_record_receipts=True, initial_known_record_refs=[])
    caller = flow.build("improvement", "existing-caller", "Acquire explicitly selected cCRE data for future analysis.", host.scope)
    return flow, caller


@pytest.mark.parametrize("arguments,selector", [(ACCESSIONS, 'accession: ["EH38E1310345","EH38E1310345"]'),
    (COORDINATES, 'coordinates: [{start: 1000000,end: 1001000,chromosome: "chr1"}]')])
def test_literal_selected_post_and_native_bytes_are_the_observed_data(host, arguments, selector):
    snapshot = screen.request_screen(host.client, arguments)
    receipt, refs = publish(host, arguments, snapshot)
    request, = host.http.calls
    query = json.loads(request.data)["query"]
    assert query == 'query { getmaxZScoresQuery(assembly: "grch38", ' + selector + ') { ' + " ".join(
        "nearestgenes { distance gene }" if field == "nearestgenes" else field for field in arguments["fields"]) + ' } }'
    assert ("coordinates:" not in query) if arguments["coordinates"] is None else ("accession:" not in query)
    assert request.full_url == screen.ROOT and request.get_method() == "POST"
    assert request.get_header("Authorization") == "Bearer " + KEY
    assert request.get_header("Content-type") == request.get_header("Accept") == "application/json"
    assert snapshot.transport["request"]["body_sha256"] == hashlib.sha256(request.data).hexdigest()
    assert base64.b64decode(snapshot.transport["request"]["body_base64"], validate=True) == request.data
    assert snapshot.transport["request_policy"] == {"timeout_seconds": 3, "automatic_redirects": False}
    assert snapshot.request == {"version": screen.REQUEST_VERSION, "arguments": arguments, "native_request": {}}
    assert host.resolutions == ["fresh-request"]
    assert receipt["acquired"] is True and refs == [receipt["source_ref"], receipt["data_ref"]]
    source = host.store.get(receipt["source_ref"])
    assert source["provider"] == screen.TOOL and source["uri"] == screen.ROOT
    assert source["accession"] is None and source["version"] is None
    assert host.store.get_artifact(receipt["data_ref"]) == DATA
    private = host.store.get_artifact(source["request_ref"])
    assert KEY.encode() not in private and KEY not in repr(snapshot)
    assert json.loads(private)["request"] == snapshot.request


def test_literal_escaping_and_field_order_never_become_caller_graphql(host):
    arguments = {**ACCESSIONS, "assembly": 'native"\\assembly', "accessions": ['opaque" ) { other } #', 'opaque" ) { other } #'],
        "fields": ["nearestgenes", "accession", "atac_max_zscore"]}
    spec = screen.screen_request_spec(arguments)
    query = json.loads(spec["body"])["query"]
    assert query == ('query { getmaxZScoresQuery(assembly: ' + json.dumps(arguments["assembly"])
        + ', accession: ' + json.dumps(arguments["accessions"], separators=(",", ":"))
        + ') { nearestgenes { distance gene } accession atac_max_zscore } }')
    assert host.http.calls == host.resolutions == []
    detached = screen.validate_screen_arguments(arguments)
    detached["fields"].reverse()
    assert arguments["fields"][0] == "nearestgenes"


@pytest.mark.parametrize("change", [
    {"accessions": None}, {"coordinates": COORDINATES["coordinates"]}, {"accessions": []},
    {"accessions": "EH38E1310345"}, {"coordinates": [], "accessions": None},
    {"coordinates": [{"chromosome": "chr1", "start": True, "end": 2}], "accessions": None},
    {"fields": []}, {"fields": ["accession", "accession"]}, {"fields": ["linkedGenesQuery"]},
    {"assembly": "bad\nassembly"}, {"max_bytes": True}, {"max_bytes": screen.MAX_BYTES + 1},
    {"query": "query { callerSelectedRoot }"},
])
def test_invalid_arguments_fail_before_key_resolution_and_http(host, change):
    with pytest.raises(ContractError, match="screen_arguments_invalid"):
        screen.request_screen(host.client, {**ACCESSIONS, **change})
    assert host.resolutions == host.http.calls == []


@pytest.mark.parametrize("timeout", [True, 0, float("inf"), "3"])
def test_invalid_timeout_precedes_even_private_key_resolution(host, timeout):
    host.client.timeout = timeout
    with pytest.raises(ContractError, match="screen_timeout_invalid"):
        screen.request_screen(host.client, ACCESSIONS)
    assert host.resolutions == host.http.calls == []


@pytest.mark.parametrize("raw,code", [
    (b'{"data":{"getmaxZScoresQuery":[]}}', None),
    (b'{"data":{"getmaxZScoresQuery":[]},"errors":[]}', None),
    (b'{"data":{"getmaxZScoresQuery":[null]}}', None),
    (b'{"data":{"getmaxZScoresQuery":null}}', "screen_native_result_unavailable"),
    (b'{"data":{}}', "screen_native_representation_invalid"),
    (b'{"data":{"getmaxZScoresQuery":{}}}', "screen_native_representation_invalid"),
    (b'{"data":{"getmaxZScoresQuery":[]},"errors":[{"message":"native partial error"}]}', "screen_graphql_errors"),
    (b'{"errors":[{"message":"native error without data"}]}', "screen_graphql_errors"),
    (b'{"data":{"getmaxZScoresQuery":[]},"errors":null}', "screen_native_representation_invalid"),
    (b'{"data":{"getmaxZScoresQuery":[],"getmaxZScoresQuery":[]}}', "screen_native_representation_invalid"),
    (b'{"data":{"getmaxZScoresQuery":[{"accession":"x","atac_max_zscore":NaN}]}}', "screen_native_representation_invalid"),
    (b'not JSON', "screen_native_representation_invalid"),
])
def test_empty_unavailable_partial_errors_and_malformed_native_are_distinct(host, raw, code):
    host.http.raw = raw
    snapshot = screen.request_screen(host.client, ACCESSIONS)
    receipt, refs = publish(host, ACCESSIONS, snapshot)
    assert receipt["acquired"] is (code is None) and receipt["failure_code"] == code
    source = host.store.get(receipt["source_ref"])
    assert host.store.get_artifact(source["artifact_ref"]) == raw
    assert refs == [source["id"], *([source["artifact_ref"]] if code is None else [])]
    assert receipt["data_ref"] == (source["artifact_ref"] if code is None else None)
    assert len(host.http.calls) == len(host.resolutions) == 1


@pytest.mark.parametrize("change", [
    {"accession": None}, {"atac_max_zscore": True},
    {"nearestgenes": [{"gene": "x", "distance": None}]}, None,
])
def test_missing_and_wrong_field_types_are_not_normalized_to_native_nulls(host, change):
    row = json.loads(ROW)
    if change is None:
        row.pop("stop")
    else:
        row.update(change)
    host.http.raw = json.dumps({"data": {"getmaxZScoresQuery": [row]}}).encode()
    receipt, _ = publish(host, ACCESSIONS, screen.request_screen(host.client, ACCESSIONS))
    assert receipt["failure_code"] == "screen_native_representation_invalid"


@pytest.mark.parametrize("path,value,code", [
    (("request", "method"), "GET", "screen_selected_request_mismatch"),
    (("request", "body_sha256"), "0" * 64, "screen_selected_request_mismatch"),
    (("request", "body_base64"), "e30=", "screen_selected_request_mismatch"),
    (("request_policy", "timeout_seconds"), 4, "screen_transfer_policy_mismatch"),
    (("request_policy", "automatic_redirects"), True, "screen_transfer_policy_mismatch"),
    (("response_byte_limit",), 65535, "screen_transfer_policy_mismatch"),
    (("body_complete",), None, "screen_capture_incomplete"),
    (("observed_body_bytes",), 0, "screen_capture_identity_mismatch"),
])
def test_contradictory_observed_post_or_capture_is_retained_but_never_acquired(host, path, value, code):
    snapshot = screen.request_screen(host.client, ACCESSIONS)
    transport = deepcopy(snapshot.transport)
    target = transport
    for name in path[:-1]:
        target = target[name]
    target[path[-1]] = value
    receipt, refs = publish(host, ACCESSIONS, replace(snapshot, transport=transport))
    assert receipt["failure_code"] == code and refs == [receipt["source_ref"]]
    assert host.store.get_artifact(host.store.get(receipt["source_ref"])["artifact_ref"]) == DATA


@pytest.mark.parametrize("status,headers,code", [
    (503, [], "screen_http_not_successful"),
    (302, [("Location", "https://example.invalid/unselected")], "screen_http_not_successful"),
    (206, [("Content-Range", "bytes 0-1/100")], "screen_partial_response"),
    (200, [("Content-Encoding", "gzip")], "screen_content_encoding_unsupported"),
])
def test_actual_shared_http_failures_keep_prefix_without_follow_decode_or_second_post(host, status, headers, code):
    host.http.status, host.http.extra_headers = status, headers
    snapshot = screen.request_screen(host.client, ACCESSIONS)
    receipt, refs = publish(host, ACCESSIONS, snapshot)
    assert receipt["failure_code"] == code and refs == [receipt["source_ref"]]
    assert len(host.http.calls) == 1 and snapshot.content == DATA


def test_byte_limit_retains_only_actual_prefix_with_no_data_grant(host):
    arguments = {**ACCESSIONS, "max_bytes": 17}
    snapshot = screen.request_screen(host.client, arguments)
    receipt, refs = publish(host, arguments, snapshot)
    assert snapshot.content == DATA[:17] and snapshot.transport["observed_body_bytes"] == 18
    assert receipt["failure_code"] == "screen_capture_incomplete" and refs == [receipt["source_ref"]]
    assert host.store.get_artifact(host.store.get(receipt["source_ref"])["artifact_ref"]) == DATA[:17]


@pytest.mark.parametrize("key,code", [(None, "screen_credential_unavailable"), ("", "screen_credential_invalid"),
    ("bad key", "screen_credential_invalid"), (42, "screen_credential_invalid")])
def test_private_key_unavailable_or_invalid_has_no_request_or_snapshot(host, key, code):
    baseline_sources = host.store.count("source")
    host.client._screen_key_resolver = lambda: key
    with pytest.raises(AcquisitionError, match=code) as caught:
        screen.request_screen(host.client, ACCESSIONS)
    assert caught.value.snapshot is None and host.http.calls == []
    assert host.store.count("source") == baseline_sources


def test_private_resolver_failure_has_no_secret_exception_context_or_default_lookup(host, monkeypatch):
    def private_failure():
        raise RuntimeError(KEY)
    host.client._screen_key_resolver = private_failure
    with pytest.raises(AcquisitionError, match="screen_credential_resolution_failed") as caught:
        screen.request_screen(host.client, ACCESSIONS)
    assert caught.value.__context__ is None and caught.value.__cause__ is None
    assert KEY not in str(caught.value) and KEY not in repr(caught.value.__dict__)
    monkeypatch.setenv("SCREEN_API_KEY", KEY)
    client = PublicClients(ncbi_email=None)
    with pytest.raises(AcquisitionError, match="screen_credential_unavailable"):
        screen.request_screen(client, ACCESSIONS)
    with pytest.raises(ValueError, match="invalid_screen_key_resolver"):
        PublicClients(ncbi_email=None, screen_key_resolver=KEY)
    assert host.http.calls == []


@pytest.mark.parametrize("where", ["body", "header", "connection", "selected_input"])
def test_shared_bearer_echo_rejection_never_publishes_unsafe_snapshot(host, where):
    baseline_sources = host.store.count("source")
    arguments = deepcopy(ACCESSIONS)
    if where == "body":
        host.http.raw = KEY.encode()
    elif where == "header":
        host.http.extra_headers = [("X-Native", KEY)]
    elif where == "connection":
        host.http.error = urllib.error.URLError(KEY)
    else:
        arguments["assembly"] = KEY
    with pytest.raises(AcquisitionError, match="provider_authentication_echo_rejected") as caught:
        screen.request_screen(host.client, arguments)
    assert caught.value.snapshot is None and KEY not in str(caught.value)
    assert KEY not in repr(caught.value.diagnostic) and host.store.count("source") == baseline_sources
    assert len(host.http.calls) == (0 if where == "selected_input" else 1)


def test_unexpected_late_validation_error_still_has_actual_source_prefix(host, monkeypatch):
    snapshot = screen.request_screen(host.client, ACCESSIONS)
    def broken(*args):
        raise RuntimeError("engineered late validation")
    monkeypatch.setattr(screen, "_representation_failure", broken)
    published = []
    token = host.tools._publications.set(published)
    try:
        with pytest.raises(RuntimeError, match="engineered late validation"):
            screen.publish_screen_request(host.tools, ACCESSIONS, snapshot)
    finally:
        host.tools._publications.reset(token)
    source, = [host.store.get(ref) for ref in published if host.store.get(ref).get("record_type") == "source"]
    assert host.store.get_artifact(source["artifact_ref"]) == DATA


@pytest.mark.parametrize("mode", ["success", "graphql_error", "no_response", "missing_key"])
def test_actual_ordinary_step_receipt_authority_and_keyless_cache_without_new_work(host, monkeypatch, mode):
    if mode == "graphql_error":
        host.http.raw = b'{"data":{"getmaxZScoresQuery":[]},"errors":[{"message":"native error"}]}'
    elif mode == "no_response":
        host.http.error = urllib.error.URLError("engineered unavailable service")
    elif mode == "missing_key":
        host.client._screen_key_resolver = None
    flow, caller = workflow(host)
    baseline = set(flow.receipts.known(caller.source.episode_id))
    action = {"kind": "tool", "tool": screen.TOOL, "arguments": deepcopy(ACCESSIONS)}
    monkeypatch.setattr(host.tools, "_sequence_worker_async", forbidden)
    monkeypatch.setattr(host.store, "commit_reasoning", forbidden)
    if mode in {"no_response", "missing_key"}:
        with pytest.raises(ActionFailure):
            asyncio.run(caller.source.execute(action, 0))
    else:
        asyncio.run(caller.source.execute(action, 0))
    outcome = deepcopy(caller.source.last_outcome)
    receipt = screen.validate_screen_receipt(outcome["result"])
    expected_code = {"success": None, "graphql_error": "screen_graphql_errors",
        "no_response": "provider_connection_failed", "missing_key": "screen_credential_unavailable"}[mode]
    assert receipt["failure_code"] == expected_code and receipt["acquired"] is (mode == "success")
    refs = outcome["record_refs"]
    assert set(flow.receipts.known(caller.source.episode_id)) == baseline | set(refs)
    resolver = flow.resolver(host.scope, source=caller.source)
    assert validate_form(receipt, screen.screen_receipt_schema(), resolver) == receipt
    if receipt["source_ref"] is not None:
        source = host.store.get(receipt["source_ref"])
        assert refs == [source["id"], *([source["artifact_ref"]] if mode == "success" else [])]
        assert resolver(source["id"], "source") is True
        assert resolver(source["artifact_ref"], "artifact") is (mode == "success")
        assert resolver(source["request_ref"], "artifact") is False
        assert KEY.encode() not in host.store.get_artifact(source["request_ref"])
    else:
        assert refs == [] and receipt["data_ref"] is None
    assert len(host.http.calls) == (0 if mode == "missing_key" else 1)
    assert host.store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 1
    assert host.store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 1
    assert host.store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 1
    for table in ("runtime_model_calls", "runtime_observations", "runtime_forms", "runtime_report_attempts"):
        assert host.store.db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
    tables = [row[0] for row in host.store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    before = {table: [tuple(row) for row in host.store.db.execute('SELECT * FROM "' + table.replace('"', '""') + '"')] for table in tables}
    stored = deepcopy(outcome)
    if "pending_work_after_action" in stored:
        validate_pending(stored.pop("pending_work_after_action"))
    host.client._screen_key_resolver = forbidden
    monkeypatch.setattr(host.client, "_http", forbidden)
    monkeypatch.setattr(host.store, "get_artifact", forbidden)
    context = flow.binding_context(caller.source)
    operation, = host.store.db.execute("SELECT * FROM tool_operations")
    with host.tools.current_invocation(context, read_received=flow.services.read_received_molecular_input,
            tool_name=screen.TOOL, arguments=ACCESSIONS, operation_key=operation["operation_key"]):
        replay = asyncio.run(host.tools.execute_async(screen.TOOL, ACCESSIONS, scope=host.scope,
            operation_key=operation["operation_key"]))
    assert replay == stored
    assert before == {table: [tuple(row) for row in host.store.db.execute('SELECT * FROM "' + table.replace('"', '""') + '"')] for table in tables}


def test_receipt_and_catalog_are_detached_closed_and_do_not_resolve_a_key(host):
    schema = screen.screen_receipt_schema()
    validate_closed_schema(schema)
    schema["properties"].clear()
    assert set(screen.screen_receipt_schema()["properties"]) == {"acquired", "source_ref", "data_ref", "failure_code"}
    contract = screen.screen_tool_contract()
    assert contract["name"] == screen.TOOL and contract["resources"] == "api"
    contract["input_schema"].clear()
    assert screen.screen_tool_contract()["input_schema"] == screen.ARGUMENTS_SCHEMA
    with pytest.raises(ContractError, match="screen_receipt_invalid"):
        screen.validate_screen_receipt({"acquired": True, "source_ref": None, "data_ref": None, "failure_code": None})
    assert host.resolutions == host.http.calls == []
