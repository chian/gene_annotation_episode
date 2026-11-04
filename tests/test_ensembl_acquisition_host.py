"""Actual Store, receipt, operation and HTTP transport controls for BioMart."""
import asyncio
import base64
from copy import deepcopy
from dataclasses import replace
from email.message import Message
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
from types import SimpleNamespace
import urllib.error
import urllib.request

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients
from gene_annotation_episode import ensembl_acquisition as native
from gene_annotation_episode import ensembl_acquisition_host as host
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.molecular_reference_privacy import molecular_reference_restriction
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.providers import _SessionConnection

import test_ensembl_acquisition as captures
from test_alphafold_acquisition_host import Provider, _controller, _credit, _selected
from test_molecular_provider_acquisition_host import _artifacts, _tables
from test_runtime import FixtureController, ScriptedProvider
from test_scientific_process_runtime import action


def forbidden(*args, **kwargs):
    raise AssertionError("Ensembl proof attempted forbidden work")


class Response(io.BytesIO):
    def __init__(self, raw, status, headers, url):
        super().__init__(raw)
        self.status, self.headers, self.url = status, headers, url

    def geturl(self):
        return self.url


class HTTP:
    def __init__(self):
        self.planned, self.requests = [], []

    def add(self, raw, *, status=200, media_type="text/plain", **headers):
        self.planned.append((raw, status, media_type, headers))

    def open(self, request, timeout):
        self.requests.append({"url": request.full_url, "method": request.get_method(),
            "body": request.data, "headers": dict(request.header_items()), "timeout": timeout})
        assert self.planned, "unselected additional BioMart request"
        raw, status, media_type, selected_headers = self.planned.pop(0)
        if isinstance(raw, Exception):
            raise raw
        headers = Message()
        for name, value in {"Content-Type": media_type, "Content-Length": str(len(raw)), **selected_headers}.items():
            headers[name] = value
        if not 200 <= status < 300:
            raise urllib.error.HTTPError(request.full_url, status, "Engineered native status", headers, io.BytesIO(raw))
        return Response(raw, status, headers, request.full_url)


@pytest.fixture
def http(monkeypatch):
    value = HTTP()
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_handlers: value)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    return value


@pytest.fixture
def acquired(tmp_path, http, request):
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=PublicClients(timeout=3))
        scope = {"subject_refs": store.create_problem(raw_sequence="ACGTACGT", molecule="dna")["subject_refs"]}
        workflow = Workflow(store, tools, Provider(), tmp_path / "run", "ensembl-host-controls", _controller, _credit,
            project_child_credit=_credit, episode_record_receipts=True, initial_known_record_refs=[])
        root = workflow.build("annotation", "root", "Retain explicitly selected BioMart evidence.", scope)
        http.add(captures.REGISTRY_XML, media_type="application/xml")
        registry_args = captures.arguments("registry")
        registry = _selected(tools, workflow, root, native.TOOL, registry_args, 0, record=True)
        assert registry["status"] == "completed"
        http.add(captures.DATASETS_TSV)
        datasets_args = captures.arguments("datasets", registry_source_ref=registry["result"]["source_ref"])
        datasets = _selected(tools, workflow, root, native.TOOL, datasets_args, 1, record=True)
        assert datasets["status"] == "completed"
        configurations = []
        for index, dataset in enumerate((captures.SOURCE_DATASET, captures.TARGET_DATASET), 2):
            attributes = (getattr(request, "param", {}).get("source_attributes")
                if dataset == captures.SOURCE_DATASET else None)
            http.add(captures.configuration(dataset, attributes=attributes), media_type="application/xml")
            selected = captures.arguments("configuration", dataset=dataset,
                datasets_source_ref=datasets["result"]["source_ref"])
            value = _selected(tools, workflow, root, native.TOOL, selected, index, record=True)
            assert value["status"] == "completed"
            configurations.append(value)
        arguments = captures.arguments("gene_homologies", source_configuration_ref=configurations[0]["result"]["source_ref"],
            target_configuration_ref=configurations[1]["result"]["source_ref"])
        context = workflow.binding_context(root.source)
        yield SimpleNamespace(store=store, tools=tools, workflow=workflow, root=root, scope=scope,
            context=context, authority=(context, workflow.services.read_received_molecular_input), arguments=arguments,
            registry=registry, datasets=datasets, configurations=configurations, http=http)


def execute(case, *, arguments=None, index=4, record=True):
    return _selected(case.tools, case.workflow, case.root, native.TOOL,
        case.arguments if arguments is None else arguments, index, record=record)


def source(case, outcome):
    return case.store.get(outcome["record_refs"][0])


def _native(case, outcome):
    """Inspect the actual private Value for native assertions, not a grant."""
    saved = source(case, outcome)
    private = json.loads(case.store.get_artifact(saved["auxiliary_artifact_refs"][1]))
    assert native.ensembl_receipt(private, source_ref=saved["id"]) == outcome["result"]
    return native.ensembl_result_from_value(private, source_ref=saved["id"])


def test_registry_keeps_ordinary_manual_acquisition_support_without_invented_runtime_actions(tmp_path, http):
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=PublicClients(timeout=3))
        scope = {"subject_refs": store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]}
        http.add(captures.REGISTRY_XML, media_type="application/xml")
        selected = captures.arguments("registry")
        outcome = asyncio.run(tools.execute_async(native.TOOL, selected, scope=scope, operation_key="caller-registry"))
        assert outcome["status"] == "completed" and len(http.requests) == 1
        saved = store.get(outcome["result"]["source_ref"])
        assert saved["parent_source_refs"] == [] and outcome["record_refs"] == [saved["id"], saved["artifact_ref"]]
        assert store.get_artifact(saved["artifact_ref"]) == captures.REGISTRY_XML


def test_real_catalog_request_transport_and_source_custody_keep_exact_selected_native_query(acquired):
    raw = captures.table(captures.row(), captures.row(target="ENSMUSG00000000001"))
    acquired.http.add(raw, media_type="text/plain; charset=utf-8")
    outcome = execute(acquired)
    assert outcome["status"] == "completed" and len(acquired.http.requests) == 5
    assert acquired.tools.catalog(acquired.scope)[native.TOOL]["input_schema"] == native.ARGUMENTS_SCHEMA
    value, saved = _native(acquired, outcome), source(acquired, outcome)
    assert saved["provider"] == "ensembl" and saved["origin"] == "external"
    assert saved["version"] is saved["accession"] is None
    assert saved["parent_source_refs"] == native.ensembl_discovery_refs(acquired.arguments)
    assert outcome["record_refs"] == [saved["id"], saved["artifact_ref"]]
    assert value["native_text"].encode() == acquired.store.get_artifact(saved["artifact_ref"]) == raw
    assert value["raw_artifact_ref"] == saved["artifact_ref"] == "artifact_" + hashlib.sha256(raw).hexdigest()
    assert value["retained_row_count"] == 2 and value["requested_id_count"] == 1
    request = acquired.http.requests[-1]
    spec = native.ensembl_request_spec(acquired.arguments)
    assert request["url"] == native.URL and request["method"] == "POST" and request["body"] == spec["body"]
    assert request["timeout"] == 3 and request["headers"]["Content-type"] == spec["content_type"]
    control = json.loads(acquired.store.get_artifact(saved["request_ref"]))
    assert control["request"] == acquired.arguments
    assert control["transport"]["request"]["body_sha256"] == hashlib.sha256(spec["body"]).hexdigest()
    private = {saved["request_ref"], *saved["auxiliary_artifact_refs"]}
    assert outcome["result"] == dict(acquired=True, source_ref=saved["id"], data_ref=saved["artifact_ref"], failure_code=None)
    assert not private.intersection(outcome["record_refs"])
    assert not private.intersection(acquired.workflow.receipts.known(acquired.context.episode_id))
    assert not acquired.store.query_records("reference", scope=acquired.scope)["records"]


@pytest.mark.parametrize("status", [200, 301, 429, 500])
def test_native_errors_http_failures_and_exact_error_bodies_are_retained_without_retry(acquired, status):
    raw = b"Query ERROR: caught BioMart::Exception::Usage: native attribute unavailable\n"
    acquired.http.add(raw, status=status, **{"Retry-After": "17", "Location": "https://do-not-follow.example.org"})
    outcome = execute(acquired)
    assert outcome["status"] == "partial" and len(acquired.http.requests) == 5
    assert outcome["result"]["failure_code"] == ("ensembl_native_error_response" if status == 200 else "ensembl_http_redirect" if status == 301 else "ensembl_http_not_success")
    assert _native(acquired, outcome)["response"]["http_status"] == status
    assert _native(acquired, outcome)["response"]["retry_after"] == "17"
    assert acquired.store.get_artifact(source(acquired, outcome)["artifact_ref"]) == raw


def test_bounded_capture_failure_keeps_original_prefix_and_independent_incomplete_state(acquired):
    raw = captures.table(captures.row())
    acquired.http.add(raw)
    selected = {**acquired.arguments, "max_bytes": 64}
    outcome = execute(acquired, arguments=selected)
    assert outcome["status"] == "partial" and len(acquired.http.requests) == 5
    value = _native(acquired, outcome)
    assert value["response"]["body_complete"] is False and value["response"]["retained_bytes"] == 64
    assert {"response_incomplete", "response_byte_limit_exceeded"} <= captures.codes(value)
    assert acquired.store.get_artifact(source(acquired, outcome)["artifact_ref"]) == raw[:64]


def test_denied_direct_source_stops_before_any_private_bytes_or_http(acquired, monkeypatch):
    acquired.store.db.execute("DELETE FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=?",
        (acquired.workflow.run_id, acquired.context.episode_id, acquired.arguments["target_configuration_ref"]))
    monkeypatch.setattr(Store, "get_artifact", forbidden)
    outcome = execute(acquired)
    assert outcome["status"] == "invalid" and outcome["result"] == native.failed_ensembl_receipt("ensembl_source_not_received") and outcome["record_refs"] == []
    assert outcome["feedback"]["code"] == "ensembl_source_not_received" and len(acquired.http.requests) == 4


def test_only_received_configurations_allow_private_sealed_ancestry_without_ancestor_or_file_grants(acquired, tmp_path, monkeypatch):
    configs = native.ensembl_discovery_refs(acquired.arguments)
    workflow = Workflow(acquired.store, acquired.tools, Provider(), tmp_path / "new-receiver", "ensembl-new-receiver",
        _controller, _credit, project_child_credit=_credit, episode_record_receipts=True,
        initial_known_record_refs=configs)
    root = workflow.build("annotation", "root", "Use only the explicitly received BioMart configurations.", acquired.scope)
    context = workflow.binding_context(root.source)
    known = set(workflow.receipts.known(context.episode_id))
    ancestors = {acquired.registry["result"]["source_ref"], acquired.datasets["result"]["source_ref"]}
    raw_refs = {source(acquired, value)["artifact_ref"] for value in
        (acquired.registry, acquired.datasets, *acquired.configurations)}
    assert set(configs) <= known and not (ancestors | raw_refs).intersection(known)
    original_reader, seen = WorkflowServices.read_received_molecular_input, []
    def metadata_only(services, current, reference, namespace, **kwargs):
        assert namespace == "source" and kwargs == {"source_metadata_only": True}
        seen.append(reference)
        return original_reader(services, current, reference, namespace, **kwargs)
    monkeypatch.setattr(WorkflowServices, "read_received_molecular_input", metadata_only)
    acquired.http.add(captures.table(captures.row()))
    outcome = _selected(acquired.tools, workflow, root, native.TOOL, acquired.arguments, 0, record=True)
    assert outcome["status"] == "completed" and seen == configs and len(acquired.http.requests) == 5
    after = set(workflow.receipts.known(context.episode_id))
    assert after - known == set(outcome["record_refs"]) and not (ancestors | raw_refs).intersection(after)


