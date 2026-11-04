"""Connected host checks using real registries and fixture exit receipts.

No native command is dispatched here. The detached companion executes the
physical native program and exit hook; these tests isolate receipt/replay and
caller behavior with scripted decisions and explicit zero credit units.
"""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

from method_loop.durable import DurableExecutionError, DurableExecutionStore
from gene_annotation_episode import native_events
from gene_annotation_episode import _local_job_worker as worker
from gene_annotation_episode.homology_jobs import FileAsset, HomologyJobs, digest
from gene_annotation_episode.independent_execution import _standard_bindings
from gene_annotation_episode.native_event_information import NativeEventInformation
from gene_annotation_episode.runtime import WorkflowError, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from detached_workflow_fixture import FixtureController, ScriptedProvider, until
from native_event_worker_fixture import EVENT_MODE, POLICY, job_episodes, launch, tool, wait, zero_science


ENDED = {'at': '2026-10-21T14:00:00+00:00', 'monotonic_ns': 123456789, 'boot_id': 'fixture-boot'}


def setup(tmp_path):
    store = Store(tmp_path / 'workspace')
    query, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
    database = tmp_path / 'reference.faa'
    database.write_text('>reference\nMARGKKIGYS\n')
    program = Path(sys.executable).resolve()
    jobs = HomologyJobs.create(tmp_path / 'jobs', executable=FileAsset(program, digest(program)),
        reference_database=FileAsset(database, digest(database)), policy=POLICY,
        max_cpu=1, search_modes=['native_defaults'])
    return store, jobs, query


def run(store, jobs, provider, directory, *, resume=False, enabled=True, root_actions=2):
    return asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
        run_dir=directory, resume=resume, project_credit=zero_science,
        controller_factory=RuntimeControllerFactory(root_actions),
        job_episodes=job_episodes(jobs), native_job_events=EVENT_MODE if enabled else None))


class RuntimeControllerFactory:
    def __init__(self, root_actions):
        self.root_actions = root_actions

    def __call__(self, path, initial):
        return FixtureController(path, initial, self.root_actions if len(path) == 1 else 3)


def fixture_dispatch(monkeypatch, *, fast=False):
    handles = []
    monkeypatch.setattr(worker, 'event_time', lambda: deepcopy(ENDED))
    for name, value in {'SERVICE_RESULT': 'success', 'EXIT_CODE': 'exited', 'EXIT_STATUS': '0'}.items():
        monkeypatch.setenv(name, value)

    def dispatch(handle):
        # The native unit is reserved and registered, but this fixture does not
        # dispatch it. A receipt commits only when explicitly requested below.
        native_events.ensure_native_event_target(handle.path)
        handles.append(handle)
        if fast:
            worker.report(handle.read()['paths']['status'], handle.path)
        return handle
    monkeypatch.setattr('gene_annotation_episode.homology_jobs.start_prepared', dispatch)
    return handles


def rows(store, table, field):
    return [json.loads(row[0]) for row in store.db.execute(f'SELECT {field} FROM {table} ORDER BY rowid')]


def event_cursor(backend):
    with backend._connect() as db:
        return db.execute('SELECT coalesce(max(cursor),0) FROM events').fetchone()[0]


