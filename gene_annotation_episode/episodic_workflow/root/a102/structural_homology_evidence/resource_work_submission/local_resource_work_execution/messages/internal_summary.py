"""Where the launch stands, as a pure function of the view: the assigned work and resource, the jobs this Episode
launched, read from the job ledger rows it holds (each handoff row with the state its latest held check row saw),
whether a handoff and a usable receiving check are held (what ``credit.py`` counts), the description of the
resource once it was read, and what each of the Episode's own actions came to.

A receiving check is a check row a ``check_handoff`` unit wrote. The check row a ``wait`` unit writes shows the
state of the job (it is the latest reading) and is not a receiving check: a wait earns nothing."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import job_rows

NOT_CHECKED = 'not_checked'
UNKNOWN = 'unknown'


def _failure(outcome):
    return None if outcome['status'] == 'completed' else outcome['failure']['code']


def internal_summary(view):
    parent = view.parent_input
    rows = job_rows(view.records)
    receiving = [unit['outcome']['check_ref'] for unit in view.outcomes
                 if unit['tool'] == 'check_handoff' and unit['outcome']['status'] == 'completed']
    jobs = []
    for row in rows:
        if row['event'] != 'handoff':
            continue
        checks = sorted((item for item in rows if item['job'] == row['job'] and item['event'] == 'check'),
                        key=lambda item: item['at'])
        jobs.append({'handoff_ref': row['id'], 'job': row['job'], 'submitted_at': row['at'],
                     'state': checks[-1]['detail']['state'] if checks else NOT_CHECKED,
                     'result_available': bool(checks) and checks[-1]['detail']['result_available'],
                     'check_refs': [item['id'] for item in checks if item['id'] in receiving],
                     'usable_check': any(item['id'] in receiving and item['detail']['state'] != UNKNOWN
                                         for item in checks)})
    descriptions = [unit['outcome']['resource'] for unit in view.outcomes if unit['tool'] == 'inspect_resource']
    return {'resource_id': parent['resource_id'], 'work_ref': parent['work_ref'],
            'credit_units': parent['credit_units'], 'completion_target': parent['completion_target'],
            'jobs': jobs, 'handoff_held': bool(jobs),
            'usable_check_held': any(job['usable_check'] for job in jobs),
            'resource_description': descriptions[-1] if descriptions else None,
            'actions': [{'action': unit['tool'], 'status': unit['outcome']['status'],
                         'failure': _failure(unit['outcome'])} for unit in view.outcomes]}
