"""Actual tiny native job; scripted choices, fixture controllers and units."""
import asyncio
import json
import sqlite3
import pytest

from gene_annotation_episode.execution_expectations import ExecutionExpectations
from gene_annotation_episode.native_timing_information import NativeTimingInformation, read_measurement
from gene_annotation_episode.monitoring_credit import MonitoringInformationCredit
from gene_annotation_episode.native_lifecycle import cancel
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.runtime import run_workflow
from test_homology_episode_runtime import Provider, action, commission, prepared, fixture_task_credit
from test_homology_jobs import wait_terminal
from test_runtime import FixtureController


UNIT = 7  # Engineering fixture, not a production weight or continuation rule.


def execute(store, tools, provider, binding, jobs, directory, counts, *, resume=False):
    expectations = (ExecutionExpectations.for_homology(jobs, binding.statistics,
        roles=binding.roles, planning_roles=('annotation',)) if binding.statistics is not None else None)
    return asyncio.run(run_workflow(store, tools, provider=provider, run_dir=directory, resume=resume,
        controller_factory=lambda path, initial: FixtureController(str(path), initial, counts[path[-1][0]]),
        project_credit=fixture_task_credit, job_episodes=binding, initial_known_record_refs=[],
        native_timing_information=NativeTimingInformation(UNIT), resource_estimator=ResourceToolEstimator(),
        execution_expectations=expectations))


def test_returned_checked_duration_and_sample_are_one_parent_timing_contribution(tmp_path):
    store, tools, query, scope, jobs, binding = prepared(tmp_path, gated=True, statistics=True,
        monitoring_credit=MonitoringInformationCredit(information_unit=UNIT, include_handoff_checks=True))
    known, durations = [], []
    selected = commission(binding, 'job_launch', scope, query_ref=query)
    form = json.loads(selected['selection']['schema_json'])
    for name, source in [('latest_launch_status', 'job_checked_status'),
                         ('child_information', 'monitoring_information_credit')]:
        form['properties'][name] = binding.fact_sources('job_launch')[source]['report_schema']
        form['required'].append(name)
    selected['selection']['schema_json'] = json.dumps(form)

    def finish_before_check(context):
        job = context['working_state']['assignment']['job_ref']
        (jobs._directory(job)/'permit-native').touch()
        wait_terminal(jobs, job)
        return action('homology.check_handoff')

    def parent_receives_duration(context):
        returned, = context['child_reports']
        known.append(returned['latest_launch_status'])
        durations.append(known[0]['elapsed_seconds'])
        assert durations[0] > 0 and returned['child_information'] == UNIT
        assert returned['local_credit'] == 5  # Explicit fixture operational score.
        assert context['current_credit'] == 0
        assert context['monitoring_information_credit'] == UNIT
        chosen = commission(binding, 'job_monitor', scope, handoff=returned['job_handoff'],
                            with_execution=True)
        chosen['selection']['prior_checked_statuses'] = known
        return chosen

    def parent_receives_same_duration_in_sample(context):
        returned = context['child_reports'][-1]
        assert returned['sample']['elapsed_seconds'] == durations[0]
        assert returned['local_credit'] == 0 and returned['information'] == []
        assert context['current_credit'] == 0
        assert context['monitoring_information_credit'] == UNIT
        return action('episode.monitoring_information', {'offset': 0, 'limit': 5})

    provider = Provider([selected, action('homology.environment'), action('homology.configure'),
        action('homology.stage'), action('homology.submit'), finish_before_check,
        parent_receives_duration, action('homology.sample'), action('homology.sample'),
        parent_receives_same_duration_in_sample])
    counts = {'annotation': 3, 'job_launch': 5, 'job_monitor': 2}
    def run(provider, *, resume=False):
        return execute(store, tools, provider, binding, jobs, tmp_path/'run', counts, resume=resume)
    try:
        summary = run(provider)
        assert summary['credit'] == 0 and summary['monitoring_information_credit'] == UNIT
        assert summary['completed_actions'] == 3
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 10
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
        assert store.count('native_execution') == 1
        record = store.list('native_execution')[0]
        measured = read_measurement(store, record['id'])
        assert record['operation'] == 'phmmer_search'
        assert measured.statistic.elapsed_seconds == durations[0]
        assert record['operands'] == [{'role': 'query', 'subject_ref': query}]
        with sqlite3.connect(binding.statistics.history_path) as db:
            before_statistics = db.execute('SELECT * FROM run_statistics').fetchall()
            assert len(before_statistics) == 1
        before_actions = store.db.execute('SELECT * FROM runtime_actions').fetchall()
        before_observations = store.db.execute('SELECT * FROM runtime_observations').fetchall()
        assert run(Provider([]), resume=True) == summary
        assert store.db.execute('SELECT * FROM runtime_actions').fetchall() == before_actions
        assert store.db.execute('SELECT * FROM runtime_observations').fetchall() == before_observations
        with sqlite3.connect(binding.statistics.history_path) as db:
            assert db.execute('SELECT * FROM run_statistics').fetchall() == before_statistics
    finally:
        for row in jobs.db.execute('SELECT job_ref FROM orders'):
            handle = jobs._handle(row[0])
            if handle.path.exists():
                cancel(handle)
        jobs.close()
        store.close()


