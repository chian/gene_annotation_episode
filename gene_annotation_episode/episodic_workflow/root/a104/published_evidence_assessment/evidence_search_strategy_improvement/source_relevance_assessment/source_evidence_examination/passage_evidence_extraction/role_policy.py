"""Own literature_targeted admission, common actions and declared child eligibility."""
from __future__ import annotations

class LiteratureRolePolicy:
    @staticmethod
    def _role(role):
        if role != 'literature_targeted':
            raise ValueError('unsupported_literature_role:' + str(role))
        return role

    def permitted_common_actions(self, context):
        self._role(context.role)
        return ('tool', 'reason', 'child', 'redeliver_report')

    def allowed_children(self, parent, caller_capabilities):
        self._role(parent.role)
        return self.child_roles(parent.role, context=parent)

    def child_roles(self, role, *, context=None):
        self._role(role)
        return ()
