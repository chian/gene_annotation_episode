"""Operational receiving failures preserve actual work and typed communication.

Tiny native jobs and scripted episode decisions, not model/science verification.
"""
from copy import deepcopy
import json
import sqlite3
import subprocess
from types import SimpleNamespace

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.communication import ReportBoundaryError
from gene_annotation_episode.execution_expectations import ExecutionExpectations
from gene_annotation_episode.native_lifecycle import cancel
from gene_annotation_episode.monitoring_credit import MonitoringInformationCredit
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.runtime import Journal, Record, TypedReportContract
from test_homology_episode_runtime import prepared, Provider, action, commission, run


def cleanup(jobs, store):
    # Restore only the deliberately closed test connection for native cleanup.
    try:
        jobs.db.execute('SELECT 1')
    except sqlite3.ProgrammingError:
        jobs.db = sqlite3.connect(jobs.directory/'jobs.sqlite')
        jobs.db.row_factory = sqlite3.Row
    for row in jobs.db.execute('SELECT job_ref FROM orders'):
        handle = jobs._handle(row[0])
        if handle.path.exists():
            cancel(handle)
    jobs.close()
    store.close()


def launch_actions():
    return [action('homology.environment'), action('homology.configure'),
        action('homology.stage'), action('homology.submit'), action('homology.check_handoff')]


@pytest.mark.parametrize('failure_kind', ['receipt_write', 'control_timeout'])
def test_closure_failure_returns_unavailable_handoff_and_preserves_selected_work(tmp_path, monkeypatch, failure_kind):
    store, tools, query, scope, jobs, binding = prepared(tmp_path)
    original = jobs.check_handoff
    calls = 0
    def check(handoff):
        nonlocal calls
        calls += 1
        if calls == 2:  # Selected check succeeded; closure hits a real SQL failure.
            if failure_kind == 'control_timeout':
                raise subprocess.TimeoutExpired(['systemctl'], 5)
            jobs.db.execute("CREATE TRIGGER fail_receipt BEFORE INSERT ON handoffs "
                "BEGIN SELECT RAISE(FAIL, 'synthetic receipt storage failure'); END")
        return original(handoff)
    monkeypatch.setattr(jobs, 'check_handoff', check)
    try:
        result = run(store, tools, Provider([
            commission(binding, 'job_launch', scope, query_ref=query), *launch_actions()]),
            binding, tmp_path/'run', counts={'annotation': 1, 'job_launch': 5})
        assert result['completed_actions'] == 1
        form = json.loads(store.db.execute('SELECT form FROM runtime_report_attempts').fetchone()[0])
        assert form['job_handoff'] is None
        assert form['job_handoff_state'] == 'unavailable'
        assert form['job_handoff_failure'] == 'receiving_interface_unavailable'
        assert form['local_credit'] == 5
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 6
        assert store.db.execute("SELECT count(*) FROM runtime_actions "
            "WHERE json_extract(action,'$.tool')='homology.check_handoff' "
            "AND json_extract(result,'$.status')='completed'").fetchone()[0] == 1
    finally:
        cleanup(jobs, store)


def test_missing_order_during_closure_keeps_original_assignment_reference(tmp_path):
    store, tools, query, scope, jobs, binding = prepared(tmp_path)
    assignment = binding.assign(store, 'job_launch', {'query_ref': query, 'cpu': 1},
        scope, operation_key='fixture')
    Journal(store, 'fixture-run')
    source = SimpleNamespace(request=SimpleNamespace(message=Record({'job_assignment': assignment})),
        workflow=SimpleNamespace(store=store, run_id='fixture-run'), episode_id='fixture-child',
        path=(('job_launch', 'fixture'),))
    try:
        jobs.db.execute('DELETE FROM orders')  # Explicit synthetic loss after assignment.
        jobs.db.commit()
        facts = binding.facts(source)
        assert facts['job_ref'] == assignment['job_ref']
        assert facts['job_handoff'] is None
        assert facts['job_handoff_failure'] == 'receiving_interface_unavailable'
        fields = {key: binding.fact_sources('job_launch')[key]['report_schema']
            for key in ('job_ref', 'job_cpu', 'job_handoff', 'job_handoff_state', 'job_handoff_failure')}
        schema = {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}
        form = {key: facts[key] for key in fields}
        contract = TypedReportContract('Retain the assigned identity and receiving failure', schema,
            lambda value, namespace=None: binding.resolve(store, scope, value, namespace, assignment=assignment),
            lambda value: binding.validate_report(value, assignment, store=store, schema=schema))
        assert contract.admit(form, audit_identifiers=('fixture-child',)).as_record() == form
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
    finally:
        cleanup(jobs, store)


