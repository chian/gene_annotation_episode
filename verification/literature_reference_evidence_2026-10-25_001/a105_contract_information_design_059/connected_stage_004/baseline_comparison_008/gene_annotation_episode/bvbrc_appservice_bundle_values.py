"""Pure construction of retained AppService acquisitions and artifact bundles.

The host supplies authenticated original records and frozen dependencies. These
functions make no requests, read no Store, publish nothing, and assign no credit.
An acquisition describes one selected response, including incomplete/error
bytes. A bundle describes requested artifacts; its status never establishes
completion of a requested scientific projection. Unknown producer versions and
weak task associations remain explicit qualifications, not invented evidence.
"""
from __future__ import annotations

from copy import deepcopy
import re

from .acquisition import SourceSnapshot
from .bvbrc_appservice_contracts import ContractValidationError, _same, validate_contract
from .bvbrc_appservice_readers import qualify_download, validate_bundle
from .execution_contracts import digest


_DOWNLOAD = "api.bvbrc_appservice.download"
_FROZEN_FIELDS = ("operation", "request_sha256", "arguments_sha256", "native_operands")


def _require(condition, code, path=""):
    if not condition:
        raise ContractValidationError(code, path)


def _diagnostic(code, path="", *, phase="association", severity="error", refs=()):
    return {"code": code, "phase": phase, "path": path, "severity": severity,
            "evidence_refs": list(dict.fromkeys(refs))}


def _unique(rows):
    result = []
    for row in rows:
        if row not in result:
            result.append(deepcopy(row))
    return result


def _common(common, diagnostics, status=None):
    value = deepcopy(common)
    value["diagnostics"] = _unique([*common["diagnostics"], *diagnostics])
    if status is not None:
        value["status"] = status
    return {"contract": "CommonReceipt", "value": validate_contract("CommonReceipt", value),
            "diagnostics": deepcopy(value["diagnostics"])}


def _event_diagnostics(event):
    rows = [validate_contract("Diagnostic", row) for row in event["facts"].get("diagnostics", [])]
    failure = event["facts"].get("failure")
    if failure is not None:
        failure = validate_contract("Failure", failure)
        rows.extend(_diagnostic(failure["code"], path, phase=failure["phase"], refs=failure["affected_refs"])
                    for path in failure["affected_pointers"] or [""])
    elif event["failure_code"] is not None:
        rows.append(_diagnostic(event["failure_code"]))
    return rows


def _publication(value):
    value = validate_contract("PublicationInputs", value)
    for evidence in value["selector"]["supplied_metadata"]:
        _evidence(value, evidence)
    args, _ = _selection(value["current_snapshot"], value)
    _require(_same(value["current_operation"], {"name": _DOWNLOAD, "arguments": args}),
             "publication_operation_conflict")
    return value


def _evidence(inputs, evidence):
    _require(any(_same(evidence, item) for item in inputs["supplied_evidence"]),
             "publication_evidence_missing")


def _requirements(inputs, args):
    """Recheck every selected meaning; never choose an arbitrary requirement."""
    requirements = {row["requirement_id"]: row for row in inputs["selector"]["requirements"]}
    for identifier in args["requirement_ids"]:
        _require(identifier in requirements, "publication_dependency_conflict")
        row = requirements[identifier]
        _require(row["role"] == args["role"] and _same(row["declared_format"], args["declared_format"])
                 and (row["exact_object"] is None or _same(row["exact_object"], args["object"])),
                 "publication_requirement_conflict")
        if row["producer_rule_evidence"] is not None:
            _evidence(inputs, row["producer_rule_evidence"])
    declared = args["declared_format"]
    for evidence in declared["transformation_evidence"]:
        _evidence(inputs, evidence)
    producer = declared["producer_source_ref"]
    if producer is not None:
        refs = {*inputs["support_receipt_refs"],
                *(row["content"]["source_ref"] for row in inputs["supplied_evidence"])}
        _require(producer in refs, "publication_producer_source_missing")


