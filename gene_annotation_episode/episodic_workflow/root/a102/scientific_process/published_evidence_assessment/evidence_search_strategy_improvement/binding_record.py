"""Private A102 literature_strategy binding record."""
from __future__ import annotations
from .source_contracts import VERSION

class SourceBindingRecord:

    def as_record(self):
        return {'version': VERSION, 'binding_id': 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement', 'configuration': {'outcome_page_size': self.outcome_page_size, 'structure_population': self.structure_population}}
