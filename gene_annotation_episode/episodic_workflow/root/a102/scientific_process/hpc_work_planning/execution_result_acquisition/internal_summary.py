"""Private A102 Results internal summary."""
from __future__ import annotations
from .execution_contracts import deepcopy, plain

class ResultsInternalSummary:

    def _with_selected_execution_task(self, context, value):
        assignment = plain(context.assignment)
        target = value.get('execution_target', {})
        requests = {target.get('resource_id'): target.get('assignment', {})}
        selected = []
        for resource_id, request in requests.items():
            if not isinstance(request, dict) or request.get('resource_kind') != 'local' or (not isinstance(request.get('requested_job', {}).get('native_protein_structure'), dict)):
                return value
            selected.append({'resource_id': resource_id, 'resource_kind': request['resource_kind'], 'endpoint': deepcopy(request.get('endpoint')), 'constraints': deepcopy(request.get('constraints', {})), 'job': deepcopy(request['requested_job']['native_protein_structure']), 'resource': self._resource_information(resource_id)})
        callback = getattr(self.services, 'scientific_parent_task', None)
        parent = None if callback is None else callback(context)
        if parent is None:
            return value
        value['selected_execution_task'] = deepcopy({'version': 'selected_execution_task_v1', 'scientific_question': parent['scientific_question'], 'selected_tool_info': parent['selected_tool_info'], 'requests': selected, 'constraints': assignment.get('constraints', {}), 'selector': assignment.get('selector'), 'result_description': value.get('execution_target_description')})
        return value

    def decision_context(self, context, current_view):
        value = {'execution_assignment': plain(context.assignment), 'execution_progress': self.facts(context, {})}
        assignment = plain(context.assignment)
        if self.local_file_sources.applies(context):
            from gene_annotation_episode.episodic_workflow.root.a102.local_file_capture_results import ORIGIN
            value['execution_target'] = {'resource_kind': 'local', 'files': deepcopy(assignment['selector']['files'])}
            value['execution_target_description'] = {'status_operations': ['execution.results.status'], 'acquisition_operations': ['execution.results.collect'], 'provenance': deepcopy(ORIGIN)}
            return self._with_selected_execution_task(context, value)
        retained = self._retained_protein_result(context, assignment, context.scope)
        if retained is None:
            value['execution_target'] = self._target(context)
            value['execution_target_description'] = self.job_progress_provider.targets.describe_target(value['execution_target']['handle'], context.scope, selector=assignment['selector'])
        else:
            from gene_annotation_episode.episodic_workflow.root.a102.protein_structure_execution_information import describe_protein_structure_result
            value['execution_target'] = retained['body']['intent']['target']
            called = retained['body']['handoff_proof']['body']['receipt']['tool_name']
            value['execution_target_description'] = describe_protein_structure_result(value['execution_target'], called_operation=called, selector=assignment['selector'])
        return self._with_selected_execution_task(context, value)
