"""Original private A107 annotation task_state responsibility."""
from __future__ import annotations

def working_state(workflow, source):
    arguments = {'record_selection': workflow.receipts.selection(source.episode_id)} if workflow.uses_received_record_context(source) else {}
    return workflow.store.reasoning_view(source.scope, limit=24, **arguments)
