"""A104 original received_outcomes defining responsibilities."""
from __future__ import annotations
from .library.live_runtime_functions import bind_functions as _bind_functions

def receive_outcome(self, source, selection, result, index):
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
    definitions = {name: globals()[name] for name in ['receive_outcome']}
    globals().update(_bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime', qualified_names={'receive_outcome': 'receive_outcome'}))

from . import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
