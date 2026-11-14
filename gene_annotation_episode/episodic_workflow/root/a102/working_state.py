"""Actual annotation working_state remainder."""
from __future__ import annotations

def working_state(self, source):
    arguments = ({'record_selection': self.receipts.selection(source.episode_id)}
                 if self.uses_received_record_context(source) else {})
    return self.store.reasoning_view(source.scope, limit=24, **arguments)

