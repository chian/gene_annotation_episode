"""The commission of a source examination. The old ``to_child_source_evidence_examination.py`` built the child's goal
(``EpisodeGoal.child``), the message (``scope``, ``initial_report``, the declared contract and the knowledge
inheritance of the old receipts) and sent the model's selection, validated by the child's own ``prepare_assignment``,
as the child's assignment: the page ``page_assignment_v1``.

Here the commission is the child's page assignment: the page the model selected (source, representation, artifact,
question context and earlier deliveries), this episode's scope and finding unit, the partner components when they
were requested, and every record this episode holds (a pass carries only the records named, so the child's tools can
read the source, its artifact and the sources it derives from). The child returns its credit and the
controlled features of its partner sheets; nothing is selected. An error in the commission raises where the child is built;
nothing checks it here."""
from episode_runtime import ChildMessage

PAGE_FIELDS = ('version', 'source_ref', 'representation', 'artifact_ref', 'question_context_refs',
               'prior_delivery_refs')


def msg_to_child(slot, arguments, summary):
    if slot != 'literature_page':
        raise ValueError('unsupported_literature_child_slot:' + str(slot))
    page = arguments['selection']
    assignment = {name: page[name] for name in PAGE_FIELDS}
    assignment.update({'scope': summary['scope'], 'finding_unit': summary['finding_unit'],
                       'received_record_refs': summary['held_record_refs']})
    if summary['partner_components'] is not None:
        assignment['literature_partner_components'] = summary['partner_components']
    return ChildMessage(objective='Investigate where and how the selected source should be examined for the '
                                  'assigned question',
                        message={'slot': slot, 'source_ref': page['source_ref']},
                        assignment=assignment, selection=())
