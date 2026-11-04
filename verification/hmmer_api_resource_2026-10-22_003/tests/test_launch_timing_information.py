"""Timing discovered during launch remains monitoring information.

Actual tiny native job, explicit fixture decisions/continuation and units. No
biological claim, configured-model verification or new stopping rule is implied.
"""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, validate_form
from gene_annotation_episode.execution_expectations import ExecutionExpectations
from gene_annotation_episode.investigation_policy import JobEvidenceCredit
from gene_annotation_episode.monitoring_credit import MonitoringInformationCredit
from gene_annotation_episode.native_lifecycle import cancel
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.run_statistics import RunHistory
from gene_annotation_episode.runtime import Journal
from test_homology_episode_runtime import Provider, action, commission, prepared, run
from test_homology_jobs import wait_terminal
from test_resource_monitoring_separation import sample
from test_runtime import obj, setup


def journal_check(store, checked, index, *, episode='launch'):
    Journal(store, 'run_fixture').save('runtime_actions', {'episode_id': episode,
        'decision_index': index, 'action': json.dumps({'kind': 'tool', 'tool': 'homology.check_handoff'}),
        'result': json.dumps({'status': 'completed', 'result': {
            'checked_at_unix_seconds': checked['checked_at_unix_seconds'],
            'sample': {key: value for key, value in checked.items() if key != 'checked_at_unix_seconds'}}}),
        'credit': None})


def test_selected_checks_earn_information_once_without_fabricating_samples_or_role_ownership(tmp_path):
    store, _ = setup(tmp_path)
    projector = MonitoringInformationCredit(information_unit=7, include_handoff_checks=True)
    pending = sample(0, None, state='returned')
    pending.update(outcome='succeeded', native_returncode=0, duration_measure='systemd_service_wall_seconds')
    for key in ('sample_ref', 'sampled_at_unix_seconds'):
        pending.pop(key)
    pending['checked_at_unix_seconds'] = 100
    completed = {**pending, 'checked_at_unix_seconds': 101, 'elapsed_seconds': 5}
    assignment = {'job_ref': pending['job_ref'], 'prior_checked_statuses': [pending]}
    journal_check(store, completed, 0)
    journal_check(store, {**completed, 'checked_at_unix_seconds': 102}, 1)
    for role in ('job_launch', 'job_monitor', 'job_results'):
        assert projector(store, role=role, assignment=assignment,
            episode_id='launch', run_id='run_fixture') == 7
    findings = projector.findings(store, assignment=assignment, episode_id='launch', run_id='run_fixture')
    finding, = findings
    assert finding['new_completed_timing'] is True
    assert finding['new_state'] is finding['new_outcome'] is False
    assert finding['sample']['observation_kind'] == 'handoff_check'
    assert finding['sample']['checked_at_unix_seconds'] == 101
    assert finding['sample']['sample_ref'] is finding['sample']['sampled_at_unix_seconds'] is None
    assert finding['new_output_states'] == finding['new_timing_overruns'] == []
    validate_form({'information': findings},
        obj({'information': projector.information_report_source()['report_schema']}), lambda *_: True)
    # A later child inherits the actually received result and cannot rediscover
    # it simply because it has another episode identity or role.
    journal_check(store, {**completed, 'checked_at_unix_seconds': 103}, 0, episode='later')
    assert projector(store, role='job_results', assignment={**assignment,
        'prior_checked_statuses': [completed]}, episode_id='later', run_id='run_fixture') == 0
    assert store.db.execute("SELECT count(*) FROM sqlite_master WHERE name='samples'").fetchone()[0] == 0
    assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
    store.db.close()


