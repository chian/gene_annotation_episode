"""The commission of the one child, ``evidence_search_strategy_improvement``. The parent states what the child takes in
its own assignment: the strategy assignment ``strategy_assignment_v1`` (the records that give the question its context
and the prior searches the model chose), the commissioned literature task and proposed annotation, the scope and the
records the child reads. Carried from the old ``to_child_evidence_search_strategy_improvement.py`` (the child goal,
scope and the same original task commission) and from the old ``from_parent.py`` / ``prepare_assignment`` (the child's
assignment carries the parent's task and proposed annotation).

A commission that is wrong (a record this episode does not hold, a field the child's form does not admit) raises in
custody or in the child's form and fails the run: nothing here checks it. For a ``verified_source_leads`` task the lead
dispositions of the child are selected, because the old parent counted the leads its children returned in its own
credit; the child's other facts are not needed by this episode."""
from episode_runtime import ChildMessage

LEADS = 'literature_source_lead_dispositions'


def msg_to_child(slot, arguments, summary):
    parent = summary['assignment']
    strategy = {'version': 'strategy_assignment_v1',
                'question_context_refs': list(arguments['question_context_refs']),
                'prior_search_refs': list(arguments['prior_search_refs'])}
    assignment = {**strategy, 'literature_task': parent['task'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
                  'scope': parent['scope'],
                  'received_record_refs': list(dict.fromkeys([*parent['received_record_refs'],
                                                              *strategy['prior_search_refs'],
                                                              *arguments['custody_refs'],
                                                              *strategy['question_context_refs'],
                                                              *arguments['context_refs']]))}
    selection = (LEADS,) if parent['task']['kind'] == 'verified_source_leads' else ()
    return ChildMessage(objective=arguments['objective'],
                        message={'slot': slot, 'prior_search_refs': list(arguments['prior_search_refs'])},
                        assignment=assignment, selection=selection)
