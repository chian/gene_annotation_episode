"""Private A103 launch operations."""
from __future__ import annotations
from .contracts import BLAST_GRADED_REQUEST_VERSION, BLAST_GRADED_RETURN_SCHEMA, BLAST_GRADED_RETURN_SOURCE, ROLE_KINDS, _outcome, canonical, checked, is_native_blast_database_target, is_native_blast_target, is_native_hmmer_preparation_target, is_native_hmmer_target, is_standard_blast_database_target, json, launch_operation_catalog, native_result_operation_catalog, plain

class LaunchOperations:

    def _delegate(self, context):
        assignment = self._validate_request(plain(context.assignment))
        return self.api_execution if context.role == 'launch_api' else self._practical[assignment['resource_id']]

    def _practical_context(self, context):
        return context

    def initialize(self, context):
        if self.local_file_sources.applies(context):
            target = self._target(context)
            self.local_file_sources.selector(plain(context.assignment), target, validate_paths=False)
            return self._result_directory(context)
        value = self._launch(plain(context.assignment), scope=context.scope)
        for resource_id, request in value['requests'].items():
            if request.get('version') == BLAST_GRADED_REQUEST_VERSION:
                self._blast_launch_requirement(request, resource_id, context.scope)
        for request in value['requests'].values():
            self._masking_inputs(context, request)
            self._utility_inputs(context, request)
        self._versions(value['immutable_input_versions'], context.scope, context=context)

    def catalog(self, context):
        if self.native_blast_masking_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.a103.native_blast_masking_results import operation_catalog as masking_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return masking_result_catalog()
        if self.native_blast_utility_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.a103.native_blast_utility_results import operation_catalog as utility_result_catalog
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
            from gene_annotation_episode.episodic_workflow.root.a103.native_file_capture import NativeFileCaptureError
            if isinstance(error, NativeFileCaptureError) and self.local_file_sources.applies(context) and (error.code in {'retained_artifact_unavailable', 'retained_artifact_mismatch'}):
                raise
            return _outcome(code=str(error))
