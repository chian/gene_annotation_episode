"""Private literature_strategy waiting behavior for A101."""
from __future__ import annotations

class LiteratureWaiting:

    @property
    def supports_wait(self):
        return False

class LiteratureTaskWaiting:

    def suspension_changed(self, condition):
        self._suspension_condition = condition
        if self.workflow.execution_handle is not None:
            self.workflow.execution_backend.set_suspension(self.workflow.execution_handle, None if condition is None else {'episode_id': self.episode_id, 'dependency': condition})
