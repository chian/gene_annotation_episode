"""MonitorBindingRecord"""
from __future__ import annotations
from copy import deepcopy
import hashlib
from .contracts import VERSION

class MonitorBindingRecord:

    def as_record(self):
        from pathlib import Path as _context_source_path
        return {'version': VERSION, 'binding_id': 'execution_progress_assessment', 'implementation_sha256': hashlib.sha256((_binding_source_bytes() + b''.join((_context_source_path(__file__).resolve().parents[5] / _context_source_key).read_bytes() for _context_source_key in ('gene_annotation_episode/__init__.py', 'gene_annotation_episode/episodic_workflow/__init__.py', 'gene_annotation_episode/episodic_workflow/root/__init__.py', 'gene_annotation_episode/episodic_workflow/root/receiving_context.py')))).hexdigest(), 'configuration': {'outcome_page_size': self.outcome_page_size, **({'information_unit': self.information_unit, 'yield_settings': deepcopy(self.yield_settings)} if self.private_yield_binding else {})}}

def _binding_source_bytes():
    from pathlib import Path
    from gene_annotation_episode.episodic_workflow.root.a101.library import monitor_prompt, progress_information_credit
    private = b''.join(path.read_bytes() for path in sorted(Path(__file__).parent.glob('*.py')))
    return private + b''.join(Path(module.__file__).read_bytes()
        for module in (monitor_prompt, progress_information_credit))
