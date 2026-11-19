"""The commission of the examination of one source. The old ``to_child_source_evidence_examination.py`` admitted the
child's scope inside this episode's scope, composed the report form from the model's selection, and sent the
model's page assignment through the child's own ``prepare_assignment``.

Here the commission is the child's ``page_assignment_v1`` (the page the model selected, which names the exact source
to examine and its artifact), this episode's scope and every record this episode holds (a pass carries only the
records named, so the child's tools can read the source, its artifact and the sources it derives from). The child
declares no selectable field, so none is selected. An error in the commission raises where the child is built;
nothing checks it here. Nothing requires the page's source to be one of this episode's ``search_result_refs`` (the
old file did not either)."""
from episode_runtime import ChildMessage


def msg_to_child(slot, arguments, summary):
    return ChildMessage(objective='Investigate where and how the selected source should be examined for the '
                                  'assigned question',
                        message={'slot': slot, 'source_ref': arguments['page']['source_ref']},
                        assignment={**arguments['page'], 'scope': summary['scope'],
                                    'received_record_refs': summary['held_record_refs']},
                        selection=())
