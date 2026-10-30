"""Direct Minhash service and durable publication; no live BV-BRC calls.

Responses are synthetic native-format fixtures. The controlled HTTP test uses
the actual urllib transport. Executor tests exercise existing selected-action
custody but bind the service directly; root-owned dispatch/communication is a
separate integration claim.
"""
import asyncio
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
import socket
from types import SimpleNamespace

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, SourceSnapshot
from gene_annotation_episode import api_bvbrc_minhash as module
from gene_annotation_episode.api_bvbrc_minhash import (
    BVBRCMinhashService, GRADING_SCHEMA, LAUNCH_OPERATIONS, RESULT_OPERATION, SERVICE,
)
from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import source_tool_gradings
from gene_annotation_episode.tools import ToolRegistry
from test_bvbrc_analysis_transport import server
from test_execution_episodes_family import context, select


ENDPOINT = "https://minhash.example.invalid/native/rpc"
CONFIGURATION = {"kind": "api", "service": SERVICE, "endpoint": ENDPOINT}
UPSTREAM_VALUES = ["0.12101", "4.48626e-214", "41/1000"]


@pytest.fixture(autouse=True)
def no_external_connections(monkeypatch):
    connect = socket.create_connection

    def local_only(address, *args, **kwargs):
        assert address[0] == "127.0.0.1", "No live service calls are permitted"
        return connect(address, *args, **kwargs)

    monkeypatch.setattr(socket, "create_connection", local_only)


def request(mode="genome", **changes):
    return {"mode": mode, "query": ("511145.12" if mode == "genome"
            else "/synthetic-owner/workspace/input.fa"),
        "max_pvalue": .2, "max_distance": 1, "max_hits": 10,
        "include_reference": 1, "include_representative": 0,
        "bacterial": 1, "viral": 0, **changes}


