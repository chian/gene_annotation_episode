"""Typed statistics and journal replays, with no models or native workload."""
from copy import deepcopy
from dataclasses import replace
import json
import sqlite3

import pytest

from gene_annotation_episode.communication import validate_closed_schema, validate_form, ReportBoundaryError
from gene_annotation_episode.execution_expectations import ExecutionExpectations
from gene_annotation_episode.homology_episodes import HomologyEpisodes
from gene_annotation_episode.monitoring_credit import MonitoringInformationCredit
from gene_annotation_episode.resource_estimation import ESTIMATE_SCHEMA, ResourceToolEstimator, recorded_estimate, report_source
from gene_annotation_episode.runtime import Journal, _compile_form
from test_runtime import setup, obj
from test_runtime_expectations import make_history, append


def captured(tmp_path):
    path = tmp_path/'history.sqlite'
    scope = make_history(path)
    binding = ExecutionExpectations(path, by_grain={'job_monitor': [scope]})
    return path, scope, binding.capture('job_monitor')


def sample(index, elapsed, *, state='running', byte_count=0):
    return {'job_ref': 'job_fixture', 'registry_ref': 'registry_fixture', 'sample_ref': f'sample_{index}',
        'sampled_at_unix_seconds': 100+index, 'state': state, 'outcome': 'pending',
        'elapsed_seconds': elapsed, 'duration_measure': 'protected_service_wall_seconds',
        'native_returncode': None, 'failure_code': None, 'resource': None,
        'progress_kind': 'native_execution_state_and_output_bytes_not_search_fraction',
        'outputs': [{'role': 'native_text', 'available': True, 'bytes': byte_count, 'writer_closed': False}]}


def test_forecaster_uses_exact_statistics_without_credit_or_stop_output(tmp_path):
    path, scope, context = captured(tmp_path)
    append(path, scope, 'second', 6)
    append(path, replace(scope, cpu_threads=2), 'different_cpu', 500)
    estimator = ResourceToolEstimator()
    before = estimator.estimate(context, job_ref='job_fixture', sample=sample(1, 3))[0]
    assert before['expected_total_seconds'] == before['observed_max_seconds'] == 2
    assert before['timing_relation'] == 'exceeds_observed_maximum'
    fresh = ExecutionExpectations(path, by_grain={'job_monitor': [scope]}).capture('job_monitor')
    after = estimator.estimate(fresh, job_ref='job_fixture', sample=sample(1, 3))[0]
    assert after['expected_total_seconds'] == 4 and after['observed_max_seconds'] == 6
    assert after['successful_duration_samples'] == 2
    assert after['timing_relation'] == 'not_exceeding_observed_maximum'
    assert estimator.estimate(context, job_ref='job_fixture', sample=sample(1, 3))[0] == before
    assert not {'credit', 'yield', 'stop', 'delay_seconds', 'remaining_seconds'} & before.keys()
    assert ResourceToolEstimator.from_record(estimator.as_record()).as_record() == estimator.as_record()


def test_missing_history_and_measurement_mismatch_do_not_invent_zero_time(tmp_path):
    _, _, context = captured(tmp_path)
    estimator = ResourceToolEstimator()
    missing = estimator.estimate(None, job_ref='job_fixture')[0]
    assert missing['status'] == 'history_unavailable' and missing['expected_total_seconds'] is None
    different_measure = sample(1, 1000)
    different_measure['duration_measure'] = 'systemd_service_wall_seconds'
    result = estimator.estimate(context, job_ref='job_fixture', sample=different_measure)[0]
    assert result['expected_total_seconds'] == 2 and result['timing_relation'] == 'measurement_mismatch'
    corrupt = deepcopy(context)
    corrupt['snapshots'][0]['data']['execution_class']['cpu_threads'] = 7
    assert estimator.estimate(corrupt, job_ref='job_fixture')[0]['status'] == 'invalid_statistics'


def test_planning_alternatives_do_not_measure_an_unassigned_job_class(tmp_path):
    path, scope, _ = captured(tmp_path)
    alternative = replace(scope, cpu_threads=2)
    append(path, alternative, 'two_cpu_execution', .5)
    context = ExecutionExpectations(path, by_grain={'job_monitor': [scope, alternative]}).capture('job_monitor')
    estimator = ResourceToolEstimator()
    records = estimator.estimate(context, job_ref='job_fixture', sample=sample(1, 1))
    assert [record['expected_total_seconds'] for record in records] == [2, .5]
    assert all(record['timing_relation'] == 'execution_class_not_assigned' for record in records)
    context['assigned_execution_class_ref'] = scope.ref
    records = estimator.estimate(context, job_ref='job_fixture', sample=sample(1, 1))
    assert records[0]['timing_relation'] == 'not_exceeding_observed_maximum'
    assert records[1]['timing_relation'] == 'execution_class_not_assigned'


def journal_sample(store, sample, estimates, index, *, episode='monitor', run='run_fixture'):
    Journal(store, run).save('runtime_actions', {'episode_id': episode, 'decision_index': index,
        'action': json.dumps({'kind': 'tool', 'tool': 'homology.sample', 'arguments': {}}),
        'result': json.dumps({'status': 'completed', 'operational_sample_ref': sample['sample_ref'],
            'result': sample, 'resource_tool_estimates': estimates}), 'credit': None})


