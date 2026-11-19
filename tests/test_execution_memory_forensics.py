"""Controlled disposable stores only; never touch the two genuine databases."""
import contextlib
import fcntl
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3

import pytest


spec = importlib.util.spec_from_file_location('execution_memory_forensics_test_helper',
    Path(__file__).with_name('execution_memory_forensics.py'))
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)


def create(path, *, attempt='attempt-one', body='original', resource='resource-one'):
    db = sqlite3.connect(path)
    try:
        db.execute('CREATE TABLE resource_observations '
                   '(id TEXT PRIMARY KEY,resource TEXT,kind TEXT,observed REAL,body TEXT)')
        db.execute('CREATE TABLE execution_measurements '
                   '(attempt TEXT PRIMARY KEY,compatibility TEXT,resource TEXT,observed REAL,body TEXT)')
        db.execute('CREATE INDEX execution_measurement_resource ON execution_measurements(resource,observed DESC)')
        # Stale and future observations must survive the census without filtering.
        db.executemany('INSERT INTO resource_observations VALUES(?,?,?,?,?)', [
            ('resource-old', 'r', 'capacity', -1000., '{"age":"old"}'),
            ('resource-future', 'r', 'queue', 999999999999., '{"age":"future"}')])
        db.execute('INSERT INTO execution_measurements VALUES(?,?,?,?,?)',
                   (attempt, 'compatibility', resource, 0., body))
        db.commit()
    finally:
        db.close()


def pair(tmp_path):
    (tmp_path / 'runs').mkdir()
    paths = [tmp_path / 'runs' / 'left.sqlite3', tmp_path / 'runs' / 'right.sqlite3']
    for path in paths:
        create(path)
    return paths


def capture(tmp_path, paths, *, references=()):
    return F.run(tmp_path, tmp_path / 'runs' / 'census', list(references), controlled_paths=paths)


def test_complete_rows_identical_and_original_bytes_preserved(tmp_path):
    paths = pair(tmp_path)
    before = [p.read_bytes() for p in paths]
    result = capture(tmp_path, paths)
    assert result['status'] == 'completed_read_only_census', result['failure']
    assert result['snapshot_complete'] and result['logical_census_complete']
    assert result['comparison']['resource_observations']['counts']['identical'] == 2
    assert result['comparison']['execution_measurements']['counts']['identical'] == 1
    assert [p.read_bytes() for p in paths] == before
    assert all(x['closed'] for x in result['descriptor_cleanup'])
    assert all(Path(x['copy']).stat().st_mode & 0o777 == 0o400 for x in result['snapshots'])


def sqlite_writer(path, ready, release):
    db = sqlite3.connect(path)
    try:
        db.execute('BEGIN IMMEDIATE')
        ready.send('reserved')
        release.recv()
        db.rollback()
    finally:
        db.close()


def test_actual_sqlite_reserved_writer_refused_and_not_stopped(tmp_path):
    paths = pair(tmp_path)
    ctx = multiprocessing.get_context('spawn')
    receiver, sender = ctx.Pipe(False)
    release_receiver, release_sender = ctx.Pipe(False)
    child = ctx.Process(target=sqlite_writer, args=(str(paths[0]), sender, release_receiver))
    child.start()
    sender.close(); release_receiver.close()
    try:
        assert receiver.recv() == 'reserved'
        result = capture(tmp_path, paths)
        assert result['status'] == 'refused_or_failed'
        assert not result['snapshot_complete']
        assert not list((tmp_path / 'runs' / 'census').glob('database-*.sqlite3'))
        assert child.is_alive()  # The forensic tool has no stop/kill/cleanup authority over it.
    finally:
        with contextlib.suppress(BrokenPipeError, EOFError):
            release_sender.send('release')
        child.join()  # Event-driven release; no timeout, terminate or polling loop.
        receiver.close(); release_sender.close()
    assert child.exitcode == 0


def probe_lock(path, ready, release):
    fd = os.open(path, os.O_RDWR)
    try:
        try:
            # SQLite's RESERVED byte lies in the region protected by whole-file lockf.
            fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB, 1, 0x40000001, os.SEEK_SET)
        except BlockingIOError:
            ready.send('excluded')
        else:
            ready.send('not-excluded')
        release.recv()
    finally:
        os.close(fd)


def test_whole_file_posix_lock_excludes_writer_starting_after_census(tmp_path):
    paths = pair(tmp_path)
    fd = F.open_original(paths[0])
    ctx = multiprocessing.get_context('spawn')
    receiver, sender = ctx.Pipe(False)
    release_receiver, release_sender = ctx.Pipe(False)
    child = ctx.Process(target=probe_lock, args=(str(paths[0]), sender, release_receiver))
    try:
        fcntl.lockf(fd, fcntl.LOCK_SH | fcntl.LOCK_NB, 0, 0, os.SEEK_SET)
        child.start()
        sender.close(); release_receiver.close()
        assert receiver.recv() == 'excluded'
    finally:
        with contextlib.suppress(BrokenPipeError, EOFError):
            release_sender.send('release')
        if child.pid is not None:
            child.join()
        os.close(fd)
        receiver.close(); sender.close(); release_receiver.close(); release_sender.close()
    assert child.exitcode == 0


