"""Private A101 job_launch internal summary."""
from __future__ import annotations

class OperationalSummary:

    def working_state(self, source):
        return {'role': 'job_launch', 'assignment': self.assignment(source)}
