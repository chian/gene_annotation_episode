"""Private root annotation waiting."""
from __future__ import annotations

def _wait_target_feedback(error, *, status):
    return {'status': status, 'category': 'wait_target', 'code': error.code, 'affected_refs': list(error.affected_refs), 'detail': str(error)}

class AnnotationWaiting:

    def suspension_changed(self, condition):
        self._suspension_condition = condition
        if self.workflow.execution_handle is not None:
            self.workflow.execution_backend.set_suspension(self.workflow.execution_handle, None if condition is None else {'episode_id': self.episode_id, 'dependency': condition})
