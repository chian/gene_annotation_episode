"""Real local subprocess lifecycle; no live model, account, network or deadlines."""
import asyncio
import json
import os
import signal

import pytest

from gene_annotation_episode.episodic_workflow.root.tests.model_transport_support import (
    LiteralPresentationSession, ControlledConnection, actual_session, assert_exited,
    configuration, ensure_closed, observed, requests)


def test_normal_close_terms_and_awaits_actual_group(tmp_path, monkeypatch):
    sent = []
    original = os.killpg
    def recording(group, signum):
        sent.append((group, signum))
        return original(group, signum)
    monkeypatch.setattr(os, 'killpg', recording)
    async def exercise():
        async with actual_session(tmp_path, descendant=True) as (session, control):
            ready = await observed(control / 'ready.json')
            await observed(control / 'initialized.json')
            assert session.process.returncode is None
        assert_exited(session, ready)
        assert session.process.returncode == 0
        assert sent == [(ready['pgid'], signal.SIGTERM)]
        for pid in (ready['pid'], ready['child_pid']):
            assert json.loads((control / ('signal-' + str(pid) + '.json')).read_text()) == {
                'pid': pid, 'signal': signal.SIGTERM}
        assert json.loads((control / 'reaped.json').read_text()) == {'pid': ready['child_pid'], 'exitcode': 0}
        assert [r['method'] for r in requests(control)] == ['initialize', 'initialized']
    asyncio.run(exercise())


def test_cancel_initialize_recovers_actual_process_and_drains(tmp_path):
    async def exercise():
        control = tmp_path / 'control'
        session = LiteralPresentationSession(configuration(control, hold_initialize=True, descendant=True),
                                              tmp_path / 'session', tmp_path)
        entering = asyncio.create_task(session.__aenter__())
        try:
            ready = await observed(control / 'ready.json', entering)
            await observed(control / 'initialize.json', entering)
            entering.cancel()
            with pytest.raises(asyncio.CancelledError):
                await entering
            assert_exited(session, ready)
            assert session.process.returncode == -signal.SIGKILL
            failure = json.loads((session.directory / 'startup-failure.json').read_text())
            assert failure['error'].startswith('CancelledError:')
            assert failure['returncode_before_cleanup'] is None
            assert failure['returncode_after_cleanup'] == session.process.returncode
        finally:
            if not entering.done():
                entering.cancel()
            await asyncio.gather(entering, return_exceptions=True)
            await ensure_closed(session)
    asyncio.run(exercise())


def test_cancel_during_spawn_retains_one_real_spawn(tmp_path, monkeypatch):
    async def exercise():
        spawned, release = asyncio.Event(), asyncio.Event()
        original = asyncio.create_subprocess_exec
        processes = []
        async def delayed_return(*args, **kwargs):
            process = await original(*args, **kwargs)
            processes.append(process)
            spawned.set()
            await release.wait()
            return process
        monkeypatch.setattr(asyncio, 'create_subprocess_exec', delayed_return)
        control = tmp_path / 'control'
        session = LiteralPresentationSession(configuration(control, descendant=True),
                                              tmp_path / 'session', tmp_path)
        entering = asyncio.create_task(session.__aenter__())
        spawn_observation = asyncio.create_task(spawned.wait())
        try:
            await asyncio.wait((spawn_observation, entering), return_when=asyncio.FIRST_COMPLETED)
            if entering.done():
                entering.result()
                raise AssertionError('Entry completed before the controlled spawn-return barrier')
            assert spawned.is_set()
            ready = await observed(control / 'ready.json', entering)
            assert session.process is None  # Actual Process exists behind the test barrier.
            entering.cancel()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await entering
            assert len(processes) == 1 and session.process is processes[0]
            assert_exited(session, ready)
            assert session.process.returncode == -signal.SIGKILL
            assert not (control / 'initialize.json').exists()
            failure = json.loads((session.directory / 'startup-failure.json').read_text())
            assert failure['returncode_after_cleanup'] == -signal.SIGKILL
        finally:
            release.set()
            if not entering.done():
                entering.cancel()
            await asyncio.gather(entering, return_exceptions=True)
            if not spawn_observation.done():
                spawn_observation.cancel()
            await asyncio.gather(spawn_observation, return_exceptions=True)
            await ensure_closed(session)
    asyncio.run(exercise())


def test_cancellation_during_shielded_close_forces_owned_group(tmp_path, monkeypatch):
    sent = []
    original = os.killpg
    def recording(group, signum):
        sent.append((group, signum))
        return original(group, signum)
    monkeypatch.setattr(os, 'killpg', recording)
    async def exercise():
        control = tmp_path / 'control'
        session = LiteralPresentationSession(configuration(control, ignore_term=True, descendant=True),
                                              tmp_path / 'session', tmp_path)
        closing = None
        try:
            await session.__aenter__()
            ready = await observed(control / 'ready.json')
            closing = asyncio.create_task(session.__aexit__(None, None, None))
            await observed(control / ('signal-' + str(ready['pid']) + '.json'), closing)
            assert session.process.returncode is None and not closing.done()
            closing.cancel()
            with pytest.raises(asyncio.CancelledError):
                await closing
            assert_exited(session, ready)
            assert session.process.returncode == -signal.SIGKILL
            assert sent == [(ready['pgid'], signal.SIGTERM), (ready['pgid'], signal.SIGKILL)]
        finally:
            if closing is not None and not closing.done():
                closing.cancel()
                await asyncio.gather(closing, return_exceptions=True)
            await ensure_closed(session)
    asyncio.run(exercise())


def test_model_connection_cancel_turn_retires_actual_worker(tmp_path):
    async def exercise():
        control = tmp_path / 'control'
        config = configuration(control, hold_turn=True, descendant=True)
        connection = ControlledConnection(config, tmp_path / 'connection', tmp_path)
        calling = asyncio.create_task(connection.complete('controlled-episode', 'REASONING',
            'Controlled protocol only', {}, {'type': 'object'}))
        try:
            ready = await observed(control / 'ready.json', calling)
            await observed(control / 'turn-started.json', calling)
            worker = connection.workers[('controlled-episode', 'REASONING')]
            calling.cancel()
            with pytest.raises(asyncio.CancelledError):
                await calling
            assert_exited(worker, ready)
            assert not connection.workers and not connection.worker_lock.locked()
            assert not worker.sessions and not worker.pending and not worker.compaction_epochs
            receipt = json.loads((connection.directory / 'retired-sessions/retired-00001.json').read_text())
            assert receipt['provider_process'] == ready['pid']
            assert receipt['provider_exit_code'] == -signal.SIGKILL
            assert receipt['local_session_removed'] is True and receipt['remaining_active_workers'] == 0
            assert sum(r['method'] == 'turn/start' for r in requests(control)) == 1
        finally:
            if not calling.done():
                calling.cancel()
            await asyncio.gather(calling, return_exceptions=True)
            await connection.__aexit__(asyncio.CancelledError, None, None)
    asyncio.run(exercise())