def rpc_snapshot(rpc, rows, *, endpoint=ENDPOINT):
    sent = json.dumps(rpc, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()
    body = json.dumps({"version": "1.1", "id": rpc["id"], "result": [rows]}).encode()
    return SourceSnapshot("bvbrc_analysis", endpoint, {"kind": "rpc", "rpc": deepcopy(rpc)},
        "2026-10-24T12:00:00+00:00", body, "application/json", {
            "status": 200, "body_complete": True,
            "request": {"method": "POST", "url": endpoint,
                "body_bytes": len(sent), "body_sha256": hashlib.sha256(sent).hexdigest(),
                "headers": [["Content-Type", "application/json"]]},
            "representation": "synthetic_native_rpc_response",
            "duration_measure": "client_http_request_turnaround",
            "http_turnaround_seconds": .125})


class Client:
    def __init__(self, rows=None, *, endpoint=ENDPOINT):
        self.rows = [["synthetic-reference", *UPSTREAM_VALUES]] if rows is None else rows
        self.endpoint = endpoint
        self.calls = []

    def rpc(self, rpc):
        self.calls.append(deepcopy(rpc))
        return rpc_snapshot(rpc, self.rows, endpoint=self.endpoint)


@pytest.fixture
def harness(tmp_path):
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
        client = Client()
        tools = ToolRegistry(store, clients=client)
        service = BVBRCMinhashService(tools, CONFIGURATION, client=client)
        yield SimpleNamespace(store=store, tools=tools, service=service, client=client,
            scope=store.validate_scope(None), tmp_path=tmp_path,
            initial_source_count=store.count("source"))


def launch(h, original):
    prepared = h.service.prepare(LAUNCH_OPERATIONS[original["mode"]], original, {},
        scope=h.scope, previous_events=[])
    return prepared, h.service.invoke(prepared)


@pytest.mark.parametrize("mode", ["genome", "fasta"])
def test_exact_assigned_eight_arguments_and_immediate_response(harness, mode):
    h = harness
    original = request(mode, max_pvalue=0, max_distance=0.5, max_hits=0,
        include_reference=-2, include_representative=3, bacterial=0, viral=7)
    before = deepcopy(original)
    prepared, snapshot = launch(h, original)
    assert original == before and prepared["request"] == original
    assert prepared["rpc_request"]["params"] == [original["query"], 0, .5, 0, -2, 3, 0, 7]
    assert prepared["rpc_request"]["version"] == "1.1"
    assert prepared["rpc_request"]["method"].endswith("for_" + mode + "2")
    repeated = h.service.prepare(LAUNCH_OPERATIONS[mode], original, {},
        scope=h.scope, previous_events=[])
    assert repeated == prepared and len(h.client.calls) == 1
    assert prepared["mutates_remote"] is True and prepared["cache_original"] is False
    assert h.service.launch_catalog(original) == [next(row for row in h.service.capabilities()
        if row["name"] == LAUNCH_OPERATIONS[mode])]
    event = h.service.decode(prepared, snapshot)
    assert event == {"kind": "response", "state": "completed", "native_handle": {},
        "handoff_ready": True, "result_available": True, "failure_code": None,
        "facts": {"mode": mode, "returned_row_count": 1,
            "population_size": None, "truncated": None}}
    result = h.service.prepare(RESULT_OPERATION, original, {}, scope=h.scope,
        previous_events=[], handle={}, selector={})
    assert result["rpc_request"] == prepared["rpc_request"]
    assert result["cache_original"] is True and result["mutates_remote"] is False
    with pytest.raises(ValueError, match="original_response_required"):
        h.service.invoke(result)
    assert h.service.prepare_observation(original, {}, scope=h.scope) is None
    assert len(h.client.calls) == 1


@pytest.mark.parametrize("field", list(request()))
def test_every_assignment_field_required_no_native_defaults(harness, field):
    original = request()
    original.pop(field)
    with pytest.raises(ValueError):
        harness.service.validate_request(original, harness.scope)
    assert harness.client.calls == []


@pytest.mark.parametrize("changes", [
    {"extra": 1}, {"mode": "sra"}, {"query": "named-genome"},
    {"max_pvalue": "0.1"}, {"max_pvalue": True}, {"max_distance": float("nan")},
    {"max_distance": float("inf")}, {"max_distance": -1}, {"max_pvalue": 2},
    {"max_hits": -1}, {"max_hits": 2.0}, {"include_reference": False},
    {"include_representative": 1.0}, {"bacterial": "1"}, {"viral": None},
])
def test_invalid_native_assignment_values_do_not_reach_transport(harness, changes):
    with pytest.raises(ValueError):
        harness.service.validate_request(request(**changes), harness.scope)
    assert harness.client.calls == []


@pytest.mark.parametrize("query", [
    ">query\nACGT", "input.fa", "https://example.invalid/input.fa", "/tmp/input.fa",
    "/owner/workspace/../input.fa", "/owner//input.fa", "/owner/workspace/input.fa/",
    "00000000-0000-0000-0000-000000000000",
])
def test_fasta_requires_selected_workspace_path(harness, query):
    with pytest.raises(ValueError, match="workspace_fasta_path_required"):
        harness.service.validate_request(request("fasta", query=query), harness.scope)
    assert harness.client.calls == []


@pytest.mark.parametrize("configuration", [
    None, {}, {**CONFIGURATION, "endpoint": None}, {**CONFIGURATION, "endpoint": "file:///tmp/rpc"},
    {**CONFIGURATION, "endpoint": "https://user:password@example.invalid/rpc"},
    {**CONFIGURATION, "endpoint": ENDPOINT + "?alternate=1"},
    {**CONFIGURATION, "kind": "local"}, {**CONFIGURATION, "service": "bvbrc_data"},
    {**CONFIGURATION, "default_max_hits": 5}, {**CONFIGURATION, "timeout": False},
    {**CONFIGURATION, "authorization_env": "not an environment name"},
    {**CONFIGURATION, "authorization_origins": ["https://example.invalid/other"]},
])
def test_configuration_validation_even_with_supplied_client(configuration):
    client = Client()
    with pytest.raises(ValueError):
        BVBRCMinhashService(None, configuration, client=client)
    assert client.calls == []


def test_action_arguments_mode_selector_and_handle_cannot_replace_assignment(harness):
    h = harness
    cases = [("api.bvbrc.minhash.fasta", {}, {}),
        (LAUNCH_OPERATIONS["genome"], {"max_hits": 3}, {}),
        (RESULT_OPERATION, {}, {"selector": {"max_hits": 3}}),
        (RESULT_OPERATION, {}, {"selector": None}),
        (RESULT_OPERATION, {}, {"selector": {}, "handle": {"task_id": "7"}})]
    for name, arguments, extra in cases:
        with pytest.raises(ValueError):
            h.service.prepare(name, request(), arguments, scope=h.scope,
                previous_events=[], **extra)
    with pytest.raises(ValueError):
        h.service.prepare_observation(request(), {"task_id": "7"}, scope=h.scope)
    assert h.client.calls == []


@pytest.mark.parametrize("mutation,code", [
    ("service", "response_service_mismatch"), ("kind", "rpc_response_required"),
    ("rpc", "response_request_mismatch"), ("endpoint", "response_endpoint_mismatch"),
    ("incomplete", "response_body_incomplete"), ("unknown_complete", "response_body_incomplete"),
    ("body_digest", "transport_request_mismatch"), ("http", "http_error"),
    ("unknown_http", "invalid_http_status"), ("correlation", "response_id_mismatch"),
    ("version", "missing_rpc_version"), ("native_error", "ambiguous_result_error"),
    ("arity", "wrong_result_arity"), ("nonarray", "native_result_array_required"),
    ("html", "invalid_json"), ("duplicate_key", "duplicate_json_member"),
])
def test_decode_rejects_wrong_or_incomplete_native_envelopes(harness, mutation, code):
    prepared, original = launch(harness, request())
    fields = asdict(original)
    body = json.loads(fields["content"])
    if mutation == "service":
        fields["service"] = SERVICE
    elif mutation == "kind":
        fields["request"]["kind"] = "download"
    elif mutation == "rpc":
        fields["request"]["rpc"]["params"][1] = 1
    elif mutation == "endpoint":
        fields["url"] = "https://other.example.invalid/rpc"
    elif mutation == "incomplete":
        fields["transport"]["body_complete"] = False
    elif mutation == "unknown_complete":
        fields["transport"].pop("body_complete")
    elif mutation == "body_digest":
        fields["transport"]["request"]["body_sha256"] = "0" * 64
    elif mutation == "http":
        fields["transport"]["status"] = 403
    elif mutation == "unknown_http":
        fields["transport"].pop("status")
    elif mutation == "correlation":
        body["id"] = "other-call"
    elif mutation == "version":
        body.pop("version")
    elif mutation == "native_error":
        body["error"] = {"code": -1, "message": "synthetic error"}
    elif mutation == "arity":
        body["result"].append([])
    elif mutation == "nonarray":
        body["result"] = [{"task_id": "7"}]
    fields["content"] = json.dumps(body).encode()
    if mutation == "html":
        fields["content"] = b"<html>Access denied</html>"
    elif mutation == "duplicate_key":
        fields["content"] = fields["content"][:-1] + b',"result":[[]]}'
    changed = SourceSnapshot(**fields)
    event = harness.service.decode(prepared, changed)
    assert event["state"] == "failed" and code in event["failure_code"]
    assert not event["handoff_ready"] and not event["result_available"]
    with pytest.raises(ValueError, match=code):
        harness.service.publish(request(), {}, changed, harness.scope, "invalid-response")
    assert harness.store.count("source") == harness.initial_source_count


def test_decode_accepts_native_2_0_and_leaves_row_errors_for_parser(harness):
    h = harness
    h.client.rows = [None, ["synthetic-reference", "bad", "0.1", "2/3"]]
    prepared, snapshot = launch(h, request())
    body = json.loads(snapshot.content)
    body.pop("version")
    body["jsonrpc"] = "2.0"
    snapshot = replace(snapshot, content=json.dumps(body).encode())
    assert h.service.decode(prepared, snapshot)["state"] == "completed"
    published = h.service.publish(request(), {}, snapshot, h.scope, "partial-publication")
    assert published["status"] == "partial"
    assert published["result"]["parse_status"] == "partial"
    assert published["result"]["projection_errors"]
    grading, = source_tool_gradings(h.store, published["result"]["source_ref"])
    assert grading["sheet"]["native_result"] == h.client.rows
    assert grading["sheet"]["rows"][0]["genome_id"] is None
    assert grading["components"]["rows"][1]["shared_hash_fraction"] == 2 / 3
    assert grading["components"]["rows"][1]["reported_distance"] is None


@pytest.mark.parametrize("mode", ["genome", "fasta"])
def test_publication_keeps_full_native_bytes_exact_request_and_numerical_sheet(harness, mode):
    h = harness
    h.client.rows.append(["synthetic-reference", "0.2", "0.1", "2/3"])
    original = request(mode, query="/owner/workspace/\u03b1.fa") if mode == "fasta" else request()
    prepared, snapshot = launch(h, original)
    published = h.service.publish(original, {}, snapshot, h.scope, "publish")
    assert published["status"] == "completed"
    assert set(published["result"]) == {"source_ref", "raw_artifact_ref",
        "grading_artifact_ref", "parse_status"}
    source = h.store.get(published["result"]["source_ref"])
    assert source["provider"] == SERVICE
    assert source["auxiliary_artifact_refs"] == [published["result"]["grading_artifact_ref"]]
    assert h.store.get_artifact(source["artifact_ref"]) == snapshot.content
    retained = json.loads(h.store.get_artifact(source["request_ref"]))
    assert retained["transport"] == snapshot.transport
    assert retained["request"] == snapshot.request
    sent = h.store.get_artifact(retained["rpc_request_artifact_ref"])
    assert json.loads(sent) == prepared["rpc_request"]
    assert hashlib.sha256(sent).hexdigest() == snapshot.transport["request"]["body_sha256"]
    grading, = source_tool_gradings(h.store, source["id"])
    assert set(grading) == {"schema", "request", "rpc_request", "selector", "parse_status",
        "sheet", "components", "diagnostics"}
    assert grading["schema"] == GRADING_SCHEMA and grading["selector"] == {}
    assert grading["request"] == original
    assert grading["rpc_request"] == prepared["rpc_request"] == grading["sheet"]["request"]
    assert grading["sheet"]["native_result"] == h.client.rows
    rows = grading["components"]["rows"]
    assert [row["row_index"] for row in rows] == [0, 1]
    assert rows[0]["reported_distance"] == .12101
    assert rows[0]["reported_pvalue"] == 4.48626e-214
    assert rows[0]["shared_hash_fraction"] == .041
    for row in rows:
        assert row["recomputed_distance"] is None and row["recomputed_pvalue"] is None
        assert row["calculation_inputs"]["pair_metadata"] is None
        assert any(issue["code"] == "pair_metadata_missing" for issue in row["diagnostics"])
    assert grading["sheet"]["search_metadata"]["population_size"] is None
    assert grading["sheet"]["search_metadata"]["truncated"] is None
    assert h.store.count("source") == h.initial_source_count + 1
    assert h.store.count("annotation") == h.store.count("observation") == 0
    assert len(h.client.calls) == 1


@pytest.mark.parametrize("rows,status,parse_status", [
    ([], "completed", "ok"), ([None], "partial", "invalid"),
    ([[None, "bad", False, None]], "partial", "invalid"),
    ([["synthetic-reference", 0, 1, "0/0"]], "completed", "ok"),
    ([["synthetic-reference", 0, 1, "4/3"]], "partial", "partial"),
])
def test_empty_invalid_and_zero_denominator_rows_remain_distinct(harness, rows, status, parse_status):
    h = harness
    h.client.rows = rows
    prepared, snapshot = launch(h, request())
    assert h.service.decode(prepared, snapshot)["state"] == "completed"
    published = h.service.publish(request(), {}, snapshot, h.scope, "boundary")
    assert published["status"] == status
    assert published["result"]["parse_status"] == parse_status
    grading, = source_tool_gradings(h.store, published["result"]["source_ref"])
    assert grading["sheet"]["native_result"] == rows
    assert len(grading["sheet"]["rows"]) == len(rows)
    assert all(row["shared_hash_fraction"] is None for row in grading["components"]["rows"])
    if not rows:
        assert any(item["code"] == "empty_result_completeness_unknown"
            for item in grading["diagnostics"])
    if rows == [["synthetic-reference", 0, 1, "0/0"]]:
        assert grading["components"]["rows"][0]["reported_distance"] == 0
        assert grading["components"]["rows"][0]["reported_pvalue"] == 1


def test_publication_replay_precedes_readers_calculators_and_preserves_identity(harness, monkeypatch):
    h = harness
    _, snapshot = launch(h, request())
    published = h.service.publish(request(), {}, snapshot, h.scope, "same-operation")
    original_count = h.store.count("source")
    original_grading = h.store.get_artifact(published["result"]["grading_artifact_ref"])

    def prohibited(*args, **kwargs):
        raise AssertionError("Saved publication must not acquire, parse or regrade")

    monkeypatch.setattr(module, "parse_minhash_result", prohibited)
    monkeypatch.setattr(module, "calculate_minhash_components", prohibited)
    monkeypatch.setattr(h.service, "_native_response", prohibited)
    monkeypatch.setattr(h.client, "rpc", prohibited)
    assert h.service.publish(request(), {}, snapshot, h.scope, "same-operation") == published
    assert h.store.count("source") == original_count
    assert h.store.get_artifact(published["result"]["grading_artifact_ref"]) == original_grading
    with pytest.raises(ValueError, match="operation_key_reused_for_different_work"):
        h.service.publish(request(max_hits=11), {}, snapshot, h.scope, "same-operation")
    with pytest.raises(ValueError, match="operation_key_reused_for_different_work"):
        h.service.publish(request(), {}, replace(snapshot,
            retrieved_at="2026-10-24T12:01:00+00:00"), h.scope, "same-operation")


def test_actual_published_envelope_supplies_only_requested_saved_facts(harness, monkeypatch):
    from gene_annotation_episode.bvbrc_minhash_views import project_minhash_facts

    h = harness
    h.client.rows = [["511145.12", *UPSTREAM_VALUES],
        ["511145.12", "bad-distance", "0.1", "2/3"], None]
    _, snapshot = launch(h, request())
    published = h.service.publish(request(), {}, snapshot, h.scope, "projection-input")
    source_ref = published["result"]["source_ref"]
    grading, = source_tool_gradings(h.store, source_ref)

    def prohibited(*args, **kwargs):
        raise AssertionError("Projection copies original saved numbers without regrading")

    monkeypatch.setattr(module, "parse_minhash_result", prohibited)
    monkeypatch.setattr(module, "calculate_minhash_components", prohibited)
    qualified = [{"source_ref": source_ref, "grading": grading}]
    counts = project_minhash_facts(qualified, requested_sources=["bvbrc_minhash_counts"])
    assert counts == {"bvbrc_minhash_counts": [{"source_ref": source_ref,
        "returned_row_count": 3, "parse_status": "partial",
        "population_size": None, "truncated": None}]}
    matches = project_minhash_facts(qualified, requested_sources=["bvbrc_minhash_matches"])
    assert set(matches) == {"bvbrc_minhash_matches"}
    rows = matches["bvbrc_minhash_matches"]
    assert [row["row_index"] for row in rows] == [0, 1, 2]
    assert [row["genome_id"] for row in rows] == ["511145.12", "511145.12", None]
    assert rows[0]["shared_hash_fraction"] == .041 and rows[0]["parse_status"] == "ok"
    assert rows[1]["reported_distance"] is None and rows[1]["shared_hash_fraction"] == 2 / 3
    assert rows[1]["parse_status"] == "partial" and rows[2]["parse_status"] == "invalid"
    assert len(h.client.calls) == 1


@pytest.mark.parametrize("mode", ["genome", "fasta"])
def test_controlled_http_uses_one_exact_rpc_and_original_result(harness, mode):
    h = harness
    original = request(mode)
    prepared = h.service.prepare(LAUNCH_OPERATIONS[mode], original, {},
        scope=h.scope, previous_events=[])
    response = rpc_snapshot(prepared["rpc_request"], h.client.rows).content
    with server(response, headers={"Content-Type": "application/json"}) as (url, calls):
        service = BVBRCMinhashService(h.tools, {**CONFIGURATION, "endpoint": url + "/rpc"})
        snapshot = service.invoke(prepared)
        assert service.decode(prepared, snapshot)["handoff_ready"]
        published = service.publish(original, {}, snapshot, h.scope, "controlled-http")
        assert service.publish(original, {}, snapshot, h.scope, "controlled-http") == published
        assert service.prepare_observation(original, {}, scope=h.scope) is None
        assert len(calls) == 1 and calls[0]["method"] == "POST"
        assert json.loads(calls[0]["body"]) == prepared["rpc_request"]
        source = h.store.get(published["result"]["source_ref"])
        retained = json.loads(h.store.get_artifact(source["request_ref"]))
        assert h.store.get_artifact(retained["rpc_request_artifact_ref"]) == calls[0]["body"]


@pytest.fixture
def executor(harness, monkeypatch):
    h = harness
    # This isolates the C4b APIServicePrimitive boundary. Shared production
    # dispatch and receiver-specific facts belong to the separate C4d tests.
    monkeypatch.setattr("gene_annotation_episode.api_services.build_service",
        lambda service, configuration, tools: h.service)
    h.journal = Journal(h.store, "minhash-service-fixture")
    h.family = APIServiceExecution(h.store, run_id=h.journal.run_id,
        directory=h.tmp_path / "run", configuration={"minhash": CONFIGURATION},
        tool_registry=h.tools, handoff_unit=3, acquired_record_unit=2)
    return h


def launch_context(h, episode_id="launch"):
    assigned = {"version": "api_service_assignment_v1", "resource_id": "minhash",
        "service": SERVICE, "request": request(), "endpoint": "usable_handoff", "constraints": {}}
    return context(h, "launch_api", assigned, episode_id)


def test_executor_custody_original_observation_result_and_publication_recovery(executor, monkeypatch):
    h = executor
    launch_ctx = launch_context(h)
    launched = select(h, launch_ctx, 0, LAUNCH_OPERATIONS["genome"])
    assert launched["status"] == "completed", launched
    handoff, = launched["record_refs"]
    target = h.family.read_target(handoff, h.scope)
    assert target["execution_id"].startswith("request:")
    observed = h.family.observe_target(target, operation_key="observation")
    assert observed["state"] == "completed" and observed["native"]["handle"] == {}
    assert observed["observed_at"] == "2026-10-24T12:00:00+00:00"
    results = context(h, "results", {"version": "execution_results_assignment_v1",
        "handoff_ref": handoff, "selector": {}}, "results")
    original_index = h.family._index_result
    first = True

    def interrupt_once(*args):
        nonlocal first
        if first:
            first = False
            raise asyncio.CancelledError()
        return original_index(*args)

    monkeypatch.setattr(h.family, "_index_result", interrupt_once)
    with pytest.raises(asyncio.CancelledError):
        select(h, results, 0, RESULT_OPERATION)
    count = h.store.count("source")

    def prohibited(*args, **kwargs):
        raise AssertionError("Recovery must use the already committed publication")

    monkeypatch.setattr(module, "parse_minhash_result", prohibited)
    monkeypatch.setattr(module, "calculate_minhash_components", prohibited)
    key = f"{results.run_id}:{results.episode_id}:0"
    published = asyncio.run(h.family.execute(results, RESULT_OPERATION, {}, key))
    assert published["status"] == "completed", published
    with h.store.transaction():
        h.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? "
            "AND decision_index=0", (canonical(published), results.run_id, results.episode_id))
    assert h.store.count("source") == count and len(h.client.calls) == 1
    acquired = h.family.read_result(published["result"]["source_ref"], h.scope)
    assert acquired["source_ref"] == published["result"]["source_ref"]
    assert acquired["service_request"] == request()
    assert h.family.completion_for_action(results, key) is not None
    assert asyncio.run(h.family.execute(results, RESULT_OPERATION, {}, key)) == published
    assert len(h.client.calls) == 1


