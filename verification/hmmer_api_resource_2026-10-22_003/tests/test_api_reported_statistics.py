"""Offline logical-result statistics, frozen forecasts and original conditions."""
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
import sqlite3

import pytest

from gene_annotation_episode.communication import (
    ReportBoundaryError, validate_closed_schema, validate_form)
from gene_annotation_episode.execution_expectations import capture_execution_scopes
from gene_annotation_episode.resource_estimation import (
    API_REPORT_ESTIMATE_SCHEMA, ESTIMATE_SCHEMA, ResourceToolEstimator,
    recorded_api_forecasts, recorded_estimate, recorded_forecasts,
    reported_report_source, report_source, validate_recorded_estimates)
from gene_annotation_episode.run_statistics import (
    ExecutionClass, ReportedResultStatistic, RunHistory, RunStatistic,
    REPORTED_RESULT_MEASURE, REPORTED_RESULT_PHASE, REPORTED_RESULT_UNIT)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def remote_scope(**changes):
    return replace(ExecutionClass(phase=REPORTED_RESULT_PHASE, backend='https',
        resource_id='fixture-hmmer', implementation_sha256=None, parameters_sha256=digest('options'),
        memory_bytes=None, scratch_bytes=None, cpu_threads=None, query_residues=253,
        reference_records=None, reference_residues=None, reference_state='unknown',
        duration_measure=REPORTED_RESULT_MEASURE), **changes)


def result_statistic(name, seconds=2, **changes):
    return replace(ReportedResultStatistic(observation_sha256=digest(name),
        source_sha256=digest('first-witness:'+name), observed_at='2026-10-22T12:00:00Z',
        elapsed_seconds=seconds, condition_ref=None), **changes)


def snapshot(history, scope):
    ref = history.capture(scope)
    reader = history.reader(ref)
    try:
        return {'ref': ref, 'data': reader.get(ref)}
    finally:
        reader.close()


def test_distinct_observation_unit_idempotency_and_immutable_snapshot(tmp_path):
    path, scope = tmp_path/'shared.sqlite', remote_scope()
    history = RunHistory(path)
    try:
        first = result_statistic('logical-job-one', 2)
        assert history.record_reported_result(scope, first) == first.observation_sha256
        assert history.record_reported_result(scope, first) == first.observation_sha256
        original = snapshot(history, scope)
        assert original['data']['observation_unit'] == REPORTED_RESULT_UNIT
        assert original['data']['statistics'] == [{'condition_state': 'unspecified',
            'reported_result_count': 1, 'mean_seconds': 2, 'min_seconds': 2, 'max_seconds': 2}]
        assert history.db.execute('SELECT count(*) FROM run_statistics').fetchone()[0] == 0
    finally:
        history.close()
    history = RunHistory(path, create=False)
    try:
        # Equal reported durations are two results only for distinct identities.
        history.record_reported_result(scope, result_statistic('logical-job-two', 2))
        newer = snapshot(history, scope)
        assert newer['data']['statistics'][0]['reported_result_count'] == 2
        reader = history.reader(original['ref'])
        try:
            assert reader.get(original['ref']) == original['data']
        finally:
            reader.close()
        serialized = canonical(newer['data'])
        assert not any(word in serialized for word in ('attempt_count', 'outcome', 'failure',
            'retry_count', 'lower_bound', 'unmeasured'))
    finally:
        history.close()


