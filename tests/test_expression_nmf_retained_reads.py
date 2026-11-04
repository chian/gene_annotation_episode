"""Opt-in metadata controls over the genuine completed NMF490 receipts.

No fit, calculator, worker or scientific File is constructed here. Each case
owns its database and small control/archive copies. The completed histories
are preserved, apart from explicit owned negative-control tampering.
"""
import asyncio
import builtins
from copy import deepcopy
from dataclasses import replace
import hashlib
from importlib import import_module
import io
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3

import pytest

from gene_annotation_episode import acquisition, native_lifecycle
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.expression_nmf_result_receipts import _CLOSED_PATHS, _READING
from gene_annotation_episode.state import Store

F = import_module('verification.tool_graders_expression_nmf_episode_path_2026-10-27_490.fixture_helpers')


ENV = 'HMMER_NATIVE_ORACLE_NMF_RETAINED'
CONTROL_NAMES = ('intent.json', 'receipt.json', 'handoff.json', 'observation.json',
    'native-snapshot.json', 'capture.json', 'worker-plan.json', 'worker-capture.json', 'worker-execution.json')


def _pin(path):
    raw = Path(path).read_bytes()
    return dict(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _bundle(root):
    return [dict(name=name, **_pin(root / name))
        for name in ('state.sqlite3', 'state.sqlite3-wal', 'state.sqlite3-shm') if (root / name).is_file()]


def _rows(store):
    return {row[0]: [dict(value) for value in store.db.execute('SELECT * FROM ' + row[0] + ' ORDER BY rowid')]
        for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}


def _files(root):
    return {str(p.relative_to(root)): dict(**_pin(p), mode=p.stat().st_mode)
        for p in root.rglob('*') if p.is_file()}


@pytest.fixture
def retained_read(tmp_path, monkeypatch):
    selected = os.environ.get(ENV + '_PROOF')
    if not selected:
        pytest.skip('requires explicit immutable completed NMF490 proof/configuration/SQLite pins')
    prefix = Path(selected).resolve(strict=True)
    original = prefix.parent
    names = [('CASE.json', '_PROOF_SHA256'), ('fixture-configuration.json', '_CONFIGURATION_SHA256'),
        ('SAVED_CHECK.json', '_SAVED_CHECK_SHA256')]
    controls = {name: _pin(original / name) for name, _ in names}
    for name, suffix in names:
        assert controls[name]['sha256'] == os.environ[ENV + suffix]
    configuration = json.loads((original / 'fixture-configuration.json').read_bytes())
    pins = _bundle(original / 'state')
    assert digest(pins) == os.environ[ENV + '_SQLITE_PINS_SHA256']
    staging, owned = tmp_path / 'sqlite-staging', tmp_path / 'owned'
    staging.mkdir(); (owned / 'state').mkdir(parents=True)
    for row in pins:
        shutil.copyfile(original / 'state' / row['name'], staging / row['name'])
    assert _bundle(staging) == pins
    source_db = sqlite3.connect(staging / 'state.sqlite3')
    destination_db = sqlite3.connect(owned / 'state/state.sqlite3')
    try:
        source_db.execute('PRAGMA query_only=ON')
        source_db.backup(destination_db)
    finally:
        destination_db.close(); source_db.close()
    for name in ('archive', 'scientific-process-library', 'scientific-tool-library',
            'tool-knowledge', 'launch-instructions'):
        path = original / 'run' / name
        if path.is_dir(): shutil.copytree(path, owned / 'run' / name)
    store = Store(owned / 'state')
    receipts = []
    for row in store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? "
            "AND json_extract(action,'$.tool')='execution.results.collect' ORDER BY rowid", (F.RUN_ID,)):
        receipt = json.loads(row['result'])['result']
        receipts.append(receipt)
        action = Path(receipt['worker_plan']['directory']).parent
        relative = action.relative_to(original / 'run')
        target = owned / 'run' / relative
        target.mkdir(parents=True, exist_ok=True)
        for name in CONTROL_NAMES:
            path = action / name
            if path.is_file(): shutil.copy2(path, target / name)
        shutil.copy2(action.parent.parent / 'assignment.json', target.parent.parent / 'assignment.json')
    assert [r['worker_plan']['mode'] for r in receipts] == [
        'native_result', 'saved_sheet_recalculation']
    class NoDecisions:
        async def complete(self, *args, **kwargs): raise AssertionError('metadata read requested a decision')
        async def release(self, episode_id): pass
    flow, _ = F.assemble(store, owned, NoDecisions(), configuration)
    owner = flow.episode_bindings.for_role('results')
    reader = owner.native_expression_nmf_results.receipts
    contexts = [reader.returns.context(r['intent']['episode_id']) for r in receipts]
    attempts = []
    def forbidden(*args, **kwargs):
        attempts.append([type(value).__name__ for value in args])
        raise AssertionError('retained metadata read attempted work, grant or scientific File access')
    path_open, builtin_open, io_open, os_open = Path.open, builtins.open, io.open, os.open
    def check_path(value, *, dir_fd=None):
        if isinstance(value, int): return
        path = Path(os.fsdecode(value))
        if not path.is_absolute():
            path = (Path(os.readlink('/proc/self/fd/' + str(dir_fd)))
                if dir_fd is not None else Path.cwd()) / path
        path = Path(os.path.normpath(path))
        if path.is_relative_to(original): forbidden(str(path))
    def checked_path(path, *args, **kwargs):
        check_path(path); return path_open(path, *args, **kwargs)
    def checked_builtin(path, *args, **kwargs):
        check_path(path); return builtin_open(path, *args, **kwargs)
    def checked_io(path, *args, **kwargs):
        check_path(path); return io_open(path, *args, **kwargs)
    def checked_os(path, flags, *args, **kwargs):
        check_path(path, dir_fd=kwargs.get('dir_fd')); return os_open(path, flags, *args, **kwargs)
    # No Artifact bodies are copied. All original and cloned scientific input
    # or result File access therefore fails independently of the guards below.
    assert not any((store.path / 'artifacts').rglob('*'))
    initial_rows = _rows(store)
    try:
        with monkeypatch.context() as guard:
            guard.setattr(Path, 'open', checked_path)
            guard.setattr(builtins, 'open', checked_builtin)
            guard.setattr(io, 'open', checked_io)
            guard.setattr(os, 'open', checked_os)
            guard.setattr(store, 'get_artifact', forbidden)
            guard.setattr(store, 'artifact', forbidden)
            guard.setattr(flow.receipts, 'receive', forbidden)
            guard.setattr(owner.native_expression_nmf_results, '_worker', forbidden)
            guard.setattr(owner.job_progress_provider.targets, 'observe_target', forbidden)
            guard.setattr(acquisition.PublicClients, '_http', forbidden)
            guard.setattr(socket, 'create_connection', forbidden)
            for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect', 'cancel'):
                guard.setattr(native_lifecycle, name, forbidden)
            yield dict(store=store, flow=flow, owner=owner, reader=reader, contexts=contexts,
                receipts=receipts, owned=owned, attempts=attempts, initial_rows=initial_rows)
        assert attempts == []
        assert {name: _pin(original / name) for name, _ in names} == controls
        assert _bundle(original / 'state') == pins
    finally:
        store.close()


