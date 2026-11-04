"""Selected C4b primitives with synthetic native responses, never live BV-BRC.

Host custody, durable reservation/recovery, scientific adapters and episode
communication are deliberately separate integration claims.
"""
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
import socket
from types import SimpleNamespace

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, SourceSnapshot
from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService
from gene_annotation_episode.bvbrc_application_definitions import get_application_spec, prepare_application
from gene_annotation_episode.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.state import Store
from test_bvbrc_analysis_transport import server


PREFIX = "api.bvbrc_appservice."
CONFIG = {"kind": "api", "service": "bvbrc_appservice",
    "execution_contract": "bvbrc_appservice_execution_v1",
    "endpoints": {"AppService": "https://app.example.invalid/rpc",
                  "Workspace": "https://workspace.example.invalid/rpc"},
    "scientific_adapters": []}
OBJECT_UUID = "11111111-1111-1111-1111-111111111111"
SHOCK_UUID = "22222222-2222-2222-2222-222222222222"


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def original_request():
    return {"version": "bvbrc_appservice_request_v1", "effect_contract": "selected_api_effects_v1",
        "required_application_id": "Homology", "parameters": {
            "output_path": "/synthetic/work/output", "output_file": "selected",
            "input_type": "dna", "input_source": "fasta_data", "input_fasta_data": ">q\nACGT\n",
            "db_type": "fna", "db_source": "fasta_data", "db_fasta_data": ">s\nACGA\n",
            "blast_program": "blastn", "blast_max_hits": 2},
        "start_parameters": {}, "definition_inputs": [], "input_bindings": [], "workspace_targets": []}


def owner():
    return {"run_id": "synthetic-run", "launch_episode_id": "original-launch",
            "parent_commission_operation_key": "synthetic-run:scientific:0",
            "original_launch_assignment_sha256": "0" * 64}


def content_binding(content=b"fixture"):
    sha = hashlib.sha256(content).hexdigest()
    return {"source_ref": "source_fixture", "artifact_field": "artifact_ref",
            "artifact_ref": "artifact_" + sha, "sha256": sha, "byte_count": len(content)}


def bound(request, suffix, arguments, **resolved):
    return {"version": "bvbrc_appservice_bound_inputs_v1", "original_job_owner": owner(),
        "resource_id": "synthetic-api", "request_sha256": digest(request),
        "selected_argument_sha256": digest(arguments), "definition": None, "inputs": [],
        "objects": [], "support_receipt_refs": [], "original_handoff_ref": None,
        "capability": None, "custody_proof_refs": [],
        "resolved": {"operation": PREFIX + suffix, **resolved}}


def original_task(request):
    return {"resource_id": "synthetic-api", "task_id": "123",
        "required_application_id": "Homology", "native_application_id": "Homology",
        "submitted_parameters": deepcopy(request["parameters"]),
        "submitted_start_parameters": deepcopy(request["start_parameters"]),
        "scheduler_returned_parameters": None, "effective_parameters": None,
        "submission_receipt_ref": "submission", "submission_operation_key": "synthetic-run:api:4",
        "submission_source_ref": "source_submission"}


def metadata(path="/synthetic/work/input.fa", *, uuid=OBJECT_UUID, type="contigs",
             size=0, shock_url=None):
    parent, name = path.rsplit("/", 1)
    native = [name, type, parent, "2026-10-24T12:00:00", uuid, "synthetic", size,
              {}, {}, "w", "n", shock_url or ""]
    return {"pointer": "/rows/0", "native_row": native, "valid": True,
            "path": path, "uuid": uuid, "type": type, "shock_url": shock_url,
            "creation_time": native[3], "size": size, "error": None}


def resolved_object(selection, *, row=None, association=None, native_reference=None):
    row = metadata() if row is None else row
    return {"selection": deepcopy(selection), "native_reference": native_reference or row["path"],
        "object": {"path": row["path"], "uuid": row["uuid"], "type": row["type"],
                   "metadata_receipt_ref": "metadata"},
        "metadata": row, "task_association": association, "identity": "workspace:" + row["uuid"]}


def association(path="/synthetic/work/input.fa"):
    return {"kind": "unverified_original_path", "evidence_ref": None, "pointer": None,
        "task_id": "123", "output_path": path, "output_uuid": OBJECT_UUID,
        "byte_version_status": "unknown", "version_evidence": []}


def common_receipt(request, suffix, arguments, *, status="ok"):
    return {"version": "bvbrc_appservice_support_receipt_v1", "receipt_ref": "preparation",
        "purpose": "support", "origin": {"run_id": "synthetic-run", "episode_id": "api",
            "operation_key": "synthetic-run:api:0", "name": PREFIX + suffix,
            "arguments_sha256": digest(arguments), "assignment_sha256": "3" * 64,
            "scope_sha256": "4" * 64}, "snapshot": None, "effect_receipt_refs": [],
        "status": status, "diagnostics": []}


def preparation_receipt(request):
    selection = {"kind": "packaged", "required_application_id": "Homology"}
    result = prepare_application("Homology", request["parameters"], request["start_parameters"])
    return {"receipt": common_receipt(request, "prepare", {"definition": selection}),
        "request_sha256": digest(request), "definition_selection": selection,
        "definition_evidence": {"content": content_binding(), "pointer": ""},
        "required_application_id": "Homology", "native_application_id": "Homology",
        "native_parameters": deepcopy(request["parameters"]),
        "start_parameters": deepcopy(request["start_parameters"]), "c3_result": result}


