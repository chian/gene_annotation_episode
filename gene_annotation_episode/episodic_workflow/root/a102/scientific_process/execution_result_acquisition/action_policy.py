"""Private A102 Results action policy."""
from __future__ import annotations
from .execution_contracts import plain

class ResultsActionPolicy:

    def permitted_common_actions(self, context):
        if self.native_protein_structure_results.applies(context):
            return ('tool',)
        target = self._target(context)
        if target['resource_kind'] == 'api' and target['assignment']['version'] == 'api_service_assignment_v1':
            return ('tool', 'wait')
        return ('tool',)
