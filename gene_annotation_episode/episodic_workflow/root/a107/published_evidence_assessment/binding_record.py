"""Private A107 binding record."""
from __future__ import annotations
from .contracts import VERSION

class LiteratureBindingRecord:

    def as_record(self):
        configuration = {'outcome_page_size': self.outcome_page_size}
        if self.reference_parent_sources is not None:
            configuration['reference_parent_sources'] = list(self.reference_parent_sources)
        if self._contract_information_profile is not None:
            configuration['contract_information_profile'] = self._contract_information_profile
        return {'version': VERSION, 'binding_id': 'published_evidence_assessment', 'configuration': configuration}