def rpc_snapshot(rpc, value, *, endpoint=None):
    endpoint = endpoint or CONFIG["endpoints"][rpc["method"].split(".", 1)[0]]
    sent = json.dumps(rpc, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    body = json.dumps({"version": "1.1", "id": rpc["id"], "result": [value]}).encode()
    return SourceSnapshot("bvbrc_analysis", endpoint, {"kind": "rpc", "rpc": deepcopy(rpc)},
        "2026-10-24T12:00:00+00:00", body, "application/json", {
            "status": 200, "body_complete": True, "received_body_bytes": len(body),
            "effective_url": endpoint, "automatic_redirects": False, "headers": {},
            "request": {"method": "POST", "url": endpoint, "body_bytes": len(sent),
                        "body_sha256": hashlib.sha256(sent).hexdigest(), "headers": []},
            "duration_measure": "client_http_request_turnaround", "http_turnaround_seconds": .25})


class Client:
    def __init__(self):
        self.calls = []
        self.value = []

    def rpc(self, rpc):
        self.calls.append(("rpc", deepcopy(rpc)))
        return rpc_snapshot(rpc, self.value)

    def task_info(self, task_id, file):
        self.calls.append(("task_info", task_id, file))
        url = CONFIG["endpoints"]["AppService"] + "/task_info/" + task_id + "/" + file
        body = (OBJECT_UUID + "\n").encode() if file.startswith("job_result") else b"native log\n"
        return SourceSnapshot("bvbrc_analysis", url, {"kind": "task_info", "task_id": task_id, "file": file},
            "2026-10-24T12:00:00+00:00", body, "text/plain", {
                "status": 200, "body_complete": True, "received_body_bytes": len(body),
                "effective_url": url, "automatic_redirects": False,
                "request": {"method": "GET", "url": url}, "headers": {"content-length": str(len(body))}})


@pytest.fixture(autouse=True)
def no_live_connections(monkeypatch):
    connect = socket.create_connection

    def local_only(address, *args, **kwargs):
        assert address[0] == "127.0.0.1", "No live service calls are permitted"
        return connect(address, *args, **kwargs)

    monkeypatch.setattr(socket, "create_connection", local_only)


@pytest.fixture
def harness(tmp_path):
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="ACGT", molecule="dna")
        tools = SimpleNamespace(store=store)
        client = Client()
        yield SimpleNamespace(store=store, tools=tools, client=client,
            service=BVBRCAppServiceService(tools, CONFIG, client=client),
            scope=store.validate_scope(None))


def prepare(harness, suffix, arguments, bindings, *, request=None, selector=None, handle=None):
    return harness.service.prepare(PREFIX + suffix, request or original_request(), arguments,
        scope=harness.scope, previous_events=[], bound_inputs=bindings, selector=selector, handle=handle)


def test_prepare_is_local_preserves_c3_qualifications_and_cannot_finish_job(harness):
    request = original_request()
    args = {"definition": {"kind": "packaged", "required_application_id": "Homology"}}
    bindings = bound(request, "prepare", args, definition_envelope=get_application_spec("Homology"))
    bindings["definition"] = {"content": content_binding(), "pointer": ""}
    operation = prepare(harness, "prepare", args, bindings)
    assert operation["native_kind"] == "local_prepare"
    assert operation["effects"] == [] and not operation["mutates_remote"]
    assert harness.service.invoke(operation) is None
    event = harness.service.decode(operation, None)
    assert event["state"] == "completed"
    assert not event["handoff_ready"] and not event["result_available"]
    assert event["facts"]["c3_result"]["status"] == "ok"
    assert "deployment_not_verified" in {row["code"] for row in event["facts"]["c3_result"]["diagnostics"]}
    assert harness.client.calls == []


def test_failed_preparation_is_retained_without_network(harness):
    request = original_request()
    del request["parameters"]["input_fasta_data"]
    args = {"definition": {"kind": "packaged", "required_application_id": "Homology"}}
    bindings = bound(request, "prepare", args, definition_envelope=get_application_spec("Homology"))
    bindings["definition"] = {"content": content_binding(), "pointer": ""}
    operation = prepare(harness, "prepare", args, bindings, request=request)
    event = harness.service.decode(operation, harness.service.invoke(operation))
    assert event["failure_code"] == "application_preparation_invalid"
    assert event["facts"]["c3_result"]["value"] is None
    assert harness.client.calls == []


def test_enumeration_one_correlated_rpc_no_launch(harness):
    request = original_request()
    operation = prepare(harness, "enumerate_apps", {}, bound(request, "enumerate_apps", {}))
    harness.client.value = [get_application_spec("Homology")["definition"]]
    snapshot = harness.service.invoke(operation)
    event = harness.service.decode(operation, snapshot)
    assert len(harness.client.calls) == 1
    assert harness.client.calls[0][1]["params"] == []
    assert event["state"] == "completed" and not event["handoff_ready"]
    validate_contract("Event", event)


@pytest.mark.parametrize("changes", [None, {}, {**CONFIG, "execution_contract": "legacy"},
    {**CONFIG, "service": "bvbrc_minhash"}, {**CONFIG, "kind": "local"},
    {**CONFIG, "endpoints": {"AppService": "https://example.invalid"}},
    {**CONFIG, "timeout": True}, {**CONFIG, "authorization_env": "invalid name"},
    {**CONFIG, "endpoints": {**CONFIG["endpoints"], "Workspace": "file:///tmp/ws"}}])
def test_configuration_rejected_before_any_request(changes):
    client = Client()
    with pytest.raises(ValueError):
        BVBRCAppServiceService(None, changes, client=client)
    assert client.calls == []


