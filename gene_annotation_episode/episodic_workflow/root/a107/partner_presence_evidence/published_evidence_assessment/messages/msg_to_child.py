"""The commission of an evidence search strategy improvement. The old ``to_child_evidence_search_strategy_improvement.py``
built the child's goal (``EpisodeGoal.child``), the message (``scope``, ``initial_report``, the declared contract,
the job and episode assignments, ``partner_presence_evidence`` and the knowledge inheritance of the old receipts) and
sent the model's selection, validated by the child's own ``prepare_assignment``, as the child's assignment:
``strategy_assignment_v1``.

Here the commission is the child's strategy assignment: the strategy the model selected (the question context and
the earlier searches), this episode's scope and finding unit, the partner components when they were requested, and
every record this episode holds (a pass carries only the records named, so the child's tools can read the sources,
their artifacts and the sources they derive from). The partner cells and the sheet references are selected, as the
old parent received the child's cells. An error in the commission raises where the child is built; nothing checks it
here."""
from episode_runtime import ChildMessage

STRATEGY_FIELDS = ('version', 'question_context_refs', 'prior_search_refs')


def msg_to_child(slot, arguments, summary):
    if slot != 'literature_strategy':
        raise ValueError('unsupported_literature_child_slot:' + str(slot))
    strategy = arguments['selection']
    for reference in strategy['prior_search_refs']:
        if reference not in summary['input_list']:      # a consumed or unassigned source is not offered
            raise ValueError('prior_search_ref_not_in_input_list:' + str(reference))
    assignment = {name: strategy[name] for name in STRATEGY_FIELDS}
    assignment.update({'scope': summary['scope'], 'finding_unit': summary['finding_unit'],
                       'received_record_refs': summary['held_record_refs']})
    if summary['partner_components'] is not None:
        assignment['literature_partner_components'] = summary['partner_components']
    return ChildMessage(objective='Investigate which search approach is productive for the assigned question',
                        message={'slot': slot, 'prior_search_refs': strategy['prior_search_refs']},
                        assignment=assignment, selection=())
