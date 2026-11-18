"""Private A106 launch_api internal summary."""
from __future__ import annotations
from .execution_contracts import deepcopy, plain

class OperationalSummary:

    def _api_decision_summary(self, api, context, current_view=None):
        api.initialize(context)
        assignment, service, target = api._context(context)
        latest = {}
        for row in api._events(context.episode_id):
            latest[row['name']] = {'state': row['event']['state'], 'kind': row['event']['kind'], 'facts': row['event']['facts'], 'failure_code': row['event']['failure_code']}
        return {'api_service': service.service, 'api_request': assignment['request'], 'api_received_progress': latest, 'api_execution_completed': api._completion(context) is not None}

    def initial_decision_context(self, context):
        return {'execution_resource_capabilities': [self._resource_information(key) for key in self.resources], 'execution_initial_information': deepcopy(self.initial_information)}

    def decision_context(self, context, current_view):
        self.credit_kind(context.role)
        value = {'execution_assignment': plain(context.assignment), 'execution_progress': self.facts(context, {})}
        value.update(self.api_execution.decision_context(context, current_view))
        return value
