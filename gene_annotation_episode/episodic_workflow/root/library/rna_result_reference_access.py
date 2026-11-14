"""Selected RNA custody/calculation actions in the existing results episode.

Receipts authenticate recorded work. This adapter chooses no native work,
resource, retry, annotation credit or extra episode observation.
"""
from __future__ import annotations

from copy import deepcopy
import json

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.communication import validate_form
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.root.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import checked, obj
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.root.library.native_rna_structure_acquisition import ORIGIN, capture_local_rna_structure_bundle, decode_json, is_native_rna_structure_target, publish_rna_structure_source, qualify_target_plan, require, retained, rna_structure_source_payload, validate_capture
from gene_annotation_episode.episodic_workflow.root.library.rna_result_preparation import prepare_rna_structure_grading, prepare_saved_rna_structure_grading, validate_prepared_rna_grading
from gene_annotation_episode.episodic_workflow.root.library.rna_result_publication import publish_selected_rna_structure_rows
from gene_annotation_episode.episodic_workflow.root.library.rna_result_operand_authority import authenticate_rna_results_commission
from gene_annotation_episode.immutable_json_records import _immutable, _read
from gene_annotation_episode.progress_records import validate_resource_observation
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_contracts import RNA_ISSUE_CODES, issue, validate_rna_issue
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_result_views import FAMILY_SOURCES, IDENTIFIER_NAMESPACES, REFERENCE_SOURCE, SAVED_SOURCE, merge_issues, prepare_rna_structure_failure_selection, project_rna_structure_failure_rows, result_receipt_key, validate_rna_structure_result_selector, validate_rna_structure_row, validate_saved_rna_input

from gene_annotation_episode.episodic_workflow.root.library.rna_result_records import VERSION, FIELDS, operation_catalog

def retained_reference_access(results, context, reference, namespace):
    """Deny accidental custody expansion, preserving independent operands."""
    if namespace not in {None, "source", "artifact", "execution_result"}:
        return None
    store = results.store
    try:
        record = store.get(reference)
    except (ValueError, KeyError):
        return None
    version = "native_rna_structure_bundle_v1"
    if record["record_type"] == "source":
        owns = record.get("provider") == "episode.execution_result" and record.get("version") == version
    elif record["record_type"] == "artifact":
        owns = store.db.execute("SELECT 1 FROM records r WHERE r.record_type='source' "
            "AND json_extract(r.data,'$.provider')='episode.execution_result' AND json_extract(r.data,'$.version')=? "
            "AND (json_extract(r.data,'$.artifact_ref')=? OR EXISTS "
            "(SELECT 1 FROM json_each(r.data,'$.auxiliary_artifact_refs') a WHERE a.value=?)) LIMIT 1",
            (version, reference, reference)).fetchone() is not None
        # Prepared handles are already compact recorded metadata. Do not open
        # another child's native files or full sheet merely to deny its access.
        if not owns:
            owns = store.db.execute("SELECT 1 FROM runtime_actions a WHERE a.run_id=? "
                "AND json_extract(a.result,'$.result.version')=? AND EXISTS (SELECT 1 FROM "
                "json_each(a.result,'$.result.prepared') p WHERE p.key IN ('sheet_artifact_ref',"
                "'components_artifact_ref','grading_artifact_ref','selected_rows_artifact_ref',"
                "'diagnostics_artifact_ref','worker_receipt_artifact_ref') AND p.value=?) LIMIT 1",
                (context.run_id, VERSION, reference)).fetchone() is not None
    else:
        return None
    if not owns:
        return None
    results.records.authenticate(context, allow_unsaved=True)
    # Explicit top-level original operands, not source traversal.
    assignment = plain(context.assignment)
    job = assignment.get("requested_job", {}).get("native_rna_structure", {})
    explicit = {row.get("artifact_ref") for row in job.get("operands", [])}
    if reference in explicit:
        from gene_annotation_episode.episodic_workflow.root.library.rna_result_operand_authority import validate_rna_structure_job_inputs
        return reference in validate_rna_structure_job_inputs(store, context, assignment)
    saved = assignment.get("selector", {}).get("saved_input")
    if saved is not None and reference in {saved[key] for key in
            ("handoff_ref", "source_ref", "bundle_artifact_ref", "sheet_artifact_ref")}:
        results.owner.native_rna_structure_returns.resolve_saved_rna_input(context, saved)
        return namespace in {None, "execution_result", record["record_type"]}
    if reference in store._refs(assignment) and reference in set(EpisodeReceipts(store, context.run_id).known(context.episode_id, baseline=True)):
        return namespace in {None, "execution_result", record["record_type"]}
    requested = {node.get("x-source") for node in (plain(context.request).get("report_contract") or {}).get("measurements", {}).get("schema", {}).get("properties", {}).values()}
    if context.role == "results" and SAVED_SOURCE in requested:
        for body in results._own_bodies(context):
            action = results.owner._selected_result_action(context.episode_id, body["operation_key"], body["tool_name"], body["arguments"])
            if action["result"] is None:
                continue
            descriptor = results.saved_descriptor(body, verify_bytes=False)
            if descriptor is not None and reference in {descriptor[key] for key in
                    ("handoff_ref", "source_ref", "bundle_artifact_ref", "sheet_artifact_ref")}:
                retained(store, descriptor["sheet_artifact_ref"])
                if record["record_type"] == "artifact":
                    retained(store, reference)
                return namespace in {None, "execution_result", record["record_type"]}
    # Scope subjects carry their actual sequence representation as an operand.
    scope = store.validate_scope(plain(context.scope))
    for subject in scope.get("subject_refs", []):
        if store.get(subject).get("sequence_ref") == reference:
            return namespace in {None, "artifact"}
    for action in store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND result IS NOT NULL",
            (context.run_id, context.episode_id)):
        outcome = json.loads(action["result"])
        if outcome.get("status") in {"completed", "partial"} and reference in outcome.get("record_refs", []):
            body = outcome.get("result")
            if isinstance(body, dict) and body.get("version") == VERSION:
                results._validate_body(body, context.scope)
            return namespace in {None, "execution_result", record["record_type"]}
    received = results.owner.native_rna_structure_returns.resolve_received(context, reference, namespace)
    if received is not None:
        return received
    # A different provider can explicitly return the identical content-addressed
    # artifact. Authenticate that original immediate-child form and inspect its
    # declared reference fields, never a recursively expanded source receipt.
    boundary = results.owner.native_rna_structure_returns
    from gene_annotation_episode.episodic_workflow.root.native_rna_structure_returns import requested_sources
    for attempt in boundary._attempts(context):
        schema = json.loads(attempt["contract"]).get("measurements", {}).get("schema", {})
        if requested_sources(schema):
            continue
        child, form, schema = boundary._attempt(context, attempt["decision_index"])
        references = []
        def collect(value, declared_namespace):
            if declared_namespace in {None, record["record_type"]}:
                references.append(value)
            return True
        validate_form(form, schema, collect)
        if reference in references:
            return namespace in {None, "execution_result", record["record_type"]}
    return False