def _selection(snapshot, inputs):
    """Validate the exact saved selected operands, independently of custody."""
    frozen = snapshot["selected_operands"]
    _require(set(frozen) == set(_FROZEN_FIELDS) and frozen["operation"] == _DOWNLOAD,
             "publication_operation_conflict")
    native = frozen["native_operands"]
    _require(type(native) is dict and set(native) == {"request", "arguments", "selector", "call", "local_failure"},
             "publication_dependency_conflict")
    args = validate_contract("OperationSelection", {"name": _DOWNLOAD, "arguments": native["arguments"]})["arguments"]
    _require(_same(native["request"], inputs["request"]) and _same(native["selector"], inputs["selector"])
             and frozen["request_sha256"] == digest(inputs["request"])
             and frozen["arguments_sha256"] == digest(args), "publication_dependency_conflict")
    call = native["call"]
    _require(type(call) is dict and set(call) == {"url", "byte_range"}
             and _same(call["byte_range"], args["byte_range"])
             and native["local_failure"] is None, "publication_dependency_conflict")
    _requirements(inputs, args)
    return args, call


def _task(task, request):
    _require(task["required_application_id"] == request["required_application_id"]
             and _same(task["submitted_parameters"], request["parameters"])
             and _same(task["submitted_start_parameters"], request["start_parameters"]),
             "original_task_mismatch")


def _reference_matches(left, right):
    if left == right:
        return True
    if type(left) is not str or type(right) is not str:
        return False
    if left.startswith("/") and right.startswith("/"):
        return re.sub(r"/+", "/", left).rstrip("/") == re.sub(r"/+", "/", right).rstrip("/")
    return False


def _original_object(selection, obj, request):
    if selection["kind"] == "original_target":
        rows = [row for row in request["workspace_targets"] if row["target_id"] == selection["target_id"]]
        _require(len(rows) == 1 and _reference_matches(rows[0]["path"], obj["path"])
                 and obj["type"] in (None, rows[0]["type"]), "workspace_target_conflict")
    elif selection["kind"] == "original_input":
        rows = [row for row in request["input_bindings"] if row["binding_id"] == selection["input_binding_id"]]
        _require(len(rows) == 1 and rows[0]["workspace_path"] is not None
                 and _reference_matches(rows[0]["workspace_path"], obj["path"]), "workspace_target_conflict")


def _qualifications(artifact):
    association, refs = artifact["task_association"], [artifact["source_ref"]]
    rows = []
    if association["kind"] in ("unverified_original_path", "task_info_folder_member"):
        rows.append(_diagnostic("output_association_unproven", severity="qualification", refs=refs))
    if association["byte_version_status"] != "producer_bytes_bound":
        rows.append(_diagnostic("output_version_unproven", severity="qualification", refs=refs))
    return rows


