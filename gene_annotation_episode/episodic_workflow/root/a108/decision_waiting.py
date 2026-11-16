"""Private A108 annotation decision_waiting responsibility."""
from __future__ import annotations

def waiting_support(workflow, source, context, *, captures):
    with workflow.store.read_snapshot():
        arguments = {}
        metadata = None
        arguments['include_identities'] = True
        metadata = workflow.source_controller_credit(source)
        if metadata is not None:
            arguments['local_return_history'] = workflow.local_return_history.capture(source.episode_id, **metadata)
        support = workflow.wait_inputs.capture(source.episode_id, pending=context['pending_work'], known_progress_refs=workflow.progress_selection(source)['known_progress_refs'], current_duration_expectations=captures, **arguments)
        if metadata is None:
            support['local_return_history_unavailable_reason'] = 'controller_credit_binding_unavailable'
        return support
