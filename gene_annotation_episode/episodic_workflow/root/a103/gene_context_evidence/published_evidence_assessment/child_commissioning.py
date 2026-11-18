"""Actual selected source parent's child admission and directional endpoints."""
from __future__ import annotations
from .source_contracts import _CHILDREN
from .from_child_evidence_search_strategy_improvement import receive_evidence_search_strategy_improvement_report

class SourceChildCommissioning:

    def allowed_children(self, parent, caller_capabilities):
        self._role(parent.role)
        return self.child_roles(parent.role, context=parent)

    def child_roles(self, role, *, context=None):
        self._role(role)
        return _CHILDREN['literature']

    def child_request_assembler(self, role):
        if role == 'literature_strategy':
            return self._assemble_evidence_search_strategy_improvement_request
        return None

    def child_report_receiver(self, role):
        if role == 'literature_strategy':
            return receive_evidence_search_strategy_improvement_report
        return None