@pytest.mark.parametrize('change', ['elapsed', 'source', 'class', 'condition'])
def test_conflicting_logical_identity_preserves_first_result(tmp_path, change):
    history, scope = RunHistory(tmp_path/'shared.sqlite'), remote_scope()
    first = result_statistic('one')
    try:
        history.record_reported_result(scope, first)
        original = snapshot(history, scope)
        condition = history.set_condition(operation_sha256=digest('outage'), resource_id=scope.resource_id,
            state='degraded', reason='outage', reported_at='2026-10-22T13:00:00Z')
        changed_scope = replace(scope, query_residues=254) if change == 'class' else scope
        changed_stat = replace(first, **{'elapsed_seconds': 3} if change == 'elapsed' else
            {'source_sha256': digest('later-page')} if change == 'source' else
            {'condition_ref': condition} if change == 'condition' else {})
        with pytest.raises(ValueError, match='reported_result_measurement_conflict'):
            history.record_reported_result(changed_scope, changed_stat)
        assert history.db.execute('SELECT count(*) FROM reported_result_statistics').fetchone()[0] == 1
        reader = history.reader(original['ref'])
        try:
            assert reader.get(original['ref']) == original['data']
        finally:
            reader.close()
    finally:
        history.close()


def test_exact_types_and_physical_attempt_boundary(tmp_path):
    history, remote = RunHistory(tmp_path/'history.sqlite'), remote_scope()
    native = ExecutionClass(phase='protein_homology_search', backend='local', resource_id='fixture-native',
        implementation_sha256=digest('program'), parameters_sha256=digest('options'),
        memory_bytes=100, scratch_bytes=100, cpu_threads=1, query_residues=253,
        reference_records=5, reference_residues=100, reference_state='available')
    physical = RunStatistic(attempt_sha256=digest('attempt'), source_sha256=digest('native-receipt'),
        observed_at='2026-10-22T12:00:00Z', outcome='succeeded', duration_kind='complete',
        elapsed_seconds=2, condition_ref=None)
    try:
        with pytest.raises(ValueError, match='distinct_statistic'):
            history.record(remote, physical)
        with pytest.raises(TypeError, match='typed_reported_result'):
            history.record_reported_result(remote, physical)
        with pytest.raises(TypeError, match='typed_reported_result'):
            history.record_reported_result(remote, asdict(result_statistic('one')))
        with pytest.raises(ValueError, match='reported_result_execution_class_required'):
            history.record_reported_result(native, result_statistic('one'))
        history.record(native, physical)
        assert snapshot(history, native)['data']['version'] == 'execution_statistics_v1'
    finally:
        history.close()


@pytest.mark.parametrize('changes', [{'implementation_sha256': digest('unknown-build')},
    {'memory_bytes': 10}, {'scratch_bytes': 10}, {'cpu_threads': 1},
    {'reference_records': 1}, {'reference_residues': 1}, {'reference_state': 'available'},
    {'wall_seconds': 1}, {'duration_measure': 'systemd_service_wall_seconds'}, {'query_residues': None}])
def test_remote_class_enforces_unknown_operands(changes):
    with pytest.raises(ValueError):
        remote_scope(**changes)


@pytest.mark.parametrize('seconds', [-1, float('nan'), float('inf'), None, True, 10**1000])
def test_reported_result_requires_actual_finite_duration(seconds):
    with pytest.raises(ValueError):
        result_statistic('invalid', seconds)


