"""Private A103 native execution operations."""
from __future__ import annotations
from .contracts import canonical, json, plain

class NativeOperations:

    def _delegate(self, context):
        assignment = self._validate_request(plain(context.assignment))
        return self.api_execution if context.role == 'launch_api' else self._practical[assignment['resource_id']]

    def _practical_context(self, context):
        return context

    def initialize(self, context):
        self._check_parent_inputs(context)
        return self._delegate(context).initialize(context)

    def _check_parent_inputs(self, context):
        if len(context.path) < 2 or context.path[-2][0] != 'launch':
            return
        row = self.store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND path=?', (self.run_id, canonical(context.path[:-1]))).fetchone()
        if row is not None:
            original = self._launch(json.loads(row['request'])['message']['episode_assignment'])
            self._masking_inputs(context, plain(context.assignment))
            self._utility_inputs(context, plain(context.assignment))
            self._versions(original['immutable_input_versions'], context.scope, context=context)
            from gene_annotation_episode.episodic_workflow.root.a103.native_blast_database_result_publication import validate_native_job_inputs
            from gene_annotation_episode.episodic_workflow.root.a103.native_blast_standard_database_result_publication import validate_standard_blast_job_inputs
            validate_native_job_inputs(self.store, context, plain(context.assignment))
            validate_standard_blast_job_inputs(self.store, context, plain(context.assignment))
            return
        raise ValueError('execution_original_launch_assignment_unavailable')

    def state(self, context):
        """Expose the original practical state for its original resource role."""
        if context.role not in {'launch_local', 'launch_hpc'}:
            raise ValueError('practical_resource_role_required')
        return self._delegate(context).state(self._practical_context(context))

    def catalog(self, context):
        practical_context = self._practical_context(context)
        return self._delegate(context).catalog(practical_context)

    async def execute(self, context, tool_name, arguments, operation_key):
        self._check_parent_inputs(context)
        practical_context = self._practical_context(context)
        outcome = await self._delegate(context).execute(practical_context, tool_name, arguments, operation_key)
        return outcome
