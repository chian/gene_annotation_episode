"""Pure projections of retained AppService support responses and effect outcomes.

The caller authenticates custody and supplies real receipt/source bindings. This
module checks their supplied relationships and decodes the original response;
it performs no storage access, transport, publication, observation or scoring.
Closed journal outcomes remain unchanged. Confirmation acknowledges a native
effect, independently of whether the original job has a usable handoff.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from urllib.parse import urlsplit

from .acquisition import SourceSnapshot
from .bvbrc_analysis_protocol import (
    decode_rpc_response, parse_task_records, parse_workspace_records,
)
from .bvbrc_appservice_contracts import ContractValidationError, _same, validate_contract
from .bvbrc_appservice_readers import _decode_json, decode_catalog, decode_task_info, decode_upload
from .execution_contracts import digest


_PREFIX = "api.bvbrc_appservice."
_METHODS = {"enumerate_apps": "AppService.enumerate_apps", "submit": "AppService.start_app2",
    "status": "AppService.query_tasks", "workspace_metadata": "Workspace.get",
    "workspace_create": "Workspace.create", "list_outputs": "Workspace.ls",
    "download_capability": "Workspace.get_download_url"}
_STATES = {"queued": "submitted", "pending": "submitted", "running": "running",
    "in-progress": "running", "completed": "completed", "failed": "failed", "deleted": "failed"}
_SUBMISSION_STATES = {"Q": "submitted", "S": "submitted", "C": "completed",
    "F": "failed", "D": "failed", "T": "failed"}
_OUTCOME_FIELDS = ("effect_ref", "state", "confirmation_source_ref",
    "native_effect_identifiers", "ancillary_effects", "failure")


def _require(condition, code):
    if not condition:
        raise ContractValidationError(code)


def _pointer(path, token):
    return path + "/" + str(token).replace("~", "~0").replace("/", "~1")


def _json_pointer(path):
    """Translate C1/C3's explicit JSON paths without interpreting their values."""
    if path.startswith("/") or path == "":
        return path
    _require(path.startswith("$"), "native_diagnostic_path_invalid")
    pointer, index = "", 1
    decoder = json.JSONDecoder()
    while index < len(path):
        if path[index] == ".":
            end = index + 1
            while end < len(path) and path[end] not in ".[":
                end += 1
            _require(end > index + 1, "native_diagnostic_path_invalid")
            token, index = path[index + 1:end], end
        else:
            _require(path[index] == "[", "native_diagnostic_path_invalid")
            token, consumed = decoder.raw_decode(path[index + 1:])
            index += consumed + 1
            _require(index < len(path) and path[index] == "]", "native_diagnostic_path_invalid")
            index += 1
        pointer = _pointer(pointer, token)
    return pointer


def _diag(code, path="", *, phase="native_decode", severity="error", refs=()):
    return {"code": code, "phase": phase, "path": path, "severity": severity,
            "evidence_refs": list(dict.fromkeys(refs))}


def _diagnostics(rows, *, prefix="", phase="native_decode", refs=()):
    return [_diag(row["code"], prefix + _json_pointer(row.get("path", "")), phase=phase,
                  severity=row.get("severity", "error"), refs=refs) for row in rows]


def _unique(rows):
    result = []
    for row in rows:
        if row not in result:
            result.append(deepcopy(row))
    return result


def _status(diagnostics, valid=False):
    return "ok" if not any(d["severity"] == "error" for d in diagnostics) else "partial" if valid else "invalid"


