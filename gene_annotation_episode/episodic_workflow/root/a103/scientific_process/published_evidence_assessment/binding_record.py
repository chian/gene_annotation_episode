"""Private A103 literature binding record."""
from __future__ import annotations
from .source_contracts import VERSION, _binding_source_bytes, hashlib

class SourceEpisodeBindingRecord:

    def as_record(self):
        implementation = _binding_source_bytes()
        return {'version': VERSION, 'binding_id': 'scientific_process/published_evidence_assessment', 'implementation_sha256': hashlib.sha256(implementation).hexdigest(), 'configuration': {'outcome_page_size': self.outcome_page_size}}
