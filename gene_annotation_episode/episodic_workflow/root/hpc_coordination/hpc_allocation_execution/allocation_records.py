"""HPC parent and prediction specializations of the ordinary Episode loop.

Launch remains the existing launch -> launch_hpc iteration. Known monitoring
and result parsing are single tools of the HPC parent. This binding never calls
a model, polls in a loop, or decides to commission children itself.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import asyncio
import shlex
import subprocess
import time

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.communication import validate_form
from gene_annotation_episode.domain import validate_schema
from gene_annotation_episode.episodic_workflow.root.episode_bindings import reference_in_context
from gene_annotation_episode.execution_contracts import obj
from gene_annotation_episode.episodic_workflow.root.library.hpc_campaign import (YIELD_ROLES, accepts, bind_progress, build_plan,
    incorporate_progress, telemetry, timestamp, validate_commission)
from gene_annotation_episode.episodic_workflow.root.library.hpc_ledger import HPCLedger
from gene_annotation_episode.episodic_workflow.root.library import hpc_prediction as prediction
from gene_annotation_episode.episodic_workflow.root.library import hpc_queue
from gene_annotation_episode.episodic_workflow.root.library.hpc_resource_prediction import forecast_metric, pbs_resource_metrics, physical_attempt_key


TEXT = {'type': 'string', 'minLength': 1}
STRINGS = {'type': 'array', 'uniqueItems': True, 'items': TEXT}


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

def _candidate(self, ledger, plan):
    return next(row for row in self._candidates(ledger) if row['id'] == plan['candidate_id'])

def _last_forecast(ledger, plan):
    monitors = [row['body'] for row in ledger.records('monitor') if row['body']['plan_id'] == plan['plan_id']]
    if monitors:
        return monitors[-1]
    forecasts = [row for row in ledger.records('forecast') if row['body']['plan_id'] == plan['plan_id']]
    return {'conditional_prediction': plan['original_prediction'], 'forecast_ref': forecasts[0]['id']}

def _collected_unit_ids(ledger, plan):
    return {row['body']['unit']['unit_id'] for row in ledger.records('result')
        if row['body'].get('plan_id') == plan['plan_id']
        and isinstance(row['body'].get('unit'), dict)
        and isinstance(row['body']['unit'].get('unit_id'), str)}

def _uncollected_completed_unit_ids(self, ledger, plan, current):
    allowed = {unit['unit_id'] for unit in self._candidate(ledger, plan)['units']}
    observed = set(current.get('telemetry', {}).get('completed_unit_ids', ()))
    return (observed & allowed)-self._collected_unit_ids(ledger, plan)

def _target(self, context, ledger, plan):
    handoff = ledger.read('handoff:'+plan['plan_id'])
    if (handoff['handoff_ref'] not in self._known(context)
            or not reference_in_context(self.services, context, handoff['handoff_ref'], None)):
        raise ValueError('original_handoff_not_received_by_this_parent')
    target = self.targets.read_target(handoff['handoff_ref'], context.scope)
    if target['assignment'] != plan['practical_assignment']:
        raise ValueError('handoff_does_not_match_frozen_portfolio')
    return target

def _window(self, target, path, limit, operation_key):
    value = self.targets.read_file(target, path=path, offset=0, limit=limit+1, operation_key=operation_key)
    payload = base64.b64decode(value['bytes_base64'], validate=True)
    if len(payload) != value['size_bytes'] or len(payload) > limit:
        raise ValueError('compact_result_incomplete_or_too_large')
    return value, payload

def _allocation(self, target, plan, operation_key):
    path = plan['manifest']['workspace']+'/allocation-status.json'
    try:
        window, payload = self._window(target, path, 512*1024, operation_key)
    except (FileNotFoundError, ValueError) as error:
        # Absence before the runner starts is normal; other failures remain
        # visible and do not manufacture a progress estimate.
        return None, {'path': path, 'failure': str(error)}
    value = json.loads(payload)
    if (value['plan_id'] != plan['plan_id'] or value['job_id'] != target['execution_id']
            or value['manifest_sha256'] != plan['manifest_sha256']):
        raise ValueError('allocation_receipt_identity_conflict')
    expected = {unit['unit_id'] for unit in plan['manifest']['units']}
    if len({row['unit_id'] for row in value['units']}) != len(value['units']) or not {row['unit_id'] for row in value['units']} <= expected:
        raise ValueError('allocation_receipt_units_conflict')
    return value, window

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

def _publish(self, context, body):
    artifact = self.store.artifact(hpc_queue.canonical(body), 'application/json')
    return self.store.put('source', {'provider': 'episode.hpc_result',
        'accession': 'hpc_'+hpc_queue.digest([self.run_id, context.episode_id, body]),
        'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': 'hpc_result_v1', 'retrieved_at': datetime.fromtimestamp(
            body['unit']['finished_at'], timezone.utc).isoformat()},
        origin='tool')['id']

