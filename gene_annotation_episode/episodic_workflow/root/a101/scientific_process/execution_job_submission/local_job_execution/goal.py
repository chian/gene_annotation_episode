"""Private A101 launch_local goal."""
from __future__ import annotations
from .execution_contracts import plain

class OperationalGoal:

    def instructions(self, context):
        self.credit_kind(context.role)
        return self._delegate(context).instructions(self._practical_context(context))
