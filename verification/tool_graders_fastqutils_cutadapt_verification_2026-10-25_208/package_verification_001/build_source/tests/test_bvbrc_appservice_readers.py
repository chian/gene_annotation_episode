import base64
from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.bvbrc_appservice_contracts import ContractValidationError, validate_contract
from gene_annotation_episode.bvbrc_appservice_readers import (
    decode_catalog, decode_job_result, decode_task_info, decode_upload,
    qualify_download, validate_bundle,
)


UUID = "11111111-2222-3333-4444-555555555555"
UUID2 = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
URL = "https://controlled.invalid/download/exact-key/file"
SHA = hashlib.sha256(b"ACGT").hexdigest()


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("pure support reader attempted a network call")
    monkeypatch.setattr("socket.socket", forbidden)


def task():
    return {"resource_id": "api:configured", "task_id": "123", "required_application_id": "Homology",
        "native_application_id": "Homology", "submitted_parameters": {"output_file": "Original name"},
        "submitted_start_parameters": {}, "scheduler_returned_parameters": None, "effective_parameters": None,
        "submission_receipt_ref": "support:submit", "submission_operation_key": "run:launch:3",
        "submission_source_ref": "source:submit"}


def workspace_object(type="txt", uuid=UUID, path="/owner/home/.output/file"):
    return {"path": path, "uuid": uuid, "type": type, "metadata_receipt_ref": "support:metadata"}


def association():
    obj = workspace_object()
    return {"kind": "task_result_manifest", "evidence_ref": "source:manifest", "pointer": "/output_files/0",
            "task_id": "123", "output_path": obj["path"], "output_uuid": obj["uuid"],
            "byte_version_status": "unknown", "version_evidence": []}


def capability():
    return {"input_index": 1, "object_selection": {"kind": "manifest_member", "manifest_receipt_ref": "manifest:1", "output_index": 0},
            "object": workspace_object(), "task_association": association(), "url": URL,
            "issued_observed_at": "2026-10-24T12:00:00+00:00", "expires_at": None, "expiry_evidence": None}


def object_binding(size=None):
    obj = workspace_object()
    if size is None:
        return {"object": obj, "metadata": None}
    parent, _, name = obj["path"].rpartition("/")
    row = [name, obj["type"], parent + "/", "2026-10-24T11:00:00", obj["uuid"], "owner", size, {}, {}, "w", "n", ""]
    return {"object": obj, "metadata": {"pointer": "/result/0/0", "native_row": row, "valid": True,
        "path": obj["path"], "uuid": obj["uuid"], "type": obj["type"], "shock_url": None,
        "creation_time": row[3], "size": size, "error": None}}


def snapshot(content=b"ACGT", status=200, headers=None, selected_range=None, complete=True):
    headers = {"content-length": str(len(content))} if headers is None else headers
    return SourceSnapshot("bvbrc_analysis", URL,
        {"kind": "download", "url": URL, "requested_byte_range": selected_range},
        "2026-10-24T12:10:00+00:00", content, "application/octet-stream",
        {"status": status, "headers": deepcopy(headers), "header_items": [[k, v] for k, v in headers.items()],
         "effective_url": URL, "automatic_redirects": False, "body_complete": complete,
         "received_body_bytes": len(content), "request": {"method": "GET", "url": URL}})


def codes(result):
    for diagnostic in result["diagnostics"]:
        validate_contract("Diagnostic", diagnostic)
    return {d["code"] for d in result["diagnostics"]}


def manifest():
    return {"id": "123", "app": {"id": "Homology", "parameters": []},
            "parameters": {"output_file": "Actual effective name", "bool_value": 1},
            "output_files": [[workspace_object()["path"], UUID]], "success": 1,
            "start_time": 1000.2, "end_time": 1001.7, "elapsed_time": 1.5,
            "hostname": "native-host", "job_output": {"native": [0, False, None]}}


