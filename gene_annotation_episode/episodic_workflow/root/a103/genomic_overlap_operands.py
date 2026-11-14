"""Read-only received input authority for the selected genomic overlap job.

This port validates retained metadata and the original receipt prefix. It does
not observe current artifact bytes: the bounded native driver owns staging,
digest checks and parsing, including later missing or changed files. Store's
scope boundary does not assert that a globally scoped dataset belongs to the
annotation target.
"""
from __future__ import annotations

from .communication import plain
from .domain import ContractError
from .episode_bindings import BindingContext
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .native_file_capture import NativeFileCaptureError, _metadata
from .native_genomic_overlap_contracts import validate_genomic_overlap_requested_job


_BASELINE_ROLES = frozenset({"launch", "launch_local", "launch_hpc", "launch_api", "results"})
_CONTEXT_ERRORS = frozenset({
    "genomic_overlap_context_conflict", "genomic_overlap_original_context_conflict",
    "genomic_overlap_saved_context_required", "episode_receipts_not_bound",
    "cyclic_receipt_inheritance", "invalid_received_report_prefix",
})


def _require(condition, code):
    if not condition:
        raise ValueError("genomic_overlap_" + code)


def _context_inputs(store, context):
    _require(isinstance(context, BindingContext), "invalid_context")
    # Construction can precede saving this episode, but must use the existing
    # runtime authority. No schema installation or receipt grants occur here.
    _require(store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='runtime_episodes'").fetchone() is not None, "invalid_context")
    try:
        EpisodeReturnRecords(store, context.run_id, failure_prefix="genomic_overlap_").authenticate(
            context, allow_unsaved=True)
        # Read the shared implementation without the writer constructor's schema
        # transaction. Inherited prefixes and original own inputs stay frozen.
        receipts = EpisodeReceipts.__new__(EpisodeReceipts)
        receipts.store, receipts.db, receipts.run_id = store, store.db, context.run_id
        known = set(receipts.known(context.episode_id, baseline=context.role in _BASELINE_ROLES))
    except ValueError as error:
        if str(error) not in _CONTEXT_ERRORS:
            raise
        raise ValueError("genomic_overlap_invalid_context") from error
    try:
        scope = store.validate_scope(plain(context.scope))
    except ContractError as error:
        raise ValueError("genomic_overlap_invalid_context") from error
    return known, scope


def _source(store, reference):
    try:
        value = store.get(reference)
    except ContractError as error:
        if str(error) != "unknown_reference":
            raise
        raise ValueError("genomic_overlap_source_artifact_mismatch") from error
    _require(value.get("id") == reference and value.get("record_type") == "source",
        "source_artifact_mismatch")
    return value


def _file(store, identity):
    # _metadata is the shared native_file_capture metadata-only boundary.
    # retained_native_file / materials.artifact_path additionally hash bytes and
    # therefore deliberately do not belong in host input qualification.
    try:
        metadata = _metadata(store, identity["artifact_ref"])
    except NativeFileCaptureError as error:
        raise ValueError("genomic_overlap_artifact_metadata_mismatch") from error
    _require(metadata["sha256"] == identity["sha256"]
        and metadata["size"] == identity["size_bytes"], "artifact_metadata_mismatch")
    return store.path / "artifacts" / metadata["sha256"][:2] / metadata["sha256"]


def validate_genomic_overlap_job_inputs(store, context, assignment, *, reference_access) -> list[str]:
    """Return only the selected received references, once in request order.

Reference metadata order is its source_refs, each contig's source_refs, then
the optional sequence_dictionary artifact. Those explicit inputs are checked
individually; the request declares no source-to-dictionary association.
    """
    if not (type(assignment) is dict and type(assignment.get("requested_job")) is dict
            and "native_genomic_overlap" in assignment["requested_job"]):
        return []
    try:
        requested = validate_genomic_overlap_requested_job(assignment["requested_job"])
    except ValueError as error:
        # The shared validator's one legacy code lacks the family prefix.
        if str(error) != "original_attempt_mismatch":
            raise
        raise ValueError("genomic_overlap_invalid_requested_job") from error
    known, scope = _context_inputs(store, context)
    job = requested["native_genomic_overlap"]
    references, seen = [], set()

    def received(reference, *, artifact=False):
        decision = reference_access(context, reference, None)
        _require(decision is None or type(decision) is bool, "invalid_reference_access")
        _require(decision is not False, "protected_reference_denied")
        _require(reference in known, "input_not_received")
        # A supplied File need not have an owning scientific record. Its actual
        # receipt plus _file's retained metadata establish admission; the
        # record-based artifact projection would require inventing such a record.
        # Sources and reference assertions still use the ordinary scope rule.
        if not artifact:
            _require(reference in store.reference_subset([reference], scope), "input_outside_scope")
        if reference not in seen:
            seen.add(reference)
            references.append(reference)

    for spec, binding in zip(job["request"]["region_sets"], job["inputs"]):
        source, identity = spec["source"], spec["source"]["file"]
        source_ref = source.get("source_ref")
        if source_ref is not None:
            received(source_ref)
        received(identity["artifact_ref"], artifact=True)
        if source_ref is not None:
            actual = _source(store, source_ref)
            _require(actual["artifact_ref"] == identity["artifact_ref"], "source_artifact_mismatch")
        _require(binding["path"] == str(_file(store, identity)), "selected_path_mismatch")
        metadata = spec["reference"]
        if metadata is not None:
            for reference in metadata["source_refs"]:
                received(reference)
                _source(store, reference)
            for contig in metadata["contigs"]:
                for reference in contig["source_refs"]:
                    received(reference)
                    _source(store, reference)
            dictionary = metadata["sequence_dictionary"]
            if dictionary is not None:
                received(dictionary["artifact_ref"], artifact=True)
                _file(store, dictionary)
    return references


__all__ = ["validate_genomic_overlap_job_inputs"]