@pytest.mark.parametrize("change", ["missing", "request", "arguments", "operation"])
def test_host_resolved_inputs_required_and_digest_bound(harness, change):
    request = original_request()
    bindings = bound(request, "enumerate_apps", {})
    if change == "missing":
        bindings = None
    elif change == "operation":
        bindings["resolved"]["operation"] = PREFIX + "status"
    else:
        bindings["request_sha256" if change == "request" else "selected_argument_sha256"] = "f" * 64
    with pytest.raises(ValueError):
        prepare(harness, "enumerate_apps", {}, bindings)
    assert harness.client.calls == []


def submit_operation(h):
    request = original_request()
    args = {"preparation_receipt_ref": "preparation", "input_evidence_refs": []}
    return prepare(h, "submit", args, bound(request, "submit", args,
        preparation=preparation_receipt(request)))


def test_submission_uses_exact_c3_operands_and_preserves_preflight(harness):
    h = harness
    operation = submit_operation(h)
    request = original_request()
    parameters = {**request["parameters"], "_preflight": {"cpu": 3}}
    h.client.value = {"id": 123, "application_id": "Homology", "state_code": "Q",
        "params": json.dumps(parameters), "app_spec": json.dumps({"id": "Homology"}),
        "output_path": request["parameters"]["output_path"], "output_file": "selected"}
    event = h.service.decode(operation, h.service.invoke(operation))
    call, = h.client.calls
    assert call[1]["params"] == ["Homology", request["parameters"], {}]
    assert event["handoff_ready"] and not event["result_available"]
    assert event["native_handle"] == {"task_id": "123"}
    assert event["facts"]["scheduler_returned_parameters"] == parameters
    assert event["facts"]["additional_native_parameters"] == {"_preflight": {"cpu": 3}}
    assert len(operation["effects"]) == 1
    assert operation["effects"][0]["slot"] == {"kind": "appservice_submit"}
    assert request["parameters"].get("_preflight") is None


@pytest.mark.parametrize("changes,code", [
    ({"application_id": "Variation"}, "original_task_mismatch"),
    ({"params": '{"unrelated":true}'}, "submission_parameters_conflict"),
    ({"app_spec": '{"id":"Variation"}'}, "original_task_mismatch"),
    ({"state_code": "F"}, "native_task_failed"),
    ({"output_file": "other"}, "submission_parameters_conflict"),
    ({"params": '{"x":1,"x":2}'}, "submission_parameters_conflict"),
])
def test_submission_conflicting_return_never_creates_handoff(harness, changes, code):
    operation = submit_operation(harness)
    harness.client.value = {"id": "123", "application_id": "Homology", "state_code": "Q", **changes}
    event = harness.service.decode(operation, harness.service.invoke(operation))
    assert event["failure_code"] == code and not event["handoff_ready"]
    assert event["facts"]["failure"]["effect_outcome"] == ("confirmed" if code == "native_task_failed" else "unknown")
    assert len(harness.client.calls) == 1


def test_missing_submission_echoes_remain_unknown_but_real_acknowledgement_survives(harness):
    operation = submit_operation(harness)
    harness.client.value = {"id": 123}
    event = harness.service.decode(operation, harness.service.invoke(operation))
    assert event["handoff_ready"] and event["native_handle"]["task_id"] == "123"
    assert event["facts"]["native_status"] is None
    assert event["facts"]["scheduler_returned_parameters"] is None
    assert "submission_parameters_echo_unobserved" in event["facts"]["qualification_codes"]


def test_original_preflight_must_not_be_silently_discarded(harness):
    request = original_request()
    request["parameters"]["_preflight"] = {"cpu": 1}
    args = {"preparation_receipt_ref": "preparation", "input_evidence_refs": []}
    operation = prepare(harness, "submit", args, bound(request, "submit", args,
        preparation=preparation_receipt(request)), request=request)
    harness.client.value = {"id": "123", "params": json.dumps({**request["parameters"], "_preflight": {"cpu": 2}})}
    event = harness.service.decode(operation, harness.service.invoke(operation))
    assert event["failure_code"] == "submission_parameters_conflict"
    assert not event["handoff_ready"]


def target(target_id, path, *, parents=True):
    return {"target_id": target_id, "path": path, "type": "contigs", "purpose": "assigned_support_object",
        "input_binding_id": None, "metadata": {}, "allow_overwrite": False, "allow_create_parents": parents}


def test_one_create_rpc_preserves_reordered_targets_and_returned_ancestors(harness):
    request = original_request()
    request["workspace_targets"] = [target("a", "/synthetic/work/a.fa"), target("b", "/synthetic/work/b.fa")]
    args = {"objects": [{"target_id": "a", "data_binding_id": None, "creation_time": None},
                        {"target_id": "b", "data_binding_id": None, "creation_time": None}],
            "options": {"createUploadNodes": 1}}
    operation = prepare(harness, "workspace_create", args, bound(request, "workspace_create", args, data_bindings=[]), request=request)
    ancestor = metadata("/synthetic/work", type="folder")["native_row"]
    a = metadata("/synthetic/work/a.fa")["native_row"]
    b = metadata("/synthetic/work/b.fa", uuid=SHOCK_UUID)["native_row"]
    harness.client.value = [b, ancestor, a]
    event = harness.service.decode(operation, harness.service.invoke(operation))
    assert len(harness.client.calls) == 1
    assert len(operation["effects"]) == 2
    assert [row["slot"]["target_path"] for row in operation["effects"]] == ["/synthetic/work/a.fa", "/synthetic/work/b.fa"]
    assert [row["request_indices"] for row in event["facts"]["workspace_records"]] == [[1], [], [0]]
    assert event["state"] == "completed" and not event["handoff_ready"]
    assert not event["result_available"]


