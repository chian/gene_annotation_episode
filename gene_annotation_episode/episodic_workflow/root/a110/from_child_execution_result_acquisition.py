"""Original complete direct-parent results receipt implementation"""
from __future__ import annotations

def receive_report(workflow, source, admitted, schema, index, *, redelivery=False):
    if workflow.receipts is not None and (not redelivery) and (not workflow.is_job_source(source)):
        from gene_annotation_episode.episodic_workflow.root.a110.episode_return_records import EpisodeReturnRecords
        references = EpisodeReturnRecords(workflow.store, workflow.run_id, failure_prefix='recorded_admission_').recorded_admission_references(workflow.binding_context(source), admitted, schema, index)
        if references is not None:
            return references
    if workflow.progress_provider is not None:
        specialist = workflow.specialist(source)
        receive_progress = getattr(specialist, 'receive_child_progress', None)
        receive_counterpart = getattr(specialist, 'receive_child_progress_for_role', None)
        handled = False
        if receive_counterpart is not None:
            from gene_annotation_episode.episodic_workflow.root.a110.delivery_counterpart import child_role_for_delivery
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
    workflow.receipts.receive(source.episode_id, references, kind='report_redelivery' if redelivery else 'child_form', source_index=index)
    references.extend((ref for ref in workflow.receive_tool_attributions(source, index, kind='report_redelivery' if redelivery else 'child_form') if ref not in references))
    return references
from gene_annotation_episode.episodic_workflow.root.a110 import runtime as _live_original_runtime
