"""Private A110 Launch resource information"""
from __future__ import annotations
from .binding_roles import KINDS
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical
from copy import deepcopy
from .received_result_records import native_result_operation_catalog
from gene_annotation_episode.episodic_workflow.root.a110.library.execution_operation_information import operation_catalog
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import obj

def launch_operation_catalog():
    """Declared launch operations, without a target/resource observation."""
    return [{'name': 'execution.capabilities', 'description': 'Read the actual caller-bound resource configuration and already recorded inventory; no discovery or selection.', 'input_schema': obj({})}]

class LaunchResourceInformation:

    def resource_tool_contracts(self):
        """Operations available through this episode's configured resources."""
        contracts = {}
        direct_flux_balance = False
        if getattr(self.tool_registry, '_flux_balance_configuration', None) is not None:
            entry = self.tool_registry.catalog().get('perform_flux_balance_analysis', {})
            direct_flux_balance = entry.get('invocation_route', {}).get('kind') == 'direct'
        for resource_id, configuration in self.resources.items():
            kind = KINDS[configuration['kind']]
            resource_role = {'local': 'launch_local', 'hpc': 'launch_hpc'}[kind]
            launch = operation_catalog(kind)
            results = native_result_operation_catalog()
            for entry_role, endpoint_role, entries in (('launch', resource_role, launch), ('results', 'results', results)):
                for entry in entries:
                    key = (entry['name'], kind)
                    route = {'entry_role': entry_role, 'resource_id': resource_id, 'resource_role': endpoint_role}
                    if key not in contracts:
                        contracts[key] = {name: deepcopy(entry[name]) for name in ('name', 'description', 'input_schema')}
                        if 'instructions' in entry:
                            contracts[key]['instructions'] = entry['instructions']
                        contracts[key].update(resources=kind, invocation_route={'kind': 'commission', 'routes': []})
                    elif canonical(contracts[key]['input_schema']) != canonical(entry['input_schema']):
                        raise ValueError('execution_resource_operation_contract_conflict:' + entry['name'])
                    if route not in contracts[key]['invocation_route']['routes']:
                        contracts[key]['invocation_route']['routes'].append(route)
            if configuration.get('native_flux_balance'):
                from gene_annotation_episode.episodic_workflow.root.a110.native_flux_balance_tool_info import flux_balance_tool_contracts
                entries = (entry for entry in flux_balance_tool_contracts(configuration['native_flux_balance'], resource_kind=kind, resource_id=resource_id) if entry['name'] != 'perform_flux_balance_analysis' or not direct_flux_balance)
                for entry in entries:
                    key = (entry['name'], kind)
                    if key in contracts:
                        prior = contracts[key]
                        if prior['description'] != entry['description']:
                            raise ValueError('execution_native_instruction_conflict:' + entry['name'])
                        sections = prior.setdefault('_native_instruction_sections', {route['resource_id']: prior['instructions'] for route in prior['invocation_route']['routes']})
                        sections[resource_id] = entry['instructions']
                        if len(set(sections.values())) > 1:
                            prior['instructions'] = '\n\n'.join(('Resource ' + key + ':\n' + value for key, value in sections.items()))
                        schemas = prior.setdefault('_native_schemas', [prior['input_schema']])
                        if entry['input_schema'] not in schemas:
                            schemas.append(entry['input_schema'])
                        prior['input_schema'] = {'anyOf': deepcopy(schemas)}
                        prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                    else:
                        contracts[key] = deepcopy(entry)
        for entry in contracts.values():
            entry.pop('_native_schemas', None)
            entry.pop('_native_instruction_sections', None)
        return [contracts[key] for key in sorted(contracts)]