def test_create_parent_constraint_is_precise_pretransport_failure(harness):
    request = original_request()
    request["workspace_targets"] = [target("a", "/synthetic/work/a.fa", parents=False)]
    args = {"objects": [{"target_id": "a", "data_binding_id": None, "creation_time": None}], "options": {}}
    operation = prepare(harness, "workspace_create", args, bound(request, "workspace_create", args, data_bindings=[]), request=request)
    event = harness.service.decode(operation, harness.service.invoke(operation))
    assert event["failure_code"] == "workspace_parent_creation_constraint_unsupported"
    assert event["facts"]["failure"]["effect_outcome"] == "not_sent"
    assert operation["effects"] == [] and harness.client.calls == []


def test_metadata_is_exact_array_metadata_only_and_preserves_failed_peer(harness):
    request = original_request()
    request["workspace_targets"] = [target("a", "/synthetic/work/a.fa"), target("b", "/synthetic/work/b.fa")]
    args = {"objects": [{"kind": "original_target", "target_id": "a"},
                        {"kind": "original_target", "target_id": "b"}], "options": {"adminmode": 0}}
    objects = [resolved_object(args["objects"][0], row=metadata("/synthetic/work/a.fa")),
               resolved_object(args["objects"][1], row=metadata("/synthetic/work/b.fa", uuid=SHOCK_UUID))]
    operation = prepare(harness, "workspace_metadata", args, bound(request, "workspace_metadata", args, objects=objects), request=request)
    harness.client.value = [[objects[0]["metadata"]["native_row"], None], [["invalid"], None]]
    event = harness.service.decode(operation, harness.service.invoke(operation))
    assert harness.client.calls[0][1]["params"] == [{"objects": ["/synthetic/work/a.fa", "/synthetic/work/b.fa"],
        "metadata_only": 1, "adminmode": 0}]
    assert event["facts"]["parse_status"] == "partial"
    assert event["facts"]["workspace_records"][0]["status"] == "ok"
    assert event["failure_code"] == "workspace_member_failed"
    assert len(harness.client.calls) == 1


@pytest.mark.parametrize("native_operation", ["query_tasks", "stdout", "stderr"])
def test_one_selected_observation_never_combines_status_and_log(harness, native_operation):
    request = original_request()
    suffix = "status" if native_operation == "query_tasks" else "task_info"
    args = {"handoff_ref": "handoff"}
    if suffix == "task_info":
        args["file"] = native_operation
    bindings = bound(request, suffix, args, original_task=original_task(request))
    bindings["original_handoff_ref"] = "handoff"
    operation = harness.service.prepare_observation(request, {"task_id": "123"},
        scope=harness.scope, native_operation=native_operation, bound_inputs=bindings)
    harness.client.value = {"123": {"id": 123, "app": "Homology", "status": "completed",
        "parameters": request["parameters"], "start_time": "", "elapsed_time": "00:03:17"}}
    event = harness.service.decode(operation, harness.service.invoke(operation))
    assert len(harness.client.calls) == 1
    if native_operation == "query_tasks":
        assert harness.client.calls[0][1]["params"] == [["123"]]
        assert event["state"] == "completed"
        assert event["facts"]["native_timing"]["elapsed_time"] == "00:03:17"
    else:
        assert harness.client.calls[0] == ("task_info", "123", native_operation)
        assert event["state"] == "unknown" and not event["result_available"]
        assert "text" not in event["facts"]["projection"]
    assert not event["handoff_ready"]


@pytest.mark.parametrize("file", ["job_result_id", "job_result_folder"])
def test_task_info_uuid_is_exact_returned_object(file, harness):
    request = original_request()
    args = {"handoff_ref": "handoff", "file": file}
    bindings = bound(request, "task_info", args, original_task=original_task(request))
    bindings["original_handoff_ref"] = "handoff"
    operation = prepare(harness, "task_info", args, bindings)
    snapshot = harness.service.invoke(operation)
    event = harness.service.decode(operation, snapshot)
    assert event["facts"]["projection"]["reported_object_uuid"] == OBJECT_UUID
    malformed = replace(snapshot, content=b"log contains " + snapshot.content,
        transport={**snapshot.transport, "received_body_bytes": len(b"log contains " + snapshot.content)})
    assert harness.service.decode(operation, malformed)["failure_code"] == "task_info_object_invalid"
    assert len(harness.client.calls) == 1


FORMAT = {"format": "synthetic_binary", "version": None, "mode": None,
          "producer_source_ref": None, "transformation_evidence": []}


def result_selector():
    return {"version": "bvbrc_appservice_result_selector_v1", "endpoint": "requested_artifacts",
        "requirements": [{"requirement_id": "r1", "role": "native_output", "required": True,
            "declared_format": deepcopy(FORMAT), "producer_rule_evidence": None, "exact_object": None}],
        "adapter": None, "requested_schema": {"type": "object", "properties": {},
            "required": [], "additionalProperties": False}, "supplied_metadata": [], "supplied_capabilities": []}


def output_object():
    selected = {"kind": "receipt_row", "receipt_ref": "metadata", "row_pointer": "/rows/0"}
    return resolved_object(selected, row=metadata(size=6), association=association())


def test_listing_is_one_explicit_native_array_and_preserves_missing_group(harness):
    request = original_request()
    obj = output_object()
    args = {"objects": [obj["selection"]], "options": {"fullHierachicalOutput": 1, "recursive": 0}}
    bindings = bound(request, "list_outputs", args, objects=[obj], original_task=original_task(request))
    bindings["original_handoff_ref"] = "handoff"
    operation = prepare(harness, "list_outputs", args, bindings, selector=result_selector())
    harness.client.value = {}
    event = harness.service.decode(operation, harness.service.invoke(operation))
    assert harness.client.calls[0][1]["params"] == [{"paths": [obj["native_reference"]],
        "fullHierachicalOutput": 1, "recursive": 0}]
    assert event["facts"]["workspace_records"] == []
    assert event["facts"]["parse_status"] == "ok"
    assert not event["result_available"] and len(harness.client.calls) == 1


