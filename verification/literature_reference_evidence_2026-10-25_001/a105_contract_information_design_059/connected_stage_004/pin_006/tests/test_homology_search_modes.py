"""Parent-owned sensitivity, exact forecasts and one tiny actual native job.

Scripted decisions/fixture continuation test execution, not scientific utility
of the mode on the full corpus or configured-model behavior.
"""
from copy import deepcopy
import asyncio
import json

import pytest

from gene_annotation_episode.execution_expectations import ExecutionExpectations
from gene_annotation_episode.homology_jobs import HomologyJobs
from gene_annotation_episode.native_lifecycle import cancel
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.run_statistics import RunHistory
from test_homology_jobs import prepare, QUERY, wait_terminal
from test_homology_episode_runtime import prepared, Provider, action, commission, run


MODES = ['native_defaults', 'maximum_sensitivity']


def test_case_records_caller_modes_and_maps_them_before_parent_choice(tmp_path):
    from gene_annotation_episode.case_execution import prepare_case_run, run_prepared_case
    from test_case_execution import prepared as prepare_case, PARAMETERS, inspect_sources
    case, configuration, policy = prepare_case(tmp_path)
    configuration['search_modes'] = list(MODES)
    directory = tmp_path/'run'
    manifest = prepare_case_run(case, directory, configuration)
    assert manifest['registry_configuration']['search_modes'] == MODES
    assert manifest['configuration']['search_modes'] == MODES
    assert prepare_case_run(case, directory, configuration) == manifest
    def inspect(context):
        options = context['job_execution_options']
        assert {value['search_mode'] for value in options} == set(MODES)
        assert {value['execution_class_ref'] for value in options} == {
            value['execution_class_ref'] for value in context['resource_tool_estimates']}
        assert all(value['job_ref'] is None for value in context['resource_tool_estimates'])
        return inspect_sources()
    result = asyncio.run(run_prepared_case(directory, policy_file=policy, parameters=PARAMETERS,
                                           provider=Provider([inspect])))
    assert result['completed_actions'] == 1
    jobs = HomologyJobs(directory/'native-jobs')
    try:
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
    finally:
        jobs.close()
    assert asyncio.run(run_prepared_case(directory, resume=True, provider=Provider([]))) == result


def test_selected_search_mode_is_explicit_owned_immutable_and_durable(tmp_path):
    jobs = prepare(tmp_path, search_modes=MODES)
    try:
        operands = {'query_ref': 'fixture', 'query_fasta': QUERY, 'cpu': 1, 'operation_key': 'selected'}
        for mode in (None, 'arbitrary_flags', '--stall'):
            with pytest.raises(ValueError, match='search_mode_outside'):
                jobs.order(**operands, search_mode=mode)
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
        job = jobs.order(**operands, search_mode='maximum_sensitivity')
        assert jobs.order(**operands, search_mode='maximum_sensitivity') == job
        with pytest.raises(ValueError, match='order_identity_conflict'):
            jobs.order(**operands, search_mode='native_defaults')
        assert jobs.environment(job)['configured_search_mode'] == 'maximum_sensitivity'
        directory = jobs.directory
        jobs.close()
        jobs = HomologyJobs(directory)
        assert jobs._row(job)['search_mode'] == 'maximum_sensitivity'
        assert '--max' in jobs._command(jobs._row(job))
        assert jobs.db.execute('SELECT sum(submission_requested) FROM orders').fetchone()[0] == 0
    finally:
        jobs.close()


