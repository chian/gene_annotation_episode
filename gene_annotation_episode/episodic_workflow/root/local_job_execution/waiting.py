"""Keep the original execution-context suspension observation."""
from __future__ import annotations


class LocalTaskWaiting:
    def bind_execution_context(self, context):
        self._execution_context = context

    def suspension_changed(self, condition):
        self._suspension_condition = condition
        if self.workflow.execution_handle is not None:
            self.workflow.execution_backend.set_suspension(self.workflow.execution_handle,
                None if condition is None else {'episode_id': self.episode_id,
                    'dependency': condition})

