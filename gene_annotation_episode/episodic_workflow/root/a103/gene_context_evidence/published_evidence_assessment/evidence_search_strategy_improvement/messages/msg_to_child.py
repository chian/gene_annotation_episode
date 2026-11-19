"""The commission of the one child, ``source_relevance_assessment``: the search assignment ``search_assignment_v1``
(the question context and the returned sources the model chose), carried from the old
``to_child_source_relevance_assessment.py`` (whose message carried the scope and the parent's context) and from the
old ``from_parent.py`` of the child, the assignment it validated.

The parent states what the child takes in its own assignment. The question context and the scope are this episode's
own; the sources are the model's answer (``action`` checked them to be held records). A pass carries only the
records named, so ``received_record_refs`` names every record this episode holds: the child's tools can read the
sources and their artifacts. A commission that is wrong (a record this episode does not hold, a field the child's
form does not admit) raises in custody or in the child's form and fails the run: nothing here checks it. The child
declares no selectable return field, so the selection is empty."""
from episode_runtime import ChildMessage


def msg_to_child(slot, arguments, summary):
    if slot != 'source_relevance_assessment':
        raise LookupError('evidence_search_strategy_improvement_child_slot_unknown:' + repr(slot))
    parent = summary['assignment']
    assignment = {'version': 'search_assignment_v1',
                  'question_context_refs': list(parent['question_context_refs']),
                  'search_result_refs': list(arguments['search_result_refs']),
                  'scope': parent['scope'],
                  'received_record_refs': list(summary['held_record_refs'])}
    if 'gene_context_evidence' in parent:
        assignment['gene_context_evidence'] = parent['gene_context_evidence']
    return ChildMessage(objective=arguments['objective'], message={'scope': parent['scope']},
                        assignment=assignment, selection=())
