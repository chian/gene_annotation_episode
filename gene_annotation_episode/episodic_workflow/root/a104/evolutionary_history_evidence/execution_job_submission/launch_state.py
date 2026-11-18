"""Private A104 Launch launch state."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.a104_homology_execution import BLAST_GRADED_REQUEST_VERSION
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import _immutable
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import _read
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import digest
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class LaunchLaunchState:

    def initialize(self, context):
        self.local_file_sources.applies(context)
        value = self._launch(plain(context.assignment), scope=context.scope)
        for resource_id, request in value['requests'].items():
            if request.get('version') == BLAST_GRADED_REQUEST_VERSION:
                self._blast_launch_requirement(request, resource_id, context.scope)
        for request in value['requests'].values():
            self._masking_inputs(context, request)
            self._utility_inputs(context, request)
        self._versions(value['immutable_input_versions'], context.scope, context=context)

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
