"""Engineered HTTP and real ordinary-episode acquisition; no external requests."""
import asyncio
import base64
from copy import deepcopy
from email.message import Message
import hashlib
import io
import json
import urllib.error
from urllib.parse import urlencode

import pytest

from gene_annotation_episode import variant_provider_acquisition as provider
from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_prompt import text_instructions
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

from test_molecular_provider_acquisition_host import (
    ReceivingProvider, _artifacts, _controller, _credit, _scope, _session,
    _tables, _two_step_controller,
)
from test_runtime import ScriptedProvider
from test_scientific_process_runtime import action
from test_variant_provider_acquisition import ARGUMENTS, CASES, document, operation


REPRESENTATIVES = ("eva_variant", "gnomad_variant")
QUESTION = ("Evaluate the supplied molecular evidence while preserving the caller-selected "
    "variant resource, reference and population scope. A retrieved response does not settle "
    "a biological conclusion.")


def forbidden(*args, **kwargs):
    raise AssertionError("unselected scientific, network or repeated publication work")


def _raw(case, mode="success"):
    value = document(case)
    if mode == "malformed":
        return b'{"incomplete":'
    if mode == "native_error":
        if case.startswith("eva_"):
            value["error"] = "controlled native error"
        else:
            value["errors"] = [{"message": "controlled native error"}]
    elif mode == "identity_mismatch":
        if case.startswith("eva_"):
            value["response"][0]["result"][0].update(mainId="rs1", ids=["rs1"])
        else:
            value["data"]["variant"].update(variant_id="1-8-A-G", pos=8)
    elif mode == "empty":
        if case.startswith("eva_"):
            value["response"][0].update(result=[], numResults=0)
        elif case == "gnomad_search":
            value["data"]["gene_search"] = []
        else:
            value["data"]["variant"] = None
    return json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("ascii") + b"\n"


class _Response:
    """A fake HTTPS response consumed by the actual bounded HTTP reader."""
    def __init__(self, raw, url, headers, *, status=200, interrupted=False):
        self.status, self.headers, self.url = status, headers, url
        self.body, self.interrupted, self.reads = io.BytesIO(raw), interrupted, 0

    def read(self, limit=-1):
        self.reads += 1
        if self.interrupted and self.reads > 1:
            raise OSError("controlled body interruption after retained bytes")
        return self.body.read(limit)

    def geturl(self):
        return self.url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.body.close()


class FakeHTTPS:
    """Only transport is engineered; PublicClients._http constructs/captures it."""
    def __init__(self, monkeypatch, case, *, mode="success", mime="application/json"):
        self.case, self.mode, self.mime = case, mode, mime
        self.raw, self.calls, self.openers = _raw(case, mode), [], []
        monkeypatch.setattr("urllib.request.build_opener", self.build_opener)
        monkeypatch.setattr("urllib.request.urlopen", forbidden)

    def build_opener(self, *handlers):
        assert len(handlers) == 1 and type(handlers[0]).__name__ == "_NoRedirect"
        self.openers.append(tuple(type(handler).__name__ for handler in handlers))
        return self

    def open(self, request, *, timeout):
        self.calls.append(dict(url=request.full_url, method=request.get_method(),
            headers=dict(request.header_items()), body=request.data, timeout=timeout))
        if self.mode == "no_response":
            raise urllib.error.URLError("controlled connection failure without response")
        if self.mode == "timeout":
            raise TimeoutError("controlled timeout without response")
        headers = Message()
        headers["Content-Type"] = self.mime
        headers["Content-Length"] = str(len(self.raw))
        headers["X-UniProt-Release"] = "unrelated-release-never-a-provider-version"
        if self.mode in {"http_error", "redirect"}:
            status = 404 if self.mode == "http_error" else 302
            if status == 302:
                headers["Location"] = "https://example.invalid/never-follow"
            raise urllib.error.HTTPError(request.full_url, status, "controlled HTTP response",
                headers, io.BytesIO(self.raw))
        return _Response(self.raw, request.full_url, headers,
            status=206 if self.mode == "partial" else 200,
            interrupted=self.mode == "interrupted")


