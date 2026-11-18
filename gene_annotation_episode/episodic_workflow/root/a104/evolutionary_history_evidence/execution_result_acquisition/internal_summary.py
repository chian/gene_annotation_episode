"""Private A104 Results internal summary."""
from __future__ import annotations
from .binding_roles import KINDS
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class ResultsInternalSummary:

    def _with_selected_execution_task(self, context, value):
        assignment = plain(context.assignment)
        target = self._target(context) if self.local_file_sources.applies(context) else value.get('execution_target', {})
        requests = {target.get('resource_id'): target.get('assignment', {})}
        callback = getattr(self.services, 'scientific_parent_task', None)
        parent = None if callback is None else callback(context)
        if parent is None:
            return value
        selected = []
        for resource_id, request in requests.items():
            if not isinstance(request, dict) or resource_id not in self.resources:
                return value
            kind = KINDS[self.resources[resource_id]['kind']]
            if kind == 'api':
                if request.get('service') != 'ebi_hmmer':
                    return value
                job = deepcopy(request)
            else:
                jobs = request.get('requested_job', {})
                supported = ('native_blast', 'native_blast_masking', 'native_blast_utility', 'native_blast_database', 'native_blast_standard_database', 'native_hmmer', 'native_hmmer_preparation')
                chosen = [name for name in supported if isinstance(jobs.get(name), dict)]
                if len(chosen) != 1:
                    return value
                name = chosen[0]
                job = deepcopy(jobs[name])
                if name in {'native_hmmer', 'native_hmmer_preparation'}:
                    from gene_annotation_episode.episodic_workflow.root.a104.native_profile_presentation import native_profile_scientific_job_view
                    job = native_profile_scientific_job_view(job)
            selected.append({'resource_id': resource_id, 'resource_kind': kind, 'endpoint': deepcopy(request.get('endpoint')), 'constraints': deepcopy(request.get('constraints', {})), 'job': job, 'resource': self._resource_information(resource_id)})
        value['selected_execution_task'] = deepcopy({'version': 'selected_execution_task_v1', 'scientific_question': parent['scientific_question'], 'selected_tool_info': parent['selected_tool_info'], 'requests': selected, 'constraints': assignment.get('constraints', {}), 'selector': assignment.get('selector'), 'result_description': value.get('execution_target_description')})
        return value

    def decision_context(self, context, current_view):
        value = {'execution_assignment': plain(context.assignment), 'execution_progress': self.facts(context, {})}
        assignment = plain(context.assignment)
        if self.local_file_sources.applies(context):
            from gene_annotation_episode.episodic_workflow.root.a104.local_file_capture_results import ORIGIN
            value['execution_target'] = {'resource_kind': 'local', 'files': deepcopy(assignment['selector']['files'])}
            value['execution_target_description'] = {'status_operations': ['execution.results.status'], 'acquisition_operations': ['execution.results.collect'], 'provenance': deepcopy(ORIGIN)}
            return self._with_selected_execution_task(context, value)
        value['execution_target'] = self._target(context)
        value['execution_target_description'] = self.job_progress_provider.targets.describe_target(value['execution_target']['handle'], context.scope, selector=assignment['selector'])
        from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_data_host import is_bvbrc_request
        if value['execution_target']['resource_kind'] == 'api' and is_bvbrc_request(value['execution_target']['assignment'].get('request')):
            value['own_bvbrc_values'] = self.api_execution.bvbrc_data.own_values(context)
        return self._with_selected_execution_task(context, value)
