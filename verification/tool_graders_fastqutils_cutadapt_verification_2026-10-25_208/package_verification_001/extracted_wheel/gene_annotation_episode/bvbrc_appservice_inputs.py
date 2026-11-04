"""Authenticate operands for one already selected AppService operation.

This host component does no acquisition, preparation retry or operation choice.
Receipt dependencies are inspected only along their declared source edges, in
the producing episode's authenticated context. Possessing a receipt does not
deliver its dependencies as additional facts to the receiver.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from urllib.parse import urlsplit

from .bvbrc_analysis_protocol import parse_workspace_records
from .bvbrc_application_definitions import get_application_spec
from .bvbrc_appservice_contracts import validate_contract, validate_request
from .bvbrc_appservice_readers import decode_job_result, decode_task_info, decode_upload, _object_binding
from .bvbrc_appservice_tool_info import PREFIX, LAUNCH_OPERATIONS, RESULT_OPERATIONS
from .communication import plain
from .execution_contracts import canonical, digest
from .practical_execution_state import _immutable, _read


_LOCAL_PROVIDER = "episode.bvbrc_appservice_definition"
_LOCAL_VERSION = "bvbrc_appservice_definition_extraction_v1"
_UUID = re.compile(r"[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}\Z")


class AppServiceInputError(ValueError):
    """A specific local failure, with the existing closed Failure projection."""

    def __init__(self, code, *, refs=(), pointers=()):
        self.code = code
        self.failure = validate_contract("Failure", {"code": code, "phase": "association",
            "affected_refs": list(dict.fromkeys(refs)), "affected_pointers": list(dict.fromkeys(pointers)),
            "effect_outcome": "not_sent", "valid_record_refs": [], "requirements": []})
        self.diagnostics = [{"code": code, "path": pointer} for pointer in (list(pointers) or [""])]
        super().__init__(code)


def _require(condition, code, *, refs=(), pointers=()):
    if not condition:
        raise AppServiceInputError(code, refs=refs, pointers=pointers)


def _same(left, right):
    return canonical(left) == canonical(right)


def _pointer(parent, token):
    return parent + "/" + str(token).replace("~", "~0").replace("/", "~1")


def _reference_same(left, right):
    if left == right:
        return left is not None
    if type(left) is not str or type(right) is not str:
        return False
    if _UUID.fullmatch(left) and _UUID.fullmatch(right):
        return left.lower() == right.lower()
    if left.startswith("/") and right.startswith("/"):
        return (re.sub(r"/+", "/", left).rstrip("/") or "/") == (
            re.sub(r"/+", "/", right).rstrip("/") or "/")
    return False


def _one(rows, condition, code):
    matches = [row for row in rows if condition(row)]
    _require(len(matches) == 1, code)
    return matches[0]


class AppServiceInputs:
    def __init__(self, execution, *, records, custody, read_acquisition=None):
        _require(read_acquisition is None or callable(read_acquisition), "appservice_acquisition_reader_invalid")
        _require(execution.store is records.store is custody.store
                 and execution.run_id == records.run_id == custody.run_id, "appservice_input_binding_conflict")
        self.execution, self.records, self.custody = execution, records, custody
        self.read_acquisition = read_acquisition

    def bind_inputs(self, context, name, arguments, *, operation_key):
        selection = validate_contract("OperationSelection", {"name": name, "arguments": plain(arguments)})
        self.custody.authenticate(context)
        selected = self.execution._selected(context, name, selection["arguments"], operation_key)
        # The older generic selected-action checker uses Python equality. Keep
        # JSON booleans and numbers distinct at this new opt-in boundary.
        actual = json.loads(selected["action"])
        _require(_same(actual.get("arguments"), selection["arguments"]), "api_selected_action_conflict")
        allowed = LAUNCH_OPERATIONS if context.role == "launch_api" else RESULT_OPERATIONS if context.role == "results" else ()
        _require(name in allowed, "bvbrc_appservice_operation_not_available")
        state = _Inputs(self, context, selection, operation_key)
        return state.resolve()


class _Inputs:
    """Per-selection state; never an episode, live context cache or broad ledger."""

    def __init__(self, binder, context, selection, key):
        self.binder, self.api = binder, binder.execution
        self.records, self.custody, self.store = binder.records, binder.custody, binder.execution.store
        self.context, self.name, self.args, self.key = context, selection["name"], selection["arguments"], key
        self.before = int(key.rsplit(":", 1)[1])
        self.owner = self.custody.original_job_owner(context)
        self.support, self.proofs, self.inputs, self.objects = [], [], [], []
        self.definition = self.capability = self.handoff_ref = self.task = None
        self.require_output = self.name in {PREFIX + name for name in ("list_outputs", "download_capability", "download")}
        self.selector = None
        assignment = plain(context.assignment)
        if context.role == "results":
            self.selector = validate_contract("ResultSelector", assignment["selector"])
            self.handoff_ref = assignment["handoff_ref"]
            handoff, producer, _ = self.receipt(self.handoff_ref, "TaskHandoff", check_job=False)
            assignment = plain(producer.assignment)
            _require(producer.role == "launch_api", "original_task_mismatch")
        self.request = validate_request(assignment["request"])
        self.resource = assignment["resource_id"]
        _require(assignment.get("version") == "api_service_assignment_v1"
                 and assignment.get("service") == "bvbrc_appservice", "original_task_mismatch")
        if self.handoff_ref is not None:
            self.task = self.handoff(handoff, producer)

    def possess(self, reference, *, receiver=None):
        receiver = self.context if receiver is None else receiver
        self.custody.possession(receiver, reference,
            before=self.before if receiver.episode_id == self.context.episode_id else None)
        if receiver.episode_id == self.context.episode_id:
            self.proofs.append(reference)

    def source(self, binding, *, receiver=None, evidence=False):
        receiver = self.context if receiver is None else receiver
        function = self.custody.evidence if evidence else self.custody.content
        value = function(receiver, binding,
            before=self.before if receiver.episode_id == self.context.episode_id else None)
        if receiver.episode_id == self.context.episode_id:
            self.proofs.append(binding["content"]["source_ref"] if evidence else binding["source_ref"])
        return value

    def prepared(self, origin):
        producer = self.custody.context(origin["episode_id"])
        directory = self.api._manifest(producer, create=False) / "actions" / digest(origin["operation_key"])
        intent = _read(directory / "intent.json")
        prepared = validate_contract("PreparedOperation", intent["prepared"])
        _require(origin["run_id"] == self.context.run_id
                 and origin["assignment_sha256"] == digest(producer.assignment)
                 and origin["scope_sha256"] == digest(producer.scope)
                 and origin["name"] == prepared["operation"]
                 and origin["arguments_sha256"] == prepared["arguments_sha256"]
                 and intent["operation_key"] == origin["operation_key"], "appservice_receipt_origin_conflict")
        selected = self.api._selected(producer, prepared["operation"],
            prepared["native_operands"]["arguments"], origin["operation_key"])
        _require(selected["result"] is not None, "appservice_receipt_completed_action_required")
        return producer, prepared

    def receipt(self, reference, contract=None, *, receiver=None, check_job=True):
        self.possess(reference, receiver=receiver)
        record = self.records.read(reference)
        _require(record["source_ref"] == reference and record["contract"] != "AcquisitionReceipt"
                 and (contract is None or record["contract"] == contract),
                 "appservice_receipt_contract_conflict", refs=[reference])
        value = validate_contract(record["contract"], record["value"])
        common = value if record["contract"] == "CommonReceipt" else value["receipt"]
        _require(common["receipt_ref"] == reference, "appservice_receipt_identity_conflict", refs=[reference])
        producer, prepared = self.prepared(common["origin"])
        operations = {"CatalogReceipt": ("enumerate_apps",), "PreparationReceipt": ("prepare",),
            "WorkspaceReceipt": ("workspace_metadata", "workspace_create", "list_outputs"),
            "UploadReceipt": ("upload",), "TaskInfoReceipt": ("task_info",),
            "TaskObservation": ("status",), "CapabilityReceipt": ("download_capability",),
            "TaskHandoff": ("submit",)}
        if record["contract"] in operations:
            _require(prepared["operation"] in tuple(PREFIX + name for name in operations[record["contract"]]),
                     "appservice_receipt_contract_conflict", refs=[reference])
        if record["contract"] == "WorkspaceReceipt":
            args = prepared["native_operands"]["arguments"]
            expected = ([{"kind": "original_target", "target_id": row["target_id"]} for row in args["objects"]]
                        if prepared["operation"] == PREFIX + "workspace_create" else args["objects"])
            _require(_same(value["requested_objects"], expected)
                     and value["method"] == prepared["native_operands"]["call"]["rpc_request"]["method"],
                     "workspace_target_conflict", refs=[reference])
        if check_job:
            self.check_job(producer, prepared)
        if receiver is None or receiver.episode_id == self.context.episode_id:
            self.support.append(reference)
        return value, producer, prepared

    def check_job(self, producer, prepared):
        bound = prepared["bound_inputs"]
        _require(_same(self.custody.original_job_owner(producer), self.owner)
                 and _same(bound["original_job_owner"], self.owner)
                 and bound["resource_id"] == self.resource
                 and prepared["request_sha256"] == digest(self.request)
                 and _same(prepared["native_operands"]["request"], self.request), "original_task_mismatch")
        if self.task is not None and prepared["bound_inputs"]["resolved"].get("original_task") is not None:
            _require(_same(prepared["bound_inputs"]["resolved"]["original_task"], self.task), "original_task_mismatch")

    def handoff(self, value, producer):
        task = value["original_task"]
        common = value["receipt"]
        _require(common["origin"]["name"] == PREFIX + "submit" and common["status"] == "ok"
                 and value["usable_handoff"] and _same(value["original_job_owner"], self.owner)
                 and _same(self.custody.original_job_owner(producer), self.owner)
                 and task["resource_id"] == self.resource
                 and task["required_application_id"] == self.request["required_application_id"]
                 and _same(task["submitted_parameters"], self.request["parameters"])
                 and _same(task["submitted_start_parameters"], self.request["start_parameters"])
                 and task["submission_receipt_ref"] == common["receipt_ref"]
                 and task["submission_operation_key"] == common["origin"]["operation_key"]
                 and common["snapshot"] is not None
                 and task["submission_source_ref"] == common["snapshot"]["source_ref"], "original_task_mismatch")
        _, prepared = self.prepared(common["origin"])
        self.check_job(producer, prepared)
        preparation = prepared["bound_inputs"]["resolved"].get("preparation")
        _require(prepared["operation"] == PREFIX + "submit" and preparation is not None
                 and task["native_application_id"] == preparation["native_application_id"]
                 and _same(value["definition_evidence"], preparation["definition_evidence"])
                 and _same(value["input_evidence_refs"], prepared["native_operands"]["arguments"]["input_evidence_refs"]),
                 "original_task_mismatch")
        native = self.source({"content": common["snapshot"]["content"], "pointer": "/result/0"},
                             receiver=producer, evidence=True)
        _require(_same(native, value["native_submission_record"]), "original_task_mismatch")
        _require(value["effect_receipt_ref"] in common["effect_receipt_refs"], "original_task_mismatch")
        effect = self.api.selected_effects.read(value["effect_receipt_ref"], original_job_owner=self.owner)
        _require(effect["state"] == "confirmed" and effect["descriptor"]["kind"] == "appservice_submit"
                 and effect["descriptor"]["resource_id"] == self.resource
                 and effect["operation_key"] == task["submission_operation_key"]
                 and effect["native_effect_identifiers"].get("task_id") == task["task_id"]
                 and effect["confirmation_source_ref"] == task["submission_source_ref"], "original_task_mismatch")
        return deepcopy(task)

    def input(self, binding_id):
        binding = _one(self.request["input_bindings"], lambda row: row["binding_id"] == binding_id,
                       "input_not_possessed")
        if binding["content"] is not None:
            self.source(binding["content"])
        if binding["link_evidence"] is not None:
            _require(_same(self.source(binding["link_evidence"], evidence=True), binding["inline_value"]),
                     "input_bytes_mismatch")
        for member in binding["members"]:
            if member["evidence"] is not None:
                self.source(member["evidence"], evidence=True)
        if binding not in self.inputs:
            self.inputs.append(deepcopy(binding))
        return deepcopy(binding)

    def identity(self, obj, refs):
        resolver = getattr(getattr(self.api, "selected_effects", None), "resolve_object_identity", None)
        _require(callable(resolver), "appservice_object_identity_unbound")
        return resolver(self.owner, self.resource, path=obj["path"], uuid=obj["uuid"], evidence_refs=refs)

    def association(self, obj, *, kind="unverified_original_path", evidence_ref=None, pointer=None):
        _require(self.task is not None, "original_task_mismatch")
        return validate_contract("TaskAssociation", {"kind": kind, "evidence_ref": evidence_ref,
            "pointer": pointer, "task_id": self.task["task_id"], "output_path": obj["path"],
            "output_uuid": obj["uuid"], "byte_version_status": "unknown", "version_evidence": []})

    def metadata_task(self, row):
        if self.task is None:
            return
        native = row["native_row"]
        metadata = native[0] if type(native) is list and len(native) in (1, 2) and type(native[0]) is list else native
        for field in (7, 8):
            values = metadata[field]
            if type(values) is dict and "task_data" in values:
                task_data = values["task_data"]
                _require(type(task_data) is dict, "task_manifest_mismatch")
                for key, expected in (("task_id", self.task["task_id"]), ("app_id", self.task["native_application_id"])):
                    _require(key not in task_data or task_data[key] is None or task_data[key] == expected,
                             "task_manifest_mismatch")

    def object(self, selection, *, receiver=None):
        selection = validate_contract("ObjectSelection", selection)
        kind = selection["kind"]
        metadata = association = None
        if kind in ("original_input", "original_target"):
            if kind == "original_input":
                # This operand selects the original Workspace path, not an
                # upload of the input's content. It grants no byte custody.
                binding = _one(self.request["input_bindings"], lambda row: row["binding_id"] == selection["input_binding_id"],
                               "input_not_possessed")
                _require(binding["workspace_path"] is not None, "workspace_target_conflict")
                path, object_type = binding["workspace_path"], None
                _require(not self.require_output, "output_association_missing")
            else:
                target = _one(self.request["workspace_targets"], lambda row: row["target_id"] == selection["target_id"],
                              "workspace_target_conflict")
                path, object_type = target["path"], target["type"]
                _require(not self.require_output or target["purpose"] == "output_parent", "output_association_missing")
            obj = {"path": path, "uuid": None, "type": object_type, "metadata_receipt_ref": None}
            reference, refs = path, [self.owner["parent_commission_operation_key"]]
            if self.task is not None and kind == "original_target" and target["purpose"] == "output_parent":
                association = self.association(obj)
        elif kind == "receipt_row":
            value, producer, prepared = self.receipt(selection["receipt_ref"], "WorkspaceReceipt", receiver=receiver)
            metadata = _one(value["rows"], lambda row: row["pointer"] == selection["row_pointer"], "workspace_row_ambiguous")
            _require(metadata["valid"], "workspace_member_failed", refs=[selection["receipt_ref"]], pointers=[selection["row_pointer"]])
            snapshot = value["receipt"]["snapshot"]
            _require(snapshot is not None, "workspace_member_failed")
            native_row = self.source({"content": snapshot["content"], "pointer": metadata["pointer"]}, receiver=producer, evidence=True)
            _require(_same(native_row, metadata["native_row"]), "workspace_target_conflict")
            native = self.source({"content": snapshot["content"], "pointer": "/result/0"}, receiver=producer, evidence=True)
            _require(_same(native, value["native_value"]), "workspace_target_conflict")
            call = prepared["native_operands"]["call"]["rpc_request"]
            _require(call["method"] == value["method"], "workspace_target_conflict")
            method, options = value["method"].split(".")[1], call["params"][0]
            references = [row[0] for row in options["objects"]] if method == "create" else options["paths" if method == "ls" else "objects"]
            parsed = parse_workspace_records(native, operation=method, requested_paths=references)
            native_record = _one(parsed["records"], lambda row: (_pointer(_pointer("/result/0", row["listing_path"]), row["row_index"])
                if method == "ls" else _pointer("/result/0", row["row_index"])) == metadata["pointer"], "workspace_row_ambiguous")
            _require(native_record["status"] == "ok", "workspace_member_failed")
            obj = {key: metadata[key] for key in ("path", "uuid", "type")}
            obj["metadata_receipt_ref"] = selection["receipt_ref"]
            _object_binding({"object": obj, "metadata": metadata})
            reference, refs = obj["path"] or obj["uuid"], [selection["receipt_ref"], snapshot["source_ref"]]
            association = self.row_association(value, prepared, native_record, obj, producer)
            if association is not None:
                self.metadata_task(metadata)
        elif kind == "task_info_object":
            value, producer, prepared = self.receipt(selection["receipt_ref"], "TaskInfoReceipt", receiver=receiver)
            if self.task is None:
                original, launch, _ = self.receipt(value["original_handoff_ref"], "TaskHandoff", receiver=producer)
                self.handoff_ref = value["original_handoff_ref"]
                self.task = self.handoff(original, launch)
            _require(self.task is not None and value["original_handoff_ref"] == self.handoff_ref
                     and value["task_id"] == self.task["task_id"] and value["receipt"]["status"] == "ok"
                     and value["body_complete"] and value["file"] in ("job_result_id", "job_result_folder")
                     and value["reported_object_uuid"] is not None
                     and prepared["operation"] == PREFIX + "task_info"
                     and prepared["native_operands"]["call"] == {"task_id": self.task["task_id"], "file": value["file"]},
                     "task_info_object_invalid")
            snapshot = value["receipt"]["snapshot"]
            _require(snapshot is not None, "task_info_object_invalid")
            raw = self.source(snapshot["content"], receiver=producer)
            parsed = decode_task_info(raw, task_id=value["task_id"], file=value["file"])
            _require(parsed["status"] == "ok" and parsed["value"]["reported_object_uuid"] == value["reported_object_uuid"],
                     "task_info_object_invalid")
            reference, refs = value["reported_object_uuid"], [selection["receipt_ref"], snapshot["source_ref"]]
            obj = {"path": None, "uuid": reference, "type": None, "metadata_receipt_ref": None}
            # This pointer addresses the named typed receipt value. The HTTP
            # source contains plain UUID text, not an invented JSON document.
            association = self.association(obj, kind="task_info_object", evidence_ref=selection["receipt_ref"],
                                           pointer="/reported_object_uuid")
        else:
            obj, association, refs = self.manifest_member(selection, receiver=receiver)
            reference = obj["path"]
        row = validate_contract("ResolvedObject", {"selection": selection, "native_reference": reference,
            "object": obj, "metadata": metadata, "task_association": association,
            "identity": self.identity(obj, refs)})
        self.objects.append(deepcopy(obj))
        return row

    def row_association(self, receipt, prepared, native, obj, producer):
        if self.task is None:
            return None
        method = receipt["method"]
        resolved = prepared["bound_inputs"]["resolved"]
        if method == "Workspace.create":
            args = prepared["native_operands"]["arguments"]
            selected = [args["objects"][i] for i in native["request_indices"]]
            target = _one(self.request["workspace_targets"], lambda row: any(
                item["target_id"] == row["target_id"] for item in selected), "output_association_missing")
            if target["purpose"] != "output_parent":
                _require(not self.require_output, "output_association_missing")
                return None
            return self.association(obj)
        if method == "Workspace.get":
            index = native["request_index"]
            _require(index is not None and index < len(resolved["objects"]), "output_association_missing")
            prior = resolved["objects"][index]
            for key in ("path", "uuid"):
                _require(prior["object"][key] is None or _reference_same(prior["object"][key], obj[key]), "workspace_target_conflict")
            association = prior["task_association"]
            if association is None:
                # A launch metadata lookup of the exact original output target
                # is still only an unverified output path association.
                selection = prior["selection"]
                if selection["kind"] != "original_target":
                    _require(not self.require_output, "output_association_missing")
                    return None
                target = _one(self.request["workspace_targets"], lambda row: row["target_id"] == selection["target_id"],
                              "output_association_missing")
                if target["purpose"] != "output_parent":
                    _require(not self.require_output, "output_association_missing")
                    return None
                return self.association(obj)
            _require(association["task_id"] == self.task["task_id"], "original_task_mismatch")
            return {**deepcopy(association), "output_path": obj["path"], "output_uuid": obj["uuid"]}
        parents = [row for row in resolved["objects"] if any(_reference_same(native["listing_path"], value)
            for value in (row["native_reference"], row["object"]["path"], row["object"]["uuid"]))]
        parent = _one(parents, lambda _: True, "output_association_missing")
        association = parent["task_association"]
        _require(association is not None and association["task_id"] == self.task["task_id"], "original_task_mismatch")
        kind = "unverified_original_path"
        if association["kind"] == "task_info_object":
            info, _, _ = self.receipt(association["evidence_ref"], "TaskInfoReceipt", receiver=producer)
            _require(info["file"] == "job_result_folder" and info["task_id"] == self.task["task_id"]
                     and info["original_handoff_ref"] == self.handoff_ref, "output_association_missing")
            kind = "task_info_folder_member"
        return self.association(obj, kind=kind, evidence_ref=receipt["receipt"]["receipt_ref"], pointer=native_pointer(receipt, native))

    def manifest_member(self, selection, *, receiver=None):
        reference = selection["manifest_receipt_ref"]
        self.possess(reference, receiver=receiver)
        _require(self.binder.read_acquisition is not None, "appservice_acquisition_reader_unbound", refs=[reference])
        acquisition = validate_contract("AcquisitionReceipt", self.binder.read_acquisition(reference))
        producer, prepared = self.prepared(acquisition["origin"])
        self.check_job(producer, prepared)
        _require(self.task is not None and acquisition["original_handoff_ref"] == self.handoff_ref
                 and acquisition["origin"]["name"] == PREFIX + "download", "original_task_mismatch")
        artifact, snapshot = acquisition["artifact"], acquisition["snapshot"]
        selected = prepared["native_operands"]["arguments"]
        _require(_same(snapshot["selected_operands"], {key: prepared[key] for key in
                    ("operation", "request_sha256", "arguments_sha256", "native_operands")})
                 and acquisition["selector_sha256"] == digest(producer.assignment["selector"])
                 and _same(acquisition["capability_selection"], selected["capability"])
                 and _same(acquisition["object_selection"], selected["object"])
                 and _same(acquisition["requirement_ids"], selected["requirement_ids"])
                 and artifact["role"] == selected["role"]
                 and _same(artifact["declared_format"], selected["declared_format"])
                 and _same(artifact["transfer"]["requested_range"], selected["byte_range"]), "task_manifest_mismatch")
        _require(artifact["transfer"]["receipt_ref"] == reference
                 and artifact["task_association"]["task_id"] == self.task["task_id"]
                 and artifact["transfer"]["object_complete"] == "yes"
                 and artifact["transfer"]["body_complete"] and acquisition["status"] in ("ok", "partial")
                 and artifact["source_ref"] == snapshot["source_ref"]
                 and artifact["raw_artifact_ref"] == snapshot["content"]["artifact_ref"]
                 and artifact["sha256"] == snapshot["content"]["sha256"]
                 and artifact["byte_count"] == snapshot["content"]["byte_count"], "task_manifest_mismatch")
        original_object = prepared["bound_inputs"]["resolved"]["object"]
        _require(_same(acquisition["object_selection"], original_object["selection"])
                 and _same(artifact["workspace_object"], original_object["object"]), "task_manifest_mismatch")
        if original_object["metadata"] is not None:
            self.metadata_task(original_object["metadata"])
        raw = self.source(snapshot["content"], receiver=producer)
        decoded = decode_job_result(raw, original_task=self.task,
            object_binding=artifact["workspace_object"], evidence_ref=artifact["source_ref"])
        member = _one(decoded["records"], lambda row: row["output_index"] == selection["output_index"], "task_manifest_mismatch")
        _require(member["valid"] and member["association"] is not None, "task_manifest_mismatch")
        path, uuid = member["native_record"]
        self.support.append(reference)
        return ({"path": path, "uuid": uuid, "type": None, "metadata_receipt_ref": None},
                member["association"], [reference, artifact["source_ref"]])

    def definition_input(self):
        selection = self.args["definition"]
        original_evidence = None
        if selection["kind"] == "packaged":
            _require(selection["required_application_id"] == self.request["required_application_id"], "definition_extraction_mismatch")
            envelope = get_application_spec(selection["required_application_id"])
            raw = envelope["source"]["content"].encode("utf-8")
            original_source = {"kind": "packaged", "source": deepcopy(envelope["source"])}
            original_source["source"].pop("content")
        else:
            if selection["kind"] == "supplied":
                binding = _one(self.request["definition_inputs"], lambda row: row["binding_id"] == selection["definition_binding_id"],
                               "definition_not_possessed")
                original_evidence = binding["evidence"]
                definition = self.source(original_evidence, evidence=True)
            else:
                catalog, producer, prepared = self.receipt(selection["catalog_receipt_ref"], "CatalogReceipt")
                _require(prepared["operation"] == PREFIX + "enumerate_apps", "definition_extraction_mismatch")
                row = _one(catalog["records"], lambda row: row["record_index"] == selection["record_index"], "definition_extraction_mismatch")
                _require(row["valid"] and row["pointer"] == f'/result/0/{selection["record_index"]}'
                         and catalog["receipt"]["snapshot"] is not None, "definition_extraction_mismatch")
                original_evidence = {"content": catalog["receipt"]["snapshot"]["content"], "pointer": row["pointer"]}
                definition = self.source(original_evidence, receiver=producer, evidence=True)
                _require(_same(definition, row["native_record"]), "definition_extraction_mismatch")
                if row["definition_content"] is not None:
                    retained = self.source({"content": row["definition_content"], "pointer": ""}, receiver=producer, evidence=True)
                    _require(_same(definition, retained), "definition_extraction_mismatch")
            _require(type(definition) is dict, "definition_extraction_mismatch")
            raw = canonical(definition).encode("utf-8")
            source_ref = original_evidence["content"]["source_ref"]
            source = self.store.get(source_ref)
            envelope = {"required_id": self.request["required_application_id"], "native_id": definition.get("id"),
                "definition": definition, "source": {"kind": "retained_service_definition",
                    "url": source.get("uri") or "urn:source:" + source_ref,
                    "content": raw.decode("utf-8"), "sha256": hashlib.sha256(raw).hexdigest()},
                "parse_corrections": [], "duplicate_object_keys": []}
            original_source = {"kind": selection["kind"], "evidence": original_evidence}
        provenance = {"version": _LOCAL_VERSION, "run_id": self.context.run_id, "episode_id": self.context.episode_id,
            "operation_key": self.key, "assignment_sha256": digest(self.context.assignment),
            "selection": deepcopy(selection), "original_source": original_source, "envelope": envelope}
        provenance_ref = self.store.artifact(canonical(provenance), "application/json")

        def retain(content, part, parents):
            artifact_ref = self.store.artifact(content, "application/json")
            source = self.store.put("source", {"provider": _LOCAL_PROVIDER,
                "accession": part + "_" + digest(provenance), "uri": envelope["source"]["url"],
                "artifact_ref": artifact_ref, "text_ref": None, "request_ref": provenance_ref,
                "version": _LOCAL_VERSION, "retrieved_at": None, "parent_source_refs": parents}, origin="tool")
            self.proofs.append(source["id"])
            return {"source_ref": source["id"], "artifact_field": "artifact_ref", "artifact_ref": artifact_ref,
                "sha256": hashlib.sha256(content).hexdigest(), "byte_count": len(content)}

        parents = [] if original_evidence is None else [original_evidence["content"]["source_ref"]]
        retained_raw = retain(raw, "source", parents)
        extracted = retain(canonical(envelope["definition"]).encode("utf-8"), "definition", [retained_raw["source_ref"]])
        self.definition = {"content": extracted, "pointer": ""}
        record = {"definition": self.definition, "definition_envelope": envelope,
            "original_evidence": original_evidence, "retained_source": retained_raw,
            "source_refs": [retained_raw["source_ref"], extracted["source_ref"]]}
        directory = self.api._manifest(self.context) / "actions" / digest(self.key)
        directory.mkdir(exist_ok=True)
        _immutable(directory / "definition_inputs.json", record)
        return envelope

    def predecessor(self, objects):
        reference = self.args["predecessor_receipt_ref"]
        if reference is None:
            return []
        # A bare journal effect ID is not a Store source or a delivered receipt.
        _require(not reference.startswith("api_effect_"), "capability_not_possessed", refs=[reference])
        value, _, prepared = self.receipt(reference)
        common = value if "receipt" not in value else value["receipt"]
        _require(prepared["operation"] == PREFIX + "download_capability"
                 and prepared["native_operands"]["arguments"]["generation"] == self.args["generation"] - 1,
                 "capability_predecessor_conflict")
        previous = prepared["bound_inputs"]["resolved"]["objects"]
        refs = []
        for obj in objects:
            old = _one(previous, lambda item: self.identity(item["object"], [reference]) == obj["identity"],
                       "capability_predecessor_conflict")
            effects = [self.api.selected_effects.read(ref, original_job_owner=self.owner) for ref in common["effect_receipt_refs"]]
            effect = _one(effects, lambda row: row["descriptor"]["kind"] == "download_capability"
                and row["descriptor"]["resource_id"] == self.resource
                and row["descriptor"]["slot"]["object_identity"] == old["identity"]
                and row["descriptor"]["slot"]["generation"] == self.args["generation"] - 1
                and row["operation_key"] == common["origin"]["operation_key"]
                and row["state"] in ("confirmed", "issued_unknown"), "capability_predecessor_conflict")
            refs.append(effect["effect_ref"])
        return list(dict.fromkeys(refs))

    def download_capability(self, obj):
        selected = self.args["capability"]
        if selected["kind"] == "acquired":
            value, producer, prepared = self.receipt(selected["receipt_ref"], "CapabilityReceipt")
            _require(prepared["operation"] == PREFIX + "download_capability"
                     and value["generation"] == prepared["native_operands"]["arguments"]["generation"]
                     and value["predecessor_receipt_ref"] == prepared["native_operands"]["arguments"]["predecessor_receipt_ref"],
                     "capability_not_possessed")
            entry = _one(value["entries"], lambda row: row["input_index"] == selected["input_index"], "capability_not_possessed")
            original = prepared["bound_inputs"]["resolved"]["objects"]
            _require(selected["input_index"] < len(original), "capability_not_possessed")
            original = original[selected["input_index"]]
            snapshot = value["receipt"]["snapshot"]
            _require(snapshot is not None and entry["issued_observed_at"] == snapshot["retrieved_at"]
                     and _same(entry["object_selection"], original["selection"])
                     and _same(entry["object"], original["object"])
                     and _same(entry["task_association"], original["task_association"]), "capability_not_possessed")
            # Missing native batch members are retained as unavailable entries;
            # a malformed present member also cannot supply a replacement URL.
            native = self.source({"content": snapshot["content"], "pointer": "/result/0"}, receiver=producer, evidence=True)
            _require(type(native) is list, "capability_not_possessed")
            native_url = native[selected["input_index"]] if selected["input_index"] < len(native) else None
            if entry["url"] is not None:
                _require(native_url == entry["url"], "capability_not_possessed")
            if entry["expiry_evidence"] is not None:
                _require(self.source(entry["expiry_evidence"], receiver=producer, evidence=True) == entry["expires_at"],
                         "capability_not_possessed")
            _require(_same(entry["object_selection"], obj["selection"])
                     and _same(entry["object"], obj["object"])
                     and _same(entry["task_association"], obj["task_association"]), "output_association_missing")
        else:
            supplied = _one(self.selector["supplied_capabilities"], lambda row: row["binding_id"] == selected["binding_id"],
                            "capability_not_possessed")
            _require(supplied["original_handoff_ref"] == self.handoff_ref
                     and _same(supplied["object_selection"], obj["selection"])
                     and _same(supplied["task_association"], obj["task_association"]), "original_task_mismatch")
            url = self.source(supplied["url_evidence"], evidence=True)
            _require(type(url) is str and bool(url), "capability_not_possessed")
            source = self.store.get(supplied["url_evidence"]["content"]["source_ref"])
            _require(type(source.get("retrieved_at")) is str and bool(source["retrieved_at"]), "capability_observation_time_unavailable")
            entry = {"input_index": 0, "object_selection": obj["selection"], "object": obj["object"],
                "task_association": obj["task_association"], "url": url, "issued_observed_at": source["retrieved_at"],
                "expires_at": None, "expiry_evidence": None}
        self.capability = selected
        return validate_contract("ResolvedCapability", {"selection": selected, "entry": entry})

    def submit_inputs(self):
        evidence = [self.receipt(ref) for ref in self.args["input_evidence_refs"]]
        originals = {row["binding_id"]: row for row in self.request["input_bindings"]}
        targets = {row["target_id"]: row for row in self.request["workspace_targets"]}
        for value, producer, prepared in evidence:
            operation = prepared["operation"]
            if operation == PREFIX + "upload":
                upload = prepared["bound_inputs"]["resolved"]["upload"]
                binding = upload["input"]
                _require(binding["binding_id"] in originals and _same(binding, originals[binding["binding_id"]])
                         and value.get("input_binding_id") == binding["binding_id"]
                         and _same(value.get("input_content"), binding["content"])
                         and _same(value.get("created_object"), upload["object"]["object"])
                         and value.get("shock_node_id") == upload["shock_node_id"]
                         and value.get("create_receipt_ref") == upload["object"]["selection"]["receipt_ref"]
                         and value.get("filename") == prepared["native_operands"]["arguments"]["filename"],
                         "input_evidence_conflict")
                snapshot = value["receipt"]["snapshot"]
                _require(snapshot is not None, "input_evidence_conflict")
                native = self.source({"content": snapshot["content"], "pointer": ""}, receiver=producer, evidence=True)
                parsed = decode_upload(native, expected_node_id=upload["shock_node_id"],
                    expected_bytes=binding["content"]["byte_count"], supplied_sha256=binding["content"]["sha256"])
                _require(all(_same(value[key], parsed["value"][key]) for key in
                    ("native_reply", "observed_node_id", "observed_file_size", "observed_checksums")), "input_evidence_conflict")
                _require(value["confirmation"] not in ("accepted_bytes_match", "accepted_identity_only")
                         or value["confirmation"] == parsed["value"]["confirmation"], "input_evidence_conflict")
            elif operation in (PREFIX + "workspace_create", PREFIX + "workspace_metadata"):
                # Only the receipt's exact originally selected input operands
                # can make it input evidence. Output-folder creation is not it.
                selections = value.get("requested_objects", [])
                direct = any(row["kind"] == "original_input" and row["input_binding_id"] in originals
                    or row["kind"] == "original_target" and row["target_id"] in targets
                    and targets[row["target_id"]]["input_binding_id"] in originals for row in selections)
                input_paths = [row["workspace_path"] for row in originals.values() if row["workspace_path"] is not None]
                input_paths.extend(row["path"] for row in targets.values() if row["input_binding_id"] in originals)
                selected_objects = prepared["bound_inputs"]["resolved"].get("objects", [])
                _require(direct or any(_reference_same(row["object"]["path"], path)
                    for row in selected_objects for path in input_paths), "input_evidence_conflict")
            else:
                raise AppServiceInputError("input_evidence_conflict")
        for original in self.request["input_bindings"]:
            binding = self.input(original["binding_id"])
            if binding["kind"] == "retained_bytes":
                matches = [value for value, _, _ in evidence if value.get("input_binding_id") == binding["binding_id"]
                    and "input_content" in value and _same(value["input_content"], binding["content"])
                    and _reference_same(value["created_object"]["path"], binding["workspace_path"])
                    and value["confirmation"] in ("accepted_bytes_match", "accepted_identity_only")
                    and value["receipt"]["status"] == "ok"]
                _require(bool(matches), "input_evidence_missing")

    def resolve(self):
        suffix = self.name.removeprefix(PREFIX)
        resolved = {"operation": self.name}
        if suffix == "prepare":
            for item in self.request["input_bindings"]:
                self.input(item["binding_id"])
            resolved["definition_envelope"] = self.definition_input()
        elif suffix == "workspace_create":
            selected = [row["data_binding_id"] for row in self.args["objects"] if row["data_binding_id"] is not None]
            resolved["data_bindings"] = [self.input(ref) for ref in dict.fromkeys(selected)]
        elif suffix == "upload":
            binding = self.input(self.args["input_binding_id"])
            obj = self.object({"kind": "receipt_row", **self.args["created_object"]})
            receipt, _, prepared = self.receipt(self.args["created_object"]["receipt_ref"], "WorkspaceReceipt")
            _require(receipt["method"] == "Workspace.create" and binding["kind"] == "retained_bytes"
                     and binding["content"] is not None and _reference_same(obj["object"]["path"], binding["workspace_path"]),
                     "workspace_target_conflict")
            targets = {row["target_id"]: row for row in self.request["workspace_targets"]}
            _require(any(targets[row["target_id"]]["input_binding_id"] == binding["binding_id"]
                and _reference_same(targets[row["target_id"]]["path"], obj["object"]["path"])
                and row["data_binding_id"] in (None, binding["binding_id"])
                for row in prepared["native_operands"]["arguments"]["objects"]),
                "workspace_target_conflict")
            url = obj["metadata"]["shock_url"]
            _require(type(url) is str, "upload_node_mismatch")
            parsed = urlsplit(url)
            node = parsed.path.rstrip("/").rsplit("/", 1)[-1]
            _require(_UUID.fullmatch(node) is not None and parsed.path.rstrip("/").endswith("/node/" + node)
                     and not parsed.query and not parsed.fragment, "upload_node_mismatch")
            resolved["upload"] = {"object": obj, "input": binding, "shock_url": url, "shock_node_id": node}
        elif suffix == "submit":
            preparation, producer, prepared = self.receipt(self.args["preparation_receipt_ref"], "PreparationReceipt")
            _require(preparation["receipt"]["origin"]["name"] == PREFIX + "prepare"
                     and preparation["receipt"]["status"] == "ok"
                     and preparation["request_sha256"] == digest(self.request)
                     and prepared["operation"] == PREFIX + "prepare"
                     and _same(preparation["definition_selection"], prepared["native_operands"]["arguments"]["definition"])
                     and _same(preparation["definition_evidence"], prepared["bound_inputs"]["definition"])
                     and _same(preparation["c3_result"], prepared["native_operands"]["call"].get("c3_result"))
                     and _same(preparation["native_parameters"], self.request["parameters"])
                     and _same(preparation["start_parameters"], self.request["start_parameters"]), "application_preparation_invalid")
            actual_definition = self.source(preparation["definition_evidence"], receiver=producer, evidence=True)
            _require(_same(actual_definition, prepared["bound_inputs"]["resolved"]["definition_envelope"]["definition"]),
                     "definition_extraction_mismatch")
            self.submit_inputs()
            resolved["preparation"] = preparation
        elif suffix in ("status", "task_info"):
            reference = self.args["handoff_ref"]
            if self.handoff_ref is not None:
                _require(reference == self.handoff_ref, "original_task_mismatch")
            value, producer, _ = self.receipt(reference, "TaskHandoff")
            self.handoff_ref = reference
            self.task = self.handoff(value, producer)
            resolved["original_task"] = self.task
        elif suffix in ("workspace_metadata", "list_outputs", "download_capability"):
            resolved["objects"] = [self.object(row) for row in self.args["objects"]]
            if suffix != "workspace_metadata":
                _require(self.task is not None, "original_task_mismatch")
            # Metadata can be acquired before submission or for a results
            # episode's exact original task. Preserve that task when present.
            if self.task is not None:
                resolved["original_task"] = self.task
            if suffix == "download_capability":
                resolved["predecessor_effect_refs"] = self.predecessor(resolved["objects"])
        elif suffix == "download":
            obj = self.object(self.args["object"])
            resolved.update(original_task=self.task, object=obj, capability=self.download_capability(obj))
        return validate_contract("BoundInputs", {"version": "bvbrc_appservice_bound_inputs_v1",
            "original_job_owner": self.owner, "request_sha256": digest(self.request),
            "selected_argument_sha256": digest(self.args), "definition": self.definition,
            "inputs": self.inputs, "objects": self.objects, "support_receipt_refs": list(dict.fromkeys(self.support)),
            "original_handoff_ref": self.handoff_ref, "capability": self.capability,
            "custody_proof_refs": list(dict.fromkeys(self.proofs)), "resource_id": self.resource, "resolved": resolved})


def native_pointer(receipt, native):
    return (_pointer(_pointer("/result/0", native["listing_path"]), native["row_index"])
            if receipt["method"] == "Workspace.ls" else _pointer("/result/0", native["row_index"]))


__all__ = ["AppServiceInputs", "AppServiceInputError"]
