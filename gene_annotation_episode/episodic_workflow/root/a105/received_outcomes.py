"""Original private A105 annotation received_outcomes responsibility."""
from __future__ import annotations

def receive_outcome(workflow, source, selection, result, index):
    if workflow.receipts is not None and (not workflow.is_job_source(source)):
        references = list(result.get('record_refs', []))
        if selection.get('kind') == 'tool' and selection.get('tool') == 'state.query':
            references.extend((row['id'] for row in (result.get('result') or {}).get('records', [])))
        workflow.receipts.receive(source.episode_id, references, kind='own_action', source_index=index)
