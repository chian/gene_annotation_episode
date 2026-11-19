"""What this episode returns to its parent. Always returned: the Episode's credit (``completion['credit']``) and the
finding (what the launch established about the permitted requests). Selectable: ``execution_handoff_refs``,
``execution_handoff_artifact_refs`` (the artifacts the handoff records name), ``execution_result_refs``,
``execution_result_origin`` (the empty record: this launch acquires no result) and ``execution_completed``."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'requested_resource_ids': Field('list', 'The resource ids whose requests the constraints permit'),
    'already_handed_off': Field('list', 'The resource ids that already had a usable handoff when the commission '
                                        'began'),
    'handed_off': Field('list', 'The resource ids that newly received a usable handoff'),
    'handoff_complete': Field('boolean', 'Whether a received handoff is marked complete by its child'),
    'qualification': Field('text', 'What the received handoffs do and do not establish'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the launch established about the permitted requests', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'The records that hold the usable handoffs received',
                                    required=False),
    'execution_handoff_artifact_refs': Field('record_refs', 'The artifacts the handoff records name',
                                             required=False),
    'execution_result_refs': Field('record_refs', 'Actual result acquisitions the children returned',
                                   required=False),
    'execution_result_origin': Field('record', 'Acquisition semantics of a retained result (the empty record: this '
                                               'launch retains none)', required=False),
    'execution_completed': Field('boolean', 'Whether a received handoff is marked complete', required=False),
})


def facts(summary):
    """The facts this Episode recorded."""
    return {'execution_handoff_refs': list(summary['handoff_refs']),
            'execution_handoff_artifact_refs': list(summary['artifact_refs']),
            'execution_result_refs': list(summary['result_refs']), 'execution_result_origin': {},
            'execution_completed': summary['completed']}


def final_to_parent(summary, completion, selection):
    recorded = facts(summary)
    finding = {'requested_resource_ids': list(summary['permitted_resource_ids']),
               'already_handed_off': list(summary['already_handed_off']), 'handed_off': list(summary['handed_off']),
               'handoff_complete': summary['completed'],
               'qualification': ('a usable handoff was received for every resource listed as handed off; a handoff '
                                 'is a record of where the job continues, not an acquired result' if
                                 summary['handed_off'] else 'no usable handoff was received by this launch')}
    result = {'credit': completion['credit'], 'finding': finding, **{name: recorded[name] for name in selection}}
    return result
