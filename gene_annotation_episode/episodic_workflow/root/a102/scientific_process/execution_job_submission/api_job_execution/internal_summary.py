"""Private A102 API internal summary."""
from __future__ import annotations
from .execution_contracts import deepcopy, plain

class APIInternalSummary:

    def _with_selected_execution_task(self, context, value):
        assignment = plain(context.assignment)
        return value

    def decision_context(self, context, current_view):
        value = {'execution_assignment': plain(context.assignment), 'execution_progress': self.facts(context, {})}
        callback = getattr(self.api_execution, 'decision_context', None)
        if callback is not None:
            value.update(callback(context, current_view))
        return self._with_selected_execution_task(context, value)

