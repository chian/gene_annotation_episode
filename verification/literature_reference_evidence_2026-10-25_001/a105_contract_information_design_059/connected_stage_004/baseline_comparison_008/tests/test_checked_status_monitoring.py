"""Known launch facts pass through the parent, without becoming new samples."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from gene_annotation_episode.execution_expectations import ExecutionExpectations
from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.homology_episodes import CHECKED_STATUS_SCHEMA
from gene_annotation_episode.monitoring_credit import MonitoringInformationCredit
from gene_annotation_episode.native_lifecycle import cancel
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.run_statistics import RunHistory
from gene_annotation_episode.runtime import Journal
from test_homology_episode_runtime import Provider, action, commission, prepared, run
from test_homology_jobs import wait_terminal
from test_resource_monitoring_separation import journal_sample, sample
from test_runtime import setup
from test_runtime_expectations import append, make_history


def test_parent_supplies_launch_status_then_monitor_gets_credit_only_for_new_completion(tmp_path):
    store, tools, query, scope, jobs, binding = prepared(tmp_path, gated=True, statistics=True,
        monitoring_credit=MonitoringInformationCredit(information_unit=1))
    expectations = ExecutionExpectations.for_homology(jobs, binding.statistics,
        roles=binding.roles, planning_roles=('annotation',))
    selected = commission(binding, 'job_launch', scope, query_ref=query)
    schema = json.loads(selected['selection']['schema_json'])
    schema['properties']['checked_execution'] = binding.fact_sources('job_launch')['job_checked_status']['report_schema']
    schema['required'].append('checked_execution')
    selected['selection']['schema_json'] = json.dumps(schema)
    known = []

    def monitor(context):
        report = context['child_reports'][-1]
        known.append(deepcopy(report['checked_execution']))
        assert known[0]['state'] == 'running'
        chosen = commission(binding, 'job_monitor', scope, handoff=report['job_handoff'],
            with_execution=True)
        chosen['selection']['prior_checked_statuses'] = known
        return chosen

    def complete_job(context):
        assert context['current_credit'] == 0
        assignment = context['working_state']['assignment']
        assert assignment['prior_checked_statuses'] == known
        assert assignment['prior_samples'] == []
        first = context['last_local_outcome']['result']
        assert first['state'] == known[0]['state']
        assert first['outcome'] == known[0]['outcome']
        (jobs._directory(first['job_ref'])/'permit-native').touch()
        wait_terminal(jobs, first['job_ref'])
        return action('homology.sample')

    def use_returned(context):
        report = context['child_reports'][-1]
        assert report['local_credit'] == 1
        assert len(report['information']) == 1
        assert report['information'][0]['new_completed_timing'] is True
        assert report['sample']['outcome'] == 'succeeded'
        return action('episode.history', {'view': 'index', 'offset': 0, 'limit': 5})

    provider = Provider([selected, action('homology.environment'), action('homology.configure'),
        action('homology.stage'), action('homology.submit'), action('homology.check_handoff'),
        monitor, action('homology.sample'), complete_job, use_returned])
    try:
        counts = {'annotation': 3, 'job_launch': 5, 'job_monitor': 2}
        summary = run(store, tools, provider, binding, tmp_path/'run', counts=counts,
            expectations=expectations, resource_estimator=ResourceToolEstimator())
        assert summary['credit'] == 0
        assert store.count('assessment') == store.count('annotation') == 0
        assert jobs.db.execute('SELECT count(*) FROM samples').fetchone()[0] == 2
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 10
        monitoring = [context for context in provider.contexts
            if context['working_state'].get('role') == 'job_monitor']
        assert [context['current_credit'] for context in monitoring] == [0, 0]
        # Checked status is known execution information, not a sample identity
        # silently inserted into the forecaster's measured-sample interface.
        assert monitoring[0]['resource_tool_estimates'][0]['sample_ref'] is None
        saved_observations = store.db.execute('SELECT * FROM runtime_observations').fetchall()
        assert run(store, tools, Provider([]), binding, resume=True, counts=counts,
            expectations=expectations, resource_estimator=ResourceToolEstimator()) == summary
        assert store.db.execute('SELECT * FROM runtime_observations').fetchall() == saved_observations
        assert jobs.db.execute('SELECT count(*) FROM samples').fetchone()[0] == 2
        history = RunHistory(binding.statistics.history_path, create=False)
        try:
            assert history.db.execute('SELECT count(*) FROM run_statistics').fetchone()[0] == 1
        finally:
            history.close()
    finally:
        for row in jobs.db.execute('SELECT job_ref FROM orders'):
            handle = jobs._handle(row[0])
            if handle.path.exists():
                cancel(handle)
        jobs.close()
        store.close()


def test_monitor_assignment_requires_exact_selected_check_and_preserves_omitted_input(tmp_path, monkeypatch):
    store, tools, query, scope, jobs, binding = prepared(tmp_path)
    Journal(store, 'check_run')
    job = binding.assign(store, 'job_launch', {'query_ref': query, 'cpu': 1}, scope,
        operation_key='launch')['job_ref']
    # Synthetic status fixture isolates admission; no native job or model call.
    current = sample(0, 3)
    current.update(job_ref=job, registry_ref=jobs.config['registry_ref'],
        duration_measure='systemd_service_wall_seconds')
    checked = {key: deepcopy(current[key]) for key in CHECKED_STATUS_SCHEMA['properties']
        if key != 'checked_at_unix_seconds'}
    checked['checked_at_unix_seconds'] = 100
    monkeypatch.setattr(jobs, 'check_handoff', lambda _: None)
    selection = {'handoff': {'job_ref': job}, 'prior_sample_refs': []}
    try:
        old_assignment = binding.assign(store, 'job_monitor', selection, scope, operation_key='monitor')
        assert 'prior_checked_statuses' not in old_assignment
        selected = {**selection, 'prior_checked_statuses': [checked]}
        with pytest.raises(ValueError, match='prior_checked_status_must_match'):
            binding.assign(store, 'job_monitor', selected, scope, operation_key='monitor')
        Journal(store, 'check_run').save('runtime_actions', {'episode_id': 'launch', 'decision_index': 0,
            'action': json.dumps({'kind': 'tool', 'tool': 'homology.check_handoff', 'arguments': {}}),
            'result': json.dumps({'status': 'completed', 'result': {
                'checked_at_unix_seconds': 100,
                'sample': {key: value for key, value in checked.items() if key != 'checked_at_unix_seconds'}}}),
            'credit': None})
        assignment = binding.assign(store, 'job_monitor', selected, scope, operation_key='monitor')
        assert assignment['prior_checked_statuses'] == [checked]
        assert assignment['prior_samples'] == []
        for field, value in [('elapsed_seconds', 4), ('checked_at_unix_seconds', 101),
                ('job_ref', 'another_job'), ('registry_ref', 'another_registry')]:
            forged = {**selection, 'prior_checked_statuses': [{**checked, field: value}]}
            with pytest.raises(ValueError, match='prior_checked_status_must_match'):
                binding.assign(store, 'job_monitor', forged, scope, operation_key='monitor')
        assert binding.assign(store, 'job_monitor', selection, scope, operation_key='monitor') == old_assignment
        assert jobs.db.execute('SELECT count(*) FROM samples').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
    finally:
        jobs.close()
        store.close()


def test_known_checked_completion_and_elapsed_do_not_earn_duplicate_information(tmp_path):
    store, _ = setup(tmp_path)
    projector = MonitoringInformationCredit(information_unit=1)
    prior = sample(0, 5, state='returned')
    prior.update(outcome='succeeded', native_returncode=0,
        duration_measure='systemd_service_wall_seconds')
    checked = {key: value for key, value in prior.items()
        if key not in {'sample_ref', 'sampled_at_unix_seconds'}}
    checked['checked_at_unix_seconds'] = 100
    validate_form(checked, CHECKED_STATUS_SCHEMA, lambda *_: True)
    assignment = {'job_ref': prior['job_ref'], 'prior_checked_statuses': [checked]}
    try:
        journal_sample(store, {**prior, 'sample_ref': 'later_sample'}, [], 0)
        assert projector.findings(store, assignment=assignment, episode_id='monitor', run_id='run_fixture') == []
        assert projector(store, role='job_monitor', assignment=assignment,
            episode_id='monitor', run_id='run_fixture') == 0
    finally:
        store.db.close()


def test_checked_elapsed_already_past_frozen_benchmark_is_not_a_new_overrun(tmp_path):
    history_path = tmp_path/'history.sqlite'
    original = make_history(history_path)
    scope = replace(original, duration_measure='systemd_service_wall_seconds')
    append(history_path, scope, 'systemd_fixture_attempt', 2)
    context = ExecutionExpectations(history_path, by_grain={'job_monitor': [scope]}).capture('job_monitor')
    store, _ = setup(tmp_path)
    projector = MonitoringInformationCredit(information_unit=1)
    prior = sample(0, 3)
    prior['duration_measure'] = 'systemd_service_wall_seconds'
    checked = {key: value for key, value in prior.items()
        if key not in {'sample_ref', 'sampled_at_unix_seconds'}}
    checked['checked_at_unix_seconds'] = 100
    validate_form(checked, CHECKED_STATUS_SCHEMA, lambda *_: True)
    assignment = {'job_ref': prior['job_ref'], 'prior_checked_statuses': [checked]}
    current = sample(1, 4)
    current['duration_measure'] = 'systemd_service_wall_seconds'
    forecasts = ResourceToolEstimator().estimate(context, job_ref=prior['job_ref'], sample=current)
    assert forecasts[0]['timing_relation'] == 'exceeds_observed_maximum'
    assert forecasts[0]['observed_max_seconds'] == 2
    try:
        journal_sample(store, current, forecasts, 0)
        assert projector.findings(store, assignment=assignment, episode_id='monitor', run_id='run_fixture') == []
        assert projector(store, role='job_monitor', assignment=assignment,
            episode_id='monitor', run_id='run_fixture') == 0
    finally:
        store.db.close()
