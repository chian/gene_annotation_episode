"""Private A103 literature_page to parent."""
from __future__ import annotations
from .source_contracts import validate_form

class SourceInvestigationReport:

    def fact_sources(self, role):
        self._role(role)
        return {}

    def facts(self, context, completion_snapshot):
        self._role('literature_page')
        return {}

    def current_report_facts(self, context):
        return {}

    def validate_report(self, context, form, original_schema):
        self._validate_assignment('literature_page', context.assignment, context.scope, context=context)
        validate_form(form, original_schema, lambda reference, namespace: self.resolve(context, reference, namespace))
        self.validate_received_report(context, form, original_schema)
