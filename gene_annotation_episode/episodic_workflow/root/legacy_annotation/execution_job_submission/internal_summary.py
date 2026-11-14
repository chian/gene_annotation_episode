"""Private internal_summary responsibility with original configured behavior."""
from __future__ import annotations
import base64
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from gene_annotation_episode.domain import identity
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.immutable_json_records import _immutable, _read
from gene_annotation_episode.execution_contracts import checked, obj
from gene_annotation_episode.episodic_workflow.root.communication import validate_form
from gene_annotation_episode.episodic_workflow.root.execution_source_declarations import (VERSION, LAUNCH_VERSION, RESULTS_VERSION, RESULT_PROVIDER, _CLOSED_CREDIT, ROLES, KINDS, ROLE_KINDS, TEXT, OFFSET, LIMIT, FILE_LIMIT, NATIVE_RESULT_ORIGIN, NATIVE_RESULT_ORIGIN_SCHEMA, RESULTS_SCHEMA, BLAST_GRADED_REQUEST_VERSION, BLAST_GRADED_REQUEST_SCHEMA, BLAST_GRADED_RETURN_SOURCE, BLAST_GRADED_RETURN_SCHEMA, NATIVE_SELECTOR_SCHEMA, launch_operation_catalog, native_result_operation_catalog, _outcome, LOCAL_FILE_SOURCE_SELECTOR_SCHEMA, MACS2_FILE_SOURCE_SELECTOR_SCHEMA, MACS2_FILE_SOURCE_SELECTOR_VERSION, LUMPY_FILE_SOURCE_SELECTOR_SCHEMA, LUMPY_FILE_SOURCE_SELECTOR_VERSION, LOCAL_FILE_SOURCE_RECEIPT_VERSION, LOCAL_FILE_SOURCE_PROVIDER, is_file_source_selector, is_macs2_file_source_selector, is_lumpy_file_source_selector, ASSIGNMENT_SCHEMA, GENERIC_REQUESTED_JOB_SCHEMA, INPUT_VERSION_SCHEMA, SELECTION_SCHEMA, validate_assignment, validate_completion_proof, operation_catalog, confined, PracticalReceiptInformation, LocalFileSourceResults, is_native_hmmer_target, is_native_blast_target, is_native_blast_masking_target, is_native_blast_utility_target, is_native_blast_database_target, is_standard_blast_database_target, is_native_infernal_target, is_native_infernal_preparation_target, is_native_hmmer_preparation_target, is_native_rna_structure_target, is_native_protein_structure_target)


class ExecutionSubmissionInternalSummary:
    def decision_context(self, context, current_view):
        if context.role != 'launch' or context.run_id != self.run_id:
            raise ValueError('fixed_execution_context_required')
        from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import is_compact_assignment as is_lumpy_assignment
        if is_lumpy_assignment(plain(context.assignment)):
            progress = self.state(context).credit_view()
            return self._with_selected_execution_task(context, {'practical_assignment': plain(context.assignment), 'practical_progress': {key: deepcopy(progress[key]) for key in ('credit', 'satisfied_keys') if key in progress}, 'practical_completed': self.state(context).completion_proof() is not None})
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_request_binding import is_compact_assignment as is_macs2_assignment
        if is_macs2_assignment(plain(context.assignment)):
            progress = self.state(context).credit_view()
            return self._with_selected_execution_task(context, {'practical_assignment': plain(context.assignment), 'practical_progress': {key: deepcopy(progress[key]) for key in ('credit', 'satisfied_keys') if key in progress}, 'practical_completed': self.state(context).completion_proof() is not None})
        from gene_annotation_episode.episodic_workflow.root.library.flux_balance_request_binding import is_compact_assignment
        if is_compact_assignment(plain(context.assignment)):
            state = self.state(context)
            progress = state.credit_view()
            return {'practical_assignment': plain(context.assignment), 'practical_progress': {key: deepcopy(progress[key]) for key in ('credit', 'satisfied_keys') if key in progress}, 'practical_completed': state.completion_proof() is not None}
        value = {'execution_assignment': plain(context.assignment), 'execution_progress': self.facts(context, {})}
        return self._with_selected_execution_task(context, value)
