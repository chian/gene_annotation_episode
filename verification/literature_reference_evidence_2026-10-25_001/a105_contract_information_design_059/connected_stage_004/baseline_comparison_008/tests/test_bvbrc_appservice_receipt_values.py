"""Synthetic native support responses through real service and journal contracts.

No network, deployed service, custody proof or complete episode path is claimed.
Source/receipt labels are explicitly supplied fixture bindings; production must
obtain them from the custody and persistence host.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.api_selected_effects import SelectedAPIEffects
from gene_annotation_episode.bvbrc_application_definitions import get_application_spec
from gene_annotation_episode.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.bvbrc_appservice_receipt_values import (
    build_appservice_receipt, confirm_appservice_effects,
)
from test_api_bvbrc_appservice import (
    PREFIX, SHOCK_UUID, OBJECT_UUID, association, bound, common_receipt,
    content_binding, harness, metadata, original_request, original_task, prepare, preparation_receipt,
    resolved_object, result_selector, rpc_snapshot, submit_operation, upload_operation,
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("receipt projection attempted network access")
    monkeypatch.setattr("socket.socket", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)


def binding(operation, snapshot):
    return {"source_ref": "source_retained_native", "content": {
        **content_binding(snapshot.content), "source_ref": "source_retained_native"},
        "retrieved_at": snapshot.retrieved_at, "media_type": snapshot.media_type,
        "transport": deepcopy(snapshot.transport), "selected_operands": {
            key: deepcopy(operation[key]) for key in
            ("operation", "request_sha256", "arguments_sha256", "native_operands")}}


def common(operation, snapshot, effects=()):
    request, args = operation["native_operands"]["request"], operation["native_operands"]["arguments"]
    receipt = common_receipt(request, operation["operation"].removeprefix(PREFIX), args)
    receipt.update(receipt_ref="support_constructed_by_host", purpose=operation["purpose"],
        snapshot=None if snapshot is None else binding(operation, snapshot),
        effect_receipt_refs=[row["effect_ref"] for row in effects])
    return receipt


def issued(tmp_path, operation):
    journal = SelectedAPIEffects(tmp_path, run_id="synthetic-run")
    reservation = journal.reserve(SimpleNamespace(run_id="synthetic-run", episode_id="api"),
        "synthetic-run:api:0", operation["effects"])
    return journal, reservation, journal.mark_issued(reservation)["effects"]


def rpc(operation, native):
    return rpc_snapshot(operation["native_operands"]["call"]["rpc_request"], native)


def changed_body(snapshot, body):
    return replace(snapshot, content=body, transport={**snapshot.transport, "received_body_bytes": len(body)})


def project(h, operation, snapshot, effects=(), receipt=None, event=None):
    event = h.service.decode(operation, snapshot) if event is None else event
    result = build_appservice_receipt(operation, event, snapshot,
        common_receipt=common(operation, snapshot, effects) if receipt is None else receipt,
        effect_receipts=list(effects))
    assert set(result) == {"contract", "value", "diagnostics"}
    validate_contract(result["contract"], result["value"])
    for diagnostic in result["diagnostics"]:
        validate_contract("Diagnostic", diagnostic)
    return result


def confirm(h, operation, snapshot, effects, snapshot_binding=None, event=None):
    event = h.service.decode(operation, snapshot) if event is None else event
    return confirm_appservice_effects(operation, event, snapshot,
        snapshot_binding=binding(operation, snapshot) if snapshot_binding is None and snapshot is not None else snapshot_binding,
        effect_receipts=effects)


def codes(result):
    return {row["code"] for row in result["diagnostics"]}


@pytest.mark.parametrize('field', ['container_id', 'data_container_id'])
def test_submission_receipt_preserves_effective_container_override(harness, tmp_path, field):
    request = original_request()
    request['parameters'][field] = 'task-selected'
    request['start_parameters'][field] = 'start-default'
    args = {'preparation_receipt_ref': 'preparation', 'input_evidence_refs': []}
    operation = prepare(harness, 'submit', args, bound(request, 'submit', args,
        preparation=preparation_receipt(request)), request=request)
    native = {'id': '123', 'application_id': 'Homology', 'state_code': 'Q',
        'params': json.dumps(request['parameters']), field: 'task-selected'}
    snapshot = rpc(operation, native)
    journal, reservation, effects = issued(tmp_path, operation)
    outcomes = confirm(harness, operation, snapshot, effects)
    assert outcomes[0]['state'] == 'confirmed'
    result = project(harness, operation, snapshot, journal.record_outcome(reservation, outcomes))
    assert result['contract'] == 'TaskHandoff'
    task = result['value']['original_task']
    assert task['submitted_parameters'][field] == 'task-selected'
    assert task['submitted_start_parameters'][field] == 'start-default'
    assert 'native_task_parameter_' + field + '_override' in codes(result)


def create_operation(h):
    request = original_request()
    request["workspace_targets"] = [{"target_id": target, "path": "/synthetic/work/" + target,
        "type": "contigs", "purpose": "input", "input_binding_id": None,
        "metadata": {}, "allow_overwrite": False, "allow_create_parents": True} for target in ("a.fa", "b.fa")]
    args = {"objects": [{"target_id": target["target_id"], "data_binding_id": None,
        "creation_time": None} for target in request["workspace_targets"]], "options": {"createUploadNodes": 1}}
    return prepare(h, "workspace_create", args, bound(request, "workspace_create", args, data_bindings=[]), request=request)


def create_rows():
    return [metadata("/synthetic/work", type="folder")["native_row"],
        metadata("/synthetic/work/b.fa", uuid="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")["native_row"],
        metadata("/synthetic/work/a.fa", shock_url="https://shock.invalid/node/" + SHOCK_UUID)["native_row"]]


def status_operation(h, suffix="status", file=None):
    request = original_request()
    args = {"handoff_ref": "original_handoff"}
    if file is not None:
        args["file"] = file
    bindings = bound(request, suffix, args, original_task=original_task(request))
    bindings["original_handoff_ref"] = args["handoff_ref"]
    return prepare(h, suffix, args, bindings, request=request)


def capability_operation(h):
    request = original_request()
    objects = [resolved_object({"kind": "receipt_row", "receipt_ref": "metadata",
        "row_pointer": f"/result/0/{i}"}, row=metadata("/synthetic/work/" + name, uuid=uuid),
        association={**association("/synthetic/work/" + name), "output_uuid": uuid})
        for i, (name, uuid) in enumerate((("a.fa", OBJECT_UUID),
            ("b.fa", "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            ("c.fa", "cccccccc-cccc-cccc-cccc-cccccccccccc")))]
    args = {"objects": [obj["selection"] for obj in objects], "generation": 0,
            "predecessor_receipt_ref": None}
    bindings = bound(request, "download_capability", args, original_task=original_task(request),
        objects=objects, predecessor_effect_refs=[])
    bindings["original_handoff_ref"] = "original_handoff"
    return prepare(h, "download_capability", args, bindings, selector=result_selector())


def upload_snapshot(operation, native, content=b"\x00\xffACGT\n"):
    call = operation["native_operands"]["call"]
    boundary = "gene-annotation-" + hashlib.sha256(call["filename"].encode() + b"\x00" + hashlib.sha256(content).digest()).hexdigest()
    multipart = (f'--{boundary}\r\nContent-Disposition: form-data; name="upload"; filename="{call["filename"]}"\r\n'
        'Content-Type: application/octet-stream\r\n\r\n').encode() + content + f"\r\n--{boundary}--\r\n".encode()
    body = json.dumps(native).encode()
    return SourceSnapshot("bvbrc_analysis", call["node_url"], {"kind": "upload", "node_url": call["node_url"],
        "filename": call["filename"], "input_bytes": len(content), "input_sha256": hashlib.sha256(content).hexdigest(),
        "multipart_field": "upload", "multipart_boundary": boundary}, "2026-10-24T12:00:00+00:00", body,
        "application/json", {"status": 200, "body_complete": True, "received_body_bytes": len(body),
        "effective_url": call["node_url"], "automatic_redirects": False, "headers": {},
        "request": {"method": "PUT", "url": call["node_url"], "body_bytes": len(multipart),
                    "body_sha256": hashlib.sha256(multipart).hexdigest()}})


def test_catalog_retains_all_native_records_and_original_indices(harness):
    op = prepare(harness, "enumerate_apps", {}, bound(original_request(), "enumerate_apps", {}))
    native = [{"id": "Homology", "parameters": [], "native_extra": [0, None, False]}, 9,
              {"id": "Homology", "parameters": [], "revision": "another-record"}]
    result = project(harness, op, rpc(op, native))
    assert result["contract"] == "CatalogReceipt"
    assert result["value"]["receipt"]["status"] == "partial"
    records = result["value"]["records"]
    assert [row["record_index"] for row in records] == [0, 1, 2]
    assert [row["native_record"] for row in records] == native
    assert [row["pointer"] for row in records] == ["/result/0/0", "/result/0/1", "/result/0/2"]
    assert [row["valid"] for row in records] == [True, False, True]
    assert all(row["definition_content"] is None for row in records)


def test_preparation_uses_actual_definition_binding_and_exact_native_parameters(harness):
    request, definition = original_request(), get_application_spec("Homology")
    args = {"definition": {"kind": "packaged", "required_application_id": "Homology"}}
    bindings = bound(request, "prepare", args, definition_envelope=definition)
    bindings["definition"] = {"content": content_binding(definition["source"]["content"].encode()), "pointer": ""}
    op = prepare(harness, "prepare", args, bindings)
    result = project(harness, op, None)
    assert result["contract"] == "PreparationReceipt"
    assert result["value"]["definition_evidence"] == bindings["definition"]
    assert result["value"]["native_parameters"] == request["parameters"]
    assert result["value"]["start_parameters"] == request["start_parameters"]
    assert "deployment_not_verified" in codes(result)
    assert harness.client.calls == []


def test_failed_preparation_returns_actual_common_receipt_without_native_defaults(harness):
    request = original_request()
    del request["parameters"]["input_fasta_data"]
    args = {"definition": {"kind": "packaged", "required_application_id": "Homology"}}
    bindings = bound(request, "prepare", args, definition_envelope=get_application_spec("Homology"))
    bindings["definition"] = {"content": content_binding(), "pointer": ""}
    op = prepare(harness, "prepare", args, bindings, request=request)
    result = project(harness, op, None)
    assert result["contract"] == "CommonReceipt"
    assert result["value"]["receipt_ref"] == "support_constructed_by_host"
    assert result["value"]["status"] == "failed"
    assert "selected_input_missing" in codes(result)


def test_unordered_create_confirms_exact_targets_and_retains_ancestor_and_empty_node(harness, tmp_path):
    op, native = create_operation(harness), create_rows()
    snapshot = rpc(op, native)
    journal, reservation, effects = issued(tmp_path, op)
    outcomes = confirm(harness, op, snapshot, effects)
    assert [row["state"] for row in outcomes] == ["confirmed", "confirmed"]
    assert [row["native_effect_identifiers"]["record_pointer"] for row in outcomes] == ["/result/0/2", "/result/0/1"]
    assert outcomes[0]["native_effect_identifiers"]["shock_url"].endswith(SHOCK_UUID)
    assert outcomes[0]["ancillary_effects"] == [{"pointer": "/result/0/0", "native_row": native[0], "valid": True}]
    closed = journal.record_outcome(reservation, outcomes)
    result = project(harness, op, snapshot, closed)
    assert result["contract"] == "WorkspaceReceipt"
    assert result["value"]["native_value"] == native
    assert result["value"]["rows"][2]["size"] == 0
    assert result["value"]["missing_requested_indices"] == []
    assert result["value"]["receipt"]["purpose"] == "support"


@pytest.mark.parametrize("defect", ["malformed", "wrong_path", "wrong_type", "native_error", "duplicate"])
def test_create_partial_member_preserves_good_target_without_positional_join(harness, tmp_path, defect):
    op, native = create_operation(harness), create_rows()
    if defect == "malformed":
        native[1] = ["bad"]
    elif defect == "wrong_path":
        native[1][0] = "wrong.fa"
    elif defect == "wrong_type":
        native[1][1] = "folder"
    elif defect == "native_error":
        native[1].append("permission denied")
    else:
        native.append(deepcopy(native[1]))
    snapshot = rpc(op, native)
    journal, reservation, effects = issued(tmp_path, op)
    outcomes = confirm(harness, op, snapshot, effects)
    assert [row["state"] for row in outcomes] == ["confirmed", "issued_unknown"]
    assert outcomes[1]["confirmation_source_ref"] is None
    assert outcomes[1]["failure"]["effect_outcome"] == "unknown"
    result = project(harness, op, snapshot, journal.record_outcome(reservation, outcomes))
    assert result["value"]["native_value"] == native
    assert result["value"]["missing_requested_indices"] == [1]
    assert result["value"]["rows"][2]["valid"] is True


def test_metadata_requires_exact_supplied_uuid_and_retains_failed_peer(harness):
    request = original_request()
    selected = [{"kind": "receipt_row", "receipt_ref": "earlier", "row_pointer": f"/result/0/{i}"} for i in range(2)]
    objects = [resolved_object(item) for item in selected]
    args = {"objects": selected, "options": {}}
    op = prepare(harness, "workspace_metadata", args, bound(request, "workspace_metadata", args, objects=objects))
    row = metadata()["native_row"]
    wrong = deepcopy(row)
    wrong[4] = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    native = [[row, None], [wrong, None]]
    result = project(harness, op, rpc(op, native))
    assert [row["valid"] for row in result["value"]["rows"]] == [True, False]
    assert result["value"]["missing_requested_indices"] == [1]
    assert result["value"]["rows"][1]["native_row"] == native[1]
    assert "workspace_target_conflict" in codes(result)


def test_listing_retains_map_keys_pointer_escaping_and_absent_empty_directory(harness):
    request = original_request()
    obj = resolved_object({"kind": "receipt_row", "receipt_ref": "earlier", "row_pointer": "/result/0/0"},
        row=metadata("/synthetic/work/a~b", type="folder"), association=association("/synthetic/work/a~b"))
    args = {"objects": [obj["selection"]], "options": {}}
    bindings = bound(request, "list_outputs", args, original_task=original_task(request), objects=[obj])
    bindings["original_handoff_ref"] = "original_handoff"
    op = prepare(harness, "list_outputs", args, bindings, selector=result_selector())
    native = {"/synthetic/work/a~b": [metadata("/synthetic/work/a~b/result.fa", size=14)["native_row"], ["bad"]]}
    result = project(harness, op, rpc(op, native))
    assert result["value"]["rows"][0]["pointer"] == "/result/0/~1synthetic~1work~1a~0b/0"
    assert result["value"]["rows"][0]["size"] == 14
    assert result["value"]["native_value"] == native
    empty = project(harness, op, rpc(op, {}))
    assert empty["value"]["rows"] == [] and empty["value"]["missing_requested_indices"] == []


def test_capability_valid_members_survive_malformed_and_null_peers_urls_remain_internal(harness, tmp_path):
    op = capability_operation(harness)
    native = ["https://download.invalid/secret-capability/a", {"bad": "member"}, None]
    snapshot = rpc(op, native)
    journal, reservation, effects = issued(tmp_path, op)
    event = harness.service.decode(op, snapshot)
    assert native[0] not in json.dumps(event)
    outcomes = confirm(harness, op, snapshot, effects)
    assert [row["state"] for row in outcomes] == ["confirmed", "issued_unknown", "issued_unknown"]
    assert native[0] not in json.dumps(outcomes)
    result = project(harness, op, snapshot, journal.record_outcome(reservation, outcomes))
    assert result["contract"] == "CapabilityReceipt"
    assert [entry["input_index"] for entry in result["value"]["entries"]] == [0, 1, 2]
    assert [entry["url"] for entry in result["value"]["entries"]] == [native[0], None, None]
    assert all(entry["expires_at"] is None and entry["expiry_evidence"] is None for entry in result["value"]["entries"])


def test_upload_exact_binary_byte_count_hash_and_unverified_algorithm_are_separate(harness, tmp_path):
    content = b"\x00\xffACGT\n"
    op = upload_operation(harness, "https://shock.invalid/node/" + SHOCK_UUID, content)
    native = {"status": 200, "error": None, "data": {"id": SHOCK_UUID, "file": {
        "size": 7, "checksum": {"sha256": hashlib.sha256(content).hexdigest(), "md5": "actual-native-field"}},
        "native_array": [0, False, None]}}
    snapshot = upload_snapshot(op, native, content)
    journal, reservation, effects = issued(tmp_path, op)
    outcomes = confirm(harness, op, snapshot, effects)
    assert outcomes[0]["state"] == "confirmed"
    result = project(harness, op, snapshot, journal.record_outcome(reservation, outcomes))
    value = result["value"]
    assert result["contract"] == "UploadReceipt"
    assert value["observed_file_size"] == value["input_content"]["byte_count"] == 7
    assert value["observed_checksums"] == native["data"]["file"]["checksum"]
    assert value["native_reply"] == native and value["confirmation"] == "accepted_bytes_match"
    assert "checksum_algorithm_unverified" in codes(result)


@pytest.mark.parametrize("defect", ["empty_node", "no_file", "wrong_node", "wrong_size", "wrong_hash", "wrong_name", "native_error"])
def test_upload_failures_never_confirm_from_empty_node_or_wrong_bytes(harness, tmp_path, defect):
    content = b"\x00\xffACGT\n"
    op = upload_operation(harness, "https://shock.invalid/node/" + SHOCK_UUID, content)
    native = {"status": 200, "error": None, "data": {"id": SHOCK_UUID,
        "file": {"size": 7, "checksum": {"sha256": hashlib.sha256(content).hexdigest()}}}}
    if defect == "empty_node":
        native["data"]["file"] = {"size": 0, "checksum": {}}
    elif defect == "no_file":
        native["data"].pop("file")
    elif defect == "wrong_node":
        native["data"]["id"] = OBJECT_UUID
    elif defect == "wrong_size":
        native["data"]["file"]["size"] = 6
    elif defect == "wrong_hash":
        native["data"]["file"]["checksum"]["sha256"] = "f" * 64
    elif defect == "wrong_name":
        native["data"]["file"]["name"] = "other.fa"
    else:
        native.update(status=403, error=["permission denied"])
    snapshot = upload_snapshot(op, native, content)
    journal, reservation, effects = issued(tmp_path, op)
    outcomes = confirm(harness, op, snapshot, effects)
    assert outcomes[0]["state"] == "issued_unknown" and outcomes[0]["failure"]["effect_outcome"] == "unknown"
    result = project(harness, op, snapshot, journal.record_outcome(reservation, outcomes))
    assert result["contract"] == "UploadReceipt"
    assert result["value"]["native_reply"] == native
    assert result["value"]["confirmation"] in {"partial", "unknown", "failed"}


def test_deliberate_empty_payload_needs_explicit_sha256_acceptance(harness, tmp_path):
    op = upload_operation(harness, "https://shock.invalid/node/" + SHOCK_UUID, b"")
    native = {"status": 200, "error": None, "data": {"id": SHOCK_UUID,
        "file": {"size": 0, "checksum": {"sha256": hashlib.sha256(b"").hexdigest()}}}}
    _, _, effects = issued(tmp_path, op)
    assert confirm(harness, op, upload_snapshot(op, native, b""), effects)[0]["state"] == "confirmed"
    native["data"]["file"]["checksum"] = {}
    assert confirm(harness, op, upload_snapshot(op, native, b""), effects)[0]["state"] == "issued_unknown"


@pytest.mark.parametrize("field", ["params", "parameters"])
def test_task_handoff_retains_exact_scheduler_source_and_original_submitted_parameters(harness, tmp_path, field):
    op = submit_operation(harness)
    expected = deepcopy(op["native_operands"]["request"]["parameters"])
    returned = {**expected, "_preflight": {"cpu": 3, "run_time": 0}}
    native = {"id": 123, "application_id": "Homology", "state_code": "Q",
        field: json.dumps(returned) if field == "params" else returned,
        "app_spec": json.dumps({"id": "Homology"}), "unknown_native_array": [0, False, None]}
    snapshot = rpc(op, native)
    journal, reservation, effects = issued(tmp_path, op)
    outcomes = confirm(harness, op, snapshot, effects)
    assert outcomes[0]["state"] == "confirmed"
    result = project(harness, op, snapshot, journal.record_outcome(reservation, outcomes))
    assert result["contract"] == "TaskHandoff"
    value, task = result["value"], result["value"]["original_task"]
    assert value["native_submission_record"] == native
    assert task["submitted_parameters"] == expected
    assert "_preflight" not in task["submitted_parameters"]
    assert task["scheduler_returned_parameters"]["value"] == returned
    assert task["scheduler_returned_parameters"]["evidence"]["pointer"] == "/result/0/" + field
    assert task["effective_parameters"] is None
    assert task["submission_source_ref"] == "source_retained_native"
    assert task["submission_receipt_ref"] == value["receipt"]["receipt_ref"]
    assert value["effect_receipt_ref"] == effects[0]["effect_ref"]


def test_failed_acknowledged_task_confirms_submission_without_usable_handoff(harness, tmp_path):
    op = submit_operation(harness)
    snapshot = rpc(op, {"id": "123", "application_id": "Homology", "state_code": "F"})
    journal, reservation, effects = issued(tmp_path, op)
    event = harness.service.decode(op, snapshot)
    assert event["facts"]["submission_acknowledged"] is True and not event["handoff_ready"]
    outcomes = confirm(harness, op, snapshot, effects)
    assert outcomes[0]["state"] == "confirmed"
    result = project(harness, op, snapshot, journal.record_outcome(reservation, outcomes))
    assert result["contract"] == "CommonReceipt" and result["value"]["status"] == "failed"
    assert "native_task_failed" in codes(result)


@pytest.mark.parametrize("raw", [{"id": "123", "application_id": "Other"},
    {"id": "123", "params": '{"blast_program":"blastp"}'},
    {"id": "123", "app_spec": '{"id":"Other"}'},
    {"id": "123", "params": '{"a":1,"a":2}'}, {"similar": {"id": "123"}}, {}])
def test_submission_conflicts_do_not_confirm_or_build_handoff(harness, tmp_path, raw):
    op = submit_operation(harness)
    snapshot = rpc(op, raw)
    journal, reservation, effects = issued(tmp_path, op)
    outcomes = confirm(harness, op, snapshot, effects)
    assert outcomes[0]["state"] == "issued_unknown"
    result = project(harness, op, snapshot, journal.record_outcome(reservation, outcomes))
    assert result["contract"] == "CommonReceipt"


def test_task_observation_keeps_valid_exact_member_and_native_timing_amid_bad_peers(harness):
    op = status_operation(harness)
    native = {"123": {"id": 123, "app": "Homology", "status": "running", "elapsed_time": "00:01:03",
        "start_time": "0000-00-00 00:00:00", "native_extra": [1, 2, 3]}, "999": ["malformed"]}
    result = project(harness, op, rpc(op, native))
    assert result["contract"] == "TaskObservation"
    assert result["value"]["native_map"] == native
    assert result["value"]["selected_record_pointer"] == "/result/0/123"
    assert result["value"]["state"] == "running"
    assert result["value"]["native_timing"]["elapsed_time"] == "00:01:03"
    assert result["value"]["native_timing"]["start_time"] == "0000-00-00 00:00:00"


@pytest.mark.parametrize("native", [{"124": {"id": 124, "app": "Homology", "status": "completed"}},
    {"123": {"id": 124, "app": "Homology", "status": "completed"}}])
def test_task_observation_does_not_infer_original_from_another_task(harness, native):
    op = status_operation(harness)
    result = project(harness, op, rpc(op, native))
    assert result["contract"] == "CommonReceipt" and "original_task_mismatch" in codes(result)


@pytest.mark.parametrize("file", ["stdout", "stderr", "job_result_id", "job_result_folder"])
def test_task_info_exact_file_and_full_representation_binding(harness, file):
    op = status_operation(harness, "task_info", file)
    snapshot = harness.client.task_info("123", file)
    result = project(harness, op, snapshot)
    assert result["contract"] == "TaskInfoReceipt"
    value = result["value"]
    assert value["reported_object_uuid"] == (OBJECT_UUID if file.startswith("job_result") else None)
    assert value["local_window"] is None
    assert value["receipt"]["snapshot"]["content"]["byte_count"] == len(snapshot.content)
    assert value["receipt"]["snapshot"]["content"]["sha256"] == hashlib.sha256(snapshot.content).hexdigest()


def test_task_info_uuid_in_log_is_not_output_identity_and_bad_uuid_retains_bytes(harness):
    op = status_operation(harness, "task_info", "stdout")
    snapshot = changed_body(harness.client.task_info("123", "stdout"), OBJECT_UUID.encode())
    assert project(harness, op, snapshot)["value"]["reported_object_uuid"] is None
    op = status_operation(harness, "task_info", "job_result_id")
    snapshot = changed_body(harness.client.task_info("123", "job_result_id"), b"prefix " + OBJECT_UUID.encode())
    result = project(harness, op, snapshot)
    assert result["contract"] == "TaskInfoReceipt" and result["value"]["reported_object_uuid"] is None
    assert "task_info_object_invalid" in codes(result)


@pytest.mark.parametrize("file", ["stdout", "job_result_id"])
def test_incomplete_task_info_retains_partial_representation_without_uuid_claim(harness, file):
    op = status_operation(harness, "task_info", file)
    snapshot = harness.client.task_info("123", file)
    snapshot = replace(snapshot, transport={**snapshot.transport, "body_complete": False})
    result = project(harness, op, snapshot)
    assert result["contract"] == "TaskInfoReceipt"
    assert result["value"]["body_complete"] is False
    assert result["value"]["reported_object_uuid"] is None
    assert result["value"]["receipt"]["snapshot"]["content"]["byte_count"] == len(snapshot.content)


@pytest.mark.parametrize("defect", ["wrong_rpc_id", "rpc_error", "http_error", "incomplete", "duplicate_json", "nonfinite_json",
    "wrong_request", "wrong_sent_digest", "wrong_endpoint", "wrong_binding_digest", "wrong_frozen_selection", "wrong_binding_transport"])
def test_native_or_binding_corruption_retains_common_and_issued_uncertainty(harness, tmp_path, defect):
    op = submit_operation(harness)
    snapshot = rpc(op, {"id": "123", "application_id": "Homology", "state_code": "Q"})
    envelope = json.loads(snapshot.content)
    if defect == "wrong_rpc_id":
        envelope["id"] = "unrelated-correlation"
        snapshot = changed_body(snapshot, json.dumps(envelope).encode())
    elif defect == "rpc_error":
        envelope.pop("result")
        envelope["error"] = {"code": -1, "message": "native failure"}
        snapshot = changed_body(snapshot, json.dumps(envelope).encode())
    elif defect in ("http_error", "incomplete"):
        snapshot = replace(snapshot, transport={**snapshot.transport,
            "status": 503 if defect == "http_error" else 200, "body_complete": defect != "incomplete"})
    elif defect == "duplicate_json":
        snapshot = changed_body(snapshot, snapshot.content[:-1] + b',"result":[{"id":"999"}]}')
    elif defect == "nonfinite_json":
        snapshot = changed_body(snapshot, snapshot.content[:-1] + b',"extra":NaN}')
    elif defect == "wrong_request":
        snapshot = replace(snapshot, request={"kind": "rpc", "rpc": {**snapshot.request["rpc"], "id": "different"}})
    elif defect == "wrong_sent_digest":
        snapshot = replace(snapshot, transport={**snapshot.transport,
            "request": {**snapshot.transport["request"], "body_sha256": "f" * 64}})
    elif defect == "wrong_endpoint":
        other = "https://unrelated.invalid/rpc"
        snapshot = replace(snapshot, url=other, transport={**snapshot.transport, "effective_url": other,
            "request": {**snapshot.transport["request"], "url": other}})
    source = binding(op, snapshot)
    if defect == "wrong_binding_digest":
        source["content"]["sha256"] = "f" * 64
    elif defect == "wrong_frozen_selection":
        source["selected_operands"]["native_operands"]["arguments"]["input_evidence_refs"] = ["not-selected"]
    elif defect == "wrong_binding_transport":
        source["transport"]["status"] = 201
    journal, reservation, effects = issued(tmp_path, op)
    outcomes = confirm(harness, op, snapshot, effects, snapshot_binding=source)
    assert outcomes[0]["state"] == "issued_unknown"
    assert outcomes[0]["confirmation_source_ref"] is None and outcomes[0]["failure"]["effect_outcome"] == "unknown"
    common_value = common(op, snapshot, effects)
    common_value["snapshot"] = source
    result = project(harness, op, snapshot, journal.record_outcome(reservation, outcomes), receipt=common_value)
    assert result["contract"] == "CommonReceipt"
    assert result["value"]["snapshot"] == source and result["value"]["status"] == "failed"


@pytest.mark.parametrize("state", ["confirmed", "not_sent"])
def test_confirmed_and_not_sent_closed_journal_rows_do_not_change_on_replay(harness, tmp_path, state):
    op = submit_operation(harness)
    snapshot = rpc(op, {"id": "123"}) if state == "confirmed" else None
    journal, reservation, effects = issued(tmp_path, op)
    outcomes = confirm(harness, op, snapshot, effects)
    if state == "not_sent":
        # Only the executor can supply this definitive pretransport exception;
        # the receipt confirmer never derives it from a native response.
        outcomes[0].update(state="not_sent", confirmation_source_ref=None, native_effect_identifiers={}, ancillary_effects=[],
            failure={"code": "fixture_definitive_pretransport", "phase": "transport", "affected_refs": [],
            "affected_pointers": [], "effect_outcome": "not_sent", "valid_record_refs": [], "requirements": []})
    closed = journal.record_outcome(reservation, outcomes)
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*.json")}
    event = harness.service.decode(op, snapshot)
    replay = confirm_appservice_effects(op, event, None, snapshot_binding=None, effect_receipts=closed)
    assert replay == outcomes
    assert journal.record_outcome(reservation, replay) == closed
    assert {str(p): p.read_bytes() for p in tmp_path.rglob("*.json")} == before


def test_missing_response_and_unconfirmed_or_wrong_source_effect_never_make_handoff(harness, tmp_path):
    op = submit_operation(harness)
    snapshot = rpc(op, {"id": "123"})
    journal, reservation, effects = issued(tmp_path, op)
    outcomes = confirm(harness, op, None, effects)
    assert outcomes[0]["state"] == "issued_unknown"
    assert outcomes[0]["failure"]["code"] == "issued_effect_unknown"
    result = project(harness, op, snapshot, effects)
    assert result["contract"] == "CommonReceipt"
    outcomes = confirm(harness, op, snapshot, effects)
    outcomes[0]["confirmation_source_ref"] = "unrelated_source"
    closed = journal.record_outcome(reservation, outcomes)
    assert project(harness, op, snapshot, closed)["contract"] == "CommonReceipt"


def test_input_bindings_and_origin_are_detached_and_never_synthesized(harness, tmp_path):
    op = submit_operation(harness)
    snapshot = rpc(op, {"id": "123"})
    journal, reservation, effects = issued(tmp_path, op)
    closed = journal.record_outcome(reservation, confirm(harness, op, snapshot, effects))
    receipt = common(op, snapshot, closed)
    originals = deepcopy((op, closed, receipt))
    result = project(harness, op, snapshot, closed, receipt=receipt)
    assert {"submission_application_echo_unobserved", "submission_parameters_echo_unobserved",
            "native_state_unknown"} <= codes(result)
    result["value"]["receipt"]["origin"]["episode_id"] = "changed-output-only"
    assert (op, closed, receipt) == originals
    receipt["origin"]["operation_key"] = "synthetic-run:other:0"
    with pytest.raises(ValueError, match="receipt_origin_conflict"):
        project(harness, op, snapshot, closed, receipt=receipt)
    changed = deepcopy(closed)
    changed[0]["descriptor"]["payload_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="effect_receipts_binding_conflict"):
        project(harness, op, snapshot, changed)


def test_uuid_only_capability_retains_unknown_path(harness, tmp_path):
    request = original_request()
    selection = {"kind": "task_info_object", "receipt_ref": "task-info-original"}
    obj = {"selection": selection, "native_reference": OBJECT_UUID,
        "object": {"path": None, "uuid": OBJECT_UUID, "type": None, "metadata_receipt_ref": None},
        "metadata": None, "task_association": {"kind": "task_info_object", "evidence_ref": "task-info-native",
        "pointer": "", "task_id": "123", "output_path": None, "output_uuid": OBJECT_UUID,
        "byte_version_status": "unknown", "version_evidence": []}, "identity": "native-source-qualified:" + OBJECT_UUID}
    args = {"objects": [selection], "generation": 0, "predecessor_receipt_ref": None}
    bindings = bound(request, "download_capability", args, original_task=original_task(request),
                     objects=[obj], predecessor_effect_refs=[])
    bindings["original_handoff_ref"] = "original_handoff"
    op = prepare(harness, "download_capability", args, bindings, selector=result_selector())
    snapshot = rpc(op, ["https://download.invalid/exact-capability/file"])
    journal, reservation, effects = issued(tmp_path, op)
    outcomes = confirm(harness, op, snapshot, effects)
    assert outcomes[0]["state"] == "confirmed"
    result = project(harness, op, snapshot, journal.record_outcome(reservation, outcomes))
    assert result["value"]["entries"][0]["object"]["path"] is None
    assert result["value"]["entries"][0]["task_association"]["output_path"] is None
    assert result["value"]["entries"][0]["object"]["uuid"] == OBJECT_UUID


def test_failed_host_common_receipt_is_not_upgraded_to_usable_handoff(harness, tmp_path):
    op = submit_operation(harness)
    snapshot = rpc(op, {"id": "123"})
    journal, reservation, effects = issued(tmp_path, op)
    closed = journal.record_outcome(reservation, confirm(harness, op, snapshot, effects))
    receipt = common(op, snapshot, closed)
    receipt["status"] = "failed"
    assert project(harness, op, snapshot, closed, receipt=receipt)["contract"] == "CommonReceipt"


@pytest.mark.parametrize("kind", ["submit", "workspace_create", "upload", "download_capability"])
def test_effect_payload_cannot_be_detached_from_selected_native_operands(harness, tmp_path, kind):
    if kind == "submit":
        op, native = submit_operation(harness), {"id": "123"}
    elif kind == "workspace_create":
        op, native = create_operation(harness), create_rows()
    elif kind == "upload":
        op = upload_operation(harness, "https://shock.invalid/node/" + SHOCK_UUID)
        native = {"status": 200, "error": None, "data": {"id": SHOCK_UUID}}
    else:
        op, native = capability_operation(harness), [None, None, None]
    snapshot = upload_snapshot(op, native) if kind == "upload" else rpc(op, native)
    event = harness.service.decode(op, snapshot)
    _, _, effects = issued(tmp_path, op)
    changed = deepcopy(op)
    call = changed["native_operands"]["call"]
    if kind == "submit":
        call["rpc_request"]["params"][1]["blast_max_hits"] = 900
    elif kind == "workspace_create":
        call["rpc_request"]["params"][0]["objects"][0][0] = "/synthetic/other/target"
    elif kind == "upload":
        call["filename"] = "other.fa"
    else:
        call["rpc_request"]["params"][0]["objects"][0] = "/synthetic/other/target"
    with pytest.raises(ValueError, match="effect_payload_binding_conflict"):
        confirm_appservice_effects(changed, event, snapshot,
            snapshot_binding=binding(changed, snapshot), effect_receipts=effects)
