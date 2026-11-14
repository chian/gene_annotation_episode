"""Private A103 Results execution state."""
from __future__ import annotations
from .execution_contracts import BLAST_GRADED_REQUEST_VERSION, BLAST_GRADED_RETURN_SCHEMA, BLAST_GRADED_RETURN_SOURCE, ROLE_KINDS, _immutable, _read, canonical, digest, plain

class ResultsExecutionState:

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
        target = self._target(context)
        self._selector(plain(context.assignment), target)
        required = self._blast_target_requirement(target, context.scope)
        if required is not None:
            schema = plain(context.request)['report_contract']['measurements']['schema']
            if not any((node.get('x-source') == BLAST_GRADED_RETURN_SOURCE and node == BLAST_GRADED_RETURN_SCHEMA for node in schema.get('properties', {}).values())):
                raise ValueError('blast_grader_typed_return_required')
        if self._masking_selector(plain(context.assignment)) or self._utility_selector(plain(context.assignment)):
            self.initial_references(context)
        if target['resource_kind'] == 'api':
            return self.api_execution.initialize(context)
        self._result_directory(context)

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
