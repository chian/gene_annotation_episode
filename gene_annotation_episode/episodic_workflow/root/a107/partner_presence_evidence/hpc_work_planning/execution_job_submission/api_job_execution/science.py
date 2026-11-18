from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _expression_nmf_reference_access
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _masking_reference_access
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _utility_reference_access
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import resolve_received_execution_reference
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_targets import is_expression_nmf_selector
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_targets import is_masking_selector
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_targets import is_utility_selector
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_targets import retained_expression_nmf_target
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_targets import retained_masking_target
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_targets import retained_utility_target
from .execution_contracts import canonical
from .execution_contracts import json
from .execution_contracts import plain
from gene_annotation_episode.episodic_workflow.root.a107.a107_blast_execution import BLAST_GRADED_REQUEST_VERSION, hashlib, plain

class NativeScienceInputs:
    _masking_selector = staticmethod(is_masking_selector)
    _retained_masking_target = retained_masking_target
    _masking_reference_access = _masking_reference_access
    _utility_selector = staticmethod(is_utility_selector)
    _retained_utility_target = retained_utility_target
    _utility_reference_access = _utility_reference_access
    _expression_nmf_reference_access = _expression_nmf_reference_access
    _expression_nmf_selector = staticmethod(is_expression_nmf_selector)
    _retained_expression_nmf_target = retained_expression_nmf_target

    def _masking_inputs(self, context, assignment):
        return self.native_blast_masking_results.validate_job_inputs(context, assignment)

    def _utility_inputs(self, context, assignment):
        return self.native_blast_utility_results.validate_job_inputs(context, assignment)

    def _expression_nmf_inputs(self, context, assignment):
        if 'native_expression_nmf' not in assignment.get('requested_job', {}):
            return []
        from gene_annotation_episode.episodic_workflow.root.a107.expression_nmf_operands import validate_expression_nmf_job_inputs
        return validate_expression_nmf_job_inputs(self.store, context, assignment, reference_access=resolve_received_execution_reference.__get__(self))

    def _versions(self, versions, scope, *, context, nmf_assignments=()):
        from gene_annotation_episode.episodic_workflow.root.a107.execution_input_versions import validate_execution_input_versions
        return validate_execution_input_versions(self, versions, scope, context=context, nmf_assignments=nmf_assignments)

    def _check_parent_inputs(self, context):
        if len(context.path) < 2 or context.path[-2][0] != 'launch':
            return
        row = self.store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND path=?', (self.run_id, canonical(context.path[:-1]))).fetchone()
        if row is not None:
            original = self._launch(json.loads(row['request'])['message']['episode_assignment'])
            self._validate_blast_api_parent_request(original, plain(context.assignment), context.scope)
            self._masking_inputs(context, plain(context.assignment))
            self._utility_inputs(context, plain(context.assignment))
            self._versions(original['immutable_input_versions'], context.scope, context=context, nmf_assignments=[plain(context.assignment)])
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_result_publication import validate_native_job_inputs
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_result_publication import validate_standard_blast_job_inputs
            validate_native_job_inputs(self.store, context, plain(context.assignment))
            validate_standard_blast_job_inputs(self.store, context, plain(context.assignment))
            return
        raise ValueError('execution_original_launch_assignment_unavailable')

    def _validate_blast_api_parent_request(self, launch, selected, scope):
        """Bind this API child's selected search to its immediate parent goal."""
        resource_id = selected['resource_id']
        request = launch['requests'].get(resource_id)
        if request is None or request.get('version') != BLAST_GRADED_REQUEST_VERSION:
            return
        if selected.get('service') != 'ncbi_blast' or not self._permitted(launch, resource_id):
            raise ValueError('blast_grader_selected_service_conflict')
        subject_ref = request['query_subject_ref']
        self.tool_registry._check_sequence_operand(subject_ref, plain(scope))
        sequence = self.tool_registry._sequence(subject_ref, molecule_model=self.store.subject_molecule(subject_ref))
        prepared = self.api_execution.services[resource_id].prepare('api.blast.prepare', selected['request'], {}, scope=plain(scope), previous_events=[])
        if prepared['sequence_sha256'] != hashlib.sha256(sequence.encode()).hexdigest():
            raise ValueError('blast_grader_selected_query_conflict')
        if request.get('database') is not None and selected['request']['database'] != request['database']:
            raise ValueError('blast_grader_selected_database_conflict')
