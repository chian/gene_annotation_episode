"""Private A104 LocalExecution native state."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import _immutable
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import _read
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import digest
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class LocalExecutionNativeState:

    def initialize(self, context):
        self.local_file_sources.applies(context)
        self._check_parent_inputs(context)
        return self._delegate(context).initialize(context)

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
