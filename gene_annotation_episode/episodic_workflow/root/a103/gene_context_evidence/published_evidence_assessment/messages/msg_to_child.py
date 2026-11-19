"""The commission of the one child, ``evidence_search_strategy_improvement``: the strategy assignment
``strategy_assignment_v1`` (the question context and the prior-search sources the model chose), carried from the old
``to_child_evidence_search_strategy_improvement.py`` (whose message carried the scope, the initial report and the
parent's context) and from the child's declared assignment form.

The parent states what the child takes in its own assignment. The question context and the scope are this episode's
own; the prior-search sources are the model's answer (``action`` checked them to be held records). A pass carries
only the records named, so ``received_record_refs`` names every record this episode holds: the child's tools can
read the sources and their artifacts. A commission that is wrong (a record this episode does not hold, a field the
child's form does not admit) raises in custody or in the child's form and fails the run: nothing here checks it. The
child declares no selectable return field, so the selection is empty."""
from episode_runtime import ChildMessage


def msg_to_child(slot, arguments, summary):
    if slot != 'evidence_search_strategy_improvement':
        raise LookupError('published_evidence_assessment_child_slot_unknown:' + repr(slot))
    parent = summary['assignment']
    assignment = {'version': 'strategy_assignment_v1',
                  'question_context_refs': list(parent['question_context_refs']),
                  'prior_search_refs': list(arguments['prior_search_refs']),
                  'scope': parent['scope'],
                  'received_record_refs': list(summary['held_record_refs'])}
    if 'gene_context_evidence' in parent:
        assignment['gene_context_evidence'] = parent['gene_context_evidence']
    return ChildMessage(objective=arguments['objective'], message={'scope': parent['scope']},
                        assignment=assignment, selection=())
