"""Engineered ENCODE acquisition controls; no live portal or scientific work.

The real bounded HTTP client and Source writer consume an in-memory HTTPS
handler. Publisher cases create no ToolOperation or fabricated completion.
Received-file selection uses a real Workflow context and receipt owner; shared
ENCODE catalogue/privacy dispatch is a separate integration requirement.
"""
from collections import deque
import asyncio
import base64
from copy import deepcopy
from dataclasses import replace
from email.message import Message
import hashlib
import io
import json
from types import SimpleNamespace
from urllib.parse import urlencode
import urllib.error
import urllib.request
from urllib.response import addinfourl

import pytest

from gene_annotation_episode import encode_tools as encode
from gene_annotation_episode import jaspar_tools as jaspar
from gene_annotation_episode.acquisition import AcquisitionError, PublicClients
from gene_annotation_episode.communication import validate_closed_schema, validate_form
from gene_annotation_episode.data_acquisition_receipts import acquisition_receipt_schema, validate_acquisition_receipt
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.runtime import ActionFailure, Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.waiting import validate_pending


SEARCH = {"operation": "search", "object_type": "File", "filters": [
    {"field": "dataset", "value": "/experiments/ENCSR000AAA/"},
    {"field": "file_format", "value": "bed"}, {"field": "file_format", "value": "bigBed"}],
    "search_term": None, "frame": "object", "limit": 10, "max_bytes": 65536}
REPORT = {**SEARCH, "operation": "report", "offset_0based": 20}
OBJECT = {"operation": "object", "object_path": "/files/ENCFF000AAA/", "frame": "object", "max_bytes": 65536}
DATA = b"chr1\t10\t20\tactual engineered native bytes\n"
FILE_ID = "/files/ENCFF000AAA/"
URL = "https://storage.example.test/advertised/native.bed?literal=one"
FILE = {"@id": FILE_ID, "@type": ["File"], "accession": "ENCFF000AAA",
    "dataset": "/experiments/ENCSR000AAA/", "replicate": "/replicates/00000000-0000-0000-0000-000000000001/",
    "file_format": "bed", "output_type": "peaks", "md5sum": hashlib.md5(DATA).hexdigest(), "file_size": len(DATA),
    "cloud_metadata": {"url": URL, "file_size": len(DATA)},
    "href": "/files/ENCFF000AAA/@@download/ENCFF000AAA.bed"}
OBJECT_BYTES = json.dumps(FILE, separators=(",", ":")).encode()
PAGE = json.dumps({"@type": ["Search"], "@graph": [FILE, FILE], "total": 27,
    "notification": "Success", "all": "/search/?type=File&limit=all",
    "native_population": {"reported": "0.0000", "unknown": None}}, separators=(",", ":")).encode()


def forbidden(*args, **kwargs):
    raise AssertionError("unselected HTTP, provider, scientific/native operation or body read")


@pytest.fixture
def http(monkeypatch):
    """Only transport I/O is engineered; PublicClients owns every HTTP envelope."""
    pending, calls = deque(), []
    class SelectedHTTPS(urllib.request.HTTPSHandler):
        def https_open(self, request):
            calls.append(request)
            assert pending, "unexpected additional GET"
            response_value = pending.popleft()
            if isinstance(response_value, Exception):
                raise response_value
            raw, status, extra = response_value
            headers = Message()
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(raw))
            for key, value in extra:
                if key in headers:
                    del headers[key]
                headers[key] = value
            response = addinfourl(io.BytesIO(raw), headers, request.full_url, status)
            response.msg = "engineered response"
            return response
    original = urllib.request.build_opener
    monkeypatch.setattr(urllib.request, "build_opener", lambda *handlers: original(SelectedHTTPS(), *handlers))
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    def respond(raw, *, status=200, headers=()):
        pending.append((raw, status, headers))
    def fail(error):
        assert isinstance(error, Exception)
        pending.append(error)
    return SimpleNamespace(respond=respond, fail=fail, calls=calls, pending=pending)


@pytest.fixture
def host(tmp_path, http):
    with Store(tmp_path / "store") as store:
        scope = {"subject_refs": store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]}
        client = PublicClients(ncbi_email=None, timeout=3)
        yield SimpleNamespace(store=store, tools=ToolRegistry(store, clients=client), client=client,
            http=http, scope=scope, tmp_path=tmp_path)


def publish(host, arguments, snapshot, *, selection=None):
    token = host.tools._publications.set([])
    try:
        with host.store.transaction():
            return encode.publish_encode_request(host.tools, arguments, snapshot, selection=selection)
    finally:
        host.tools._publications.reset(token)


def acquired_metadata(host, *, raw=OBJECT_BYTES, arguments=OBJECT, deliver=True):
    host.http.respond(raw)
    class NoModel:
        complete = staticmethod(forbidden)
        release = staticmethod(forbidden)
    def neutral(*args, **kwargs):
        return 0
    workflow = Workflow(host.store, host.tools, NoModel(), host.tmp_path / "run", "encode-received-selection",
        forbidden, neutral, root_role="improvement", episode_record_receipts=True,
        initial_known_record_refs=[])
    caller = workflow.build("improvement", "existing-caller", "Retrieve the caller-selected advertised data.", host.scope)
    # Requires the finite ENCODE ordinary dispatch. The actual runtime and
    # registry write their own action, ToolOperation, result and receipts.
    asyncio.run(caller.source.execute({"kind": "tool", "tool": encode.TOOL, "arguments": arguments}, 0))
    receipt = encode.validate_encode_receipt(caller.source.last_outcome["result"])
    assert receipt["acquired"] is True and caller.source.last_outcome["status"] == "completed"
    if not deliver:
        workflow = Workflow(host.store, host.tools, NoModel(), host.tmp_path / "unreceived-run", "encode-unreceived-selection",
            forbidden, neutral, root_role="improvement", episode_record_receipts=True, initial_known_record_refs=[])
        caller = workflow.build("improvement", "unreceived-caller", "Retrieve the caller-selected advertised data.", host.scope)
    context = workflow.binding_context(caller.source)
    arguments = {"operation": "file", "metadata_source_ref": receipt["source_ref"],
        "file_pointer": "" if arguments["operation"] == "object" else "/@graph/1",
        "file_id": FILE_ID, "max_bytes": 65536}
    return SimpleNamespace(receipt=receipt, workflow=workflow, caller=caller, arguments=arguments,
        authority=(context, workflow.services.read_received_molecular_input))


def test_exact_native_query_keys_and_repeated_filters_are_not_generated_or_collapsed():
    expected = [("type", "File"), ("dataset", "/experiments/ENCSR000AAA/"),
        ("file_format", "bed"), ("file_format", "bigBed"), ("limit", 10), ("frame", "object"), ("format", "json")]
    assert encode.encode_request_spec(SEARCH)["params"] == expected
    report = encode.encode_request_spec(REPORT)
    assert report["url"] == encode.ROOT + "/report/" and report["params"] == [*expected, ("from", 20)]
    assert "from" not in dict(encode.encode_request_spec(SEARCH)["params"])
    assert encode.encode_request_spec({**SEARCH, "search_term": "literal assay (A+B)"})["params"][4] == (
        "searchTerm", "literal assay (A+B)")
    assert encode.encode_request_spec(OBJECT)["url"] == encode.ROOT + FILE_ID


@pytest.mark.parametrize("arguments", [
    {**SEARCH, "offset_0based": 1}, {**REPORT, "offset_0based": True}, {**SEARCH, "limit": "all"},
    {**SEARCH, "limit": True}, {**SEARCH, "max_bytes": encode.MAX_METADATA_BYTES + 1},
    {**SEARCH, "filters": [{"field": "limit", "value": "all"}]},
    {**SEARCH, "filters": [{"field": "format!", "value": "html"}]},
    {**SEARCH, "filters": [{"field": "bad&field", "value": "x"}]},
    {**SEARCH, "filters": [{"field": "status", "value": "released\n"}]},
    {**SEARCH, "object_type": "File&limit=all"}, {**OBJECT, "object_path": "/files/../"},
    {**OBJECT, "object_path": "https://example.test/files/x/"},
    {**OBJECT, "object_path": "/files/x/?frame=raw"}, {**OBJECT, "object_path": "/files/x%2fy/"},
    {**OBJECT, "frame": "raw"}, {**OBJECT, "prompt": "choose anything"},
    {"operation": "file", "metadata_source_ref": "source_" + "a" * 24, "file_pointer": "/x~2y",
        "file_id": FILE_ID, "max_bytes": 100},
])
def test_invalid_public_choices_fail_before_transport(arguments):
    with pytest.raises(ContractError, match="^encode_arguments_invalid$"):
        encode.request_encode(SimpleNamespace(timeout=3, _http=forbidden), arguments)


@pytest.mark.parametrize("timeout", [None, True, 0, float("inf"), 10 ** 1000])
def test_timeout_is_explicit_positive_finite_before_http(timeout):
    with pytest.raises(ContractError, match="^encode_timeout_invalid$"):
        encode.request_encode(SimpleNamespace(timeout=timeout, _http=forbidden), SEARCH)


