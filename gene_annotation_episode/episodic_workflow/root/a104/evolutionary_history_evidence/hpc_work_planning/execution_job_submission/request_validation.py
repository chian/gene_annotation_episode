"""Private A104 Launch request validation."""
from __future__ import annotations
from .contracts import ASSIGNMENT_SCHEMA, GENERIC_REQUESTED_JOB_SCHEMA, KINDS, confined, deepcopy, preparation_job_schemas, requested_job_schemas, validate_assignment

class LaunchRequestValidation:

    def _request_schema(self, resource_id, *, selected, internal=False, compact=True):
        kind = KINDS[self.resources[resource_id]['kind']]
        schema = deepcopy(self.api_execution.assignment_schema(resource_id) if kind == 'api' else ASSIGNMENT_SCHEMA)
        if schema.get('type') != 'object' or not isinstance(schema.get('properties'), dict):
            raise ValueError('concrete_execution_assignment_schema_required')
        schema['properties']['resource_id'] = {'type': 'string', 'const': resource_id}
        if kind != 'api':
            schema['properties']['resource_kind'] = {'type': 'string', 'const': kind}
            alternatives = [*requested_job_schemas(self.resources[resource_id], kind, resource_id), *preparation_job_schemas(self.resources[resource_id], kind, resource_id)]
            schema['properties']['requested_job'] = {'anyOf': [deepcopy(GENERIC_REQUESTED_JOB_SCHEMA), *alternatives]} if alternatives else deepcopy(GENERIC_REQUESTED_JOB_SCHEMA)
        if selected and 'resource_id' not in schema['required']:
            schema['required'].append('resource_id')
        return schema

    def _validate_request(self, value, *, resource_id=None):
        resource_id = resource_id or value.get('resource_id')
        if resource_id not in self.resources:
            raise ValueError('execution_resource_not_bound')
        config = self.resources[resource_id]
        kind = KINDS[config['kind']]
        value = self.api_execution.validate_assignment(value) if kind == 'api' else validate_assignment(value)
        if value.get('resource_id', resource_id) != resource_id:
            raise ValueError('execution_resource_identity_conflict')
        if kind != 'api':
            if value['resource_kind'] != kind:
                raise ValueError('execution_resource_kind_conflict')
            confined(value['workspace'], config['workspace'])
            operations = self._practical[resource_id]._operations(kind)
            validator = getattr(operations, 'validate_assignment', None)
            if validator is not None:
                validator({**value, 'resource_id': resource_id})
        return value

    @staticmethod
    def _constraints(constraints):
        for key in ('allowed_resource_ids', 'allowed_kinds'):
            if key in constraints and (not isinstance(constraints[key], list) or any((not isinstance(item, str) or not item for item in constraints[key]))):
                raise ValueError('invalid_execution_resource_constraints')

    def _permitted(self, assignment, resource_id):
        constraints = assignment['constraints']
        kind = KINDS[self.resources[resource_id]['kind']]
        return resource_id in assignment['requests'] and ('allowed_resource_ids' not in constraints or resource_id in constraints['allowed_resource_ids']) and ('allowed_kinds' not in constraints or kind in constraints['allowed_kinds']) and ('resource_id' not in constraints or resource_id == constraints['resource_id']) and ('kind' not in constraints or kind == constraints['kind'])

    def _versions(self, versions, scope, *, context):
        from gene_annotation_episode.episodic_workflow.root.a104.library.execution_input_versions import validate_execution_input_versions
        return validate_execution_input_versions(self, versions, scope, context=context)
