"""Selected, actually received RNA operands for retained comparisons.

The routing handoff has no scientific baseline meaning. Each canonical member
has its own original receipt and frozen return proof; nothing is reacquired.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from .communication import plain
from .episode_receipts import EpisodeReceipts
from .execution_contracts import digest
from .native_rna_structure_acquisition import decode_json, is_native_rna_structure_target
from .native_rna_structure_result_publication import authenticate_rna_results_commission
from .rna_structure_comparison_contracts import (
    SELECTOR_VERSION, validate_rna_comparison_issue, validate_rna_comparison_selector,
)
from .rna_structure_contracts import validate_rna_sheet
from .rna_structure_result_views import (
    FAMILY_SOURCES, SAVED_SOURCE, project_rna_structure_failure_rows, validate_rna_structure_row,
    validate_saved_rna_input,
)

RESOLVED_VERSION = "rna_structure_comparison_resolved_operands_v1"
SAVED_REFERENCE_FIELDS = ("handoff_ref", "source_ref", "bundle_artifact_ref", "sheet_artifact_ref")


def _require(condition, code):
    if not condition:
        raise ValueError("rna_comparison_" + code)


class RNAComparisonInputError(ValueError):
    """Established original authority whose required retained bytes are lost."""

    def __init__(self, issue):
        self.issue = validate_rna_comparison_issue(issue)
        super().__init__(self.issue["code"])


def _custody_error(member_id, code):
    return RNAComparisonInputError({"stage": "input", "code": code,
        "member_id": member_id, "comparison_id": None, "selection_id": None,
        "field": None, "index": None})


def _context(context, returns):
    returns.authenticate(context, allow_unsaved=True)
    receipts = EpisodeReceipts(returns.store, context.run_id)
    # The frozen manifest belongs to the original request, not today's ancestry.
    current, seen = context, set()
    while True:
        _require(current.episode_id not in seen, "saved_prefix_conflict")
        seen.add(current.episode_id)
        manifest = receipts.manifest(current.episode_id)
        _require(returns._equal(plain(current.request)["message"].get("knowledge_inheritance"), manifest),
            "saved_prefix_conflict")
        parent_id = manifest["parent_episode_id"]
        if parent_id is None:
            break
        parent = returns.context(parent_id)
        _require(current.path[:-1] == parent.path, "saved_prefix_conflict")
        current = parent
    if context.role == "results":
        authenticate_rna_results_commission(returns.store, context, allow_unsaved=True)
    return set(receipts.known(context.episode_id, baseline=context.role == "results"))


def _completed_original(returns, body):
    selected = returns.owner._selected_result_action(body["episode_id"], body["operation_key"],
        body["tool_name"], body["arguments"])
    _require(selected["result"] is not None, "original_action_incomplete")
    _require(json.loads(selected["result"]).get("status") == "completed", "original_action_incomplete")


def authenticate_received_rna_operand(context, descriptor, *, returns) -> dict:
    """Authenticate one original descriptor without imposing an anchor match."""
    _context(context, returns)
    descriptor = validate_saved_rna_input(descriptor)
    body = returns.authenticate_received_saved_input(context, descriptor)
    _completed_original(returns, body)
    for field in SAVED_REFERENCE_FIELDS:
        expected_type = "artifact" if field.endswith("artifact_ref") else "source"
        _require(returns.store.get(descriptor[field])["record_type"] == expected_type,
            "original_receipt_mismatch")
    _received_operand_value(context, descriptor, [descriptor[key] for key in SAVED_REFERENCE_FIELDS],
        returns, SAVED_SOURCE)
    return deepcopy(body)


def authenticate_received_rna_failure(context, failure, *, returns) -> dict:
    """Authenticate the entire selected failure row and its original ordinal."""
    _context(context, returns)
    failure = validate_rna_structure_row(failure)
    _require(failure["family"] == "failure", "original_receipt_mismatch")
    body = returns.results.read_receipt_key(failure["result_receipt_key"], context.scope)
    _completed_original(returns, body)
    selector = body["assignment"]["selector"]
    rows = project_rna_structure_failure_rows(body,
        selector=selector if selector["projection"]["family"] == "failure" else None)
    _require(any(returns._equal(failure, row) for row in rows), "original_receipt_mismatch")
    references = [] if failure["source_ref"] is None else [failure["source_ref"]]
    for reference in references:
        _require(returns.store.get(reference)["record_type"] == "source", "original_receipt_mismatch")
    _received_operand_value(context, failure, references, returns, FAMILY_SOURCES["failure"])
    return deepcopy(body)


def _received_operand_value(context, value, references, returns, source):
    """Prove actual form receipt order independently of Store-ref possession."""
    receipts = EpisodeReceipts(returns.store, context.run_id)
    known = set(receipts.known(context.episode_id, baseline=context.role == "results"))
    _require(set(references) <= known, "saved_operand_not_received")
    current, allowed, before = context, None, None
    while True:
        attempts = returns.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? "
            "AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL ORDER BY decision_index",
            (context.run_id, current.episode_id)).fetchall()
        for attempt in attempts:
            if current.episode_id == context.episode_id and context.role == "results":
                continue  # Selected inputs are this child's original knowledge.
            if before is not None and attempt["decision_index"] >= before:
                continue
            if allowed is not None:
                identity = {key: attempt[key] for key in ("decision_index", "delivery_ref", "child_episode_id")}
                identity.update(contract_sha256=digest(json.loads(attempt["contract"])),
                    form_sha256=digest(json.loads(attempt["form"])))
                if not any(returns._equal(identity, row) for row in allowed):
                    continue
            schema = json.loads(attempt["contract"]).get("measurements", {}).get("schema", {})
            if not any(node.get("x-source") == source for node in schema.get("properties", {}).values()):
                continue
            child, form, schema = returns._attempt(current, attempt["decision_index"])
            values = returns._validate_historical(child, form, schema, verify_artifacts=False)
            if any(returns._equal(value, received) for received in values.get(source, [])):
                return
        manifest = receipts.manifest(current.episode_id)
        if manifest["parent_episode_id"] is None:
            break
        prefix = manifest.get("received_report_prefix")
        _require(type(prefix) is dict and set(prefix) == {"version", "attempts"}
            and prefix["version"] == "frozen_received_report_prefix_v1" and type(prefix["attempts"]) is list,
            "operand_prefix_proof_unavailable")
        allowed = prefix["attempts"]
        _require(current.path[-1][1].startswith("child_"), "saved_prefix_conflict")
        before = int(current.path[-1][1][6:])
        current = returns.context(manifest["parent_episode_id"])
    raise ValueError("rna_comparison_saved_operand_not_received")


def _selected(store, context, selector, anchor_handoff_ref, returns):
    _require(returns.store is store and returns.run_id == context.run_id, "authority_binding_conflict")
    selector = validate_rna_comparison_selector(selector)
    known = _context(context, returns)
    if context.role == "results":
        assignment = plain(context.assignment)
        _require(assignment.get("version") == "execution_results_assignment_v1"
            and assignment.get("handoff_ref") == anchor_handoff_ref
            and returns._equal(assignment.get("selector"), selector), "selected_assignment_conflict")
    _require(anchor_handoff_ref in known, "anchor_not_received")
    _require(store.get(anchor_handoff_ref)["record_type"] == "source", "anchor_mismatch")
    target = returns.owner.job_progress_provider.targets.read_target(anchor_handoff_ref, context.scope)
    _require(is_native_rna_structure_target(target) and target["handle"] == anchor_handoff_ref
        and target["run_id"] == context.run_id, "anchor_mismatch")
    store.validate_scope(target["scope"], parent_scope=plain(context.scope))
    references, originals = [], {}
    for member in selector["question"]["membership"]:
        kind, member_id = member["kind"], member["member_id"]
        if kind == "saved_sheet":
            descriptor = member["saved_input"]
            originals[member_id] = authenticate_received_rna_operand(context, descriptor, returns=returns)
            references.extend(descriptor[field] for field in SAVED_REFERENCE_FIELDS)
        elif kind == "received_failure":
            originals[member_id] = authenticate_received_rna_failure(context, member["failure"], returns=returns)
            if member["failure"]["source_ref"] is not None:
                references.append(member["failure"]["source_ref"])
    for comparison in selector["question"]["comparisons"]:
        correspondence = comparison["correspondence"]
        reference = None if correspondence is None else correspondence.get("authority", {}).get("source_ref")
        if reference is not None:
            _require(reference in known and store.get(reference)["record_type"] == "source",
                "correspondence_source_not_received")
            _require(store.reference_subset([reference], plain(context.scope)), "correspondence_source_scope_conflict")
            references.append(reference)
    references.append(anchor_handoff_ref)
    return selector, originals, list(dict.fromkeys(references))


def validate_rna_comparison_selected_inputs(store, context, selector, *, anchor_handoff_ref, returns) -> list[str]:
    """Validate only the explicit membership and routing anchor at commission."""
    return _selected(store, context, selector, anchor_handoff_ref, returns)[2]


def _original_sheet(store, descriptor, member_id):
    metadata = store.get(descriptor["sheet_artifact_ref"])
    _require(metadata["record_type"] == "artifact" and metadata["sha256"] == descriptor["sheet_sha256"]
        and metadata["id"] == "artifact_" + descriptor["sheet_sha256"], "original_receipt_mismatch")
    path = store.path / "artifacts" / metadata["sha256"][:2] / metadata["sha256"]
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise _custody_error(member_id, "retained_sheet_missing") from error
    if hashlib.sha256(raw).hexdigest() != descriptor["sheet_sha256"] or len(raw) != metadata["size"]:
        error = ValueError("retained_artifact_bytes_disagree_with_original_digest")
        raise _custody_error(member_id, "retained_sheet_digest_mismatch") from error
    sheet = validate_rna_sheet(decode_json(raw, canonical_bytes=True))
    _require(all(sheet[field] == descriptor[field] for field in ("record_key", "operation", "mode")),
        "original_receipt_mismatch")
    return sheet


def resolve_rna_comparison_operands(store, context, selector, *, anchor_handoff_ref, returns) -> dict:
    """Read exact selected original sheets and already retained bundle software."""
    selector, originals, references = _selected(store, context, selector, anchor_handoff_ref, returns)
    data = {}
    for member in selector["question"]["membership"]:
        kind, member_id = member["kind"], member["member_id"]
        if kind == "alias":
            continue
        row = {"original_sheet": None, "original_bundle_software": None, "received_failure": None}
        if kind == "saved_sheet":
            row["original_sheet"] = _original_sheet(store, member["saved_input"], member_id)
            # Original result validation already authenticates this bundle.
            # No captured auxiliary output or producer location is traversed.
            bundle = returns.results._bundle(originals[member_id])
            row["original_bundle_software"] = deepcopy(bundle["software"])
        elif kind == "received_failure":
            row["received_failure"] = deepcopy(member["failure"])
        data[member_id] = row
    return {"version": RESOLVED_VERSION, "data": data, "original_receipts": originals,
        "selected_references": references}


__all__ = ["RNAComparisonInputError", "authenticate_received_rna_operand",
    "authenticate_received_rna_failure", "validate_rna_comparison_selected_inputs",
    "resolve_rna_comparison_operands"]