@pytest.mark.parametrize('fast', [True, False], ids=['before-form-delivery', 'after-subscription'])
def test_selected_native_wait_uses_original_form_and_one_zero_gain_observation(tmp_path, monkeypatch, fast):
    store, jobs, query = setup(tmp_path)
    handles = fixture_dispatch(monkeypatch, fast=fast)
    directory, tasks, selected = tmp_path / 'run', [], []

    async def select(context):
        report, = context['child_reports']
        visible, = context['native_event_targets']
        assert report['notifications'] == [visible]
        assert visible['after_cursor'] == 0
        assert context['waiting_support']['native_event_targets'] == [visible]
        assert context['pending_work']['items'] == []
        assert context['current_credit'] == 0
        assert store.count('observation') == 0
        target = visible['target']
        assert target['job_ref'] == report['job']
        selected.append(target)
        backend = DurableExecutionStore(directory / 'episode-execution')
        if not fast:
            async def after_subscription():
                # A selected wait exists before the fixture supplies a physical
                # receipt. Registration by itself leaves it incomplete.
                await until(lambda: store.db.execute('SELECT 1 FROM episode_waits WHERE outcome IS NULL').fetchone())
                await asyncio.sleep(.02)
                assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 4
                assert event_cursor(backend) == 0
                assert store.db.execute('SELECT outcome FROM episode_waits').fetchone()[0] is None
                worker.report(handles[0].read()['paths']['status'], handles[0].path)
            tasks.append(asyncio.create_task(after_subscription()))
        else:
            assert event_cursor(backend) == 1
        return wait(target['handle'])

    async def exercise():
        provider = ScriptedProvider([launch(query, {'subject_refs': [query]}),
            tool('homology.configure'), tool('homology.stage'), tool('homology.submit'), select])
        summary = await run_workflow(store, ToolRegistry(store), provider=provider, run_dir=directory,
            controller_factory=RuntimeControllerFactory(2),
            project_credit=zero_science, job_episodes=job_episodes(jobs), native_job_events=EVENT_MODE)
        await asyncio.gather(*tasks)
        return summary, provider
    try:
        summary, provider = asyncio.run(exercise())
        assert summary['completed_actions'] == 2 and summary['credit'] == 0
        target, = selected
        backend = DurableExecutionStore(directory / 'episode-execution')
        registration = backend.native_target(target['handle'])
        child = store.db.execute('SELECT episode_id FROM runtime_episodes WHERE json_array_length(path)=2').fetchone()[0]
        assert registration['owner_episode_id'] == child
        saved = rows(store, 'episode_waits', 'outcome')[0]
        assert saved['wake_reason'] == 'state_changed'
        assert saved['trigger'] == {'handle': target['handle'], 'cursor': 1}
        assert saved['measured_duration_seconds'] >= 0
        own = [row for row in rows(store, 'runtime_observations', 'observation') if row['label'].startswith('wait:')]
        assert len(own) == 1 and own[0]['step']['delta'] == 0
        assert len(rows(store, 'runtime_observations', 'observation')) == 5
        assert not list(backend.return_page(registration['owner_episode_id'], 0, 10)['items'])
        assert store.count('observation') == 0
        assert json.loads(store.db.execute('SELECT facts FROM runtime_forms').fetchone()[0])['native_event_targets'] == [{'target': target, 'after_cursor': 0}]
        raw = Path(handles[0].read()['paths']['status']).read_bytes()
        disposition = native_events.publish_native_events(handles[0].path)
        assert backend.native_publication(target['handle'], disposition['record_ref'])['receipt_bytes'] == raw
        before = {table: rows(store, table, field) for table, field in (
            ('episode_waits', 'outcome'), ('runtime_observations', 'observation'),
            ('runtime_estimation_contexts', 'data'), ('runtime_model_calls', 'request'))}
        unused = ScriptedProvider([])
        assert run(store, jobs, unused, directory, resume=True) == summary
        assert unused.contexts == []
        assert {table: rows(store, table, field) for table, field in (
            ('episode_waits', 'outcome'), ('runtime_observations', 'observation'),
            ('runtime_estimation_contexts', 'data'), ('runtime_model_calls', 'request'))} == before
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
    finally:
        jobs.close()
        store.close()


def test_unrequested_native_metadata_is_not_received_and_foreign_wait_is_rejected(tmp_path, monkeypatch):
    store, jobs, query = setup(tmp_path)
    handles = fixture_dispatch(monkeypatch)
    def excluded(context):
        assert context['child_reports'] == [{'job': jobs.db.execute('SELECT job_ref FROM orders').fetchone()[0]}]
        assert context['native_event_targets'] == []
        target, = jobs.native_event_targets(jobs.db.execute('SELECT job_ref FROM orders').fetchone()[0])
        return wait(target['handle'])
    def repaired(context):
        assert context['feedback']['category'] == 'action_contract'
        assert context['feedback']['detail'] == 'native_event_information_target_not_visible'
        assert store.db.execute('SELECT count(*) FROM episode_waits').fetchone()[0] == 0
        return tool('state.query', {'refs': [query]})
    try:
        provider = ScriptedProvider([launch(query, {'subject_refs': [query]}, requested=False),
            tool('homology.configure'), tool('homology.stage'), tool('homology.submit'), excluded, repaired])
        result = run(store, jobs, provider, tmp_path / 'run')
        assert result['completed_actions'] == 2 and result['credit'] == 0
        assert len(handles) == 1
        assert store.db.execute('SELECT count(*) FROM episode_waits').fetchone()[0] == 0
    finally:
        jobs.close()
        store.close()