def _read(case, position):
    receipt, context = case['receipts'][position], case['contexts'][position]
    return case['reader'].read_completed(episode_id=context.episode_id,
        operation_key=receipt['intent']['operation_key'], scope=context.scope)


def test_retained_closed_native_saved_and_same_key_collect_read_only_metadata(retained_read, monkeypatch):
    c = retained_read
    before_files = _files(c['owned'] / 'run')
    def no_lock(*args, **kwargs): raise AssertionError('cached collect entered the writer lock')
    monkeypatch.setattr(c['reader'], 'locked_action', no_lock)
    for position, (context, receipt) in enumerate(zip(c['contexts'], c['receipts'], strict=True)):
        assert _read(c, position) == receipt
        assert _CLOSED_PATHS.get() == _READING.get() == ()
        proof = c['owner'].completion_for_action(context, receipt['intent']['operation_key'])
        assert proof is not None and c['owner'].verify_completion(context, proof)
        result = asyncio.run(c['owner'].native_expression_nmf_results.execute(context,
            receipt['intent']['target'], 'execution.results.collect', {}, receipt['intent']['operation_key']))
        assert result['result'] == receipt
        assert result['record_refs'] == [r['artifact_ref'] for r in receipt['facts'][F.SAVED_SOURCE]]
    science, = [c['reader'].returns.context(row['episode_id']) for row in c['store'].db.execute(
        "SELECT episode_id FROM runtime_episodes WHERE json_extract(path,'$[#-1][0]')='scientific_process'")]
    values = c['reader'].returns.received_facts(science, science.request['report_contract']['measurements']['schema'])
    assert values[F.PROJECTION_SOURCE] == [r['projection'] for r in c['receipts']]
    assert _CLOSED_PATHS.get() == _READING.get() == ()
    assert _rows(c['store']) == c['initial_rows']
    assert _files(c['owned'] / 'run') == before_files


