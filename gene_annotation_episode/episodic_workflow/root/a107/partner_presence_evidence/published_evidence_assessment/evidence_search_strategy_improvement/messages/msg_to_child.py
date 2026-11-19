"""The commission of a source relevance assessment. The old ``to_child_source_relevance_assessment.py`` built the
child's goal (``EpisodeGoal.child``), the message (``scope``, ``initial_report``, the declared contract and the
knowledge inheritance of the old receipts) and sent the model's selection, validated by the child's own
``prepare_assignment``, as the child's assignment: ``search_assignment_v1``.

Here the commission is the child's search assignment: the search the model selected (the question context and the
located sources), this episode's scope and finding unit, the partner components when they were requested, and every
record this episode holds (a pass carries only the records named, so the child's tools can read the sources, their
artifacts and the sources they derive from). The partner cells and the sheet references are selected, as the old
parent received the child's cells. An error in the commission raises where the child is built; nothing checks it
here."""
from episode_runtime import ChildMessage

SEARCH_FIELDS = ('version', 'question_context_refs', 'search_result_refs')


def msg_to_child(slot, arguments, summary):
    if slot != 'literature_search':
        raise ValueError('unsupported_literature_child_slot:' + str(slot))
    search = arguments['selection']
    assignment = {name: search[name] for name in SEARCH_FIELDS}
    assignment.update({'scope': summary['scope'], 'finding_unit': summary['finding_unit'],
                       'received_record_refs': summary['held_record_refs']})
    if summary['partner_components'] is not None:
        assignment['literature_partner_components'] = summary['partner_components']
    return ChildMessage(objective='Investigate which of the located sources merit examination for the assigned '
                                  'question',
                        message={'slot': slot, 'search_result_refs': search['search_result_refs']},
                        assignment=assignment, selection=())
