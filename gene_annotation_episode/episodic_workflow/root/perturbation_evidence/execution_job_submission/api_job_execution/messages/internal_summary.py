"""Where the job stands, from the loop's view (carried from ``internal_summary.py``, ``decision_state.py``,
``task_state.py`` and ``execution_state.py``).

Own fields of the old decision context: ``execution_assignment`` (the parent input) and ``execution_progress`` (the
recorded facts: here the operations so far, the handoff and result references and the facts the service reported).
The credit is the credit the API service executor's credit view gave after the last unit that reported one; a wait,
a capabilities read, a lookup and a failed operation report none and keep it.
"""
INITIAL_CREDIT = 0.0


def internal_summary(view):
    summary = {**view.parent_input, 'steps': [], 'credit': INITIAL_CREDIT, 'handoff_refs': [], 'result_refs': [],
               'completed': False, 'facts': {}, 'report_update': view.parent_input['initial_report'],
               'last_status': None,
               'controller': None if view.controller_state is None else view.controller_state.as_record()}
    for unit in view.outcomes:
        outcome = unit['outcome']
        summary['steps'].append({'tool': unit['tool'], 'operation': outcome.get('operation'),
                                 'status': outcome['status'], 'event': outcome.get('event'),
                                 'feedback': outcome.get('feedback')})
        summary['last_status'] = outcome['status']
        if 'report_update' in unit['arguments']:
            summary['report_update'] = unit['arguments']['report_update']
        if outcome.get('credit') is not None:
            summary['credit'] = outcome['credit']
        for name in ('handoff_refs', 'result_refs'):
            summary[name] += [ref for ref in outcome.get(name, ()) if ref not in summary[name]]
        summary['completed'] = summary['completed'] or bool(outcome.get('completed'))
        summary['facts'].update(outcome.get('facts') or {})
    return summary
