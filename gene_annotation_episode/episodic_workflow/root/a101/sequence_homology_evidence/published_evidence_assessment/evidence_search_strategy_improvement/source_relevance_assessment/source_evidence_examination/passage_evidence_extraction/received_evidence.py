"""Private A101 literature_targeted received evidence."""
from __future__ import annotations

class LiteratureReceivedEvidence:

    def received_report_sources(self, role):
        self._role(role)
        return {}

    def received_report_facts(self, context):
        return {}

    def received_form_references(self, context, form, schema, operation_key):
        return []

    def received_evidence_tokens(self, context):
        return []

    def validate_received_report(self, context, form, schema):
        return None
