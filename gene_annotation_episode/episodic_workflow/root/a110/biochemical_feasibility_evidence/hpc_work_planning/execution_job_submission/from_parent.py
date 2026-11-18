"""Private A110 Launch from parent"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_records import ASSIGNMENT_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_records import GENERIC_REQUESTED_JOB_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a110.resource_records import INPUT_VERSION_SCHEMA
from .binding_roles import KINDS
from .launch_assignment_records import LAUNCH_VERSION
from gene_annotation_episode.episodic_workflow.root.a110.local_file_capture_results import SELECTOR_SCHEMA as LOCAL_FILE_SOURCE_SELECTOR_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a110.library.execution_result_contract import RESULTS_SCHEMA
from .binding_roles import ROLE_KINDS
from gene_annotation_episode.episodic_workflow.root.a110.launch_instructions import SELECTION_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import checked
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a110.local_file_capture_results import is_file_source_selector
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import obj
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain

class LaunchFromParent:

    def child_assignment_schema(self, parent, role):
        if parent.role == 'launch' and False:
            pass
        return self.assignment_schema(role)

    def assignment_schema(self, role, *, internal=False):
        self.credit_kind(role)
        schema = obj({'version': {'const': LAUNCH_VERSION}, 'requests': {'type': 'object', 'properties': {key: self._request_schema(key, selected=False, internal=internal, compact=False) for key in self.resources}, 'minProperties': 1, 'additionalProperties': False}, 'immutable_input_versions': {'type': 'array', 'items': deepcopy(INPUT_VERSION_SCHEMA)}, 'constraints': {'type': 'object'}})
        schema['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
        if any((value.get('native_flux_balance') for value in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import launch_assignment_schema
            return {'anyOf': [schema, launch_assignment_schema(self.resources)]}
        return schema

    def _permitted(self, assignment, resource_id):
        constraints = assignment['constraints']
        kind = KINDS[self.resources[resource_id]['kind']]
        return resource_id in assignment['requests'] and ('allowed_resource_ids' not in constraints or resource_id in constraints['allowed_resource_ids']) and ('allowed_kinds' not in constraints or kind in constraints['allowed_kinds']) and ('resource_id' not in constraints or resource_id == constraints['resource_id']) and ('kind' not in constraints or kind == constraints['kind'])

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        selected = checked(selection, self.assignment_schema(role, internal=True), 'invalid_execution_assignment')
        if parent.role in ('hpc', 'hpc_execution') and True:
            from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.hpc_work_planning.to_child_execution_job_submission import authenticate_launch
            authenticate_launch(parent, selected, operation_key, self.directory)
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import is_compact_assignment, is_compact_launch, read_request_binding
        if True and is_compact_launch(selected):
            return self.flux_balance_requests.preview(parent, selected)[0]
        if False and is_compact_assignment(selected):
            pass
        selected = self._launch(selected, scope=scope)
        for request in selected['requests'].values():
            self._flux_balance_inputs(parent, request, input_versions=selected['immutable_input_versions'])
        self._versions(selected['immutable_input_versions'], scope, context=parent, flux_balance_assignments=selected['requests'].values())
        return selected

    def _request_schema(self, resource_id, *, selected, internal=False, compact=True):
        kind = KINDS[self.resources[resource_id]['kind']]
        schema = deepcopy(ASSIGNMENT_SCHEMA)
        if schema.get('type') != 'object' or not isinstance(schema.get('properties'), dict):
            raise ValueError('concrete_execution_assignment_schema_required')
        schema['properties']['resource_id'] = {'type': 'string', 'const': resource_id}
        schema['properties']['resource_kind'] = {'type': 'string', 'const': kind}
        alternatives = []
        if internal and self.resources[resource_id].get('native_flux_balance'):
            from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_contracts import flux_balance_schema
            for binding in self.resources[resource_id]['native_flux_balance']:
                alternatives.append({'allOf': [flux_balance_schema('FBARequestedJob'), {'properties': {'native_flux_balance': {'properties': {'operation': {'const': binding['operation']}, 'mode': {'const': binding['mode']}, 'software': {'const': deepcopy(binding['software'])}, 'model_input': {'properties': {'format': {'enum': deepcopy(binding['model_formats'])}}}}}}}]})
        schema['properties']['requested_job'] = {'anyOf': [deepcopy(GENERIC_REQUESTED_JOB_SCHEMA), *alternatives]} if alternatives else deepcopy(GENERIC_REQUESTED_JOB_SCHEMA)
        if selected and 'resource_id' not in schema['required']:
            schema['required'].append('resource_id')
        if compact and kind == 'local' and self.resources[resource_id].get('native_flux_balance'):
            from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import resource_assignment_schema
            return {'anyOf': [schema, resource_assignment_schema(resource_id, selected=selected)]}
        return schema

    def _launch(self, value, *, scope=None):
        value = checked(value, self.assignment_schema('launch', internal=True), 'invalid_execution_launch_assignment')
        for resource_id, request in value['requests'].items():
            self._validate_request(request, resource_id=resource_id)
        self._constraints(value['constraints'])
        return value
