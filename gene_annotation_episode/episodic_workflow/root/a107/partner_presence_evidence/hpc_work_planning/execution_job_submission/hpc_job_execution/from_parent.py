from __future__ import annotations
from .execution_contracts import ASSIGNMENT_SCHEMA
from .execution_contracts import BLAST_GRADED_REQUEST_SCHEMA
from .execution_contracts import BLAST_GRADED_REQUEST_VERSION
from .execution_contracts import GENERIC_REQUESTED_JOB_SCHEMA
from .execution_contracts import KINDS
from .execution_contracts import ROLE_KINDS
from .execution_contracts import checked
from .execution_contracts import deepcopy
from .execution_contracts import json
from .execution_contracts import plain
from .execution_contracts import preparation_job_schemas
from .execution_contracts import requested_job_schemas
from .execution_contracts import _validate_request
from .execution_contracts import obj
from .execution_contracts import SELECTION_SCHEMA
from .execution_contracts import INPUT_VERSION_SCHEMA
from .execution_contracts import launch_request_schema
from .execution_contracts import LAUNCH_VERSION

class NativeParentRequests:

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
    _validate_request = _validate_request

    def _launch(self, value, *, scope=None):
        from gene_annotation_episode.episodic_workflow.root.a107.library.execution_request_compatibility import launch_assignment_schema
        value = checked(value, launch_assignment_schema(self, True, _read_request_INPUT_VERSION_SCHEMA=lambda: INPUT_VERSION_SCHEMA, _read_request_LAUNCH_VERSION=lambda: LAUNCH_VERSION, _read_request_SELECTION_SCHEMA=lambda: SELECTION_SCHEMA, _read_request_deepcopy=lambda: deepcopy, _read_request_launch_request_schema=lambda: launch_request_schema, _read_request_obj=lambda: obj), 'invalid_execution_launch_assignment')
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

    def child_assignment_schema(self, parent, role):
        """A frozen HPC launch exposes only its already authorized request."""
        if parent.role == 'launch' and any((ancestor == 'hpc' for ancestor, _ in parent.path)):
            assignment = plain(parent.assignment)
            requests = [request for resource_id, request in assignment['requests'].items() if self._permitted(assignment, resource_id) and request.get('resource_kind') == 'hpc']
            if not requests:
                raise ValueError('frozen_hpc_launch_request_missing')
            return {'type': 'object', 'enum': requests}
        return self.assignment_schema(role)

    def assignment_schema(self, role, *, internal=False):
        self.credit_kind(role)
        alternatives = [self._request_schema(key, selected=True, internal=internal) for key, config in self.resources.items() if KINDS[config['kind']] == ROLE_KINDS[role]]
        return {'anyOf': alternatives} if alternatives else {'not': {}}

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        selected = checked(selection, self.assignment_schema(role, internal=True), 'invalid_execution_assignment')
        if parent.role in ('hpc', 'hpc_execution') and False:
            pass
        selected = self._validate_request(selected)
        if ROLE_KINDS[role] == 'api':
            selected = self.api_execution.validate_assignment(selected, scope=scope)
        if ROLE_KINDS[role] != KINDS[self.resources[selected['resource_id']]['kind']]:
            raise ValueError('execution_resource_kind_conflict')
        if parent.role != 'launch':
            raise ValueError('resource_child_role_owned_by_launch')
        original = self._launch(plain(parent.assignment))
        self._masking_inputs(parent, selected)
        self._utility_inputs(parent, selected)
        self._versions(original['immutable_input_versions'], scope, context=parent, nmf_assignments=[selected])
        from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_result_publication import validate_native_job_inputs
        from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_result_publication import validate_standard_blast_job_inputs
        from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_result_publication import validate_rna_structure_job_inputs
        validate_native_job_inputs(self.store, parent, selected)
        validate_standard_blast_job_inputs(self.store, parent, selected)
        validate_rna_structure_job_inputs(self.store, parent, selected)
        return selected
