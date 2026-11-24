"""Where the episode stands, as a pure function of the loop's view (carried from ``internal_summary.py``,
``decision_state.py``, ``decision_inputs.py`` and ``task_state.py``).

The parent input (owner, commission identity, scope, input records), the owner ledger as the latest tool outcome
showed it (``ledger_view``: credit view, commission, candidates, current model, plans, latest monitor, monitor
controllers, queue references), the actions taken so far (the old ``requested_action_history`` and
``completed_action_reports``), the launches commissioned with the handoffs they returned (the old
``hpc_launch_deliveries``), the sources of the original result bytes the result tool published, and the
controller's yield table. The old ``pending_work``, ``waiting_support``, ``hpc_activity_decision`` (it read the old
estimator's journaled diagnostics) and ``hpc_launch_report_form`` (the form the old model repaired a launch report
with) are not carried: a child completes inside the unit that commissioned it and the system admits its result."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

INJECTED = ('owner_episode_id', 'commission_identity', 'scope')


def internal_summary(view):
    ledger_view, actions, launches, monitors, acquisitions, result_refs = None, [], [], [], [], []
    for index, unit in enumerate(view.outcomes):
        if unit['kind'] == 'tool':
            outcome = unit['outcome']
            ledger_view = outcome['ledger_view']
            actions.append({'index': index, 'kind': 'tool', 'name': unit['tool'], 'status': outcome['status'],
                            'arguments': {name: value for name, value in unit['arguments'].items()
                                          if name not in INJECTED}})
            result_refs.extend(ref for ref in outcome['record_refs'] if ref not in result_refs)
            continue
        report = unit['report']
        actions.append({'index': index, 'kind': 'child', 'name': unit['slot'], 'status': 'completed',
                        'arguments': dict(unit['arguments'])})
        if unit['slot'] == 'launch':
            launches.append({'plan_ref': unit['arguments']['plan_ref'], 'handoff_refs': report['handoff_refs'],
                             'completed': report['completed']})
        elif unit['slot'] == 'monitor':
            monitors.append(report)
        else:
            acquisitions.append(report)
    state = view.controller_state
    return {**view.parent_input, 'units_consumed': view.units_consumed, 'ledger_view': ledger_view,
            'actions': actions, 'launches': launches, 'monitors': monitors, 'acquisitions': acquisitions,
            'result_refs': result_refs,
            'action_yields': None if state is None else yield_table(state, forecast_unit='credit')}
