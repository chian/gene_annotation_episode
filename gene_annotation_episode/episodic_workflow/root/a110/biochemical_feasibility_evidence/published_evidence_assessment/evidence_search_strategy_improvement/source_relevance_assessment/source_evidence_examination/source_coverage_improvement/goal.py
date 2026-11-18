"""Private A110 goal."""
from __future__ import annotations
from .contracts import _ROLE_INSTRUCTIONS

class LiteratureGoal:

    def instructions(self, context):
        self._role(context.role)
        return _ROLE_INSTRUCTIONS['literature_ordered'] + '\nInvestigate the reported reaction and resource evidence for this source. Preserve source identity, exact conditions, units, uncertainty and byte anchors. Keep reported product ratios, resource budgets and named predictions distinct. Unknown replication, calibration, alternative reactions and resource completeness remain unresolved. A search or read earns no scientific credit by itself.'
