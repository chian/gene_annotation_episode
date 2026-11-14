from gene_annotation_episode.episodic_workflow.root.a103.delivery_counterpart import child_role_for_delivery
from gene_annotation_episode.episodic_workflow.root.a103.from_parent import validate_path
"""Original legacy parent admission of its saved homology monitor report."""
from gene_annotation_episode.episodic_workflow.root.a103.runtime import WorkflowError, _json, _references_in, json

def receive_annotation_homology_monitor_report(self, source, admitted, schema, index, *, redelivery=False):
    validate_path(source.path)
    if self.receipts is not None and (not redelivery) and (not self.is_job_source(source)):
        from gene_annotation_episode.episodic_workflow.root.a103.episode_return_records import EpisodeReturnRecords
        references = EpisodeReturnRecords(self.store, self.run_id, failure_prefix='recorded_admission_').recorded_admission_references(self.binding_context(source), admitted, schema, index)
        if references is not None:
            return references
    if self.progress_provider is not None:
        specialist = self.specialist(source)
        receive_progress = getattr(specialist, 'receive_child_progress', None)
        receive_counterpart = getattr(specialist, 'receive_child_progress_for_role', None)
        handled = False
        if receive_counterpart is not None:
            from gene_annotation_episode.episodic_workflow.root.a103.delivery_counterpart import child_role_for_delivery
            handled = receive_counterpart(self.binding_context(source), child_role_for_delivery(self, source, index), admitted, schema, f'{self.run_id}:{source.episode_id}:{index}:typed_form', self.progress_provider)
        if handled:
            pass
        elif receive_progress is None:
            self.progress_provider.receive_form(source.episode_id, admitted, schema, source.scope, f'{self.run_id}:{source.episode_id}:{index}:typed_form')
        else:
            receive_progress(self.binding_context(source), admitted, schema, f'{self.run_id}:{source.episode_id}:{index}:typed_form', self.progress_provider)
    if self.receipts is None or self.is_job_source(source):
        return []
    references = _live_original_runtime._references_in({}, self.store.get, forms=[(admitted, schema)], reference_subset=lambda refs: self.store.reference_subset(refs, source.scope))
    references.extend(self.episode_bindings.received_form_references(self.binding_context(source), admitted, schema, f'{self.run_id}:{source.episode_id}:{index}:typed_form'))
    references = list(dict.fromkeys(references))
    if self.native_timing_information is not None and self.job_episodes is not None:
        with self.store.transaction():
            key = (self.run_id, source.episode_id, index)
            row = self.store.db.execute('SELECT timing_receipts FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?', key).fetchone()
            if row is None:
                raise _live_original_runtime.WorkflowError('received_form_requires_recorded_attempt')
            if row[0] is None:
                received = self.job_episode_for_child(source.path, child_role_for_delivery(self, source, index)).received_timing_records(self.store, admitted, schema, source.scope)
                self.store.db.execute('UPDATE runtime_report_attempts SET timing_receipts=? WHERE run_id=? AND parent_episode_id=? AND decision_index=?', (_live_original_runtime._json(received), *key))
            else:
                received = _live_original_runtime.json.loads(row[0])
        references.extend((ref for ref in received['native_execution_refs'] if ref not in references))
    self.receipts.receive(source.episode_id, references, kind='report_redelivery' if redelivery else 'child_form', source_index=index)
    references.extend((ref for ref in self.receive_tool_attributions(source, index, kind='report_redelivery' if redelivery else 'child_form') if ref not in references))
    return references
from gene_annotation_episode.episodic_workflow.root.a103 import runtime as _live_original_runtime
