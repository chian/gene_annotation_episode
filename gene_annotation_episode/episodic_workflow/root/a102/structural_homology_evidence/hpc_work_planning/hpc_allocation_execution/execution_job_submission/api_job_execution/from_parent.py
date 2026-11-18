"""Private A102 API from parent."""
from __future__ import annotations
from .execution_contracts import INPUT_VERSION_SCHEMA, KINDS, LAUNCH_VERSION, LOCAL_FILE_SOURCE_SELECTOR_SCHEMA, RESULTS_SCHEMA, ROLE_KINDS, SELECTION_SCHEMA, checked, deepcopy, is_file_source_selector, is_native_protein_structure_target, obj, plain

class APIFromParent:

    def required_return_sources(self, parent, role):
        """Preserve the original job identity across its scientific return."""
        if parent is not None and parent.path[-1][0] == 'structural_homology_evidence' and getattr(self.services, 'annotation_task_required', lambda: False)():
            return ()
        return ()

    def child_assignment_schema(self, parent, role):
        parent.role
        return self.assignment_schema(role)

    def assignment_schema(self, role, *, internal=False):
        self.credit_kind(role)
        alternatives = [self._request_schema(key, selected=True, internal=internal) for key, config in self.resources.items() if KINDS[config['kind']] == ROLE_KINDS[role]]
        return {'anyOf': alternatives} if alternatives else {'not': {}}

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        selected = checked(selection, self.assignment_schema(role, internal=True), 'invalid_execution_assignment')
        # Preserve the original parent-role read before own request validation.
        parent.role
        selected = self._validate_request(selected)
        selected = self.api_execution.validate_assignment(selected, scope=scope)
        if ROLE_KINDS[role] != KINDS[self.resources[selected['resource_id']]['kind']]:
            raise ValueError('execution_resource_kind_conflict')
        if parent.role != 'launch':
            raise ValueError('resource_child_role_owned_by_launch')
        original = self._launch(plain(parent.assignment))
        from gene_annotation_episode.episodic_workflow.root.a102.protein_structure_operands import validate_protein_structure_job_inputs
        validate_protein_structure_job_inputs(self.store, parent, selected, returns=self.native_protein_structure_returns)
        self._versions(original['immutable_input_versions'], scope, context=parent)
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
