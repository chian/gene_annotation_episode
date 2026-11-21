"""Where the extraction stands, from the loop's view: the chunk's text (read through custody from the artifact of the
source's representation the page commissioned), the extraction records its units held, and the counts of the fields they
state (stated, newly stated, asked)."""
from gene_annotation_episode.episodic_workflow.root.a105.experimental_activity_evidence.literature.strategy.web_search.page.chunk.credit import field_counts

# The source record's field holding the artifact of each representation the page can commission (the source record's
# custody keys: artifact_ref the original bytes, text_ref the text projection, stdout_ref and stderr_ref the retained streams).
ARTIFACT_FIELD = {'original': 'artifact_ref', 'text': 'text_ref', 'stdout': 'stdout_ref', 'stderr': 'stderr_ref'}


def internal_summary(view):
    parent = view.parent_input
    artifact = view.records.get(parent['source_ref']).get(ARTIFACT_FIELD[parent['representation']])
    if artifact is None:
        raise LookupError('literature_source_representation_unavailable:' + parent['representation'])
    window = view.records.get_artifact(artifact)[parent['offset']:parent['offset'] + parent['limit']]
    held = [unit['outcome'] for unit in view.outcomes]
    record_refs = list(dict.fromkeys(outcome['record_ref'] for outcome in held))   # content-addressed: the same answer holds the same record
    return {**parent, 'chunk': window.decode('utf-8'), 'chunk_bytes': len(window), 'record_refs': record_refs,
            'counts': field_counts(view.records, record_refs), 'units_consumed': view.units_consumed}
