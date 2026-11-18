from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.runtime import EventTargetError, _wait_target_feedback

async def perform_selected_native_wait(self, selection, index):
    try:
        result = await self.workflow.perform_selected_wait(self, selection['condition'], index)
    except _live_original_runtime.EventTargetError as error:
        result = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': _live_original_runtime._wait_target_feedback(error, status='failed')}
    return result
from gene_annotation_episode.episodic_workflow.root.a110 import runtime as _live_original_runtime
