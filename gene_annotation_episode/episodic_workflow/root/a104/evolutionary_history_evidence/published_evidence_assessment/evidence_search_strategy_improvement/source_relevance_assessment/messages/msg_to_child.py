"""The commission of the one child, ``source_evidence_examination``. The parent states what the child takes in its own
assignment: the page assignment ``page_assignment_v1`` (the one source the model chose, its representation and that
representation's artifact, the records that give the question its context and the records delivered by earlier
examinations of the source), the commissioned literature task and proposed annotation, the scope and the records the
child reads. Carried from the old ``to_child_source_evidence_examination.py`` (the child goal, scope and the same
original task commission) and from the old ``from_parent.py`` (``child_assignment_schema``: the page the child takes).

A commission that is wrong (a record this episode does not hold, a field the child's form does not admit) raises in
custody or in the child's form and fails the run: nothing here checks it. For a ``verified_source_leads`` task the lead
dispositions of the child are selected, because the old parent counted the leads its children returned in its own
credit; the child's other facts are not needed by this episode."""
from episode_runtime import ChildMessage

LEADS = 'literature_source_lead_dispositions'


def msg_to_child(slot, arguments, summary):
    parent = summary['assignment']
    page = {'version': 'page_assignment_v1', 'source_ref': arguments['source_ref'],
            'representation': arguments['representation'], 'artifact_ref': arguments['artifact_ref'],
            'question_context_refs': list(parent['search']['question_context_refs']),
            'prior_delivery_refs': list(arguments['prior_delivery_refs'])}
    assignment = {**page, 'literature_task': parent['task'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
                  'scope': parent['scope'],
                  'received_record_refs': list(dict.fromkeys([*parent['received_record_refs'],
                                                              arguments['source_ref'], arguments['artifact_ref'],
                                                              *arguments['custody_refs'],
                                                              *page['question_context_refs'],
                                                              *page['prior_delivery_refs']]))}
    selection = (LEADS,) if parent['task']['kind'] == 'verified_source_leads' else ()
    return ChildMessage(objective=arguments['objective'], message={'slot': slot, 'source_ref': arguments['source_ref']},
                        assignment=assignment, selection=selection)