def test_explicit_estimator_and_exact_separate_report_source(tmp_path):
    native = ResourceToolEstimator()
    opted = ResourceToolEstimator.with_reported_results()
    assert native.as_record() == {'version': 'resource_tool_duration_estimator_v2',
        'method': 'exact_class_current_condition_successful_duration_mean'}
    assert opted.as_record() == {'version': 'resource_tool_duration_estimator_v3',
        'method': 'exact_class_current_condition_successful_duration_mean',
        'reported_result_method': 'exact_exposed_configuration_current_condition_reported_duration_mean_v1'}
    assert ResourceToolEstimator.from_record(opted.as_record()).as_record() == opted.as_record()
    assert ResourceToolEstimator.from_record(native.as_record()).as_record() == native.as_record()
    assert REPORTED_RESULT_PHASE not in ESTIMATE_SCHEMA['properties']['phase']['enum']
    assert report_source()['report_schema']['items'] == ESTIMATE_SCHEMA
    history = RunHistory(tmp_path/'history.sqlite')
    try:
        history.record_reported_result(remote_scope(), result_statistic('one', 0))
    finally:
        history.close()
    context = capture_execution_scopes(tmp_path/'history.sqlite', [remote_scope()])
    with pytest.raises(ValueError, match='not_enabled'):
        native.estimate_reported_context(context)
    with pytest.raises(ValueError, match='native_execution_classes'):
        opted.estimate_context(context)
    row, = opted.estimate_reported_context(context)
    assert row['expected_total_seconds'] == 0
    assert row['outcome_support'] is row['job_ref'] is row['sample_ref'] is row['elapsed_seconds'] is None
    assert row['reported_result_support'] == {'reported_result_count': 1}
    assert row['successful_duration_samples'] == 1 and row['timing_relation'] == 'unknown'
    schema = {'type': 'object', 'additionalProperties': False, 'required': ['reported'],
        'properties': {'reported': reported_report_source()['report_schema']}}
    validate_closed_schema(schema)
    validate_form({'reported': [row]}, schema, lambda *_: True)
    assert schema['properties']['reported']['items'] == API_REPORT_ESTIMATE_SCHEMA
    assert schema['properties']['reported']['x-source'] == 'api_reported_execution_forecasts'
    forged = {**row, 'outcome_support': [{'outcome': 'succeeded', 'attempt_count': 1}]}
    with pytest.raises(ReportBoundaryError):
        validate_form({'reported': [forged]}, schema, lambda *_: True)


def test_current_condition_groups_and_unavailable_support_are_distinct(tmp_path):
    path, scope = tmp_path/'history.sqlite', remote_scope()
    history = RunHistory(path)
    estimator = ResourceToolEstimator.with_reported_results()
    try:
        history.record_reported_result(scope, result_statistic('old', 2))
        original = capture_execution_scopes(path, [scope])
        condition = history.set_condition(operation_sha256=digest('degraded'), resource_id=scope.resource_id,
            state='degraded', reason='operator_report', reported_at='2026-10-22T13:00:00Z')
        # A known empty current condition is zero result support, never zero duration.
        empty, = estimator.estimate_reported_context(capture_execution_scopes(path, [scope]))
        assert empty['status'] == 'no_matching_history'
        assert empty['reported_result_support'] == {'reported_result_count': 0}
        assert empty['expected_total_seconds'] is None
        history.record_reported_result(scope, result_statistic('new', 10, condition_ref=condition))
        history.record_reported_result(scope, result_statistic('late-old', 4))
        current, = estimator.estimate_reported_context(capture_execution_scopes(path, [scope]))
        assert current['expected_total_seconds'] == 10
        assert current['reported_result_support'] == {'reported_result_count': 1}
        old, = estimator.estimate_reported_context(original)
        assert old['expected_total_seconds'] == 2 and old['current_condition_state'] == 'unspecified'
    finally:
        history.close()
    missing, = estimator.estimate_reported_context(capture_execution_scopes(tmp_path/'absent.sqlite', [scope]))
    assert missing['status'] == 'history_unavailable' and missing['reported_result_support'] is None
    assert not (tmp_path/'absent.sqlite').exists()


@pytest.mark.parametrize('corruption', ['count', 'unit', 'range', 'extra', 'condition', 'duplicate',
    'sequence', 'snapshot_digest'])
