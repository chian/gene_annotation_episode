"""Private A103 API job operations."""
from __future__ import annotations
from .contracts import BLAST_GRADED_REQUEST_VERSION, BLAST_GRADED_RETURN_SCHEMA, BLAST_GRADED_RETURN_SOURCE, ROLE_KINDS, _outcome, canonical, checked, is_native_blast_database_target, is_native_blast_target, is_native_hmmer_preparation_target, is_native_hmmer_target, is_standard_blast_database_target, json, launch_operation_catalog, native_result_operation_catalog, plain

class APIJobOperations:

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
        self._check_parent_inputs(context)
        return self._delegate(context).initialize(context)

    def _check_parent_inputs(self, context):
        if len(context.path) < 2 or context.path[-2][0] != 'launch':
            return
        row = self.store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND path=?', (self.run_id, canonical(context.path[:-1]))).fetchone()
        if row is not None:
            original = self._launch(json.loads(row['request'])['message']['episode_assignment'])
            self._validate_blast_api_parent_request(original, plain(context.assignment), context.scope)
            self._masking_inputs(context, plain(context.assignment))
            self._utility_inputs(context, plain(context.assignment))
            self._versions(original['immutable_input_versions'], context.scope, context=context)
            from gene_annotation_episode.episodic_workflow.root.a103.native_blast_database_result_publication import validate_native_job_inputs
            from gene_annotation_episode.episodic_workflow.root.a103.native_blast_standard_database_result_publication import validate_standard_blast_job_inputs
            validate_native_job_inputs(self.store, context, plain(context.assignment))
            validate_standard_blast_job_inputs(self.store, context, plain(context.assignment))
            return
        raise ValueError('execution_original_launch_assignment_unavailable')

    def catalog(self, context):
        if self.native_blast_masking_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.a103.native_blast_masking_results import operation_catalog as masking_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return masking_result_catalog()
        if self.native_blast_utility_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.a103.native_blast_utility_results import operation_catalog as utility_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return utility_result_catalog()
        practical_context = self._practical_context(context)
        return self._delegate(context).catalog(practical_context)

    async def execute(self, context, tool_name, arguments, operation_key):
        self._check_parent_inputs(context)
        practical_context = self._practical_context(context)
        outcome = await self._delegate(context).execute(practical_context, tool_name, arguments, operation_key)
        return outcome

