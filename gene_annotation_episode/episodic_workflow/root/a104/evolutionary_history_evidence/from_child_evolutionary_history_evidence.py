"""Original A104 evolutionary_history_evidence directional request/receipt assembly."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.runtime import WorkflowError, _json, _references_in, json

def receive_report(workflow, source, admitted, schema, index, *, redelivery=False):
    if workflow.receipts is not None and (not redelivery) and (not workflow.is_job_source(source)):
        from gene_annotation_episode.episodic_workflow.root.a104.episode_return_records import EpisodeReturnRecords
        references = EpisodeReturnRecords(workflow.store, workflow.run_id, failure_prefix='recorded_admission_').recorded_admission_references(workflow.binding_context(source), admitted, schema, index)
        if references is not None:
            return references
    if workflow.progress_provider is not None:
        specialist = workflow.specialist(source)
        receive_progress = getattr(specialist, 'receive_child_progress', None)
        receive_counterpart = getattr(specialist, 'receive_child_progress_for_role', None)
        handled = False
        if receive_counterpart is not None:
            from gene_annotation_episode.episodic_workflow.root.a104.delivery_counterpart import child_role_for_delivery
            handled = receive_counterpart(workflow.binding_context(source), child_role_for_delivery(workflow, source, index), admitted, schema, f'{workflow.run_id}:{source.episode_id}:{index}:typed_form', workflow.progress_provider)
        if handled:
            pass
        elif receive_progress is None:
            workflow.progress_provider.receive_form(source.episode_id, admitted, schema, source.scope, f'{workflow.run_id}:{source.episode_id}:{index}:typed_form')
        else:
            receive_progress(workflow.binding_context(source), admitted, schema, f'{workflow.run_id}:{source.episode_id}:{index}:typed_form', workflow.progress_provider)
    if workflow.receipts is None or workflow.is_job_source(source):
        return []
    references = _references_in({}, workflow.store.get, forms=[(admitted, schema)], reference_subset=lambda refs: workflow.store.reference_subset(refs, source.scope))
    references.extend(workflow.episode_bindings.received_form_references(workflow.binding_context(source), admitted, schema, f'{workflow.run_id}:{source.episode_id}:{index}:typed_form'))
    references = list(dict.fromkeys(references))
    if workflow.native_timing_information is not None and workflow.job_episodes is not None:
        with workflow.store.transaction():
            key = (workflow.run_id, source.episode_id, index)
            row = workflow.store.db.execute('SELECT timing_receipts FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?', key).fetchone()
            if row is None:
                raise WorkflowError('received_form_requires_recorded_attempt')
            if row[0] is None:
                received = workflow.job_episodes.received_timing_records(workflow.store, admitted, schema, source.scope)
                workflow.store.db.execute('UPDATE runtime_report_attempts SET timing_receipts=? WHERE run_id=? AND parent_episode_id=? AND decision_index=?', (_json(received), *key))
            else:
                received = json.loads(row[0])
        references.extend((ref for ref in received['native_execution_refs'] if ref not in references))
    workflow.receipts.receive(source.episode_id, references, kind='report_redelivery' if redelivery else 'child_form', source_index=index)
    references.extend((ref for ref in workflow.receive_tool_attributions(source, index, kind='report_redelivery' if redelivery else 'child_form') if ref not in references))
    return references


from ..library.live_runtime_functions import bind_functions as _bind_parent_functions
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

def _bind_parent_runtime(namespace):
    definitions = {name: globals()[name] for name in ['admit_parent_return', 'receive_parent_child_failure']}
    globals().update(_bind_parent_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime', qualified_names={'admit_parent_return': 'admit_parent_return', 'receive_parent_child_failure': 'receive_parent_child_failure'}))

from .. import runtime as _parent_runtime
_bind_parent_runtime(vars(_parent_runtime))
