"""The commission of one ``literature_search`` child: the search the model chose (the records giving the question
context and the returned search results of this episode's custody to be assessed), the commissioned task, the
proposed annotation, the scope and every record this episode names for the child, and the typed answers this
commission selects.

Carried from the old ``to_child_source_relevance_assessment.assemble_request`` (child goal, scope, initial report,
assignment, knowledge inheritance). The old goal is now a fixed ``objective`` per slot and the message is empty; the scope is a field of the child's
assignment; ``knowledge_inheritance`` is the system's custody. The old model filled the child's whole assignment;
here the model names ``question_context_refs`` and ``search_result_refs`` and the task, the proposed annotation,
and the scope are copied from this episode's summary. The records named are each search
result with its artifacts and the sources it derives from that this episode holds
(``summary['literature_source_custody']``), the question context and the proposed annotation. A wrong commission
raises and fails the run."""
from episode_runtime import ChildMessage

SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'

# No text passes: the objective is fixed by the slot and the message is empty (controlled messaging).
OBJECTIVE = 'assess_returned_sources'


def msg_to_child(slot, arguments, summary):
    if slot != 'literature_search':
        raise KeyError(slot)
    task, search = summary['task'], arguments['search']
    custody = {entry['source_ref']: entry for entry in summary['literature_source_custody']}
    passed = [*search['question_context_refs'], summary['proposed_annotation_ref']]
    for reference in search['search_result_refs']:
        passed.extend(custody[reference]['passed_record_refs'])
    assignment = {'version': 'search_assignment_v1', 'question_context_refs': search['question_context_refs'],
                  'search_result_refs': search['search_result_refs'], 'literature_task': task,
                  'proposed_annotation_ref': summary['proposed_annotation_ref'], 'scope': summary['scope'],
                  'received_record_refs': list(dict.fromkeys(passed))}
    selection = (LEADS,) if task['kind'] == 'verified_source_leads' else (
        (SCREENING,) if task['answer_kind'] == 'screening' else ())
    return ChildMessage(objective=OBJECTIVE, message={}, assignment=assignment, selection=selection)
