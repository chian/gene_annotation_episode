"""Private A102 Results acquisition operations."""
from __future__ import annotations
from .execution_contracts import ROLE_KINDS, _outcome, checked, launch_operation_catalog, native_result_operation_catalog, plain

class ResultsAcquisitionOperations:

    def catalog(self, context):
        if self.native_protein_structure_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.a102.native_protein_structure_results import operation_catalog as protein_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return protein_result_catalog()
        target = self._target(context)
        self._selector(plain(context.assignment), target)
        if target['resource_kind'] == 'api':
            return self.api_execution.catalog(context)
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
            if self.native_protein_structure_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_protein_structure_results.execute(context, target, tool_name, arguments, operation_key)
            if target['resource_kind'] == 'api':
                return await self.api_execution.execute(context, tool_name, arguments, operation_key)
            return await self._execute_native_results(context, target, tool_name, arguments, operation_key)
        except (ValueError, TypeError) as error:
            from gene_annotation_episode.episodic_workflow.root.a102.native_file_capture import NativeFileCaptureError
            if isinstance(error, NativeFileCaptureError) and self.local_file_sources.applies(context) and (error.code in {'retained_artifact_unavailable', 'retained_artifact_mismatch'}):
                raise
            return _outcome(code=str(error))
