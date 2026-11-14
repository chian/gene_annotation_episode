"""Small storage/contract/model checks; no native algorithms, SSH or PBS jobs."""
import hashlib
import time
from types import SimpleNamespace

import pytest

from gene_annotation_episode.execution_memory import ExecutionMemory, ForgettingPolicy
from gene_annotation_episode.execution_guidance import compare_routes, recipe
from gene_annotation_episode.hpc_episodes import HPCEpisodes
from gene_annotation_episode import hpc_prediction as prediction
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.episode_bindings import BindingContext
from hpc_helpers import commission, resources, recorded_queue


def profile(**changes):
    return {**dict(resource_id='aurora:BioReason-Aurora-Test', backend='hpc', tool='blastp',
        implementation='blast-2.17.0:sha256:verified-build', parameters='options-and-db-version',
        hardware='aurora-cpu'), **changes}


def measured(now, **changes):
    return {**{'observed_at': now, 'features': {'size': 10, 'nodes': 1},
        'metrics': {'work': {'seconds': 100, 'censored': False},
                    'queue': {'seconds': 30, 'censored': False}},
        'success': True, 'provenance': ['mathematical-storage-test-receipt']}, **changes}


def context():
    return BindingContext('memory-test', 'owner', 'hpc', (('hpc', 'owner'),),
        {'subject_refs': []}, {'commission_id': 'work'}, {})


def test_freshness_does_not_refresh_on_read_and_future_data_is_unknown(tmp_path):
    memory = ExecutionMemory(tmp_path/'memory.sqlite3', policy={'queue_seconds': 20})
    ref = memory.observe('aurora', 'queue', {'count': 3}, observed_at=100, provenance=['qstat-receipt'])
    assert memory.latest('aurora', 'queue', now=99)['state'] == 'unknown'
    fresh = memory.latest('aurora', 'queue', now=110)
    assert fresh['reference'] == ref and fresh['age_seconds'] == 10
    assert memory.latest('aurora', 'queue', now=121)['data'] is None
    assert memory.latest('aurora', 'queue', now=121)['state'] == 'stale'


def test_shared_attempts_are_idempotent_and_incompatible_work_does_not_pool(tmp_path):
    first, second = [ExecutionMemory(tmp_path/'memory.sqlite3') for _ in range(2)]
    first.record(attempt_id='physical-1', profile=profile(), observation=measured(100))
    second.record(attempt_id='physical-1', profile=profile(), observation=measured(100))
    assert len(second.history(profile(), now=110)) == 1
    for key in ('tool', 'implementation', 'parameters', 'hardware', 'resource_id'):
        assert second.history(profile(**{key: 'changed'}), now=110) == []
    assert len(second.history(profile(tool='hmmscan'), now=110, queue_only=True)) == 1
    with pytest.raises(ValueError, match='physical_attempt_measurement_conflict'):
        second.record(attempt_id='physical-1', profile=profile(), observation=measured(101))


def test_queue_forgets_faster_without_deleting_work_receipts(tmp_path):
    memory = ExecutionMemory(tmp_path/'memory.sqlite3', policy={
        'history_seconds': 1000, 'history_half_life_seconds': 100,
        'queue_history_seconds': 50, 'queue_half_life_seconds': 25})
    memory.record(attempt_id='old', profile=profile(), observation=measured(100))
    row, = memory.history(profile(), now=200)
    assert row['weight'] == .5
    assert row['metrics']['work']['weight'] == .5
    assert 'queue' not in row['metrics']
    assert memory.history(profile(), now=200, queue_only=True) == []
    assert memory.history(profile(), now=1101) == []
    # Forgetting changes forecast operands, not the underlying provenance.
    assert memory.history(profile(), now=100)[0]['provenance']


def test_failure_and_censored_measurements_remain_in_training(tmp_path):
    memory = ExecutionMemory(tmp_path/'memory.sqlite3')
    failed = measured(100, success=False, metrics={'work': {'seconds': 600, 'censored': True}})
    memory.record(attempt_id='failure', profile=profile(), observation=failed)
    row, = memory.history(profile(), now=110)
    assert row['success'] is False and row['metrics']['work']['censored'] is True


