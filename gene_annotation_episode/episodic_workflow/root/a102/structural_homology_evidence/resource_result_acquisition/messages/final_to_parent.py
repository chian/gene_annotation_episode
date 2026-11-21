"""The return, chosen for the scientific parent's next decision: interpret the acquired files, or come back for
them later. Always returned: the credit (the system's), the finding (two values of fixed vocabularies: the state of
the job at the latest status reading the Episode holds, and what its latest fetch came to), the acquired result
files in the order of the requested names, and the closure row of the job (a parent that holds it no longer counts
the job as outstanding). Selectable: the status check rows this Episode wrote. No text the model wrote and no
description of the job is returned: the job's records are the references."""
from episode_runtime.job_access import STATES
from method_loop import ChoiceField, Field, RecordForm

JOB_STATES = ('not_checked', *STATES)
FETCH_OUTCOMES = ('not_requested', 'results_acquired', 'results_not_available', 'result_not_in_catalog',
                  'request_failed')

FINDING_FORM = RecordForm({
    'job_state': ChoiceField('text', 'The state of the job at the latest status reading this Episode holds',
                             JOB_STATES),
    'fetch_outcome': ChoiceField('text', 'What the latest fetch of this Episode came to', FETCH_OUTCOMES),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The state of the job and what the fetch came to', form=FINDING_FORM),
    'result_refs': Field('record_refs', 'The distinct acquired requested result files, in the order of the '
                                        'requested names'),
    'closure_refs': Field('record_refs', 'The closure row of the job, written by the fetch'),
    'check_refs': Field('record_refs', 'The status check rows this Episode wrote', required=False),
})


def fetch_outcome(actions):
    fetches = [item for item in actions if item['action'] == 'fetch_results']
    if not fetches:
        return 'not_requested'
    if fetches[-1]['status'] == 'completed':
        return 'results_acquired'
    return fetches[-1]['failure'] if fetches[-1]['failure'] in FETCH_OUTCOMES else 'request_failed'


def final_to_parent(summary, completion, selection):
    result = {'credit': completion['credit'],
              'finding': {'job_state': summary['job_state'], 'fetch_outcome': fetch_outcome(summary['actions'])},
              'result_refs': list(dict.fromkeys(item['ref'] for item in summary['acquired'])),
              'closure_refs': list(summary['closure_refs'])}
    if 'check_refs' in selection:
        result['check_refs'] = list(summary['check_refs'])
    return result
