"""Private A102 native execution from parent."""
from __future__ import annotations
from .contracts import ASSIGNMENT_SCHEMA, GENERIC_REQUESTED_JOB_SCHEMA, INPUT_VERSION_SCHEMA, KINDS, LAUNCH_VERSION, LOCAL_FILE_SOURCE_SELECTOR_SCHEMA, RESULTS_SCHEMA, ROLE_KINDS, SELECTION_SCHEMA, checked, confined, deepcopy, is_file_source_selector, is_native_protein_structure_target, obj, plain, requested_job_schemas, validate_assignment

class NativeAssignment:

    def child_assignment_schema(self, parent, role):
        if parent.role == 'launch' and role == 'launch_hpc' and any((ancestor == 'hpc' for ancestor, _ in parent.path)):
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

    def _permitted(self, assignment, resource_id):
        constraints = assignment['constraints']
        kind = KINDS[self.resources[resource_id]['kind']]
        return resource_id in assignment['requests'] and ('allowed_resource_ids' not in constraints or resource_id in constraints['allowed_resource_ids']) and ('allowed_kinds' not in constraints or kind in constraints['allowed_kinds']) and ('resource_id' not in constraints or resource_id == constraints['resource_id']) and ('kind' not in constraints or kind == constraints['kind'])

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        selected = checked(selection, self.assignment_schema(role, internal=True), 'invalid_execution_assignment')
        # Preserve the original parent-role read before own request validation.
        parent.role
        selected = self._validate_request(selected)
        if ROLE_KINDS[role] != KINDS[self.resources[selected['resource_id']]['kind']]:
            raise ValueError('execution_resource_kind_conflict')
        if parent.role != 'launch':
            raise ValueError('resource_child_role_owned_by_launch')
        original = self._launch(plain(parent.assignment))
        from gene_annotation_episode.episodic_workflow.root.a102.protein_structure_operands import validate_protein_structure_job_inputs
        validate_protein_structure_job_inputs(self.store, parent, selected, returns=self.native_protein_structure_returns)
        self._versions(original['immutable_input_versions'], scope, context=parent)
        return selected

    def _request_schema(self, resource_id, *, selected, internal=False, compact=True):
        kind = KINDS[self.resources[resource_id]['kind']]
        schema = deepcopy(self.api_execution.assignment_schema(resource_id) if kind == 'api' else ASSIGNMENT_SCHEMA)
        if schema.get('type') != 'object' or not isinstance(schema.get('properties'), dict):
            raise ValueError('concrete_execution_assignment_schema_required')
        schema['properties']['resource_id'] = {'type': 'string', 'const': resource_id}
        if kind != 'api':
            schema['properties']['resource_kind'] = {'type': 'string', 'const': kind}
            alternatives = []
            protein = self.resources[resource_id].get('native_protein_structure', [])
            if protein:
                from gene_annotation_episode.episodic_workflow.root.a102.native_protein_structure_tool_info import protein_structure_tool_contracts
                alternatives.extend((row['input_schema'] for row in protein_structure_tool_contracts(protein, resource_kind='local', resource_id=resource_id)))
            alternatives.extend(requested_job_schemas(self.resources[resource_id], kind, resource_id))
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
        """Preserve the original job identity across its scientific return."""
        if parent is not None and parent.path[-1][0] == 'structural_homology_evidence' and getattr(self.services, 'annotation_task_required', lambda: False)():
            return ()
        return ()

    def initial_references(self, context):
        if context.role != 'results':
            from gene_annotation_episode.episodic_workflow.root.a102.protein_structure_operands import validate_protein_structure_job_inputs
            assignment = plain(context.assignment)
            requests = assignment.get('requests', {}).values() if context.role == 'launch' else [assignment] if context.role in ROLE_KINDS else []
            references = []
            for request in requests:
                references.extend(validate_protein_structure_job_inputs(self.store, context, request, returns=self.native_protein_structure_returns))
            return list(dict.fromkeys(references))
        assignment = plain(context.assignment)
        target = self._target(context)
        if self.native_protein_structure_results.applies(context):
            self._selector(assignment, target)
            from gene_annotation_episode.episodic_workflow.root.a102.protein_structure_operands import validate_protein_structure_selected_inputs
            return validate_protein_structure_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref'], returns=self.native_protein_structure_returns)
        return [assignment['handoff_ref']]

