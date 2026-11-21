"""The commission of one reading child: the page of this episode's source, the selection the model chose (a table
or window, one starting window, or the passages), the commissioned task, the proposed annotation, the scope and
every record this episode names for the child, and the typed answers this commission selects.

Carried from the three old assemblers ``to_child_table_evidence_extraction``, ``to_child_source_coverage_improvement``
and ``to_child_passage_evidence_extraction`` (byte-identical to each other: child goal, scope, initial report,
assignment, knowledge inheritance). The old goal is now a fixed ``objective`` per slot and the message is empty; the scope is a field of the child's
assignment; ``knowledge_inheritance`` is the system's custody. A wrong commission raises and fails the run."""
from episode_runtime import ChildMessage

SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'

# No text passes: the objective of each investigation is fixed by its slot and the message is empty (controlled
# messaging; the model chooses only the reading selection).
OBJECTIVES = {'literature_table': 'investigate_selected_table', 'literature_ordered': 'read_source_in_order',
              'literature_targeted': 'investigate_selected_passages'}


def msg_to_child(slot, arguments, summary):
    task = summary['task']
    page = {key: summary['literature_assignment'][key] for key in
            ('version', 'source_ref', 'representation', 'artifact_ref', 'question_context_refs',
             'prior_delivery_refs')}
    by_id = {item['candidate_id']: item for item in summary['content_candidates']}

    def window(start, end):
        return {'source_ref': page['source_ref'], 'representation': page['representation'],
                'offset': start, 'limit': end - start}
    # The selection is built from the page's input list: a table region, the first window of the remaining prose in
    # document order (the child continues from it), or the windows of the chosen unconsumed candidates.
    if slot == 'literature_table':
        item = by_id[arguments['candidate_id']]
        selection = window(item['start'], item['end'])
    elif slot == 'literature_ordered':
        start, end = summary['report_windows'][0]
        selection = window(start, end)
    else:
        selection = {'spans': [window(by_id[candidate_id]['start'], by_id[candidate_id]['end'])
                               for candidate_id in arguments['candidate_ids']]}
    assignment = {'version': 'reading_assignment_v1', 'page': page, 'selection': selection,
                  'literature_task': task, 'proposed_annotation_ref': summary['proposed_annotation_ref'],
                  'scope': summary['scope'], 'received_record_refs': summary['received_record_refs']}
    selection = (LEADS,) if task['kind'] == 'verified_source_leads' else (
        (SCREENING,) if task['answer_kind'] == 'screening' else ())
    return ChildMessage(objective=OBJECTIVES[slot], message={},
                        assignment=assignment, selection=selection)
