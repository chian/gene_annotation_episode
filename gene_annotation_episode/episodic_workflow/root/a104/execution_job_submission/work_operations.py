"""Private A104 Launch work operations."""
from __future__ import annotations
from .action_outcome import _outcome
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import checked
from .resource_operations import launch_operation_catalog
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class LaunchWorkOperations:

    def catalog(self, context):
        if self.native_blast_masking_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_masking_result_records import operation_catalog as masking_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return masking_result_catalog()
        if self.native_blast_utility_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_utility_result_records import operation_catalog as utility_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return utility_result_catalog()
        return launch_operation_catalog()

    async def execute(self, context, tool_name, arguments, operation_key):
        try:
            catalog = {entry['name']: entry for entry in self.catalog(context)}
            if tool_name not in catalog:
                raise ValueError('execution_operation_not_available')
            arguments = checked(arguments, catalog[tool_name]['input_schema'], 'invalid_execution_operation_arguments')
            return _outcome(self.initial_decision_context(context))
        except (ValueError, TypeError) as error:
            from gene_annotation_episode.episodic_workflow.root.a104.native_file_capture import NativeFileCaptureError
            if isinstance(error, NativeFileCaptureError) and self.local_file_sources.applies(context) and (error.code in {'retained_artifact_unavailable', 'retained_artifact_mismatch'}):
                raise
            return _outcome(code=str(error))