@pytest.mark.parametrize("arguments,raw", [(SEARCH, PAGE), (REPORT, PAGE.replace(b'Search', b'Report')), (OBJECT, OBJECT_BYTES)])
def test_actual_shared_http_source_uri_bytes_and_metadata_remain_literal(host, arguments, raw):
    host.http.respond(raw)
    snapshot = encode.request_encode(host.client, arguments)
    receipt, refs = publish(host, arguments, snapshot)
    source = host.store.get(receipt["source_ref"])
    spec = encode.encode_request_spec(arguments)
    address = spec["url"] + "?" + urlencode(spec["params"], doseq=True)
    assert len(host.http.calls) == 1 and host.http.calls[0].full_url == address
    assert snapshot.url == spec["url"] and snapshot.url != address
    assert source["uri"] == address and source["provider"] == encode.TOOL and source["version"] is None
    assert receipt == {"acquired": True, "source_ref": source["id"],
        "data_ref": "artifact_" + hashlib.sha256(raw).hexdigest(), "failure_code": None}
    assert refs == [source["id"], source["artifact_ref"]]
    assert host.store.get_artifact(receipt["data_ref"]) == raw
    control = json.loads(host.store.get_artifact(source["request_ref"]))
    assert control["transport"] == json.loads(json.dumps(snapshot.transport, allow_nan=False))
    assert control["request"]["arguments"] == arguments and control["request"]["selection"] is None
    assert control["transport"]["request_policy"] == {"timeout_seconds": 3, "automatic_redirects": False}
    assert host.store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 0
    assert host.store.count("observation") == host.store.count("annotation") == 0


@pytest.mark.parametrize("operation,status,total,graph,notification,acquired", [
    ("search", 404, 0, [], "No results found", True),
    ("report", 404, 0, [], "No results found", True),
    ("search", 404, 1, [], "No results found", False),
    ("search", 404, 0, [], "not found", False),
    ("object", 404, 0, [], "No results found", False),
    ("report", 200, 10, [], "Success", True),
])
def test_empty_native_search_and_missing_object_are_distinct(host, operation, status, total, graph, notification, acquired):
    arguments = {"search": SEARCH, "report": REPORT, "object": OBJECT}[operation]
    raw = json.dumps({"@type": ["Report" if operation == "report" else "Search"],
        "total": total, "@graph": graph, "notification": notification}).encode()
    host.http.respond(raw, status=status)
    receipt, refs = publish(host, arguments, encode.request_encode(host.client, arguments))
    assert receipt["acquired"] is acquired
    assert refs == [receipt["source_ref"], *([receipt["data_ref"]] if acquired else [])]
    if not acquired:
        assert receipt["data_ref"] is None and receipt["failure_code"] == "encode_http_not_successful"
    assert len(host.http.calls) == 1


@pytest.mark.parametrize("status,headers,expected", [
    (302, [("Location", "https://example.test/unselected")], "encode_http_not_successful"),
    (206, [("Content-Range", "bytes 0-4/100")], "encode_partial_response"),
    (200, [("Content-Encoding", "gzip")], "encode_content_encoding_unsupported"),
    (503, [], "encode_http_not_successful"),
])
def test_no_redirect_range_decoding_or_fallback_transfer(host, status, headers, expected):
    host.http.respond(PAGE, status=status, headers=headers)
    receipt, refs = publish(host, SEARCH, encode.request_encode(host.client, SEARCH))
    assert receipt["acquired"] is False and receipt["failure_code"] == expected
    assert refs == [receipt["source_ref"]] and len(host.http.calls) == 1
    assert host.store.get_artifact(host.store.get(receipt["source_ref"])["artifact_ref"]) == PAGE


def test_captured_prefix_and_original_request_contradiction_are_retained_without_relabeling(host):
    arguments = {**SEARCH, "max_bytes": 13}
    host.http.respond(PAGE)
    snapshot = encode.request_encode(host.client, arguments)
    receipt, _ = publish(host, arguments, snapshot)
    assert snapshot.content == PAGE[:13] and snapshot.transport["observed_body_bytes"] == 14
    assert receipt["failure_code"] == "encode_capture_incomplete" and receipt["data_ref"] is None
    host.http.respond(PAGE)
    snapshot = encode.request_encode(host.client, SEARCH)
    snapshot.transport["request"]["url"] = "https://example.test/not-selected"
    receipt, _ = publish(host, SEARCH, snapshot)
    source = host.store.get(receipt["source_ref"])
    assert receipt["failure_code"] == "encode_selected_request_mismatch" and source["uri"] == snapshot.url
    assert json.loads(host.store.get_artifact(source["request_ref"]))["transport"] == json.loads(json.dumps(snapshot.transport, allow_nan=False))


@pytest.mark.parametrize("raw,code", [
    (b'{"@id":"/files/OTHER/"}', "encode_object_identity_conflict"),
    (b'{"@id":"/files/ENCFF000AAA/","@id":"/files/ENCFF000AAA/"}', "encode_native_representation_invalid"),
    (b'{"@id":"/files/ENCFF000AAA/","x":NaN}', "encode_native_representation_invalid"),
    (b'\xffnative bytes', "encode_native_representation_invalid"),
])
def test_wrong_or_malformed_object_stays_captured_data_not_a_selected_success(host, raw, code):
    host.http.respond(raw)
    receipt, _ = publish(host, OBJECT, encode.request_encode(host.client, OBJECT))
    assert receipt["failure_code"] == code and receipt["acquired"] is False
    assert host.store.get_artifact(host.store.get(receipt["source_ref"])["artifact_ref"]) == raw


def test_received_exact_file_occurrence_drives_one_advertised_transfer_with_native_checksum(host):
    second = deepcopy(FILE); second["cloud_metadata"]["url"] = URL + "&occurrence=second"
    raw = json.dumps({"@type": ["Search"], "total": 2, "@graph": [FILE, second]}).encode()
    metadata = acquired_metadata(host, raw=raw, arguments=SEARCH)
    selection = encode.prepare_encode_request(host.tools, metadata.arguments, authority=metadata.authority)
    assert selection["association"]["advertised_url"] == second["cloud_metadata"]["url"]
    assert selection["association"]["file_size"] == len(DATA)
    host.http.respond(DATA, headers=[("Content-Type", "text/plain")])
    snapshot = encode.request_encode(host.client, metadata.arguments, selection=selection)
    receipt, refs = publish(host, metadata.arguments, snapshot, selection=selection)
    source = host.store.get(receipt["source_ref"])
    assert receipt["acquired"] is True and host.store.get_artifact(receipt["data_ref"]) == DATA
    assert source["uri"] == second["cloud_metadata"]["url"] and source["parent_source_refs"] == [metadata.receipt["source_ref"]]
    assert len(source["auxiliary_artifact_refs"]) == 1
    assert json.loads(host.store.get_artifact(source["auxiliary_artifact_refs"][0])) == selection
    assert source["request_ref"] not in refs and source["auxiliary_artifact_refs"][0] not in refs
    assert len(host.http.calls) == 2 and not host.http.pending
    assert host.store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 1
    assert host.store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 1
    assert host.store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 1
    for table in ("runtime_model_calls", "runtime_observations", "runtime_forms"):
        assert host.store.db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0


def test_unreceived_metadata_stops_before_controls_body_or_download(host, monkeypatch):
    metadata = acquired_metadata(host, deliver=False)
    count = len(host.http.calls)
    monkeypatch.setattr(host.store, "get_artifact", forbidden)
    with pytest.raises(ContractError, match="^encode_metadata_not_received$"):
        encode.prepare_encode_request(host.tools, metadata.arguments, authority=metadata.authority)
    assert len(host.http.calls) == count


@pytest.mark.parametrize("change", [
    {"file_pointer": "/missing"}, {"file_pointer": "/@graph/00"}, {"file_id": "/files/OTHER/"},
])
def test_explicit_pointer_and_file_identity_never_fall_back_to_a_first_match(host, change):
    metadata = acquired_metadata(host, raw=PAGE, arguments=SEARCH)
    with pytest.raises(ContractError, match="^encode_file_metadata_invalid$"):
        encode.prepare_encode_request(host.tools, {**metadata.arguments, **change}, authority=metadata.authority)
    assert len(host.http.calls) == 1


@pytest.mark.parametrize("change", [
    {"cloud_metadata": {}}, {"cloud_metadata": {"url": "http://example.test/native"}},
    {"cloud_metadata": {"url": "https://user:secret@example.test/native"}},
    {"cloud_metadata": {"url": URL, "file_size": True}},
    {"cloud_metadata": {"url": URL, "file_size": 999}},
    {"cloud_metadata": {"url": URL, "md5sum_base64": "not base64"}},
    {"restricted": True}, {"no_file_available": True},
])
def test_missing_or_conflicting_advertisement_has_no_storage_guess_or_second_get(host, change):
    metadata = acquired_metadata(host, raw=json.dumps({**FILE, **change}).encode())
    with pytest.raises(ContractError, match="^encode_file_metadata_invalid$"):
        encode.prepare_encode_request(host.tools, metadata.arguments, authority=metadata.authority)
    assert len(host.http.calls) == 1


