"""Private A103 resource binding record."""
from __future__ import annotations

class ResourceBindingRecord:

    def as_record(self):
        return {'version': 'resource_episode_binding_v1', 'binding_id': 'gene_context_evidence/resource_work_submission/hpc_resource_work_execution', 'configuration': {'resource_adapters': [adapter.as_record() for adapter in self.adapters.values()], **({'contract_information_profile': self._contract_information_profile} if self._contract_information_profile is not None else {})}}
