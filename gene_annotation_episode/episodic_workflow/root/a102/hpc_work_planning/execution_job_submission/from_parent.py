"""Private A102 Launch from parent."""
from __future__ import annotations
from .execution_contracts import INPUT_VERSION_SCHEMA, KINDS, LAUNCH_VERSION, LOCAL_FILE_SOURCE_SELECTOR_SCHEMA, RESULTS_SCHEMA, ROLE_KINDS, SELECTION_SCHEMA, checked, deepcopy, is_file_source_selector, is_native_protein_structure_target, obj, plain

class LaunchFromParent:

    def required_return_sources(self, parent, role):
        """Preserve the original job identity across its scientific return."""
        if parent is not None and parent.path[-1][0] == 'scientific_process' and getattr(self.services, 'annotation_task_required', lambda: False)():
            return ('execution_handoff_refs',)
        return ()

    def child_assignment_schema(self, parent, role):
        parent.role
        return self.assignment_schema(role)

    def assignment_schema(self, role, *, internal=False):
        self.credit_kind(role)
        schema = obj({'version': {'const': LAUNCH_VERSION}, 'requests': {'type': 'object', 'properties': {key: self._request_schema(key, selected=False, internal=internal) for key in self.resources}, 'minProperties': 1, 'additionalProperties': False}, 'immutable_input_versions': {'type': 'array', 'items': deepcopy(INPUT_VERSION_SCHEMA)}, 'constraints': {'type': 'object'}})
        schema['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
        return schema

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        selected = checked(selection, self.assignment_schema(role, internal=True), 'invalid_execution_assignment')
        if parent.role in ('hpc', 'hpc_execution') and role == 'launch':
            from gene_annotation_episode.episodic_workflow.root.a102.hpc_work_planning.to_child_execution_job_submission import authenticate_launch
            authenticate_launch(parent, selected, operation_key, self.directory)
        selected = self._launch(selected, scope=scope)
        from gene_annotation_episode.episodic_workflow.root.a102.protein_structure_operands import validate_protein_structure_job_inputs
        for request in selected['requests'].values():
            validate_protein_structure_job_inputs(self.store, parent, request, returns=self.native_protein_structure_returns)
        self._versions(selected['immutable_input_versions'], scope, context=parent)
        return selected

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
