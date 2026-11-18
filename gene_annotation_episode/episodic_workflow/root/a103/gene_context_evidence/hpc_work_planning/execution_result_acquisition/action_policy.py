"""Selected A103 Results action policy; own saved-path contexts only."""
from __future__ import annotations

class ResultsActionPolicy:

    def permitted_common_actions(self, context):
        target = self._target(context)
        if target['resource_kind'] == 'api' and target['assignment']['version'] == 'api_service_assignment_v1':
            return ('tool', 'wait')
        return ('tool',)
