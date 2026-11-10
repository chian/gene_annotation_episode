"""Application consumer checks with real detached ordinary-Workflow workers.

Only provider decisions, gates, credit units and controller stopping are fixtures.
These checks exercise actual Store/backend/subprocess/form/admission/wait paths;
they do not establish configured-model scientific or numerical validity.
"""
import asyncio
from copy import deepcopy
import json
import os

import pytest

from method_loop.archive import ArchivedRecord
from method_loop.durable import DurableExecutionStore
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from detached_workflow_fixture import (ControllerFactory, FixtureTools, ScriptedProvider,
    child_credit, commission, gate_paths, make_binding, parent_credit, until)


class InterruptedParent(RuntimeError):
    pass


class Scenario:
    def __init__(self, path):
        self.workspace, self.directory = path / 'workspace', path / 'run'
        with Store(self.workspace) as store:
            self.subject = store.create_problem(raw_sequence='MARGKKIGYS',
                molecule='protein', role='protein')['subject_refs'][0]
        self.binding = make_binding(self.workspace, self.directory)
        self.backend = DurableExecutionStore(self.directory / 'episode-execution')
        self.tasks = []

    async def run(self, provider, *, completed_actions, resume=False):
        with Store(self.workspace) as store:
            return await run_workflow(store, FixtureTools(store), provider=provider,
                run_dir=self.directory, resume=resume,
                controller_factory=ControllerFactory(completed_actions),
                project_credit=parent_credit, project_child_credit=child_credit,
                execution_binding=self.binding, episode_binding_descriptors=[],
                binding_definitions={
                    'credit': {'kind': 'fixture_received_source_count',
                               'unit': 'one_distinct_received_fixture_source'},
                    'scientific_child_credit': {'kind': 'fixture_received_source_count',
                               'unit': 'one_distinct_received_fixture_source'},
                    'controller': {'kind': 'fixture_completed_action_stop',
                                   'completed_actions': completed_actions}})

    def root(self, store):
        return dict(store.db.execute("SELECT * FROM runtime_episodes WHERE "
            'json_array_length(path)=1').fetchone())

    def observations(self, store):
        return [json.loads(row[0]) for row in store.db.execute(
            'SELECT observation FROM runtime_observations WHERE episode_id=? ORDER BY unit_index',
            (self.root(store)['episode_id'],))]

    def frozen_slots(self, store):
        return [json.loads(row[0]) for row in store.db.execute(
            'SELECT slot FROM runtime_completion_slots WHERE episode_id=? ORDER BY sequence',
            (self.root(store)['episode_id'],))]

    def spec(self):
        with Store(self.workspace) as store:
            rows = list(store.db.execute('SELECT spec FROM runtime_commission_intents'))
            assert len(rows) == 1
            return json.loads(rows[0][0])

    def supplied_metadata_reasoning(self):
        # A permitted root action using actual caller-supplied metadata. The
        # fixture's unchanged source-count projection assigns this zero gain.
        with Store(self.workspace) as store:
            commit = {name: [] for name in store.reasoning_schema()['required']}
            commit['hypotheses'] = [{'alias': 'supplied_molecule',
                'subject_refs': [self.subject], 'predicate': 'molecule_type',
                'value': {'type': 'enum', 'value': store.get_input(self.subject)['molecule']},
                'context_refs': []}]
        return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}

    async def child_live(self, context):
        pending = context['pending_work']['items']
        assert len(pending) == 1
        handle = pending[0]['handle']
        ready, release = gate_paths(self.directory, handle)
        await until(ready.exists)
        status = self.backend.status(handle)
        assert status['liveness'] == 'live' and not status['return_available']
        assert status['execution_identity']['pid'] != os.getpid()
        assert json.loads(ready.read_text())['pid'] == status['execution_identity']['pid']
        assert not release.exists()
        with Store(self.workspace) as store:
            root = self.root(store)
            # Dispatch is pending; neither child internal turns nor starting a
            # process have supplied a completed parent observation or credit.
            assert self.observations(store) == []
            action = store.db.execute('SELECT result,credit FROM runtime_actions '
                'WHERE episode_id=? AND decision_index=0', (root['episode_id'],)).fetchone()
            assert json.loads(action['result'])['status'] == 'pending'
            assert action['credit'] is None
            assert context['child_reports'] == [] and context['current_credit'] == 0
        return self.supplied_metadata_reasoning()

    async def select_wait(self, context):
        pending = context['pending_work']['items']
        assert len(pending) == 1 and not pending[0]['return_available']
        assert context['current_credit'] == 0 and context['child_reports'] == []
        handle = pending[0]['handle']
        status = self.backend.status(handle)
        assert status['liveness'] == 'live'
        with Store(self.workspace) as store:
            observations = self.observations(store)
            assert [row['decision_index'] for row in observations] == [1]
            assert observations[0]['step']['delta'] == 0
        condition = {'version': 'event_condition_v1', 'events': [
            {'handle': handle, 'event': 'returned', 'after_cursor': 0}], 'reconsider_at': None}

        async def release_after_selection():
            # Hold the fixture until the application durably selected the wait.
            # This keeps the required wait -> return order independent of PID
            # startup speed. No runtime action is chosen by this synchronization.
            def selected():
                with Store(self.workspace) as store:
                    return store.db.execute(
                        'SELECT 1 FROM episode_waits WHERE outcome IS NULL').fetchone()
            await until(selected)
            ready, release = gate_paths(self.directory, handle)
            assert ready.exists()
            release.write_text('selected-wait\n')
        self.tasks.append(asyncio.create_task(release_after_selection()))
        return {'selection': {'kind': 'wait', 'condition': condition}, 'report_update': {}}

    def followup(self, context):
        assert context['pending_work']['items'] == []
        assert context['current_credit'] == 1
        assert len(context['child_reports']) == 1
        report = context['child_reports'][0]
        assert report['finding'] == 'qualified'
        assert report['subjects'] == [self.subject] and report['child_credit'] == 1
        assert len(report['sources']) == 1
        with Store(self.workspace) as store:
            source = store.get(report['sources'][0])
            assert source['provider'] == 'fixture.detached_workflow' and source['accession'] == 'child_one'
            assert [row['decision_index'] for row in self.observations(store)] == [1, 2, 0]
        return self.supplied_metadata_reasoning()

    async def returned(self):
        spec = self.spec()
        await asyncio.wait_for(self.backend.wait_events({'version': 'event_condition_v1',
            'events': [{'handle': spec['handle'], 'event': 'returned', 'after_cursor': 0}],
            'reconsider_at': None}), 20)
        status = self.backend.status(spec['handle'])
        returned = self.backend.load_return(spec['handle'], status['return_id'])
        assert returned['outcome'] == 'closed', returned
        assert returned['failure'] is None
        return returned

    async def cleanup(self):
        # Fixture failures still release selected workers; no descendant is
        # cancelled as a side effect of a parent yield or interruption.
        for ready in (self.directory / 'fixture-gates').glob('*.ready.json'):
            ready.with_name(ready.name.removesuffix('.ready.json') + '.release').write_text('fixture-cleanup\n')
        with Store(self.workspace) as store:
            installed = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='runtime_commission_intents'").fetchone()
            if installed:
                for row in store.db.execute('SELECT handle FROM runtime_commission_intents'):
                    gate_paths(self.directory, row[0])[1].write_text('fixture-cleanup\n')
        for task in self.tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)