@pytest.mark.parametrize('fact,statistics,history_available', [
    (None, True, True), ('monitoring_findings', True, True),
    ('job_checked_status', False, True), ('job_checked_status', True, False)])
def test_only_requested_timing_crosses_and_missing_provenance_does_not_reject_form(
        tmp_path, fact, statistics, history_available):
    store, tools, query, scope, jobs, binding = prepared(tmp_path, gated=True, statistics=statistics,
        monitoring_credit=MonitoringInformationCredit(information_unit=UNIT, include_handoff_checks=True))
    if statistics and not history_available:
        binding.statistics.history_path.unlink()
    selected = commission(binding, 'job_launch', scope, query_ref=query)
    form = json.loads(selected['selection']['schema_json'])
    fields = {'child_information': 'monitoring_information_credit'}
    if fact:
        fields['requested_execution_information'] = fact
    for name, source in fields.items():
        form['properties'][name] = binding.fact_sources('job_launch')[source]['report_schema']
        form['required'].append(name)
    selected['selection']['schema_json'] = json.dumps(form)
    expected = UNIT if fact and statistics else 0

    def completed_check(context):
        job = context['working_state']['assignment']['job_ref']
        (jobs._directory(job)/'permit-native').touch()
        wait_terminal(jobs, job)
        return action('homology.check_handoff')

    def parent(context):
        returned, = context['child_reports']
        assert returned['child_information'] == UNIT
        assert context['monitoring_information_credit'] == expected
        assert context['current_credit'] == 0
        delivery, = context['report_deliveries']
        assert delivery['status'] == 'delivered'
        if fact and not statistics:
            issue, = delivery['timing_receipt_issues']
            assert issue['source'] == fact and issue['code'] == 'measurement_not_recorded'
            assert issue['field'] == ['requested_execution_information']
        else:
            assert 'timing_receipt_issues' not in delivery
        return action('episode.monitoring_information', {'offset': 0, 'limit': 5})

    provider = Provider([selected, action('homology.environment'), action('homology.configure'),
        action('homology.stage'), action('homology.submit'), completed_check, parent])
    try:
        summary = execute(store, tools, provider, binding, jobs, tmp_path/'run',
            {'annotation': 2, 'job_launch': 5})
        assert summary['credit'] == 0 and summary['monitoring_information_credit'] == expected
        assert summary['pending_report_deliveries'] == 0
        assert store.count('native_execution') == int(expected > 0)
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 7
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
        if statistics and not history_available:
            assert not binding.statistics.history_path.exists()
    finally:
        for row in jobs.db.execute('SELECT job_ref FROM orders'):
            handle = jobs._handle(row[0])
            if handle.path.exists():
                cancel(handle)
        jobs.close()
        store.close()