def test_completed_wait_replay_uses_frozen_context_after_control_cleanup(tmp_path, monkeypatch):
    store, jobs, query = setup(tmp_path)
    handles = fixture_dispatch(monkeypatch, fast=True)
    directory = tmp_path / 'run'
    def native_wait(context):
        return wait(context['native_event_targets'][0]['target']['handle'])
    try:
        provider = ScriptedProvider([launch(query, {'subject_refs': [query]}),
            tool('homology.configure'), tool('homology.stage'), tool('homology.submit'), native_wait,
            asyncio.CancelledError()])
        with pytest.raises(asyncio.CancelledError):
            run(store, jobs, provider, directory, root_actions=3)
        original = rows(store, 'episode_waits', 'outcome')
        observations = rows(store, 'runtime_observations', 'observation')
        saved_context = rows(store, 'runtime_model_calls', 'request')[-1]['context']
        assert saved_context['native_event_targets'][0]['after_cursor'] == 1
        receipt_bytes = Path(handles[0].read()['paths']['status']).read_bytes()
        # A cleanup removes the local native reservation. Durable registration,
        # original return form and received wait remain authoritative.
        for value in handles[0].read()['paths'].values():
            Path(value).unlink(missing_ok=True)
        handles[0].path.unlink()
        original_read = NativeEventInformation.read
        def no_new_root_context(self, context):
            assert len(context.path) > 1, 'refreshed completed/saved root context'
            return original_read(self, context)
        monkeypatch.setattr(NativeEventInformation, 'read', no_new_root_context)
        monkeypatch.setattr(NativeEventInformation, 'validate_wait', lambda *a:
            (_ for _ in ()).throw(AssertionError('revalidated completed original wait')))
        def resumed(context):
            assert context == saved_context
            return tool('state.query', {'refs': [query]})
        result = run(store, jobs, ScriptedProvider([resumed]), directory, resume=True, root_actions=3)
        assert result['completed_actions'] == 3 and result['credit'] == 0
        assert rows(store, 'episode_waits', 'outcome') == original
        assert rows(store, 'runtime_observations', 'observation')[:5] == observations
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
        backend = DurableExecutionStore(directory / 'episode-execution')
        target = saved_context['native_event_targets'][0]['target']['handle']
        wake = original[0]['trigger']
        assert wake == {'handle': target, 'cursor': 1}
        with backend._connect() as db:
            record_ref = db.execute('SELECT record_ref FROM native_publications').fetchone()[0]
        assert backend.native_publication(target, record_ref)['receipt_bytes'] == receipt_bytes
    finally:
        jobs.close()
        store.close()


