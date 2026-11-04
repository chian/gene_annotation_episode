"""Real ordinary actions and receipt custody with engineered opaque transfers.

Only the HTTPS response is controlled. No fixture body is an SRA archive, and
these tests claim neither a live download nor parsed run/read identity.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from email.message import Message
import hashlib
import io
import json
from types import SimpleNamespace
import urllib.error
import urllib.request
from urllib.parse import urlsplit

import pytest

from gene_annotation_episode import ncbi_sra_acquisition as sra
from gene_annotation_episode import ncbi_sra_acquisition_host as host
from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, canonical, identity
from gene_annotation_episode.runtime import ActionFailure, Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

from test_molecular_acquisition_ordinary import NoModel, _neutral_bookkeeping, _snapshot
from test_molecular_provider_acquisition_host import (
    ReceivingProvider, _artifacts, _credit, _session, _two_step_controller,
)
from test_ncbi_sra_acquisition import ENGINEERED, engineered
from test_runtime import ScriptedProvider
from test_scientific_process_runtime import action


QUESTION = ("Assess the supplied sequencing evidence. Retain the caller-selected advertised "
    "SRA file as an ordinary acquisition step for later separately selected decoding; "
    "retrieval alone establishes no biological conclusion.")


def forbidden(*args, **kwargs):
    raise AssertionError("unselected network, native, scientific, or repeated byte work")


class _Response:
    def __init__(self, raw, url, headers, *, status=200, interrupted=False):
        self.body, self.url, self.headers, self.status = io.BytesIO(raw), url, headers, status
        self.interrupted, self.reads = interrupted, 0

    def read(self, limit=-1):
        self.reads += 1
        if self.interrupted and self.reads > 1:
            raise OSError("engineered interrupted transfer")
        return self.body.read(limit)

    def geturl(self):
        return self.url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.body.close()


class HTTPS:
    """Actual Request/bounded-reader path, including urllib's real Host step."""
    def __init__(self, monkeypatch, *, raw=ENGINEERED, mode="success", media_type="application/octet-stream"):
        self.raw, self.mode, self.media_type, self.calls, self.openers = raw, mode, media_type, [], []
        monkeypatch.setattr("urllib.request.build_opener", self.build_opener)
        monkeypatch.setattr("urllib.request.urlopen", forbidden)
        monkeypatch.setattr("socket.create_connection", forbidden)
        monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
        monkeypatch.setattr(ToolRegistry, "_sequence_worker_async", forbidden)

    def build_opener(self, *handlers):
        assert len(handlers) == 1 and type(handlers[0]).__name__ == "_NoRedirect"
        self.openers.append(tuple(type(item).__name__ for item in handlers))
        return self

    def open(self, request, *, timeout):
        handler = urllib.request.AbstractHTTPHandler()
        handler.add_parent(SimpleNamespace(addheaders=[]))
        request = handler.do_request_(request)
        self.calls.append(dict(url=request.full_url, method=request.get_method(), body=request.data,
            headers=dict(request.header_items()), timeout=timeout))
        assert len(self.calls) == 1, "no second request, retry, follow-up or redirect was selected"
        if self.mode == "no_response":
            raise urllib.error.URLError("engineered connection failure")
        if self.mode == "timeout":
            raise TimeoutError("engineered timeout without a response")
        headers = Message()
        headers["Content-Type"] = self.media_type
        headers["Content-Length"] = str(len(self.raw))
        headers["X-UniProt-Release"] = "unrelated-not-an-SRA-version"
        if self.mode in {"http_error", "redirect"}:
            status = 503 if self.mode == "http_error" else 302
            if status == 302:
                headers["Location"] = "https://example.invalid/unselected"
            raise urllib.error.HTTPError(request.full_url, status, "engineered native status", headers, io.BytesIO(self.raw))
        if self.mode == "encoded":
            headers["Content-Encoding"] = "gzip"
        return _Response(self.raw, request.full_url, headers,
            status=206 if self.mode == "partial" else 200, interrupted=self.mode == "interrupted")


def _workflow(store, tools, provider, directory, *, initial=(), run_id="ordinary-sra-file", loop=False):
    return Workflow(store, tools, provider, directory, run_id,
        _two_step_controller if loop else forbidden, _credit if loop else _neutral_bookkeeping,
        project_child_credit=_credit, root_role="improvement", episode_record_receipts=True,
        episode_binding_factories=(), initial_known_record_refs=list(initial))


def _case(tmp_path, monkeypatch, *, raw=ENGINEERED, mode="success", attributes=None, admitted=True,
        max_bytes=None, media_type="application/octet-stream", provider=None, loop=False):
    wire = HTTPS(monkeypatch, raw=raw, mode=mode, media_type=media_type)
    xml, arguments, _ = engineered(attributes=attributes)
    if max_bytes is not None:
        arguments["max_bytes"] = max_bytes
    store = Store(tmp_path / "store")
    advertisement = store.artifact(xml, "application/xml")
    assert advertisement == arguments["advertisement_file"]["artifact_ref"]
    subject, = store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]
    scope = store.validate_scope(dict(subject_refs=[subject]))
    tools = ToolRegistry(store, clients=PublicClients(ncbi_email=None, timeout=3))
    workflow = _workflow(store, tools, provider if provider is not None else NoModel(), tmp_path / "workflow",
        initial=[advertisement] if admitted else [], loop=loop)
    caller = workflow.build("improvement", "root", QUESTION, scope)
    context = workflow.binding_context(caller.source)
    return SimpleNamespace(store=store, wire=wire, xml=xml, arguments=arguments, tools=tools,
        workflow=workflow, caller=caller, context=context, scope=scope, advertisement=advertisement,
        baseline=set(workflow.receipts.known(context.episode_id)),
        key=f"{workflow.run_id}:{caller.source.episode_id}:0")


def _execute(case):
    try:
        asyncio.run(case.caller.source.execute(dict(kind="tool", tool=sra.TOOL, arguments=case.arguments), 0))
    except ActionFailure:
        pass
    return deepcopy(case.caller.source.last_outcome)


