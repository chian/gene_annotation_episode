"""Persisted monitor schedules and the forecast value of retaining pending work.

The owning episode selects a scheduled monitor tool. Its one action waits and
then observes the original job. Scheduling does not create earned credit.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import math
import time

from . import hpc_prediction as prediction


DEFAULT_POLICY = {'min_interval_seconds': 60., 'max_interval_seconds': 1800.,
                  'monitor_cost': .001}


def validate_policy(policy):
    if set(policy) != set(DEFAULT_POLICY) or any(type(v) not in (int, float)
            or not math.isfinite(v) for v in policy.values()):
        raise ValueError('explicit_finite_monitor_policy_required')
    if not 0 < policy['min_interval_seconds'] <= policy['max_interval_seconds'] or policy['monitor_cost'] < 0:
        raise ValueError('invalid_monitor_interval_or_cost')
    return deepcopy(policy)


class MonitorCheckpoint(Exception):
    def __init__(self, schedule):
        self.schedule = schedule


def choose_schedule(forecast, candidate, commission, policy, *, credited=(), now):
    """Compare monitoring times using a conditional phase-completion forecast.

    Value after waiting is the remaining accomplishment's predicted credit,
    less additional time/node/monitor cost. Observation timing additionally
    weighs the probability of a phase change by that time. These are model
    expectations, not credit receipts or calibrated confidence statements.
    """
    validate_policy(policy)
    state = forecast.get('telemetry', {}).get('state', 'queued')
    remaining = sum(value['credit'] for key, value in commission['obligations'].items()
                    if key not in credited and any(unit['obligation_id'] == key for unit in candidate['units']))
    if remaining == 0 or state in ('complete', 'failed'):
        return {'state': state, 'schedule': False, 'reason': 'terminal_or_no_remaining_value',
                'remaining_credit_bound': remaining, 'expected_continuation_credit': 0.,
                'next_action': 'results' if state in ('complete', 'failed') else 'reconsider'}
    preferences = commission['preferences']
    compared = prediction.compare(candidate, forecast, commission['obligations'], preferences,
                                   already_credited=credited)
    value = compared['expected_actual_credit']
    metric = 'queue' if state == 'queued' else 'work'
    distribution = forecast['times'][metric]
    if distribution is None:
        raise ValueError('pending_monitor_requires_phase_forecast')
    maximum = policy['max_interval_seconds']
    minimum = min(maximum, policy['min_interval_seconds'])
    horizons = sorted({minimum, maximum, *[min(maximum, max(minimum, prediction.quantile(distribution, q)))
                                         for q in (.1, .25, .5, .75, .9)]})
    # Include time already passed since the last real observation without
    # inventing an observation that the job stayed in that phase meanwhile.
    age = max(0., now-forecast.get('telemetry', {}).get('observed_at', now))
    alternatives = []
    for seconds in horizons:
        probability = prediction.probability_within(distribution, age+seconds)
        cost = policy['monitor_cost']+preferences['elapsed_cost_per_second']*seconds
        if state == 'running':
            cost += preferences['node_hour_cost']*candidate['nodes']*seconds/3600
        alternatives.append({'delay_seconds': seconds, 'event_probability': probability,
            'expected_future_actual_credit': value, 'incremental_cost': cost,
            'expected_observation_value': probability*value-cost,
            'expected_continuation_credit': max(0., value-cost)})
    selected = max(alternatives, key=lambda row: (row['expected_observation_value'], -row['delay_seconds']))
    return {'state': state, 'schedule': selected['expected_continuation_credit'] > 0,
            'reason': 'conditional_pending_credit', 'metric': metric, **selected,
            'remaining_credit_bound': remaining, 'alternatives': alternatives,
            'method': 'conditional_phase_probability_and_remaining_accomplishment_value',
            'model_support': forecast['support'], 'earned_wait_credit': 0.}


class MonitorCronController:
    """One explicit monitor owner and immutable wake per original tool action."""
    def __init__(self, ledger):
        self.ledger = ledger

    def attach(self, plan, job_id, policy):
        reference = 'monitor-controller:'+plan['plan_id']
        issued = [row['body']['issued_at'] for row in self.ledger.records('forecast')
                  if row['body']['plan_id'] == plan['plan_id']]
        if not issued:
            raise ValueError('monitor_requires_original_forecast')
        self.ledger.put('monitor_controller', {'version': 'hpc_monitor_controller_v1',
            'plan_id': plan['plan_id'], 'job_id': job_id, 'policy': validate_policy(policy),
            'wake_action': 'hpc.monitor', 'scheduler_backend': 'systemd_calendar_v1'}, identity=reference)
        return reference

    def reserve(self, plan, candidate, monitor, operation_key, *, now=None):
        reference = 'monitor-schedule:'+operation_key
        def calculate():
            controller = self.ledger.read('monitor-controller:'+plan['plan_id'])
            plans = [row for row in self.ledger.records('plan') if row['body'] == plan]
            if len(plans) != 1:
                raise ValueError('monitor_requires_exact_original_plan')
            credited = [row['slot'].removeprefix('actual:') for row in self.ledger.credit_view()['contributions']
                        if row['kind'] == 'actual']
            issued = time.time() if now is None else now
            selection = choose_schedule(monitor['conditional_prediction'], candidate, self.ledger.commission,
                controller['policy'], credited=credited, now=issued)
            due = issued+selection.get('delay_seconds', 0.)
            return {'version': 'hpc_monitor_schedule_v1', 'schedule_ref': reference,
                'controller_ref': 'monitor-controller:'+plan['plan_id'], 'plan_id': plan['plan_id'],
                'job_id': controller['job_id'], 'operation_key': operation_key, 'plan_ref': plans[0]['id'],
                'forecast_ref': monitor['forecast_ref'], 'issued_at': issued, 'due_at': due,
                'reconsider_at': datetime.fromtimestamp(due, timezone.utc).isoformat(),
                'wake_action': {'tool': 'hpc.monitor',
                                'arguments': {'plan_ref': plans[0]['id'], 'refresh_queue': True}},
                'valuation': selection}
        return self.ledger.once(reference, 'monitor_schedule', calculate)

    async def wait(self, schedule):
        import asyncio
        from method_loop.suspension import external_wait
        if not schedule['valuation']['schedule']:
            return
        remaining = schedule['due_at']-time.time()
        if remaining > 0:
            await external_wait(asyncio.sleep(remaining), {'kind': 'scheduled_external_job',
                'job_id': schedule['job_id'], 'schedule_ref': schedule['schedule_ref'],
                'due_at': schedule['reconsider_at']})


class HPCContinuationEstimator:
    """Use frozen pending-value evidence; retain the actual raw credit history."""
    def __init__(self, verify, cost=0.):
        self.verify, self.cost = verify, cost

    def with_continuation_cost(self, cost):
        return type(self)(self.verify, cost)

    def __call__(self, history, parameters, contexts):
        from .numerical import YieldEstimate, NumericBand, estimate_score_yield
        from .completion_evidence import validate_completion_evidence
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
