from __future__ import annotations
from .. import runtime as _original_runtime

def receive_report(self, source, admitted, schema, index, *, redelivery=False, child_role=None):
    if self.receipts is not None and (not redelivery) and (not self.is_job_source(source)):
        from gene_annotation_episode.episodic_workflow.root.a110.episode_return_records import EpisodeReturnRecords
        references = EpisodeReturnRecords(self.store, self.run_id, failure_prefix='recorded_admission_').recorded_admission_references(self.binding_context(source), admitted, schema, index)
        if references is not None:
            return references
    if self.progress_provider is not None:
        specialist = self.specialist(source)
        receive_progress = getattr(specialist, 'receive_child_progress', None)
        receive_counterpart = getattr(specialist, 'receive_child_progress_for_role', None)
        handled = False
        if receive_counterpart is not None:
            from gene_annotation_episode.episodic_workflow.root.a110.delivery_counterpart import child_role_for_delivery
            handled = receive_counterpart(self.binding_context(source), child_role_for_delivery(self, source, index), admitted, schema, f'{self.run_id}:{source.episode_id}:{index}:typed_form', self.progress_provider)
        if handled:
            pass
        elif receive_progress is None:
            self.progress_provider.receive_form(source.episode_id, admitted, schema, source.scope, f'{self.run_id}:{source.episode_id}:{index}:typed_form')
        else:
            receive_progress(self.binding_context(source), admitted, schema, f'{self.run_id}:{source.episode_id}:{index}:typed_form', self.progress_provider)
    if self.receipts is None or self.is_job_source(source):
        return []
    references = _original_runtime._references_in({}, self.store.get, forms=[(admitted, schema)], reference_subset=lambda refs: self.store.reference_subset(refs, source.scope))
    references.extend(self.episode_bindings.received_form_references(self.binding_context(source), admitted, schema, f'{self.run_id}:{source.episode_id}:{index}:typed_form'))
    references = list(dict.fromkeys(references))
    self.receipts.receive(source.episode_id, references, kind='report_redelivery' if redelivery else 'child_form', source_index=index)
    references.extend((ref for ref in self.receive_tool_attributions(source, index, kind='report_redelivery' if redelivery else 'child_form') if ref not in references))
    return references
