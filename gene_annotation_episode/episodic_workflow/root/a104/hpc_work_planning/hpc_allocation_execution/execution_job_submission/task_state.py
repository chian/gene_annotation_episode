"""Private A104 Launch task_state."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.runtime import ActionLeaf, EFFECT_VERSION, Episode, Record, _json, _object, _plain, interpretation_schema, json

class LaunchTaskState:

    def __init__(self, workflow, path, request, scope):
        self.workflow, self.path, self.request, self.scope = (workflow, path, request, scope)
        self.episode_id = Episode.identity(workflow.context, workflow.grains[path[-1][0]], path[-1][1], parent_path=path[:-1]).episode_id
        self.calls = 0
        self.feedback = None
        self.last_outcome = None
        self.last_outcome_index = None
        self.report_values = _plain(request.message.as_record()['initial_report'])
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
        self.interpret_schema = interpretation_schema(request.report_contract.schema) if request.report_contract else _object({})

    def bind_execution_context(self, context):
        self._execution_context = context

    def record_execution_failure(self, error, *, unit=None):
        from gene_annotation_episode.episodic_workflow.root.a104.episode_source_failure import record_source_failure
        import traceback
        diagnostic = self.workflow.archive.store(Record({'exception_type': type(error).__name__, 'traceback': traceback.format_exc()}))
        index = getattr(unit, 'decision_index', None)
        failure = record_source_failure(self.workflow.store, self.workflow.run_id, self.episode_id, index if index is not None else max(0, self.calls - 1), error, category='episode_execution', cause_code='selected_operation_failed')
        self.feedback = {**failure, 'diagnostic_ref': str(diagnostic.path)}
        action = None if index is None else self.workflow.journal.row('runtime_actions', self.episode_id, index)
        if action is not None and action['result'] is None and (json.loads(action['action']).get('kind') in {'tool', 'reason'}):
            selection = json.loads(action['action'])
            outcome = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'feedback': self.feedback}
            with self.workflow.store.transaction():
                self.workflow.journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': action['action'], 'result': _json(outcome), 'credit': None})
                credit = self.workflow.source_credit_view(self)['credit']
                value = self.workflow.controller_value(self, index, credit)
                self.workflow.journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': action['action'], 'result': _json(outcome), 'credit': credit})
                if self.workflow.execution_binding is not None:
                    self.workflow.completions.stage(self.episode_id, index, label=f"{selection['kind']}:{index}", kind='own_action', controller_input=value, child_return=None)
            self.last_outcome, self.last_outcome_index = (outcome, index)
            self.checkpoint()
            return ActionLeaf(selection, extract=lambda _: value, result=lambda _, result: result, label=f"{selection['kind']}:{index}", decision_index=index)
        self.checkpoint()

    def restore_checkpoint(self):
        """Restore latest source state after replay, before receiving new work."""
        if self._restored_source_state is not None:
            saved = self._restored_source_state
            self._restored_source_state = None
            self.last_outcome_index = saved['last_outcome_index']
            self.last_outcome = None if self.last_outcome_index is None else json.loads(self.workflow.journal.row('runtime_actions', self.episode_id, self.last_outcome_index)['result'])
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
            self.last_outcome = json.loads(action['result'])
            self.last_outcome_index = index
        self._unfinished_own_actions = self.workflow.inprocess_replay.unfinished(self) if self.workflow.inprocess_replay is not None else restored['unfinished_own_action_indices']
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
            self.workflow.completions.record_decision_effect(self.episode_id, index, {'version': EFFECT_VERSION, 'state': state, 'report_values': self.report_values, 'report_basis_refs': self.report_basis, 'feedback': self.feedback})
            self._latest_effect_index = index
            self.checkpoint()

    def checkpoint(self):
        if self.workflow.inprocess_replay is not None and (not self._inprocess_replay_ready):
            return
        if self.workflow.execution_binding is not None or self.workflow.inprocess_replay is not None:
            if self.workflow.inprocess_replay is not None and self._inprocess_replay_ready:
                self.workflow.inprocess_replay.capture(self)
            saved = self.workflow.completions.checkpoint_source(self.episode_id, expected_revision=self._source_revision, latest_effect_index=self._latest_effect_index, last_outcome_index=self.last_outcome_index, feedback=self.feedback)
            self._source_revision = saved['revision']


def _bind_preserved_runtime_providers(namespace):
    from gene_annotation_episode.episodic_workflow.root.a104.library.live_runtime_functions import bind_functions
    definitions = {'LaunchTaskState.__init__': LaunchTaskState.__dict__['__init__'], 'LaunchTaskState.record_execution_failure': LaunchTaskState.__dict__['record_execution_failure'], 'LaunchTaskState.restore_checkpoint': LaunchTaskState.__dict__['restore_checkpoint'], 'LaunchTaskState.restore': LaunchTaskState.__dict__['restore'], 'LaunchTaskState.record_effect': LaunchTaskState.__dict__['record_effect']}
    bound = bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime',
        qualified_names={name: name for name in definitions}, defining_module='gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.hpc_allocation_execution.execution_job_submission.task_state')
    setattr(LaunchTaskState, '__init__', bound['LaunchTaskState.__init__'])
    setattr(LaunchTaskState, 'record_execution_failure', bound['LaunchTaskState.record_execution_failure'])
    setattr(LaunchTaskState, 'restore_checkpoint', bound['LaunchTaskState.restore_checkpoint'])
    setattr(LaunchTaskState, 'restore', bound['LaunchTaskState.restore'])
    setattr(LaunchTaskState, 'record_effect', bound['LaunchTaskState.record_effect'])

from gene_annotation_episode.episodic_workflow.root.a104 import runtime as _preserved_runtime_namespace
_bind_preserved_runtime_providers(vars(_preserved_runtime_namespace))
