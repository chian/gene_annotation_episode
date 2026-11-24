"""Where the episode stands, carried from the old ``internal_summary.py`` (``PredictionSummary.decision_context``),
the view-derived part of ``decision_state.py`` and ``decision_inputs.py``: a pure function of the view.

Every tool of this episode ends by returning what the HPC ledger of the commission shows (``outcome['ledger']``,
``task._ledger_view``); the summary keeps the latest and arranges it for the next decision. Before the first unit the
ledger is not open: ``ledger`` is ``None`` and the task opens it.

For the model (``task.decide`` shows these and nothing else): ``commission`` (objective, obligations and their
credit, cost preferences, credit scales, model features, the fixed validation ids), ``resource``, ``measured_cases``
(each with its role, training or validation), ``ledger_state`` (current model and its held-out quality, the quality
this episode started from, the model, queue and comparison records, candidates, plans, accepted obligations),
``hpc_credit``, ``units_so_far`` and ``last_outcome`` (the last tool's result without the ledger view, which is
shown once). For the return: ``ledger_refs`` (every row of the ledger this Episode holds, and the records they name)
and ``result_refs`` (the result sources of the ledger this Episode holds).

Not carried: the controller's state and the progress clock in the request (old ``controller``, ``current_credit``,
``time_accounting``: estimator internals, nothing the model decides on), the empty monitor fields (this episode
observes no job), ``hpc_report_form`` and the old-runner parts of the decision inputs (completed action reports,
pending work, the decision protocol and contract-information profile)."""
from ..credit import credit_view

ASSIGNED = ('ledger', 'scope')


def internal_summary(view):
    ledger, last, units = None, None, []
    for unit in view.outcomes:
        outcome = unit['outcome']
        ledger = outcome['ledger']
        last = {'tool': unit['tool'], 'status': outcome['status'], 'result': outcome['result'],
                'feedback': outcome.get('feedback')}
        units.append({'tool': unit['tool'], 'status': outcome['status'],
                      'arguments': {name: value for name, value in unit['arguments'].items()
                                    if name not in ASSIGNED}})
    base = {**view.parent_input, 'ledger': ledger}
    # The first unit opened the ledger: it is not one of the model's own units.
    summary = {**base, 'hpc_credit': credit_view(base), 'units_so_far': units[1:],
               'last_outcome': last if len(units) > 1 else None,
               'commission': None, 'resource': None, 'measured_cases': None, 'ledger_state': None,
               'ledger_refs': [], 'result_refs': []}
    if ledger is not None:
        summary.update({
            'commission': ledger['commission'], 'resource': ledger['resource'], 'measured_cases': ledger['cases'],
            'ledger_state': {
                'current_model_ref': ledger['current_model_ref'],
                'current_model_held_out_quality': ledger['current_quality'],
                'held_out_quality_at_start': ledger['model_entry']['quality'],
                'current_model_support': ledger['model_support'], 'model_refs': ledger['model_refs'],
                'queue_refs': ledger['queue_refs'], 'comparison_refs': ledger['comparison_refs'],
                'latest_comparison': ledger['latest_comparison'], 'candidates': ledger['candidates'],
                'plans': ledger['plans'], 'accepted_obligations': ledger['accepted_obligations'],
                'shared_history_refs': ledger['shared_history_refs'],
                'tool_requests': ledger['tool_requests']},
            'ledger_refs': ledger['ledger_refs'],
            # The result sources of the ledger this episode holds (old: those in its received references).
            'result_refs': [ref for ref in ledger['result_source_refs'] if view.records.holds(ref)]})
    return summary
