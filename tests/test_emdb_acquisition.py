"""Controlled metadata/HTTP proof, with a separately gated single live GET."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import threading

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.acquisition import PublicClients, SourceSnapshot
from gene_annotation_episode import emdb_acquisition as emdb
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider
from test_scientific_process_runtime import action


# These are engineering EMDB-shaped JSON operands, not a retained live reply or
# an assertion that arbitrary native fields have a particular scientific unit.
NATIVE = {"emdb_id": "EMD-8117", "map": {"unknown_unit_object": {"valueOf_": 0, "units": "literal-unit"}},
    "sample": {"macromolecule_list": {"macromolecule": [{"macromolecule_id": 2}, {"macromolecule_id": 1}]}},
    "structure_determination_list": {"structure_determination": [
        {"method": "first-literal", "image_processing": [{"final_reconstruction": {"resolution": None}}]},
        {"method": "second-literal", "image_processing": [{"final_reconstruction": {
            "resolution": {"valueOf_": 2.8, "units": "A"}}}]}]},
    "crossreferences": {"pdb_list": {"pdb_reference": [{"pdb_id": "5irx", "relationship": {"in_frame": "FULLOVERLAP"}}]},
        "emdb_list": {"emdb_reference": [{"emdb_id": "EMD-8118", "relationship": {"other": "other EM volume"}}]},
        "citation_list": {"literal_uninterpreted": "retained native text"}},
    "unknown_column": [None, 0, False, [], {}]}


def snapshot(raw=None, *, native=NATIVE, max_bytes=4096):
    raw = json.dumps(native, ensure_ascii=False, separators=(",", ":")).encode() if raw is None else raw
    args = {"entry_id": "EMD-8117", "max_bytes": max_bytes}
    url = emdb.emdb_entry_url(args["entry_id"])
    return SourceSnapshot(emdb.SERVICE, url, args, "2026-10-31T00:00:00+00:00", raw,
        "application/json", {"status": 200, "body_complete": True,
            "headers": {"content-type": "application/json"}, "observed_body_bytes": len(raw),
            "declared_body_bytes": len(raw), "retained_body_bytes": len(raw),
            "response_byte_limit": max_bytes, "request": {"method": "GET", "url": url},
            "request_policy": {"automatic_redirects": False, "timeout_seconds": 3}})


def project(value):
    return emdb.emdb_entry_result(value, arguments={"entry_id": "EMD-8117", "max_bytes": value.request["max_bytes"]},
        source_ref="source_" + "a" * 24, artifact_ref="artifact_" + hashlib.sha256(value.content).hexdigest())


@pytest.mark.parametrize("changed", [
    {"entry_id": "8117"}, {"entry_id": "emd-8117"}, {"entry_id": "EMD-8117\n"},
    {"entry_id": "EMD-8117\r"}, {"entry_id": "EMD-８１１７"}, {"entry_id": "EMD-8117/other"},
    {"entry_id": " EMD-8117"}, {"entry_id": "EMD-"}, {"entry_id": True},
    {"max_bytes": True}, {"max_bytes": 1.0}, {"max_bytes": 0}, {"fields": []},
])
def test_only_literal_identifier_and_explicit_byte_limit_are_accepted(changed):
    with pytest.raises(ValueError):
        emdb.validate_emdb_entry_arguments({"entry_id": "EMD-8117", "max_bytes": 4096, **changed})


def test_full_native_arrays_associations_units_null_zero_and_unknown_columns_survive():
    original = snapshot()
    result = project(original)
    assert result["native_json"] == NATIVE and result["issues"] == []
    assert result["requested"] == {"entry_id": "EMD-8117", "max_bytes": 4096}
    assert len(result["native_json"]["structure_determination_list"]["structure_determination"]) == 2
    assert result["native_json"]["unknown_column"] == [None, 0, False, [], {}]
    result["native_json"]["unknown_column"].append("detached")
    assert json.loads(original.content) == NATIVE
    assert emdb.emdb_entry_url("EMD-0008117").endswith("/EMD-0008117")


@pytest.mark.parametrize("native,code", [({}, "native_entry_id_missing"),
    ({"emdb_id": None}, "native_entry_id_null"), ({"emdb_id": False}, "native_entry_id_invalid"),
    ({"emdb_id": "EMD-8118"}, "native_entry_id_differs_from_request")])
def test_native_identity_is_literal_and_never_filled_from_request(native, code):
    result = project(snapshot(native=native))
    assert result["native_json"] == native
    assert result["issues"] == [{"code": code, "pointer": "/emdb_id"}]


@pytest.mark.parametrize("raw,state", [(b'{"emdb_id":1,"emdb_id":2}', "decode_failed"),
    (b'{"emdb_id":NaN}', "decode_failed"), (b'{"x":Infinity}', "decode_failed"),
    (b'{"x":"\\ud800"}', "decode_failed"), (b'\xff', "decode_failed"),
    (b'null', "non_object"), (b'[0,null,false]', "non_object")])
def test_invalid_json_and_nonobjects_remain_distinct_retained_response_states(raw, state):
    result = project(snapshot(raw))
    assert result["parse_state"] == state
    assert result["native_json"] == (None if state == "decode_failed" else json.loads(raw))
    assert result["response"]["retained_bytes"] == len(raw)
    assert result["issues"][0]["pointer"] == ""


@pytest.mark.parametrize("field,value", [("status", 200.0), ("body_complete", 1),
    ("observed_body_bytes", False), ("retained_body_bytes", True)])
def test_transport_type_aliases_are_not_observed_facts(field, value):
    original = snapshot()
    metadata = deepcopy(original.transport)
    metadata[field] = value
    result = project(replace(original, transport=metadata))
    assert {"code": "transport_metadata_unavailable", "pointer": "/transport/" + field} in result["issues"]
    public_field = "http_status" if field == "status" else field
    if public_field in result["response"]:
        assert result["response"][public_field] is None


@pytest.mark.parametrize("policy", [{"automatic_redirects": 0, "timeout_seconds": 3},
    {"automatic_redirects": False, "timeout_seconds": True}])
def test_selected_no_redirect_policy_rejects_bool_integer_aliases(policy):
    original = snapshot()
    with pytest.raises(ValueError, match="transport_policy_conflict"):
        project(replace(original, transport={**original.transport, "request_policy": policy}))


@pytest.mark.parametrize("changed", [{"service": "rcsb_pdb"}, {"url": "https://example.invalid/EMD-8117"},
    {"request": {"entry_id": "EMD-8118", "max_bytes": 4096}},
    {"request": {"entry_id": "EMD-8117", "max_bytes": 4096, "fields": []}}])
def test_response_cannot_be_rebound_to_another_selected_operand(changed):
    with pytest.raises(ValueError):
        project(replace(snapshot(), **changed))


def test_original_artifact_digest_and_external_dto_states_are_checked():
    original = snapshot()
    with pytest.raises(ValueError, match="artifact_identity_conflict"):
        emdb.emdb_entry_result(original, arguments=original.request,
            source_ref="source_" + "a" * 24, artifact_ref="artifact_" + "0" * 64)
    result = project(original)
    for key, altered in (("parse_state", "decode_failed"), ("source_ref", result["source_ref"] + "\n"),
            ("raw_artifact_ref", result["raw_artifact_ref"] + "\n")):
        with pytest.raises(ValueError):
            emdb.validate_emdb_entry_result({**result, key: altered})


@pytest.mark.parametrize("response,issues", [
    ({"http_status": 404}, []),
    ({"body_complete": False}, []),
    ({}, [{"code": "http_not_success", "pointer": "/transport/status"}]),
    ({}, [{"code": "response_incomplete", "pointer": "/transport/body_complete"}]),
    ({"http_status": None}, []),
    ({"body_complete": None}, [{"code": "response_incomplete", "pointer": "/transport/body_complete"}]),
    ({}, [{"code": "transport_metadata_unavailable", "pointer": "/transport/status"}]),
    ({}, [{"code": "transport_metadata_unavailable", "pointer": "/transport/headers/content-type"}]),
    ({}, [{"code": "transport_metadata_unavailable", "pointer": "/transport/body_complete"}]),
    ({}, [{"code": "transport_metadata_unavailable", "pointer": "/transport/observed_body_bytes"}]),
    ({}, [{"code": "transport_metadata_unavailable", "pointer": "/transport/declared_body_bytes"}]),
    ({"http_status": 404}, [{"code": "http_not_success", "pointer": "/transport/body_complete"}]),
    ({"body_complete": False}, [{"code": "response_incomplete", "pointer": "/transport/status"}]),
    ({}, [{"code": "transport_metadata_unavailable", "pointer": "/emdb_id"}]),
])
def test_external_dto_rejects_response_issue_contradictions_and_wrong_pairings(response, issues):
    result = project(snapshot())
    result["response"].update(response)
    result["issues"] = issues
    with pytest.raises(ValueError):
        emdb.validate_emdb_entry_result(result)


@pytest.mark.parametrize("response,issues", [
    ({"http_status": 404}, [{"code": "http_not_success", "pointer": "/transport/status"}]),
    ({"body_complete": False}, [{"code": "response_incomplete", "pointer": "/transport/body_complete"}]),
    ({"http_status": None}, [{"code": "transport_metadata_unavailable", "pointer": "/transport/status"}]),
    ({"body_complete": None}, [
        {"code": "transport_metadata_unavailable", "pointer": "/transport/body_complete"},
        {"code": "response_incomplete", "pointer": "/transport/body_complete"}]),
    ({"content_type": None}, [{"code": "transport_metadata_unavailable", "pointer": "/transport/headers/content-type"}]),
    ({"observed_body_bytes": None}, [{"code": "transport_metadata_unavailable", "pointer": "/transport/observed_body_bytes"}]),
    ({"declared_body_bytes": None}, [{"code": "transport_metadata_unavailable", "pointer": "/transport/declared_body_bytes"}]),
    ({}, [{"code": "transport_metadata_unavailable", "pointer": "/transport/retained_body_bytes"}]),
    ({}, [{"code": "transport_metadata_unavailable", "pointer": "/transport/response_byte_limit"}]),
    ({"content_type": None, "observed_body_bytes": None, "declared_body_bytes": None}, []),
])
def test_external_dto_preserves_qualified_http_unknowns_and_omitted_native_transport_values(response, issues):
    result = project(snapshot())
    result["response"].update(response)
    result["issues"] = issues
    assert emdb.validate_emdb_entry_result(result) == result


@pytest.mark.parametrize("code,pointer", [
    ("invalid_native_json", ""), ("response_not_object", ""),
    ("native_entry_id_missing", "/emdb_id"), ("native_entry_id_null", "/emdb_id"),
    ("native_entry_id_invalid", "/emdb_id"), ("native_entry_id_differs_from_request", "/emdb_id"),
])
def test_external_dto_rejects_spurious_native_parse_and_identity_issues(code, pointer):
    result = project(snapshot())
    result["issues"] = [{"code": code, "pointer": pointer}]
    with pytest.raises(ValueError):
        emdb.validate_emdb_entry_result(result)


@pytest.mark.parametrize("raw", [b'{', b'null', b'{}', b'{"emdb_id":null}',
    b'{"emdb_id":false}', b'{"emdb_id":"EMD-8118"}'])
def test_external_dto_requires_exact_native_issue_and_pointer(raw):
    result = project(snapshot(raw))
    assert emdb.validate_emdb_entry_result(result) == result
    original = result["issues"][0]
    for issues in [[], [{**original, "pointer": "/emdb_id" if original["pointer"] == "" else ""}]]:
        with pytest.raises(ValueError):
            emdb.validate_emdb_entry_result({**result, "issues": issues})


def test_owned_result_schema_embeds_without_borrowing_parent_native_json_definition():
    result = project(snapshot())
    schema = {"type": "object", "$defs": {"NativeJSON": {"const": "wrong outer definition"}},
        "properties": {"entry": deepcopy(emdb.EMDB_ENTRY_RESULT_SCHEMA)}, "required": ["entry"],
        "additionalProperties": False}
    assert Draft202012Validator(schema).is_valid({"entry": result})
    # Draft shape alone does not authenticate Source or artifact possession.
    assert result["native_json"]["unknown_column"][1] == 0


@pytest.fixture
def archive(monkeypatch):
    state = {"requests": [], "status": 200, "raw": json.dumps(NATIVE).encode(), "headers": {}}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            state["requests"].append(self.path)
            self.send_response(state["status"])
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("X-UniProt-Release", "not-an-EMDB-version")
            for key, value in state["headers"].items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(state["raw"])))
            self.end_headers()
            self.wfile.write(state["raw"])
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    state["root"] = "http://127.0.0.1:" + str(server.server_port) + "/entry/"
    monkeypatch.setattr(emdb, "ENTRY_ROOT", state["root"])
    try:
        yield state
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.mark.parametrize("status,limit,expected", [(302, 4096, "partial"), (404, 4096, "partial"),
    (200, 8, "partial")])
def test_registered_http_failure_or_limited_reply_retains_real_source_and_cached_status(
        archive, tmp_path, status, limit, expected):
    archive.update(status=status, raw=json.dumps(NATIVE).encode())
    archive["headers"] = {"Location": archive["root"] + "must-not-follow"} if status == 302 else {}
    with Store(tmp_path / "store") as store:
        scope = {"subject_refs": store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]}
        tools = ToolRegistry(store, clients=PublicClients(timeout=3))
        args = {"entry_id": "EMD-8117", "max_bytes": limit}
        outcome = tools.execute("public.emdb.entry", args, scope=scope, operation_key="emdb-boundary")
        assert outcome["status"] == expected
        result = emdb.validate_emdb_receipt(outcome["result"])
        source = store.get(result["source_ref"])
        assert outcome["record_refs"] == [source["id"]] and source["version"] is None
        assert not result['acquired'] and result['data_ref'] is None
        assert result['failure_code'] == ('emdb_http_not_success' if status != 200 else 'emdb_response_incomplete')
        assert store.get_artifact(source["artifact_ref"]) == archive["raw"][:limit]
        control = json.loads(store.get_artifact(source['request_ref']))
        assert control['request'] == args and control['transport']['status'] == status
        assert tools.execute("public.emdb.entry", args, scope=scope, operation_key="emdb-boundary") == outcome
        assert archive["requests"] == ["/entry/EMD-8117"]


def _controller(path, initial):
    return FixtureController(str(path), initial, 1)


def _tables(store):
    return {name: list(map(tuple, store.db.execute('SELECT * FROM "' + name + '" ORDER BY rowid')))
        for name, in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}


def _files(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*") if path.is_file()}


def _selected_path(tmp_path, monkeypatch, *, client, live=False):
    calls, original = [], client._http
    def observed(*args, **kwargs):
        calls.append({"service": args[0], "url": args[1], "max_bytes": kwargs["max_bytes"],
            "follow_redirects": kwargs["follow_redirects"]})
        return original(*args, **kwargs)
    monkeypatch.setattr(client, "_http", observed)
    def forbidden(*args, **kwargs):
        raise AssertionError("metadata acquisition attempted native work or closed replay HTTP")
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=client)
        scope = {'subject_refs': store.create_problem(raw_sequence='MKWAA', molecule='protein')['subject_refs']}
        directory = tmp_path / 'run'
        question = ('Evaluate structural evidence for the supplied protein, keeping unresolved its correspondence '
            'to caller-selected reference data. This acquisition step does not settle a scientific conclusion.')
        args = {"entry_id": "EMD-8117", "max_bytes": 2 * 1024**2}
        provider = ScriptedProvider([action("public.emdb.entry", args)])
        def make(provider):
            return Workflow(store, tools, provider, directory, "emdb-acquisition", _controller,
                lambda *a, **k: 0, project_child_credit=lambda *a, **k: 0,
                root_role='improvement', episode_record_receipts=True, initial_known_record_refs=[])
        workflow = make(provider)
        root = workflow.build('improvement', 'root', question, scope)
        baseline = set(workflow.receipts.known(root.source.episode_id))
        assert workflow.permits_common_action(root.source, 'tool')
        assert 'public.emdb.entry' in {item['name'] for item in workflow.catalog(scope, source=root.source)}
        record = asyncio.run(root.run_async(workflow.context))
        final = asyncio.run(root.build_result(record)).as_record()
        rows = list(store.db.execute("SELECT * FROM tool_operations"))
        assert len(rows) == 1 and rows[0]["name"] == "public.emdb.entry"
        outcome = json.loads(rows[0]["result"])
        assert outcome["status"] == "completed"
        result = emdb.validate_emdb_receipt(outcome["result"])
        source = store.get(result["source_ref"])
        raw = store.get_artifact(source["artifact_ref"])
        assert result == {'acquired': True, 'source_ref': source['id'],
            'data_ref': source['artifact_ref'], 'failure_code': None}
        control_raw = store.get_artifact(source['request_ref'])
        control = json.loads(control_raw)
        assert control_raw == canonical(control).encode()
        native = emdb.emdb_entry_result(SourceSnapshot(emdb.SERVICE, source['uri'], control['request'],
            source['retrieved_at'], raw, store.get(source['artifact_ref'])['media_type'], control['transport']),
            arguments=args, source_ref=source['id'], artifact_ref=source['artifact_ref'])
        assert native['native_json'] == json.loads(raw) and native['issues'] == []
        assert source["provider"] == "emdb" and source["version"] is None and source["accession"] == "EMD-8117"
        assert source["artifact_ref"] == result["data_ref"] == "artifact_" + hashlib.sha256(raw).hexdigest()
        assert len(calls) == 1 and calls[0] == {"service": "emdb", "url": emdb.emdb_entry_url("EMD-8117"),
            "max_bytes": args["max_bytes"], "follow_redirects": False}
        assert set(workflow.receipts.known(root.source.episode_id)) == baseline | {source['id'], source['artifact_ref']}
        assert {row[0] for row in store.db.execute('SELECT record_ref FROM runtime_record_receipts '
            "WHERE episode_id=? AND receipt_kind='own_action'", (root.source.episode_id,))} == {source['id'], source['artifact_ref']}
        assert source['request_ref'] not in workflow.receipts.known(root.source.episode_id)
        assert store.db.execute('SELECT count(*) FROM runtime_forms').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_report_attempts').fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_record_receipts WHERE receipt_kind='child_form'").fetchone()[0] == 0
        episode = store.db.execute('SELECT path,state FROM runtime_episodes').fetchone()
        assert json.loads(episode['path']) == [['improvement', 'root']] and episode['state'] == 'yielded'
        selected_action = json.loads(store.db.execute('SELECT action FROM runtime_actions').fetchone()[0])
        assert selected_action == {'kind': 'tool', 'tool': 'public.emdb.entry', 'arguments': args}
        count = {name: store.db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in
            ("runtime_episodes", "runtime_actions", "runtime_observations", "runtime_model_calls", "tool_operations")}
        assert count == {"runtime_episodes": 1, "runtime_actions": 1, "runtime_observations": 1,
            "runtime_model_calls": 1, "tool_operations": 1}
        before, files, archives = _tables(store), _files(store.path / "artifacts"), _files(directory / 'archive')
        monkeypatch.setattr(client, "_http", forbidden)
        original_get = Store.get_artifact
        def controls_only(current, reference):
            assert reference != source['artifact_ref'], 'closed acquisition replay reread original entity'
            return original_get(current, reference)
        monkeypatch.setattr(Store, 'get_artifact', controls_only)
        monkeypatch.setattr(ToolRegistry, 'execute_async', forbidden)
        replay_provider = ScriptedProvider([])
        replay = make(replay_provider)
        restored = replay.build('improvement', 'root', question, scope)
        record = asyncio.run(restored.run_async(replay.context))
        assert asyncio.run(restored.build_result(record)).as_record() == final
        assert replay_provider.contexts == [] and len(calls) == 1
        assert _tables(store) == before and _files(store.path / "artifacts") == files
        assert _files(directory / 'archive') == archives
        (tmp_path / "EMDB_ACQUISITION.json").write_text(json.dumps({
            "qualification": "live selected entry GET; scripted Workflow" if live else
                "loopback engineering native JSON; scripted Workflow; no live claim",
            "http_requests": calls, "counts": count, "result": result,
            "current_episode_received_source_and_data_file": True, "closed_current_episode_replay_without_http": True,
            "tables_and_artifacts_value_unchanged": True,
            "scope": "ordinary acquisition in the existing improvement role; controller yield after one step; no child, scientific report, density map, coordinate parser, numerical analysis or scientific conclusion"},
            indent=2) + "\n")


def test_registered_same_episode_metadata_receipts_and_closed_replay(archive, tmp_path, monkeypatch):
    _selected_path(tmp_path, monkeypatch, client=PublicClients(timeout=3))
    assert archive["requests"] == ["/entry/EMD-8117"]


def test_live_selected_emdb_entry_metadata(tmp_path, monkeypatch):
    if os.environ.get("HMMER_NATIVE_ORACLE_EMDB_LIVE") != "1":
        pytest.skip("requires explicitly selected HMMER_NATIVE_ORACLE_EMDB_LIVE=1")
    _selected_path(tmp_path, monkeypatch, client=PublicClients(timeout=90), live=True)