def build_acquisition_value(prepared, event, snapshot, *, common_receipt,
                            publication_inputs, acquisition_receipt_ref):
    """Construct AcquisitionReceipt, or keep CommonReceipt when mapping fails.

    ``acquisition_receipt_ref`` is the host's actual or explicit provisional
    identity; this module never creates an identity. Malformed host CommonReceipt
    is rejected. A mapping/selection conflict returns its common retained source
    with a specific diagnostic. No bytes are truncated, assembled or replaced.
    """
    common = validate_contract("CommonReceipt", common_receipt)
    diagnostics = []
    try:
        prepared = validate_contract("PreparedOperation", prepared)
        event = validate_contract("Event", event)
        diagnostics = _event_diagnostics(event)
        _require(type(acquisition_receipt_ref) is str and bool(acquisition_receipt_ref), "acquisition_receipt_ref_missing")
        _require(prepared["operation"] == _DOWNLOAD and prepared["purpose"] == "acquisition"
                 and not prepared["effects"] and not prepared["mutates_remote"], "publication_operation_conflict")
        _require(common["origin"]["name"] == _DOWNLOAD and common["purpose"] == "acquisition"
                 and common["origin"]["arguments_sha256"] == prepared["arguments_sha256"]
                 and not common["effect_receipt_refs"], "receipt_origin_conflict")
        _require(event["facts"].get("operation") == _DOWNLOAD and not event["handoff_ready"], "appservice_event_operation_conflict")
        if snapshot is None:
            if not diagnostics:
                diagnostics.append(_diagnostic("download_snapshot_missing", phase="transport"))
            return _common(common, diagnostics, "failed" if event["state"] == "failed" else "unknown")
        inputs = _publication(publication_inputs)
        binding = common["snapshot"]
        _require(binding is not None and _same(binding, inputs["current_snapshot"]), "snapshot_binding_conflict")
        _require(_same(binding["selected_operands"], {key: prepared[key] for key in _FROZEN_FIELDS}),
                 "snapshot_selection_conflict")
        args, call = _selection(binding, inputs)
        _require(_same(inputs["current_operation"], {"name": _DOWNLOAD, "arguments": args}), "publication_operation_conflict")
        _require(prepared["native_kind"] == "download", "publication_operation_conflict")
        bound, resolved = prepared["bound_inputs"], prepared["bound_inputs"]["resolved"]
        task = resolved["original_task"]
        _task(task, inputs["request"])
        _require(task["resource_id"] == bound["resource_id"]
                 and bound["original_handoff_ref"] == inputs["original_handoff_ref"], "original_task_mismatch")
        obj, cap = resolved["object"], resolved["capability"]
        _require(_same(obj["selection"], args["object"]), "workspace_target_conflict")
        reference = obj["native_reference"]
        _require(_reference_matches(reference, obj["object"]["path"])
                 or (obj["object"]["uuid"] is not None
                     and reference.lower() == obj["object"]["uuid"].lower()), "workspace_target_conflict")
        _require(_same(cap["selection"], args["capability"]) and _same(bound["capability"], args["capability"]),
                 "capability_not_possessed")
        entry = cap["entry"]
        _require(_same(entry["object_selection"], args["object"]) and _same(entry["object"], obj["object"])
                 and _same(entry["task_association"], obj["task_association"]), "output_association_missing")
        if args["capability"]["kind"] == "acquired":
            _require(entry["input_index"] == args["capability"]["input_index"], "capability_not_possessed")
        _require(obj["task_association"] is not None and obj["task_association"]["task_id"] == task["task_id"],
                 "original_task_mismatch")
        _original_object(args["object"], obj["object"], inputs["request"])
        _require(isinstance(snapshot, SourceSnapshot) and snapshot.service == "bvbrc_analysis"
                 and type(snapshot.content) is bytes, "native_snapshot_missing")
        _require(snapshot.url == call["url"] == entry["url"] and _same(snapshot.request,
                 {"kind": "download", "url": call["url"], "requested_byte_range": call["byte_range"]}),
                 "native_request_conflict")
        _require(binding["content"]["sha256"] == snapshot.sha256
                 and binding["content"]["byte_count"] == len(snapshot.content)
                 and binding["retrieved_at"] == snapshot.retrieved_at
                 and binding["media_type"] == snapshot.media_type
                 and _same(binding["transport"], snapshot.transport), "snapshot_binding_conflict")
        parsed = qualify_download(snapshot, capability=entry,
            object_binding={key: obj[key] for key in ("object", "metadata")})
        diagnostics.extend(parsed["diagnostics"])
        facts = event["facts"]
        _require(facts.get("parse_status") == parsed["status"] and _same(facts.get("projection"), parsed["value"])
                 and facts.get("http_status") == snapshot.transport["status"]
                 and facts.get("body_complete") is snapshot.transport["body_complete"]
                 and event["native_handle"] == {"task_id": task["task_id"]}, "appservice_event_projection_conflict")
        projection, content = parsed["value"], binding["content"]
        artifact = {"role": args["role"], "requirement_ids": deepcopy(args["requirement_ids"]),
            "source_ref": binding["source_ref"],
            "raw_artifact_ref": content["artifact_ref"], "sha256": content["sha256"], "byte_count": content["byte_count"],
            "workspace_object": obj["object"], "task_association": obj["task_association"],
            "transfer": {"receipt_ref": acquisition_receipt_ref, **{key: projection[key] for key in
                ("body_complete", "requested_range", "observed_range", "total_size", "object_complete")}},
            "declared_format": args["declared_format"]}
        diagnostics.extend(_qualifications(artifact))
        diagnostics = _unique([*common["diagnostics"], *diagnostics])
        errors = [row for row in diagnostics if row["severity"] == "error"]
        failure = None if not errors else {"code": errors[0]["code"], "phase": errors[0]["phase"],
            "affected_refs": [binding["source_ref"]], "affected_pointers": list(dict.fromkeys(row["path"] for row in errors)),
            "effect_outcome": None, "valid_record_refs": [binding["source_ref"]], "requirements": []}
        value = {"version": "bvbrc_appservice_acquisition_v1", "origin": common["origin"],
            "original_handoff_ref": inputs["original_handoff_ref"], "selector_sha256": digest(inputs["selector"]),
            "snapshot": binding, "capability_selection": args["capability"], "object_selection": args["object"],
            "artifact": artifact, "requirement_ids": args["requirement_ids"], "publication_inputs_sha256": digest(inputs),
            "publication_ref": None, "valid_record_refs": [binding["source_ref"]],
            "status": parsed["status"], "failure": failure}
        return {"contract": "AcquisitionReceipt", "value": validate_contract("AcquisitionReceipt", value),
                "diagnostics": diagnostics}
    except ContractValidationError as error:
        diagnostics.extend(_diagnostic(row["code"], row["path"]) for row in error.diagnostics)
        return _common(common, diagnostics, "invalid")


