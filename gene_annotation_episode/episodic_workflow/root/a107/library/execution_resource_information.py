"""Original configured resource information, selected by actual own-axis consumers."""
from copy import deepcopy
from .execution_operation_information import operation_catalog
KINDS = {'local': 'local', 'pbs_ssh': 'hpc', 'hmmer_api': 'api', 'api': 'api'}

def resource_information_for_id(self, resource_id):
    config = self.resources[resource_id]
    capability = next((value for value in self.capabilities() if value['resource_id'] == resource_id))
    value = {'resource_id': resource_id, 'resource_kind': KINDS[config['kind']], 'availability': capability['availability'], 'tool_names': capability['tool_names'], **{key: deepcopy(config[key]) for key in ('workspace', 'policy', 'account', 'python_executable', 'service', 'base_url') if key in config}, 'inventory_snapshot': deepcopy(self.initial_information.get(resource_id))}
    if config['kind'] == 'api':
        facts = {}
        for entry in self.api_execution.capabilities(resource_id):
            reported = entry.get('configuration', {})
            for name in ('ncbi_contact_configured', 'provider_rate_state_configured'):
                if name not in reported:
                    continue
                actual = reported[name]
                if type(actual) is not bool:
                    raise ValueError('api_configuration_fact_must_be_boolean')
                if name in facts and facts[name] != actual:
                    raise ValueError('api_configuration_fact_conflict')
                facts[name] = actual
        if facts:
            value['api_configuration_facts'] = facts
    return value
def execution_capabilities(self):
    """Configured operation availability, with no deployment/authentication probe."""
    return [{'resource_id': key, 'kind': KINDS[configuration['kind']], 'availability': 'unknown', 'observed_at': 'caller_configuration', 'provenance_refs': [], 'knowledge_entry_ids': [], 'tool_names': [entry['name'] for entry in (self.api_execution.capabilities(key) if KINDS[configuration['kind']] == 'api' else operation_catalog(KINDS[configuration['kind']]))]} for key, configuration in self.resources.items()]

def execution_capability_information(self, context):
    return {'execution_resource_capabilities': [self._resource_information(key) for key in self.resources], 'execution_initial_information': deepcopy(self.initial_information), 'received_bvbrc_values': [] if self.api_execution is None else self.api_execution.received_bvbrc_context(context)}