@pytest.mark.parametrize("data,code", [(DATA + b"extra", "encode_file_size_conflict"),
    (DATA[:-1] + b"X", "encode_file_md5_conflict")])
def test_advertised_file_size_and_transferred_md5_remain_distinct_from_content_md5(host, data, code):
    metadata = acquired_metadata(host, raw=json.dumps({**FILE, "content_md5sum": "0" * 32}).encode())
    selection = encode.prepare_encode_request(host.tools, metadata.arguments, authority=metadata.authority)
    host.http.respond(data, headers=[("Content-Type", "application/octet-stream")])
    receipt, refs = publish(host, metadata.arguments,
        encode.request_encode(host.client, metadata.arguments, selection=selection), selection=selection)
    assert receipt["acquired"] is False and receipt["failure_code"] == code
    assert refs == [receipt["source_ref"]]


def test_metadata_original_timeout_is_not_replaced_by_the_later_client_setting(host):
    metadata = acquired_metadata(host)
    host.client.timeout = 7
    selection = encode.prepare_encode_request(host.tools, metadata.arguments, authority=metadata.authority)
    assert selection["association"]["advertised_url"] == URL


def test_explicit_zero_byte_advertised_file_is_complete_data_not_a_missing_file(host):
    empty = {**FILE, "file_size": 0, "md5sum": hashlib.md5(b"").hexdigest(),
        "cloud_metadata": {"url": URL, "file_size": 0,
            "md5sum_base64": base64.b64encode(hashlib.md5(b"").digest()).decode()}}
    metadata = acquired_metadata(host, raw=json.dumps(empty).encode())
    selection = encode.prepare_encode_request(host.tools, metadata.arguments, authority=metadata.authority)
    host.http.respond(b"", headers=[("Content-Type", "application/octet-stream")])
    receipt, refs = publish(host, metadata.arguments,
        encode.request_encode(host.client, metadata.arguments, selection=selection), selection=selection)
    assert receipt["acquired"] is True and host.store.get_artifact(receipt["data_ref"]) == b""
    assert refs == [receipt["source_ref"], "artifact_" + hashlib.sha256(b"").hexdigest()]


def test_mutable_selection_cannot_change_the_pinned_advertised_url(host):
    metadata = acquired_metadata(host)
    selection = encode.prepare_encode_request(host.tools, metadata.arguments, authority=metadata.authority)
    changed = deepcopy(selection); changed["association"]["advertised_url"] = "https://example.test/other"
    host.http.respond(DATA)
    snapshot = encode.request_encode(host.client, metadata.arguments, selection=changed)
    with pytest.raises(ContractError, match="^encode_file_selection_conflict$"):
        publish(host, metadata.arguments, snapshot, selection=changed)
    assert len(host.http.calls) == 2  # The deliberately corrupted private carrier is never relabeled.


@pytest.mark.parametrize("successful", [True, False])
def test_saved_file_authenticator_uses_current_admission_and_controls_without_entity_reads(host, monkeypatch, successful):
    metadata = acquired_metadata(host)
    selection = encode.prepare_encode_request(host.tools, metadata.arguments, authority=metadata.authority)
    host.http.respond(DATA, status=200 if successful else 503)
    receipt, refs = publish(host, metadata.arguments,
        encode.request_encode(host.client, metadata.arguments, selection=selection), selection=selection)
    # A literal publisher-result carrier tests this callback only. No saved
    # ToolOperation or completed RuntimeAction is fabricated by this unit case.
    outcome = {"status": "completed" if successful else "partial", "result": receipt, "record_refs": refs}
    source = host.store.get(receipt["source_ref"])
    allowed = {source["request_ref"], *source["auxiliary_artifact_refs"]}
    original = host.store.get_artifact
    reads = []
    def control_only(reference):
        assert reference in allowed, "saved authentication reopened original metadata or downloaded data"
        reads.append(reference)
        return original(reference)
    monkeypatch.setattr(host.store, "get_artifact", control_only)
    monkeypatch.setattr(host.client, "_http", forbidden)
    calls = len(host.http.calls)
    before = {table: [tuple(row) for row in host.store.db.execute("SELECT * FROM " + table)]
        for table in ("records", "artifacts", "tool_operations", "runtime_record_receipts", "runtime_actions")}
    encode.authenticate_saved_encode_request(host.tools, metadata.arguments, authority=metadata.authority, outcome=outcome)
    assert reads == [source["request_ref"], source["auxiliary_artifact_refs"][0]]
    assert len(host.http.calls) == calls
    assert before == {table: [tuple(row) for row in host.store.db.execute("SELECT * FROM " + table)] for table in before}


def test_saved_file_denial_precedes_private_controls_even_for_a_literal_result(host, monkeypatch):
    metadata = acquired_metadata(host, deliver=False)
    monkeypatch.setattr(host.store, "get_artifact", forbidden)
    with pytest.raises(ContractError, match="^encode_metadata_not_received$"):
        encode.authenticate_saved_encode_request(host.tools, metadata.arguments, authority=metadata.authority,
            outcome={"status": "failed", "record_refs": [], "result": {"acquired": False, "source_ref": None,
                "data_ref": None, "failure_code": "provider_connection_failed"}})


