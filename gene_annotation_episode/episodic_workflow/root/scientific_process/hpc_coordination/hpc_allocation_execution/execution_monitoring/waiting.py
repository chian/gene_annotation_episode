from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.method_loop.durable import EventTargetError
from gene_annotation_episode.episodic_workflow.root.waiting import _wait_target_feedback

class MonitorWaiting:

    def suspension_changed(self, condition):
        self._suspension_condition = condition
        if self.workflow.execution_handle is not None:
            self.workflow.execution_backend.set_suspension(self.workflow.execution_handle, None if condition is None else {'episode_id': self.episode_id, 'dependency': condition})

    async def _perform_wait_action(self, selection, index):
        try:
            result = await self.workflow.perform_selected_wait(self, selection['condition'], index)
        except EventTargetError as error:
            result = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': _wait_target_feedback(error, status='failed')}
        return result
