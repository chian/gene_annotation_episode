"""Private A102 literature_strategy binding record."""
from __future__ import annotations
from .source_contracts import VERSION, _binding_source_bytes, _implementation_path, hashlib

class SourceBindingRecord:

    def as_record(self):
        implementation = _binding_source_bytes()
        for name in ('a102_literature_bindings.py', 'literature_structure_storage.py', 'literature_experimental_prompt.py', 'literature_reference_parent_prompt.py', 'literature_sheet_updates.py'):
            implementation += _implementation_path(name).read_bytes()
        return {'version': VERSION, 'binding_id': 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement', 'implementation_sha256': hashlib.sha256(implementation).hexdigest(), 'configuration': {'outcome_page_size': self.outcome_page_size, 'structure_population': self.structure_population}}
