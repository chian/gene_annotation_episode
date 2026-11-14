"""Actual A103 parent request/admission responsibility; original late predicates retained."""
from __future__ import annotations

def admit_return(self, source, child, index, schema, contract, result, request):
    delivery_ref = 'delivery_' + _get__digest()({'run': self.run_id, 'parent': source.episode_id, 'index': index})[:24]
    owned = self.episode_branch_lifecycle == _get_EPISODE_BRANCH_LIFECYCLE()
    action = self.journal.row('runtime_actions', source.episode_id, index)
    frozen_index = None if action['result'] is None else _get_json().loads(action['result']).get('delivery_resolution_index')
    saved = self.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND ' + ('decision_index=?' if frozen_index is not None or not owned else 'delivery_ref=? ORDER BY decision_index DESC LIMIT 1'), (self.run_id, source.episode_id, frozen_index if frozen_index is not None else delivery_ref if owned else index)).fetchone()
    if saved is not None:
        if saved['failure'] is not None:
            raise _get_ReportDeliveryError()(_get_Record()(_get_json().loads(saved['failure'])))
        admitted = _get_json().loads(saved['form'])
    else:
        try:
            admitted = contract.admit(result.as_record()['form'], audit_identifiers=(child.source.episode_id, request.goal.goal_id)).as_record()
        except _get_ReportBoundaryError() as error:
            feedback = self.delivery_feedback(delivery_ref, error)
            self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, failure=feedback)
            raise _get_ReportDeliveryError()(_get_Record()(feedback)) from error
        self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, form=admitted)
    delivery_index = index if saved is None else saved['decision_index']
    delivery_schema = schema if saved is None else _get_json().loads(saved['contract'])['measurements']['schema']
    references = self.receive_form(source, admitted, delivery_schema, delivery_index, redelivery=delivery_index != index)
    return (admitted, references)

def admit_unowned_return(self, source, child, index, schema, contract, result, request):
    delivery_ref = 'delivery_' + _get__digest()({'run': self.run_id, 'parent': source.episode_id, 'index': index})[:24]
    try:
        admitted = contract.admit(result.as_record()['form'], audit_identifiers=(child.source.episode_id, request.goal.goal_id)).as_record()
    except _get_ReportBoundaryError() as error:
        feedback = self.delivery_feedback(delivery_ref, error)
        self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, failure=feedback)
        raise _get_ReportDeliveryError()(_get_Record()(feedback)) from error
    self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, form=admitted)
    self.receive_form(source, admitted, schema, index)
    return admitted

from gene_annotation_episode.episodic_workflow.root.a103.runtime import (
    _parent_name_EPISODE_BRANCH_LIFECYCLE as _get_EPISODE_BRANCH_LIFECYCLE,
    _parent_name_Record as _get_Record,
    _parent_name_ReportBoundaryError as _get_ReportBoundaryError,
    _parent_name_ReportDeliveryError as _get_ReportDeliveryError,
    _parent_name__digest as _get__digest,
    _parent_name_json as _get_json,
)
