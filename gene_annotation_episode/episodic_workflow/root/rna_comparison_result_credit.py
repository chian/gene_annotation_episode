"""One selected retained comparison action inside the existing results role.

Original inputs and actions establish authority. The separate worker owns only
deterministic calculation/publication. No native observation or acquisition runs.
"""
from __future__ import annotations

from copy import deepcopy
import json

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.communication import validate_form
from gene_annotation_episode.episodic_workflow.root.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_contracts import obj
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.root.library.rna_result_operand_authority import authenticate_rna_results_commission
from gene_annotation_episode.immutable_json_records import _immutable, _read
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_comparison_contracts import CALCULATOR_VERSION, SELECTOR_VERSION, validate_rna_comparison_issue, validate_rna_comparison_selector
from gene_annotation_episode.episodic_workflow.root.rna_structure_comparison_operands import RNAComparisonInputError, SAVED_REFERENCE_FIELDS, _require, resolve_rna_comparison_operands, validate_rna_comparison_selected_inputs
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_comparison_views import PROJECTION_SOURCE

from gene_annotation_episode.episodic_workflow.root.library.rna_comparison_result_records import VERSION, IDENTIFIER_NAMESPACES, FIELDS, PREPARED_COPY_FIELDS, VALIDATION_KEYS, result_receipt_key, operation_catalog, _original_keys
from gene_annotation_episode.episodic_workflow.root.library.native_rna_structure_contracts import POLICY

class RnaComparisonResultCredit:
    def credit_view(self, context, receiver_selection):
        self._assignment(context, allow_unsaved=True)
        selection = plain(receiver_selection)
        _require(type(selection) is dict and all(type(selection.get(key)) is list
            and all(type(ref) is str for ref in selection[key]) for key in ("known_record_refs", "initial_known_record_refs"))
            and set(selection["initial_known_record_refs"]) <= set(selection["known_record_refs"]), "invalid_receiver_selection")
        return {"credit": 0, "operational_credit": 0, "new_handoff_count": 0, "new_acquired_record_count": 0,
            "operational_credit_binding": {"version": VERSION, "handoff_unit": self.owner.handoff_unit,
                "acquired_record_unit": self.owner.acquired_record_unit, "scientific_credit": False, "monitoring_credit": False}}

    def completion(self, context):
        for body in self._own_bodies(context):
            selected = self.owner._selected_result_action(context.episode_id, body["operation_key"], body["tool_name"], body["arguments"])
            if body["tool_name"] == "execution.results.collect" and body["delivery_complete"] and selected["result"] is not None:
                return {"version": "practical_completion_v1", "run_id": context.run_id, "episode_id": context.episode_id,
                    "assignment_sha256": digest(plain(context.assignment)), "endpoint": "usable_handoff",
                    "operation_key": body["operation_key"], "receipt_sha256": digest(body), "validation_keys": list(VALIDATION_KEYS)}
        return None