def test_aged_observation_has_less_influence_than_recent_observation():
    spec = commission()['model']
    row = measured(100)
    row.update(id='observation', features={'size': 1}, metrics={'work': {'seconds': 2000, 'censored': False}})
    recent = prediction.fit(spec, [row])
    old = prediction.fit(spec, [{**row, 'weight': .01}])
    before = prediction.predict(prediction.prior_model(spec), {'size': 1})
    def median(model):
        return prediction.quantile(prediction.predict(model, {'size': 1})['times']['work'])
    assert prediction.quantile(before['times']['work']) < median(old) < median(recent)
    assert old['successes'] == .01


def test_all_actual_catalog_entries_receive_recipes_without_remote_fabrication(tmp_path):
    actual = [{'name': name, 'resources': kind, 'description': 'Explicit test contract.',
        'instructions': 'Original supplied instructions.',
        'input_schema': {'type': 'object', 'properties': {}, 'additionalProperties': False}}
        for name, kind in [('result.blast.hsp', 'local'), ('public.ncbi.entrez', 'api'),
                            ('custom.new_algorithm', 'local')]]
    library = ScientificToolLibrary.freeze(tmp_path/'tools', catalog=actual, tool_info=True)
    for contract in actual:
        row, = library.resolve_tool_info([{key: contract[key] for key in ('name', 'resources')}])
        assert 'Original supplied instructions.' in row['instructions']
        assert 'Execution planning and shared memory' in row['instructions']
        assert 'waiting and polling earn no credit' in row['instructions']
    with pytest.raises(ValueError, match='scientific_tool_unknown'):
        library.resolve_tool_info([{'name': 'custom.new_algorithm', 'resources': 'hpc'}])
    assert 'A101 homology workloads' in recipe('result.blast.hsp', 'local')


def test_local_first_requires_real_capacity_and_sufficient_deadline():
    route = {'binding_available': True, 'capacity_state': 'fresh',
             'available': {'cpu_threads': 1, 'memory_bytes': 100, 'scratch_bytes': 100},
             'total_seconds_upper': 50, 'provenance': ['measured-prediction']}
    need = {'cpu_threads': 1, 'memory_bytes': 50}
    assert compare_routes(route, route, requirements=need)['preferred'] == 'local'
    busy = {**route, 'available': {**route['available'], 'memory_bytes': 10}}
    assert compare_routes(busy, route, requirements=need)['preferred'] == 'hpc'
    stale = {**route, 'capacity_state': 'stale'}
    assert compare_routes(stale, stale, requirements=need)['preferred'] is None
    assert compare_routes({**route, 'total_seconds_upper': 100000}, route,
                          requirements=need)['preferred'] == 'local'


def test_hpc_initialization_reuses_history_and_queue_without_remote_work(tmp_path):
    memory = ExecutionMemory(tmp_path/'memory.sqlite3')
    memory.record(attempt_id='retained', profile=profile(), observation=measured(time.time()-10))
    c = {**commission(), 'execution_profile': profile()}
    episodes = HPCEpisodes(None, store=None, run_id='memory-test', directory=tmp_path/'run',
        resources=resources(), commissions={'work': c}, shared_execution_memory=memory.as_record())
    episodes.initialize(context())
    ledger = episodes.state(context())
    assert 'shared:retained' in episodes._history(ledger)
    model = ledger.read(episodes._current_model(ledger))
    assert model['training_ids'] == ['shared:retained']
    snapshot = recorded_queue()
    snapshot['captured_at'] = time.time()
    value = {'snapshot': snapshot, 'acquisition': {'origin': 'retained-test-input'}}
    memory.observe(profile()['resource_id'], 'queue', value,
        observed_at=snapshot['captured_at'], provenance=['tests/fixtures/hpc'])
    assert episodes._observe_queue(ledger, resources()['aurora']) == value
    assert 'hpc.history.refresh' in {row['name'] for row in episodes.catalog(context())}


