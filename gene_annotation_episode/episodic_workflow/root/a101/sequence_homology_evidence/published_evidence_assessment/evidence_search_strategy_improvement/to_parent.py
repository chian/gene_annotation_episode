"""Private A101 literature_strategy to parent."""
from __future__ import annotations
from .source_contracts import validate_form

class LiteratureReport:

    def fact_sources(self, role):
        self._role(role)
        return {}

    def facts(self, context, completion_snapshot):
        self._role(context.role)
        return {}

    def current_report_facts(self, context):
        return {}

    def validate_report(self, context, form, original_schema):
        self._validate_assignment(context.role, context.assignment, context.scope, context=context)
        validate_form(form, original_schema, lambda reference, namespace: self.resolve(context, reference, namespace))
        self.validate_received_report(context, form, original_schema)
