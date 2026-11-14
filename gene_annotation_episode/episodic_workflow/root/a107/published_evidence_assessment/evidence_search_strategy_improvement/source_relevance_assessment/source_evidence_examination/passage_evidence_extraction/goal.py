"""Private A107 goal."""
from __future__ import annotations
from .contracts import _ROLE_INSTRUCTIONS

class LiteratureGoal:

    def instructions(self, context):
        self._role(context.role)
        return _ROLE_INSTRUCTIONS['literature_targeted'] + '\nInvestigate reported partner removal, addback and coexpression evidence. Preserve the original molecule and partner roles, normalization, nonpartner conditions, physical measurement identity, source units and uncertainty. Condition-specific dependence does not establish universal necessity, genomic presence, target correspondence or annotation credit. A search or read earns no scientific credit by itself.'