@pytest.mark.parametrize("successful", [True, False])
def test_actual_ordinary_file_step_and_registry_cache_keep_scope_refs_and_private_controls(host, monkeypatch, successful):
    """Requires finite shared wiring; runs no provider/model or child episode."""
    metadata = acquired_metadata(host)
    caller, workflow, arguments = metadata.caller, metadata.workflow, metadata.arguments
    baseline = set(workflow.receipts.known(caller.source.episode_id))
    host.http.respond(DATA, status=200 if successful else 503)
    action = {"kind": "tool", "tool": encode.TOOL, "arguments": arguments}
    asyncio.run(caller.source.execute(action, 1))
    outcome = deepcopy(caller.source.last_outcome)
    receipt = encode.validate_encode_receipt(outcome["result"])
    source = host.store.get(receipt["source_ref"])
    refs = [source["id"], *([source["artifact_ref"]] if successful else [])]
    assert receipt["acquired"] is successful and outcome["status"] == ("completed" if successful else "partial")
    assert outcome["record_refs"] == refs
    assert set(workflow.receipts.known(caller.source.episode_id)) == baseline | set(refs)
    resolver = workflow.resolver(host.scope, source=caller.source)
    assert resolver(source["id"], "source") is True
    assert resolver(source["artifact_ref"], "artifact") is successful
    assert resolver(source["request_ref"], "artifact") is False
    assert all(resolver(reference, "artifact") is False for reference in source["auxiliary_artifact_refs"])
    assert validate_form(receipt, encode.encode_receipt_schema(), resolver) == receipt
    assert source["version"] is None and source["parent_source_refs"] == [metadata.receipt["source_ref"]]
    assert host.store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 1
    assert host.store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 2
    assert host.store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 2
    for table in ("runtime_model_calls", "runtime_observations", "runtime_forms", "runtime_report_attempts"):
        assert host.store.db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
    tables = [row[0] for row in host.store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    before = {table: [tuple(row) for row in host.store.db.execute('SELECT * FROM "' + table.replace('"', '""') + '"')]
        for table in tables}
    monkeypatch.setattr(host.client, "_http", forbidden)
    context = workflow.binding_context(caller.source)
    key = f"{workflow.run_id}:{context.episode_id}:1"
    with host.tools.current_invocation(context, read_received=workflow.services.read_received_molecular_input,
            tool_name=encode.TOOL, arguments=arguments, operation_key=key):
        replay = asyncio.run(host.tools.execute_async(encode.TOOL, arguments, scope=host.scope, operation_key=key))
    original_operation = deepcopy(outcome)
    if "pending_work_after_action" in original_operation:
        validate_pending(original_operation.pop("pending_work_after_action"))
    assert replay == original_operation and replay["result"] == outcome["result"]
    assert before == {table: [tuple(row) for row in host.store.db.execute('SELECT * FROM "' + table.replace('"', '""') + '"')]
        for table in tables}
    assert len(host.http.calls) == 2


def test_original_snapshot_service_contradiction_is_retained_in_private_request(host, monkeypatch):
    original = host.client._http
    def wrong_service(*args, **kwargs):
        return replace(original(*args, **kwargs), service="not-the-selected-provider")
    monkeypatch.setattr(host.client, "_http", wrong_service)
    host.http.respond(OBJECT_BYTES)
    snapshot = encode.request_encode(host.client, OBJECT)
    receipt, _ = publish(host, OBJECT, snapshot)
    source = host.store.get(receipt["source_ref"])
    assert receipt["failure_code"] == "encode_selected_request_mismatch"
    assert json.loads(host.store.get_artifact(source["request_ref"]))["request"]["native_service"] == "not-the-selected-provider"


@pytest.mark.parametrize("change", [
    {"acquired": 1}, {"source_ref": None}, {"data_ref": None}, {"source_ref": "source_bad"},
    {"failure_code": "encode_http_not_successful"}, {"extra": 1},
    {"acquired": False, "data_ref": None, "failure_code": None},
    {"acquired": False, "data_ref": None, "failure_code": "uncontrolled prose"},
])
def test_common_receipt_owner_enforces_success_references_and_failure_exclusion(change):
    receipt = {"acquired": True, "source_ref": "source_" + "a" * 24,
        "data_ref": "artifact_" + "b" * 64, "failure_code": None, **change}
    with pytest.raises(ContractError, match="^encode_receipt_invalid$"):
        encode.validate_encode_receipt(receipt)


def test_common_factor_preserves_jaspar_schema_and_error_strings_and_closed_return_grammar():
    expected = {"type": "object", "properties": {"acquired": {"type": "boolean"},
        "source_ref": {"type": ["string", "null"], "format": "reference", "x-reference-namespace": "source"},
        "data_ref": {"type": ["string", "null"], "format": "reference", "x-reference-namespace": "artifact"},
        "failure_code": {"type": ["string", "null"], "enum": [None, *jaspar.FAILURE_CODES]}},
        "required": ["acquired", "source_ref", "data_ref", "failure_code"], "additionalProperties": False}
    assert jaspar.jaspar_receipt_schema() == expected
    assert acquisition_receipt_schema(failure_codes=jaspar.FAILURE_CODES) == expected
    with pytest.raises(ContractError, match="^jaspar_receipt_invalid$"):
        jaspar.validate_jaspar_receipt({})
    schema = encode.encode_receipt_schema()
    assert validate_closed_schema(schema) == schema
    receipt = {"acquired": False, "source_ref": None, "data_ref": None, "failure_code": "provider_connection_failed"}
    assert validate_acquisition_receipt(receipt, failure_codes=encode.FAILURE_CODES,
        invalid_code="encode_receipt_invalid") == encode.validate_encode_receipt(receipt)
    assert validate_form(receipt, schema, forbidden) == receipt
    assert "x-source" not in json.dumps(schema)
    detached = encode.encode_tool_contract(); detached["input_schema"].clear()
    assert encode.encode_tool_contract()["input_schema"] == encode.ARGUMENTS_SCHEMA


@pytest.mark.parametrize("failure", ["malformed_search", "connection_without_response"])
def test_ordinary_metadata_failures_return_only_controlled_receipt_without_extra_work(host, monkeypatch, failure):
    """Actual registry/action failure paths, with engineered transport only."""
    class NoModel:
        complete = staticmethod(forbidden)
        release = staticmethod(forbidden)
    def neutral(*args, **kwargs):
        return 0
    workflow = Workflow(host.store, host.tools, NoModel(), host.tmp_path / "failure-run",
        "encode-controlled-metadata-failure", forbidden, neutral, root_role="improvement",
        episode_record_receipts=True, initial_known_record_refs=[])
    caller = workflow.build("improvement", "existing-caller", "Retrieve the explicitly selected ENCODE metadata.", host.scope)
    initial_known = set(workflow.receipts.known(caller.source.episode_id))
    source_count = host.store.count("source")
    arguments = deepcopy(SEARCH)
    if failure == "malformed_search":
        # JSON-shaped but invalid native reserved filter: provider validation
        # must reject before any HTTP request or Source publication.
        arguments["filters"] = [{"field": "limit", "value": "all"}]
        expected_code, expected_gets = "encode_arguments_invalid", 0
    else:
        host.http.fail(urllib.error.URLError("engineered connection unavailable before any response"))
        expected_code, expected_gets = "provider_connection_failed", 1
    monkeypatch.setattr(host.tools, "_sequence_worker_async", forbidden)
    monkeypatch.setattr(host.store, "commit_reasoning", forbidden)
    action = {"kind": "tool", "tool": encode.TOOL, "arguments": arguments}
    with pytest.raises(ActionFailure):
        asyncio.run(caller.source.execute(action, 0))
    outcome = deepcopy(caller.source.last_outcome)
    expected = {"acquired": False, "source_ref": None, "data_ref": None, "failure_code": expected_code}
    assert encode.validate_encode_receipt(outcome["result"]) == expected
    assert validate_form(outcome["result"], encode.encode_receipt_schema(), forbidden) == expected
    assert outcome["status"] == ("invalid" if failure == "malformed_search" else "failed")
    assert outcome["record_refs"] == [] and outcome["feedback"]["code"] == expected_code
    assert len(host.http.calls) == expected_gets and not host.http.pending
    if expected_gets:
        spec = encode.encode_request_spec(arguments)
        assert host.http.calls[0].get_method() == "GET"
        assert host.http.calls[0].full_url == spec["url"] + "?" + urlencode(spec["params"], doseq=True)
    operation, = host.store.db.execute("SELECT * FROM tool_operations")
    assert operation["name"] == encode.TOOL and json.loads(operation["arguments"]) == arguments
    stored = json.loads(operation["result"])
    original_operation = deepcopy(outcome)
    if "pending_work_after_action" in original_operation:
        validate_pending(original_operation.pop("pending_work_after_action"))
    assert stored == original_operation and stored["result"] == expected
    selected, = host.store.db.execute("SELECT * FROM runtime_actions")
    assert json.loads(selected["action"]) == action and json.loads(selected["result"]) == outcome
    assert selected["credit"] is None
    assert host.store.count("source") == source_count
    assert host.store.count("observation") == host.store.count("annotation") == 0
    assert set(workflow.receipts.known(caller.source.episode_id)) == initial_known
    assert host.store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 1
    for table in ("runtime_model_calls", "runtime_observations", "runtime_forms", "runtime_report_attempts"):
        assert host.store.db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
    tables = [row[0] for row in host.store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    before = {table: [tuple(row) for row in host.store.db.execute('SELECT * FROM "' + table.replace('"', '""') + '"')]
        for table in tables}
    monkeypatch.setattr(host.client, "_http", forbidden)
    context = workflow.binding_context(caller.source)
    with host.tools.current_invocation(context, read_received=workflow.services.read_received_molecular_input,
            tool_name=encode.TOOL, arguments=arguments, operation_key=operation["operation_key"]):
        replay = asyncio.run(host.tools.execute_async(encode.TOOL, arguments, scope=host.scope,
            operation_key=operation["operation_key"]))
    assert replay == stored and replay["result"] == expected
    assert len(host.http.calls) == expected_gets
    assert before == {table: [tuple(row) for row in host.store.db.execute('SELECT * FROM "' + table.replace('"', '""') + '"')]
        for table in tables}


# Explicit live discovery is selected separately from every engineered case
# above. This node never selects or downloads an advertised File.
import os
from pathlib import Path
import re
import stat

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.domain import identity
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.materials import artifact_path
from test_molecular_acquisition_ordinary import _live_audit, _live_pin, _live_write


LIVE_ENCODE_DISCOVERY_ARGUMENTS = {"operation": "search", "object_type": "File", "filters": [
    {"field": "status", "value": "released"},
    {"field": "file_format", "value": "bed"},
    {"field": "assay_term_name", "value": "DNase-seq"},
    {"field": "assembly", "value": "GRCh38"},
    {"field": "file_size", "value": "lte:1048576"}],
    "search_term": None, "frame": "object", "limit": 5, "max_bytes": 2097152}
LIVE_ENCODE_DISCOVERY_QUESTION = (
    "Acquire the explicitly selected ENCODE metadata and any later caller-selected File for future analysis."
)


class _EncodeLiveNoModel:
    complete = staticmethod(forbidden)
    release = staticmethod(forbidden)


def _encode_live_neutral(*args, **kwargs):
    return 0


def _encode_live_workflow(store, *, directory, run_id):
    """Use the same callable bindings for discovery and a later explicit File step."""
    tools = ToolRegistry(store, clients=PublicClients(ncbi_email=None, timeout=90))
    return Workflow(store, tools, _EncodeLiveNoModel(), directory, run_id, forbidden, _encode_live_neutral,
        root_role="improvement", episode_binding_factories=(), episode_record_receipts=True, initial_known_record_refs=[])


def _encode_live_configuration(workflow):
    """Record actual constructor bindings without creating a runtime marker."""
    provider_type = type(workflow.provider)
    return {"factory": f"{_encode_live_workflow.__module__}.{_encode_live_workflow.__qualname__}",
        "provider_type": f"{provider_type.__module__}.{provider_type.__qualname__}",
        "controller_binding": deepcopy(workflow.controller_binding),
        "credit_binding": deepcopy(workflow.credit_binding),
        "child_credit_binding": deepcopy(workflow.child_credit_binding),
        "root_role": workflow.root_role, "episode_roles": list(workflow.episode_bindings.roles),
        "episode_record_receipts": workflow.episode_record_receipts,
        "initial_known_record_refs": list(workflow.initial_known_record_refs),
        "restoration_settings": deepcopy(workflow.restoration_settings),
        "execution_binding": deepcopy(workflow.execution_binding),
        "decision_protocol": workflow.decision_protocol, "root_action_boundary": workflow.root_action_boundary,
        "progress_receipt_order": workflow.progress_receipt_order,
        "wait_inputs_version": workflow.wait_inputs_version,
        "completed_action_inputs_version": workflow.completed_action_inputs_version}


def _encode_live_gate(tmp_path):
    attempt = os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_ACQUISITION_ATTEMPT", "")
    bounded = os.environ.get("HMMER529_ATTEMPT", "")
    if os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_ENCODE_LIVE") != "1" or not attempt or not bounded:
        pytest.skip("requires explicit live ENCODE discovery selection and unique bounded acquisition attempt")
    assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}", attempt), "select a unique explicit attempt ID"
    bounded_path = Path(bounded).resolve(strict=True)
    assert tmp_path.resolve().is_relative_to(bounded_path)
    selected = json.loads((bounded_path / "selected_request.json").read_bytes())
    assert selected["policy"] == {'memory_bytes': 20 * 1024 ** 3, 'scratch_bytes': 4 * 1024 ** 3}
    assert selected["swap_bytes"] == 0
    return attempt, bounded


def _encode_live_capture(snapshot, root, action, proof, prefix, *, file_name="original-encode-discovery-http-body.bin"):
    """Retain original response/error bytes before the ordinary Source writer."""
    assert isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes
    path = root / file_name
    with path.open("xb") as handle:
        handle.write(snapshot.content)
        handle.flush()
        os.fsync(handle.fileno())
    action["http_capture"] = {"service": snapshot.service, "url": snapshot.url,
        "request": deepcopy(snapshot.request), "retrieved_at": snapshot.retrieved_at,
        "media_type": snapshot.media_type, "transport": deepcopy(snapshot.transport), "body_file": _live_pin(path)}
    _live_write(prefix, proof)


def _encode_live_verify_action(store, workflow, caller, action):
    """Join the one actual selected action, receipt and literal metadata Source."""
    row = workflow.journal.row("runtime_actions", caller.source.episode_id, 0)
    assert row is not None and json.loads(row["action"]) == action["selection"] and row["result"] is not None
    outcome = json.loads(row["result"])
    action["runtime_action"], action["outcome"] = dict(row), deepcopy(outcome)
    receipt = encode.validate_encode_receipt(outcome["result"])
    operation = store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (action["operation_key"],)).fetchone()
    assert operation is not None and operation["name"] == encode.TOOL
    assert operation["id"] == identity("operation", {"key": action["operation_key"], "name": encode.TOOL,
        "arguments": action["arguments"]})
    assert operation["arguments"] == canonical(action["arguments"]) and operation["scope"] == canonical(caller.source.scope)
    operation_outcome = deepcopy(outcome)
    if "pending_work_after_action" in operation_outcome:
        validate_pending(operation_outcome.pop("pending_work_after_action"))
    assert json.loads(operation["result"]) == operation_outcome
    action["tool_operation"] = dict(operation)
    known = set(workflow.receipts.known(caller.source.episode_id))
    resolver = workflow.resolver(caller.source.scope, source=caller.source)
    assert validate_form(receipt, encode.encode_receipt_schema(), resolver) == receipt
    assert known == set(action["known_before"]) | set(outcome["record_refs"])
    action.update(known_after=sorted(known), receipt_verified=True, acquired=receipt["acquired"])
    if receipt["source_ref"] is None:
        assert receipt["acquired"] is False and receipt["data_ref"] is None
        assert outcome["record_refs"] == [] and action["http_capture"] is None
        return
    source = store.get(receipt["source_ref"])
    capture = action["http_capture"]
    assert capture is not None
    raw_pin = capture["body_file"]
    raw = Path(raw_pin["path"]).read_bytes()
    assert 0 <= len(raw) == raw_pin["size_bytes"] <= action["arguments"]["max_bytes"]
    assert source["provider"] == encode.TOOL and source["origin"] == "external" and source["version"] is None
    assert source["uri"] == action["selected_wire_uri"] == capture["transport"]["request"]["url"]
    assert source["retrieved_at"] == capture["retrieved_at"] and source["accession"] is None
    assert source["parent_source_refs"] == source["auxiliary_artifact_refs"] == []
    assert source["artifact_ref"] == "artifact_" + raw_pin["sha256"]
    artifact = store.get(source["artifact_ref"])
    assert artifact["sha256"] == raw_pin["sha256"] and artifact["size"] == len(raw)
    assert store.get_artifact(source["artifact_ref"]) == raw
    controls = json.loads(store.get_artifact(source["request_ref"]))
    assert canonical(controls) == canonical({"request": {"version": encode.REQUEST_VERSION,
        "arguments": action["arguments"], "native_service": capture["service"],
        "native_request": capture["request"], "selection": None}, "transport": capture["transport"]})
    assert source["request_ref"] not in known and resolver(source["request_ref"], "artifact") is False
    with pytest.raises(ContractError):
        artifact_path(store, source["request_ref"])
    expected = [source["id"], source["artifact_ref"]] if receipt["acquired"] else [source["id"]]
    assert outcome["record_refs"] == expected and resolver(source["id"], "source") is True
    independently_known = source["artifact_ref"] in set(action["known_before"])
    assert resolver(source["artifact_ref"], "artifact") is (receipt["acquired"] or independently_known)
    action.update(source=source, source_control=controls, raw_identity_verified=True, private_controls_denied=True)
    if not receipt["acquired"]:
        assert outcome["status"] == "partial" and receipt["data_ref"] is None
        return
    transport = capture["transport"]
    assert outcome["status"] == "completed" and receipt["data_ref"] == source["artifact_ref"]
    assert transport["body_complete"] is True and transport["status"] in (200, 404)
    assert transport["request_policy"] == {"timeout_seconds": 90, "automatic_redirects": False}
    assert transport["response_byte_limit"] == action["arguments"]["max_bytes"]
    assert transport["observed_body_bytes"] == transport["retained_body_bytes"] == len(raw)
    document = json.loads(raw)
    assert type(document) is dict and type(document["@graph"]) is list
    assert type(document["total"]) is int and 0 <= len(document["@graph"]) <= action["arguments"]["limit"]
    assert len(document["@graph"]) <= document["total"]
    action["native_page_metadata"] = {"total": document["total"], "returned_occurrences": len(document["@graph"]),
        "ordered_file_ids": [item["@id"] for item in document["@graph"]]}
    action["native_request_and_complete_metadata_verified"] = True


