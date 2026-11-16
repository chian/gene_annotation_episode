"""A104 original library/decision_source_execution defining responsibilities."""
from __future__ import annotations
from ..library.live_runtime_functions import bind_functions as _bind_functions

def record_execution_failure(self, error, *, unit=None):
    from .episode_source_failure import record_source_failure
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

async def execute(self, selection, index):
    journal = self.workflow.journal
    old = journal.row('runtime_actions', self.episode_id, index)
    if old and json.loads(old['action']) != selection:
        raise WorkflowError('reconstructed selected work changed')
    if old and old['result'] is not None:
        result, credit = (json.loads(old['result']), old['credit'])
    else:
        if self.path[-1][0] == 'scientific_process':
            self.workflow.scientific_process_binding.validate_execution_context(self.workflow.binding_context(self))
        journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': _json(selection), 'result': None, 'credit': None})
        key = f'{self.workflow.run_id}:{self.episode_id}:{index}'
        with journal.measure('runtime_actions', self.episode_id, index):
            if selection['kind'] == 'reason':
                payload = selection['commit']
                scope_binding = {'account_invocation': (self.workflow.run_id, self.episode_id)} if payload.get('interpretation_accounts') else {}
                specialist = self.workflow.specialist(self)
                execute_reasoning = getattr(specialist, 'execute_reasoning', None)
                result = execute_reasoning(self.workflow.binding_context(self), selection, key) if execute_reasoning is not None else None
                if result is None:
                    result = self.workflow.store.commit_reasoning(payload, self.scope, key, **scope_binding)
            elif selection['kind'] == 'wait':
                try:
                    result = await self.workflow.perform_selected_wait(self, selection['condition'], index)
                except EventTargetError as error:
                    result = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': _wait_target_feedback(error, status='failed')}
            else:
                result = self.workflow.execute(self, selection['tool'], selection['arguments'], decision_index=index, operation_key=key)
            if inspect.isawaitable(result):
                result = await result
        result = {**result, 'pending_work_after_action': self.workflow.pending_work(self)}
        with self.workflow.store.transaction() if self.workflow.execution_binding is not None else nullcontext():
            journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': _json(selection), 'result': _json(result), 'credit': None})
            self.last_outcome, self.last_outcome_index = (result, index)
            if result['status'] not in ('completed', 'partial'):
                self.feedback = result.get('feedback') or {'status': result['status'], 'category': result.get('error_code', 'work_failed')}
            self.checkpoint()
        credit = None
    observed_outcome = observes_action_outcome(selection['kind'], result['status'])
    with self.workflow.store.transaction() if self.workflow.execution_binding is not None else nullcontext():
        self.workflow.receive_native_outcome(self, result, index)
        if credit is None and observed_outcome:
            self.workflow.receive_outcome(self, selection, result, index)
    if credit is None and observed_outcome and (selection['kind'] != 'wait'):
        result = await self.workflow.automatic_score_updates(self, index, result)
    with self.workflow.store.transaction() if self.workflow.execution_binding is not None else nullcontext():
        if credit is None and observed_outcome:
            if selection['kind'] == 'wait':
                credit = self.workflow.last_observed_credit(self)
            else:
                credit_view = self.workflow.source_credit_view(self)
                credit = credit_view['credit']
                if selection.get('kind') == 'tool' and selection.get('tool') == 'shared.read_information':
                    self.workflow.retain_shared_grading_results(self, result, credit_view)
            journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': _json(selection), 'result': _json(result), 'credit': credit})
        if self.workflow.execution_binding is not None and observed_outcome:
            self.workflow.completions.stage(self.episode_id, index, label=f"{selection['kind']}:{index}", kind='own_action', controller_input=self.workflow.controller_value(self, index, credit), child_return=None)
            self.last_outcome, self.last_outcome_index = (result, index)
            self.checkpoint()
    self.last_outcome = result
    self.last_outcome_index = index
    if not observed_outcome:
        raise ActionFailure(result.get('feedback') or {'status': result['status'], 'category': result.get('error_code', 'work_failed')})
    return self.workflow.controller_value(self, index, credit)


def _bind_original_runtime(namespace):
    definitions = {name: globals()[name] for name in ['record_execution_failure', 'execute']}
    globals().update(_bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime', qualified_names={'record_execution_failure': 'DecisionSource.record_execution_failure', 'execute': 'DecisionSource.execute'}))

from .. import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