def _saved(case):
    row, = case.store.db.execute("SELECT * FROM tool_operations")
    assert row["name"] == sra.TOOL and row["operation_key"] == case.key
    assert row["arguments"] == canonical(case.arguments) and row["scope"] == canonical(case.scope)
    assert row["id"] == identity("operation", dict(key=case.key, name=sra.TOOL, arguments=case.arguments))
    return json.loads(row["result"])


def _replay(case):
    return asyncio.run(case.workflow.execute(case.caller.source, sra.TOOL, case.arguments,
        decision_index=0, operation_key=case.key))


def _retained(case, outcome):
    receipt = sra.validate_sra_file_receipt(outcome["result"])
    assert set(receipt) == {"acquired", "source_ref", "data_ref", "failure_code"}
    source = case.store.get(receipt["source_ref"])
    assert source["record_type"] == "source" and source["origin"] == "external"
    assert source["provider"] == sra.TOOL and source["accession"] is source["version"] is None
    assert source["parent_source_refs"] == [] and source["text_ref"] is None
    assert source["uri"] == case.arguments["url"]
    body = case.store.get_artifact(source["artifact_ref"])
    assert source["artifact_ref"] == "artifact_" + hashlib.sha256(body).hexdigest()
    control = json.loads(case.store.get_artifact(source["request_ref"]))
    witness, = source["auxiliary_artifact_refs"]
    evidence = json.loads(case.store.get_artifact(witness))
    assert evidence["version"] == host.EVIDENCE_VERSION
    prepared = evidence["prepared"]
    assert prepared["version"] == host.PREPARED_VERSION and prepared["arguments"] == case.arguments
    assert prepared["invocation"]["operation_key"] == case.key and prepared["invocation"]["decision_index"] == 0
    assert prepared["input"]["metadata"]["file"] == case.arguments["advertisement_file"]
    assert prepared["input"]["metadata"]["byte_verification"] == "unavailable"
    assert prepared["input"]["admission"]["baseline"] is True
    if evidence["evidence"]["kind"] == "value":
        value = sra.validate_sra_file_value(evidence["evidence"]["value"])
        assert value["observed"]["request"] == control["request"]
        assert value["observed"]["transport"] == control["transport"]
        assert value["raw_file"]["artifact_ref"] == source["artifact_ref"]
        assert value["raw_file"]["size_bytes"] == len(body)
        assert value["checks"]["archive_identity"] == "not_parsed"
    expected = [source["id"], *([source["artifact_ref"]] if receipt["acquired"] else [])]
    assert outcome["record_refs"] == expected
    known = set(case.workflow.receipts.known(case.context.episode_id))
    assert known - case.baseline == set(expected)
    assert {witness, source["request_ref"]}.isdisjoint(known)
    assert (source["artifact_ref"] in known) is receipt["acquired"]
    return receipt, source, evidence, control, body


def _wire(case):
    call, = case.wire.calls
    assert len(case.wire.openers) == 1 and call["url"] == case.arguments["url"]
    assert call["method"] == "GET" and call["body"] is None and call["timeout"] == 3
    assert {key.lower(): value for key, value in call["headers"].items()} == {
        "accept": "application/octet-stream", "host": urlsplit(case.arguments["url"]).netloc,
        "user-agent": "gene-annotation-episode/0.2"}


def _forbid_entities(monkeypatch, case, source=None):
    original = Store.get_artifact
    entities = {case.advertisement, *([source["artifact_ref"]] if source else [])}
    def controls_only(store, reference):
        assert reference not in entities, "cached authentication reopened an original entity"
        return original(store, reference)
    monkeypatch.setattr(Store, "get_artifact", controls_only)
    for name in ("retained_native_file", "read_bytes"):
        monkeypatch.setattr(host, name, forbidden)
    monkeypatch.setattr(sra, "resolve_sra_file_selection", forbidden)
    monkeypatch.setattr(sra, "sra_file_value", forbidden)
    monkeypatch.setattr(PublicClients, "_http", forbidden)


def test_actual_current_episode_file_only_admission_one_get_and_explicit_data_receipt(tmp_path, monkeypatch):
    case = _case(tmp_path, monkeypatch)
    with case.store:
        assert case.caller.request.report_contract is None and case.workflow.episode_bindings.roles == ()
        assert sra.TOOL in {row["name"] for row in case.workflow.catalog(case.scope, source=case.caller.source)}
        outcome = _execute(case)
        receipt, source, evidence, control, body = _retained(case, outcome)
        assert receipt["acquired"] is True and outcome["status"] == "completed" and outcome["feedback"] is None
        assert body == ENGINEERED and receipt["data_ref"] == source["artifact_ref"]
        assert evidence["evidence"]["value"]["checks"] == dict(request="matched", body_capture="complete",
            native_size="verified", native_md5="verified", archive_identity="not_parsed")
        assert control["transport"]["request_policy"] == dict(timeout_seconds=3, automatic_redirects=False)
        assert control["transport"]["response_byte_limit"] == case.arguments["max_bytes"]
        assert _saved(case) == {key: value for key, value in outcome.items() if key != "pending_work_after_action"}
        _wire(case)
        assert case.store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 1
        assert case.store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 1
        for table in ("runtime_model_calls", "runtime_observations", "runtime_forms", "runtime_report_attempts"):
            assert case.store.db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0


@pytest.mark.parametrize("mode,raw,cap,code", [
    ("http_error", ENGINEERED, None, "sra_file_http_not_success"),
    ("redirect", ENGINEERED, None, "sra_file_http_not_success"),
    ("partial", ENGINEERED, None, "sra_file_unrequested_range"),
    ("interrupted", ENGINEERED, None, "provider_body_capture_failed"),
    ("success", ENGINEERED, 8, "provider_response_byte_limit"),
    ("success", ENGINEERED + b"changed", None, "sra_file_native_size_conflict"),
    ("success", b"x" * len(ENGINEERED), None, "sra_file_native_md5_conflict"),
    ("encoded", ENGINEERED, None, "sra_file_content_encoding_unsupported"),
])
def test_captured_failed_or_partial_transfer_preserves_original_bytes_source_only_and_cached_cause(
        tmp_path, monkeypatch, mode, raw, cap, code):
    case = _case(tmp_path, monkeypatch, raw=raw, mode=mode, max_bytes=cap)
    with case.store:
        outcome = _execute(case)
        receipt, source, _, _, body = _retained(case, outcome)
        assert receipt == dict(acquired=False, source_ref=source["id"], data_ref=None, failure_code=code)
        assert outcome["status"] == "partial" and outcome["feedback"]["category"] == "acquisition"
        assert body == (raw[:cap] if cap is not None else raw)
        _wire(case)
        before, files = _snapshot(case.store), _artifacts(case.store.path / "artifacts")
        _forbid_entities(monkeypatch, case, source)
        assert _replay(case) == _saved(case)
        assert _snapshot(case.store) == before and _artifacts(case.store.path / "artifacts") == files


