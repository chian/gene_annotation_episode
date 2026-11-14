"""Private A104 source operations."""
from __future__ import annotations
from .contracts import ContractError, Mapping, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _population_catalog, deepcopy, identity, inspect, plain, source_location_inputs, validate_schema

class LiteratureSourceCatalog:

    def catalog(self, context, *, _accept_legacy_quotes=False):
        self._role(context.role)
        available = self.services.tool_catalog(context.scope)
        entries = [{'name': name, **entry} for name, entry in available.items()] if isinstance(available, Mapping) else list(available)
        allowed = set(_ACCESS_TOOLS)
        context.role in {'literature', 'literature_strategy', 'literature_search'}
        allowed.update(_ACQUISITION_TOOLS)
        result = []
        for entry in entries:
            if entry['name'] not in allowed:
                continue
            entry = deepcopy(plain(entry))
            if entry['name'] == 'public.ncbi.search':
                entry['input_schema']['properties']['database'] = {'enum': ['pubmed']}
            if entry['name'] == 'execution.estimate':
                branches = [branch for branch in entry['input_schema'].get('anyOf', ()) if branch.get('properties', {}).get('tool', {}).get('const') in {'source.xlsx.sheets', 'source.xlsx.rows'}]
                if not branches:
                    continue
                entry['input_schema'] = {'anyOf': branches}
            result.append(entry)
        if self.rate_population:
            populations = _population_catalog(assay_grading_population=self.assay_grading_population, ratio_source_population=self.ratio_source_population, controlled_response_population=self.controlled_response_population, gel_population=self.gel_population, completion_time_population=self.completion_time_population, active_site_population=self.active_site_population, parent_depletion_population=self.parent_depletion_population, stoichiometric_balance_population=self.stoichiometric_balance_population, product_partition_population=self.product_partition_population, compiled_assay_population=self.compiled_assay_population, channel_population=self.channel_population, ion_discrimination_population=self.ion_discrimination_population)
            if self._contract_information_profile is not None:
                from gene_annotation_episode.episodic_workflow.root.a104.composition_information import CONTRACT_ARGUMENT_TRANSPORT
                populations = [{**row, 'argument_transport': CONTRACT_ARGUMENT_TRANSPORT} for row in populations]
            result.extend(populations)
        return [{**entry, 'input_schema': source_location_inputs(entry['input_schema'], allow_legacy_quote=_accept_legacy_quotes)} for entry in result]

