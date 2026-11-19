"""Where the episode stands, as a pure function of the loop's view (carried from ``internal_summary.py``,
``decision_state.py``, ``decision_inputs.py``, ``task_state.py`` and ``waiting.py``).

The parent input (commission identity, tool request, scope, received and input records, launch instruction selection),
the ledger as the latest tool outcome showed it (``ledger_view``: credit view, commission, candidates, current model,
plans, latest monitor, monitor controllers, queue references, result sources), the actions taken so far (the old
``requested_action_history`` and ``completed_action_reports``), what each child commission returned (the old
``hpc_launch_deliveries`` for the launches, and the reports of the monitor, results, prediction and allocation
execution children), the result sources and their artifacts that this episode holds (the old ``hpc_result_refs``:
those of the ledger known to this context), and the controller's yield table.

``ledger_stale`` is true when the last unit commissioned a sister (prediction or allocation execution): it changed the
shared ledger, which this view has not read again; ``decide`` then reads it again. Until it has, the model identity, the
accepted obligations and the result sources are those the sister returned in its report.

Not carried: ``pending_work``, ``waiting_support``, ``hpc_activity_decision`` (the old continuation estimator's
journaled diagnostics: the wait-or-collect mode and the active next gain; the three controllers offer none) and
``hpc_launch_report_form`` and ``hpc_report_form`` (the forms the old model repaired a child's report with: a child
completes inside the unit that commissioned it, the system admits its result, and the parent writes no form)."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..task import INJECTED, LEDGER_SISTERS


def internal_summary(view):
    ledger_view, actions, stale, last_report = None, [], False, None
    launches, monitors, acquisitions, predictions, executions = [], [], [], [], []
    for index, unit in enumerate(view.outcomes):
        stale = False
        if unit['kind'] == 'tool':
            outcome = unit['outcome']
            ledger_view = outcome['ledger_view']
            actions.append({'index': index, 'kind': 'tool', 'name': unit['tool'], 'status': outcome['status'],
                            'arguments': {name: value for name, value in unit['arguments'].items()
                                          if name not in INJECTED}})
            continue
        report = unit['report']
        actions.append({'index': index, 'kind': 'child', 'name': unit['slot'], 'status': 'completed',
                        'arguments': dict(unit['arguments'])})
        if unit['slot'] == 'launch':
            launches.append({'plan_ref': unit['arguments']['plan_ref'], 'handoff_refs': report['handoff_refs'],
                             'completed': report['completed']})
        elif unit['slot'] == 'monitor':
            monitors.append(report)
        elif unit['slot'] == 'results':
            acquisitions.append({**report, 'handoff_ref': unit['arguments']['handoff_ref']})
        elif unit['slot'] == 'hpc_prediction':
            predictions.append(report)
        else:
            executions.append(report)
        if unit['slot'] in LEDGER_SISTERS:
            stale, last_report = True, report
    model_ref, model_refs, accepted, sources = None, None, None, []
    result_refs, result_artifact_refs = [], []
    if ledger_view is not None:
        model_ref, model_refs = ledger_view['model_ref'], list(ledger_view['model_refs'])
        accepted = [row['slot'].removeprefix('actual:') for row in ledger_view['credit']['contributions']
                    if row['kind'] == 'actual']
        sources = list(ledger_view['result_source_refs'])
        if stale:
            model_ref = last_report['model_ref']
            if model_ref not in model_refs:
                model_refs.append(model_ref)
            accepted = list(last_report['accepted_obligations'])
            sources.extend(last_report['result_refs'])
        result_refs = [ref for ref in dict.fromkeys(sources) if view.records.holds(ref)]
        for ref in result_refs:
            artifact = view.records.get(ref)['artifact_ref']
            if view.records.holds(artifact) and artifact not in result_artifact_refs:
                result_artifact_refs.append(artifact)
    state = view.controller_state
    return {**view.parent_input, 'units_consumed': view.units_consumed, 'ledger_view': ledger_view,
            'ledger_stale': stale, 'hpc_model_ref': model_ref, 'hpc_model_refs': model_refs,
            'hpc_accepted_obligations': accepted, 'actions': actions, 'launches': launches, 'monitors': monitors,
            'acquisitions': acquisitions, 'predictions': predictions, 'executions': executions,
            'result_refs': result_refs, 'result_artifact_refs': result_artifact_refs,
            'action_yields': None if state is None else yield_table(state, forecast_unit='credit')}
