"""Private A104 Launch native receipt support."""
from __future__ import annotations
from .contracts import plain

class LaunchNativeReceiptSupport:

    def _delegate(self, context):
        assignment = self._validate_request(plain(context.assignment))
        context.role
        return self._practical[assignment['resource_id']]

    def _practical_context(self, context):
        return context