def read_manifest(value=None, *, content=None, original_task=None, obj=None):
    content = json.dumps(manifest() if value is None else value).encode() if content is None else content
    return decode_job_result(content, original_task=task() if original_task is None else original_task,
        object_binding=workspace_object(type="job_result", path="/owner/home/output") if obj is None else obj,
        evidence_ref="source:manifest")


def test_catalog_retains_invalid_rows_full_definitions_duplicate_ids_and_indices():
    native = [{"id": "Homology", "parameters": [], "full": {"untrimmed": [1, 2, 3]}},
              None, {"id": "Homology", "parameters": [{"id": "repeat"}, {"id": "repeat"}]},
              {"id": "broken", "parameters": "invalid"}]
    result = decode_catalog(native, source_ref="source:catalog")
    assert result["status"] == "partial"
    assert result["native"] == native
    assert [r["record_index"] for r in result["records"]] == [0, 1, 2, 3]
    assert [r["valid"] for r in result["records"]] == [True, False, True, False]
    assert result["records"][2]["pointer"] == "/result/0/2"
    assert result["records"][2]["native_record"]["parameters"] == [{"id": "repeat"}] * 2
    native[0]["parameters"].append("changed")
    assert result["native"][0]["parameters"] == []
    assert codes(result) == {"catalog_definition_invalid"}
    assert decode_catalog([], source_ref="source:catalog")["status"] == "ok"
    assert decode_catalog({"wrong": []}, source_ref="source:catalog")["status"] == "invalid"


def test_upload_checks_node_size_sha256_and_preserves_other_checksum_algorithms():
    native = {"status": 200, "error": None, "data": {"id": UUID, "file": {"size": 4,
        "checksum": {"sha256": SHA, "md5": "actual-md5-field"}}, "version": "native-version"}}
    result = decode_upload(native, expected_node_id=UUID, expected_bytes=4, supplied_sha256=SHA)
    assert result["status"] == "ok"
    assert result["value"]["confirmation"] == "accepted_bytes_match"
    assert result["native"] == native
    assert result["value"]["checksum_comparisons"] == [
        {"algorithm": "sha256", "native_value": SHA, "matches_supplied": True},
        {"algorithm": "md5", "native_value": "actual-md5-field", "matches_supplied": None}]
    assert "checksum_algorithm_unverified" in codes(result)


@pytest.mark.parametrize("change,expected", [
    ({"id": UUID2}, "upload_node_mismatch"),
    ({"file": {"size": 0, "checksum": {}}}, "upload_size_mismatch"),
    ({"file": {"size": True, "checksum": {}}}, "native_upload_size_invalid"),
    ({"file": {"size": 4, "checksum": {"sha256": "b" * 64}}}, "upload_checksum_mismatch"),
    ({"file": {"size": 4, "checksum": ["bad"]}}, "native_upload_checksum_invalid"),
])
def test_upload_conflicts_keep_native_reply_and_partial_observations(change, expected):
    native = {"status": 200, "error": None, "data": {"id": UUID, "file": {"size": 4, "checksum": {"sha256": SHA}}}}
    native["data"].update(change)
    result = decode_upload(native, expected_node_id=UUID, expected_bytes=4, supplied_sha256=SHA)
    assert expected in codes(result)
    assert result["native"] == native
    assert result["value"]["confirmation"] in {"partial", "unknown"}
    assert result["status"] in {"partial", "invalid"}


