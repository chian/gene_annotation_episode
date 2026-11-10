"""Measured resource demand, separate from scheduler allocation requests.

CPU time and memory are PBS accounting measurements. They are not allocated
core counts, per-process peaks, GPU utilization or a claim of perfect sampling.
Missing measurements stay absent. Forecasts inform choices; they install no
runtime controls.
"""
from __future__ import annotations

import math
import re


RESOURCE_UNITS = {'cpu_seconds': 'cpu_seconds', 'memory_bytes': 'bytes'}


def physical_attempt_key(observation):
    """Recognize an original Aurora job across caller and shared-history IDs."""
    matches = {item for item in observation.get('provenance', []) if isinstance(item, str)
               and re.fullmatch(r'[0-9]+\.aurora-pbs-[A-Za-z0-9.-]+', item)}
    if len(matches) > 1:
        raise ValueError('one_physical_job_per_training_observation_required')
    return next(iter(matches)) if matches else None


def measured_value(metric, item):
    if metric in RESOURCE_UNITS:
        if item.get('unit') != RESOURCE_UNITS[metric]:
            raise ValueError('resource_measurement_unit_conflict:'+metric)
        value = item['value']
    else:
        value = item['seconds']
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('nonnegative_finite_measured_value_required')
    return value


def forecast_metric(forecast, metric):
    return forecast.get('resources' if metric in RESOURCE_UNITS else 'times', {}).get(metric)


def pbs_resource_metrics(observation):
    from .hpc_campaign import memory_bytes, timestamp
    from .hpc_queue import seconds
    native = observation['native']
    fields = native['pbs_fields']
    used = fields.get('resources_used', {})
    terminal = observation['state'] in ('completed', 'complete', 'failed')
    observed = timestamp(fields.get('obittime')) if terminal else None
    observed = observed or timestamp(observation['observed_at'])
    result = {}
    for metric, value, source in (
        ('cpu_seconds', seconds(used.get('cput')), 'pbs.resources_used.cput'),
        ('memory_bytes', memory_bytes(used.get('mem')), 'pbs.resources_used.mem')):
        if value is None:
            continue
        result[metric] = {'value': value, 'unit': RESOURCE_UNITS[metric],
            'censored': not terminal, 'observed_at': observed,
            'measurement_scope': 'pbs_job_accounting', 'source': source}
    return result


def resource_summary(forecast, candidate):
    from .hpc_prediction import probability_within, quantile
    distributions = forecast.get('resources', {})
    demand = {name: {'unit': RESOURCE_UNITS[name],
        **{'p'+str(int(q*100)): distribution['elapsed']+quantile(distribution, q)
           for q in (.1, .5, .9)}} for name, distribution in distributions.items()
        if distribution is not None}
    capacity = candidate.get('resource_capacity', {})
    memory = distributions.get('memory_bytes')
    memory_fit = (probability_within(memory, capacity['memory_bytes']-memory['elapsed'])
        if memory is not None and 'memory_bytes' in capacity else None)
    work = forecast['times']['work']
    cpu = demand.get('cpu_seconds')
    average_cores = (cpu['p50']/max(1e-12, work['elapsed']+quantile(work))
                     if cpu and work is not None else None)
    return {'requested_nodes': candidate['nodes'], 'declared_capacity': capacity,
        'worker_threads': candidate['features'].get('worker_threads', candidate['features'].get('chains')),
        'demand': demand, 'memory_fit_probability': memory_fit,
        'average_busy_cores_ratio_of_medians': average_cores,
        'interpretation': 'PBS accounting demand; CPU ratio is approximate, not peak concurrency. '
            'Missing demand/capacity is unknown. Allocation capacity is not measured utilization.'}