@pytest.mark.parametrize("damage", ["source_record", "original_action", "producer_result", "missing_producer"])
def test_discovery_ids_alone_cannot_replace_actual_source_and_original_producer_joins(acquired, damage):
    reference = acquired.arguments["source_configuration_ref"]
    if damage == "source_record":
        saved = acquired.store.get(reference); saved["parent_source_refs"] = []
        acquired.store.db.execute("UPDATE records SET data=? WHERE id=?", (canonical(saved), reference))
    elif damage == "original_action":
        acquired.store.db.execute("UPDATE runtime_actions SET action=? WHERE decision_index=2", (canonical({"kind": "tool", "tool": "wrong", "arguments": {}}),))
    elif damage == "producer_result":
        outcome = deepcopy(acquired.configurations[0]); outcome["result"]["data_ref"] = "artifact_" + "0" * 64
        acquired.store.db.execute("UPDATE tool_operations SET result=? WHERE id=?", (canonical(outcome), outcome["operation_ref"]))
        acquired.store.db.execute("UPDATE runtime_actions SET result=? WHERE decision_index=2", (canonical(outcome),))
    else:
        acquired.store.db.execute("DELETE FROM tool_operations WHERE id=?", (acquired.configurations[0]["operation_ref"],))
    outcome = execute(acquired)
    assert outcome["status"] == "invalid" and outcome["record_refs"] == [] and len(acquired.http.requests) == 4


@pytest.mark.parametrize("raw,status", [(captures.table(captures.row()), "completed"),
    (b"Query ERROR: native retained denial", "partial"), (b"\xff", "partial")])
def test_pending_saved_outcome_replays_without_native_entity_reads_http_or_new_operation(acquired, monkeypatch, raw, status):
    acquired.http.add(raw)
    outcome = execute(acquired, record=False)
    assert outcome["status"] == status
    raw_refs = {source(acquired, value)["artifact_ref"] for value in
        (acquired.registry, acquired.datasets, *acquired.configurations)} | {source(acquired, outcome)["artifact_ref"]}
    actual_get, reads = Store.get_artifact, []
    def controls_only(store, reference):
        assert reference not in raw_refs, "cached selection reopened a scientific entity"
        reads.append(reference)
        return actual_get(store, reference)
    monkeypatch.setattr(Store, "get_artifact", controls_only)
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    key = f"{acquired.workflow.run_id}:{acquired.context.episode_id}:4"
    with acquired.tools.current_invocation(acquired.context,
            read_received=acquired.workflow.services.read_received_molecular_input,
            tool_name=native.TOOL, arguments=acquired.arguments, operation_key=key):
        replay = asyncio.run(acquired.tools.execute_async(native.TOOL, acquired.arguments,
            scope=plain(acquired.context.scope), operation_key=key))
    assert replay == outcome and reads and len(acquired.http.requests) == 5
    assert acquired.store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 5


def test_connection_failure_has_no_new_source_and_replays_its_original_diagnostic(acquired, monkeypatch):
    acquired.http.add(urllib.error.URLError("engineered no response"))
    outcome = execute(acquired, record=False)
    assert outcome["status"] == "failed" and outcome["result"] == native.failed_ensembl_receipt("data_acquisition_failed") and outcome["record_refs"] == []
    assert outcome["feedback"]["code"] == "provider_connection_failed"
    monkeypatch.setattr(Store, "get_artifact", forbidden)
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    key = f"{acquired.workflow.run_id}:{acquired.context.episode_id}:4"
    with acquired.tools.current_invocation(acquired.context,
            read_received=acquired.workflow.services.read_received_molecular_input,
            tool_name=native.TOOL, arguments=acquired.arguments, operation_key=key):
        replay = asyncio.run(acquired.tools.execute_async(native.TOOL, acquired.arguments,
            scope=plain(acquired.context.scope), operation_key=key))
    assert replay == outcome and len(acquired.http.requests) == 5


@pytest.mark.parametrize("damage", ["selected_snapshot", "prepared_selection"])
def test_source_first_association_failure_preserves_only_the_actual_new_source(acquired, monkeypatch, damage):
    if damage == "selected_snapshot":
        original = PublicClients.ensembl_request
        def changed(client, *, arguments):
            value = original(client, arguments=arguments)
            return replace(value, request={**value.request, "max_bytes": value.request["max_bytes"] - 1})
        monkeypatch.setattr(PublicClients, "ensembl_request", changed)
    else:
        original = host.prepare_ensembl_request
        def changed(*args, **kwargs):
            value = original(*args, **kwargs)
            value["selection"]["sources"][0]["operation_result_sha256"] = "0" * 64
            return value
        monkeypatch.setattr(host, "prepare_ensembl_request", changed)
    raw = captures.table(captures.row())
    acquired.http.add(raw)
    outcome = execute(acquired)
    assert outcome["status"] == "partial" and len(acquired.http.requests) == 5
    saved = source(acquired, outcome)
    assert outcome["record_refs"] == [saved["id"]]
    assert outcome["result"]["acquired"] is False and outcome["result"]["source_ref"] == saved["id"]
    assert outcome["result"]["data_ref"] is None
    assert acquired.store.get_artifact(saved["artifact_ref"]) == raw
    assert saved["artifact_ref"] not in outcome["record_refs"] and saved["request_ref"] not in outcome["record_refs"]
    if damage == "prepared_selection":
        assert "parent_source_refs" not in saved and len(saved["auxiliary_artifact_refs"]) == 1
        assert json.loads(acquired.store.get_artifact(saved["auxiliary_artifact_refs"][0]))["version"] == host.FAILURE_WITNESS_VERSION


@pytest.mark.parametrize("status", [200, 429])
def test_actual_client_normalizes_selected_processing_media_and_arguments_for_success_and_error(acquired, status):
    acquired.http.add(b"native text", status=status, media_type="text/plain; charset=utf-8")
    if status == 200:
        snapshot = acquired.tools.clients.ensembl_request(arguments=acquired.arguments)
    else:
        with pytest.raises(AcquisitionError) as caught:
            acquired.tools.clients.ensembl_request(arguments=acquired.arguments)
        snapshot = caught.value.snapshot
    assert snapshot.request == acquired.arguments and snapshot.media_type == "text/plain"
    assert snapshot.transport["headers"]["content-type"] == "text/plain; charset=utf-8"
    assert snapshot.transport["request"]["method"] == "POST" and len(acquired.http.requests) == 5


@pytest.mark.parametrize("damage", ["selected_snapshot", "prepared_selection"])
def test_sealed_and_unsealed_failed_witness_cache_replays_without_entity_reads_or_new_publication(
        acquired, monkeypatch, damage):
    if damage == "selected_snapshot":
        original = PublicClients.ensembl_request
        def changed(client, *, arguments):
            snapshot = original(client, arguments=arguments)
            return replace(snapshot, request={**snapshot.request, "max_bytes": snapshot.request["max_bytes"] - 1})
        monkeypatch.setattr(PublicClients, "ensembl_request", changed)
    else:
        original = host.prepare_ensembl_request
        def changed(*args, **kwargs):
            prepared = original(*args, **kwargs)
            prepared["selection"]["sources"][0]["operation_result_sha256"] = "0" * 64
            return prepared
        monkeypatch.setattr(host, "prepare_ensembl_request", changed)
    acquired.http.add(captures.table(captures.row()))
    outcome = execute(acquired, record=False)
    saved = source(acquired, outcome)
    assert outcome["status"] == "partial" and outcome["result"]["acquired"] is False
    assert outcome["result"]["source_ref"] == saved["id"] and outcome["result"]["data_ref"] is None
    assert len(saved["auxiliary_artifact_refs"]) == (2 if damage == "selected_snapshot" else 1)
    before, files = _tables(acquired.store), _artifacts(acquired.store.path / "artifacts")
    entities = {row["artifact_ref"] for row in acquired.store.list("source") if row["provider"] == "ensembl"}
    actual_get = Store.get_artifact
    def controls_only(store, reference):
        assert reference not in entities
        return actual_get(store, reference)
    monkeypatch.setattr(Store, "get_artifact", controls_only)
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    monkeypatch.setattr(host, "prepare_ensembl_request", forbidden)
    monkeypatch.setattr(host, "publish_ensembl_request", forbidden)
    key = f"{acquired.workflow.run_id}:{acquired.context.episode_id}:4"
    with acquired.tools.current_invocation(acquired.context,
            read_received=acquired.workflow.services.read_received_molecular_input,
            tool_name=native.TOOL, arguments=acquired.arguments, operation_key=key):
        replay = asyncio.run(acquired.tools.execute_async(native.TOOL, acquired.arguments,
            scope=plain(acquired.context.scope), operation_key=key))
    assert replay == outcome and len(acquired.http.requests) == 5
    assert _tables(acquired.store) == before and _artifacts(acquired.store.path / "artifacts") == files


@pytest.mark.parametrize("native_error,http_status", [(False, 200), (True, 200), (True, 429)])
def test_admitted_source_primary_read_and_separately_admitted_artifact_are_distinct_existing_ports(
        acquired, tmp_path, native_error, http_status):
    raw = b"Query ERROR: original native denial\n" if native_error else captures.table(captures.row())
    acquired.http.add(raw, status=http_status)
    outcome = execute(acquired)
    assert outcome["status"] == ("partial" if native_error else "completed")
    saved = source(acquired, outcome)
    # This actual receiver was explicitly supplied only the Source, even when
    # the producing episode also received an acquired DataRef.
    workflow = Workflow(acquired.store, acquired.tools, Provider(), tmp_path / "source-only-receiver",
        "ensembl-source-only-receiver", _controller, _credit, project_child_credit=_credit,
        episode_record_receipts=True, initial_known_record_refs=[saved["id"]])
    root = workflow.build("annotation", "root", "Evaluate supplied evidence in the original scope.", acquired.scope)
    context = workflow.binding_context(root.source)
    original_known = set(workflow.receipts.known(context.episode_id))
    assert saved["id"] in original_known and saved["artifact_ref"] not in original_known
    resolve = workflow.resolver(context.scope, context=context)
    assert resolve(saved["id"], "source") is True
    assert resolve(saved["artifact_ref"], "artifact") is False
    unavailable, path = workflow.services.read_received_molecular_input(context,
        saved["artifact_ref"], "artifact", file_format="text")
    assert unavailable["failure"]["code"] == "reference_not_received" and path is None
    for index, representation in enumerate(("original", "text")):
        read = _selected(acquired.tools, workflow, root, "source.read",
            {"source_ref": saved["id"], "representation": representation, "offset": 0, "limit": len(raw)},
            index, record=True)
        assert read["status"] == "completed" and read["result"]["text"].encode() == raw
        assert read["result"]["artifact_ref"] == saved["artifact_ref"]
        assert read["result"]["representation"] == "original" and read["record_refs"] == []
    assert set(workflow.receipts.known(context.episode_id)) == original_known
    workflow.receipts.receive(context.episode_id, [saved["artifact_ref"]], kind="initial")
    assert resolve(saved["artifact_ref"], "artifact") is True
    admitted, path = workflow.services.read_received_molecular_input(context,
        saved["artifact_ref"], "artifact", file_format="text")
    assert admitted["failure"] is None and admitted["input"]["byte_verification"] == "verified"
    assert path.read_bytes() == raw
    assert set(workflow.receipts.known(context.episode_id)) - original_known == {saved["artifact_ref"]}
    assert len(acquired.http.requests) == 5


