"""Private A101 results execution operations."""
from __future__ import annotations
from .execution_contracts import KINDS, ROLE_KINDS, _outcome, canonical, checked, deepcopy, homology_api_contracts, is_native_blast_database_target, is_native_blast_target, is_native_hmmer_preparation_target, is_native_hmmer_target, is_standard_blast_database_target, launch_operation_catalog, native_operation_contracts, native_result_operation_catalog, operation_catalog, plain, preparation_operation_contracts

class OperationalOperations:

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
        """Declare only bound A101 launch, result and homology operations."""
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
            for entry_role, owner_role, entries in (('launch', resource_role, launch), ('results', 'results', results)):
                for entry in entries:
                    route = {'entry_role': entry_role, 'resource_id': resource_id, 'resource_role': owner_role}
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
                    proteome_versions = tuple(version for version in ('1', '2') if ('bvbrc_proteome', version) in service.scientific_adapters)
                    if proteome_versions:
                        from gene_annotation_episode.episodic_workflow.root.a101.bvbrc_proteome_tool_info import proteome_tool_contracts
                        for entry in proteome_tool_contracts(resource_id=resource_id, assignment_schema=self.api_execution.assignment_schema(resource_id), adapter_versions=proteome_versions):
                            add(entry, kind)
            for entry in (*native_operation_contracts(configuration, kind, resource_id), *preparation_operation_contracts(configuration, kind, resource_id)):
                add(entry, kind)
        for entry in contracts.values():
            entry.pop('_native_schemas', None)
        return [contracts[key] for key in sorted(contracts)]

    def catalog(self, context):
        self.credit_kind(context.role)
        if self.native_blast_masking_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.a101.native_blast_masking_results import operation_catalog as masking_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return masking_result_catalog()
        if self.native_blast_utility_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.a101.native_blast_utility_results import operation_catalog as utility_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return utility_result_catalog()
        if 'results' in ROLE_KINDS:
            practical_context = self._practical_context(context)
            return self._delegate(context).catalog(practical_context)
        target = self._target(context)
        if is_standard_blast_database_target(target):
            self._selector(plain(context.assignment), target)
            from gene_annotation_episode.episodic_workflow.root.a101.native_blast_standard_database_results import operation_catalog as database_catalog
            return database_catalog()
        if is_native_blast_database_target(target):
            selector = self._selector(plain(context.assignment), target)
            from gene_annotation_episode.episodic_workflow.root.a101.native_blast_database_results import operation_catalog as database_catalog
            return database_catalog(selector)
        if target['resource_kind'] == 'api':
            return self.api_execution.catalog(context)
        if is_native_hmmer_preparation_target(target):
            if self.native_hmmer_preparation_results is None:
                raise ValueError('native_hmmer_preparation_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a101.native_hmmer_preparation_results import operation_catalog as hmmer_preparation_result_catalog
            return hmmer_preparation_result_catalog()
        if is_native_hmmer_target(target):
            from gene_annotation_episode.episodic_workflow.root.a101.native_hmmer_results import operation_catalog as hmmer_result_catalog
            return hmmer_result_catalog()
        if is_native_blast_target(target):
            if self.native_blast_results is None:
                raise ValueError('native_blast_results_binding_unavailable')
            from gene_annotation_episode.episodic_workflow.root.a101.native_blast_results import operation_catalog as blast_result_catalog
            return blast_result_catalog()
        return native_result_operation_catalog()

    async def execute(self, context, tool_name, arguments, operation_key):
        self.credit_kind(context.role)
        if 'results' in ROLE_KINDS:
            self._check_parent_inputs(context)
            practical_context = self._practical_context(context)
            outcome = await self._delegate(context).execute(practical_context, tool_name, arguments, operation_key)
            return outcome
        try:
            catalog = {entry['name']: entry for entry in self.catalog(context)}
            if tool_name not in catalog:
                raise ValueError('execution_operation_not_available')
            arguments = checked(arguments, catalog[tool_name]['input_schema'], 'invalid_execution_operation_arguments')
            target = self._target(context)
            if self.local_file_sources.applies(context):
                return await self.local_file_sources.execute(context, target, tool_name, arguments, operation_key)
            if self.native_blast_masking_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_blast_masking_results.execute(context, target, tool_name, arguments, operation_key)
            if self.native_blast_utility_results.applies(context):
                self._selector(plain(context.assignment), target)
                return await self.native_blast_utility_results.execute(context, target, tool_name, arguments, operation_key)
            if is_standard_blast_database_target(target):
                return await self.native_blast_standard_database_results.execute(context, target, tool_name, arguments, operation_key)
            if is_native_blast_database_target(target):
                return await self.native_blast_database_results.execute(context, target, tool_name, arguments, operation_key)
            if target['resource_kind'] == 'api':
                return await self.api_execution.execute(context, tool_name, arguments, operation_key)
            if is_native_hmmer_preparation_target(target):
                return await self.native_hmmer_preparation_results.execute(context, target, tool_name, arguments, operation_key)
            if is_native_hmmer_target(target):
                return await self.native_hmmer_results.execute(context, target, tool_name, arguments, operation_key)
            if is_native_blast_target(target):
                return await self.native_blast_results.execute(context, target, tool_name, arguments, operation_key)
            return await self._execute_native_results(context, target, tool_name, arguments, operation_key)
        except (ValueError, TypeError) as error:
            from gene_annotation_episode.episodic_workflow.root.a101.native_file_capture import NativeFileCaptureError
            if isinstance(error, NativeFileCaptureError) and self.local_file_sources.applies(context) and (error.code in {'retained_artifact_unavailable', 'retained_artifact_mismatch'}):
                raise
            return _outcome(code=str(error))

    def _has_appservice(self):
        return self.api_execution is not None and any((service.service == 'bvbrc_appservice' for service in self.api_execution.services.values()))

    def _has_uniprot(self):
        return self.api_execution is not None and any((service.service == 'uniprot' for service in self.api_execution.services.values()))

    @staticmethod
    def _appservice_sources():
        from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_homology_return_values import homology_fact_sources
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_phylogeny_returns import phylogeny_fact_sources
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_alignment_returns import alignment_fact_sources
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_genome_alignment_returns import genome_alignment_fact_sources
        from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_proteome_return_values import proteome_fact_sources
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_comparative_systems_returns import comparative_systems_fact_sources
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_fastqutils_returns import fastqutils_fact_sources
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_application_returns import application_fact_sources
        return {**homology_fact_sources(), **phylogeny_fact_sources(), **alignment_fact_sources(), **genome_alignment_fact_sources(), **proteome_fact_sources(), **comparative_systems_fact_sources(), **fastqutils_fact_sources(), **application_fact_sources(), 'bvbrc_appservice_support_refs': {'type': 'array', 'meaning': 'Actually received AppService preparation, Workspace, upload or observation receipts; these are not scientific result acquisitions.', 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'bvbrc_appservice_support'}, 'x-source': 'bvbrc_appservice_support_refs'}}}
