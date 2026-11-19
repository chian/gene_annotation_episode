"""Where the episode stands, as a pure function of the loop's view (carried from ``internal_summary.py`` /
``HPCSummary.decision_context``, ``decision_state.py``, ``decision_inputs.py`` and ``task_state.py``).

The parent input (commission identity, scope, input records, the tool request), the owner ledger as the latest tool
outcome showed it (``ledger_view``: credit view, commission, candidates, current model, plans, latest monitor, monitor
controllers, queue references), the credit of that ledger as last known (``ledger_credit``: the latest tool's view, or
what the execution sister returned after it), the actions taken so far (the old ``requested_action_history`` and
``completed_action_reports``), the launches commissioned with the handoffs they returned (the old
``hpc_launch_deliveries``), the sources of the original result bytes the result tool published or the execution
sister returned, and the controller's yield table. ``ledger_stale`` says that the last unit was a commission of a
sister that writes the ledger, so ``decide`` reads the ledger again before it decides (the old ``decision_context``
read it live at every decision).

The old ``pending_work``, ``waiting_support``, ``hpc_activity_decision`` (it read the old estimator's journaled
diagnostics), ``hpc_launch_report_form`` and ``hpc_report_form`` (the forms the old model repaired a report with) are
not carried: a child completes inside the unit that commissioned it and the system admits its result."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

INJECTED = ('scope',)
LEDGER_SISTERS = ('hpc_prediction', 'hpc_execution')


def internal_summary(view):
    ledger_view, ledger_credit, stale = None, 0.0, False
    actions, launches, monitors, acquisitions, sisters, result_refs = [], [], [], [], [], []
    for index, unit in enumerate(view.outcomes):
        if unit['kind'] == 'tool':
            outcome = unit['outcome']
            ledger_view = outcome['ledger_view']
            ledger_credit = float(ledger_view['credit']['credit'])
            stale = False
            actions.append({'index': index, 'kind': 'tool', 'name': unit['tool'], 'status': outcome['status'],
                            'arguments': {name: value for name, value in unit['arguments'].items()
                                          if name not in INJECTED}})
            result_refs.extend(ref for ref in outcome['record_refs'] if ref not in result_refs)
            continue
        report = unit['report']
        actions.append({'index': index, 'kind': 'child', 'name': unit['slot'], 'status': 'completed',
                        'arguments': dict(unit['arguments'])})
        stale = unit['slot'] in LEDGER_SISTERS
        if unit['slot'] == 'launch':
            launches.append({'plan_ref': unit['arguments']['plan_ref'], 'handoff_refs': report['handoff_refs'],
                             'completed': report['completed']})
        elif unit['slot'] == 'monitor':
            monitors.append(report)
        elif unit['slot'] == 'results':
            acquisitions.append(report)
        else:
            sisters.append(report)
            result_refs.extend(ref for ref in report['hpc_result_refs'] if ref not in result_refs)
            if unit['slot'] == 'hpc_execution':
                ledger_credit = float(report['hpc_credit'])
    state = view.controller_state
    return {**view.parent_input, 'owner_episode_id': view.episode_ref.episode_id,
            'units_consumed': view.units_consumed, 'ledger_view': ledger_view, 'ledger_credit': ledger_credit,
            'ledger_stale': stale, 'actions': actions, 'launches': launches, 'monitors': monitors,
            'acquisitions': acquisitions, 'sisters': sisters, 'result_refs': result_refs,
            'action_yields': None if state is None else yield_table(state, forecast_unit='credit')}