def test_live_preselected_encode_discovery_metadata_only(tmp_path, monkeypatch):
    attempt, bounded = _encode_live_gate(tmp_path)
    prefix, store_directory = tmp_path / "ENCODE_DISCOVERY_PREFIX.json", tmp_path / "store"
    arguments = deepcopy(LIVE_ENCODE_DISCOVERY_ARGUMENTS)
    spec = encode.encode_request_spec(arguments)
    action = {"decision_index": 0, "arguments": arguments, "request_spec": spec,
        "selected_wire_uri": spec["url"] + "?" + urlencode(spec["params"], doseq=True),
        "selection": {"kind": "tool", "tool": encode.TOOL, "arguments": arguments},
        "http_calls": [], "http_capture": None, "action_returned": False, "receipt_verified": False,
        "acquired": False, "raw_identity_verified": False, "private_controls_denied": False,
        "native_request_and_complete_metadata_verified": False}
    proof = {"version": "ordinary_encode_discovery_live_proof_v1", "attempt": attempt, "bounded_attempt": bounded,
        "question": LIVE_ENCODE_DISCOVERY_QUESTION, "tool": encode.TOOL, "run_id": "ordinary-live-encode-" + attempt,
        "store_directory": str(store_directory), "workflow_directory": str(tmp_path / "run"),
        "workflow_parameters": {"root_role": "improvement", "caller_key": "existing-caller",
            "episode_binding_factories": [], "episode_record_receipts": True, "initial_known_record_refs": []},
        "client_configuration": {"ncbi_email": None, "timeout_seconds": 90},
        "qualification": "One supplied discovery action only; no File selection/download, page following, scientific analysis or completion claim",
        "actions": [action], "passed": False, "ordinary_episode_boundary_verified": False}
    _live_write(prefix, proof, exclusive=True)
    original_http = PublicClients._http
    def observed_http(client, service, url, params, media_type, **options):
        assert action["http_calls"] == [], "no retry, automatic page or additional GET was selected"
        selected = {"service": service, "url": url, "params": deepcopy(params), "media_type": media_type, **options}
        assert selected == {**spec, "timeout_seconds": 90}
        action["http_calls"].append({"started": True, **selected})
        _live_write(prefix, proof)
        try:
            snapshot = original_http(client, service, url, params, media_type, **options)
        except AcquisitionError as error:
            action["http_calls"][0]["failure"] = {"code": error.code, "phase": error.phase}
            if error.snapshot is not None:
                _encode_live_capture(error.snapshot, tmp_path, action, proof, prefix)
            _live_write(prefix, proof)
            raise
        except BaseException as error:
            action["http_calls"][0]["failure"] = {"exception_type": type(error).__name__, "message": str(error)}
            _live_write(prefix, proof)
            raise
        _encode_live_capture(snapshot, tmp_path, action, proof, prefix)
        return snapshot
    try:
        with Store(store_directory) as store:
            subject, = store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]
            scope = {"subject_refs": [subject]}
            workflow = _encode_live_workflow(store, directory=tmp_path / "run", run_id=proof["run_id"])
            tools = workflow.tools
            caller = workflow.build("improvement", "existing-caller", proof["question"], scope)
            proof.update(episode_id=caller.source.episode_id, scope=scope,
                workflow_configuration=_encode_live_configuration(workflow),
                tool_info=deepcopy(tools.catalog(scope)[encode.TOOL]))
            action["operation_key"] = f"{workflow.run_id}:{caller.source.episode_id}:0"
            action["known_before"] = sorted(workflow.receipts.known(caller.source.episode_id))
            _live_audit(store, workflow, caller, proof)
            _live_write(prefix, proof)
            try:
                with monkeypatch.context() as live:
                    live.setattr(PublicClients, "_http", observed_http)
                    live.setattr("urllib.request.urlopen", forbidden)
                    live.setattr("subprocess.Popen", forbidden)
                    live.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
                    live.setattr("gene_annotation_episode.native_lifecycle.resume_start", forbidden)
                    live.setattr(ToolRegistry, "_sequence_worker_async", forbidden)
                    live.setattr(store, "commit_reasoning", forbidden)
                    asyncio.run(caller.source.execute(action["selection"], 0))
                    action["action_returned"] = True
                    _encode_live_verify_action(store, workflow, caller, action)
                    assert len(action["http_calls"]) == 1
                    assert store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 1
                    assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 1
                    assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 1
                    for table in ("runtime_model_calls", "runtime_observations", "runtime_forms", "runtime_report_attempts"):
                        assert store.db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
                    assert store.count("observation") == store.count("annotation") == 0
                    assert caller.request.report_contract is None and workflow.episode_bindings.roles == ()
                    _live_audit(store, workflow, caller, proof)
                    episode, = proof["journal"]["runtime_episodes"]
                    assert episode["state"] == "active" and episode["completion"] is episode["archive"] is None
                    proof["ordinary_episode_boundary_verified"] = True
                    _live_write(prefix, proof)
                    assert action["acquired"] is True, action["outcome"]["result"]
                    assert action["native_request_and_complete_metadata_verified"] is True
            finally:
                _live_audit(store, workflow, caller, proof)
                proof["table_counts"] = {row[0]: store.db.execute('SELECT count(*) FROM "' + row[0].replace('"', '""') + '"').fetchone()[0]
                    for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}
                _live_write(prefix, proof)
    except BaseException as error:
        proof["test_failure"] = {"exception_type": type(error).__name__, "message": str(error)}
        raise
    finally:
        bundle = []
        for name in ("state.sqlite3", "state.sqlite3-wal", "state.sqlite3-shm"):
            path = store_directory / name
            if path.is_file():
                row = _live_pin(path)
                bundle.append({"name": name, "sha256": row["sha256"], "size_bytes": row["size_bytes"]})
        proof["sqlite_files"] = bundle
        proof["sqlite_pins_sha256"] = hashlib.sha256(canonical(bundle).encode("utf-8")).hexdigest()
        proof["store_files"] = {str(path.relative_to(store_directory)): {**_live_pin(path), "mode": stat.S_IMODE(path.stat().st_mode)}
            for path in sorted(store_directory.rglob("*")) if path.is_file()}
        proof["workflow_files_at_finally"] = {str(path.relative_to(tmp_path / "run")): {**_live_pin(path), "mode": stat.S_IMODE(path.stat().st_mode)}
            for path in sorted((tmp_path / "run").rglob("*")) if path.is_file()}
        _live_write(prefix, proof)
    proof["passed"] = True
    _live_write(prefix, proof)


