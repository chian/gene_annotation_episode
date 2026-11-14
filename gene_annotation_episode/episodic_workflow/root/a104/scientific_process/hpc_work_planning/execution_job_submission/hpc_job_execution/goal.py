"""Private A104 HPCExecution goal."""
from __future__ import annotations

class HPCExecutionGoal:

    def instructions(self, context):
        return self._delegate(context).instructions(self._practical_context(context))
