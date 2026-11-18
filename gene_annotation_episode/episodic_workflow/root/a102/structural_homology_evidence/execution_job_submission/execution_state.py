"""Private A102 Launch execution state."""
from __future__ import annotations
from .execution_contracts import ROLE_KINDS, _immutable, _read, canonical, digest, is_native_protein_structure_target, plain

class LaunchExecutionState:

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
        from gene_annotation_episode.episodic_workflow.root.a102.protein_structure_operands import validate_protein_structure_job_inputs
        for request in value['requests'].values():
            validate_protein_structure_job_inputs(self.store, context, request, returns=self.native_protein_structure_returns)
        self._versions(value['immutable_input_versions'], context.scope, context=context)
        return

    def _result_directory(self, context, *, create=True):
        if type(create) is not bool:
            raise TypeError('execution_results_directory_create_boolean_required')
        directory = self.directory / 'execution-results' / digest([context.run_id, context.episode_id])
        manifest = {'run_id': context.run_id, 'episode_id': context.episode_id, 'assignment': plain(context.assignment), 'scope': plain(context.scope)}
        if create:
            directory.mkdir(parents=True, exist_ok=True)
            _immutable(directory / 'assignment.json', manifest)
        else:
            try:
                existing = _read(directory / 'assignment.json')
            except FileNotFoundError as error:
                raise ValueError('execution_results_assignment_control_missing') from error
            if canonical(existing) != canonical(manifest):
                raise ValueError('practical_immutable_record_conflict')
        return directory
