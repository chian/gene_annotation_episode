"""Actual shared Episode tree and tiny native job; explicit fixture scores.

No live models, full-corpus search, production credit policy or annotation claim.
"""
import asyncio
from copy import deepcopy
import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.homology_episodes import HomologyEpisodes
from gene_annotation_episode.communication import ReportBoundaryError
from gene_annotation_episode.execution_recording import HomologyStatistics
from gene_annotation_episode.execution_expectations import ExecutionExpectations
from gene_annotation_episode.episode_reports import report_sources
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate
from gene_annotation_episode.run_statistics import RunHistory
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.monitoring_credit import MonitoringInformationCredit
from gene_annotation_episode.resource_estimation import ResourceToolEstimator, report_source
from gene_annotation_episode.native_lifecycle import cancel
from gene_annotation_episode.runtime import Journal, Record, TypedReportContract, Workflow, WorkflowError, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_homology_jobs import prepare, PROJECT, PROGRAM, QUERY, wait_terminal
from gene_annotation_episode.homology_jobs import HomologyJobs, FileAsset, digest
from test_runtime import FixtureController, obj


def fixture_task_credit(store, scope):
    return 0  # Job infrastructure does not establish scientific progress.


def fixture_job_credit(store, *, role, assignment, episode_id, run_id):
    """Engineering-only test projection, deliberately no production policy."""
    contributions = set()
    prior_states = {json.dumps({key: sample.get(key) for key in ('state', 'outcome', 'outputs')}, sort_keys=True)
                    for sample in assignment.get('prior_samples', [])}
    for row in store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=?',
                                (run_id, episode_id)):
        if not row[1]:
            continue
        action, result = json.loads(row[0]), json.loads(row[1])
        if result['status'] not in {'completed', 'partial'}:
            continue
        if role == 'job_launch':
            contributions.add(action['tool'])
        elif role == 'job_monitor':
            sample = result.get('result') or {}
            state = json.dumps({key: sample.get(key) for key in ('state', 'outcome', 'outputs')}, sort_keys=True)
            if state not in prior_states:
                contributions.add(state)
        else:
            contributions.update(result.get('changed_record_refs', []))
    return len(contributions)


class ParentTools:
    def __init__(self, store):
        self.store, self.seen = store, []

    def catalog(self, scope=None):
        return [{'name': 'fixture.inspect_returned', 'input_schema': obj({'observation_ref': {'type': 'string'}})}]

    def execute(self, name, args, **kwargs):
        assert name == 'fixture.inspect_returned'
        record = self.store.get(args['observation_ref'])
        assert record['record_type'] == 'observation'
        self.seen.append(record['id'])
        return {'status': 'completed', 'record_refs': [record['id']], 'changed_record_refs': [],
                'result': {'kind': record['kind']}}


class Provider:
    def __init__(self, script):
        self.script, self.contexts = iter(script), []

    async def complete(self, episode_id, model_role, instructions, context, schema):
        assert model_role == 'REASONING'
        self.contexts.append(deepcopy(context))
        value = next(self.script)
        if isinstance(value, BaseException):
            raise value
        return value(context) if callable(value) else deepcopy(value)

    async def release(self, episode_id):
        pass


def action(name, args=None):
    return {'selection': {'kind': 'tool', 'tool': name, 'arguments': args or {}}, 'report_update': {}}


def commission(binding, role, scope, *, query_ref=None, cpu=1, handoff=None, prior_sample_refs=(), existing_job_ref=None,
               with_yield=False, with_execution=False):
    if role == 'job_launch':
        fields = {key: binding.fact_sources(role)[key]['report_schema']
                  for key in ('job_ref', 'job_cpu', 'job_handoff', 'job_handoff_state', 'job_handoff_failure')}
        operand = {'existing_job_ref': existing_job_ref} if existing_job_ref is not None else {'query_ref': query_ref, 'cpu': cpu}
    elif role == 'job_monitor':
        fields = {'sample': binding.fact_sources(role)['job_sample']['report_schema']}
        operand = {'handoff': handoff, 'prior_sample_refs': list(prior_sample_refs)}
    else:
        fields = {'comparisons': {'type': 'array', 'items': {'type': 'string', 'format': 'reference',
                  'x-reference-namespace': 'observation'}, 'x-source': 'changed_record_refs'}}
        operand = {'handoff': handoff}
    fields['local_credit'] = {'type': 'number', 'x-source': 'credit'}
    if with_yield:
        fields['closing_yield'] = report_sources()['episode_yield']['report_schema']
    if with_execution:
        fields['execution_forecasts'] = binding.fact_sources(role)['resource_tool_estimates']['report_schema']
        if role == 'job_monitor':
            fields['information'] = binding.fact_sources(role)['monitoring_findings']['report_schema']
    return {'selection': {'kind': 'job_child', 'role': role, 'goal': 'Iteratively investigate the assigned job responsibility',
        'scope': scope, 'purpose': 'Choose subsequent work from actual constrained results',
        'schema_json': json.dumps(obj(fields)), 'initial_report_json': '{}', **operand}, 'report_update': {}}


