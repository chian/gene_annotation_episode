"""Shared original source protocol decision_source_outcomes."""
from __future__ import annotations


def record_execution_failure(self, error, *, unit=None):
    from gene_annotation_episode.episodic_workflow.root.a105.episode_source_failure import record_source_failure
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

async def finish(self, record):
    if self.request.report_contract is None:
        result = {'credit': self.workflow.source_credit_view(self)['credit'], 'pending_handles': self.workflow.pending_handles(self)}
        result.update(self.workflow.episode_bindings.current_report_facts(self.workflow.binding_context(self)))
        await self.workflow.release(self.episode_id)
        return _original_runtime.Record(result)
    saved = self.workflow.journal.row('runtime_forms', self.episode_id)
    if saved and saved['form'] is not None:
        form = _original_runtime.json.loads(saved['form'])
    else:
        facts = self.workflow.facts(self, completion_record=record)
        form = _original_runtime.form_with_facts(self.report_values, self.request.report_contract.schema, facts)
        self.workflow.journal.save('runtime_forms', {'episode_id': self.episode_id, 'facts': _original_runtime._json({**facts, 'interpretations': self.report_values}), 'form': _original_runtime._json(form)})
    await self.workflow.release(self.episode_id)
    return _original_runtime.Record({'form': form})

from gene_annotation_episode.episodic_workflow.root.a105 import runtime as _original_runtime
