"""Selected result-state regressions over actual local HTTP, without public calls."""
import asyncio
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

from gene_annotation_episode.domain import ContractError, canonical, identity
from gene_annotation_episode.provider_jobs import RemoteSearches
from gene_annotation_episode.public_search_operations import ProviderJobOperations
from gene_annotation_episode.public_search_publication import PublicSearchResultPublisher
from gene_annotation_episode.tools import ToolRegistry
from test_hmmer_api_operations import JOB, LocalHTTPClient, registry, result_body, setup


UNFINISHED = ('PENDING', 'RECEIVED', 'STARTED', 'RETRY')
NON_SUCCESS = (*UNFINISHED, 'FAILURE', 'REVOKED')
FOREIGN = '00000000-0000-4000-8000-000000000000'


def entity(body):
    # Whitespace is deliberate: custody must preserve bytes, not reserialize JSON.
    return (json.dumps(body, indent=2) + '\n').encode()


@pytest.fixture
def local_operations(tmp_path):
    service = SimpleNamespace(requests=[], status=entity({'id': JOB, 'task': {'status': 'SUCCESS'}}),
        result=entity(result_body()))

    class Handler(BaseHTTPRequestHandler):
        def respond(self, raw):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            body = self.rfile.read(int(self.headers['Content-Length']))
            service.requests.append(('POST', self.path, body))
            self.respond(entity({'id': JOB}))

        def do_GET(self):
            service.requests.append(('GET', self.path, None))
            self.respond(service.status if self.path.startswith('/search/') else service.result)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=.01), daemon=True)
    thread.start()
    address = f'http://127.0.0.1:{server.server_port}'
    store, client, ops, order = setup(tmp_path, LocalHTTPClient(address))
    try:
        with store:
            yield SimpleNamespace(service=service, store=store, client=client, ops=ops,
                order=order, job=order['job_ref'], address=address)
    finally:
        server.shutdown()
        thread.join(5)
        server.server_close()


async def make_ready(env):
    submitted = await env.ops.submit_once(env.job, operation_key='submit')
    ready = await env.ops.status_once(env.job, operation_key='ready')
    assert submitted['remote_id'] == JOB and ready['state'] == 'SUCCESS'
    assert ready['result_ready'] is True and ready['result_cached'] is False
    assert len(env.service.requests) == 2
    return ready


def publisher(env):
    return PublicSearchResultPublisher(env.store, ToolRegistry(env.store, clients=env.client), operations=env.ops)


def assert_failure_custody(env, receipt, raw, operation, code, *, native_code='provider_response_invalid'):
    assert receipt['version'] == 'public_search_operation_v1'
    assert receipt['operation'] == operation and receipt['outcome'] == 'failed'
    assert receipt['job_ref'] == env.job and receipt['remote_id'] == JOB
    assert receipt['request_sha256'] == env.order['request_sha256']
    assert receipt['provider_chronology'] == 'unknown'
    assert receipt['failure'] == dict(code=code, native_code=native_code, phase=operation,
        submission_outcome=None, prerequisite=None, retry_after_seconds=None, http_status=None,
        diagnostic_ref=None, response_snapshot_ref=receipt['snapshot_ref'],
        affected_refs=[env.job], partial_record_refs=[])
    assert env.ops.read_operation(receipt['receipt_ref']) == receipt
    assert env.ops.read_snapshot(receipt['receipt_ref']).content == raw
    capsule = env.ops._capsule_path(receipt['operation_key'])
    assert (capsule / 'response.entity').read_bytes() == raw
    manifest = json.loads((capsule / 'manifest.json').read_bytes())
    assert manifest['client_failure'] is None
    assert manifest['snapshot']['content_sha256'] == hashlib.sha256(raw).hexdigest()
    assert manifest['snapshot']['content_bytes'] == len(raw)
    assert manifest['selection_sha256'] == receipt['selection_sha256']
    assert manifest['job_ref'] == env.job and manifest['operation'] == operation
    assert not env.store.db.in_transaction


def assert_no_result_publication(env, receipt):
    before = (len(env.service.requests), env.store.count('source'), env.store.count('reference'),
        env.store.count('observation'))
    with pytest.raises(ContractError, match='public_search_result_not_publishable'):
        publisher(env).publish(receipt['receipt_ref'], scope={'subject_refs': env.store.problem()['subject_refs']},
            operation_key='forbidden-publication')
    assert before == (len(env.service.requests), env.store.count('source'), env.store.count('reference'),
        env.store.count('observation'))


