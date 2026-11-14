"""Private literature_targeted yield behavior for A101."""
from __future__ import annotations

class LiteratureYield:
    def continuation_task(self, context):
        self._role(context.role)
        return None

    def yield_controller(self, context, initial_credit, epoch):
        self._role(context.role)
        return None
