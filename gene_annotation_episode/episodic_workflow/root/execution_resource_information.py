"""Original configured-resource contracts and selected-work presentation.

An actual fixed execution owner supplies the recorded receiver ports. This
module registers no episode, builds no provider and grants no execution authority.
"""
from __future__ import annotations

from copy import deepcopy

from gene_annotation_episode.execution_contracts import obj
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.communication import plain
from .library.terminal_command_contract import operation_catalog


KINDS = {'local': 'local', 'pbs_ssh': 'hpc', 'hmmer_api': 'api', 'api': 'api'}
TEXT = {'type': 'string', 'minLength': 1}
OFFSET = {'type': 'integer', 'minimum': 0}
LIMIT = {'type': 'integer', 'minimum': 1}
FILE_LIMIT = {**LIMIT, 'maximum': 1024*1024}


def native_result_operation_catalog():
    """Actual local/PBS acquisition operators; execution still requires a target."""
    return [
        {'name': 'execution.results.status', 'description': 'Observe the exact handed-off physical attempt once.',
         'input_schema': obj({})},
        {'name': 'execution.results.collect', 'description':
            'Observe the original attempt and acquire bounded first windows of the requested paths.', 'input_schema': obj({})},
        {'name': 'execution.results.read', 'description':
            'Acquire one selected bounded byte window within the original requested paths and interval.',
         'input_schema': obj({'path': TEXT, 'offset': OFFSET, 'limit': FILE_LIMIT})}]


