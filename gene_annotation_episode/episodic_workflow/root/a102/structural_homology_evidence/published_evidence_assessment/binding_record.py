"""Private A102 literature binding record."""
from __future__ import annotations
from .source_contracts import VERSION

class SourceBindingRecord:

    def as_record(self):
        return {'version': VERSION, 'binding_id': 'structural_homology_evidence/published_evidence_assessment', 'configuration': {'outcome_page_size': self.outcome_page_size, 'structure_population': self.structure_population}}