def _effect_payloads(prepared):
    """Tie each journal payload to its original selected native operands."""
    operands, bindings = prepared["native_operands"], prepared["bound_inputs"]
    args, request, call = operands["arguments"], operands["request"], operands["call"]
    resolved = bindings["resolved"]
    suffix = prepared["operation"].removeprefix(_PREFIX)
    for effect in prepared["effects"]:
        kind, slot = effect["kind"], effect["slot"]
        _require(kind == {"workspace_create": "workspace_create", "upload": "shock_upload",
            "submit": "appservice_submit", "download_capability": "download_capability"}.get(suffix),
            "effect_payload_binding_conflict")
        if kind == "appservice_submit":
            rpc = call["rpc_request"]
            _require(rpc["method"] == "AppService.start_app2" and _same(rpc["params"],
                [resolved["preparation"]["native_application_id"], request["parameters"], request["start_parameters"]]),
                "effect_payload_binding_conflict")
            payload = {"method": rpc["method"], "params": rpc["params"]}
        elif kind == "workspace_create":
            native = call["rpc_request"]["params"][0]
            targets = {target["target_id"]: target for target in request["workspace_targets"]}
            matches = [(i, targets[selected["target_id"]]) for i, selected in enumerate(args["objects"])
                       if targets[selected["target_id"]]["path"] == slot["target_path"]]
            _require(len(matches) == 1 and len(native["objects"]) == len(args["objects"])
                and _same({key: value for key, value in native.items() if key != "objects"}, args["options"]),
                "effect_payload_binding_conflict")
            index, target = matches[0]
            obj = native["objects"][index]
            _require(obj[:3] == [target["path"], target["type"], target["metadata"]], "effect_payload_binding_conflict")
            payload = {"target": target, "native_object": obj, "options": args["options"]}
        elif kind == "shock_upload":
            upload = resolved["upload"]
            supplied = upload["input"]
            _require(slot["shock_node_id"] == upload["shock_node_id"]
                and call["node_url"] == upload["shock_url"] and call["filename"] == args["filename"]
                and _same(call["content"], supplied["content"]), "effect_payload_binding_conflict")
            payload = {"node_url": call["node_url"], "input_binding_id": supplied["binding_id"],
                "sha256": supplied["content"]["sha256"], "byte_count": supplied["content"]["byte_count"],
                "filename": call["filename"]}
        else:
            objects = resolved["objects"]
            matches = [obj for obj in objects if obj["identity"] == slot["object_identity"]]
            _require(len(matches) == 1 and slot["generation"] == args["generation"]
                and _same([obj["selection"] for obj in objects], args["objects"])
                and _same(call["rpc_request"]["params"], [{"objects": [obj["native_reference"] for obj in objects]}]),
                "effect_payload_binding_conflict")
            payload = {"reference": matches[0]["native_reference"], "object": matches[0]["object"],
                       "generation": args["generation"]}
        _require(effect["payload_sha256"] == digest(payload), "effect_payload_binding_conflict")


def _inputs(prepared, event, effect_receipts):
    prepared = validate_contract("PreparedOperation", prepared)
    operands = prepared["native_operands"]
    _require(set(operands) == {"request", "arguments", "selector", "call", "local_failure"},
             "prepared_operands_invalid")
    validate_contract("AppServiceRequest", operands["request"])
    validate_contract("OperationSelection", {"name": prepared["operation"], "arguments": operands["arguments"]})
    _require(prepared["request_sha256"] == digest(operands["request"])
             and prepared["arguments_sha256"] == digest(operands["arguments"]), "prepared_binding_conflict")
    event = validate_contract("Event", event)
    _require(event["facts"].get("operation") == prepared["operation"], "appservice_event_operation_conflict")
    _require(type(effect_receipts) is list, "effect_receipts_invalid")
    receipts = [validate_contract("EffectReceipt", row) for row in effect_receipts]
    _require(len(receipts) == len(prepared["effects"]), "effect_receipts_binding_conflict")
    _require(len({row["effect_ref"] for row in receipts}) == len(receipts), "effect_receipts_binding_conflict")
    _require(not receipts or len({row["operation_key"] for row in receipts}) == 1,
             "effect_receipts_binding_conflict")
    unmatched = deepcopy(prepared["effects"])
    for row in receipts:
        matches = [i for i, descriptor in enumerate(unmatched) if _same(row["descriptor"], descriptor)]
        _require(len(matches) == 1, "effect_receipts_binding_conflict")
        unmatched.pop(matches[0])
    try:
        _effect_payloads(prepared)
    except (KeyError, TypeError, IndexError) as error:
        raise ContractValidationError("effect_payload_binding_conflict") from error
    return prepared, deepcopy(event), receipts


