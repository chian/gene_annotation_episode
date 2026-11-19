"""The commission of the assessment of which returned sources merit examination. The old
``to_child_source_relevance_assessment.py`` admitted the child's scope inside this episode's scope, composed the
report form from the model's selection, and sent the model's search assignment through the child's own
``prepare_assignment``.

Here the commission is the child's ``search_assignment_v1`` (the question context and the sources a search
returned, which the model selected), this episode's scope and every record this episode holds (a pass carries only
the records named, so the child's tools can read the sources and their artifacts). The child declares no
selectable field, so none is selected. An error in the commission raises where the child is built; nothing checks
it here."""
from episode_runtime import ChildMessage


def msg_to_child(slot, arguments, summary):
    return ChildMessage(objective='Investigate which returned sources merit examination for the assigned question',
                        message={'slot': slot, 'search_result_refs': arguments['search']['search_result_refs']},
                        assignment={**arguments['search'], 'scope': summary['scope'],
                                    'received_record_refs': summary['held_record_refs']},
                        selection=())
