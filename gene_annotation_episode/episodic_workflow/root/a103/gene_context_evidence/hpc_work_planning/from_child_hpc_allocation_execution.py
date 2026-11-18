"""Receive this allocation child's admitted form through its original receipt and shared-ledger path."""

def receive_allocation_report(workflow, source, admitted, schema, index, *, redelivery=False):
    if workflow.receipts is not None and (not redelivery) and (not workflow.is_job_source(source)):
        from gene_annotation_episode.episodic_workflow.root.a103.episode_return_records import EpisodeReturnRecords
        references = EpisodeReturnRecords(workflow.store, workflow.run_id, failure_prefix='recorded_admission_').recorded_admission_references(workflow.binding_context(source), admitted, schema, index)
        if references is not None:
            return references
    if workflow.progress_provider is not None:
        workflow.progress_provider.receive_form(source.episode_id, admitted, schema, source.scope, f'{workflow.run_id}:{source.episode_id}:{index}:typed_form')
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
from gene_annotation_episode.episodic_workflow.root.a103 import runtime as _live_original_runtime
