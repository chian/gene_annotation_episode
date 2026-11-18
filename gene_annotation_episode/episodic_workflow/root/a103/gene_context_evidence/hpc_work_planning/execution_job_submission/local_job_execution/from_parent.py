"""Private A103 native execution from parent."""
from __future__ import annotations
from .contracts import ASSIGNMENT_SCHEMA, BLAST_GRADED_REQUEST_SCHEMA, BLAST_GRADED_REQUEST_VERSION, GENERIC_REQUESTED_JOB_SCHEMA, INPUT_VERSION_SCHEMA, KINDS, LAUNCH_VERSION, LOCAL_FILE_SOURCE_SELECTOR_SCHEMA, RESULTS_SCHEMA, ROLE_KINDS, SELECTION_SCHEMA, checked, confined, deepcopy, is_file_source_selector, is_native_blast_database_target, is_standard_blast_database_target, launch_request_schema, obj, plain, preparation_job_schemas, requested_job_schemas, result_selector_conditions, validate_assignment

class NativeAssignment:

    def child_assignment_schema(self, parent, role):
        """Describe this selected child's original admitted assignment."""
        parent.role
        return self.assignment_schema(role)

    def assignment_schema(self, role, *, internal=False):
        self.credit_kind(role)
        alternatives = [self._request_schema(key, selected=True, internal=internal) for key, config in self.resources.items() if KINDS[config['kind']] == ROLE_KINDS[role]]
        return {'anyOf': alternatives} if alternatives else {'not': {}}

    def _permitted(self, assignment, resource_id):
        constraints = assignment['constraints']
        kind = KINDS[self.resources[resource_id]['kind']]
        return resource_id in assignment['requests'] and ('allowed_resource_ids' not in constraints or resource_id in constraints['allowed_resource_ids']) and ('allowed_kinds' not in constraints or kind in constraints['allowed_kinds']) and ('resource_id' not in constraints or resource_id == constraints['resource_id']) and ('kind' not in constraints or kind == constraints['kind'])

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        selected = checked(selection, self.assignment_schema(role, internal=True), 'invalid_execution_assignment')
        # Preserve the original parent-role read before resource validation.
        parent.role
        selected = self._validate_request(selected)
        if ROLE_KINDS[role] != KINDS[self.resources[selected['resource_id']]['kind']]:
            raise ValueError('execution_resource_kind_conflict')
        if parent.role != 'launch':
            raise ValueError('resource_child_role_owned_by_launch')
        original = self._launch(plain(parent.assignment))
        self._masking_inputs(parent, selected)
        self._utility_inputs(parent, selected)
        self._versions(original['immutable_input_versions'], scope, context=parent)
        from gene_annotation_episode.episodic_workflow.root.a103.native_blast_database_result_publication import validate_native_job_inputs
        from gene_annotation_episode.episodic_workflow.root.a103.native_blast_standard_database_result_publication import validate_standard_blast_job_inputs
        validate_native_job_inputs(self.store, parent, selected)
        validate_standard_blast_job_inputs(self.store, parent, selected)
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
        from .parent_launch_contract import parent_launch_schema
        value = checked(value, parent_launch_schema(self), 'invalid_execution_launch_assignment')
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

    def required_return_sources(self, parent, role):
        """Preserve the original job identity across a scientific owner return."""
        if parent is not None and parent.path[-1][0] == 'gene_context_evidence' and getattr(self.services, 'annotation_task_required', lambda: False)():
            return ()
        return ()

    def initial_references(self, context):
        if context.role != 'results':
            assignment = plain(context.assignment)
            requests = assignment.get('requests', {}).values() if context.role == 'launch' else [assignment] if context.role == 'launch_local' else []
            references = []
            for request in requests:
                references.extend(self._masking_inputs(context, request))
                references.extend(self._utility_inputs(context, request))
            return list(dict.fromkeys(references))
        assignment = plain(context.assignment)
        target = self._target(context)
        if self.native_blast_masking_results.applies(context):
            self._selector(assignment, target)
            return self.native_blast_masking_results.validate_selected_inputs(context, assignment)
        if self.native_blast_utility_results.applies(context):
            self._selector(assignment, target)
            return self.native_blast_utility_results.validate_selected_inputs(context, assignment)
        selected = [assignment['handoff_ref']]
        if is_standard_blast_database_target(target):
            from gene_annotation_episode.episodic_workflow.root.a103.native_blast_standard_database_result_publication import validate_standard_blast_selected_inputs
            selected.extend(validate_standard_blast_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref']))
        if is_native_blast_database_target(target):
            from gene_annotation_episode.episodic_workflow.root.a103.native_blast_database_result_publication import validate_selected_inputs
            selected.extend(validate_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref']))
        return list(dict.fromkeys(selected))

