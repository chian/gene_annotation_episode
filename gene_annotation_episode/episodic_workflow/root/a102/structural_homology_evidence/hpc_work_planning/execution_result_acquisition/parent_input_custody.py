"""Private A102 Results parent input custody."""
from __future__ import annotations
from .execution_contracts import ASSIGNMENT_SCHEMA, GENERIC_REQUESTED_JOB_SCHEMA, KINDS, canonical, checked, confined, deepcopy, json, plain, requested_job_schemas, validate_assignment

class ResultsParentInputCustody:

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

    def _launch(self, value, *, scope=None):
        value = checked(value, self.assignment_schema('launch', internal=True), 'invalid_execution_launch_assignment')
        for resource_id, request in value['requests'].items():
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
