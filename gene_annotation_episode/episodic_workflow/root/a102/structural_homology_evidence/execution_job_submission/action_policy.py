"""Original private A102 launch action policy and configured callbacks."""
from __future__ import annotations
from .execution_contracts import plain

class LaunchActionPolicy:

    def permitted_common_actions(self, context):
        if self.native_protein_structure_results.applies(context):
            return ('tool',)
        if any((role == 'hpc' for role, _ in context.path)):
            return ('tool', 'child', 'redeliver_report')
        return ('tool', 'reason', 'child', 'wait', 'redeliver_report')

