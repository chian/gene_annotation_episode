"""Private A104 Results work operations."""
from __future__ import annotations
from .action_outcome import _outcome
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import checked
from gene_annotation_episode.episodic_workflow.root.a104.native_blast_database_acquisition import is_native_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a104.native_blast_acquisition import is_native_blast_target
from gene_annotation_episode.episodic_workflow.root.a104.native_hmmer_preparation_acquisition import is_native_hmmer_preparation_target
from gene_annotation_episode.episodic_workflow.root.a104.native_hmmer_acquisition import is_native_hmmer_target
from gene_annotation_episode.episodic_workflow.root.a104.native_blast_standard_database_acquisition import is_standard_blast_database_target
from .result_operations import native_result_operation_catalog
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class ResultsWorkOperations:

    def catalog(self, context):
        if self.native_blast_masking_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_masking_result_records import operation_catalog as masking_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return masking_result_catalog()
        if self.native_blast_utility_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_utility_result_records import operation_catalog as utility_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return utility_result_catalog()
        target = self._target(context)
        if is_standard_blast_database_target(target):
            self._selector(plain(context.assignment), target)
            from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_standard_database_result_records import operation_catalog as database_catalog
            return database_catalog()
        if is_native_blast_database_target(target):
            selector = self._selector(plain(context.assignment), target)
            from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_database_result_records import operation_catalog as database_catalog
            return database_catalog(selector)
        if target['resource_kind'] == 'api':
            return self.api_execution.catalog(context)
        if is_native_hmmer_preparation_target(target):
            if self.native_hmmer_preparation_results is None:
                raise ValueError('native_hmmer_preparation_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a104.library.native_hmmer_preparation_result_records import operation_catalog as hmmer_preparation_result_catalog
            return hmmer_preparation_result_catalog()
        if is_native_hmmer_target(target):
            from gene_annotation_episode.episodic_workflow.root.a104.library.native_hmmer_result_records import operation_catalog as hmmer_result_catalog
            return hmmer_result_catalog()
        if is_native_blast_target(target):
            if self.native_blast_results is None:
                raise ValueError('native_blast_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_result_records import operation_catalog as blast_result_catalog
            return blast_result_catalog()
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
            return await self._execute_native_results(context, target, tool_name, arguments, operation_key)
        except (ValueError, TypeError) as error:
            from gene_annotation_episode.episodic_workflow.root.a104.native_file_capture import NativeFileCaptureError
            if isinstance(error, NativeFileCaptureError) and self.local_file_sources.applies(context) and (error.code in {'retained_artifact_unavailable', 'retained_artifact_mismatch'}):
                raise
            return _outcome(code=str(error))