def test_executor_unknown_call_is_never_retried_or_replaced(executor, monkeypatch):
    h = executor
    launch_ctx = launch_context(h)

    def lost_response(rpc):
        h.client.calls.append(deepcopy(rpc))
        raise AcquisitionError("synthetic_lost_reply", phase="http_request", submission_outcome="unknown")

    monkeypatch.setattr(h.client, "rpc", lost_response)
    failed = select(h, launch_ctx, 0, LAUNCH_OPERATIONS["genome"])
    assert failed["status"] == "failed"
    assert failed["feedback"]["submission_outcome"] == "unknown"
    key = f"{launch_ctx.run_id}:{launch_ctx.episode_id}:0"
    assert asyncio.run(h.family.execute(launch_ctx, LAUNCH_OPERATIONS["genome"], {}, key)) == failed
    replacement = select(h, launch_ctx, 1, LAUNCH_OPERATIONS["genome"])
    assert replacement["status"] == "invalid"
    assert replacement["feedback"]["code"] == "api_original_submission_already_exists"
    assert len(h.client.calls) == 1


_METADATA_FIELDS = ("kmer_length", "query_length", "reference_length", "alphabet_size")


def explicit_pair_inputs(h, original, *, values=None, row_index=0, genome_id="511145.12"):
    """Synthetic caller data; service tests do not establish episode custody."""
    values = {"kmer_length": 1, "query_length": 2, "reference_length": 2, "alphabet_size": 2} if values is None else values
    material = h.store.register_material(data=canonical(values).encode(),
        name="synthetic-explicit-pair-inputs", format="opaque")
    source = h.store.get(material["source_ref"])
    evidence = [{"field": name, "source_ref": source["id"], "artifact_ref": source["artifact_ref"],
        "record_path": "/" + name} for name in _METADATA_FIELDS if values[name] is not None]
    metadata = {"row_index": row_index, "genome_id": genome_id, **deepcopy(values), "provenance": {
        "kind": "explicit_retained_pair_inputs", "query_mode": original["mode"],
        "query_operand": original["query"], "native_parameter_equivalence": "unestablished", "fields": evidence}}
    return material, metadata


