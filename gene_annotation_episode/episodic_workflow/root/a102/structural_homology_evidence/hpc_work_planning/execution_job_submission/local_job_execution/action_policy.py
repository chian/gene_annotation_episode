"""Original private A102 launch_local action policy and configured callbacks."""
from __future__ import annotations

class NativeActionPolicy:

    def permitted_common_actions(self, context):
        return ('tool',)
