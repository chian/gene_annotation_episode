"""Private A101 launch from parent."""
from __future__ import annotations
from .execution_contracts import ASSIGNMENT_SCHEMA, BLAST_GRADED_REQUEST_SCHEMA, BLAST_GRADED_REQUEST_VERSION, GENERIC_REQUESTED_JOB_SCHEMA, INPUT_VERSION_SCHEMA, KINDS, LAUNCH_VERSION, LOCAL_FILE_SOURCE_SELECTOR_SCHEMA, RESULTS_SCHEMA, ROLE_KINDS, SELECTION_SCHEMA, checked, confined, deepcopy, is_file_source_selector, is_native_blast_database_target, is_standard_blast_database_target, launch_request_schema, obj, plain, preparation_job_schemas, requested_job_schemas, result_selector_conditions, validate_assignment

class OperationalAssignment:

    def child_assignment_schema(self, parent, role):
        """A frozen HPC launch exposes only its already authorized request."""
        if parent.role == 'launch' and role == 'launch_hpc' and any((ancestor == 'hpc' for ancestor, _ in parent.path)):
            assignment = plain(parent.assignment)
            requests = [request for resource_id, request in assignment['requests'].items() if self._permitted(assignment, resource_id) and request.get('resource_kind') == 'hpc']
            if not requests:
                raise ValueError('frozen_hpc_launch_request_missing')
            return {'type': 'object', 'enum': requests}
        return self.assignment_schema(role)

    def assignment_schema(self, role, *, internal=False):
        self.credit_kind(role)
        schema = obj({'version': {'const': LAUNCH_VERSION}, 'requests': {'type': 'object', 'properties': {key: launch_request_schema(self._request_schema(key, selected=False, internal=internal, compact=False), key, self.resources[key].get('service')) for key in self.resources}, 'minProperties': 1, 'additionalProperties': False}, 'immutable_input_versions': {'type': 'array', 'items': deepcopy(INPUT_VERSION_SCHEMA)}, 'constraints': {'type': 'object'}})
        schema['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
        return schema

    def _permitted(self, assignment, resource_id):
        constraints = assignment['constraints']
        kind = KINDS[self.resources[resource_id]['kind']]
        return resource_id in assignment['requests'] and ('allowed_resource_ids' not in constraints or resource_id in constraints['allowed_resource_ids']) and ('allowed_kinds' not in constraints or kind in constraints['allowed_kinds']) and ('resource_id' not in constraints or resource_id == constraints['resource_id']) and ('kind' not in constraints or kind == constraints['kind'])

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        self.credit_kind(role)
        selected = checked(selection, self.assignment_schema('launch', internal=True), 'invalid_execution_assignment')
        if parent.role in ('hpc', 'hpc_execution'):
            from gene_annotation_episode.episodic_workflow.root.a101.hpc_launch_authentication import authenticate_launch
            authenticate_launch(parent, selected, operation_key, self.directory)
        selected = self._launch(selected, scope=scope)
        for request in selected['requests'].values():
            self._masking_inputs(parent, request)
            self._utility_inputs(parent, request)
        self._versions(selected['immutable_input_versions'], scope, context=parent)
        from gene_annotation_episode.episodic_workflow.root.a101.native_blast_database_result_publication import validate_native_job_inputs
        from gene_annotation_episode.episodic_workflow.root.a101.native_blast_standard_database_result_publication import validate_standard_blast_job_inputs
        for request in selected['requests'].values():
            validate_native_job_inputs(self.store, parent, request)
            validate_standard_blast_job_inputs(self.store, parent, request)
        return selected

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

    def _launch(self, value, *, scope=None):
        value = checked(value, self._parent_launch_assignment_schema(internal=True), 'invalid_execution_launch_assignment')
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

    def initial_references(self, context):
        self.credit_kind(context.role)
        assignment = plain(context.assignment)
        requests = assignment.get('requests', {}).values()
        references = []
        for request in requests:
            references.extend(self._masking_inputs(context, request))
            references.extend(self._utility_inputs(context, request))
        return list(dict.fromkeys(references))
