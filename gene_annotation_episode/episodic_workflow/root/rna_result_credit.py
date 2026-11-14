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
from gene_annotation_episode.episodic_workflow.root.library.rna_result_reference_access import retained_reference_access

class RnaResultCredit:
    def credit_view(self, context, receiver_selection):
        selection = plain(receiver_selection)
        known, initial = set(selection["known_record_refs"]), set(selection["initial_known_record_refs"])
        require(initial <= known)
        acquired, inherited = set(), set()
        for body in self._own_bodies(context):
            if body["assignment"]["selector"]["acquisition"] == "complete_bound_bundle" and body["source_ref"] in known:
                acquired.add(digest(self._bundle(body)["identity"]))
        for reference in initial:
            try:
                inherited.add(self.result_identity(reference, context.scope))
            except (ValueError, KeyError, OSError):
                pass
        count = len(acquired - inherited)
        value = self.owner.acquired_record_unit * count
        return {"credit": value, "operational_credit": value, "new_handoff_count": 0,
            "new_acquired_record_count": count, "operational_credit_binding": {"version": VERSION,
                "handoff_unit": self.owner.handoff_unit, "acquired_record_unit": self.owner.acquired_record_unit,
                "scientific_credit": False, "monitoring_credit": False}}

    def completion(self, context):
        for body in self._own_bodies(context):
            selected = self.owner._selected_result_action(context.episode_id, body["operation_key"], body["tool_name"], body["arguments"])
            if body["delivery_complete"] and selected["result"] is not None:
                return {"version": "practical_completion_v1", "run_id": context.run_id, "episode_id": context.episode_id,
                    "assignment_sha256": digest(context.assignment), "endpoint": "usable_handoff", "operation_key": body["operation_key"],
                    "receipt_sha256": digest(body), "validation_keys": ["original_native_attempt",
                        "retained_original_sheet_custody" if body["assignment"]["selector"]["acquisition"] == "retained_sheet_only" else "complete_sealed_bundle_acquisition",
                        "requested_rna_projection_or_explicit_unavailability"]}
        return None

