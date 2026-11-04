"""Read existing received File custody and metadata without opening payloads.

This is the common metadata authority used by native input adapters. It creates
no Sources, receipts, grants or scope mappings. The selected native process
separately verifies and stages the actual bytes.
"""
from __future__ import annotations

import json

from method_loop.identities import EpisodeRef

from .communication import plain
from .domain import ContractError
from .episode_bindings import BindingContext
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .native_file_capture import NativeFileCaptureError, _identity, _metadata


_BASELINE_ROLES = frozenset({"launch", "launch_local", "launch_hpc", "launch_api", "results"})


def _require(condition, code, failure_prefix):
    if not condition:
        raise ValueError(failure_prefix + code)


def received_file_context(store, context, *, failure_prefix, baseline=None):
    """Authenticate the original context, inheritance prefix and scoped receipts."""
    require = lambda condition, code: _require(condition, code, failure_prefix)
    require(baseline is None or type(baseline) is bool, "invalid_context")
    require(isinstance(context, BindingContext) and context.path
        and context.role == context.path[-1][0], "invalid_context")
    required = {"runtime_episodes", "runtime_actions", "runtime_forms",
        "runtime_model_calls", "runtime_observations", "runtime_record_receipts",
        "runtime_receipt_inheritance"}
    present = {row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    require(required <= present, "invalid_context")
    authority = EpisodeReturnRecords(store, context.run_id, failure_prefix=failure_prefix)
    receipts = EpisodeReceipts.__new__(EpisodeReceipts)
    receipts.store, receipts.db, receipts.run_id = store, store.db, context.run_id
    context_errors = {failure_prefix + value for value in (
        "context_conflict", "original_context_conflict", "saved_context_required")}
    context_errors.update({"episode_receipts_not_bound", "cyclic_receipt_inheritance",
        "invalid_received_report_prefix", "binding_context_path_must_match_role"})
    try:
        authority.authenticate(context, allow_unsaved=True)
        saved = store.db.execute("SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (context.run_id, context.episode_id)).fetchone()
        if saved is None:
            for table in ("runtime_actions", "runtime_forms", "runtime_model_calls", "runtime_observations"):
                require(store.db.execute(f"SELECT 1 FROM {table} WHERE run_id=? AND episode_id=? LIMIT 1",
                    (context.run_id, context.episode_id)).fetchone() is None, "invalid_context")
        current, seen = context, set()
        while True:
            require(current.episode_id not in seen, "invalid_context")
            seen.add(current.episode_id)
            manifest = receipts.manifest(current.episode_id)
            expected_parent = (EpisodeRef(context.run_id, current.path[:-1]).episode_id
                if len(current.path) > 1 else None)
            require("received_report_prefix" in manifest
                and manifest["parent_episode_id"] == expected_parent
                and authority._equal(current.request.get("message", {}).get("knowledge_inheritance"), manifest),
                "invalid_context")
            through = manifest["through_receipt_index"]
            require(through is None if expected_parent is None else type(through) is int and through >= 0,
                "invalid_context")
            if expected_parent is None:
                break
            parent = authority.context(expected_parent)
            require(parent.path == current.path[:-1] and parent.role == parent.path[-1][0], "invalid_context")
            store.validate_scope(plain(current.scope), plain(parent.scope))
            current = parent
        known = set(receipts.known(context.episode_id,
            baseline=context.role in _BASELINE_ROLES if baseline is None else baseline))
        scope = store.validate_scope(plain(context.scope))
    except (ContractError, json.JSONDecodeError) as error:
        raise ValueError(failure_prefix + "invalid_context") from error
    except ValueError as error:
        if str(error) not in context_errors:
            raise
        raise ValueError(failure_prefix + "invalid_context") from error
    return known, scope


def received_file_source(store, reference, *, metadata=False, failure_prefix):
    code = "metadata_source_required" if metadata else "source_artifact_mismatch"
    try:
        value = store.get(reference)
    except ContractError as error:
        if str(error) != "unknown_reference":
            raise
        raise ValueError(failure_prefix + code) from error
    _require(value.get("id") == reference and value.get("record_type") == "source", code, failure_prefix)
    return value


def received_file_path(store, identity, *, failure_prefix):
    _require(identity["artifact_ref"] == "artifact_" + identity["sha256"],
        "artifact_metadata_mismatch", failure_prefix)
    try:
        metadata = _metadata(store, identity["artifact_ref"])
    except NativeFileCaptureError as error:
        raise ValueError(failure_prefix + "artifact_metadata_mismatch") from error
    _require(metadata["sha256"] == identity["sha256"] and metadata["size"] == identity["size_bytes"],
        "artifact_metadata_mismatch", failure_prefix)
    return store.path / "artifacts" / identity["sha256"][:2] / identity["sha256"]


def validate_received_native_file_inputs(store, context, bindings, *, metadata_source_refs,
        reference_access, failure_prefix):
    """Return exact received bindings in order, without reading their byte paths."""
    known, scope = received_file_context(store, context, failure_prefix=failure_prefix)
    references, seen = [], set()
    require = lambda condition, code: _require(condition, code, failure_prefix)

    def received(reference, *, artifact=False):
        decision = reference_access(context, reference, None)
        require(decision is None or type(decision) is bool, "invalid_reference_access")
        require(decision is not False, "protected_reference_denied")
        require(reference in known, "input_not_received")
        if not artifact:
            require(reference in store.reference_subset([reference], scope), "input_outside_scope")
        if reference not in seen:
            seen.add(reference)
            references.append(reference)

    for binding in bindings:
        identity = binding["file"]
        received(identity["artifact_ref"], artifact=True)
        require(binding["path"] == str(received_file_path(store, identity,
            failure_prefix=failure_prefix)), "selected_path_mismatch")
    for reference in metadata_source_refs:
        if reference is not None:
            received(reference)
            received_file_source(store, reference, metadata=True, failure_prefix=failure_prefix)
    return references


def validate_macs2_peak_job_inputs(store, context, assignment, *, reference_access):
    """Authenticate both selected raw Files using the existing receipt authority."""
    if not (type(assignment) is dict and type(assignment.get("requested_job")) is dict
            and "native_macs2_peak" in assignment["requested_job"]):
        return []
    from .native_macs2_peak_execution import validate_macs2_peak_requested_job
    try:
        job = validate_macs2_peak_requested_job(assignment["requested_job"])["native_macs2_peak"]
    except ValueError as error:
        raise ValueError("macs2_peak_input_invalid_requested_job") from error
    for occurrence, binding in zip(job["request"]["inputs"], job["input_bindings"]):
        _require(binding["input_key"] == occurrence["input_key"] and binding["file"] == occurrence["file"],
            "input_binding_mismatch", "macs2_peak_input_")
        _identity(binding["file"])
    reference = job["request"]["reference"]
    metadata = [source for value in [reference, *reference["contigs"], *reference["aliases"]]
        for source in value["source_refs"]]
    return validate_received_native_file_inputs(store, context, job["input_bindings"],
        metadata_source_refs=metadata, reference_access=reference_access, failure_prefix="macs2_peak_input_")


__all__ = ["received_file_context", "received_file_source", "received_file_path",
    "validate_received_native_file_inputs", "validate_macs2_peak_job_inputs"]
