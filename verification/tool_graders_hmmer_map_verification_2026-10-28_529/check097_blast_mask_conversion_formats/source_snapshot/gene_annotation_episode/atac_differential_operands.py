"""Qualify selected atac inputs from original received metadata only.

This boundary neither reads scientific bytes nor establishes native usability.
The selected driver owns staging, digest verification and parsing. Receipt
access and scope access do not assert a biological relationship to the target.
"""
from __future__ import annotations

import json

from method_loop.identities import EpisodeRef

from .communication import plain
from .domain import ContractError
from .episode_bindings import BindingContext
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .native_atac_differential_contracts import validate_atac_requested_job
from .native_file_capture import NativeFileCaptureError, _metadata


_BASELINE_ROLES = frozenset({"launch", "launch_local", "launch_hpc", "launch_api", "results"})
_JOB_ERRORS = frozenset({"original_attempt_mismatch", "native_dependency_unavailable",
    "unsupported_native_format", "invalid_output_path", "invalid_native_environment",
    "explicit_runtime_environment_required"})
_CONTEXT_ERRORS = frozenset({"atac_input_context_conflict",
    "atac_input_original_context_conflict", "atac_input_saved_context_required",
    "episode_receipts_not_bound", "cyclic_receipt_inheritance", "invalid_received_report_prefix",
    "binding_context_path_must_match_role"})


def _require(condition, code):
    if not condition:
        raise ValueError("atac_input_" + code)


def _context_inputs(store, context):
    _require(isinstance(context, BindingContext) and context.path
        and context.role == context.path[-1][0], "invalid_context")
    required = {"runtime_episodes", "runtime_actions", "runtime_forms",
        "runtime_model_calls", "runtime_observations", "runtime_record_receipts",
        "runtime_receipt_inheritance"}
    present = {row[0] for row in store.db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    _require(required <= present, "invalid_context")
    authority = EpisodeReturnRecords(store, context.run_id, failure_prefix="atac_input_")
    # Reading the existing receipt selection must not run its schema writer.
    receipts = EpisodeReceipts.__new__(EpisodeReceipts)
    receipts.store, receipts.db, receipts.run_id = store, store.db, context.run_id
    try:
        authority.authenticate(context, allow_unsaved=True)
        saved = store.db.execute("SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (context.run_id, context.episode_id)).fetchone()
        if saved is None:
            # Ordinary construction precedes the episode row, not its history.
            for table in ("runtime_actions", "runtime_forms", "runtime_model_calls", "runtime_observations"):
                _require(store.db.execute(f"SELECT 1 FROM {table} WHERE run_id=? AND episode_id=? LIMIT 1",
                    (context.run_id, context.episode_id)).fetchone() is None, "invalid_context")
        current, seen = context, set()
        while True:
            _require(current.episode_id not in seen, "invalid_context")
            seen.add(current.episode_id)
            manifest = receipts.manifest(current.episode_id)
            expected_parent = (EpisodeRef(context.run_id, current.path[:-1]).episode_id
                if len(current.path) > 1 else None)
            _require("received_report_prefix" in manifest
                and manifest["parent_episode_id"] == expected_parent
                and authority._equal(current.request.get("message", {}).get("knowledge_inheritance"), manifest),
                "invalid_context")
            through = manifest["through_receipt_index"]
            _require(through is None if expected_parent is None else type(through) is int and through >= 0,
                "invalid_context")
            if expected_parent is None:
                break
            parent = authority.context(expected_parent)
            _require(parent.path == current.path[:-1] and parent.role == parent.path[-1][0], "invalid_context")
            store.validate_scope(plain(current.scope), plain(parent.scope))
            current = parent
        known = set(receipts.known(context.episode_id, baseline=context.role in _BASELINE_ROLES))
        scope = store.validate_scope(plain(context.scope))
    except (ContractError, json.JSONDecodeError) as error:
        raise ValueError("atac_input_invalid_context") from error
    except ValueError as error:
        if str(error) not in _CONTEXT_ERRORS:
            raise
        raise ValueError("atac_input_invalid_context") from error
    return known, scope


def _source(store, reference, *, metadata=False):
    code = "metadata_source_required" if metadata else "source_artifact_mismatch"
    try:
        value = store.get(reference)
    except ContractError as error:
        if str(error) != "unknown_reference":
            raise
        raise ValueError("atac_input_" + code) from error
    _require(value.get("id") == reference and value.get("record_type") == "source", code)
    return value


def _file(store, identity):
    _require(identity["artifact_ref"] == "artifact_" + identity["sha256"], "artifact_metadata_mismatch")
    try:
        metadata = _metadata(store, identity["artifact_ref"])
    except NativeFileCaptureError as error:
        raise ValueError("atac_input_artifact_metadata_mismatch") from error
    _require(metadata["sha256"] == identity["sha256"] and metadata["size"] == identity["size_bytes"],
        "artifact_metadata_mismatch")
    return store.path / "artifacts" / identity["sha256"][:2] / identity["sha256"]


def validate_atac_job_inputs(
    store, context: BindingContext, assignment: dict, *, reference_access
) -> list[str]:
    """Return exact selected received handles once, in the agreed field order.

    Callback True is only a provider decision. Actual original receipts, Store
    scope, source/file relationships and metadata identity remain necessary.
    """
    if not (type(assignment) is dict and type(assignment.get("requested_job")) is dict
            and "native_atac_differential" in assignment["requested_job"]):
        return []
    try:
        requested = validate_atac_requested_job(assignment["requested_job"])
    except ValueError as error:
        raise ValueError("atac_input_invalid_requested_job") from error
    known, scope = _context_inputs(store, context)
    job = requested["native_atac_differential"]
    request = job["request"]
    references, seen = [], set()

    def received(reference, *, artifact=False):
        decision = reference_access(context, reference, None)
        _require(decision is None or type(decision) is bool, "invalid_reference_access")
        _require(decision is not False, "protected_reference_denied")
        _require(reference in known, "input_not_received")
        # Explicitly received raw BAM custody is sufficient here. Store's
        # generic artifact registry intentionally only lists source-attached
        # artifacts; creating a source would invent a scientific origin.
        if not artifact:
            _require(reference in store.reference_subset([reference], scope), "input_outside_scope")
        if reference not in seen:
            seen.add(reference)
            references.append(reference)

    def metadata_source(reference):
        if reference is not None:
            received(reference)
            _source(store, reference, metadata=True)

    for occurrence, binding in zip(request["inputs"], job["input_bindings"]):
        identity = occurrence["file"]
        received(identity["artifact_ref"], artifact=True)
        _require(binding["input_key"] == occurrence["input_key"]
            and binding["file"] == identity, "input_binding_mismatch")
        _require(binding["path"] == str(_file(store, identity)), "selected_path_mismatch")
    reference = request["reference"]
    for value in [reference, *reference["contigs"], *reference["aliases"]]:
        for source_ref in value["source_refs"]:
            metadata_source(source_ref)
    return references


__all__ = ["validate_atac_job_inputs"]
