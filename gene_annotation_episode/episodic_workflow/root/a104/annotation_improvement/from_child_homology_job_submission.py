"""A104 original implicit improvement responsibility."""
from __future__ import annotations
from ..library.live_runtime_functions import bind_functions as _bind_functions

def admit_parent_return(self, source, child, index, schema, contract, result, request):
    delivery_ref = 'delivery_' + _digest({'run': self.run_id, 'parent': source.episode_id, 'index': index})[:24]
    action = self.journal.row('runtime_actions', source.episode_id, index)
    frozen_index = None if action['result'] is None else json.loads(action['result']).get('delivery_resolution_index')
    saved = self.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND ' + ('decision_index=?' if frozen_index is not None else 'delivery_ref=? ORDER BY decision_index DESC LIMIT 1'), (self.run_id, source.episode_id, frozen_index if frozen_index is not None else delivery_ref)).fetchone()
    if saved is not None:
        if saved['failure'] is not None:
            raise ReportDeliveryError(Record(json.loads(saved['failure'])))
        admitted = json.loads(saved['form'])
    else:
        try:
            admitted = contract.admit(result.as_record()['form'], audit_identifiers=(child.source.episode_id, request.goal.goal_id)).as_record()
        except ReportBoundaryError as error:
            feedback = self.delivery_feedback(delivery_ref, error)
            self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, failure=feedback)
            raise ReportDeliveryError(Record(feedback)) from error
        self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, form=admitted)
    delivery_index = index if saved is None else saved['decision_index']
    delivery_schema = schema if saved is None else json.loads(saved['contract'])['measurements']['schema']
    references = self.receive_form(source, admitted, delivery_schema, delivery_index, redelivery=delivery_index != index)
    return (admitted, references)

def receive_parent_child_failure(self, source, selection, index, error):
    outcome = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'feedback': {'category': 'child_execution', 'exception_type': type(error).__name__}}
    from .communication import ReportBoundaryError
    if isinstance(error, ReportBoundaryError):
        outcome['feedback']['report_boundary'] = dict(error.diagnostic)
    self.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': index, 'action': _json(selection), 'result': _json(outcome), 'credit': None})
    value = self.source_credit_view(source)['credit']
    self.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': index, 'action': _json(selection), 'result': _json(outcome), 'credit': value})
    source.last_outcome, source.last_outcome_index = (outcome, index)
    source.feedback = outcome['feedback']
    return self.controller_value(source, index, value)

def _bind_original_runtime(namespace):
    definitions = {name: globals()[name] for name in ['admit_parent_return', 'receive_parent_child_failure']}
    globals().update(_bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime', qualified_names={'admit_parent_return': 'admit_parent_return', 'receive_parent_child_failure': 'receive_parent_child_failure'}))

from .. import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