# This separately selected live action continues the immutable discovery case
# on an owned copy. It performs no discovery request or implicit File choice.
import shutil
import sqlite3


LIVE_ENCODE_FILE_ARGUMENTS = {"operation": "file", "metadata_source_ref": "source_6f215bdc16a524163c0cd039",
    "file_pointer": "/@graph/2", "file_id": "/files/ENCFF860AEN/", "max_bytes": 1048576}
_ENCODE_DISCOVERY_PROOF_SHA256 = "57829ac10e7b0bc5d72d9ebdfac6589e40de3e9e299a3d66ee6f73da8289a0d1"
_ENCODE_DISCOVERY_SQLITE_SHA256 = "79237755e05e4297c8b2ea738a23b18543f4d16d5768e0cfc0618edda944802b"
_ENCODE_DISCOVERY_BUNDLE_SHA256 = "257aca0036bdf3da4e985eb07a7902d48f81240c64425ce34e15360c553ca366"


def _encode_retained_tree(directory):
    result = {}
    for path in sorted(Path(directory).rglob("*")):
        mode = path.lstat().st_mode
        assert not stat.S_ISLNK(mode), "retained evidence must not redirect through a symlink"
        if stat.S_ISREG(mode):
            pin = _live_pin(path)
            result[str(path.relative_to(directory))] = {"sha256": pin["sha256"],
                "size_bytes": pin["size_bytes"], "mode": stat.S_IMODE(mode)}
        else:
            assert stat.S_ISDIR(mode)
    return result


def _encode_retained_rows(connection):
    tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    result = {}
    for table in tables:
        cursor = connection.execute('SELECT * FROM "' + table.replace('"', '""') + '" ORDER BY rowid')
        columns = [item[0] for item in cursor.description]
        result[table] = [dict(zip(columns, row, strict=True)) for row in cursor]
    return result


def _encode_live_file_gate(tmp_path):
    if os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_ENCODE_FILE_LIVE") != "1":
        pytest.skip("requires explicit retained discovery and one selected live ENCODE File transfer")
    attempt, bounded = _encode_live_gate(tmp_path)
    keys = ("HMMER_NATIVE_ORACLE_ENCODE_RETAINED_DISCOVERY", "HMMER_NATIVE_ORACLE_ENCODE_DISCOVERY_PROOF_SHA256",
        "HMMER_NATIVE_ORACLE_ENCODE_DISCOVERY_SQLITE_SHA256", "HMMER_NATIVE_ORACLE_ENCODE_DISCOVERY_SQLITE_PINS_SHA256",
        "HMMER_NATIVE_ORACLE_ENCODE_FILE_ARGUMENTS")
    assert all(os.environ.get(key) for key in keys), "supply every explicit retained-evidence and File-selection gate"
    path = Path(os.environ[keys[0]]).resolve(strict=True)
    pin = _live_pin(path)
    assert pin["sha256"] == os.environ[keys[1]] == _ENCODE_DISCOVERY_PROOF_SHA256 and pin["size_bytes"] == 54791
    discovery = json.loads(path.read_bytes())
    arguments = json.loads(os.environ[keys[4]])
    assert canonical(arguments) == canonical(LIVE_ENCODE_FILE_ARGUMENTS)
    assert encode.validate_encode_arguments(arguments) == arguments
    assert discovery["version"] == "ordinary_encode_discovery_live_proof_v1" and discovery["passed"] is True
    assert attempt != discovery["attempt"], "the File transfer needs its own explicit bounded attempt"
    assert discovery["ordinary_episode_boundary_verified"] is True and discovery["tool"] == encode.TOOL
    assert discovery["question"] == LIVE_ENCODE_DISCOVERY_QUESTION
    assert discovery["workflow_parameters"] == {"root_role": "improvement", "caller_key": "existing-caller",
        "episode_binding_factories": [], "episode_record_receipts": True, "initial_known_record_refs": []}
    assert discovery["client_configuration"] == {"ncbi_email": None, "timeout_seconds": 90}
    assert discovery["actions"][0]["arguments"] == LIVE_ENCODE_DISCOVERY_ARGUMENTS
    assert discovery["actions"][0]["outcome"]["result"] == discovery["outcome"]["result"]
    assert discovery["outcome"]["result"]["source_ref"] == arguments["metadata_source_ref"]
    assert discovery["outcome"]["result"]["acquired"] is True
    assert discovery["scientific_record_counts"] == {"observation": 0, "annotation": 0}
    directory = Path(discovery["store_directory"]).resolve(strict=True)
    db_pin = _live_pin(directory / "state.sqlite3")
    assert db_pin["sha256"] == os.environ[keys[2]] == _ENCODE_DISCOVERY_SQLITE_SHA256 and db_pin["size_bytes"] == 339968
    physical = [{"name": name, **{key: value for key, value in _live_pin(directory / name).items() if key != "path"}}
        for name in ("state.sqlite3", "state.sqlite3-wal", "state.sqlite3-shm") if (directory / name).is_file()]
    assert physical == discovery["sqlite_files"]
    assert hashlib.sha256(canonical(physical).encode()).hexdigest() == discovery["sqlite_pins_sha256"] == (
        os.environ[keys[3]]) == _ENCODE_DISCOVERY_BUNDLE_SHA256
    return attempt, bounded, path, pin, discovery, arguments, physical


