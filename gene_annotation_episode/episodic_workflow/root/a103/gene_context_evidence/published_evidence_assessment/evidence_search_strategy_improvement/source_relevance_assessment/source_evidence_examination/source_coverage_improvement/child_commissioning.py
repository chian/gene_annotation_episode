"""Actual selected source parent's child admission and directional endpoints."""
from __future__ import annotations
from .source_contracts import _CHILDREN

class SourceChildCommissioning:

    def allowed_children(self, parent, caller_capabilities):
        self._role(parent.role)
        return self.child_roles(parent.role, context=parent)

    def child_roles(self, role, *, context=None):
        self._role(role)
        return _CHILDREN['literature_ordered']
