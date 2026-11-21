"""Where the launch stands, as a pure function of the view: the parent input (the commission and what
``read_from_parent`` derived from it), the lookup of the configured resources, the commissions run (each resource
child's report with the resource it was commissioned on), the resources that handed off, and what each action
earned (the marginal credits the yield controller observed: the productivity signal shown to the model).

A resource has a usable handoff when its resource child returned handoff references; ``credit`` asks
``records.holds`` for each of them."""


def internal_summary(view):
    parent = view.parent_input
    capabilities, commissions = None, []
    for outcome in view.outcomes:
        if outcome['kind'] == 'tool':
            capabilities = outcome['outcome']
            continue
        report = outcome['report']
        commissions.append({'resource_id': outcome['arguments']['resource_id'], 'slot': report['slot'],
                            'handoff_refs': report['handoff_refs'], 'completed': report['completed'],
                            'child_credit': report['child_credit'], 'finding': report['finding']})
    handed_off = {}
    for commission in commissions:
        if commission['handoff_refs']:
            handed_off.setdefault(commission['resource_id'], []).extend(commission['handoff_refs'])
    already = set(parent['already_handed_off_resource_ids'])
    controller = view.controller_state           # None only in the view before any unit, which has no history
    return {
        **parent,
        'capabilities': capabilities,
        'commissions': commissions,
        'handed_off': {resource_id: sorted(set(refs)) for resource_id, refs in sorted(handed_off.items())},
        'new_handoff_resource_ids': sorted(set(handed_off) - already),
        'handoff_refs': sorted({ref for refs in handed_off.values() for ref in refs}),
        'completed': any(commission['completed'] for commission in commissions),
        'credit_by_action': [] if controller is None else list(controller.history),
        'units_consumed': view.units_consumed,
    }