@pytest.mark.parametrize('interrupt_before_redelivery', [False, True])
def test_timing_form_redelivery_and_interruption_preserve_one_receipt_and_original_observations(
        tmp_path, interrupt_before_redelivery):
    store, tools, query, scope, jobs, binding = prepared(tmp_path, gated=True, statistics=True,
        monitoring_credit=MonitoringInformationCredit(information_unit=UNIT, include_handoff_checks=True))
    selected = commission(binding, 'job_launch', scope, query_ref=query)
    form = json.loads(selected['selection']['schema_json'])
    form['properties']['duration_status'] = binding.fact_sources('job_launch')['job_checked_status']['report_schema']
    form['required'].append('duration_status')
    selected['selection']['schema_json'] = json.dumps(form)
    counts = {'annotation': 2, 'job_launch': 5}

    def completed_check(context):
        job = context['working_state']['assignment']['job_ref']
        (jobs._directory(job)/'permit-native').touch()
        wait_terminal(jobs, job)
        return action('homology.check_handoff')

    def redeliver(context):
        assert context['monitoring_information_credit'] == UNIT
        assert context['controller']['scores'] == [0]
        return {'selection': {'kind': 'redeliver_report',
            'delivery_ref': context['report_deliveries'][0]['delivery_ref'],
            'purpose': 'Read the same requested measured status again.',
            'schema_json': json.dumps(form)}, 'report_update': {}}

    def after_redelivery(context):
        assert context['monitoring_information_credit'] == UNIT
        assert context['controller']['scores'] == [0]
        return action('episode.monitoring_information', {'offset': 0, 'limit': 5})

    prefix = [selected, action('homology.environment'), action('homology.configure'),
              action('homology.stage'), action('homology.submit'), completed_check]
    try:
        before_actions, before_observations = [], []
        if interrupt_before_redelivery:
            with pytest.raises(asyncio.CancelledError):
                execute(store, tools, Provider(prefix+[asyncio.CancelledError()]), binding, jobs,
                    tmp_path/'run', counts)
            before_actions = store.db.execute('SELECT * FROM runtime_actions ORDER BY rowid').fetchall()
            before_observations = store.db.execute('SELECT * FROM runtime_observations ORDER BY rowid').fetchall()
            summary = execute(store, tools, Provider([redeliver, after_redelivery]), binding, jobs,
                tmp_path/'run', counts, resume=True)
        else:
            summary = execute(store, tools, Provider(prefix+[redeliver, after_redelivery]), binding, jobs,
                tmp_path/'run', counts)
        assert summary['credit'] == 0 and summary['monitoring_information_credit'] == UNIT
        assert summary['completed_actions'] == 2 and summary['pending_report_deliveries'] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 7
        assert store.count('native_execution') == 1
        projections = [json.loads(row[0]) for row in store.db.execute(
            'SELECT timing_receipts FROM runtime_report_attempts ORDER BY decision_index')]
        assert len(projections) == 2 and projections[0] == projections[1]
        assert projections[0]['issues'] == [] and len(projections[0]['native_execution_refs']) == 1
        if before_actions:
            assert store.db.execute('SELECT * FROM runtime_actions ORDER BY rowid LIMIT ?',
                (len(before_actions),)).fetchall() == before_actions
            assert store.db.execute('SELECT * FROM runtime_observations ORDER BY rowid LIMIT ?',
                (len(before_observations),)).fetchall() == before_observations
        with sqlite3.connect(binding.statistics.history_path) as db:
            assert db.execute('SELECT count(*) FROM run_statistics').fetchone()[0] == 1
    finally:
        for row in jobs.db.execute('SELECT job_ref FROM orders'):
            handle = jobs._handle(row[0])
            if handle.path.exists():
                cancel(handle)
        jobs.close()
        store.close()
