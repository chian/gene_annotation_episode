"""Private A102 resource child commissioning."""
from __future__ import annotations
from .resource_contracts import RESOURCE_ROLES

class ResourceChildCommissioning:

    def child_roles(self, role):
        return ()

    def allowed_children(self, parent, caller_capabilities):
        parent.role
        return ()
