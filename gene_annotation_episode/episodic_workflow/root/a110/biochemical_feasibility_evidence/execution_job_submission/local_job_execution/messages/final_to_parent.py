"""The return: controlled data only. Always returned: the Episode's credit (the system hands it in ``completion``;
it is the signal of whether the launch was productive) and the finding, which is three counts of what the Episode
did. A parent may select ``execution_handoff_refs``, the handoff record of the launched job as a record reference
(the ``JOB_LEDGER`` row, in custody: what a later check or fetch of the job is handed), and
``execution_completed``, whether the handoff exists. Nothing the model wrote is returned and no field holds text."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'launches_handed_off': Field('integer', 'Launch requests the resource accepted: jobs started and handed off'),
    'launches_failed': Field('integer', 'Launch requests the resource refused: no job was started'),
    'holds': Field('integer', 'Actions that held the launch'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The counts of what the launch actions did', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'The handoff record of the launched job: its job ledger row',
                                    required=False),
    'execution_completed': Field('boolean', 'Whether the handoff of the assigned job exists', required=False),
})


def final_to_parent(summary, completion, selection):
    launches = summary['launches']
    handed_off = len(summary['handoff_refs'])
    facts = {'execution_handoff_refs': list(summary['handoff_refs']), 'execution_completed': handed_off > 0}
    return {'credit': completion['credit'],
            'finding': {'launches_handed_off': handed_off, 'launches_failed': len(launches) - handed_off,
                        'holds': len(summary['holds'])},
            **{name: facts[name] for name in selection}}