@pytest.mark.parametrize('suffix', ['-wal', '-shm', '-journal', '-mj-test'])
def test_companions_refused_without_recovery_or_cleanup(tmp_path, suffix):
    paths = pair(tmp_path)
    companion = Path(str(paths[0]) + suffix)
    companion.write_bytes(b'controlled-present-companion')
    result = capture(tmp_path, paths)
    assert result['failure']['code'] == 'sqlite_companion_present'
    assert companion.read_bytes() == b'controlled-present-companion'
    assert not result['snapshot_complete']


def test_real_wal_header_without_sidecars_is_still_refused(tmp_path):
    paths = pair(tmp_path)
    db = sqlite3.connect(paths[0])
    assert db.execute('PRAGMA journal_mode=WAL').fetchone() == ('wal',)
    db.close()
    assert not F.sidecars(paths[0])
    result = capture(tmp_path, paths)
    assert result['failure']['code'] == 'rollback_journal_header_required'


def test_open_writable_descriptor_refused_even_without_active_transaction(tmp_path):
    paths = pair(tmp_path)
    fd = os.open(paths[0], os.O_RDWR)
    try:
        result = capture(tmp_path, paths)
        assert result['failure']['code'] == 'observed_writer_descriptor_or_mapping'
        assert any(x['writable'] for x in result['processes_before']['matches'])
    finally:
        os.close(fd)


def test_symlink_and_same_inode_alias_not_accepted(tmp_path):
    paths = pair(tmp_path)
    alias = tmp_path / 'runs' / 'alias.sqlite3'
    alias.symlink_to(paths[0])
    result = capture(tmp_path, [alias, paths[1]])
    assert result['failure']['code'] == 'symlink_path_refused'
    alias.unlink()
    os.link(paths[0], alias)
    evidence = {}
    with pytest.raises(F.Refusal, match='same_inode_alias_refused'):
        F.snapshot_pair([paths[0], alias], tmp_path / 'runs', evidence)
    assert all(x['closed'] for x in evidence['descriptor_cleanup'])


def test_unknown_table_not_silently_omitted(tmp_path):
    paths = pair(tmp_path)
    db = sqlite3.connect(paths[0])
    db.execute('CREATE TABLE other_history(value TEXT)')
    db.execute("INSERT INTO other_history VALUES('must-not-discard')")
    db.commit(); db.close()
    result = capture(tmp_path, paths)
    assert result['snapshot_complete'] and not result['logical_census_complete']
    assert result['failure']['code'] == 'unreviewed_table_set'
    assert 'other_history' in F.canonical(result['failure']['detail'])


def test_null_primary_identity_retained_as_explicit_incomplete_domain(tmp_path):
    paths = pair(tmp_path)
    db = sqlite3.connect(paths[0])
    db.execute('INSERT INTO execution_measurements VALUES(NULL,?,?,?,?)', ('c', 'r', 0., 'raw-null-key'))
    db.commit(); db.close()
    result = capture(tmp_path, paths)
    assert result['failure']['code'] == 'invalid_key_domain'
    assert not result['logical_census_complete']
    export = result['exports']['execution_measurements'][0]
    assert export['rows'] == 2 and export['invalid_or_repeated_keys'] == 1
    assert 'raw-null-key' in Path(export['file']).read_text()


def test_copy_tamper_is_rejected_before_sqlite(tmp_path):
    paths = pair(tmp_path)
    result = capture(tmp_path, paths)
    assert result['failure'] is None
    record = result['snapshots'][0]
    path = Path(record['copy'])
    path.chmod(0o600)
    path.write_bytes(path.read_bytes() + b'tampered')
    path.chmod(0o400)
    with pytest.raises(F.Refusal, match='copy_tampered'):
        F.open_snapshot(record)


def test_reference_mismatch_refuses_before_source_snapshot(tmp_path):
    paths = pair(tmp_path)
    (tmp_path / 'runs' / 'saved.json').write_text('{}')
    result = capture(tmp_path, paths, references=[{
        'path': 'runs/saved.json', 'sha256': '0' * 64, 'kind': 'controlled'}])
    assert result['failure']['code'] == 'reference_hash_mismatch'
    assert 'originals' not in result and not result['snapshot_complete']


def test_no_sqlite_connection_ever_targets_originals(tmp_path, monkeypatch):
    paths = pair(tmp_path)
    original = sqlite3.connect
    seen = []
    def connection(value, *args, **kwargs):
        seen.append(value)
        assert '?mode=ro&immutable=1' in value
        assert '/census/database-' in value
        return original(value, *args, **kwargs)
    monkeypatch.setattr(F.sqlite3, 'connect', connection)
    result = capture(tmp_path, paths)
    assert result['failure'] is None and len(seen) == 2