def test_actual_launch_timing_reaches_parent_and_history_without_combining_controller_scores(tmp_path):
    monitoring = MonitoringInformationCredit(information_unit=7, include_handoff_checks=True)
    store, tools, query, scope, jobs, binding = prepared(tmp_path, statistics=True,
                                                       monitoring_credit=monitoring)
    # Explicit unequal fixture units expose an accidental sum or replacement.
    operational = JobEvidenceCredit(jobs.config['registry_ref'], handoff_unit=3, acquired_record_unit=1)
    binding.project_credit, binding.credit_binding = operational, operational.as_record()
    expectations = ExecutionExpectations.for_homology(jobs, binding.statistics,
        roles=binding.roles, planning_roles=('annotation', 'improvement'))
    received = []
    def request_launch(context):
        assert context['current_credit'] == 0
        selected = commission(binding, 'job_launch', scope, query_ref=query)
        schema = json.loads(selected['selection']['schema_json'])
        for name in ('job_checked_status', 'monitoring_findings', 'monitoring_information_credit'):
            schema['properties'][name] = binding.fact_sources('job_launch')[name]['report_schema']
            schema['required'].append(name)
        selected['selection']['schema_json'] = json.dumps(schema)
        return selected
    def completed_check(context):
        assert context['monitoring_information_credit'] == 0
        assert context['current_credit'] == 0
        wait_terminal(jobs, context['working_state']['assignment']['job_ref'])
        return action('homology.check_handoff')
    def request_repair(context):
        report, = context['child_reports']
        received.append(report)
        assert report['local_credit'] == 3
        assert report['monitoring_information_credit'] == 7
        finding, = report['monitoring_findings']
        assert finding['new_completed_timing'] is True
        assert finding['sample']['observation_kind'] == 'handoff_check'
        assert finding['sample']['sample_ref'] is None
        checked = report['job_checked_status']
        assert finding['sample']['elapsed_seconds'] == checked['elapsed_seconds'] > 0
        assert jobs.db.execute('SELECT count(*) FROM samples').fetchone()[0] == 0
        estimate, = context['resource_tool_estimates']
        assert estimate['expected_total_seconds'] == pytest.approx(checked['elapsed_seconds'])
        assert estimate['successful_duration_samples'] == 1
        assert context['current_credit'] == 0
        # The communication check binds a native checked result to its actual
        # selected values, rather than treating job identity as sufficient.
        schema = {'type': 'object', 'properties': {
            'information': monitoring.information_report_source()['report_schema']},
            'required': ['information'], 'additionalProperties': False}
        assignment = {'job_ref': checked['job_ref']}
        binding.validate_report({'information': report['monitoring_findings']}, assignment,
                                store=store, schema=schema)
        forged = deepcopy(report['monitoring_findings'])
        forged[0]['sample']['elapsed_seconds'] += 1
        with pytest.raises(ReportBoundaryError, match='selected recorded work'):
            binding.validate_report({'information': forged}, assignment, store=store, schema=schema)
        described_schema = deepcopy(schema)
        described_schema['properties']['information']['items']['properties']['sample']['properties']['elapsed_seconds']['description'] = 'Actual measured duration'
        described_schema['properties']['information']['items']['properties']['sample']['properties']['outputs']['items']['properties']['bytes']['description'] = 'Recorded output size'
        with pytest.raises(ReportBoundaryError, match='selected recorded work'):
            binding.validate_report({'information': forged}, assignment, store=store, schema=described_schema)
        reordered_schema = deepcopy(described_schema)
        native = reordered_schema['properties']['information']['items']['properties']['sample']
        native['required'].reverse()
        native['properties']['observation_kind']['enum'].reverse()
        native['properties']['sample_ref']['type'].reverse()
        native['properties']['elapsed_seconds']['type'].reverse()
        narrowed_schema = deepcopy(reordered_schema)
        narrowed = narrowed_schema['properties']['information']['items']['properties']['sample']['properties']
        narrowed['observation_kind']['enum'] = ['handoff_check']
        narrowed['elapsed_seconds']['minimum'] = checked['elapsed_seconds']/2
        constant_schema = deepcopy(narrowed_schema)
        kind_field = constant_schema['properties']['information']['items']['properties']['sample']['properties']['observation_kind']
        kind_field.pop('enum')
        kind_field['const'] = 'handoff_check'
        for supplied_schema in (reordered_schema, narrowed_schema, constant_schema):
            validate_form({'information': forged}, supplied_schema, lambda *_: True)
            with pytest.raises(ReportBoundaryError, match='selected recorded work'):
                binding.validate_report({'information': forged}, assignment, store=store, schema=supplied_schema)
        # Same field names do not reserve a parent's declared semantic types.
        alternate_schema = deepcopy(schema['properties']['information']['items']['properties']['sample'])
        alternate = deepcopy(finding['sample'])
        for name in ('job_ref', 'registry_ref', 'sample_ref'):
            alternate_schema['properties'][name] = {'type': 'string', 'format': 'reference',
                                                   'x-reference-namespace': 'subject'}
            alternate[name] = query
        alternate['elapsed_seconds'] += 1
        validate_form({'parent_fields': alternate}, obj({'parent_fields': alternate_schema}), lambda *_: True)
        binding.validate_report({'parent_fields': alternate}, assignment, store=store,
                                schema=obj({'parent_fields': alternate_schema}))
        selected = commission(binding, 'job_launch', scope, existing_job_ref=checked['job_ref'])
        selected['selection']['prior_checked_statuses'] = [checked]
        selected['selection']['prior_sample_refs'] = []
        repair_schema = json.loads(selected['selection']['schema_json'])
        for name in ('job_checked_status', 'monitoring_findings', 'monitoring_information_credit'):
            repair_schema['properties'][name] = binding.fact_sources('job_launch')[name]['report_schema']
            repair_schema['required'].append(name)
        selected['selection']['schema_json'] = json.dumps(repair_schema)
        malformed = deepcopy(selected['selection'])
        malformed['prior_checked_statuses'][0]['elapsed_seconds'] += 1
        with pytest.raises(ValueError, match='prior_checked_status_must_match_recorded_assigned_job_check'):
            binding.assign(store, 'job_launch', malformed, scope, operation_key='invalid_repair')
        return selected
    def repaired_check(context):
        assert context['monitoring_information_credit'] == 0
        assert context['working_state']['assignment']['prior_checked_statuses'] == [received[0]['job_checked_status']]
        return action('homology.check_handoff')
    def request_monitor(context):
        report = context['child_reports'][-1]
        assert report['local_credit'] == 3
        assert report['monitoring_information_credit'] == 0
        assert report['monitoring_findings'] == []
        assert report['job_ref'] == received[0]['job_ref']
        selected = commission(binding, 'job_monitor', scope, handoff=report['job_handoff'],
                              with_execution=True)
        selected['selection']['prior_checked_statuses'] = [report['job_checked_status']]
        return selected
    def use_result(context):
        report = context['child_reports'][-1]
        assert report['information'] == [] and report['local_credit'] == 0
        assert context['current_credit'] == 0
        # The same production assignment path accepts already-known samples
        # for a later launch repair or acquisition, with exact job ownership.
        for role in ('job_launch', 'job_results'):
            operands = ({'existing_job_ref': report['sample']['job_ref']} if role == 'job_launch'
                        else {'handoff': received[0]['job_handoff']})
            assignment = binding.assign(store, role, {**operands,
                'prior_sample_refs': [report['sample']['sample_ref']],
                'prior_checked_statuses': [received[0]['job_checked_status']]}, scope,
                operation_key='known_sample_'+role)
            assert assignment['prior_samples'] == [report['sample']]
            assert assignment['prior_checked_statuses'] == [received[0]['job_checked_status']]
        return action('episode.history', {'view': 'index', 'offset': 0, 'limit': 5})
    provider = Provider([request_launch, action('homology.environment'), action('homology.configure'),
        action('homology.stage'), action('homology.submit'), completed_check, request_repair,
        action('homology.environment'), action('homology.configure'), action('homology.stage'),
        action('homology.submit'), repaired_check, request_monitor,
        action('homology.sample'), action('homology.sample'), use_result])
    try:
        summary = run(store, tools, provider, binding, tmp_path/'run',
            counts={'annotation': 4, 'job_launch': 5, 'job_monitor': 2},
            expectations=expectations, resource_estimator=ResourceToolEstimator())
        assert summary['credit'] == 0 and summary['completed_actions'] == 4
        assert store.count('annotation') == store.count('assessment') == 0
        observations = [json.loads(row[0]) for row in store.db.execute(
            'SELECT observation FROM runtime_observations ORDER BY rowid')]
        launch = [row for row in observations if row['label'] == 'tool:4']
        assert len(launch) == 2 and all(row['credit']['credit'] == 3 for row in launch)
        assert len(observations) == 16  # Four parent, ten launch/repair, two monitor.
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
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
