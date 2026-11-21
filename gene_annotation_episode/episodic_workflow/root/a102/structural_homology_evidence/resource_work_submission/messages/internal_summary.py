"""Where the episode stands, as a pure function of the view: the assignment, the launched jobs read from the job
ledger rows it holds (the handoff and check rows its resource children returned and the check rows of its own
receiving checks), whether a usable handoff is held (what ``credit.py`` counts), what each commission came to,
what each reading of a resource and each library lookup returned, and what each of its own actions came to. The
declared resources are read from the resource adapter service in ``decide``; a summary reads no service."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import job_rows

NOT_CHECKED = 'not_checked'
UNKNOWN = 'unknown'
LOOKUPS = ('knowledge_lookup', 'launch_instruction_lookup')


def _entry(unit):
    """What one of the Episode's own tool units came to: a resource tool's failure is the code it gave; a lookup
    has the status its library gave it."""
    outcome = unit['outcome']
    failed = unit['tool'] not in LOOKUPS and outcome['status'] != 'completed'
    return {'action': unit['tool'], 'status': outcome['status'],
            'failure': outcome['failure']['code'] if failed else None}


def internal_summary(view):
    parent = view.parent_input
    rows = job_rows(view.records)
    jobs = []
    for row in rows:
        if row['event'] != 'handoff':
            continue
        checks = sorted((item for item in rows if item['job'] == row['job'] and item['event'] == 'check'),
                        key=lambda item: item['at'])
        jobs.append({'handoff_ref': row['id'], 'job': row['job'], 'resource_id': row['detail']['resource_id'],
                     'route_kind': row['detail']['kind'], 'submitted_at': row['at'],
                     'state': checks[-1]['detail']['state'] if checks else NOT_CHECKED,
                     'result_available': bool(checks) and checks[-1]['detail']['result_available'],
                     'check_refs': [item['id'] for item in checks]})
    commissions, inspections, lookups, actions = [], {}, [], []
    for unit in view.outcomes:
        if unit['kind'] == 'child':
            commissions.append({'resource_id': unit['arguments']['resource_id'],
                                'kind': unit['arguments']['kind'], **unit['report']})
            actions.append({'action': 'launch_work', 'resource_id': unit['arguments']['resource_id'],
                            'status': 'completed', 'failure': None})
            continue
        outcome = unit['outcome']
        if unit['tool'] == 'inspect_resource':
            inspections[outcome['resource_id']] = {name: outcome[name] for name in ('availability', 'bound', 'facts')}
        elif unit['tool'] in LOOKUPS:
            lookups.append({'action': unit['tool'], **unit['arguments'], 'status': outcome['status'],
                            'result': outcome['result'], 'feedback': outcome['feedback']})
        actions.append(_entry(unit))
    return {**parent, 'jobs': jobs, 'handoff_held': bool(jobs),
            'usable_handoff_held': any(job['state'] not in (NOT_CHECKED, UNKNOWN) for job in jobs),
            'commissions': commissions, 'inspections': inspections, 'lookups': lookups, 'actions': actions}
