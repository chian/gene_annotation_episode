"""The commissions of the three children. The parent states what each child takes in its own assignment: the
reading assignment ``reading_assignment_v1`` (this page, the selection the model chose, the scope and the records
the child reads). Carried from the old ``to_child_table_evidence_extraction.py``,
``to_child_source_coverage_improvement.py`` and ``to_child_passage_evidence_extraction.py`` (the message the child
read: its scope and its objective) and from the old ``from_parent.py`` (the page the children re-validated).

A commission that is wrong (a selection the child's form does not admit, a record this episode does not hold)
raises in the child's form or in custody and fails the run: nothing here checks it. The children declare no
selectable return field, so each selection is empty."""
from episode_runtime import ChildMessage


def page_of(parent):
    """This episode's page assignment, as the child's ``page`` field takes it."""
    return {'version': parent['version'], 'source_ref': parent['source_ref'],
            'representation': parent['representation'], 'artifact_ref': parent['artifact_ref'],
            'question_context_refs': list(parent['question_context_refs']),
            'prior_delivery_refs': list(parent['prior_delivery_refs'])}


def msg_to_child(slot, arguments, summary):
    parent = summary['assignment']
    assignment = {'version': 'reading_assignment_v1', 'page': page_of(parent), 'selection': arguments['selection'],
                  'scope': parent['scope']}
    if slot == 'table_evidence_extraction':
        assignment['received_record_refs'] = list(parent['received_record_refs'])
    elif slot in ('source_coverage_improvement', 'passage_evidence_extraction'):
        assignment['record_refs'] = list(dict.fromkeys(
            [*parent['received_record_refs'], *parent['question_context_refs'], *parent['prior_delivery_refs']]))
        if 'gene_context_evidence' in parent:
            assignment['gene_context_evidence'] = parent['gene_context_evidence']
    else:
        raise LookupError('source_evidence_examination_child_slot_unknown:' + repr(slot))
    return ChildMessage(objective=arguments['objective'], message={'scope': parent['scope']},
                        assignment=assignment, selection=())