def test_capability_array_retains_null_and_does_not_leak_url_into_event(harness):
    request = original_request()
    first = output_object()
    second = resolved_object({"kind": "receipt_row", "receipt_ref": "metadata", "row_pointer": "/rows/1"},
        row=metadata("/synthetic/work/b.fa", uuid=SHOCK_UUID),
        association={**association("/synthetic/work/b.fa"), "output_uuid": SHOCK_UUID})
    args = {"objects": [first["selection"], second["selection"]], "generation": 0, "predecessor_receipt_ref": None}
    bindings = bound(request, "download_capability", args, original_task=original_task(request),
        objects=[first, second], predecessor_effect_refs=[])
    bindings["original_handoff_ref"] = "handoff"
    operation = prepare(harness, "download_capability", args, bindings, selector=result_selector())
    harness.client.value = ["https://download.example.invalid/file?private-capability=value", None]
    snapshot = harness.service.invoke(operation)
    event = harness.service.decode(operation, snapshot)
    assert len(harness.client.calls) == 1 and len(operation["effects"]) == 2
    assert [row["available"] for row in event["facts"]["workspace_records"]] == [True, False]
    assert "private-capability" not in canonical(event)
    assert b"private-capability" in snapshot.content
    assert all(row["slot"]["generation"] == 0 for row in operation["effects"])
    assert not event["handoff_ready"] and not event["result_available"]


def download_operation(h, url, *, byte_range=None):
    request = original_request()
    obj = output_object()
    capability = {"kind": "acquired", "receipt_ref": "capability", "input_index": 0}
    entry = {"input_index": 0, "object_selection": obj["selection"], "object": obj["object"],
        "task_association": obj["task_association"], "url": url,
        "issued_observed_at": "2026-10-24T12:00:00+00:00", "expires_at": None, "expiry_evidence": None}
    args = {"capability": capability, "object": obj["selection"], "byte_range": byte_range, "max_bytes": 1048576,
        "requirement_ids": ["r1"], "role": "native_output", "declared_format": deepcopy(FORMAT)}
    bindings = bound(request, "download", args, original_task=original_task(request), object=obj,
        capability={"selection": capability, "entry": entry})
    bindings["original_handoff_ref"] = "handoff"
    bindings["capability"] = capability
    return prepare(h, "download", args, bindings, selector=result_selector())


@pytest.mark.parametrize("status,body,headers,complete", [
    (200, b"abcdef", {}, "yes"),
    (206, b"cde", {"Content-Range": "bytes 2-4/6"}, "no"),
])
def test_actual_download_transport_keeps_ignored_range_or_partial_object(harness, status, body, headers, complete):
    from gene_annotation_episode.bvbrc_analysis_transport import BVBRCAnalysisClient
    with server(body, status=status, headers=headers) as (url, calls):
        harness.service.client = BVBRCAnalysisClient(CONFIG["endpoints"])
        operation = download_operation(harness, url + "/file?key=synthetic", byte_range=[2, 4])
        snapshot = harness.service.invoke(operation)
    event = harness.service.decode(operation, snapshot)
    assert len(calls) == 1 and calls[0]["method"] == "GET"
    assert calls[0]["headers"]["Range"] == "bytes=2-4"
    assert snapshot.content == body
    assert event["facts"]["projection"]["object_complete"] == complete
    assert event["result_available"] and not event["handoff_ready"]
    assert operation["effects"] == []
    if status == 200:
        assert "range_ignored" in {d["code"] for d in event["facts"]["diagnostics"]}


def test_incomplete_download_retains_bytes_for_same_action_host_publication(harness):
    from gene_annotation_episode.bvbrc_analysis_transport import BVBRCAnalysisClient
    with server(b"abc", headers={"Content-Length": "6"}) as (url, calls):
        harness.service.client = BVBRCAnalysisClient(CONFIG["endpoints"])
        operation = download_operation(harness, url + "/file")
        with pytest.raises(AcquisitionError) as raised:
            harness.service.invoke(operation)
    snapshot = raised.value.snapshot
    event = harness.service.decode(operation, snapshot)
    assert snapshot.content == b"abc" and len(calls) == 1
    assert event["result_available"] and event["failure_code"] == "download_incomplete"
    assert event["facts"]["projection"]["object_complete"] == "no"


def test_null_capability_is_specific_unavailable_result_without_network(harness):
    operation = download_operation(harness, None)
    event = harness.service.decode(operation, harness.service.invoke(operation))
    assert event["failure_code"] == "capability_unavailable"
    assert not event["result_available"] and harness.client.calls == []


def upload_operation(h, url, content=b"\x00\xffACGT\n"):
    request = original_request()
    source = content_binding(content)
    source["artifact_ref"] = h.store.artifact(content)
    binding = {"binding_id": "query", "parameter_pointer": "/input_fasta_file", "kind": "retained_bytes",
        "content": source, "workspace_path": "/synthetic/work/input.fa", "inline_value": None,
        "link_evidence": None, "members": []}
    request["parameters"].update(input_source="fasta_file", input_fasta_file=binding["workspace_path"])
    request["input_bindings"] = [binding]
    created = {"receipt_ref": "metadata", "row_pointer": "/rows/0"}
    obj = resolved_object({"kind": "receipt_row", **created}, row=metadata(shock_url=url))
    args = {"created_object": created, "input_binding_id": "query", "filename": "original.fa"}
    bindings = bound(request, "upload", args, upload={"object": obj, "input": binding,
        "shock_node_id": SHOCK_UUID, "shock_url": url})
    return prepare(h, "upload", args, bindings, request=request)


