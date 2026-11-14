"""Original A101 iterative annotation-improvement working_state responsibility."""

def working_state(self, source):
    arguments = {'record_selection': self.receipts.selection(source.episode_id)} if self.uses_received_record_context(source) else {}
    return self.store.reasoning_view(source.scope, limit=24, **arguments)

def _bind_original_runtime(namespace):
    from gene_annotation_episode.episodic_workflow.root.a101.library.live_runtime_functions import bind_functions
    selected = bind_functions(namespace, {name: globals()[name] for name in ('working_state',)},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a101.runtime', qualified_names={'working_state': 'working_state'},
        defining_module='gene_annotation_episode.episodic_workflow.root.a101.annotation_improvement.working_state')
    globals().update(selected)

from gene_annotation_episode.episodic_workflow.root.a101 import runtime as _original_runtime
_bind_original_runtime(vars(_original_runtime))
