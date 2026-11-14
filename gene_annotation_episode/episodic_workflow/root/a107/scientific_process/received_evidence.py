"""Private A107 scientific received_evidence."""
from __future__ import annotations

class ScientificReceivedEvidence:

    def received_report_facts(self, context):
        if context.role != 'annotation':
            return {}
        return self._component_scoring_facts(context)

    def validate_received_report(self, context, form, schema):
        if context.role == 'annotation':
            self._validate_component_axis_report(context, form, schema)
