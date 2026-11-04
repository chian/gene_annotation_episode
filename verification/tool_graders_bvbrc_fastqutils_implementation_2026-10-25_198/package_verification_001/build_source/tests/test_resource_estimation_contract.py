"""Offline estimator contract; these fixtures do not establish episode behavior."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import validate_closed_schema, validate_form
from gene_annotation_episode.execution_expectations import ExecutionExpectations, capture_execution_scopes
from gene_annotation_episode.resource_estimation import ResourceToolEstimator, recorded_estimate, report_source
from gene_annotation_episode.run_statistics import ExecutionClass, RunHistory, RunStatistic


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


@pytest.fixture
def scope():
    return ExecutionClass(phase='protein_homology_search', backend='local', resource_id='fixture-host',
        implementation_sha256=digest('program'), parameters_sha256=digest('parameters-and-corpus'),
        memory_bytes=20*1024**3, scratch_bytes=4*1024**3, cpu_threads=1, query_residues=253,
        reference_residues=10000, reference_records=100, reference_state='available',
        duration_measure='systemd_service_wall_seconds')


def record(history, scope, name, seconds, *, outcome='succeeded', kind='complete', condition=None):
    history.record(scope, RunStatistic(attempt_sha256=digest(name), source_sha256=digest('receipt:'+name),
        observed_at='2026-10-20T10:00:00Z', outcome=outcome, duration_kind=kind,
        elapsed_seconds=seconds, condition_ref=condition))


def support(estimate):
    return {row['outcome']: row for row in estimate['outcome_support']}


def test_prospective_and_assigned_share_projection_without_creating_a_job(tmp_path, scope):
    path = tmp_path/'history.sqlite'
    history = RunHistory(path)
    record(history, scope, 'fast-success', 2)
    record(history, scope, 'slow-success', 6)
    history.close()
    context = capture_execution_scopes(path, [scope], assigned_execution_class_ref=scope.ref)
    original = deepcopy(context)
    estimator = ResourceToolEstimator()
    planning, = estimator.estimate_context(context)
    assigned, = estimator.estimate(context, job_ref='fixture_job')
    assert planning['job_ref'] is None and assigned['proposal_ref'] is None
    assert planning['proposal_ref'].startswith('execution_proposal_')
    assert planning['execution_class_ref'] == scope.ref
    assert planning['expectation_ref'] == context['snapshots'][0]['ref']
    assert planning['expected_total_seconds'] == 4
    assert (planning['observed_min_seconds'], planning['observed_max_seconds']) == (2, 6)
    assert planning['cpu_threads'] == 1
    assert planning['memory_limit_bytes'] == scope.memory_bytes
    assert planning['scratch_limit_bytes'] == scope.scratch_bytes
    for field in planning.keys() - {'estimate_ref', 'proposal_ref', 'job_ref'}:
        assert planning[field] == assigned[field]
    assert context == original
    assert list(tmp_path.iterdir()) == [path]
    assert ResourceToolEstimator.from_record(estimator.as_record()).as_record() == estimator.as_record()
    schema = {'type': 'object', 'additionalProperties': False, 'required': ['execution'],
        'properties': {'execution': report_source()['report_schema']}}
    validate_closed_schema(schema)
    validate_form({'execution': [planning, assigned]}, schema, lambda *_: True)
    assert not {'credit', 'yield', 'stop', 'remaining_seconds', 'queue_wait_seconds', 'memory_used_bytes'} & planning.keys()


def test_success_conditional_mean_retains_failures_censoring_and_unknowns(tmp_path, scope):
    path = tmp_path/'history.sqlite'
    history = RunHistory(path)
    record(history, scope, 'only-success', 10)
    before, = ResourceToolEstimator().estimate_context(capture_execution_scopes(path, [scope]))
    for index in range(12):
        record(history, scope, f'failure-{index}', 100+index, outcome='failed')
    record(history, scope, 'cancelled', 30, outcome='cancelled', kind='lower_bound')
    record(history, scope, 'resource-limit', 40, outcome='resource_limit')
    record(history, scope, 'unknown-running', 80, outcome='unknown', kind='lower_bound')
    record(history, scope, 'lost', None, outcome='unknown', kind='unmeasured')
    history.close()
    after, = ResourceToolEstimator().estimate_context(capture_execution_scopes(path, [scope]))
    assert before['expected_total_seconds'] == after['expected_total_seconds'] == 10
    assert before['successful_duration_samples'] == after['successful_duration_samples'] == 1
    assert before['proposal_ref'] == after['proposal_ref']
    assert before['expectation_ref'] != after['expectation_ref']
    groups = support(after)
    assert groups['failed']['attempt_count'] == groups['failed']['complete_duration_count'] == 12
    assert groups['cancelled']['lower_bound_count'] == 1
    assert groups['cancelled']['max_lower_bound_seconds'] == 30
    assert groups['resource_limit']['complete_duration_count'] == 1
    assert groups['unknown'] == {'outcome': 'unknown', 'attempt_count': 2, 'complete_duration_count': 0,
        'lower_bound_count': 1, 'unmeasured_count': 1, 'max_lower_bound_seconds': 80}


def test_current_conditions_and_exact_classes_do_not_transfer_timing(tmp_path, scope):
    path = tmp_path/'history.sqlite'
    history = RunHistory(path)
    record(history, scope, 'original', 5)
    alternatives = [replace(scope, **change) for change in (
        {'query_residues': 500}, {'cpu_threads': 2}, {'reference_residues': 20000},
        {'duration_measure': 'protected_service_wall_seconds'})]
    for index, alternative in enumerate(alternatives):
        record(history, alternative, f'alternative-{index}', 100)
    fresh = replace(scope, query_residues=254)
    forecasts = ResourceToolEstimator().estimate_context(capture_execution_scopes(path, [scope, fresh]))
    assert forecasts[0]['expected_total_seconds'] == 5
    assert forecasts[1]['status'] == 'no_matching_history'
    assert forecasts[1]['expected_total_seconds'] is None
    assert all(row['attempt_count'] == 0 for row in forecasts[1]['outcome_support'])
    condition = history.set_condition(operation_sha256=digest('operator-condition'), resource_id=scope.resource_id,
        state='degraded', reason='operator_report', reported_at='2026-10-20T11:00:00Z')
    record(history, scope, 'degraded-failure', 80, outcome='failed', condition=condition)
    degraded, = ResourceToolEstimator().estimate_context(capture_execution_scopes(path, [scope]))
    assert degraded['current_condition_state'] == 'degraded'
    assert degraded['status'] == 'no_matching_history' and degraded['expected_total_seconds'] is None
    assert support(degraded)['failed']['attempt_count'] == 1
    assert support(degraded)['succeeded']['attempt_count'] == 0
    record(history, scope, 'degraded-success', 50, condition=condition)
    history.close()
    current, = ResourceToolEstimator().estimate_context(capture_execution_scopes(path, [scope]))
    assert current['expected_total_seconds'] == 50
    assert forecasts[0]['expected_total_seconds'] == 5


def test_missing_history_preserves_known_configuration_without_creating_storage(tmp_path, scope):
    path = tmp_path/'absent-directory'/'history.sqlite'
    binding = ExecutionExpectations(path, by_grain={'annotation': [scope]})
    context = capture_execution_scopes(path, [scope])
    assert binding.capture('annotation') == context
    estimate, = ResourceToolEstimator().estimate_context(context)
    assert estimate['status'] == 'history_unavailable'
    assert estimate['execution_class_ref'] == scope.ref and estimate['cpu_threads'] == scope.cpu_threads
    assert estimate['expected_total_seconds'] is estimate['outcome_support'] is estimate['expectation_ref'] is None
    assert not path.parent.exists()
    # An existing unrelated SQLite database must not acquire statistics tables.
    unrelated = tmp_path/'other.sqlite'
    with sqlite3.connect(unrelated) as db:
        db.execute('CREATE TABLE unrelated (id INTEGER)')
    assert capture_execution_scopes(unrelated, [scope])['status'] == 'unavailable'
    with sqlite3.connect(unrelated) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == [('unrelated',)]


def test_no_proposed_configuration_has_no_fabricated_forecast(tmp_path):
    context = capture_execution_scopes(tmp_path/'missing.sqlite', [])
    assert context['execution_classes'] == context['snapshots'] == []
    assert ResourceToolEstimator().estimate_context(context) == []


@pytest.mark.parametrize('corruption', ['negative_count', 'bad_count_total', 'nan_mean', 'duplicate_group', 'wrong_resource'])
def test_invalid_statistics_are_structured_information(tmp_path, scope, corruption):
    path = tmp_path/'history.sqlite'
    history = RunHistory(path)
    record(history, scope, 'success', 5)
    history.close()
    context = capture_execution_scopes(path, [scope])
    snapshot = context['snapshots'][0]
    data = snapshot['data']
    row = data['statistics'][0]
    if corruption == 'negative_count':
        row['complete_duration_count'] = -1
    elif corruption == 'bad_count_total':
        row['attempt_count'] = 20
    elif corruption == 'nan_mean':
        row['mean_seconds'] = float('nan')
    elif corruption == 'duplicate_group':
        data['statistics'].append(deepcopy(row))
    else:
        data['current_condition']['resource_id'] = 'another-host'
    # Keep valid content identity for finite corruptions, so validation must
    # check semantics rather than relying only on the snapshot digest.
    if corruption != 'nan_mean':
        snapshot['ref'] = 'execution_expectation_'+digest(json.dumps(data, sort_keys=True, separators=(',', ':')))
    estimate, = ResourceToolEstimator().estimate_context(context)
    assert estimate['status'] == 'invalid_statistics'
    assert estimate['expected_total_seconds'] is estimate['outcome_support'] is None


def test_frozen_forecast_and_overrun_do_not_invent_remaining_time(tmp_path, scope):
    path = tmp_path/'history.sqlite'
    history = RunHistory(path)
    record(history, scope, 'first', 2)
    context = capture_execution_scopes(path, [scope])
    estimator = ResourceToolEstimator()
    sample = {'sample_ref': 'fixture_sample', 'elapsed_seconds': 100, 'duration_measure': scope.duration_measure}
    original, = estimator.estimate(context, job_ref='fixture_job', sample=sample)
    assert original['timing_relation'] == 'exceeds_observed_maximum'
    assert 'remaining_seconds' not in original
    mismatch, = estimator.estimate(context, job_ref='fixture_job', sample={**sample,
        'duration_measure': 'protected_service_wall_seconds'})
    assert mismatch['timing_relation'] == 'measurement_mismatch'
    record(history, scope, 'later', 10)
    history.close()
    future, = estimator.estimate(capture_execution_scopes(path, [scope]), job_ref='fixture_job', sample=sample)
    assert future['expected_total_seconds'] == 6
    assert estimator.estimate(context, job_ref='fixture_job', sample=sample) == [original]


@pytest.mark.parametrize('journal', ['action', 'decision'])
@pytest.mark.parametrize('prospective', [False, True])
def test_forecast_references_resolve_from_original_journals(tmp_path, scope, journal, prospective):
    path = tmp_path/'history.sqlite'
    history = RunHistory(path)
    record(history, scope, 'original', 5)
    history.close()
    context = capture_execution_scopes(path, [scope])
    estimator = ResourceToolEstimator()
    forecast, = (estimator.estimate_context(context) if prospective else
        estimator.estimate(context, job_ref='fixture_job'))
    # This focused journal fixture supplies the authoritative columns consumed
    # by the resolver. No global-history access or reforecast is available.
    path.unlink()
    db = sqlite3.connect(':memory:')
    try:
        db.execute('CREATE TABLE runtime_actions (result TEXT)')
        db.execute('CREATE TABLE runtime_model_calls (request TEXT)')
        if journal == 'action':
            db.execute('INSERT INTO runtime_actions VALUES(?)',
                (json.dumps({'resource_tool_estimates': [forecast]}),))
        else:
            db.execute('INSERT INTO runtime_model_calls VALUES(?)',
                (json.dumps({'context': {'resource_tool_estimates': [forecast]}}),))
        store = SimpleNamespace(db=db)
        fields = {'job_execution_estimate': 'estimate_ref', 'execution_class': 'execution_class_ref',
            'execution_expectation': 'expectation_ref', 'execution_proposal': 'proposal_ref'}
        for namespace, field in fields.items():
            reference = forecast[field]
            if reference is not None:
                assert recorded_estimate(store, reference, namespace=namespace) == forecast
                assert recorded_estimate(store, reference, 'wrong_job', namespace=namespace) is None
                if not prospective:
                    assert recorded_estimate(store, reference, 'fixture_job', namespace=namespace) == forecast
            assert recorded_estimate(store, 'nonexistent', namespace=namespace) is None
        assert recorded_estimate(store, forecast['estimate_ref']) == forecast
        assert recorded_estimate(store, forecast['estimate_ref'], namespace='execution_class') is None
        assert recorded_estimate(store, forecast['estimate_ref'], namespace='unrecognized') is None
    finally:
        db.close()
