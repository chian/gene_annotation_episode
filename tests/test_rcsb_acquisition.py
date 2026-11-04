"""Controlled RCSB-shaped HTTP/Workflow fixtures; no live archive claim."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, SourceSnapshot
from gene_annotation_episode import rcsb_acquisition as rcsb
from gene_annotation_episode.domain import identity
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider
from test_scientific_process_runtime import action


SOURCE = "source_" + "a" * 24


@pytest.fixture
def archive(monkeypatch):
    state = dict(requests=[], responses={})
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            state["requests"].append(self.path)
            status, body, headers = state["responses"].get(self.path, (404, b"not found", {}))
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            if "Content-Length" not in headers:
                self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
            self.close_connection = True

        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    root = f"http://127.0.0.1:{server.server_port}"
    # Test-only endpoint substitution is visible in actual URL/transport. It
    # does not describe these engineering replies as live RCSB acquisitions.
    monkeypatch.setattr(rcsb, "DATA_ROOT", root + "/data/")
    monkeypatch.setattr(rcsb, "FILE_ROOT", root + "/files/")
    state["root"] = root
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def entry(archive, body=None, *, fields=None):
    body = b'{"rcsb_id":"4HHB"}' if body is None else body
    archive["responses"]["/data/4HHB"] = (200, body, {"Content-Type": "application/json; charset=utf-8"})
    arguments = dict(entry_id="4HHB", fields=["rcsb_id"] if fields is None else fields, max_bytes=4096)
    snapshot = PublicClients(timeout=3).rcsb_entry(**arguments)
    return snapshot, arguments


def artifact(snapshot):
    return "artifact_" + hashlib.sha256(snapshot.content).hexdigest()


@pytest.mark.parametrize("kind,change", [
    ("entry", {"max_bytes": True}), ("entry", {"max_bytes": 1.0}), ("entry", {"max_bytes": 0}),
    ("entry", {"entry_id": "../4HHB"}), ("entry", {"entry_id": ""}), ("entry", {"entry_id": 4}),
    ("entry", {"entry_id": "4HHB\n"}), ("entry", {"entry_id": "4HHB\r"}),
    ("entry", {"entry_id": "４HHB"}), ("entry", {"entry_id": "4/HHB"}),
    ("entry", {"fields": ["citation"]}), ("entry", {"fields": ["rcsb_id", "rcsb_id"]}),
    ("entry", {"fields": "rcsb_id"}), ("entry", {"extra": None}),
    ("file", {"file_format": "cif"}), ("file", {"max_bytes": False}),
])
def test_strict_explicit_arguments_precede_any_http(kind, change, monkeypatch):
    client = PublicClients(timeout=3)
    def forbidden(*args, **kwargs):
        raise AssertionError("Malformed operands reached HTTP")
    monkeypatch.setattr(client, "_http", forbidden)
    arguments = (dict(entry_id="4HHB", fields=["rcsb_id"], max_bytes=4096) if kind == "entry" else
        dict(entry_id="4HHB", file_format="pdbx_mmcif_text", max_bytes=4096))
    arguments.update(change)
    validator = rcsb.validate_rcsb_entry_arguments if kind == "entry" else rcsb.validate_rcsb_file_arguments
    with pytest.raises(ValueError):
        validator(arguments)
    if "extra" not in arguments:
        with pytest.raises(ValueError):
            (client.rcsb_entry if kind == "entry" else client.rcsb_structure_file)(**arguments)


def test_two_explicit_clients_preserve_selected_path_and_actual_http_bytes(archive):
    client = PublicClients(timeout=3)
    raw_entry = b'{ "rcsb_id" : "4HHB", "rcsb_entry_info":{"count":0} }\n'
    archive["responses"]["/data/4HHB"] = (200, raw_entry, {"Content-Type": "application/json"})
    raw_file = b"data_literal\n_entry.id 4HHB\n"
    archive["responses"]["/files/pdb_00004hhb.cif"] = (200, raw_file, {"Content-Type": "chemical/x-mmcif"})
    requested = dict(entry_id="4HHB", fields=["rcsb_entry_info"], max_bytes=4096)
    snapshot = client.rcsb_entry(**requested)
    file = client.rcsb_structure_file("pdb_00004hhb", file_format="pdbx_mmcif_text", max_bytes=4096)
    assert archive["requests"] == ["/data/4HHB", "/files/pdb_00004hhb.cif"]
    assert snapshot.content == raw_entry and file.content == raw_file
    assert snapshot.request == requested
    assert file.request == dict(entry_id="pdb_00004hhb", file_format="pdbx_mmcif_text", max_bytes=4096)
    for value in (snapshot, file):
        assert value.transport["request"]["url"] == value.url
        assert value.transport["request_policy"] == dict(timeout_seconds=3, automatic_redirects=False)
        assert value.transport["body_complete"] is True
        assert value.transport["retained_body_bytes"] == len(value.content)


@pytest.mark.parametrize("case", ["redirect", "not_found", "limited", "short_body"])
def test_error_or_partial_response_is_retained_without_followup(archive, case):
    url = "/files/4HHB.pdb"
    status, body, headers, limit = 200, b"abcdef", {"Content-Type": "text/plain"}, 4096
    if case == "redirect":
        status, headers = 302, {"Location": archive["root"] + "/must_not_follow", "Content-Type": "text/plain"}
    elif case == "not_found":
        status = 404
    elif case == "limited":
        limit = 4
    else:
        headers["Content-Length"] = str(len(body) + 5)
    archive["responses"][url] = status, body, headers
    arguments = dict(entry_id="4HHB", file_format="pdb_3x_text", max_bytes=limit)
    with pytest.raises(AcquisitionError) as error:
        PublicClients(timeout=3).rcsb_structure_file(**arguments)
    snapshot = error.value.snapshot
    assert snapshot is not None and snapshot.content == body[:limit]
    assert snapshot.request == arguments and snapshot.transport["status"] == status
    assert archive["requests"] == [url]
    result = rcsb.rcsb_file_result(snapshot, arguments=arguments, source_ref=SOURCE, artifact_ref=artifact(snapshot))
    assert result["response"]["content_type"] == "text/plain"
    assert result["response"]["body_complete"] is (case in {"redirect", "not_found"})
    assert result["observed_identity"] == dict(native_entry_id=None, state="not_parsed")
    assert ("http_not_success" in [row["code"] for row in result["issues"]]) == (status != 200)


@pytest.mark.parametrize("case", ["redirect", "not_found", "limited", "short_body"])
def test_registered_file_failure_status_retains_source_and_replays_without_get(archive, tmp_path, monkeypatch, case):
    status, body, headers, limit = 200, b"abcdef", {"Content-Type": "text/plain"}, 4096
    if case == "redirect":
        status, headers = 302, {"Location": archive["root"] + "/must_not_follow", "Content-Type": "text/plain"}
    elif case == "not_found":
        status = 404
    elif case == "limited":
        limit = 4
    else:
        headers["Content-Length"] = str(len(body) + 5)
    archive["responses"]["/files/4HHB.pdb"] = status, body, headers
    arguments = dict(entry_id="4HHB", file_format="pdb_3x_text", max_bytes=limit)
    with Store(tmp_path / "store") as store:
        scope = {"subject_refs": store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]}
        tools = ToolRegistry(store, clients=PublicClients(timeout=3))
        key = "rcsb-file-status:" + case
        outcome = asyncio.run(tools.execute_async("public.rcsb.file", arguments, scope=scope, operation_key=key))
        code = "rcsb_http_not_success" if status != 200 else "rcsb_response_incomplete"
        assert outcome["status"] == "partial"
        assert outcome["feedback"]["category"] == "acquisition"
        assert outcome["feedback"]["code"] == code
        result = rcsb.validate_rcsb_receipt(outcome["result"])
        source = store.get(result["source_ref"])
        assert result == rcsb.failed_rcsb_receipt(code, source_ref=source["id"])
        assert source["version"] is None and source["uri"] == archive["root"] + "/files/4HHB.pdb"
        assert outcome["record_refs"] == [source["id"]]
        assert store.get_artifact(source["artifact_ref"]) == body[:limit]
        retained = json.loads(store.get_artifact(source["request_ref"]))
        assert retained["request"] == arguments and retained["transport"]["status"] == status
        assert retained["transport"]["body_complete"] is (status != 200)
        saved = store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (key,)).fetchone()
        assert json.loads(saved["result"]) == outcome
        def forbidden(*args, **kwargs):
            raise AssertionError("Saved RCSB failure attempted another request or publication")
        monkeypatch.setattr(tools.clients, "_http", forbidden)
        monkeypatch.setattr(rcsb, "rcsb_file_result", forbidden)
        monkeypatch.setattr(rcsb, "publish_rcsb_request", forbidden)
        replay = asyncio.run(tools.execute_async("public.rcsb.file", arguments, scope=scope, operation_key=key))
        assert replay == outcome
        assert archive["requests"] == ["/files/4HHB.pdb"]
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 1


@pytest.mark.parametrize("case", ["malformed", "missing_selected", "native_id_difference"])
def test_registered_entry_partial_retains_literal_source_and_cached_status(archive, tmp_path, monkeypatch, case):
    bodies = dict(malformed=b'{"rcsb_id":', missing_selected=b'{"rcsb_id":"4HHB"}',
        native_id_difference=b'{"rcsb_id":"OTHER","rcsb_entry_info":{"polymer_entity_count_protein":0}}')
    body = bodies[case]
    archive["responses"]["/data/4HHB"] = 200, body, {"Content-Type": "application/json"}
    arguments = dict(entry_id="4HHB", fields=["rcsb_entry_info"], max_bytes=4096)
    with Store(tmp_path / "store") as store:
        scope = {"subject_refs": store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]}
        tools = ToolRegistry(store, clients=PublicClients(timeout=3))
        key = "rcsb-entry-status:" + case
        outcome = asyncio.run(tools.execute_async("public.rcsb.entry", arguments, scope=scope, operation_key=key))
        assert outcome["status"] == "partial"
        assert outcome["feedback"]["category"] == "acquisition"
        result = rcsb.validate_rcsb_receipt(outcome["result"])
        source = store.get(result["source_ref"])
        assert source["version"] is None and source["uri"] == archive["root"] + "/data/4HHB"
        assert outcome["record_refs"] == [source["id"]]
        assert store.get_artifact(source["artifact_ref"]) == body
        expected = {"malformed": "rcsb_invalid_native_json", "missing_selected": "rcsb_selected_field_missing",
            "native_id_difference": "rcsb_native_entry_id_differs_from_request"}[case]
        assert result == rcsb.failed_rcsb_receipt(expected, source_ref=source["id"])
        assert outcome["feedback"]["code"] == expected
        retained = json.loads(store.get_artifact(source["request_ref"]))
        assert retained["request"] == arguments and retained["transport"]["status"] == 200
        assert retained["transport"]["body_complete"] is True
        if case == "native_id_difference":
            native = json.loads(body)
            assert native["rcsb_id"] == "OTHER" and native["rcsb_entry_info"]["polymer_entity_count_protein"] == 0
        elif case == "missing_selected":
            assert json.loads(body) == {"rcsb_id": "4HHB"}
        else:
            with pytest.raises(json.JSONDecodeError):
                json.loads(body)
        def forbidden(*args, **kwargs):
            raise AssertionError("Saved RCSB qualification attempted another request or projection")
        monkeypatch.setattr(tools.clients, "_http", forbidden)
        monkeypatch.setattr(rcsb, "rcsb_entry_result", forbidden)
        monkeypatch.setattr(rcsb, "publish_rcsb_request", forbidden)
        replay = asyncio.run(tools.execute_async("public.rcsb.entry", arguments, scope=scope, operation_key=key))
        assert replay == outcome and archive["requests"] == ["/data/4HHB"]
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 1


def test_selected_entry_values_keep_order_null_missing_zero_and_raw_unselected_data(archive):
    native = dict(rcsb_id="4HHB", cell=None, rcsb_entry_info=dict(polymer_entity_count_protein=0, resolution_combined=None),
        citation=[dict(title="UNSELECTED_CITATION_MUST_NOT_APPEAR")])
    snapshot, arguments = entry(archive, json.dumps(native).encode(), fields=["cell", "exptl", "rcsb_entry_info"])
    result = rcsb.rcsb_entry_result(snapshot, arguments=arguments, source_ref=SOURCE, artifact_ref=artifact(snapshot))
    assert [row["field"] for row in result["values"]] == arguments["fields"]
    assert [row["state"] for row in result["values"]] == ["native_null", "missing", "present"]
    assert result["values"][2]["value"] == native["rcsb_entry_info"]
    assert result["observed_identity"] == dict(native_entry_id="4HHB", state="present", relation="exact_literal_match")
    assert "UNSELECTED_CITATION_MUST_NOT_APPEAR" not in json.dumps(result)
    assert b"UNSELECTED_CITATION_MUST_NOT_APPEAR" in snapshot.content


@pytest.mark.parametrize("native,state", [("OTHER", "present"), (None, "native_null"), (False, "invalid"), ({}, "missing")])
def test_requested_id_is_never_substituted_for_missing_or_different_native_id(archive, native, state):
    body = {} if state == "missing" else dict(rcsb_id=native)
    snapshot, arguments = entry(archive, json.dumps(body).encode())
    result = rcsb.rcsb_entry_result(snapshot, arguments=arguments, source_ref=SOURCE, artifact_ref=artifact(snapshot))
    assert result["requested"]["entry_id"] == "4HHB" and result["observed_identity"]["state"] == state
    assert result["observed_identity"]["native_entry_id"] == (native if state == "present" else None)
    assert result["observed_identity"]["relation"] == ("different_literal" if state == "present" else "unknown")


@pytest.mark.parametrize("raw,state", [(b'{"rcsb_id":"4HHB","rcsb_id":"OTHER"}', "decode_failed"),
    (b'{"rcsb_id":NaN}', "decode_failed"), (b'{"rcsb_id":"\\ud800"}', "decode_failed"),
    (b"null", "non_object"), (b"[]", "non_object")])
def test_invalid_or_nonobject_json_is_not_fabricated_missing_metadata(archive, raw, state):
    snapshot, arguments = entry(archive, raw)
    result = rcsb.rcsb_entry_result(snapshot, arguments=arguments, source_ref=SOURCE, artifact_ref=artifact(snapshot))
    assert result["parse_state"] == state and snapshot.content == raw
    assert result["values"] == [dict(field="rcsb_id", state="unavailable", value=None)]
    assert result["observed_identity"]["state"] == "unavailable"


@pytest.mark.parametrize("file_format", list(rcsb.FILE_FORMATS))
def test_file_format_is_only_selected_processing_and_observed_type_stays_separate(archive, file_format):
    body = b"not a parsed structure\x00"
    suffix = rcsb.FILE_FORMATS[file_format]
    archive["responses"]["/files/4HHB." + suffix] = (200, body, {"Content-Type": "application/json"})
    arguments = dict(entry_id="4HHB", file_format=file_format, max_bytes=4096)
    snapshot = PublicClients(timeout=3).rcsb_structure_file(**arguments)
    result = rcsb.rcsb_file_result(snapshot, arguments=arguments, source_ref=SOURCE, artifact_ref=artifact(snapshot))
    assert result["file"] == dict(artifact_ref=artifact(snapshot), sha256=hashlib.sha256(body).hexdigest(),
        byte_length=len(body), format=file_format)
    assert result["response"]["content_type"] == "application/json"
    assert result["observed_identity"] == dict(native_entry_id=None, state="not_parsed")


@pytest.mark.parametrize("field,value", [("status", 200.0), ("body_complete", 1), ("declared_body_bytes", False)])
def test_transport_type_aliases_remain_unknown_instead_of_verified(archive, field, value):
    snapshot, arguments = entry(archive)
    transport = {**snapshot.transport, field: value}
    changed = replace(snapshot, transport=transport)
    result = rcsb.rcsb_entry_result(changed, arguments=arguments, source_ref=SOURCE, artifact_ref=artifact(snapshot))
    output = "http_status" if field == "status" else field
    assert result["response"][output] is None
    assert any(row["code"] == "transport_metadata_unavailable" for row in result["issues"])
    assert changed.transport[field] == value


def test_snapshot_operand_and_artifact_identity_cannot_be_replaced(archive):
    snapshot, arguments = entry(archive)
    with pytest.raises(ValueError, match="rcsb_artifact_identity_conflict"):
        rcsb.rcsb_entry_result(snapshot, arguments=arguments, source_ref=SOURCE, artifact_ref="artifact_" + "f" * 64)
    with pytest.raises(ValueError):
        rcsb.rcsb_entry_result(replace(snapshot, request={**arguments, "max_bytes": 4096.0}),
            arguments=arguments, source_ref=SOURCE, artifact_ref=artifact(snapshot))


@pytest.mark.parametrize("parse_state", ["decode_failed", "non_object"])
def test_external_entry_dto_cannot_claim_native_identity_after_decode_failure(archive, parse_state):
    snapshot, arguments = entry(archive)
    result = rcsb.rcsb_entry_result(snapshot, arguments=arguments, source_ref=SOURCE, artifact_ref=artifact(snapshot))
    result["parse_state"] = parse_state
    result["values"] = [dict(field="rcsb_id", state="unavailable", value=None)]
    with pytest.raises(ValueError):
        rcsb.validate_rcsb_entry_result(result)


@pytest.mark.parametrize("kind", ["entry", "file"])
def test_result_json_schema_owns_recursive_native_values_when_embedded(archive, kind):
    snapshot, arguments = entry(archive, b'{"rcsb_id":"4HHB","rcsb_entry_info":{"nested":[0,null]}}',
        fields=["rcsb_entry_info"])
    if kind == "entry":
        result = rcsb.rcsb_entry_result(snapshot, arguments=arguments, source_ref=SOURCE, artifact_ref=artifact(snapshot))
        schema = rcsb.RCSB_ENTRY_RESULT_SCHEMA
    else:
        archive["responses"]["/files/4HHB.cif"] = (200, b"data_literal\n", {"Content-Type": "chemical/x-mmcif"})
        arguments = dict(entry_id="4HHB", file_format="pdbx_mmcif_text", max_bytes=4096)
        snapshot = PublicClients(timeout=3).rcsb_structure_file(**arguments)
        result = rcsb.rcsb_file_result(snapshot, arguments=arguments, source_ref=SOURCE, artifact_ref=artifact(snapshot))
        schema = rcsb.RCSB_FILE_RESULT_SCHEMA
    parent = dict(type="object", properties=dict(arbitrary=schema), required=["arbitrary"], additionalProperties=False,
        **{"$defs": {"NativeJSON": {"type": "null"}}})
    Draft202012Validator.check_schema(parent)
    assert Draft202012Validator(parent).is_valid(dict(arbitrary=result))
    altered = deepcopy(result)
    altered["unexpected"] = None
    assert not Draft202012Validator(parent).is_valid(dict(arbitrary=altered))


def _controller(path, initial):
    return FixtureController(str(path), initial, 2)


def _credit(*args, **kwargs):
    return 0


def _tables(store):
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: sorted((tuple(row) for row in store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')), key=repr)
        for name in names}


def _files(directory):
    return {str(path.relative_to(directory)): (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size)
        for path in directory.rglob("*") if path.is_file()}


@pytest.mark.parametrize("kind,partial", [("entry", False), ("entry", True), ("file", False)])
def test_legacy_rich_cached_outcome_keeps_its_literal_dto_and_status(archive, tmp_path, monkeypatch, kind, partial):
    """Engineer the old publication via its real writer, without runtime history."""
    if kind == "entry":
        raw = b'{"rcsb_id":"4HHB"}' if partial else b'{"rcsb_id":"4HHB","rcsb_entry_info":{"count":0}}'
        snapshot, arguments = entry(archive, raw, fields=["rcsb_entry_info"])
        expected_path = "/data/4HHB"
    else:
        raw = b"data_literal\n_entry.id 4HHB\n"
        archive["responses"]["/files/4HHB.cif"] = (200, raw, {"Content-Type": "chemical/x-mmcif"})
        arguments = dict(entry_id="4HHB", file_format="pdbx_mmcif_text", max_bytes=4096)
        snapshot = PublicClients(timeout=3).rcsb_structure_file(**arguments)
        expected_path = "/files/4HHB.cif"
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store)
        scope = {"subject_refs": store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]}
        name, key = "public.rcsb." + kind, "engineered-legacy-rcsb-cache"
        token = tools._publications.set([])
        try:
            with store.transaction():
                legacy, refs = tools._import(name, arguments, snapshot)
                outcome = dict(status="partial" if partial else "completed",
                    operation_ref=identity("operation", {"key": key, "name": name, "arguments": arguments}),
                    record_refs=refs, result=legacy, feedback=({"category": "representation",
                        "code": "rcsb_selected_response_partial", "source_ref": legacy["source_ref"]} if partial else None))
                tools._save(key, name, arguments, scope, outcome)
        finally:
            tools._publications.reset(token)
        source = store.get(legacy["source_ref"])
        assert store.get_artifact(source["artifact_ref"]) == raw
        assert json.loads(store.get_artifact(source["request_ref"])) == json.loads(canonical({
            "request": arguments, "transport": snapshot.transport}))
        assert legacy["version"] == "rcsb_" + kind + "_result_v1"
        if partial:
            assert legacy["values"] == [dict(field="rcsb_entry_info", state="missing", value=None)]
        before, files = _tables(store), _files(store.path / "artifacts")
        def forbidden(*args, **kwargs):
            raise AssertionError("Legacy cache attempted HTTP, entity reads, projection or publication")
        monkeypatch.setattr(PublicClients, "_http", forbidden)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        monkeypatch.setattr(rcsb, "rcsb_entry_result", forbidden)
        monkeypatch.setattr(rcsb, "rcsb_file_result", forbidden)
        monkeypatch.setattr(rcsb, "publish_rcsb_request", forbidden)
        replay = asyncio.run(tools.execute_async(name, arguments, scope=scope, operation_key=key))
        assert replay == outcome and replay["result"] == legacy
        assert _tables(store) == before and _files(store.path / "artifacts") == files
        assert archive["requests"] == [expected_path]


def _registered_path(tmp_path, monkeypatch, *, client, max_bytes, expected_urls,
                     metadata=None, structure=None, live=False):
    requested_http, original_http = [], client._http
    def observed_http(*args, **kwargs):
        requested_http.append(dict(service=args[0], url=args[1], max_bytes=kwargs["max_bytes"],
            follow_redirects=kwargs["follow_redirects"]))
        return original_http(*args, **kwargs)
    monkeypatch.setattr(client, "_http", observed_http)
    def no_native(*args, **kwargs):
        raise AssertionError("Acquisition attempted a native worker")
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", no_native)
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=client)
        scope = {"subject_refs": store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]}
        directory = tmp_path / "run"
        question = "Retain the caller-selected RCSB evidence."
        provider = ScriptedProvider([
            action("public.rcsb.entry", dict(entry_id="4HHB", fields=["rcsb_entry_info"], max_bytes=max_bytes)),
            action("public.rcsb.file", dict(entry_id="4HHB", file_format="pdbx_mmcif_text", max_bytes=max_bytes))])
        def make(actor):
            return Workflow(store, tools, actor, directory, "rcsb-engineering", _controller,
                _credit, project_child_credit=_credit, root_role="improvement",
                episode_record_receipts=True, initial_known_record_refs=[])
        workflow = make(provider)
        root = workflow.build("improvement", "root", question, scope)
        baseline = set(workflow.receipts.known(root.source.episode_id))
        assert workflow.permits_common_action(root.source, "tool")
        assert {"public.rcsb.entry", "public.rcsb.file"} <= {
            item["name"] for item in workflow.catalog(scope, source=root.source)}
        record = asyncio.run(root.run_async(workflow.context))
        final = asyncio.run(root.build_result(record)).as_record()
        assert [row["url"] for row in requested_http] == expected_urls
        assert all(row["service"] == "rcsb_pdb" and row["max_bytes"] == max_bytes
            and row["follow_redirects"] is False for row in requested_http)
        assert len(provider.contexts) == 2
        rows = list(store.db.execute("SELECT * FROM tool_operations ORDER BY operation_key"))
        assert len(rows) == 2
        outcomes = {row["name"]: json.loads(row["result"]) for row in rows}
        assert all(value["status"] == "completed" for value in outcomes.values())
        file_result = rcsb.validate_rcsb_receipt(outcomes["public.rcsb.file"]["result"])
        entry_result = rcsb.validate_rcsb_receipt(outcomes["public.rcsb.entry"]["result"])
        entry_source = store.get(entry_result["source_ref"])
        file_source = store.get(file_result["source_ref"])
        assert entry_source["version"] is file_source["version"] is None
        assert entry_source["accession"] == file_source["accession"] == "4HHB"
        assert entry_source["artifact_ref"] == entry_result["data_ref"]
        acquired_metadata = store.get_artifact(entry_source["artifact_ref"])
        acquired_structure = store.get_artifact(file_source["artifact_ref"])
        if metadata is not None:
            assert acquired_metadata == metadata
        if structure is not None:
            assert acquired_structure == structure
        native = json.loads(acquired_metadata)
        assert native["rcsb_id"] == "4HHB" and "rcsb_entry_info" in native
        native_results = {}
        for name, source, result, raw in (
                ("entry", entry_source, entry_result, acquired_metadata),
                ("file", file_source, file_result, acquired_structure)):
            assert result == {"acquired": True, "source_ref": source["id"],
                "data_ref": source["artifact_ref"], "failure_code": None}
            assert outcomes["public.rcsb." + name]["record_refs"] == [source["id"], source["artifact_ref"]]
            assert source["artifact_ref"] == "artifact_" + hashlib.sha256(raw).hexdigest()
            assert store.get(source["artifact_ref"])["size"] == len(raw)
            control_raw = store.get_artifact(source["request_ref"])
            control = json.loads(control_raw)
            assert control_raw == canonical(control).encode()
            assert control["request"] == {"entry_id": "4HHB", "max_bytes": max_bytes,
                **({"fields": ["rcsb_entry_info"]} if name == "entry" else {"file_format": "pdbx_mmcif_text"})}
            assert control["transport"]["status"] == 200 and control["transport"]["body_complete"] is True
            retained = SourceSnapshot(rcsb.SERVICE, source["uri"], control["request"], source["retrieved_at"], raw,
                store.get(source["artifact_ref"])["media_type"], control["transport"])
            builder = rcsb.rcsb_entry_result if name == "entry" else rcsb.rcsb_file_result
            native_results[name] = builder(retained, arguments=control["request"],
                source_ref=source["id"], artifact_ref=source["artifact_ref"])
        assert native_results["entry"]["observed_identity"] == dict(
            native_entry_id="4HHB", state="present", relation="exact_literal_match")
        assert native_results["entry"]["values"] == [
            dict(field="rcsb_entry_info", state="present", value=native["rcsb_entry_info"])]
        assert native_results["file"]["observed_identity"] == dict(native_entry_id=None, state="not_parsed")
        assert native_results["file"]["file"]["sha256"] == hashlib.sha256(acquired_structure).hexdigest()
        assert native_results["file"]["file"]["byte_length"] == len(acquired_structure)
        contexts = EpisodeReturnRecords(store, workflow.run_id, failure_prefix="rcsb_test_")
        episodes = list(store.db.execute("SELECT episode_id,path FROM runtime_episodes ORDER BY json_array_length(path)"))
        assert len(episodes) == 1 and json.loads(episodes[0]["path"]) == [["improvement", "root"]]
        caller = contexts.context(episodes[0]["episode_id"])
        received, path = workflow.services.read_received_molecular_input(caller,
            file_result["source_ref"], "source", file_format="pdbx_mmcif_text")
        assert received["failure"] is None and path.read_bytes() == acquired_structure
        assert received["input"]["byte_verification"] == "verified"
        returned = {entry_result["source_ref"], entry_result["data_ref"], file_result["source_ref"], file_result["data_ref"]}
        known = set(workflow.receipts.known(caller.episode_id))
        assert known == baseline | returned
        assert {row[0] for row in store.db.execute("SELECT record_ref FROM runtime_record_receipts "
            "WHERE episode_id=? AND receipt_kind='own_action'", (caller.episode_id,))} == returned
        assert {entry_source["request_ref"], file_source["request_ref"]}.isdisjoint(known)
        for private_ref in (entry_source["request_ref"], file_source["request_ref"]):
            private, private_path = workflow.services.read_received_molecular_input(caller,
                private_ref, "artifact", file_format="text")
            assert private_path is None and private["input"] is None
            assert private["failure"]["code"] == "reference_not_received"
        assert store.db.execute("SELECT count(*) FROM runtime_forms").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_report_attempts").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_record_receipts WHERE receipt_kind='child_form'").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM records WHERE record_type='observation'").fetchone()[0] == 0
        unknown = store.artifact(b"unreceived fixture", "application/octet-stream")
        denied, path = workflow.services.read_received_molecular_input(caller, unknown, "artifact", file_format="text")
        assert path is None and denied["input"] is None and denied["failure"]["code"] == "reference_not_received"
        counts = {name: store.db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in
            ("runtime_actions", "runtime_observations", "runtime_model_calls", "tool_operations")}
        assert counts == dict(runtime_actions=2, runtime_observations=2, runtime_model_calls=2, tool_operations=2)
        actions = [json.loads(row[0]) for row in store.db.execute("SELECT action FROM runtime_actions ORDER BY decision_index")]
        assert [item["kind"] for item in actions] == ["tool", "tool"]
        assert [item["tool"] for item in actions] == ["public.rcsb.entry", "public.rcsb.file"]
        before_tables, before_files = _tables(store), _files(store.path / "artifacts")
        before_archive = _files(directory / "archive")
        def forbidden(*args, **kwargs):
            raise AssertionError("Closed RCSB replay attempted acquisition")
        monkeypatch.setattr(client, "_http", forbidden)
        actual_get = Store.get_artifact
        def controls_only(current, reference):
            assert reference not in {entry_source["artifact_ref"], file_source["artifact_ref"]}, "closed replay reopened native entity"
            return actual_get(current, reference)
        monkeypatch.setattr(Store, "get_artifact", controls_only)
        monkeypatch.setattr(ToolRegistry, "execute_async", forbidden)
        monkeypatch.setattr(rcsb, "rcsb_entry_result", forbidden)
        monkeypatch.setattr(rcsb, "rcsb_file_result", forbidden)
        monkeypatch.setattr(rcsb, "publish_rcsb_request", forbidden)
        replay_provider = ScriptedProvider([])
        replay = make(replay_provider)
        replay_root = replay.build("improvement", "root", question, scope)
        replay_record = asyncio.run(replay_root.run_async(replay.context))
        assert asyncio.run(replay_root.build_result(replay_record)).as_record() == final
        assert replay_provider.contexts == [] and len(requested_http) == 2
        assert _tables(store) == before_tables and _files(store.path / "artifacts") == before_files
        assert _files(directory / "archive") == before_archive
        (tmp_path / "RCSB_ACQUISITION.json").write_text(json.dumps(dict(
            qualification=("live caller-selected RCSB GETs; scripted Workflow; no coordinate parsing or native math" if live else
                "loopback engineering RCSB-shaped replies; scripted Workflow; no live archive claim"),
            http_requests=requested_http, counts=counts, entry_result=entry_result, file_result=file_result,
            native_qualifications_from_retained_sources=native_results,
            current_episode_received_source_and_data_files=True, unreceived_file_denied=True,
            closed_current_episode_replay_without_http=True, tables_and_artifacts_value_unchanged=True,
            scope="Ordinary improvement episode; two selected actions; no child, scientific report, coordinate parser or numerical analysis."),
            indent=2) + "\n")


def test_registered_rcsb_calls_deliver_real_source_file_receipts_without_native_work(archive, tmp_path, monkeypatch):
    metadata = b'{"rcsb_id":"4HHB","rcsb_entry_info":{"polymer_entity_count_protein":0}}'
    structure = b"data_literal\n_entry.id 4HHB\n"
    archive["responses"]["/data/4HHB"] = (200, metadata, {"Content-Type": "application/json"})
    archive["responses"]["/files/4HHB.cif"] = (200, structure, {"Content-Type": "chemical/x-mmcif"})
    _registered_path(tmp_path, monkeypatch, client=PublicClients(timeout=3), max_bytes=4096,
        expected_urls=[archive["root"] + "/data/4HHB", archive["root"] + "/files/4HHB.cif"],
        metadata=metadata, structure=structure)
    assert archive["requests"] == ["/data/4HHB", "/files/4HHB.cif"]


def test_live_selected_rcsb_entry_and_mmcif_source_file_delivery(tmp_path, monkeypatch):
    if os.environ.get("HMMER_NATIVE_ORACLE_RCSB_LIVE") != "1":
        pytest.skip("requires explicitly selected HMMER_NATIVE_ORACLE_RCSB_LIVE=1")
    _registered_path(tmp_path, monkeypatch, client=PublicClients(timeout=90), max_bytes=2 * 1024**2,
        expected_urls=["https://data.rcsb.org/rest/v1/core/entry/4HHB", "https://files.rcsb.org/download/4HHB.cif"],
        live=True)
