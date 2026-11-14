"""Private A106 results execution operations."""
from __future__ import annotations
from .execution_contracts import _outcome, canonical, checked, deepcopy, launch_operation_catalog, plain

class OperationalOperations:

    def _api_operation_catalog(self, api, context):
        assignment, service, target = api._context(context)
        return service.launch_catalog(assignment['request']) if target is None else service.result_catalog(assignment['request'], plain(context.assignment)['selector'])


    def _resource_information(self, resource_id):
        config = self.resources[resource_id]
        capability = next((value for value in self.capabilities() if value['resource_id'] == resource_id))
        return {'resource_id': resource_id, 'resource_kind': 'api', 'availability': capability['availability'], 'tool_names': capability['tool_names'], **{key: deepcopy(config[key]) for key in ('service', 'base_url') if key in config}, 'inventory_snapshot': deepcopy(self.initial_information.get(resource_id))}

    def capabilities(self):
        return [{'resource_id': key, 'kind': 'api', 'availability': 'unknown', 'observed_at': 'caller_configuration', 'provenance_refs': [], 'knowledge_entry_ids': [], 'tool_names': [entry['name'] for entry in self.api_execution.capabilities(key)]} for key in self.resources]

    def resource_tool_contracts(self):
        contracts = {}
        for resource_id in self.resources:
            for entry_role, resource_role, entries in (('results', 'results', self.api_execution.operation_contracts(resource_id, 'results')),):
                for entry in entries:
                    key = (entry['name'], 'api')
                    route = {'entry_role': entry_role, 'resource_id': resource_id, 'resource_role': resource_role}
                    if key not in contracts:
                        contracts[key] = {name: deepcopy(entry[name]) for name in ('name', 'description', 'input_schema')}
                        if 'instructions' in entry:
                            contracts[key]['instructions'] = entry['instructions']
                        contracts[key].update(resources='api', invocation_route={'kind': 'commission', 'routes': []})
                    elif canonical(contracts[key]['input_schema']) != canonical(entry['input_schema']):
                        raise ValueError('execution_resource_operation_contract_conflict:' + entry['name'])
                    if route not in contracts[key]['invocation_route']['routes']:
                        contracts[key]['invocation_route']['routes'].append(route)
        return [contracts[key] for key in sorted(contracts)]

    def catalog(self, context):
        self.credit_kind(context.role)
        self._selector(plain(context.assignment), self._target(context))
        return self.api_execution.catalog(context)

    async def execute(self, context, tool_name, arguments, operation_key):
        self.credit_kind(context.role)
        try:
            catalog = {entry['name']: entry for entry in self.catalog(context)}
            if tool_name not in catalog:
                raise ValueError('execution_operation_not_available')
            arguments = checked(arguments, catalog[tool_name]['input_schema'], 'invalid_execution_operation_arguments')
            return await self.api_execution.execute(context, tool_name, arguments, operation_key)
        except (ValueError, TypeError) as error:
            return _outcome(code=str(error))

    @staticmethod
    def _appservice_sources():
        from gene_annotation_episode.episodic_workflow.root.a106.library.bvbrc_application_facts import application_fact_sources
        return {**application_fact_sources(), 'bvbrc_appservice_support_refs': {'type': 'array', 'meaning': 'Actually received AppService preparation, Workspace, upload or observation receipts; these are not scientific result acquisitions.', 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'bvbrc_appservice_support'}, 'x-source': 'bvbrc_appservice_support_refs'}}}
