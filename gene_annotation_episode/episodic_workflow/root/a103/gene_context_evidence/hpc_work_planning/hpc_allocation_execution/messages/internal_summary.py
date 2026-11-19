"""Where the episode stands, as a pure function of the loop's view (carried from ``internal_summary.py``
(``HPCSummary.decision_context``), ``decision_state.py`` and ``from_child_execution_job_submission.py``
(``LaunchReceiptCustody.original_launch_handoff``)).

The parent input (the commission, the scope, the owner), the HPC ledger state the last tool unit left behind
(``hpc_state``: its credit view, candidates, plans, handoffs, comparisons, monitors, queue observations and
history; before any tool unit only the commission's candidates and the ledger credit the commission began with),
the launches this Episode commissioned with the handoff records their returns carried (the old ``hpc_launch_deliveries``,
and the recovery of the actual handoff across a report repair: custody and ``view.outcomes`` make it a plain
read), the progress observations the monitor children delivered (the old received progress), the retained result
records, and the controller's yield table. ``credit.py`` and ``final_to_parent`` read exactly these facts."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table


def initial_state(parent):
    commission = parent['commission']
    return {'credit_view': {'credit': parent['ledger_credit'], 'components': None, 'contributions': []},
            'model_ref': 'reference_model', 'model_support': None, 'candidates': list(commission['candidates']),
            'plans': {}, 'handoffs': {}, 'launch_inputs': {}, 'closed': [], 'tool_requests': [],
            'latest_comparison': [], 'latest_monitor': [], 'monitor_controllers': [], 'pending_collect': {},
            'queue_refs': [], 'shared_history_refs': [], 'available_training_ids': [], 'accepted_obligations': []}


def internal_summary(view):
    parent = view.parent_input
    hpc, loaded = initial_state(parent), False
    launches, results_children, progress_refs, snapshots = [], [], [], {}
    result_refs, result_artifact_refs, actions, last = [], [], [], None
    for unit in view.outcomes:
        if unit['kind'] == 'tool':
            body = unit['outcome']
            hpc, loaded = body['hpc_state'], True
            result_refs.extend(ref for ref in body.get('result_source_refs', []) if ref not in result_refs)
            result_artifact_refs.extend(ref for ref in body.get('result_artifact_refs', [])
                                        if ref not in result_artifact_refs)
            actions.append({'kind': 'tool', 'name': unit['tool'], 'status': body['status']})
            last = {'kind': 'tool', 'name': unit['tool'], 'status': body['status'], 'result': body['result'],
                    'feedback': body.get('feedback')}
            continue
        report = unit['report']
        if unit['slot'] == 'launch':
            launches.append({'plan_ref': unit['arguments']['plan_ref'], 'handoff_refs': report['handoff_refs'],
                             'completed': report['completed']})
        elif unit['slot'] == 'monitor':
            progress_refs.extend(ref for ref in report['progress_refs'] if ref not in progress_refs)
            snapshots.update(report['progress_snapshots'])
        else:
            results_children.append({'plan_ref': unit['arguments']['plan_ref'], 'result_refs': report['result_refs'],
                                     'completed': report['completed']})
        actions.append({'kind': 'child', 'name': unit['slot'], 'status': 'returned'})
        last = {'kind': 'child', 'name': unit['slot'], 'report': report}
    state = view.controller_state
    return {**parent, 'units_consumed': view.units_consumed, 'hpc': hpc, 'hpc_loaded': loaded,
            'launches': launches, 'results_children': results_children,
            'received_progress_refs': progress_refs, 'received_progress_snapshots': snapshots,
            'result_refs': result_refs, 'result_artifact_refs': result_artifact_refs, 'actions': actions,
            'last_outcome': last,
            'action_yields': None if state is None else yield_table(state, forecast_unit='credit')}
