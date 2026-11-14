"""Private homology monitoring internal summary."""
from __future__ import annotations

class MonitorSummary:

    def working_state(self, source):
        return {'role': source.path[-1][0], 'assignment': self.assignment(source)}
