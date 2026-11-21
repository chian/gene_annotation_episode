"""Where the acquisition stands, as a pure function of the view: the handed-off job read from the job ledger rows
the Episode holds (the handoff row the parent passed, every check and closure row it holds), the requested result
files a held closure row names, and what each of the Episode's own actions came to. Nothing is read from a
service: the job ledger rows are the record of the job."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import job_rows

NOT_CHECKED = 'not_checked'


def _failure(outcome):
    return None if outcome['status'] == 'completed' else outcome['failure']['code']


def internal_summary(view):
    requested = view.parent_input['requested_names']
    rows = job_rows(view.records)
    handoff = next(row for row in rows if row['event'] == 'handoff')
    readings = sorted((row for row in rows if row['job'] == handoff['job'] and row['event'] in ('check', 'closure')),
                      key=lambda row: row['at'])
    closures = [row for row in readings if row['event'] == 'closure']
    files = {item['name']: item for row in closures for item in row['detail']['results']}
    own_checks = [unit['outcome']['check_ref'] for unit in view.outcomes
                  if unit['tool'] == 'check_job' and unit['outcome']['status'] == 'completed']
    return {'requested_names': requested,
            'job': {'handoff_ref': handoff['id'], 'job': handoff['job'],
                    'resource_id': handoff['detail']['resource_id'], 'kind': handoff['detail']['kind'],
                    'submitted_at': handoff['at']},
            'job_state': readings[-1]['detail']['state'] if readings else NOT_CHECKED,
            'result_available': any(row['event'] == 'closure' or row['detail']['result_available']
                                    for row in readings),
            'acquired': [{'name': name, 'ref': files[name]['ref']} for name in requested if name in files],
            'closure_refs': [row['id'] for row in closures], 'check_refs': own_checks,
            'actions': [{'action': unit['tool'], 'status': unit['outcome']['status'],
                         'failure': _failure(unit['outcome'])} for unit in view.outcomes]}
