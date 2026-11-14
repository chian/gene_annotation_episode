"""Bounded grading preparation, actual-context binding and selected RNA delivery.

The host validates custody and original authority. Scientific arithmetic remains
in the pure calculators. No Store observation, annotation score or retry is made.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.library.native_rna_structure_contracts import POLICY

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from typing import TYPE_CHECKING
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
from gene_annotation_episode.materials import artifact_file
from gene_annotation_episode.episodic_workflow.root.library.native_rna_structure_acquisition import decode_json, require, retained, validate_capture, rna_structure_source_payload, publish_rna_structure_source
from gene_annotation_episode.immutable_json_records import _immutable, _read
from gene_annotation_episode.episodic_workflow.root.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_contracts import RNA_ISSUE_CODES, analyze_rna_input_sequence, issue, validate_rna_input, validate_rna_sheet, validate_rna_components, validate_rna_parameters
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_result_views import merge_issues, project_rna_prepublication, validate_rna_structure_result_selector, validate_rna_structure_row, validate_saved_rna_input
from gene_annotation_episode.episodic_workflow.root.library.tool_grading_artifacts import retain_tool_grading, source_tool_gradings

if TYPE_CHECKING:
    from gene_annotation_episode.episodic_workflow.root.native_rna_structure_returns import NativeRNAStructureReturns

def _authority(store, context, *, baseline=False, allow_unsaved=False):
    EpisodeReturnRecords(store, context.run_id, failure_prefix="rna_").authenticate(context, allow_unsaved=allow_unsaved)
    return set(EpisodeReceipts(store, context.run_id).known(context.episode_id, baseline=baseline))


def authenticate_rna_results_commission(store, context, *, allow_unsaved=False):
    """The original parent action defines this results child's exact request."""
    records = EpisodeReturnRecords(store, context.run_id, failure_prefix="rna_")
    records.authenticate(context, allow_unsaved=allow_unsaved)
    require(context.role == "results" and len(context.path) > 1 and context.path[-1][0] == "results")
    slot = context.path[-1][1]
    require(slot.startswith("child_") and slot[6:].isdecimal() and str(int(slot[6:])) == slot[6:])
    parent_id = EpisodeRef(context.run_id, context.path[:-1]).episode_id
    parent = records.context(parent_id)
    store.validate_scope(plain(context.scope), parent_scope=plain(parent.scope))
    row = store.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
        (context.run_id, parent_id, int(slot[6:]))).fetchone()
    if row is None and allow_unsaved:
        # Workflow builds and validates the child before recording the selected
        # parent commission. This construction-only check grants no execution
        # authority: a persisted child still requires that exact original row.
        saved = store.db.execute("SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (context.run_id, context.episode_id)).fetchone()
        require(saved is None)
        manifest = EpisodeReceipts(store, context.run_id).manifest(context.episode_id)
        require(manifest["parent_episode_id"] == parent_id and
            records._equal(plain(context.request)["message"].get("knowledge_inheritance"), manifest))
        own = store.db.execute("SELECT 1 FROM runtime_actions WHERE run_id=? AND episode_id=? UNION ALL "
            "SELECT 1 FROM runtime_forms WHERE run_id=? AND episode_id=? LIMIT 1",
            (context.run_id, context.episode_id, context.run_id, context.episode_id)).fetchone()
        require(own is None)
        return context
    require(row is not None)
    action = decode_json(row["action"])
    contract = plain(context.request)["report_contract"]
    require(action.get("kind") in {"episode_child", "job_child"} and action.get("role") == "results" and
        action.get("assignment") == plain(context.assignment) and action.get("scope") == plain(context.scope) and
        action.get("purpose") == contract["decision"] and decode_json(action["schema_json"]) == contract["measurements"]["schema"])
    return context


def _qualify_original_handoff(store, context, bundle):
    authenticate_rna_results_commission(store, context)
    assignment = plain(context.assignment)
    handle = assignment["handoff_ref"]
    require(handle in _authority(store, context, baseline=True))
    original = PracticalReceiptInformation(store, context.run_id).read(handle, context.scope)
    source = store.get(handle)
    snapshot = decode_json(store.get_artifact(source["request_ref"]))
    selected, receipt = snapshot["assignment"], original["receipt"]
    job = receipt["outcome"].get("facts", {}).get("requested_job")
    identity = bundle["identity"]
    require(isinstance(job, dict) and isinstance(job.get("handoff"), dict) and
        receipt["tool_name"] in {"practical.job.start", "practical.job.status", "practical.job.collect"} and
        selected["requested_job"] == bundle["requested_job"] and selected["resource_kind"] == "local" and
        selected["resource_id"] == identity["resource_id"] and original["run_id"] == identity["run_id"] == context.run_id and
        original["episode_id"] == identity["episode_id"] and
        job["requested_job_sha256"] == identity["requested_job_sha256"] == digest(selected["requested_job"]) and
        job["argv"] == selected["requested_job"]["argv"] and job["environment"] == selected["requested_job"]["environment"] and
        job["resource_kind"] == selected["resource_kind"] and job["execution_id"] == identity["execution_id"] == job["handoff"]["execution_id"] and
        job["handoff"]["monitor_operation"] == "practical.job.status" and job["handoff"]["results_operation"] == "practical.job.collect")
    root = Path(selected["workspace"]) / ".episode-operations" / digest({"run": identity["run_id"], "episode": identity["episode_id"]}) / digest(identity["operation_key"])
    require(Path(identity["execution_id"]) == root / "native.json")
    requested = selected["requested_job"]["native_rna_structure"]
    require(all(bundle[name] == requested[name] for name in ("operation", "mode", "record_key")))


def _rna_reverse(sequence):
    require(all(letter in "ACGURYSWKMBDHVNacguryswkmbdhvn" for letter in sequence), "rna_subject_binding_conflict")
    return sequence.translate(str.maketrans("ACGURYSWKMBDHVNacguryswkmbdhvn", "UGCAYRSWMKVHDBNugcayrswmkvhdbn"))[::-1]


def _subject_sequence(store, reference):
    row = store.get(reference)
    if row["record_type"] == "feature":
        parent = _subject_sequence(store, row["subject_ref"])
        sequence = "".join(parent[part["start"]:part["end"]] for part in row["segments"])
        return _rna_reverse(sequence) if row["strand"] == "-" else sequence
    if row["record_type"] == "read_subject":
        from gene_annotation_episode.materials_packing import component_window
        return component_window(store, store.get(row["member_ref"]), "sequence", 0, row["length"]).decode("ascii")
    require(row.get("sequence_ref") is not None, "rna_subject_binding_conflict")
    return store.get_artifact(row["sequence_ref"]).decode("ascii")


def validate_rna_structure_publication_inputs(store, context, *, original_input, capture):
    if original_input is None:
        return None
    try:
        mode = "mfe_prediction" if original_input["schema"] == "rna_prediction_input_v1" else "supplied_features"
        request = validate_rna_input(original_input, mode=mode)
        binding = request["subject_binding"]
        provenance = request.get("structure_source_ref")
        if binding is None and provenance is None:
            return None
        known = _authority(store, context, baseline=True)
        if provenance is not None:
            require(provenance in known and store.get(provenance)["record_type"] == "source", "rna_subject_binding_conflict")
        if binding is None:
            return None
        subject, artifact = binding["subject_ref"], binding["sequence_artifact_ref"]
        require({subject, artifact} <= known, "rna_subject_binding_conflict")
        require(store.subject_unit(subject) == "nt" and store.subject_molecule(subject) == "rna", "rna_subject_binding_conflict")
        sequence = _subject_sequence(store, subject)
        require(store.get_artifact(artifact).decode("ascii") == sequence and len(sequence) == store.subject_length(subject), "rna_subject_binding_conflict")
        start, end = binding["start"], binding["end"]
        require(0 <= start < end <= len(sequence), "rna_subject_binding_conflict")
        footprint = store.map_segments(subject, [{"start": start, "end": end}])
        require(bool(footprint) and store.scope_covers(footprint, plain(context.scope)), "rna_subject_binding_conflict")
        selected = sequence[start:end]
        if binding["strand"] == "-":
            selected = _rna_reverse(selected)
        if request["normalization"] == "uppercase_ascii":
            selected = selected.translate(str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
        analysis, _ = analyze_rna_input_sequence(request, mode=mode)
        require(analysis is not None and analysis["analysis_sequence"] == selected, "rna_subject_binding_conflict")
        return deepcopy(binding)
    except (ValueError, OSError, KeyError, UnicodeError) as error:
        raise ValueError("rna_subject_binding_conflict") from error


def validate_rna_structure_job_inputs(store, context, assignment):
    request = assignment.get("requested_job", {})
    if "native_rna_structure" not in request:
        return []
    from gene_annotation_episode.episodic_workflow.root.library.native_rna_structure_contracts import validate_rna_structure_requested_job
    job = validate_rna_structure_requested_job(request)["native_rna_structure"]
    known, refs, original = _authority(store, context, allow_unsaved=True), [], None
    for operand in job["operands"]:
        ref = operand["artifact_ref"]
        if ref is None:
            continue
        require(ref in known, "rna_subject_binding_conflict")
        metadata, _ = retained(store, ref)
        require((metadata["sha256"], metadata["size"]) == (operand["sha256"], operand["size_bytes"]), "rna_capture_digest_mismatch")
        refs.append(ref)
        if operand["role"] == "input":
            original = validate_rna_input(decode_json(store.get_artifact(ref)), mode=job["mode"])
            require(original["record_key"] == job["record_key"], "rna_input_identity_mismatch")
    if original is not None:
        binding = original["subject_binding"]
        refs.extend([] if binding is None else [binding["subject_ref"], binding["sequence_artifact_ref"]])
        if original.get("structure_source_ref") is not None:
            refs.append(original["structure_source_ref"])
        require(set(refs) <= known, "rna_subject_binding_conflict")
    return list(dict.fromkeys(refs))


def validate_rna_structure_selected_inputs(store, context, selector, *, handoff_ref,
        returns: NativeRNAStructureReturns):
    if selector.get("acquisition") != "retained_sheet_only":
        return []
    saved = validate_saved_rna_input(selector["saved_input"])
    require(saved["handoff_ref"] == handoff_ref)
    returns.resolve_saved_rna_input(context, saved)
    return [saved[key] for key in ("handoff_ref", "source_ref", "bundle_artifact_ref", "sheet_artifact_ref")]


