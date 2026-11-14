"""Original A101 iterative annotation-improvement waiting responsibility."""

def suspension_changed(self, condition):
    self._suspension_condition = condition
    if self.workflow.execution_handle is not None:
        self.workflow.execution_backend.set_suspension(self.workflow.execution_handle, None if condition is None else {'episode_id': self.episode_id, 'dependency': condition})

def _bind_original_runtime(namespace):
    from gene_annotation_episode.episodic_workflow.root.a101.library.live_runtime_functions import bind_functions
    selected = bind_functions(namespace, {name: globals()[name] for name in ('suspension_changed',)},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a101.runtime', qualified_names={'suspension_changed': 'suspension_changed'},
        defining_module='gene_annotation_episode.episodic_workflow.root.a101.annotation_improvement.waiting')
    globals().update(selected)

from gene_annotation_episode.episodic_workflow.root.a101 import runtime as _original_runtime
_bind_original_runtime(vars(_original_runtime))
