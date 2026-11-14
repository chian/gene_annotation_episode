"""Private A101 job_results internal summary."""
from __future__ import annotations

class OperationalSummary:

    def working_state(self, source):
        return {'role': 'job_results', 'assignment': self.assignment(source)}