def selected_inputs(metadata, *, saved=None):
    records = deepcopy(metadata)
    selected = {"version": "bvbrc_minhash_result_selector_v2",
        "mode": "native_result" if saved is None else "saved_sheet",
        "saved_result_ref": None if saved is None else saved["source_ref"], "pair_metadata": records}
    inputs = {"version": "bvbrc_minhash_publication_inputs_v1", "selector": deepcopy(selected),
        "pair_metadata": records, "metadata_bindings": [{"pair_metadata_index": index,
            **deepcopy(field), "artifact_sha256": field["artifact_ref"][len("artifact_"):],
            "value": record[field["field"]]} for index, record in enumerate(records)
            for field in record["provenance"]["fields"]], "saved_result": deepcopy(saved)}
    return selected, inputs


def saved_input(h, published):
    source = h.store.get(published["result"]["source_ref"])
    grading, = source_tool_gradings(h.store, source["id"])
    grading_ref, = source["auxiliary_artifact_refs"]
    return {"source_ref": source["id"], "native_artifact_ref": source["artifact_ref"],
        "native_sha256": hashlib.sha256(h.store.get_artifact(source["artifact_ref"])).hexdigest(),
        "grading_artifact_ref": grading_ref,
        "grading_sha256": hashlib.sha256(h.store.get_artifact(grading_ref)).hexdigest(),
        "sheet": deepcopy(grading["sheet"]), "original_components": deepcopy(grading["components"])}


