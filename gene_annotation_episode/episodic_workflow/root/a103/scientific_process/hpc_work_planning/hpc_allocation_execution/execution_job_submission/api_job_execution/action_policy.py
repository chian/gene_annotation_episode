"""Action policy for this private binding's selected launch_api role."""
from __future__ import annotations
from .contracts import plain

class APIJobActionPolicy:

    def permitted_common_actions(self, context):
        assignment = self._validate_request(plain(context.assignment))
        if assignment['version'] == 'api_service_assignment_v1':
            return ('tool', 'wait')
        return ('tool',)

