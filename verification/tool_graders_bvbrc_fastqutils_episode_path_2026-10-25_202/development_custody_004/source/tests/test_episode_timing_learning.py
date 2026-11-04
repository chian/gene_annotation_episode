"""Timing information through real episode boundaries, with fixture decisions.

The native test uses one real phmmer query/reference. Scripted action choices,
test controller lengths and information_unit=1 are explicit engineering fixtures,
not a production scientific score, scheduling policy or model investigation.
"""
import json

import pytest

from gene_annotation_episode.execution_expectations import ExecutionExpectations
from gene_annotation_episode.monitoring_credit import MonitoringInformationCredit
from gene_annotation_episode.native_lifecycle import cancel
from gene_annotation_episode.numerical import NumericBand, YieldEstimate
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.run_statistics import RunHistory
from test_homology_episode_runtime import Provider, action, commission, prepared, run
from test_homology_jobs import wait_terminal
from test_resource_monitoring_separation import journal_sample, sample
from test_runtime import setup


@pytest.mark.parametrize('outcome,returncode', [('succeeded', 0), ('failed', 1)])
def test_learning_completed_duration_earns_monitoring_credit_when_state_is_already_known(
        tmp_path, outcome, returncode):
    store, _ = setup(tmp_path)
    projector = MonitoringInformationCredit(information_unit=1)
    prior = sample(0, None, state='returned')
    prior.update(outcome=outcome, native_returncode=returncode)
    current = {**prior, 'sample_ref': 'sample_completed', 'elapsed_seconds': 5.0,
               'sampled_at_unix_seconds': 101}
    assignment = {'job_ref': prior['job_ref'], 'prior_samples': [prior]}
    scientific_before = store.db.execute('SELECT * FROM synthetic_records ORDER BY id').fetchall()
    journal_sample(store, current, [], 0)
    facts = projector.findings(store, assignment=assignment, episode_id='monitor', run_id='run_fixture')
    assert len(facts) == 1
    assert facts[0]['new_completed_timing'] is True
    assert facts[0]['new_state'] is facts[0]['new_outcome'] is False
    assert facts[0]['new_output_states'] == facts[0]['new_timing_overruns'] == []
    assert projector(store, role='job_monitor', assignment=assignment,
                     episode_id='monitor', run_id='run_fixture') == 1
    duplicate = {**current, 'sample_ref': 'sample_duplicate', 'sampled_at_unix_seconds': 102}
    journal_sample(store, duplicate, [], 1)
    assert projector(store, role='job_monitor', assignment=assignment,
                     episode_id='monitor', run_id='run_fixture') == 1
    assert store.db.execute('SELECT * FROM synthetic_records ORDER BY id').fetchall() == scientific_before
    store.db.close()


def test_actual_timing_learned_by_monitoring_updates_parent_expectation_and_requested_form(tmp_path):
    store, tools, query, scope, jobs, binding = prepared(
        tmp_path, gated=True, statistics=True,
        monitoring_credit=MonitoringInformationCredit(information_unit=1))
    expectations = ExecutionExpectations.for_homology(jobs, binding.statistics,
        roles=binding.roles, planning_roles=('annotation', 'improvement'))
    handoffs, monitoring_histories = [], []

    def monitor_estimator(history, parameters, contexts):
        # Fixture continuation only. The observations come from the actual
        # monitoring projector and the existing completed-action boundary.
        monitoring_histories.append(tuple(history))
        return YieldEstimate(len(history), NumericBand.exact(0 if len(history) == 2 else 1),
                             parameters, {'kind': 'fixture_continuation'})

    def first_parent_choice(context):
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
        estimate, = context['resource_tool_estimates']
        assert estimate['job_ref'] is None
        assert estimate['status'] == 'no_matching_history'
        assert estimate['expected_total_seconds'] is None
        return commission(binding, 'job_launch', scope, query_ref=query)

    def commission_monitor(context):
        report = context['child_reports'][-1]
        assert report['job_handoff_state'] == 'usable'
        handoffs.append(report['job_handoff'])
        # Test-controlled release of the coordination wrapper, not an action
        # implemented by the production parent or a new biological observation.
        (jobs._directory(handoffs[0]['job_ref'])/'permit-native').touch()
        wait_terminal(jobs, handoffs[0]['job_ref'])
        return commission(binding, 'job_monitor', scope, handoff=handoffs[0],
                          with_execution=True, with_yield=True)

    def use_monitoring_result(context):
        report = context['child_reports'][-1]
        assert report['sample']['outcome'] == 'succeeded'
        measured_seconds = report['sample']['elapsed_seconds']
        assert measured_seconds > 0
        assert report['local_credit'] == 1
        assert len(report['information']) == 1
        assert report['information'][0]['new_completed_timing'] is True
        assert report['information'][0]['sample']['elapsed_seconds'] == measured_seconds
        estimate, = context['resource_tool_estimates']
        assert estimate['status'] == 'available'
        assert estimate['successful_duration_samples'] == 1
        assert estimate['expected_total_seconds'] == pytest.approx(measured_seconds)
        assert context['current_credit'] == 0
        assert report['closing_yield']['stop_requested'] is True
        # The parent can use its returned timing information and expectation
        # in its next actual choice. It does not need another monitoring child
        # to recover this already learned completed duration.
        return action('episode.history', {'view': 'index', 'offset': 0, 'limit': 5})

    provider = Provider([first_parent_choice,
        action('homology.environment'), action('homology.configure'), action('homology.stage'),
        action('homology.submit'), action('homology.check_handoff'), commission_monitor,
        action('homology.sample'), action('homology.sample'), use_monitoring_result])
    try:
        summary = run(store, tools, provider, binding, tmp_path/'run',
            counts={'annotation': 3, 'job_launch': 5, 'job_monitor': 2},
            expectations=expectations, monitor_estimator=monitor_estimator,
            resource_estimator=ResourceToolEstimator())
        assert summary['credit'] == 0
        assert store.count('annotation') == store.count('assessment') == 0
        assert monitoring_histories == [(), (1,), (1, 0)]
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
        history = RunHistory(binding.statistics.history_path, create=False)
        try:
            assert history.db.execute('SELECT count(*) FROM run_statistics').fetchone()[0] == 1
        finally:
            history.close()
        parents = [context for context in provider.contexts if 'role' not in context['working_state']]
        first, last = parents[0]['resource_tool_estimates'][0], parents[-1]['resource_tool_estimates'][0]
        assert first['proposal_ref'] == last['proposal_ref']
        assert first['expectation_ref'] != last['expectation_ref']
        assert first['expected_total_seconds'] is None
        facts = json.loads(store.db.execute("SELECT facts FROM runtime_forms WHERE "
            "json_extract(facts,'$.monitoring_findings[0].new_completed_timing')=1").fetchone()[0])
        assert facts['monitoring_findings'][0]['sample']['outcome'] == 'succeeded'
    finally:
        for row in jobs.db.execute('SELECT job_ref FROM orders'):
            handle = jobs._handle(row[0])
            if handle.path.exists():
                cancel(handle)
        jobs.close()
        store.close()