@pytest.mark.parametrize("mode", ["genome", "fasta"])
@pytest.mark.parametrize("profile", ["full", "k_only", "null"])
def test_v2_selected_inputs_preserve_request_and_native_measurements(harness, mode, profile):
    h = harness
    original = request(mode)
    h.client.rows = [["511145.12", "0.223144", "0.259259", "2/3"]]
    values = {"kmer_length": 1, "query_length": 2, "reference_length": 2, "alphabet_size": 2}
    if profile != "full":
        values.update(query_length=None, reference_length=None, alphabet_size=None)
    if profile == "null":
        values["kmer_length"] = None
    _, metadata = explicit_pair_inputs(h, original, values=values)
    selector, inputs = selected_inputs([metadata])
    launch_intent, snapshot = launch(h, original)
    sent_bytes = module._rpc_bytes(launch_intent["rpc_request"])
    prepared = h.service.prepare(RESULT_OPERATION, original, {}, scope=h.scope,
        previous_events=[], selector=selector)
    assert prepared["selector"] == selector and h.service._prepared(prepared) == prepared
    assert prepared["rpc_request"] == launch_intent["rpc_request"]
    assert module._rpc_bytes(prepared["rpc_request"]) == sent_bytes
    assert len(prepared["rpc_request"]["params"]) == 8
    published = h.service.publish(original, selector, snapshot, h.scope, "v2-native",
        publication_inputs=inputs)
    assert published["status"] == "completed", published
    grading, = source_tool_gradings(h.store, published["result"]["source_ref"])
    assert grading["schema"] == "bvbrc_minhash_grading_v2"
    assert grading["publication_inputs"] == inputs and grading["selector"] == selector
    assert grading["sheet"]["native_result"] == h.client.rows
    component, = grading["components"]["rows"]
    assert component["reported_distance"] == .223144 and component["reported_pvalue"] == .259259
    assert component["shared_hash_fraction"] == 2 / 3
    if profile == "null":
        assert component["recomputed_distance"] is None
    else:
        assert component["recomputed_distance"] == pytest.approx(.22314355131420976)
    if profile == "full":
        assert component["recomputed_pvalue"] == pytest.approx(.2592592592592592)
    else:
        assert component["recomputed_pvalue"] is None
    assert len(h.client.calls) == 1
    retained = json.loads(h.store.get_artifact(h.store.get(published["result"]["source_ref"])["request_ref"]))
    assert h.store.get_artifact(retained["rpc_request_artifact_ref"]) == sent_bytes


