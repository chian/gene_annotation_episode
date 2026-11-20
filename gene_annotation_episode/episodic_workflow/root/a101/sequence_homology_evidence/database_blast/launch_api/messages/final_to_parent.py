"""What this episode returns: controlled data only. Always returned: ``credit`` (the handoff's credit or zero) and
``finding``, two counts of what the episode did. Selectable: ``execution_handoff_refs`` (the handoff row of the accepted
submission in the job ledger: the job identity the monitor and results children work from, passed in custody) and
``execution_completed`` (whether that handoff is established). Nothing a model wrote is returned: no model is asked
here."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'submissions': Field('integer', 'The submissions made'),
    'failed_submissions': Field('integer', 'The submissions that failed (not sent, lost or refused)'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the Episode did, as counts', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'The handoff row of the accepted submission in the job ledger; '
                                    'empty when no submission was accepted', required=False),
    'execution_completed': Field('boolean', 'Whether the handoff of the assigned job is established; yielding '
                                 'alone is false', required=False),
})


def final_to_parent(summary, completion, selection):
    recorded = {'execution_handoff_refs': list(summary['handoff_refs']),
                'execution_completed': bool(summary['handoff_refs'])}
    failed = [item for item in summary['submissions'] if item['status'] != 'completed']
    result = {'credit': completion['credit'],
              'finding': {'submissions': len(summary['submissions']), 'failed_submissions': len(failed)}}
    for name in selection:
        result[name] = recorded[name]
    return result
