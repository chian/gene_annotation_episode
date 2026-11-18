"""Private A110 Results received_launch_requests"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_records import ASSIGNMENT_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_records import GENERIC_REQUESTED_JOB_SCHEMA
from .binding_roles import KINDS
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import checked
from copy import deepcopy

class ResultsReceivedLaunchRequests:

    def _permitted(self, assignment, resource_id):
        constraints = assignment['constraints']
        kind = KINDS[self.resources[resource_id]['kind']]
        return resource_id in assignment['requests'] and ('allowed_resource_ids' not in constraints or resource_id in constraints['allowed_resource_ids']) and ('allowed_kinds' not in constraints or kind in constraints['allowed_kinds']) and ('resource_id' not in constraints or resource_id == constraints['resource_id']) and ('kind' not in constraints or kind == constraints['kind'])

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