def test_v2_supplied_row_occurrences_and_ambiguous_candidates_are_retained(harness):
    h = harness
    h.client.rows = [["511145.12", ".1", ".2", "2/3"], ["511145.12", ".3", ".4", "1/2"]]
    _, row0 = explicit_pair_inputs(h, request())
    _, row1 = explicit_pair_inputs(h, request(), row_index=1)
    wrong = {**deepcopy(row0), "genome_id": "999.1"}
    selector, inputs = selected_inputs([row1, row0, deepcopy(row0), wrong])
    _, snapshot = launch(h, request())
    published = h.service.publish(request(), selector, snapshot, h.scope, "pair-occurrences",
        publication_inputs=inputs)
    grading, = source_tool_gradings(h.store, published["result"]["source_ref"])
    assert grading["publication_inputs"]["pair_metadata"] == [row1, row0, row0, wrong]
    assert [row["pair_metadata_index"] for row in inputs["metadata_bindings"]] == [0]*4 + [1]*4 + [2]*4 + [3]*4
    rows = grading["components"]["rows"]
    assert rows[0]["recomputed_distance"] is None
    assert rows[0]["shared_hash_fraction"] == 2 / 3
    assert rows[0]["calculation_inputs"]["pair_metadata_candidates"] == [row0, row0]
    assert rows[1]["calculation_inputs"]["pair_metadata"] == row1
    assert any(item["code"] == "pair_metadata_genome_id_mismatch"
        and item["path"] == "pair_metadata[3].genome_id" for item in grading["components"]["diagnostics"])


