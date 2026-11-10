"""Mathematical and custody tests; these never emulate SSH or submit work."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import math

import pytest

from gene_annotation_episode import hpc_prediction as prediction
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.execution_memory import ExecutionMemory
from gene_annotation_episode.hpc_episodes import HPCEpisodes
from gene_annotation_episode.hpc_ledger import HPCLedger
from gene_annotation_episode.hpc_resource_prediction import pbs_resource_metrics
from hpc_helpers import commission, resources, recorded_queue
from test_hpc_episode_design import context


def resource_commission():
    c = commission()
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


def test_resources_learn_from_measured_usage_and_size_changes():
    c = resource_commission()
    model = prediction.fit(c['model'], c['history'][:6])
    prior = prediction.prior_model(c['model'])
    assert prediction.quality(model, c['history'][6:]) > prediction.quality(prior, c['history'][6:])
    small = prediction.predict(model, {'size': 2})
    large = prediction.predict(model, {'size': 12})
    assert small['support']['metric_observations']['memory_bytes'] == 6
    for metric in ('cpu_seconds', 'memory_bytes'):
        assert prediction.quantile(small['resources'][metric]) < prediction.quantile(large['resources'][metric])
    assert large['support']['extrapolated_features'] == ['size']


def test_predictor_can_acquire_missing_operands_but_cannot_launch(tmp_path):
    binding = HPCEpisodes(None, store=None, run_id='test-run', directory=tmp_path,
                          resources=resources(), commissions={'commission': resource_commission()})
    binding.initialize(context())
    child = context('hpc_prediction')
    binding.initialize(child)
    tools = {entry['name'] for entry in binding.catalog(child)}
    assert {'hpc.discovery.run', 'hpc.queue.observe', 'hpc.candidate.propose'} <= tools
    assert not {'hpc.plan', 'hpc.handoff', 'hpc.results'} & tools
    invalid = asyncio.run(binding.execute(child, 'hpc.compare',
        {'model_ref': 'reference_model', 'queue_ref': 'resource:wrong-kind'}, 'invalid-queue'))
    assert invalid['status'] == 'invalid'
    assert 'hpc.queue.observe' in invalid['feedback']['recovery']


def test_retained_plan_projection_preserves_operands_and_excludes_child_audit_id():
    from gene_annotation_episode.hpc_prompt import plan_outcome_view
    original = {'status': 'completed', 'result': {'plan_id': 'original-plan',
        'model_ref': 'selected-model', 'original_prediction': {'resources': {'cpu_seconds': 'distribution'}},
        'practical_assignment': {'argv': ['original-executable']}, 'prediction_episode_id': 'private-child-id'}}
    saved = deepcopy(original)
    projected = plan_outcome_view(original)
    assert original == saved
    assert 'prediction_episode_id' not in projected['result']
    assert projected['result']['model_ref'] == 'selected-model'
    assert projected['result']['practical_assignment'] == original['result']['practical_assignment']
    unrelated = {'result': {'prediction_episode_id': 'not-a-plan'}}
    assert plan_outcome_view(unrelated) is unrelated


def test_predictor_resume_preserves_original_entry_after_training(tmp_path):
    c = resource_commission()
    binding = HPCEpisodes(None, store=None, run_id='test-run', directory=tmp_path,
                          resources=resources(), commissions={'commission': c})
    binding.initialize(context())
    child = context('hpc_prediction')
    binding.initialize(child)
    ledger = binding.state(child)
    entry = ledger.read('entry:'+child.episode_id)
    trained = asyncio.run(binding.execute(child, 'hpc.model.fit',
        {'training_ids': [row['id'] for row in c['history'][:6]]}, 'fit-before-resume'))['result']['model_ref']
    assert trained != entry['model_ref']
    binding.initialize(child)
    assert ledger.read('entry:'+child.episode_id) == entry
    assert binding._current_model(ledger) == trained


def test_resource_forecasts_change_portfolio_value_without_a_runtime_gate():
    c = resource_commission()
    forecast = prediction.predict(prediction.fit(c['model'], c['history'][:6]), {'size': 4})
    small = deepcopy(c['candidates'][0])
    small['resource_capacity'] = {'cpu_threads': 2, 'memory_bytes': 1024**2}
    large = {**small, 'resource_capacity': {'cpu_threads': 16, 'memory_bytes': 8*1024**3}}
    a, b = [prediction.compare(candidate, forecast, c['obligations'], c['preferences'])
            for candidate in (small, large)]
    assert a['expected_actual_credit'] < b['expected_actual_credit']
    assert a['resource_estimates']['memory_fit_probability'] < b['resource_estimates']['memory_fit_probability']
    assert b['resource_estimates']['average_busy_cores_ratio_of_medians'] > 0
    assert 'allowed' not in a and 'allowed' not in b
    unknown = prediction.compare(c['candidates'][0], forecast, c['obligations'], c['preferences'])
    assert unknown['resource_estimates']['memory_fit_probability'] is None


def test_monitor_conditions_resource_demand_once_from_original_forecast():
    c = resource_commission()
    initial = prediction.predict(prediction.prior_model(c['model']), {'size': 1})
    saved = deepcopy(initial)
    current = {'state': 'running', 'work_elapsed_seconds': 100., 'completed_fraction': .25,
               'peak_memory_bytes': 8*1024**3, 'cpu_seconds': 400.}
    updated = prediction.update(initial, current)
    assert updated == prediction.update(initial, current)
    assert initial == saved
    assert updated['resources']['memory_bytes']['elapsed'] == current['peak_memory_bytes']
    assert updated['resources']['cpu_seconds']['elapsed'] == 400.


@pytest.mark.parametrize('keys', [('plan_id', 'unit_id'), ('HPC_PLAN_ID', 'HPC_UNIT_ID')])
def test_progress_spelling_preserves_original_identity_and_raw_document(keys):
    from gene_annotation_episode.hpc_campaign import bind_progress
    progress = {keys[0]: 'original-plan', keys[1]: 'original-unit',
                'observed_at': 100., 'completed_fraction': .4}
    saved = deepcopy(progress)
    bound = bind_progress(progress, 'original-plan')
    assert bound['plan_id'] == 'original-plan' and bound['unit_id'] == 'original-unit'
    assert bound['completed_fraction'] == .4 and progress == saved
    with pytest.raises(ValueError, match='identity_conflict'):
        bind_progress(progress, 'different-plan')
    with pytest.raises(ValueError, match='conflicting_original_progress_identity'):
        bind_progress({**progress, 'plan_id': 'different-plan', 'HPC_PLAN_ID': 'original-plan'}, 'original-plan')
    with pytest.raises(ValueError, match='invalid_original_unit_progress'):
        bind_progress({**progress, 'completed_fraction': float('nan')}, 'original-plan')


def test_pbs_measurements_never_substitute_allocated_cores_for_usage():
    value = {'state': 'running', 'observed_at': '2026-11-04T17:53:00+00:00',
        'native': {'pbs_fields': {'Resource_List': {'ncpus': 208},
            'resources_used': {'cput': '00:00:24', 'mem': '123kb'}}}}
    measured = pbs_resource_metrics(value)
    assert measured['cpu_seconds']['value'] == 24
    assert measured['memory_bytes']['value'] == 123*1024
    assert all(row['censored'] for row in measured.values())
    value['state'] = 'completed'
    assert not pbs_resource_metrics(value)['cpu_seconds']['censored']
    value['native']['pbs_fields']['resources_used'] = {}
    assert pbs_resource_metrics(value) == {}


def test_prediction_and_execution_sisters_share_original_model_and_delayed_credit(tmp_path):
    c = resource_commission()
    binding = HPCEpisodes(None, store=None, run_id='test-run', directory=tmp_path,
                          resources=resources(), commissions={'commission': c})
    parent = context()
    binding.initialize(parent)
    def sister(role, identity):
        assignment = binding.prepare_assignment(parent, role,
            {'commission_id': 'commission', 'owner_episode_id': parent.episode_id}, parent.scope, 'commission:'+identity)
        child = BindingContext(parent.run_id, identity, role, (*parent.path, (role, identity)),
                               parent.scope, assignment, {})
        binding.initialize(child)
        return child
    predict = sister('hpc_prediction', 'predict')
    execute = sister('hpc_execution', 'execute')
    assert 'launch' in binding.child_roles(execute.role)
    assert 'launch' not in binding.child_roles(predict.role)
    ledger = binding.state(parent)
    fitted = asyncio.run(binding.execute(predict, 'hpc.model.fit',
        {'training_ids': [row['id'] for row in c['history'][:6]]}, 'fit'))['result']['model_ref']
    assert binding._current_model(binding.state(execute)) == fitted
    assert binding.resolve(parent, fitted, 'hpc_model')
    before = binding.credit_view(predict, None)
    assert before['credit'] > 0 and before['prospective_validation_credit'] == 0
    forecast = prediction.predict(ledger.read(fitted), {'size': 7})
    reference = prediction.predict(ledger.read('reference_model'), {'size': 7})
    ledger.freeze({'plan_id': 'original', 'issued_at': 10., 'prediction': forecast, 'reference': reference,
                   'elapsed': {}, 'prediction_episode_id': predict.episode_id, 'model_ref': fitted},
                  ['cpu_seconds', 'memory_bytes'])
    measured = deepcopy(c['history'][6]['metrics'])
    for row in measured.values():
        row['observed_at'] = 20.
    ref = ledger.put('measured', {'plan_id': 'original', 'metrics': measured})
    ledger.score(ref)
    after = binding.credit_view(predict, None)
    assert after['prospective_validation_credit'] > 0
    ledger.score(ref)
    assert binding.credit_view(predict, None) == after
    assert binding.credit_view(execute, None)['components']['actual'] == 0
    with pytest.raises(ValueError, match='original_hpc_parent'):
        binding.prepare_assignment(replace(parent, episode_id='unrelated'), 'hpc_execution',
            dict(execute.assignment), parent.scope, 'other')


def test_shared_resource_history_keeps_units_and_forgetting(tmp_path):
    memory = ExecutionMemory(tmp_path/'history.sqlite')
    profile = {'resource_id': 'aurora', 'backend': 'hpc', 'tool': 'example',
               'implementation': 'v1', 'parameters': 'v1', 'hardware': 'aurora'}
    row = resource_commission()['history'][0]
    memory.record(attempt_id='original', profile=profile, observation=row)
    received = memory.history(profile, now=row['observed_at']+60)[0]
    assert received['metrics']['memory_bytes']['unit'] == 'bytes'
    assert 0 < received['metrics']['memory_bytes']['weight'] < 1
    assert memory.history(profile, queue_only=True, now=row['observed_at']+60) == []


def test_same_physical_job_cannot_train_twice_under_different_record_ids():
    c = resource_commission()
    original = deepcopy(c['history'][0])
    original['provenance'] = ['123.aurora-pbs-0001.example']
    duplicate = {**original, 'id': 'shared-copy'}
    with pytest.raises(ValueError, match='one_training_case_per_physical_attempt'):
        prediction.fit(c['model'], [original, duplicate])


def test_prediction_returns_when_model_and_comparison_are_ready_without_a_counter_cap(tmp_path):
    import time
    c = resource_commission()
    c['validation_ids'] = []
    binding = HPCEpisodes(None, store=None, run_id='test-run', directory=tmp_path,
                          resources=resources(), commissions={'commission': c})
    parent = context()
    binding.initialize(parent)
    child = context('hpc_prediction')
    binding.initialize(child)
    ledger = binding.state(parent)
    first = c['history'][0]
    assert asyncio.run(binding.execute(child, 'hpc.read', {'reference': first['id']}, 'read'))['result'] == first
    assert binding.continuation_for_action(child, 'test-run:prediction:0') is None
    model = asyncio.run(binding.execute(child, 'hpc.model.fit',
        {'training_ids': [row['id'] for row in c['history']]}, 'fit'))['result']['model_ref']
    assert binding.continuation_for_action(child, 'test-run:prediction:1') is None
    queue = recorded_queue()
    queue['captured_at'] = time.time()
    queue_ref = ledger.put('queue', {'snapshot': queue})
    asyncio.run(binding.execute(child, 'hpc.compare', {'model_ref': model, 'queue_ref': queue_ref}, 'compare'))
    packet = binding.continuation_for_action(child, 'test-run:prediction:2')
    assert packet['evidence']['active_credit_ceiling'] == 0
    assert packet['evidence']['expected_continuation_credit'] == 0
    assert binding.credit_view(child, None)['credit'] == 0
    newer = deepcopy(first)
    newer['id'] = 'new-actual-measurement'
    ledger.put('shared_history', {'observations': [newer]})
    assert binding.continuation_for_action(child, 'test-run:prediction:3') is None
