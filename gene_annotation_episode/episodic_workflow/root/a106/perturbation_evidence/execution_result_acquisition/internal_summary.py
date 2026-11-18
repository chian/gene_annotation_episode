"""Private A106 results internal summary."""
from __future__ import annotations
from .execution_contracts import deepcopy, plain

class OperationalSummary:

    def initial_decision_context(self, context):
        return {'execution_resource_capabilities': [self._resource_information(key) for key in self.resources], 'execution_initial_information': deepcopy(self.initial_information)}

    def decision_context(self, context, current_view):
        self.credit_kind(context.role)
        value = {'execution_assignment': plain(context.assignment), 'execution_progress': self.facts(context, {})}
        value['execution_target'] = self._target(context)
        value['execution_target_description'] = self.job_progress_provider.targets.describe_target(context.assignment['handoff_ref'], context.scope, selector=plain(context.assignment)['selector'])
        return value
