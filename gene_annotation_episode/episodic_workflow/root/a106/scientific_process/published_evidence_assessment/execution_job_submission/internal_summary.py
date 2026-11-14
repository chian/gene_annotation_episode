"""Private A106 launch internal summary."""
from __future__ import annotations
from .execution_contracts import deepcopy, plain

class OperationalSummary:

    def initial_decision_context(self, context):
        return {'execution_resource_capabilities': [self._resource_information(key) for key in self.resources], 'execution_initial_information': deepcopy(self.initial_information)}

    def decision_context(self, context, current_view):
        self.credit_kind(context.role)
        value = {'execution_assignment': plain(context.assignment), 'execution_progress': self.facts(context, {})}
        return value
