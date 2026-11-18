"""Private A107 numerical report facts."""
from __future__ import annotations
from .contracts import ContractError, replace

class LiteratureNumericalReportFacts:

    def _rate_fact_sources(self):
        from gene_annotation_episode.episodic_workflow.root.a107.library.partner_source_contracts import fact_sources
        return fact_sources()

    def _rate_facts(self, context, references):
        from gene_annotation_episode.episodic_workflow.root.a107.library.literature_sheet_updates import current_sheet_refs
        current = current_sheet_refs(self.services.workflow.store, context)
        references = list(dict.fromkeys([*references, *current]))
        view = replace(context, received_record_refs=tuple(dict.fromkeys([*context.received_record_refs, *current])))
        result = {}
        for namespace, requested_field, provider, defaults, repository in self._population_routes():
            adapter = repository()
            selected = []
            for reference in references:
                if reference not in view.received_record_refs:
                    continue
                row = self.services.read_record(reference)
                if row.get('record_type') != 'source' or row.get('provider') != provider:
                    continue
                if row.get('version') != adapter.record_version:
                    raise ContractError('literature_partner_projection_version_mismatch')
                selected.append(reference)
            components = tuple(context.assignment.get(requested_field, defaults))
            result[namespace] = adapter.fact_cells(view, selected, components=components)
        return result
