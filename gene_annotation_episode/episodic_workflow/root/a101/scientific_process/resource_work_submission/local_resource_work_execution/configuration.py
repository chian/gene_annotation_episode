"""Private A101 launch_local configuration."""
from __future__ import annotations

class OperationalConfiguration:

    def __init__(self, services, *, resource_adapters=(), contract_information_profile=None):
        self.services = services
        from gene_annotation_episode.episodic_workflow.root.a101.composition_information import CONTRACT_INFORMATION_PROFILE
        if contract_information_profile not in (None, CONTRACT_INFORMATION_PROFILE):
            raise ValueError('unsupported_resource_contract_information_profile')
        self._contract_information_profile = contract_information_profile
        self.adapters = {}
        required = ('capability', 'as_record', 'prepare_assignment', 'catalog', 'execute', 'fact_sources', 'facts', 'resolve', 'validate_report', 'credit_view')
        for adapter in resource_adapters:
            if not isinstance(adapter.resource_id, str) or not adapter.resource_id or any((not callable(getattr(adapter, name, None)) for name in required)):
                raise TypeError('explicit_resource_adapter_required')
            if adapter.resource_id in self.adapters:
                raise ValueError('duplicate_resource_id')
            bind_selection = getattr(adapter, 'bind_record_selection', None)
            if bind_selection is not None:
                bind_selection(getattr(services, 'record_selection', None))
            self.adapters[adapter.resource_id] = adapter