@pytest.mark.parametrize("http_status", [200, 429])
def test_unreceived_successful_or_failed_source_cannot_open_its_primary_body(acquired, monkeypatch, http_status):
    raw = captures.table(captures.row()) if http_status == 200 else b"Query ERROR: original native denial\n"
    acquired.http.add(raw, status=http_status)
    outcome = execute(acquired, record=False)
    saved = source(acquired, outcome)
    assert saved["id"] not in set(acquired.workflow.receipts.known(acquired.context.episode_id))
    resolve = acquired.workflow.resolver(acquired.context.scope, context=acquired.context)
    monkeypatch.setattr(Store, "get_artifact", forbidden)
    monkeypatch.setattr("gene_annotation_episode.materials.artifact_path", forbidden)
    assert resolve(saved["id"], "source") is False and resolve(saved["artifact_ref"], "artifact") is False
    read = _selected(acquired.tools, acquired.workflow, acquired.root, "source.read",
        {"source_ref": saved["id"], "representation": "original"}, 5, record=True)
    assert read["status"] == "invalid" and read["record_refs"] == []
    assert read["feedback"]["code"] == "ensembl_source_primary_body_not_received"
    assert len(acquired.http.requests) == 5


@pytest.mark.parametrize("http_status", [200, 429])
def test_request_and_witness_controls_remain_private_even_if_explicitly_receipted_on_success_or_failure(
        acquired, monkeypatch, http_status):
    raw = captures.table(captures.row()) if http_status == 200 else b"Query ERROR: original native denial\n"
    acquired.http.add(raw, status=http_status)
    outcome = execute(acquired)
    saved = source(acquired, outcome)
    controls = [saved["request_ref"], *saved["auxiliary_artifact_refs"]]
    acquired.workflow.receipts.receive(acquired.context.episode_id, controls, kind="initial")
    assert set(controls) <= set(acquired.workflow.receipts.known(acquired.context.episode_id))
    resolve = acquired.workflow.resolver(acquired.context.scope, context=acquired.context)
    monkeypatch.setattr(Store, "get_artifact", forbidden)
    for reference in controls:
        assert resolve(reference, "artifact") is False
        assert molecular_reference_restriction(acquired.store, None, reference, "artifact", private_only=True) is False
        denied, path = acquired.workflow.services.read_received_molecular_input(acquired.context,
            reference, "artifact", file_format="text")
        assert denied["failure"]["code"] == "reference_denied" and path is None


def test_diagnostics_are_classified_by_the_actual_public_operation_name_without_a_source(acquired, monkeypatch):
    acquired.http.add(urllib.error.URLError("engineered no response"))
    outcome = execute(acquired)
    assert outcome["status"] == "failed" and outcome["record_refs"] == []
    diagnostic = outcome["feedback"]["diagnostic_ref"]
    acquired.workflow.receipts.receive(acquired.context.episode_id, [diagnostic], kind="initial")
    resolve = acquired.workflow.resolver(acquired.context.scope, context=acquired.context)
    monkeypatch.setattr(Store, "get_artifact", forbidden)
    assert molecular_reference_restriction(acquired.store, acquired.context, diagnostic, "artifact", providers=("ensembl",)) is False
    assert resolve(diagnostic, "artifact") is False


def test_unrelated_caller_source_keeps_its_existing_forward_receipt_semantics(acquired):
    raw = acquired.store.artifact(b"original caller evidence", "text/plain")
    supplied = acquired.store.put("source", {"provider": "caller_original", "accession": None,
        "uri": None, "artifact_ref": raw, "text_ref": None, "request_ref": None,
        "version": None, "retrieved_at": None}, origin="caller")
    acquired.workflow.receipts.receive(acquired.context.episode_id, [supplied["id"]], kind="initial")
    assert {supplied["id"], raw} <= set(acquired.workflow.receipts.known(acquired.context.episode_id))
    assert molecular_reference_restriction(acquired.store, acquired.context, supplied["id"], "source") is None


@pytest.mark.parametrize("damage", ["origin", "version", "artifact_as_source"])
def test_source_primary_exception_requires_the_actual_source_type_origin_and_version_policy(acquired, monkeypatch, damage):
    acquired.http.add(captures.table(captures.row()))
    outcome = execute(acquired)
    saved = source(acquired, outcome)
    if damage == "artifact_as_source":
        reference = saved["artifact_ref"]
    else:
        payload = {key: value for key, value in saved.items() if key not in {"id", "record_type", "origin"}}
        if damage == "version":
            payload["version"] = "unqualified_version"
        supplied = acquired.store.put("source", payload, origin="caller" if damage == "origin" else "external")
        reference = supplied["id"]
    acquired.workflow.receipts.receive(acquired.context.episode_id, [reference], kind="initial")
    monkeypatch.setattr(Store, "get_artifact", forbidden)
    monkeypatch.setattr("gene_annotation_episode.materials.artifact_path", forbidden)
    read = _selected(acquired.tools, acquired.workflow, acquired.root, "source.read",
        {"source_ref": reference, "representation": "original"}, 5, record=True)
    assert read["status"] == "invalid" and read["record_refs"] == [] and len(acquired.http.requests) == 5


def test_text_selection_cannot_use_a_derivative_in_place_of_the_admitted_primary_body(acquired, monkeypatch):
    original = ToolRegistry._source
    def with_derivative(registry, provider, body, **kwargs):
        if provider == "ensembl" and kwargs["snapshot"].request["operation"] == "gene_homologies":
            kwargs["text"] = "Engineered separate text representation."
        return original(registry, provider, body, **kwargs)
    monkeypatch.setattr(ToolRegistry, "_source", with_derivative)
    raw = captures.table(captures.row())
    acquired.http.add(raw)
    outcome = execute(acquired)
    assert outcome["status"] == "completed"
    saved = source(acquired, outcome)
    assert saved["text_ref"] != saved["artifact_ref"]
    assert saved["text_ref"] not in set(acquired.workflow.receipts.known(acquired.context.episode_id))
    read = _selected(acquired.tools, acquired.workflow, acquired.root, "source.read",
        {"source_ref": saved["id"], "representation": "text"}, 5, record=True)
    assert read["status"] == "invalid" and read["feedback"]["code"] == "ensembl_source_primary_body_not_received"
    primary = _selected(acquired.tools, acquired.workflow, acquired.root, "source.read",
        {"source_ref": saved["id"], "representation": "original"}, 6, record=True)
    assert primary["status"] == "completed" and primary["result"]["text"].encode() == raw


@pytest.mark.parametrize("acquired", [{"source_attributes": [name for name in captures.ATTRIBUTES
    if name != "mmusculus_homolog_perc_id"]}], indirect=True)
def test_received_valid_configuration_missing_selected_attribute_preserves_preflight_code_without_http_or_grants(
        acquired, monkeypatch):
    before_sources = {row["id"] for row in acquired.store.list("source")}
    before_artifacts = {row[0] for row in acquired.store.db.execute("SELECT id FROM artifacts")}
    before_known = set(acquired.workflow.receipts.known(acquired.context.episode_id))
    assert len(acquired.http.requests) == 4
    assert all(value["status"] == "completed" and _native(acquired, value)["issues"] == []
        for value in acquired.configurations)
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    outcome = execute(acquired)
    assert outcome["status"] == "invalid" and outcome["result"] == native.failed_ensembl_receipt("ensembl_attribute_not_uniquely_advertised") and outcome["record_refs"] == []
    assert outcome["feedback"] == {"category": "arguments_or_reference",
        "code": "ensembl_attribute_not_uniquely_advertised"}
    assert len(acquired.http.requests) == 4
    assert {row["id"] for row in acquired.store.list("source")} == before_sources
    assert {row[0] for row in acquired.store.db.execute("SELECT id FROM artifacts")} == before_artifacts
    assert set(acquired.workflow.receipts.known(acquired.context.episode_id)) == before_known


@pytest.mark.parametrize("tag,raw", [("registry", captures.REGISTRY_XML), ("datasets", captures.DATASETS_TSV),
    ("configuration", captures.configuration()), ("gene_homologies", captures.table(captures.row()))])
def test_finite_model_view_preserves_original_dto_bytes_and_separate_capture_population_meanings(tag, raw):
    value = captures.result(captures.arguments(tag), raw)
    outcome = {"status": "completed", "record_refs": [value["source_ref"]], "result": value, "feedback": None}
    original = canonical(outcome)
    shown = native.ensembl_outcome_view(outcome)
    assert canonical(outcome) == original and shown is not outcome
    assert shown["result"]["version"] == native.MODEL_VIEW_VERSION
    assert not {"native_text", "xml_document", "tsv_lines"}.intersection(shown["result"])
    for key in ("source_ref", "raw_artifact_ref", "requested", "response", "parse_state", "decode_error",
            "representation_state", "native_response_state", "native_completion", "columns", "dataset_contexts",
            "requested_id_count", "retained_row_count", "matching_population_count", "population_coverage",
            "native_pagination", "issues"):
        assert shown["result"][key] == value[key]
    assert shown["result"]["native_body"]["retained_body_available"] is True
    if tag in {"datasets", "gene_homologies"}:
        lines = shown["result"]["native_lines"]
        assert "".join("\t".join(line["cells"]) + line["ending"] for line in lines).encode() == raw
    elif tag == "registry":
        assert shown["result"]["registry_marts"] == [{"virtual_schema": "default",
            "mart": "ENSEMBL_MART_ENSEMBL", "display_name": "Ensembl Genes 116", "visible": "1"}]
    else:
        configuration = shown["result"]["configuration"]
        assert configuration["reported_dataset"] == captures.SOURCE_DATASET
        assert configuration["native_dataset_version"] == "assembly-not-release"
        assert configuration["gene_id_filter"]["advertisement"] == "unique"


