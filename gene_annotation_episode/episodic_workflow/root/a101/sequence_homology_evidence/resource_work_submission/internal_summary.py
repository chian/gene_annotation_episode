"""Private A101 launch internal summary."""
from __future__ import annotations
from .execution_contracts import plain

class OperationalSummary:

    def decision_context(self, context, current_view):
        self.credit_kind(context.role)
        values = {'role': 'launch', 'assignment': plain(context.assignment), 'resource_capabilities': list(self.capabilities())}
        adapters = self.adapters.values()
        estimates = []
        for adapter in adapters:
            callback = getattr(adapter, 'decision_context', None)
            if callback is not None:
                estimates.extend(callback(context).get('resource_tool_estimates', []))
        values['resource_tool_estimates'] = estimates
        return values
