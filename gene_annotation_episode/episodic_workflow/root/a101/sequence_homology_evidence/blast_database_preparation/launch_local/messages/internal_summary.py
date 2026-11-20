"""Where the launch stands, as a pure function of the view: the commission (the parent input), what each launch did
(handed off, or refused with its failure code) and the handoff references."""


def internal_summary(view):
    parent = view.parent_input
    launches = []
    for unit in view.outcomes:
        if unit['tool'] != 'launch_preparation_job':
            continue
        outcome = unit['outcome']
        if outcome['status'] == 'completed':
            launches.append({'status': 'handed_off', 'job': outcome['job'], 'handoff_ref': outcome['handoff_ref'],
                            'plan_ref': outcome['plan_ref']})
        else:
            launches.append({'status': 'failed', 'job': outcome['job'], 'failure_code': outcome['failure']['code']})
    return {'fields': parent['fields'], 'resource_id': parent['resource_id'], 'handoff_unit': parent['handoff_unit'],
            'launches': launches,
            'handoff_refs': [launch['handoff_ref'] for launch in launches if launch['status'] == 'handed_off'],
            'plan_refs': [launch['plan_ref'] for launch in launches if launch['status'] == 'handed_off']}