def _acquisition(row, inputs, task):
    _require(type(row) is dict and set(row) == {"receipt_ref", "receipt"}
             and type(row["receipt_ref"]) is str and bool(row["receipt_ref"]), "acquisition_dependency_invalid")
    ref, receipt = row["receipt_ref"], validate_contract("AcquisitionReceipt", row["receipt"])
    args, call = _selection(receipt["snapshot"], inputs)
    artifact, binding = receipt["artifact"], receipt["snapshot"]
    _require(receipt["origin"]["name"] == _DOWNLOAD and receipt["origin"]["arguments_sha256"] == digest(args)
             and receipt["original_handoff_ref"] == inputs["original_handoff_ref"]
             and receipt["selector_sha256"] == digest(inputs["selector"]), "publication_dependency_conflict")
    _require(_same(receipt["object_selection"], args["object"])
             and _same(receipt["capability_selection"], args["capability"])
             and _same(receipt["requirement_ids"], args["requirement_ids"])
             and ("requirement_ids" not in artifact or _same(artifact["requirement_ids"], args["requirement_ids"]))
             and artifact["role"] == args["role"] and _same(artifact["declared_format"], args["declared_format"]),
             "publication_requirement_conflict")
    _require(artifact["task_association"]["task_id"] == task["task_id"], "original_task_mismatch")
    _original_object(args["object"], artifact["workspace_object"], inputs["request"])
    _require(artifact["source_ref"] == binding["source_ref"] == binding["content"]["source_ref"]
             and artifact["raw_artifact_ref"] == binding["content"]["artifact_ref"]
             and artifact["sha256"] == binding["content"]["sha256"]
             and artifact["byte_count"] == binding["content"]["byte_count"]
             and artifact["transfer"]["receipt_ref"] == ref
             and _same(artifact["transfer"]["requested_range"], args["byte_range"]), "acquisition_source_conflict")
    transport = binding["transport"]
    _require(type(transport.get("status")) is int and 100 <= transport["status"] <= 599
             and type(transport.get("body_complete")) is bool
             and type(transport.get("received_body_bytes")) is int
             and transport["received_body_bytes"] == artifact["byte_count"]
             and transport.get("effective_url") == call["url"] and transport.get("automatic_redirects") is False
             and type(transport.get("request")) is dict and transport["request"].get("method") == "GET"
             and transport["request"].get("url") == call["url"], "acquisition_transport_conflict")
    _require(not artifact["transfer"]["body_complete"] or transport["body_complete"], "acquisition_transport_conflict")
    _require(transport["status"] in (200, 206) or receipt["status"] == "failed", "acquisition_status_conflict")
    return ref, receipt


def _usable(receipt):
    transfer = receipt["artifact"]["transfer"]
    return (receipt["status"] == "ok" and receipt["failure"] is None
            and transfer["body_complete"] and transfer["object_complete"] == "yes")


def _representation(artifact):
    # A new metadata/association receipt does not make the same object's bytes
    # independent. Every original provenance field stays in the actual member.
    return {"object": {key: artifact["workspace_object"][key] for key in ("path", "uuid", "type")},
            "task_id": artifact["task_association"]["task_id"], "sha256": artifact["sha256"],
            "byte_count": artifact["byte_count"], "observed_range": artifact["transfer"]["observed_range"]}


def _missing(requirement, receipts):
    if not receipts:
        reason = "output_bytes_missing"
    elif all(row["status"] == "failed" for row in receipts):
        reason = "download_failed"
    elif all(row["status"] == "invalid" for row in receipts):
        reason = "download_invalid"
    elif any(not row["artifact"]["transfer"]["body_complete"]
             or row["artifact"]["transfer"]["object_complete"] == "no" for row in receipts):
        reason = "download_incomplete"
    else:
        reason = "object_completeness_unproven"
    return {"requirement_id": requirement["requirement_id"], "kind": "output_bytes", "role": requirement["role"],
            "source_refs": list(dict.fromkeys(row["artifact"]["source_ref"] for row in receipts)), "reason_code": reason}


