from __future__ import annotations
from .. import runtime as _original_runtime

def waiting_support(self, source, context, *, captures):
    with self.store.read_snapshot():
        arguments = {}
        metadata = None
        if self.wait_inputs_version == 'wait_inputs_binding_v2':
            arguments['include_identities'] = True
            metadata = self.source_controller_credit(source)
            if metadata is not None:
                arguments['local_return_history'] = self.local_return_history.capture(source.episode_id, **metadata)
        support = self.wait_inputs.capture(source.episode_id, pending=context['pending_work'], known_progress_refs=self.progress_selection(source)['known_progress_refs'], current_duration_expectations=captures, **arguments)
        if self.wait_inputs_version == 'wait_inputs_binding_v2' and metadata is None:
            support['local_return_history_unavailable_reason'] = 'controller_credit_binding_unavailable'
        return support
