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


def state(self, context):
    validate_schema(plain(context.assignment), self.assignment_schema(context.role))
    commission = self._commission(context.assignment, context.scope)
    owner = context.episode_id
    directory = self.directory/'hpc'/hpc_queue.digest([self.run_id, owner])
    ledger = HPCLedger(directory, commission)
    ledger.put('owner', {'run_id': self.run_id, 'episode_id': owner,
        'scope': plain(context.scope), **self.commission_identity(context.assignment)}, identity='owner')
    if 'tool_request' in context.assignment:
        ledger.once('tool_request', 'tool_request', lambda: self._tool_request(
            plain(context.assignment['tool_request']), plain(context.scope)))
    return ledger

def initialize(self, context):
    ledger = self.state(context)
    prior = prediction.prior_model(ledger.commission['model'])
    ledger.put('model', prior, identity='reference_model')
    if self.memory is not None:
        imported = ledger.once('shared_history_entry', 'shared_history', lambda: self._shared_history(ledger))
        if imported['observations'] and not ledger.records('model_choice'):
            model = prediction.fit(ledger.commission['model'], imported['observations'])
            reference = ledger.put('model', model)
            ledger.put('model_choice', {'model_ref': reference, 'origin': 'shared_history_entry'},
                       identity='shared_history_initial_model')

def _current_model(ledger):
    records = ledger.records('model_choice')
    return records[-1]['body']['model_ref'] if records else 'reference_model'

def _quality(ledger, model):
    if not set(model['training_ids']) <= {row['id'] for row in ledger.commission['history']}:
        return None
    selected = [row for row in ledger.commission['history'] if row['id'] in ledger.commission['validation_ids']]
    return prediction.quality(model, selected) if selected else None

def _history(ledger):
    rows = {row['id']: row for row in ledger.commission['history']}
    original_attempts = {physical_attempt_key(row) for row in rows.values()}-{None}
    for snapshot in ledger.records('shared_history')[-1:]:
        rows.update({row['id']: row for row in snapshot['body']['observations']
                     if physical_attempt_key(row) not in original_attempts})
    plans = {row['body']['plan_id']: row['body'] for row in ledger.records('plan')}
    closed = {row['body']['plan_id'] for row in ledger.records('closed')}
    # Keep one latest observation per actual allocation, not one training
    # example per poll. Failed unfinished work retains a censored duration.
    latest = {}
    for row in ledger.records('measured'):
        if row['body']['plan_id'] in closed:
            latest[row['body']['plan_id']] = row
    for plan_id, row in latest.items():
        body = row['body']
        rows['allocation:'+plan_id] = {'id': 'allocation:'+plan_id,
            'observed_at': body['observed_at'], 'features': plans[plan_id]['original_prediction']['features'],
            'metrics': body['metrics'], 'success': body['success'], 'provenance': [row['id']]}
    return rows

def _shared_history(self, ledger):
    from gene_annotation_episode.episodic_workflow.root.library.execution_resource_identity import resource_identity
    commission = ledger.commission
    profile = commission.get('execution_profile')
    resource = resource_identity(commission['resource_id'], self.resources[commission['resource_id']])
    # Queue timing is resource-wide. Work timing requires explicit matching
    # algorithm, parameters, software and hardware, never just 'Aurora'.
    query = profile or {'resource_id': resource, 'backend': 'hpc', 'tool': 'allocation',
        'implementation': 'unspecified', 'parameters': 'unspecified', 'hardware': resource}
    now = time.time()
    rows = {row['id']: row for row in self.memory.history(query, now=now, queue_only=True)}
    if profile:
        rows.update({row['id']: row for row in self.memory.history(profile, now=now)})
    queues = {candidate['queue'] for candidate in self._candidates(ledger)}
    model_features = {item['name'] for item in commission['model']['features']}
    filtered = []
    for row in rows.values():
        queue = row.get('queue')
        # Different PBS queues are not interchangeable. Pool only when
        # the portfolio has one matching queue, or the model explicitly
        # carries its categorical indicator.
        if 'queue' in row['metrics'] and not (queue and
                (queues == {queue} or 'queue:'+queue in model_features)):
            row['metrics'].pop('queue')
        if queue:
            row['features']['queue:'+queue] = 1.
        if row['metrics'] or row['success'] is not None:
            filtered.append(row)
    original = {row['id'] for row in commission['history']}
    original_attempts = {physical_attempt_key(row) for row in commission['history']}-{None}
    return {'captured_at': now, 'policy': self.memory.as_record()['policy'],
            'observations': [row for row in filtered if row['id'] not in original
                             and physical_attempt_key(row) not in original_attempts][:2000]}

def _observe_queue(self, ledger, configuration):
    from gene_annotation_episode.episodic_workflow.root.library.execution_resource_identity import resource_identity
    resource = resource_identity(ledger.commission['resource_id'], configuration)
    if self.memory:
        cached = self.memory.latest(resource, 'queue')
        if (cached['state'] == 'fresh' and cached['age_seconds'] <=
                ledger.commission['limits']['queue_max_age_seconds']):
            return cached['data']
    value = hpc_queue.observe(configuration)
    if self.memory:
        self.memory.observe(resource, 'queue', value,
            observed_at=value['snapshot']['captured_at'], provenance=value['acquisition'])
    return value

def export_closed(self, ledger, plan):
    """Reusable for retained completed runs; this performs no remote work."""
    if self.memory is None:
        return
    from gene_annotation_episode.episodic_workflow.root.library.hpc_history import closed_measurement
    if not any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('closed')):
        raise ValueError('only_closed_allocations_enter_shared_history')
    measured = ledger.once('export_measurement:'+plan['plan_id'], 'export_measurement', lambda:
        [row for row in ledger.records('measured') if row['body']['plan_id'] == plan['plan_id']][-1])
    handoff = [row['body'] for row in ledger.records('handoff') if row['body']['plan_id'] == plan['plan_id']][-1]
    self.memory.record(**closed_measurement(ledger.commission, plan, measured, handoff,
                                           resources=self.resources, ledger_path=ledger.path))

def _queue(self, ledger, reference, *, require_fresh=False):
    observation = ledger.read(reference)['snapshot']
    if require_fresh and time.time()-observation['captured_at'] > ledger.commission['limits']['queue_max_age_seconds']:
        raise ValueError('fresh_queue_observation_required_before_planning')
    return observation

def _candidates(ledger):
    return ledger.commission['candidates']+[row['body'] for row in ledger.records('candidate')]

def _features(candidate, queue):
    return {**candidate['features'], 'nodes': candidate['nodes'], 'wall_seconds': candidate['wall_seconds'],
        'queue:'+candidate['queue']: 1.,
        **{key: value for key, value in queue.items() if type(value) in (int, float) or value is None}}

def _comparisons(self, ledger, model_ref, queue_ref):
    model = ledger.read(model_ref)
    observed = self._queue(ledger, queue_ref)
    actual = [row['slot'].removeprefix('actual:') for row in ledger.credit_view()['contributions'] if row['kind'] == 'actual']
    results = []
    for candidate in self._candidates(ledger):
        queue = hpc_queue.features(observed, candidate)
        forecast = prediction.predict(model, self._features(candidate, queue))
        row = prediction.compare(candidate, forecast, ledger.commission['obligations'],
                                 ledger.commission['preferences'], already_credited=actual)
        row['queue_features'] = queue
        results.append(row)
    return sorted(results, key=lambda row: row['net_expected_value'], reverse=True)