def build_artifact_bundle(publication_inputs, *, original_task, acquisitions,
                          input_bindings, query_bindings):
    """Build from the host's ordered, authenticated prior/current acquisitions.

    Repeated refs must retain the same value. Distinct and repeated representations
    remain in artifact order; the schema's unique reference list records every
    distinct receipt. Prior publication hashes belong to their prior envelopes,
    which the host authenticates. Only the current hash equals the current inputs.
    Missing requirements use the closed reason set in ``_missing``. Scientific
    format validity, producer-specific rules and projection completeness belong
    to the separately bound scientific adapter, not to this acquisition builder.
    """
    inputs = _publication(publication_inputs)
    task = validate_contract("OriginalTask", original_task)
    _task(task, inputs["request"])
    _require(type(acquisitions) is list and type(input_bindings) is list and type(query_bindings) is list,
             "publication_dependency_conflict")
    _require(_same(input_bindings, inputs["request"]["input_bindings"]), "publication_input_bindings_conflict")
    artifacts, diagnostics, refs, seen, selected = [], [], [], {}, []
    current = None
    for index, row in enumerate(acquisitions):
        ref, receipt = _acquisition(row, inputs, task)
        if ref in seen:
            _require(_same(receipt, seen[ref]), "publication_dependency_conflict")
            diagnostics.append(_diagnostic("duplicate_acquisition_receipt", f"/acquisitions/{index}",
                                            severity="qualification", refs=[ref]))
        else:
            seen[ref] = receipt
            refs.append(ref)
        if ref not in inputs["prior_acquisition_receipt_refs"]:
            _require(current in (None, ref) and _same(receipt["snapshot"], inputs["current_snapshot"])
                     and receipt["publication_inputs_sha256"] == digest(inputs), "publication_dependency_conflict")
            current = ref
        else:
            _require(not _same(receipt["snapshot"], inputs["current_snapshot"]), "publication_dependency_conflict")
        if not receipt["requirement_ids"]:
            diagnostics.append(_diagnostic("unselected_artifact_retained", f"/acquisitions/{index}",
                                            severity="qualification", refs=[ref]))
            continue
        selected.append(receipt)
        artifact = receipt["artifact"]
        if receipt["status"] != "failed":
            for earlier in artifacts:
                if _same(_representation(earlier), _representation(artifact)):
                    diagnostics.append(_diagnostic("duplicate_artifact_representation", f"/acquisitions/{index}",
                        severity="qualification", refs=[earlier["transfer"]["receipt_ref"], ref]))
                    break
            artifacts.append(deepcopy(artifact))
            diagnostics.extend(_qualifications(artifact))
        if receipt["failure"] is not None:
            failure = receipt["failure"]
            diagnostics.append(_diagnostic(failure["code"], phase=failure["phase"], refs=[ref]))
    _require(refs == [*inputs["prior_acquisition_receipt_refs"], *([current] if current is not None else [])],
             "publication_dependency_conflict")
    missing = []
    for requirement in inputs["selector"]["requirements"]:
        candidates = [row for row in selected if requirement["requirement_id"] in row["requirement_ids"]]
        if requirement["required"] and not any(_usable(row) for row in candidates):
            missing.append(_missing(requirement, candidates))
    if not missing:
        status = "ok"
    elif (selected and all(row["status"] == "failed" for row in selected)
          and all(row["reason_code"] == "download_failed" for row in missing)):
        status = "failed"
    elif (selected and all(row["status"] == "invalid" for row in selected)
          and all(row["reason_code"] == "download_invalid" for row in missing)):
        status = "invalid"
    else:
        status = "partial"
    bundle = {"version": "bvbrc_appservice_artifact_bundle_v1", "original_task": task,
        "artifacts": artifacts, "input_bindings": input_bindings, "query_bindings": query_bindings,
        "supplied_scientific_metadata": inputs["supplied_evidence"], "acquisition_receipt_refs": refs,
        "requested_selector_sha256": digest(inputs["selector"]), "status": status,
        "missing_requirements": missing, "diagnostics": _unique(diagnostics)}
    if "supplied_contents" in inputs["selector"]:
        bundle["supplied_contents"] = deepcopy(inputs["selector"]["supplied_contents"])
    return validate_bundle(bundle)


__all__ = ["build_acquisition_value", "build_artifact_bundle"]
