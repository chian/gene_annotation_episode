"""The selected private API execution role has no child episodes."""
from __future__ import annotations
from .contracts import KINDS, ROLE_KINDS, plain

class APIJobChildEligibility:

    def child_roles(self, role):
        return ()

    def allowed_children(self, parent, caller_capabilities):
        return ()

