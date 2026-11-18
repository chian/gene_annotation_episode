"""Private scientific waiting."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a106.runtime import EventTargetError, _wait_target_feedback

class ScientificWaiting:

    def suspension_changed(self, condition):
        self._suspension_condition = condition
        if self.workflow.execution_handle is not None:
            self.workflow.execution_backend.set_suspension(self.workflow.execution_handle, None if condition is None else {'episode_id': self.episode_id, 'dependency': condition})

    async def _execute_selected_wait(self, selection, index):
        try:
            result = await self.workflow.perform_selected_wait(self, selection['condition'], index)
        except EventTargetError as error:
            result = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': _wait_target_feedback(error, status='failed')}
        return result


def _bind_scientific_runtime_providers(namespace):
    from ..library.live_runtime_functions import bind_functions
    names = {'_execute_selected_wait': 'ScientificWaiting._execute_selected_wait'}
    functions = bind_functions(namespace, {name: ScientificWaiting.__dict__[name] for name in names},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a106.runtime', qualified_names=names,
        defining_module='gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.waiting')
    for name, function in functions.items():
        setattr(ScientificWaiting, name, function)

from .. import runtime as _original_runtime
_bind_scientific_runtime_providers(vars(_original_runtime))
