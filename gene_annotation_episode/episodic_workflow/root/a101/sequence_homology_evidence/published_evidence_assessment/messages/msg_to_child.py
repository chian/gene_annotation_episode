"""The commission of the strategy investigation. The old ``to_child_evidence_search_strategy_improvement.py``
admitted the child's scope inside this episode's scope, composed the report form from the model's selection and
sent the model's strategy assignment through the child's own ``prepare_assignment``.

Here the commission is the child's ``strategy_assignment_v1`` (the question context and the searches already made,
which the model selected), this episode's scope and every record this episode holds (a pass carries only the
records named, so the child's tools can read the sources and their artifacts). The child declares no selectable
field, so none is selected. An error in the commission raises where the child is built; nothing checks it here."""
from episode_runtime import ChildMessage


def msg_to_child(slot, arguments, summary):
    return ChildMessage(objective='Investigate which search approach is productive for the assigned question',
                        message={'slot': slot, 'prior_search_refs': arguments['strategy']['prior_search_refs']},
                        assignment={**arguments['strategy'], 'scope': summary['scope'],
                                    'received_record_refs': summary['held_record_refs']},
                        selection=())
