"""Where the episode stands, as a function of the loop's view (carried from ``internal_summary.py``,
``decision_state.py``, ``decision_inputs.py``, ``task_state.py`` and ``waiting.py``).

The ledger is rows in custody, so the summary reads it where it stands: once ``hpc_open`` has returned the ledger
id, ``task.ledger_view`` is computed over ``view.records`` (the rows this Episode wrote, the rows it was passed and
the rows its sisters returned). A sister's work is therefore in the summary, and in the credit, of the unit that
commissioned it. Before the first unit the ledger is not open: ``ledger_view`` is ``None`` and the task opens it.

For the model (``task.decide`` shows these and nothing else): ``commission``, ``ledger_state`` (current model and
its support, the count of measured cases, candidates, queue and comparison records, the plans with whether each is
handed off and closed, the latest monitor, the monitor controllers, the accepted obligations), ``predictions`` and
``executions`` (what each sister commission returned: its credit and its counts), ``launches``, ``monitors`` and
``acquisitions`` (the job children), ``credit`` (the ledger's credit and its components), ``units_so_far`` and
``last_outcome``. For the commissions and the return: ``ledger_view`` in full, ``result_refs`` and
``result_artifact_refs`` (the result sources of the ledger this Episode holds, and their artifacts).

Not carried: the yield table of the controller and the progress clock in the request (old ``action_yields`` and
``time_accounting``: estimator internals, nothing the model decides on), ``pending_work``, ``waiting_support``,
``hpc_activity_decision``, ``hpc_launch_report_form`` and ``hpc_report_form``: a child completes inside the unit that
commissioned it, the system admits its result, and the parent writes no form."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc_ledger import HpcLedger

from ..task import INJECTED, ledger_view as view_of_ledger

UNIT_CREDITS = ('handoff_unit', 'information_unit', 'acquired_record_unit')


def internal_summary(view):
    ledger_id, entry_credit, units, last = None, None, [], None
    launches, monitors, acquisitions, predictions, executions = [], [], [], [], []
    for unit in view.outcomes:
        if unit['kind'] == 'tool':
            outcome = unit['outcome']
            if unit['tool'] == 'hpc_open':
                ledger_id, entry_credit = outcome['result']['ledger'], outcome['result']['credit_at_open']
            units.append({'action': unit['tool'], 'status': outcome['status'],
                          'arguments': {name: value for name, value in unit['arguments'].items()
                                        if name not in INJECTED}})
            last = {'action': unit['tool'], 'status': outcome['status'], 'result': outcome['result'],
                    'feedback': outcome['feedback']}
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
        elif unit['slot'] == 'results':
            acquisitions.append({**report, 'handoff_ref': unit['arguments']['handoff_ref']})
        elif unit['slot'] == 'hpc_prediction':
            predictions.append(report)
        else:
            executions.append(report)
    # The first unit opened the ledger: it is not one of the model's own units.
    summary = {**view.parent_input, 'ledger': ledger_id, 'ledger_view': None, 'entry_credit': entry_credit,
               'units_so_far': units[1:],
               'last_outcome': last if len(units) > 1 else None, 'launches': launches, 'monitors': monitors,
               'acquisitions': acquisitions, 'predictions': predictions, 'executions': executions,
               'result_refs': [], 'result_artifact_refs': [], 'commission': None, 'ledger_state': None,
               'credit': None}
    if ledger_id is not None:
        ledger = view_of_ledger(HpcLedger.existing(view.records, ledger_id))
        result_refs = [ref for ref in dict.fromkeys(ledger['result_source_refs']) if view.records.holds(ref)]
        artifacts = [view.records.get(ref)['artifact_ref'] for ref in result_refs]
        summary.update({
            'ledger_view': ledger, 'commission': ledger['commission'], 'result_refs': result_refs,
            'result_artifact_refs': [ref for ref in dict.fromkeys(artifacts) if view.records.holds(ref)],
            'credit': {'earned_by_this_episode': ledger['credit']['credit'] - entry_credit,
                       'ledger_credit': ledger['credit']['credit'],
                       'ledger_components': ledger['credit']['components']},
            'ledger_state': {
                'current_model_ref': ledger['model_ref'], 'current_model_support': ledger['model_support'],
                'measured_cases': ledger['measured_cases'], 'model_refs': ledger['model_refs'],
                'candidates': ledger['candidates'], 'queue_refs': ledger['queue_refs'],
                'comparison_refs': ledger['comparison_refs'], 'latest_comparison': ledger['latest_comparison'],
                'plans': [{name: plan[name] for name in ('plan_ref', 'candidate_id', 'handed_off', 'closed')}
                          for plan in ledger['plans']],
                'latest_monitor': ledger['latest_monitor'], 'monitor_controllers': ledger['monitor_controllers'],
                'accepted_obligations': [row['slot'].removeprefix('actual:')
                                         for row in ledger['credit']['contributions'] if row['kind'] == 'actual'],
                'shared_history_refs': ledger['shared_history_refs'], 'tool_requests': ledger['tool_requests']}})
    return summary
