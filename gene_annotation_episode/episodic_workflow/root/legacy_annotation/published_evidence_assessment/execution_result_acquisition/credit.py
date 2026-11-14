"""Private credit responsibility with original configured behavior."""
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


class ResultAcquisitionCredit:
    def credit_kind(self, role):
        if role != 'results':
            raise ValueError('fixed_execution_role_required')
        return 'operational'

    def project_credit(self, context, receiver_selection):
        if context.role != 'results' or context.run_id != self.run_id:
            raise ValueError('fixed_execution_context_required')
        closed = self._closed_operational_credit_view(context, receiver_selection)
        return self._live_project_credit(context, receiver_selection) if closed is None else closed

    def _live_project_credit(self, context, receiver_selection):
        if self.native_flux_balance_results is not None and self.native_flux_balance_results.applies(context):
            return self.native_flux_balance_results.credit_view(context, receiver_selection)
        if self.native_blast_masking_results.applies(context):
            return self.native_blast_masking_results.credit_view(context, receiver_selection)
        if self.native_blast_utility_results.applies(context):
            return self.native_blast_utility_results.credit_view(context, receiver_selection)
        if self.native_fluorescence_results.applies(context):
            return self.native_fluorescence_results.credit_view(context, receiver_selection)
        if self.native_expression_nmf_results is not None and self.native_expression_nmf_results.applies(context):
            return self.native_expression_nmf_results.credit_view(context, receiver_selection)
        if self.atac_results is not None and self.atac_results.applies(context):
            return self.atac_results.credit_view(context, receiver_selection)
        if self.native_chromatin_interaction_results is not None and self.native_chromatin_interaction_results.applies(context):
            return self.native_chromatin_interaction_results.credit_view(context, receiver_selection)
        if self.native_genomic_overlap_results is not None and self.native_genomic_overlap_results.applies(context):
            return self.native_genomic_overlap_results.credit_view(context, receiver_selection)
        if self.native_protein_structure_results.applies(context):
            return self.native_protein_structure_results.credit_view(context, receiver_selection)
        if self.rna_structure_comparison_results is not None and self.rna_structure_comparison_results.applies(context):
            return self.rna_structure_comparison_results.credit_view(context, receiver_selection)
        if self.native_rna_structure_results is not None and self.native_rna_structure_results.applies(context):
            return self.native_rna_structure_results.credit_view(context, receiver_selection)
        if self.native_blast_standard_database_results is not None and self.native_blast_standard_database_results.applies(context):
            return self.native_blast_standard_database_results.credit_view(context, receiver_selection)
        if self.native_blast_database_results is not None and self.native_blast_database_results.applies(context):
            return self.native_blast_database_results.credit_view(context, receiver_selection)
        if self.native_hmmer_preparation_results is not None and self.native_hmmer_preparation_results.applies(context):
            return self.native_hmmer_preparation_results.credit_view(context, receiver_selection)
        if self.native_infernal_preparation_results is not None and self.native_infernal_preparation_results.applies(context):
            return self.native_infernal_preparation_results.credit_view(context, receiver_selection)
        if self.native_blast_results is not None and self.native_blast_results.applies(context):
            return self.native_blast_results.credit_view(context, receiver_selection)
        if self.native_infernal_results is not None and self.native_infernal_results.applies(context):
            return self.native_infernal_results.credit_view(context, receiver_selection)
        if self.native_hmmer_results.applies(context):
            return self.native_hmmer_results.credit_view(context, receiver_selection)
        if self._target(context)['resource_kind'] == 'api':
            return self.api_execution.credit_view(context, receiver_selection)
        selected, handoffs, results = self._received(context, receiver_selection)
        handoffs = {ref: target for ref, target in handoffs.items() if self.job_progress_provider.targets.usable_handoff(target)}
        initial = set(selected['initial_known_record_refs'])
        baseline = {target['resource_id'] for ref, target in handoffs.items() if ref in initial}
        identities = {target['resource_id'] for target in handoffs.values()}
        handoff_count = 0
        mixed = self.local_file_sources.acquisition_counts(context, selected, results)
        acquired_fraction = self._generic_result_selector_progress(context, results, initial) if mixed is None else 0.0
        acquired_count = int(acquired_fraction > 0)
        credit = self.handoff_unit * handoff_count + self.acquired_record_unit * acquired_fraction
        if mixed is not None:
            acquired_count = sum(mixed)
            credit = self.handoff_unit * handoff_count + self.acquired_record_unit * acquired_count
        return {'credit': credit, 'operational_credit': credit, 'new_handoff_count': handoff_count, **({'new_file_acquisition_count': mixed[1]} if mixed is not None else {}), **({'new_acquired_selector_fraction': acquired_fraction} if mixed is None else {}), 'new_acquired_record_count': acquired_count, 'operational_credit_binding': {'version': 'execution_received_selector_coverage_credit_v2' if mixed is None else 'execution_received_records_credit_v1', 'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit, 'qualification': 'original_selector_byte_position_union_current_filesystem_version_unverified' if mixed is None else 'original_request_resource_scope_selector_and_actual_received_unique_information'}}

    def credit_view(self, context, receiver_selection):
        if context.role != 'results' or context.run_id != self.run_id:
            raise ValueError('fixed_execution_context_required')
        return self.project_credit(context, receiver_selection)

