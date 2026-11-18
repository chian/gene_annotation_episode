"""Private A102 Results child commissioning."""
from __future__ import annotations
from .execution_contracts import KINDS, ROLE_KINDS, plain

class ResultsChildCommissioning:

    def child_roles(self, role):
        return ()

    def allowed_children(self, parent, caller_capabilities):
        return ()
