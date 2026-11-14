"""Original configured resource information, selected by actual own-axis consumers."""
from copy import deepcopy
from .execution_operation_information import operation_catalog
KINDS = {'local': 'local', 'pbs_ssh': 'hpc'}

def resource_information_for_id(self, resource_id):
    config = self.resources[resource_id]
    capability = next((value for value in self.capabilities() if value['resource_id'] == resource_id))
    value = {'resource_id': resource_id, 'resource_kind': KINDS[config['kind']], 'availability': capability['availability'], 'tool_names': capability['tool_names'], **{key: deepcopy(config[key]) for key in ('workspace', 'policy', 'account', 'python_executable', 'service', 'base_url') if key in config}, 'inventory_snapshot': deepcopy(self.initial_information.get(resource_id))}
    return value
def execution_capabilities(self):
    """Configured operation availability, with no deployment/authentication probe."""
    return [{'resource_id': key, 'kind': KINDS[configuration['kind']], 'availability': 'unknown', 'observed_at': 'caller_configuration', 'provenance_refs': [], 'knowledge_entry_ids': [], 'tool_names': [entry['name'] for entry in operation_catalog(KINDS[configuration['kind']])]} for key, configuration in self.resources.items()]

def execution_capability_information(self, context):
    return {'execution_resource_capabilities': [self._resource_information(key) for key in self.resources], 'execution_initial_information': deepcopy(self.initial_information)}