def _encode_copy_discovery(discovery, physical, tmp_path):
    """Open SQLite only after copying its complete authenticated physical family."""
    original = Path(discovery["store_directory"])
    staging = tmp_path / "physical-sqlite-copy"
    staging.mkdir()
    for item in physical:
        shutil.copy2(original / item["name"], staging / item["name"])
        copied = _live_pin(staging / item["name"])
        assert {key: copied[key] for key in ("sha256", "size_bytes")} == {
            key: item[key] for key in ("sha256", "size_bytes")}
    store_directory, workflow_directory = tmp_path / "store", tmp_path / "run"
    store_directory.mkdir()
    source, destination = sqlite3.connect(staging / "state.sqlite3"), sqlite3.connect(store_directory / "state.sqlite3")
    try:
        original_rows = _encode_retained_rows(source)
        source.backup(destination)
        assert _encode_retained_rows(destination) == original_rows
    finally:
        destination.close()
        source.close()
    assert {table: len(rows) for table, rows in original_rows.items()} == discovery["table_counts"]
    shutil.copytree(original / "artifacts", store_directory / "artifacts")
    shutil.copytree(discovery["workflow_directory"], workflow_directory)
    return store_directory, workflow_directory, original_rows


def _encode_live_verify_file_action(store, workflow, caller, action, discovery, selected_file):
    row = workflow.journal.row("runtime_actions", caller.source.episode_id, 1)
    assert row is not None and json.loads(row["action"]) == action["selection"] and row["result"] is not None
    outcome = json.loads(row["result"])
    operation = store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (action["operation_key"],)).fetchone()
    assert operation is not None and operation["name"] == encode.TOOL
    assert operation["id"] == identity("operation", {"key": action["operation_key"], "name": encode.TOOL,
        "arguments": action["arguments"]})
    assert operation["arguments"] == canonical(action["arguments"]) and operation["scope"] == canonical(caller.source.scope)
    literal = deepcopy(outcome)
    if "pending_work_after_action" in literal:
        validate_pending(literal.pop("pending_work_after_action"))
    assert json.loads(operation["result"]) == literal
    receipt = encode.validate_encode_receipt(outcome["result"])
    resolver = workflow.resolver(caller.source.scope, source=caller.source)
    assert validate_form(receipt, encode.encode_receipt_schema(), resolver) == receipt
    known = set(workflow.receipts.known(caller.source.episode_id))
    assert known == set(action["known_before"]) | set(outcome["record_refs"])
    action.update(runtime_action=dict(row), outcome=outcome, tool_operation=dict(operation),
        known_after=sorted(known), receipt_verified=True, acquired=receipt["acquired"])
    if receipt["source_ref"] is None:
        assert receipt["acquired"] is False and receipt["data_ref"] is None and outcome["record_refs"] == []
        assert action["http_capture"] is None
        return literal, None
    source, capture = store.get(receipt["source_ref"]), action["http_capture"]
    assert capture is not None
    raw_pin = capture["body_file"]
    raw = Path(raw_pin["path"]).read_bytes()
    assert _live_pin(raw_pin["path"]) == raw_pin and len(raw) <= action["arguments"]["max_bytes"]
    assert source["provider"] == encode.TOOL and source["origin"] == "external" and source["version"] is None
    assert source["accession"] is None and source["retrieved_at"] == capture["retrieved_at"]
    assert source["uri"] == action["selected_wire_uri"] == capture["transport"]["request"]["url"]
    assert source["artifact_ref"] == "artifact_" + raw_pin["sha256"]
    assert store.get_artifact(source["artifact_ref"]) == raw
    assert store.get(source["artifact_ref"])["size"] == raw_pin["size_bytes"]
    assert source["parent_source_refs"] == [action["arguments"]["metadata_source_ref"]]
    assert len(source["auxiliary_artifact_refs"]) == 1
    selection = json.loads(store.get_artifact(source["auxiliary_artifact_refs"][0]))
    association = {"file_id": selected_file["@id"], "advertised_url": selected_file["cloud_metadata"]["url"],
        "file_size": selected_file["file_size"], "md5sum": selected_file["md5sum"]}
    assert selection["version"] == encode.SELECTION_VERSION and selection["arguments"] == action["arguments"]
    assert selection["association"] == association
    metadata = store.get(action["arguments"]["metadata_source_ref"])
    original_operation, = discovery["tool_operations"]
    assert selection["metadata_operation"] == {"operation_key": original_operation["operation_key"],
        "operation_ref": original_operation["id"]}
    assert selection["metadata_source_sha256"] == hashlib.sha256(canonical(metadata).encode()).hexdigest()
    assert selection["metadata_artifact_ref"] == metadata["artifact_ref"]
    assert selection["metadata_size_bytes"] == store.get(metadata["artifact_ref"])["size"]
    assert selection["metadata_request_ref"] == metadata["request_ref"]
    assert selection["metadata_request_sha256"] == store.get(metadata["request_ref"])["sha256"]
    control = json.loads(store.get_artifact(source["request_ref"]))
    assert canonical(control) == canonical({"request": {"version": encode.REQUEST_VERSION,
        "arguments": action["arguments"], "native_service": capture["service"], "native_request": capture["request"],
        "selection": selection}, "transport": capture["transport"]})
    private = [source["request_ref"], *source["auxiliary_artifact_refs"], metadata["request_ref"]]
    for reference in private:
        assert reference not in known and resolver(reference, "artifact") is False
        with pytest.raises(ContractError):
            artifact_path(store, reference)
    expected = [source["id"], *([source["artifact_ref"]] if receipt["acquired"] else [])]
    assert outcome["record_refs"] == expected and resolver(source["id"], "source") is True
    assert resolver(source["artifact_ref"], "artifact") is (receipt["acquired"] or source["artifact_ref"] in action["known_before"])
    assert resolver(metadata["id"], "source") is True and resolver(metadata["artifact_ref"], "artifact") is True
    action.update(source=source, source_control=control, file_selection=selection,
        raw_identity_verified=True, private_controls_denied=True, current_metadata_admission_verified=True)
    if receipt["acquired"]:
        transport = capture["transport"]
        assert outcome["status"] == "completed" and receipt["data_ref"] == source["artifact_ref"]
        assert transport["status"] == 200 and transport["body_complete"] is True
        assert transport["request_policy"] == {"timeout_seconds": 90, "automatic_redirects": False}
        assert transport["response_byte_limit"] == action["arguments"]["max_bytes"]
        assert transport["observed_body_bytes"] == transport["retained_body_bytes"] == len(raw) == 587299
        assert hashlib.md5(raw).hexdigest() == selected_file["md5sum"] == "f57370e7ac072df44190460c18582ffc"
        assert base64.b64decode(selected_file["cloud_metadata"]["md5sum_base64"], validate=True).hex() == hashlib.md5(raw).hexdigest()
        action["native_file_size_and_transfer_md5_verified"] = True
    else:
        assert outcome["status"] == "partial" and receipt["data_ref"] is None
    return literal, source


