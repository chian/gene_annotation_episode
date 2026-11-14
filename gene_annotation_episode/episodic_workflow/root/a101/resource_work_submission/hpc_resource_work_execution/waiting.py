"""Private A101 launch_hpc waiting."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a101.runtime import EventTargetError, _wait_target_feedback

class OperationalTaskWaiting:

    async def _execute_selected_wait(self, selection, index):
        try:
            result = await self.workflow.perform_selected_wait(self, selection['condition'], index)
        except EventTargetError as error:
            result = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': _wait_target_feedback(error, status='failed')}
        return result


    def suspension_changed(self, condition):
        self._suspension_condition = condition
        if self.workflow.execution_handle is not None:
            self.workflow.execution_backend.set_suspension(self.workflow.execution_handle, None if condition is None else {'episode_id': self.episode_id, 'dependency': condition})


def _bind_original_task_runtime_providers(namespace):
    from gene_annotation_episode.episodic_workflow.root.a101.library.live_runtime_functions import bind_functions
    names = {'_execute_selected_wait': 'OperationalTaskWaiting._execute_selected_wait'}
    functions = bind_functions(namespace, {name: OperationalTaskWaiting.__dict__[name] for name in names},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a101.runtime', qualified_names=names,
        defining_module='gene_annotation_episode.episodic_workflow.root.a101.resource_work_submission.hpc_resource_work_execution.waiting')
    for name, function in functions.items():
        setattr(OperationalTaskWaiting, name, function)

from gene_annotation_episode.episodic_workflow.root.a101 import runtime as _original_runtime
_bind_original_task_runtime_providers(vars(_original_runtime))