@pytest.fixture
def scenario(tmp_path):
    return Scenario(tmp_path)


def assert_original_child_closure(scenario, returned):
    spec = scenario.spec()
    assert returned['completion']['units_consumed'] == 2
    assert spec['runtime_binding'] == scenario.binding
    assert spec['child']['scope'] == spec['child']['request']['message']['scope']
    assert spec['child']['request']['goal']['parent_goal_id'] == spec['parent']['goal_id']
    calls = [json.loads(line) for line in (scenario.directory / 'fixture-child-calls.jsonl').read_text().splitlines()]
    assert len(calls) == 2
    assert len({call['pid'] for call in calls}) == 1
    assert all(call['episode_id'] == spec['child']['episode_id'] for call in calls)
    assert calls[1]['context']['last_local_outcome']['result']['label'] == 'child_one'
    assert calls[1]['context']['current_report_update'] == {'finding': 'unknown'}
    for field in ('episode_archive', 'result_archive', 'facts_archive'):
        descriptor = returned[field]
        assert ArchivedRecord(scenario.directory / 'archive' / descriptor['file'],
            descriptor['sha256'], descriptor['index_sha256']).load()
    with Store(scenario.workspace) as store:
        saved = store.db.execute('SELECT facts,form FROM runtime_forms WHERE episode_id=?',
            (spec['child']['episode_id'],)).fetchone()
        assert json.loads(saved['form']) == returned['form']
        assert json.loads(saved['facts'])['changed_record_refs'] == returned['form']['sources']
        assert store.db.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?',
            (spec['child']['episode_id'],)).fetchone()[0] == 2
    retirement = json.loads((scenario.directory / ('fixture-retired-' + spec['handle'] + '.json')).read_text())
    assert retirement['active_controllers'] == retirement['active_episodes'] == 0
    assert set(retirement['released']) == {spec['child']['episode_id']}