def test_host_recovers_original_export_without_resubmission_or_restamping(tmp_path, monkeypatch):
    store, jobs, query = setup(tmp_path)
    actual_publish = DurableExecutionStore.publish_native_event
    monkeypatch.setattr(DurableExecutionStore, 'publish_native_event', lambda *a, **k:
        (_ for _ in ()).throw(DurableExecutionError('storage_failure')))
    handles = fixture_dispatch(monkeypatch, fast=True)
    directory = tmp_path / 'run'
    try:
        provider = ScriptedProvider([launch(query, {'subject_refs': [query]}),
            tool('homology.configure'), tool('homology.stage'), tool('homology.submit'),
            asyncio.CancelledError()])
        with pytest.raises(asyncio.CancelledError):
            run(store, jobs, provider, directory)
        handle, = handles
        raw = Path(handle.read()['paths']['status']).read_bytes()
        failed = json.loads(Path(handle.read()['paths']['native_events']).read_text())
        assert failed['state'] == 'unavailable' and failed['code'] == 'native_event_storage_unavailable'
        before = rows(store, 'runtime_observations', 'observation')
        backend = DurableExecutionStore(directory / 'episode-execution')
        assert event_cursor(backend) == 0
        monkeypatch.setattr(DurableExecutionStore, 'publish_native_event', actual_publish)
        monkeypatch.setattr(worker, 'report', lambda *a, **k:
            (_ for _ in ()).throw(AssertionError('reentered exit hook')))
        monkeypatch.setattr(worker, 'event_time', lambda:
            (_ for _ in ()).throw(AssertionError('restamped original receipt')))
        monkeypatch.setattr('gene_annotation_episode.homology_jobs.start_prepared', lambda *a, **k:
            (_ for _ in ()).throw(AssertionError('resubmitted original native job')))
        def recovered(context):
            target = context['native_event_targets'][0]['target']
            # The saved decision context is exact even though host assembly has
            # now repaired the missing event from original receipt bytes.
            assert context['native_event_targets'][0]['after_cursor'] == 0
            assert event_cursor(backend) == 1
            return wait(target['handle'])
        result = run(store, jobs, ScriptedProvider([recovered]), directory, resume=True)
        assert result['completed_actions'] == 2 and result['credit'] == 0
        assert Path(handle.read()['paths']['status']).read_bytes() == raw
        repaired = json.loads(Path(handle.read()['paths']['native_events']).read_text())
        assert repaired['state'] == 'recorded' and repaired['cursor'] == 1
        assert backend.native_publication(repaired['target_handle'], repaired['record_ref'])['receipt_bytes'] == raw
        assert rows(store, 'runtime_observations', 'observation')[:4] == before
        assert len(handles) == jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
        for mode in (None, {**EVENT_MODE, 'resource_id': 'foreign-resource'}):
            unused = ScriptedProvider([])
            with pytest.raises(WorkflowError, match='original_native_job_events'):
                asyncio.run(run_workflow(store, ToolRegistry(store), provider=unused,
                    run_dir=directory, resume=True, project_credit=zero_science,
                    controller_factory=RuntimeControllerFactory(2), job_episodes=job_episodes(jobs),
                    native_job_events=mode))
            assert unused.contexts == []
    finally:
        jobs.close()
        store.close()


@pytest.mark.parametrize('bad', [{}, {'version': 'native_job_events_v9', 'resource_id': 'local'},
    {'version': 'native_job_events_v1', 'resource_id': ''}, {**EVENT_MODE, 'extra': True}])
def test_invalid_mode_fails_before_provider_and_creates_no_job(tmp_path, bad):
    store, jobs, query = setup(tmp_path)
    provider = ScriptedProvider([])
    try:
        with pytest.raises(ValueError, match='invalid_native_job_events_binding'):
            asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path / 'run',
                project_credit=zero_science, controller_factory=lambda p, i: FixtureController(p, i, 1),
                job_episodes=job_episodes(jobs), native_job_events=bad))
        assert provider.contexts == [] and jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
    finally:
        jobs.close()
        store.close()


def test_absent_mode_stays_absent_and_resume_cannot_add_remove_or_replace_it(tmp_path):
    store, jobs, query = setup(tmp_path)
    try:
        provider = ScriptedProvider([tool('state.query', {'refs': [query]})])
        summary = run(store, jobs, provider, tmp_path / 'run', enabled=False, root_actions=1)
        context, = provider.contexts
        assert 'native_event_targets' not in context
        assert 'native_event_targets' not in context['waiting_support']
        assert 'native_event_targets' not in context['available_report_facts']
        saved = json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])
        assert 'native_job_events' not in saved
        assert run(store, jobs, ScriptedProvider([]), tmp_path / 'run', resume=True, enabled=False,
                   root_actions=1) == summary
        with pytest.raises(WorkflowError, match='original_native_job_events'):
            run(store, jobs, ScriptedProvider([]), tmp_path / 'run', resume=True, enabled=True, root_actions=1)
        # The standard factory cannot infer an executable job/resource binding.
        with pytest.raises(DurableExecutionError) as failure:
            _standard_bindings(store, tmp_path / 'run', {**saved, 'native_job_events': EVENT_MODE})
        assert failure.value.failure['code'] == 'unavailable_binding'
    finally:
        jobs.close()
        store.close()
