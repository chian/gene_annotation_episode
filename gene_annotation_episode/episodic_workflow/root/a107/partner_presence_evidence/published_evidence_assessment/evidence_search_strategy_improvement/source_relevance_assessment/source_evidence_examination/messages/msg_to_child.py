"""The commission of a child investigation of this episode's source. The old ``to_child_*.py`` (identical but for the
role constant) admitted the child's scope inside this episode's scope, built the goal and the message
(``scope``, ``initial_report`` and the knowledge inheritance of the old receipts) and sent the model's assignment
through the child's own ``prepare_assignment``.

Here the commission is the child's ``reading_assignment_v1``: this episode's page as the child's ``page``, the
selection the model made, this episode's scope and finding unit, and every record this episode holds (a pass
carries only the records named, so the child's tools can read the source, its artifact and the sources it derives
from). Each assignment is written in the names of that child's own form. The partner cells (and, where the child
declares it, the sheet references) are selected, as the old parent received the child's cells. An error in the
commission raises where the child is built; nothing checks it here."""
from episode_runtime import ChildMessage

OBJECTIVES = {
    'literature_table': 'Investigate the selected table or sheet of the examined source for the assigned question',
    'literature_ordered': 'Investigate the examined source in document order for the assigned question',
    'literature_targeted': 'Investigate the selected passages of the examined source for the assigned question',
}


def msg_to_child(slot, arguments, summary):
    page, scope = summary['page'], summary['scope']
    held = summary['held_record_refs']
    message = {'slot': slot, 'source_ref': page['source_ref']}
    base = {'version': 'reading_assignment_v1', 'page': page, 'selection': arguments['selection'], 'scope': scope}
    components = summary['partner_components']
    if slot == 'literature_table':
        assignment = {**base, 'received_record_refs': held, 'finding_unit': summary['finding_unit']}
        selection = ()
    elif slot == 'literature_ordered':
        assignment = {**base, 'received_record_refs': held}
        if components is not None:
            assignment['literature_partner_components'] = components
        selection = ()
    elif slot == 'literature_targeted':
        assignment = {**base, 'held_refs': held, 'finding_unit': summary['finding_unit']}
        if components is not None:
            assignment['partner_components'] = components
        selection = ()
    else:
        raise ValueError('unsupported_literature_child_slot:' + str(slot))
    return ChildMessage(objective=OBJECTIVES[slot], message=message, assignment=assignment, selection=selection)
