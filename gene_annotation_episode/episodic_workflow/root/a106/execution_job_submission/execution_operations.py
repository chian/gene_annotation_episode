"""Private A106 launch execution operations."""
from __future__ import annotations
from .execution_contracts import _outcome, canonical, checked, deepcopy, launch_operation_catalog, plain

class OperationalOperations:

    def _resource_information(self, resource_id):
        config = self.resources[resource_id]
        capability = next((value for value in self.capabilities() if value['resource_id'] == resource_id))
        return {'resource_id': resource_id, 'resource_kind': 'api', 'availability': capability['availability'], 'tool_names': capability['tool_names'], **{key: deepcopy(config[key]) for key in ('service', 'base_url') if key in config}, 'inventory_snapshot': deepcopy(self.initial_information.get(resource_id))}

    def capabilities(self):
        return [{'resource_id': key, 'kind': 'api', 'availability': 'unknown', 'observed_at': 'caller_configuration', 'provenance_refs': [], 'knowledge_entry_ids': [], 'tool_names': [entry['name'] for entry in self.api_execution.capabilities(key)]} for key in self.resources]


    def catalog(self, context):
        self.credit_kind(context.role)
        return launch_operation_catalog()

    async def execute(self, context, tool_name, arguments, operation_key):
        self.credit_kind(context.role)
        try:
            catalog = {entry['name']: entry for entry in self.catalog(context)}
            if tool_name not in catalog:
                raise ValueError('execution_operation_not_available')
            arguments = checked(arguments, catalog[tool_name]['input_schema'], 'invalid_execution_operation_arguments')
            return _outcome(self.initial_decision_context(context))
        except (ValueError, TypeError) as error:
            return _outcome(code=str(error))

    @staticmethod
    def _appservice_sources():
        from gene_annotation_episode.episodic_workflow.root.a106.library.bvbrc_application_facts import application_fact_sources
        return {**application_fact_sources(), 'bvbrc_appservice_support_refs': {'type': 'array', 'meaning': 'Actually received AppService preparation, Workspace, upload or observation receipts; these are not scientific result acquisitions.', 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'bvbrc_appservice_support'}, 'x-source': 'bvbrc_appservice_support_refs'}}}
