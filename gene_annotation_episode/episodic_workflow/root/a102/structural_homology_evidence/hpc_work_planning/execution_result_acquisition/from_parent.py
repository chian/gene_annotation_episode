"""Private A102 Results from parent."""
from __future__ import annotations
from .execution_contracts import INPUT_VERSION_SCHEMA, KINDS, LAUNCH_VERSION, LOCAL_FILE_SOURCE_SELECTOR_SCHEMA, RESULTS_SCHEMA, ROLE_KINDS, SELECTION_SCHEMA, checked, deepcopy, is_file_source_selector, is_native_protein_structure_target, obj, plain

class ResultsFromParent:

    def required_return_sources(self, parent, role):
        """Preserve the original job identity across its scientific return."""
        if parent is not None and parent.path[-1][0] == 'structural_homology_evidence' and getattr(self.services, 'annotation_task_required', lambda: False)():
            return ('execution_result_refs',)
        return ()

    def child_assignment_schema(self, parent, role):
        parent.role
        return self.assignment_schema(role)

    def assignment_schema(self, role, *, internal=False):
        self.credit_kind(role)
        schema = deepcopy(RESULTS_SCHEMA)
        schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'local_file_source_selector_v1'}}}, 'then': deepcopy(LOCAL_FILE_SOURCE_SELECTOR_SCHEMA)})
        if any((configuration.get('native_protein_structure') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.a102.protein_structure_selection import protein_structure_result_selector_schema
            schema['properties']['selector']['allOf'].append({'if': {'required': ['version'], 'properties': {'version': {'const': 'protein_structure_result_selector_v1'}}}, 'then': protein_structure_result_selector_schema()})
        return schema

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        selected = checked(selection, self.assignment_schema(role, internal=True), 'invalid_execution_assignment')
        parent.role
        recorded = self._recorded_results_assignment(parent, selected, scope, operation_key)
        if recorded is not None:
            return recorded
        retained = self._retained_protein_result(parent, selected, scope)
        target = retained['body']['intent']['target'] if retained is not None else self.job_progress_provider.targets.read_target(selected['handoff_ref'], scope)
        self._selector(selected, target)
        if is_file_source_selector(selected.get('selector')):
            self.local_file_sources.admit(parent, selected, target)
        if is_native_protein_structure_target(target):
            from gene_annotation_episode.episodic_workflow.root.a102.protein_structure_operands import validate_protein_structure_selected_inputs
            validate_protein_structure_selected_inputs(self.store, parent, selected['selector'], handoff_ref=selected['handoff_ref'], returns=self.native_protein_structure_returns)
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
