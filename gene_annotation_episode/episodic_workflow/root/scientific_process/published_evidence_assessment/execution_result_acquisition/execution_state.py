"""Fixed results execution state responsibility."""
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


class ResultAcquisitionExecutionState:
    def initialize(self, context):
        if context.role != 'results' or context.run_id != self.run_id:
            raise ValueError('fixed_execution_context_required')
        from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import is_compact_assignment as is_lumpy_assignment, is_compact_launch as is_lumpy_launch
        if is_lumpy_launch(plain(context.assignment)):
            self.lumpy_requests.initialize_launch(context)
            return
        if is_lumpy_assignment(plain(context.assignment)):
            self.lumpy_requests.initialize_resource(context)
            return self._delegate(context).initialize(self._practical_context(context))
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_request_binding import is_compact_assignment as is_macs2_assignment, is_compact_launch as is_macs2_launch
        if is_macs2_launch(plain(context.assignment)):
            self.macs2_peak_requests.initialize_launch(context)
            return
        if is_macs2_assignment(plain(context.assignment)):
            self.macs2_peak_requests.initialize_resource(context)
            return self._delegate(context).initialize(self._practical_context(context))
        from gene_annotation_episode.episodic_workflow.root.library.flux_balance_request_binding import is_compact_assignment, is_compact_launch
        if is_compact_launch(plain(context.assignment)):
            self.flux_balance_requests.initialize_launch(context)
            return
        if is_compact_assignment(plain(context.assignment)):
            self.flux_balance_requests.initialize_resource(context)
            self.flux_balance_inputs.initialize(context)
            return self._delegate(context).initialize(self._practical_context(context))
        if self.local_file_sources.applies(context):
            target = self._target(context)
            self.local_file_sources.selector(plain(context.assignment), target, validate_paths=False)
            return self._result_directory(context)
        if self._has_uniprot():
            original = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
            self.api_execution.uniprot_returns._selection(context, original)
        target = self._target(context)
        self._selector(plain(context.assignment), target)
        required = self._blast_target_requirement(target, context.scope)
        if required is not None:
            schema = plain(context.request)['report_contract']['measurements']['schema']
            if not any((node.get('x-source') == BLAST_GRADED_RETURN_SOURCE and node == BLAST_GRADED_RETURN_SCHEMA for node in schema.get('properties', {}).values())):
                raise ValueError('blast_grader_typed_return_required')
        if self._flux_balance_selector(plain(context.assignment)) or self._masking_selector(plain(context.assignment)) or self._utility_selector(plain(context.assignment)) or self._fluorescence_selector(plain(context.assignment)) or self._expression_nmf_selector(plain(context.assignment)) or self._atac_selector(plain(context.assignment)) or self._chromatin_selector(plain(context.assignment)) or self._genomic_overlap_selector(plain(context.assignment)) or self._comparison_selector(plain(context.assignment)) or is_native_protein_structure_target(target):
            self.initial_references(context)
        if target['resource_kind'] == 'api':
            return self.api_execution.initialize(context)
        self._result_directory(context)

    def state(self, context):
        """Expose the original practical state for its original resource role."""
        if context.role != 'results' or context.run_id != self.run_id:
            raise ValueError('fixed_execution_context_required')
        raise ValueError('practical_resource_role_required')

