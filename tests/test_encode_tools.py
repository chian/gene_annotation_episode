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

from gene_annotation_episode.episodic_workflow.root.library import encode_tools as encode
from gene_annotation_episode import jaspar_tools as jaspar
from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.episodic_workflow.root.communication import validate_closed_schema, validate_form
from gene_annotation_episode.data_acquisition_receipts import acquisition_receipt_schema, validate_acquisition_receipt
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.task_action_units import ActionFailure
from gene_annotation_episode.episodic_workflow.root.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.wait_events import validate_pending


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


# This separately selected live action continues the immutable discovery case
# on an owned copy. It performs no discovery request or implicit File choice.


