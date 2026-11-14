"""Original AppService response, snapshot and task identity checks."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re
from urllib.parse import quote

from .acquisition import SourceSnapshot
from .api_services import event
from .bvbrc_analysis_protocol import decode_rpc_response, parse_task_records, parse_workspace_records
from .bvbrc_analysis_transport import SERVICE as TRANSPORT_SERVICE
from .bvbrc_appservice_contracts import download_request
from .bvbrc_appservice_readers import _decode_json, decode_task_info, decode_upload, qualify_download
from .bvbrc_appservice_tool_info import PREFIX
from .bvbrc_appservice_service_values import (
    _NATIVE_STATES, _RAW_STATES, _check, _same, _rpc_bytes, _failure, _diagnostic,
)

class AppServiceResponseDecoding:
    def _snapshot(self, prepared, snapshot):
        _check(isinstance(snapshot, SourceSnapshot) and snapshot.service == TRANSPORT_SERVICE,
               "native_response_invalid")
        call, kind = prepared["native_operands"]["call"], prepared["native_kind"]
        transport = snapshot.transport
        _check(type(transport) is dict and type(transport.get("body_complete")) is bool,
               "native_response_invalid")
        _check(type(transport.get("status")) is int and 100 <= transport["status"] <= 599,
               "native_response_invalid")
        _check(type(snapshot.content) is bytes and transport.get("received_body_bytes") == len(snapshot.content),
               "native_response_invalid")
        sent = transport.get("request")
        _check(type(sent) is dict, "native_response_invalid")
        if kind == "rpc":
            rpc = call["rpc_request"]
            url = self.configuration["endpoints"][rpc["method"].split(".", 1)[0]]
            _check(_same(snapshot.request, {"kind": "rpc", "rpc": rpc}), "native_response_invalid")
            body = _rpc_bytes(rpc)
            _check(sent.get("method") == "POST" and sent.get("body_bytes") == len(body)
                   and sent.get("body_sha256") == hashlib.sha256(body).hexdigest(), "native_response_invalid")
        elif kind == "task_info":
            url = self.configuration["endpoints"]["AppService"].rstrip("/") + "/task_info/" + quote(call["task_id"], safe="") + "/" + call["file"]
            _check(_same(snapshot.request, {"kind": "task_info", **call}) and sent.get("method") == "GET",
                   "native_response_invalid")
        elif kind == "download":
            url = call["url"]
            _check(_same(snapshot.request, download_request(call,
                    arguments=prepared["native_operands"]["arguments"]))
                   and sent.get("method") == "GET", "native_response_invalid")
        else:
            url = call["node_url"]
            request = snapshot.request
            boundary = "gene-annotation-" + hashlib.sha256(call["filename"].encode("utf-8")
                + b"\x00" + bytes.fromhex(call["content"]["sha256"])).hexdigest()
            prefix = (f'--{boundary}\r\nContent-Disposition: form-data; name="upload"; '
                f'filename="{call["filename"]}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode("utf-8")
            suffix = f"\r\n--{boundary}--\r\n".encode("ascii")
            _check(type(request) is dict and request.get("kind") == "upload"
                   and request.get("node_url") == url and request.get("filename") == call["filename"]
                   and request.get("input_bytes") == call["content"]["byte_count"]
                   and request.get("input_sha256") == call["content"]["sha256"]
                   and request.get("multipart_field") == "upload" and request.get("multipart_boundary") == boundary
                   and sent.get("method") == "PUT"
                   and sent.get("body_bytes") == len(prefix) + call["content"]["byte_count"] + len(suffix)
                   and type(sent.get("body_sha256")) is str and re.fullmatch(r"[0-9a-f]{64}", sent["body_sha256"]) is not None,
                   "native_response_invalid")
        _check(snapshot.url == url and sent.get("url") == url
               and transport.get("effective_url") == url and transport.get("automatic_redirects") is False,
               "native_response_invalid")

    def decode(self, prepared, snapshot):
        prepared = self._prepared(prepared)
        operands, bindings = prepared["native_operands"], prepared["bound_inputs"]
        resolved, suffix = bindings["resolved"], prepared["operation"].removeprefix(PREFIX)
        kind = prepared["native_kind"]
        facts = {"operation": prepared["operation"], "parse_status": "invalid", "diagnostics": []}
        if kind == "local_prepare":
            failure = operands["local_failure"]
            if failure is None:
                c3 = operands["call"]["c3_result"]
                facts["c3_result"] = deepcopy(c3)
                facts["parse_status"] = c3["status"]
                failure = None if c3["status"] == "ok" else _failure("application_preparation_invalid")
            facts["failure"] = failure
            return event("preparation", "completed" if failure is None else "failed", facts=facts,
                         failure_code=None if failure is None else failure["code"])
        handle = {"task_id": resolved["original_task"]["task_id"]} if "original_task" in resolved else None
        try:
            self._snapshot(prepared, snapshot)
        except (ValueError, KeyError, TypeError) as error:
            return self._failed_event(prepared, facts, "native_response_invalid", handle=handle)
        facts["body_complete"] = snapshot.transport["body_complete"]
        facts["http_status"] = snapshot.transport["status"]
        if kind == "download":
            parsed = qualify_download(snapshot, capability=resolved["capability"]["entry"],
                object_binding={key: resolved["object"][key] for key in ("object", "metadata")})
            facts.update(parse_status=parsed["status"], diagnostics=parsed["diagnostics"], projection=parsed["value"])
            error = next((d["code"] for d in parsed["diagnostics"] if d["severity"] == "error"), None)
            facts["failure"] = None if error is None else _failure(error, phase="transport", effect_outcome=None)
            # Actual bytes remain useful even if the body or requested form is
            # partial; only the custody host decides original-form completion.
            return event("response", "failed" if parsed["status"] == "failed" else "completed",
                native_handle=handle, result_available=bool(snapshot.content) or parsed["value"]["object_complete"] == "yes",
                facts=facts, failure_code=error)
        if not 200 <= snapshot.transport["status"] < 300:
            code = "task_info_unavailable" if kind == "task_info" else "native_http_error"
            return self._failed_event(prepared, facts, code, handle=handle, phase="transport")
        if not snapshot.transport["body_complete"]:
            return self._failed_event(prepared, facts, "native_response_invalid", handle=handle, phase="transport")
        if kind == "task_info":
            parsed = decode_task_info(snapshot.content, **operands["call"])
            projection = {key: value for key, value in parsed["value"].items() if key != "text"}
            facts.update(parse_status=parsed["status"], diagnostics=parsed["diagnostics"], projection=projection)
            if parsed["status"] != "ok":
                return self._failed_event(prepared, facts, "task_info_object_invalid", handle=handle)
            facts["qualification_codes"] = ["execution_state_not_observed", "signature_redacted_representation"]
            return event("job", "unknown", native_handle=handle, facts=facts)
        if kind == "upload":
            native, issues = _decode_json(snapshot.content)
            if any(row["severity"] == "error" for row in issues):
                facts["diagnostics"] = issues
                return self._failed_event(prepared, facts, "native_response_invalid")
            upload = resolved["upload"]
            parsed = decode_upload(native, expected_node_id=upload["shock_node_id"],
                expected_bytes=upload["input"]["content"]["byte_count"], supplied_sha256=upload["input"]["content"]["sha256"])
            facts.update(parse_status=parsed["status"], diagnostics=parsed["diagnostics"], projection=parsed["value"])
            code = next((d["code"] for d in parsed["diagnostics"] if d["severity"] == "error"), None)
            if code:
                return self._failed_event(prepared, facts, code)
            return event("metadata", "completed", facts=facts)
        rpc = operands["call"]["rpc_request"]
        decoded = decode_rpc_response(snapshot.content, method=rpc["method"], request_id=rpc["id"],
                                      http_status=snapshot.transport["status"])
        facts["rpc_diagnostics"] = decoded["diagnostics"]
        if decoded["status"] != "ok":
            code = "native_rpc_error" if any(d["code"] == "native_rpc_error" for d in decoded["diagnostics"]) else "native_response_invalid"
            return self._failed_event(prepared, facts, code, handle=handle)
        native = decoded["value"]
        if suffix == "enumerate_apps":
            _valid = lambda row: type(row) is dict and type(row.get("id")) is str and bool(row["id"]) and type(row.get("parameters")) is list
            valid = sum(_valid(row) for row in native) if type(native) is list else 0
            facts.update(parse_status="ok" if type(native) is list and valid == len(native) else "partial" if valid else "invalid",
                         returned_records=len(native) if type(native) is list else None, valid_records=valid)
            if facts["parse_status"] == "invalid":
                return self._failed_event(prepared, facts, "native_response_invalid")
            return event("metadata", "completed", facts=facts)
        if suffix in ("workspace_metadata", "workspace_create", "list_outputs", "download_capability"):
            method = rpc["method"].split(".", 1)[1]
            options = rpc["params"][0]
            references = [row[0] for row in options["objects"]] if method == "create" else options["paths" if method == "ls" else "objects"]
            parsed = parse_workspace_records(native, operation=method, requested_paths=references)
            facts.update(parse_status=parsed["status"], workspace_records=parsed["records"],
                         workspace_diagnostics=parsed["diagnostics"])
            if suffix == "download_capability":
                # Capability URLs stay only in the retained HTTP source and
                # host-private capability receipts, never in event summaries.
                facts["workspace_records"] = [{key: value for key, value in row.items()
                    if key not in ("download_url", "native_record")} | {"available": row["download_url"] is not None}
                    for row in parsed["records"]]
            if method == "create":
                targets = {row["target_id"]: row for row in operands["request"]["workspace_targets"]}
                for row in parsed["records"]:
                    for index in row["request_indices"]:
                        expected = targets[operands["arguments"]["objects"][index]["target_id"]]
                        if row["type"] != expected["type"]:
                            row["status"] = "invalid"
                            row["diagnostics"].append({"code": "workspace_target_conflict", "path": "$"})
                            facts["parse_status"] = "partial" if any(r["status"] == "ok" for r in parsed["records"]) else "invalid"
            if facts["parse_status"] != "ok":
                facts["failure"] = _failure("workspace_member_failed", phase="native_decode",
                    effect_outcome="unknown" if prepared["mutates_remote"] else None)
            return event("metadata", "failed" if facts["parse_status"] == "invalid" else "completed",
                         facts=facts, failure_code=None if facts["parse_status"] == "ok" else "workspace_member_failed")
        return self._decode_task(prepared, native, facts, handle)

    def _failed_event(self, prepared, facts, code, *, handle=None, phase="native_decode", effect_outcome=None):
        facts["failure"] = _failure(code, phase=phase,
            effect_outcome=effect_outcome or ("unknown" if prepared["mutates_remote"] else None))
        return event("job" if prepared["purpose"] in ("handoff", "observation") else "response",
                     "failed", native_handle=handle, facts=facts, failure_code=code)

    def _decode_task(self, prepared, native, facts, handle):
        suffix = prepared["operation"].removeprefix(PREFIX)
        submission = suffix == "submit"
        resolved = prepared["bound_inputs"]["resolved"]
        rpc = prepared["native_operands"]["call"]["rpc_request"]
        native_app = (resolved["preparation"]["native_application_id"] if submission else resolved["original_task"]["native_application_id"])
        expected_params = prepared["native_operands"]["request"]["parameters"]
        parsed = parse_task_records(native, operation="start_app2" if submission else "query_tasks",
            requested_task_ids=None if submission else [resolved["original_task"]["task_id"]])
        facts.update(task_records=parsed["records"], task_diagnostics=parsed["diagnostics"], parse_status=parsed["status"])
        if submission:
            selected_rows = parsed["records"] if parsed["status"] == "ok" else []
        else:
            selected_rows = [row for row in parsed["records"] if row["status"] == "ok"
                and str(row["task_id"]) == resolved["original_task"]["task_id"]]
        if len(selected_rows) != 1:
            return self._failed_event(prepared, facts, "original_task_mismatch", handle=handle)
        row = selected_rows[0]
        raw = row["native_record"]
        parameters, parameters_pointer = None, None
        qualifications = []
        if not submission and parsed["status"] != "ok":
            qualifications.append("unrequested_or_invalid_task_records_retained")
        for field in ("application_id", "app"):
            if field in raw and raw[field] is not None and raw[field] != native_app:
                return self._failed_event(prepared, facts, "original_task_mismatch", handle=handle)
        if row["application_id"] is None:
            qualifications.append("submission_application_echo_unobserved" if submission else "task_application_echo_unobserved")
        for field in ("params", "parameters"):
            if field not in raw or raw[field] is None:
                continue
            value = raw[field]
            if field == "params":
                value, issues = _decode_json(value.encode("utf-8")) if type(value) is str else (None, [_diagnostic("native_response_invalid")])
                if any(d["severity"] == "error" for d in issues):
                    return self._failed_event(prepared, facts, "submission_parameters_conflict", handle=handle)
            if type(value) is not dict or any(key not in value or not _same(value[key], operand) for key, operand in expected_params.items()):
                return self._failed_event(prepared, facts, "submission_parameters_conflict", handle=handle)
            if parameters is not None and not _same(parameters, value):
                return self._failed_event(prepared, facts, "submission_parameters_conflict", handle=handle)
            parameters = value
            if parameters_pointer is None:
                parameters_pointer = "/result/0/" + field
        if parameters is None:
            qualifications.append("submission_parameters_echo_unobserved" if submission else "task_parameters_echo_unobserved")
        # app_spec is serialized in the raw SchedulerDB receipt. Preserve the
        # original field; validate every application identity it actually echoes.
        if raw.get("app_spec") is not None:
            app_spec, issues = _decode_json(raw["app_spec"].encode("utf-8")) if type(raw["app_spec"]) is str else (None, [_diagnostic("native_response_invalid")])
            if any(d["severity"] == "error" for d in issues) or type(app_spec) is not dict or app_spec.get("id") != native_app:
                return self._failed_event(prepared, facts, "original_task_mismatch", handle=handle)
        original_start = prepared["native_operands"]["request"]["start_parameters"]
        if raw.get("start_parameters") is not None and (type(raw["start_parameters"]) is not dict
                or any(key not in raw["start_parameters"] or not _same(raw["start_parameters"][key], value)
                       for key, value in original_start.items())):
            return self._failed_event(prepared, facts, "submission_parameters_conflict", handle=handle)
        for field, native_field in (("parent_id", "parent_task"), ("base_url", "base_url"),
                ("user_metadata", "user_metadata")):
            if submission and field in original_start and native_field in raw and not _same(raw[native_field], original_start[field]):
                return self._failed_event(prepared, facts, "submission_parameters_conflict", handle=handle)
        for field in ("container_id", "data_container_id"):
            expected = expected_params.get(field)
            if expected is None:
                expected = original_start.get(field)
            # The inspected scheduler's determine_*_override gives task
            # parameters precedence. The returned field is that effective
            # value, not an echo replacing the original StartParams operand.
            if submission and field in raw and expected is not None and not _same(raw[field], expected):
                return self._failed_event(prepared, facts, "submission_parameters_conflict", handle=handle)
            if submission and field in raw and expected_params.get(field) is not None and field in original_start:
                qualifications.append("native_task_parameter_" + field + "_override")
        for field in ("output_path", "output_file"):
            if field in raw and raw[field] is not None and field in expected_params and not _same(raw[field], expected_params[field]):
                return self._failed_event(prepared, facts, "submission_parameters_conflict", handle=handle)
        native_status = row["native_state"]
        state = (_RAW_STATES if submission else _NATIVE_STATES).get(native_status, "unknown")
        if state == "unknown":
            qualifications.append("native_state_unknown")
        task_id = str(row["task_id"])
        facts.update(native_task_id=task_id, native_status=native_status,
            scheduler_returned_parameters=deepcopy(parameters) if submission else None,
            scheduler_parameters_pointer=parameters_pointer if submission else None,
            additional_native_parameters=({key: deepcopy(value) for key, value in parameters.items() if key not in expected_params} if parameters is not None else {}),
            native_timing={field: deepcopy(raw.get(field)) for field in ("submit_time", "start_time", "completed_time", "elapsed_time")},
            qualification_codes=qualifications)
        if submission:
            facts["submission_acknowledged"] = True
            if state == "failed":
                return self._failed_event(prepared, facts, "native_task_failed", handle={"task_id": task_id},
                                          effect_outcome="confirmed")
            # The exact correlated successful creation response and its task ID
            # acknowledge submission even when no native state echo is supplied.
            acknowledged_state = state if state in ("submitted", "running", "completed") else "submitted"
            return event("job", acknowledged_state, native_handle={"task_id": task_id},
                         handoff_ready=True, facts=facts)
        return event("job", state, native_handle={"task_id": task_id}, facts=facts)

