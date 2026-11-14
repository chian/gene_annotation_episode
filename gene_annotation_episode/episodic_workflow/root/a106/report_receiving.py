"""A106 original report_receiving defining responsibilities."""
from __future__ import annotations
from .library.live_runtime_functions import bind_functions as _bind_functions

def _receive_form(self, source, admitted, schema, index, *, redelivery=False):
    binding_receiver_selector = getattr(self.specialist(source), 'child_report_receiver_for_binding', None)
    if binding_receiver_selector is not None:
        from .delivery_counterpart import child_role_for_delivery
        original_role = child_role_for_delivery(self, source, index)
        original_binding = self.episode_bindings.for_child(source.path, original_role)
        named_receiver = binding_receiver_selector(original_role, original_binding.binding_path)
        if named_receiver is not None:
            return named_receiver(self, source, admitted, schema, index, redelivery=redelivery)
    receiver_for_role = getattr(self.specialist(source), 'child_report_receiver', None)
    if receiver_for_role is not None:
        from .delivery_counterpart import child_role_for_delivery
        receiver = receiver_for_role(child_role_for_delivery(self, source, index))
        if receiver is not None:
            return receiver(self, source, admitted, schema, index, redelivery=redelivery)
    if binding_receiver_selector is not None:
        from .scientific_process.child_message_owners import exchange_for_child
        child_exchange = exchange_for_child(self, source, original_role)
        if child_exchange is not None:
            return child_exchange[3](self, source, admitted, schema, index, redelivery=redelivery)
    if self.receipts is not None and (not redelivery) and (not self.is_job_source(source)):
        from .episode_return_records import EpisodeReturnRecords
        references = EpisodeReturnRecords(self.store, self.run_id, failure_prefix='recorded_admission_').recorded_admission_references(self.binding_context(source), admitted, schema, index)
        if references is not None:
            return references
    if self.progress_provider is not None:
        specialist = self.specialist(source)
        receive_progress = getattr(specialist, 'receive_child_progress', None)
        receive_counterpart = getattr(specialist, 'receive_child_progress_for_role', None)
        handled = False
        if receive_counterpart is not None:
            from .delivery_counterpart import child_role_for_delivery
            handled = receive_counterpart(self.binding_context(source), child_role_for_delivery(self, source, index), admitted, schema, f'{self.run_id}:{source.episode_id}:{index}:typed_form', self.progress_provider)
        if handled:
            pass
        elif receive_progress is None:
            self.progress_provider.receive_form(source.episode_id, admitted, schema, source.scope, f'{self.run_id}:{source.episode_id}:{index}:typed_form')
        else:
            receive_progress(self.binding_context(source), admitted, schema, f'{self.run_id}:{source.episode_id}:{index}:typed_form', self.progress_provider)
    if self.receipts is None or self.is_job_source(source):
        return []
    references = _references_in({}, self.store.get, forms=[(admitted, schema)], reference_subset=lambda refs: self.store.reference_subset(refs, source.scope))
    references.extend(self.episode_bindings.received_form_references(self.binding_context(source), admitted, schema, f'{self.run_id}:{source.episode_id}:{index}:typed_form'))
    references = list(dict.fromkeys(references))
    if self.native_timing_information is not None and self.job_episodes is not None:
        with self.store.transaction():
            key = (self.run_id, source.episode_id, index)
            row = self.store.db.execute('SELECT timing_receipts FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?', key).fetchone()
            if row is None:
                raise WorkflowError('received_form_requires_recorded_attempt')
            if row[0] is None:
                received = self.job_episodes.received_timing_records(self.store, admitted, schema, source.scope)
                self.store.db.execute('UPDATE runtime_report_attempts SET timing_receipts=? WHERE run_id=? AND parent_episode_id=? AND decision_index=?', (_json(received), *key))
            else:
                received = json.loads(row[0])
        references.extend((ref for ref in received['native_execution_refs'] if ref not in references))
    self.receipts.receive(source.episode_id, references, kind='report_redelivery' if redelivery else 'child_form', source_index=index)
    return references


def _bind_original_runtime(namespace):
    names = {'_receive_form': 'Workflow._receive_form'}
    globals().update(_bind_functions(namespace, {name: globals()[name] for name in names},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a106.runtime', qualified_names=names,
        defining_module=None))

from . import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
