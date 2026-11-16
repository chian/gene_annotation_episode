"""Private A110 binding record."""
from __future__ import annotations
from .contracts import VERSION

class LiteratureBindingRecord:

    def as_record(self):
        configuration = {'outcome_page_size': self.outcome_page_size}
        if self.reference_parent_sources is not None:
            configuration['reference_parent_sources'] = list(self.reference_parent_sources)
        if self._contract_information_profile is not None:
            configuration['contract_information_profile'] = self._contract_information_profile
        return {'version': VERSION, 'binding_id': 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction', 'configuration': configuration}
