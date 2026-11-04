"""Production score/controller lifecycle with scripted selections, not models.

The synthetic native barrier makes ongoing execution reproducible. It releases
real phmmer after a monitoring episode yields. It is not a production scheduler,
duration benchmark, scientific claim or prescribed episode sequence.
"""
import asyncio
import json

from gene_annotation_episode.execution_expectations import ExecutionExpectations
from gene_annotation_episode.homology_episodes import HomologyEpisodes
from gene_annotation_episode.investigation_policy import create_policy
from gene_annotation_episode.native_lifecycle import cancel
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.run_statistics import RunHistory
from gene_annotation_episode.runtime import run_workflow
from test_homology_episode_runtime import prepared, action, commission, wait_terminal
from test_investigation_policy import parameters


class ScriptedSelections:
    def __init__(self, jobs, binding, query, scope):
        self.jobs, self.binding, self.query, self.scope = jobs, binding, query, scope
        self.calls = {}
        self.released = set()
        self.first_monitor_report = None
        self.returned_observation = None

    async def complete(self, episode_id, model_role, instructions, context, schema):
        assert model_role == 'REASONING'
        count = self.calls.get(episode_id, 0)
        self.calls[episode_id] = count + 1
        role = context['working_state'].get('role', 'annotation')
        names = {item['name'] for item in context['tools']}
        assert ('homology.submit' in names) == (role == 'job_launch')
        if role == 'job_launch':
            selected = ('homology.environment', 'homology.configure', 'homology.stage',
                'homology.submit', 'homology.check_handoff')
            if count < len(selected):
                return action(selected[count])
            # This fixture explicitly selects each later read. The real
            # controller, not this stand-in, determines when the child closes.
            return action('episode.history', {'view': 'index', 'offset': 0, 'limit': 1})
        if role == 'job_monitor':
            return action('homology.sample')
        if role == 'job_results':
            if count == 0:
                return action('homology.extract', {'limit': 10})
            snapshot = context['last_local_outcome']['result']['snapshot_ref']
            return action('homology.coverage', {'snapshot_ref': snapshot})

        reports = context['child_reports']
        if not reports:
            assert self.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
            assert context['resource_tool_estimates'][0]['status'] == 'no_matching_history'
            return commission(self.binding, 'job_launch', self.scope, query_ref=self.query, with_yield=True)
        if len(reports) == 1:
            assert reports[-1]['local_credit'] == 1
            assert reports[-1]['closing_yield']['stop_requested'] is True
            return commission(self.binding, 'job_monitor', self.scope,
                handoff=reports[0]['job_handoff'], with_yield=True, with_execution=True)
        if len(reports) == 2:
            report = reports[-1]
            assert report['sample']['state'] == 'running'
            assert report['local_credit'] == 1
            assert len(report['information']) == 1
            assert report['closing_yield']['stop_requested'] is True
            self.first_monitor_report = report
            # Test-only release of native availability. This occurs AFTER
            # numerical monitoring closure, never to manufacture a stop.
            (self.jobs._directory(report['sample']['job_ref'])/'permit-native').touch()
            wait_terminal(self.jobs, report['sample']['job_ref'])
            selected = commission(self.binding, 'job_monitor', self.scope,
                handoff=reports[0]['job_handoff'], prior_sample_refs=[report['sample']['sample_ref']],
                with_yield=True, with_execution=True)
            # A scripted selection informed by the actual closing decision;
            # no production delay formula is implied by this fixture value.
            selected['selection']['delay_seconds'] = .01 if report['closing_yield']['stop_requested'] else 0
            return selected
        if len(reports) == 3:
            report = reports[-1]
            assert report['sample']['outcome'] == 'succeeded'
            assert report['local_credit'] == 1
            assert report['information'][0]['new_completed_timing'] is True
            assert report['closing_yield']['stop_requested'] is True
            assert context['resource_tool_estimates'][0]['status'] == 'available'
            return commission(self.binding, 'job_results', self.scope,
                handoff=reports[0]['job_handoff'], with_yield=True)
        assert len(reports) == 4
        assert reports[-1]['local_credit'] > 0
        assert reports[-1]['closing_yield']['stop_requested'] is True
        self.returned_observation = reports[-1]['comparisons'][0]
        return action('fixture.inspect_returned', {'observation_ref': self.returned_observation})

    async def release(self, episode_id):
        self.released.add(episode_id)


def test_native_roles_and_parent_close_only_from_production_numerical_controller(tmp_path):
    store, tools, query, scope, jobs, previous = prepared(tmp_path, gated=True, statistics=True)
    settings = parameters(jobs.config['registry_ref'])
    policy = create_policy(settings)
    binding = HomologyEpisodes(jobs, parser_policy=previous.parser_policy,
        credit_projector=policy.project_job_credit, credit_binding=policy.job_credit_definition,
        monitoring_projector=policy.project_monitoring_credit,
        monitoring_binding=policy.monitoring_credit_definition, statistics=previous.statistics)
    expectations = ExecutionExpectations.for_homology(jobs, binding.statistics,
        roles=binding.roles, planning_roles=('annotation',))
    provider = ScriptedSelections(jobs, binding, query, scope)
    try:
        result = asyncio.run(run_workflow(store, tools, provider=provider, run_dir=tmp_path/'run',
            project_credit=policy.project_task_credit,
            project_child_credit=policy.project_scientific_child_credit,
            controller_factory=policy.controller_factory, job_episodes=binding,
            execution_expectations=expectations, resource_estimator=ResourceToolEstimator()))
        assert result['state'] == 'yielded' and result['credit'] == 0
        assert store.count('annotation') == store.count('assessment') == 0
        assert provider.first_monitor_report['sample']['state'] == 'running'
        assert tools.seen and set(tools.seen) == {provider.returned_observation}
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM runtime_report_attempts').fetchone()[0] == 4
        episodes = list(store.db.execute('SELECT episode_id,path,state FROM runtime_episodes'))
        assert len(episodes) == 5
        assert {row['episode_id'] for row in episodes} <= provider.released
        for episode in episodes:
            assert episode['state'] == 'yielded'
            observations = [json.loads(row[0]) for row in store.db.execute(
                'SELECT observation FROM runtime_observations WHERE episode_id=? ORDER BY unit_index',
                (episode['episode_id'],))]
            actions = store.db.execute('SELECT count(*) FROM runtime_actions WHERE episode_id=? AND credit IS NOT NULL',
                (episode['episode_id'],)).fetchone()[0]
            assert actions == len(observations) == provider.calls[episode['episode_id']]
            assert observations[-1]['step']['decision']['stop'] is True
            assert all(not observation['step']['decision']['stop'] for observation in observations[:-1])
            closing = observations[-1]['step']['decision']
            assert closing['projected_gain']['upper'] <= closing['continuation_cost'] == .001
            assert all(observation['step']['estimate']['provenance']['estimator']
                == 'completed_signed_score_preferential_yield_v1' for observation in observations)
        timer = dict(store.db.execute('SELECT * FROM runtime_timed_commissions').fetchone())
        assert timer['fired_at'] >= timer['due_at'] >= timer['scheduled_at']
        assert timer['returned_at'] >= timer['fired_at']
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
