"""Ordinary Entrez retrieval receipts and data custody; no external requests."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import http.client
import json
from types import SimpleNamespace
import urllib.error
import urllib.request
from urllib.parse import urlencode

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode import ncbi_entrez_acquisition as native
from gene_annotation_episode import ncbi_entrez_tools as host
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.providers import _SessionConnection

from test_alphafold_acquisition_host import Provider, _controller, _credit, _selected
from test_ensembl_acquisition_host import HTTP
from test_molecular_provider_acquisition_host import _artifacts, _tables
from test_runtime import FixtureController, ScriptedProvider
from test_scientific_process_runtime import action
import test_ncbi_entrez_acquisition as captures


SEARCH = b'{"esearchresult":{"count":"27","retstart":"0","retmax":"2","idlist":["42","42"],"unknown":null}}'
RECEIPT_FIELDS = {"acquired", "source_ref", "data_ref", "failure_code"}


def forbidden(*args, **kwargs):
    raise AssertionError("ordinary Entrez control attempted unselected work")


@pytest.fixture
def host_case(tmp_path, monkeypatch, request):
    http = HTTP()
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_handlers: http)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    selected = deepcopy(getattr(request, "param", captures.arguments(term="GSE1000[ACCN]", max_bytes=4096)))
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=PublicClients(timeout=3))
        scope = {"subject_refs": store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]}
        workflow = Workflow(store, tools, Provider(), tmp_path / "run", "ordinary-entrez-host-controls",
            _controller, _credit, project_child_credit=_credit,
            episode_record_receipts=True, initial_known_record_refs=[])
        root = workflow.build("annotation", "root", "Retrieve the selected native data for later analysis.", scope)
        yield SimpleNamespace(store=store, tools=tools, scope=scope, workflow=workflow, root=root,
            context=workflow.binding_context(root.source), request=selected, http=http, tmp_path=tmp_path)


def execute(case, *, arguments=None, index=0, record=True):
    return _selected(case.tools, case.workflow, case.root, host.TOOL,
        case.request if arguments is None else arguments, index, record=record)


def acquire(case, raw=SEARCH, *, status=200, media_type="application/json", record=True):
    case.http.add(raw, status=status, media_type=media_type)
    outcome = execute(case, record=record)
    assert set(outcome["result"]) == RECEIPT_FIELDS
    receipt = outcome["result"]
    source = None if receipt["source_ref"] is None else case.store.get(receipt["source_ref"])
    return SimpleNamespace(outcome=outcome, receipt=receipt, source=source)


def test_ordinary_catalog_and_saved_action_deliver_only_receipt_source_and_original_data(host_case):
    h = host_case
    contract = host.ncbi_entrez_tool_contract()
    assert contract["input_schema"] == native.ARGUMENTS_SCHEMA
    assert "Retrieval STEP" in contract["instructions"] and "future analysis" in contract["instructions"]
    assert h.tools.catalog(h.scope)[host.TOOL] == contract
    result = acquire(h)
    receipt, source = result.receipt, result.source
    assert receipt == {"acquired": True, "source_ref": source["id"],
        "data_ref": source["artifact_ref"], "failure_code": None}
    assert result.outcome["status"] == "completed"
    assert result.outcome["record_refs"] == [source["id"], source["artifact_ref"]]
    assert h.store.get_artifact(receipt["data_ref"]) == SEARCH
    assert receipt["data_ref"] == "artifact_" + hashlib.sha256(SEARCH).hexdigest()
    assert source["origin"] == "external" and source["provider"] == host.TOOL
    assert source["version"] is source["accession"] is None
    control_raw = h.store.get_artifact(source["request_ref"])
    control = json.loads(control_raw)
    assert control_raw == canonical(control).encode() and control["request"] == h.request
    spec = native.entrez_request_spec(h.request)
    wire, = h.http.requests
    assert wire["url"] == spec["url"] + "?" + urlencode(spec["params"])
    assert wire["method"] == "GET" and wire["body"] is None and wire["timeout"] == 3
    assert control["transport"]["request_policy"] == {"timeout_seconds": 3, "automatic_redirects": False}
    operation, = h.store.db.execute("SELECT * FROM tool_operations")
    action, = h.store.db.execute("SELECT * FROM runtime_actions")
    assert operation["name"] == host.TOOL and operation["scope"] == canonical(h.scope)
    assert json.loads(operation["arguments"]) == h.request
    assert json.loads(operation["result"]) == json.loads(action["result"]) == result.outcome
    assert json.loads(action["action"]) == {"kind": "tool", "tool": host.TOOL, "arguments": h.request}
    assert h.store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 1
    for table in ("runtime_model_calls", "runtime_forms", "runtime_report_attempts", "runtime_observations"):
        assert h.store.db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
    assert h.store.count("reference") == h.store.count("observation") == h.store.count("annotation") == 0


@pytest.mark.parametrize("raw", [
    b'{"esearchresult":{"count":"0","retstart":"0","retmax":"2","idlist":[]}}',
    b'{"esearchresult":{"count":"1","count":"2","retstart":"0","retmax":"2","idlist":[],"value":1e-9999,"units":null}}',
    b'{"esearchresult":{"idlist":["1"]},"esearchresult":{"idlist":[]}}',
    b'{"esearchresult":{"count":"0","retstart":"0","retmax":"2","idlist":[],"warninglist":{"warning":["native qualification"]}}}',
])
def test_empty_results_and_native_data_qualifications_do_not_become_analysis_acceptance_thresholds(host_case, raw):
    result = acquire(host_case, raw)
    assert result.receipt["acquired"] is True and result.receipt["failure_code"] is None
    assert host_case.store.get_artifact(result.receipt["data_ref"]) == raw
    assert set(result.receipt) == RECEIPT_FIELDS
    assert len(host_case.http.requests) == 1


@pytest.mark.parametrize("host_case", [captures.arguments("summary", "sra", ids=["1"], max_bytes=4096)], indirect=True)
def test_sra_associations_and_embedded_biosample_bioproject_stay_in_original_data_for_future_analysis(host_case):
    raw = json.dumps({"result": {"uids": ["1"], "1": {"uid": "1",
        "expxml": '<Study acc="SRP1"/><Sample accession="SRS1"/><Experiment acc="SRX1"/><Run acc="SRR1"/>',
        "biosample": "SAMN1", "bioproject": "PRJNA1"}}}).encode()
    result = acquire(host_case, raw)
    assert result.receipt["acquired"] is True
    assert host_case.store.get_artifact(result.receipt["data_ref"]) == raw
    assert set(result.receipt) == RECEIPT_FIELDS and len(host_case.http.requests) == 1


@pytest.mark.parametrize("host_case", [captures.arguments("fetch", "gene", ids=["1"], max_bytes=4096)], indirect=True)
def test_selected_gene_xml_data_is_original_and_has_no_model_analysis_projection(host_case):
    raw = b'<Entrezgene-Set><Entrezgene><Gene-track_geneid>1</Gene-track_geneid><unknown units="unknown">native</unknown></Entrezgene></Entrezgene-Set>'
    result = acquire(host_case, raw, media_type="application/xml; charset=utf-8")
    assert result.receipt["acquired"] is True
    assert host_case.store.get_artifact(result.receipt["data_ref"]) == raw
    assert host_case.http.requests[0]["headers"]["Accept"] == "application/xml"
    assert set(result.receipt) == RECEIPT_FIELDS


@pytest.mark.parametrize("host_case", [captures.arguments("fetch", "nuccore", ids=["TEST0001.1"], max_bytes=4096)], indirect=True)
@pytest.mark.parametrize("raw", [b"", b"complete native HTTP body without a GenBank record\n"])
def test_empty_or_non_genbank_fetch_body_is_not_acquired_as_native_data(host_case, raw):
    result = acquire(host_case, raw, media_type="text/plain")
    assert result.receipt == {"acquired": False, "source_ref": result.source["id"], "data_ref": None,
        "failure_code": "ncbi_entrez_native_format_unavailable"}
    assert result.outcome["record_refs"] == [result.source["id"]]
    assert host_case.store.get_artifact(result.source["artifact_ref"]) == raw
    assert len(host_case.http.requests) == 1


@pytest.mark.parametrize("raw,status,code", [
    (b'{"error":"native denial"}', 200, "ncbi_entrez_native_error_response"),
    (b'{"error":"native denial"}', 503, "ncbi_entrez_http_not_success"),
    (b'<html>original failure</html>', 200, "ncbi_entrez_native_format_unavailable"),
    (b'\xff', 200, "ncbi_entrez_native_format_unavailable"),
    (b'{}', 200, "ncbi_entrez_native_response_identity_missing"),
    (b'{"result":{"uids":[]}}', 200, "ncbi_entrez_native_response_identity_missing"),
])
def test_captured_wrong_or_error_response_returns_false_receipt_and_retains_source_without_data_grant(host_case, raw, status, code):
    h = host_case
    result = acquire(h, raw, status=status)
    assert result.receipt == {"acquired": False, "source_ref": result.source["id"], "data_ref": None, "failure_code": code}
    assert result.outcome["record_refs"] == [result.source["id"]]
    assert h.store.get_artifact(result.source["artifact_ref"]) == raw
    known = set(h.workflow.receipts.known(h.context.episode_id))
    assert result.source["artifact_ref"] not in known and result.source["request_ref"] not in known
    assert len(h.http.requests) == 1


@pytest.mark.parametrize("status,headers", [(206, {}), (200, {"cOnTeNt-RaNgE": "bytes 0-99/200"})])
def test_unrequested_partial_entity_is_not_acquired_even_when_native_json_and_capture_are_complete(host_case, status, headers):
    h = host_case
    h.http.add(SEARCH, status=status, media_type="application/json", **headers)
    outcome = execute(h)
    receipt = outcome["result"]
    source = h.store.get(receipt["source_ref"])
    assert receipt == {"acquired": False, "source_ref": source["id"], "data_ref": None,
        "failure_code": "ncbi_entrez_unrequested_range_response"}
    assert outcome["record_refs"] == [source["id"]]
    assert h.store.get_artifact(source["artifact_ref"]) == SEARCH
    control = json.loads(h.store.get_artifact(source["request_ref"]))
    assert control["transport"]["body_complete"] is True
    assert control["transport"]["retained_body_bytes"] == control["transport"]["observed_body_bytes"] == len(SEARCH)
    assert source["artifact_ref"] not in set(h.workflow.receipts.known(h.context.episode_id))
    assert len(h.http.requests) == 1


def test_bounded_capture_keeps_actual_prefix_but_does_not_deliver_it_as_complete_data(host_case):
    h = host_case
    raw = SEARCH[:-1] + b',"padding":"' + b'x' * 5000 + b'"}'
    result = acquire(h, raw)
    assert result.receipt["acquired"] is False and result.receipt["data_ref"] is None
    assert result.receipt["failure_code"] == "provider_response_byte_limit"
    assert h.store.get_artifact(result.source["artifact_ref"]) == raw[:4096]
    assert result.outcome["record_refs"] == [result.source["id"]] and len(h.http.requests) == 1


def test_interrupted_capture_retains_partial_bytes_and_reports_original_capture_cause(host_case, monkeypatch):
    h = host_case
    original_open = h.http.open
    partial = SEARCH[:40]
    def interrupted(request, timeout):
        response = original_open(request, timeout)
        def read(_size=-1):
            raise http.client.IncompleteRead(partial=partial, expected=len(SEARCH) - len(partial))
        response.read = read
        return response
    monkeypatch.setattr(h.http, "open", interrupted)
    result = acquire(h)
    assert result.receipt["acquired"] is False and result.receipt["data_ref"] is None
    assert result.receipt["failure_code"] == "provider_body_capture_failed"
    assert h.store.get_artifact(result.source["artifact_ref"]) == partial
    assert len(h.http.requests) == 1


@pytest.mark.parametrize("change", ["url", "method", "redirect", "accept", "limit"])
def test_actual_selected_request_transport_mismatch_preserves_captured_source_with_no_data_handle(host_case, monkeypatch, change):
    h = host_case
    original_http = h.tools.clients._http
    def mismatched(*args, **kwargs):
        snapshot = original_http(*args, **kwargs)
        transport = deepcopy(snapshot.transport)
        if change == "url": transport["request"]["url"] += "&unselected=yes"
        elif change == "method": transport["request"]["method"] = "POST"
        elif change == "redirect": transport["request_policy"]["automatic_redirects"] = True
        elif change == "accept": transport["request"]["headers"]["Accept"] = "text/plain"
        else: transport["response_byte_limit"] = True
        return replace(snapshot, transport=transport)
    monkeypatch.setattr(h.tools.clients, "_http", mismatched)
    result = acquire(h)
    assert result.receipt["acquired"] is False and result.receipt["data_ref"] is None
    assert result.receipt["failure_code"].startswith("ncbi_entrez_transport_")
    assert h.store.get_artifact(result.source["artifact_ref"]) == SEARCH
    assert result.outcome["record_refs"] == [result.source["id"]] and len(h.http.requests) == 1


@pytest.mark.parametrize("status", [200, 503])
def test_supplied_client_contradictory_native_request_is_preserved_on_success_and_http_error(host_case, monkeypatch, status):
    h = host_case
    original_http = h.tools.clients._http
    def conflicting(*args, **kwargs):
        try:
            snapshot = original_http(*args, **kwargs)
        except AcquisitionError as error:
            assert error.snapshot is not None
            error.snapshot = replace(error.snapshot, request={**error.snapshot.request, "term": "contradictory native query"})
            raise
        return replace(snapshot, request={**snapshot.request, "term": "contradictory native query"})
    monkeypatch.setattr(h.tools.clients, "_http", conflicting)
    result = acquire(h, status=status)
    assert result.receipt == {"acquired": False, "source_ref": result.source["id"], "data_ref": None,
        "failure_code": "ncbi_entrez_selected_request_conflict"}
    control = json.loads(h.store.get_artifact(result.source["request_ref"]))
    assert control["request"] == {**native.entrez_request_spec(h.request)["params"], "term": "contradictory native query"}
    assert control["request"] != h.request
    assert result.outcome["record_refs"] == [result.source["id"]]
    assert h.store.get_artifact(result.source["artifact_ref"]) == SEARCH and len(h.http.requests) == 1


def test_reopened_same_key_uses_existing_ordinary_saved_receipt_without_http_or_new_publication(host_case, monkeypatch):
    h = host_case
    result = acquire(h)
    before = {name: h.store.db.execute("SELECT count(*) FROM " + name).fetchone()[0]
        for name in ("tool_operations", "records", "artifacts", "runtime_actions")}
    key = f'{h.context.run_id}:{h.context.episode_id}:0'
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    monkeypatch.setattr(host, "publish_ncbi_entrez_request", forbidden)
    with Store(h.store.path) as reopened:
        tools = ToolRegistry(reopened, clients=PublicClients(timeout=3))
        replay = asyncio.run(tools.execute_async(host.TOOL, h.request, scope=h.scope, operation_key=key))
        assert replay == result.outcome
        assert {name: reopened.db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in before} == before
    assert len(h.http.requests) == 1


@pytest.mark.parametrize("change", ["arguments", "scope"])
def test_existing_operation_key_cannot_change_selected_work_or_scope(host_case, change):
    h = host_case
    result = acquire(h)
    selected, scope = deepcopy(h.request), deepcopy(h.scope)
    if change == "arguments": selected["retmax"] = 1
    else: scope = {"subject_refs": []}
    key = f'{h.context.run_id}:{h.context.episode_id}:0'
    with pytest.raises(ContractError, match="operation_key_reused_for_different_work"):
        asyncio.run(h.tools.execute_async(host.TOOL, selected, scope=scope, operation_key=key))
    assert len(h.http.requests) == 1
    assert h.store.db.execute("SELECT result FROM tool_operations").fetchone()[0] == canonical(result.outcome)


def test_no_response_failure_returns_false_null_handles_and_cached_original_cause(host_case, monkeypatch):
    h = host_case
    h.http.add(urllib.error.URLError("engineered no response"))
    outcome = execute(h)
    assert outcome["result"] == {"acquired": False, "source_ref": None, "data_ref": None,
        "failure_code": "provider_connection_failed"}
    assert outcome["record_refs"] == []
    assert not h.store.db.execute("SELECT 1 FROM records WHERE json_extract(data,'$.provider')=?", (host.TOOL,)).fetchone()
    diagnostic = outcome["feedback"]["diagnostic_ref"]
    h.workflow.receipts.receive(h.context.episode_id, [diagnostic], kind="initial")
    assert h.workflow.resolver(h.context.scope, context=h.context)(diagnostic, "artifact") is False
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    key = f'{h.context.run_id}:{h.context.episode_id}:0'
    assert asyncio.run(h.tools.execute_async(host.TOOL, h.request, scope=h.scope, operation_key=key)) == outcome
    assert len(h.http.requests) == 1


def test_successful_data_file_delivery_is_explicit_and_private_controls_are_never_delivered(host_case):
    h = host_case
    result = acquire(h)
    resolve = h.workflow.resolver(h.context.scope, context=h.context)
    known = set(h.workflow.receipts.known(h.context.episode_id))
    assert {result.source["id"], result.receipt["data_ref"]} <= known
    assert result.source["request_ref"] not in known
    assert resolve(result.source["id"], "source") is True and resolve(result.receipt["data_ref"], "artifact") is True
    admitted, path = h.workflow.services.read_received_molecular_input(h.context,
        result.receipt["data_ref"], "artifact", file_format="text")
    assert admitted["failure"] is None and path.read_bytes() == SEARCH
    h.workflow.receipts.receive(h.context.episode_id, [result.source["request_ref"]], kind="initial")
    assert resolve(result.source["request_ref"], "artifact") is False


@pytest.mark.parametrize("status,raw", [(200, SEARCH), (503, b'{"error":"native denial"}')])
def test_source_only_receiving_context_can_read_primary_body_without_implicit_data_file_grant(host_case, status, raw):
    h = host_case
    result = acquire(h, raw, status=status)
    receiver = h.workflow.build("annotation", "source-receiver", "Inspect received source data.", h.scope)
    context = h.workflow.binding_context(receiver.source)
    h.workflow.receipts.receive(context.episode_id, [result.source["id"]], kind="initial")
    known = set(h.workflow.receipts.known(context.episode_id))
    assert result.source["artifact_ref"] not in known and result.source["request_ref"] not in known
    resolve = h.workflow.resolver(context.scope, context=context)
    assert resolve(result.source["id"], "source") is True and resolve(result.source["artifact_ref"], "artifact") is False
    read = _selected(h.tools, h.workflow, receiver, "source.read", {"source_ref": result.source["id"],
        "representation": "original", "offset": 0, "limit": len(raw)}, 0, record=True)
    assert read["status"] == "completed" and read["result"]["text"].encode() == raw
    assert read["record_refs"] == [] and set(h.workflow.receipts.known(context.episode_id)) == known


def test_unreceived_source_and_data_fail_before_bytes_without_new_grants(host_case, monkeypatch):
    h = host_case
    result = acquire(h, record=False)
    known = set(h.workflow.receipts.known(h.context.episode_id))
    monkeypatch.setattr(Store, "get_artifact", forbidden)
    monkeypatch.setattr("gene_annotation_episode.materials.artifact_path", forbidden)
    resolve = h.workflow.resolver(h.context.scope, context=h.context)
    assert resolve(result.source["id"], "source") is False and resolve(result.source["artifact_ref"], "artifact") is False
    read = _selected(h.tools, h.workflow, h.root, "source.read",
        {"source_ref": result.source["id"], "representation": "original"}, 1, record=True)
    assert read["status"] == "invalid" and read["record_refs"] == []
    assert read["feedback"]["code"] == "ncbi_entrez_source_primary_body_not_received"
    assert set(h.workflow.receipts.known(h.context.episode_id)) == known


def test_native_validation_failure_keeps_source_prefix_and_a_four_field_failure_receipt(host_case, monkeypatch):
    def rejected(*args, **kwargs):
        raise ValueError("ncbi_entrez_engineered_selected_request_conflict")
    monkeypatch.setattr(native, "entrez_result", rejected)
    result = acquire(host_case)
    assert result.receipt == {"acquired": False, "source_ref": result.source["id"],
        "data_ref": None, "failure_code": "ncbi_entrez_engineered_selected_request_conflict"}
    assert result.outcome["record_refs"] == [result.source["id"]]
    assert host_case.store.get_artifact(result.source["artifact_ref"]) == SEARCH


def test_unexpected_constructor_failure_preserves_only_actual_source_and_private_diagnostic(host_case, monkeypatch):
    h = host_case
    def rejected(*args, **kwargs):
        raise RuntimeError("engineered unexpected native validation exception")
    monkeypatch.setattr(native, "entrez_result", rejected)
    result = acquire(h)
    assert result.receipt == {"acquired": False, "source_ref": result.source["id"], "data_ref": None,
        "failure_code": "data_acquisition_publication_incomplete"}
    assert result.outcome["record_refs"] == result.outcome["changed_record_refs"] == [result.source["id"]]
    assert h.store.get_artifact(result.source["artifact_ref"]) == SEARCH
    diagnostic = result.outcome["feedback"]["diagnostic_ref"]
    assert diagnostic not in result.outcome["record_refs"]
    h.workflow.receipts.receive(h.context.episode_id, [diagnostic], kind="initial")
    assert h.workflow.resolver(h.context.scope, context=h.context)(diagnostic, "artifact") is False


@pytest.mark.parametrize("selected", [captures.arguments(database="pubmed"), captures.arguments(database="pmc"),
    captures.arguments(database="biosample"), captures.arguments(database="bioproject"),
    captures.arguments("fetch", "sra", ids=["SRR6263255"], native_format="unsupported"), captures.arguments(url="https://elsewhere.invalid")])
def test_out_of_scope_databases_unestablished_fetch_and_arbitrary_endpoints_never_issue_http(host_case, selected):
    outcome = execute(host_case, arguments=selected)
    assert outcome["status"] == "invalid" and outcome["record_refs"] == []
    assert not host_case.http.requests


def _genbank_record(accession='TEST0001', version='1', *, gi=None, secondary=(), protein=False):
    """Engineered native record identities; no search, annotation or fitting."""
    locus = (f'LOCUS       {accession:<27}4 aa            linear   PRI 01-JAN-2000\n' if protein else
        f'LOCUS       {accession:<27}4 bp    DNA     linear   UNA 01-JAN-2000\n')
    return (locus + 'DEFINITION  Engineered retained identity.\nACCESSION   ' + ' '.join((accession, *secondary)) +
        '\nVERSION     ' + accession + '.' + version + ('' if gi is None else '  GI:' + gi) +
        '\nKEYWORDS    .\nSOURCE      synthetic construct\n  ORGANISM  synthetic construct\n'
        'FEATURES             Location/Qualifiers\n     source          1..4\nORIGIN\n        1 ' +
        ('mkwa' if protein else 'atgc') + '\n//\n').encode()


@pytest.mark.parametrize('host_case,raw,state', [
    (captures.arguments('summary', 'protein', ids=['1'], max_bytes=4096),
        b'{"result":{"uids":["999"],"999":{"uid":"999"}}}', 'mismatch'),
    (captures.arguments('summary', 'protein', ids=['1'], max_bytes=4096),
        b'{"result":{"uids":["1"],"1":{"uid":"999"}}}', 'unavailable'),
    (captures.arguments('summary', 'protein', ids=['1'], max_bytes=4096),
        b'{"result":{"uids":["1"],"1":{"title":"native missing uid"}}}', 'unavailable'),
    (captures.arguments('summary', 'gene', ids=['1'], max_bytes=4096),
        b'{"result":{"uids":["999"],"999":{"uid":"999","currentid":1,"status":2}}}', 'unavailable'),
    (captures.arguments('summary', 'protein', ids=['1'], max_bytes=4096),
        b'{"result":{"uids":[]}}', 'empty'),
    (captures.arguments('fetch', 'gene', ids=['1'], max_bytes=4096),
        b'<Entrezgene-Set><Entrezgene><Gene-track_geneid>999</Gene-track_geneid>'
        b'<Gene-track_status value="live">0</Gene-track_status></Entrezgene></Entrezgene-Set>', 'mismatch'),
    (captures.arguments('fetch', 'gene', ids=['1'], max_bytes=4096),
        b'<Entrezgene-Set><Entrezgene><Gene-track_geneid>999</Gene-track_geneid>'
        b'<Gene-track_status value="secondary">1</Gene-track_status>'
        b'<Gene-track_current-id><Dbtag/></Gene-track_current-id></Entrezgene></Entrezgene-Set>', 'unavailable'),
    (captures.arguments('fetch', 'taxonomy', ids=['1'], max_bytes=4096),
        b'<TaxaSet><Taxon><TaxId>999</TaxId><LineageEx><Taxon><TaxId>1</TaxId></Taxon></LineageEx></Taxon></TaxaSet>', 'mismatch'),
    (captures.arguments('fetch', 'taxonomy', ids=['1'], max_bytes=4096),
        b'<TaxaSet><Taxon><TaxId>999</TaxId><AkaTaxIds><TaxId>1</TaxId></AkaTaxIds></Taxon></TaxaSet>', 'matched'),
], indirect=['host_case'])
def test_native_identity_disagreement_is_distinct_from_empty_alias_or_unavailable_identity(host_case, raw, state):
    h = host_case
    media = 'application/json' if h.request['native_format'] == 'json' else 'application/xml'
    result = acquire(h, raw, media_type=media)
    value = captures.result(raw, h.request)
    assert native.entrez_selected_identity_state(value) == state
    assert result.receipt['acquired'] is (state != 'mismatch')
    assert result.receipt['failure_code'] == ('ncbi_entrez_selected_record_identity_conflict' if state == 'mismatch' else None)
    assert h.store.get_artifact(result.source['artifact_ref']) == raw
    assert result.outcome['record_refs'] == ([result.source['id']] if state == 'mismatch' else
        [result.source['id'], result.source['artifact_ref']])
    assert len(h.http.requests) == 1 and set(result.receipt) == RECEIPT_FIELDS


@pytest.mark.parametrize('host_case,raw,state', [
    (captures.arguments('fetch', 'nuccore', ids=['TEST0001.1'], max_bytes=4096),
        _genbank_record('OTHER0001'), 'mismatch'),
    (captures.arguments('fetch', 'nuccore', ids=['TEST0001.2'], max_bytes=4096),
        _genbank_record(), 'mismatch'),
    (captures.arguments('fetch', 'nuccore', ids=['TEST0001'], max_bytes=4096),
        _genbank_record(), 'matched'),
    (captures.arguments('fetch', 'nuccore', ids=['ALT0002'], max_bytes=4096),
        _genbank_record(secondary=('ALT0002',)), 'matched'),
    (captures.arguments('fetch', 'nuccore', ids=['ALT0002.9'], max_bytes=4096),
        _genbank_record(secondary=('ALT0002',)), 'unavailable'),
    (captures.arguments('fetch', 'protein', ids=['123'], max_bytes=4096),
        _genbank_record(gi='123', protein=True), 'matched'),
    (captures.arguments('fetch', 'protein', ids=['123'], max_bytes=4096),
        _genbank_record(gi='999', protein=True), 'mismatch'),
    (captures.arguments('fetch', 'protein', ids=['123'], max_bytes=4096),
        _genbank_record(protein=True), 'unavailable'),
    (captures.arguments('fetch', 'nuccore', ids=['test0001.1'], max_bytes=4096),
        _genbank_record(), 'unavailable'),
], indirect=['host_case'])
def test_native_accession_version_and_gi_roles_do_not_invent_aliases(host_case, raw, state):
    h = host_case
    result = acquire(h, raw, media_type='text/x-genbank')
    assert native.entrez_selected_identity_state(captures.result(raw, h.request)) == state
    assert result.receipt['acquired'] is (state != 'mismatch')
    assert result.receipt['failure_code'] == ('ncbi_entrez_selected_record_identity_conflict' if state == 'mismatch' else None)
    assert h.store.get_artifact(result.source['artifact_ref']) == raw
    assert len(h.http.requests) == 1


def test_query_translation_and_native_not_found_are_not_reclassified_as_identity_disagreement(host_case):
    h = host_case
    raw = b'{"esearchresult":{"count":"0","retstart":"0","retmax":"2","idlist":[],"querytranslation":"different native translation","warninglist":{"outputmessages":["No items found."]}}}'
    result = acquire(h, raw)
    assert result.receipt['acquired'] is True and result.receipt['failure_code'] is None
    assert native.entrez_selected_identity_state(captures.result(raw, h.request)) == 'empty'
    assert h.store.get_artifact(result.receipt['data_ref']) == raw


@pytest.mark.parametrize('host_case', [captures.arguments('summary', 'protein', ids=['1'], max_bytes=4096)], indirect=True)
def test_native_not_found_error_keeps_its_original_failure_before_identity_checks(host_case):
    raw = b'{"result":{"uids":["999"],"999":{"uid":"999","error":"selected record not found"}}}'
    result = acquire(host_case, raw)
    assert result.receipt['acquired'] is False
    assert result.receipt['failure_code'] == 'ncbi_entrez_native_error_response'
    assert result.outcome['record_refs'] == [result.source['id']]
    assert host_case.store.get_artifact(result.source['artifact_ref']) == raw


@pytest.mark.parametrize("host_case", [captures.arguments("search", "snp", term="rs328[RS] OR rs699[RS]",
    retstart=7, retmax=2, max_bytes=4096)], indirect=True)
def test_snp_search_is_one_literal_selected_page_and_original_data_receipt(host_case):
    h = host_case
    raw = b'{"esearchresult":{"count":"00027","retstart":"7","retmax":"2","idlist":["699","699"],"unknown":1e-9999}}'
    result = acquire(h, raw)
    assert result.receipt["acquired"] is True and result.outcome["status"] == "completed"
    assert h.store.get_artifact(result.receipt["data_ref"]) == raw
    assert len(h.http.requests) == 1
    spec = native.entrez_request_spec(h.request)
    assert h.http.requests[0]["url"] == spec["url"] + "?" + urlencode(spec["params"])
    assert spec["params"]["term"] == h.request["term"] and spec["params"]["retstart"] == 7
    assert not {"usehistory", "query_key", "WebEnv"}.intersection(spec["params"])
    value = captures.result(raw, h.request)
    assert value["population"]["matching_count_native"] == "00027"
    assert value["population"]["returned_record_count"] == 2
    assert value["population"]["returned_id_order_native"] == ["699", "699"]
    assert not {"population", "records", "native_document"}.intersection(result.receipt)


@pytest.mark.parametrize("host_case", [captures.arguments("summary", "snp", ids=["328", "699", "328"], max_bytes=4096)], indirect=True)
def test_snp_summary_keeps_requested_uid_order_and_every_native_document_association(host_case):
    h = host_case
    raw = (b'{"result":{"uids":["699","328","699"],"328":{"uid":"328","snp_id":328},'
        b'"699":{"uid":"699","native_associations":{"assembly":null,"frequency":0}},'
        b'"699":{"uid":"699","frequency":null,"unknown":1e-9999}}}')
    result = acquire(h, raw)
    assert result.receipt["acquired"] and h.store.get_artifact(result.receipt["data_ref"]) == raw
    assert native.entrez_request_spec(h.request)["params"]["id"] == "328,699,328"
    value = captures.result(raw, h.request)
    assert native.entrez_selected_identity_state(value) == "matched"
    assert value["population"]["requested_id_count"] == value["population"]["returned_record_count"] == 3
    assert value["population"]["returned_id_order_native"] == ["699", "328", "699"]
    assert [record["identifier"] for record in value["records"]] == ["328", "699", "699"]
    assert value["population"]["matching_count_native"] is None and value["associations"] == []
    assert len(h.http.requests) == 1 and result.outcome["record_refs"] == [result.source["id"], result.source["artifact_ref"]]


@pytest.mark.parametrize("host_case,raw,code", [
    (captures.arguments("search", "snp", max_bytes=4096), b'{"esearchresult":{"count":"0","idlist":null}}', "ncbi_entrez_native_response_identity_missing"),
    (captures.arguments("search", "snp", max_bytes=4096), b'{"esearchresult":{"count":"0"}}', "ncbi_entrez_native_response_identity_missing"),
    (captures.arguments("search", "snp", max_bytes=4096), b'{"esearchresult":{"idlist":["rs699"]}}', "ncbi_entrez_native_response_identity_missing"),
    (captures.arguments("search", "snp", max_bytes=4096), b'{"esearchresult":{"idlist":[699]}}', "ncbi_entrez_native_response_identity_missing"),
    (captures.arguments("summary", "snp", ids=["699"], max_bytes=4096), b'{"result":{"uids":null}}', "ncbi_entrez_native_response_identity_missing"),
    (captures.arguments("summary", "snp", ids=["699"], max_bytes=4096), b'{"result":{"699":{"uid":"699"}}}', "ncbi_entrez_native_response_identity_missing"),
    (captures.arguments("summary", "snp", ids=["699"], max_bytes=4096), b'{"result":{"uids":["699"]}}', "ncbi_entrez_native_response_identity_missing"),
    (captures.arguments("summary", "snp", ids=["699"], max_bytes=4096), b'{"result":{"uids":["699"],"699":{"snp_id":699}}}', "ncbi_entrez_native_response_identity_missing"),
    (captures.arguments("summary", "snp", ids=["699"], max_bytes=4096), b'{"result":{"uids":["699"],"699":{"uid":false}}}', "ncbi_entrez_native_response_identity_missing"),
    (captures.arguments("summary", "snp", ids=["699"], max_bytes=4096), b'{"result":{"uids":["699"],"699":{"uid":"699","uid":"699"}}}', "ncbi_entrez_native_response_identity_missing"),
    (captures.arguments("summary", "snp", ids=["699"], max_bytes=4096), b'{"result":{"uids":["999"],"999":{"uid":"999"}}}', "ncbi_entrez_selected_record_identity_conflict"),
    (captures.arguments("summary", "snp", ids=["699"], max_bytes=4096), b'{"result":{"uids":["699"],"699":{"uid":"999"}}}', "ncbi_entrez_selected_record_identity_conflict"),
], indirect=["host_case"])
def test_snp_missing_or_conflicting_native_uid_inventory_is_not_confirmed_or_relabelled(host_case, raw, code):
    h = host_case
    result = acquire(h, raw)
    assert result.receipt == dict(acquired=False, source_ref=result.source["id"], data_ref=None, failure_code=code)
    assert h.store.get_artifact(result.source["artifact_ref"]) == raw
    assert result.outcome["record_refs"] == [result.source["id"]] and len(h.http.requests) == 1
    assert result.source["artifact_ref"] not in set(h.workflow.receipts.known(h.context.episode_id))


@pytest.mark.parametrize("host_case,raw", [
    (captures.arguments("search", "snp", max_bytes=4096), b'{"esearchresult":{"count":"0","retstart":"0","retmax":"2","idlist":[]}}'),
    (captures.arguments("summary", "snp", ids=["699"], max_bytes=4096), b'{"result":{"uids":[]}}'),
], indirect=["host_case"])
def test_snp_explicit_empty_native_inventory_is_acquired_data_not_a_found_variant_claim(host_case, raw):
    result = acquire(host_case, raw)
    assert result.receipt["acquired"] is True and result.receipt["failure_code"] is None
    assert host_case.store.get_artifact(result.receipt["data_ref"]) == raw
    value = captures.result(raw, host_case.request)
    assert value["population"]["returned_record_count"] == 0 and value["records"] == []
    assert native.entrez_selected_identity_state(value) == "empty"
    assert len(host_case.http.requests) == 1


@pytest.mark.parametrize("host_case", [captures.arguments("summary", "snp", ids=["699"], max_bytes=4096)], indirect=True)
@pytest.mark.parametrize("raw,status,code", [
    (b'{"error":"native denial"}', 429, "ncbi_entrez_http_not_success"),
    (b'{"result":{"uids":["699"],"699":{"uid":"699","error":"selected record not found"}}}', 200, "ncbi_entrez_native_error_response"),
    (b'{"unfinished":', 200, "ncbi_entrez_native_format_unavailable"),
])
def test_snp_original_http_and_native_errors_precede_identity_confirmation(host_case, raw, status, code):
    result = acquire(host_case, raw, status=status)
    assert result.receipt == dict(acquired=False, source_ref=result.source["id"], data_ref=None, failure_code=code)
    assert host_case.store.get_artifact(result.source["artifact_ref"]) == raw
    assert len(host_case.http.requests) == 1


@pytest.mark.parametrize("host_case", [captures.arguments("summary", "snp", ids=["699"], max_bytes=32)], indirect=True)
def test_snp_bounded_capture_retains_only_actual_prefix_without_a_data_file_receipt(host_case):
    raw = b'{"result":{"uids":["699"],"699":{"uid":"699","unknown":"original"}}}'
    result = acquire(host_case, raw)
    assert result.receipt["acquired"] is False and result.receipt["data_ref"] is None
    assert result.receipt["failure_code"] == "provider_response_byte_limit"
    assert host_case.store.get_artifact(result.source["artifact_ref"]) == raw[:32]
    assert len(host_case.http.requests) == 1


@pytest.mark.parametrize("selected", [captures.arguments("fetch", "snp", native_format="json"),
    captures.arguments("summary", "snp", ids=["rs699"]), captures.arguments("summary", "snp", ids=["699\n"])])
def test_snp_unsupported_fetch_and_uid_rewriting_are_rejected_before_transport(host_case, selected):
    outcome = execute(host_case, arguments=selected)
    assert outcome["status"] == "invalid" and outcome["record_refs"] == []
    assert outcome["result"]["source_ref"] is outcome["result"]["data_ref"] is None
    assert not host_case.http.requests


def _snp_controller(path, initial):
    return FixtureController(str(path), initial, 2)


def _snp_session(directory):
    role = dict(model="snp-presentation-engineering", reasoning_effort="low")
    return _SessionConnection(dict(connection={"command": ["unselected-model-command"]},
        FAST=role, REASONING=role, routing={}), directory, directory.parent)


class _SnpProvider(ScriptedProvider):
    """Actual DecisionSource calls; Session presentation only, no model RPC."""
    def __init__(self, script, session):
        super().__init__(script)
        self.session, self.dispatches = session, []

    async def complete(self, episode_id, role, instructions, context, output_schema):
        wire, model_instructions = self.session._presentation(episode_id, role, instructions, context)
        self.dispatches.append(dict(context=deepcopy(context), instructions=instructions,
            schema=deepcopy(output_schema), wire=wire, model_instructions=model_instructions))
        return await super().complete(episode_id, role, instructions, context, output_schema)


@pytest.mark.parametrize("operation", ["search", "summary"])
def test_snp_current_episode_receipt_admission_lost_reply_session_and_closed_replay(
        tmp_path, monkeypatch, operation):
    """Engineered transport in one real episode; no getter child or model RPC."""
    class LostReply(RuntimeError): pass
    http = HTTP()
    selected = (captures.arguments("search", "snp", term="rs328[RS] OR rs699[RS]", retstart=7, retmax=2, max_bytes=4096)
        if operation == "search" else captures.arguments("summary", "snp", ids=["699", "328", "699"], max_bytes=4096))
    raw = (b'{"esearchresult":{"count":"27","retstart":"7","retmax":"2","idlist":["699","328"]}}'
        if operation == "search" else b'{"result":{"uids":["328","699"],"699":{"uid":"699","frequency":0},"328":{"uid":"328","frequency":null}}}')
    http.add(raw, media_type="application/json")
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_handlers: http)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    monkeypatch.setattr("gene_annotation_episode.providers._SessionConnection._rpc", forbidden)
    with Store(tmp_path / "store") as store:
        scope = {"subject_refs": store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]}
        original_targets = deepcopy(store.problem()["subject_refs"])
        tools, session = ToolRegistry(store, clients=PublicClients(timeout=3)), _snp_session(tmp_path / "session")
        directory, run_id = tmp_path / "run", "ordinary-snp-current-episode-engineering"
        goal = ("Evaluate molecular evidence for the supplied protein while keeping its correspondence to "
            "caller-selected dbSNP reference data unresolved. Acquiring a record does not settle a scientific conclusion.")
        def workflow(actor):
            return Workflow(store, tools, actor, directory, run_id, _snp_controller, _credit,
                project_child_credit=_credit, root_role="improvement", episode_record_receipts=True,
                initial_known_record_refs=[])
        actor = _SnpProvider([action(host.TOOL, selected)], session)
        current = workflow(actor)
        root = current.build("improvement", "root", goal, scope)
        baseline = set(current.receipts.known(root.source.episode_id))
        actual_execute, lost = ToolRegistry.execute_async, []
        async def lose_reply(registry, name, arguments, **kwargs):
            outcome = await actual_execute(registry, name, arguments, **kwargs)
            if name == host.TOOL and not lost:
                assert outcome["status"] == "completed"
                lost.append(deepcopy(outcome)); raise LostReply()
            return outcome
        with monkeypatch.context() as patch:
            patch.setattr(ToolRegistry, "execute_async", lose_reply)
            with pytest.raises(LostReply): asyncio.run(root.run_async(current.context))
        assert len(http.requests) == len(actor.dispatches) == 1
        assert store.db.execute("SELECT result FROM runtime_actions").fetchone()[0] is None
        source = store.get(lost[0]["result"]["source_ref"])
        data_ref = source["artifact_ref"]
        assert {source["id"], data_ref}.isdisjoint(current.receipts.known(root.source.episode_id))
        assert store.get_artifact(data_ref) == raw
        actual_get = Store.get_artifact
        holder = {}
        def read_data(context):
            # The same-key getter already returned before body reads are
            # re-enabled for this separately selected Source read.
            assert context["last_local_outcome"]["result"] == lost[0]["result"]
            monkeypatch.setattr(Store, "get_artifact", actual_get)
            owner, resumed = holder["owner"], holder["root"]
            binding = owner.binding_context(resumed.source)
            known = set(owner.receipts.known(binding.episode_id))
            assert known == baseline | {source["id"], data_ref}
            assert source["request_ref"] not in known
            resolve = owner.resolver(plain(binding.scope), context=binding)
            assert resolve(source["id"], "source") is True and resolve(data_ref, "artifact") is True
            assert resolve(source["request_ref"], "artifact") is False
            admitted, path = owner.services.read_received_molecular_input(binding, data_ref, "artifact", file_format="text")
            assert admitted["failure"] is None and path.read_bytes() == raw
            return action("source.read", dict(source_ref=source["id"], representation="original", offset=0, limit=len(raw)))
        monkeypatch.setattr(PublicClients, "_http", forbidden)
        monkeypatch.setattr(host, "publish_ncbi_entrez_request", forbidden)
        monkeypatch.setattr(native, "entrez_result", forbidden)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        receiver = _SnpProvider([read_data], session)
        recovered = workflow(receiver)
        resumed = recovered.build("improvement", "root", goal, scope)
        holder.update(owner=recovered, root=resumed)
        record = asyncio.run(resumed.run_async(recovered.context))
        final = asyncio.run(resumed.build_result(record)).as_record()
        assert len(http.requests) == 1 and store.problem()["subject_refs"] == original_targets
        assert json.loads(store.db.execute("SELECT result FROM tool_operations WHERE name='source.read'").fetchone()[0])["result"]["text"].encode() == raw
        calls = list(store.db.execute("SELECT request,response FROM runtime_model_calls ORDER BY call_index"))
        dispatches = actor.dispatches + receiver.dispatches
        assert len(calls) == len(dispatches) == 2
        for saved, dispatched in zip(calls, dispatches):
            assert json.loads(saved["request"])["context"] == dispatched["context"] and saved["response"] is not None
            assert json.loads(dispatched["wire"]) == dispatched["context"]
            assert dispatched["model_instructions"] == dispatched["instructions"]
            assert dispatched["context"]["goal"] == root.source.request.goal.as_record()
        counts = {name: store.db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in (
            "runtime_episodes", "runtime_actions", "runtime_observations", "runtime_model_calls", "tool_operations")}
        assert counts == dict(runtime_episodes=1, runtime_actions=2, runtime_observations=2,
            runtime_model_calls=2, tool_operations=2)
        assert store.db.execute("SELECT count(*) FROM runtime_forms").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_report_attempts").fetchone()[0] == 0
        before, files, archives = _tables(store), _artifacts(store.path / "artifacts"), _artifacts(directory / "archive")
        monkeypatch.setattr(ToolRegistry, "execute_async", forbidden)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        replay_actor = ScriptedProvider([])
        replay = workflow(replay_actor)
        replay_root = replay.build("improvement", "root", goal, scope)
        replay_record = asyncio.run(replay_root.run_async(replay.context))
        assert asyncio.run(replay_root.build_result(replay_record)).as_record() == final
        assert replay_actor.contexts == [] and _tables(store) == before
        assert _artifacts(store.path / "artifacts") == files and _artifacts(directory / "archive") == archives


def test_live_retained_sra_accession_search_ordinary_acquisition(tmp_path, monkeypatch):
    """One selected SRA metadata page; a controlled failure is not acquired data."""
    import os
    from pathlib import Path

    from gene_annotation_episode.acquisition import SourceSnapshot
    from gene_annotation_episode.domain import identity
    from gene_annotation_episode.runtime import ActionFailure
    from test_molecular_acquisition_ordinary import (
        NoModel, _forbidden, _neutral_bookkeeping, _snapshot,
        _live_audit, _live_capture, _live_pin, _live_write,
    )

    if os.environ.get("HMMER_NATIVE_ORACLE_SRA_METADATA") != "1":
        pytest.skip("requires explicit one-request SRA metadata acquisition")

    fixture_root = Path(__file__).parent / "fixtures/bvbrc_fastqutils/sra"
    native_path = fixture_root / "native_selected_run.json"
    origin_path = fixture_root / "SOURCE_RECEIPT.json"
    assert _live_pin(native_path)["sha256"] == "64e2f99d807691af2536df4287d93cef70b76a83c5ad6c1ce83f42533db68051"
    assert _live_pin(origin_path)["sha256"] == "9decad6cb2abeeea846e7981f6b5b9ee9d39f03ab9105db8994ee2e662e4ce91"
    native_row, = json.loads(native_path.read_bytes())
    origin = json.loads(origin_path.read_bytes())
    original, = [row for row in origin["cases"] if row["case"] == "native_selected_run"]
    assert native_row["run_id"] == native_row["accession"] == original["accession_filter"] == "SRR6263255"
    assert original["provenance"] == "unaltered_live_NCBI_XML"
    assert original["original_live_XML_sha256"] == "e2e72cc189d988194ef9ab9faff6b96132749afd7cdc3293f386902544e45b10"
    assert original["files"]["metadata.json"] == _live_pin(native_path)["sha256"]
    assert original["selected_function"] == "parse_accession_metadata" and original["row_count"] == 1
    assert origin["read_download"] is origin["live_BV_BRC_job"] is False

    arguments = dict(operation="search", database="sra", term="SRR6263255",
        retstart=0, retmax=2, native_format="json", max_bytes=8388608)
    spec = native.entrez_request_spec(arguments)
    address = spec["url"] + "?" + urlencode(spec["params"])
    assert spec == dict(service="ncbi_entrez",
        url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", method="GET",
        params=dict(db="sra", tool="gene-annotation-episode", term="SRR6263255",
            retstart=0, retmax=2, retmode="json"),
        media_type="application/json", max_bytes=8388608, follow_redirects=False)
    assert address == ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?"
        "db=sra&tool=gene-annotation-episode&term=SRR6263255&retstart=0&retmax=2&retmode=json")

    proof_path = tmp_path / "SRA_METADATA_ACQUISITION_PREFIX.json"
    store_directory = tmp_path / "store"
    proof = dict(version="sra_metadata_live_invocation_v1", tool=host.TOOL,
        service=spec["service"], arguments=arguments, selected_wire_url=address,
        bounded_attempt=os.environ.get("HMMER529_ATTEMPT"),
        input_provenance=dict(native_fixture=_live_pin(native_path),
            source_receipt_fixture=_live_pin(origin_path),
            original_live_XML_sha256=original["original_live_XML_sha256"],
            native_run_accession=native_row["run_id"],
            experiment_accession=native_row["exp_id"], sample_accession=native_row["sample_id"],
            study_accession=native_row["study_id"]),
        store_directory=str(store_directory), workflow_directory=str(tmp_path / "run"),
        invocation_check_passed=False, native_data_acquired=None,
        requested_run_presence="not_established_by_search_UIDs", http_calls=[],
        qualification="One ordinary selected metadata search page before controller observation. "
            "An acquired empty page is query-response data, not a found run or exhaustive absence. "
            "No UID conversion, summary follow-up, archive/FASTQ acquisition, read counting, "
            "analysis or whole-episode completion is performed.",
        read_download=False, analysis_performed=False, same_key_replay_verified=False)
    _live_write(proof_path, proof, exclusive=True)
    actual_http = PublicClients._http

    def http(client, service, url, params, media_type, **kwargs):
        assert proof["http_calls"] == [], "one selected HTTP invocation; no retry or follow-up"
        assert dict(service=service, url=url, params=params, media_type=media_type, **kwargs) == dict(
            service=spec["service"], url=spec["url"], params=spec["params"],
            media_type=spec["media_type"], max_bytes=arguments["max_bytes"],
            timeout_seconds=90, follow_redirects=False)
        proof["http_calls"].append(dict(started=True, service=service, url=url,
            params=deepcopy(params), media_type=media_type, keywords=deepcopy(kwargs)))
        _live_write(proof_path, proof)
        try:
            capture = actual_http(client, service, url, params, media_type, **kwargs)
        except AcquisitionError as error:
            proof["http_calls"][0]["failure"] = dict(code=error.code, phase=error.phase)
            if isinstance(error.snapshot, SourceSnapshot):
                _live_capture(error.snapshot, tmp_path, proof, proof_path)
            _live_write(proof_path, proof)
            raise
        except BaseException as error:
            proof["http_calls"][0]["failure"] = dict(exception_type=type(error).__name__, message=str(error))
            _live_write(proof_path, proof)
            raise
        _live_capture(capture, tmp_path, proof, proof_path)
        return capture

    failure_codes = {
        "provider_connection_failed", "provider_request_timeout", "provider_response_byte_limit",
        "provider_body_capture_failed", "data_acquisition_failed", "data_acquisition_publication_incomplete",
        "invalid_tool_input", "adapter_execution_failed", "ncbi_entrez_contract_invalid",
        "ncbi_entrez_snapshot_conflict", "ncbi_entrez_selected_request_conflict",
        "ncbi_entrez_transport_request_conflict", "ncbi_entrez_transport_policy_conflict",
        "ncbi_entrez_transport_media_conflict", "ncbi_entrez_transport_limit_conflict",
        "ncbi_entrez_references_invalid", "ncbi_entrez_artifact_identity_conflict",
        "ncbi_entrez_response_request_conflict", "ncbi_entrez_native_text_identity_conflict",
        "ncbi_entrez_native_result_conflict", "ncbi_entrez_representation_conflict",
        "ncbi_entrez_population_conflict", "ncbi_entrez_http_status_unknown",
        "ncbi_entrez_http_not_success", "ncbi_entrez_unrequested_range_response",
        "ncbi_entrez_capture_not_complete", "ncbi_entrez_native_error_response",
        "ncbi_entrez_native_format_unavailable", "ncbi_entrez_native_response_identity_missing",
        "ncbi_entrez_native_response_identity_conflict", "ncbi_entrez_selected_record_identity_conflict",
    }
    try:
        with Store(store_directory) as store:
            subject, = store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]
            scope = store.validate_scope(dict(subject_refs=[subject]))
            tools = ToolRegistry(store, clients=PublicClients(ncbi_email=None, timeout=90))
            workflow = Workflow(store, tools, NoModel(), tmp_path / "run", "sra-metadata-live",
                _forbidden, _neutral_bookkeeping, episode_binding_factories=(), root_role="improvement",
                episode_record_receipts=True, initial_known_record_refs=[])
            caller = workflow.build("improvement", "existing-caller",
                "Retrieve the caller-selected SRA metadata search page for later analysis", scope)
            selection = dict(kind="tool", tool=host.TOOL, arguments=arguments)
            key = f"{workflow.run_id}:{caller.source.episode_id}:0"
            known_before = set(workflow.receipts.known(caller.source.episode_id))
            proof.update(run_id=workflow.run_id, episode_id=caller.source.episode_id,
                operation_key=key, selection=selection, scope=scope,
                tool_info=deepcopy(tools.catalog(scope)[host.TOOL]), known_before=sorted(known_before))
            _live_write(proof_path, proof)
            try:
                with monkeypatch.context() as live:
                    live.setattr(PublicClients, "_http", http)
                    live.setattr("urllib.request.urlopen", _forbidden)
                    live.setattr("gene_annotation_episode.native_lifecycle.prepare_job", _forbidden)
                    live.setattr(ToolRegistry, "_sequence_worker_async", _forbidden)
                    live.setattr("gene_annotation_episode.bvbrc_fastqutils_sra_native.parse_sra_metadata", _forbidden)
                    try:
                        asyncio.run(caller.source.execute(selection, 0))
                    except ActionFailure as error:
                        proof["action_failure"] = deepcopy(error.feedback)
            finally:
                _live_audit(store, workflow, caller, proof)
                _live_write(proof_path, proof)

            assert len(proof["http_calls"]) == 1
            action_row, = proof["journal"]["runtime_actions"]
            assert json.loads(action_row["action"]) == selection and action_row["decision_index"] == 0
            assert action_row["run_id"] == workflow.run_id and action_row["episode_id"] == caller.source.episode_id
            outcome = json.loads(action_row["result"])
            assert caller.source.last_outcome == outcome
            receipt = outcome["result"]
            assert type(receipt) is dict and set(receipt) == RECEIPT_FIELDS
            assert type(receipt["acquired"]) is bool
            proof["native_data_acquired"] = receipt["acquired"]
            if receipt["acquired"]:
                assert outcome["status"] == "completed" and receipt["failure_code"] is None
                assert receipt["source_ref"] is not None and receipt["data_ref"] is not None
            else:
                assert outcome["status"] in {"partial", "failed", "unavailable", "invalid"}
                assert receipt["data_ref"] is None and receipt["failure_code"] in failure_codes

            capture = proof.get("http_capture")
            references, source = [], None
            if receipt["source_ref"] is not None:
                assert capture is not None and capture["service"] == spec["service"]
                assert capture["request"] == spec["params"]
                source = store.get(receipt["source_ref"])
                pin = capture["body_file"]
                assert source["provider"] == host.TOOL and source["origin"] == "external"
                assert source["version"] is source["accession"] is None
                assert source["uri"] == capture["url"] and capture["url"] in {spec["url"], address}
                assert source["artifact_ref"] == "artifact_" + pin["sha256"]
                artifact = store.get(source["artifact_ref"])
                assert artifact["sha256"] == pin["sha256"] and artifact["size"] == pin["size_bytes"] <= arguments["max_bytes"]
                retained = _live_pin(store.path / "artifacts" / artifact["sha256"][:2] / artifact["sha256"])
                assert {k: retained[k] for k in ("sha256", "size_bytes")} == {k: pin[k] for k in ("sha256", "size_bytes")}
                control = json.loads(store.get_artifact(source["request_ref"]))
                assert control["request"] == arguments
                assert canonical(control["transport"]) == canonical(capture["transport"])
                transport = control["transport"]
                assert transport["request"]["method"] == "GET" and transport["request"]["url"] == address
                assert [value for name, value in transport["request"]["headers"].items()
                    if name.lower() == "accept"] == ["application/json"]
                assert transport["request_policy"] == dict(timeout_seconds=90, automatic_redirects=False)
                assert transport["response_byte_limit"] == arguments["max_bytes"]
                references = [source["id"]]
                if receipt["acquired"]:
                    assert receipt["data_ref"] == source["artifact_ref"]
                    assert 200 <= transport["status"] < 300 and transport["status"] != 206
                    assert transport["body_complete"] is True
                    assert transport["observed_body_bytes"] == transport["retained_body_bytes"] == pin["size_bytes"]
                    references.append(source["artifact_ref"])
                proof.update(source=source, source_control=control, retained_capture_file=retained)
            else:
                assert not receipt["acquired"]
                assert not [row for row in proof["sources"] if row["record"]["provider"] == host.TOOL]
                proof["captured_response_without_published_source"] = capture is not None
            assert outcome["record_refs"] == references
            known = set(workflow.receipts.known(caller.source.episode_id))
            assert known - known_before == set(references)
            context = workflow.binding_context(caller.source)
            resolve = workflow.resolver(plain(context.scope), context=context)
            private = set()
            if source is not None:
                private.update([source["request_ref"], *source.get("auxiliary_artifact_refs", [])])
                assert resolve(source["id"], "source") is True
                assert resolve(source["artifact_ref"], "artifact") is receipt["acquired"]
            diagnostic = (outcome.get("feedback") or {}).get("diagnostic_ref")
            if diagnostic is not None:
                private.add(diagnostic)
            assert private.isdisjoint(known)
            assert all(resolve(reference, "artifact") is False for reference in private)
            episode, = proof["journal"]["runtime_episodes"]
            assert episode["state"] == "active" and episode["completion"] is episode["archive"] is None
            for name in ("runtime_observations", "runtime_model_calls", "runtime_forms", "runtime_report_attempts"):
                assert proof["journal"][name] == []
            assert proof["scientific_record_counts"] == dict(observation=0, annotation=0)
            assert caller.request.report_contract is None and workflow.episode_bindings.roles == ()
            operation_row, = proof["tool_operations"]
            saved = json.loads(operation_row["result"])
            assert operation_row["operation_key"] == key and operation_row["name"] == host.TOOL
            assert operation_row["id"] == outcome["operation_ref"] == identity("operation",
                dict(key=key, name=host.TOOL, arguments=arguments))
            assert operation_row["arguments"] == canonical(arguments) and operation_row["scope"] == canonical(scope)
            assert saved == {k: v for k, v in outcome.items() if k != "pending_work_after_action"}
            before, files = _snapshot(store), _artifacts(store.path / "artifacts")
            with monkeypatch.context() as replay:
                replay.setattr(PublicClients, "_http", _forbidden)
                replay.setattr(host, "publish_ncbi_entrez_request", _forbidden)
                replay.setattr(native, "entrez_result", _forbidden)
                replay.setattr(Store, "get_artifact", _forbidden)
                cached = asyncio.run(workflow.execute(caller.source, host.TOOL, arguments,
                    decision_index=0, operation_key=key))
            assert cached == saved and _snapshot(store) == before
            assert _artifacts(store.path / "artifacts") == files
            proof.update(invocation_check_passed=True, same_key_replay_verified=True,
                newly_received_record_refs=sorted(known - known_before), private_record_refs=sorted(private))
    except BaseException as error:
        proof["test_failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        database = store_directory / "state.sqlite3"
        if database.is_file():
            proof["database_file"] = _live_pin(database)
            proof["store_files"] = {str(p.relative_to(store_directory)): _live_pin(p)
                for p in sorted(store_directory.rglob("*")) if p.is_file()}
        _live_write(proof_path, proof)


@pytest.mark.parametrize("host_case", [captures.sra_fetch_arguments()], indirect=True)
def test_sra_docset_fetch_delivers_exact_retained_xml_file_with_ordinary_receipt(host_case):
    raw = captures.sra_native_xml()
    acquired = acquire(host_case, raw, media_type="application/xml")
    assert acquired.outcome["status"] == "completed" and acquired.receipt["acquired"] is True
    assert acquired.receipt["data_ref"] == acquired.source["artifact_ref"]
    assert acquired.outcome["record_refs"] == [acquired.source["id"], acquired.receipt["data_ref"]]
    assert host_case.store.get_artifact(acquired.receipt["data_ref"]) == raw
    request, = host_case.http.requests
    spec = native.entrez_request_spec(host_case.request)
    assert request["url"] == spec["url"] + "?" + urlencode(spec["params"])
    assert request["method"] == "GET" and request["body"] is None and request["timeout"] == 3
    assert acquired.source["provider"] == host.TOOL and acquired.source["accession"] is acquired.source["version"] is None
    control = json.loads(host_case.store.get_artifact(acquired.source["request_ref"]))
    assert control["request"] == host_case.request
    assert control["transport"]["request_policy"] == dict(timeout_seconds=3, automatic_redirects=False)
    assert acquired.source["request_ref"] not in set(host_case.workflow.receipts.known(host_case.context.episode_id))


@pytest.mark.parametrize("body,code", [
    (captures.sra_docset("", package=False), "ncbi_entrez_native_response_identity_missing"),
    (captures.sra_docset("<EXPERIMENT_PACKAGE/>", package=False), "ncbi_entrez_native_response_identity_missing"),
    (captures.sra_docset("<RUN/>"), "ncbi_entrez_native_response_identity_missing"),
    (captures.sra_docset('<RUN accession="SRR9" alias="SRR6263255"/>'), "ncbi_entrez_selected_record_identity_conflict"),
    (captures.sra_docset('<RUN accession="SRR6263255"><IDENTIFIERS><PRIMARY_ID>SRR9</PRIMARY_ID></IDENTIFIERS></RUN>'),
        "ncbi_entrez_selected_record_identity_conflict"),
    ("<TaxaSet/>", "ncbi_entrez_native_response_identity_conflict"),
    ("<ERROR>Native requested run unavailable</ERROR>", "ncbi_entrez_native_error_response"),
    ("<EXPERIMENT_PACKAGE_SET>", "ncbi_entrez_native_format_unavailable"),
])
@pytest.mark.parametrize("host_case", [captures.sra_fetch_arguments()], indirect=True)
def test_sra_fetch_cannot_promote_empty_missing_error_or_different_run_to_requested_advertisement(host_case, body, code):
    raw = body.encode()
    acquired = acquire(host_case, raw, media_type="application/xml")
    assert acquired.receipt == dict(acquired=False, source_ref=acquired.source["id"], data_ref=None, failure_code=code)
    assert acquired.outcome["status"] == "partial" and acquired.outcome["record_refs"] == [acquired.source["id"]]
    assert host_case.store.get_artifact(acquired.source["artifact_ref"]) == raw and len(host_case.http.requests) == 1
    known = set(host_case.workflow.receipts.known(host_case.context.episode_id))
    assert acquired.source["id"] in known and acquired.source["artifact_ref"] not in known


@pytest.mark.parametrize("host_case", [captures.sra_fetch_arguments()], indirect=True)
def test_sra_fetch_retains_related_sibling_and_duplicate_runs_without_selecting_their_files(host_case):
    raw = captures.sra_docset('<RUN accession="SRR9"/><RUN accession="SRR6263255"/>'
        '<RUN accession="SRR6263255" unknown="literal"/>').encode()
    acquired = acquire(host_case, raw, media_type="application/xml")
    assert acquired.receipt["acquired"] is True and acquired.outcome["status"] == "completed"
    assert host_case.store.get_artifact(acquired.receipt["data_ref"]) == raw
    assert set(acquired.receipt) == RECEIPT_FIELDS and len(host_case.http.requests) == 1


def _sra_chain_transport(monkeypatch):
    """Only fake HTTPS replies; both actual selected ordinary getters execute."""
    http = HTTP()
    monkeypatch.setattr(urllib.request, "build_opener", lambda *handlers: http)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    monkeypatch.setattr("gene_annotation_episode.providers._SessionConnection._rpc", forbidden)
    monkeypatch.setattr(ToolRegistry, "_sequence_worker_async", forbidden)
    return http


def test_current_episode_selected_docset_fetch_supplies_actual_own_action_file_for_sra_download_and_cache(tmp_path, monkeypatch):
    from gene_annotation_episode import ncbi_sra_acquisition as sra
    from gene_annotation_episode import ncbi_sra_acquisition_host as sra_host
    from test_ncbi_sra_acquisition import ENGINEERED, engineered
    http = _sra_chain_transport(monkeypatch)
    xml, file_arguments, _ = engineered()
    fetch_arguments = captures.sra_fetch_arguments(max_bytes=4096)
    http.add(xml, media_type="application/xml")
    http.add(ENGINEERED, media_type="application/octet-stream")
    with Store(tmp_path / "store") as store:
        scope = {"subject_refs": store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]}
        tools, session = ToolRegistry(store, clients=PublicClients(timeout=3)), _snp_session(tmp_path / "session")
        goal = ("Assess the supplied sequencing evidence. Acquire the selected experiment-package metadata "
            "and separately selected advertised file for later decoding. Retrieval establishes no biological conclusion.")
        holder = {}
        def select_advertised_file(context):
            receipt = context["last_local_outcome"]["result"]
            assert receipt["acquired"] is True and receipt["data_ref"] == file_arguments["advertisement_file"]["artifact_ref"]
            workflow, root = holder["workflow"], holder["root"]
            binding = workflow.binding_context(root.source)
            metadata = workflow.services.read_received_molecular_file_metadata(binding, receipt["data_ref"], "artifact",
                file_format=sra.ADVERTISEMENT_FORMAT)
            assert metadata["file"] == file_arguments["advertisement_file"] and metadata["byte_verification"] == "unavailable"
            row = store.db.execute("SELECT receipt_kind,source_index FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=?",
                (workflow.run_id, binding.episode_id, receipt["data_ref"])).fetchone()
            assert tuple(row) == ("own_action", 0)
            return action(sra.TOOL, file_arguments)
        actor = _SnpProvider([action(host.TOOL, fetch_arguments), select_advertised_file], session)
        directory = tmp_path / "workflow"
        workflow = Workflow(store, tools, actor, directory, "ordinary-sra-metadata-then-file", _snp_controller, _credit,
            project_child_credit=_credit, root_role="improvement", episode_binding_factories=(),
            episode_record_receipts=True, initial_known_record_refs=[])
        root = workflow.build("improvement", "root", goal, scope)
        holder.update(workflow=workflow, root=root)
        baseline = set(workflow.receipts.known(root.source.episode_id))
        assert file_arguments["advertisement_file"]["artifact_ref"] not in baseline
        record = asyncio.run(root.run_async(workflow.context))
        final = asyncio.run(root.build_result(record)).as_record()
        operations = {row["name"]: (row["operation_key"], json.loads(row["result"])) for row in store.db.execute("SELECT * FROM tool_operations")}
        assert set(operations) == {host.TOOL, sra.TOOL}
        fetch_key, fetched = operations[host.TOOL]
        file_key, acquired = operations[sra.TOOL]
        assert fetch_key.endswith(":0") and file_key.endswith(":1")
        assert fetched["status"] == acquired["status"] == "completed"
        metadata_source, data_source = store.get(fetched["result"]["source_ref"]), store.get(acquired["result"]["source_ref"])
        assert store.get_artifact(metadata_source["artifact_ref"]) == xml
        assert store.get_artifact(data_source["artifact_ref"]) == ENGINEERED
        assert data_source["accession"] is data_source["version"] is None and data_source["parent_source_refs"] == []
        evidence = json.loads(store.get_artifact(data_source["auxiliary_artifact_refs"][0]))
        admission = evidence["prepared"]["input"]["admission"]
        assert admission["baseline"] is False and admission["file_receipt"]["receipt_kind"] == "own_action"
        assert admission["file_receipt"]["source_index"] == 0
        assert evidence["prepared"]["invocation"]["decision_index"] == 1
        assert evidence["evidence"]["value"]["checks"]["archive_identity"] == "not_parsed"
        assert len(http.requests) == 2 and http.planned == []
        specification = native.entrez_request_spec(fetch_arguments)
        assert http.requests[0]["url"] == specification["url"] + "?" + urlencode(specification["params"])
        assert http.requests[1]["url"] == file_arguments["url"]
        assert [row["method"] for row in http.requests] == ["GET", "GET"]
        binding = workflow.binding_context(root.source)
        known = set(workflow.receipts.known(binding.episode_id))
        assert known == baseline | set(fetched["record_refs"]) | set(acquired["record_refs"])
        resolve = workflow.resolver(plain(binding.scope), context=binding)
        for source in [metadata_source, data_source]:
            assert resolve(source["id"], "source") is True and resolve(source["artifact_ref"], "artifact") is True
            for private in [source["request_ref"], *source.get("auxiliary_artifact_refs", [])]:
                assert private not in known and resolve(private, "artifact") is False
        calls = list(store.db.execute("SELECT request,response FROM runtime_model_calls ORDER BY call_index"))
        assert len(calls) == len(actor.dispatches) == 2
        for call, dispatched in zip(calls, actor.dispatches):
            assert call["response"] is not None and json.loads(call["request"])["context"] == dispatched["context"]
            assert json.loads(dispatched["wire"]) == dispatched["context"]
            assert goal in json.dumps(dispatched["context"]["goal"]) and dispatched["context"]["requested_form"] is None
        assert store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 2
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 2
        assert store.db.execute("SELECT count(*) FROM runtime_forms").fetchone()[0] == 0
        for source in [metadata_source, data_source]:
            sha = source["artifact_ref"].removeprefix("artifact_")
            (store.path / "artifacts" / sha[:2] / sha).unlink()
        before, files, archives = _tables(store), _artifacts(store.path / "artifacts"), _artifacts(directory / "archive")
        monkeypatch.setattr(PublicClients, "_http", forbidden)
        monkeypatch.setattr(host, "publish_ncbi_entrez_request", forbidden)
        monkeypatch.setattr(native, "entrez_result", forbidden)
        monkeypatch.setattr(sra_host, "retained_native_file", forbidden)
        monkeypatch.setattr(sra_host, "read_bytes", forbidden)
        monkeypatch.setattr(sra, "resolve_sra_file_selection", forbidden)
        actual_get = Store.get_artifact
        def private_only(current, reference):
            assert reference not in {metadata_source["artifact_ref"], data_source["artifact_ref"]}
            return actual_get(current, reference)
        monkeypatch.setattr(Store, "get_artifact", private_only)
        assert asyncio.run(workflow.execute(root.source, host.TOOL, fetch_arguments, decision_index=0, operation_key=fetch_key)) == fetched
        assert asyncio.run(workflow.execute(root.source, sra.TOOL, file_arguments, decision_index=1, operation_key=file_key)) == acquired
        assert _tables(store) == before and _artifacts(store.path / "artifacts") == files
        monkeypatch.setattr(ToolRegistry, "execute_async", forbidden)
        replay_actor = ScriptedProvider([])
        replay = Workflow(store, tools, replay_actor, directory, workflow.run_id, _snp_controller, _credit,
            project_child_credit=_credit, root_role="improvement", episode_binding_factories=(),
            episode_record_receipts=True, initial_known_record_refs=[])
        restored = replay.build("improvement", "root", goal, scope)
        restored_record = asyncio.run(restored.run_async(replay.context))
        assert asyncio.run(restored.build_result(restored_record)).as_record() == final
        assert replay_actor.contexts == [] and len(http.requests) == 2
        assert _tables(store) == before and _artifacts(store.path / "artifacts") == files
        assert _artifacts(directory / "archive") == archives


def test_later_real_docset_file_receipt_cannot_backfill_an_earlier_denied_sra_action(tmp_path, monkeypatch):
    from gene_annotation_episode import ncbi_sra_acquisition as sra
    from gene_annotation_episode import ncbi_sra_acquisition_host as sra_host
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    from gene_annotation_episode.runtime import ActionFailure
    from test_molecular_acquisition_ordinary import NoModel, _neutral_bookkeeping
    from test_ncbi_sra_acquisition import engineered
    http = _sra_chain_transport(monkeypatch)
    xml, file_arguments, _ = engineered()
    fetch_arguments = captures.sra_fetch_arguments(max_bytes=4096)
    http.add(xml, media_type="application/xml")
    with Store(tmp_path / "store") as store:
        artifact = store.artifact(xml, "application/xml")
        assert artifact == file_arguments["advertisement_file"]["artifact_ref"]
        scope = {"subject_refs": store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]}
        tools = ToolRegistry(store, clients=PublicClients(timeout=3))
        workflow = Workflow(store, tools, NoModel(), tmp_path / "workflow", "sra-original-action-cutoff", forbidden,
            _neutral_bookkeeping, root_role="improvement", episode_binding_factories=(),
            episode_record_receipts=True, initial_known_record_refs=[])
        root = workflow.build("improvement", "root", "Retain selected sequencing inputs for later analysis.", scope)
        with pytest.raises(ActionFailure):
            asyncio.run(root.source.execute(dict(kind="tool", tool=sra.TOOL, arguments=file_arguments), 0))
        first = deepcopy(root.source.last_outcome)
        assert first["status"] == "invalid" and first["result"]["failure_code"] == "sra_file_input_not_received"
        assert http.requests == []
        asyncio.run(root.source.execute(dict(kind="tool", tool=host.TOOL, arguments=fetch_arguments), 1))
        assert root.source.last_outcome["result"]["acquired"] is True and len(http.requests) == 1
        context = workflow.binding_context(root.source)
        current = workflow.services.read_received_molecular_file_metadata(context, artifact, "artifact", file_format=sra.ADVERTISEMENT_FORMAT)
        assert current["file"] == file_arguments["advertisement_file"] and current["byte_verification"] == "unavailable"
        row = store.db.execute("SELECT receipt_kind,source_index FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=?",
            (workflow.run_id, context.episode_id, artifact)).fetchone()
        assert tuple(row) == ("own_action", 1)
        calls, original = [], EpisodeReturnRecords.file_admission_before
        def original_cutoff(records, receiving, reference, namespace, artifact_ref, cutoff):
            calls.append((reference, namespace, artifact_ref, cutoff))
            return original(records, receiving, reference, namespace, artifact_ref, cutoff)
        monkeypatch.setattr(EpisodeReturnRecords, "file_admission_before", original_cutoff)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        monkeypatch.setattr(PublicClients, "_http", forbidden)
        monkeypatch.setattr(sra_host, "retained_native_file", forbidden)
        monkeypatch.setattr(sra_host, "read_bytes", forbidden)
        monkeypatch.setattr(sra, "resolve_sra_file_selection", forbidden)
        before, files = _tables(store), _artifacts(store.path / "artifacts")
        denied = asyncio.run(workflow.execute(root.source, sra.TOOL, file_arguments, decision_index=0,
            operation_key=f"{workflow.run_id}:{context.episode_id}:0"))
        assert denied["status"] == "invalid" and denied["result"] == dict(acquired=False, source_ref=None,
            data_ref=None, failure_code="sra_file_input_not_received")
        assert calls == [(artifact, "artifact", artifact, 0)]
        assert _tables(store) == before and _artifacts(store.path / "artifacts") == files
        assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 2
        assert store.db.execute("SELECT count(*) FROM runtime_model_calls").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
