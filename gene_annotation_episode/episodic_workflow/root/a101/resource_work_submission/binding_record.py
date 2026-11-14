"""Private A101 launch binding record."""
from __future__ import annotations
from .execution_contracts import _AXIS_DIRECTORY, _binding_source_bytes, hashlib

class OperationalBindingRecord:

    def as_record(self):
        from pathlib import Path as _context_source_path
        implementation = _binding_source_bytes()
        from gene_annotation_episode.episodic_workflow.root.a101.a101_resource_implementation import resource_implementation_bytes
        implementation += resource_implementation_bytes()
        implementation += (_AXIS_DIRECTORY / 'resource_records.py').read_bytes()
        implementation += (_AXIS_DIRECTORY / 'launch_instructions.py').read_bytes()
        if self._contract_information_profile is not None:
            for name in ('composition_information.py', 'schema_information_text.py'):
                implementation += (_AXIS_DIRECTORY / name).read_bytes()
        return {'version': 'resource_episode_binding_v1', 'binding_id': 'resource_work_submission', 'implementation_sha256': hashlib.sha256((implementation + b''.join((_context_source_path(__file__).resolve().parents[5] / _context_source_key).read_bytes() for _context_source_key in ('gene_annotation_episode/__init__.py', 'gene_annotation_episode/episodic_workflow/__init__.py', 'gene_annotation_episode/episodic_workflow/root/__init__.py', 'gene_annotation_episode/episodic_workflow/root/receiving_context.py')))).hexdigest(), 'configuration': {'resource_adapters': [adapter.as_record() for adapter in self.adapters.values()], **({'contract_information_profile': self._contract_information_profile} if self._contract_information_profile is not None else {})}}
