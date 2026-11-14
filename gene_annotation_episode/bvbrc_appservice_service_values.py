"""Original AppService value checks; no service construction or invocation."""
from __future__ import annotations

import hashlib
import json
import re

from .domain import ContractError, canonical
from .bvbrc_appservice_contracts import contract_schema, validate_contract
from .bvbrc_appservice_readers import _object_binding

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


