"""Private A101 literature binding record."""
from __future__ import annotations
from .source_contracts import VERSION, _binding_source_bytes, hashlib

class LiteratureBindingRecord:

    def as_record(self):
        from pathlib import Path as _context_source_path
        implementation = _binding_source_bytes()
        return {'version': VERSION, 'binding_id': 'published_evidence_assessment', 'implementation_sha256': hashlib.sha256((implementation + b''.join((_context_source_path(__file__).resolve().parents[5] / _context_source_key).read_bytes() for _context_source_key in ('gene_annotation_episode/__init__.py', 'gene_annotation_episode/episodic_workflow/__init__.py', 'gene_annotation_episode/episodic_workflow/root/__init__.py', 'gene_annotation_episode/episodic_workflow/root/receiving_context.py')))).hexdigest(), 'configuration': {'outcome_page_size': self.outcome_page_size}}
