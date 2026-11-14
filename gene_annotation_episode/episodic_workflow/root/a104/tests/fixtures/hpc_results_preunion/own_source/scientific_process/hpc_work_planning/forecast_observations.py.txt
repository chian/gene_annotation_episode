"""Private forecast observations for A104 hpc."""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a104.library.hpc_resource_prediction import forecast_metric
from gene_annotation_episode.episodic_workflow.root.a104 import hpc_queue
from gene_annotation_episode.episodic_workflow.root.a104.library.hpc_resource_prediction import pbs_resource_metrics
from gene_annotation_episode.episodic_workflow.root.a104.library import hpc_prediction as prediction
import time
from gene_annotation_episode.episodic_workflow.root.a104.hpc_campaign import timestamp




class ForecastObservations:
    def _freeze(self, ledger, plan, predicted, reference, current, phase, operation_key):
        elapsed = {'queue': current.get('queue_elapsed_seconds', 0.), 'work': current.get('work_elapsed_seconds', 0.)}
        slots = [slot['id'] for slot in ledger.commission['credit']['validation_slots']
            if slot['phase'] == phase and elapsed.get(slot['metric'], elapsed['work']) >= slot['minimum_elapsed_seconds']
            and forecast_metric(predicted, slot['metric']) is not None]
        body = ledger.once('issued:'+operation_key, 'forecast_issue', lambda: {
            'plan_id': plan['plan_id'], 'issued_at': time.time(), 'prediction': predicted,
            'reference': reference, 'phase': phase, 'elapsed': elapsed,
            'model_ref': plan.get('model_ref'),
            'prediction_episode_id': plan.get('prediction_episode_id')})
        return ledger.freeze(body, slots)

    @staticmethod
    def _last_forecast(ledger, plan):
        monitors = [row['body'] for row in ledger.records('monitor') if row['body']['plan_id'] == plan['plan_id']]
        if monitors:
            return monitors[-1]
        forecasts = [row for row in ledger.records('forecast') if row['body']['plan_id'] == plan['plan_id']]
        return {'conditional_prediction': plan['original_prediction'], 'forecast_ref': forecasts[0]['id']}

    def _measure(self, ledger, plan, observation, current, allocation):
        now = current['observed_at']
        metrics = pbs_resource_metrics(observation)
        if current['queued_at'] is not None:
            metrics['queue'] = {'seconds': current['queue_elapsed_seconds'],
                'censored': current['started_at'] is None, 'observed_at': current['started_at'] or now}
        receipt = observation['native'].get('exit_receipt')
        if receipt:
            metrics['work'] = {'seconds': receipt['duration_seconds'], 'censored': current['state'] == 'failed',
                               'observed_at': timestamp(receipt['finished_at'])}
        elif current['started_at'] is not None:
            metrics['work'] = {'seconds': current['work_elapsed_seconds'], 'censored': True, 'observed_at': now}
        if allocation and current['started_at'] is not None:
            metrics['setup'] = {'seconds': max(0., allocation['started_at']-current['started_at']),
                               'censored': False, 'observed_at': allocation['started_at']}
            if allocation.get('finished_at') is not None:
                metrics['work'] = {'seconds': allocation['finished_at']-allocation['started_at'],
                                  'censored': False, 'observed_at': allocation['finished_at']}
        measured = {'plan_id': plan['plan_id'], 'metrics': metrics, 'observed_at': now,
                    'success': False if current['state'] == 'failed' else None}
        reference = ledger.put('measured', measured)
        ledger.score(reference)
        return reference

    async def _update_conditional_forecast(self, context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration, plan, target, candidate, observation, allocation, allocation_window, observation_ref, current, measured_ref):
        refreshed = None
        queue_ref = plan['queue_ref']
        if arguments['refresh_queue']:
            queue_ref = 'queue:' + hpc_queue.digest(operation_key)
            queue_value = ledger.once(queue_ref, 'queue', lambda: self._observe_queue(ledger, configuration))
            queue = hpc_queue.features(queue_value['snapshot'], candidate, job_id=target['execution_id'])
            refreshed = prediction.predict(ledger.read(self._current_model(ledger)), self._features(candidate, queue))['times']['queue']
        predicted = prediction.update(plan['original_prediction'], current, refreshed_queue=refreshed)
        reference = prediction.update(plan['original_reference'], current)
        forecast_ref = self._freeze(ledger, plan, predicted, reference, current, current['state'], operation_key)
        orders = [row['body'] for row in ledger.records('allocation_order') if row['body']['plan_id'] == plan['plan_id']]
        ordered_candidate = deepcopy(candidate)
        if orders:
            units = {row['unit_id']: row for row in candidate['units']}
            first = [current['current_unit_id']] if current.get('current_unit_id') else []
            ids = list(dict.fromkeys([*first, *orders[-1]['unit_ids'], *units]))
            ordered_candidate['units'] = [units[identity] for identity in ids]
        result = {'plan_id': plan['plan_id'], 'observation_ref': observation_ref, 'measured_ref': measured_ref, 'forecast_ref': forecast_ref, 'queue_ref': queue_ref, 'conditional_prediction': predicted, 'remaining_work': prediction.compare(ordered_candidate, predicted, commission['obligations'], commission['preferences']), 'next_observation': 'Choose an event/elapsed threshold where changed evidence could alter a decision.'}
        ledger.put('monitor', result)
        outcome = {'status': 'completed', 'record_refs': references, 'changed_record_refs': references, 'result': result}
        return ledger.save_action(operation_key, selection, outcome)