@pytest.mark.parametrize("mode,code", [("no_response", "provider_connection_failed"), ("timeout", "provider_request_timeout")])
def test_no_response_has_no_source_or_data_and_replays_only_its_original_finite_failure(tmp_path, monkeypatch, mode, code):
    case = _case(tmp_path, monkeypatch, mode=mode)
    with case.store:
        sources = list(case.store.db.execute("SELECT id FROM records WHERE record_type='source'"))
        outcome = _execute(case)
        assert sra.validate_sra_file_receipt(outcome["result"]) == dict(
            acquired=False, source_ref=None, data_ref=None, failure_code=code)
        assert outcome["status"] == "failed" and outcome["record_refs"] == []
        assert list(case.store.db.execute("SELECT id FROM records WHERE record_type='source'")) == sources
        known = set(case.workflow.receipts.known(case.context.episode_id))
        diagnostic = outcome["feedback"]["diagnostic_ref"]
        assert diagnostic not in known and known == case.baseline
        before = _snapshot(case.store)
        _forbid_entities(monkeypatch, case)
        assert case.workflow.resolver(plain(case.context.scope), context=case.context)(diagnostic, "artifact") is False
        assert _replay(case) == _saved(case) and _snapshot(case.store) == before
        _wire(case)


@pytest.mark.parametrize("missing", ["advertisement", "download", "both"])
def test_saved_action_needs_only_current_metadata_and_private_controls_not_entity_bodies(tmp_path, monkeypatch, missing):
    case = _case(tmp_path, monkeypatch)
    with case.store:
        outcome = _execute(case)
        _, source, _, _, _ = _retained(case, outcome)
        references = {"advertisement": [case.advertisement], "download": [source["artifact_ref"]],
            "both": [case.advertisement, source["artifact_ref"]]}[missing]
        for reference in references:
            sha = reference.removeprefix("artifact_")
            (case.store.path / "artifacts" / sha[:2] / sha).unlink()
        before, files = _snapshot(case.store), _artifacts(case.store.path / "artifacts")
        _forbid_entities(monkeypatch, case, source)
        assert _replay(case) == _saved(case)
        assert _snapshot(case.store) == before and _artifacts(case.store.path / "artifacts") == files


def test_unreceived_advertisement_denies_before_xml_bytes_http_controls_or_new_source(tmp_path, monkeypatch):
    case = _case(tmp_path, monkeypatch, admitted=False)
    with case.store:
        monkeypatch.setattr(host, "retained_native_file", forbidden)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        before = case.store.db.execute("SELECT count(*) FROM records WHERE record_type='source'").fetchone()[0]
        outcome = _execute(case)
        assert outcome["status"] == "invalid" and outcome["result"] == dict(
            acquired=False, source_ref=None, data_ref=None, failure_code="sra_file_input_not_received")
        assert case.wire.calls == [] and set(case.workflow.receipts.known(case.context.episode_id)) == case.baseline
        assert case.store.db.execute("SELECT count(*) FROM records WHERE record_type='source'").fetchone()[0] == before


@pytest.mark.parametrize("change", ["size", "format", "hash"])
def test_contradictory_or_invalid_input_file_descriptor_cannot_open_bytes_or_http(tmp_path, monkeypatch, change):
    case = _case(tmp_path, monkeypatch)
    with case.store:
        if change == "size":
            case.arguments["advertisement_file"]["size_bytes"] += 1
        elif change == "format":
            case.arguments["advertisement_file"]["format"] = "unselected_format"
        else:
            case.arguments["advertisement_file"]["sha256"] = "0" * 64
        monkeypatch.setattr(host, "retained_native_file", forbidden)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        outcome = _execute(case)
        assert outcome["status"] == "invalid" and outcome["result"]["acquired"] is False
        assert outcome["result"]["source_ref"] is outcome["result"]["data_ref"] is None
        assert case.wire.calls == []


@pytest.mark.parametrize("conflict", ["scope", "name", "arguments", "key", "reader"])
def test_saved_authentication_requires_actual_context_action_key_and_exact_metadata_reader(tmp_path, monkeypatch, conflict):
    case = _case(tmp_path, monkeypatch)
    with case.store:
        _execute(case)
        saved = _saved(case)
        context, reader = case.context, case.workflow.services.read_received_molecular_file_metadata
        selected_name, selected_args, key = sra.TOOL, case.arguments, case.key
        authority = (context, reader)
        if conflict == "scope":
            context = replace(context, scope={"subject_refs": []})
            authority = (context, reader)
        elif conflict == "name":
            selected_name = "public.ncbi.entrez"
        elif conflict == "arguments":
            selected_args = {**case.arguments, "max_bytes": case.arguments["max_bytes"] + 1}
        elif conflict == "key":
            key = case.key.rsplit(":", 1)[0] + ":1"
        else:
            authority = (context, lambda *args, **kwargs: forbidden())
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        with case.tools.current_invocation(context, read_received=reader, tool_name=selected_name,
                arguments=selected_args, operation_key=key):
            with pytest.raises((ContractError, ValueError)):
                host.authenticate_saved_sra_file(case.tools, case.arguments, authority=authority,
                    operation_key=case.key, outcome=saved)


