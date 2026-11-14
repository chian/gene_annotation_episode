"""a106 scientific parent's original recursive typed-return custody."""
from __future__ import annotations
from .. import runtime as _runtime

def admit_return(self, source, child, index, schema, contract, result, request):
    delivery_ref = "delivery_" + _runtime._digest({"run": self.run_id, "parent": source.episode_id, "index": index})[:24]
    owned = self.episode_branch_lifecycle == _runtime.EPISODE_BRANCH_LIFECYCLE
    action = self.journal.row('runtime_actions', source.episode_id, index)
    frozen_index = (None if action['result'] is None else
        _runtime.json.loads(action['result']).get('delivery_resolution_index'))
    saved = self.store.db.execute('SELECT * FROM runtime_report_attempts '
        'WHERE run_id=? AND parent_episode_id=? AND '
        + ('decision_index=?' if frozen_index is not None or not owned else
            'delivery_ref=? ORDER BY decision_index DESC LIMIT 1'),
        (self.run_id, source.episode_id,
            frozen_index if frozen_index is not None else delivery_ref if owned else index)).fetchone()
    if saved is not None:
        if saved['failure'] is not None:
            raise _runtime.ReportDeliveryError(_runtime.Record(_runtime.json.loads(saved['failure'])))
        admitted = _runtime.json.loads(saved['form'])
    else:
        try:
            admitted = contract.admit(result.as_record()["form"], audit_identifiers=(
                child.source.episode_id, request.goal.goal_id)).as_record()
        except _runtime.ReportBoundaryError as error:
            feedback = self.delivery_feedback(delivery_ref, error)
            self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id,
                              contract, failure=feedback)
            raise _runtime.ReportDeliveryError(_runtime.Record(feedback)) from error
        self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id,
                          contract, form=admitted)
    delivery_index = index if saved is None else saved['decision_index']
    delivery_schema = schema if saved is None else _runtime.json.loads(saved['contract'])['measurements']['schema']
    references = self.receive_form(source, admitted, delivery_schema, delivery_index,
        redelivery=delivery_index != index)
    return admitted, references

def admit_unowned_return(self, source, child, index, schema, contract, result, request):
    delivery_ref = "delivery_" + _runtime._digest({"run": self.run_id, "parent": source.episode_id, "index": index})[:24]
    try:
        admitted = contract.admit(result.as_record()["form"], audit_identifiers=(
            child.source.episode_id, request.goal.goal_id)).as_record()
    except _runtime.ReportBoundaryError as error:
        feedback = self.delivery_feedback(delivery_ref, error)
        self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id,
                          contract, failure=feedback)
        raise _runtime.ReportDeliveryError(_runtime.Record(feedback)) from error
    self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id,
                      contract, form=admitted)
    self.receive_form(source, admitted, schema, index)
    return admitted

def receive_report(self, source, admitted, schema, index, *, redelivery=False):
    if self.receipts is not None and not redelivery and not self.is_job_source(source):
        from ..episode_return_records import EpisodeReturnRecords
        references = EpisodeReturnRecords(self.store, self.run_id,
            failure_prefix='recorded_admission_').recorded_admission_references(
                self.binding_context(source), admitted, schema, index)
        if references is not None:
            return references
    # A typed progress delivery remains real received information even when
    # the caller has no scientific receipt projection. C4 supplies the
    # surrounding admission transaction; legacy callers use this boundary.
    if self.progress_provider is not None:
        specialist = self.specialist(source)
        receive_progress = getattr(specialist, 'receive_child_progress', None)
        receive_counterpart = getattr(specialist, 'receive_child_progress_for_role', None)
        handled = False
        if receive_counterpart is not None:
            from ..delivery_counterpart import child_role_for_delivery
            handled = receive_counterpart(self.binding_context(source),
                child_role_for_delivery(self, source, index), admitted, schema,
                f'{self.run_id}:{source.episode_id}:{index}:typed_form', self.progress_provider)
        if handled:
            pass
        elif receive_progress is None:
            self.progress_provider.receive_form(source.episode_id, admitted, schema, source.scope,
                f'{self.run_id}:{source.episode_id}:{index}:typed_form')
        else:
            receive_progress(self.binding_context(source), admitted, schema,
                f'{self.run_id}:{source.episode_id}:{index}:typed_form', self.progress_provider)
    if self.receipts is None or self.is_job_source(source):
        return []
    references = _runtime._references_in({}, self.store.get, forms=[(admitted, schema)],
        reference_subset=lambda refs: self.store.reference_subset(refs, source.scope))
    references.extend(self.episode_bindings.received_form_references(
        self.binding_context(source), admitted, schema,
        f'{self.run_id}:{source.episode_id}:{index}:typed_form'))
    references = list(dict.fromkeys(references))
    if self.native_timing_information is not None and self.job_episodes is not None:
        # A requested job status can deliver a real completed duration
        # without naming a Store receipt. Normalize that exact admitted
        # fact through its original host measurement. Persist this attempt's
        # projection so reconstruction cannot silently retry/reprice it.
        with self.store.transaction():
            key = (self.run_id, source.episode_id, index)
            row = self.store.db.execute('SELECT timing_receipts FROM runtime_report_attempts '
                'WHERE run_id=? AND parent_episode_id=? AND decision_index=?', key).fetchone()
            if row is None:
                raise _runtime.WorkflowError('received_form_requires_recorded_attempt')
            if row[0] is None:
                received = self.job_episodes.received_timing_records(self.store, admitted, schema, source.scope)
                self.store.db.execute('UPDATE runtime_report_attempts SET timing_receipts=? '
                    'WHERE run_id=? AND parent_episode_id=? AND decision_index=?', (_runtime._json(received), *key))
            else:
                received = _runtime.json.loads(row[0])
        references.extend(ref for ref in received['native_execution_refs'] if ref not in references)
    self.receipts.receive(source.episode_id, references,
        kind='report_redelivery' if redelivery else 'child_form', source_index=index)
    return references
