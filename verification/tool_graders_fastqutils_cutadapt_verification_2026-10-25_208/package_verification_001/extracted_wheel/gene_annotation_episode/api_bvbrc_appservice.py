"""One explicitly selected AppService/Workspace primitive.

Custody, effect reservation, durable issue/recovery and publication belong to
the host. This component makes no choices, searches, retry loops or scientific
calculations. Prepared operands are finite JSON and reconstruct locally.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from urllib.parse import urlsplit, quote

from .acquisition import AcquisitionError, SourceSnapshot
from .api_services import event
from .bvbrc_analysis_protocol import (
    decode_rpc_response, parse_task_records, parse_workspace_records, prepare_rpc_request,
)
from .bvbrc_analysis_transport import BVBRCAnalysisClient, SERVICE as TRANSPORT_SERVICE, _url
from .bvbrc_application_definitions import prepare_application
from .bvbrc_appservice_contracts import contract_schema, validate_contract, validate_request
from .bvbrc_appservice_readers import (
    _decode_json, _object_binding, decode_task_info, decode_upload, qualify_download,
)
from .bvbrc_appservice_tool_info import (
    PREFIX, OPERATIONS, LAUNCH_OPERATIONS, RESULT_OPERATIONS, operation_catalog,
)
from .domain import ContractError, canonical


SERVICE = "bvbrc_appservice"
EXECUTION_CONTRACT = "bvbrc_appservice_execution_v1"
_UUID = re.compile(r"[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}\Z")
_NATIVE_STATES = {"queued": "submitted", "pending": "submitted", "running": "running",
                  "in-progress": "running", "completed": "completed", "failed": "failed",
                  "deleted": "failed"}
_RAW_STATES = {"Q": "submitted", "S": "submitted", "C": "completed", "F": "failed",
               "D": "failed", "T": "failed"}


def _digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _same(left, right):
    return canonical(left) == canonical(right)


def _check(condition, code):
    if not condition:
        raise ContractError(code)


def _embedded_schema(name):
    schema = contract_schema(name)
    schema["$id"] = "urn:gene-annotation:bvbrc-appservice:" + name
    return schema


def _failure(code, *, phase="prepare", effect_outcome="not_sent", refs=(), pointers=()):
    return validate_contract("Failure", {"code": code, "phase": phase,
        "affected_refs": list(dict.fromkeys(refs)), "affected_pointers": list(dict.fromkeys(pointers)),
        "effect_outcome": effect_outcome, "valid_record_refs": [], "requirements": []})


def _diagnostic(code, *, path="", phase="native_decode", severity="error"):
    return {"code": code, "path": path, "phase": phase, "severity": severity, "evidence_refs": []}


def _rpc_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _check_task(task, request, bindings):
    _check(task["resource_id"] == bindings["resource_id"]
           and task["required_application_id"] == request["required_application_id"]
           and _same(task["submitted_parameters"], request["parameters"])
           and _same(task["submitted_start_parameters"], request["start_parameters"]),
           "original_task_mismatch")
    _check(bindings["original_handoff_ref"] is not None, "original_task_mismatch")


def _native_reference_matches(left, right):
    if left == right:
        return True
    if type(left) is not str or type(right) is not str:
        return False
    if _UUID.fullmatch(left) and _UUID.fullmatch(right):
        return left.lower() == right.lower()
    if left.startswith("/") and right.startswith("/"):
        return re.sub(r"/+", "/", left).rstrip("/") == re.sub(r"/+", "/", right).rstrip("/")
    return False


def _check_object(row, selection, *, task=None, require_association=True):
    _check(_same(row["selection"], selection), "workspace_target_conflict")
    obj, _ = _object_binding({"object": row["object"], "metadata": row["metadata"]})
    reference = row["native_reference"]
    # Only the host establishes aliases; local projection must still carry
    # the actual selected spelling or exact object UUID.
    _check(any(_native_reference_matches(reference, value) for value in (obj["path"], obj["uuid"])),
           "workspace_target_conflict")
    association = row["task_association"]
    if association is not None:
        _check(task is None or association["task_id"] == task["task_id"], "original_task_mismatch")
        for field, associated in (("path", "output_path"), ("uuid", "output_uuid")):
            _check(association[associated] is None or association[associated] == obj[field],
                   "output_association_missing")
    if task is not None and require_association:
        _check(association is not None, "output_association_missing")


def _check_original_object(row, request):
    selected = row["selection"]
    if selected["kind"] == "original_target":
        targets = [item for item in request["workspace_targets"] if item["target_id"] == selected["target_id"]]
        _check(len(targets) == 1 and _native_reference_matches(targets[0]["path"], row["object"]["path"])
               and row["object"]["type"] in (None, targets[0]["type"]), "workspace_target_conflict")
    elif selected["kind"] == "original_input":
        inputs = [item for item in request["input_bindings"] if item["binding_id"] == selected["input_binding_id"]]
        _check(len(inputs) == 1 and inputs[0]["workspace_path"] is not None
               and _native_reference_matches(inputs[0]["workspace_path"], row["object"]["path"]), "workspace_target_conflict")


class BVBRCAppServiceService:
    service = SERVICE
    request_schema = _embedded_schema("AppServiceRequest")
    selector_schema = _embedded_schema("ResultSelector")

    def __init__(self, tool_registry, configuration=None, *, client=None,
                 publication_callback=None):
        config = validate_contract("ServiceConfiguration", configuration)
        configured = BVBRCAnalysisClient(config["endpoints"], timeout=config.get("timeout", 90),
            authorization_env=config.get("authorization_env"),
            authorization_origins=config.get("authorization_origins", ()))
        _check(publication_callback is None or callable(publication_callback),
               "appservice_publication_callback_invalid")
        self.tools, self.configuration = tool_registry, config
        self.client = configured if client is None else client
        self.publication_callback = publication_callback
        from .bvbrc_appservice_adapters import bind_adapters
        self.scientific_adapters = bind_adapters(config['scientific_adapters'])

    def validate_request(self, request, scope):
        value = validate_request(request)
        if scope is not None:
            self.tools.store.validate_scope(scope)
        return value

    @staticmethod
    def capabilities():
        return operation_catalog("launch_api")

    @staticmethod
    def result_capabilities():
        return operation_catalog("results")

    def launch_catalog(self, request):
        self.validate_request(request, None)
        return self.capabilities()

    def result_catalog(self, request, selector):
        self.validate_request(request, None)
        validate_contract("ResultSelector", selector)
        from .bvbrc_appservice_adapters import selected_adapter
        binding = selected_adapter(self, selector['adapter'])
        if binding is not None:
            implementation, _ = binding
            implementation.validate_parameters(selector['adapter']['parameters'])
            implementation.validate_requested_form(selector['requested_schema'])
            if (selector['adapter']['adapter_id'], selector['adapter']['adapter_version']) == ('bvbrc_proteome', '2'):
                implementation.validate_result_selector(selector)
        return self.result_capabilities()

    def prepare(self, name, request, arguments, *, scope, previous_events,
                handle=None, selector=None, bound_inputs=None):
        request = self.validate_request(request, scope)
        selection = validate_contract("OperationSelection", {"name": name, "arguments": arguments})
        arguments = selection["arguments"]
        _check(name in (LAUNCH_OPERATIONS if selector is None else RESULT_OPERATIONS),
               "bvbrc_appservice_operation_not_available")
        if selector is not None:
            selector = validate_contract("ResultSelector", selector)
        bindings = validate_contract("BoundInputs", bound_inputs)
        _check(bindings["request_sha256"] == _digest(request)
               and bindings["selected_argument_sha256"] == _digest(arguments)
               and bindings["resolved"]["operation"] == name, "prepared_binding_conflict")
        resolved = bindings["resolved"]
        suffix = name.removeprefix(PREFIX)
        task = resolved.get("original_task")
        if task is not None:
            _check_task(task, request, bindings)
            if "handoff_ref" in arguments:
                _check(arguments["handoff_ref"] == bindings["original_handoff_ref"], "original_task_mismatch")
            if handle:
                _check(handle.get("task_id") == task["task_id"], "original_task_mismatch")
        elif handle:
            raise ContractError("original_task_mismatch")

        call, effects, local_failure = {}, [], None
        kind, purpose = "rpc", "support"

        def effect(effect_kind, slot, payload, predecessors=()):
            effects.append(validate_contract("EffectDescriptor", {
                "version": "selected_api_effects_v1", "original_job_owner": bindings["original_job_owner"],
                "resource_id": bindings["resource_id"], "kind": effect_kind,
                "slot": {"kind": effect_kind, **slot}, "payload_sha256": _digest(payload),
                "predecessor_evidence_refs": list(dict.fromkeys(predecessors))}))

        method, params = None, None
        if suffix == "enumerate_apps":
            method, params = "AppService.enumerate_apps", []
        elif suffix == "prepare":
            kind = "local_prepare"
            _check(bindings["definition"] is not None, "definition_not_possessed")
            definition = resolved["definition_envelope"]
            if arguments["definition"]["kind"] == "packaged":
                _check(arguments["definition"]["required_application_id"] == request["required_application_id"],
                       "definition_extraction_mismatch")
            call["c3_result"] = prepare_application(request["required_application_id"], request["parameters"],
                request["start_parameters"], definition=definition)
        elif suffix in ("workspace_metadata", "list_outputs", "download_capability"):
            objects = resolved["objects"]
            _check(len(objects) == len(arguments["objects"]), "workspace_target_conflict")
            for row, selected in zip(objects, arguments["objects"], strict=True):
                _check_object(row, selected, task=task, require_association=suffix != 'workspace_metadata')
                _check_original_object(row, request)
            references = [row["native_reference"] for row in objects]
            if suffix == "workspace_metadata":
                method, params = "Workspace.get", [{"objects": references, "metadata_only": 1, **arguments["options"]}]
            elif suffix == "list_outputs":
                method, params = "Workspace.ls", [{"paths": references, **arguments["options"]}]
            else:
                method, params = "Workspace.get_download_url", [{"objects": references}]
                identities = [row["identity"] for row in objects]
                _check(len(identities) == len(set(identities)), "workspace_row_ambiguous")
                predecessors = resolved["predecessor_effect_refs"]
                _check(bool(predecessors) == (arguments["generation"] > 0), "capability_predecessor_conflict")
                for row in objects:
                    effect("download_capability", {"object_identity": row["identity"], "generation": arguments["generation"]},
                           {"reference": row["native_reference"], "object": row["object"], "generation": arguments["generation"]},
                           [*predecessors, *([arguments["predecessor_receipt_ref"]] if arguments["predecessor_receipt_ref"] else [])])
        elif suffix == "workspace_create":
            targets = {row["target_id"]: row for row in request["workspace_targets"]}
            inputs = {row["binding_id"]: row for row in request["input_bindings"]}
            supplied = {row["binding_id"]: row for row in resolved["data_bindings"]}
            selected_ids = {row["data_binding_id"] for row in arguments["objects"] if row["data_binding_id"] is not None}
            _check(len(supplied) == len(resolved["data_bindings"]) and set(supplied) == selected_ids,
                   "input_not_possessed")
            _check(all(key in inputs and _same(inputs[key], value) for key, value in supplied.items()), "input_bytes_mismatch")
            tuples = []
            options = arguments["options"]
            for selected in arguments["objects"]:
                _check(selected["target_id"] in targets, "workspace_target_conflict")
                target = targets[selected["target_id"]]
                if not target["allow_create_parents"]:
                    local_failure = _failure("workspace_parent_creation_constraint_unsupported")
                _check(options.get("overwrite", 0) != 1 or target["allow_overwrite"], "workspace_target_conflict")
                data = None
                binding_id = selected["data_binding_id"]
                if binding_id is not None:
                    binding = supplied[binding_id]
                    _check(target["input_binding_id"] == binding_id, "workspace_target_conflict")
                    if binding["kind"] == "supplied_link":
                        _check(options.get("downloadFromLinks", 0) == 1 and options.get("createUploadNodes", 0) != 1,
                               "workspace_target_conflict")
                        data = binding["inline_value"]
                    elif binding["kind"] == "inline_parameter":
                        _check(options.get("downloadFromLinks", 0) != 1 and options.get("createUploadNodes", 0) != 1,
                               "workspace_target_conflict")
                        data = binding["inline_value"]
                    elif binding["kind"] == "retained_bytes":
                        _check(options.get("createUploadNodes", 0) == 1 and options.get("downloadFromLinks", 0) != 1,
                               "workspace_target_conflict")
                    else:
                        raise ContractError("workspace_target_conflict")
                else:
                    _check(options.get("downloadFromLinks", 0) != 1, "input_not_possessed")
                native = [target["path"], target["type"], deepcopy(target["metadata"]), data, selected["creation_time"]]
                tuples.append(native)
                effect("workspace_create", {"target_path": target["path"]}, {"target": target, "native_object": native, "options": options})
            method, params = "Workspace.create", [{"objects": tuples, **options}]
        elif suffix == "upload":
            kind = "upload"
            upload = resolved["upload"]
            row, binding = upload["object"], upload["input"]
            selected = {"kind": "receipt_row", **arguments["created_object"]}
            _check_object(row, selected)
            originals = {row["binding_id"]: row for row in request["input_bindings"]}
            _check(binding["binding_id"] == arguments["input_binding_id"] and binding["kind"] == "retained_bytes"
                   and _same(originals.get(binding["binding_id"]), binding), "input_bytes_mismatch")
            _check(_native_reference_matches(row["object"]["path"], binding["workspace_path"])
                   and row["object"]["metadata_receipt_ref"] == arguments["created_object"]["receipt_ref"],
                   "workspace_target_conflict")
            _check(row["metadata"] is not None and row["metadata"]["shock_url"] == upload["shock_url"], "upload_node_mismatch")
            url = _url(upload["shock_url"])
            parts = urlsplit(url)
            _check(not parts.query and parts.path.rstrip("/").endswith("/node/" + upload["shock_node_id"])
                   and _UUID.fullmatch(upload["shock_node_id"]) is not None, "upload_node_mismatch")
            filename = arguments["filename"]
            _check(not any(char in filename for char in ('\r', '\n', '\x00', '"', '/', '\\')), "bvbrc_upload_filename_invalid")
            call = {"node_url": url, "filename": filename, "content": deepcopy(binding["content"])}
            effect("shock_upload", {"shock_node_id": upload["shock_node_id"]},
                   {"node_url": url, "input_binding_id": binding["binding_id"],
                    "sha256": binding["content"]["sha256"], "byte_count": binding["content"]["byte_count"], "filename": filename})
        elif suffix == "submit":
            purpose = "handoff"
            preparation = resolved["preparation"]
            _check(preparation["receipt"]["receipt_ref"] == arguments["preparation_receipt_ref"]
                   and preparation["receipt"]["origin"]["name"] == PREFIX + "prepare"
                   and preparation["request_sha256"] == _digest(request), "application_preparation_invalid")
            c3 = preparation["c3_result"]
            _check(preparation["receipt"]["status"] == "ok" and c3.get("status") == "ok"
                   and type(c3.get("value")) is dict, "application_preparation_invalid")
            native = c3["value"]
            _check(preparation["required_application_id"] == request["required_application_id"]
                   and native.get("required_id") == request["required_application_id"]
                   and native.get("native_application_id") == preparation["native_application_id"]
                   and _same(preparation["native_parameters"], request["parameters"])
                   and _same(preparation["start_parameters"], request["start_parameters"])
                   and _same(native.get("native_params"), [preparation["native_application_id"], request["parameters"], request["start_parameters"]]),
                   "submission_parameters_conflict")
            allowed = {request["required_application_id"]}
            if request["required_application_id"] == "InfluenzaHASubtypeConversion":
                allowed.add("HASubtypeNumberingConversion")
            _check(preparation["native_application_id"] in allowed, "original_task_mismatch")
            method, params = "AppService.start_app2", deepcopy(native["native_params"])
            effect("appservice_submit", {}, {"method": method, "params": params})
        elif suffix in ("status", "task_info"):
            purpose = "observation"
            if suffix == "status":
                method, params = "AppService.query_tasks", [[task["task_id"]]]
            else:
                kind, call = "task_info", {"task_id": task["task_id"], "file": arguments["file"]}
                _check(re.fullmatch(r"[A-Za-z0-9_-]+", task["task_id"]) is not None,
                       "bvbrc_task_info_selection_invalid")
        elif suffix == "download":
            kind, purpose = "download", "acquisition"
            row, capability = resolved["object"], resolved["capability"]
            _check_object(row, arguments["object"], task=task)
            _check_original_object(row, request)
            _check(_same(capability["selection"], arguments["capability"])
                   and _same(bindings["capability"], arguments["capability"]), "capability_not_possessed")
            entry = capability["entry"]
            _check(_same(entry["object_selection"], arguments["object"])
                   and _same(entry["object"], row["object"])
                   and _same(entry["task_association"], row["task_association"]), "output_association_missing")
            if capability["selection"]["kind"] == "acquired":
                _check(entry["input_index"] == capability["selection"]["input_index"], "capability_not_possessed")
            requirements = {row["requirement_id"]: row for row in selector["requirements"]}
            for requirement_id in arguments["requirement_ids"]:
                _check(requirement_id in requirements, "publication_dependency_conflict")
                requirement = requirements[requirement_id]
                _check(requirement["role"] == arguments["role"]
                       and _same(requirement["declared_format"], arguments["declared_format"])
                       and (requirement["exact_object"] is None or _same(requirement["exact_object"], arguments["object"])),
                       "publication_dependency_conflict")
            if entry["url"] is None:
                local_failure = _failure("capability_unavailable", phase="association", effect_outcome=None)
            else:
                _url(entry["url"])
            call = {"url": entry["url"], "byte_range": arguments["byte_range"]}
        else:
            raise ContractError("bvbrc_appservice_operation_not_available")

        if method is not None:
            rpc_id = "bvbrc_rpc_" + _digest({"operation": name, "owner": bindings["original_job_owner"],
                "resource_id": bindings["resource_id"], "request": bindings["request_sha256"],
                "arguments": bindings["selected_argument_sha256"]})
            call = {"rpc_request": prepare_rpc_request(method, params, request_id=rpc_id)}
        if local_failure is not None:
            kind, effects = "local_prepare", []
        return validate_contract("PreparedOperation", {
            "version": "bvbrc_appservice_prepared_operation_v1", "execution_contract": EXECUTION_CONTRACT,
            "operation": name, "purpose": purpose, "request_sha256": _digest(request),
            "arguments_sha256": _digest(arguments), "bound_inputs": bindings,
            "mutates_remote": bool(effects), "effects": effects, "native_kind": kind,
            "native_operands": {"request": request, "arguments": arguments, "selector": selector,
                                "call": call, "local_failure": local_failure}})

    def _prepared(self, prepared):
        value = validate_contract("PreparedOperation", prepared)
        operands = value["native_operands"]
        _check(set(operands) == {"request", "arguments", "selector", "call", "local_failure"},
               "bvbrc_appservice_prepared_request_conflict")
        expected = self.prepare(value["operation"], operands["request"], operands["arguments"],
            scope=None, previous_events=[], selector=operands["selector"], bound_inputs=value["bound_inputs"])
        _check(_same(value, expected), "bvbrc_appservice_prepared_request_conflict")
        return value

    def invoke(self, prepared, *, upload_content=None):
        prepared = self._prepared(prepared)
        kind, call = prepared["native_kind"], prepared["native_operands"]["call"]
        if kind == "local_prepare":
            return None
        if kind == "rpc":
            return self.client.rpc(call["rpc_request"])
        if kind == "task_info":
            return self.client.task_info(call["task_id"], call["file"])
        if kind == "download":
            selected_range = call["byte_range"]
            return self.client.download(call["url"], byte_range=None if selected_range is None else tuple(selected_range))
        binding = call["content"]
        try:
            # The asynchronous executor resolves the exact artifact on the
            # Store's owning thread, before running transport in a worker.
            # Direct synchronous callers retain the same artifact-read path.
            content = (self.tools.store.get_artifact(binding["artifact_ref"])
                       if upload_content is None else upload_content)
        except (ValueError, KeyError, OSError) as error:
            raise AcquisitionError("input_not_possessed", phase="prepare", submission_outcome="not_sent") from error
        if type(content) is not bytes or len(content) != binding["byte_count"] or hashlib.sha256(content).hexdigest() != binding["sha256"]:
            raise AcquisitionError("input_bytes_mismatch", phase="prepare", submission_outcome="not_sent")
        return self.client.upload(call["node_url"], content, filename=call["filename"])

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
            _check(_same(snapshot.request, {"kind": "download", "url": url,
                    "requested_byte_range": call["byte_range"]}) and sent.get("method") == "GET", "native_response_invalid")
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

    def prepare_observation(self, request, handle, *, scope, native_operation, bound_inputs=None):
        _check(native_operation in ("query_tasks", "stdout", "stderr"), "bvbrc_appservice_observation_invalid")
        bindings = validate_contract("BoundInputs", bound_inputs)
        suffix = "status" if native_operation == "query_tasks" else "task_info"
        arguments = {"handoff_ref": bindings["original_handoff_ref"]}
        if suffix == "task_info":
            arguments["file"] = native_operation
        return self.prepare(PREFIX + suffix, request, arguments, scope=scope, previous_events=[],
                            handle=handle, bound_inputs=bindings)

    def publish(self, request, selector, snapshot, scope, operation_key, *,
                submission_snapshot=None, handle=None, publication_inputs=None):
        original = self.validate_request(request, scope)
        selector = validate_contract("ResultSelector", selector)
        inputs = validate_contract("PublicationInputs", publication_inputs)
        _check(_same(inputs["request"], original) and _same(inputs["selector"], selector),
               "publication_dependency_conflict")
        _check(isinstance(snapshot, SourceSnapshot) and snapshot.service == TRANSPORT_SERVICE
               and type(snapshot.request) is dict
               and snapshot.request.get("kind") == "download"
               and _same(snapshot.request.get("requested_byte_range"), inputs["current_operation"]["arguments"]["byte_range"]),
               "publication_dependency_conflict")
        current = inputs["current_snapshot"]
        content = current["content"]
        selected = current["selected_operands"]
        operation = inputs["current_operation"]
        _check(set(selected) == {"operation", "request_sha256", "arguments_sha256", "native_operands"}
               and selected["operation"] == operation["name"]
               and selected["request_sha256"] == _digest(original)
               and selected["arguments_sha256"] == _digest(operation["arguments"]),
               "publication_dependency_conflict")
        native = selected["native_operands"]
        _check(type(native) is dict and set(native) == {"request", "arguments", "selector", "call", "local_failure"}
               and _same(native["request"], original) and _same(native["selector"], selector)
               and _same(native["arguments"], operation["arguments"])
               and native["local_failure"] is None, "publication_dependency_conflict")
        call = native["call"]
        _check(type(call) is dict and set(call) == {"url", "byte_range"}
               and _same(call["byte_range"], operation["arguments"]["byte_range"])
               and _same(snapshot.request, {"kind": "download", "url": call["url"],
                    "requested_byte_range": call["byte_range"]})
               and snapshot.url == call["url"], "publication_dependency_conflict")
        _check(content["sha256"] == snapshot.sha256 and content["byte_count"] == len(snapshot.content)
               and current["retrieved_at"] == snapshot.retrieved_at
               and current["media_type"] == snapshot.media_type
               and _same(current["transport"], snapshot.transport), "publication_dependency_conflict")
        _check(self.publication_callback is not None, "appservice_publication_unbound")
        return self.publication_callback(snapshot, publication_inputs=inputs, operation_key=operation_key)


__all__ = ["BVBRCAppServiceService", "SERVICE", "EXECUTION_CONTRACT"]
