"""Private A101 job_monitor internal summary."""
from __future__ import annotations

class OperationalSummary:

    def working_state(self, source):
        return {'role': 'job_monitor', 'assignment': self.assignment(source)}
