"""The commissions of the three children. The parent states what each child takes in its own assignment: the
reading assignment ``reading_assignment_v1`` (this page, the selection the model chose, the commissioned literature
task and proposed annotation, the scope and the records the child reads). Carried from the old
``to_child_table_evidence_extraction.py``, ``to_child_source_coverage_improvement.py`` and
``to_child_passage_evidence_extraction.py`` (the child goal, scope and the same original task commission) and from
the old ``from_parent.py`` (the page the children re-validated).

A commission that is wrong (a selection the child's form does not admit, a record this episode does not hold)
raises in the child's form or in custody and fails the run: nothing here checks it. For a ``verified_source_leads``
task the lead dispositions of the child are selected, because the old parent counted the leads its children
returned in its own credit; the other children's facts are not needed by this episode."""
from episode_runtime import ChildMessage

LEADS = 'literature_source_lead_dispositions'


def msg_to_child(slot, arguments, summary):
    parent = summary['assignment']
    page = parent['page']
    assignment = {'version': 'reading_assignment_v1', 'page': dict(page), 'selection': arguments['selection'],
                  'literature_task': parent['task'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
                  'scope': parent['scope'],
                  'received_record_refs': list(dict.fromkeys([*parent['received_record_refs'],
                                                              *page['question_context_refs'],
                                                              *page['prior_delivery_refs']]))}
    selection = (LEADS,) if parent['task']['kind'] == 'verified_source_leads' else ()
    return ChildMessage(objective=arguments['objective'], message={'slot': slot, 'source_ref': page['source_ref']},
                        assignment=assignment, selection=selection)