def test_path_replacement_is_detected_with_held_original_descriptor(tmp_path, monkeypatch):
    paths = pair(tmp_path)
    real = F.digest_fd
    calls = []
    def replace_after_copy(fd):
        answer = real(fd)
        calls.append(fd)
        if len(calls) == 3:
            # Deliberately non-cooperative directory mutation, only in this
            # controlled test. Neither forensic code nor any genuine path does it.
            moved = paths[0].with_name('retained-original.sqlite3')
            paths[0].rename(moved)
            paths[0].write_bytes(moved.read_bytes())
        return answer
    monkeypatch.setattr(F, 'digest_fd', replace_after_copy)
    result = capture(tmp_path, paths)
    assert result['failure']['code'] == 'source_changed_under_locks'
    assert not result['snapshot_complete']
    assert all(row['closed'] for row in result['descriptor_cleanup'])


def test_workflow_membership_keeps_nested_workers_and_rejects_adjacent_prefix():
    # Pure parsing examples only; production obtains its witness from /proc.
    group = '/user.slice/gene-episode-workflow-' + 'a' * 32 + '.service'
    raw = '0::' + group + '/nested/worker\n'
    assert F._workflow_group(raw) == group
    assert F._workflow_member(raw, group)
    assert F._workflow_member('0::' + group + '\n', group)
    assert not F._workflow_member('0::' + group + '-adjacent/worker\n', group)
    assert F._workflow_group('0::' + group + '-adjacent/worker\n') is None
    assert not F._workflow_member(raw, None)
    assert F._workflow_group('0::/user.slice/unrecognized.service/worker\n') is None


def test_real_inventory_retains_unknown_coverage_and_actual_executor_links(tmp_path):
    paths = pair(tmp_path)
    observed = F.process_inventory(paths, {os.getuid()})
    assert observed['uid_scope_establishes_link'] is False
    assert observed['unknown_visibility_is_not_absence'] is True
    assert any(row['pid'] == str(os.getpid()) and any(link['kind'] == 'current_executor'
               for link in row['links']) for row in observed['process_links'])
    assert all(row['links'] == [] and row['scope'] == 'unknown_target_or_workflow_link'
               for row in observed['unclassified_process_observations'])
    # No required count of inaccessible processes: that is actual host state.
    F.assert_inventory(observed)


def readonly_child_visibility_transition(path, ready, control):
    import ctypes
    fd = os.open(path, os.O_RDONLY)
    try:
        ready.send(('opened', os.getpid(), fd))
        command = control.recv()
        if command == 'deny_visibility':
            libc = ctypes.CDLL(None, use_errno=True)
            libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
            libc.prctl.restype = ctypes.c_int
            code = libc.prctl(4, 0, 0, 0, 0)  # PR_SET_DUMPABLE: actual /proc permission transition.
            ready.send(('visibility_changed', code, ctypes.get_errno()))
            control.recv()
    finally:
        os.close(fd)


def test_actual_target_link_survives_later_fdinfo_permission_denial(tmp_path, monkeypatch):
    paths = pair(tmp_path)
    ctx = multiprocessing.get_context('spawn')
    receiver, sender = ctx.Pipe(False)
    control_receiver, control_sender = ctx.Pipe(False)
    child = ctx.Process(target=readonly_child_visibility_transition,
                        args=(str(paths[0]), sender, control_receiver))
    child.start(); sender.close(); control_receiver.close()
    try:
        kind, pid, fd = receiver.recv()
        assert kind == 'opened' and pid == child.pid
        target = Path('/proc') / str(pid) / 'task' / str(pid) / 'fdinfo' / str(fd)
        original = Path.read_text
        triggered = []
        def observe_then_read(path, *args, **kwargs):
            if path == target and not triggered:
                triggered.append(str(path))
                control_sender.send('deny_visibility')
                state, code, error = receiver.recv()
                assert state == 'visibility_changed' and code == 0, error
            return original(path, *args, **kwargs)  # Actual OS read; no synthetic PermissionError.
        with monkeypatch.context() as patch:
            patch.setattr(Path, 'read_text', observe_then_read)
            observed = F.process_inventory(paths, {os.getuid()})
        assert triggered == [str(target)]
        linked = [row for row in observed['unresolved'] if row['pid'] == str(pid)]
        assert linked and linked[0]['type'] == 'PermissionError'
        assert any(link['kind'] == 'target_descriptor' and link['fd'] == str(fd)
                   and link['matched'] == str(paths[0]) for link in linked[0]['links'])
        assert not any(row['pid'] == str(pid) for row in observed['unclassified_process_observations'])
        with pytest.raises(F.Refusal, match='relevant_process_visibility_unresolved'):
            F.assert_inventory(observed)
        assert child.is_alive()
    finally:
        with contextlib.suppress(BrokenPipeError, EOFError):
            control_sender.send('release')
        child.join()
        receiver.close(); control_sender.close()
    assert child.exitcode == 0