def test_configuration_model_view_reports_finite_missing_ambiguous_and_header_context_without_full_xml():
    names = [name for name in captures.ATTRIBUTES if name != "mmusculus_homolog_perc_id"]
    names += ["mmusculus_homolog_ensembl_gene", "unrelated_native_attribute"]
    raw = captures.configuration(attributes=names)
    value = captures.result(captures.arguments("configuration"), raw)
    shown = native.ensembl_outcome_view({"result": value})["result"]
    namespace, = shown["configuration"]["native_homology_namespaces"]
    assert namespace["attribute_namespace"] == "mmusculus_homolog_"
    assert namespace["gene_context"]["ambiguous_attributes"] == ["mmusculus_homolog_ensembl_gene"]
    assert namespace["identity_percentages"]["missing_attributes"] == ["mmusculus_homolog_perc_id"]
    assert "unrelated_native_attribute" not in canonical(shown)
    assert value["native_text"].encode() == raw and "unrelated_native_attribute" in value["native_text"]


def test_model_view_keeps_every_scientific_row_duplicate_blank_numeric_token_and_source_target_denominator():
    first = captures.row(); first[10] = "1e-9999"
    blank = [captures.GENE, "13", "1", "10", "-1"] + [""] * 8
    rows = [first, first, captures.row(target="ENSMUSG00000000001"), blank]
    raw = captures.table(*rows).replace(b"\n", b"\r\n")
    value = captures.result(raw=raw)
    shown = native.ensembl_outcome_view({"result": value})["result"]
    assert [line["cells"] for line in shown["native_lines"] if line["role"] == "row"] == rows
    assert shown["columns"][10]["denominator"] == "target_sequence"
    assert shown["columns"][11]["denominator"] == "query_sequence"
    assert shown["retained_row_count"] == 4 and shown["requested_id_count"] == 1
    assert shown["matching_population_count"] is None and shown["native_completion"] == "reported_complete"
    assert "".join("\t".join(line["cells"]) + line["ending"] for line in shown["native_lines"]).encode() == raw


@pytest.mark.parametrize("raw,changes", [(b"Query ERROR: native field not found", {}),
    (b"\xff", {}), (captures.table(captures.row(), stamp=False), {}),
    (captures.table(captures.row()), {"body_complete": False, "body_capture_failure": "provider_response_byte_limit",
        "observed_body_bytes": 65537})])
def test_model_view_preserves_error_incomplete_and_native_completion_as_independent_original_facts(raw, changes):
    value = captures.result(raw=raw, **changes)
    shown = native.ensembl_outcome_view({"result": value})["result"]
    assert shown["response"] == value["response"] and shown["issues"] == value["issues"]
    assert shown["native_response_state"] == value["native_response_state"]
    assert shown["native_completion"] == value["native_completion"]
    assert shown["representation_state"] == value["representation_state"]


@pytest.mark.parametrize("damage", ["version", "operation", "service", "resource", "row", "role", "source", "extra"])
def test_unknown_or_inconsistent_profiles_keep_the_original_unprojected_path(damage):
    value = captures.result()
    if damage in {"version", "operation", "service", "resource"}:
        value[damage] = "unrelated_profile"
    elif damage == "row":
        value["tsv_lines"][1]["cells"][0] = "OTHER"
    elif damage == "role":
        value["tsv_lines"][1]["role"] = "header"
    elif damage == "source":
        value["source_ref"] += "\n"
    else:
        value["unregistered"] = True
    outcome = {"result": value}
    before = deepcopy(outcome)
    assert native.ensembl_outcome_view(outcome) is None and outcome == before


def test_actual_workflow_boundary_keeps_receipt_without_previewing_private_native_data(acquired):
    acquired.http.add(captures.table(captures.row()))
    outcome = execute(acquired)
    row = acquired.store.db.execute("SELECT result FROM tool_operations WHERE id=?", (outcome["operation_ref"],)).fetchone()[0]
    before = canonical(outcome)
    shown = acquired.workflow.local_outcome_preview(outcome, decision_index=4)
    assert shown == outcome and canonical(outcome) == before
    assert set(shown["result"]) == {"acquired", "source_ref", "data_ref", "failure_code"}
    assert acquired.store.db.execute("SELECT result FROM tool_operations WHERE id=?", (outcome["operation_ref"],)).fetchone()[0] == row
    assert shown["record_refs"] == outcome["record_refs"]


def _current_controller(path, initial):
    return FixtureController(str(path), initial, 6)


def _current_session(directory):
    role = dict(model="ensembl-presentation-engineering", reasoning_effort="low")
    return _SessionConnection(dict(connection={"command": ["unselected-model-command"]},
        FAST=role, REASONING=role, routing={}), directory, directory.parent)


class _CurrentProvider(ScriptedProvider):
    """Actual DecisionSource callbacks, using only the pure Session port."""
    def __init__(self, script, session):
        super().__init__(script)
        self.session, self.dispatches = session, []

    async def complete(self, episode_id, role, instructions, context, output_schema):
        wire, model_instructions = self.session._presentation(episode_id, role, instructions, context)
        self.dispatches.append(dict(context=deepcopy(context), instructions=instructions,
            schema=deepcopy(output_schema), wire=wire, model_instructions=model_instructions))
        return await super().complete(episode_id, role, instructions, context, output_schema)


def _current_workflow(store, tools, actor, directory, run_id):
    return Workflow(store, tools, actor, directory, run_id, _current_controller, _credit,
        project_child_credit=_credit, root_role="improvement", episode_record_receipts=True,
        initial_known_record_refs=[])


def _assert_current_controls_private(holder, source):
    owner, root, tools = holder["owner"], holder["root"], holder["tools"]
    context = owner.binding_context(root.source)
    known = set(owner.receipts.known(context.episode_id))
    private = {source["request_ref"], *source.get("auxiliary_artifact_refs", [])}
    assert private.isdisjoint(known)
    resolve = owner.resolver(plain(context.scope), context=context)
    for reference in private:
        assert resolve(reference, "artifact") is False
        assert tools.retained_molecular_reference_access(context, reference, "artifact") is False


def _current_choices(holder, finish, *, prefix_error=AssertionError):
    """Five independently selected requests; no acquisition or row is implied."""
    selected = {}
    def received(context):
        outcome = context["last_local_outcome"]
        confirmed = native.validate_ensembl_receipt(outcome["result"])
        holder.setdefault("observed_receipts", []).append(deepcopy(confirmed))
        if not confirmed["acquired"]:
            raise prefix_error("selected response retained without requested-data confirmation")
        source = holder["store"].get(confirmed["source_ref"])
        assert confirmed["data_ref"] == source["artifact_ref"]
        assert outcome["record_refs"] == [source["id"], source["artifact_ref"]]
        _assert_current_controls_private(holder, source)
        return source["id"]
    def datasets(context):
        return action(native.TOOL, _ensembl_live_arguments("datasets", registry_source_ref=received(context)))
    def source_configuration(context):
        selected["datasets"] = received(context)
        return action(native.TOOL, _ensembl_live_arguments("configuration", dataset=captures.SOURCE_DATASET,
            datasets_source_ref=selected["datasets"]))
    def target_configuration(context):
        selected["source_configuration"] = received(context)
        return action(native.TOOL, _ensembl_live_arguments("configuration", dataset=captures.TARGET_DATASET,
            datasets_source_ref=selected["datasets"]))
    def homologies(context):
        return action(native.TOOL, _ensembl_live_arguments("gene_homologies", source_dataset=captures.SOURCE_DATASET,
            target_dataset=captures.TARGET_DATASET, source_configuration_ref=selected["source_configuration"],
            target_configuration_ref=received(context), source_attribute_style="homologs",
            gene_ids=[captures.GENE, captures.GENE, "UNKNOWN_ID"] if holder.get("engineered") else [captures.GENE],
            include_identity_percentages=True, include_confidence=False))
    def read_selected(context):
        return finish(context, received(context))
    return [action(native.TOOL, _ensembl_live_arguments("registry")), datasets,
        source_configuration, target_configuration, homologies, read_selected]


