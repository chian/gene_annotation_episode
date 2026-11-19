"""A104 HPC prediction and resource-measurement calculations, with test-written commissions; no job runs."""
from copy import deepcopy
import math

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.evolutionary_history_evidence import hpc_prediction as p
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.evolutionary_history_evidence import hpc_resource_prediction as r
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.evolutionary_history_evidence import hpc_monitoring as monitoring


def base_commission():
    # Deliberately unlaunchable command: these inputs test contracts and mathematics, never an HPC job.
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
                'effort': 1., 'argv': ['/not-an-executable-contract-fixture'], 'environment': {}}]}],
        'credit': {'model_scale': .01, 'validation_scale': .1, 'validation_slots': [
            {'id': 'original-queue', 'metric': 'queue', 'phase': 'planned', 'weight': 1., 'minimum_elapsed_seconds': 0},
            {'id': 'running-work', 'metric': 'work', 'phase': 'running', 'weight': 1., 'minimum_elapsed_seconds': 60}]},
        'preferences': {'elapsed_cost_per_second': .0001, 'node_hour_cost': .01}}


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



def test_measured_resources_improve_fixed_disjoint_quality():
    c = commission()
    original = deepcopy(c)
    model, prior = p.fit(c['model'], c['history'][:6]), p.prior_model(c['model'])
    assert p.quality(model, c['history'][6:]) > p.quality(prior, c['history'][6:])
    small, large = [p.predict(model, {'size': size}) for size in (2, 12)]
    for metric in ('cpu_seconds', 'memory_bytes'):
        assert p.quantile(small['resources'][metric]) < p.quantile(large['resources'][metric])
    assert large['support']['extrapolated_features'] == ['size']
    with pytest.raises(ValueError, match='training_validation_overlap'):
        p.quality(model, c['history'][:1])
    assert c == original



def test_conditional_survival_quantiles_preserve_censored_information():
    value = p.distribution(math.log1p(100), .5, elapsed=200)
    points = [p.quantile(value, probability) for probability in (.1, .5, .9)]
    assert 0 < points[0] < points[1] < points[2]
    for point, probability in zip(points, (.1, .5, .9)):
        assert p.probability_within(value, point) == pytest.approx(probability)
        assert math.exp(p.log_score(value, point, censored=True)) == pytest.approx(1-probability)
    c = commission()
    row = deepcopy(c['history'][0])
    row['metrics']['work']['censored'] = True
    model = p.fit(c['model'], [row])
    assert model['metrics']['work']['censored'] == 1
    assert model['metrics']['work']['observations'] == 1



def test_original_physical_attempt_cannot_train_under_two_record_ids():
    c = commission()
    original = deepcopy(c['history'][0])
    original['provenance'] = ['123.aurora-pbs-0001.example']
    with pytest.raises(ValueError, match='one_training_case_per_physical_attempt'):
        p.fit(c['model'], [original, {**original, 'id': 'another-record'}])



def test_accounting_units_and_missing_usage_do_not_become_allocation_capacity():
    observation = {'state': 'running', 'observed_at': '2026-11-04T17:53:00+00:00',
        'native': {'pbs_fields': {'Resource_List': {'ncpus': 208},
            'resources_used': {'cput': '00:00:24', 'mem': '123kb'}}}}
    measured = r.pbs_resource_metrics(observation)
    assert measured['cpu_seconds']['value'] == 24
    assert measured['memory_bytes']['value'] == 123*1024
    assert all(row['censored'] for row in measured.values())
    observation['state'] = 'completed'
    assert not r.pbs_resource_metrics(observation)['cpu_seconds']['censored']
    observation['native']['pbs_fields']['resources_used'] = {}
    assert r.pbs_resource_metrics(observation) == {}
    with pytest.raises(ValueError, match='resource_measurement_unit_conflict'):
        r.measured_value('memory_bytes', {'unit': 'cpu_seconds', 'value': 1})



def test_resource_forecast_changes_portfolio_value_without_execution_gate():
    c = commission()
    forecast = p.predict(p.fit(c['model'], c['history'][:6]), {'size': 4})
    small = deepcopy(c['candidates'][0])
    small['resource_capacity'] = {'cpu_threads': 2, 'memory_bytes': 1024**2}
    large = {**small, 'resource_capacity': {'cpu_threads': 16, 'memory_bytes': 8*1024**3}}
    a, b = [p.compare(candidate, forecast, c['obligations'], c['preferences']) for candidate in (small, large)]
    assert a['expected_actual_credit'] < b['expected_actual_credit']
    assert a['resource_estimates']['memory_fit_probability'] < b['resource_estimates']['memory_fit_probability']
    assert 'allowed' not in a and 'allowed' not in b
    unknown = p.compare(c['candidates'][0], forecast, c['obligations'], c['preferences'])
    assert unknown['resource_estimates']['memory_fit_probability'] is None



def test_conditioning_uses_original_forecast_without_repeated_precision():
    c = commission()
    initial = p.predict(p.prior_model(c['model']), {'size': 1})
    original = deepcopy(initial)
    observation = {'state': 'running', 'work_elapsed_seconds': 100., 'completed_fraction': .25,
        'peak_memory_bytes': 8*1024**3, 'cpu_seconds': 400.}
    updated = p.update(initial, observation)
    assert updated == p.update(initial, observation) and initial == original
    assert updated['resources']['memory_bytes']['elapsed'] == observation['peak_memory_bytes']
    assert updated['resources']['cpu_seconds']['elapsed'] == 400.



def test_shared_monitor_valuation_retains_possible_success_and_zero_wait_credit():
    c = commission()
    candidate = c['candidates'][0]
    candidate['wall_seconds'] = 600
    value = p.predict(p.prior_model(c['model']), {'size': 1})
    value = p.update(value, {'state': 'queued', 'observed_at': 100.,
        'queue_elapsed_seconds': 20., 'work_elapsed_seconds': 0.})
    value['times']['setup'] = p.distribution(math.log1p(30), 16.2773)
    value['times']['work'] = p.distribution(math.log1p(120), 16.2773)
    assert p.quantile(value['times']['setup']) > candidate['wall_seconds']
    compared = p.compare(candidate, value, c['obligations'], c['preferences'])
    upper = p.probability_within(value['times']['setup'], 600)*value['success_probability']
    assert 0 < compared['attainable_units'][0]['completion_probability'] < upper
    for now in (100., 5001.):
        selected = monitoring.choose_schedule(value, candidate, c, monitoring.DEFAULT_POLICY, now=now)
        assert selected['schedule'] and selected['expected_continuation_credit'] > 0
        assert selected['earned_wait_credit'] == 0