def test_parent_own_action_then_selected_wait_original_return_and_followup(scenario):
    async def exercise():
        provider = ScriptedProvider([commission(scenario.subject), scenario.child_live,
            scenario.select_wait, scenario.followup])
        try:
            summary = await scenario.run(provider, completed_actions=4)
            returned = await scenario.returned()
            await asyncio.gather(*scenario.tasks)
            return summary, returned, provider
        finally:
            await scenario.cleanup()
    summary, returned, provider = asyncio.run(exercise())
    assert summary['state'] == 'yielded' and summary['pending_handles'] == []
    assert summary['completed_actions'] == 4 and summary['credit'] == 1
    assert summary['scientific_completion'] == 'not_established_by_termination'
    assert len(provider.contexts) == 4
    assert_original_child_closure(scenario, returned)
    with Store(scenario.workspace) as store:
        observations = scenario.observations(store)
        assert [row['decision_index'] for row in observations] == [1, 2, 0, 3]
        assert [row['step']['delta'] for row in observations] == [0, 0, 1, 0]
        own = store.db.execute("SELECT action,result FROM runtime_actions WHERE episode_id=? "
            "AND json_extract(action,'$.kind')='reason' ORDER BY decision_index",
            (scenario.root(store)['episode_id'],)).fetchall()
        assert len(own) == 2
        for action, result in own:
            assert json.loads(action) == scenario.supplied_metadata_reasoning()['selection']
            for ref in json.loads(result)['record_refs']:
                assert store.get(ref)['record_type'] != 'source'
        assert [row['original_decision_index'] for row in scenario.frozen_slots(store)] == [1, 2, 0, 3]
        wait = json.loads(store.db.execute('SELECT outcome FROM episode_waits').fetchone()[0])
        assert wait['wake_reason'] == 'returned'
        assert wait['measured_duration_seconds'] >= 0
        context = json.loads(store.db.execute('SELECT data FROM runtime_estimation_contexts '
            'WHERE episode_id=? AND decision_index=2', (scenario.root(store)['episode_id'],)).fetchone()[0])
        assert context['pending_work_at_selection']['items'][0]['handle'] == returned['handle']
        assert context['pending_work_after_action']['items'][0]['return_available'] is True
        assert context['own_completed_action_history'][0]['decision_index'] == 1
        assert store.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0] == 1
    assert scenario.backend.status(returned['handle'])['lifecycle_state'] == 'admitted'


