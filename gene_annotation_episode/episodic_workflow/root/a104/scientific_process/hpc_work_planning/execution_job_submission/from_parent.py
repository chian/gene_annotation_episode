"""Private A104 Launch from parent."""
from __future__ import annotations
from .contracts import BLAST_GRADED_REQUEST_SCHEMA, BLAST_GRADED_REQUEST_VERSION, INPUT_VERSION_SCHEMA, KINDS, LAUNCH_VERSION, SELECTION_SCHEMA, checked, deepcopy, launch_request_schema, obj, plain

class LaunchAssignment:

    def child_assignment_schema(self, parent, role):
        """Describe this selected child's admitted incoming assignment."""
        parent.role
        return self.assignment_schema(role)

    def assignment_schema(self, role, *, internal=False):
        self.credit_kind(role)
        schema = obj({'version': {'const': LAUNCH_VERSION}, 'requests': {'type': 'object', 'properties': {key: launch_request_schema(self._request_schema(key, selected=False, internal=internal, compact=False), key, self.resources[key].get('service')) for key in self.resources}, 'minProperties': 1, 'additionalProperties': False}, 'immutable_input_versions': {'type': 'array', 'items': deepcopy(INPUT_VERSION_SCHEMA)}, 'constraints': {'type': 'object'}})
        schema['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
        return schema

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        selected = checked(selection, self.assignment_schema(role, internal=True), 'invalid_execution_assignment')
        if parent.role in ('hpc', 'hpc_execution'):
            from gene_annotation_episode.episodic_workflow.root.a104.scientific_process.hpc_work_planning.to_child_execution_job_submission import authenticate_launch
            authenticate_launch(parent, selected, operation_key, self.directory)
        selected = self._launch(selected, scope=scope)
        for request in selected['requests'].values():
            self._masking_inputs(parent, request)
            self._utility_inputs(parent, request)
        self._versions(selected['immutable_input_versions'], scope, context=parent)
        from gene_annotation_episode.episodic_workflow.root.a104.native_blast_database_result_publication import validate_native_job_inputs
        from gene_annotation_episode.episodic_workflow.root.a104.native_blast_standard_database_result_publication import validate_standard_blast_job_inputs
        for request in selected['requests'].values():
            validate_native_job_inputs(self.store, parent, request)
            validate_standard_blast_job_inputs(self.store, parent, request)
        return selected

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
