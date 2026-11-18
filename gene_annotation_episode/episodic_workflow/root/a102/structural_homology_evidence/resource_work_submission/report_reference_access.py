"""Resolve original Resource references through actual shared receiving interfaces."""
from __future__ import annotations
from .resource_contracts import HANDOFF_SCHEMA, Mapping, ReportBoundaryError, _array, _nullable, plain, reference_in_context

class ResourceReportReferenceAccess:

    def resolve(self, context, reference, namespace):
        if reference_in_context(self.services, context, reference, namespace):
            return True
        return any((adapter.resolve(context, reference, namespace) for adapter in self.adapters.values()))

