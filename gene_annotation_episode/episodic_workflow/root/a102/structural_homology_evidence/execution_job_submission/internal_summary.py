"""Private A102 Launch internal summary."""
from __future__ import annotations
from .execution_contracts import deepcopy, plain

class LaunchInternalSummary:

    def _with_selected_execution_task(self, context, value):
        assignment = plain(context.assignment)
        requests = assignment.get('requests')
        if not isinstance(requests, dict) or not requests:
            return value
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
        return self._with_selected_execution_task(context, value)