def test_actual_upload_sends_only_exact_original_bytes_to_created_node(harness):
    from gene_annotation_episode.bvbrc_analysis_transport import BVBRCAnalysisClient
    content = b"\x00\xffACGT\n"
    reply = {"status": 200, "data": {"id": SHOCK_UUID, "file": {"size": len(content),
        "checksum": {"sha256": hashlib.sha256(content).hexdigest()}}}, "error": None}
    with server(json.dumps(reply).encode()) as (url, calls):
        harness.service.client = BVBRCAnalysisClient(CONFIG["endpoints"])
        operation = upload_operation(harness, url + "/node/" + SHOCK_UUID, content)
        snapshot = harness.service.invoke(operation)
    event = harness.service.decode(operation, snapshot)
    assert len(calls) == 1 and calls[0]["method"] == "PUT"
    assert content in calls[0]["body"] and b'name="upload"' in calls[0]["body"]
    assert event["facts"]["projection"]["confirmation"] == "accepted_bytes_match"
    assert operation["effects"][0]["slot"] == {"kind": "shock_upload", "shock_node_id": SHOCK_UUID}
    assert not event["handoff_ready"] and not event["result_available"]


def test_upload_rechecks_exact_artifact_bytes_before_transport(harness, monkeypatch):
    operation = upload_operation(harness, "https://shock.example.invalid/node/" + SHOCK_UUID)
    monkeypatch.setattr(harness.store, "get_artifact", lambda reference: b"wrong bytes")
    with pytest.raises(AcquisitionError) as raised:
        harness.service.invoke(operation)
    assert raised.value.code == "input_bytes_mismatch"
    assert raised.value.submission_outcome == "not_sent" and harness.client.calls == []


def test_prepared_native_mutation_rejected_before_transport(harness):
    operation = submit_operation(harness)
    operation["native_operands"]["call"]["rpc_request"]["params"][1]["blast_max_hits"] = 900
    with pytest.raises(ValueError, match="prepared_request_conflict"):
        harness.service.invoke(operation)
    assert harness.client.calls == []


@pytest.mark.parametrize("mutation,code", [("correlation", "native_response_invalid"),
    ("error", "native_rpc_error"), ("http", "native_http_error"),
    ("incomplete", "native_response_invalid"), ("endpoint", "native_response_invalid"),
    ("sent_digest", "native_response_invalid"), ("duplicate", "native_response_invalid")])
def test_rpc_failure_retains_exact_snapshot_and_never_retries(harness, mutation, code):
    operation = submit_operation(harness)
    harness.client.value = {"id": "123"}
    snapshot = harness.service.invoke(operation)
    fields = asdict(snapshot)
    value = json.loads(fields["content"])
    if mutation == "correlation":
        value["id"] = "other"
    elif mutation == "error":
        value.pop("result")
        value["error"] = {"code": -1, "message": "synthetic failure"}
    elif mutation == "http":
        fields["transport"]["status"] = 403
    elif mutation == "incomplete":
        fields["transport"]["body_complete"] = False
    elif mutation == "endpoint":
        fields["url"] = "https://other.example.invalid/rpc"
    elif mutation == "sent_digest":
        fields["transport"]["request"]["body_sha256"] = "0" * 64
    fields["content"] = json.dumps(value).encode()
    if mutation == "duplicate":
        fields["content"] = fields["content"].replace(b'"result":', b'"result": [], "result":')
    fields["transport"]["received_body_bytes"] = len(fields["content"])
    changed = SourceSnapshot(**fields)
    before = asdict(changed)
    event = harness.service.decode(operation, changed)
    assert event["failure_code"] == code and not event["handoff_ready"]
    assert asdict(changed) == before and len(harness.client.calls) == 1
    assert event["facts"]["failure"]["effect_outcome"] == "unknown"


def publication_inputs(operation, snapshot):
    content = content_binding(snapshot.content)
    return {"version": "bvbrc_appservice_publication_inputs_v1",
        "request": operation["native_operands"]["request"],
        "selector": operation["native_operands"]["selector"], "original_handoff_ref": "handoff",
        "current_operation": {"name": operation["operation"], "arguments": operation["native_operands"]["arguments"]},
        "current_snapshot": {"source_ref": content["source_ref"], "content": content,
            "retrieved_at": snapshot.retrieved_at, "media_type": snapshot.media_type,
            "transport": deepcopy(snapshot.transport), "selected_operands": {
                key: deepcopy(operation[key]) for key in ("operation", "request_sha256", "arguments_sha256", "native_operands")}},
        "prior_acquisition_receipt_refs": [], "support_receipt_refs": ["capability"],
        "supplied_evidence": [], "adapter": None, "adapter_implementation_sha256": None}