@pytest.mark.parametrize('tamper', ['sidecar', 'outcome', 'archive', 'frozen_facts'])
def test_closed_read_rejects_tampered_evidence_and_resets_nested_context(retained_read, tamper):
    c = retained_read
    original = c['receipts'][0]
    root = c['reader'].action_directory(original['intent']['episode_id'], original['intent']['operation_key'])
    path = None; restore_row = None
    if tamper == 'sidecar':
        path = root / 'worker-plan.json'
    elif tamper == 'archive':
        row = c['flow'].journal.row('runtime_episodes', c['contexts'][0].episode_id)
        path = c['owned'] / 'run/archive' / json.loads(row['archive'])['file']
    if path is not None:
        raw, mode = path.read_bytes(), path.stat().st_mode
        path.chmod(mode | 0o200)
        path.write_bytes(raw + b' ' if tamper == 'archive' else b'{}')
    elif tamper == 'outcome':
        row = c['flow'].journal.row('runtime_actions', c['contexts'][0].episode_id, 0)
        restore_row = ('runtime_actions', 'result', row['result'])
        changed = json.loads(row['result']); changed['result']['delivery_complete'] = False
        c['store'].db.execute('UPDATE runtime_actions SET result=? WHERE episode_id=? AND decision_index=0',
            (canonical(changed), c['contexts'][0].episode_id))
    else:
        row = c['flow'].journal.row('runtime_forms', c['contexts'][0].episode_id)
        restore_row = ('runtime_forms', 'facts', row['facts'])
        changed = json.loads(row['facts']); changed[F.PROJECTION_SOURCE][0]['has_more'] = True
        c['store'].db.execute('UPDATE runtime_forms SET facts=? WHERE episode_id=?',
            (canonical(changed), c['contexts'][0].episode_id))
    try:
        # Reading the saved receipt recursively authenticates its real native
        # origin. The outer and failed inner contexts must both be unwound.
        with pytest.raises((ValueError, KeyError)):
            _read(c, 1)
        assert _CLOSED_PATHS.get() == _READING.get() == ()
    finally:
        if path is not None:
            path.write_bytes(raw); path.chmod(mode)
        if restore_row is not None:
            table, field, raw = restore_row
            c['store'].db.execute('UPDATE ' + table + ' SET ' + field + '=? WHERE episode_id=?' +
                (' AND decision_index=0' if table == 'runtime_actions' else ''),
                (raw, c['contexts'][0].episode_id))
    assert _read(c, 1) == c['receipts'][1]
    assert _CLOSED_PATHS.get() == _READING.get() == ()
    assert _rows(c['store']) == c['initial_rows']


@pytest.mark.parametrize('state', ['active', 'incomplete'])
def test_active_or_incomplete_receipts_keep_strict_current_roots(retained_read, state):
    c = retained_read
    context = c['contexts'][0]
    if state == 'active':
        row = dict(c['flow'].journal.row('runtime_episodes', context.episode_id))
        c['store'].db.execute("UPDATE runtime_episodes SET state='active',completion=NULL,archive=NULL WHERE episode_id=?",
            (context.episode_id,))
    else:
        row = dict(c['flow'].journal.row('runtime_actions', context.episode_id, 0))
        c['store'].db.execute('UPDATE runtime_actions SET result=NULL WHERE episode_id=? AND decision_index=0',
            (context.episode_id,))
    try:
        with pytest.raises(ValueError, match='nmf_worker_selection_mismatch|nmf_completed_result_required'):
            _read(c, 0)
        assert _CLOSED_PATHS.get() == _READING.get() == ()
    finally:
        if state == 'active':
            c['store'].db.execute('UPDATE runtime_episodes SET state=?,completion=?,archive=? WHERE episode_id=?',
                (row['state'], row['completion'], row['archive'], context.episode_id))
        else:
            c['store'].db.execute('UPDATE runtime_actions SET result=? WHERE episode_id=? AND decision_index=0',
                (row['result'], context.episode_id))
    assert _read(c, 0) == c['receipts'][0]


@pytest.mark.parametrize('changed', ['target', 'context', 'key'])
def test_closed_cached_collect_rejects_changed_invocation_before_lock(retained_read, monkeypatch, changed):
    c = retained_read
    context, receipt = c['contexts'][0], c['receipts'][0]
    target, key = deepcopy(receipt['intent']['target']), receipt['intent']['operation_key']
    def no_lock(*args, **kwargs): raise AssertionError('invalid cached collect entered writer lock')
    monkeypatch.setattr(c['reader'], 'locked_action', no_lock)
    with pytest.raises(ValueError):
        if changed == 'target': target['request_sha256'] = '0' * 64
        elif changed == 'context': context = replace(context, scope={'subject_refs': []})
        else: key = key.rsplit(':', 1)[0] + ':1'
        asyncio.run(c['owner'].native_expression_nmf_results.execute(context, target,
            'execution.results.collect', {}, key))
    assert _CLOSED_PATHS.get() == _READING.get() == ()
    assert _rows(c['store']) == c['initial_rows']