def test_parent_yield_suspends_until_child_return_then_preserves_closed_history(scenario):
    async def exercise():
        provider = ScriptedProvider([commission(scenario.subject), scenario.child_live])
        parent = asyncio.create_task(scenario.run(provider, completed_actions=1))
        scenario.tasks.append(parent)
        try:
            def stopped_selecting():
                if parent.done():
                    parent.result()
                    raise AssertionError('parent closed before its selected child returned')
                with Store(scenario.workspace) as store:
                    installed = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                        "AND name='runtime_observations'").fetchone()
                    if installed is None:
                        return False
                    row = store.db.execute('SELECT o.observation FROM runtime_observations o '
                        'JOIN runtime_episodes e ON e.episode_id=o.episode_id '
                        'WHERE json_array_length(e.path)=1 ORDER BY o.unit_index DESC LIMIT 1').fetchone()
                    return row is not None and json.loads(row[0])['step']['stop']

            await until(stopped_selecting)
            spec = scenario.spec()
            status = scenario.backend.status(spec['handle'])
            assert status['liveness'] == 'live' and not status['return_available']
            with Store(scenario.workspace) as store:
                active = scenario.root(store)
                assert active['state'] == 'active'
                assert active['completion'] is None and active['archive'] is None
                stopped_observations = deepcopy(scenario.observations(store))
                assert [row['decision_index'] for row in stopped_observations] == [1]
                assert stopped_observations[0]['step']['delta'] == 0
                assert store.db.execute('SELECT count(*) FROM runtime_report_attempts').fetchone()[0] == 0
                pending = store.db.execute('SELECT result,credit FROM runtime_actions WHERE episode_id=? '
                    'AND decision_index=0', (spec['parent']['episode_id'],)).fetchone()
                assert json.loads(pending['result'])['status'] == 'pending' and pending['credit'] is None
            assert not parent.done() and len(provider.contexts) == 2
            gate_paths(scenario.directory, spec['handle'])[1].write_text('parent-selection-yielded\n')
            summary = await parent
            returned = await scenario.returned()
            assert len(provider.contexts) == 2
            with Store(scenario.workspace) as store:
                observations = deepcopy(scenario.observations(store))
                assert observations[:1] == stopped_observations
                assert [row['decision_index'] for row in observations] == [1, 0]
                assert [row['step']['delta'] for row in observations] == [0, 1]
                slots = deepcopy(scenario.frozen_slots(store))
                assert [row['original_decision_index'] for row in slots] == [1, 0]
                assert store.db.execute("SELECT count(*) FROM runtime_actions "
                    "WHERE json_extract(action,'$.kind')='wait'").fetchone()[0] == 0
                closed = scenario.root(store)
                assert closed['state'] == 'yielded'
                descriptor = json.loads(closed['archive'])
                archive_path = scenario.directory / 'archive' / descriptor['file']
                archive_bytes = archive_path.read_bytes()
            unused = ScriptedProvider([])
            resumed = await scenario.run(unused, completed_actions=1, resume=True)
            assert resumed == summary and unused.contexts == []
            with Store(scenario.workspace) as store:
                assert scenario.observations(store) == observations
                assert scenario.frozen_slots(store) == slots
                assert scenario.root(store) == closed
                assert archive_path.read_bytes() == archive_bytes
                assert store.db.execute('SELECT count(*) FROM runtime_report_attempts').fetchone()[0] == 1
                assert store.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0] == 1
                action = store.db.execute('SELECT result,credit FROM runtime_actions WHERE episode_id=? '
                    'AND decision_index=0', (spec['parent']['episode_id'],)).fetchone()
                assert json.loads(action['result'])['status'] == 'completed' and action['credit'] == 1
            assert scenario.backend.status(spec['handle'])['lifecycle_state'] == 'admitted'
            return summary, returned
        finally:
            await scenario.cleanup()
    summary, returned = asyncio.run(exercise())
    assert summary['state'] == 'yielded'
    assert summary['pending_handles'] == []
    assert summary['completed_actions'] == 2 and summary['credit'] == 1
    assert summary['scientific_completion'] == 'not_established_by_termination'
    assert_original_child_closure(scenario, returned)


