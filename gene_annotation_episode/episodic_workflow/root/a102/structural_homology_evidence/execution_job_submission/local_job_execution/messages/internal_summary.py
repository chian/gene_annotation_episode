"""Where the launch stands, as a pure function of the view: the assignment and the credit a handoff earns (the
parent input), what each action did (a launch handed the job off or its request failed; a hold and its reason), the
handoff records, and what each action earned (the marginal credits the yield controller observed: the
productivity signal shown to the model)."""


def internal_summary(view):
    parent = view.parent_input
    launches, holds = [], []
    for unit in view.outcomes:
        outcome = unit['outcome']
        if unit['tool'] == 'hold_launch':
            holds.append(outcome['reason'])
        elif outcome['status'] == 'completed':
            launches.append({'status': 'handed_off', 'job': outcome['job'], 'submitted_at': outcome['submitted_at'],
                             'handoff_ref': outcome['handoff_ref']})
        else:
            launches.append({'status': 'failed', 'job': outcome['job'], 'failure_code': outcome['failure']['code']})
    controller = view.controller_state           # None only in the view before any unit, which has no history
    return {'assignment': parent['assignment'], 'handoff_credit': parent['handoff_credit'],
            'launches': launches, 'holds': holds,
            'handoff_refs': [launch['handoff_ref'] for launch in launches if launch['status'] == 'handed_off'],
            'credit_by_action': [] if controller is None else list(controller.history)}