def _registry(store, monkeypatch):
    clients = PublicClients(ncbi_email=None, timeout=3)
    monkeypatch.setattr(clients, "_skill", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    for method in ("_prepare_sequence_work_async", "_native_mapping_async", "_native_cmsearch_async"):
        monkeypatch.setattr(ToolRegistry, method, forbidden)
    return ToolRegistry(store, clients=clients)


def _assert_wire(wire, case, arguments):
    spec = provider.provider_request_spec(operation(case), arguments)
    address = spec["url"] + ("?" + urlencode(spec["params"], doseq=True) if spec["params"] else "")
    assert len(wire.calls) == len(wire.openers) == 1
    call, = wire.calls
    assert call["url"] == address and call["timeout"] == 3
    assert call["method"] == ("POST" if spec["body"] is not None else "GET")
    assert call["body"] == spec["body"]
    headers = {key.lower(): value for key, value in call["headers"].items()}
    assert headers == {"user-agent": "gene-annotation-episode/0.2", "accept": "application/json",
        **({"content-type": "application/json"} if spec["body"] is not None else {})}
    assert spec["follow_redirects"] is False
    if spec["body"] is not None:
        native_body = json.loads(call["body"])
        assert set(native_body) == {"query", "variables"}
        if arguments["request_type"] == "variant":
            assert native_body["variables"]["id"] == arguments["variant_id"]
    return address


def _retained(store, outcome, wire, case, arguments, *, value_expected=True):
    receipt = provider.validate_provider_receipt(outcome["result"])
    assert set(receipt) == {"acquired", "source_ref", "data_ref", "failure_code"}
    source = store.get(receipt["source_ref"])
    expected_raw = wire.raw[:arguments["max_bytes"]]
    assert source["record_type"] == "source" and source["origin"] == "external"
    assert source["provider"] == operation(case).split(".")[1]
    assert source["version"] is None and source["accession"] is None
    assert source["artifact_ref"] == "artifact_" + hashlib.sha256(expected_raw).hexdigest()
    assert store.get_artifact(source["artifact_ref"]) == expected_raw
    assert outcome["record_refs"] == [source["id"], *([source["artifact_ref"]] if receipt["acquired"] else [])]
    assert receipt["data_ref"] == (source["artifact_ref"] if receipt["acquired"] else None)
    request = json.loads(store.get_artifact(source["request_ref"]))
    spec = provider.provider_request_spec(operation(case), arguments)
    assert request["request"] == spec["params"]
    transport = request["transport"]
    assert transport["request"]["url"] == wire.calls[0]["url"]
    assert transport["request"]["method"] == wire.calls[0]["method"]
    assert transport["request_policy"] == {"timeout_seconds": 3, "automatic_redirects": False}
    assert transport["response_byte_limit"] == arguments["max_bytes"]
    assert transport["retained_body_bytes"] == len(expected_raw)
    assert transport["declared_body_bytes"] == len(wire.raw)
    if spec["body"] is not None:
        assert transport["request"]["body_base64"] == base64.b64encode(spec["body"]).decode("ascii")
        assert transport["request"]["body_sha256"] == hashlib.sha256(spec["body"]).hexdigest()
    auxiliary, = source["auxiliary_artifact_refs"]
    private = json.loads(store.get_artifact(auxiliary))
    if value_expected:
        private = provider.validate_provider_value(private)
        assert private["operation"] == operation(case) and private["requested"] == arguments
        assert base64.b64decode(private["raw"]["data"], validate=True) == expected_raw
        assert source["uri"] == transport["request"]["url"]
    else:
        assert set(private) == {"version", "observed_snapshot_service", "observed_snapshot_url", "failure_code"}
        assert private["version"] == "variant_provider_failure_witness_v1"
        assert private["failure_code"] == receipt["failure_code"]
        assert private["observed_snapshot_service"] == source["provider"]
        assert private["observed_snapshot_url"] == source["uri"]
    assert "source_ref" not in private
    assert {auxiliary, source["request_ref"]}.isdisjoint(outcome["record_refs"])
    return receipt, source, private, transport


@pytest.mark.parametrize("case", CASES)
def test_registry_five_selected_requests_use_actual_http_and_exact_cached_receipt(tmp_path, monkeypatch, case):
    wire = FakeHTTPS(monkeypatch, case)
    arguments = deepcopy(ARGUMENTS[case])
    with Store(tmp_path / "store") as store:
        tools, scope = _registry(store, monkeypatch), _scope(store)
        outcome = tools.execute(operation(case), arguments, scope=scope, operation_key="selected-getter")
        assert outcome["status"] == "completed" and outcome["feedback"] is None
        _assert_wire(wire, case, arguments)
        receipt, source, private, transport = _retained(store, outcome, wire, case, arguments)
        assert receipt["acquired"] is True and private["failure_code"] is None
        assert private["population_scope"] == "returned_response_only"
        assert transport["body_complete"] is True
        before, files = _tables(store), _artifacts(store.path / "artifacts")
        monkeypatch.setattr(PublicClients, "_http", forbidden)
        monkeypatch.setattr(provider, "provider_value", forbidden)
        monkeypatch.setattr(provider, "publish_provider_request", forbidden)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        assert tools.execute(operation(case), arguments, scope=scope, operation_key="selected-getter") == outcome
        assert _tables(store) == before and _artifacts(store.path / "artifacts") == files
        assert len(wire.calls) == 1
        with pytest.raises(ContractError, match="^operation_key_reused_for_different_work$"):
            tools.execute(operation(case), {**arguments, "max_bytes": arguments["max_bytes"] - 1},
                scope=scope, operation_key="selected-getter")


@pytest.mark.parametrize("case", REPRESENTATIVES)
@pytest.mark.parametrize("mode", ("identity_mismatch", "native_error", "malformed", "partial"))
def test_captured_native_or_partial_response_failure_has_source_without_data_grant(tmp_path, monkeypatch, case, mode):
    wire = FakeHTTPS(monkeypatch, case, mode=mode)
    arguments = deepcopy(ARGUMENTS[case])
    with Store(tmp_path / "store") as store:
        tools = _registry(store, monkeypatch)
        outcome = tools.execute(operation(case), arguments, scope=_scope(store), operation_key="captured-failure")
        assert outcome["status"] == "partial" and outcome["feedback"]["category"] == "acquisition"
        _assert_wire(wire, case, arguments)
        receipt, _, private, _ = _retained(store, outcome, wire, case, arguments)
        suffix = {"native_error": "native_error", "malformed": "native_representation_invalid",
            "partial": "partial_response"}.get(mode,
                "native_result_unavailable" if case.startswith("eva_") else "native_identity_conflict")
        assert receipt["failure_code"] == "variant_provider_" + suffix
        assert receipt["acquired"] is False and private["failure_code"] == receipt["failure_code"]


@pytest.mark.parametrize("case", REPRESENTATIVES)
@pytest.mark.parametrize("mode,mime", (("http_error", "application/json"),
    ("http_error", "text/plain"), ("redirect", "text/html")))
def test_actual_http_error_mime_and_disabled_redirect_preserve_literal_failure_capture(tmp_path, monkeypatch, case, mode, mime):
    wire = FakeHTTPS(monkeypatch, case, mode=mode, mime=mime)
    arguments = deepcopy(ARGUMENTS[case])
    with Store(tmp_path / "store") as store:
        tools = _registry(store, monkeypatch)
        outcome = tools.execute(operation(case), arguments, scope=_scope(store), operation_key="http-error")
        _assert_wire(wire, case, arguments)
        receipt, source, _, transport = _retained(store, outcome, wire, case, arguments,
            value_expected=mime == "application/json")
        assert outcome["status"] == "partial" and receipt["acquired"] is False
        assert receipt["failure_code"] == ("variant_provider_http_not_successful" if mime == "application/json"
            else "variant_provider_selected_request_conflict")
        assert source["uri"] == wire.calls[0]["url"]
        assert transport["status"] == (302 if mode == "redirect" else 404)
        assert store.db.execute("SELECT media_type FROM artifacts WHERE id=?", (source["artifact_ref"],)).fetchone()[0] == mime


@pytest.mark.parametrize("case", REPRESENTATIVES)
@pytest.mark.parametrize("mime", ("application/json", "text/plain"))
def test_actual_interrupted_capture_keeps_prefix_and_actual_capture_mime(tmp_path, monkeypatch, case, mime):
    wire = FakeHTTPS(monkeypatch, case, mode="interrupted", mime=mime)
    arguments = deepcopy(ARGUMENTS[case])
    with Store(tmp_path / "store") as store:
        tools = _registry(store, monkeypatch)
        outcome = tools.execute(operation(case), arguments, scope=_scope(store), operation_key="interrupted")
        _assert_wire(wire, case, arguments)
        receipt, _, _, transport = _retained(store, outcome, wire, case, arguments,
            value_expected=mime == "application/json")
        assert outcome["status"] == "partial" and receipt["acquired"] is False
        assert receipt["failure_code"] == ("variant_provider_capture_incomplete" if mime == "application/json"
            else "variant_provider_selected_request_conflict")
        assert transport["body_complete"] is False
        assert transport["body_capture_failure"] == "provider_body_capture_failed"
        assert transport["observed_body_bytes"] == len(wire.raw)


@pytest.mark.parametrize("case", REPRESENTATIVES)
def test_actual_byte_limit_retains_only_the_failed_prefix(tmp_path, monkeypatch, case):
    wire = FakeHTTPS(monkeypatch, case)
    arguments = {**deepcopy(ARGUMENTS[case]), "max_bytes": 32}
    with Store(tmp_path / "store") as store:
        outcome = _registry(store, monkeypatch).execute(operation(case), arguments,
            scope=_scope(store), operation_key="bounded-prefix")
        _assert_wire(wire, case, arguments)
        receipt, _, _, transport = _retained(store, outcome, wire, case, arguments)
        assert outcome["status"] == "partial" and receipt["failure_code"] == "variant_provider_capture_incomplete"
        assert transport["body_complete"] is False and transport["observed_body_bytes"] == 33
        assert transport["body_capture_failure"] == "provider_response_byte_limit"


@pytest.mark.parametrize("case", REPRESENTATIVES)
def test_successful_declared_json_with_native_content_type_qualification_is_not_rewritten(tmp_path, monkeypatch, case):
    wire = FakeHTTPS(monkeypatch, case, mime="text/plain")
    arguments = deepcopy(ARGUMENTS[case])
    with Store(tmp_path / "store") as store:
        outcome = _registry(store, monkeypatch).execute(operation(case), arguments,
            scope=_scope(store), operation_key="native-content-type")
        receipt, source, private, transport = _retained(store, outcome, wire, case, arguments)
        assert outcome["status"] == "completed" and receipt["acquired"] is True
        assert private["observed"]["media_type"] == "application/json"
        assert transport["headers"]["content-type"] == "text/plain"
        assert {"code": "native_content_type_qualification", "pointer": "/observed/transport/header_items"} in private["qualifications"]
        assert store.get_artifact(source["artifact_ref"]) == wire.raw


@pytest.mark.parametrize("case", REPRESENTATIVES)
@pytest.mark.parametrize("mode", ("no_response", "timeout"))
def test_no_response_is_finite_cached_failure_without_invented_source(tmp_path, monkeypatch, case, mode):
    wire = FakeHTTPS(monkeypatch, case, mode=mode)
    arguments = deepcopy(ARGUMENTS[case])
    with Store(tmp_path / "store") as store:
        tools, scope = _registry(store, monkeypatch), _scope(store)
        sources_before = {row[0] for row in store.db.execute("SELECT id FROM records WHERE record_type='source'")}
        outcome = tools.execute(operation(case), arguments, scope=scope, operation_key="no-response")
        _assert_wire(wire, case, arguments)
        assert outcome["status"] == "failed" and outcome["record_refs"] == []
        assert provider.validate_provider_receipt(outcome["result"]) == {
            "acquired": False, "source_ref": None, "data_ref": None,
            "failure_code": "provider_connection_failed" if mode == "no_response" else "provider_request_timeout"}
        assert {row[0] for row in store.db.execute("SELECT id FROM records WHERE record_type='source'")} == sources_before
        before, files = _tables(store), _artifacts(store.path / "artifacts")
        monkeypatch.setattr(PublicClients, "_http", forbidden)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        assert tools.execute(operation(case), arguments, scope=scope, operation_key="no-response") == outcome
        assert _tables(store) == before and _artifacts(store.path / "artifacts") == files


@pytest.mark.parametrize("case", REPRESENTATIVES)
def test_invalid_selected_arguments_are_controlled_before_any_transport_or_source(tmp_path, monkeypatch, case):
    wire = FakeHTTPS(monkeypatch, case)
    with Store(tmp_path / "store") as store:
        tools, scope = _registry(store, monkeypatch), _scope(store)
        sources_before = {row[0] for row in store.db.execute("SELECT id FROM records WHERE record_type='source'")}
        outcome = tools.execute(operation(case),
            {**deepcopy(ARGUMENTS[case]), "max_bytes": True}, scope=scope, operation_key="invalid")
        assert outcome["status"] == "invalid" and outcome["record_refs"] == []
        assert provider.validate_provider_receipt(outcome["result"]) == {
            "acquired": False, "source_ref": None, "data_ref": None, "failure_code": "invalid_tool_input"}
        assert wire.calls == wire.openers == []
        assert {row[0] for row in store.db.execute("SELECT id FROM records WHERE record_type='source'")} == sources_before


@pytest.mark.parametrize("case,acquired", (("eva_variant", True), ("gnomad_search", True), ("gnomad_variant", False)))
def test_native_empty_query_and_exact_null_keep_distinct_registry_statuses(tmp_path, monkeypatch, case, acquired):
    wire = FakeHTTPS(monkeypatch, case, mode="empty")
    arguments = deepcopy(ARGUMENTS[case])
    with Store(tmp_path / "store") as store:
        outcome = _registry(store, monkeypatch).execute(operation(case), arguments,
            scope=_scope(store), operation_key="native-empty")
        receipt, _, private, _ = _retained(store, outcome, wire, case, arguments)
        _assert_wire(wire, case, arguments)
        assert receipt["acquired"] is acquired
        assert outcome["status"] == ("completed" if acquired else "partial")
        assert private["identity_state"] == ("empty" if acquired else "unavailable")
        assert receipt["failure_code"] == (None if acquired else "variant_provider_native_result_unavailable")


def _workflow(store, tools, actor, directory, *, steps=2, run_id="current-variant-acquisition"):
    return Workflow(store, tools, actor, directory, run_id,
        _two_step_controller if steps == 2 else _controller, _credit, project_child_credit=_credit,
        root_role="improvement", episode_record_receipts=True, initial_known_record_refs=[])


def _assert_dispatches(store, dispatches, root):
    calls = list(store.db.execute("SELECT request,response FROM runtime_model_calls ORDER BY call_index"))
    assert len(calls) == len(dispatches)
    for dispatched, call in zip(dispatches, calls):
        assert call["response"] is not None
        assert json.loads(call["request"])["context"] == dispatched["context"]
        assert dispatched["wire"].startswith("TASK\n") and "\n\nSTEERING\n" in dispatched["wire"]
        assert QUESTION in dispatched["wire"]
        assert "Absent: no parent return form was supplied." in dispatched["wire"]
        assert dispatched["model_instructions"] == text_instructions(dispatched["instructions"])
        assert dispatched["context"]["goal"] == root.source.request.goal.as_record()
        assert QUESTION in json.dumps(dispatched["context"]["goal"])
        assert dispatched["context"]["requested_form"] is None


def _assert_no_child(store, *, calls, actions):
    counts = {name: store.db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in (
        "runtime_episodes", "runtime_actions", "runtime_observations", "runtime_model_calls", "tool_operations")}
    assert counts == {"runtime_episodes": 1, "runtime_actions": actions, "runtime_observations": actions,
        "runtime_model_calls": calls, "tool_operations": actions}
    assert store.db.execute("SELECT count(*) FROM runtime_forms").fetchone()[0] == 0
    assert store.db.execute("SELECT count(*) FROM runtime_report_attempts").fetchone()[0] == 0
    assert store.db.execute("SELECT count(*) FROM runtime_record_receipts WHERE receipt_kind='child_form'").fetchone()[0] == 0
    assert [json.loads(row[0])["kind"] for row in store.db.execute(
        "SELECT action FROM runtime_actions ORDER BY decision_index")] == ["tool"] * actions


def _assert_private_denials(workflow, tools, context, source):
    private = {source["request_ref"], *source["auxiliary_artifact_refs"]}
    known = set(workflow.receipts.known(context.episode_id))
    assert private.isdisjoint(known)
    resolve = workflow.resolver(plain(context.scope), context=context)
    for reference in private:
        assert resolve(reference, "artifact") is False
        assert tools.retained_molecular_reference_access(context, reference, "artifact") is False
    return known, resolve


@pytest.mark.parametrize("case", REPRESENTATIVES)
def test_current_episode_lost_reply_receives_data_then_reads_and_replays_without_work(tmp_path, monkeypatch, case):
    class LostReply(RuntimeError):
        pass
    wire = FakeHTTPS(monkeypatch, case)
    arguments = deepcopy(ARGUMENTS[case])
    with Store(tmp_path / "store") as store:
        tools, scope = _registry(store, monkeypatch), _scope(store)
        connection = _session(tmp_path / "session")
        actor = ReceivingProvider([action(operation(case), arguments)], connection)
        current = _workflow(store, tools, actor, tmp_path / "workflow")
        root = current.build("improvement", "root", QUESTION, scope)
        baseline = set(current.receipts.known(root.source.episode_id))
        assert operation(case) in {entry["name"] for entry in current.catalog(scope, source=root.source)}
        info = next(entry for entry in current.services.tool_information_catalog(scope) if entry["name"] == operation(case))
        assert info["resources"] == "api" and info["invocation_route"] == {"kind": "direct"}
        execute, lost = ToolRegistry.execute_async, []
        async def lose_reply(registry, name, selected, **kwargs):
            outcome = await execute(registry, name, selected, **kwargs)
            if name == operation(case) and not lost:
                assert outcome["status"] == "completed"
                lost.append(deepcopy(outcome))
                raise LostReply()
            return outcome
        with monkeypatch.context() as patch:
            patch.setattr(ToolRegistry, "execute_async", lose_reply)
            with pytest.raises(LostReply):
                asyncio.run(root.run_async(current.context))
        assert store.db.execute("SELECT result FROM runtime_actions WHERE decision_index=0").fetchone()[0] is None
        assert len(lost) == len(actor.dispatches) == len(wire.calls) == 1
        receipt, source, _, _ = _retained(store, lost[0], wire, case, arguments)
        def read_acquired(context):
            assert context["last_local_outcome"]["result"] == receipt
            assert context["last_local_outcome"]["record_refs"] == lost[0]["record_refs"]
            return action("source.read", dict(source_ref=source["id"], representation="original", offset=0, limit=4096))
        async def cached_without_bytes(registry, name, selected, **kwargs):
            if name == operation(case):
                with monkeypatch.context() as patch:
                    patch.setattr(Store, "get_artifact", forbidden)
                    return await execute(registry, name, selected, **kwargs)
            return await execute(registry, name, selected, **kwargs)
        monkeypatch.setattr(PublicClients, "_http", forbidden)
        monkeypatch.setattr(provider, "publish_provider_request", forbidden)
        monkeypatch.setattr(provider, "provider_value", forbidden)
        monkeypatch.setattr(ToolRegistry, "execute_async", cached_without_bytes)
        receiving = ReceivingProvider([read_acquired], connection)
        recovered = _workflow(store, tools, receiving, tmp_path / "workflow")
        recovered_root = recovered.build("improvement", "root", QUESTION, scope)
        record = asyncio.run(recovered_root.run_async(recovered.context))
        result = asyncio.run(recovered_root.build_result(record)).as_record()
        _assert_dispatches(store, actor.dispatches + receiving.dispatches, root)
        _assert_wire(wire, case, arguments)
        context = recovered.binding_context(recovered_root.source)
        known, resolve = _assert_private_denials(recovered, tools, context, source)
        assert known == baseline | set(lost[0]["record_refs"])
        for reference, namespace in ((source["id"], "source"), (source["artifact_ref"], "artifact")):
            assert resolve(reference, namespace) is True
            item, path = recovered.services.read_received_molecular_input(context, reference, namespace, file_format="json")
            assert item["failure"] is None and item["input"]["file"]["artifact_ref"] == source["artifact_ref"]
            assert path.read_bytes() == wire.raw
        assert {row[0] for row in store.db.execute("SELECT record_ref FROM runtime_record_receipts "
            "WHERE episode_id=? AND receipt_kind='own_action'", (context.episode_id,))} == set(lost[0]["record_refs"])
        read_outcome = json.loads(store.db.execute("SELECT result FROM runtime_actions WHERE decision_index=1").fetchone()[0])
        assert read_outcome["status"] == "completed" and read_outcome["result"]["text"] == wire.raw.decode("ascii")
        assert read_outcome["result"]["artifact_ref"] == receipt["data_ref"]
        _assert_no_child(store, calls=2, actions=2)
        before, files, archives = _tables(store), _artifacts(store.path / "artifacts"), _artifacts(tmp_path / "workflow" / "archive")
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        monkeypatch.setattr(ToolRegistry, "execute_async", forbidden)
        restored_actor = ScriptedProvider([])
        restored = _workflow(store, tools, restored_actor, tmp_path / "workflow")
        restored_root = restored.build("improvement", "root", QUESTION, scope)
        restored_record = asyncio.run(restored_root.run_async(restored.context))
        assert asyncio.run(restored_root.build_result(restored_record)).as_record() == result
        assert restored_actor.contexts == [] and len(wire.calls) == 1
        assert _tables(store) == before and _artifacts(store.path / "artifacts") == files
        assert _artifacts(tmp_path / "workflow" / "archive") == archives


@pytest.mark.parametrize("case", REPRESENTATIVES)
def test_current_episode_captured_failure_may_read_received_source_without_file_permission(tmp_path, monkeypatch, case):
    wire = FakeHTTPS(monkeypatch, case, mode="native_error")
    arguments = deepcopy(ARGUMENTS[case])
    with Store(tmp_path / "store") as store:
        tools, scope = _registry(store, monkeypatch), _scope(store)
        connection, observed = _session(tmp_path / "session"), []
        def read_failure(context):
            outcome = context["last_local_outcome"]
            receipt = provider.validate_provider_receipt(outcome["result"])
            assert outcome["status"] == "partial" and receipt["acquired"] is False
            assert receipt["data_ref"] is None and outcome["record_refs"] == [receipt["source_ref"]]
            observed.append(deepcopy(outcome))
            return action("source.read", dict(source_ref=receipt["source_ref"], representation="original", offset=0, limit=4096))
        actor = ReceivingProvider([action(operation(case), arguments), read_failure], connection)
        current = _workflow(store, tools, actor, tmp_path / "workflow")
        root = current.build("improvement", "root", QUESTION, scope)
        record = asyncio.run(root.run_async(current.context))
        asyncio.run(root.build_result(record))
        receipt, source, _, _ = _retained(store, observed[0], wire, case, arguments)
        _assert_dispatches(store, actor.dispatches, root)
        _assert_no_child(store, calls=2, actions=2)
        _assert_wire(wire, case, arguments)
        last = json.loads(store.db.execute("SELECT result FROM runtime_actions WHERE decision_index=1").fetchone()[0])
        assert last["status"] == "completed" and last["result"]["text"] == wire.raw.decode("ascii")
        assert last["result"]["artifact_ref"] == source["artifact_ref"]
        context = current.binding_context(root.source)
        known, resolve = _assert_private_denials(current, tools, context, source)
        assert source["id"] in known and source["artifact_ref"] not in known
        assert resolve(source["id"], "source") is True and resolve(source["artifact_ref"], "artifact") is False
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        monkeypatch.setattr("gene_annotation_episode.molecular_sequence_input_bindings.retained_native_file", forbidden)
        item, path = current.services.read_received_molecular_input(context, source["artifact_ref"], "artifact", file_format="json")
        assert item["input"] is None and item["failure"]["code"] == "reference_not_received" and path is None
        assert receipt["failure_code"] == "variant_provider_native_error"


@pytest.mark.parametrize("case", REPRESENTATIVES)
def test_same_scope_unreceived_context_denies_source_file_and_private_controls_before_bytes(tmp_path, monkeypatch, case):
    wire = FakeHTTPS(monkeypatch, case)
    arguments = deepcopy(ARGUMENTS[case])
    with Store(tmp_path / "store") as store:
        tools, scope = _registry(store, monkeypatch), _scope(store)
        owner = _workflow(store, tools, ScriptedProvider([action(operation(case), arguments)]),
            tmp_path / "owner", steps=1, run_id="variant-owner")
        root = owner.build("improvement", "root", QUESTION, scope)
        record = asyncio.run(root.run_async(owner.context))
        asyncio.run(root.build_result(record))
        outcome = json.loads(store.db.execute("SELECT result FROM tool_operations").fetchone()[0])
        source = store.get(outcome["result"]["source_ref"])
        other = _workflow(store, tools, ScriptedProvider([]), tmp_path / "unreceived", steps=1, run_id="variant-unreceived")
        receiver = other.build("improvement", "root", QUESTION, scope)
        context = other.binding_context(receiver.source)
        known = set(other.receipts.known(context.episode_id))
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        monkeypatch.setattr("gene_annotation_episode.molecular_sequence_input_bindings.retained_native_file", forbidden)
        resolve = other.resolver(plain(context.scope), context=context)
        for reference, namespace in ((source["id"], "source"), (source["artifact_ref"], "artifact"),
                (source["request_ref"], "artifact"), *[(ref, "artifact") for ref in source["auxiliary_artifact_refs"]]):
            assert resolve(reference, namespace) is False
            item, path = other.services.read_received_molecular_input(context, reference, namespace, file_format="json")
            assert item["input"] is None and item["failure"] is not None and path is None
        read_args = dict(source_ref=source["id"], representation="original", offset=0, limit=4096)
        with tools.current_invocation(context, read_received=other.services.read_received_molecular_input,
                tool_name="source.read", arguments=read_args, operation_key="unreceived-byte-probe"):
            with pytest.raises(ContractError, match="^" + operation(case).split(".")[1] + "_source_primary_body_not_received$"):
                tools._check_molecular_source_bytes("source.read", read_args)
        assert set(other.receipts.known(context.episode_id)) == known
        assert store.db.execute("SELECT count(*) FROM runtime_actions WHERE episode_id=?", (context.episode_id,)).fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_model_calls WHERE episode_id=?", (context.episode_id,)).fetchone()[0] == 0
        assert len(wire.calls) == 1


@pytest.mark.parametrize("case", REPRESENTATIVES)
def test_current_episode_no_response_diagnostic_is_not_a_data_receipt_or_forwarded_control(tmp_path, monkeypatch, case):
    class PendingFailureBoundary(RuntimeError):
        """The real failed-action continuation is captured before its reply."""

    wire = FakeHTTPS(monkeypatch, case, mode="no_response")
    with Store(tmp_path / "store") as store:
        tools, scope = _registry(store, monkeypatch), _scope(store)
        observed = []
        def inspect_failed_continuation(context):
            outcome = context["last_local_outcome"]
            assert outcome["status"] == "failed" and outcome["record_refs"] == []
            assert provider.validate_provider_receipt(outcome["result"]) == {
                "acquired": False, "source_ref": None, "data_ref": None,
                "failure_code": "provider_connection_failed"}
            assert outcome["feedback"]["code"] == "provider_connection_failed"
            observed.append(deepcopy(outcome))
            raise PendingFailureBoundary()
        actor = ReceivingProvider([action(operation(case), deepcopy(ARGUMENTS[case])),
            inspect_failed_continuation], _session(tmp_path / "session"))
        current = _workflow(store, tools, actor, tmp_path / "workflow", steps=1)
        root = current.build("improvement", "root", QUESTION, scope)
        baseline = set(current.receipts.known(root.source.episode_id))
        sources_before = {row[0] for row in store.db.execute("SELECT id FROM records WHERE record_type='source'")}
        with pytest.raises(PendingFailureBoundary):
            asyncio.run(root.run_async(current.context))
        outcome = json.loads(store.db.execute("SELECT result FROM tool_operations").fetchone()[0])
        selected, = store.db.execute("SELECT action,result,credit FROM runtime_actions")
        action_outcome = json.loads(selected["result"])
        assert len(observed) == 1 and observed[0] == action_outcome
        assert set(action_outcome) == set(outcome) | {"pending_work_after_action"}
        assert {key: value for key, value in action_outcome.items() if key != "pending_work_after_action"} == outcome
        assert provider.validate_provider_receipt(outcome["result"]) == {
            "acquired": False, "source_ref": None, "data_ref": None, "failure_code": "provider_connection_failed"}
        assert outcome["status"] == "failed" and outcome["record_refs"] == []
        diagnostic = outcome["feedback"]["diagnostic_ref"]
        assert type(diagnostic) is str
        context = current.binding_context(root.source)
        assert set(current.receipts.known(context.episode_id)) == baseline and diagnostic not in baseline
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        assert current.resolver(plain(context.scope), context=context)(diagnostic, "artifact") is False
        assert tools.retained_molecular_reference_access(context, diagnostic, "artifact") is False
        counts = {name: store.db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in (
            "runtime_episodes", "runtime_actions", "runtime_observations", "runtime_model_calls", "tool_operations")}
        assert counts == {"runtime_episodes": 1, "runtime_actions": 1, "runtime_observations": 0,
            "runtime_model_calls": 2, "tool_operations": 1}
        assert store.db.execute("SELECT count(*) FROM runtime_forms").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_report_attempts").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_record_receipts WHERE receipt_kind='child_form'").fetchone()[0] == 0
        assert json.loads(selected["action"]) == action(operation(case), ARGUMENTS[case])["selection"]
        assert selected["credit"] is None
        assert {row[0] for row in store.db.execute("SELECT id FROM records WHERE record_type='source'")} == sources_before
        calls = list(store.db.execute("SELECT request,response FROM runtime_model_calls ORDER BY call_index"))
        assert len(actor.dispatches) == len(actor.contexts) == len(calls) == 2
        assert calls[0]["response"] is not None and calls[1]["response"] is None
        for dispatched, call in zip(actor.dispatches, calls):
            assert json.loads(call["request"])["context"] == dispatched["context"]
            assert dispatched["wire"].startswith("TASK\n") and "\n\nSTEERING\n" in dispatched["wire"]
            assert QUESTION in dispatched["wire"]
            assert "Absent: no parent return form was supplied." in dispatched["wire"]
            assert dispatched["model_instructions"] == text_instructions(dispatched["instructions"])
            assert diagnostic not in dispatched["wire"]
            assert dispatched["context"]["goal"] == root.source.request.goal.as_record()
            assert QUESTION in json.dumps(dispatched["context"]["goal"])
            assert dispatched["context"]["requested_form"] is None
        assert actor.dispatches[1]["context"]["last_local_outcome"] == action_outcome
        # No completed unit/controller observation is invented for a failed
        # attempt. This is an active prefix at its real next decision, not a
        # closed-workflow success or a scientific result.
        _assert_wire(wire, case, ARGUMENTS[case])
