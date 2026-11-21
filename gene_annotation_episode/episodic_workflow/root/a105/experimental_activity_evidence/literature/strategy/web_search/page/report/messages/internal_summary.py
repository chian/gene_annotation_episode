"""Where the document-order extraction stands (nano-graphrag ``ReportWindowSource``: the remaining prose read in document
order, each chunk once). The input list (``input_list``) is the commissioned windows not yet read, in document order:
after k extractions it is ``windows[k:]``, and each extraction reads its first window and removes it. The window of this
unit is the first of that list (``offset``, ``limit``, ``window``: its text read through custody from the artifact of the
commissioned representation, ``representation_content``); with the list empty there is no window. Also the library's
``extraction_state`` over the extractions (the leaf records held, the field counts, the records that stand: one per window),
and ``windows_total``, the number of commissioned windows."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    extraction_state, representation_content)


def internal_summary(view):
    parent = view.parent_input
    extracted = [outcome for outcome in view.outcomes if outcome['tool'] == 'extract']
    remaining = parent['windows'][len(extracted):]
    current = {'offset': None, 'limit': None, 'window': None, 'window_bytes': 0}
    start = None
    if remaining:
        content = representation_content(view.records, parent['source_ref'], parent['representation'])
        start, end = remaining[0]
        current = {'offset': start, 'limit': end - start, 'window': content[start:end].decode('utf-8'),
                   'window_bytes': end - start}
    return {**parent, **current, **extraction_state(view.records, extracted, window_start=start),
            'windows_total': len(parent['windows']), 'input_list': remaining, 'units_consumed': view.units_consumed}