def test_empty_node_metadata_is_not_completed_upload_and_missing_checksum_is_unknown():
    empty_node = {"status": 200, "error": None, "data": {"id": UUID, "file": {"size": 0, "checksum": {}}}}
    result = decode_upload(empty_node, expected_node_id=UUID, expected_bytes=4, supplied_sha256=SHA)
    assert result["value"]["confirmation"] == "partial"
    assert "upload_size_mismatch" in codes(result)
    missing = {"status": 200, "error": None, "data": {"id": UUID}}
    result = decode_upload(missing, expected_node_id=UUID, expected_bytes=4, supplied_sha256=SHA)
    assert result["status"] == "ok"
    assert result["value"]["confirmation"] == "accepted_identity_only"
    assert result["value"]["observed_file_size"] is None
    result = decode_upload({"status": 403, "data": None, "error": ["native permission message"]},
        expected_node_id=UUID, expected_bytes=4, supplied_sha256=SHA)
    assert result["status"] == "failed"
    assert result["value"]["confirmation"] == "failed"


def test_observed_empty_upload_and_download_are_distinct_from_unknown_or_failed():
    empty_sha = hashlib.sha256(b"").hexdigest()
    native = {"status": 200, "error": None, "data": {"id": UUID, "file": {"size": 0, "checksum": {"sha256": empty_sha}}}}
    result = decode_upload(native, expected_node_id=UUID, expected_bytes=0, supplied_sha256=empty_sha)
    assert result["status"] == "ok"
    assert result["value"]["confirmation"] == "accepted_bytes_match"
    result = qualify_download(snapshot(content=b""), capability=capability(), object_binding=object_binding(0))
    assert result["status"] == "ok"
    assert result["value"]["body_complete"] is True
    assert result["value"]["object_complete"] == "yes"
    assert result["value"]["total_size"] == result["value"]["byte_count"] == 0
    assert result["value"]["sha256"] == empty_sha


@pytest.mark.parametrize("suffix", [b"", b"\n", b"\r\n"])
def test_task_info_reads_exact_uuid_and_retains_complete_representation(suffix):
    data = UUID.encode() + suffix
    result = decode_task_info(data, task_id="123", file="job_result_id")
    assert result["status"] == "ok"
    assert result["value"]["reported_object_uuid"] == UUID
    assert base64.b64decode(result["native"]["data"]) == data
    assert "body_complete" not in result["value"]  # the byte-only reader cannot know this


@pytest.mark.parametrize("content", [b"", b"prefix " + UUID.encode(), UUID.encode() + b"\nsecond", UUID.encode() + b"\n\n", b"\xff", b" " + UUID.encode()])
def test_task_info_does_not_extract_ids_from_malformed_native_bodies(content):
    result = decode_task_info(content, task_id="123", file="job_result_folder")
    assert result["status"] == "invalid"
    assert result["value"]["reported_object_uuid"] is None
    assert "task_info_object_invalid" in codes(result)
    assert base64.b64decode(result["native"]["data"]) == content


def test_logs_preserve_binary_bytes_and_never_infer_status_or_object():
    content = b"running\xff\x00" + UUID.encode() + b"\ncompleted 100%"
    result = decode_task_info(content, task_id="123", file="stdout")
    assert result["status"] == "ok"
    assert result["value"]["reported_object_uuid"] is None
    assert result["value"]["text"] is None
    assert base64.b64decode(result["native"]["data"]) == content
    assert "state" not in result["value"]


def test_manifest_preserves_effective_parameters_failures_and_full_native_data():
    original = task()
    native = manifest()
    native["success"] = 0
    result = read_manifest(native, original_task=original)
    assert result["status"] == "ok"
    assert result["native"] == native
    assert result["value"]["success"] == 0
    assert result["value"]["effective_parameters"] == native["parameters"]
    assert original == task()  # native defaults/overrides never rewrite submission
    association = result["value"]["outputs"][0]["association"]
    assert association["byte_version_status"] == "unknown"
    assert association["pointer"] == "/output_files/0"
    assert association["output_uuid"] == UUID
    assert "output_version_unproven" in codes(result)