def prepared(tmp_path, *, gated=False, statistics=False, monitoring_credit=None, max_cpu=1, search_modes=None):
    store = Store(tmp_path/'workspace')
    target = store.create_problem(PROJECT/'cases/gene_001/target.fna', molecule='dna', role='gene')['subject_refs'][0]
    scope = {'subject_refs': [target]}
    translated = ToolRegistry(store).execute('sequence.translate', {'subject_ref': target, 'code': 11, 'cds': True}, scope=scope)
    query = translated['result']['records'][0]['product_ref']
    if gated:
        # Explicit synthetic coordination fixture: actual phmmer only starts
        # when this test releases it after a monitoring child has closed.
        wrapper = tmp_path/'gated-phmmer'
        wrapper.write_text('#!'+sys.executable+'\nimport os,sys,time\n'
            'while not os.path.exists("permit-native"):\n    time.sleep(.01)\n'
            'os.execv('+repr(str(PROGRAM))+', ['+repr(str(PROGRAM))+', *sys.argv[1:]])\n')
        wrapper.chmod(0o700)
        database = tmp_path/'references.faa'
        database.write_text(QUERY.replace('>gene_001', '>reference_self_fixture'))
        jobs = HomologyJobs.create(tmp_path/'jobs', executable=FileAsset(wrapper, digest(wrapper)),
            reference_database=FileAsset(database, digest(database)),
            policy=LocalJobPolicy(128*1024**2, 4*1024**2), max_cpu=max_cpu, search_modes=search_modes)
    else:
        jobs = prepare(tmp_path, max_cpu=max_cpu, search_modes=search_modes)
    statistical_binding = None
    if statistics:
        history = RunHistory(tmp_path/'global-execution.sqlite')
        history.close()
        statistical_binding = HomologyStatistics(tmp_path/'global-execution.sqlite', 'fixture-host', 1, 253)
    binding = HomologyEpisodes(jobs, parser_policy=LocalJobPolicy(256*1024**2, 4*1024**2),
        credit_projector=fixture_job_credit, credit_binding={'kind': 'fixture_only_not_production'},
        monitoring_projector=monitoring_credit or fixture_job_credit,
        monitoring_binding=(monitoring_credit.as_record() if monitoring_credit else {'kind': 'fixture_monitor_only_not_production'}),
        statistics=statistical_binding)
    return store, ParentTools(store), query, scope, jobs, binding


def run(store, tools, provider, binding, directory=None, *, counts=None, resume=False, expectations=None,
        monitor_estimator=None, resource_estimator=None):
    counts = counts or {'annotation': 5, 'job_launch': 5, 'job_monitor': 2, 'job_results': 2}
    def factory(path, initial):
        if path[-1][0] == 'job_monitor' and monitor_estimator is not None:
            return YieldController(str(path), initial, 0, estimate_with_context=monitor_estimator)
        return FixtureController(str(path), initial, counts[path[-1][0]])
    return asyncio.run(run_workflow(store, tools, provider=provider, run_dir=directory, resume=resume,
        controller_factory=factory, project_credit=fixture_task_credit, job_episodes=binding,
        execution_expectations=expectations, resource_estimator=resource_estimator))


