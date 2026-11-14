"""Original returned action information custody for the parent and compatible sources."""

def receive_outcome(self, source, selection, result, index):
    if self.progress_provider is not None and self.progress_receipt_order == 'received_progress_order_v1':
        self.progress_provider.receive_outcome(source.episode_id, result, source.scope, f'{self.run_id}:{source.episode_id}:{index}:own_progress')
    if self.receipts is not None and (not self.is_job_source(source)):
        references = list(result.get('record_refs', []))
        if selection.get('kind') == 'tool' and selection.get('tool') == 'state.query':
            references.extend((row['id'] for row in (result.get('result') or {}).get('records', [])))
        self.receipts.receive(source.episode_id, references, kind='own_action', source_index=index)
        projection_read = selection.get('kind') == 'tool' and selection.get('tool') in {'episode.credit', 'episode.annotation_score', 'episode.monitoring_information'}
        derived = [] if projection_read else self.receive_tool_attributions(source, index, kind='own_action')
        if derived:
            result['record_refs'] = list(dict.fromkeys([*result.get('record_refs', []), *derived]))
            references.extend((ref for ref in derived if ref not in references))

def _bind_original_runtime(namespace):
    from gene_annotation_episode.episodic_workflow.root.a101.library.live_runtime_functions import bind_functions
    selected = bind_functions(namespace, {name: globals()[name] for name in ('receive_outcome',)},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a101.runtime', qualified_names={'receive_outcome': 'Workflow.receive_outcome'},
        defining_module=None)
    globals().update(selected)

from gene_annotation_episode.episodic_workflow.root.a101 import runtime as _original_runtime
_bind_original_runtime(vars(_original_runtime))
