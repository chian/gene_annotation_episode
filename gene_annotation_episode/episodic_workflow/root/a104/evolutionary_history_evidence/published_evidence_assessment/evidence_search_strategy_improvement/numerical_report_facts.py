"""Private A104 numerical report facts."""
from __future__ import annotations
from .contracts import ContractError, deepcopy, replace

from .report_field_contracts import LiteratureReportFieldContracts

class LiteratureNumericalReportFacts(LiteratureReportFieldContracts):

    def _rate_facts(self, context, references):
        from gene_annotation_episode.episodic_workflow.root.a104.literature_sheet_updates import current_sheet_refs
        current = current_sheet_refs(self.services.workflow.store, context)
        references = list(dict.fromkeys([*references, *current]))
        context = replace(context, received_record_refs=tuple(dict.fromkeys([*context.received_record_refs, *current])))
        result = {}
        for namespace, requested_field, provider, defaults, repository in self._population_routes(context):
            selected = []
            adapter = repository()
            for reference in references:
                if reference not in context.received_record_refs:
                    continue
                row = self.services.read_record(reference)
                if row.get('record_type') == 'source' and row.get('provider') == provider:
                    if namespace in {'literature_figure_cells', 'literature_endpoint_signal_cells'}:
                        if row.get('version') not in {'literature_figure_record_v1', 'literature_figure_endpoint_signal_record_v1'}:
                            raise ContractError('literature_figure_projection_version_mismatch')
                        if row.get('version') != adapter.record_version:
                            continue
                    if namespace in {'literature_rate_cells', 'literature_rate_source_cells', 'literature_rate_source_domain_cells', 'literature_rate_source_meaning_cells'}:
                        if row.get('version') not in {'literature_rate_population_record_v1', 'literature_rate_population_record_v2'}:
                            raise ContractError('literature_rate_projection_version_mismatch')
                        if row.get('version') != adapter.record_version:
                            continue
                    if namespace in {'literature_rate_observation_cells', 'literature_rate_grid_cells'}:
                        if row.get('version') not in {'literature_reported_rate_observation_record_v1', 'literature_reported_rate_observation_record_v2'}:
                            raise ContractError('literature_rate_grid_projection_version_mismatch')
                        if row.get('version') != adapter.record_version:
                            continue
                    if namespace == 'literature_ratio_source_cells' and row.get('version') != adapter.record_version:
                        raise ContractError('literature_ratio_source_projection_version_mismatch')
                    if namespace in {'literature_compiled_assay_cells', 'literature_compiled_assay_v2_cells', 'literature_compiled_assay_v3_cells'}:
                        if row.get('version') not in {'literature_compiled_assay_record_v1', 'literature_compiled_assay_record_v2', 'literature_compiled_assay_record_v3'}:
                            raise ContractError('literature_compiled_assay_projection_version_mismatch')
                        if row.get('version') != adapter.record_version:
                            continue
                    selected.append(reference)
            components = tuple(context.assignment.get(requested_field, defaults))
            result[namespace] = adapter.fact_cells(context, selected, components=components)
        if not self.rate_population:
            return result
        if self.controlled_response_population:
            from gene_annotation_episode.episodic_workflow.root.a104.literature_controlled_response_storage import PROVIDER
            adapter = self._controlled_response_repository()
            rows = []
            for reference in dict.fromkeys(references):
                if reference not in context.received_record_refs:
                    continue
                record = self.services.read_record(reference)
                if record.get('record_type') == 'source' and record.get('provider') == PROVIDER:
                    keys = adapter.requested_component_keys(reference, context.assignment)
                    rows.extend(adapter.fact_cells(context, [reference], components=keys))
            result['literature_controlled_response_component_cells'] = rows
        if self.gel_population:
            from gene_annotation_episode.episodic_workflow.root.a104.literature_gel_storage import PROVIDER
            adapter = self._gel_repository()
            rows = []
            for reference in dict.fromkeys(references):
                if reference not in context.received_record_refs:
                    continue
                record = self.services.read_record(reference)
                if record.get('record_type') == 'source' and record.get('provider') == PROVIDER:
                    keys = adapter.requested_component_keys(reference, context.assignment)
                    rows.extend(adapter.fact_cells(context, [reference], components=keys))
            result['literature_gel_component_cells'] = rows
        return result