def test_factory_preserves_shared_memory_policy_across_reconstruction(tmp_path):
    memory = ExecutionMemory(tmp_path/'shared.sqlite3', policy={'queue_seconds': 75})
    factory = ExecutionServiceFactory(resources(), {}, 1, 1, 1,
        hpc_commissions={'work': commission()}, shared_execution_memory=memory.as_record())
    restored = ExecutionServiceFactory.from_record(factory.as_record())
    assert restored.as_record() == factory.as_record()


def test_invalid_policy_and_cross_resource_profile_fail_closed():
    with pytest.raises(ValueError, match='forgetting'):
        ForgettingPolicy(queue_seconds=0)
    from gene_annotation_episode.hpc_campaign import validate_commission
    with pytest.raises(ValueError, match='profile_resource_conflict'):
        validate_commission({**commission(), 'execution_profile': profile(resource_id='somewhere-else')}, resources())


def test_failed_attempt_without_a_duration_still_updates_failure_expectations(tmp_path):
    memory = ExecutionMemory(tmp_path/'memory.sqlite3')
    memory.record(attempt_id='lost-clock', profile=profile(),
                  observation=measured(100, success=False, metrics={}))
    row, = memory.history(profile(), now=110)
    assert row['success'] is False and row['metrics'] == {}
    assert memory.profiles(now=110)[0]['attempt_count'] == 1
    assert memory.profiles(now=110, tools=['hmmscan']) == []


def test_hpc_tool_request_resolves_real_contract_and_rejects_wrong_operands(tmp_path):
    catalog = [{'name': name, 'resources': 'local', 'description': 'Contract-only check.',
        'input_schema': {'type': 'object', 'properties': {'size': {'type': 'integer', 'minimum': 1}},
                         'required': ['size'], 'additionalProperties': False}}
        for name in ('sequence.align', 'result.blast.hsp')]
    library = ScientificToolLibrary.freeze(tmp_path/'tools', catalog=catalog, tool_info=True)
    scientific = SimpleNamespace(tool_library=library, _information_catalog=lambda scope: catalog)
    services = SimpleNamespace(workflow=SimpleNamespace(scientific_process_binding=scientific))
    episodes = HPCEpisodes(services, store=None, run_id='memory-test', directory=tmp_path/'run',
                           resources=resources(), commissions={'work': commission()})
    request = {'name': 'sequence.align', 'resources': 'local', 'arguments_json': '{"size": 7}',
               'result_reader': 'result.blast.hsp', 'objective': 'Validate the handoff contract.'}
    selected = {'commission_id': 'work', 'tool_request': request}
    assert episodes.prepare_assignment(context(), 'hpc', selected, {'subject_refs': []}, 'op') == selected
    expanded = episodes._tool_request(request, {'subject_refs': []})
    assert expanded['arguments'] == {'size': 7}
    assert expanded['tool_contract']['input_schema'] == catalog[0]['input_schema']
    with pytest.raises(ValueError):
        episodes._tool_request({**request, 'arguments_json': '{"size": -1}'}, {'subject_refs': []})
    with pytest.raises(ValueError, match='actual_result_reader'):
        episodes._tool_request({**request, 'result_reader': 'invented.reader'}, {'subject_refs': []})