def test_restart_reuses_live_handle_pid_and_replays_original_completion_order(scenario):
    async def exercise():
        try:
            first = ScriptedProvider([commission(scenario.subject), scenario.child_live,
                InterruptedParent('interrupt with live child')])
            with pytest.raises(InterruptedParent):
                await scenario.run(first, completed_actions=4)
            spec = scenario.spec()
            identity = scenario.backend.status(spec['handle'])['execution_identity']
            assert scenario.backend.status(spec['handle'])['liveness'] == 'live'
            with Store(scenario.workspace) as store:
                original_observation = deepcopy(scenario.observations(store))
            second = ScriptedProvider([scenario.select_wait,
                InterruptedParent('interrupt after child completion')])
            with pytest.raises(InterruptedParent):
                await scenario.run(second, completed_actions=4, resume=True)
            await asyncio.gather(*scenario.tasks)
            assert scenario.backend.start(spec['handle'])['execution_identity'] == identity
            with Store(scenario.workspace) as store:
                before = deepcopy(scenario.observations(store))
                slots = deepcopy(scenario.frozen_slots(store))
                assert before[:1] == original_observation
                assert [row['decision_index'] for row in before] == [1, 2, 0]
            final_provider = ScriptedProvider([scenario.followup])
            summary = await scenario.run(final_provider, completed_actions=4, resume=True)
            with Store(scenario.workspace) as store:
                assert scenario.observations(store)[:3] == before
                assert scenario.frozen_slots(store)[:3] == slots
                assert store.db.execute('SELECT count(*) FROM runtime_commission_intents').fetchone()[0] == 1
                assert store.db.execute('SELECT count(*) FROM detached_fixture_operations').fetchone()[0] == 2
            returned = await scenario.returned()
            assert scenario.backend.start(spec['handle'])['execution_identity'] == identity
            assert len(final_provider.contexts) == 1
            return summary, returned
        finally:
            await scenario.cleanup()
    summary, returned = asyncio.run(exercise())
    assert summary['completed_actions'] == 4 and summary['credit'] == 1
    assert summary['pending_handles'] == []
    assert_original_child_closure(scenario, returned)


def test_controller_stop_after_wait_admits_original_child_return(scenario):
    async def exercise():
        try:
            provider = ScriptedProvider([commission(scenario.subject), scenario.child_live,
                scenario.select_wait])
            summary = await scenario.run(provider, completed_actions=2)
            await asyncio.gather(*scenario.tasks)
            returned = await scenario.returned()
            with Store(scenario.workspace) as store:
                observations = scenario.observations(store)
                assert [row['decision_index'] for row in observations] == [1, 2, 0]
                assert [row['step']['delta'] for row in observations] == [0, 0, 1]
                assert observations[1]['step']['stop'] is True
                assert [row['original_decision_index'] for row in scenario.frozen_slots(store)] == [1, 2, 0]
                assert store.db.execute('SELECT count(*) FROM runtime_report_attempts').fetchone()[0] == 1
                assert store.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0] == 1
            assert len(provider.contexts) == 3
            assert scenario.backend.status(returned['handle'])['lifecycle_state'] == 'admitted'
            assert scenario.backend.status(returned['handle'])['acknowledgment_id'] is not None
            return summary, returned
        finally:
            await scenario.cleanup()
    summary, returned = asyncio.run(exercise())
    assert summary['state'] == 'yielded'
    assert summary['pending_handles'] == []
    assert summary['completed_actions'] == 3 and summary['credit'] == 1
    assert summary['scientific_completion'] == 'not_established_by_termination'
    assert_original_child_closure(scenario, returned)
