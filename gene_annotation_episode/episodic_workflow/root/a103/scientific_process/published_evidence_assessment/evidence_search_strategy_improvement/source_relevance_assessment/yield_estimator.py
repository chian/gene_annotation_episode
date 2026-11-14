"""Private A103 literature_search yield."""
from __future__ import annotations

class SourceInvestigationYield:

    def continuation_task(self, context):
        self._role('literature_search')
        return None

    def yield_controller(self, context, initial_credit, epoch):
        self._role('literature_search')
        return None