def test_native_roles_return_forms_and_parent_receives_one_observation_per_child(tmp_path, monkeypatch):
    store, tools, query, scope, jobs, binding = prepared(tmp_path, gated=True, statistics=True,
        monitoring_credit=MonitoringInformationCredit(information_unit=1))
    execution_class = binding.statistics.execution_class(jobs, {'cpu': 1,
        'query_fasta': '>query\n'+''.join(QUERY.splitlines()[1:])+'\n'})
    expectations = ExecutionExpectations.for_homology(jobs, binding.statistics,
        roles=['job_launch', 'job_monitor', 'job_results'])
    handoffs = []
    monitor_fits = []
    def monitor_estimator(history, parameters, contexts):
        # An explicit test policy, not a proposed scientific/time formula.
        monitor_fits.append(tuple(history))
        if history:
            assert contexts[-1]['resource_tool_estimates_after_action'][0]['sample_ref'] is not None
            assert contexts[-1]['resource_tool_estimates_after_action'][0]['status'] == 'no_matching_history'
        return YieldEstimate(len(history), NumericBand.exact(0 if len(history) == 2 else 1),
            parameters, {'private_fixture_diagnostic': 'PRIVATE_MONITOR_HISTORY'})
    def monitor(context):
        report = context['child_reports'][-1]
        assert report['job_handoff_state'] == 'usable' and report['local_credit'] == 5
        handoffs.append(report['job_handoff'])
        return commission(binding, 'job_monitor', scope, handoff=handoffs[0], with_yield=True, with_execution=True)
    def results(context):
        report = context['child_reports'][-1]
        assert report['sample']['job_ref'] == handoffs[0]['job_ref']
        assert report['sample']['state'] == 'running'
        assert report['local_credit'] == 0  # This child received the parent's prior observation.
        assert report['information'] == []
        assert report['execution_forecasts'][0]['status'] == 'no_matching_history'
        assert report['closing_yield']['expected_next_gain'] == NumericBand.exact(0).as_record()
        # This is test-controlled native availability, not a production parent
        # tool that submits a job or fabricates scientific progress.
        (jobs._directory(handoffs[0]['job_ref'])/'permit-native').touch()
        wait_terminal(jobs, handoffs[0]['job_ref'])
        return commission(binding, 'job_results', scope, handoff=handoffs[0])
    def schedule_monitor(context):
        report = context['child_reports'][-1]
        assert report['sample']['state'] == 'running'
        assert report['local_credit'] == 1
        assert len(report['information']) == 1
        assert report['information'][0]['new_state'] is True
        assert report['information'][0]['new_timing_overruns'] == []
        projection = report['closing_yield']
        assert projection['completed_actions'] == 2 and projection['stop_requested'] is True
        assert projection['expected_next_gain'] == NumericBand.exact(0).as_record()
        selected = commission(binding, 'job_monitor', scope, handoff=handoffs[0],
                              prior_sample_refs=[report['sample']['sample_ref']], with_yield=True, with_execution=True)
        # Fixture-selected delay demonstrates plumbing, not a production
        # timing/yield formula or compulsory recommissioning cadence.
        # Interpret the recorded child's decision; do not reimplement its
        # numerical status/upper-bound rule in the parent fixture.
        selected['selection']['delay_seconds'] = .03 if projection['stop_requested'] else 0
        return selected
    def next_page(context):
        result = context['last_local_outcome']['result']
        return action('homology.extract', {'limit': 10, 'snapshot_ref': result['snapshot_ref']})
    def inspect_returned(context):
        report = context['child_reports'][-1]
        assert len(report['comparisons']) == 1 and report['local_credit'] == 1
        return action('fixture.inspect_returned', {'observation_ref': report['comparisons'][0]})
    provider = Provider([action('homology.submit'), commission(binding, 'job_launch', scope, query_ref=query),
        action('homology.environment'), action('homology.configure'), action('homology.stage'),
        action('homology.submit'), action('homology.check_handoff'), monitor,
        action('homology.submit'), action('homology.sample'), action('homology.sample'), schedule_monitor,
        action('homology.sample'), action('homology.sample'), results,
        action('homology.extract', {'limit': 0}), next_page, inspect_returned])
    try:
        summary = run(store, tools, provider, binding, tmp_path/'run', expectations=expectations,
                      monitor_estimator=monitor_estimator, resource_estimator=ResourceToolEstimator())
        assert summary['completed_actions'] == 5 and summary['credit'] == 0
        assert len(tools.seen) == 1 and store.count('annotation') == store.count('assessment') == 0
        observations = [json.loads(row[0]) for row in store.db.execute('SELECT observation FROM runtime_observations')]
        assert len(observations) == 5+5+2+2+2
        root = store.db.execute("SELECT episode_id FROM runtime_episodes WHERE json_array_length(path)=1").fetchone()[0]
        assert store.db.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?', (root,)).fetchone()[0] == 5
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
        assert jobs.db.execute('SELECT count(*) FROM samples').fetchone()[0] == 4
        history = RunHistory(binding.statistics.history_path, create=False)
        try:
            assert history.db.execute('SELECT count(*) FROM run_statistics').fetchone()[0] == 1
            measured_class = json.loads(history.db.execute('SELECT data FROM execution_classes').fetchone()[0])
            assert measured_class['query_residues'] == measured_class['reference_residues'] == 253
            assert measured_class['reference_records'] == 1
            assert all('expected_next_gain' not in row[0] and 'episode_yield' not in row[0]
                       for row in history.db.execute('SELECT data FROM run_statistics'))
        finally:
            history.close()
        child_contexts = [context for context in provider.contexts
                          if context['working_state'].get('role') == 'job_monitor']
        assert child_contexts[-1]['working_state']['assignment']['prior_samples'][0]['state'] == 'running'
        launch_contexts = [context for context in provider.contexts
                           if context['working_state'].get('role') == 'job_launch']
        assert [context['execution_expectations']['execution_classes'][0]['cpu_threads']
                for context in launch_contexts] == [1, 1, 1, 1, 1]
        launch_history = launch_contexts[-1]['restored_episode_history']['entries']
        assert [entry['tool'] for entry in launch_history] == [
            'homology.environment', 'homology.configure', 'homology.stage', 'homology.submit']
        commissions = [entry for entry in provider.contexts[-1]['restored_episode_history']['entries']
                       if entry['kind'] == 'job_child']
        assert len(commissions) == 4 and all(entry['status'] == 'completed' for entry in commissions)
        timer = dict(store.db.execute('SELECT * FROM runtime_timed_commissions').fetchone())
        assert timer['fired_at'] >= timer['due_at'] >= timer['scheduled_at']
        assert timer['returned_at'] >= timer['fired_at']
        assert provider.contexts[1]['feedback']['category'] == 'action_contract'
        assert sum(context.get('feedback', {}).get('category') == 'action_contract'
                   for context in provider.contexts if context.get('feedback')) == 2
        for context in provider.contexts:
            names = {item['name'] for item in context['tools']}
            role = context['working_state'].get('role', 'annotation')
            assert ('homology.submit' in names) == (role == 'job_launch')
            if role != 'annotation':
                assert 'fixture.inspect_returned' not in names
                assert set(context['working_state']) == {'role', 'assignment'}
            if role == 'job_monitor':
                assert context['execution_expectations']['snapshots'][0]['data']['statistics'] == []
            elif role == 'job_results':
                stats = context['execution_expectations']['snapshots'][0]['data']['statistics']
                assert stats[0]['attempt_count'] == stats[0]['complete_duration_count'] == 1
                assert stats[0]['mean_seconds'] > 0
            elif role == 'annotation':
                assert 'execution_expectations' not in context
                assert all('execution_statistics_export' not in form for form in context['child_reports'])
                assert 'PRIVATE_MONITOR_HISTORY' not in json.dumps(context)
        assert monitor_fits == [(), (1,), (1, 0), (), (0,), (0, 0)]
        # Historical completion inspection does not submit, parse or poll again.
        assert run(store, tools, Provider([]), binding, resume=True, monitor_estimator=monitor_estimator) == summary
        assert monitor_fits == [(), (1,), (1, 0), (), (0,), (0, 0)]
        assert jobs.db.execute('SELECT count(*) FROM samples').fetchone()[0] == 4
        assert dict(store.db.execute('SELECT * FROM runtime_timed_commissions').fetchone()) == timer
        sample = json.loads(jobs.db.execute('SELECT body FROM samples LIMIT 1').fetchone()[0])
        binding.validate_report({'latest': sample}, {'job_ref': handoffs[0]['job_ref']})
        with pytest.raises(ReportBoundaryError, match='recorded values'):
            binding.validate_report({'latest': {**sample, 'elapsed_seconds': sample['elapsed_seconds']+1}},
                                    {'job_ref': handoffs[0]['job_ref']})
        stale = jobs._directory(handoffs[0]['job_ref'])/'statistics_recovery.json'
        stale.write_text('{"synthetic_old_diagnostic":true}')
        unlink = Path.unlink
        def deny_old_diagnostic(path, *args, **kwargs):
            if path == stale:
                raise PermissionError('synthetic diagnostic cleanup failure')
            return unlink(path, *args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(Path, 'unlink', deny_old_diagnostic)
            recovered = list(jobs.recover_statistics(handoffs[0]['job_ref']))
        assert recovered[0]['state'] == 'recorded' and recovered[0]['diagnostic_cleanup_failed'] is True
    finally:
        for row in jobs.db.execute('SELECT job_ref FROM orders'):
            handle = jobs._handle(row[0])
            if handle.path.exists():
                cancel(handle)
        jobs.close(); store.close()


def test_launch_can_yield_without_claiming_a_successful_handoff(tmp_path):
    store, tools, query, scope, jobs, binding = prepared(tmp_path)
    provider = Provider([commission(binding, 'job_launch', scope, query_ref=query), action('homology.environment')])
    try:
        result = run(store, tools, provider, binding, tmp_path/'run', counts={'annotation': 1, 'job_launch': 1})
        assert result['completed_actions'] == 1
        form = json.loads(store.db.execute('SELECT form FROM runtime_report_attempts').fetchone()[0])
        assert form['job_handoff'] is None and form['job_handoff_state'] == 'unavailable'
        assert form['job_handoff_failure'] == 'job_not_submitted'
        assert not jobs._handle(form['job_ref']).path.exists()
        assert store.count('annotation') == 0
    finally:
        jobs.close(); store.close()


def test_parent_selected_cpu_reaches_assignment_native_job_and_returned_form(tmp_path):
    store, tools, query, scope, jobs, binding = prepared(tmp_path, statistics=True, max_cpu=2)
    expectations = ExecutionExpectations.for_homology(jobs, binding.statistics, roles=binding.roles,
        planning_roles=('annotation',))
    def choose(context):
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
        assert {row['cpu_threads'] for row in context['resource_tool_estimates']} == {1, 2}
        assert all(row['job_ref'] is None for row in context['resource_tool_estimates'])
        return commission(binding, 'job_launch', scope, query_ref=query, cpu=2)
    provider = Provider([choose, action('homology.environment'),
        action('homology.configure', {'cpu': 1}),  # Invalid child substitution; parent selection persists.
        action('homology.configure'), action('homology.stage'), action('homology.submit'),
        action('homology.check_handoff')])
    try:
        result = run(store, tools, provider, binding, tmp_path/'run', counts={'annotation': 1, 'job_launch': 5},
            expectations=expectations, resource_estimator=ResourceToolEstimator())
        assert result['completed_actions'] == 1
        row = dict(jobs.db.execute('SELECT * FROM orders').fetchone())
        assert row['cpu'] == 2
        wait_terminal(jobs, row['job_ref'])
        handle = jobs._handle(row['job_ref']).read()
        assert handle['command'][1:3] == ['--cpu', '2']
        assert handle['statistics']['execution_class']['cpu_threads'] == 2
        form = json.loads(store.db.execute('SELECT form FROM runtime_report_attempts').fetchone()[0])
        assert form['job_cpu'] == 2
        launch = [context for context in provider.contexts if context['working_state'].get('role') == 'job_launch']
        assert all(context['working_state']['assignment']['cpu'] == 2 for context in launch)
        assert launch[2]['feedback']['category'] == 'action_contract'
        repaired = binding.assign(store, 'job_launch', {'existing_job_ref': row['job_ref']}, scope,
            operation_key='repair')
        assert repaired['cpu'] == 2 and repaired['job_ref'] == row['job_ref']
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
    finally:
        for row in jobs.db.execute('SELECT job_ref FROM orders'):
            handle = jobs._handle(row[0])
            if handle.path.exists():
                cancel(handle)
        jobs.close(); store.close()


def test_prospective_forecast_references_pass_real_workflow_form_boundary_without_a_job(tmp_path):
    store, tools, query, scope, jobs, binding = prepared(tmp_path, statistics=True)
    expectations = ExecutionExpectations.for_homology(jobs, binding.statistics, roles=binding.roles,
        planning_roles=('annotation', 'improvement'))
    workflow = Workflow(store, tools, Provider([]), tmp_path/'run', 'fixture-run',
        lambda path, initial: FixtureController(str(path), initial, 1), fixture_task_credit,
        execution_expectations=expectations, job_episodes=binding, resource_estimator=ResourceToolEstimator())
    try:
        classes = binding.prospective_execution_classes(store, scope)
        context = expectations.capture('annotation', planning_scopes=classes)
        forecasts = ResourceToolEstimator().estimate_context(context)
        workflow.journal.save('runtime_model_calls', {'episode_id': 'fixture-parent', 'call_index': 0,
            'purpose': 'decision', 'request': json.dumps({'context': {'resource_tool_estimates': forecasts}}),
            'response': None})
        schema = obj({'forecasts': report_source()['report_schema']})
        contract = TypedReportContract('Use original execution expectations', schema, workflow.resolver(scope),
            lambda value: workflow.validate_report(value, scope, schema=schema))
        admitted = contract.admit({'forecasts': forecasts}, audit_identifiers=('fixture-child',))
        assert admitted.as_record()['forecasts'] == forecasts
        altered = deepcopy(forecasts)
        altered[0]['expected_total_seconds'] = 0
        with pytest.raises(ReportBoundaryError) as mismatch:
            contract.admit({'forecasts': altered}, audit_identifiers=('fixture-child',))
        assert mismatch.value.diagnostic['code'] == 'estimate_fact_mismatch'
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
        assert query not in json.dumps(context['snapshots'])
        frozen = deepcopy(admitted.as_record())
        # A later receipt changes future expectations, not the references or
        # values of the original admitted forecast.
        from test_runtime_expectations import append
        append(binding.statistics.history_path, classes[0], 'later-execution', 5)
        assert contract.admit(frozen, audit_identifiers=('fixture-child',)).as_record() == frozen
        narrow = {'subject_refs': scope['subject_refs'], 'segments': [
            {'target_ref': scope['subject_refs'][0], 'start': 0, 'end': 3, 'unit': 'nt'}]}
        assert not workflow.resolver(narrow)(forecasts[0]['estimate_ref'], 'job_execution_estimate')
        assert not workflow.resolver(scope)('execution_proposal_nonexistent', 'execution_proposal')
    finally:
        jobs.close(); store.close()


def test_interruption_after_submit_reuses_job_and_original_operational_scores(tmp_path):
    store, tools, query, scope, jobs, binding = prepared(tmp_path, statistics=True)
    blocker = sqlite3.connect(binding.statistics.history_path)
    blocker.execute('BEGIN EXCLUSIVE')
    counts = {'annotation': 1, 'job_launch': 5}
    first = Provider([commission(binding, 'job_launch', scope, query_ref=query),
        action('homology.environment'), action('homology.configure'), action('homology.stage'),
        action('homology.submit'), KeyboardInterrupt()])
    try:
        with pytest.raises(KeyboardInterrupt):
            run(store, tools, first, binding, tmp_path/'run', counts=counts)
        job = jobs.db.execute('SELECT job_ref FROM orders').fetchone()[0]
        wait_terminal(jobs, job)
        assert jobs.status(job)['outcome'] == 'succeeded'
        assert json.loads((jobs._directory(job)/'native.handle.json').read_text())['statistics']['condition_capture'] == 'unavailable_before_submission'
        blocker.rollback()
        history = RunHistory(binding.statistics.history_path, create=False)
        assert history.db.execute('SELECT count(*) FROM run_statistics').fetchone()[0] == 0
        history.close()
        native_before = jobs._handle(job).path.read_bytes()
        original_scores = [row[0] for row in store.db.execute('SELECT credit FROM runtime_actions WHERE credit IS NOT NULL ORDER BY decision_index')]
        assert original_scores == [1, 2, 3, 4]
        second = Provider([action('homology.check_handoff')])
        result = run(store, tools, second, binding, resume=True, counts=counts)
        assert result['completed_actions'] == 1 and result['credit'] == 0
        assert jobs._handle(job).path.read_bytes() == native_before
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
        assert len(second.contexts) == 1
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 6
        history = RunHistory(binding.statistics.history_path, create=False)
        assert history.db.execute('SELECT count(*) FROM run_statistics').fetchone()[0] == 1
        history.close()
        child_id = store.db.execute("SELECT episode_id FROM runtime_episodes WHERE json_extract(path,'$[#-1][0]')='job_launch'").fetchone()[0]
        assert [row[0] for row in store.db.execute('SELECT credit FROM runtime_actions WHERE episode_id=? AND decision_index<4 ORDER BY decision_index',
                                                  (child_id,))] == original_scores
    finally:
        blocker.rollback(); blocker.close()
        for row in jobs.db.execute('SELECT job_ref FROM orders'):
            handle = jobs._handle(row[0])
            if handle.path.exists():
                cancel(handle)
        jobs.close(); store.close()


def test_delayed_commission_recovery_keeps_original_due_time_and_one_parent_action(tmp_path, monkeypatch):
    store, tools, query, scope, jobs, binding = prepared(tmp_path)
    selected = commission(binding, 'job_launch', scope, query_ref=query)
    selected['selection']['delay_seconds'] = .03
    counts = {'annotation': 1, 'job_launch': 1}
    async def interrupted_wait(self, parent, index):
        raise KeyboardInterrupt()
    try:
        with monkeypatch.context() as patch:
            patch.setattr(Journal, 'await_child_commission', interrupted_wait)
            with pytest.raises(KeyboardInterrupt):
                run(store, tools, Provider([selected]), binding, tmp_path/'run', counts=counts)
        timer = dict(store.db.execute('SELECT * FROM runtime_timed_commissions').fetchone())
        assert timer['fired_at'] is None and timer['returned_at'] is None
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
        resumed = Provider([action('homology.environment')])
        result = run(store, tools, resumed, binding, resume=True, counts=counts)
        after = dict(store.db.execute('SELECT * FROM runtime_timed_commissions').fetchone())
        assert after['due_at'] == timer['due_at'] and after['scheduled_at'] == timer['scheduled_at']
        assert after['fired_at'] >= after['due_at'] and after['returned_at'] >= after['fired_at']
        assert result['completed_actions'] == 1
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 2
        assert len(resumed.contexts) == 1  # Saved parent commission was not selected again.
        assert jobs.db.execute('SELECT sum(submission_requested) FROM orders').fetchone()[0] == 0
    finally:
        jobs.close(); store.close()


def test_parent_repairs_job_form_from_saved_facts_without_recommissioning(tmp_path):
    store, tools, query, scope, jobs, binding = prepared(tmp_path)
    correct = commission(binding, 'job_launch', scope, query_ref=query)
    broken = deepcopy(correct)
    schema = json.loads(broken['selection']['schema_json'])
    schema['properties']['local_credit']['maximum'] = 0  # Deliberate test contract contradiction.
    broken['selection']['schema_json'] = json.dumps(schema)
    def repair(context):
        assert context['feedback']['kind'] == 'report_delivery_failure'
        return {'selection': {'kind': 'redeliver_report', 'delivery_ref': context['feedback']['delivery_ref'],
            'purpose': 'Read the existing checked operational handoff',
            'schema_json': correct['selection']['schema_json']}, 'report_update': {}}
    def monitor(context):
        report = context['child_reports'][-1]
        assert report['local_credit'] == 5 and report['job_handoff_state'] == 'usable'
        return commission(binding, 'job_monitor', scope, handoff=report['job_handoff'])
    provider = Provider([broken, action('homology.environment'), action('homology.configure'),
        action('homology.stage'), action('homology.submit'), action('homology.check_handoff'),
        repair, monitor, action('homology.sample')])
    try:
        result = run(store, tools, provider, binding, tmp_path/'run',
            counts={'annotation': 2, 'job_launch': 5, 'job_monitor': 1})
        assert result['completed_actions'] == 2 and result['pending_report_deliveries'] == 0
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 3
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 8
        assert store.db.execute('SELECT count(*) FROM runtime_report_attempts WHERE failure IS NOT NULL').fetchone()[0] == 1
    finally:
        for row in jobs.db.execute('SELECT job_ref FROM orders'):
            handle = jobs._handle(row[0])
            if handle.path.exists():
                cancel(handle)
        jobs.close(); store.close()


def test_parent_commissions_iterative_repair_of_existing_reserved_job(tmp_path, monkeypatch):
    import gene_annotation_episode.homology_jobs as module
    from gene_annotation_episode.acquisition import AcquisitionError
    store, tools, query, scope, jobs, binding = prepared(tmp_path)
    original_dispatch = module.start_prepared
    def unavailable(handle, **kwargs):
        raise AcquisitionError('local_job_boundary_unavailable', phase='local_preflight',
                               operational={'reason': 'synthetic_temporary_backend_unavailable'})
    monkeypatch.setattr(module, 'start_prepared', unavailable)
    prior_job = []
    def commission_repair(context):
        form = context['child_reports'][-1]
        assert form['job_handoff'] is None
        assert form['job_handoff_failure'] == 'submission_unconfirmed'
        prior_job.append(form['job_ref'])
        # Explicitly simulated external recovery, not an unchanged deterministic
        # retry or a production infrastructure loop overriding an episode.
        monkeypatch.setattr(module, 'start_prepared', original_dispatch)
        return commission(binding, 'job_launch', scope, existing_job_ref=form['job_ref'])
    provider = Provider([commission(binding, 'job_launch', scope, query_ref=query),
        action('homology.environment'), action('homology.configure'), action('homology.stage'),
        action('homology.submit'), action('homology.environment'), commission_repair,
        action('homology.environment'), action('homology.resume_start'), action('homology.check_handoff'),
        action('homology.environment')])
    try:
        summary = run(store, tools, provider, binding, tmp_path/'run', counts={'annotation': 2, 'job_launch': 4})
        assert summary['completed_actions'] == 2 and summary['credit'] == 0
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
        forms = [json.loads(row[0]) for row in store.db.execute('SELECT form FROM runtime_report_attempts ORDER BY decision_index')]
        assert forms[0]['job_ref'] == forms[1]['job_ref'] == prior_job[0]
        assert forms[0]['job_handoff'] is None and forms[1]['job_handoff_state'] == 'usable'
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 10
        failed = [json.loads(row[0]) for row in store.db.execute("SELECT result FROM runtime_actions WHERE json_extract(result,'$.status')='failed'")]
        assert len(failed) == 1 and failed[0]['feedback']['code'] == 'local_job_boundary_unavailable'
    finally:
        for row in jobs.db.execute('SELECT job_ref FROM orders'):
            handle = jobs._handle(row[0])
            if handle.path.exists():
                cancel(handle)
        jobs.close(); store.close()


def test_unreadable_launch_receipt_returns_basic_form_facts_without_erasing_state(tmp_path):
    store, tools, query, scope, jobs, binding = prepared(tmp_path)
    try:
        assignment = binding.assign(store, 'job_launch', {'query_ref': query, 'cpu': 1}, scope, operation_key='fixture')
        directory = jobs._directory(assignment['job_ref'])
        directory.mkdir()
        handle = directory/'native.handle.json'
        handle.write_bytes(b'{"explicit_synthetic_broken_receipt":')
        original = handle.read_bytes()
        Journal(store, 'fixture-run')
        source = SimpleNamespace(request=SimpleNamespace(message=Record({'job_assignment': assignment})),
            workflow=SimpleNamespace(store=store, run_id='fixture-run'), episode_id='fixture-source',
            path=(('job_launch', 'fixture'),))
        facts = binding.facts(source)
        assert facts['job_handoff'] is None and facts['job_handoff_state'] == 'unavailable'
        assert facts['job_handoff_failure'] == 'receiving_interface_unavailable'
        assert handle.read_bytes() == original
        assert store.count('annotation') == store.count('assessment') == 0
    finally:
        jobs.close(); store.close()


def test_job_bindings_do_not_silently_adopt_default_scientific_scores(tmp_path):
    store, tools, query, scope, jobs, binding = prepared(tmp_path)
    try:
        with pytest.raises(ValueError, match='explicit_controller_and_task_credit'):
            asyncio.run(run_workflow(store, tools, provider=Provider([]), run_dir=tmp_path/'run', job_episodes=binding))
        selection = {'query_ref': scope['subject_refs'][0]}
        with pytest.raises(ValueError, match='protein_of_assigned_target'):
            binding.assign(store, 'job_launch', selection, scope, operation_key='invalid-query')
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
    finally:
        jobs.close(); store.close()


def test_assigned_form_reference_names_follow_declared_namespaces(tmp_path):
    store, tools, query, scope, jobs, binding = prepared(tmp_path, statistics=True)
    expectations = ExecutionExpectations.for_homology(jobs, binding.statistics, roles=binding.roles)
    workflow = Workflow(store, tools, Provider([]), tmp_path/'run', 'fixture-run',
        lambda path, initial: FixtureController(str(path), initial, 1), fixture_task_credit,
        execution_expectations=expectations, job_episodes=binding, resource_estimator=ResourceToolEstimator())
    try:
        assignment = binding.assign(store, 'job_launch', {'query_ref': query, 'cpu': 1}, scope,
            operation_key='assigned-form')
        def ref(namespace):
            return {'type': 'string', 'format': 'reference', 'x-reference-namespace': namespace}
        schema = obj({'sample_ref': ref('homology_job'), 'job_ref': ref('subject'),
            'registry_ref': ref('subject'), 'estimate_ref': ref('subject'),
            'assigned_identity': ref('homology_job')})
        report = {'sample_ref': assignment['job_ref'], 'job_ref': query, 'registry_ref': query,
            'estimate_ref': query, 'assigned_identity': assignment['job_ref']}
        contract = TypedReportContract('Use declared reference meanings', schema,
            workflow.resolver(scope, assignment=assignment),
            lambda value: workflow.validate_report(value, scope, assignment=assignment, schema=schema))
        assert contract.admit(report, audit_identifiers=('fixture-child',)).as_record() == report
        other = binding.assign(store, 'job_launch', {'query_ref': query, 'cpu': 1}, scope,
            operation_key='other-assignment')
        with pytest.raises(ReportBoundaryError):
            contract.admit({**report, 'assigned_identity': other['job_ref']}, audit_identifiers=('fixture-child',))
        assert jobs.db.execute('SELECT sum(submission_requested) FROM orders').fetchone()[0] == 0
    finally:
        jobs.close(); store.close()
