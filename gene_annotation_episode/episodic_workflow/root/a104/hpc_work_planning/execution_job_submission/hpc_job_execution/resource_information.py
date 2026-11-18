"""Private A104 HPCExecution resource information."""
from __future__ import annotations
from .binding_roles import KINDS
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a104.a104_execution_bindings import homology_api_contracts
from gene_annotation_episode.episodic_workflow.root.a104.a104_execution_bindings import native_operation_contracts
from .result_operations import native_result_operation_catalog
from gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.execution_job_submission.hpc_job_execution.native_tool_contracts import operation_catalog
from gene_annotation_episode.episodic_workflow.root.a104.a104_execution_bindings import preparation_operation_contracts

class HPCExecutionResourceInformation:

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

    def initial_decision_context(self, context):
        if self.local_file_sources.applies(context):
            target = self._target(context)
            return {'execution_resource_capabilities': [{'resource_id': target['resource_id'], 'resource_kind': 'local'}], 'execution_initial_information': {}}
        value = {'execution_resource_capabilities': [self._resource_information(key) for key in self.resources], 'execution_initial_information': deepcopy(self.initial_information), 'received_bvbrc_values': [] if self.api_execution is None else self.api_execution.received_bvbrc_context(context)}
        if context.role in {'annotation', 'evolutionary_history_evidence'} and self.api_execution is not None and any((service.service == 'ncbi_blast' for service in self.api_execution.services.values())):
            jobs = self.api_execution.received_blast_jobs(context, self.job_progress_provider)
            value['received_blast_jobs'] = jobs
            value['received_blast_jobs_meaning'] = 'Saved original BLAST jobs for received handoffs. Status is only as of observed_at; the scheduling estimate is recalculated locally as of forecast_as_of without a new provider observation. No status request is made to build this view. Waiting earns no scientific credit.'
        return value

    def capabilities(self):
        """Configured operation availability, with no deployment/authentication probe."""
        return [{'resource_id': key, 'kind': KINDS[configuration['kind']], 'availability': 'unknown', 'observed_at': 'caller_configuration', 'provenance_refs': [], 'knowledge_entry_ids': [], 'tool_names': [entry['name'] for entry in (self.api_execution.capabilities(key) if KINDS[configuration['kind']] == 'api' else operation_catalog(KINDS[configuration['kind']]))]} for key, configuration in self.resources.items()]

    def resource_tool_contracts(self):
        """Declare only bound A104 launch, result and homology operations."""
        contracts = {}

        def add(entry, kind):
            key = (entry['name'], kind)
            if key in contracts:
                prior = contracts[key]
                if canonical(prior['input_schema']) != canonical(entry['input_schema']):
                    schemas = prior.setdefault('_native_schemas', [deepcopy(prior['input_schema'])])
                    if entry['input_schema'] not in schemas:
                        schemas.append(deepcopy(entry['input_schema']))
                    prior['input_schema'] = {'anyOf': deepcopy(schemas)}
                for route in entry.get('invocation_route', {}).get('routes', ()):
                    if route not in prior['invocation_route']['routes']:
                        prior['invocation_route']['routes'].append(route)
                return
            contracts[key] = deepcopy(entry)
        for resource_id, configuration in self.resources.items():
            kind = KINDS[configuration['kind']]
            resource_role = {'api': 'launch_api', 'local': 'launch_local', 'hpc': 'launch_hpc'}[kind]
            launch = self.api_execution.operation_contracts(resource_id, 'launch_api') if kind == 'api' else operation_catalog(kind)
            results = self.api_execution.operation_contracts(resource_id, 'results') if kind == 'api' else native_result_operation_catalog()
            for entry_role, target_role, entries in (('launch', resource_role, launch), ('results', 'results', results)):
                for entry in entries:
                    route = {'entry_role': entry_role, 'resource_id': resource_id, 'resource_role': target_role}
                    selected = {name: deepcopy(entry[name]) for name in ('name', 'description', 'input_schema')}
                    if 'instructions' in entry:
                        selected['instructions'] = entry['instructions']
                    selected.update(resources=kind, invocation_route={'kind': 'commission', 'routes': [route]})
                    add(selected, kind)
            if kind == 'api':
                service = self.api_execution.services.get(resource_id)
                for entry in homology_api_contracts(self.api_execution, resource_id, kind, service):
                    add(entry, kind)
                if service is not None and service.service == 'bvbrc_appservice':
                    versions = tuple((version for version in ('1', '2') if ('bvbrc_proteome', version) in service.scientific_adapters))
                    if versions:
                        from gene_annotation_episode.episodic_workflow.root.a104.library.bvbrc_proteome_tool_info import proteome_tool_contracts
                        for entry in proteome_tool_contracts(resource_id=resource_id, assignment_schema=self.api_execution.assignment_schema(resource_id), adapter_versions=versions):
                            add(entry, kind)
            for entry in (*native_operation_contracts(configuration, kind, resource_id), *preparation_operation_contracts(configuration, kind, resource_id)):
                add(entry, kind)
        for entry in contracts.values():
            entry.pop('_native_schemas', None)
        return [contracts[key] for key in sorted(contracts)]
