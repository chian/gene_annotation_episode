"""Private A104 LocalExecution goal."""
from __future__ import annotations

class LocalExecutionGoal:

    def instructions(self, context):
        return self._delegate(context).instructions(self._practical_context(context))
