"""Actual selected source parent's child admission and directional endpoints."""
from __future__ import annotations
from .source_contracts import _CHILDREN
from .from_child_table_evidence_extraction import receive_table_evidence_extraction_report
from .from_child_source_coverage_improvement import receive_source_coverage_improvement_report
from .from_child_passage_evidence_extraction import receive_passage_evidence_extraction_report

class SourceChildCommissioning:

    def allowed_children(self, parent, caller_capabilities):
        self._role(parent.role)
        return self.child_roles(parent.role, context=parent)

    def child_roles(self, role, *, context=None):
        self._role(role)
        return _CHILDREN['literature_page']

    def child_request_assembler(self, role):
        if role == 'literature_table':
            return self._assemble_table_evidence_extraction_request
        if role == 'literature_ordered':
            return self._assemble_source_coverage_improvement_request
        if role == 'literature_targeted':
            return self._assemble_passage_evidence_extraction_request
        return None

    def child_report_receiver(self, role):
        if role == 'literature_table':
            return receive_table_evidence_extraction_report
        if role == 'literature_ordered':
            return receive_source_coverage_improvement_report
        if role == 'literature_targeted':
            return receive_passage_evidence_extraction_report
        return None
