"""Action policy for this private binding's selected launch role."""
from __future__ import annotations
from .contracts import plain

class LaunchActionPolicy:

    def permitted_common_actions(self, context):
        if any((role == 'hpc' for role, _ in context.path)):
            return ('tool', 'child', 'redeliver_report')
        return ('tool', 'reason', 'child', 'wait', 'redeliver_report')

