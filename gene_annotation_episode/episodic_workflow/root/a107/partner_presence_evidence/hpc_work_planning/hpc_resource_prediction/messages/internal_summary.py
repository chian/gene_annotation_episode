"""Where the episode stands, carried from the old ``internal_summary.py`` (``PredictionSummary.decision_context``),
the view-derived part of ``decision_state.py`` and ``decision_inputs.py``: a pure function of the view.

The old summary read the parent-owned ledger directly. The ledger is outside the Store, so every tool of this
episode ends by returning the ledger's present view in its outcome (``outcome['ledger']``: commission, resource,
candidates, current model and its held-out quality, support, entry record, latest comparison, plans, monitors,
queue observations, shared history, available training ids, validation contribution, accepted obligations and
the result sources); the summary keeps the latest. Before the first unit (the ledger not yet opened) it is ``None``
and the task opens the ledger.

Names of the old decision context are kept: ``hpc_commission``, ``hpc_candidates``, ``hpc_resource``,
``hpc_tool_request``, ``hpc_model_ref``, ``hpc_credit``, ``hpc_latest_comparison``, ``hpc_model_support``,
``hpc_plans``, ``hpc_latest_monitor``, ``hpc_monitor_controllers``, ``hpc_queue_refs``, ``hpc_shared_memory``
(added by ``decide``, a recorded read of a service), ``hpc_shared_history_refs``, ``hpc_available_training_ids``.
Not carried: ``hpc_report_form`` (the typed report form of the old report-form machinery: the result is admitted
against ``RETURN_FORM``) and the old-runner parts of the decision inputs (completed action reports, pending work,
the decision protocol and contract-information profile)."""
from yield_control import YieldState

from ..credit import credit_view


def internal_summary(view):
    parent = view.parent_input
    ledger, last = None, None
    history = []
    for outcome in view.outcomes:
        last = outcome
        ledger = outcome['outcome']['ledger']
        history.append({'tool': outcome['tool'], 'arguments': outcome['arguments'],
                        'status': outcome['outcome']['status']})
    controller = view.controller_state.as_record() if isinstance(view.controller_state, YieldState) else None
    base = {**parent, 'ledger': ledger}
    credit = credit_view(base)
    summary = {**base,
               'hpc_credit': credit,
               'requested_action_history': history,
               'last_local_outcome': last,
               'controller': controller,
               'current_credit': credit['credit'],
               'hpc_commission': None, 'hpc_candidates': None, 'hpc_resource': None, 'hpc_tool_request': None,
               'hpc_model_ref': None, 'hpc_latest_comparison': None, 'hpc_model_support': None,
               'hpc_plans': None, 'hpc_latest_monitor': None, 'hpc_monitor_controllers': None,
               'hpc_queue_refs': None, 'hpc_shared_history_refs': None, 'hpc_available_training_ids': None,
               'hpc_model_refs': None, 'hpc_accepted_obligations': None, 'hpc_result_refs': None}
    if ledger is not None:
        summary.update({
            'hpc_commission': ledger['commission'], 'hpc_candidates': ledger['candidates'],
            'hpc_resource': ledger['resource'], 'hpc_tool_request': ledger['tool_requests'],
            'hpc_model_ref': ledger['current_model_ref'], 'hpc_latest_comparison': ledger['latest_comparison'],
            'hpc_model_support': ledger['model_support'], 'hpc_plans': ledger['plans'],
            'hpc_latest_monitor': ledger['latest_monitor'], 'hpc_monitor_controllers': ledger['monitor_controllers'],
            'hpc_queue_refs': ledger['queue_refs'], 'hpc_shared_history_refs': ledger['shared_history_refs'],
            'hpc_available_training_ids': ledger['available_training_ids'],
            'hpc_model_refs': ledger['model_refs'],
            'hpc_accepted_obligations': ledger['accepted_obligations'],
            # The result sources of the ledger this episode holds (old: those in its received references).
            'hpc_result_refs': [ref for ref in ledger['result_source_refs'] if view.records.holds(ref)]})
    return summary