@pytest.mark.parametrize("empty", [False, True])
def test_current_episode_discovery_receipts_lost_reply_data_admission_session_and_closed_replay(
        tmp_path, http, monkeypatch, empty):
    class LostReply(RuntimeError): pass
    blank = [captures.GENE, "13", "1", "10", "-1"] + [""] * 7
    first = captures.row()[:-1]; first[10] = "1e-9999"
    rows = [] if empty else [first, first, blank]
    raw = captures.table(*rows, confidence=False).replace(b"\n", b"\r\n")
    for body, media in [(captures.REGISTRY_XML, "application/xml"), (captures.DATASETS_TSV, "text/plain"),
            (captures.configuration(), "application/xml"),
            (captures.configuration(captures.TARGET_DATASET), "application/xml"), (raw, "text/plain")]:
        http.add(body, media_type=media)
    with Store(tmp_path / "store") as store:
        target, = store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]
        scope, tools = {"subject_refs": [target]}, ToolRegistry(store, clients=PublicClients(timeout=3))
        original_targets = deepcopy(store.problem()["subject_refs"])
        session = _current_session(tmp_path / "session")
        directory, run_id = tmp_path / "run", "ensembl-current-episode-engineering"
        holder = dict(store=store, tools=tools, engineered=True)
        actual_get = Store.get_artifact
        cached_reads = []
        def finish(context, source_ref):
            assert len(holder["observed_receipts"]) == 5
            # Recovered acquisition was authenticated from controls/Value only;
            # a subsequent explicitly selected Source read is a separate step.
            assert cached_reads
            monkeypatch.setattr(Store, "get_artifact", actual_get)
            source = store.get(source_ref)
            owner, root = holder["owner"], holder["root"]
            binding = owner.binding_context(root.source)
            known = set(owner.receipts.known(binding.episode_id))
            delivered = {reference for result in holder["observed_receipts"]
                for reference in (result["source_ref"], result["data_ref"])}
            assert known == holder["baseline"] | delivered
            admitted, path = owner.services.read_received_molecular_input(binding, source["artifact_ref"],
                "artifact", file_format="text")
            assert admitted["failure"] is None and path.read_bytes() == raw
            return action("source.read", dict(source_ref=source_ref, representation="original", offset=0, limit=len(raw)))
        choices = _current_choices(holder, finish)
        actor = _CurrentProvider(choices[:5], session)
        workflow = _current_workflow(store, tools, actor, directory, run_id)
        goal = "Evaluate the supplied protein with caller-selected homology evidence, without assigning a function."
        root = workflow.build("improvement", "root", goal, scope)
        holder.update(owner=workflow, root=root, baseline=set(workflow.receipts.known(root.source.episode_id)))
        original_execute, lost = ToolRegistry.execute_async, []
        async def lose_reply(registry, name, arguments, **kwargs):
            outcome = await original_execute(registry, name, arguments, **kwargs)
            if name == native.TOOL and arguments["operation"] == "gene_homologies" and not lost:
                assert outcome["status"] == "completed"
                lost.append(deepcopy(outcome)); raise LostReply()
            return outcome
        with monkeypatch.context() as patch:
            patch.setattr(ToolRegistry, "execute_async", lose_reply)
            with pytest.raises(LostReply): asyncio.run(root.run_async(workflow.context))
        assert len(http.requests) == len(actor.dispatches) == 5
        assert store.db.execute("SELECT result FROM runtime_actions WHERE decision_index=4").fetchone()[0] is None
        source_ref = lost[0]["result"]["source_ref"]
        source_record = store.get(source_ref)
        private = json.loads(store.get_artifact(source_record["auxiliary_artifact_refs"][1]))
        view = native.ensembl_result_from_value(private, source_ref=source_ref)
        assert view["native_text"].encode() == raw
        assert [line["cells"] for line in view["tsv_lines"] if line["role"] == "row"] == rows
        assert view["requested_id_count"] == 3 and view["retained_row_count"] == len(rows)
        assert view["matching_population_count"] is None and view["native_completion"] == "reported_complete"
        raw_refs = {source["artifact_ref"] for source in store.list("source") if source["provider"] == "ensembl"}
        def controls_only(current_store, reference):
            assert reference not in raw_refs, "cached acquisition reopened original entity bytes"
            cached_reads.append(reference)
            return actual_get(current_store, reference)
        monkeypatch.setattr(Store, "get_artifact", controls_only)
        monkeypatch.setattr(PublicClients, "_http", forbidden)
        monkeypatch.setattr(host, "prepare_ensembl_request", forbidden)
        monkeypatch.setattr(host, "publish_ensembl_request", forbidden)
        receiver = _CurrentProvider(choices[5:], session)
        recovered = _current_workflow(store, tools, receiver, directory, run_id)
        recovered_root = recovered.build("improvement", "root", goal, scope)
        holder.update(owner=recovered, root=recovered_root)
        record = asyncio.run(recovered_root.run_async(recovered.context))
        final = asyncio.run(recovered_root.build_result(record)).as_record()
        assert len(http.requests) == 5 and store.problem()["subject_refs"] == original_targets
        calls = list(store.db.execute("SELECT request,response FROM runtime_model_calls ORDER BY call_index"))
        dispatches = actor.dispatches + receiver.dispatches
        assert len(calls) == len(dispatches) == 6
        for row, dispatched in zip(calls, dispatches):
            assert json.loads(row["request"])["context"] == dispatched["context"]
            assert json.loads(dispatched["wire"]) == dispatched["context"] and row["response"] is not None
            assert dispatched["model_instructions"] == dispatched["instructions"]
            assert dispatched["context"]["goal"] == root.source.request.goal.as_record()
        assert dispatches[-1]["context"]["last_local_outcome"]["result"] == lost[0]["result"]
        last = json.loads(store.db.execute("SELECT result FROM tool_operations WHERE name='source.read'").fetchone()[0])
        assert last["result"]["text"].encode() == raw
        counts = {name: store.db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in (
            "runtime_episodes", "runtime_actions", "runtime_observations", "runtime_model_calls", "tool_operations")}
        assert counts == dict(runtime_episodes=1, runtime_actions=6, runtime_observations=6,
            runtime_model_calls=6, tool_operations=6)
        assert store.db.execute("SELECT count(*) FROM runtime_forms").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_report_attempts").fetchone()[0] == 0
        before, files, archives = _tables(store), _artifacts(store.path / "artifacts"), _artifacts(directory / "archive")
        monkeypatch.setattr(ToolRegistry, "execute_async", forbidden)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        replay_actor = ScriptedProvider([])
        replay = _current_workflow(store, tools, replay_actor, directory, run_id)
        replay_root = replay.build("improvement", "root", goal, scope)
        replay_record = asyncio.run(replay_root.run_async(replay.context))
        assert asyncio.run(replay_root.build_result(replay_record)).as_record() == final
        assert replay_actor.contexts == [] and _tables(store) == before
        assert _artifacts(store.path / "artifacts") == files and _artifacts(directory / "archive") == archives


def test_real_legacy_registry_publication_and_cache_keep_original_rich_shape_and_single_selection(tmp_path, http, monkeypatch):
    http.add(captures.REGISTRY_XML, media_type="application/xml")
    with Store(tmp_path / "store") as store:
        scope = {"subject_refs": store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]}
        tools = ToolRegistry(store, clients=PublicClients(timeout=3))
        selected = captures.arguments("registry")
        snapshot = tools.clients.ensembl_request(arguments=selected)
        prepared = host.prepare_ensembl_request(tools, selected)
        token = tools._publications.set([])
        try:
            with store.transaction():
                witness = store.artifact(canonical(prepared["selection"]), "application/json")
                source_record = tools._source("ensembl", None, snapshot=snapshot, accession=None,
                    parent_source_refs=[], auxiliary_artifact_refs=[witness])
                rich = native.ensembl_result(snapshot, arguments=selected, source_ref=source_record["id"],
                    artifact_ref=source_record["artifact_ref"], evidence={})
                from gene_annotation_episode.domain import identity
                key = "engineered-original-ensembl-registry"
                outcome = dict(status="completed", operation_ref=identity("operation", dict(key=key,
                    name=native.TOOL, arguments=selected)), record_refs=[source_record["id"]],
                    changed_record_refs=[source_record["id"]], result=rich, feedback=None)
                tools._save(key, native.TOOL, selected, scope, outcome)
        finally: tools._publications.reset(token)
        before, files = _tables(store), _artifacts(store.path / "artifacts")
        actual_get = Store.get_artifact
        def controls_only(current_store, reference):
            assert reference != source_record["artifact_ref"]
            return actual_get(current_store, reference)
        monkeypatch.setattr(Store, "get_artifact", controls_only)
        monkeypatch.setattr(PublicClients, "_http", forbidden)
        monkeypatch.setattr(host, "prepare_ensembl_request", forbidden)
        monkeypatch.setattr(host, "publish_ensembl_request", forbidden)
        assert asyncio.run(tools.execute_async(native.TOOL, selected, scope=scope, operation_key=key)) == outcome
        assert _tables(store) == before and _artifacts(store.path / "artifacts") == files


ENSEMBL_LIVE_QUESTION = (
    "For the caller-selected Ensembl gene stable ID ENSG00000139618, what mouse homologue gene IDs, "
    "native homology types, source and target chromosome names and one-based inclusive gene intervals, "
    "source strand, and separate query/target percentage identities does the explicitly selected Ensembl "
    "116 BioMart resource return when querying hsapiens_gene_ensembl against mmusculus_gene_ensembl? "
    "Preserve every returned row, duplicate and blank target; do not assume a unique or one-to-one conversion.")
ENSEMBL_LIVE_RUN = "ensembl-selected-published-live"
ENSEMBL_LIVE_FORM = {"type": "object", "properties": {"homology_source_refs": {
    "type": "array", "items": {"type": "string", "format": "reference", "x-reference-namespace": "source"},
    "x-source": "last_outcome_refs"}}, "required": ["homology_source_refs"], "additionalProperties": False}
ENSEMBL_LIVE_PURPOSE = (
    "Return only the final homology response Source identity. Native rows remain retained in that Source; "
    "no copied homology row facts are requested.")


def _ensembl_live_arguments(operation, **operands):
    common = {"operation": operation, "resource": native.RESOURCE, "max_bytes": native.MAX_RESPONSE_BYTES}
    if operation != "registry":
        common.update(virtual_schema="default", mart="ENSEMBL_MART_ENSEMBL")
    return {**common, **operands}


def _ensembl_live_json(value):
    """Represent literal request bytes in proof JSON without changing I/O."""
    if type(value) is bytes:
        return {"base64": base64.b64encode(value).decode("ascii"),
            "sha256": hashlib.sha256(value).hexdigest(), "size_bytes": len(value)}
    if type(value) is dict:
        return {key: _ensembl_live_json(child) for key, child in value.items()}
    if type(value) in (list, tuple):
        return [_ensembl_live_json(child) for child in value]
    return value


def _ensembl_live_prefix(store, client, actor):
    from test_molecular_provider_acquisition_live import _counts
    operations = []
    for row in store.db.execute("SELECT * FROM tool_operations ORDER BY operation_key"):
        outcome = json.loads(row["result"])
        value = outcome.get("result")
        operations.append({"operation_key": row["operation_key"], "operation_ref": row["id"],
            "name": row["name"], "arguments": json.loads(row["arguments"]),
            "status": outcome["status"], "record_refs": outcome["record_refs"], "feedback": outcome.get("feedback"),
            "response": value.get("response") if type(value) is dict else None,
            "issues": value.get("issues") if type(value) is dict else None,
            "saved_outcome_sha256": hashlib.sha256(row["result"].encode()).hexdigest()})
    return {"question": ENSEMBL_LIVE_QUESTION,
        "scope": "Live bounded BioMart HTTP, actual published A101/P01 Workflow; scripted decisions and controlled text transport; no biological inference or live-model reasoning claim.",
        "return_scope": "Only the final Source ID through last_outcome_refs; rich native rows are audited outside the model loop.",
        "client_calls": _ensembl_live_json(client.calls), "captures": deepcopy(client.persisted_captures),
        "transport_failures": deepcopy(client.transport_failures), "operations": operations,
        "counts": _counts(store), "scripted_decision_calls": len(actor.calls), "external_model_calls": 0,
        "parent_return_verified": False, "native_homology_response_verified": False,
        "closed_root_replay_reached": False, "separate_retained_replay_required": True}


