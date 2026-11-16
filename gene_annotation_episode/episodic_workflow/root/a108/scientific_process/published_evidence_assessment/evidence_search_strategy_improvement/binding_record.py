from __future__ import annotations
'binding record for this private A108 episode.'
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_contracts import VERSION, deepcopy

class LiteratureBindingRecord:

    def as_record(self):
        configuration = {'outcome_page_size': self.outcome_page_size}
        if self.private_yield_binding:
            configuration['private_yield_binding'] = True
            configuration['yield_bindings'] = deepcopy(self._yield_bindings)
        if self.reference_parent_sources is not None:
            configuration['reference_parent_sources'] = list(self.reference_parent_sources)
        if self._contract_information_profile is not None:
            configuration['contract_information_profile'] = self._contract_information_profile
        return {'version': VERSION, 'binding_id': 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement', 'configuration': configuration}
