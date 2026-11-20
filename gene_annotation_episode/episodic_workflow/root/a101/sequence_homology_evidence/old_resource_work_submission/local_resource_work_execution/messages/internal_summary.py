"""Where the episode stands, as a pure function of the loop's view (old ``internal_summary.py`` and
``decision_state.py``): the admitted assignment, every unit outcome, the latest feedback, the latest credit view
and resource facts the resource tools returned, the latest recorded interpretation and the controller state.

The role-specific fields of the old ``decision_context`` (``role``, ``assignment``, ``resource_capabilities``,
``resource_tool_estimates``) need the resource service, which a summary cannot read: ``decide`` adds them."""


def internal_summary(view):
    parent = view.parent_input
    summary = {
        'assignment': {name: value for name, value in parent.items() if name not in ('scope', 'initial_report')},
        'scope': parent['scope'],
        'outcome_log': [], 'last_outcome': None, 'feedback': None,
        'credit_view': None, 'facts': None, 'interpretation': parent['initial_report'],
        'reasoning_schema': view.records.reasoning_schema(),
        'controller': None if view.controller_state is None else view.controller_state.as_record(),
        'units_consumed': view.units_consumed,
    }
    for position, unit in enumerate(view.outcomes):
        outcome = unit['outcome']
        name = unit['arguments']['tool'] if unit['tool'] == 'resource_tool' else unit['tool']
        summary['outcome_log'].append({'position': position, 'tool': name, 'status': outcome['status'],
                                       'record_refs': outcome['record_refs'], 'feedback': outcome.get('feedback')})
        summary['last_outcome'] = outcome
        summary['feedback'] = None if outcome['status'] in ('completed', 'partial') else outcome.get('feedback')
        if outcome.get('credit_view') is not None:
            summary['credit_view'] = outcome['credit_view']
        if outcome.get('facts') is not None:
            summary['facts'] = outcome['facts']
        if unit['tool'] == 'report' and outcome['status'] == 'completed':
            summary['interpretation'] = outcome['interpretation']
    return summary
