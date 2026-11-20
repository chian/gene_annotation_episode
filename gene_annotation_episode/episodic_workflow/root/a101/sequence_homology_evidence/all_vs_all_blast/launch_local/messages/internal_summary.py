"""Where the launch stands, as a pure function of the view: the commission (the parent input), what each launch did (it
handed the job off, or the resource refused the request), and the handoff and job records. The records are read from
the outcomes of the units, which are the references of records the episode holds."""


def internal_summary(view):
    parent = view.parent_input
    launches = []
    for unit in view.outcomes:
        outcome = unit['outcome']
        if outcome['status'] == 'completed':
            launches.append({'status': 'handed_off', 'job': outcome['job'], 'handoff_ref': outcome['handoff_ref'],
                             'job_ref': outcome['job_ref']})
        else:
            launches.append({'status': 'failed', 'job': outcome['job'], 'failure_code': outcome['failure']['code']})
    handed_off = [launch for launch in launches if launch['status'] == 'handed_off']
    return {'assignment': parent, 'handoff_unit': parent['handoff_unit'], 'launches': launches,
            'handoff_refs': [launch['handoff_ref'] for launch in handed_off],
            'job_refs': [launch['job_ref'] for launch in handed_off]}
