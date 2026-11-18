"""Private A110 to parent."""
from __future__ import annotations
from .contracts import reference_in_context, validate_form

class LiteratureReport:

    def fact_sources(self, role):
        self._role(role)
        return self._rate_fact_sources()

    def resolve(self, context, reference, namespace):
        self._role(context.role)
        return reference_in_context(self.services, context, reference, namespace)

    def validate_report(self, context, form, original_schema):
        self._validate_assignment(context.role, context.assignment, context.scope, context=context)
        validate_form(form, original_schema, lambda reference, namespace: self.resolve(context, reference, namespace))
        self.validate_received_report(context, form, original_schema)
