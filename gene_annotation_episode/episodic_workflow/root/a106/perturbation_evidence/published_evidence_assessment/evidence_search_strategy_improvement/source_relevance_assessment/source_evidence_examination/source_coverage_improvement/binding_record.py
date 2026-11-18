"""Private A106 literature_ordered binding record."""
from __future__ import annotations
from .source_contracts import VERSION, deepcopy

class LiteratureBindingRecord:

    def as_record(self):
        configuration = {'outcome_page_size': self.outcome_page_size}
        for name in ('private_yield_binding', 'ratio_source_population', 'controlled_response_population', 'gel_population', 'completion_time_population', 'product_partition_population', 'active_site_population', 'parent_depletion_population', 'stoichiometric_balance_population', 'compiled_assay_population', 'channel_population', 'ion_discrimination_population'):
            if getattr(self, name):
                configuration[name] = True
        if self.private_yield_binding:
            configuration['yield_bindings'] = deepcopy(self._yield_bindings)
        if self.reference_parent_sources is not None:
            configuration['reference_parent_sources'] = list(self.reference_parent_sources)
        if self._contract_information_profile is not None:
            configuration['contract_information_profile'] = self._contract_information_profile
        if self.ratio_source_population:
            configuration['ratio_source_evidence_origin'] = self.ratio_source_evidence_origin
        if self.controlled_response_population:
            configuration['controlled_response_descriptor'] = deepcopy(self._controlled_response_descriptor)
            configuration['controlled_response_evidence_origin'] = self.controlled_response_evidence_origin
        if self.gel_population:
            configuration['gel_descriptor'] = deepcopy(self._gel_descriptor)
            configuration['gel_evidence_origin'] = self.gel_evidence_origin
        return {'version': VERSION, 'binding_id': 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement', 'configuration': configuration}
