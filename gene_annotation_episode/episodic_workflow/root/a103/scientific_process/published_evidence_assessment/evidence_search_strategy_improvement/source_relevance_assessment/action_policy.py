"""This selected source role's action policy and original receiving-role validation."""
from __future__ import annotations
from .source_contracts import ROLES

class SourceActionPolicy:

    @staticmethod
    def _role(role):
        if role not in ROLES:
            raise ValueError('unsupported_literature_role:' + str(role))
        return role

    def permitted_common_actions(self, context):
        self._role(context.role)
        return ('tool', 'child', 'redeliver_report')

