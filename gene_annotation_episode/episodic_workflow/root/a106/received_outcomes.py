"""A106 original received_outcomes defining responsibilities."""
from __future__ import annotations
from .library.live_runtime_functions import bind_functions as _bind_functions

def receive_outcome(self, source, selection, result, index):
    if self.progress_provider is not None:
        self.progress_provider.receive_outcome(source.episode_id, result, source.scope, f'{self.run_id}:{source.episode_id}:{index}:own_progress')
    from .annotation_improvement.episode import is_improvement_parent
    if is_improvement_parent(self, source):
        from .annotation_improvement.received_outcomes import receive_outcome
        return receive_outcome(self, source, selection, result, index)
    if self.receipts is not None and (not self.is_job_source(source)):
        references = list(result.get('record_refs', []))
        if selection.get('kind') == 'tool' and selection.get('tool') == 'state.query':
            references.extend((row['id'] for row in (result.get('result') or {}).get('records', [])))
        self.receipts.receive(source.episode_id, references, kind='own_action', source_index=index)

def _bind_original_runtime(namespace):
    names = {'receive_outcome': 'Workflow.receive_outcome'}
    globals().update(_bind_functions(namespace, {name: globals()[name] for name in names}, runtime_module='gene_annotation_episode.episodic_workflow.root.a106.runtime', qualified_names=names, defining_module=None))
from . import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
