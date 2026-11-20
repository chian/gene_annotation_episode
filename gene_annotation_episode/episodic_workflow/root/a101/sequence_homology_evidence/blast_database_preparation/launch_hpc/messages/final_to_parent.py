"""The return: controlled data only. Always: the credit and the finding (two counts). Selectable:
``execution_handoff_refs`` (the handoff row of the launched job, a record reference the parent then holds) and
``execution_completed`` (whether the handoff exists)."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'launches_handed_off': Field('integer', 'Launch requests the resource accepted: jobs started and handed off'),
    'launches_failed': Field('integer', 'Launch requests the resource refused: no job was started'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The counts of what the launch actions did', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'The handoff record of the launched job: its job ledger row',
                                    required=False),
    'execution_completed': Field('boolean', 'Whether the handoff of the commissioned job exists', required=False),
    'plan_refs': Field('record_refs', 'The artifact of the plan the launched job runs: what the results of the job '
                                      'are later checked against', required=False),
})


def final_to_parent(summary, completion, selection):
    handed_off = len(summary['handoff_refs'])
    facts = {'execution_handoff_refs': list(summary['handoff_refs']), 'execution_completed': handed_off > 0,
             'plan_refs': list(summary['plan_refs'])}
    return {'credit': completion['credit'],
            'finding': {'launches_handed_off': handed_off, 'launches_failed': len(summary['launches']) - handed_off},
            **{name: facts[name] for name in selection}}
