"""Private A106 launch_api from parent."""
from __future__ import annotations
from .execution_contracts import INPUT_VERSION_SCHEMA, KINDS, LAUNCH_VERSION, RESULTS_SCHEMA, SELECTION_SCHEMA, checked, deepcopy, obj, plain

from gene_annotation_episode.episodic_workflow.root.a106.library.standalone_api_context import standalone_api_context

class OperationalAssignment:

    def _api_context(self, api, context, *, verify_artifacts=True):
        if context.run_id != api.run_id:
            raise ValueError('api_execution_run_conflict')
        if context.role != 'launch_api':
            return standalone_api_context(api, context, verify_artifacts=verify_artifacts)
        assignment = api.validate_assignment(context.assignment, scope=context.scope)
        return (assignment, api.services[assignment['resource_id']], None)


    def child_assignment_schema(self, parent, role):
        return self.assignment_schema(role)

    def assignment_schema(self, role, *, internal=False):
        self.credit_kind(role)
        alternatives = [self._request_schema(key, selected=True, internal=internal) for key in self.resources]
        return {'anyOf': alternatives} if alternatives else {'not': {}}

    def _permitted(self, assignment, resource_id):
        constraints = assignment['constraints']
        kind = KINDS[self.resources[resource_id]['kind']]
        return resource_id in assignment['requests'] and ('allowed_resource_ids' not in constraints or resource_id in constraints['allowed_resource_ids']) and ('allowed_kinds' not in constraints or kind in constraints['allowed_kinds']) and ('resource_id' not in constraints or resource_id == constraints['resource_id']) and ('kind' not in constraints or kind == constraints['kind'])

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        self.credit_kind(role)
        selected = checked(selection, self.assignment_schema('launch_api', internal=True), 'invalid_execution_assignment')
        selected = self.api_execution.validate_assignment(self._validate_request(selected), scope=scope)
        if parent.role != 'launch':
            raise ValueError('resource_child_role_owned_by_launch')
        original = self._launch(plain(parent.assignment))
        self._versions(original['immutable_input_versions'], scope, context=parent)
        return selected

    def _request_schema(self, resource_id, *, selected, internal=False, compact=True):
        schema = deepcopy(self.api_execution.assignment_schema(resource_id))
        if schema.get('type') != 'object' or not isinstance(schema.get('properties'), dict):
            raise ValueError('concrete_execution_assignment_schema_required')
        schema['properties']['resource_id'] = {'type': 'string', 'const': resource_id}
        if selected and 'resource_id' not in schema['required']:
            schema['required'].append('resource_id')
        return schema

    def _validate_request(self, value, *, resource_id=None):
        resource_id = resource_id or value.get('resource_id')
        if resource_id not in self.resources:
            raise ValueError('execution_resource_not_bound')
        value = self.api_execution.validate_assignment(value)
        if value.get('resource_id', resource_id) != resource_id:
            raise ValueError('execution_resource_identity_conflict')
        return value

    def _launch(self, value, *, scope=None):
        value = checked(value, self._parent_launch_assignment_schema(internal=True), 'invalid_execution_launch_assignment')
        for resource_id, request in value['requests'].items():
            self._validate_request(request, resource_id=resource_id)
            if scope is not None:
                self.api_execution.validate_assignment(request, scope=scope)
        self._constraints(value['constraints'])
        return value

    @staticmethod
    def _constraints(constraints):
        for key in ('allowed_resource_ids', 'allowed_kinds'):
            if key in constraints and (not isinstance(constraints[key], list) or any((not isinstance(item, str) or not item for item in constraints[key]))):
                raise ValueError('invalid_execution_resource_constraints')

    def initial_references(self, context):
        self.credit_kind(context.role)
        return []
