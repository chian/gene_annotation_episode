"""Admit this parent's original published-evidence response and redelivery."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a102.runtime import WorkflowError, _json, _references_in, json

def receive_report(workflow, source, admitted, schema, index, *, redelivery=False):
    if workflow.receipts is not None and (not redelivery) and (not workflow.is_job_source(source)):
        from gene_annotation_episode.episodic_workflow.root.a102.episode_return_records import EpisodeReturnRecords
        references = EpisodeReturnRecords(workflow.store, workflow.run_id, failure_prefix='recorded_admission_').recorded_admission_references(workflow.binding_context(source), admitted, schema, index)
        if references is not None:
            return references
    if workflow.progress_provider is not None:
        specialist = workflow.specialist(source)
        receive_progress = getattr(specialist, 'receive_child_progress', None)
        receive_counterpart = getattr(specialist, 'receive_child_progress_for_role', None)
        handled = False
        if receive_counterpart is not None:
            from gene_annotation_episode.episodic_workflow.root.a102.delivery_counterpart import child_role_for_delivery
            handled = receive_counterpart(workflow.binding_context(source), child_role_for_delivery(workflow, source, index), admitted, schema, f'{workflow.run_id}:{source.episode_id}:{index}:typed_form', workflow.progress_provider)
        if handled:
            pass
        elif receive_progress is None:
            workflow.progress_provider.receive_form(source.episode_id, admitted, schema, source.scope, f'{workflow.run_id}:{source.episode_id}:{index}:typed_form')
        else:
            receive_progress(workflow.binding_context(source), admitted, schema, f'{workflow.run_id}:{source.episode_id}:{index}:typed_form', workflow.progress_provider)
    if workflow.receipts is None or workflow.is_job_source(source):
        return []
    references = _live_original_runtime._references_in({}, workflow.store.get, forms=[(admitted, schema)], reference_subset=lambda refs: workflow.store.reference_subset(refs, source.scope))
    references.extend(workflow.episode_bindings.received_form_references(workflow.binding_context(source), admitted, schema, f'{workflow.run_id}:{source.episode_id}:{index}:typed_form'))
    references = list(dict.fromkeys(references))
    if workflow.native_timing_information is not None and workflow.job_episodes is not None:
        with workflow.store.transaction():
            key = (workflow.run_id, source.episode_id, index)
            row = workflow.store.db.execute('SELECT timing_receipts FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?', key).fetchone()
            if row is None:
                raise _live_original_runtime.WorkflowError('received_form_requires_recorded_attempt')
            if row[0] is None:
                received = workflow.job_episodes.received_timing_records(workflow.store, admitted, schema, source.scope)
                workflow.store.db.execute('UPDATE runtime_report_attempts SET timing_receipts=? WHERE run_id=? AND parent_episode_id=? AND decision_index=?', (_live_original_runtime._json(received), *key))
            else:
                received = _live_original_runtime.json.loads(row[0])
        references.extend((ref for ref in received['native_execution_refs'] if ref not in references))
    workflow.receipts.receive(source.episode_id, references, kind='report_redelivery' if redelivery else 'child_form', source_index=index)
    references.extend((ref for ref in workflow.receive_tool_attributions(source, index, kind='report_redelivery' if redelivery else 'child_form') if ref not in references))
    return references

def select_report_receiver(workflow, source, index):
    from gene_annotation_episode.episodic_workflow.root.a102.episode_bindings import EpisodeBindingRegistry
    from gene_annotation_episode.episodic_workflow.root.a102.episode_journal import WorkflowError
    from gene_annotation_episode.episodic_workflow.root.a102.delivery_counterpart import child_role_for_delivery
    if not (len(source.path) == 1 and source.path[0][0] == 'annotation') or type(workflow.episode_bindings) is not EpisodeBindingRegistry:
        return None
    try:
        role = child_role_for_delivery(workflow, source, index)
        if role != 'literature':
            return None
        child = workflow.episode_bindings.for_child(source.path, role)
    except (WorkflowError, LookupError, ValueError, TypeError, AttributeError):
        return None
    from gene_annotation_episode.episodic_workflow.root.a102.published_evidence_assessment.episode import LiteratureEpisode
    if type(child) is LiteratureEpisode and child.binding_path == 'published_evidence_assessment' and (child.commissioning_parent == 'legacy_annotation'):
        return receive_report
    return None

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
from gene_annotation_episode.episodic_workflow.root.a102 import runtime as _live_original_runtime