def test_publication_requires_frozen_dependencies_and_delegates_only_exact_snapshot(harness):
    from gene_annotation_episode.bvbrc_analysis_transport import BVBRCAnalysisClient
    with server(b"abcdef") as (url, requests):
        harness.service.client = BVBRCAnalysisClient(CONFIG["endpoints"])
        operation = download_operation(harness, url + "/file")
        snapshot = harness.service.invoke(operation)
    inputs = publication_inputs(operation, snapshot)
    request, selector = inputs["request"], inputs["selector"]
    with pytest.raises(ValueError):
        harness.service.publish(request, selector, snapshot, harness.scope, "selected:publication")
    with pytest.raises(ValueError, match="appservice_publication_unbound"):
        harness.service.publish(request, selector, snapshot, harness.scope, "selected:publication", publication_inputs=inputs)
    calls = []

    def publish(received_snapshot, *, publication_inputs, operation_key):
        calls.append((received_snapshot, deepcopy(publication_inputs), operation_key))
        return {"status": "partial", "record_refs": ["retained-acquisition"]}

    harness.service.publication_callback = publish
    result = harness.service.publish(request, selector, snapshot, harness.scope, "selected:publication", publication_inputs=inputs)
    assert result == {"status": "partial", "record_refs": ["retained-acquisition"]}
    assert calls == [(snapshot, inputs, "selected:publication")]
    assert len(requests) == 1
    for field in ("request", "selector", "current_snapshot", "native_call", "arguments_digest"):
        changed = deepcopy(inputs)
        if field == "request":
            changed[field]["parameters"]["blast_max_hits"] = 3
        elif field == "selector":
            changed[field]["requirements"][0]["role"] = "other-role"
        elif field == "current_snapshot":
            changed[field]["content"]["sha256"] = "f" * 64
        elif field == "native_call":
            changed["current_snapshot"]["selected_operands"]["native_operands"]["call"]["url"] = "https://other.example.invalid/file"
        else:
            changed["current_snapshot"]["selected_operands"]["arguments_sha256"] = "e" * 64
        with pytest.raises(ValueError, match="publication_dependency_conflict"):
            harness.service.publish(request, selector, snapshot, harness.scope, "selected:publication", publication_inputs=changed)
    assert len(calls) == 1


def test_service_schemas_survive_embedding_in_common_assignment_and_operation_schema():
    from jsonschema import Draft202012Validator
    schema = {"type": "object", "properties": {"request": BVBRCAppServiceService.request_schema,
        "selector": BVBRCAppServiceService.selector_schema}, "required": ["request", "selector"],
        "additionalProperties": False}
    Draft202012Validator(schema).validate({"request": original_request(), "selector": result_selector()})
    # These are independent JSON Schema resources, so the local $defs do not
    # accidentally resolve against a different outer assignment's definitions.
    assert BVBRCAppServiceService.request_schema["$id"] != BVBRCAppServiceService.selector_schema["$id"]


def test_workspace_source_path_normalization_does_not_rewrite_native_operand(harness):
    request = original_request()
    original_path = "/synthetic//work/input.fa/"
    request["workspace_targets"] = [target("input", original_path)]
    selected = {"kind": "original_target", "target_id": "input"}
    args = {"objects": [selected], "options": {}}
    obj = resolved_object(selected, native_reference=original_path)
    operation = prepare(harness, "workspace_metadata", args,
        bound(request, "workspace_metadata", args, objects=[obj]), request=request)
    assert operation["native_operands"]["call"]["rpc_request"]["params"][0]["objects"] == [original_path]
    assert harness.client.calls == []


def test_unrelated_original_target_cannot_enter_native_request(harness):
    request = original_request()
    request["workspace_targets"] = [target("input", "/synthetic/work/actual.fa")]
    selected = {"kind": "original_target", "target_id": "input"}
    args = {"objects": [selected], "options": {}}
    obj = resolved_object(selected)
    with pytest.raises(ValueError, match="workspace_target_conflict"):
        prepare(harness, "workspace_metadata", args, bound(request, "workspace_metadata", args, objects=[obj]), request=request)
    assert harness.client.calls == []


def test_status_wrong_task_stays_failed_with_original_identity(harness):
    request = original_request()
    args = {"handoff_ref": "handoff"}
    bindings = bound(request, "status", args, original_task=original_task(request))
    bindings["original_handoff_ref"] = "handoff"
    operation = prepare(harness, "status", args, bindings)
    harness.client.value = {"999": {"id": "999", "status": "completed"}}
    event = harness.service.decode(operation, harness.service.invoke(operation))
    assert event["failure_code"] == "original_task_mismatch"
    assert event["native_handle"] == {"task_id": "123"}
    assert event["facts"]["task_records"][0]["native_record"]["id"] == "999"
    assert len(harness.client.calls) == 1


def test_native_effective_container_precedence_preserves_both_original_operands(harness):
    request = original_request()
    request["parameters"]["container_id"] = "native-task-container"
    request["start_parameters"]["container_id"] = "original-start-container"
    args = {"preparation_receipt_ref": "preparation", "input_evidence_refs": []}
    operation = prepare(harness, "submit", args, bound(request, "submit", args,
        preparation=preparation_receipt(request)), request=request)
    harness.client.value = {"id": "123", "application_id": "Homology", "params": json.dumps(request["parameters"]),
        "container_id": "native-task-container"}
    event = harness.service.decode(operation, harness.service.invoke(operation))
    assert event["handoff_ready"]
    assert "native_task_parameter_container_id_override" in event["facts"]["qualification_codes"]
    native = harness.client.calls[0][1]["params"]
    assert native[1]["container_id"] == "native-task-container"
    assert native[2]["container_id"] == "original-start-container"


def test_results_metadata_of_original_input_does_not_require_output_association(harness):
    request = original_request()
    args = {'objects': [{'kind': 'receipt_row', 'receipt_ref': 'input_metadata',
        'row_pointer': '/result/0/0'}], 'options': {}}
    obj = resolved_object(args['objects'][0])
    assert obj['task_association'] is None
    bindings = bound(request, 'workspace_metadata', args, objects=[obj], original_task=original_task(request))
    bindings['original_handoff_ref'] = 'original_handoff'
    operation = prepare(harness, 'workspace_metadata', args, bindings, request=request,
        selector=result_selector())
    assert operation['native_operands']['call']['rpc_request']['method'] == 'Workspace.get'


