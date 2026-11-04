"""Real tiny native exit hooks wake selected waits in detached Workflow hosts.

The native command is a gated real phmmer over one short protein and reference.
Providers, synchronization gates, zero units and continuation controllers are
explicit engineering fixtures; no configured-model science is claimed.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys

import pytest

from method_loop.archive import ArchivedRecord
from method_loop.durable import DurableExecutionStore, content_digest
from gene_annotation_episode.homology_jobs import FileAsset, HomologyJobs, OUTPUTS, digest
from gene_annotation_episode.native_events import publish_native_events
from gene_annotation_episode.native_lifecycle import collect, release, status
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from detached_workflow_fixture import ScriptedProvider, until
from native_event_worker_fixture import (CONTROLLER_ACTIONS, EVENT_MODE, POLICY, SERVICE_DEFINITION,
    ControllerFactory, application_services, binding_definitions, gates, implementation_sha256,
    job_episodes, launch, make_binding, monitor, tool, wait, zero_science)


PROJECT = Path(__file__).resolve().parents[1]
PROGRAM = PROJECT / 'resources/software/infernal-1.1.5/hmmer/src/phmmer'
PROTEIN = 'MKWVTFISLLFLFSSAYSRGVFRRDTHKSEIAHRFKDLGE'


class Scenario:
    def __init__(self, path, *, fast):
        self.workspace, self.directory, self.jobs_directory = path / 'workspace', path / 'run', path / 'jobs'
        self.fast, self.tasks, self.target = fast, [], None
        self.source_pin = implementation_sha256()
        wrapper = path / 'gated-phmmer'
        wrapper.write_text('#!' + sys.executable + '\nimport os,sys,time\n'
            'open("native-entered", "w").write(str(os.getpid()))\n'
            'while not os.path.exists("permit-native"):\n    time.sleep(.01)\n'
            'os.execv(' + repr(str(PROGRAM)) + ', [' + repr(str(PROGRAM)) + ', *sys.argv[1:]])\n')
        wrapper.chmod(0o700)
        database = path / 'tiny-reference.faa'
        database.write_text('>tiny_native_event_reference\n' + PROTEIN + '\n')
        with Store(self.workspace) as store:
            self.query, = store.create_problem(raw_sequence=PROTEIN, molecule='protein')['subject_refs']
            self.scope = store.validate_scope({'subject_refs': [self.query]})
        jobs = HomologyJobs.create(self.jobs_directory,
            executable=FileAsset(wrapper, digest(wrapper)), reference_database=FileAsset(database, digest(database)),
            policy=POLICY, max_cpu=1, search_modes=['native_defaults'])
        jobs.close()
        self.binding = make_binding(self.workspace, self.directory, self.jobs_directory)
        self.backend = DurableExecutionStore(self.directory / 'episode-execution')

    async def run(self, provider, *, resume=False):
        with Store(self.workspace) as store:
            jobs = HomologyJobs(self.jobs_directory)
            caller = job_episodes(jobs)
            descriptor = caller.as_record()
            try:
                result = await run_workflow(store, ToolRegistry(store), provider=provider,
                    run_dir=self.directory, resume=resume, controller_factory=ControllerFactory(),
                    project_credit=zero_science, job_episodes=caller,
                    execution_binding=self.binding, binding_definitions=binding_definitions(),
                    native_job_events=EVENT_MODE, episode_service_factory=application_services,
                    episode_service_binding=SERVICE_DEFINITION)
                assert caller.native_event_provider is None and caller.as_record() == descriptor
                return result
            finally:
                jobs.close()

    def specs(self):
        with Store(self.workspace) as store:
            return [json.loads(row[0]) for row in store.db.execute(
                'SELECT spec FROM runtime_commission_intents ORDER BY rowid')]

    def native_handle(self):
        from gene_annotation_episode.native_lifecycle import NativeJobHandle
        assert self.target is not None
        return NativeJobHandle(self.jobs_directory / self.target['job_ref'] / 'native.handle.json')

    def native_publication(self):
        handle = self.native_handle()
        path = Path(handle.read()['paths']['native_events'])
        if not path.is_file():
            return None
        value = json.loads(path.read_text())
        return value if value['state'] == 'recorded' else None

    def permit_native(self):
        (self.jobs_directory / self.target['job_ref'] / 'permit-native').write_text('explicit-test-release\n')

    async def overlap(self, context):
        ready = await until(lambda: gates(self.directory, 'launch')[0].exists())
        original = json.loads(gates(self.directory, 'launch')[0].read_text())
        row, = original['targets']
        self.target = row['target']
        state = self.backend.status(original['handle'])
        assert state['liveness'] == 'live' and state['return_available'] is False
        assert state['execution_identity']['pid'] == original['pid'] != os.getpid()
        await until(lambda: (self.jobs_directory / self.target['job_ref'] / 'native-entered').exists())
        assert self.native_publication() is None
        assert context['native_event_targets'] == []  # Storage existence is not delivery.
        assert context['child_reports'] == [] and context['current_credit'] == 0
        assert context['pending_work']['items'][0]['handle'] == original['handle']
        return tool('state.query', {'refs': [self.query]})

    async def await_launch(self, context):
        child, = context['pending_work']['items']
        assert child['role'] == 'job_launch' and not child['return_available']
        async def release_after_selected():
            def selected():
                with Store(self.workspace) as store:
                    row = store.db.execute('SELECT request FROM episode_waits WHERE outcome IS NULL').fetchone()
                    return row is not None and json.loads(row[0])['condition']['events'][0]['handle'] == child['handle']
            await until(selected)
            if self.fast:
                self.permit_native()
                await until(self.native_publication)
                assert self.backend.status(child['handle'])['return_available'] is False
            gates(self.directory, 'launch')[1].write_text('original-return-selected\n')
        self.tasks.append(asyncio.create_task(release_after_selected()))
        return wait(child['handle'], event='returned')

    def after_launch(self, context):
        report, = context['child_reports']
        assert report == {'job': self.target['job_ref'],
                          'notifications': [{'target': self.target, 'after_cursor': 0}]}
        assert context['native_event_targets'] == report['notifications']
        assert context['current_credit'] == 0
        return monitor(self.target['job_ref'], self.scope, self.target['handle'])

    async def native_wait(self, context):
        assert context['feedback'] is None
        await until(lambda: gates(self.directory, 'monitor')[0].exists())
        ready = json.loads(gates(self.directory, 'monitor')[0].read_text())
        assert ready['targets'] == [{'target': self.target, 'after_cursor': 0}]
        pending, = context['pending_work']['items']
        assert pending['role'] == 'monitor' and pending['handle'] == ready['handle']
        assert self.backend.status(pending['handle'])['liveness'] == 'live'
        assert context['waiting_support']['native_event_targets'] == context['native_event_targets']
        assert context['native_event_targets'] == [{'target': self.target, 'after_cursor': 0}]
        if not self.fast:
            assert self.native_publication() is None
            async def release_after_subscription():
                def selected():
                    with Store(self.workspace) as store:
                        return store.db.execute("SELECT 1 FROM episode_waits WHERE outcome IS NULL "
                            "AND json_extract(request,'$.condition.events[0].handle')=?",
                            (self.target['handle'],)).fetchone()
                await until(selected)
                # This scheduling pause checks that identity registration has
                # produced no wake. It is test synchronization, not runtime policy.
                await asyncio.sleep(.02)
                assert self.native_publication() is None
                with Store(self.workspace) as store:
                    assert selected()
                    assert store.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0] == 1
                self.permit_native()
            self.tasks.append(asyncio.create_task(release_after_subscription()))
        return wait(self.target['handle'])

    def after_native(self, context):
        publication = self.native_publication()
        assert publication is not None
        visible, = context['native_event_targets']
        assert visible == {'target': self.target, 'after_cursor': publication['cursor']}
        outcome = context['last_local_outcome']['wait_outcome']
        assert outcome['wake_reason'] == 'state_changed'
        assert outcome['trigger'] == {'handle': self.target['handle'], 'cursor': publication['cursor']}
        assert context['controller']['deltas'] == [0, 0, 0, 0]
        pending, = context['pending_work']['items']
        assert pending['role'] == 'monitor' and pending['return_available'] is False
        assert len(context['child_reports']) == 1
        assert self.backend.status(pending['handle'])['lifecycle_state'] == 'executing'
        with Store(self.workspace) as store:
            assert store.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0] == 1
            assert not store.list('observation') and not store.list('assessment')
        return tool('state.query', {'refs': [self.query]})

    async def returned(self, handle):
        await asyncio.wait_for(self.backend.wait_events({'version': 'event_condition_v1',
            'events': [{'handle': handle, 'event': 'returned', 'after_cursor': 0}],
            'reconsider_at': None}), 20)
        state = self.backend.status(handle)
        value = self.backend.load_return(handle, state['return_id'])
        if value['failure'] is not None:
            diagnostic = value['failure']['diagnostic_ref']
            raise AssertionError(Path(diagnostic).read_text() if diagnostic else value)
        return value

    async def cleanup(self):
        for name in ('launch', 'monitor'):
            gates(self.directory, name)[1].write_text('fixture-cleanup\n')
        jobs = HomologyJobs(self.jobs_directory)
        try:
            handles = [jobs._handle(row[0]) for row in jobs.db.execute('SELECT job_ref FROM orders')]
            for handle in handles:
                handle.path.parent.mkdir(exist_ok=True)
                (handle.path.parent / 'permit-native').write_text('fixture-cleanup\n')
        finally:
            jobs.close()
        for task in self.tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        await asyncio.gather(*(self.returned(spec['handle']) for spec in self.specs()),
                             return_exceptions=True)
        for handle in handles:
            if handle.path.exists():
                await until(lambda: status(handle)['quiescent'])
                release(handle)


@pytest.mark.parametrize('fast', [True, False], ids=['physical-before-delivery', 'physical-after-subscription'])
def test_real_native_exit_wakes_selected_wait_without_admitting_live_child(tmp_path, fast):
    scenario = Scenario(tmp_path, fast=fast)

    async def exercise():
        provider = ScriptedProvider([launch(scenario.query, scenario.scope), scenario.overlap,
            scenario.await_launch, scenario.after_launch, scenario.native_wait, scenario.after_native])
        try:
            summary = await scenario.run(provider)
            await asyncio.gather(*scenario.tasks)
            assert implementation_sha256() == scenario.source_pin
            launch_spec, monitor_spec = scenario.specs()
            identities = [scenario.backend.status(spec['handle'])['execution_identity']
                          for spec in (launch_spec, monitor_spec)]
            assert len({value['pid'] for value in identities}) == 2
            assert os.getpid() not in {value['pid'] for value in identities}
            assert summary['completed_actions'] == 5 and summary['credit'] == 0
            assert summary['state'] == 'yielded_with_pending_work'
            assert summary['pending_handles'] == [monitor_spec['handle']]
            assert summary['scientific_completion'] == 'not_established_by_termination'
            publication = scenario.native_publication()
            handle = scenario.native_handle()
            await until(lambda: status(handle)['terminal'])
            assert collect(handle).returncode == 0
            raw = Path(handle.read()['paths']['status']).read_bytes()
            native_receipt = json.loads(raw)
            assert native_receipt['version'] == 'native_service_exit_receipt_v1'
            assert native_receipt['EXIT_STATUS'] == '0'
            saved = scenario.backend.native_publication(scenario.target['handle'], publication['record_ref'])
            assert saved['receipt_bytes'] == raw
            assert saved['publication']['receipt_sha256'] == hashlib.sha256(raw).hexdigest()
            assert saved['publication']['occurred_at'] == native_receipt['ended']['at']
            assert publish_native_events(handle.path) == publication
            assert Path(handle.read()['paths']['status']).read_bytes() == raw
            assert 'phmmer' in Path(handle.read()['stdout']).read_text()
            assert '[ok]' in Path(handle.read()['stdout']).read_text()
            registration = scenario.backend.native_target(scenario.target['handle'])
            assert registration['owner_episode_id'] == launch_spec['child']['episode_id']
            assert registration['run_id'] == launch_spec['run_id']
            assert registration['resource_id'] == EVENT_MODE['resource_id']
            assert registration['native_identity'] == native_receipt['native_identity']
            with scenario.backend._connect() as db:
                events = [dict(row) for row in db.execute('SELECT cursor,handle,event FROM events ORDER BY cursor')]
                assert db.execute('SELECT count(*) FROM native_targets').fetchone()[0] == 1
                assert db.execute('SELECT count(*) FROM native_publications').fetchone()[0] == 1
                assert db.execute('SELECT count(*) FROM commissions').fetchone()[0] == 2
            native, = [row for row in events if row['handle'] == scenario.target['handle']]
            child_return, = [row for row in events if row['handle'] == launch_spec['handle'] and row['event'] == 'returned']
            assert native['event'] == 'state_changed' and native['cursor'] == publication['cursor']
            assert (native['cursor'] < child_return['cursor']) is fast
            assert len({row['cursor'] for row in events}) == len(events)
            with Store(scenario.workspace) as store:
                root = dict(store.db.execute('SELECT * FROM runtime_episodes WHERE json_array_length(path)=1').fetchone())
                root_id = root['episode_id']
                frozen = {table: [dict(row) for row in store.db.execute('SELECT * FROM ' + table +
                    ' WHERE episode_id=? ORDER BY rowid', (root_id,))] for table in
                    ('runtime_actions', 'runtime_observations', 'runtime_completion_slots')}
                root_archive = scenario.directory / 'archive' / json.loads(root['archive'])['file']
                archive_bytes = root_archive.read_bytes()
                observations = [json.loads(row['observation']) for row in frozen['runtime_observations']]
                assert [row['decision_index'] for row in observations] == [1, 2, 0, 4, 5]
                assert [row['step']['delta'] for row in observations] == [0] * 5
                own_native = [row for row in observations if row['label'] == 'wait:4']
                assert len(own_native) == 1
                waits = [json.loads(row[0]) for row in store.db.execute('SELECT outcome FROM episode_waits ORDER BY rowid')]
                assert [value['wake_reason'] for value in waits] == ['returned', 'state_changed']
                assert waits[1]['trigger'] == {'handle': scenario.target['handle'], 'cursor': publication['cursor']}
                assert store.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0] == 1
                settings = json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])
                assert settings['native_job_events'] == EVENT_MODE
            # A parent's closure does not cancel the selected monitor. Its
            # later form is durable but never reprices the closed parent.
            gates(scenario.directory, 'monitor')[1].write_text('parent-already-yielded\n')
            returned = await asyncio.gather(*(scenario.returned(spec['handle']) for spec in (launch_spec, monitor_spec)))
            for spec, result, identity in zip((launch_spec, monitor_spec), returned, identities):
                assert result['commission_sha256'] == content_digest(spec)
                assert scenario.backend.start(spec['handle'])['execution_identity'] == identity
                assert spec['runtime_binding'] == scenario.binding
                assert result['completion']['units_consumed'] == CONTROLLER_ACTIONS[spec['child']['role']]
                assert result['form']['notifications'] == [{'target': scenario.target, 'after_cursor': 0}]
                calls = [json.loads(line) for line in (scenario.directory / (
                    'native-event-calls-' + spec['handle'] + '.jsonl')).read_text().splitlines()]
                assert len(calls) == CONTROLLER_ACTIONS[spec['child']['role']]
                assert {call['pid'] for call in calls} == {identity['pid']}
                for name in ('episode_archive', 'result_archive', 'facts_archive'):
                    ref = result[name]
                    assert ArchivedRecord(scenario.directory / 'archive' / ref['file'],
                        ref['sha256'], ref['index_sha256']).load()
                retirement_path = scenario.directory / ('native-event-retired-' + spec['handle'] + '.json')
                await until(retirement_path.exists)
                retirement = json.loads(retirement_path.read_text())
                assert retirement['active_controllers'] == retirement['active_episodes'] == 0
                assert set(retirement['released']) == {spec['child']['episode_id']}
            assert returned[1]['form']['selected_target'] == scenario.target['handle']
            unused = ScriptedProvider([])
            assert await scenario.run(unused, resume=True) == summary
            assert unused.contexts == []
            with Store(scenario.workspace) as store:
                assert dict(store.db.execute('SELECT * FROM runtime_episodes WHERE episode_id=?', (root_id,)).fetchone()) == root
                for table, expected in frozen.items():
                    assert [dict(row) for row in store.db.execute('SELECT * FROM ' + table +
                        ' WHERE episode_id=? ORDER BY rowid', (root_id,))] == expected
                assert root_archive.read_bytes() == archive_bytes
                assert store.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0] == 1
            jobs = HomologyJobs(scenario.jobs_directory)
            try:
                assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
            finally:
                jobs.close()
            assert implementation_sha256() == scenario.source_pin
        finally:
            await scenario.cleanup()

    asyncio.run(exercise())