@pytest.mark.parametrize("target", ["request", "evidence"])
def test_changed_private_control_bytes_are_denied_without_entity_reads_or_new_publication(tmp_path, monkeypatch, target):
    case = _case(tmp_path, monkeypatch)
    with case.store:
        outcome = _execute(case)
        _, source, _, _, _ = _retained(case, outcome)
        reference = source["request_ref"] if target == "request" else source["auxiliary_artifact_refs"][0]
        sha = reference.removeprefix("artifact_")
        (case.store.path / "artifacts" / sha[:2] / sha).write_bytes(b"{}")
        before, files = _snapshot(case.store), _artifacts(case.store.path / "artifacts")
        _forbid_entities(monkeypatch, case, source)
        denied = _replay(case)
        assert denied["status"] == "invalid" and denied["result"]["acquired"] is False
        assert denied["record_refs"] == [] and denied["result"]["source_ref"] is None
        assert _snapshot(case.store) == before and _artifacts(case.store.path / "artifacts") == files


@pytest.mark.parametrize("target", ["request", "evidence"])
def test_missing_private_control_is_a_finite_cached_denial_without_entity_reads_or_saved_result_changes(
        tmp_path, monkeypatch, target):
    case = _case(tmp_path, monkeypatch)
    with case.store:
        outcome = _execute(case)
        _, source, _, _, _ = _retained(case, outcome)
        reference = source["request_ref"] if target == "request" else source["auxiliary_artifact_refs"][0]
        sha = reference.removeprefix("artifact_")
        (case.store.path / "artifacts" / sha[:2] / sha).unlink()
        before, files = _snapshot(case.store), _artifacts(case.store.path / "artifacts")
        saved = _saved(case)
        _forbid_entities(monkeypatch, case, source)
        denied = _replay(case)
        assert denied["status"] == "invalid" and denied["result"] == dict(acquired=False,
            source_ref=None, data_ref=None, failure_code="sra_file_saved_outcome_conflict")
        assert denied["record_refs"] == [] and _saved(case) == saved
        assert _snapshot(case.store) == before and _artifacts(case.store.path / "artifacts") == files


def test_same_scope_unreceived_caller_cannot_use_source_raw_file_or_private_controls(tmp_path, monkeypatch):
    case = _case(tmp_path, monkeypatch)
    with case.store:
        outcome = _execute(case)
        _, source, _, _, _ = _retained(case, outcome)
        receiver = _workflow(case.store, case.tools, NoModel(), tmp_path / "other", run_id="unreceived-sra-file")
        other = receiver.build("improvement", "root", QUESTION, case.scope)
        context = receiver.binding_context(other.source)
        known = set(receiver.receipts.known(context.episode_id))
        before = _snapshot(case.store)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        resolve = receiver.resolver(plain(context.scope), context=context)
        for reference, namespace in [(source["id"], "source"), (source["artifact_ref"], "artifact"),
                (source["request_ref"], "artifact"), (source["auxiliary_artifact_refs"][0], "artifact")]:
            assert resolve(reference, namespace) is False
            assert case.tools.retained_molecular_reference_access(context, reference, namespace) is False
        read_args = dict(source_ref=source["id"], representation="original", offset=0, limit=4096)
        with case.tools.current_invocation(context, read_received=receiver.services.read_received_molecular_input,
                tool_name="source.read", arguments=read_args, operation_key="denied-body-probe"):
            with pytest.raises(ContractError):
                case.tools._check_molecular_source_bytes("source.read", read_args)
        assert set(receiver.receipts.known(context.episode_id)) == known and _snapshot(case.store) == before


@pytest.mark.parametrize("successful", [True, False])
def test_separately_selected_source_read_preserves_explicit_file_grant_distinction_and_private_controls(
        tmp_path, monkeypatch, successful):
    case = _case(tmp_path, monkeypatch, mode="success" if successful else "http_error")
    with case.store:
        outcome = _execute(case)
        receipt, source, _, _, raw = _retained(case, outcome)
        selection = dict(kind="tool", tool="source.read", arguments=dict(source_ref=source["id"],
            representation="original", offset=0, limit=4096))
        asyncio.run(case.caller.source.execute(selection, 1))
        read = case.caller.source.last_outcome
        assert read["status"] == "completed" and read["result"]["artifact_ref"] == source["artifact_ref"]
        assert read["result"]["text"] == raw.decode()
        context = case.workflow.binding_context(case.caller.source)
        known = set(case.workflow.receipts.known(context.episode_id))
        assert source["id"] in known and (source["artifact_ref"] in known) is successful
        assert (receipt["data_ref"] == source["artifact_ref"]) is successful
        resolve = case.workflow.resolver(plain(context.scope), context=context)
        assert resolve(source["id"], "source") is True
        assert resolve(source["artifact_ref"], "artifact") is successful
        before = _snapshot(case.store)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        reader = case.workflow.services.read_received_molecular_file_metadata
        if successful:
            item = reader(context, source["artifact_ref"], "artifact", file_format="opaque_sra_archive")
            assert item["byte_verification"] == "unavailable" and item["file"]["artifact_ref"] == source["artifact_ref"]
        else:
            with pytest.raises(ValueError, match="molecular_sequence_input_"):
                reader(context, source["artifact_ref"], "artifact", file_format="opaque_sra_archive")
        for private in [source["request_ref"], *source["auxiliary_artifact_refs"]]:
            assert private not in known and resolve(private, "artifact") is False
            assert case.tools.retained_molecular_reference_access(context, private, "artifact") is False
        assert _snapshot(case.store) == before and len(case.wire.calls) == 1


def test_unrepresentable_value_uses_distinct_finite_failure_witness_and_no_fabricated_value(tmp_path, monkeypatch):
    case = _case(tmp_path, monkeypatch)
    with case.store:
        capture = case.tools.clients._http
        def contradictory_snapshot(**kwargs):
            return replace(capture(**kwargs), service=None)
        monkeypatch.setattr(case.tools.clients, "_http", contradictory_snapshot)
        outcome = _execute(case)
        receipt, source, evidence, _, body = _retained(case, outcome)
        assert body == ENGINEERED and outcome["status"] == "partial"
        assert receipt == dict(acquired=False, source_ref=source["id"], data_ref=None,
            failure_code="sra_file_value_invalid")
        assert evidence["evidence"] == dict(kind="failure", code="sra_file_value_invalid",
            observed_snapshot_service=None, observed_snapshot_url=case.arguments["url"])
        assert "value" not in evidence["evidence"]
        before = _snapshot(case.store)
        _forbid_entities(monkeypatch, case, source)
        assert _replay(case) == _saved(case) and _snapshot(case.store) == before