def test_monitoring_credit_rewards_new_overrun_once_without_rewriting_history(tmp_path):
    path, scope, context = captured(tmp_path)
    store, _ = setup(tmp_path)
    Journal(store, 'run_fixture')
    scientific_before = store.db.execute('SELECT * FROM synthetic_records ORDER BY id').fetchall()
    estimator = ResourceToolEstimator()
    projector = MonitoringInformationCredit(information_unit=1)
    prior = sample(0, 1)
    assignment = {'job_ref': 'job_fixture', 'prior_samples': [prior]}
    def credit():
        return projector(store, role='job_monitor', assignment=assignment, episode_id='monitor', run_id='run_fixture')
    assert credit() == 0
    unchanged = sample(1, 1.5, byte_count=500)
    journal_sample(store, unchanged, estimator.estimate(context, job_ref='job_fixture', sample=unchanged), 0)
    assert credit() == 0  # Bytes and elapsed ticks alone have no credit.
    overrun = sample(2, 3)
    estimates = estimator.estimate(context, job_ref='job_fixture', sample=overrun)
    journal_sample(store, overrun, estimates, 1)
    assert credit() == 1
    later = sample(3, 4, byte_count=1000)
    journal_sample(store, later, estimator.estimate(context, job_ref='job_fixture', sample=later), 2)
    assert credit() == 1
    findings = projector.findings(store, assignment=assignment, episode_id='monitor', run_id='run_fixture')
    assert len(findings) == 1 and findings[0]['new_state'] is False
    assert findings[0]['new_timing_overruns'] == estimates
    # Global new knowledge cannot reprice the closed child's prior work.
    append(path, scope, 'later_real_duration', 100)
    assert credit() == 1 and projector.findings(store, assignment=assignment,
        episode_id='monitor', run_id='run_fixture') == findings
    assert store.db.execute('SELECT * FROM synthetic_records ORDER BY id').fetchall() == scientific_before
    assert recorded_estimate(store, estimates[0]['estimate_ref'], 'job_fixture') == estimates[0]
    assert recorded_estimate(store, estimates[0]['estimate_ref'], 'another_job') is None
    # Passing known samples to a later child establishes its baseline, not new credit.
    journal_sample(store, later, estimator.estimate(context, job_ref='job_fixture', sample=later), 0, episode='monitor_2')
    assert projector(store, role='job_monitor', assignment={'job_ref': 'job_fixture', 'prior_samples': [overrun]},
        episode_id='monitor_2', run_id='run_fixture') == 0
    # This did not append either local credit or local estimates to global statistics.
    with sqlite3.connect(path) as db:
        rows = [json.loads(row[0]) for row in db.execute('SELECT data FROM run_statistics')]
    assert len(rows) == 2 and all('credit' not in row and 'estimate_ref' not in row for row in rows)


def test_forecasts_and_findings_are_closed_parent_form_fields(tmp_path):
    _, _, context = captured(tmp_path)
    estimator = ResourceToolEstimator()
    forecast = estimator.estimate(context, job_ref='job_fixture')[0]
    schema = obj({'execution': report_source()['report_schema']})
    validate_closed_schema(schema)
    _compile_form(json.dumps(schema), {'resource_tool_estimates': report_source()})
    assert validate_form({'execution': [forecast]}, schema, lambda *_: True)
    bad = deepcopy(forecast)
    bad['instructions'] = 'Wait and submit another job'
    with pytest.raises(ReportBoundaryError):
        validate_form({'execution': [bad]}, schema, lambda *_: True)
    validate_closed_schema(obj({'information': MonitoringInformationCredit.report_source()['report_schema']}))
    _compile_form(json.dumps(obj({'information': MonitoringInformationCredit.report_source()['report_schema']})),
        {'monitoring_findings': MonitoringInformationCredit.report_source()})
    # Built-in reference arrays retain their original reference-only rule.
    with pytest.raises(ValueError, match='recorded reference arrays'):
        _compile_form(json.dumps(obj({'refs': {'type': 'array', 'items': {'type': 'number'},
            'x-source': 'changed_record_refs'}})))


def test_identity_is_not_permission_to_invent_forecast_values(tmp_path):
    _, _, context = captured(tmp_path)
    store, _ = setup(tmp_path)
    estimator = ResourceToolEstimator()
    measured = sample(1, 3)
    forecast = estimator.estimate(context, job_ref='job_fixture', sample=measured)[0]
    journal_sample(store, measured, [forecast], 0)
    # A null sample forecast is also a legitimate pre-sample planning record.
    planning = estimator.estimate(context, job_ref='job_fixture')[0]
    Journal(store, 'run_fixture').save('runtime_model_calls', {'episode_id': 'monitor', 'call_index': 0,
        'purpose': 'decision', 'request': json.dumps({'context': {'resource_tool_estimates': [planning]}}), 'response': None})
    binding = object.__new__(HomologyEpisodes)
    binding.validate_report(planning, {'job_ref': 'job_fixture'}, store=store, schema=ESTIMATE_SCHEMA)
    forged = deepcopy(planning)
    forged['expected_total_seconds'] = 0
    with pytest.raises(ReportBoundaryError) as error:
        binding.validate_report(forged, {'job_ref': 'job_fixture'}, store=store, schema=ESTIMATE_SCHEMA)
    assert error.value.diagnostic['code'] == 'estimate_fact_mismatch'
