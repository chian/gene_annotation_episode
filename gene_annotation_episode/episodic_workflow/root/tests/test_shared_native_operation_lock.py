"""Actual filesystem locking and cancellation; no scientific/native worker job."""
import asyncio
from contextlib import suppress
import errno
import fcntl
import os
import threading

import pytest

from gene_annotation_episode.native_operation_lock import _action_lock


def assert_unlocked(path):
    descriptor = os.open(path, os.O_RDWR)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


def test_real_lock_serializes_two_callers(tmp_path):
    async def run():
        first_entered, release_first, second_entered = (asyncio.Event() for _ in range(3))
        order = []
        async def first():
            async with _action_lock(tmp_path):
                order.append('first-enter'); first_entered.set()
                await release_first.wait()
                order.append('first-leave')
        async def second():
            async with _action_lock(tmp_path):
                order.append('second-enter'); second_entered.set()
        one = asyncio.create_task(first())
        await first_entered.wait()
        two = asyncio.create_task(second())
        await asyncio.sleep(0)
        assert not second_entered.is_set()
        release_first.set()
        await asyncio.gather(one, two)
        assert order == ['first-enter', 'first-leave', 'second-enter']
    asyncio.run(run())
    assert_unlocked(tmp_path / '.action.lock')


def test_repeated_cancellation_during_acquisition_releases_only_after_acquiring(tmp_path, monkeypatch):
    path = tmp_path / '.action.lock'
    held = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    fcntl.flock(held, fcntl.LOCK_EX)
    started = threading.Event()
    original = fcntl.flock
    acquired = []
    def observed(descriptor, operation):
        if descriptor != held and operation == fcntl.LOCK_EX:
            started.set()
        result = original(descriptor, operation)
        if descriptor != held:
            acquired.append(operation)
        return result
    monkeypatch.setattr(fcntl, 'flock', observed)
    async def run():
        entered = []
        async def waiting():
            async with _action_lock(tmp_path):
                entered.append(True)
        task = asyncio.create_task(waiting())
        try:
            await asyncio.to_thread(started.wait)
            task.cancel(); await asyncio.sleep(0)
            task.cancel(); await asyncio.sleep(0)
            assert not task.done() and entered == [] and acquired == []
        finally:
            original(held, fcntl.LOCK_UN)
            if not task.done():
                task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        assert task.cancelled()
        assert entered == []
        assert acquired == [fcntl.LOCK_EX, fcntl.LOCK_UN]
    try:
        asyncio.run(run())
    finally:
        original(held, fcntl.LOCK_UN)
        os.close(held)
    assert_unlocked(path)


def test_cancellation_in_body_releases_real_lock(tmp_path):
    async def run():
        entered = asyncio.Event()
        async def body():
            async with _action_lock(tmp_path):
                entered.set()
                await asyncio.Event().wait()
        task = asyncio.create_task(body())
        await entered.wait(); task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(run())
    assert_unlocked(tmp_path / '.action.lock')


def test_body_exception_releases_real_lock(tmp_path):
    async def run():
        with pytest.raises(LookupError, match='declared-body-failure'):
            async with _action_lock(tmp_path):
                raise LookupError('declared-body-failure')
    asyncio.run(run())
    assert_unlocked(tmp_path / '.action.lock')


def test_acquisition_error_closes_its_descriptor(tmp_path, monkeypatch):
    descriptors = []
    def unavailable(descriptor, operation):
        assert operation == fcntl.LOCK_EX
        descriptors.append(descriptor)
        raise OSError(errno.EIO, 'declared-lock-acquisition-failure')
    monkeypatch.setattr(fcntl, 'flock', unavailable)
    async def run():
        with pytest.raises(OSError, match='declared-lock-acquisition-failure'):
            async with _action_lock(tmp_path):
                pytest.fail('failed acquisition entered body')
    asyncio.run(run())
    assert len(descriptors) == 1
    with pytest.raises(OSError) as caught:
        os.fstat(descriptors[0])
    assert caught.value.errno == errno.EBADF


def test_original_no_follow_policy_rejects_symlink(tmp_path):
    target = tmp_path / 'untouched'
    target.write_bytes(b'original-target')
    (tmp_path / '.action.lock').symlink_to(target)
    async def run():
        with pytest.raises(OSError) as caught:
            async with _action_lock(tmp_path):
                pytest.fail('symlink entered body')
        assert caught.value.errno == errno.ELOOP
    asyncio.run(run())
    assert target.read_bytes() == b'original-target'