def test_results_metadata_cannot_change_a_present_task_association(harness):
    request = original_request()
    args = {'objects': [{'kind': 'receipt_row', 'receipt_ref': 'metadata',
        'row_pointer': '/result/0/0'}], 'options': {}}
    obj = resolved_object(args['objects'][0], association={**association(), 'task_id': '999'})
    bindings = bound(request, 'workspace_metadata', args, objects=[obj], original_task=original_task(request))
    bindings['original_handoff_ref'] = 'original_handoff'
    with pytest.raises(ValueError, match='original_task_mismatch'):
        prepare(harness, 'workspace_metadata', args, bindings, request=request, selector=result_selector())


def test_submission_preserves_actual_parameters_echo_pointer(harness):
    operation = submit_operation(harness)
    harness.client.value = {"id": "123", "parameters": original_request()["parameters"]}
    event = harness.service.decode(operation, harness.service.invoke(operation))
    assert event["handoff_ready"]
    assert event["facts"]["scheduler_parameters_pointer"] == "/result/0/parameters"


def test_status_preserves_valid_requested_member_despite_unrelated_malformed_peer(harness):
    request = original_request()
    args = {"handoff_ref": "handoff"}
    bindings = bound(request, "status", args, original_task=original_task(request))
    bindings["original_handoff_ref"] = "handoff"
    operation = prepare(harness, "status", args, bindings)
    harness.client.value = {"123": {"id": "123", "app": "Homology", "status": "running"}, "999": ["malformed"]}
    event = harness.service.decode(operation, harness.service.invoke(operation))
    assert event["state"] == "running" and event["failure_code"] is None
    assert event["native_handle"] == {"task_id": "123"}
    assert event["facts"]["parse_status"] == "partial"
    assert len(event["facts"]["task_records"]) == 2
    assert event["facts"]["task_records"][1]["native_record"] == ["malformed"]
    assert "unrequested_or_invalid_task_records_retained" in event["facts"]["qualification_codes"]


def test_create_upload_node_does_not_read_or_upload_retained_input_bytes(harness, monkeypatch):
    upload = upload_operation(harness, "https://shock.example.invalid/node/" + SHOCK_UUID)
    request = deepcopy(upload["native_operands"]["request"])
    binding = request["input_bindings"][0]
    request["workspace_targets"] = [{**target("input", binding["workspace_path"]),
        "purpose": "input", "input_binding_id": binding["binding_id"]}]
    args = {"objects": [{"target_id": "input", "data_binding_id": "query", "creation_time": None}],
            "options": {"createUploadNodes": 1}}
    monkeypatch.setattr(harness.store, "get_artifact", lambda ref: pytest.fail("create must not read upload bytes"))
    operation = prepare(harness, "workspace_create", args,
        bound(request, "workspace_create", args, data_bindings=[binding]), request=request)
    native = operation["native_operands"]["call"]["rpc_request"]["params"][0]
    assert native["objects"] == [[binding["workspace_path"], "contigs", {}, None, None]]
    harness.client.value = [metadata(shock_url="https://shock.example.invalid/node/" + SHOCK_UUID)["native_row"]]
    event = harness.service.decode(operation, harness.service.invoke(operation))
    assert event["state"] == "completed" and len(harness.client.calls) == 1
    assert harness.client.calls[0][0] == "rpc" and not event["handoff_ready"]


def test_supplied_link_create_preserves_exact_link_and_server_fetch_option(harness):
    request = original_request()
    link = "https://supplied.example.invalid/exact-input.fa?version=original"
    request["parameters"]["supplied_input_link"] = link
    binding = {"binding_id": "link", "parameter_pointer": "/supplied_input_link", "kind": "supplied_link",
        "content": None, "workspace_path": None, "inline_value": link,
        "link_evidence": {"content": content_binding(link.encode()), "pointer": ""}, "members": []}
    request["input_bindings"] = [binding]
    request["workspace_targets"] = [{**target("linked", "/synthetic/work/linked.fa"), "input_binding_id": "link"}]
    args = {"objects": [{"target_id": "linked", "data_binding_id": "link", "creation_time": None}],
            "options": {"downloadFromLinks": 1}}
    operation = prepare(harness, "workspace_create", args,
        bound(request, "workspace_create", args, data_bindings=[binding]), request=request)
    native = operation["native_operands"]["call"]["rpc_request"]["params"][0]
    assert native == {"objects": [["/synthetic/work/linked.fa", "contigs", {}, link, None]], "downloadFromLinks": 1}
    harness.client.value = [metadata("/synthetic/work/linked.fa")["native_row"]]
    harness.service.decode(operation, harness.service.invoke(operation))
    assert len(harness.client.calls) == 1 and harness.client.calls[0][0] == "rpc"


def test_duplicate_upload_reply_members_do_not_manufacture_confirmation(harness):
    from gene_annotation_episode.bvbrc_analysis_transport import BVBRCAnalysisClient
    reply = ('{"status":200,"data":{"id":"' + SHOCK_UUID + '","id":"' + SHOCK_UUID + '"},"error":null}').encode()
    with server(reply) as (url, calls):
        harness.service.client = BVBRCAnalysisClient(CONFIG["endpoints"])
        operation = upload_operation(harness, url + "/node/" + SHOCK_UUID)
        snapshot = harness.service.invoke(operation)
    event = harness.service.decode(operation, snapshot)
    assert event["failure_code"] == "native_response_invalid"
    assert "duplicate_json_member" in {row["code"] for row in event["facts"]["diagnostics"]}
    assert len(calls) == 1 and snapshot.content == reply
