"""The commissions of the three investigations of the examined source (carried from the old
``to_child_table_evidence_extraction.py``, ``to_child_source_coverage_improvement.py`` and
``to_child_passage_evidence_extraction.py``, which were identical but for the role: ``literature_table``,
``literature_ordered``, ``literature_targeted``).

The old ``prepare_request`` validated the child scope, expanded the report contract form from the fact sources the
child binding required, checked the initial report against the interpretation schema, checked the role against the
allowed children, materialized the launch instructions and let the child binding's ``prepare_assignment`` build
the child's assignment. Here the child declares what it returns and this commission selects the fact sources it
wants (the old fact-source names); the assignment is the child's ``reading_assignment_v1``: the page of this
source, the reading selection the model chose, the commissioned task, the proposed annotation, the scope and every
record this episode names for the child. Nothing is checked here: a commission the child does not admit fails.
The child's scope is this episode's own (the old model-selected sub-scope is not carried).

No text passes: the objective of each investigation is fixed by its slot and the message is empty (controlled
messaging; the model chooses only the reading selection)."""
from episode_runtime import ChildMessage

SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'
OBJECTIVES = {'literature_table': 'investigate_selected_table', 'literature_ordered': 'read_source_in_order',
              'literature_targeted': 'investigate_selected_passages'}


def window(summary, start, end):
    """A byte window of the assigned source in its assigned representation (the child's WINDOW shape)."""
    page = summary['page']
    return {'source_ref': page['source_ref'], 'representation': page['representation'], 'offset': start,
            'limit': end - start}


def selection_of(slot, arguments, summary):
    """The reading the investigation is handed, built from the input list (``summary['content_candidates']`` and its
    unconsumed remainder, ``internal_summary``): ``literature_table`` the one table region the model named,
    ``literature_targeted`` the prose chunks and table regions it named (one span each), ``literature_ordered`` the first
    window of the remaining prose in document order (``report_windows``). What is handed out is consumed
    (``internal_summary.consumed_candidates``)."""
    candidates = {item['candidate_id']: item for item in summary['content_candidates']}
    if slot == 'literature_table':
        item = candidates[arguments['candidate_id']]
        return window(summary, item['start'], item['end'])
    if slot == 'literature_targeted':
        return {'spans': [window(summary, candidates[name]['start'], candidates[name]['end'])
                          for name in arguments['candidate_ids']]}
    start, end = summary['report_windows'][0]
    return window(summary, start, end)


def msg_to_child(slot, arguments, summary):
    task = summary['task']
    # The answers the parent counts: dispositions of the leads of a leads commission (its credit counts them) and
    # the screening answer of a screening commission; an assessment answer is a Store record, not a fact source.
    selection = ((LEADS,) if task['kind'] == 'verified_source_leads'
                 else (SCREENING,) if task['answer_kind'] == 'screening' else ())
    assignment = {'version': 'reading_assignment_v1', 'page': summary['page'],
                  'selection': selection_of(slot, arguments, summary), 'literature_task': task,
                  'proposed_annotation_ref': summary['proposed_annotation_ref'], 'scope': summary['scope'],
                  'received_record_refs': list(summary['received_record_refs'])}
    return ChildMessage(objective=OBJECTIVES[slot], message={},
                        assignment=assignment, selection=selection)
