from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _flux_balance_reference_access
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _flux_balance_selector
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _retained_flux_balance_target
from .execution_contracts import canonical
from .execution_contracts import json
from .execution_contracts import plain

class NativeScienceInputs:
    _flux_balance_reference_access = _flux_balance_reference_access
    _flux_balance_selector = staticmethod(_flux_balance_selector)
    _retained_flux_balance_target = _retained_flux_balance_target

    def _versions(self, versions, scope, *, context, flux_balance_assignments=()):
        from gene_annotation_episode.episodic_workflow.root.a110.execution_input_versions import validate_execution_input_versions
        return validate_execution_input_versions(self, versions, scope, context=context, flux_balance_assignments=flux_balance_assignments)

    def _flux_balance_inputs(self, context, assignment, *, input_versions=None):
        if 'native_flux_balance' not in assignment.get('requested_job', {}):
            return []
        from gene_annotation_episode.episodic_workflow.root.a110.episode_return_records import EpisodeReturnRecords
        if input_versions is None:
            if context.role == 'launch':
                input_versions = plain(context.assignment)['immutable_input_versions']
            else:
                _, input_versions = self.flux_balance_inputs._original(context)
        frozen = self.flux_balance_inputs.received(context, required=False) if context.role == 'launch_local' and self._matches_flux_balance_assignment(context, assignment) else None
        binding = frozen['receipt']['binding'] if frozen is not None else self.flux_balance_inputs.validate_selected(context, assignment, input_versions=input_versions)
        if not EpisodeReturnRecords._equal(binding['input_versions'], list(input_versions)):
            raise ValueError('flux_balance_execution_input_original_versions_conflict')
        return list(dict.fromkeys((row['reference'] for row in binding['input_versions'])))

    def _matches_flux_balance_assignment(self, context, assignment):
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import is_compact_assignment, materialized_assignment
        original = materialized_assignment(self.store, context) if is_compact_assignment(plain(context.assignment)) else plain(context.assignment)
        return canonical(original) == canonical(assignment)

    def _check_parent_inputs(self, context):
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import is_compact_assignment, read_request_binding
        if is_compact_assignment(plain(context.assignment)):
            read_request_binding(self.store, self.run_id, context.episode_id)
            self.flux_balance_inputs.received(context)
            return
        if len(context.path) < 2 or context.path[-2][0] != 'launch':
            return
        row = self.store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND path=?', (self.run_id, canonical(context.path[:-1]))).fetchone()
        if row is None:
            raise ValueError('execution_original_launch_assignment_unavailable')
        original = self._launch(json.loads(row['request'])['message']['episode_assignment'])
        self._flux_balance_inputs(context, plain(context.assignment), input_versions=original['immutable_input_versions'])
        self._versions(original['immutable_input_versions'], context.scope, context=context, flux_balance_assignments=[plain(context.assignment)])