def test_semantic_and_content_validation_before_reported_projection(tmp_path, corruption):
    path, scope = tmp_path/'history.sqlite', remote_scope()
    history = RunHistory(path)
    try:
        history.record_reported_result(scope, result_statistic('one', 2))
    finally:
        history.close()
    context = capture_execution_scopes(path, [scope])
    saved = context['snapshots'][0]
    data, row = saved['data'], saved['data']['statistics'][0]
    if corruption == 'count':
        row['reported_result_count'] = 0
    elif corruption == 'unit':
        data['observation_unit'] = 'physical_attempt'
    elif corruption == 'range':
        row['max_seconds'] = 5
    elif corruption == 'extra':
        row['attempt_count'] = 1
    elif corruption == 'condition':
        data['current_condition']['resource_id'] = 'other-service'
    elif corruption == 'duplicate':
        data['statistics'].append(deepcopy(row))
    elif corruption == 'sequence':
        data['history_through_sequence'] = 0
    else:
        data['statistics'][0]['mean_seconds'] = 99
    if corruption != 'snapshot_digest':
        saved['ref'] = 'execution_expectation_'+digest(canonical(data))
    forecast, = ResourceToolEstimator.with_reported_results().estimate_reported_context(context)
    assert forecast['status'] == 'invalid_statistics'
    assert forecast['expected_total_seconds'] is forecast['reported_result_support'] is None


@pytest.fixture
def statistics(tmp_path):
    from gene_annotation_episode.api_timing_records import ApiTimingBinding
    from gene_annotation_episode.api_reported_statistics import ApiReportedStatistics
    binding = ApiTimingBinding(ledger_path=tmp_path/'timing.sqlite', history_path=tmp_path/'history.sqlite',
        resource_id='fixture-hmmer', monitoring_information_unit=1.25)
    registry = {'version': 'public_search_registry_v1', 'registry_ref': 'fixture_registry',
        'resource_id': binding.resource_id, 'provider': 'hmmer', 'client_binding_sha256': digest('fixture-client')}
    return ApiReportedStatistics(binding, registry=registry)


def request(**changes):
    from gene_annotation_episode.provider_jobs import build_search_request
    normalized, _ = build_search_request(subject_ref='sequence_fixture', query_fasta='>fixture\nM'+'A'*252,
        algorithm='phmmer', database='uniprotrefprot', parameters={})
    return {**normalized, **changes}


def witness(statistics, *, start=None, remote_id='01234567-89ab-4cde-8fab-0123456789ab', seconds=3):
    from gene_annotation_episode.api_timing_records import reported_result_identity
    identity = reported_result_identity(statistics.registry['registry_ref'], remote_id)
    return {'version': 'hmmer_reported_duration_witness_v1', 'measurement_ref': identity['measurement_ref'],
        'order_binding_ref': 'api_order_'+digest('order'), 'intent_ref': 'api_intent_'+digest('intent'),
        'submission_binding_ref': 'api_submission_'+digest('submission'),
        'registry_ref': statistics.registry['registry_ref'], 'resource_id': statistics.binding.resource_id,
        'job_ref': 'provider_job_'+digest('job'), 'remote_id': remote_id,
        'request_sha256': digest(canonical(request())), 'acquisition_receipt_ref': 'provider_operation_'+digest('result'),
        'snapshot_ref': 'artifact_'+digest('snapshot'), 'entity_sha256': digest('entity'),
        'field_path': '$.result.stats.elapsed', 'duration_measure': REPORTED_RESULT_MEASURE,
        'observation_unit': REPORTED_RESULT_UNIT, 'elapsed_seconds': seconds,
        'observed_at': '2026-10-22T13:00:00Z', 'semantics_version': 'hmmer_reported_elapsed_source_v1',
        'start_context': start if start is not None else statistics.capture_start(request())}


def test_actual_exposed_configuration_excludes_biology_and_retrieval(statistics):
    first = statistics.execution_class(request())
    same = request(subject_ref='another_gene', query_sha256=digest('different-fasta-label'),
        sequence_sha256=digest('different-sequence'), page_size=1,
        parameters={'include_taxonomy': [], 'exclude_taxonomy': []})
    assert statistics.execution_class(same) == first
    for change in ({'query_length': 254}, {'algorithm': 'hmmscan'}, {'database': 'pfam'},
                   {'parameters': {'E': 10}}, {'parameters': {'mx': 'BLOSUM62'}}):
        assert statistics.execution_class(request(**change)).ref != first.ref
    for field in ('memory_bytes', 'scratch_bytes', 'cpu_threads', 'implementation_sha256',
                  'reference_records', 'reference_residues', 'wall_seconds'):
        assert getattr(first, field) is None
    serialized = canonical(asdict(first))
    assert not any(value in serialized for value in ('sequence_fixture', request()['query_sha256'],
        request()['sequence_sha256'], 'taxonomy', 'uniprotrefprot'))


