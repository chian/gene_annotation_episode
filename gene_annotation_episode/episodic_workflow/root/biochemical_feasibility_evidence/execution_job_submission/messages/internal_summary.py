"""Where the launch stands, as a pure function of the view: the assignment and what the commissioner passed, the
lookup of the configured resources, the launches run (each launch child's report with the resource it was
commissioned on), the resources that have a usable handoff, and what each action earned (the marginal credits the
yield controller observed: the productivity signal shown to the model).

A resource has a usable handoff when a launch child commissioned on it reported its handoff established and
returned its handoff records."""


def internal_summary(view):
    parent = view.parent_input
    capabilities, launches, handoff_refs, handoff_resources = None, [], [], []
    for unit in view.outcomes:
        if unit['kind'] == 'tool':
            capabilities = unit['outcome']
            continue
        report = unit['report']
        resource_id = unit['arguments']['resource_id']
        launches.append({'slot': unit['slot'], 'resource_id': resource_id, **report})
        handoff_refs.extend(ref for ref in report['handoff_refs'] if ref not in handoff_refs)
        if report['completed'] and report['handoff_refs'] and resource_id not in handoff_resources:
            handoff_resources.append(resource_id)
    controller = view.controller_state           # None only in the view before any unit, which has no history
    return {'assignment': parent['assignment'], 'message': parent['message'], 'record_refs': parent['record_refs'],
            'handoff_unit': parent['handoff_unit'], 'acquired_record_unit': parent['acquired_record_unit'],
            'scientific_task': parent.get('scientific_task'),
            'received_handoff_resources': parent['received_handoff_resources'], 'permitted': parent['permitted'],
            'capabilities': capabilities, 'launches': launches, 'handoff_refs': handoff_refs,
            'handoff_resources': handoff_resources,
            'credit_by_action': [] if controller is None else list(controller.history),
            'units_consumed': view.units_consumed}