def test_real_source_survives_later_receipt_publication_failure_without_a_data_grant(tmp_path, monkeypatch):
    case = _case(tmp_path, monkeypatch)
    with case.store:
        def fail_after_source(*args, **kwargs):
            raise RuntimeError("engineered failure after actual Source publication")
        with monkeypatch.context() as patch:
            patch.setattr(sra, "sra_file_receipt", fail_after_source)
            outcome = _execute(case)
        receipt, source, evidence, _, body = _retained(case, outcome)
        assert body == ENGINEERED and evidence["evidence"]["value"]["failure_code"] is None
        assert receipt == dict(acquired=False, source_ref=source["id"], data_ref=None,
            failure_code="data_acquisition_publication_incomplete")
        assert outcome["status"] == "partial" and outcome["feedback"]["code"] == receipt["failure_code"]
        assert outcome["record_refs"] == [source["id"]]
        assert outcome["feedback"]["diagnostic_ref"] not in set(case.workflow.receipts.known(case.context.episode_id))
        before = _snapshot(case.store)
        _forbid_entities(monkeypatch, case, source)
        assert _replay(case) == _saved(case) and _snapshot(case.store) == before


@pytest.mark.parametrize("field", ["status", "receipt", "operation_ref"])
def test_cached_custody_authenticates_actual_original_toolop_not_a_supplied_outcome(tmp_path, monkeypatch, field):
    case = _case(tmp_path, monkeypatch)
    with case.store:
        _execute(case)
        saved = _saved(case)
        candidate = deepcopy(saved)
        if field == "status":
            candidate["status"] = "partial"
        elif field == "receipt":
            candidate["result"] = sra.failed_sra_file_receipt("data_acquisition_failed")
        else:
            candidate["operation_ref"] = "operation_" + "0" * 24
        context, reader = case.context, case.workflow.services.read_received_molecular_file_metadata
        before = _snapshot(case.store)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        with case.tools.current_invocation(context, read_received=reader, tool_name=sra.TOOL,
                arguments=case.arguments, operation_key=case.key):
            with pytest.raises(ContractError, match="sra_file_saved_outcome_conflict"):
                host.authenticate_saved_sra_file(case.tools, case.arguments, authority=(context, reader),
                    operation_key=case.key, outcome=candidate)
        assert _snapshot(case.store) == before


@pytest.mark.parametrize("successful", [True, False])
def test_self_consistent_engineered_journal_status_tamper_cannot_change_acquisition_meaning(tmp_path, monkeypatch, successful):
    case = _case(tmp_path, monkeypatch, mode="success" if successful else "http_error")
    with case.store:
        outcome = _execute(case)
        _, source, _, _, _ = _retained(case, outcome)
        saved = _saved(case)
        action_row, = case.store.db.execute("SELECT result FROM runtime_actions")
        recorded = json.loads(action_row["result"])
        wrong = "partial" if successful else "completed"
        saved["status"] = recorded["status"] = wrong
        # Mutate only this engineered fixture's two original journal values,
        # so the receipt/status consistency check must do the denial itself.
        with case.store.transaction():
            case.store.db.execute("UPDATE tool_operations SET result=? WHERE operation_key=?", (canonical(saved), case.key))
            case.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
                (canonical(recorded), case.workflow.run_id, case.context.episode_id))
        before, files = _snapshot(case.store), _artifacts(case.store.path / "artifacts")
        _forbid_entities(monkeypatch, case, source)
        denied = _replay(case)
        assert denied["status"] == "invalid" and denied["result"] == dict(acquired=False,
            source_ref=None, data_ref=None, failure_code="sra_file_saved_outcome_conflict")
        assert denied["record_refs"] == [] and _snapshot(case.store) == before
        assert _artifacts(case.store.path / "artifacts") == files


