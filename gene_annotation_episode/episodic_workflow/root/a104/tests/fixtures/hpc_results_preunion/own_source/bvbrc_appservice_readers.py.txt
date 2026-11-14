"""Pure native AppService support projections, without acquisition or grading.

All decoders return ``status, native, value, diagnostics``. Catalog and manifest
decoders additionally retain ordered ``records`` including invalid members.
Diagnostics are the closed C4 Diagnostic form. ``ok`` means the supplied native
representation parsed consistently, not that an operation or science succeeded.
Byte readers retain an exact base64 representation alongside their projection;
download qualification leaves its potentially large bytes in the supplied,
unchanged SourceSnapshot and reports their exact digest/count.

These projections are not durable receipts. The host supplies receipt origins,
source/artifact references, actual transport completeness, and custody proofs.
An association in a projection never authenticates the supplied evidence.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import math
import re

from .acquisition import SourceSnapshot
from .bvbrc_analysis_protocol import parse_workspace_records
from .bvbrc_appservice_contracts import (
    ContractValidationError, _Validator, _finite_json, _same, contract_schema, download_request,
    validate_contract,
)


_UUID = re.compile(r"[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}\Z")
_TASK_FILES = frozenset({"stdout", "stderr", "job_result_id", "job_result_folder"})


def _diagnostic(code, path="", *, phase="native_decode", severity="error", refs=()):
    return {"code": code, "phase": phase, "path": path, "severity": severity,
            "evidence_refs": list(dict.fromkeys(refs))}


def _pointer(path, token):
    return path + "/" + str(token).replace("~", "~0").replace("/", "~1")


def _nonempty(value, label):
    if type(value) is not str or not value:
        raise ContractValidationError(label + "_invalid")


def _check_json(value):
    try:
        _finite_json(value)
    except RecursionError as error:
        raise ContractValidationError("json_nesting_too_deep") from error
    return deepcopy(value)


def _status(diagnostics, *, valid=False):
    return ("ok" if not any(d["severity"] == "error" for d in diagnostics)
            else "partial" if valid else "invalid")


def _raw(content):
    if type(content) is not bytes:
        raise ContractValidationError("native_bytes_required")
    return {"encoding": "base64", "data": base64.b64encode(content).decode("ascii"),
            "byte_count": len(content), "sha256": hashlib.sha256(content).hexdigest()}


class _Pairs(list):
    pass


def _decode_json(content):
    """Retain duplicate-bearing bytes; never treat a winning duplicate as valid."""
    issues = []

    def finite_float(lexeme):
        value = float(lexeme)
        if not math.isfinite(value) or (value == 0 and re.search(r"[1-9]", lexeme.lower().split("e")[0])):
            raise ValueError("unrepresentable_json_number")
        return value

    def reject_constant(value):
        raise ValueError("non_json_numeric_constant")

    def materialize(value, path=""):
        if isinstance(value, _Pairs):
            result = {}
            for key, child in value:
                if key in result:
                    issues.append(_diagnostic("duplicate_json_member", _pointer(path, key)))
                result[key] = materialize(child, _pointer(path, key))
            return result
        if type(value) is list:
            return [materialize(child, _pointer(path, i)) for i, child in enumerate(value)]
        return value

    try:
        native = materialize(json.loads(content, object_pairs_hook=_Pairs,
            parse_float=finite_float, parse_constant=reject_constant))
    except (ValueError, UnicodeError, RecursionError) as error:
        code = str(error) if str(error) in {"unrepresentable_json_number", "non_json_numeric_constant"} else "invalid_json"
        return None, [_diagnostic(code)]
    return native, issues


def decode_catalog(value: object, *, source_ref: str) -> dict:
    """Read C1's unwrapped enumerate_apps value, retaining native array order.

    Pointers address records in the retained RPC envelope's /result/0 array.
    Structural validity does not replace C3's selected-definition preparation.
    Extraction content identities must be supplied by the custody host.
    """
    _nonempty(source_ref, "source_ref")
    native = _check_json(value)
    diagnostics, records = [], []
    if type(native) is not list:
        diagnostics.append(_diagnostic("native_response_invalid", refs=[source_ref]))
    else:
        for index, item in enumerate(native):
            pointer = f"/result/0/{index}"
            valid = (type(item) is dict and type(item.get("id")) is str and bool(item["id"])
                     and type(item.get("parameters")) is list)
            if not valid:
                diagnostics.append(_diagnostic("catalog_definition_invalid", pointer, refs=[source_ref]))
            records.append({"record_index": index, "pointer": pointer,
                "native_record": deepcopy(item), "definition_content": None,
                "application_id": item.get("id") if type(item) is dict and type(item.get("id")) is str and item["id"] else None,
                "valid": valid})
    status = _status(diagnostics, valid=any(row["valid"] for row in records))
    return {"status": status, "native": native, "value": {"records": deepcopy(records)},
            "records": records, "diagnostics": diagnostics}


def decode_upload(value: object, *, expected_node_id: str,
                  expected_bytes: int, supplied_sha256: str) -> dict:
    """Read a Shock {status,data,error} reply, never a JSON-RPC envelope.

    Only a returned sha256 can be compared to the supplied sha256. Other native
    checksum algorithms stay intact and explicitly unchecked. A matching size
    alone is not byte-identity proof. HTTP completeness/status remain separate
    transport facts that the host must check before confirming an effect.
    """
    if type(expected_node_id) is not str or not _UUID.fullmatch(expected_node_id):
        raise ContractValidationError("expected_shock_node_invalid")
    if type(expected_bytes) is not int or expected_bytes < 0:
        raise ContractValidationError("expected_upload_size_invalid")
    if type(supplied_sha256) is not str or not re.fullmatch(r"[0-9a-f]{64}", supplied_sha256):
        raise ContractValidationError("supplied_upload_sha256_invalid")
    native = _check_json(value)
    diagnostics = []
    result = {"native_reply": deepcopy(native), "observed_node_id": None,
              "observed_file_size": None, "observed_checksums": {},
              "confirmation": "unknown", "checksum_comparisons": []}
    if type(native) is not dict:
        diagnostics.append(_diagnostic("native_response_invalid"))
        return {"status": "invalid", "native": native, "value": result, "diagnostics": diagnostics}
    status = native.get("status")
    envelope_valid = (type(status) is int and 100 <= status <= 599
                      and "data" in native and "error" in native)
    if not envelope_valid:
        diagnostics.append(_diagnostic("native_response_invalid"))
    native_error = native.get("error")
    if native_error is not None:
        diagnostics.append(_diagnostic("native_upload_error", "/error"))
    if type(status) is int and status != 200:
        diagnostics.append(_diagnostic("native_upload_status", "/status"))
    data = native.get("data")
    if type(data) is not dict:
        diagnostics.append(_diagnostic("native_upload_node_missing", "/data"))
    else:
        node = data.get("id")
        if type(node) is str and _UUID.fullmatch(node):
            result["observed_node_id"] = node
            if node != expected_node_id:
                diagnostics.append(_diagnostic("upload_node_mismatch", "/data/id", phase="association"))
        else:
            diagnostics.append(_diagnostic("native_upload_node_invalid", "/data/id"))
        file = data.get("file")
        if file is None:
            diagnostics.append(_diagnostic("upload_file_metadata_missing", "/data/file", severity="qualification"))
        elif type(file) is not dict:
            diagnostics.append(_diagnostic("native_upload_file_invalid", "/data/file"))
        else:
            size = file.get("size")
            if size is None:
                diagnostics.append(_diagnostic("upload_size_unobserved", "/data/file/size", severity="qualification"))
            elif type(size) is not int or size < 0:
                diagnostics.append(_diagnostic("native_upload_size_invalid", "/data/file/size"))
            else:
                result["observed_file_size"] = size
                if size != expected_bytes:
                    diagnostics.append(_diagnostic("upload_size_mismatch", "/data/file/size", phase="association"))
            checksums = file.get("checksum")
            if checksums is None:
                diagnostics.append(_diagnostic("upload_checksum_unobserved", "/data/file/checksum", severity="qualification"))
            elif type(checksums) is not dict:
                diagnostics.append(_diagnostic("native_upload_checksum_invalid", "/data/file/checksum"))
            else:
                result["observed_checksums"] = deepcopy(checksums)
                for algorithm, checksum in checksums.items():
                    comparison = {"algorithm": algorithm, "native_value": deepcopy(checksum), "matches_supplied": None}
                    if algorithm == "sha256":
                        if type(checksum) is not str or not re.fullmatch(r"[0-9a-fA-F]{64}", checksum):
                            diagnostics.append(_diagnostic("native_upload_checksum_invalid", "/data/file/checksum/sha256"))
                        else:
                            comparison["matches_supplied"] = checksum.lower() == supplied_sha256
                            if not comparison["matches_supplied"]:
                                diagnostics.append(_diagnostic("upload_checksum_mismatch", "/data/file/checksum/sha256", phase="association"))
                    else:
                        diagnostics.append(_diagnostic("checksum_algorithm_unverified", _pointer("/data/file/checksum", algorithm), severity="qualification"))
                    result["checksum_comparisons"].append(comparison)
                if "sha256" not in checksums:
                    diagnostics.append(_diagnostic("upload_sha256_unobserved", "/data/file/checksum", severity="qualification"))
    errors = any(d["severity"] == "error" for d in diagnostics)
    identity_ok = result["observed_node_id"] == expected_node_id
    if envelope_valid and (status != 200 or native_error is not None):
        result["confirmation"] = "failed"
        parsed_status = "failed"
    elif errors:
        result["confirmation"] = "partial" if result["observed_node_id"] is not None else "unknown"
        parsed_status = "partial" if identity_ok else "invalid"
    else:
        hash_ok = any(row["algorithm"] == "sha256" and row["matches_supplied"] is True for row in result["checksum_comparisons"])
        result["confirmation"] = ("accepted_bytes_match" if hash_ok and result["observed_file_size"] == expected_bytes
                                  else "accepted_identity_only")
        parsed_status = "ok"
    return {"status": parsed_status, "native": native, "value": result, "diagnostics": diagnostics}


def decode_task_info(content: bytes, *, task_id: str, file: str) -> dict:
    """Read the entire returned representation; UUID files must be only a UUID.

    The source writes UUID plus newline. Accept one optional LF/CRLF and preserve
    its exact bytes. Logs never establish a UUID, status, throughput or completion.
    Body completeness is unknown to this pure byte-only interface.
    """
    if type(task_id) is not str or re.fullmatch(r"[A-Za-z0-9_-]+", task_id) is None:
        raise ContractValidationError("task_id_invalid")
    if type(file) is not str or file not in _TASK_FILES:
        raise ContractValidationError("task_info_file_invalid")
    raw = _raw(content)
    diagnostics = []
    value = {"task_id": task_id, "file": file, "reported_object_uuid": None,
             "returned_representation": "signature_redacted_http_bytes",
             "local_window": None, "text": None, "byte_count": len(content), "sha256": raw["sha256"]}
    try:
        value["text"] = content.decode("utf-8")
    except UnicodeError:
        diagnostics.append(_diagnostic("task_info_text_encoding_invalid", severity=("error" if file.startswith("job_result") else "qualification")))
    if file in ("job_result_id", "job_result_folder"):
        match = re.fullmatch(rb"([a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12})(?:\r?\n)?", content)
        if match is None:
            diagnostics.append(_diagnostic("task_info_object_invalid"))
        else:
            value["reported_object_uuid"] = match[1].decode("ascii")
    return {"status": _status(diagnostics), "native": raw, "value": value, "diagnostics": diagnostics}


def decode_job_result(content: bytes, *, original_task: dict,
                      object_binding: dict, evidence_ref: str) -> dict:
    """Parse source AppScript job_result JSON, retaining every output ordinal.

    original_task is OriginalTask; object_binding is WorkspaceObject. The host
    separately cross-checks metadata task_data and source custody. Effective
    parameters are actual manifest values, never replacements for submitted or
    scheduler parameters. Matching task/object identity proves no byte version.
    """
    task = validate_contract("OriginalTask", original_task)
    obj = validate_contract("WorkspaceObject", object_binding)
    _nonempty(evidence_ref, "evidence_ref")
    raw = _raw(content)
    native, diagnostics = _decode_json(content)
    records, outputs = [], []
    result = {"native_task_id": None, "native_application_id": None,
              "effective_parameters": None, "effective_parameters_pointer": "/parameters",
              "outputs": outputs, "success": None, "object": obj}
    identity_ok = True
    if obj["type"] != "job_result" or type(obj["uuid"]) is not str or not _UUID.fullmatch(obj["uuid"]):
        diagnostics.append(_diagnostic("task_manifest_object_invalid", phase="association", refs=[evidence_ref]))
        identity_ok = False
    if type(native) is not dict:
        diagnostics.append(_diagnostic("native_response_invalid", refs=[evidence_ref]))
        return {"status": "invalid", "native": native, "raw_content": raw,
                "value": result, "records": records, "diagnostics": diagnostics}
    native_id = native.get("id")
    app = native.get("app")
    app_id = app.get("id") if type(app) is dict else None
    if type(native_id) is str and native_id:
        result["native_task_id"] = native_id
    if type(app_id) is str and app_id:
        result["native_application_id"] = app_id
    for actual, expected, pointer in ((native_id, task["task_id"], "/id"),
                                      (app_id, task["native_application_id"], "/app/id")):
        if not _same(actual, expected):
            diagnostics.append(_diagnostic("task_manifest_mismatch", pointer, phase="association", refs=[evidence_ref]))
            identity_ok = False
    if type(native.get("parameters")) is not dict:
        diagnostics.append(_diagnostic("native_manifest_parameters_invalid", "/parameters", refs=[evidence_ref]))
        identity_ok = False
    else:
        result["effective_parameters"] = deepcopy(native["parameters"])
        if task["effective_parameters"] is not None and not _same(task["effective_parameters"]["value"], native["parameters"]):
            diagnostics.append(_diagnostic("task_manifest_mismatch", "/parameters", phase="association", refs=[evidence_ref]))
            identity_ok = False
    if native.get("success") is not None:
        if type(native["success"]) is int and native["success"] in (0, 1):
            result["success"] = native["success"]
        else:
            diagnostics.append(_diagnostic("native_manifest_success_invalid", "/success", refs=[evidence_ref]))
    if any(d["code"] == "duplicate_json_member" for d in diagnostics):
        identity_ok = False
    members = native.get("output_files")
    if type(members) is not list:
        diagnostics.append(_diagnostic("native_manifest_outputs_invalid", "/output_files", refs=[evidence_ref]))
    else:
        for index, member in enumerate(members):
            pointer = f"/output_files/{index}"
            valid = (type(member) is list and len(member) == 2 and type(member[0]) is str
                     and member[0].startswith("/") and not any(c in member[0] for c in "\r\n\x00")
                     and type(member[1]) is str and _UUID.fullmatch(member[1]) is not None)
            record = {"output_index": index, "pointer": pointer, "native_record": deepcopy(member),
                      "valid": bool(valid), "association": None}
            records.append(record)
            if not valid:
                diagnostics.append(_diagnostic("native_manifest_member_invalid", pointer, refs=[evidence_ref]))
            elif identity_ok:
                association = {"kind": "task_result_manifest", "evidence_ref": evidence_ref,
                    "pointer": pointer, "task_id": task["task_id"], "output_path": member[0],
                    "output_uuid": member[1], "byte_version_status": "unknown", "version_evidence": []}
                record["association"] = deepcopy(association)
                outputs.append({"output_index": index, "pointer": pointer, "path": member[0],
                                "uuid": member[1], "association": association})
    if outputs:
        diagnostics.append(_diagnostic("output_version_unproven", "/output_files", phase="association", severity="qualification", refs=[evidence_ref]))
    status = _status(diagnostics, valid=identity_ok and bool(outputs)) if identity_ok else "invalid"
    return {"status": status, "native": native, "raw_content": raw,
            "value": result, "records": records, "diagnostics": diagnostics}


def _capability(value):
    """Validate the exact inline CapabilityReceipt.entries member contract."""
    value = _check_json(value)
    parent = contract_schema("CapabilityReceipt")
    entry_schema = parent["$defs"]["CapabilityReceipt"]["properties"]["entries"]["items"]
    schema = {**entry_schema, "$defs": parent["$defs"]}
    if not _Validator(schema).is_valid(value):
        raise ContractValidationError("capability_entry_invalid")
    validate_contract("WorkspaceObject", value["object"])
    validate_contract("TaskAssociation", value["task_association"])
    association = value["task_association"]
    for field, associated in (("path", "output_path"), ("uuid", "output_uuid")):
        if association[associated] is not None and value["object"][field] != association[associated]:
            raise ContractValidationError("output_association_" + field + "_conflict")
    if (value["expires_at"] is None) != (value["expiry_evidence"] is None):
        raise ContractValidationError("capability_expiry_evidence_conflict")
    return value


def _object_binding(value):
    if type(value) is not dict or set(value) != {"object", "metadata"}:
        raise ContractValidationError("download_object_binding_invalid")
    obj = validate_contract("WorkspaceObject", value["object"])
    metadata = value["metadata"]
    if metadata is None:
        return obj, None
    metadata = validate_contract("WorkspaceRow", metadata)
    if not metadata["valid"]:
        raise ContractValidationError("download_metadata_invalid")
    for key in ("path", "uuid", "type"):
        if metadata[key] != obj[key]:
            raise ContractValidationError("download_metadata_identity_conflict")
    raw = metadata["native_row"]
    operation = "get" if type(raw) is list and len(raw) in (1, 2) and type(raw[0]) is list else "create"
    parsed = parse_workspace_records([raw], operation=operation, requested_paths=[obj["path"]])
    if parsed["status"] != "ok" or len(parsed["records"]) != 1:
        raise ContractValidationError("download_metadata_native_invalid")
    row = parsed["records"][0]
    for field, native_field in (("path", "object_path"), ("uuid", "object_id"), ("type", "type"),
                                ("size", "size"), ("shock_url", "shock_url"),
                                ("creation_time", "creation_time"), ("error", "error")):
        # Empty optional native strings remain empty in C1 but are null in the
        # closed projection fields whose schema excludes empty strings.
        actual = row[native_field]
        if field == "shock_url" and actual == "":
            actual = None
        if not _same(metadata[field], actual):
            raise ContractValidationError("download_metadata_native_conflict")
    return obj, metadata


def _headers(transport, diagnostics):
    headers = transport.get("headers")
    if type(headers) is not dict or any(type(k) is not str or type(v) is not str for k, v in headers.items()):
        raise ContractValidationError("download_headers_invalid")
    lowered = {key.lower(): value for key, value in headers.items()}
    if "header_items" in transport:
        items = transport["header_items"]
        if type(items) is not list or any(type(x) is not list or len(x) != 2 or any(type(y) is not str for y in x) for x in items):
            raise ContractValidationError("download_header_items_invalid")
        seen = {}
        for key, value in items:
            key = key.lower()
            if key in seen and seen[key] != value and key in {"content-length", "content-range", "content-encoding", "transfer-encoding"}:
                diagnostics.append(_diagnostic("conflicting_http_header", "/transport/header_items", phase="transport"))
            seen[key] = value
        for key, value in seen.items():
            if lowered.get(key) != value:
                diagnostics.append(_diagnostic("http_header_projection_conflict", "/transport/headers", phase="transport"))
    return lowered


def _bounded_capture(request, transport, byte_count, headers):
    """Check local cap evidence without inferring an unseen body or object."""
    complete, diagnostics = transport["body_complete"], []
    if "max_bytes" not in request:
        return complete, diagnostics
    limit = request["max_bytes"]
    conflicts = []
    observed = transport.get("observed_body_bytes")
    if type(transport.get("response_byte_limit")) is not int or transport["response_byte_limit"] != limit:
        conflicts.append("response_byte_limit")
    if type(transport.get("retained_body_bytes")) is not int or transport["retained_body_bytes"] != byte_count:
        conflicts.append("retained_body_bytes")
    if type(transport.get("received_body_bytes")) is not int or transport["received_body_bytes"] != byte_count:
        conflicts.append("received_body_bytes")
    if type(observed) is not int or observed < 0 or byte_count != min(observed, limit):
        conflicts.append("observed_body_bytes")
    declared = None
    text = headers.get("content-length")
    if type(text) is str and re.fullmatch(r"[0-9]+", text) and headers.get("transfer-encoding") is None:
        declared = int(text)
    supplied = transport.get("declared_body_bytes")
    if (supplied is not None and type(supplied) is not int) or not _same(supplied, declared):
        conflicts.append("declared_body_bytes")
    failure = transport.get("body_capture_failure")
    if failure is not None and type(failure) is not str:
        conflicts.append("body_capture_failure")
    if complete and (observed != byte_count or failure is not None):
        conflicts.append("body_complete")
    exceeded = byte_count > limit or type(observed) is int and observed > limit or failure == "provider_response_byte_limit"
    if exceeded:
        diagnostics.append(_diagnostic("download_byte_limit_exceeded", phase="transport"))
    diagnostics.extend(_diagnostic("download_capture_limit_conflict", "/transport/" + key,
        phase="transport") for key in conflicts)
    return complete and not exceeded and not conflicts, diagnostics


def qualify_download(snapshot, *, capability: dict, object_binding: dict) -> dict:
    """Qualify one already-acquired body; no requests, assembly, or truncation.

    capability is one exact CapabilityReceipt.entries member. object_binding is
    {object: WorkspaceObject, metadata: WorkspaceRow | None}. Null metadata does
    not supply a size. Request range comes only from snapshot.request. A 200 body
    without a declared length or supplied object size has unknown object
    completeness, including the source proxy's premature-success case.
    """
    capability = _capability(capability)
    obj, metadata = _object_binding(object_binding)
    if not _same(capability["object"], obj):
        raise ContractValidationError("capability_object_conflict")
    if not isinstance(snapshot, SourceSnapshot) or type(snapshot.content) is not bytes:
        raise ContractValidationError("download_snapshot_invalid")
    request, transport = _check_json(snapshot.request), _check_json(snapshot.transport)
    if (type(request) is not dict or request.get("kind") != "download"
            or "requested_byte_range" not in request):
        raise ContractValidationError("download_request_invalid")
    call = {"url": request.get("url"), "byte_range": request["requested_byte_range"]}
    if "max_bytes" in request:
        call["max_bytes"] = request["max_bytes"]
    if not _same(request, download_request(call)):
        raise ContractValidationError("download_request_invalid")
    selected_range = request["requested_byte_range"]
    if selected_range is not None:
        selected_range = validate_contract("Range", selected_range)
    diagnostics = []
    if capability["url"] is None:
        diagnostics.append(_diagnostic("capability_unavailable", phase="association"))
    if request.get("url") != capability["url"] or snapshot.url != capability["url"]:
        diagnostics.append(_diagnostic("capability_url_conflict", phase="association"))
    if type(transport) is not dict or type(transport.get("body_complete")) is not bool:
        raise ContractValidationError("download_transport_invalid")
    http_status = transport.get("status")
    if type(http_status) is not int or not 100 <= http_status <= 599:
        raise ContractValidationError("download_http_status_invalid")
    if transport.get("effective_url") != snapshot.url or transport.get("automatic_redirects") is not False:
        diagnostics.append(_diagnostic("download_transport_identity_conflict", phase="transport"))
    if "request" in transport and (type(transport["request"]) is not dict
            or transport["request"].get("method") != "GET" or transport["request"].get("url") != snapshot.url):
        diagnostics.append(_diagnostic("download_transport_request_conflict", phase="transport"))
    byte_count = len(snapshot.content)
    if type(transport.get("received_body_bytes")) is not int or transport["received_body_bytes"] != byte_count:
        diagnostics.append(_diagnostic("download_body_count_conflict", phase="transport"))
    headers = _headers(transport, diagnostics)
    body_complete, capture_diagnostics = _bounded_capture(request, transport, byte_count, headers)
    diagnostics.extend(capture_diagnostics)
    content_length = None
    if "content-length" in headers:
        if re.fullmatch(r"[0-9]+", headers["content-length"].strip()) is None:
            diagnostics.append(_diagnostic("content_length_invalid", "/transport/headers/content-length", phase="transport"))
        else:
            content_length = int(headers["content-length"].strip())
            if content_length != byte_count:
                body_complete = False
                diagnostics.append(_diagnostic("download_incomplete" if byte_count < content_length else "object_size_conflict", "/transport/headers/content-length", phase="transport"))
    if headers.get("transfer-encoding") and content_length is not None:
        diagnostics.append(_diagnostic("conflicting_http_framing", "/transport/headers", phase="transport"))
    observed = None
    content_range = headers.get("content-range")
    if http_status == 206:
        match = re.fullmatch(r"bytes ([0-9]+)-([0-9]+)/(\*|[0-9]+)", content_range or "")
        if match is None:
            diagnostics.append(_diagnostic("range_conflict", "/transport/headers/content-range", phase="transport"))
        else:
            candidate = {"start": int(match[1]), "end_inclusive": int(match[2]),
                         "total_size": None if match[3] == "*" else int(match[3])}
            try:
                observed = validate_contract("ObservedRange", candidate)
            except ContractValidationError:
                diagnostics.append(_diagnostic("range_conflict", "/transport/headers/content-range", phase="transport"))
    elif http_status == 200:
        if content_range is not None:
            diagnostics.append(_diagnostic("range_conflict", "/transport/headers/content-range", phase="transport"))
        if selected_range is not None:
            diagnostics.append(_diagnostic("range_ignored", "/request/requested_byte_range", phase="transport", severity="qualification"))
    else:
        diagnostics.append(_diagnostic("capability_http_error", "/transport/status", phase="transport"))
    metadata_size = metadata["size"] if metadata is not None and obj["type"] != "folder" else None
    total_size = observed["total_size"] if observed is not None else (content_length if http_status == 200 else None)
    if metadata_size is not None:
        if total_size is not None and metadata_size != total_size:
            diagnostics.append(_diagnostic("object_size_conflict", phase="association"))
        if total_size is None:
            total_size = metadata_size
    if observed is not None:
        width = observed["end_inclusive"] - observed["start"] + 1
        if byte_count != width:
            body_complete = False
            diagnostics.append(_diagnostic("download_incomplete" if byte_count < width else "range_conflict", phase="transport"))
        if total_size is not None and observed["end_inclusive"] >= total_size:
            diagnostics.append(_diagnostic("object_size_conflict", phase="association"))
        if selected_range is not None:
            start, end = selected_range
            expected_end = min(end, total_size - 1) if end is not None and total_size is not None else (
                end if end is not None else total_size - 1 if total_size is not None else None)
            if observed["start"] != start or expected_end is not None and observed["end_inclusive"] != expected_end:
                diagnostics.append(_diagnostic("range_conflict", "/request/requested_byte_range", phase="transport"))
    elif http_status == 200 and total_size is not None and byte_count != total_size:
        diagnostics.append(_diagnostic("object_size_conflict", phase="association"))
    if not body_complete and not any(d["code"] == "download_incomplete" for d in diagnostics):
        diagnostics.append(_diagnostic("download_incomplete", phase="transport"))
    encoded = headers.get("content-encoding", "identity").lower() != "identity"
    if encoded:
        diagnostics.append(_diagnostic("content_encoding_uninterpreted", "/transport/headers/content-encoding", phase="transport", severity="qualification"))
    if capability["expires_at"] is not None:
        try:
            expires, retrieved = (datetime.fromisoformat(x.replace("Z", "+00:00")) for x in (capability["expires_at"], snapshot.retrieved_at))
            if expires.tzinfo is None or retrieved.tzinfo is None:
                raise ValueError("unqualified_time")
            if retrieved >= expires:
                diagnostics.append(_diagnostic("capability_expired_at_retrieval", phase="association", severity="qualification"))
        except (TypeError, ValueError):
            diagnostics.append(_diagnostic("capability_expiry_time_uninterpretable", phase="association", severity="qualification"))
    errors = any(d["severity"] == "error" for d in diagnostics)
    if not body_complete:
        object_complete = "no"
    elif errors or encoded or total_size is None:
        object_complete = "unknown"
    elif observed is not None:
        object_complete = "yes" if observed["start"] == 0 and observed["end_inclusive"] + 1 == total_size else "no"
    else:
        object_complete = "yes" if http_status == 200 and byte_count == total_size else "unknown"
    if object_complete == "unknown":
        diagnostics.append(_diagnostic("object_completeness_unproven", phase="association", severity="qualification"))
    received_range = None
    if observed is not None and byte_count and byte_count <= observed["end_inclusive"] - observed["start"] + 1:
        received_range = {"start": observed["start"], "end_inclusive": observed["start"] + byte_count - 1,
                          "total_size": total_size}
    value = {"body_complete": body_complete, "requested_range": deepcopy(selected_range),
             "observed_range": observed, "received_range": received_range, "total_size": total_size,
             "metadata_size": metadata_size, "object_complete": object_complete,
             "byte_count": byte_count, "sha256": hashlib.sha256(snapshot.content).hexdigest()}
    parsed_status = "failed" if http_status not in (200, 206) else _status(diagnostics, valid=bool(snapshot.content))
    return {"status": parsed_status, "native": {"request": request, "transport": transport},
            "value": value, "diagnostics": diagnostics}


def validate_bundle(value: dict) -> dict:
    """Check a supplied bundle's shape/relationships, without resolving custody."""
    return validate_contract("ArtifactBundle", value)


__all__ = ["decode_catalog", "decode_upload", "decode_task_info", "decode_job_result",
           "qualify_download", "validate_bundle"]
