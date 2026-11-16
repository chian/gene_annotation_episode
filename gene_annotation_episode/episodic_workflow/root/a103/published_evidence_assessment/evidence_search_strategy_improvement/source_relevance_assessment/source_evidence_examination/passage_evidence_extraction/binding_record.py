"""Private A103 literature_targeted binding record."""
from __future__ import annotations
from .source_contracts import VERSION

class SourceEpisodeBindingRecord:

    def as_record(self):
        return {'version': VERSION, 'binding_id': 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction', 'configuration': {'outcome_page_size': self.outcome_page_size}}
