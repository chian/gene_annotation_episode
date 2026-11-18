"""Action policy for this private binding's selected launch_hpc role."""
from __future__ import annotations
from .contracts import plain

class NativeActionPolicy:

    def permitted_common_actions(self, context):
        return ('tool',)