def _snapshot_check(prepared, snapshot, binding):
    """Check supplied storage identity and selected native call, never custody."""
    _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes,
             "native_snapshot_missing")
    binding = validate_contract("SnapshotBinding", binding)
    frozen = {key: deepcopy(prepared[key]) for key in
              ("operation", "request_sha256", "arguments_sha256", "native_operands")}
    _require(_same(binding["selected_operands"], frozen), "snapshot_selection_conflict")
    _require(binding["content"]["sha256"] == snapshot.sha256
             and binding["content"]["byte_count"] == len(snapshot.content)
             and binding["retrieved_at"] == snapshot.retrieved_at
             and binding["media_type"] == snapshot.media_type
             and _same(binding["transport"], snapshot.transport), "snapshot_binding_conflict")
    _require(snapshot.service == "bvbrc_analysis", "native_response_invalid")
    transport, call, kind = snapshot.transport, prepared["native_operands"]["call"], prepared["native_kind"]
    _require(type(transport) is dict and type(transport.get("status")) is int
             and 100 <= transport["status"] <= 599
             and type(transport.get("body_complete")) is bool
             and type(transport.get("received_body_bytes")) is int
             and transport["received_body_bytes"] == len(snapshot.content), "native_response_invalid")
    sent = transport.get("request")
    _require(type(sent) is dict and sent.get("url") == snapshot.url
             and transport.get("effective_url") == snapshot.url
             and transport.get("automatic_redirects") is False, "native_response_invalid")
    if kind == "rpc":
        rpc = call["rpc_request"]
        suffix = prepared["operation"].removeprefix(_PREFIX)
        _require(rpc["method"] == _METHODS.get(suffix)
                 and _same(snapshot.request, {"kind": "rpc", "rpc": rpc})
                 and sent.get("method") == "POST", "native_request_conflict")
        encoded = json.dumps(rpc, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        _require(sent.get("body_bytes") == len(encoded)
                 and sent.get("body_sha256") == hashlib.sha256(encoded).hexdigest(), "native_request_conflict")
    elif kind == "task_info":
        _require(_same(snapshot.request, {"kind": "task_info", **call})
                 and sent.get("method") == "GET"
                 and urlsplit(snapshot.url).path.endswith("/task_info/" + call["task_id"] + "/" + call["file"]),
                 "native_request_conflict")
    elif kind == "upload":
        request = snapshot.request
        boundary = "gene-annotation-" + hashlib.sha256(call["filename"].encode()
            + b"\x00" + bytes.fromhex(call["content"]["sha256"])).hexdigest()
        prefix = (f'--{boundary}\r\nContent-Disposition: form-data; name="upload"; '
            f'filename="{call["filename"]}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()
        suffix = f"\r\n--{boundary}--\r\n".encode()
        expected = {"kind": "upload", "node_url": call["node_url"], "filename": call["filename"],
            "input_bytes": call["content"]["byte_count"], "input_sha256": call["content"]["sha256"],
            "multipart_field": "upload", "multipart_boundary": boundary}
        _require(_same(request, expected) and snapshot.url == call["node_url"] and sent.get("method") == "PUT"
                 and sent.get("body_bytes") == len(prefix) + call["content"]["byte_count"] + len(suffix)
                 and type(sent.get("body_sha256")) is str
                 and re.fullmatch(r"[0-9a-f]{64}", sent["body_sha256"]) is not None, "native_request_conflict")
    else:
        raise ContractValidationError("support_native_kind_invalid")
    return binding


def _native(prepared, event, snapshot, binding):
    """Return only a successfully correlated native value, plus exact errors."""
    try:
        binding = _snapshot_check(prepared, snapshot, binding)
        # The service knows its configured endpoint, which is deliberately not
        # duplicated in PreparedOperation. These facts are emitted only after
        # its complete transport/request check, including that endpoint check.
        facts = event["facts"]
        _require(type(facts.get("http_status")) is int
                 and facts["http_status"] == snapshot.transport["status"]
                 and facts.get("body_complete") is snapshot.transport["body_complete"],
                 "native_response_invalid")
    except (ContractValidationError, KeyError, TypeError, ValueError) as error:
        return None, [_diag(getattr(error, "code", "native_response_invalid"), phase="association")]
    refs = [binding["source_ref"]]
    if not 200 <= snapshot.transport["status"] < 300:
        code = "task_info_unavailable" if prepared["native_kind"] == "task_info" else "native_http_error"
        return None, [_diag(code, "/transport/status", phase="transport", refs=refs)]
    if not snapshot.transport["body_complete"]:
        return None, [_diag("native_response_incomplete", "/transport/body_complete", phase="transport", refs=refs)]
    if prepared["native_kind"] == "rpc":
        rpc = prepared["native_operands"]["call"]["rpc_request"]
        result = decode_rpc_response(snapshot.content, method=rpc["method"], request_id=rpc["id"],
                                     http_status=snapshot.transport["status"])
        diagnostics = _diagnostics(result["diagnostics"], refs=refs)
        return (result["value"] if result["status"] == "ok" else None), diagnostics
    if prepared["native_kind"] == "upload":
        native, diagnostics = _decode_json(snapshot.content)
        return (native if not diagnostics else None), diagnostics
    return snapshot.content, []


def _workspace(prepared, native, source_ref):
    call = prepared["native_operands"]["call"]["rpc_request"]
    operation = call["method"].split(".", 1)[1]
    args = prepared["native_operands"]["arguments"]
    resolved = prepared["bound_inputs"]["resolved"]
    options = call["params"][0]
    references = [row[0] for row in options["objects"]] if operation == "create" else options["paths" if operation == "ls" else "objects"]
    parsed = parse_workspace_records(native, operation=operation, requested_paths=references)
    diagnostics = _diagnostics(parsed["diagnostics"], prefix="/result/0", refs=[source_ref])
    targets = {row["target_id"]: row for row in prepared["native_operands"]["request"]["workspace_targets"]}
    for row in parsed["records"]:
        row["pointer"] = _pointer("/result/0", row["row_index"]) if operation != "ls" else _pointer(
            _pointer("/result/0", row["listing_path"]), row["row_index"])
        if operation == "create":
            expected = [targets[args["objects"][i]["target_id"]] for i in row["request_indices"]]
            conflict = any(row["type"] != target["type"] for target in expected)
        elif operation == "get" and row["request_index"] is not None:
            expected = resolved["objects"][row["request_index"]]["object"]
            conflict = any(expected[key] is not None and row[native_key] != expected[key]
                for key, native_key in (("uuid", "object_id"), ("type", "type")))
        else:
            conflict = False
        if conflict:
            row["status"] = "invalid"
            diagnostics.append(_diag("workspace_target_conflict", row["pointer"], phase="association", refs=[source_ref]))
    parsed["status"] = _status(diagnostics, any(row["status"] == "ok" for row in parsed["records"]))
    parsed["diagnostics"] = diagnostics
    return parsed


def _task(prepared, native, source_ref):
    """Validate every echoed original field without replacing submitted values."""
    submission = prepared["operation"] == _PREFIX + "submit"
    resolved, request = prepared["bound_inputs"]["resolved"], prepared["native_operands"]["request"]
    original = None if submission else resolved["original_task"]
    native_app = resolved["preparation"]["native_application_id"] if submission else original["native_application_id"]
    parsed = parse_task_records(native, operation="start_app2" if submission else "query_tasks",
        requested_task_ids=None if submission else [original["task_id"]])
    diagnostics = _diagnostics(parsed["diagnostics"], prefix="/result/0", refs=[source_ref])
    matches = [row for row in parsed["records"] if row["status"] == "ok" and
        (submission or str(row["task_id"]) == original["task_id"])]
    if len(matches) != 1:
        diagnostics.append(_diag("original_task_mismatch", "/result/0", phase="association", refs=[source_ref]))
        return None, diagnostics
    row = matches[0]
    raw = row["native_record"]
    pointer = "/result/0" if submission else _pointer("/result/0", row["task_map_key"])
    parameters, parameter_pointer = None, None
    own_errors, qualifications = [], []

    def error(code, field):
        own_errors.append(_diag(code, _pointer(pointer, field), phase="association", refs=[source_ref]))

    for field in ("application_id", "app"):
        if raw.get(field) is not None and raw[field] != native_app:
            error("original_task_mismatch", field)
    if row["application_id"] is None:
        qualifications.append("submission_application_echo_unobserved" if submission else "task_application_echo_unobserved")
    for field in ("params", "parameters"):
        if raw.get(field) is None:
            continue
        value = raw[field]
        if field == "params":
            value, issues = _decode_json(value.encode()) if type(value) is str else (None, [None])
            if issues:
                error("submission_parameters_conflict", field)
                continue
        if (type(value) is not dict or any(key not in value or not _same(value[key], operand)
                for key, operand in request["parameters"].items())
                or parameters is not None and not _same(parameters, value)):
            error("submission_parameters_conflict", field)
        elif parameters is None:
            parameters, parameter_pointer = deepcopy(value), _pointer(pointer, field)
    if parameters is None:
        qualifications.append("submission_parameters_echo_unobserved" if submission else "task_parameters_echo_unobserved")
    if raw.get("app_spec") is not None:
        app, issues = _decode_json(raw["app_spec"].encode()) if type(raw["app_spec"]) is str else (None, [None])
        if issues or type(app) is not dict or app.get("id") != native_app:
            error("original_task_mismatch", "app_spec")
    start = request["start_parameters"]
    if raw.get("start_parameters") is not None and (type(raw["start_parameters"]) is not dict
            or any(key not in raw["start_parameters"] or not _same(raw["start_parameters"][key], value)
                   for key, value in start.items())):
        error("submission_parameters_conflict", "start_parameters")
    for field, native_field in (("parent_id", "parent_task"), ("base_url", "base_url"),
            ("user_metadata", "user_metadata")):
        if submission and field in start and native_field in raw and not _same(start[field], raw[native_field]):
            error("submission_parameters_conflict", native_field)
    # As in the native service decoder, task parameters override StartParams
    # for these scheduler fields. Preserve both submitted operands separately.
    for field in ("container_id", "data_container_id"):
        expected = request['parameters'].get(field)
        if expected is None:
            expected = start.get(field)
        if submission and field in raw and expected is not None and not _same(raw[field], expected):
            error('submission_parameters_conflict', field)
        if submission and field in raw and request['parameters'].get(field) is not None and field in start:
            qualifications.append('native_task_parameter_' + field + '_override')
    for field in ("output_path", "output_file"):
        if raw.get(field) is not None and field in request["parameters"] and not _same(raw[field], request["parameters"][field]):
            error("submission_parameters_conflict", field)
    diagnostics.extend(own_errors)
    if own_errors:
        return None, diagnostics
    state = (_SUBMISSION_STATES if submission else _STATES).get(row["native_state"], "unknown")
    if state == "unknown":
        qualifications.append("native_state_unknown")
    return {"raw": raw, "pointer": pointer, "task_id": str(row["task_id"]), "state": state,
        "native_status": row["native_state"] or None, "parameters": parameters,
        "parameter_pointer": parameter_pointer, "qualification_codes": qualifications,
        "native_timing": {field: deepcopy(raw.get(field)) for field in
                          ("submit_time", "start_time", "completed_time", "elapsed_time")}}, diagnostics


def _upload(prepared, native):
    upload = prepared["bound_inputs"]["resolved"]["upload"]
    content = upload["input"]["content"]
    parsed = decode_upload(native, expected_node_id=upload["shock_node_id"],
        expected_bytes=content["byte_count"], supplied_sha256=content["sha256"])
    value = parsed["value"]
    size = value["observed_file_size"]
    # A node-only reply and an empty newly-created node are not file acceptance.
    if parsed["status"] == "ok" and (size is None or size == 0 and
            value["confirmation"] != "accepted_bytes_match"):
        value["confirmation"] = "unknown"
        parsed["diagnostics"].append(_diag("upload_file_acceptance_unproven", "/data/file", phase="association"))
        parsed["status"] = "partial"
    file = native.get("data", {}).get("file") if type(native) is dict and type(native.get("data")) is dict else None
    if type(file) is dict and "name" in file and file["name"] != prepared["native_operands"]["arguments"]["filename"]:
        value["confirmation"] = "partial"
        parsed["diagnostics"].append(_diag("upload_filename_mismatch", "/data/file/name", phase="association"))
        parsed["status"] = "partial"
    return parsed


def _event_diagnostics(event):
    rows = [validate_contract("Diagnostic", row) for row in event["facts"].get("diagnostics", [])]
    failure = event["facts"].get("failure")
    if failure is not None:
        failure = validate_contract("Failure", failure)
        rows.extend(_diag(failure["code"], path, phase=failure["phase"], refs=failure["affected_refs"])
                    for path in (failure["affected_pointers"] or [""]))
    elif event.get("failure_code"):
        rows.append(_diag(event["failure_code"]))
    return rows


def _finish(contract, value, common, diagnostics, status):
    common = deepcopy(common)
    common["diagnostics"] = _unique([*common["diagnostics"], *diagnostics])
    # Host failures are not upgraded by a local representation projection.
    common["status"] = status if common["status"] == "ok" else common["status"]
    if status in ("failed", "invalid"):
        common["status"] = status
    if contract == "CommonReceipt":
        value = common
    else:
        value = {**value, "receipt": common}
    return {"contract": contract, "value": validate_contract(contract, value),
            "diagnostics": deepcopy(common["diagnostics"])}


def build_appservice_receipt(prepared, event, snapshot, *, common_receipt, effect_receipts):
    """Build one existing C4 receipt using only the host's supplied bindings."""
    prepared, event, effects = _inputs(prepared, event, effect_receipts)
    common = validate_contract("CommonReceipt", common_receipt)
    _require(common["origin"]["name"] == prepared["operation"]
             and common["origin"]["arguments_sha256"] == prepared["arguments_sha256"]
             and common["purpose"] == prepared["purpose"]
             and common["effect_receipt_refs"] == [row["effect_ref"] for row in effects]
             and all(row["operation_key"] == common["origin"]["operation_key"] for row in effects),
             "receipt_origin_conflict")
    diagnostics = _event_diagnostics(event)
    args, request = prepared["native_operands"]["arguments"], prepared["native_operands"]["request"]
    bindings, suffix = prepared["bound_inputs"], prepared["operation"].removeprefix(_PREFIX)
    resolved = bindings["resolved"]
    if prepared["native_kind"] == "local_prepare":
        _require(snapshot is None and common["snapshot"] is None, "local_preparation_snapshot_conflict")
        c3 = prepared["native_operands"]["call"].get("c3_result")
        if suffix != "prepare" or c3 is None or c3.get("status") != "ok" or c3.get("value") is None:
            if c3 is not None:
                diagnostics.extend(_diagnostics(c3.get("diagnostics", []), phase="prepare"))
            return _finish("CommonReceipt", {}, common, diagnostics, "failed")
        _require(bindings["definition"] is not None, "definition_evidence_missing")
        value = c3["value"]
        _require(_same(value.get("native_params"), [value.get("native_application_id"), request["parameters"], request["start_parameters"]])
                 and value.get("required_id") == request["required_application_id"], "preparation_parameters_conflict")
        diagnostics.extend(_diagnostics(c3["diagnostics"], phase="prepare"))
        return _finish("PreparationReceipt", {"request_sha256": prepared["request_sha256"],
            "definition_selection": args["definition"], "definition_evidence": bindings["definition"],
            "required_application_id": request["required_application_id"], "native_application_id": value["native_application_id"],
            "native_parameters": request["parameters"], "start_parameters": request["start_parameters"],
            "c3_result": c3}, common, diagnostics, "ok")
    native, issues = _native(prepared, event, snapshot, common["snapshot"])
    diagnostics.extend(issues)
    if suffix == "task_info" and len(issues) == 1 and issues[0]["code"] == "native_response_incomplete":
        # Identity and retained bytes passed validation. A truncated log still
        # has useful bytes, but even a UUID-looking prefix cannot bind an object.
        parsed = decode_task_info(snapshot.content, **prepared["native_operands"]["call"])
        value = {key: parsed["value"][key] for key in
                 ("task_id", "file", "returned_representation", "local_window")}
        value.update(original_handoff_ref=bindings["original_handoff_ref"],
                     body_complete=False, reported_object_uuid=None)
        return _finish("TaskInfoReceipt", value, common,
                       [*diagnostics, *parsed["diagnostics"]], "partial")
    if issues:
        return _finish("CommonReceipt", {}, common, diagnostics, "failed")
    source_ref = common["snapshot"]["source_ref"]
    if suffix == "enumerate_apps":
        parsed = decode_catalog(native, source_ref=source_ref)
        return _finish("CatalogReceipt", {"records": parsed["records"]}, common,
                       [*diagnostics, *parsed["diagnostics"]], parsed["status"])
    if suffix in ("workspace_create", "workspace_metadata", "list_outputs"):
        parsed = _workspace(prepared, native, source_ref)
        selected = [{"kind": "original_target", "target_id": row["target_id"]} for row in args["objects"]] if suffix == "workspace_create" else args["objects"]
        rows = [{"pointer": row["pointer"], "native_row": row["native_record"], "valid": row["status"] == "ok",
            "path": row["object_path"] or None, "uuid": row["object_id"] or None, "type": row["type"] or None,
            "shock_url": row["shock_url"] or None, "creation_time": row["creation_time"],
            "size": row["size"], "error": row["error"]} for row in parsed["records"]]
        returned = {i for row in parsed["records"] if row["status"] == "ok" for i in row["request_indices"]}
        # ls may omit an empty directory. Absence is retained in native_value;
        # it is not reinterpreted as a failed metadata lookup or a zero-row page.
        missing = [] if suffix == "list_outputs" else [i for i in range(len(selected)) if i not in returned]
        return _finish("WorkspaceReceipt", {"method": _METHODS[suffix], "requested_objects": selected,
            "rows": rows, "native_value": native, "missing_requested_indices": missing}, common,
            [*diagnostics, *parsed["diagnostics"]], parsed["status"])
    if suffix == "upload":
        parsed, upload = _upload(prepared, native), resolved["upload"]
        value = {key: deepcopy(parsed["value"][key]) for key in
                 ("native_reply", "observed_node_id", "observed_file_size", "observed_checksums", "confirmation")}
        value.update(created_object=upload["object"]["object"], create_receipt_ref=args["created_object"]["receipt_ref"],
            shock_node_id=upload["shock_node_id"], input_binding_id=upload["input"]["binding_id"],
            input_content=upload["input"]["content"], filename=args["filename"])
        return _finish("UploadReceipt", value, common, [*diagnostics, *parsed["diagnostics"]], parsed["status"])
    if suffix == "task_info":
        parsed = decode_task_info(native, **prepared["native_operands"]["call"])
        value = {key: parsed["value"][key] for key in ("task_id", "file", "reported_object_uuid", "returned_representation", "local_window")}
        value.update(original_handoff_ref=bindings["original_handoff_ref"], body_complete=snapshot.transport["body_complete"])
        return _finish("TaskInfoReceipt", value, common, [*diagnostics, *parsed["diagnostics"]], parsed["status"])
    if suffix == "download_capability":
        parsed = _workspace(prepared, native, source_ref)
        rows = {row["request_index"]: row for row in parsed["records"] if row["request_index"] is not None}
        entries = []
        for i, obj in enumerate(resolved["objects"]):
            row = rows.get(i)
            url = row["download_url"] if row is not None and row["status"] == "ok" else None
            if url is None:
                diagnostics.append(_diag("capability_unavailable", f"/result/0/{i}", phase="association", refs=[source_ref]))
            entries.append({"input_index": i, "object_selection": obj["selection"], "object": obj["object"],
                "task_association": obj["task_association"], "url": url, "issued_observed_at": snapshot.retrieved_at,
                "expires_at": None, "expiry_evidence": None})
        diagnostics.extend(parsed["diagnostics"])
        return _finish("CapabilityReceipt", {"generation": args["generation"],
            "predecessor_receipt_ref": args["predecessor_receipt_ref"], "entries": entries}, common, diagnostics,
            _status(diagnostics, any(row["url"] is not None for row in entries)))
    if suffix in ("submit", "status"):
        task, issues = _task(prepared, native, source_ref)
        diagnostics.extend(issues)
        if task is None:
            return _finish("CommonReceipt", {}, common, diagnostics, "failed")
        diagnostics.extend(_diag(code, task["pointer"], severity="qualification", refs=[source_ref])
                           for code in task["qualification_codes"])
        if suffix == "status":
            return _finish("TaskObservation", {"original_task": resolved["original_task"], "native_map": native,
                "selected_record_pointer": task["pointer"], "native_status": task["native_status"],
                "state": task["state"], "native_timing": task["native_timing"],
                "qualification_codes": task["qualification_codes"]}, common, diagnostics, _status(issues, True))
        confirmed = [row for row in effects if row["descriptor"]["kind"] == "appservice_submit"
            and row["state"] == "confirmed" and row["confirmation_source_ref"] == source_ref
            and row["native_effect_identifiers"].get("task_id") == task["task_id"]]
        state = task["state"] if task["state"] in ("submitted", "running", "completed") else "submitted"
        usable = (task["state"] != "failed" and len(confirmed) == 1 and event.get("handoff_ready") is True
            and event.get("state") == state and event.get("failure_code") is None
            and event.get("native_handle") == {"task_id": task["task_id"]}
            and common["status"] == "ok" and not any(d["severity"] == "error" for d in diagnostics))
        if not usable:
            diagnostics.append(_diag("native_task_failed" if task["state"] == "failed" else "submission_handoff_unconfirmed",
                                     "/result/0", phase="association", refs=[source_ref]))
            return _finish("CommonReceipt", {}, common, diagnostics, "failed")
        preparation = resolved["preparation"]
        scheduler = None if task["parameters"] is None else {"value": task["parameters"],
            "evidence": {"content": common["snapshot"]["content"], "pointer": task["parameter_pointer"]}}
        original = {"resource_id": bindings["resource_id"], "task_id": task["task_id"],
            "required_application_id": request["required_application_id"],
            "native_application_id": preparation["native_application_id"],
            "submitted_parameters": request["parameters"], "submitted_start_parameters": request["start_parameters"],
            "scheduler_returned_parameters": scheduler, "effective_parameters": None,
            "submission_receipt_ref": common["receipt_ref"], "submission_operation_key": common["origin"]["operation_key"],
            "submission_source_ref": source_ref}
        return _finish("TaskHandoff", {"version": "bvbrc_appservice_task_handoff_v1",
            "original_job_owner": bindings["original_job_owner"], "original_task": original,
            "native_submission_record": task["raw"], "definition_evidence": preparation["definition_evidence"],
            "input_evidence_refs": args["input_evidence_refs"], "effect_receipt_ref": confirmed[0]["effect_ref"],
            "state": state, "usable_handoff": True}, common, diagnostics, "ok")
    raise ContractValidationError("support_operation_not_owned")


def _failure(code, row, diagnostics):
    return {"code": code, "phase": diagnostics[0]["phase"] if diagnostics else "native_decode",
        "affected_refs": [row["effect_ref"]], "affected_pointers": list(dict.fromkeys(
            d["path"] for d in diagnostics if d["severity"] == "error")),
        "effect_outcome": "unknown", "valid_record_refs": list(dict.fromkeys(
            reference for diagnostic in diagnostics for reference in diagnostic["evidence_refs"])),
        "requirements": []}


def confirm_appservice_effects(prepared, event, snapshot, *, snapshot_binding, effect_receipts):
    """Return exact journal outcome rows; never infer that an issued call was not sent."""
    prepared, event, receipts = _inputs(prepared, event, effect_receipts)
    if not receipts:
        return []
    _require(all(row["state"] != "prepared_not_issued" for row in receipts), "effect_issue_marker_required")
    if all(row["state"] in ("confirmed", "not_sent") for row in receipts):
        return [{key: deepcopy(row[key]) for key in _OUTCOME_FIELDS} for row in receipts]
    native, diagnostics = ((None, [_diag("issued_effect_unknown", phase="recovery")])
        if snapshot is None else _native(prepared, event, snapshot, snapshot_binding))
    source_ref = snapshot_binding["source_ref"] if not diagnostics else None
    suffix = prepared["operation"].removeprefix(_PREFIX)
    parsed, task = None, None
    if not diagnostics:
        if suffix in ("workspace_create", "download_capability"):
            parsed = _workspace(prepared, native, source_ref)
        elif suffix == "upload":
            parsed = _upload(prepared, native)
        elif suffix == "submit":
            task, diagnostics = _task(prepared, native, source_ref)
    outcomes = []
    for row in receipts:
        if row["state"] in ("confirmed", "not_sent"):
            outcomes.append({key: deepcopy(row[key]) for key in _OUTCOME_FIELDS})
            continue
        outcome = {"effect_ref": row["effect_ref"], "state": "issued_unknown", "confirmation_source_ref": None,
            "native_effect_identifiers": {}, "ancillary_effects": [], "failure": None}
        problems, identifiers = deepcopy(diagnostics), None
        kind, slot = row["descriptor"]["kind"], row["descriptor"]["slot"]
        if not problems and suffix == "workspace_create" and kind == "workspace_create":
            targets = prepared["native_operands"]["call"]["rpc_request"]["params"][0]["objects"]
            indices = [i for i, target in enumerate(targets) if target[0] == slot["target_path"]]
            matches = [r for r in parsed["records"] if any(i in r["request_indices"] for i in indices)]
            if len(indices) == 1 and len(matches) == 1 and matches[0]["status"] == "ok":
                match = matches[0]
                identifiers = {"target_path": slot["target_path"], "workspace_path": match["object_path"],
                    "workspace_uuid": match["object_id"], "workspace_type": match["type"],
                    "record_pointer": match["pointer"], "shock_url": match["shock_url"] or None}
            else:
                problems = parsed["diagnostics"] or [_diag("workspace_target_unconfirmed", "/result/0", phase="association")]
            outcome["ancillary_effects"] = [{"pointer": r["pointer"], "native_row": r["native_record"],
                "valid": r["status"] == "ok"} for r in parsed["records"] if not r["request_indices"]]
        elif not problems and suffix == "download_capability" and kind == "download_capability":
            objects = prepared["bound_inputs"]["resolved"]["objects"]
            indices = [i for i, obj in enumerate(objects) if obj["identity"] == slot["object_identity"]]
            matches = [r for r in parsed["records"] if r["request_index"] in indices]
            if (len(indices) == 1 and len(matches) == 1 and matches[0]["status"] == "ok"
                    and matches[0]["download_url"] is not None
                    and slot["generation"] == prepared["native_operands"]["arguments"]["generation"]):
                identifiers = {"object_identity": slot["object_identity"], "generation": slot["generation"],
                    "input_index": indices[0], "record_pointer": matches[0]["pointer"]}
            else:
                problems = [_diag("capability_unavailable", f"/result/0/{indices[0]}" if len(indices) == 1 else "/result/0", phase="association")]
        elif not problems and suffix == "upload" and kind == "shock_upload":
            value = parsed["value"]
            if (parsed["status"] == "ok" and value["observed_node_id"] == slot["shock_node_id"]
                    and value["confirmation"] in ("accepted_bytes_match", "accepted_identity_only")):
                identifiers = {"shock_node_id": value["observed_node_id"], "file_size": value["observed_file_size"],
                    "checksums": value["observed_checksums"], "confirmation": value["confirmation"], "record_pointer": "/data"}
            else:
                problems = parsed["diagnostics"] or [_diag("upload_node_mismatch", "/data/id", phase="association")]
        elif not problems and suffix == "submit" and kind == "appservice_submit" and task is not None:
            identifiers = {"task_id": task["task_id"],
                "native_application_id": prepared["bound_inputs"]["resolved"]["preparation"]["native_application_id"],
                "record_pointer": task["pointer"], "native_status": task["native_status"]}
        if identifiers is not None:
            outcome.update(state="confirmed", confirmation_source_ref=source_ref, native_effect_identifiers=identifiers)
        else:
            code = next((d["code"] for d in problems if d["severity"] == "error"), "issued_effect_unknown")
            outcome["failure"] = _failure(code, row, problems)
        validate_contract("EffectReceipt", {**row, **outcome})
        outcomes.append(outcome)
    return outcomes


__all__ = ["build_appservice_receipt", "confirm_appservice_effects"]
