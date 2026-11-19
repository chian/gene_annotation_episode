"""The commission of a child investigation of this episode's source. The old ``to_child_*.py`` (identical but for
the role constant) admitted the child's scope inside this episode's scope, composed the report form from the model's
selection, and sent the model's assignment through the child's own ``prepare_assignment``.

Here the commission is the child's ``reading_assignment_v1``: this episode's page, the selection the model made, this
episode's scope and every record this episode holds (a pass carries only the records named, so the child's tools can
read the source, its artifact and the sources it derives from). The children declare no selectable field, so none is
selected. An error in the commission raises where the child is built; nothing checks it here."""
from episode_runtime import ChildMessage

OBJECTIVES = {
    'table_evidence_extraction': 'Investigate the selected table or sheet of the examined source for the assigned question',
    'source_coverage_improvement': 'Investigate the examined source in document order for the assigned question',
    'passage_evidence_extraction': 'Investigate the selected passages of the examined source for the assigned question',
}


def msg_to_child(slot, arguments, summary):
    return ChildMessage(objective=OBJECTIVES[slot],
                        message={'slot': slot, 'source_ref': summary['literature_assignment']['source_ref']},
                        assignment={'version': 'reading_assignment_v1', 'page': summary['literature_assignment'],
                                    'selection': arguments['selection'], 'scope': summary['scope'],
                                    'received_record_refs': summary['held_record_refs']},
                        selection=())