def _current_live_ensembl(tmp_path, monkeypatch, *, attempt_id):
    """Opt-in selected HTTP in one existing-purpose episode, not a getter child."""
    from test_molecular_provider_acquisition_live import OriginalLivePrefixObserved, RecordingLiveClients
    client = RecordingLiveClients(tmp_path / "provider-access")
    monkeypatch.setattr(client, "_skill", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    report = dict(version="ensembl_current_acquisition_live_v1", attempt_id=attempt_id,
        question=ENSEMBL_LIVE_QUESTION, current_episode_only=True, acquisition_verified=False,
        data_admitted=False, current_receiving_builder_verified=False, closed_replay_verified=False,
        scope="five caller-selected BioMart responses and one later selected Source read; no analysis or child")
    proof = tmp_path / "ENSEMBL_ACQUISITION_CURRENT.json"
    with Store(tmp_path / "store") as store:
        scope = {"subject_refs": store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]}
        tools = ToolRegistry(store, clients=client)
        session = _current_session(tmp_path / "session")
        holder = dict(store=store, tools=tools)
        def finish(context, source_ref):
            source = store.get(source_ref)
            owner, root = holder["owner"], holder["root"]
            binding = owner.binding_context(root.source)
            admitted, path = owner.services.read_received_molecular_input(binding,
                source["artifact_ref"], "artifact", file_format="text")
            assert admitted["failure"] is None
            raw = path.read_bytes()
            private = json.loads(store.get_artifact(source["auxiliary_artifact_refs"][1]))
            view = native.ensembl_result_from_value(private, source_ref=source_ref)
            assert view["native_text"].encode() == raw and view["native_completion"] == "reported_complete"
            assert view["requested"]["source_dataset"] == captures.SOURCE_DATASET
            assert view["requested"]["target_dataset"] == captures.TARGET_DATASET
            assert view["requested"]["gene_ids"] == [captures.GENE]
            assert view["matching_population_count"] is None
            report.update(acquisition_verified=True, data_admitted=True, source_ref=source_ref,
                raw_sha256=hashlib.sha256(raw).hexdigest(), raw_size_bytes=len(raw),
                native_response=view["response"], native_completion=view["native_completion"],
                requested_id_count=view["requested_id_count"], retained_row_count=view["retained_row_count"],
                matching_population_count=None, selected_native_rows=[line for line in view["tsv_lines"]
                    if line["role"] == "row"])
            monkeypatch.setattr(PublicClients, "_http", forbidden)
            monkeypatch.setattr(host, "publish_ensembl_request", forbidden)
            return action("source.read", dict(source_ref=source_ref, representation="original", offset=0, limit=len(raw)))
        actor = _CurrentProvider(_current_choices(holder, finish, prefix_error=OriginalLivePrefixObserved), session)
        directory, run_id = tmp_path / "run", "current-ensembl-selected-" + attempt_id
        current = _current_workflow(store, tools, actor, directory, run_id)
        root = current.build("improvement", "root", ENSEMBL_LIVE_QUESTION, scope)
        holder.update(owner=current, root=root)
        stopped, record = False, None
        try:
            record = asyncio.run(root.run_async(current.context))
        except OriginalLivePrefixObserved as error:
            stopped = True
            report["prefix_reason"] = str(error)
        except BaseException as error:
            report["failure"] = dict(type=type(error).__name__, message=str(error))
            raise
        finally:
            report.update(prefix_stopped=stopped, client_calls=_ensembl_live_json(client.calls),
                public_receipts=holder.get("observed_receipts", []),
                counts={name: store.db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in (
                    "runtime_episodes", "runtime_actions", "runtime_observations", "runtime_model_calls", "tool_operations")})
            proof.write_text(json.dumps(report, indent=2, allow_nan=False))
        assert len(client.calls) <= 5
        assert store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM runtime_forms").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_report_attempts").fetchone()[0] == 0
        if stopped:
            assert record is None
            pytest.skip("selected BioMart prefix retained; unavailable requested data is not confirmed")
        assert len(client.calls) == 5 and report["acquisition_verified"] and report["data_admitted"]
        final = asyncio.run(root.build_result(record)).as_record()
        calls = list(store.db.execute("SELECT request,response FROM runtime_model_calls ORDER BY call_index"))
        assert len(calls) == len(actor.dispatches) == 6
        for row, dispatched in zip(calls, actor.dispatches):
            assert json.loads(row["request"])["context"] == dispatched["context"]
            assert json.loads(dispatched["wire"]) == dispatched["context"] and row["response"] is not None
        report["current_receiving_builder_verified"] = True
        before, files, archives = _tables(store), _artifacts(store.path / "artifacts"), _artifacts(directory / "archive")
        monkeypatch.setattr(PublicClients, "_http", forbidden)
        monkeypatch.setattr(ToolRegistry, "execute_async", forbidden)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        replay_actor = ScriptedProvider([])
        replay = _current_workflow(store, tools, replay_actor, directory, run_id)
        replay_root = replay.build("improvement", "root", ENSEMBL_LIVE_QUESTION, scope)
        replay_record = asyncio.run(replay_root.run_async(replay.context))
        assert asyncio.run(replay_root.build_result(replay_record)).as_record() == final
        assert replay_actor.contexts == [] and _tables(store) == before
        assert _artifacts(store.path / "artifacts") == files and _artifacts(directory / "archive") == archives
        report.update(closed_replay_verified=True, final_result=final)
        proof.write_text(json.dumps(report, indent=2, allow_nan=False))


@pytest.mark.skipif(os.environ.get("HMMER_NATIVE_ORACLE_ENSEMBL_LIVE") != "1"
    or "HMMER529_ATTEMPT" not in os.environ, reason="explicit bounded original BioMart request set only")
def test_opt_in_current_episode_ensembl_homology_receipt_and_data_refs(tmp_path, monkeypatch):
    _current_live_ensembl(tmp_path, monkeypatch, attempt_id="original-current-episode")


@pytest.mark.skipif(not os.environ.get("HMMER_NATIVE_ORACLE_ENSEMBL_RETAINED"),
    reason="explicit immutable original BioMart case and SQLite SHA256 required")