def test_manifest_invalid_member_does_not_discard_valid_peers_or_reindex():
    native = manifest()
    native["output_files"] = [["/owner/home/.output/file", UUID], ["same-name-only"],
                              ["/owner/home/.output/other", UUID2]]
    result = read_manifest(native)
    assert result["status"] == "partial"
    assert [r["output_index"] for r in result["value"]["outputs"]] == [0, 2]
    assert [r["valid"] for r in result["records"]] == [True, False, True]
    assert result["records"][1]["native_record"] == ["same-name-only"]
    assert result["native"]["output_files"] == native["output_files"]


@pytest.mark.parametrize("field,value", [("id", "124"), ("id", 123), ("app", {"id": "MSA"})])
def test_other_task_or_application_never_receives_original_output_associations(field, value):
    native = manifest()
    native[field] = value
    result = read_manifest(native)
    assert result["status"] == "invalid"
    assert result["value"]["outputs"] == []
    assert result["records"][0]["native_record"] == native["output_files"][0]
    assert result["records"][0]["association"] is None
    assert "task_manifest_mismatch" in codes(result)


@pytest.mark.parametrize("content", [b'{"id":"wrong","id":"123","app":{"id":"Homology"},"parameters":{},"output_files":[]}',
    b'{"id":"123","unrepresentable":1e999}', b'{"value":NaN}', b'{"value":1e-9999}', b'{"incomplete":', b'\xff'])
def test_malformed_manifest_retains_exact_bytes_without_trusting_projection(content):
    result = read_manifest(content=content)
    assert result["status"] == "invalid"
    assert result["value"]["outputs"] == []
    assert base64.b64decode(result["raw_content"]["data"]) == content


def test_manifest_empty_output_is_valid_parse_not_a_scientific_zero_score():
    native = manifest()
    native["output_files"] = []
    result = read_manifest(native)
    assert result["status"] == "ok"
    assert result["records"] == []
    assert "score" not in result["value"]
    assert "usable_handoff" not in result["value"]


def test_whole_download_ignoring_range_remains_whole_with_original_range():
    source = snapshot(content=b"ACGTACGT", selected_range=[2, 3])
    result = qualify_download(source, capability=capability(), object_binding=object_binding(8))
    assert result["status"] == "ok"
    assert result["value"]["byte_count"] == 8
    assert result["value"]["sha256"] == hashlib.sha256(b"ACGTACGT").hexdigest()
    assert result["value"]["requested_range"] == [2, 3]
    assert result["value"]["observed_range"] is None
    assert result["value"]["object_complete"] == "yes"
    assert source.content == b"ACGTACGT"
    assert "range_ignored" in codes(result)


def test_complete_range_is_not_complete_object():
    source = snapshot(content=b"GT", status=206, headers={"content-range": "bytes 2-3/8", "content-length": "2"}, selected_range=[2, 3])
    result = qualify_download(source, capability=capability(), object_binding=object_binding(8))
    assert result["status"] == "ok"
    assert result["value"]["body_complete"] is True
    assert result["value"]["object_complete"] == "no"
    assert result["value"]["observed_range"] == {"start": 2, "end_inclusive": 3, "total_size": 8}
    assert result["value"]["received_range"] == result["value"]["observed_range"]


def test_incomplete_206_retains_header_interval_and_actual_received_prefix():
    source = snapshot(content=b"GT", status=206, headers={"content-range": "bytes 2-5/8", "content-length": "4"}, selected_range=[2, 5], complete=False)
    result = qualify_download(source, capability=capability(), object_binding=object_binding(8))
    assert result["status"] == "partial"
    assert result["value"]["body_complete"] is False
    assert result["value"]["object_complete"] == "no"
    assert result["value"]["observed_range"]["end_inclusive"] == 5
    assert result["value"]["received_range"]["end_inclusive"] == 3
    assert result["value"]["byte_count"] == 2
    assert "download_incomplete" in codes(result)
    assert source.content == b"GT"


