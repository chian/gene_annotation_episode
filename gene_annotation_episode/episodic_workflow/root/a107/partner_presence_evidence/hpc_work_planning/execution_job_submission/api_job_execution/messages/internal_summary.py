"""Where the job stands, from the loop's view (carried from ``internal_summary.py``, ``task_state.py``,
``state.py`` and the old ``decision_context``).

Own fields of the old decision context: ``execution_assignment`` (the parent input) and ``execution_progress`` (the
recorded facts, here the operations so far and the handoff and result references they produced). The credit is the
credit the API service's credit view gave after the last unit that reported one; a wait, a capabilities read and a
failed operation report none and keep it. ``selected_execution_task`` is shown by ``decide`` from the parent input.
The old ``native_decision_snapshot`` read the old runner's journal and Store tables (``runtime_actions``,
``working_state``, ``local_outcome_preview``); the state it presented comes from the view here.
"""
INITIAL_CREDIT = 0.0


def internal_summary(view):
    summary = {**view.parent_input, 'steps': [], 'credit': INITIAL_CREDIT, 'handoff_refs': [], 'result_refs': [],
               'completed': False, 'report_update': view.parent_input['initial_report'], 'last_status': None,
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
    return summary