def test_retained_live_ensembl_published_source_and_cached_root_replay(tmp_path, monkeypatch):
    from gene_annotation_episode.acquisition import SourceSnapshot
    from gene_annotation_episode.domain import identity
    from test_molecular_provider_acquisition_host import _artifacts, _tables
    from test_molecular_provider_acquisition_live import (
        _counts, _retained_live_artifact, _retained_live_inventory, _retained_live_rows,
    )
    from test_published_axis_workflow import ScriptedDecisions
    from test_runtime import FixtureController

    original = Path(os.environ["HMMER_NATIVE_ORACLE_ENSEMBL_RETAINED"]).resolve()
    expected_sha = os.environ.get("HMMER_NATIVE_ORACLE_ENSEMBL_RETAINED_DB_SHA256")
    assert type(expected_sha) is str and len(expected_sha) == 64 and set(expected_sha) <= set("0123456789abcdef")
    assert original.is_dir() and not original.is_symlink()
    assert not list(original.rglob("*-wal")) and not list(original.rglob("*-shm"))
    inventory = _retained_live_inventory(original)
    assert inventory["store/state.sqlite3"]["sha256"] == expected_sha
    proof = tmp_path / "ENSEMBL_ACQUISITION_RETAINED.json"
    report = {"question": ENSEMBL_LIVE_QUESTION, "original_database_sha256": expected_sha,
        "original_verified": False, "cached_root_replay_reached": False,
        "new_HTTP_requests": 0, "new_native_jobs": 0, "new_model_calls": 0}
    proof.write_text(json.dumps(report, indent=2, allow_nan=False))
    connection = sqlite3.connect((original / "store/state.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = _retained_live_rows(connection)
        live = json.loads((original / "ENSEMBL_ACQUISITION_LIVE.json").read_bytes())
        assert live["question"] == ENSEMBL_LIVE_QUESTION
        assert live["parent_return_verified"] is live["native_homology_response_verified"] is True
        assert live["closed_root_replay_reached"] is False
        operations = list(connection.execute("SELECT * FROM tool_operations ORDER BY operation_key"))
        evidence, outcomes, sources, entries = {}, [], [], {}
        for row in operations:
            selected, outcome = json.loads(row["arguments"]), json.loads(row["result"])
            assert row["name"] == native.TOOL and outcome["status"] == "completed"
            value = outcome["result"]
            saved = json.loads(connection.execute("SELECT data FROM records WHERE id=?", (value["source_ref"],)).fetchone()[0])
            raw = _retained_live_artifact(connection, original / "store", saved["artifact_ref"])
            control_raw = _retained_live_artifact(connection, original / "store", saved["request_ref"])
            control = json.loads(control_raw)
            assert control_raw == canonical(control).encode()
            assert outcome["record_refs"] == [saved["id"]]
            assert row["id"] == identity("operation", {"key": row["operation_key"], "name": native.TOOL, "arguments": selected})
            assert saved["id"] == identity("source", {"origin": saved["origin"], "record": {
                key: child for key, child in saved.items() if key not in {"id", "record_type", "origin"}}})
            witness_raw = _retained_live_artifact(connection, original / "store", saved["auxiliary_artifact_refs"][0])
            witness = {"version": host.SELECTION_VERSION, "arguments": selected,
                "direct_source_refs": native.ensembl_discovery_refs(selected),
                "sources": [entries[item["source_ref"]] for item in value["discovery_evidence"]]}
            assert witness_raw == canonical(witness).encode()
            snapshot = SourceSnapshot("ensembl", saved["uri"], control["request"], saved["retrieved_at"], raw,
                value["response"]["media_type"], control["transport"])
            assert canonical(native.ensembl_result(snapshot, arguments=selected, source_ref=saved["id"],
                artifact_ref=saved["artifact_ref"], evidence=evidence)) == canonical(value)
            assert selected == live["actual_selected_arguments"][len(outcomes)]
            assert saved["parent_source_refs"] == native.ensembl_discovery_refs(selected)
            assert saved["version"] is saved["accession"] is None and saved["origin"] == "external"
            assert row["result"] == canonical(outcome)
            assert hashlib.sha256(row["result"].encode()).hexdigest() == live["operations"][len(outcomes)]["saved_outcome_sha256"]
            evidence[saved["id"]] = {"snapshot": snapshot, "artifact_ref": saved["artifact_ref"]}
            entries[saved["id"]] = {"source_ref": saved["id"],
                "source_record_sha256": hashlib.sha256(canonical(saved).encode()).hexdigest(),
                "raw_artifact_ref": saved["artifact_ref"], "request_ref": saved["request_ref"],
                "operation_key": row["operation_key"], "operation_ref": row["id"],
                "operation_result_sha256": hashlib.sha256(row["result"].encode()).hexdigest()}
            sources.append(saved); outcomes.append(outcome)
        assert len(operations) == len(live["client_calls"]) == len(live["captures"]) == 5
        assert outcomes[-1]["result"] == live["actual_homology_result"]
        for capture, call, outcome in zip(live["captures"], live["client_calls"], outcomes):
            raw = (original / capture["file"]).read_bytes()
            assert len(raw) == capture["retained_bytes"] and hashlib.sha256(raw).hexdigest() == capture["raw_sha256"]
            assert capture["raw_sha256"] == outcome["result"]["raw_artifact_ref"][len("artifact_"):]
            spec = native.ensembl_request_spec(outcome["result"]["requested"])
            assert call == _ensembl_live_json({"service": "ensembl", "url": native.URL, "params": spec["params"],
                "media_type": spec["media_type"], "body": spec["body"], "content_type": spec["content_type"],
                "max_bytes": native.MAX_RESPONSE_BYTES, "timeout_seconds": 30, "follow_redirects": False})
        episodes = list(connection.execute("SELECT * FROM runtime_episodes"))
        assert len(episodes) == 2 and all(row["state"] == "yielded" and row["archive"] is not None for row in episodes)
        parent = next(row for row in episodes if len(json.loads(row["path"])) == 1)
        child = next(row for row in episodes if len(json.loads(row["path"])) == 2)
        parent_request, child_request = json.loads(parent["request"]), json.loads(child["request"])
        assert child_request["goal"]["objective"] == ENSEMBL_LIVE_QUESTION
        assert child_request["message"]["episode_assignment"]["selection"]["evidence_axis"]["option_id"] == "A101"
        assert child_request["message"]["episode_assignment"]["selection"]["thought_pattern"]["option_id"] == "P01"
        assert child_request["report_contract"]["measurements"]["schema"] == ENSEMBL_LIVE_FORM
        original_call, = connection.execute("SELECT request FROM runtime_model_calls WHERE episode_id=?", (parent["episode_id"],))
        original_context = json.loads(original_call["request"])["context"]
        actions = list(connection.execute("SELECT * FROM runtime_actions WHERE episode_id=? ORDER BY decision_index", (child["episode_id"],)))
        assert len(actions) == 5
        for index, (action, operation, outcome) in enumerate(zip(actions, operations, outcomes)):
            assert json.loads(action["action"]) == {"kind": "tool", "tool": native.TOOL,
                "arguments": json.loads(operation["arguments"])}
            actual = json.loads(action["result"])
            assert actual.pop("pending_work_after_action")["items"] == [] and canonical(actual) == canonical(outcome)
            assert operation["operation_key"] == parent["run_id"] + ":" + child["episode_id"] + ":" + str(index)
            assert operation["scope"] == canonical(child_request["message"]["scope"])
        exchanges = list(connection.execute("SELECT request FROM runtime_decision_exchanges WHERE episode_id=? ORDER BY decision_index,exchange_index",
            (child["episode_id"],)))
        assert len(exchanges) == len(live["published_turn_texts"]) == 5
        for index, (exchange, text) in enumerate(zip(exchanges, live["published_turn_texts"]), 1):
            wire = json.loads((original / "model-wire" / ("call-" + str(index).zfill(5)) / "request.json").read_bytes())
            original_exchange = json.loads(exchange["request"])
            assert wire["context"] == original_exchange["context"] and wire["output_schema"] == original_exchange["output_schema"]
            assert wire["instructions"] == original_exchange["instructions"] and wire["input"][0]["text"] == text
            assert ENSEMBL_LIVE_QUESTION in text and "xml_document" not in text and "native_text |" not in text
        form, = connection.execute("SELECT * FROM runtime_forms")
        attempt, = connection.execute("SELECT * FROM runtime_report_attempts")
        assert json.loads(form["form"]) == json.loads(attempt["form"]) == live["parent_form"] == {
            "homology_source_refs": [sources[-1]["id"]]}
        assert attempt["failure"] is None and attempt["parent_episode_id"] == parent["episode_id"]
        receipt, = connection.execute("SELECT receipt_kind,source_index FROM runtime_record_receipts WHERE episode_id=? AND record_ref=?",
            (parent["episode_id"], sources[-1]["id"]))
        assert receipt["receipt_kind"] == "child_form" and receipt["source_index"] == 0
        parent_receipts = {row[0] for row in connection.execute(
            "SELECT record_ref FROM runtime_record_receipts WHERE episode_id=?", (parent["episode_id"],))}
        assert sources[-1]["id"] in parent_receipts and not {item["id"] for item in sources[:-1]}.intersection(parent_receipts)
        assert not {reference for item in sources for reference in
            (item["artifact_ref"], item["request_ref"], *item["auxiliary_artifact_refs"])}.intersection(parent_receipts)
        report.update(original_verified=True, original_parent_form=live["parent_form"],
            original_counts=live["counts"], homology_source_ref=sources[-1]["id"])
        proof.write_text(json.dumps(report, indent=2, allow_nan=False))
    finally:
        connection.close()
        assert _retained_live_inventory(original) == inventory
    owned = tmp_path / "owned-retained-ensembl"
    shutil.copytree(original, owned)
    for path in [owned, *owned.rglob("*")]:
        path.chmod(0o755 if path.is_dir() else 0o644)
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    monkeypatch.setattr(PublicClients, "_skill", forbidden)
    monkeypatch.setattr(ToolRegistry, "execute_async", forbidden)
    monkeypatch.setattr(host, "prepare_ensembl_request", forbidden)
    monkeypatch.setattr(host, "publish_ensembl_request", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    try:
        with Store(owned / "store") as store:
            assert _tables(store) == rows
            before, artifacts = _tables(store), _artifacts(store.path / "artifacts")
            run_files = _retained_live_inventory(owned / "run")
            actor = ScriptedDecisions([])
            monkeypatch.setattr(actor, "complete", forbidden)
            tools = ToolRegistry(store)
            descriptor = child_request["message"]["scientific_process"]["mechanics_binding"]
            workflow = Workflow(store, tools, actor, owned / "run", parent["run_id"],
                lambda path, initial: FixtureController(str(path), initial, 1 if len(path) == 1 else 5), _credit,
                project_child_credit=_credit, episode_binding_descriptors=[descriptor], episode_record_receipts=True,
                initial_known_record_refs=[], decision_protocol="decision_exchange_v1",
                credit_binding=original_context["credit_binding"],
                child_credit_binding=original_context["scientific_child_credit_binding"],
                controller_binding=original_context["controller_binding"])
            role, key = json.loads(parent["path"])[0]
            root = workflow.build(role, key, parent_request["goal"]["objective"], parent_request["message"]["scope"])
            record = asyncio.run(root.run_async(workflow.context))
            assert workflow.archive.store(record).descriptor() == json.loads(parent["archive"])
            final = asyncio.run(root.build_result(record)).as_record()
            assert final == live["final_root_result"] and actor.calls == []
            assert _counts(store) == live["counts"] and _tables(store) == before
            assert _artifacts(store.path / "artifacts") == artifacts and _retained_live_inventory(owned / "run") == run_files
            report.update(cached_root_replay_reached=True, cached_root_result=final,
                tables_artifacts_and_run_files_unchanged=True)
    except Exception as error:
        report["replay_failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        assert _retained_live_inventory(original) == inventory
        report["original_files_unchanged"] = True
        proof.write_text(json.dumps(report, indent=2, allow_nan=False))


def _ensembl_selected_attempt_id(value):
    import re
    assert type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value), "explicit unique BioMart attempt ID required"
    return value


def _ensembl_attempt_native_evidence(connection, directory, report):
    """Audit actual five-request evidence independently of late delivery flags."""
    from gene_annotation_episode.acquisition import SourceSnapshot
    from gene_annotation_episode.domain import identity
    from test_molecular_provider_acquisition_live import _retained_live_artifact
    rows = list(connection.execute("SELECT * FROM tool_operations ORDER BY operation_key"))
    assert len(rows) == len(report["client_calls"]) == len(report["captures"]) == 5
    evidence, entries, values, sources, arguments = {}, {}, [], [], []
    for index, row in enumerate(rows):
        selected, outcome = json.loads(row["arguments"]), json.loads(row["result"])
        assert row["name"] == native.TOOL and outcome["status"] == "completed"
        assert row["arguments"] == canonical(selected) and row["result"] == canonical(outcome)
        assert row["id"] == identity("operation", {"key": row["operation_key"], "name": native.TOOL, "arguments": selected})
        value = outcome["result"]
        saved = json.loads(connection.execute("SELECT data FROM records WHERE id=?", (value["source_ref"],)).fetchone()[0])
        assert saved["id"] == identity("source", {"origin": "external", "record": {
            key: child for key, child in saved.items() if key not in {"id", "record_type", "origin"}}})
        assert saved["record_type"] == "source" and saved["origin"] == "external" and saved["provider"] == "ensembl"
        assert saved["version"] is saved["accession"] is None
        assert outcome["record_refs"] == [saved["id"]]
        assert saved["parent_source_refs"] == native.ensembl_discovery_refs(selected)
        raw = _retained_live_artifact(connection, directory / "store", saved["artifact_ref"])
        control_raw = _retained_live_artifact(connection, directory / "store", saved["request_ref"])
        control = json.loads(control_raw)
        assert control_raw == canonical(control).encode() and control["request"] == selected
        witness = {"version": host.SELECTION_VERSION, "arguments": selected,
            "direct_source_refs": native.ensembl_discovery_refs(selected),
            "sources": [entries[item["source_ref"]] for item in value["discovery_evidence"]]}
        assert len(saved["auxiliary_artifact_refs"]) == 1
        assert _retained_live_artifact(connection, directory / "store", saved["auxiliary_artifact_refs"][0]) == canonical(witness).encode()
        snapshot = SourceSnapshot("ensembl", saved["uri"], selected, saved["retrieved_at"], raw,
            value["response"]["media_type"], control["transport"])
        assert canonical(native.ensembl_result(snapshot, arguments=selected, source_ref=saved["id"],
            artifact_ref=saved["artifact_ref"], evidence=evidence)) == canonical(value)
        assert value["response"]["http_status"] == 200 and value["response"]["body_complete"] is True
        assert value["issues"] == []
        capture, call = report["captures"][index], report["client_calls"][index]
        capture_path = directory / capture["file"]
        assert capture_path.parent == directory / "http-captures" and not capture_path.is_symlink()
        assert capture_path.read_bytes() == raw
        assert capture["raw_sha256"] == snapshot.sha256 and capture["retained_bytes"] == len(raw)
        assert capture["transport"] == _ensembl_live_json(control["transport"])
        spec = native.ensembl_request_spec(selected)
        assert call == _ensembl_live_json({"service": "ensembl", "url": native.URL, "params": spec["params"],
            "media_type": spec["media_type"], "body": spec["body"], "content_type": spec["content_type"],
            "max_bytes": native.MAX_RESPONSE_BYTES, "timeout_seconds": 30, "follow_redirects": False})
        action = connection.execute("SELECT * FROM runtime_actions WHERE ?=run_id||':'||episode_id||':'||decision_index",
            (row["operation_key"],)).fetchone()
        assert action is not None and action["decision_index"] == index
        assert json.loads(action["action"]) == {"kind": "tool", "tool": native.TOOL, "arguments": selected}
        assert action["run_id"] == report["run_id"]
        episode = connection.execute("SELECT request FROM runtime_episodes WHERE episode_id=? AND run_id=?",
            (action["episode_id"], action["run_id"])).fetchone()
        assert episode is not None and row["scope"] == canonical(json.loads(episode["request"])["message"]["scope"])
        if action["result"] is not None:
            actual = json.loads(action["result"])
            if "pending_work_after_action" in actual:
                from gene_annotation_episode.waiting import validate_pending
                validate_pending(actual.pop("pending_work_after_action"))
            assert canonical(actual) == canonical(outcome)
        evidence[saved["id"]] = {"snapshot": snapshot, "artifact_ref": saved["artifact_ref"]}
        entries[saved["id"]] = {"source_ref": saved["id"],
            "source_record_sha256": hashlib.sha256(canonical(saved).encode()).hexdigest(),
            "raw_artifact_ref": saved["artifact_ref"], "request_ref": saved["request_ref"],
            "operation_key": row["operation_key"], "operation_ref": row["id"],
            "operation_result_sha256": hashlib.sha256(row["result"].encode()).hexdigest()}
        values.append(value); sources.append(saved); arguments.append(selected)
    assert [item["operation"] for item in arguments] == ["registry", "datasets", "configuration", "configuration", "gene_homologies"]
    selected = arguments[-1]
    assert selected["resource"] == native.RESOURCE and native.URL == "https://jun2026.archive.ensembl.org/biomart/martservice"
    assert selected["source_dataset"] == captures.SOURCE_DATASET == "hsapiens_gene_ensembl"
    assert selected["target_dataset"] == captures.TARGET_DATASET == "mmusculus_gene_ensembl"
    assert selected["gene_ids"] == [captures.GENE] == ["ENSG00000139618"]
    assert selected["source_attribute_style"] == "homologs"
    assert selected["include_identity_percentages"] is True and selected["include_confidence"] is False
    return values, sources, arguments


def _ensembl_attempt_parent_delivery(store, workflow, sources):
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    form, = store.db.execute("SELECT * FROM runtime_forms")
    attempt, = store.db.execute("SELECT * FROM runtime_report_attempts")
    expected = {"homology_source_refs": [sources[-1]["id"]]}
    assert json.loads(form["form"]) == json.loads(attempt["form"]) == expected
    assert attempt["failure"] is None and form["episode_id"] == attempt["child_episode_id"]
    facts = json.loads(form["facts"])
    assert facts["last_outcome_refs"] == [sources[-1]["id"]]
    assert facts["committed_record_refs"] == [item["id"] for item in sources]
    contexts = EpisodeReturnRecords(store, workflow.run_id, failure_prefix="ensembl_attempt_")
    parent = contexts.context(attempt["parent_episode_id"])
    known = set(workflow.receipts.known(parent.episode_id))
    assert sources[-1]["id"] in known and not {item["id"] for item in sources[:-1]}.intersection(known)
    private = {reference for item in sources for reference in
        (item["artifact_ref"], item["request_ref"], *item["auxiliary_artifact_refs"])}
    assert not private.intersection(known)
    assert workflow.services.reference_in_context(parent, sources[-1]["id"], "source") is True
    assert all(workflow.services.reference_in_context(parent, reference, "artifact") is False for reference in private)
    receipt, = store.db.execute("SELECT receipt_kind,source_index FROM runtime_record_receipts WHERE episode_id=? AND record_ref=?",
        (parent.episode_id, sources[-1]["id"]))
    assert receipt["receipt_kind"] == "child_form" and receipt["source_index"] == 0
    return expected


@pytest.mark.skipif(not os.environ.get("HMMER_NATIVE_ORACLE_ENSEMBL_LIVE_ATTEMPT_ID")
    or "HMMER529_ATTEMPT" not in os.environ
    or bool(os.environ.get("HMMER_NATIVE_ORACLE_ENSEMBL_LIVE_ATTEMPT_RETAINED")),
    reason="separately selected fresh BioMart attempt ID required; retained mode forbids live acquisition")
def test_opt_in_fresh_ensembl116_current_episode_homology_receipt_and_data_refs(tmp_path, monkeypatch):
    attempt_id = _ensembl_selected_attempt_id(os.environ["HMMER_NATIVE_ORACLE_ENSEMBL_LIVE_ATTEMPT_ID"])
    _current_live_ensembl(tmp_path, monkeypatch, attempt_id=attempt_id)


@pytest.mark.skipif(not os.environ.get("HMMER_NATIVE_ORACLE_ENSEMBL_LIVE_ATTEMPT_RETAINED"),
    reason="explicit immutable fresh-attempt case, attempt ID and database SHA256 required")
def test_retained_fresh_ensembl116_native_work_and_owned_parent_delivery(tmp_path, monkeypatch):
    from test_molecular_provider_acquisition_live import _retained_live_inventory, _retained_live_rows
    from test_published_axis_workflow import ScriptedDecisions
    from test_runtime import FixtureController
    selected_original = Path(os.environ["HMMER_NATIVE_ORACLE_ENSEMBL_LIVE_ATTEMPT_RETAINED"])
    assert not selected_original.is_symlink()
    original = selected_original.resolve()
    expected_sha = os.environ.get("HMMER_NATIVE_ORACLE_ENSEMBL_LIVE_ATTEMPT_RETAINED_DB_SHA256")
    attempt_id = _ensembl_selected_attempt_id(os.environ.get("HMMER_NATIVE_ORACLE_ENSEMBL_LIVE_ATTEMPT_RETAINED_ID"))
    assert type(expected_sha) is str and len(expected_sha) == 64 and set(expected_sha) <= set("0123456789abcdef")
    assert original.is_dir() and not original.is_symlink()
    assert not list(original.rglob("*-wal")) and not list(original.rglob("*-shm"))
    inventory = _retained_live_inventory(original)
    assert inventory["store/state.sqlite3"]["sha256"] == expected_sha
    report = {"attempt_id": attempt_id, "original_database_sha256": expected_sha,
        "question": ENSEMBL_LIVE_QUESTION, "native_evidence_verified": False, "parent_return_verified": False,
        "new_HTTP_requests": 0, "new_native_jobs": 0, "new_model_calls": 0, "forbidden_attempts": {}}
    proof = tmp_path / "ENSEMBL_ATTEMPT_RETAINED.json"
    live = json.loads((original / "ENSEMBL_ACQUISITION_LIVE_ATTEMPT.json").read_bytes())
    assert live["attempt_id"] == attempt_id and live["question"] == ENSEMBL_LIVE_QUESTION
    assert live["run_id"] == "ensembl-selected-published-live-attempt-" + attempt_id
    connection = sqlite3.connect((original / "store/state.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        before_original = _retained_live_rows(connection)
        values, sources, arguments = _ensembl_attempt_native_evidence(connection, original, live)
        episodes = list(connection.execute("SELECT * FROM runtime_episodes"))
        assert len(episodes) == 2
        parent = next(row for row in episodes if len(json.loads(row["path"])) == 1)
        child = next(row for row in episodes if len(json.loads(row["path"])) == 2)
        parent_request, child_request = json.loads(parent["request"]), json.loads(child["request"])
        assignment = child_request["message"]["episode_assignment"]
        assert child_request["goal"]["objective"] == parent_request["goal"]["objective"] == ENSEMBL_LIVE_QUESTION
        assert assignment["context"]["verification_attempt_id"] == attempt_id
        assert assignment["selection"]["evidence_axis"]["option_id"] == "A101"
        assert assignment["selection"]["thought_pattern"]["option_id"] == "P01"
        assert assignment["constraints"]["maximum_selected_requests"] == 5
        assert assignment["constraints"]["no_redirects_retries_or_substitutions"] is True
        assert assignment["constraints"]["literal_operations"] == [item["operation"] for item in arguments]
        assert assignment["constraints"]["max_bytes_per_response"] == native.MAX_RESPONSE_BYTES
        assert child_request["report_contract"]["measurements"]["schema"] == ENSEMBL_LIVE_FORM
        root_call, = connection.execute("SELECT request FROM runtime_model_calls WHERE episode_id=?", (parent["episode_id"],))
        original_context = json.loads(root_call["request"])["context"]
        report.update(native_evidence_verified=True, original_counts=live["counts"],
            original_parent_state=parent["state"], original_child_state=child["state"],
            actual_selected_arguments=arguments, homology_source_ref=sources[-1]["id"])
    finally:
        connection.close()
        assert _retained_live_inventory(original) == inventory
        proof.write_text(json.dumps(report, indent=2, allow_nan=False))
    owned = tmp_path / "owned-retained-ensembl-attempt"
    shutil.copytree(original, owned)
    for path in [owned, *owned.rglob("*")]:
        path.chmod(0o755 if path.is_dir() else 0o644)
    def deny(kind):
        def rejected(*args, **kwargs):
            report["forbidden_attempts"][kind] = report["forbidden_attempts"].get(kind, 0) + 1
            raise AssertionError("retained Ensembl recovery attempted new " + kind)
        return rejected
    monkeypatch.setattr(PublicClients, "_http", deny("HTTP"))
    monkeypatch.setattr(PublicClients, "_skill", deny("skill"))
    monkeypatch.setattr(host, "prepare_ensembl_request", deny("new_request_preparation"))
    monkeypatch.setattr(host, "publish_ensembl_request", deny("new_response_publication"))
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", deny("native_job"))
    monkeypatch.setattr("gene_annotation_episode.providers._SessionConnection._rpc", deny("model_RPC"))
    try:
        with Store(owned / "store") as store:
            try:
                assert _retained_live_rows(store.db) == before_original
                original_operations = [tuple(row) for row in store.db.execute("SELECT * FROM tool_operations ORDER BY operation_key")]
                original_model_calls = [tuple(row) for row in store.db.execute("SELECT * FROM runtime_model_calls ORDER BY episode_id,call_index")]
                closed = all(row["state"] == "yielded" and row["archive"] is not None for row in episodes)
                original_artifacts = _retained_live_inventory(owned / "store" / "artifacts")
                original_run_files = _retained_live_inventory(owned / "run")
                actor = ScriptedDecisions([])
                monkeypatch.setattr(actor, "complete", deny("model_decision"))
                tools = ToolRegistry(store)
                execute = tools.execute_async
                async def saved_only(name, args, *, scope=None, operation_key=None, **kwargs):
                    saved = store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (operation_key,)).fetchone()
                    assert saved is not None and saved["name"] == name == native.TOOL
                    assert saved["arguments"] == canonical(args) and saved["scope"] == canonical(scope)
                    return await execute(name, args, scope=scope, operation_key=operation_key, **kwargs)
                monkeypatch.setattr(tools, "execute_async", saved_only)
                descriptor = child_request["message"]["scientific_process"]["mechanics_binding"]
                workflow = Workflow(store, tools, actor, owned / "run", parent["run_id"],
                    lambda path, initial: FixtureController(str(path), initial, 1 if len(path) == 1 else 5), _credit,
                    project_child_credit=_credit, episode_binding_descriptors=[descriptor], episode_record_receipts=True,
                    initial_known_record_refs=[], decision_protocol="decision_exchange_v1",
                    credit_binding=original_context["credit_binding"], child_credit_binding=original_context["scientific_child_credit_binding"],
                    controller_binding=original_context["controller_binding"])
                role, key = json.loads(parent["path"])[0]
                root = workflow.build(role, key, parent_request["goal"]["objective"], parent_request["message"]["scope"])
                record = asyncio.run(root.run_async(workflow.context))
                final = asyncio.run(root.build_result(record)).as_record()
                expected = _ensembl_attempt_parent_delivery(store, workflow, sources)
                if live.get("parent_return_verified"):
                    assert expected == live["parent_form"] and final == live["final_root_result"]
                assert [tuple(row) for row in store.db.execute("SELECT * FROM tool_operations ORDER BY operation_key")] == original_operations
                assert [tuple(row) for row in store.db.execute("SELECT * FROM runtime_model_calls ORDER BY episode_id,call_index")] == original_model_calls
                assert not report["forbidden_attempts"] and actor.calls == []
                if closed:
                    assert _retained_live_rows(store.db) == before_original
                    assert _retained_live_inventory(owned / "store" / "artifacts") == original_artifacts
                    assert _retained_live_inventory(owned / "run") == original_run_files
                report.update(parent_return_verified=True, parent_form=expected, final_root_result=final,
                    saved_operations_and_model_calls_unchanged=True, owned_recovery_reached=True,
                    originally_closed_root=closed, closed_original_tables_files_unchanged=closed)
            finally:
                report["owned_workflow_prefix"] = _ensembl_live_json(_retained_live_rows(store.db))
    except BaseException as error:
        report["recovery_failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        assert _retained_live_inventory(original) == inventory
        report["original_files_unchanged"] = True
        proof.write_text(json.dumps(report, indent=2, allow_nan=False))
