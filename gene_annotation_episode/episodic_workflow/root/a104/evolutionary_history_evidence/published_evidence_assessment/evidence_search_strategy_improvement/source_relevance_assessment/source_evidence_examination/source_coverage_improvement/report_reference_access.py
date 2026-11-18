"""Private A104 to parent."""
from __future__ import annotations
from .contracts import reference_in_context, validate_form


class LiteratureReportReferenceAccess:

    def resolve(self, context, reference, namespace):
        self._role(context.role)
        return reference_in_context(self.services, context, reference, namespace)

