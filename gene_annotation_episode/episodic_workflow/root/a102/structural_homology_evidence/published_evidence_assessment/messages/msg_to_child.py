"""The commission of one ``literature_strategy`` child: the strategy the model chose (the records giving the
question context and the sources of this episode's custody the strategy starts from), the commissioned task, the
proposed annotation, the scope and every record this episode names for the child, and the typed answers this
commission selects.

Carried from the old ``to_child_evidence_search_strategy_improvement.assemble_request`` (child goal, scope, initial
report, assignment, knowledge inheritance). The old goal is now a fixed ``objective`` per slot and the message is empty; the scope is a field of the child's
assignment; ``knowledge_inheritance`` is the system's custody. The old model filled the child's whole
``strategy_assignment_v1``; here the model names ``question_context_refs`` and ``prior_search_refs`` and the task,
the proposed annotation and the scope are copied from this episode's summary. The
records named are each prior search source with its artifacts and the sources it derives from that this episode
holds (``summary['literature_source_custody']``), the question context and the proposed annotation. A wrong
commission raises and fails the run."""
from episode_runtime import ChildMessage

SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'

# No text passes: the objective is fixed by the slot and the message is empty (controlled messaging).
OBJECTIVE = 'improve_search_strategy'


def msg_to_child(slot, arguments, summary):
    if slot != 'literature_strategy':
        raise KeyError(slot)
    task, strategy = summary['task'], arguments['strategy']
    custody = {entry['source_ref']: entry for entry in summary['literature_source_custody']}
    passed = [*strategy['question_context_refs'], summary['proposed_annotation_ref']]
    for reference in strategy['prior_search_refs']:
        if reference not in summary['input_list']:      # a consumed or unheld source is not offered
            raise KeyError(reference)
        passed.extend(custody[reference]['passed_record_refs'])
    assignment = {'version': 'strategy_assignment_v1', 'question_context_refs': strategy['question_context_refs'],
                  'prior_search_refs': strategy['prior_search_refs'], 'literature_task': task,
                  'proposed_annotation_ref': summary['proposed_annotation_ref'], 'scope': summary['scope'],
                  'received_record_refs': list(dict.fromkeys(passed))}
    selection = (LEADS,) if task['kind'] == 'verified_source_leads' else (
        (SCREENING,) if task['answer_kind'] == 'screening' else ())
    return ChildMessage(objective=OBJECTIVE, message={}, assignment=assignment, selection=selection)
