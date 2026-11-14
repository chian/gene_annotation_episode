"""A106 original working_state defining responsibilities."""
from __future__ import annotations
from .library.live_runtime_functions import bind_functions as _bind_functions

def working_state(self, source):
    from .annotation_improvement.episode import is_improvement_parent
    if is_improvement_parent(self, source):
        from .annotation_improvement.working_state import working_state
        return working_state(self, source)
    arguments = {'record_selection': self.receipts.selection(source.episode_id)} if self.uses_received_record_context(source) else {}
    return self.store.reasoning_view(source.scope, limit=24, **arguments)

def _bind_original_runtime(namespace):
    names = {'working_state': 'working_state'}
    globals().update(_bind_functions(namespace, {name: globals()[name] for name in names}, runtime_module='gene_annotation_episode.episodic_workflow.root.a106.runtime', qualified_names=names, defining_module='gene_annotation_episode.episodic_workflow.root.a106.working_state'))
from . import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
