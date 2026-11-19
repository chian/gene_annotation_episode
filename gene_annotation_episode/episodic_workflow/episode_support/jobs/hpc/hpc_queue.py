"""PBS and ALCF activity observations reduced to dated prediction operands.

No rank is an asserted dispatch order. In particular, PBS Priority and ALCF's
computed score are different fields. Missing/stale status scores stay unknown.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shlex
import subprocess
import time
from urllib.request import urlopen


ACTIVITY_URL = 'https://status.alcf.anl.gov/aurora/activity.json'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) and not isinstance(value, bool) else None
    except (ValueError, TypeError):
        return None


def seconds(value):
    if not isinstance(value, str) or ':' not in value:
        return number(value)
    try:
        parts = [float(part) for part in value.split(':')]
        if len(parts) not in (3, 4) or any(part < 0 for part in parts):
            return None
        factors = (86400, 3600, 60, 1)[-len(parts):]
        return sum(a*b for a, b in zip(parts, factors))
    except ValueError:
        return None


def nodes(resources):
    count = number(resources.get('nodect'))
    if count is not None:
        return count
    chunks = str(resources.get('select', '')).split('+')
    if not chunks[0]:
        return None
    # A chunk without an explicit multiplicity means one node.
    return sum(int(chunk.split(':')[0]) if chunk.split(':')[0].isdigit() else 1
               for chunk in chunks)


def snapshot(jobs, queues, activity=None, *, captured_at=None, max_status_age=180):
    """Normalize real JSON; retain source hashes and asynchronous sample times."""
    if not isinstance(jobs.get('Jobs'), dict) or not isinstance(queues.get('Queue'), dict):
        raise ValueError('PBS JSON Jobs and Queue objects required')
    captured_at = time.time() if captured_at is None else captured_at
    activity = activity or {}
    status_time = number(activity.get('updated'))
    status_age = None if status_time is None else captured_at-status_time
    fresh = status_age is not None and -30 <= status_age <= max_status_age
    scores = {row['jobid']: row for row in activity.get('queued', [])
              if isinstance(row, dict) and isinstance(row.get('jobid'), str)} if fresh else {}
    rows = []
    for identity, job in jobs['Jobs'].items():
        resources = job.get('Resource_List') or {}
        used = job.get('resources_used') or {}
        rows.append({'job_id': identity, 'queue': job.get('queue'),
            'state': job.get('job_state'), 'nodes': nodes(resources),
            'wall_seconds': seconds(resources.get('walltime')),
            'used_wall_seconds': seconds(used.get('walltime')),
            'priority': number(job.get('Priority')),
            'scheduler_score': number(scores.get(identity, {}).get('score')),
            'base_score': number(resources.get('base_score', job.get('base_score'))),
            'project_priority': number(resources.get('project_priority', job.get('project_priority'))),
            'estimated_start': (job.get('estimated') or {}).get('start_time'),
            'comment': job.get('comment'),
            'queue_flags': {key: resources.get(key) for key in
                ('enable_fifo', 'enable_wfp', 'enable_backfill', 'overburn', 'score_boost')}})
    normalized_queues = {}
    for name, row in queues['Queue'].items():
        limits = {}
        for bound in ('min', 'max'):
            values = row.get('resources_'+bound, {})
            limits[bound+'_nodes'] = number(values.get('nodect'))
            limits[bound+'_wall_seconds'] = seconds(values.get('walltime'))
        normalized_queues[name] = {**limits,
            'enabled': str(row.get('enabled')).lower() == 'true',
            'started': str(row.get('started')).lower() == 'true',
            'type': row.get('queue_type'), 'route_destinations': row.get('route_destinations'),
            'assigned_nodes': number(row.get('resources_assigned', {}).get('nodect')),
            'max_run': row.get('max_run'), 'max_queued': row.get('max_queued'),
            'max_run_res': row.get('max_run_res'),
            'defaults': row.get('resources_default', {})}
    return {'version': 'hpc_queue_snapshot_v1', 'captured_at': captured_at,
        'jobs_sample_at': number(jobs.get('timestamp')), 'queues_sample_at': number(queues.get('timestamp')),
        'status_sample_at': status_time, 'status_age_seconds': status_age,
        'status_scores_usable': fresh, 'jobs': rows, 'queues': normalized_queues,
        'reservations': activity.get('reservation', []) if fresh else None,
        'maintenance': activity.get('motd_info') if fresh else None,
        'sources': {'qstat_jobs_sha256': digest(jobs), 'qstat_queues_sha256': digest(queues),
                    'activity_sha256': digest(activity), 'activity_url': ACTIVITY_URL}}


def features(observation, candidate, *, job_id=None, score=None, priority=None):
    """Same-queue comparables within a factor of two in nodes and walltime.

    Higher score/priority counts exclude held/waiting jobs. Ties and jobs with
    unknown scores are reported separately. Resource sums are pressure features,
    not waiting-time arithmetic. Routing queues need a concrete destination.
    """
    queue = candidate['queue']
    target = next((row for row in observation['jobs'] if row['job_id'] == job_id), None)
    if target:
        queue, score, priority = target['queue'], target['scheduler_score'], target['priority']
    others = [row for row in observation['jobs'] if row['queue'] == queue and row['job_id'] != job_id]
    queued = [row for row in others if row['state'] == 'Q']
    running = [row for row in others if row['state'] in ('R', 'E', 'B')]
    comparable = [row for row in queued if row['nodes'] is not None and row['wall_seconds'] is not None
        and .5 <= row['nodes']/candidate['nodes'] <= 2
        and .5 <= row['wall_seconds']/candidate['wall_seconds'] <= 2]
    ahead = [row for row in queued if score is not None and row['scheduler_score'] is not None
             and row['scheduler_score'] > score]
    comparable_ahead = [row for row in comparable if row in ahead]
    rules = observation['queues'].get(queue)
    reserved_now, reserved_soon, next_reservation = 0., 0., None
    for reservation in observation['reservations'] or []:
        start, duration, count = (number(reservation.get(key)) for key in ('start', 'duration', 'resv_nodect'))
        if start is None or duration is None or count is None:
            continue
        until = start-observation['captured_at']
        if -duration <= until <= 0:
            reserved_now += count
        elif until > 0:
            next_reservation = min(next_reservation, until) if next_reservation is not None else until
            if until <= candidate['wall_seconds']:
                reserved_soon += count
    cap = re.search(r'\[o:PBS_ALL=([0-9]+)\]', str((rules or {}).get('max_run_res', {}).get('nodect', '')))
    node_cap = int(cap[1]) if cap else None
    def ending_within(horizon):
        return sum(row['nodes'] for row in running if row['nodes'] is not None
            and row['wall_seconds'] is not None and row['used_wall_seconds'] is not None
            and 0 <= row['wall_seconds']-row['used_wall_seconds'] <= horizon)
    return {'queue': queue, 'job_id': job_id, 'scheduler_score': score, 'pbs_priority': priority,
        'queued_jobs': len(queued), 'comparable_jobs': len(comparable),
        'higher_score_jobs': len(ahead) if score is not None else None,
        'comparable_higher_score_jobs': len(comparable_ahead) if score is not None else None,
        'equal_score_jobs': sum(row['scheduler_score'] == score for row in queued) if score is not None else None,
        'unknown_score_jobs': sum(row['scheduler_score'] is None for row in queued),
        'higher_pbs_priority_jobs': sum(row['priority'] > priority for row in queued
            if row['priority'] is not None) if priority is not None else None,
        'higher_score_node_hours': sum(row['nodes']*row['wall_seconds']/3600 for row in ahead
            if row['nodes'] is not None and row['wall_seconds'] is not None) if score is not None else None,
        'queued_node_hours': sum(row['nodes']*row['wall_seconds']/3600 for row in queued
            if row['nodes'] is not None and row['wall_seconds'] is not None),
        'running_jobs': len(running),
        'running_nodes': sum(row['nodes'] for row in running if row['nodes'] is not None),
        'queue_assigned_nodes': (rules or {}).get('assigned_nodes'), 'queue_node_cap': node_cap,
        'running_nodes_requested_end_within_15min': ending_within(900),
        'running_nodes_requested_end_within_hour': ending_within(3600),
        'active_reserved_nodes': reserved_now if observation['reservations'] is not None else None,
        'reserved_nodes_starting_within_walltime': reserved_soon if observation['reservations'] is not None else None,
        'next_reservation_in_seconds': next_reservation,
        'held_or_waiting_jobs': sum(row['state'] in ('H', 'W', 'S') for row in others),
        'estimated_start': target['estimated_start'] if target else None,
        'queue_rules': rules, 'reservations': observation['reservations'],
        'sample_at': observation['captured_at'], 'source_hash': digest(observation),
        'interpretation': 'relative pressure, not dispatch rank; backfill, eligibility and reservations matter'}


def observe(configuration):
    """One read-only acquisition, using the caller's reuse-only SSH transport.

    Sequential queries; no subprocess, HTTP or authentication retries. Keep
    normalized selected fields and source hashes, excluding unrelated users'
    environment variables and avoiding a multi-megabyte prompt per query.
    """
    raw = {}
    for name, argv in (('jobs', ['qstat', '-f', '-F', 'json']),
                       ('queues', ['qstat', '-Qf', '-F', 'json'])):
        result = subprocess.run([*configuration['ssh_argv'], shlex.join(argv)],
            capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError('queue_observation_failed:'+name+':'+str(result.returncode))
        raw[name] = json.loads(result.stdout)
    try:
        with urlopen(ACTIVITY_URL, timeout=20) as response:
            payload = response.read(8*1024*1024+1)
            if len(payload) > 8*1024*1024:
                raise ValueError('activity_response_too_large')
            raw['activity'] = json.loads(payload)
    except (OSError, ValueError) as error:
        raw['activity'] = {}
        raw['activity_failure'] = type(error).__name__
    return {'snapshot': snapshot(raw['jobs'], raw['queues'], raw['activity']),
            'acquisition': {'jobs_command': ['qstat', '-f', '-F', 'json'],
                'queues_command': ['qstat', '-Qf', '-F', 'json'],
                'activity_url': ACTIVITY_URL, 'activity_failure': raw.get('activity_failure')}}
