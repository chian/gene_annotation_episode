"""Original private A102 annotation task_state responsibility."""
from __future__ import annotations
from .. import runtime as _runtime

class ImprovementTaskState:
    def __init__(self, workflow, path, request, scope):
        self.workflow, self.path, self.request, self.scope = workflow, path, request, scope
        self.episode_id = _runtime.Episode.identity(workflow.context, workflow.grains[path[-1][0]],
            path[-1][1], parent_path=path[:-1]).episode_id
        self.calls = 0
        self.feedback = None
        self.last_outcome = None
        self.last_outcome_index = None
        self.report_values = _runtime._plain(request.message.as_record()["initial_report"])
        self.report_basis = []
        self._restored = False
        self._unfinished_own_actions = []
        self._source_revision = None
        self._latest_effect_index = None
        self._restored_source_state = None
        self._model_snapshot = None
        self._presented_conversation_key = None
        self._selection_view = None
        self._delivery_resolution_ref = None
        self._execution_context = None
        self._suspension_condition = None
        self._inprocess_replay_ready = False
        self.interpret_schema = (_runtime.interpretation_schema(request.report_contract.schema)
                                if request.report_contract else _runtime._object({}))

    def bind_execution_context(self, context):
        self._execution_context = context

    def suspension_changed(self, condition):
        self._suspension_condition = condition
        if self.workflow.execution_handle is not None:
            self.workflow.execution_backend.set_suspension(self.workflow.execution_handle,
                None if condition is None else {'episode_id': self.episode_id,
                    'dependency': condition})

    def restore_checkpoint(self):
        """Restore latest source state after replay, before receiving new work."""
        if self._restored_source_state is not None:
            saved = self._restored_source_state
            self._restored_source_state = None
            self.last_outcome_index = saved['last_outcome_index']
            self.last_outcome = (None if self.last_outcome_index is None else _runtime.json.loads(
                self.workflow.journal.row('runtime_actions', self.episode_id,
                    self.last_outcome_index)['result']))
            self.feedback = saved['feedback']

    def restore(self):
        restored = self.workflow.completions.restore_source(self.episode_id)
        self.calls = restored['next_call_index']
        effect = restored['latest_effect']
        if effect is not None:
            self.report_values = effect['report_values']
            self.report_basis = effect['report_basis_refs']
            self.feedback = effect['feedback']
        index = restored['last_completed_decision_index']
        if index is not None:
            action = self.workflow.journal.row('runtime_actions', self.episode_id, index)
            self.last_outcome = _runtime.json.loads(action['result'])
            self.last_outcome_index = index
        self._unfinished_own_actions = (self.workflow.inprocess_replay.unfinished(self)
            if self.workflow.inprocess_replay is not None else restored['unfinished_own_action_indices'])
        self._latest_effect_index = restored['latest_effect_index']
        self._restored_source_state = restored['source_state']
        if self._restored_source_state is not None:
            self._source_revision = self._restored_source_state['revision']
        if self.workflow.execution_binding is not None:
            self.workflow.recover_commissions(self)
        if self.workflow.progress_provider is not None:
            self.workflow.progress_provider.flush_notifications()
        self._restored = True

    def record_effect(self, index, state):
        if self.workflow.execution_binding is not None or self.workflow.inprocess_replay is not None:
            self.workflow.completions.record_decision_effect(self.episode_id, index, {
                'version': _runtime.EFFECT_VERSION, 'state': state, 'report_values': self.report_values,
                'report_basis_refs': self.report_basis, 'feedback': self.feedback})
            self._latest_effect_index = index
            self.checkpoint()

    def checkpoint(self):
        if self.workflow.inprocess_replay is not None and not self._inprocess_replay_ready:
            # Rebuilding a prefix must not replace the original latest source
            # checkpoint with a partially reconstructed transient state.
            return
        if self.workflow.execution_binding is not None or self.workflow.inprocess_replay is not None:
            if self.workflow.inprocess_replay is not None and self._inprocess_replay_ready:
                self.workflow.inprocess_replay.capture(self)
            saved = self.workflow.completions.checkpoint_source(self.episode_id,
                expected_revision=self._source_revision, latest_effect_index=self._latest_effect_index,
                last_outcome_index=self.last_outcome_index, feedback=self.feedback)
            self._source_revision = saved['revision']

