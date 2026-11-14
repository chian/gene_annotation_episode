"""Private A104 scientific report integrity."""
from __future__ import annotations
from .scientific_assignment_contracts import ReportBoundaryError, plain, requested_molecular_fact_fields, requested_molecular_fact_sources, validate_frozen_molecular_return

class ScientificReportIntegrity:

    def _validate_component_axis_report(self, context, form, schema):
        return

    def _validate_molecular_report(self, context, form, schema):
        for source in requested_molecular_fact_sources(plain(schema)):
            fields = requested_molecular_fact_fields(plain(schema), fact_source=source)
            label, missing_code = {'protein_conservation_outcomes': ('literal conservation', 'protein_conservation_facts_not_frozen'), 'protein_phylogeny_outcomes': ('native protein phylogeny', 'protein_phylogeny_facts_not_frozen')}[source]
            try:
                frozen = self.services.molecular_frozen_facts(context, fact_source=source)
                if frozen is None:
                    raise ValueError(missing_code)
                validate_frozen_molecular_return(plain(form), plain(schema), frozen, fact_source=source)
            except ReportBoundaryError:
                raise
            except ValueError as error:
                raise ReportBoundaryError(f'Return differs from the frozen {label} facts', code=str(error), field=fields[0]) from error
