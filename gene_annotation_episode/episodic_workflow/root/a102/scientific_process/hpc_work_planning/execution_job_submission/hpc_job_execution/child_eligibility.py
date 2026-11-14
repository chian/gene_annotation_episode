"""Private A102 native execution child eligibility."""
from __future__ import annotations

class NativeChildEligibility:

    def child_roles(self, role):
        return ()

    def allowed_children(self, parent, caller_capabilities):
        return ()
