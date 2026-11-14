"""Admit this original child through its retained counterpart and typed custody."""

def receive_report(workflow, source, admitted, schema, index, *, redelivery=False):
    from gene_annotation_episode.episodic_workflow.root.a106.runtime import _references_in, _json, WorkflowError, json
    from gene_annotation_episode.episodic_workflow.root.a106.delivery_counterpart import child_role_for_delivery
    role = child_role_for_delivery(workflow, source, index)
    if role != 'results' or workflow.episode_bindings.for_child(source.path, role).binding_path != 'scientific_process/execution_result_acquisition':
        raise WorkflowError('original_delivery_binding_path_conflict')
    if workflow.receipts is not None and (not redelivery) and (not workflow.is_job_source(source)):
        from gene_annotation_episode.episodic_workflow.root.a106.episode_return_records import EpisodeReturnRecords
        references = EpisodeReturnRecords(workflow.store, workflow.run_id, failure_prefix='recorded_admission_').recorded_admission_references(workflow.binding_context(source), admitted, schema, index)
        if references is not None:
            return references
    if workflow.progress_provider is not None:
        specialist = workflow.specialist(source)
        receive_progress = getattr(specialist, 'receive_child_progress', None)
        receive_counterpart = getattr(specialist, 'receive_child_progress_for_role', None)
        handled = False
        if receive_counterpart is not None:
            from gene_annotation_episode.episodic_workflow.root.a106.delivery_counterpart import child_role_for_delivery
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
    return references


# Original Workflow.selected admission, defined for this actual parent/child boundary.
def admit_return(self, source, child, index, schema, contract, result, request):
    delivery_ref = 'delivery_' + _digest({'run': self.run_id, 'parent': source.episode_id, 'index': index})[:24]
    owned = self.episode_branch_lifecycle == EPISODE_BRANCH_LIFECYCLE
    action = self.journal.row('runtime_actions', source.episode_id, index)
    frozen_index = None if action['result'] is None else json.loads(action['result']).get('delivery_resolution_index')
    saved = self.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND ' + ('decision_index=?' if frozen_index is not None or not owned else 'delivery_ref=? ORDER BY decision_index DESC LIMIT 1'), (self.run_id, source.episode_id, frozen_index if frozen_index is not None else delivery_ref if owned else index)).fetchone()
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

def admit_unowned_return(self, source, child, index, schema, contract, result, request):
    delivery_ref = 'delivery_' + _digest({'run': self.run_id, 'parent': source.episode_id, 'index': index})[:24]
    try:
        admitted = contract.admit(result.as_record()['form'], audit_identifiers=(child.source.episode_id, request.goal.goal_id)).as_record()
    except ReportBoundaryError as error:
        feedback = self.delivery_feedback(delivery_ref, error)
        self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, failure=feedback)
        raise ReportDeliveryError(Record(feedback)) from error
    self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, form=admitted)
    self.receive_form(source, admitted, schema, index)
    return admitted

def _bind_incoming_runtime(namespace):
    from gene_annotation_episode.episodic_workflow.root.a106.library.live_runtime_functions import bind_functions
    selected = bind_functions(namespace, {name: globals()[name] for name in ('admit_return', 'admit_unowned_return')},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a106.runtime',
        qualified_names={'admit_return': 'admit_return', 'admit_unowned_return': 'admit_unowned_return'},
        defining_module='gene_annotation_episode.episodic_workflow.root.a106.scientific_process.from_child_execution_result_acquisition')
    globals().update(selected)

from gene_annotation_episode.episodic_workflow.root.a106 import runtime as _original_runtime
_bind_incoming_runtime(vars(_original_runtime))