@pytest.mark.parametrize('state', NON_SUCCESS)
@pytest.mark.parametrize('body_kind', ('omitted', 'null', 'dict'))
def test_result_non_success_after_readiness_retains_state_and_one_capture(local_operations, state, body_kind):
    env = local_operations

    async def run():
        ready = await make_ready(env)
        body = None if body_kind == 'null' else {'stats': {'id': JOB, 'algo': 'phmmer', 'database': 'swissprot'}}
        raw = entity({'status': state} if body_kind == 'omitted' else {'status': state, 'result': body})
        env.service.result = raw
        receipt = await env.ops.result_once(env.job, operation_key='selected-result', page=2, page_size=2)
        code = 'remote_job_failed' if state in {'FAILURE', 'REVOKED'} else 'result_not_ready'
        assert_failure_custody(env, receipt, raw, 'result', code, native_code=None)
        assert receipt['state'] == state and receipt['result_ready'] is False
        assert receipt['result_cached'] is False and receipt['result_snapshot_refs'] == []
        assert env.ops.inspect(env.job)['result_receipt_refs'] == []
        assert env.ops.remote_searches._get(env.job)['result'] is None
        assert env.ops.read_operation(ready['receipt_ref']) == ready
        assert_no_result_publication(env, receipt)
        env.service.result = entity(result_body(2))
        assert await env.ops.result_once(env.job, operation_key='selected-result', page=2, page_size=2) == receipt
        assert len(env.service.requests) == 3
        request = urlsplit(env.service.requests[-1][1])
        assert request.path == '/result/' + JOB
        assert parse_qs(request.query) == {'page': ['2'], 'page_size': ['2'], 'with_domains': ['True']}
        with pytest.raises(ContractError, match='operation_conflict'):
            await env.ops.result_once(env.job, operation_key='selected-result', page=1, page_size=2)
        assert len(env.service.requests) == 3

    asyncio.run(run())


@pytest.mark.parametrize('operation', ('status', 'result'))
@pytest.mark.parametrize('body', ([], [1], None, 'SUCCESS', 42, True))
def test_nonobject_json_is_structured_and_same_key_replays_after_reopening(local_operations, operation, body):
    env = local_operations

    async def run():
        if operation == 'result':
            await make_ready(env)
        else:
            await env.ops.submit_once(env.job, operation_key='submit')
        raw = entity(body)
        setattr(env.service, operation, raw)
        before = env.ops.remote_searches._get(env.job)
        count = len(env.service.requests)
        if operation == 'status':
            receipt = await env.ops.status_once(env.job, operation_key='malformed')
        else:
            receipt = await env.ops.result_once(env.job, operation_key='malformed', page=1, page_size=2)
        assert_failure_custody(env, receipt, raw, operation, 'response_invalid')
        assert receipt['result_cached'] is False and receipt['result_ready'] is None
        assert env.ops.remote_searches._get(env.job) == before
        assert_no_result_publication(env, receipt)
        new_client = LocalHTTPClient(env.address)
        reopened = ProviderJobOperations(env.store, RemoteSearches(env.store, new_client), registry=registry(new_client))
        if operation == 'status':
            repeated = await reopened.status_once(env.job, operation_key='malformed')
        else:
            repeated = await reopened.result_once(env.job, operation_key='malformed', page=1, page_size=2)
        assert repeated == receipt and len(env.service.requests) == count + 1

    asyncio.run(run())


@pytest.mark.parametrize('body', (
    {'status': 'SUCCESS', 'result': None},
    {'status': 'SUCCESS', 'result': []},
    {'status': 'SUCCESS', 'result': 'not-a-result'},
    {'status': 'SUCCESS', 'result': 0},
    {'status': 'SUCCESS'},
    {'status': 'SUCCESS', 'result': {}},
    {'status': 'SUCCESS', 'result': {'hits': None}},
    {'status': 'SUCCESS', 'result': {'hits': {}}},
    {'status': 'SUCCESS', 'result': {'hits': [], 'stats': []}},
))
def test_success_requires_result_dictionary_and_hits_list(local_operations, body):
    env = local_operations

    async def run():
        await make_ready(env)
        raw = entity(body)
        env.service.result = raw
        receipt = await env.ops.result_once(env.job, operation_key='invalid-success', page=1, page_size=2)
        assert receipt['failure']['code'] == 'response_invalid'
        assert env.ops.read_snapshot(receipt['receipt_ref']).content == raw
        assert receipt['result_cached'] is False and receipt['result_snapshot_refs'] == []
        assert env.ops.inspect(env.job)['result_receipt_refs'] == []
        assert env.ops.remote_searches._get(env.job)['result'] is None
        assert_no_result_publication(env, receipt)
        assert await env.ops.result_once(env.job, operation_key='invalid-success', page=1, page_size=2) == receipt
        assert len(env.service.requests) == 3

    asyncio.run(run())


