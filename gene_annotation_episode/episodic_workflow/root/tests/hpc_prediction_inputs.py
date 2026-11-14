"""Small mathematical contracts for HPC unit tests; no executable workload."""
from copy import deepcopy
import json
from pathlib import Path


FIXTURES = Path(__file__).parent/'fixtures'/'hpc_prediction'


def recorded_queue(queue_module):
    snapshot = queue_module.snapshot
    jobs, queues, activity = [json.loads((FIXTURES/('aurora_'+name+'.json')).read_text())
                              for name in ('jobs', 'queues', 'activity')]
    return snapshot(jobs, queues, activity, captured_at=activity['updated'])


def base_commission():
    # Deliberately unlaunchable command: these fixtures test contracts and
    # mathematics, never submit or pretend to execute an HPC job.
    model = {'features': [{'name': 'size', 'transform': 'log1p', 'scale': 1}],
        'priors': {name: {'median_seconds': 100, 'log_sigma': .5, 'coefficient_variance': .2}
                   for name in ('queue', 'setup', 'work', 'return')}, 'success_prior': [2, 1]}
    history = [{'id': 'measurement-'+str(i), 'observed_at': i, 'features': {'size': i},
                'metrics': {'work': {'seconds': 20*i, 'censored': False}}, 'success': True,
                'provenance': ['mathematical_test_case']} for i in range(1, 9)]
    return {'objective': 'Exercise the contract without running a job', 'resource_id': 'aurora',
        'model': model, 'history': history, 'validation_ids': ['measurement-7', 'measurement-8'],
        'obligations': {'original-work': {'credit': 10., 'acceptance': [
            {'field': ['quality'], 'operator': 'ge', 'value': .9}]}},
        'candidates': [{'id': 'one-portfolio', 'queue': 'debug', 'nodes': 1, 'wall_seconds': 3600,
            'features': {'size': 10}, 'units': [{'unit_id': 'unit-1', 'obligation_id': 'original-work',
                'effort': 1.,
                'argv': ['/not-an-executable-contract-fixture'], 'environment': {}}]}],
        'credit': {'model_scale': .01, 'validation_scale': .1, 'validation_slots': [
            {'id': 'original-queue', 'metric': 'queue', 'phase': 'planned', 'weight': 1., 'minimum_elapsed_seconds': 0},
            {'id': 'running-work', 'metric': 'work', 'phase': 'running', 'weight': 1., 'minimum_elapsed_seconds': 60}]},
        'preferences': {'elapsed_cost_per_second': .0001, 'node_hour_cost': .01},
        'limits': {'result_limit_bytes': 65536,
            'queue_max_age_seconds': 1e10}}


def resources():
    return json.loads((FIXTURES/'aurora_execution_resources.json').read_text())


def commission():
    c = base_commission()
    c['model']['resource_priors'] = {
        'cpu_seconds': {'median': 1000., 'unit': 'cpu_seconds', 'log_sigma': .4, 'coefficient_variance': 2.},
        'memory_bytes': {'median': 4*1024**3, 'unit': 'bytes', 'log_sigma': .4, 'coefficient_variance': 2.}}
    for row in c['history']:
        size = row['features']['size']
        row['metrics'].update(cpu_seconds={'value': 5*size, 'unit': 'cpu_seconds', 'censored': False},
            memory_bytes={'value': 32*1024**2*size, 'unit': 'bytes', 'censored': False})
    c['credit']['validation_slots'] += [
        {'id': name, 'metric': name, 'phase': 'planned', 'weight': 1., 'minimum_elapsed_seconds': 0.}
        for name in ('cpu_seconds', 'memory_bytes')]
    return c
