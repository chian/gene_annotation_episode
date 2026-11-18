"""Original private A102 launch_api action policy and configured callbacks."""
from __future__ import annotations
from .execution_contracts import plain

class APIActionPolicy:

    def permitted_common_actions(self, context):
        if self.native_protein_structure_results.applies(context):
            return ('tool',)
        assignment = self._validate_request(plain(context.assignment))
        if assignment['version'] == 'api_service_assignment_v1':
            return ('tool', 'wait')
        return ('tool',)