@pytest.mark.parametrize('parameters', [{'include_taxonomy': [562]}, {'exclude_taxonomy': [562]},
    {'E': float('nan')}, {'E': True}, {'E': 10**1000}, {'mx': 'matrix with prose'}, {'threshold': []},
    {'arbitrary_control': 1}])
def test_unsupported_exposed_configuration_preserves_no_shared_biological_proxy(statistics, parameters):
    with pytest.raises(ValueError, match='unsupported_statistics_configuration'):
        statistics.execution_class(request(parameters=parameters))
    captured = statistics.capture(request(parameters=parameters))
    assert captured['status'] == 'unavailable' and captured['code'] == 'unsupported_statistics_configuration'
    assert captured['execution_classes'] == captured['snapshots'] == []
    assert not statistics.binding.history_path.exists()


def test_original_condition_export_and_cross_run_learning(statistics):
    history = RunHistory(statistics.binding.history_path)
    try:
        before = statistics.capture(request())
        start = statistics.capture_start(request())
        assert start['condition_capture'] == 'captured_before_submission' and start['condition_ref'] is None
        history.set_condition(operation_sha256=digest('later-condition'), resource_id='fixture-hmmer',
            state='degraded', reason='outage', reported_at='2026-10-22T12:30:00Z')
        observed = witness(statistics, start=start)
        exported = statistics.export(observed)
        assert exported['state'] == 'recorded' and exported['code'] is None
        assert statistics.export(observed) == exported
        stored = json.loads(history.db.execute('SELECT data FROM reported_result_statistics').fetchone()[0])
        assert stored['condition_ref'] is None
        assert stored['source_sha256'] == digest(canonical(observed))
        assert stored['observation_sha256'] == exported['observation_sha256']
        assert set(stored) == {'observation_sha256', 'source_sha256', 'observed_at', 'elapsed_seconds', 'condition_ref'}
        assert history.db.execute('SELECT count(*) FROM run_statistics').fetchone()[0] == 0
        estimator = ResourceToolEstimator.with_reported_results()
        original, = estimator.estimate_reported_context(before)
        assert original['status'] == 'no_matching_history'
        # A second actual binding object shares only this caller-selected history.
        from gene_annotation_episode.api_reported_statistics import ApiReportedStatistics
        second = ApiReportedStatistics(statistics.binding, registry=statistics.registry)
        current, = estimator.estimate_reported_context(second.capture(request()))
        assert current['reported_result_support'] == {'reported_result_count': 0}
        assert current['current_condition_state'] == 'degraded'
        assert estimator.estimate_reported_context(before) == [original]
    finally:
        history.close()


def test_unknown_start_never_becomes_unspecified_after_history_recovery(statistics):
    start = statistics.capture_start(request())
    assert start['condition_capture'] == 'unavailable_before_submission' and start['condition_ref'] is None
    observed = witness(statistics, start=start)
    assert statistics.export(observed)['code'] == 'start_condition_unknown'
    history = RunHistory(statistics.binding.history_path)
    try:
        assert statistics.export(observed)['code'] == 'start_condition_unknown'
        assert history.db.execute('SELECT count(*) FROM reported_result_statistics').fetchone()[0] == 0
        assert statistics.capture_start(request())['condition_capture'] == 'captured_before_submission'
    finally:
        history.close()


