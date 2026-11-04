"""Selected waits through the application's real shared source and event backend."""
import asyncio
from datetime import datetime, timedelta, timezone
import json

from gene_annotation_episode.runtime import run_workflow
from test_runtime import FixtureController, ScriptedProvider, fixture_credit, setup


def test_selected_time_wait_is_one_zero_gain_observation_and_replays_without_waiting(tmp_path):
    store, tools = setup(tmp_path)
    deadline = (datetime.now(timezone.utc) + timedelta(milliseconds=10)).isoformat()
    selection = {'kind': 'wait', 'condition': {'version': 'event_condition_v1',
        'events': [], 'reconsider_at': deadline}}
    provider = ScriptedProvider([{'selection': selection, 'report_update': {}}])
    factory = lambda path, initial: FixtureController(str(path), initial, 1)
    kwargs = {'run_dir': tmp_path / 'run', 'controller_factory': factory,
              'project_credit': fixture_credit}
    summary = asyncio.run(run_workflow(store, tools, provider=provider, **kwargs))
    assert summary['completed_actions'] == 1
    row = store.db.execute('SELECT observation FROM runtime_observations').fetchone()
    observation = json.loads(row[0])
    assert observation['step']['delta'] == 0
    context = json.loads(store.db.execute('SELECT data FROM runtime_estimation_contexts').fetchone()[0])
    assert context['version'] == 'completed_action_estimation_context_v5'
    assert context['current_completion_evidence']['unit_ref'] == observation['unit_ref']
    assert context['wait_outcome']['wake_reason'] == 'reconsideration'
    assert context['wait_outcome']['measured_duration_seconds'] >= 0
    assert context['pending_work_at_selection']['items'] == []
    assert context['pending_work_after_action']['items'] == []
    saved = store.db.execute('SELECT outcome FROM episode_waits').fetchone()[0]
    unused = ScriptedProvider([])
    assert asyncio.run(run_workflow(store, tools, provider=unused, resume=True, **kwargs)) == summary
    assert not unused.contexts
    assert store.db.execute('SELECT outcome FROM episode_waits').fetchone()[0] == saved
    assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 1


def test_proposed_wait_uses_own_completed_history_before_the_episode_selects_waiting(tmp_path):
    store, tools = setup(tmp_path)
    condition = {'version': 'event_condition_v1', 'events': [],
                 'reconsider_at': '2026-01-01T00:00:00+00:00'}

    def select_wait(context):
        estimate = context['last_local_outcome']['result']
        assert estimate['scientific_gain'] is None and estimate['monitoring_gain'] is None
        assert store.db.execute('SELECT count(*) FROM episode_waits').fetchone()[0] == 0
        history = context['waiting_support']['own_completed_action_history']
        assert len(history) == 1 and history[0]['decision_index'] == 0
        assert history[0]['controller_step']['delta'] == 0
        assert any(item['name'] == 'episode.estimate_wait' for item in context['tools'])
        return {'selection': {'kind': 'wait', 'condition': condition}, 'report_update': {}}

    provider = ScriptedProvider([
        {'selection': {'kind': 'tool', 'tool': 'episode.estimate_wait',
                       'arguments': {'condition': condition}}, 'report_update': {}},
        select_wait])
    controllers = []
    def factory(path, initial):
        controller = FixtureController(str(path), initial, 2)
        controllers.append(controller)
        return controller

    summary = asyncio.run(run_workflow(store, tools, provider=provider, run_dir=tmp_path / 'run',
        controller_factory=factory, project_credit=fixture_credit))
    assert summary['completed_actions'] == 2 and controllers[0].scores == [0, 0]
    assert store.db.execute('SELECT count(*) FROM episode_waits').fetchone()[0] == 1
    saved = json.loads(store.db.execute('SELECT data FROM runtime_estimation_contexts '
        'WHERE decision_index=1').fetchone()[0])
    history = saved['own_completed_action_history']
    assert len(history) == 1 and history[0]['decision_index'] == 0
    assert saved['wait_estimate_at_selection']['scientific_gain'] is None
