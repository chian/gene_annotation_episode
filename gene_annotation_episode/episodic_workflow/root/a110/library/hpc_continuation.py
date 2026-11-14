"""Shared HPC continuation estimate from authenticated evidence and unchanged credit history."""
from __future__ import annotations


class HPCContinuationEstimator:
    """Use frozen pending-value evidence; retain the actual raw credit history."""
    def __init__(self, verify, cost=0.):
        self.verify, self.cost = verify, cost

    def with_continuation_cost(self, cost):
        return type(self)(self.verify, cost)

    def __call__(self, history, parameters, contexts):
        from ..numerical import YieldEstimate, NumericBand, estimate_score_yield
        from ..completion_evidence import validate_completion_evidence
        if len(history) != len(contexts):
            raise ValueError('hpc_continuation_requires_aligned_contexts')
        supplied = contexts[-1].get('hpc_continuation') if contexts and contexts[-1] else None
        if supplied is None:
            return None
        packet = validate_completion_evidence(contexts[-1]['current_completion_evidence'])
        body = supplied['evidence']
        if (body['run_id'] != packet['run_id'] or body['episode_id'] != packet['episode_id']
                or body['operation_key'] != f"{packet['run_id']}:{packet['episode_id']}:{packet['original_decision_index']}"
                or packet['unit_ref']['unit_index'] != len(history)-1 or not self.verify(supplied)):
            raise ValueError('hpc_continuation_identity_conflict')
        from dataclasses import replace
        indices = body.get('active_history_indices', list(range(len(history))))
        if sorted(set(indices)) != indices or any(type(i) is not int or not 0 <= i < len(history) for i in indices):
            raise ValueError('active_yield_requires_original_completed_action_indices')
        active_estimate = estimate_score_yield([history[i] for i in indices], parameters,
            contexts=[contexts[i] for i in indices], evaluation_time=contexts[-1].get('progress_time'))
        active = active_estimate.expected_next_gain
        if body.get('active_credit_ceiling') == 0:
            active = NumericBand.exact(0.)
        pending = body['expected_continuation_credit']
        is_bound = body.get('valuation', {}).get('value_kind') == 'unresolved_acceptance_upper_bound'
        pending_point = 0. if is_bound else pending
        if active.status_code == 0:
            mode = ('active' if active.upper > self.cost else
                    body.get('pending_action', 'wait') if pending > self.cost else 'finish')
            selected = replace(active, value=max(active.value, pending_point),
                               lower=max(active.lower, pending_point), upper=max(active.upper, pending))
        else:
            mode, selected = 'active_yield_unknown', active
        # Pending value keeps the workflow alive, but is not attributed to
        # another active action. The decision gate parks exhausted active work.
        return YieldEstimate(len(history), selected, parameters,
            {'hpc_continuation': supplied, 'earned_wait_credit': 0.,
             'active_next_gain': active.as_record(), 'active_history_indices': indices,
             'active_time_fit': active_estimate.diagnostics,
             'pending_expected_credit': None if is_bound else pending,
             'pending_credit_upper_bound': pending if is_bound else None, 'activity_mode': mode,
             'pending_value_is_not_active_action_yield': True,
             'forecast_interpretation': ('unresolved_acceptance_upper_bound' if is_bound
                                         else 'conditional_model_expectation_not_certainty'),
             'raw_credit_history': 'unchanged'}, estimator_binding={
                 'version': 'hpc_pending_accomplishment_yield_v1',
                 'continuation': 'expected_pending_credit_less_incremental_cost',
                 'credit_receipts': 'actual_results_and_prospective_validation_only'})
    uses_template_when_unbound = True
