"""Private A107 Results resource_information"""
from __future__ import annotations
from .binding_roles import KINDS
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import canonical
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a107.a107_execution_bindings import homology_api_contracts
from gene_annotation_episode.episodic_workflow.root.a107.a107_execution_bindings import native_operation_contracts
from .result_records import native_result_operation_catalog
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import obj
from gene_annotation_episode.episodic_workflow.root.a107.library.execution_operation_information import operation_catalog
from gene_annotation_episode.episodic_workflow.root.a107.a107_execution_bindings import preparation_operation_contracts

class ResultsResourceInformation:

    def resource_tool_contracts(self):
        """Declare only bound A107 launch, result and homology operations."""
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
            if configuration.get('native_expression_nmf'):
                from gene_annotation_episode.episodic_workflow.root.a107.native_expression_nmf_tool_info import expression_nmf_tool_contracts
                for entry in expression_nmf_tool_contracts(configuration['native_expression_nmf'], resource_kind=kind, resource_id=resource_id):
                    add(entry, kind)
            additional = []
            if configuration.get('native_rna_structure'):
                from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_tool_info import rna_structure_tool_contracts
                additional.extend(rna_structure_tool_contracts(configuration['native_rna_structure'], resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_infernal'):
                from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_tool_info import native_infernal_tool_contracts
                additional.extend(native_infernal_tool_contracts(configuration['native_infernal'], resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_infernal_preparation'):
                from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_preparation_tool_info import native_infernal_preparation_tool_contracts
                additional.extend(native_infernal_preparation_tool_contracts(configuration['native_infernal_preparation'], resource_kind=kind, resource_id=resource_id))
            for entry in (*native_operation_contracts(configuration, kind, resource_id), *preparation_operation_contracts(configuration, kind, resource_id), *additional):
                add(entry, kind)
        for entry in contracts.values():
            entry.pop('_native_schemas', None)
        return [contracts[key] for key in sorted(contracts)]
