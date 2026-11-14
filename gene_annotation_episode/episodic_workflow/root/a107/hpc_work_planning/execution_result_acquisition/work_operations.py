"""Private A107 Results work_operations"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.library.execution_resource_information import execution_capability_information
from .binding_roles import ROLE_KINDS
from .action_outcome import _outcome
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import checked
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_acquisition import is_native_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_acquisition import is_native_blast_target
from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_preparation_acquisition import is_native_hmmer_preparation_target
from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_acquisition import is_native_hmmer_target
from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_preparation_acquisition import is_native_infernal_preparation_target
from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_acquisition import is_native_infernal_target
from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_acquisition import is_native_rna_structure_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_acquisition import is_standard_blast_database_target
import gene_annotation_episode.episodic_workflow.root.a107.hpc_work_planning.execution_result_acquisition.resource_information as _retained_resource_information_import_effect
from .result_records import native_result_operation_catalog
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain

class ResultsWorkOperations:

    def catalog(self, context):
        if self.native_expression_nmf_results is not None and self.native_expression_nmf_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.a107.native_expression_nmf_results import operation_catalog as nmf_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return nmf_result_catalog()
        if self.native_blast_masking_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_masking_results import operation_catalog as masking_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return masking_result_catalog()
        if self.native_blast_utility_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_utility_results import operation_catalog as utility_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return utility_result_catalog()
        target = self._target(context)
        if self._comparison_selector(plain(context.assignment)):
            self._selector(plain(context.assignment), target)
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_results import operation_catalog as comparison_catalog
            return comparison_catalog()
        if is_native_rna_structure_target(target):
            self._selector(plain(context.assignment), target)
            from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_results import operation_catalog as rna_result_catalog
            return rna_result_catalog()
        if is_standard_blast_database_target(target):
            self._selector(plain(context.assignment), target)
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_results import operation_catalog as database_catalog
            return database_catalog()
        if is_native_blast_database_target(target):
            selector = self._selector(plain(context.assignment), target)
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_results import operation_catalog as database_catalog
            return database_catalog(selector)
        if target['resource_kind'] == 'api':
            return self.api_execution.catalog(context)
        if is_native_hmmer_preparation_target(target):
            if self.native_hmmer_preparation_results is None:
                raise ValueError('native_hmmer_preparation_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_preparation_results import operation_catalog as hmmer_preparation_result_catalog
            return hmmer_preparation_result_catalog()
        if is_native_hmmer_target(target):
            from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_results import operation_catalog as hmmer_result_catalog
            return hmmer_result_catalog()
        if is_native_blast_target(target):
            if self.native_blast_results is None:
                raise ValueError('native_blast_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_results import operation_catalog as blast_result_catalog
            return blast_result_catalog()
        if is_native_infernal_target(target):
            if self.native_infernal_results is None:
                raise ValueError('native_infernal_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_results import operation_catalog as infernal_catalog
            return infernal_catalog()
        if is_native_infernal_preparation_target(target):
            if self.native_infernal_preparation_results is None:
                raise ValueError('native_infernal_preparation_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_preparation_results import operation_catalog as preparation_catalog
            return preparation_catalog()
        return native_result_operation_catalog()

    async def execute(self, context, tool_name, arguments, operation_key):
        try:
            catalog = {entry['name']: entry for entry in self.catalog(context)}
            if tool_name not in catalog:
                raise ValueError('execution_operation_not_available')
            arguments = checked(arguments, catalog[tool_name]['input_schema'], 'invalid_execution_operation_arguments')
            target = self._target(context)
            if self.local_file_sources.applies(context):
                return await self.local_file_sources.execute(context, target, tool_name, arguments, operation_key)
            if self.native_blast_masking_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_blast_masking_results.execute(context, target, tool_name, arguments, operation_key)
            if self.native_blast_utility_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_blast_utility_results.execute(context, target, tool_name, arguments, operation_key)
            if self.native_expression_nmf_results is not None and self.native_expression_nmf_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_expression_nmf_results.execute(context, target, tool_name, arguments, operation_key)
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
            from gene_annotation_episode.episodic_workflow.root.a107.native_file_capture import NativeFileCaptureError
            if isinstance(error, NativeFileCaptureError) and self.local_file_sources.applies(context) and (error.code in {'retained_artifact_unavailable', 'retained_artifact_mismatch'}):
                raise
            return _outcome(code=str(error))