@pytest.mark.parametrize('failure,code', [
    (sqlite3.OperationalError('synthetic unavailable registry'), 'job_storage_failed'),
    (OSError('synthetic unavailable interface'), 'job_operation_failed'),
    (subprocess.TimeoutExpired(['systemctl'], 5), 'job_control_failed'),
    (AcquisitionError('local_job_boundary_unavailable'), 'local_job_boundary_unavailable'),
])
def test_parent_receives_assignment_failure_and_can_repair_without_an_extra_observation(
        tmp_path, monkeypatch, failure, code):
    store, tools, query, scope, jobs, binding = prepared(tmp_path)
    original = jobs.check_handoff
    selected = []
    def monitor(context):
        form = context['child_reports'][-1]
        selected.append(commission(binding, 'job_monitor', scope, handoff=form['job_handoff']))
        def unavailable(handoff):
            raise failure
        monkeypatch.setattr(jobs, 'check_handoff', unavailable)
        return selected[0]
    def repair(context):
        assert context['feedback']['category'] == 'job_assignment'
        assert context['feedback']['code'] == code
        assert context['feedback']['job_ref'] == selected[0]['selection']['handoff']['job_ref']
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 6
        # External receiving availability changed; this is not an unchanged retry.
        monkeypatch.setattr(jobs, 'check_handoff', original)
        return selected[0]
    try:
        result = run(store, tools, Provider([
            commission(binding, 'job_launch', scope, query_ref=query), *launch_actions(),
            monitor, repair, action('homology.sample')]), binding, tmp_path/'run',
            counts={'annotation': 2, 'job_launch': 5, 'job_monitor': 1})
        assert result['completed_actions'] == 2
        assert store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 3
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 8
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
    finally:
        cleanup(jobs, store)


def test_registry_loss_after_sample_keeps_exact_sample_forecast_and_assigned_identity(tmp_path, monkeypatch):
    store, tools, query, scope, jobs, binding = prepared(tmp_path, statistics=True,
        monitoring_credit=MonitoringInformationCredit(information_unit=1))
    expectations = ExecutionExpectations.for_homology(jobs, binding.statistics, roles=binding.roles)
    original = jobs.sample
    samples = []
    def sample(handoff, **kwargs):
        value = original(handoff, **kwargs)
        samples.append(value)
        jobs.db.close()  # Actual later registry loss, after successful sampling.
        return value
    monkeypatch.setattr(jobs, 'sample', sample)
    assignments = []
    def monitor(context):
        handoff = context['child_reports'][-1]['job_handoff']
        selected = commission(binding, 'job_monitor', scope, handoff=handoff, with_execution=True)
        schema = json.loads(selected['selection']['schema_json'])
        for key in ('job_ref', 'job_cpu', 'job_handoff_state', 'job_handoff_failure'):
            schema['properties'][key] = binding.fact_sources('job_monitor')[key]['report_schema']
            schema['required'].append(key)
        selected['selection']['schema_json'] = json.dumps(schema)
        assignments.append({'job_ref': handoff['job_ref'], 'query_ref': query, 'cpu': 1})
        return selected
    try:
        result = run(store, tools, Provider([
            commission(binding, 'job_launch', scope, query_ref=query), *launch_actions(),
            monitor, action('homology.sample')]), binding, tmp_path/'run',
            counts={'annotation': 2, 'job_launch': 5, 'job_monitor': 1},
            expectations=expectations, resource_estimator=ResourceToolEstimator())
        assert result['completed_actions'] == 2
        forms = [json.loads(row[0]) for row in store.db.execute(
            'SELECT form FROM runtime_report_attempts ORDER BY decision_index')]
        form = forms[-1]
        assert form['sample'] == samples[0]
        assert form['job_ref'] == samples[0]['job_ref']
        assert form['job_cpu'] == 1
        assert form['job_handoff_state'] == 'unavailable'
        assert form['job_handoff_failure'] == 'receiving_interface_unavailable'
        assert form['execution_forecasts'][0]['job_ref'] == samples[0]['job_ref']
        assert binding.resolve(store, scope, samples[0]['sample_ref'], 'job_sample', assignment=assignments[0])
        assert not binding.resolve(store, scope, 'homology_job_invented', 'homology_job', assignment=assignments[0])
        changed = deepcopy(form)
        changed['sample']['elapsed_seconds'] = (samples[0]['elapsed_seconds'] or 0) + 10
        with pytest.raises(ReportBoundaryError, match='Native sample fields'):
            binding.validate_report(changed, assignments[0], store=store)
        changed = deepcopy(form)
        changed['execution_forecasts'][0]['expected_total_seconds'] = 0
        with pytest.raises(ReportBoundaryError):
            binding.validate_report(changed, assignments[0], store=store)
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 8
        exported = json.loads(store.db.execute("SELECT json_extract(result,'$.execution_statistics_export') "
            "FROM runtime_actions WHERE json_extract(action,'$.tool')='homology.sample'").fetchone()[0])
        assert exported[0]['code'] == 'statistics_registry_unavailable'
    finally:
        cleanup(jobs, store)


def test_control_timeout_is_actionable_tool_feedback(tmp_path, monkeypatch):
    import asyncio
    store, tools, query, scope, jobs, binding = prepared(tmp_path)
    assignment = binding.assign(store, 'job_launch', {'query_ref': query, 'cpu': 1}, scope, operation_key='fixture')
    source = SimpleNamespace(request=SimpleNamespace(message=Record({'job_assignment': assignment})),
        path=(('job_launch', 'fixture'),))
    def unavailable(job_ref):
        raise subprocess.TimeoutExpired(['systemctl'], 5)
    monkeypatch.setattr(jobs, 'environment', unavailable)
    try:
        result = asyncio.run(binding.execute(source, 'homology.environment', {}, operation_key='selected'))
        assert result['status'] == 'failed'
        assert result['feedback']['code'] == 'job_control_failed'
        assert result['feedback']['job_ref'] == assignment['job_ref']
        assert jobs.db.execute('SELECT sum(submission_requested) FROM orders').fetchone()[0] == 0
    finally:
        cleanup(jobs, store)
