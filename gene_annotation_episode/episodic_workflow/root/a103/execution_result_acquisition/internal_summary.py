"""Private A103 Results internal summary."""
from __future__ import annotations
from .execution_contracts import KINDS, deepcopy, plain

class ResultsInternalSummary:

    def decision_context(self, context, current_view):
        value = {'execution_assignment': plain(context.assignment), 'execution_progress': self.facts(context, {})}
        assignment = plain(context.assignment)
        if self.local_file_sources.applies(context):
            from gene_annotation_episode.episodic_workflow.root.a103.local_file_capture_results import ORIGIN
            value['execution_target'] = {'resource_kind': 'local', 'files': deepcopy(assignment['selector']['files'])}
            value['execution_target_description'] = {'status_operations': ['execution.results.status'], 'acquisition_operations': ['execution.results.collect'], 'provenance': deepcopy(ORIGIN)}
            return self._with_selected_execution_task(context, value)
        value['execution_target'] = self._target(context)
        value['execution_target_description'] = self.job_progress_provider.targets.describe_target(value['execution_target']['handle'], context.scope, selector=assignment['selector'])
        from gene_annotation_episode.episodic_workflow.root.a103.bvbrc_data_host import is_bvbrc_request
        if value['execution_target']['resource_kind'] == 'api' and is_bvbrc_request(value['execution_target']['assignment'].get('request')):
            value['own_bvbrc_values'] = self.api_execution.bvbrc_data.own_values(context)
        return self._with_selected_execution_task(context, value)
