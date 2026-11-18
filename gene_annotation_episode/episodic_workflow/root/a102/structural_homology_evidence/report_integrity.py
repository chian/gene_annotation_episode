"""Private A102 scientific report integrity."""
from __future__ import annotations
from .scientific_contracts import PROTEIN_ACTION_FACT_SOURCES, ReportBoundaryError, plain, requested_protein_structure_action_fields, validate_frozen_protein_structure_action_return

class ScientificReportIntegrity:

    def _validate_protein_structure_action_report(self, context, form, schema):
        for source in PROTEIN_ACTION_FACT_SOURCES:
            fields = requested_protein_structure_action_fields(plain(schema), fact_source=source)
            if not fields:
                continue
            try:
                frozen = self.services.protein_structure_action_frozen_facts(context, fact_source=source)
            except ValueError as error:
                raise ReportBoundaryError('Original protein action facts unavailable', code=str(error), field=fields[0]) from error
            validate_frozen_protein_structure_action_return(plain(form), plain(schema), frozen, fact_source=source)