@pytest.mark.parametrize('state', ('PENDING', 'FAILURE', 'SUCCESS'))
@pytest.mark.parametrize('field,wrong', (
    ('id', FOREIGN), ('algo', 'hmmscan'), ('database', {'id': 'pdb'}), ('input', '>foreign\nYYYYYYYY'),
))
def test_present_result_envelope_identity_cannot_become_not_ready_or_success(local_operations, state, field, wrong):
    env = local_operations

    async def run():
        await make_ready(env)
        body = result_body()
        body.update(status=state, **{field: wrong})
        if state != 'SUCCESS':
            body['result'] = None
        raw = entity(body)
        env.service.result = raw
        receipt = await env.ops.result_once(env.job, operation_key='foreign-envelope', page=1, page_size=2)
        assert_failure_custody(env, receipt, raw, 'result', 'remote_identity_conflict',
            native_code='remote_identity_conflict_' + field)
        assert receipt['result_cached'] is False and receipt['result_ready'] is None
        assert env.ops.inspect(env.job)['result_receipt_refs'] == []
        assert_no_result_publication(env, receipt)
        assert await env.ops.result_once(env.job, operation_key='foreign-envelope', page=1, page_size=2) == receipt
        assert len(env.service.requests) == 3

    asyncio.run(run())


@pytest.mark.parametrize('state', ('PENDING', 'FAILURE', 'SUCCESS'))
@pytest.mark.parametrize('field,wrong', (('id', FOREIGN), ('algo', 'hmmscan'), ('database', {'id': 'pdb'})))
def test_present_nested_stats_identity_is_checked_for_every_result_state(local_operations, state, field, wrong):
    env = local_operations

    async def run():
        await make_ready(env)
        body = result_body()
        body['status'] = state
        body['result']['stats'][field] = wrong
        raw = entity(body)
        env.service.result = raw
        receipt = await env.ops.result_once(env.job, operation_key='foreign-stats', page=1, page_size=2)
        assert_failure_custody(env, receipt, raw, 'result', 'remote_identity_conflict',
            native_code='remote_identity_conflict_' + field)
        assert receipt['result_cached'] is False and receipt['result_ready'] is None
        assert_no_result_publication(env, receipt)
        assert await env.ops.result_once(env.job, operation_key='foreign-stats', page=1, page_size=2) == receipt
        assert len(env.service.requests) == 3

    asyncio.run(run())


@pytest.mark.parametrize('operation,body', (
    ('status', {}), ('status', {'status': 'SUCCESS'}), ('status', {'task': None}),
    ('status', {'task': []}), ('status', {'task': {'status': []}}),
    ('status', {'task': {'status': 'unknown'}}),
    ('result', {}), ('result', {'task': {'status': 'SUCCESS'}, 'result': None}),
    ('result', {'status': None, 'result': None}), ('result', {'status': [], 'result': None}),
    ('result', {'status': 'unknown', 'result': None}),
    ('result', {'status': 'PENDING', 'result': []}),
    ('result', {'status': 'PENDING', 'result': 'malformed'}),
    ('result', {'status': 'PENDING', 'result': {'stats': []}}),
))
def test_malformed_envelope_and_state_remain_response_invalid(local_operations, operation, body):
    env = local_operations

    async def run():
        await make_ready(env)
        raw = entity(body)
        setattr(env.service, operation, raw)
        before = env.ops.remote_searches._get(env.job)
        if operation == 'status':
            receipt = await env.ops.status_once(env.job, operation_key='invalid-envelope')
        else:
            receipt = await env.ops.result_once(env.job, operation_key='invalid-envelope', page=1, page_size=2)
        assert receipt['failure']['code'] == 'response_invalid'
        assert env.ops.read_snapshot(receipt['receipt_ref']).content == raw
        assert env.ops.remote_searches._get(env.job) == before
        assert receipt['result_cached'] is False and receipt['result_ready'] is None
        assert_no_result_publication(env, receipt)
        assert len(env.service.requests) == 3

    asyncio.run(run())