def test_v2_requires_frozen_inputs_and_legacy_intents_remain_exact(harness):
    h = harness
    _, metadata = explicit_pair_inputs(h, request())
    selector, inputs = selected_inputs([metadata])
    launch_intent, snapshot = launch(h, request())
    legacy = h.service.prepare(RESULT_OPERATION, request(), {}, scope=h.scope,
        previous_events=[], selector={})
    assert set(legacy) == {"operation", "request", "rpc_request", "mutates_remote", "cache_original"}
    assert h.service._prepared(legacy) == legacy
    assert "selector" not in launch_intent
    for selected, supplied in [(selector, None), ({}, inputs)]:
        with pytest.raises(ValueError, match="minhash_publication_inputs_conflict"):
            h.service.publish(request(), selected, snapshot, h.scope, "missing-inputs",
                publication_inputs=supplied)
    with pytest.raises(ValueError, match="minhash_result_selector_invalid"):
        h.service.prepare(LAUNCH_OPERATIONS["genome"], request(), {}, scope=h.scope,
            previous_events=[], selector=selector)


def test_v2_saved_sheet_recalculation_retains_original_and_uses_same_calculator(harness, monkeypatch):
    h = harness
    h.client.rows = [["511145.12", "0.223144", "0.259259", "2/3"]]
    _, metadata = explicit_pair_inputs(h, request())
    selector, inputs = selected_inputs([metadata])
    _, snapshot = launch(h, request())
    original = h.service.publish(request(), selector, snapshot, h.scope, "original-v2",
        publication_inputs=inputs)
    retained_grade = h.store.get_artifact(original["result"]["grading_artifact_ref"])
    _, changed = explicit_pair_inputs(h, request(), values={"kmer_length": 2,
        "query_length": 2, "reference_length": 2, "alphabet_size": 2})
    selector2, inputs2 = selected_inputs([changed], saved=saved_input(h, original))

    def prohibited(*args, **kwargs):
        raise AssertionError("Saved-sheet publication must not extract a native response")

    monkeypatch.setattr(module, "parse_minhash_result", prohibited)
    monkeypatch.setattr(h.service, "_native_response", prohibited)
    monkeypatch.setattr(h.client, "rpc", prohibited)
    recalculated = h.service.publish(request(), selector2, snapshot, h.scope, "saved-v2",
        publication_inputs=inputs2)
    assert recalculated["status"] == "completed", recalculated
    grade, = source_tool_gradings(h.store, recalculated["result"]["source_ref"])
    row, = grade["components"]["rows"]
    assert row["recomputed_distance"] == pytest.approx(.11157177565710488)
    assert row["recomputed_pvalue"] == pytest.approx(.10400000000000001)
    assert row["reported_distance"] == .223144 and row["reported_pvalue"] == .259259
    assert grade["sheet"] == inputs2["saved_result"]["sheet"]
    assert original["result"]["source_ref"] != recalculated["result"]["source_ref"]
    assert original["result"]["raw_artifact_ref"] == recalculated["result"]["raw_artifact_ref"]
    assert h.store.get_artifact(original["result"]["grading_artifact_ref"]) == retained_grade
    monkeypatch.setattr(module, "calculate_minhash_components", prohibited)
    assert h.service.publish(request(), selector, snapshot, h.scope, "original-v2",
        publication_inputs=inputs) == original
    assert h.service.publish(request(), selector2, snapshot, h.scope, "saved-v2",
        publication_inputs=inputs2) == recalculated
    with pytest.raises(ValueError, match="operation_key_reused_for_different_work"):
        h.service.publish(request(), selector2, snapshot, h.scope, "original-v2", publication_inputs=inputs2)


@pytest.mark.parametrize("conflict", ["request", "response"])
def test_v2_saved_input_must_name_same_native_request_and_response(harness, conflict):
    h = harness
    h.client.rows = [["511145.12", ".1", ".2", "2/3"]]
    _, snapshot = launch(h, request())
    published = h.service.publish(request(), {}, snapshot, h.scope, "saved-baseline")
    _, metadata = explicit_pair_inputs(h, request())
    selector, inputs = selected_inputs([metadata], saved=saved_input(h, published))
    changed = (replace(snapshot, request={"kind": "rpc", "rpc": {**snapshot.request["rpc"], "id": "wrong"}})
        if conflict == "request" else replace(snapshot, content=snapshot.content + b" "))
    with pytest.raises(ValueError, match="minhash_saved_result_" + conflict + "_conflict"):
        h.service.publish(request(), selector, changed, h.scope, "saved-conflict", publication_inputs=inputs)
