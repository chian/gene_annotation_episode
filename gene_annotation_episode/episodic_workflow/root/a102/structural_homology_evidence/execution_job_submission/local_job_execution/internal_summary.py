"""Private A102 native execution internal summary."""
from __future__ import annotations
from .contracts import KINDS, canonical, deepcopy, native_operation_contracts, native_result_operation_catalog, operation_catalog, plain

class NativeSummary:

    def initial_decision_context(self, context):
        if self.local_file_sources.applies(context):
            target = self._target(context)
            return {'execution_resource_capabilities': [{'resource_id': target['resource_id'], 'resource_kind': 'local'}], 'execution_initial_information': {}}
        return {'execution_resource_capabilities': [self._resource_information(key) for key in self.resources], 'execution_initial_information': deepcopy(self.initial_information)}

    def decision_context(self, context, current_view):
        value = self._delegate(context).decision_context(context, current_view)
        return self._with_selected_execution_task(context, value)

    def _with_selected_execution_task(self, context, value):
        assignment = plain(context.assignment)
        requests = {assignment.get('resource_id'): assignment}
        selected = []
        for resource_id, request in requests.items():
            if not isinstance(request, dict) or request.get('resource_kind') != 'local' or (not isinstance(request.get('requested_job', {}).get('native_protein_structure'), dict)):
                return value
            selected.append({'resource_id': resource_id, 'resource_kind': request['resource_kind'], 'endpoint': deepcopy(request.get('endpoint')), 'constraints': deepcopy(request.get('constraints', {})), 'job': deepcopy(request['requested_job']['native_protein_structure']), 'resource': self._resource_information(resource_id)})
        callback = getattr(self.services, 'scientific_parent_task', None)
        parent = None if callback is None else callback(context)
        if parent is None:
            return value
        value['selected_execution_task'] = deepcopy({'version': 'selected_execution_task_v1', 'scientific_question': parent['scientific_question'], 'selected_tool_info': parent['selected_tool_info'], 'requests': selected, 'constraints': assignment.get('constraints', {}), 'selector': assignment.get('selector'), 'result_description': value.get('execution_target_description')})
        return value

    def _resource_information(self, resource_id):
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

    def capabilities(self):
        """Configured operation availability, with no deployment/authentication probe."""
        return [{'resource_id': key, 'kind': KINDS[configuration['kind']], 'availability': 'unknown', 'observed_at': 'caller_configuration', 'provenance_refs': [], 'knowledge_entry_ids': [], 'tool_names': [entry['name'] for entry in (self.api_execution.capabilities(key) if KINDS[configuration['kind']] == 'api' else operation_catalog(KINDS[configuration['kind']]))]} for key, configuration in self.resources.items()]

    def resource_tool_contracts(self):
        """Expose this structural episode's configured launch and result operations."""
        contracts = {}
        direct_protein_names = set()
        if getattr(self.tool_registry, '_protein_structure_configuration', None) is not None:
            direct_protein_names = set(self.tool_registry.catalog()) & {'inspect_protein_structure', 'extract_protein_structure_sequence', 'compare_protein_structures'}
        for resource_id, configuration in self.resources.items():
            kind = KINDS[configuration['kind']]
            resource_role = {'api': 'launch_api', 'local': 'launch_local', 'hpc': 'launch_hpc'}[kind]
            launch = self.api_execution.operation_contracts(resource_id, 'launch_api') if kind == 'api' else operation_catalog(kind)
            results = self.api_execution.operation_contracts(resource_id, 'results') if kind == 'api' else native_result_operation_catalog()
            for entry_role, destination_role, entries in (('launch', resource_role, launch), ('results', 'results', results)):
                for entry in entries:
                    key = (entry['name'], kind)
                    route = {'entry_role': entry_role, 'resource_id': resource_id, 'resource_role': destination_role}
                    if key not in contracts:
                        contracts[key] = {name: deepcopy(entry[name]) for name in ('name', 'description', 'input_schema')}
                        if 'instructions' in entry:
                            contracts[key]['instructions'] = entry['instructions']
                        contracts[key].update(resources=kind, invocation_route={'kind': 'commission', 'routes': []})
                    elif canonical(contracts[key]['input_schema']) != canonical(entry['input_schema']):
                        raise ValueError('execution_resource_operation_contract_conflict:' + entry['name'])
                    if route not in contracts[key]['invocation_route']['routes']:
                        contracts[key]['invocation_route']['routes'].append(route)
            native_entries = []
            if configuration.get('native_protein_structure'):
                from gene_annotation_episode.episodic_workflow.root.a102.native_protein_structure_tool_info import protein_structure_tool_contracts
                native_entries.extend((entry for entry in protein_structure_tool_contracts(configuration['native_protein_structure'], resource_kind='local', resource_id=resource_id) if entry['name'] not in direct_protein_names))
            native_entries.extend(native_operation_contracts(configuration, kind, resource_id))
            for entry in native_entries:
                key = (entry['name'], kind)
                if key in contracts:
                    prior = contracts[key]
                    if prior['description'] != entry['description']:
                        raise ValueError('execution_native_instruction_conflict:' + entry['name'])
                    schemas = prior.setdefault('_native_schemas', [prior['input_schema']])
                    if entry['input_schema'] not in schemas:
                        schemas.append(entry['input_schema'])
                    prior['input_schema'] = {'anyOf': deepcopy(schemas)}
                    prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                else:
                    contracts[key] = deepcopy(entry)
        for entry in contracts.values():
            entry.pop('_native_schemas', None)
        return [contracts[key] for key in sorted(contracts)]
