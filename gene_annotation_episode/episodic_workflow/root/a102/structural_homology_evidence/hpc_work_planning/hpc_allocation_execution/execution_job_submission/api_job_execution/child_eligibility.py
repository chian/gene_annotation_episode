"""Original API child eligibility, pending explicit own-role specialization."""
from __future__ import annotations
from .execution_contracts import KINDS, ROLE_KINDS, plain

class APIChildEligibility:

    def child_roles(self, role):
        return ()

    def allowed_children(self, parent, caller_capabilities):
        return ()
