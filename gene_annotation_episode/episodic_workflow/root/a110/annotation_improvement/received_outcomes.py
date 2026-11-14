from __future__ import annotations
from .. import runtime as _original_runtime

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