def test_closed_receipt_import_is_read_only_and_repeated_export_is_one_sample(tmp_path):
    from gene_annotation_episode.hpc_campaign import build_plan
    from gene_annotation_episode.hpc_ledger import HPCLedger
    from gene_annotation_episode.hpc_history import import_ledger
    c = commission()
    ledger = HPCLedger(tmp_path/'retained', c)
    plan = build_plan(c, c['candidates'][0], resources()['aurora'], 'contract-test', 1)
    plan['original_prediction'] = prediction.predict(prediction.prior_model(c['model']), {'size': 10})
    ledger.put('plan', plan)
    ledger.put('handoff', {'plan_id': plan['plan_id'], 'job_id': 'mathematical-contract-case'})
    observation = measured(time.time()-10)
    ledger.put('measured', {**observation, 'plan_id': plan['plan_id']})
    ledger.put('closed', {'plan_id': plan['plan_id']})
    before = hashlib.sha256(ledger.path.read_bytes()).hexdigest()
    memory = ExecutionMemory(tmp_path/'memory.sqlite3')
    first = import_ledger(ledger.path, memory=memory, resources=resources())
    assert import_ledger(ledger.path, memory=memory, resources=resources()) == first
    assert hashlib.sha256(ledger.path.read_bytes()).hexdigest() == before
    assert len(memory.history(first[0]['profile'])) == 1


def test_existing_native_statistics_export_feeds_the_same_shared_memory(tmp_path, monkeypatch):
    from gene_annotation_episode.run_statistics import ExecutionClass, RunStatistic, RunHistory
    from gene_annotation_episode.execution_recording import NativeMeasurement, _export_measurement
    path = tmp_path/'native.sqlite3'
    history = RunHistory(path)
    history.close()
    memory = ExecutionMemory(tmp_path/'shared.sqlite3')
    monkeypatch.setenv('GENE_EPISODE_EXECUTION_MEMORY', str(memory.path))
    scope = ExecutionClass(phase='protein_homology_search', backend='local', resource_id='local-test',
        implementation_sha256='a'*64, parameters_sha256='b'*64, memory_bytes=100, scratch_bytes=100,
        cpu_threads=1, query_residues=10, reference_residues=1000, reference_records=10,
        reference_state='available')
    statistic = RunStatistic('c'*64, 'd'*64, '2026-11-04T00:00:00+00:00', 'succeeded', 'complete', 2., None)
    measurement = NativeMeasurement(scope, statistic, 'unavailable_before_submission')
    assert _export_measurement(path, measurement)['state'] == 'recorded'
    assert _export_measurement(path, measurement)['state'] == 'recorded'
    from datetime import datetime
    profiles = memory.profiles(now=datetime.fromisoformat(statistic.observed_at).timestamp()+1)
    assert profiles[0]['attempt_count'] == 1


def test_available_queue_history_does_not_mix_different_pbs_queues(tmp_path):
    memory = ExecutionMemory(tmp_path/'memory.sqlite3')
    memory.record(attempt_id='production-queue', profile=profile(),
                  observation={**measured(time.time()-10), 'queue': 'prod'})
    c = {**commission(), 'execution_profile': profile()}
    episodes = HPCEpisodes(None, store=None, run_id='memory-test', directory=tmp_path/'run',
        resources=resources(), commissions={'work': c}, shared_execution_memory=memory.as_record())
    row, = episodes._shared_history(episodes.state(context()))['observations']
    assert 'work' in row['metrics'] and 'queue' not in row['metrics']


@pytest.mark.parametrize('field', ['max_wall_seconds', 'max_node_hours', 'shutdown_margin_seconds'])
def test_hpc_has_no_run_cutoff_configuration(field):
    from gene_annotation_episode.hpc_campaign import validate_commission
    c = commission()
    c['limits'][field] = 3600
    with pytest.raises(ValueError, match='not_configuration'):
        validate_commission(c, resources())


@pytest.mark.parametrize('field', ['maximum_seconds', 'minimum_seconds', 'timeout', 'wall_seconds'])
def test_hpc_has_no_unit_cutoff_configuration(field):
    from gene_annotation_episode.hpc_campaign import validate_commission
    c = commission()
    c['candidates'][0]['units'][0][field] = 3600
    with pytest.raises(ValueError, match='not_configuration'):
        validate_commission(c, resources())


def test_prediction_costs_are_distinct_from_an_execution_deadline():
    from gene_annotation_episode.hpc_campaign import validate_commission
    c = commission()
    c['preferences']['deadline_seconds'] = 3600
    with pytest.raises(ValueError, match='not_configuration'):
        validate_commission(c, resources())