def test_missing_schema_is_not_created_by_forecast_or_export(statistics):
    history = RunHistory(statistics.binding.history_path)
    history.db.execute('DROP TABLE reported_result_statistics')
    history.db.commit()
    history.close()
    start = statistics.capture_start(request())
    observed = witness(statistics, start=start)
    assert start['condition_capture'] == 'captured_before_submission'
    assert statistics.capture(request())['code'] == 'history_schema_unavailable'
    assert statistics.export(observed)['code'] == 'history_schema_unavailable'
    with sqlite3.connect(statistics.binding.history_path) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE name='reported_result_statistics'").fetchall() == []
    # Explicit history initialization is the only schema upgrade here.
    history = RunHistory(statistics.binding.history_path)
    history.close()
    assert statistics.export(observed)['state'] == 'recorded'


def test_locked_history_returns_missingness_and_preserves_start_condition(statistics):
    history = RunHistory(statistics.binding.history_path)
    history.close()
    known = statistics.capture_start(request())
    observed = witness(statistics, start=known)
    with sqlite3.connect(statistics.binding.history_path) as blocker:
        blocker.execute('BEGIN EXCLUSIVE')
        assert statistics.capture_start(request())['condition_capture'] == 'unavailable_before_submission'
        assert statistics.capture(request())['code'] == 'history_unavailable'
        assert statistics.export(observed)['code'] == 'history_unavailable'
        blocker.rollback()
    assert statistics.export(observed)['state'] == 'recorded'


def test_actual_logical_identity_conflict_and_distinct_equal_values(statistics):
    history = RunHistory(statistics.binding.history_path)
    try:
        first = witness(statistics)
        assert statistics.export(first)['state'] == 'recorded'
        conflict = statistics.export({**first, 'elapsed_seconds': first['elapsed_seconds']+1})
        assert conflict['state'] == 'conflict' and conflict['code'] == 'statistics_identity_conflict'
        assert statistics.export({**first, 'entity_sha256': digest('different-first-source')})['state'] == 'conflict'
        second = witness(statistics, remote_id='abcdefab-1234-4567-89ab-abcdefabcdef')
        assert statistics.export(second)['state'] == 'recorded'
        result, = ResourceToolEstimator.with_reported_results().estimate_reported_context(statistics.capture(request()))
        assert result['reported_result_support'] == {'reported_result_count': 2}
        assert result['expected_total_seconds'] == first['elapsed_seconds']
    finally:
        history.close()


def test_two_actual_opted_in_callers_share_only_exposed_class_statistics(statistics, tmp_path):
    from gene_annotation_episode.api_reported_statistics import ApiReportedStatistics
    from gene_annotation_episode.api_timing_records import ApiTimingBinding
    history = RunHistory(statistics.binding.history_path)
    history.close()
    binding = ApiTimingBinding(ledger_path=tmp_path/'second-ledger.sqlite',
        history_path=statistics.binding.history_path, resource_id=statistics.binding.resource_id,
        monitoring_information_unit=statistics.binding.monitoring_information_unit)
    second = ApiReportedStatistics(binding,
        registry={**statistics.registry, 'registry_ref': 'second_run_registry'})
    estimator = ResourceToolEstimator.with_reported_results()
    original = second.capture(request(subject_ref='another_sequence'))
    empty, = estimator.estimate_reported_context(original)
    assert empty['reported_result_support'] == {'reported_result_count': 0}
    assert statistics.export(witness(statistics))['state'] == 'recorded'
    learned, = estimator.estimate_reported_context(second.capture(request(subject_ref='another_sequence')))
    assert learned['expected_total_seconds'] == 3
    assert learned['reported_result_support'] == {'reported_result_count': 1}
    assert estimator.estimate_reported_context(original) == [empty]
    for changed in ({'query_length': 254}, {'algorithm': 'hmmscan'}, {'parameters': {'T': 1}},
                    {'database': 'pfam'}):
        incompatible, = estimator.estimate_reported_context(second.capture(request(**changed)))
        assert incompatible['status'] == 'no_matching_history'
        assert incompatible['reported_result_support'] == {'reported_result_count': 0}
        assert incompatible['expected_total_seconds'] is None
    other = ApiReportedStatistics(ApiTimingBinding(ledger_path=tmp_path/'other-ledger.sqlite',
        history_path=statistics.binding.history_path, resource_id='other-hmmer', monitoring_information_unit=1.25),
        registry={**statistics.registry, 'resource_id': 'other-hmmer'})
    incompatible, = estimator.estimate_reported_context(other.capture(request()))
    assert incompatible['reported_result_support'] == {'reported_result_count': 0}
    assert not binding.ledger_path.exists() and not statistics.binding.ledger_path.exists()


