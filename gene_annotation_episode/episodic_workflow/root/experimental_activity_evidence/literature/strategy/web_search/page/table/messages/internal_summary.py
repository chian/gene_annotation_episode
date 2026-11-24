"""Where the extraction stands: the table's text (the commissioned byte window, read through custody from the artifact of
the commissioned representation, ``representation_content``), and the library's ``extraction_state``: the held leaf
records, the field counts, the records that stand (one per experiment ref) and what they already state and leave unstated.

The input list (nano-graphrag: a table region is consumed when it is selected): ``input_list`` holds the one window of the
commission, ``[[offset, offset + limit]]``, until it has been extracted once, and is empty after that.
While a form of the latest extraction is refused (``refused``: experiment type -> reason) the window stays on the list:
the next unit reads it again for those types."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    extraction_state, refused_forms, representation_content)


def internal_summary(view):
    parent = view.parent_input
    content = representation_content(view.records, parent['source_ref'], parent['representation'])
    window = content[parent['offset']:parent['offset'] + parent['limit']]
    extracted = [outcome for outcome in view.outcomes if outcome['tool'] == 'extract']
    return {**parent, 'table': window.decode('utf-8'), 'table_bytes': len(window),
            **extraction_state(view.records, extracted), 'units_consumed': view.units_consumed,
            'refused': refused_forms(extracted),
            'input_list': ([] if extracted and not refused_forms(extracted)
                           else [[parent['offset'], parent['offset'] + parent['limit']]])}
