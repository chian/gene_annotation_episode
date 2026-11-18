"""Original selected scientific waiting, including unavailable-target outcomes and unchanged prior-credit handling in the task."""
from gene_annotation_episode.episodic_workflow.root.a108.runtime import EventTargetError, _wait_target_feedback

class ScientificWaiting:

    async def perform_selected_wait(self, selection, index):
        try:
            result = await self.workflow.perform_selected_wait(self, selection['condition'], index)
        except _original_runtime.EventTargetError as error:
            result = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': _original_runtime._wait_target_feedback(error, status='failed')}
        return result
from gene_annotation_episode.episodic_workflow.root.a108 import runtime as _original_runtime