def test_actual_lost_reply_receiving_session_explicit_source_read_and_closed_replay_stay_in_one_episode(tmp_path, monkeypatch):
    class LostReply(RuntimeError):
        pass
    connection = _session(tmp_path / "session")
    actor = ReceivingProvider([lambda context: action(sra.TOOL, case.arguments)], connection)
    case = _case(tmp_path, monkeypatch, provider=actor, loop=True)
    with case.store:
        workflow, root = case.workflow, case.caller
        baseline = set(workflow.receipts.known(root.source.episode_id))
        execute, lost = ToolRegistry.execute_async, []
        async def lose_reply(registry, name, arguments, **kwargs):
            outcome = await execute(registry, name, arguments, **kwargs)
            if name == sra.TOOL and not lost:
                lost.append(deepcopy(outcome))
                raise LostReply()
            return outcome
        with monkeypatch.context() as patch:
            patch.setattr(ToolRegistry, "execute_async", lose_reply)
            with pytest.raises(LostReply):
                asyncio.run(root.run_async(workflow.context))
        assert len(lost) == len(case.wire.calls) == 1
        assert case.store.db.execute("SELECT result FROM runtime_actions").fetchone()[0] is None
        receipt = sra.validate_sra_file_receipt(lost[0]["result"])
        source = case.store.get(receipt["source_ref"])
        def read_acquired(context):
            assert context["last_local_outcome"]["result"] == receipt
            return action("source.read", dict(source_ref=source["id"], representation="original", offset=0, limit=4096))
        receiving = ReceivingProvider([read_acquired], connection)
        restored = _workflow(case.store, case.tools, receiving, tmp_path / "workflow",
            initial=[case.advertisement], loop=True)
        restored_root = restored.build("improvement", "root", QUESTION, case.scope)
        # Only cached acquisition is forbidden from opening entity bodies.
        async def metadata_cached(registry, name, arguments, **kwargs):
            if name == sra.TOOL:
                with monkeypatch.context() as patch:
                    _forbid_entities(patch, case, source)
                    return await execute(registry, name, arguments, **kwargs)
            return await execute(registry, name, arguments, **kwargs)
        monkeypatch.setattr(ToolRegistry, "execute_async", metadata_cached)
        monkeypatch.setattr(PublicClients, "_http", forbidden)
        record = asyncio.run(restored_root.run_async(restored.context))
        result = asyncio.run(restored_root.build_result(record)).as_record()
        dispatches = actor.dispatches + receiving.dispatches
        calls = list(case.store.db.execute("SELECT request,response FROM runtime_model_calls ORDER BY call_index"))
        assert len(calls) == len(dispatches) == 2 and all(row["response"] is not None for row in calls)
        for dispatch, row in zip(dispatches, calls):
            assert json.loads(row["request"])["context"] == dispatch["context"]
            assert json.loads(dispatch["wire"]) == dispatch["context"]
            assert dispatch["model_instructions"] == dispatch["instructions"]
            assert QUESTION in json.dumps(dispatch["context"]["goal"])
            assert dispatch["context"]["requested_form"] is None
        context = restored.binding_context(restored_root.source)
        known = set(restored.receipts.known(context.episode_id))
        assert known == baseline | {source["id"], source["artifact_ref"]}
        resolve = restored.resolver(plain(context.scope), context=context)
        assert resolve(source["id"], "source") is True and resolve(source["artifact_ref"], "artifact") is True
        for private in [source["request_ref"], *source["auxiliary_artifact_refs"]]:
            assert private not in known and resolve(private, "artifact") is False
        read = json.loads(case.store.db.execute("SELECT result FROM runtime_actions WHERE decision_index=1").fetchone()[0])
        assert read["status"] == "completed" and read["result"]["artifact_ref"] == source["artifact_ref"]
        assert read["result"]["text"] == ENGINEERED.decode()
        assert case.store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 1
        assert case.store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 2
        assert case.store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 2
        assert case.store.db.execute("SELECT count(*) FROM runtime_forms").fetchone()[0] == 0
        before, files, archives = _snapshot(case.store), _artifacts(case.store.path / "artifacts"), _artifacts(tmp_path / "workflow" / "archive")
        monkeypatch.setattr(ToolRegistry, "execute_async", forbidden)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        replay_actor = ScriptedProvider([])
        replay = _workflow(case.store, case.tools, replay_actor, tmp_path / "workflow",
            initial=[case.advertisement], loop=True)
        closed = replay.build("improvement", "root", QUESTION, case.scope)
        recovered = asyncio.run(closed.run_async(replay.context))
        assert asyncio.run(closed.build_result(recovered)).as_record() == result
        assert replay_actor.contexts == [] and len(case.wire.calls) == 1
        assert _snapshot(case.store) == before and _artifacts(case.store.path / "artifacts") == files
        assert _artifacts(tmp_path / "workflow" / "archive") == archives


def _live_sra_normalized_arguments(advertisement_file):
    """Literal caller selection from the authenticated210 XML, with no fallback."""
    return sra.validate_sra_file_arguments(dict(advertisement_file=deepcopy(advertisement_file),
        experiment_package_ordinal_0based=0, run_ordinal_0based=0, file_ordinal_0based=1,
        url_selection=dict(kind="file_url"), run_accession="SRR6263255", semantic_name="SRA Normalized",
        supertype="Primary ETL", file_name="SRR6263255",
        url="https://sra-pub-run-odp.s3.amazonaws.com/sra/SRR6263255/SRR6263255", max_bytes=1024**3))


