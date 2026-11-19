"""Where the episode stands, as a pure function of the view (old ``HPCSummary.decision_context``, ``decision_state``
and ``decision_inputs``): what the commissioner gave, the ledger's decision state as the latest tool unit returned it
(every tool outcome carries it), the launches, monitors and acquisitions commissioned so far, and the controller's
yield table.

The ledger itself is read by the tools (``task.py``): this function has no services. The old
``hpc_launch_deliveries`` (rows of ``runtime_report_attempts``), ``hpc_activity_decision`` (the last controller step
of ``runtime_observations``) and the two JSON-schema report forms (``hpc_report_form``, ``hpc_launch_report_form``)
are old-runner machinery and are not carried."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table


def internal_summary(view):
    parent = view.parent_input
    state, launches, monitors, acquisitions, staged = None, [], [], [], {}
    for unit in view.outcomes:
        if unit['kind'] == 'tool':
            outcome = unit['outcome']
            state = outcome['state']
            if unit['tool'] == 'hpc_plan' and outcome['status'] == 'completed':
                staged[outcome['result']['plan_ref']] = outcome['result'].get('supplied_input_file')
            continue
        entry = {'plan_ref': unit['arguments'].get('plan_ref'), **unit['report']}
        {'launch': launches, 'monitor': monitors, 'results': acquisitions}[unit['slot']].append(entry)
    controller = view.controller_state
    plans = {} if state is None else {row['plan_ref']: row for row in state['hpc_plans']}
    return {'episode': {'owner_episode_id': parent['owner_episode_id'], 'scope': parent['scope'],
                        'commission': parent['commission']},
            'handoff_unit': parent['handoff_unit'], 'acquired_record_unit': parent['acquired_record_unit'],
            'information_unit': parent['information_unit'],
            'state': state, 'plans': plans, 'staged_inputs': staged,
            'launches': launches, 'monitors': monitors, 'acquisitions': acquisitions,
            'controller': None if controller is None else yield_table(controller, forecast_unit='ledger credit'),
            'units_consumed': view.units_consumed}
