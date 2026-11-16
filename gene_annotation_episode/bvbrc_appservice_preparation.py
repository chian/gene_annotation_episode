"""Original selected AppService preparation and catalogue methods."""
from __future__ import annotations

from copy import deepcopy
import re
from urllib.parse import urlsplit

from .domain import ContractError
from .bvbrc_analysis_protocol import prepare_rpc_request
from .bvbrc_analysis_transport import _url
from .bvbrc_application_definitions import prepare_application
from .bvbrc_appservice_contracts import validate_contract, validate_request
from .bvbrc_appservice_tool_info import PREFIX, LAUNCH_OPERATIONS, RESULT_OPERATIONS, operation_catalog
from .bvbrc_appservice_service_values import (
    EXECUTION_CONTRACT, _UUID, _digest, _same, _check, _failure,
    _check_task, _check_object, _check_original_object, _native_reference_matches,
)

class AppServicePreparation:
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
        implementation = selected_adapter(self, selector['adapter'])
        if implementation is not None:
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
            call = {"url": entry["url"], "byte_range": arguments["byte_range"],
                "max_bytes": arguments["max_bytes"]}
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

    def prepare_observation(self, request, handle, *, scope, native_operation, bound_inputs=None):
        _check(native_operation in ("query_tasks", "stdout", "stderr"), "bvbrc_appservice_observation_invalid")
        bindings = validate_contract("BoundInputs", bound_inputs)
        suffix = "status" if native_operation == "query_tasks" else "task_info"
        arguments = {"handoff_ref": bindings["original_handoff_ref"]}
        if suffix == "task_info":
            arguments["file"] = native_operation
        return self.prepare(PREFIX + suffix, request, arguments, scope=scope, previous_events=[],
                            handle=handle, bound_inputs=bindings)