def test_unframed_200_keeps_object_completeness_unknown_without_metadata():
    source = snapshot(headers={})
    result = qualify_download(source, capability=capability(), object_binding=object_binding())
    assert result["value"]["body_complete"] is True
    assert result["value"]["object_complete"] == "unknown"
    assert result["value"]["total_size"] is None
    assert "object_completeness_unproven" in codes(result)
    qualified = qualify_download(source, capability=capability(), object_binding=object_binding(4))
    assert qualified["value"]["object_complete"] == "yes"


@pytest.mark.parametrize("headers,selected", [
    ({"content-range": "bytes 1-2/8", "content-length": "2"}, [2, 3]),
    ({"content-range": "bytes 2-8/8", "content-length": "2"}, [2, 8]),
    ({"content-range": "not-a-range", "content-length": "2"}, [2, 3]),
    ({"content-length": "2"}, [2, 3]),
])
def test_malformed_or_conflicting_ranges_never_claim_complete_object(headers, selected):
    source = snapshot(content=b"GT", status=206, headers=headers, selected_range=selected)
    result = qualify_download(source, capability=capability(), object_binding=object_binding(8))
    assert result["value"]["object_complete"] != "yes"
    assert "range_conflict" in codes(result)
    assert result["native"]["transport"]["headers"] == headers


def test_whole_object_range_and_clipped_upper_endpoint():
    source = snapshot(status=206, headers={"content-range": "bytes 0-3/4", "content-length": "4"}, selected_range=[0, 100])
    result = qualify_download(source, capability=capability(), object_binding=object_binding(4))
    assert result["status"] == "ok"
    assert result["value"]["object_complete"] == "yes"


def test_object_metadata_size_conflict_and_overwritten_version_remain_distinct():
    source = snapshot(content=b"changed-body")
    result = qualify_download(source, capability=capability(), object_binding=object_binding(4))
    assert "object_size_conflict" in codes(result)
    assert result["value"]["object_complete"] != "yes"
    same_size = qualify_download(snapshot(content=b"TTTT"), capability=capability(), object_binding=object_binding(4))
    assert same_size["value"]["object_complete"] == "yes"
    assert same_size["value"]["sha256"] != SHA
    assert capability()["task_association"]["byte_version_status"] == "unknown"
    assert "producer_bytes_bound" not in json.dumps(same_size)


@pytest.mark.parametrize("field,value", [("path", "/other/task/same-name/file"), ("uuid", UUID2), ("type", "folder")])
def test_download_does_not_join_same_names_or_other_objects(field, value):
    obj = object_binding(4)
    obj["object"][field] = value
    with pytest.raises(ContractValidationError):
        qualify_download(snapshot(), capability=capability(), object_binding=obj)


def test_metadata_projection_must_agree_with_its_native_tuple():
    obj = object_binding(4)
    obj["metadata"]["native_row"][6] = 5
    with pytest.raises(ContractValidationError, match="metadata_native_conflict"):
        qualify_download(snapshot(), capability=capability(), object_binding=obj)


def test_expired_capability_http_failure_preserves_body_and_has_no_refresh():
    cap = capability()
    cap["expires_at"] = "2026-10-24T12:01:00+00:00"
    cap["expiry_evidence"] = {"content": {"source_ref": "source:expiry", "artifact_field": "artifact_ref",
        "artifact_ref": "artifact:expiry", "sha256": SHA, "byte_count": 4}, "pointer": "/expires_at"}
    source = snapshot(content=b"expired capability", status=403)
    result = qualify_download(source, capability=cap, object_binding=object_binding(4))
    assert result["status"] == "failed"
    assert {"capability_http_error", "capability_expired_at_retrieval"} <= codes(result)
    assert result["value"]["byte_count"] == len(b"expired capability")
    assert source.content == b"expired capability"


