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


def without_nulls(value):
    """The model's selection names every field of the table and window shapes and leaves those of the other shape
    null; the child's form takes a field only when it is present."""
    if isinstance(value, dict):
        return {name: without_nulls(item) for name, item in value.items() if item is not None}
    if isinstance(value, list):
        return [without_nulls(item) for item in value]
    return value


def msg_to_child(slot, arguments, summary):
    task = summary['task']
    # The answers the parent counts: dispositions of the leads of a leads commission (its credit counts them) and
    # the screening answer of a screening commission; an assessment answer is a Store record, not a fact source.
    selection = ((LEADS,) if task['kind'] == 'verified_source_leads'
                 else (SCREENING,) if task['answer_kind'] == 'screening' else ())
    assignment = {'version': 'reading_assignment_v1', 'page': summary['page'],
                  'selection': without_nulls(arguments['selection']), 'literature_task': task,
                  'proposed_annotation_ref': summary['proposed_annotation_ref'], 'scope': summary['scope'],
                  'received_record_refs': list(summary['received_record_refs'])}
    return ChildMessage(objective=OBJECTIVES[slot], message={},
                        assignment=assignment, selection=selection)
