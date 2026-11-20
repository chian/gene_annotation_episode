"""The return: controlled data only. Always returned: the episode's credit (the system hands it in ``completion``) and
the finding, two counts of what the launches did. A parent may select ``execution_handoff_refs`` (the handoff row of
the launched chunk in custody: what a later check or fetch of the job is handed), ``all_vs_all_job_refs`` (the record
of the job: its chunk, its operands and its parameters, which the results episode checks the report against) and
``execution_completed`` (whether the handoff exists). Nothing a model wrote is returned and no field holds text."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'launches_handed_off': Field('integer', 'Launch requests the resource accepted: jobs started and handed off'),
    'launches_failed': Field('integer', 'Launch requests the resource refused: no job was started'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The episode's credit when its controller stopped it"),
    'finding': Field('record', 'The counts of what the launches did', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'The handoff record of the launched chunk: its job ledger row',
                                    required=False),
    'all_vs_all_job_refs': Field('record_refs', 'The record of the launched job: chunk, operands and parameters',
                                 required=False),
    'execution_completed': Field('boolean', 'Whether the handoff of the chunk exists', required=False),
})


def final_to_parent(summary, completion, selection):
    handed_off = len(summary['handoff_refs'])
    facts = {'execution_handoff_refs': list(summary['handoff_refs']), 'all_vs_all_job_refs': list(summary['job_refs']),
             'execution_completed': handed_off > 0}
    return {'credit': completion['credit'],
            'finding': {'launches_handed_off': handed_off, 'launches_failed': len(summary['launches']) - handed_off},
            **{name: facts[name] for name in selection}}
