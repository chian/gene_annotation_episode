"""A110 shared decision-source protocol: decision_source_outcomes"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110 import runtime as _original_runtime

def record_execution_failure(self, error, *, unit=None):
    from ..episode_source_failure import record_source_failure
    import traceback
    diagnostic = self.workflow.archive.store(_original_runtime.Record({'exception_type': type(error).__name__, 'traceback': traceback.format_exc()}))
    index = getattr(unit, 'decision_index', None)
    failure = record_source_failure(self.workflow.store, self.workflow.run_id, self.episode_id, index if index is not None else max(0, self.calls - 1), error, category='episode_execution', cause_code='selected_operation_failed')
    self.feedback = {**failure, 'diagnostic_ref': str(diagnostic.path)}
    action = None if index is None else self.workflow.journal.row('runtime_actions', self.episode_id, index)
    if action is not None and action['result'] is None and (_original_runtime.json.loads(action['action']).get('kind') in {'tool', 'reason'}):
        selection = _original_runtime.json.loads(action['action'])
        outcome = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'feedback': self.feedback}
        with self.workflow.store.transaction():
            self.workflow.journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': action['action'], 'result': _original_runtime._json(outcome), 'credit': None})
            credit = self.workflow.source_credit_view(self)['credit']
            value = self.workflow.controller_value(self, index, credit)
            self.workflow.journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': action['action'], 'result': _original_runtime._json(outcome), 'credit': credit})
            if self.workflow.execution_binding is not None:
                self.workflow.completions.stage(self.episode_id, index, label=f"{selection['kind']}:{index}", kind='own_action', controller_input=value, child_return=None)
        self.last_outcome, self.last_outcome_index = (outcome, index)
        self.checkpoint()
        return _original_runtime.ActionLeaf(selection, extract=lambda _: value, result=lambda _, result: result, label=f"{selection['kind']}:{index}", decision_index=index)
    self.checkpoint()

async def execute(self, selection, index):
    journal = self.workflow.journal
    old = journal.row('runtime_actions', self.episode_id, index)
    if old and _original_runtime.json.loads(old['action']) != selection:
        raise _original_runtime.WorkflowError('reconstructed selected work changed')
    if old and old['result'] is not None:
        result, credit = (_original_runtime.json.loads(old['result']), old['credit'])
    else:
        if self.path[-1][0] == 'scientific_process':
            self.workflow.scientific_process_binding.validate_execution_context(self.workflow.binding_context(self))
        journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': _original_runtime._json(selection), 'result': None, 'credit': None})
        key = f'{self.workflow.run_id}:{self.episode_id}:{index}'
        with journal.measure('runtime_actions', self.episode_id, index):
            if selection['kind'] == 'reason':
                payload = selection['commit']
                account_context = {'account_invocation': (self.workflow.run_id, self.episode_id)} if payload.get('interpretation_accounts') else {}
                specialist = self.workflow.specialist(self)
                execute_reasoning = getattr(specialist, 'execute_reasoning', None)
                result = execute_reasoning(self.workflow.binding_context(self), selection, key) if execute_reasoning is not None else None
                if result is None:
                    result = self.workflow.store.commit_reasoning(payload, self.scope, key, **account_context)
            elif selection['kind'] == 'wait':
                try:
                    result = await self.workflow.perform_selected_wait(self, selection['condition'], index)
                except _original_runtime.EventTargetError as error:
                    result = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': _original_runtime._wait_target_feedback(error, status='failed')}
            else:
                result = self.workflow.execute(self, selection['tool'], selection['arguments'], decision_index=index, operation_key=key)
            if _original_runtime.inspect.isawaitable(result):
                result = await result
        if self.workflow.execution_binding is not None or self.workflow.wait_inputs_version == 'wait_inputs_binding_v2' or self.workflow.completed_action_inputs_version is not None:
            result = {**result, 'pending_work_after_action': self.workflow.pending_work(self)}
        with self.workflow.store.transaction() if self.workflow.execution_binding is not None else _original_runtime.nullcontext():
            journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': _original_runtime._json(selection), 'result': _original_runtime._json(result), 'credit': None})
            self.last_outcome, self.last_outcome_index = (result, index)
            if result['status'] not in ('completed', 'partial'):
                self.feedback = result.get('feedback') or {'status': result['status'], 'category': result.get('error_code', 'work_failed')}
            self.checkpoint()
        credit = None
    observed_outcome = _original_runtime.observes_action_outcome(selection['kind'], result['status'])
    with self.workflow.store.transaction() if self.workflow.execution_binding is not None else _original_runtime.nullcontext():
        self.workflow.receive_native_outcome(self, result, index)
        if credit is None and observed_outcome:
            self.workflow.receive_outcome(self, selection, result, index)
    if credit is None and observed_outcome and (selection['kind'] != 'wait'):
        result = await self.workflow.automatic_score_updates(self, index, result)
    with self.workflow.store.transaction() if self.workflow.execution_binding is not None else _original_runtime.nullcontext():
        if credit is None and observed_outcome:
            if selection['kind'] == 'wait':
                credit = self.workflow.last_observed_credit(self)
            else:
                credit_view = self.workflow.source_credit_view(self)
                credit = credit_view['credit']
                if selection.get('kind') == 'tool' and selection.get('tool') == 'shared.read_information':
                    self.workflow.retain_shared_grading_results(self, result, credit_view)
            journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': _original_runtime._json(selection), 'result': _original_runtime._json(result), 'credit': credit})
        if self.workflow.execution_binding is not None and observed_outcome:
            self.workflow.completions.stage(self.episode_id, index, label=f"{selection['kind']}:{index}", kind='own_action', controller_input=self.workflow.controller_value(self, index, credit), child_return=None)
            self.last_outcome, self.last_outcome_index = (result, index)
            self.checkpoint()
    self.last_outcome = result
    self.last_outcome_index = index
    if not observed_outcome:
        raise _original_runtime.ActionFailure(result.get('feedback') or {'status': result['status'], 'category': result.get('error_code', 'work_failed')})
    return self.workflow.controller_value(self, index, credit)
