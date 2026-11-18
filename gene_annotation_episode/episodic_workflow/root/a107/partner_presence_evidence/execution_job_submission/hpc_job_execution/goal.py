from __future__ import annotations

class NativeGoal:

    def instructions(self, context):
        return self._delegate(context).instructions(self._practical_context(context))
