"""Private A103 resource internal summary."""
from __future__ import annotations
from .resource_contracts import plain

class ResourceInternalSummary:

    def decision_context(self, context, current_view):
        values = {'role': 'launch', 'assignment': plain(context.assignment), 'resource_capabilities': list(self.capabilities())}
        adapters = self.adapters.values()
        estimates = []
        for adapter in adapters:
            callback = getattr(adapter, 'decision_context', None)
            if callback is not None:
                estimates.extend(callback(context).get('resource_tool_estimates', []))
        values['resource_tool_estimates'] = estimates
        return values
