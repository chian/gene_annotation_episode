"""Private A102 literature_ordered child commissioning."""
from __future__ import annotations

class SourceChildCommissioning:

    def allowed_children(self, parent, caller_capabilities):
        self._role(parent.role)
        return self.child_roles(parent.role, context=parent)

    def child_roles(self, role, *, context=None):
        self._role(role)
        return ()
