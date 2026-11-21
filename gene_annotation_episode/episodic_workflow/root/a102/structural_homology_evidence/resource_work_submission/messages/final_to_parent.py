"""The return, chosen for the scientific parent's next decision: monitor the launched job or acquire its results
(it needs the handoff row and the kind of route the job is on), or try the launch another way (its credit says
whether a usable handoff exists). Always returned: the credit (the system's), the finding (two values of fixed
vocabularies: the state of the launched job at its latest receiving check, and the kind of route it was launched
on) and the handoff row of the launched job, in custody. Selectable: the rows of the receiving checks. No text is
returned and nothing describes the handoff: the rows are the handoff."""
from episode_runtime.job_access import STATES
from method_loop import ChoiceField, Field, RecordForm

JOB_STATES = ('not_launched', 'not_checked', *STATES)
ROUTE_KINDS = ('none', 'local', 'pbs', 'api')

FINDING_FORM = RecordForm({
    'job_state': ChoiceField('text', 'The state of the launched job at its latest receiving check', JOB_STATES),
    'route_kind': ChoiceField('text', 'The kind of route the launched job is on, as its handoff row records it',
                              ROUTE_KINDS),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The state of the launched job and the kind of its resource', form=FINDING_FORM),
    'handoff_refs': Field('record_refs', 'The handoff row of the launched job'),
    'check_refs': Field('record_refs', 'The rows of the receiving checks of that job', required=False),
})


def final_to_parent(summary, completion, selection):
    jobs = summary['jobs']
    result = {'credit': completion['credit'],
              'finding': {'job_state': jobs[-1]['state'] if jobs else 'not_launched',
                          'route_kind': jobs[-1]['route_kind'] if jobs else 'none'},
              'handoff_refs': [job['handoff_ref'] for job in jobs]}
    if 'check_refs' in selection:
        result['check_refs'] = [ref for job in jobs for ref in job['check_refs']]
    return result
