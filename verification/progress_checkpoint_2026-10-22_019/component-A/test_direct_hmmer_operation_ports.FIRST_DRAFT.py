"""Synthetic operational custody checks; no public/model/native transports."""
import asyncio
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import itertools
import json
from pathlib import Path
import sqlite3
import threading

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, SourceSnapshot
from gene_annotation_episode.domain import ContractError, canonical, identity
from gene_annotation_episode.provider_jobs import RemoteSearches
from gene_annotation_episode.public_search_operations import (
    ProviderJobOperations, ProviderOperationInProgress, hmmer_client_binding_sha256)
from gene_annotation_episode.state import Store


REMOTE = '81bddc6e-f6ef-4f16-a8c1-32d262016ccb'
TABLES = ('provider_jobs', 'public_search_orders', 'public_search_order_scopes',
          'public_search_claims', 'public_search_operations', 'public_search_results',
          'public_search_selections', 'public_search_registries', 'artifacts')


def snapshot(body):
    return SourceSnapshot('fixture_hmmer', 'http://fixture.invalid/' + REMOTE, {},
        '2026-10-22T00:00:00+00:00', canonical(body).encode(), 'application/json',
        {'representation': 'synthetic_protocol_fixture', 'status': 200})


class Client:
    hmmer_fixture_binding = dict(transport_timeout_seconds=20,
        submit_url_prefix='http://fixture.invalid/search/',
        status_url_prefix='http://fixture.invalid/search/',
        result_url_prefix='http://fixture.invalid/result/')

    def __init__(self):
        self.calls = []
        self.state = 'SUCCESS'
        self.error = None
        self.entered, self.release = threading.Event(), threading.Event()
        self.release.set()

    def hmmer_submit(self, query_fasta, **kwargs):
        self.calls.append(('submit', query_fasta, kwargs))
        return snapshot({'id': REMOTE})

    def hmmer_status(self, remote):
        self.calls.append(('status', remote))
        self.entered.set()
        if not self.release.wait(10):
            raise RuntimeError('fixture release gate expired')
        if self.error is not None:
            raise self.error
        return snapshot({'id': REMOTE, 'task': {'status': self.state}})

    def hmmer_result(self, remote, **kwargs):
        self.calls.append(('result', remote, kwargs))
        return snapshot({'status': 'SUCCESS', 'result': {'stats': {
            'id': REMOTE, 'algo': 'phmmer', 'database': 'swissprot'}, 'hits': []}})


def registry(client):
    return dict(version='public_search_registry_v1', registry_ref='execution_registry_fixture',
        resource_id='fixture_hmmer_resource', provider='hmmer',
        client_binding_sha256=hmmer_client_binding_sha256(client))


@pytest.fixture
def env(tmp_path):
    store = Store(tmp_path / 'store')
    try:
        problem = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        client = Client()
        ops = ProviderJobOperations(store, RemoteSearches(store, client), registry=registry(client))
        subject = problem['subject_refs'][0]
        order = ops.order(operation_key='order', provider='hmmer', subject_ref=subject,
            query_fasta=f'>{subject}\nMACDEFGH', algorithm='phmmer', database='swissprot',
            scope={'subject_refs': problem['subject_refs']}, page_size=2)
        yield store, client, ops, order
    finally:
        store.close()


async def completed(env):
    store, client, ops, order = env
    job = order['job_ref']
    await ops.submit_once(job, operation_key='submit')
    await ops.status_once(job, operation_key='status')
    await ops.result_once(job, operation_key='result', page=1, page_size=2)