def test_parent_mode_reaches_native_repair_results_and_separate_duration_history(tmp_path):
    store, tools, query, scope, jobs, binding = prepared(tmp_path, statistics=True, search_modes=MODES)
    expectations = ExecutionExpectations.for_homology(jobs, binding.statistics,
        roles=binding.roles, planning_roles=('annotation', 'improvement'))
    initial_forecasts = []
    received = []
    def request_launch(context):
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
        options = context['job_execution_options']
        assert {(v['query_ref'], v['cpu'], v['search_mode']) for v in options} == {
            (query, 1, mode) for mode in MODES}
        assert len({v['execution_class_ref'] for v in options}) == 2
        initial_forecasts.extend(deepcopy(context['resource_tool_estimates']))
        assert {value['execution_class_ref'] for value in initial_forecasts} == {
            value['execution_class_ref'] for value in options}
        assert all(v['status'] == 'no_matching_history' and v['job_ref'] is None for v in initial_forecasts)
        selected = commission(binding, 'job_launch', scope, query_ref=query)
        selected['selection']['search_mode'] = 'maximum_sensitivity'
        schema = json.loads(selected['selection']['schema_json'])
        schema['properties']['mode'] = binding.fact_sources('job_launch')['job_search_mode']['report_schema']
        schema['required'].append('mode')
        selected['selection']['schema_json'] = json.dumps(schema)
        return selected
    def request_repair(context):
        report = context['child_reports'][-1]
        received.append(report)
        assert report['mode'] == 'maximum_sensitivity'
        row = jobs._row(report['job_ref'])
        assert row['search_mode'] == 'maximum_sensitivity'
        command = jobs._handle(row['job_ref']).read()['command']
        assert command == [jobs.config['executable']['path'], '--cpu', '1', '--max',
            '--tblout', 'hits.tbl', '--domtblout', 'domains.tbl', 'query.faa', 'references.faa']
        wait_terminal(jobs, row['job_ref'])
        binding.recover_statistics()
        return commission(binding, 'job_launch', scope, existing_job_ref=report['job_ref'])
    def assert_repair(context):
        assert context['working_state']['assignment']['search_mode'] == 'maximum_sensitivity'
        return action('homology.environment')
    def request_results(context):
        report = context['child_reports'][-1]
        assert report['job_ref'] == received[0]['job_ref']
        forecasts = {v['execution_class_ref']: v for v in context['resource_tool_estimates']}
        options = {v['search_mode']: v for v in context['job_execution_options']}
        maximum = forecasts[options['maximum_sensitivity']['execution_class_ref']]
        default = forecasts[options['native_defaults']['execution_class_ref']]
        assert maximum['status'] == 'available' and maximum['successful_duration_samples'] == 1
        assert maximum['expected_total_seconds'] > 0
        assert default['status'] == 'no_matching_history' and default['expected_total_seconds'] is None
        assert all(v['status'] == 'no_matching_history' for v in initial_forecasts)
        assignment = {'job_ref': report['job_ref'], 'query_ref': query, 'cpu': 1,
                      'search_mode': 'native_defaults'}
        assert expectations.capture('job_launch', assignment=assignment)['status'] == 'unavailable'
        return commission(binding, 'job_results', scope, handoff=report['job_handoff'])
    def read_coverage(context):
        assert context['working_state']['assignment']['search_mode'] == 'maximum_sensitivity'
        return action('homology.coverage', {'snapshot_ref': context['last_local_outcome']['result']['snapshot_ref']})
    def use_results(context):
        report = context['child_reports'][-1]
        observation = next(ref for ref in report['comparisons'] if store.get(ref)['record_type'] == 'observation')
        assert context['current_credit'] == 0
        return action('fixture.inspect_returned', {'observation_ref': observation})
    provider = Provider([request_launch, action('homology.environment'), action('homology.configure'),
        action('homology.stage'), action('homology.submit'), action('homology.check_handoff'), request_repair,
        assert_repair, action('homology.configure'), action('homology.stage'), action('homology.submit'),
        action('homology.check_handoff'), request_results, action('homology.extract', {'limit': 10}),
        read_coverage, use_results])
    try:
        counts = {'annotation': 4, 'job_launch': 5, 'job_results': 2}
        summary = run(store, tools, provider, binding, tmp_path/'run', counts=counts,
                      expectations=expectations, resource_estimator=ResourceToolEstimator())
        assert summary['completed_actions'] == 4 and summary['credit'] == 0
        assert store.count('assessment') == store.count('annotation') == 0
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 16
        assert len(tools.seen) == 1
        history = RunHistory(binding.statistics.history_path, create=False)
        try:
            assert history.db.execute('SELECT count(*) FROM run_statistics').fetchone()[0] == 1
        finally:
            history.close()
        assert run(store, tools, Provider([]), binding, tmp_path/'run', counts=counts, resume=True,
            expectations=expectations, resource_estimator=ResourceToolEstimator()) == summary
    finally:
        for row in jobs.db.execute('SELECT job_ref FROM orders'):
            handle = jobs._handle(row[0])
            if handle.path.exists():
                cancel(handle)
        jobs.close()
        store.close()
