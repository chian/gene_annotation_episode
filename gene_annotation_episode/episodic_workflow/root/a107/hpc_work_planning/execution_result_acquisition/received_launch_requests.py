"""Private A107 Results received_launch_requests"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.practical_execution_records import ASSIGNMENT_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a107.a107_blast_execution import BLAST_GRADED_REQUEST_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a107.a107_blast_execution import BLAST_GRADED_REQUEST_VERSION
from gene_annotation_episode.episodic_workflow.root.a107.practical_execution_records import GENERIC_REQUESTED_JOB_SCHEMA
from .binding_roles import KINDS
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import checked
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a107.a107_execution_bindings import preparation_job_schemas
from gene_annotation_episode.episodic_workflow.root.a107.a107_execution_bindings import requested_job_schemas

class ResultsReceivedLaunchRequests:

    def _permitted(self, assignment, resource_id):
        constraints = assignment['constraints']
        kind = KINDS[self.resources[resource_id]['kind']]
        return resource_id in assignment['requests'] and ('allowed_resource_ids' not in constraints or resource_id in constraints['allowed_resource_ids']) and ('allowed_kinds' not in constraints or kind in constraints['allowed_kinds']) and ('resource_id' not in constraints or resource_id == constraints['resource_id']) and ('kind' not in constraints or kind == constraints['kind'])

    def _request_schema(self, resource_id, *, selected, internal=False, compact=True):
        kind = KINDS[self.resources[resource_id]['kind']]
        schema = deepcopy(self.api_execution.assignment_schema(resource_id) if kind == 'api' else ASSIGNMENT_SCHEMA)
        if schema.get('type') != 'object' or not isinstance(schema.get('properties'), dict):
            raise ValueError('concrete_execution_assignment_schema_required')
        schema['properties']['resource_id'] = {'type': 'string', 'const': resource_id}
        if kind != 'api':
            schema['properties']['resource_kind'] = {'type': 'string', 'const': kind}
            alternatives = requested_job_schemas(self.resources[resource_id], kind, resource_id)
            nmf = self.resources[resource_id].get('native_expression_nmf', [])
            if nmf:
                from gene_annotation_episode.episodic_workflow.root.a107.native_expression_nmf_tool_info import expression_nmf_tool_contracts
                alternatives.extend((row['input_schema'] for row in expression_nmf_tool_contracts(nmf, resource_kind=kind, resource_id=resource_id)))
            rna = self.resources[resource_id].get('native_rna_structure', [])
            if rna:
                from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_tool_info import rna_structure_tool_contracts
                alternatives.extend((row['input_schema'] for row in rna_structure_tool_contracts(rna, resource_kind=kind, resource_id=resource_id)))
            infernal = self.resources[resource_id].get('native_infernal', [])
            if infernal:
                from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_tool_info import native_infernal_tool_contracts
                alternatives.extend((row['input_schema'] for row in native_infernal_tool_contracts(infernal, resource_kind=kind, resource_id=resource_id)))
            preparation = self.resources[resource_id].get('native_infernal_preparation', [])
            if preparation:
                from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_preparation_tool_info import native_infernal_preparation_tool_contracts
                alternatives.extend((row['input_schema'] for row in native_infernal_preparation_tool_contracts(preparation, resource_kind=kind, resource_id=resource_id)))
            alternatives.extend(preparation_job_schemas(self.resources[resource_id], kind, resource_id))
            schema['properties']['requested_job'] = {'anyOf': [deepcopy(GENERIC_REQUESTED_JOB_SCHEMA), *alternatives]} if alternatives else deepcopy(GENERIC_REQUESTED_JOB_SCHEMA)
        if selected and 'resource_id' not in schema['required']:
            schema['required'].append('resource_id')
        return schema

    def _launch(self, value, *, scope=None):
        value = checked(value, self.assignment_schema('launch', internal=True), 'invalid_execution_launch_assignment')
        for resource_id, request in value['requests'].items():
            if request.get('version') == BLAST_GRADED_REQUEST_VERSION:
                checked(request, BLAST_GRADED_REQUEST_SCHEMA, 'blast_database_grader_return_request_invalid')
                if request['resource_id'] != resource_id or self.resources[resource_id].get('service') != 'ncbi_blast':
                    raise ValueError('blast_database_grader_resource_conflict')
                continue
            self._validate_request(request, resource_id=resource_id)
            if scope is not None and KINDS[self.resources[resource_id]['kind']] == 'api':
                self.api_execution.validate_assignment(request, scope=scope)
        self._constraints(value['constraints'])
        return value

    @staticmethod
    def _constraints(constraints):
        for key in ('allowed_resource_ids', 'allowed_kinds'):
            if key in constraints and (not isinstance(constraints[key], list) or any((not isinstance(item, str) or not item for item in constraints[key]))):
                raise ValueError('invalid_execution_resource_constraints')
