"""Private A102 Launch api operations."""
from __future__ import annotations
from .execution_contracts import ROLE_KINDS, _outcome, checked, launch_operation_catalog, native_result_operation_catalog, plain

class LaunchApiOperations:

    def catalog(self, context):
        if self.native_protein_structure_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.a102.native_protein_structure_results import operation_catalog as protein_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return protein_result_catalog()
        return launch_operation_catalog()

    async def execute(self, context, tool_name, arguments, operation_key):
        try:
            catalog = {entry['name']: entry for entry in self.catalog(context)}
            if tool_name not in catalog:
                raise ValueError('execution_operation_not_available')
            arguments = checked(arguments, catalog[tool_name]['input_schema'], 'invalid_execution_operation_arguments')
            return _outcome(self.initial_decision_context(context))
        except (ValueError, TypeError) as error:
            from gene_annotation_episode.episodic_workflow.root.a102.native_file_capture import NativeFileCaptureError
            if isinstance(error, NativeFileCaptureError) and self.local_file_sources.applies(context) and (error.code in {'retained_artifact_unavailable', 'retained_artifact_mismatch'}):
                raise
            return _outcome(code=str(error))