def readonly_classification(env, monkeypatch, *, job=None):
    store, client, ops, order = env
    before = {name: store.db.execute('SELECT count(*) FROM ' + name).fetchone()[0] for name in TABLES}
    changes, calls = store.db.total_changes, list(client.calls)
    files = lambda: {str(p.relative_to(store.path)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for root in (store.path / 'artifacts', ops.captures) for p in root.rglob('*') if p.is_file()}
    files_before = files()
    original, snapshots = store.read_snapshot, []

    @contextmanager
    def counted():
        snapshots.append(True)
        with original():
            yield store

    with monkeypatch.context() as patch:
        patch.setattr(store, 'read_snapshot', counted)
        result = ops.classify_order(order['job_ref'] if job is None else job)
    assert len(snapshots) == 1
    assert store.db.total_changes == changes
    assert before == {name: store.db.execute('SELECT count(*) FROM ' + name).fetchone()[0] for name in TABLES}
    assert calls == client.calls and files_before == files()
    assert set(result) == {'version', 'job_ref', 'registry_ref', 'state', 'code'}
    assert result['version'] == 'public_search_order_membership_v1'
    assert result['registry_ref'] == ops.registry['registry_ref']
    return result


def pair(result):
    return result['state'], result['code']


@pytest.mark.parametrize('bits', list(itertools.product((False, True), repeat=6)))
def test_complete_committed_evidence_matrix(env, monkeypatch, bits):
    asyncio.run(completed(env))
    store, client, ops, order = env
    p, o, s, c, r, b = bits
    for present, table in zip(bits, TABLES[:6]):
        if not present:
            store.db.execute('DELETE FROM ' + table)
    result = readonly_classification(env, monkeypatch)
    if not p:
        expected = ('conflict', 'public_search_registration_incomplete') if any(bits[1:]) else ('unavailable', 'unknown_job')
    elif not o and not s and not any((c, r, b)):
        expected = ('unregistered', None)
    elif not (o and s) or r != b:
        # The retained complete result receipt/index must retain both links.
        expected = ('conflict', 'public_search_registration_incomplete')
    else:
        expected = ('registered', None)
    assert pair(result) == expected


@pytest.mark.parametrize('value', [None, '', ' job', 'job ', 'x\n', 'x\x7f', 'x\u0080', 1, True, []])
def test_invalid_membership_arguments_fail_before_storage(env, monkeypatch, value):
    store, client, ops, order = env
    def forbidden():
        raise AssertionError('invalid argument reached storage')
    monkeypatch.setattr(store, 'read_snapshot', forbidden)
    with pytest.raises(ContractError, match='^public_search_membership_arguments_invalid$'):
        ops.classify_order(value)
    assert client.calls == []


def test_new_unsubmitted_and_inflight_claim_are_registered(env, monkeypatch):
    store, client, ops, order = env
    assert pair(readonly_classification(env, monkeypatch)) == ('registered', None)

    async def run():
        # Hold only the synthetic submit capture, leaving a real durable claim
        # without a terminal receipt, as a cancelled/interrupted caller can.
        original = ops._dispatch
        async def interrupted(*args, **kwargs):
            await original(*args, **kwargs)
            raise asyncio.CancelledError()
        monkeypatch.setattr(ops, '_dispatch', interrupted)
        with pytest.raises(asyncio.CancelledError):
            await ops.submit_once(order['job_ref'], operation_key='submit')
    asyncio.run(run())
    assert store.db.execute('SELECT count(*) FROM public_search_claims').fetchone()[0] == 1
    assert store.db.execute('SELECT count(*) FROM public_search_operations').fetchone()[0] == 0
    assert pair(readonly_classification(env, monkeypatch)) == ('registered', None)


def mutate_json(store, table, column, value):
    row = store.db.execute('SELECT data FROM ' + table).fetchone()
    data = json.loads(row[0]); data[column] = value
    store.db.execute('UPDATE ' + table + ' SET data=?', (canonical(data),))


@pytest.mark.parametrize('cut,expected', [
    ('order_extra', 'identity_conflict'), ('order_registry', 'identity_conflict'),
    ('order_digest', 'identity_conflict'), ('scope_digest', 'identity_conflict'),
    ('scope_shape', 'identity_conflict'), ('scope_normalization', 'identity_conflict'),
    ('registry_missing', 'public_search_registration_incomplete'),
    ('registry_foreign', 'identity_conflict'), ('order_json', 'identity_conflict'),
    ('request_artifact_row', 'public_search_registration_incomplete'),
    ('request_artifact_file', 'public_search_registration_incomplete'),
    ('request_artifact_digest', 'identity_conflict'), ('fasta_artifact_digest', 'identity_conflict'),
    ('claim_shape', 'identity_conflict'), ('claim_predecessor', 'identity_conflict'),
    ('claim_selection', 'public_search_registration_incomplete'),
    ('receipt_selection', 'public_search_registration_incomplete'),
    ('receipt_column', 'identity_conflict'), ('receipt_shape', 'identity_conflict'),
    ('result_receipt_missing', 'public_search_registration_incomplete'),
    ('result_selector', 'identity_conflict'), ('result_receipt_wrong', 'identity_conflict'),
])
def test_registered_custody_cuts_never_fall_back(env, monkeypatch, cut, expected):
    asyncio.run(completed(env))
    store, client, ops, order = env
    if cut == 'order_extra': mutate_json(store, 'public_search_orders', 'extra', 1)
    elif cut == 'order_registry': mutate_json(store, 'public_search_orders', 'registry_ref', 'foreign')
    elif cut == 'order_digest': mutate_json(store, 'public_search_orders', 'request_sha256', '0' * 64)
    elif cut == 'scope_digest': mutate_json(store, 'public_search_order_scopes', 'scope_sha256', '0' * 64)
    elif cut == 'scope_shape': mutate_json(store, 'public_search_order_scopes', 'extra', 1)
    elif cut == 'scope_normalization': mutate_json(store, 'public_search_order_scopes', 'scope', {'subject_refs': []})
    elif cut == 'registry_missing': store.db.execute('DELETE FROM public_search_registries')
    elif cut == 'registry_foreign': mutate_json(store, 'public_search_registries', 'resource_id', 'foreign')
    elif cut == 'order_json': store.db.execute("UPDATE public_search_orders SET data='{' ")
    elif cut in {'request_artifact_row', 'request_artifact_file', 'request_artifact_digest', 'fasta_artifact_digest'}:
        ref = order['query_fasta_ref'] if cut == 'fasta_artifact_digest' else order['request_ref']
        path = store.path / 'artifacts' / ref[9:11] / ref[9:]
        if cut == 'request_artifact_row': store.db.execute('DELETE FROM artifacts WHERE id=?', (ref,))
        elif cut == 'request_artifact_file': path.unlink()
        else: path.write_bytes(b'corrupt actual retained bytes')
    elif cut == 'claim_shape': mutate_json(store, 'public_search_claims', 'extra', 1)
    elif cut == 'claim_predecessor': store.db.execute("UPDATE public_search_claims SET predecessor='foreign'")
    elif cut == 'claim_selection': store.db.execute("DELETE FROM public_search_selections WHERE operation_key='submit'")
    elif cut == 'receipt_selection': store.db.execute("DELETE FROM public_search_selections WHERE operation_key='status'")
    elif cut == 'receipt_column': store.db.execute("UPDATE public_search_operations SET operation_key='foreign' WHERE operation_key='status'")
    elif cut == 'receipt_shape':
        row = store.db.execute("SELECT data FROM public_search_operations WHERE operation_key='status'").fetchone()
        data = json.loads(row[0]); data['extra'] = 1
        store.db.execute("UPDATE public_search_operations SET data=? WHERE operation_key='status'", (canonical(data),))
    elif cut == 'result_receipt_missing': store.db.execute("DELETE FROM public_search_operations WHERE operation_key='result'")
    elif cut == 'result_selector': store.db.execute('UPDATE public_search_results SET page=2')
    elif cut == 'result_receipt_wrong':
        ref = store.db.execute("SELECT id FROM public_search_operations WHERE operation_key='status'").fetchone()[0]
        store.db.execute('UPDATE public_search_results SET receipt_ref=?', (ref,))
    assert pair(readonly_classification(env, monkeypatch)) == ('conflict', expected)


def test_legacy_row_does_not_read_request_artifacts_or_failures(env, monkeypatch):
    store, client, ops, order = env
    store.db.execute('DELETE FROM public_search_orders')
    store.db.execute('DELETE FROM public_search_order_scopes')
    store.db.execute("UPDATE provider_jobs SET request='unsupported legacy identity'")
    store.db.execute('INSERT INTO provider_job_failures VALUES(?,?)', (order['job_ref'], '{legacy'))
    def forbidden(*args): raise AssertionError('legacy artifact normalized/read')
    monkeypatch.setattr(store, 'get_artifact', forbidden)
    assert pair(readonly_classification(env, monkeypatch)) == ('unregistered', None)
    assert pair(readonly_classification(env, monkeypatch, job='unknown')) == ('unavailable', 'unknown_job')


@pytest.mark.parametrize('kind', ['sqlite', 'permission'])
def test_storage_failure_is_structured_without_fallback(env, monkeypatch, kind):
    store, client, ops, order = env
    def unavailable(*args):
        raise sqlite3.OperationalError('synthetic readonly access failure') if kind == 'sqlite' else PermissionError('synthetic artifact access failure')
    with monkeypatch.context() as patch:
        patch.setattr(store, 'read_snapshot' if kind == 'sqlite' else 'get_artifact', unavailable)
        result = ops.classify_order(order['job_ref'])
    assert pair(result) == ('unavailable', 'public_search_storage_unavailable')
    assert client.calls == []


def assert_wrapper(value, origin, job, key):
    assert set(value) == {'version', 'origin', 'receipt'}
    assert value['version'] == 'public_search_status_read_v1' and value['origin'] == origin
    receipt = value['receipt']
    assert len(receipt) == 19 and 'origin' not in receipt
    assert receipt['job_ref'] == job and receipt['operation_key'] == key and receipt['operation'] == 'status'
    return receipt


@pytest.mark.parametrize('state', ['PENDING', 'FAILURE', 'REVOKED'])
def test_status_worker_receipt_replay_and_legacy_shape(env, state):
    async def run():
        store, client, ops, order = env; job = order['job_ref']
        await ops.submit_once(job, operation_key='submit'); client.state = state
        receipt = assert_wrapper(await ops.status_once_with_origin(job, operation_key='status'), 'worker_dispatched', job, 'status')
        saved = store.db.execute("SELECT data FROM public_search_operations WHERE operation_key='status'").fetchone()[0]
        assert receipt['outcome'] == 'completed' and receipt['failure'] is None and receipt['state'] == state
        assert_wrapper(await ops.status_once_with_origin(job, operation_key='status'), 'receipt_reused', job, 'status')
        assert await ops.status_once(job, operation_key='status') == receipt
        assert store.db.execute("SELECT data FROM public_search_operations WHERE operation_key='status'").fetchone()[0] == saved == canonical(receipt)
        assert [row[0] for row in client.calls] == ['submit', 'status']
    asyncio.run(run())


def test_status_retained_capture_origin_after_import_cut(env, monkeypatch):
    async def run():
        store, client, ops, order = env; job = order['job_ref']
        await ops.submit_once(job, operation_key='submit')
        original = ops._import_capture
        def cut(*args): raise RuntimeError('fixture interruption before receipt commit')
        with monkeypatch.context() as patch:
            patch.setattr(ops, '_import_capture', cut)
            with pytest.raises(RuntimeError, match='fixture interruption'):
                await ops.status_once_with_origin(job, operation_key='status')
        assert ops._capsule_path('status').is_dir()
        assert store.db.execute("SELECT count(*) FROM public_search_operations WHERE operation_key='status'").fetchone()[0] == 0
        assert_wrapper(await ops.status_once_with_origin(job, operation_key='status'), 'capture_reused', job, 'status')
        assert [row[0] for row in client.calls] == ['submit', 'status']
    asyncio.run(run())


@pytest.mark.parametrize('prerequisite', [True, False])
def test_status_no_capture_for_prerequisite_and_executor_rejection(env, monkeypatch, prerequisite):
    async def run():
        store, client, ops, order = env; job = order['job_ref']
        if not prerequisite: await ops.submit_once(job, operation_key='submit')
        def reject(*args, **kwargs): raise RuntimeError('synthetic executor rejection')
        with monkeypatch.context() as patch:
            if not prerequisite: patch.setattr(asyncio.get_running_loop(), 'run_in_executor', reject)
            receipt = assert_wrapper(await ops.status_once_with_origin(job, operation_key='status'), 'no_capture', job, 'status')
        assert receipt['outcome'] == 'failed'
        assert receipt['failure']['code'] == ('prerequisite_missing' if prerequisite else 'client_failure')
        assert all(row[0] != 'status' for row in client.calls)
        assert await ops.status_once(job, operation_key='status') == receipt
    asyncio.run(run())


def test_scheduled_client_not_sent_is_still_worker_origin(env):
    async def run():
        store, client, ops, order = env; job = order['job_ref']
        await ops.submit_once(job, operation_key='submit')
        client.error = AcquisitionError('provider_connection_failed', submission_outcome='not_sent')
        receipt = assert_wrapper(await ops.status_once_with_origin(job, operation_key='status'), 'worker_dispatched', job, 'status')
        assert receipt['outcome'] == 'failed' and receipt['failure']['native_code'] == 'provider_connection_failed'
    asyncio.run(run())


def test_same_key_concurrency_and_cancellation_preserve_capture(env):
    async def run():
        store, client, ops, order = env; job = order['job_ref']
        await ops.submit_once(job, operation_key='submit'); client.release.clear()
        task = asyncio.create_task(ops.status_once_with_origin(job, operation_key='status'))
        try:
            assert await asyncio.to_thread(client.entered.wait, 3)
            with pytest.raises(ProviderOperationInProgress):
                await ops.status_once_with_origin(job, operation_key='status')
            task.cancel()
            with pytest.raises(asyncio.CancelledError): await task
        finally:
            client.release.set()
        await asyncio.get_running_loop().shutdown_default_executor()
        assert store.db.execute("SELECT count(*) FROM public_search_operations WHERE operation_key='status'").fetchone()[0] == 0
        assert_wrapper(await ops.status_once_with_origin(job, operation_key='status'), 'capture_reused', job, 'status')
        assert [row[0] for row in client.calls] == ['submit', 'status']
    asyncio.run(run())


def test_dispatching_invocation_keeps_origin_when_another_importer_wins(env, monkeypatch):
    async def run():
        store, client, ops, order = env; job = order['job_ref']
        await ops.submit_once(job, operation_key='submit')
        original, imported = ops._dispatch, []
        async def racing(*args, **kwargs):
            value = await original(*args, **kwargs)
            with Store(store.path) as other:
                other_client = Client()
                other_ops = ProviderJobOperations(other, RemoteSearches(other, other_client), registry=registry(other_client))
                imported.append(await other_ops.status_once_with_origin(job, operation_key='status'))
                assert other_client.calls == []
            return value
        monkeypatch.setattr(ops, '_dispatch', racing)
        result = await ops.status_once_with_origin(job, operation_key='status')
        receipt = assert_wrapper(result, 'worker_dispatched', job, 'status')
        assert assert_wrapper(imported[0], 'capture_reused', job, 'status') == receipt
        assert store.db.execute("SELECT count(*) FROM public_search_operations WHERE operation_key='status'").fetchone()[0] == 1
        assert [row[0] for row in client.calls] == ['submit', 'status']
    asyncio.run(run())