@pytest.mark.parametrize('missing', ['start_context', 'intent_ref', 'submission_binding_ref'])
def test_missing_original_binding_cannot_export(statistics, missing):
    history = RunHistory(statistics.binding.history_path)
    try:
        observed = witness(statistics)
        observed[missing] = None
        result = statistics.export(observed)
        assert result['state'] == 'unavailable'
        assert result['code'] == ('submission_binding_unavailable' if missing == 'submission_binding_ref'
                                 else 'start_binding_unavailable')
        assert history.db.execute('SELECT count(*) FROM reported_result_statistics').fetchone()[0] == 0
    finally:
        history.close()


def test_api_forecasts_resolve_only_original_journals_and_validate_facts(tmp_path):
    from types import SimpleNamespace
    path, scope = tmp_path/'history.sqlite', remote_scope()
    history = RunHistory(path)
    try:
        history.record_reported_result(scope, result_statistic('one', 3))
    finally:
        history.close()
    forecast, = ResourceToolEstimator.with_reported_results().estimate_reported_context(capture_execution_scopes(path, [scope]))
    path.unlink()
    db = sqlite3.connect(':memory:')
    store = SimpleNamespace(db=db)
    try:
        db.execute('CREATE TABLE runtime_actions(run_id TEXT,episode_id TEXT,decision_index INTEGER,result TEXT)')
        db.execute('CREATE TABLE runtime_model_calls(run_id TEXT,episode_id TEXT,call_index INTEGER,request TEXT)')
        db.execute('INSERT INTO runtime_model_calls VALUES(?,?,?,?)', ('run', 'episode', 0,
            canonical({'context': {'api_reported_execution_forecasts': [forecast]}})))
        db.execute('INSERT INTO runtime_actions VALUES(?,?,?,?)', ('run', 'episode', 0, canonical({'status': 'completed'})))
        assert recorded_api_forecasts(store, run_id='run', episode_id='episode') == [forecast]
        assert recorded_forecasts(store, run_id='run', episode_id='episode') == []
        for namespace, field in (('job_execution_estimate', 'estimate_ref'), ('execution_class', 'execution_class_ref'),
                ('execution_proposal', 'proposal_ref'), ('execution_expectation', 'expectation_ref')):
            assert recorded_estimate(store, forecast[field], namespace=namespace) == forecast
        assert recorded_estimate(store, forecast['estimate_ref'], job_ref='native-job') is None
        validate_recorded_estimates(store, forecast, schema=API_REPORT_ESTIMATE_SCHEMA)
        with pytest.raises(ReportBoundaryError, match='differs'):
            validate_recorded_estimates(store, {**forecast, 'reported_result_support': {'reported_result_count': 99}},
                schema=API_REPORT_ESTIMATE_SCHEMA)
        # Failed work does not become the completed forecast boundary.
        db.execute('INSERT INTO runtime_actions VALUES(?,?,?,?)', ('run', 'episode', 1,
            canonical({'status': 'failed', 'api_reported_execution_forecasts': []})))
        assert recorded_api_forecasts(store, run_id='run', episode_id='episode') == [forecast]
        db.execute('INSERT INTO runtime_actions VALUES(?,?,?,?)', ('run', 'episode', 2,
            canonical({'status': 'partial', 'api_reported_execution_forecasts': []})))
        assert recorded_api_forecasts(store, run_id='run', episode_id='episode') == []
    finally:
        db.close()