def test_live_preselected_encode_file_from_retained_discovery(tmp_path, monkeypatch):
    attempt, bounded, original_prefix, original_pin, discovery, arguments, physical = _encode_live_file_gate(tmp_path)
    original_case = original_prefix.parent
    assert not tmp_path.resolve().is_relative_to(original_case)
    original_files = _encode_retained_tree(original_case)
    assert _encode_retained_tree(Path(discovery["store_directory"])) == {
        name: {key: item[key] for key in ("sha256", "size_bytes", "mode")} for name, item in discovery["store_files"].items()}
    assert _encode_retained_tree(Path(discovery["workflow_directory"])) == {
        name: {key: item[key] for key in ("sha256", "size_bytes", "mode")}
        for name, item in discovery["workflow_files_at_finally"].items()}
    prefix = tmp_path / "ENCODE_FILE_PREFIX.json"
    action = {"decision_index": 1, "arguments": arguments,
        "selection": {"kind": "tool", "tool": encode.TOOL, "arguments": arguments},
        "http_calls": [], "http_capture": None, "action_returned": False, "receipt_verified": False,
        "acquired": False, "raw_identity_verified": False, "private_controls_denied": False,
        "current_metadata_admission_verified": False, "native_file_size_and_transfer_md5_verified": False}
    proof = {"version": "ordinary_encode_selected_file_live_proof_v1", "attempt": attempt, "bounded_attempt": bounded,
        "original_discovery_prefix": original_pin, "original_sqlite_files": physical,
        "original_sqlite_pins_sha256": discovery["sqlite_pins_sha256"], "original_case_files_before": original_files,
        "run_id": discovery["run_id"], "episode_id": discovery["episode_id"], "question": discovery["question"],
        "scope": discovery["scope"], "actions": [action], "passed": False, "reconstruction_unchanged": False,
        "registry_cache_verified": False, "original_evidence_unchanged": False, "ordinary_episode_boundary_verified": False,
        "qualification": "One explicitly selected original compressed File transfer on an owned discovery copy; no new metadata GET, decoding, analysis, model, child, or Workflow completion"}
    _live_write(prefix, proof, exclusive=True)
    failure = None
    try:
        store_directory, directory, original_rows = _encode_copy_discovery(discovery, physical, tmp_path)
        proof.update(store_directory=str(store_directory), workflow_directory=str(directory), original_table_rows=original_rows)
        with Store(store_directory) as store:
            assert _encode_retained_rows(store.db) == original_rows
            workflow = _encode_live_workflow(store, directory=directory, run_id=discovery["run_id"])
            assert _encode_live_configuration(workflow) == discovery["workflow_configuration"]
            caller = workflow.build("improvement", "existing-caller", discovery["question"], discovery["scope"])
            assert caller.source.episode_id == discovery["episode_id"]
            assert _encode_retained_rows(store.db) == original_rows
            assert sorted(workflow.receipts.known(caller.source.episode_id)) == discovery["known_after"]
            assert workflow.tools.catalog(discovery["scope"])[encode.TOOL] == discovery["tool_info"]
            action.update(operation_key=f"{workflow.run_id}:{caller.source.episode_id}:1", known_before=discovery["known_after"])
            metadata = store.get(arguments["metadata_source_ref"])
            assert metadata == next(item["record"] for item in discovery["sources"] if item["id"] == metadata["id"])
            raw_metadata = store.get_artifact(metadata["artifact_ref"])
            assert hashlib.sha256(raw_metadata).hexdigest() == metadata["artifact_ref"].removeprefix("artifact_")
            selected_file = json.loads(raw_metadata)["@graph"][2]
            assert selected_file["@id"] == arguments["file_id"] and selected_file["file_size"] == 587299
            assert selected_file["cloud_metadata"]["file_size"] == selected_file["file_size"]
            assert selected_file["dataset"] == "/experiments/ENCSR859CZM/"
            assert selected_file["biosample_ontology"] == "/biosample-types/tissue_UBERON_0002021/"
            spec = {"service": "encode", "url": selected_file["cloud_metadata"]["url"], "params": {},
                "media_type": "application/octet-stream", "accept": "*/*", "max_bytes": 1048576, "follow_redirects": False}
            proof.update(reconstruction_unchanged=True, workflow_configuration=_encode_live_configuration(workflow),
                selected_native_file=selected_file, metadata_source=metadata)
            action.update(request_spec=spec, selected_wire_uri=spec["url"])
            _live_audit(store, workflow, caller, proof)
            _live_write(prefix, proof)
            original_http, original_open = PublicClients._http, Path.open
            def owned_open(path, *args, **kwargs):
                assert not path.resolve().is_relative_to(original_case), "application reopened original discovery evidence"
                return original_open(path, *args, **kwargs)
            def observed_http(client, service, url, params, media_type, **options):
                assert action["http_calls"] == [], "no retry, metadata GET, redirect or fallback was selected"
                selected = {"service": service, "url": url, "params": deepcopy(params), "media_type": media_type, **options}
                assert selected == {**spec, "timeout_seconds": 90}
                action["http_calls"].append({"started": True, **selected})
                _live_write(prefix, proof)
                try:
                    snapshot = original_http(client, service, url, params, media_type, **options)
                except AcquisitionError as error:
                    action["http_calls"][0]["failure"] = {"code": error.code, "phase": error.phase}
                    if error.snapshot is not None:
                        _encode_live_capture(error.snapshot, tmp_path, action, proof, prefix,
                            file_name="original-encode-selected-file-http-body.bin")
                    _live_write(prefix, proof)
                    raise
                except BaseException as error:
                    action["http_calls"][0]["failure"] = {"exception_type": type(error).__name__, "message": str(error)}
                    _live_write(prefix, proof)
                    raise
                _encode_live_capture(snapshot, tmp_path, action, proof, prefix,
                    file_name="original-encode-selected-file-http-body.bin")
                return snapshot
            try:
                with monkeypatch.context() as live:
                    live.setattr(Path, "open", owned_open)
                    live.setattr(PublicClients, "_http", observed_http)
                    live.setattr("urllib.request.urlopen", forbidden)
                    live.setattr("subprocess.Popen", forbidden)
                    live.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
                    live.setattr("gene_annotation_episode.native_lifecycle.resume_start", forbidden)
                    live.setattr(ToolRegistry, "_sequence_worker_async", forbidden)
                    live.setattr(store, "commit_reasoning", forbidden)
                    try:
                        asyncio.run(caller.source.execute(action["selection"], 1))
                        action["action_returned"] = True
                    except ActionFailure as error:
                        action["action_failure"] = {"exception_type": type(error).__name__, "message": str(error)}
                    literal, source = _encode_live_verify_file_action(store, workflow, caller, action, discovery, selected_file)
                    assert len(action["http_calls"]) == 1
                    before_cache = _encode_retained_rows(store.db)
                    known_before_cache = sorted(workflow.receipts.known(caller.source.episode_id))
                    permitted = set() if source is None else {source["request_ref"], *source["auxiliary_artifact_refs"]}
                    original_artifact_read, control_reads = store.get_artifact, []
                    body_refs = {metadata["artifact_ref"], *([] if source is None else [source["artifact_ref"]])}
                    body_paths = {store.path / "artifacts" / ref[9:11] / ref[9:] for ref in body_refs}
                    def controls_only(reference):
                        assert reference in permitted, "cache reopened metadata entity or downloaded File bytes"
                        control_reads.append(reference)
                        return original_artifact_read(reference)
                    def cache_open(path, *args, **kwargs):
                        assert path.resolve() not in body_paths, "cache reopened an entity by path"
                        return owned_open(path, *args, **kwargs)
                    with monkeypatch.context() as cached:
                        cached.setattr(PublicClients, "_http", forbidden)
                        cached.setattr(Path, "open", cache_open)
                        cached.setattr(store, "get_artifact", controls_only)
                        cached.setattr(store, "artifact", forbidden)
                        cached.setattr(store, "put", forbidden)
                        context = workflow.binding_context(caller.source)
                        with workflow.tools.current_invocation(context, read_received=workflow.services.read_received_molecular_input,
                                tool_name=encode.TOOL, arguments=arguments, operation_key=action["operation_key"]):
                            replay = asyncio.run(workflow.tools.execute_async(encode.TOOL, arguments,
                                scope=caller.source.scope, operation_key=action["operation_key"]))
                    assert replay == literal and replay["result"] == action["outcome"]["result"]
                    assert _encode_retained_rows(store.db) == before_cache
                    assert sorted(workflow.receipts.known(caller.source.episode_id)) == known_before_cache
                    proof.update(registry_cache_verified=True, cache_result=replay, cache_control_reads=control_reads)
                    assert store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 1
                    assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 2
                    assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 2
                    for table in ("runtime_model_calls", "runtime_observations", "runtime_forms", "runtime_report_attempts"):
                        assert store.db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
                    assert store.count("observation") == store.count("annotation") == 0
                    assert caller.request.report_contract is None and workflow.episode_bindings.roles == ()
                    _live_audit(store, workflow, caller, proof)
                    episode, = proof["journal"]["runtime_episodes"]
                    assert episode == discovery["journal"]["runtime_episodes"][0]
                    proof["ordinary_episode_boundary_verified"] = True
                    _live_write(prefix, proof)
                    assert action["acquired"] is True, action["outcome"]["result"]
                    assert action["native_file_size_and_transfer_md5_verified"] is True
            finally:
                _live_audit(store, workflow, caller, proof)
                final_rows = _encode_retained_rows(store.db)
                proof["final_table_rows"] = final_rows
                proof["table_counts"] = {table: len(rows) for table, rows in final_rows.items()}
                assert set(final_rows) == set(original_rows)
                for table, rows in original_rows.items():
                    assert final_rows[table][:len(rows)] == rows, "original retained rows changed in " + table
                proof["original_row_prefixes_unchanged"] = True
                _live_write(prefix, proof)
    except BaseException as error:
        failure = error
        proof["test_failure"] = {"exception_type": type(error).__name__, "message": str(error)}
        raise
    finally:
        try:
            proof["original_case_files_after"] = _encode_retained_tree(original_case)
            assert proof["original_case_files_after"] == original_files
            assert _live_pin(original_prefix) == original_pin
            proof["original_evidence_unchanged"] = True
        except BaseException as error:
            proof["preservation_failure"] = {"exception_type": type(error).__name__, "message": str(error)}
            if failure is None:
                raise
        finally:
            try:
                proof["store_files"] = _encode_retained_tree(tmp_path / "store")
                proof["workflow_files_at_finally"] = _encode_retained_tree(tmp_path / "run")
                bundle = [{"name": name, **{key: proof["store_files"][name][key] for key in ("sha256", "size_bytes")}}
                    for name in ("state.sqlite3", "state.sqlite3-wal", "state.sqlite3-shm") if name in proof["store_files"]]
                proof["sqlite_files"] = bundle
                proof["sqlite_pins_sha256"] = hashlib.sha256(canonical(bundle).encode()).hexdigest()
                raw_path = tmp_path / "original-encode-selected-file-http-body.bin"
                if raw_path.is_file():
                    proof["raw_transfer_file_at_finally"] = _live_pin(raw_path)
            except BaseException as error:
                proof["final_inventory_failure"] = {"exception_type": type(error).__name__, "message": str(error)}
                if failure is None and "preservation_failure" not in proof:
                    raise
            finally:
                _live_write(prefix, proof)
    proof["passed"] = True
    _live_write(prefix, proof)
