"""Where the episode stands, as a pure function of the loop's view (carried from ``internal_summary.py``,
``decision_state.py``, ``decision_inputs.py`` and ``task_state.py``).

Every tool of this episode ends by returning what the HPC ledger of the commission shows (``ledger_view``,
``task.ledger_view``); the summary keeps the latest and arranges it for the next decision. Before the first unit
no tool has read the ledger: ``ledger_view`` is ``None`` and the task reads the commission from it.

For the model (``task.decide`` shows these and nothing else): ``commission`` (objective, obligations with credit and
acceptance, preferences, limits, credit scales), ``ledger_state`` (current model and its support, candidates, queue
and comparison records, the plans with whether each is handed off and closed, the latest monitor, the monitor
controllers, the accepted obligations), ``launches``, ``monitors`` and ``acquisitions`` (what the children returned),
``credit`` (the ledger's credit and its components), ``units_so_far`` and ``last_outcome`` (the last action's result
without the ledger view, which is shown once). For the commissions and the return: ``ledger_view`` in full,
``result_refs`` and ``result_artifact_refs`` (the result sources this episode published).

Not carried: the yield table of the controller and the progress clock in the request (old ``action_yields`` and
``time_accounting``: estimator internals, nothing the model decides on), ``pending_work``, ``waiting_support``,
``hpc_activity_decision`` and ``hpc_launch_report_form``: a child completes inside the unit that commissioned it and
the system admits its result."""

INJECTED = ('owner_episode_id', 'ledger', 'commission_identity', 'scope')
UNIT_CREDITS = ('handoff_unit', 'information_unit', 'acquired_record_unit')


def internal_summary(view):
    ledger_view, entry_credit, units, last, launches, monitors, acquisitions = None, None, [], None, [], [], []
    result_refs, result_artifact_refs = [], []
    for unit in view.outcomes:
        if unit['kind'] == 'tool':
            outcome = unit['outcome']
            ledger_view = outcome['ledger_view']
            entry_credit = ledger_view['credit']['credit'] if entry_credit is None else entry_credit
            units.append({'action': unit['tool'], 'status': outcome['status'],
                          'arguments': {name: value for name, value in unit['arguments'].items()
                                        if name not in INJECTED}})
            last = {'action': unit['tool'], 'status': outcome['status'], 'result': outcome['result'],
                    'feedback': outcome['feedback']}
            result_refs.extend(ref for ref in outcome['record_refs'] if ref not in result_refs)
            result_artifact_refs.extend(ref for ref in outcome['artifact_refs'] if ref not in result_artifact_refs)
            continue
        report = unit['report']
        units.append({'action': unit['slot'], 'status': 'completed',
                      'arguments': {name: value for name, value in unit['arguments'].items()
                                    if name not in UNIT_CREDITS}})
        last = {'action': unit['slot'], 'status': 'completed', 'result': report, 'feedback': None}
        if unit['slot'] == 'launch':
            launches.append({'plan_ref': unit['arguments']['plan_ref'], 'handoff_refs': report['handoff_refs'],
                             'completed': report['completed']})
        elif unit['slot'] == 'monitor':
            monitors.append(report)
        else:
            acquisitions.append(report)
    # The first unit read the commission: it is not one of the model's own units.
    summary = {**view.parent_input, 'ledger_view': ledger_view, 'entry_credit': entry_credit,
               'units_so_far': units[1:],
               'last_outcome': last if len(units) > 1 else None, 'launches': launches, 'monitors': monitors,
               'acquisitions': acquisitions, 'result_refs': result_refs,
               'result_artifact_refs': result_artifact_refs, 'commission': None, 'ledger_state': None,
               'credit': None}
    if ledger_view is not None:
        summary.update({
            'commission': ledger_view['commission'],
            'credit': {'earned_by_this_episode': ledger_view['credit']['credit'] - entry_credit,
                       'ledger_credit': ledger_view['credit']['credit'],
                       'ledger_components': ledger_view['credit']['components']},
            'ledger_state': {
                'current_model_ref': ledger_view['model_ref'], 'current_model_support': ledger_view['model_support'],
                'model_refs': ledger_view['model_refs'], 'candidates': ledger_view['candidates'],
                'queue_refs': ledger_view['queue_refs'], 'comparison_refs': ledger_view['comparison_refs'],
                'latest_comparison': ledger_view['latest_comparison'],
                'plans': [{name: plan[name] for name in ('plan_ref', 'candidate_id', 'handed_off', 'closed')}
                          for plan in ledger_view['plans']],
                'latest_monitor': ledger_view['latest_monitor'],
                'monitor_controllers': ledger_view['monitor_controllers'],
                'accepted_obligations': [row['slot'].removeprefix('actual:')
                                         for row in ledger_view['credit']['contributions']
                                         if row['kind'] == 'actual'],
                'shared_history_refs': ledger_view['shared_history_refs'],
                'tool_requests': ledger_view['tool_requests']}})
    return summary
