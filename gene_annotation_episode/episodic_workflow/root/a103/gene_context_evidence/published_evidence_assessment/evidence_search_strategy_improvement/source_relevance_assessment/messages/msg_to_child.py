"""The commission of the one child, ``source_evidence_examination``: the page assignment ``page_assignment_v1`` of
the source the model chose (carried from the old ``to_child_source_evidence_examination.py``, whose message carried
the scope and the parent's context, and from the old ``from_parent.py`` of the child, the page it validated).

The parent states what the child takes in its own assignment. The page names the source, the representation read,
the source's artifact for it and the earlier deliveries of that source (the model's answer, checked by ``action``
to name held records); the question context is this episode's own. The child reads the source and its artifact:
both are named in ``received_record_refs``, since a pass carries only the records named.

A commission that is wrong (a record this episode does not hold, a field the child's form does not admit) raises in
custody or in the child's form and fails the run: nothing here checks it. The child declares no selectable return
field, so the selection is empty."""
from episode_runtime import ChildMessage


def msg_to_child(slot, arguments, summary):
    if slot != 'source_evidence_examination':
        raise LookupError('source_relevance_assessment_child_slot_unknown:' + repr(slot))
    parent = summary['assignment']
    custody = next(entry for entry in summary['source_custody'] if entry['source_ref'] == arguments['source_ref'])
    received = list(dict.fromkeys([arguments['source_ref'], arguments['artifact_ref'],
                                   *(custody.get('parent_source_refs') or []), *parent['question_context_refs'],
                                   *arguments['prior_delivery_refs']]))
    assignment = {'version': 'page_assignment_v1', 'source_ref': arguments['source_ref'],
                  'representation': arguments['representation'], 'artifact_ref': arguments['artifact_ref'],
                  'question_context_refs': list(parent['question_context_refs']),
                  'prior_delivery_refs': list(arguments['prior_delivery_refs']),
                  'scope': parent['scope'],
                  'received_record_refs': received}
    if 'gene_context_evidence' in parent:
        assignment['gene_context_evidence'] = parent['gene_context_evidence']
    return ChildMessage(objective=arguments['objective'], message={'scope': parent['scope']},
                        assignment=assignment, selection=())