@pytest.mark.parametrize('body,code', (
    ({'status': 'PENDING', 'result': None}, 'result_not_ready'),
    ({'status': 'FAILURE', 'result': None}, 'remote_job_failed'),
    ({'status': 'SUCCESS', 'result': None}, 'response_invalid'),
    ([], 'response_invalid'),
    ({'status': 'PENDING', 'id': FOREIGN, 'result': None}, 'remote_identity_conflict'),
))
def test_later_failed_selector_preserves_first_valid_result_and_publication(local_operations, body, code):
    env = local_operations

    async def run():
        await make_ready(env)
        original = await env.ops.result_once(env.job, operation_key='original-result', page=1, page_size=2)
        original_job = env.ops.remote_searches._get(env.job)
        published = publisher(env).publish(original['receipt_ref'],
            scope={'subject_refs': env.store.problem()['subject_refs']}, operation_key='original-publication')
        counts = (env.store.count('source'), env.store.count('reference'), env.store.count('observation'))
        raw = entity(body)
        env.service.result = raw
        failed = await env.ops.result_once(env.job, operation_key='later-result', page=2, page_size=2)
        assert failed['failure']['code'] == code
        assert failed['result_cached'] is True and failed['result_snapshot_refs'] == [original['snapshot_ref']]
        assert failed['result_ready'] is (False if code in {'result_not_ready', 'remote_job_failed'} else None)
        assert env.ops.read_snapshot(failed['receipt_ref']).content == raw
        assert env.ops.remote_searches._get(env.job) == original_job
        assert env.ops.read_operation(original['receipt_ref']) == original
        assert env.ops.inspect(env.job)['result_receipt_refs'] == [original['receipt_ref']]
        assert_no_result_publication(env, failed)
        cached = await env.ops.result_once(env.job, operation_key='cached-original', page=1, page_size=2)
        assert cached['snapshot_ref'] == original['snapshot_ref'] and cached['state'] == 'SUCCESS'
        assert publisher(env).publish(original['receipt_ref'],
            scope={'subject_refs': env.store.problem()['subject_refs']}, operation_key='original-publication') == published
        assert (env.store.count('source'), env.store.count('reference'), env.store.count('observation')) == counts
        assert await env.ops.result_once(env.job, operation_key='later-result', page=2, page_size=2) == failed
        assert len(env.service.requests) == 4

    asyncio.run(run())


def test_success_keeps_original_selector_identity_and_publication(local_operations):
    env = local_operations

    async def run():
        await make_ready(env)
        body = result_body(2)
        body.update(id=JOB.upper(), algo='phmmer', database={'id': 'swissprot'}, input='>renamed\nmacdefgh')
        env.service.result = raw = entity(body)
        receipt = await env.ops.result_once(env.job, operation_key='selected-success', page=2, page_size=2)
        selection = dict(registry=env.ops.registry, job_ref=env.job, operation='result',
            operation_key='selected-success', operands={'page': 2, 'page_size': 2})
        assert receipt['selection_sha256'] == hashlib.sha256(canonical(selection).encode()).hexdigest()
        assert receipt['receipt_ref'] == identity('provider_operation',
            {'registry_ref': env.ops.registry['registry_ref'], 'operation_key': 'selected-success'})
        assert receipt['outcome'] == 'completed' and receipt['failure'] is None
        assert receipt['state'] == 'SUCCESS' and receipt['result_ready'] is True and receipt['result_cached'] is True
        snapshot = env.ops.read_snapshot(receipt['receipt_ref'])
        assert snapshot.content == raw and snapshot.request['page'] == 2 and snapshot.request['page_size'] == 2
        assert snapshot.transport['job_ref'] == env.job
        result = publisher(env).publish(receipt['receipt_ref'],
            scope={'subject_refs': env.store.problem()['subject_refs']}, operation_key='success-publication')['result']
        proof = env.store.get(result['publication_ref'])
        published = json.loads(env.store.get_artifact(proof['artifact_ref']))
        assert published['selector'] == dict(version='public_search_result_selector_v1', provider='hmmer',
            first_page=2, last_page=2, page_size=2)
        assert env.store.get_artifact(env.store.get(result['source_ref'])['artifact_ref']) == raw
        assert all(row['acquisition_receipt_ref'] == receipt['receipt_ref'] and row['page'] == 2
            and row['page_size'] == 2 and row['job_ref'] == env.job for row in result['publication_rows'])
        assert await env.ops.result_once(env.job, operation_key='selected-success', page=2, page_size=2) == receipt
        assert len(env.service.requests) == 3 and not env.store.current_annotations()

    asyncio.run(run())
