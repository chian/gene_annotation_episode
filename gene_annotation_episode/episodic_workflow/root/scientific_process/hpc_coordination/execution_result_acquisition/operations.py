"""Fixed results operations responsibility."""
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


class ResultAcquisitionOperations:
    def catalog(self, context):
        if context.role != 'results' or context.run_id != self.run_id:
            raise ValueError('fixed_execution_context_required')
        if self.native_flux_balance_results is not None and self.native_flux_balance_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.native_flux_balance_results import operation_catalog as fba_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return fba_result_catalog()
        if self.native_blast_masking_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.library.native_blast_masking_results import operation_catalog as masking_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return masking_result_catalog()
        if self.native_blast_utility_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.library.native_blast_utility_results import operation_catalog as utility_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return utility_result_catalog()
        if self.native_fluorescence_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.native_fluorescence_results import operation_catalog as fluorescence_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return fluorescence_result_catalog()
        if self.native_expression_nmf_results is not None and self.native_expression_nmf_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.native_expression_nmf_results import operation_catalog as nmf_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return nmf_result_catalog()
        if self.atac_results is not None and self.atac_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.native_atac_differential_results import operation_catalog as atac_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return atac_result_catalog()
        if self.native_chromatin_interaction_results is not None and self.native_chromatin_interaction_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.native_chromatin_interaction_results import operation_catalog as chromatin_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return chromatin_result_catalog()
        if self.native_genomic_overlap_results is not None and self.native_genomic_overlap_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.native_genomic_overlap_results import operation_catalog as overlap_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return overlap_result_catalog()
        if self.native_protein_structure_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.library.protein_structure_selection import validate_protein_structure_result_selector
            from gene_annotation_episode.episodic_workflow.root.native_protein_structure_results import operation_catalog as protein_result_catalog
            validate_protein_structure_result_selector(plain(context.assignment)['selector'])
            return protein_result_catalog()
        target = self._target(context)
        if is_native_protein_structure_target(target):
            self._selector(plain(context.assignment), target)
        if self._comparison_selector(plain(context.assignment)):
            self._selector(plain(context.assignment), target)
            from gene_annotation_episode.episodic_workflow.root.library.rna_comparison_result_records import operation_catalog as comparison_catalog
            return comparison_catalog()
        if is_native_rna_structure_target(target):
            self._selector(plain(context.assignment), target)
            from gene_annotation_episode.episodic_workflow.root.library.rna_result_records import operation_catalog as rna_result_catalog
            return rna_result_catalog()
        if is_standard_blast_database_target(target):
            self._selector(plain(context.assignment), target)
            from gene_annotation_episode.episodic_workflow.root.native_blast_standard_database_results import operation_catalog as database_catalog
            return database_catalog()
        if is_native_blast_database_target(target):
            selector = self._selector(plain(context.assignment), target)
            from gene_annotation_episode.episodic_workflow.root.native_blast_database_results import operation_catalog as database_catalog
            return database_catalog(selector)
        if target['resource_kind'] == 'api':
            return self.api_execution.catalog(context)
        if is_native_hmmer_preparation_target(target):
            if self.native_hmmer_preparation_results is None:
                raise ValueError('native_hmmer_preparation_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.native_hmmer_preparation_results import operation_catalog as hmmer_preparation_result_catalog
            return hmmer_preparation_result_catalog()
        if is_native_hmmer_target(target):
            from gene_annotation_episode.episodic_workflow.root.native_hmmer_results import operation_catalog as hmmer_result_catalog
            return hmmer_result_catalog()
        if is_native_blast_target(target):
            if self.native_blast_results is None:
                raise ValueError('native_blast_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.native_blast_results import operation_catalog as blast_result_catalog
            return blast_result_catalog()
        if is_native_infernal_target(target):
            if self.native_infernal_results is None:
                raise ValueError('native_infernal_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.native_infernal_results import operation_catalog as infernal_result_catalog
            return infernal_result_catalog()
        if is_native_infernal_preparation_target(target):
            if self.native_infernal_preparation_results is None:
                raise ValueError('native_infernal_preparation_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.native_infernal_preparation_results import operation_catalog as preparation_result_catalog
            return preparation_result_catalog()
        return native_result_operation_catalog()

    async def execute(self, context, tool_name, arguments, operation_key):
        if context.role != 'results' or context.run_id != self.run_id:
            raise ValueError('fixed_execution_context_required')
        try:
            catalog = {entry['name']: entry for entry in self.catalog(context)}
            if tool_name not in catalog:
                raise ValueError('execution_operation_not_available')
            arguments = checked(arguments, catalog[tool_name]['input_schema'], 'invalid_execution_operation_arguments')
            target = self._target(context)
            if self.local_file_sources.applies(context):
                return await self.local_file_sources.execute(context, target, tool_name, arguments, operation_key)
            if self.native_flux_balance_results is not None and self.native_flux_balance_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_flux_balance_results.execute(context, target, tool_name, arguments, operation_key)
            if self.native_blast_masking_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_blast_masking_results.execute(context, target, tool_name, arguments, operation_key)
            if self.native_blast_utility_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_blast_utility_results.execute(context, target, tool_name, arguments, operation_key)
            if self.native_fluorescence_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_fluorescence_results.execute(context, target, tool_name, arguments, operation_key)
            if self.native_expression_nmf_results is not None and self.native_expression_nmf_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_expression_nmf_results.execute(context, target, tool_name, arguments, operation_key)
            if self.atac_results is not None and self.atac_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.atac_results.execute(context, target, tool_name, arguments, operation_key)
            if self.native_chromatin_interaction_results is not None and self.native_chromatin_interaction_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_chromatin_interaction_results.execute(context, target, tool_name, arguments, operation_key)
            if self.native_genomic_overlap_results is not None and self.native_genomic_overlap_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_genomic_overlap_results.execute(context, target, tool_name, arguments, operation_key)
            if self.native_protein_structure_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_protein_structure_results.execute(context, target, tool_name, arguments, operation_key)
            if self._comparison_selector(plain(context.assignment)):
                return await self.rna_structure_comparison_results.execute(context, target, tool_name, arguments, operation_key)
            if is_native_rna_structure_target(target):
                return await self.native_rna_structure_results.execute(context, target, tool_name, arguments, operation_key)
            if is_standard_blast_database_target(target):
                return await self.native_blast_standard_database_results.execute(context, target, tool_name, arguments, operation_key)
            if is_native_blast_database_target(target):
                return await self.native_blast_database_results.execute(context, target, tool_name, arguments, operation_key)
            if target['resource_kind'] == 'api':
                return await self.api_execution.execute(context, tool_name, arguments, operation_key)
            if is_native_hmmer_preparation_target(target):
                return await self.native_hmmer_preparation_results.execute(context, target, tool_name, arguments, operation_key)
            if is_native_hmmer_target(target):
                return await self.native_hmmer_results.execute(context, target, tool_name, arguments, operation_key)
            if is_native_blast_target(target):
                return await self.native_blast_results.execute(context, target, tool_name, arguments, operation_key)
            if is_native_infernal_target(target):
                return await self.native_infernal_results.execute(context, target, tool_name, arguments, operation_key)
            if is_native_infernal_preparation_target(target):
                return await self.native_infernal_preparation_results.execute(context, target, tool_name, arguments, operation_key)
            return await self._execute_native_results(context, target, tool_name, arguments, operation_key)
        except (ValueError, TypeError) as error:
            from gene_annotation_episode.native_file_capture import NativeFileCaptureError
            if isinstance(error, NativeFileCaptureError) and self.local_file_sources.applies(context) and (error.code in {'retained_artifact_unavailable', 'retained_artifact_mismatch'}):
                raise
            return _outcome(code=str(error))
