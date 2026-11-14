"""Private A104 Results result state."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.a104_homology_execution import BLAST_GRADED_RETURN_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a104.a104_homology_execution import BLAST_GRADED_RETURN_SOURCE
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import _immutable
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import _read
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import digest
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class ResultsResultState:

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
