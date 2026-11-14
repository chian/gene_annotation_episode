"""Original A102 parent exchange with hpc_work_planning."""
from __future__ import annotations
from . import runtime as _runtime

def admit_return(self, source, child, index, schema, contract, result, request):
    delivery_ref = 'delivery_' + _runtime._digest({'run': self.run_id, 'parent': source.episode_id, 'index': index})[:24]
    owned = self.episode_branch_lifecycle == _runtime.EPISODE_BRANCH_LIFECYCLE
    action = self.journal.row('runtime_actions', source.episode_id, index)
    frozen_index = None if action['result'] is None else _runtime.json.loads(action['result']).get('delivery_resolution_index')
    saved = self.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND ' + ('decision_index=?' if frozen_index is not None or not owned else 'delivery_ref=? ORDER BY decision_index DESC LIMIT 1'), (self.run_id, source.episode_id, frozen_index if frozen_index is not None else delivery_ref if owned else index)).fetchone()
    if saved is not None:
        if saved['failure'] is not None:
            raise _runtime.ReportDeliveryError(_runtime.Record(_runtime.json.loads(saved['failure'])))
        admitted = _runtime.json.loads(saved['form'])
    else:
        try:
            admitted = contract.admit(result.as_record()['form'], audit_identifiers=(child.source.episode_id, request.goal.goal_id)).as_record()
        except _runtime.ReportBoundaryError as error:
            feedback = self.delivery_feedback(delivery_ref, error)
            self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, failure=feedback)
            raise _runtime.ReportDeliveryError(_runtime.Record(feedback)) from error
        self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, form=admitted)
    delivery_index = index if saved is None else saved['decision_index']
    delivery_schema = schema if saved is None else _runtime.json.loads(saved['contract'])['measurements']['schema']
    references = self.receive_form(source, admitted, delivery_schema, delivery_index, redelivery=delivery_index != index)
    return (admitted, references)

def admit_unowned_return(self, source, child, index, schema, contract, result, request):
    delivery_ref = 'delivery_' + _runtime._digest({'run': self.run_id, 'parent': source.episode_id, 'index': index})[:24]
    try:
        admitted = contract.admit(result.as_record()['form'], audit_identifiers=(child.source.episode_id, request.goal.goal_id)).as_record()
    except _runtime.ReportBoundaryError as error:
        feedback = self.delivery_feedback(delivery_ref, error)
        self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, failure=feedback)
        raise _runtime.ReportDeliveryError(_runtime.Record(feedback)) from error
    self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, form=admitted)
    self.receive_form(source, admitted, schema, index)
    return admitted
