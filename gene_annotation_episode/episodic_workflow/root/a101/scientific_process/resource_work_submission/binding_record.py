"""Private A101 launch binding record."""
from __future__ import annotations

class OperationalBindingRecord:

    def as_record(self):
        return {'version': 'resource_episode_binding_v1', 'binding_id': 'scientific_process/resource_work_submission', 'configuration': {'resource_adapters': [adapter.as_record() for adapter in self.adapters.values()], **({'contract_information_profile': self._contract_information_profile} if self._contract_information_profile is not None else {})}}
