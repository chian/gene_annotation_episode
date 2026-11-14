"""Private A103 resource binding record."""
from __future__ import annotations
from .resource_contracts import _AXIS_DIRECTORY, _binding_source_bytes, hashlib

class ResourceBindingRecord:

    def as_record(self):
        implementation = _binding_source_bytes()
        from gene_annotation_episode.episodic_workflow.root.a103.a103_resource_implementation import resource_implementation_bytes
        implementation += resource_implementation_bytes()
        implementation += (_AXIS_DIRECTORY / 'resource_records.py').read_bytes()
        implementation += (_AXIS_DIRECTORY / 'launch_instructions.py').read_bytes()
        if self._contract_information_profile is not None:
            for name in ('composition_information.py', 'schema_information_text.py'):
                implementation += (_AXIS_DIRECTORY / name).read_bytes()
        return {'version': 'resource_episode_binding_v1', 'binding_id': 'resource_work_submission', 'implementation_sha256': hashlib.sha256(implementation).hexdigest(), 'configuration': {'resource_adapters': [adapter.as_record() for adapter in self.adapters.values()], **({'contract_information_profile': self._contract_information_profile} if self._contract_information_profile is not None else {})}}