def test_conflicting_duplicate_headers_and_encoding_are_not_silent_success():
    source = snapshot()
    source.transport["header_items"].insert(0, ["Content-Length", "999"])
    result = qualify_download(source, capability=capability(), object_binding=object_binding(4))
    assert "conflicting_http_header" in codes(result)
    assert result["value"]["object_complete"] == "unknown"
    source = snapshot(headers={"content-length": "4", "content-encoding": "gzip"})
    result = qualify_download(source, capability=capability(), object_binding=object_binding(4))
    assert "content_encoding_uninterpreted" in codes(result)
    assert result["value"]["object_complete"] == "unknown"


def bundle():
    member = {"member_id": "sequence", "member_pointer": "/records/0", "length": 4,
              "molecule": "dna", "sequence_sha256": SHA, "evidence": None}
    binding = {"binding_id": "input", "parameter_pointer": "/fasta", "kind": "retained_bytes",
        "content": {"source_ref": "source:input", "artifact_field": "artifact_ref", "artifact_ref": "artifact:input", "sha256": SHA, "byte_count": 4},
        "workspace_path": "/owner/home/input", "inline_value": None, "link_evidence": None, "members": [member]}
    return {"version": "bvbrc_appservice_artifact_bundle_v1", "original_task": task(),
        "artifacts": [{"role": "native", "source_ref": "source:download", "raw_artifact_ref": "artifact:download",
            "sha256": SHA, "byte_count": 4, "workspace_object": workspace_object(), "task_association": association(),
            "transfer": {"receipt_ref": "acquisition:1", "body_complete": True, "requested_range": None,
                         "observed_range": None, "total_size": 4, "object_complete": "yes"},
            "declared_format": {"format": "explicit_format", "version": None, "mode": "explicit_mode", "producer_source_ref": None, "transformation_evidence": []}}],
        "input_bindings": [binding], "query_bindings": [{"input_binding_id": "input", "input_source_ref": "source:input",
            "input_member_id": "sequence", "input_member_pointer": "/records/0", "length": 4, "molecule": "dna",
            "sequence_sha256": SHA, "raw_source_ref": "source:download", "raw_report_ordinal": 0,
            "query_id": "native-id", "query_title": "native title", "transformation_evidence": []}],
        "supplied_scientific_metadata": [], "acquisition_receipt_refs": ["acquisition:1"],
        "requested_selector_sha256": SHA, "status": "ok", "missing_requirements": [], "diagnostics": []}


def test_bundle_validation_preserves_associations_and_requires_no_external_lookup():
    value = bundle()
    checked = validate_bundle(value)
    assert checked == value
    value["query_bindings"][0]["query_title"] = "changed after validation"
    assert checked["query_bindings"][0]["query_title"] == "native title"


@pytest.mark.parametrize("change", [
    lambda x: x["artifacts"][0]["task_association"].update(task_id="other-task"),
    lambda x: x["artifacts"][0]["task_association"].update(output_uuid=UUID2),
    lambda x: x["artifacts"][0]["task_association"].update(byte_version_status="producer_bytes_bound"),
    lambda x: x["artifacts"][0]["transfer"].update(body_complete=False),
    lambda x: x["artifacts"][0].update(byte_count=3),
    lambda x: x["query_bindings"][0].update(input_member_id="other-sequence"),
    lambda x: x["query_bindings"][0].update(length=5),
    lambda x: x["query_bindings"][0].update(raw_source_ref="source:unacquired"),
    lambda x: x.update(acquisition_receipt_refs=[]),
])
def test_bundle_rejects_cross_record_mismatches(change):
    value = bundle()
    change(value)
    with pytest.raises(ContractValidationError):
        validate_bundle(value)


def test_partial_bundle_retains_valid_acquisition_with_explicit_missing_input():
    value = bundle()
    value["status"] = "partial"
    value["missing_requirements"] = [{"requirement_id": "sidecar", "kind": "output_bytes", "role": "sidecar",
                                      "source_refs": [], "reason_code": "scientific_inputs_missing"}]
    assert validate_bundle(value) == value
    value["status"] = "ok"
    with pytest.raises(ContractValidationError, match="bundle_status_conflict"):
        validate_bundle(value)
