"""Private A104 to parent."""
from __future__ import annotations
from .contracts import reference_in_context, validate_form

from .report_fields import LiteratureReportFields

from .report_reference_access import LiteratureReportReferenceAccess

class LiteratureReport(LiteratureReportReferenceAccess, LiteratureReportFields):

    def validate_report(self, context, form, original_schema):
        self._validate_assignment(context.role, context.assignment, context.scope, context=context)
        validate_form(form, original_schema, lambda reference, namespace: self.resolve(context, reference, namespace))
        self.validate_received_report(context, form, original_schema)
