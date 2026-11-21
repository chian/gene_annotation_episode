"""The return, chosen for the parent's next decision: whether a usable handoff now exists (its credit says so) and
which records carry it. Always returned: the credit (the system's), the finding (two controlled values: the state
of the launched job at its latest receiving check, and whether its results are available yet), the handoff row of
the launched job and the rows of its receiving checks, in custody. The parent passes those rows to whoever monitors
the job or fetches its results. No text is returned and nothing describes the handoff: the rows are the handoff."""
from episode_runtime.job_access import STATES
from method_loop import ChoiceField, Field, RecordForm

JOB_STATES = ('not_launched', 'not_checked', *STATES)

FINDING_FORM = RecordForm({
    'job_state': ChoiceField('text', 'The state of the launched job at its latest receiving check', JOB_STATES),
    'result_available': Field('boolean', 'Whether that check found the results of the job available'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The state of the launched job at its latest receiving check', form=FINDING_FORM),
    'handoff_refs': Field('record_refs', 'The handoff row of the launched job'),
    'check_refs': Field('record_refs', 'The rows of the receiving checks of that job'),
})


def final_to_parent(summary, completion, selection):
    jobs = summary['jobs']
    return {'credit': completion['credit'],
            'finding': {'job_state': jobs[-1]['state'] if jobs else 'not_launched',
                        'result_available': bool(jobs) and jobs[-1]['result_available']},
            'handoff_refs': [job['handoff_ref'] for job in jobs],
            'check_refs': [ref for job in jobs for ref in job['check_refs']]}
