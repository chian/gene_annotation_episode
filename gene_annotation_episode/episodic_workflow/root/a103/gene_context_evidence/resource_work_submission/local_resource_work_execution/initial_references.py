"""Own the genuine cross-context initial reference hook for Resource bindings."""
from __future__ import annotations
from .resource_contracts import Mapping, RESULTS_VERSION

class ResourceInitialReferences:

    def initial_references(self, context):
        if context.role != 'results':
            return []
        callback = getattr(self._adapter(context.assignment), 'initial_references', None)
        return [] if callback is None else callback(context)