def test_live_current_episode_entrez_advertisement_then_one_explicit_sra_normalized_transfer(tmp_path, monkeypatch):
    """Opt-in live invocation prefix; no episode or scientific completion claim."""
    import os
    from pathlib import Path
    from gene_annotation_episode import ncbi_entrez_acquisition as entrez
    from gene_annotation_episode import ncbi_entrez_tools as entrez_tools
    from gene_annotation_episode.acquisition import AcquisitionError
    from gene_annotation_episode.data_acquisition_receipts import validate_acquisition_receipt
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords

    if os.environ.get("HMMER_NATIVE_ORACLE_SRA_LIVE_WORKFLOW") != "1":
        pytest.skip("requires explicit bounded live metadata and up-to-1GiB archive acquisition selection")
    fixture = Path(__file__).parent / "fixtures/ncbi_sra/experiment_package.xml"
    fixture_raw = fixture.read_bytes()
    assert len(fixture_raw) == 7802 and hashlib.sha256(fixture_raw).hexdigest() == (
        "e2e72cc189d988194ef9ab9faff6b96132749afd7cdc3293f386902544e45b10")
    metadata_arguments = entrez.validate_entrez_arguments(dict(operation="fetch", database="sra",
        ids=["SRR6263255"], native_format="sra_experiment_package_xml", max_bytes=8*1024**2))
    metadata_spec = entrez.entrez_request_spec(metadata_arguments)
    question = ("Retain the explicitly requested SRR6263255 metadata and caller-selected SRA Normalized file "
        "for a separately selected future decoder, preserving any retrieval failure and its actual Source. "
        "Acquisition alone establishes neither archive contents nor a biological conclusion.")
    proof = dict(version="live_ordinary_sra_advertisement_and_file_v1", phase="prepared", passed=False,
        invocation_and_controlled_failure_correct=False, metadata_acquired=False, archive_acquired=False,
        whole_episode_completed=False,
        live_http_calls=[], cache_control_reads=[], archive_decoded=False,
        qualification="One live metadata GET and at most one explicitly selected archive GET; no retries, fallback, analysis or archive decoding.",
        caller_selection_provenance=dict(fixture=str(fixture), sha256=hashlib.sha256(fixture_raw).hexdigest(),
            occurrence=dict(experiment_package_ordinal_0based=0, run_ordinal_0based=0, file_ordinal_0based=1)),
        required_runtime_material="Bounded runner must explicitly bind the selected TLS, DNS and NSS native-library closure.")
    output = tmp_path / "SRA_LIVE_ORDINARY_WORKFLOW.json"
    metadata_failures = (
        "provider_connection_failed", "provider_request_timeout", "provider_body_capture_failed",
        "provider_response_byte_limit", "data_acquisition_failed", "data_acquisition_publication_incomplete",
        "ncbi_entrez_http_status_unknown", "ncbi_entrez_http_not_success", "ncbi_entrez_unrequested_range_response",
        "ncbi_entrez_capture_not_complete", "ncbi_entrez_native_error_response", "ncbi_entrez_native_format_unavailable",
        "ncbi_entrez_native_response_identity_missing", "ncbi_entrez_native_response_identity_conflict",
        "ncbi_entrez_selected_record_identity_conflict")
    try:
        with Store(tmp_path / "store") as store:
            store.create_problem(raw_sequence="ACGT", molecule="dna")
            scope = store.validate_scope()
            clients = PublicClients(ncbi_email=None, timeout=120)
            actual_http = clients._http

            def once_http(service, url, params, media_type, **kwargs):
                index = len(proof["live_http_calls"])
                assert index < 2
                if index == 0:
                    assert service == metadata_spec["service"] and url == metadata_spec["url"]
                    assert params == metadata_spec["params"] and media_type == metadata_spec["media_type"]
                    expected_limit = 8*1024**2
                else:
                    assert service == sra.SERVICE and params == {} and media_type == "application/octet-stream"
                    assert url == "https://sra-pub-run-odp.s3.amazonaws.com/sra/SRR6263255/SRR6263255"
                    expected_limit = 1024**3
                assert kwargs == dict(max_bytes=expected_limit, timeout_seconds=120, follow_redirects=False)
                call = dict(service=service, url=url, params=deepcopy(params), media_type=media_type,
                    policy=deepcopy(kwargs), returned_snapshot=None)
                proof["live_http_calls"].append(call)
                try:
                    snapshot = actual_http(service, url, params, media_type, **kwargs)
                except AcquisitionError as error:
                    snapshot = error.snapshot
                    call["failure_code"] = error.code
                    if snapshot is not None:
                        call["returned_snapshot"] = dict(sha256=hashlib.sha256(snapshot.content).hexdigest(),
                            size_bytes=len(snapshot.content), retrieved_at=snapshot.retrieved_at,
                            transport=deepcopy(snapshot.transport))
                    raise
                call["returned_snapshot"] = dict(sha256=hashlib.sha256(snapshot.content).hexdigest(),
                    size_bytes=len(snapshot.content), retrieved_at=snapshot.retrieved_at,
                    transport=deepcopy(snapshot.transport))
                return snapshot

            monkeypatch.setattr(clients, "_http", once_http)
            monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
            monkeypatch.setattr(ToolRegistry, "_sequence_worker_async", forbidden)
            tools = ToolRegistry(store, clients=clients)
            selected_archive = []
            workflow = _workflow(store, tools, NoModel(), tmp_path / "workflow", run_id="live-ordinary-sra-file")
            root = workflow.build("improvement", "root", question, scope)
            caller_context = workflow.binding_context(root.source)
            baseline = set(workflow.receipts.known(caller_context.episode_id))
            assert root.request.report_contract is None and workflow.episode_bindings.roles == ()
            assert {entrez.TOOL, sra.TOOL} <= {item["name"] for item in workflow.catalog(scope, source=root.source)}

            def dispatch(index, name, arguments):
                selected = dict(kind="tool", tool=name, arguments=deepcopy(arguments))
                try:
                    asyncio.run(root.source.execute(selected, index))
                except ActionFailure:
                    pass
                row = workflow.journal.row("runtime_actions", root.source.episode_id, index)
                assert json.loads(row["action"]) == selected and row["result"] is not None
                return deepcopy(root.source.last_outcome)

            metadata_outcome = dispatch(0, entrez.TOOL, metadata_arguments)
            proof.update(phase="metadata_attempt_returned", metadata_arguments=metadata_arguments,
                metadata_outcome=metadata_outcome)
            metadata_receipt = validate_acquisition_receipt(metadata_outcome["result"],
                failure_codes=metadata_failures, invalid_code="live_entrez_receipt_invalid")
            if metadata_receipt["acquired"]:
                known = set(workflow.receipts.known(caller_context.episode_id))
                assert {metadata_receipt["source_ref"], metadata_receipt["data_ref"]} <= known
                metadata = host._metadata(store, metadata_receipt["data_ref"])
                file = dict(artifact_ref=metadata["id"], sha256=metadata["sha256"], size_bytes=metadata["size"],
                    format=sra.ADVERTISEMENT_FORMAT)
                arguments = _live_sra_normalized_arguments(file)
                selected_archive.append(arguments)
                proof["archive_arguments"] = arguments
                proof["archive_outcome"] = dispatch(1, sra.TOOL, arguments)
                proof["phase"] = "archive_attempt_returned"
            actions = [dict(row) for row in store.db.execute("SELECT * FROM runtime_actions ORDER BY decision_index")]
            operations = [dict(row) for row in store.db.execute("SELECT * FROM tool_operations ORDER BY rowid")]
            assert len(actions) == len(operations) in (1, 2)
            outcomes = [json.loads(row["result"]) for row in actions]
            receipts = [validate_acquisition_receipt(outcomes[0]["result"], failure_codes=metadata_failures,
                invalid_code="live_entrez_receipt_invalid")]
            if len(actions) == 2:
                receipts.append(sra.validate_sra_file_receipt(outcomes[1]["result"]))
            assert len(actions) == (2 if receipts[0]["acquired"] else 1)
            assert [json.loads(row["action"])["tool"] for row in actions] == [entrez.TOOL, *([sra.TOOL] if len(actions) == 2 else [])]
            assert len(selected_archive) == len(actions)-1
            assert 1 <= len(proof["live_http_calls"]) <= len(actions)
            assert len(proof["live_http_calls"]) == 1 + sum(call["service"] == sra.SERVICE for call in proof["live_http_calls"])
            expected_known, sources, private_controls = set(baseline), [], set()
            for index, (row, operation, outcome, receipt) in enumerate(zip(actions, operations, outcomes, receipts)):
                selection = json.loads(row["action"])
                assert operation["name"] == selection["tool"] and json.loads(operation["arguments"]) == selection["arguments"]
                assert operation["operation_key"] == f"{workflow.run_id}:{root.source.episode_id}:{index}"
                saved = json.loads(operation["result"])
                assert saved == {key: value for key, value in outcome.items() if key != "pending_work_after_action"}
                expected_refs = [] if receipt["source_ref"] is None else [receipt["source_ref"]]
                if receipt["acquired"]:
                    assert outcome["status"] == "completed" and outcome["feedback"] is None
                    expected_refs.append(receipt["data_ref"])
                else:
                    assert outcome["status"] in {"partial", "invalid", "failed", "unavailable"}
                    assert outcome["feedback"]["code"] == receipt["failure_code"]
                assert outcome["record_refs"] == expected_refs
                expected_known.update(expected_refs)
                if receipt["source_ref"] is not None:
                    source = store.get(receipt["source_ref"])
                    assert source["origin"] == "external" and source["provider"] == selection["tool"]
                    assert source["accession"] is source["version"] is None
                    sources.append(source)
                    private_controls.update([source["request_ref"], *source.get("auxiliary_artifact_refs", [])])
                    snapshot = proof["live_http_calls"][index]["returned_snapshot"]
                    assert snapshot is not None
                    metadata = host._metadata(store, source["artifact_ref"])
                    assert metadata["sha256"] == snapshot["sha256"] and metadata["size"] == snapshot["size_bytes"]
                    assert source["retrieved_at"] == snapshot["retrieved_at"]
            known = set(workflow.receipts.known(caller_context.episode_id))
            assert known == expected_known and private_controls.isdisjoint(known)
            resolve = workflow.resolver(plain(caller_context.scope), context=caller_context)
            assert all(resolve(ref, "artifact") is False for ref in private_controls)
            if selected_archive:
                advertisement = selected_archive[0]["advertisement_file"]
                admission = EpisodeReturnRecords(store, workflow.run_id, failure_prefix="live_sra_").file_admission_before(
                    caller_context, advertisement["artifact_ref"], "artifact", advertisement["artifact_ref"], 1)
                assert admission["baseline"] is False and admission["delivery"] is None
                assert admission["file_receipt"]["receipt_kind"] == "own_action" and admission["file_receipt"]["source_index"] == 0
                proof["advertisement_file"] = advertisement
                proof["advertisement_admission"] = admission
                assert not store.db.execute("SELECT 1 FROM runtime_forms").fetchone()
                if receipts[1]["source_ref"] is not None:
                    archive_source = store.get(receipts[1]["source_ref"])
                    witness, = archive_source["auxiliary_artifact_refs"]
                    evidence = json.loads(store.get_artifact(witness))
                    assert evidence["prepared"]["input"]["admission"] == admission
                    assert evidence["prepared"]["arguments"] == selected_archive[0]
                    if evidence["evidence"]["kind"] == "value":
                        value = sra.validate_sra_file_value(evidence["evidence"]["value"])
                        assert value["checks"]["archive_identity"] == "not_parsed"
                        assert value["requested"] == selected_archive[0]
                        proof["archive_value"] = value
            counts = {name: store.db.execute("SELECT count(*) FROM " + name).fetchone()[0]
                for name in ("runtime_episodes", "runtime_actions", "runtime_model_calls", "runtime_observations",
                    "runtime_forms", "runtime_report_attempts")}
            assert counts == dict(runtime_episodes=1, runtime_actions=len(actions), runtime_model_calls=0,
                runtime_observations=0, runtime_forms=0, runtime_report_attempts=0)
            episode, = store.db.execute("SELECT state,completion,archive FROM runtime_episodes")
            assert tuple(episode) == ("active", None, None)
            if receipts[0]["acquired"]:
                before, files = _snapshot(store), _artifacts(store.path / "artifacts")
                original_get = Store.get_artifact
                with monkeypatch.context() as patch:
                    def controls_only(current, reference):
                        assert reference in private_controls, "cache reopened original advertisement/archive entity"
                        proof["cache_control_reads"].append(reference)
                        return original_get(current, reference)
                    patch.setattr(Store, "get_artifact", controls_only)
                    patch.setattr(Store, "artifact", forbidden)
                    patch.setattr(Store, "put", forbidden)
                    patch.setattr(PublicClients, "_http", forbidden)
                    patch.setattr(clients, "_http", forbidden)
                    patch.setattr(host, "read_bytes", forbidden)
                    patch.setattr(host, "retained_native_file", forbidden)
                    patch.setattr(sra, "resolve_sra_file_selection", forbidden)
                    patch.setattr(sra, "sra_file_value", forbidden)
                    patch.setattr(host, "publish_sra_file_request", forbidden)
                    patch.setattr(entrez, "entrez_result", forbidden)
                    patch.setattr(entrez, "validate_entrez_result", forbidden)
                    patch.setattr(entrez_tools, "publish_ncbi_entrez_request", forbidden)
                    patch.setattr(ToolRegistry, "_source", forbidden)
                    patch.setattr(ToolRegistry, "_save", forbidden)
                    for row, operation in zip(actions, operations):
                        selected = json.loads(row["action"])
                        replay = asyncio.run(workflow.execute(root.source, selected["tool"], selected["arguments"],
                            decision_index=row["decision_index"], operation_key=operation["operation_key"]))
                        assert replay == json.loads(operation["result"])
                assert _snapshot(store) == before and _artifacts(store.path / "artifacts") == files
                proof["cache_rows_and_files_unchanged"] = True
                proof["cache_entity_and_http_parser_publisher_calls_forbidden"] = True
                proof["integrity_inventory_reads_performed"] = True
            else:
                proof["cache_verification"] = "not_selected_metadata_not_acquired"
            proof.update(phase="invocation_prefix_verified", passed=True, invocation_and_controlled_failure_correct=True,
                metadata_acquired=receipts[0]["acquired"], archive_acquired=len(receipts) == 2 and receipts[1]["acquired"],
                metadata_arguments=metadata_arguments, archive_arguments=selected_archive[0] if selected_archive else None,
                receipts=receipts, outcomes=outcomes, source_records=sources, counts=counts,
                receipt_rows=[dict(row) for row in store.db.execute("SELECT * FROM runtime_record_receipts ORDER BY receipt_index")],
                provider_decision_calls=0, archive_identity="not_parsed")
    except BaseException as error:
        proof["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        output.write_text(json.dumps(proof, sort_keys=True, indent=2, allow_nan=False) + "\n")