class ExecutionResourceInformation:
    def _resource_information(self, resource_id):
        config = self.resources[resource_id]
        capability = next(value for value in self.capabilities() if value['resource_id'] == resource_id)
        value = {'resource_id': resource_id, 'resource_kind': KINDS[config['kind']],
            'availability': capability['availability'], 'tool_names': capability['tool_names'],
            **{key: deepcopy(config[key]) for key in ('workspace', 'policy', 'account', 'python_executable',
                'service', 'base_url') if key in config},
            'inventory_snapshot': deepcopy(self.initial_information.get(resource_id))}
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
            return {'execution_resource_capabilities': [{'resource_id': target['resource_id'],
                'resource_kind': 'local'}], 'execution_initial_information': {}}
        value = {'execution_resource_capabilities': [self._resource_information(key) for key in self.resources],
            'execution_initial_information': deepcopy(self.initial_information),
            'received_bvbrc_values': [] if self.api_execution is None else
                self.api_execution.received_bvbrc_context(context)}
        if (context.role in {'annotation', 'scientific_process'}
                and self.api_execution is not None
                and any(service.service == 'ncbi_blast' for service in self.api_execution.services.values())):
            jobs = self.api_execution.received_blast_jobs(context, self.job_progress_provider)
            for job in jobs:
                job.update(self._blast_scientific_owner(job['origin_episode_id']))
            value['received_blast_jobs'] = (self._blast_axis_summaries(jobs)
                if context.role == 'annotation' else jobs)
            value['received_blast_jobs_meaning'] = (
                'Saved original BLAST jobs for received handoffs; root sees one summary per '
                'annotation, axis and subject, while the scientific owner sees its original handles. '
                'Status is only as of observed_at; the scheduling estimate is recalculated '
                'locally as of forecast_as_of without a new provider observation. '
                'No status request is made to build this view. The scientific owner can work locally or '
                'return its handoff upward; the annotation root can choose another axis. A later owner '
                'may monitor or fetch the same handoff without a new submission. Waiting earns no '
                'scientific credit.')
        if self._forwards_minhash_reports(context.role):
            value['received_minhash_values'] = self.api_execution.minhash.received_context(context)
        if self.native_rna_structure_returns is not None and context.role in {'annotation', 'scientific_process'}:
            value['received_rna_structure_values'] = self.native_rna_structure_returns.received_context(context)
            value['received_rna_comparison_values'] = self.rna_structure_comparison_returns.received_context(context)
        return value

    def capabilities(self):
        """Configured operation availability, with no deployment/authentication probe."""
        return [{'resource_id': key, 'kind': KINDS[configuration['kind']],
            'availability': 'unknown', 'observed_at': 'caller_configuration',
            'provenance_refs': [], 'knowledge_entry_ids': [],
            'tool_names': [entry['name'] for entry in (
                self.api_execution.capabilities(key) if KINDS[configuration['kind']] == 'api'
                else operation_catalog(KINDS[configuration['kind']]))]}
            for key, configuration in self.resources.items()]

    def resource_tool_contracts(self):
        """Information for commissioning the actual configured resource owners.

        These declarations do not enable direct scientific invocation. The
        original launch/results assignment still supplies the job and selector;
        only the selected resource episode can execute each operation.
        """
        contracts = {}
        direct_protein_names = set()
        if getattr(self.tool_registry, '_protein_structure_configuration', None) is not None:
            direct_protein_names = set(self.tool_registry.catalog()) & {
                'inspect_protein_structure', 'extract_protein_structure_sequence',
                'compare_protein_structures'}
        direct_flux_balance = False
        if getattr(self.tool_registry, '_flux_balance_configuration', None) is not None:
            entry = self.tool_registry.catalog().get('perform_flux_balance_analysis', {})
            direct_flux_balance = entry.get('invocation_route', {}).get('kind') == 'direct'
        for resource_id, configuration in self.resources.items():
            kind = KINDS[configuration['kind']]
            resource_role = {'api': 'launch_api', 'local': 'launch_local', 'hpc': 'launch_hpc'}[kind]
            launch = (self.api_execution.operation_contracts(resource_id, 'launch_api')
                      if kind == 'api' else operation_catalog(kind))
            results = (self.api_execution.operation_contracts(resource_id, 'results')
                       if kind == 'api' else native_result_operation_catalog())
            for entry_role, owner_role, entries in (
                    ('launch', resource_role, launch), ('results', 'results', results)):
                for entry in entries:
                    key = entry['name'], kind
                    route = {'entry_role': entry_role, 'resource_id': resource_id,
                             'resource_role': owner_role}
                    if key not in contracts:
                        contracts[key] = {name: deepcopy(entry[name])
                            for name in ('name', 'description', 'input_schema')}
                        if 'instructions' in entry:
                            contracts[key]['instructions'] = entry['instructions']
                        contracts[key].update(resources=kind,
                            invocation_route={'kind': 'commission', 'routes': []})
                    elif canonical(contracts[key]['input_schema']) != canonical(entry['input_schema']):
                        raise ValueError('execution_resource_operation_contract_conflict:' + entry['name'])
                    if route not in contracts[key]['invocation_route']['routes']:
                        contracts[key]['invocation_route']['routes'].append(route)
            if kind == 'api':
                service = self.api_execution.services.get(resource_id)
                if (service is not None and service.service == 'bvbrc_appservice'
                        and ('bvbrc_homology', '1') in service.scientific_adapters):
                    from .library.bvbrc_homology_tool_info import homology_tool_contracts
                    for entry in homology_tool_contracts(resource_id=resource_id,
                            assignment_schema=self.api_execution.assignment_schema(resource_id)):
                        key = entry['name'], kind
                        if key not in contracts:
                            contracts[key] = entry
                        else:
                            prior = contracts[key]
                            prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                            prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                if service is not None and service.service == 'bvbrc_appservice':
                    if ('bvbrc_genome_alignment', '1') in service.scientific_adapters:
                        from .library.bvbrc_genome_alignment_tool_info import genome_alignment_tool_contracts
                        for entry in genome_alignment_tool_contracts(resource_id=resource_id,
                                assignment_schema=self.api_execution.assignment_schema(resource_id)):
                            key = entry['name'], kind
                            if key not in contracts:
                                contracts[key] = entry
                            else:
                                prior = contracts[key]
                                prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                                prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                    if ('bvbrc_comparative_systems', '1') in service.scientific_adapters:
                        from .library.bvbrc_comparative_systems_tool_info import comparative_systems_tool_contracts
                        for entry in comparative_systems_tool_contracts(resource_id=resource_id,
                                assignment_schema=self.api_execution.assignment_schema(resource_id)):
                            key = entry['name'], kind
                            if key not in contracts:
                                contracts[key] = entry
                            else:
                                prior = contracts[key]
                                prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                                prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                    if ('bvbrc_fastqutils', '2') in service.scientific_adapters:
                        from gene_annotation_episode.bvbrc_fastqutils_tool_info import fastqutils_tool_contracts
                        for entry in fastqutils_tool_contracts(resource_id=resource_id,
                                assignment_schema=self.api_execution.assignment_schema(resource_id)):
                            key = entry['name'], kind
                            if key not in contracts:
                                contracts[key] = entry
                            else:
                                prior = contracts[key]
                                prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                                prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                    proteome_versions = tuple(version for version in ('1', '2')
                        if ('bvbrc_proteome', version) in service.scientific_adapters)
                    if proteome_versions:
                        from .library.bvbrc_proteome_tool_info import proteome_tool_contracts
                        for entry in proteome_tool_contracts(resource_id=resource_id,
                                assignment_schema=self.api_execution.assignment_schema(resource_id),
                                adapter_versions=proteome_versions):
                            key = entry['name'], kind
                            if key not in contracts:
                                contracts[key] = entry
                            else:
                                prior = contracts[key]
                                prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                                prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                    for provider in ('bvbrc_msa', 'bvbrc_metacats'):
                        if (provider, '1') not in service.scientific_adapters:
                            continue
                        from .library.bvbrc_alignment_tool_info import alignment_tool_contracts
                        for entry in alignment_tool_contracts(resource_id=resource_id,
                                assignment_schema=self.api_execution.assignment_schema(resource_id),
                                provider=provider):
                            key = entry['name'], kind
                            if key not in contracts:
                                contracts[key] = entry
                            else:
                                prior = contracts[key]
                                prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                                prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                    for provider in ('bvbrc_gene_tree', 'bvbrc_codon_tree'):
                        if (provider, '1') not in service.scientific_adapters:
                            continue
                        from .library.bvbrc_phylogeny_tool_info import phylogeny_tool_contracts
                        for entry in phylogeny_tool_contracts(resource_id=resource_id,
                                assignment_schema=self.api_execution.assignment_schema(resource_id),
                                provider=provider):
                            key = entry['name'], kind
                            if key not in contracts:
                                contracts[key] = entry
                            else:
                                prior = contracts[key]
                                prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                                prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
            native_entries = []
            if configuration.get('native_flux_balance'):
                from gene_annotation_episode.episodic_workflow.root.library.native_flux_balance_tool_info import flux_balance_tool_contracts
                native_entries.extend(entry for entry in flux_balance_tool_contracts(
                    configuration['native_flux_balance'], resource_kind=kind, resource_id=resource_id)
                    if entry['name'] != 'perform_flux_balance_analysis' or not direct_flux_balance)
            if configuration.get('native_fluorescence'):
                from gene_annotation_episode.episodic_workflow.root.library.native_fluorescence_tool_info import fluorescence_tool_contracts
                native_entries.extend(fluorescence_tool_contracts(configuration['native_fluorescence'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_expression_nmf'):
                from .library.native_expression_nmf_tool_info import expression_nmf_tool_contracts
                native_entries.extend(expression_nmf_tool_contracts(configuration['native_expression_nmf'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_macs2_peak'):
                from gene_annotation_episode.episodic_workflow.root.library.native_macs2_peak_execution import macs2_peak_tool_contracts
                native_entries.extend(macs2_peak_tool_contracts(configuration['native_macs2_peak'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_lumpy'):
                from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import lumpy_tool_contracts
                native_entries.extend(lumpy_tool_contracts(configuration['native_lumpy'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_atac_differential'):
                from gene_annotation_episode.episodic_workflow.root.library.native_atac_differential_tool_info import atac_tool_contracts
                native_entries.extend(atac_tool_contracts(configuration['native_atac_differential'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_chromatin_interactions'):
                from gene_annotation_episode.episodic_workflow.root.library.native_chromatin_interaction_tool_info import chromatin_interaction_tool_contracts
                native_entries.extend(chromatin_interaction_tool_contracts(configuration['native_chromatin_interactions'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_genomic_overlap'):
                from .library.native_genomic_overlap_tool_info import genomic_overlap_tool_contracts
                native_entries.extend(genomic_overlap_tool_contracts(configuration['native_genomic_overlap'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_protein_structure'):
                from gene_annotation_episode.episodic_workflow.root.library.native_protein_structure_tool_info import protein_structure_tool_contracts
                native_entries.extend(entry for entry in protein_structure_tool_contracts(
                    configuration['native_protein_structure'], resource_kind='local', resource_id=resource_id)
                    if entry['name'] not in direct_protein_names)
            if configuration.get('native_rna_structure'):
                from gene_annotation_episode.episodic_workflow.root.library.native_rna_structure_tool_info import rna_structure_tool_contracts
                native_entries.extend(rna_structure_tool_contracts(configuration['native_rna_structure'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_blast_standard_database'):
                from .library.native_blast_standard_database_tool_info import standard_blast_database_tool_contracts
                native_entries.extend(standard_blast_database_tool_contracts(configuration['native_blast_standard_database']['bindings'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_blast_database'):
                from .library.native_blast_database_tool_info import native_blast_database_tool_contracts
                native_entries.extend(native_blast_database_tool_contracts(configuration['native_blast_database']['bindings'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_hmmer'):
                from .library.native_hmmer_tool_info import native_hmmer_tool_contracts
                native_entries.extend(native_hmmer_tool_contracts(configuration['native_hmmer'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_blast_masking'):
                from gene_annotation_episode.episodic_workflow.root.library.native_blast_masking_tool_info import native_blast_masking_tool_contracts
                native_entries.extend(native_blast_masking_tool_contracts(configuration['native_blast_masking'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_blast_utility'):
                from gene_annotation_episode.episodic_workflow.root.library.native_blast_utility_tool_info import native_blast_utility_tool_contracts
                native_entries.extend(native_blast_utility_tool_contracts(configuration['native_blast_utility'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_blast'):
                from .library.native_blast_tool_info import native_blast_tool_contracts
                native_entries.extend(native_blast_tool_contracts(configuration['native_blast'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_infernal'):
                from .library.native_infernal_tool_info import native_infernal_tool_contracts
                native_entries.extend(native_infernal_tool_contracts(configuration['native_infernal'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_infernal_preparation'):
                from gene_annotation_episode.episodic_workflow.root.library.native_infernal_preparation_tool_info import native_infernal_preparation_tool_contracts
                native_entries.extend(native_infernal_preparation_tool_contracts(
                    configuration['native_infernal_preparation'], resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_hmmer_preparation'):
                from gene_annotation_episode.episodic_workflow.root.library.native_hmmer_preparation_tool_info import native_hmmer_preparation_tool_contracts
                native_entries.extend(native_hmmer_preparation_tool_contracts(
                    configuration['native_hmmer_preparation'], resource_kind=kind, resource_id=resource_id))
            for entry in native_entries:
                key = entry['name'], kind
                if key in contracts:
                    # Different deployment software must remain explicit in
                    # the bound request schema; combine actual alternatives.
                    prior = contracts[key]
                    if prior['description'] != entry['description']:
                        raise ValueError('execution_native_instruction_conflict:' + entry['name'])
                    sections = prior.setdefault('_native_instruction_sections', {
                        route['resource_id']: prior['instructions']
                        for route in prior['invocation_route']['routes']})
                    sections[resource_id] = entry['instructions']
                    if len(set(sections.values())) > 1:
                        prior['instructions'] = '\n\n'.join('Resource '+key+':\n'+value
                            for key, value in sections.items())
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

    def _with_selected_execution_task(self, context, value):
        """Detach original selected work without changing its commission."""
        assignment = plain(context.assignment)
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_request_binding import (is_compact_assignment as is_macs2_assignment,
            is_compact_launch as is_macs2_launch, read_request_binding as read_macs2_binding)
        compact = is_macs2_launch(assignment) or is_macs2_assignment(assignment)
        from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import (is_compact_assignment as is_lumpy_assignment,
            is_compact_launch as is_lumpy_launch, read_request_binding as read_lumpy_binding)
        if is_lumpy_launch(assignment) or is_lumpy_assignment(assignment):
            control = read_lumpy_binding(self.store, self.run_id, context.episode_id)
            requests = {row['resource_id']: row['assignment'] for row in control['requests']}
        elif compact:
            control = read_macs2_binding(self.store, self.run_id, context.episode_id)
            requests = {row['resource_id']: row['assignment'] for row in control['requests']}
        elif context.role == 'launch':
            requests = assignment.get('requests')
            if not isinstance(requests, dict) or not requests:
                return value
        elif context.role in {'launch_local', 'launch_api'}:
            requests = {assignment.get('resource_id'): assignment}
        elif context.role == 'results':
            target = self._target(context) if self.local_file_sources.applies(context) else value.get('execution_target', {})
            requests = {target.get('resource_id'): target.get('assignment', {})}
        else:
            return value
        def profile_api(request):
            return (isinstance(request, dict)
                and KINDS.get(self.resources.get(request.get('resource_id'), {}).get('kind')) == 'api'
                and ((request.get('version') == 'api_execution_assignment_v1'
                        and request.get('service') == 'ebi_hmmer')
                    or (request.get('version') == 'api_service_assignment_v1'
                        and request.get('service') == 'rfam_batch')))
        if any(not profile_api(request) and (not isinstance(request, dict) or request.get('resource_kind') != 'local'
                or not isinstance(request.get('requested_job'), dict)
                or not any(isinstance(request['requested_job'].get(kind), dict)
                    for kind in ('native_protein_structure', 'native_macs2_peak', 'native_lumpy',
                        'native_genomic_overlap', 'native_chromatin_interactions',
                        'native_atac_differential', 'native_expression_nmf',
                        'native_hmmer', 'native_infernal',
                        'native_hmmer_preparation', 'native_infernal_preparation')))
                for request in requests.values()):
            return value
        callback = getattr(self.services, 'scientific_parent_task', None)
        parent = None if callback is None else callback(context)
        if parent is None:
            return value
        selected = []
        for resource_id, request in requests.items():
            if profile_api(request):
                from gene_annotation_episode.episodic_workflow.root.execution_prompt import select_profile_api_execution_values
                # Validate the display operands without changing their original
                # assignment or calling a provider, parser or calculator.
                if (request['resource_id'] != resource_id
                        or select_profile_api_execution_values(request) is None):
                    return value
                selected.append({'resource_id': resource_id, 'resource_kind': 'api',
                    'endpoint': deepcopy(request.get('endpoint')),
                    'constraints': deepcopy(request.get('constraints', {})),
                    'job': deepcopy(request), 'resource': self._resource_information(resource_id)})
                continue
            kind = next(kind for kind in ('native_macs2_peak', 'native_lumpy', 'native_genomic_overlap',
                'native_chromatin_interactions', 'native_atac_differential',
                'native_expression_nmf', 'native_protein_structure',
                'native_hmmer', 'native_infernal',
                'native_hmmer_preparation', 'native_infernal_preparation')
                if isinstance(request['requested_job'].get(kind), dict))
            job = deepcopy(request['requested_job'][kind])
            if kind == 'native_lumpy':
                from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import scientific_job_view
                job = scientific_job_view(job)
            elif kind == 'native_macs2_peak':
                from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_presentation import macs2_peak_scientific_job_view
                job = macs2_peak_scientific_job_view(job)
            elif kind == 'native_genomic_overlap':
                from gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_presentation import genomic_overlap_scientific_job_view
                job = genomic_overlap_scientific_job_view(job)
            elif kind == 'native_chromatin_interactions':
                from gene_annotation_episode.episodic_workflow.root.library.chromatin_interaction_presentation import chromatin_scientific_job_view
                job = chromatin_scientific_job_view(job)
            elif kind == 'native_atac_differential':
                from gene_annotation_episode.episodic_workflow.root.library.atac_differential_presentation import atac_scientific_job_view
                job = atac_scientific_job_view(job)
            elif kind == 'native_expression_nmf':
                from gene_annotation_episode.episodic_workflow.root.library.expression_nmf_presentation import expression_nmf_scientific_job_view
                job = expression_nmf_scientific_job_view(job)
            elif kind in ('native_hmmer', 'native_infernal',
                    'native_hmmer_preparation', 'native_infernal_preparation'):
                from gene_annotation_episode.episodic_workflow.root.library.native_profile_presentation import native_profile_scientific_job_view
                job = native_profile_scientific_job_view(job)
            selected.append({'resource_id': resource_id, 'resource_kind': request['resource_kind'],
                'endpoint': deepcopy(request.get('endpoint')),
                'constraints': deepcopy(request.get('constraints', {})), 'job': job,
                'resource': self._resource_information(resource_id)})
        value['selected_execution_task'] = deepcopy({'version': 'selected_execution_task_v1',
            'scientific_question': parent['scientific_question'],
            'selected_tool_info': parent['selected_tool_info'], 'requests': selected,
            'constraints': assignment.get('constraints', {}), 'selector': assignment.get('selector'),
            'result_description': value.get('execution_target_description')})
        return value

