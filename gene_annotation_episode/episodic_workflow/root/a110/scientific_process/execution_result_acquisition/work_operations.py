"""Private A110 Results work_operations"""
from __future__ import annotations
from .binding_roles import ROLE_KINDS
from .action_outcome import _outcome
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import checked
from .result_records import native_result_operation_catalog
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain

class ResultsWorkOperations:

    def catalog(self, context):
        if self.native_flux_balance_results is not None and self.native_flux_balance_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.a110.native_flux_balance_results import operation_catalog as fba_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return fba_result_catalog()
        target = self._target(context)
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
            if self.native_flux_balance_results is not None and self.native_flux_balance_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_flux_balance_results.execute(context, target, tool_name, arguments, operation_key)
            return await self._execute_native_results(context, target, tool_name, arguments, operation_key)
        except (ValueError, TypeError) as error:
            from gene_annotation_episode.episodic_workflow.root.a110.native_file_capture import NativeFileCaptureError
            if isinstance(error, NativeFileCaptureError) and self.local_file_sources.applies(context) and (error.code in {'retained_artifact_unavailable', 'retained_artifact_mismatch'}):
                raise
            return _outcome(code=str(error))
