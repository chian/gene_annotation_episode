"""Actual local HTTP custody through external progress and received credit.

The service, biological sequence, decisions and information unit are fixtures.
These checks contact no public provider, configured model or native executor.
"""
import asyncio
from contextlib import contextmanager
from copy import deepcopy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from types import SimpleNamespace
import urllib.parse

import pytest

from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_monitoring import FIELDS, MonitorEpisodes, ProgressProvider
from gene_annotation_episode.episode_progress_credit import ProgressInformationCredit
from gene_annotation_episode.hmmer_progress import HmmerProgressProvider
from gene_annotation_episode.progress_records import (external_job_status,
    validate_external_job_status, EXTERNAL_JOB_STATUS_SCHEMA)
from gene_annotation_episode.public_search_operations import (ProviderJobOperations,
    PublicSearchPorts, hmmer_client_binding_sha256)
from gene_annotation_episode.public_search_publication import PublicSearchResultPublisher
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from method_loop.durable import DurableExecutionStore, content_digest
from method_loop.identities import EpisodeRef
from test_durable_episode import commission_spec
from test_recursive_monitoring import Services, assignment
from test_job_progress_consumer import ContractJob


RUN = 'durable-fixture-run'
REMOTE = 'f2e3e0dd-fb31-4c56-bd23-438f000d59ec'
PROTEIN = 'MKWAA'


class LocalHmmerClient(PublicClients):
    """An explicitly identified local fixture using the actual HTTP transport."""

    def __init__(self, base):
        super().__init__(timeout=5)
        self.base = base
        self.hmmer_fixture_binding = {'transport_timeout_seconds': self.timeout,
            'submit_url_prefix': base + '/search/', 'status_url_prefix': base + '/search/',
            'result_url_prefix': base + '/result/'}

    def hmmer_submit(self, query_fasta, *, algorithm, database, parameters=None):
        return self._http('fixture_hmmer', self.base + '/search/' + algorithm,
            {}, 'application/json', json_body={'input': query_fasta, 'database': database,
                                               **(parameters or {})})

    def hmmer_status(self, job_id):
        return self._http('fixture_hmmer', self.base + '/search/' + job_id, {}, 'application/json')

    def hmmer_result(self, job_id, *, page=1, page_size=50, with_domains=True):
        return self._http('fixture_hmmer', self.base + '/result/' + job_id,
            {'page': page, 'page_size': page_size, 'with_domains': str(with_domains).lower()},
            'application/json')


@contextmanager
def local_service():
    state = SimpleNamespace(status='PENDING', calls=[], started=threading.Event(),
                            release=threading.Event(), delay_next=False, invalid=False)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def respond(self, body):
            raw = json.dumps(body).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            state.calls.append(('POST', self.path, body))
            self.respond({'id': REMOTE})

        def do_GET(self):
            state.calls.append(('GET', self.path, None))
            if self.path.startswith('/result/'):
                self.respond({'status': 'SUCCESS', 'result': {'stats': {
                    'id': REMOTE, 'algo': 'phmmer', 'database': 'fixture'}, 'hits': []}})
                return
            selected_status = state.status
            if state.delay_next:
                state.delay_next = False
                state.started.set()
                assert state.release.wait(10), 'test fixture release missing'
            self.respond({} if state.invalid else {'id': REMOTE, 'algo': 'phmmer',
                'database': 'fixture', 'task': {'status': selected_status}})

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state, LocalHmmerClient('http://127.0.0.1:' + str(server.server_address[1]))
    finally:
        state.release.set()
        server.shutdown()
        server.server_close()
        thread.join(10)


@pytest.fixture
def saved(tmp_path):
    with local_service() as (http, client), Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence=PROTEIN, molecule='protein')
        query = store.problem()['subject_refs'][0]
        registry = {'version': 'public_search_registry_v1',
            'registry_ref': 'execution_registry_fixture_api', 'resource_id': 'fixture_hmmer_service',
            'provider': 'hmmer', 'client_binding_sha256': hmmer_client_binding_sha256(client)}
        tools = ToolRegistry(store, clients=client)
        operations = ProviderJobOperations(store, tools.remote_searches, registry=registry)
        publisher = PublicSearchResultPublisher(store, tools, operations=operations)
        ports = PublicSearchPorts(registry, operations, publisher)
        original_scope = store.validate_scope({'subject_refs': [query], 'segments': store.coverage(query)})
        order = operations.order(operation_key='original-order', provider='hmmer',
            subject_ref=query, query_fasta='>query\n' + PROTEIN + '\n',
            algorithm='phmmer', database='fixture', parameters={}, page_size=50,
            scope=original_scope)
        provider = HmmerProgressProvider(store, run_id=RUN, ports=ports)
        scope = provider.scope(order['job_ref'])
        durable = DurableExecutionStore(tmp_path / 'executions')
        c8 = ProgressProvider(store, durable, run_id=RUN, job_provider=provider)
        yield SimpleNamespace(http=http, client=client, store=store, operations=operations,
            ports=ports, order=order, provider=provider, scope=scope, c8=c8, durable=durable,
            query=query, job=order['job_ref'], tools=tools)


def submit(saved):
    receipt = asyncio.run(saved.operations.submit_once(saved.job, operation_key='selected-submit'))
    assert receipt['outcome'] == 'completed'


def observe(saved, key, *, fields=FIELDS):
    return asyncio.run(saved.c8.observe_async(saved.job, fields, saved.scope, operation_key=key))


def status_calls(saved):
    return [row for row in saved.http.calls if row[0] == 'GET' and row[1].startswith('/search/')]


def project(saved, known, initial=()):
    context = BindingContext(RUN, 'receiver', 'monitor', (('monitor', 'receiver'),),
        saved.scope, {}, {})
    return ProgressInformationCredit(saved.c8, information_unit=.25)(context, {
        'run_id': RUN, 'episode_id': 'receiver', 'known_progress_refs': list(known),
        'initial_progress_refs': list(initial)})


def test_explicit_descriptor_scope_and_no_execution_from_addressability(saved):
    record = saved.provider.as_record()
    assert set(record) == {'version', 'registry', 'implementation_sha256'}
    assert record['registry'] == saved.ports.registry
    assert record['implementation_sha256'] == hashlib.sha256(Path(
        'gene_annotation_episode/hmmer_progress.py').read_bytes()).hexdigest()
    assert saved.provider.direct_dependencies(saved.job, saved.scope) == []
    assert saved.http.calls == []
    assert saved.operations.inspect(saved.job)['state'] == 'not_submitted'
    record['registry']['resource_id'] = 'mutated presentation'
    assert saved.provider.as_record()['registry'] == saved.ports.registry
    with pytest.raises(ContractError, match='outside_scope'):
        saved.provider.scope(saved.job)
        saved.provider.direct_dependencies(saved.job, {'subject_refs': [saved.query], 'segments': [{
            'target_ref': saved.query, 'start': 0, 'end': 1, 'unit': 'aa'}]})


def test_sync_entry_rejects_async_provider_without_dispatch_or_event_loop(saved):
    submit(saved)
    with pytest.raises(ContractError, match='asynchronous_progress_observation_required'):
        saved.c8.observe(saved.job, FIELDS, saved.scope, operation_key='sync-selected')
    assert status_calls(saved) == []
    assert saved.store.db.execute('SELECT count(*) FROM runtime_progress_observations').fetchone()[0] == 0


def test_one_status_capture_has_exact_source_custody_and_no_native_facts(saved):
    submit(saved)
    snapshot = observe(saved, 'selected-status')
    status = validate_external_job_status(snapshot['execution_status'])
    assert set(status) == set(EXTERNAL_JOB_STATUS_SCHEMA['properties'])
    assert status['native_state'] == 'PENDING' and status['lifecycle_state'] == 'pending'
    assert status['provider_chronology'] == 'unknown' and status['remote_id'] == REMOTE
    assert status['result_available'] is False
    assert snapshot['measurements'] == snapshot['log_windows'] == []
    assert snapshot['dependencies'] == snapshot['committed_record_refs'] == []
    assert len(status_calls(saved)) == 1
    source = next(saved.store.get(reference) for reference in snapshot['provenance_refs']
                  if reference.startswith('source_'))
    body = json.loads(saved.store.get_artifact(source['request_ref']))
    receipt = saved.operations.read_operation(status['status_receipt_ref'])
    raw = saved.operations.read_snapshot(receipt['receipt_ref'])
    assert body['receipt'] == receipt and body['order'] == saved.order
    assert saved.store.get_artifact(source['artifact_ref']) == raw.content
    assert body['snapshot']['retrieved_at'] == raw.retrieved_at
    assert source['retrieved_at'] == receipt['observed_at'] == snapshot['observed_at']
    assert saved.store.reference_subset([source['id'], source['artifact_ref']], saved.scope)
    assert not saved.store.list('observation') and not saved.store.list('native_execution')


def test_same_state_distinct_http_receipts_reuse_original_delivery_and_credit(saved):
    submit(saved)
    first = observe(saved, 'first-status')
    # The selected operands remain exact; field ordering changes no exposed fact.
    second = observe(saved, 'second-status', fields=list(reversed(FIELDS)))
    assert first == second
    references = saved.operations.inspect(saved.job)['latest_operation_refs']
    receipts = [saved.operations.read_operation(ref) for ref in references]
    statuses = [receipt for receipt in receipts if receipt['operation'] == 'status']
    assert len(statuses) == len(status_calls(saved)) == 2
    assert statuses[0]['receipt_ref'] != statuses[1]['receipt_ref']
    assert statuses[0]['observed_at'] != statuses[1]['observed_at']
    assert first['execution_status']['status_receipt_ref'] == statuses[0]['receipt_ref']
    assert project(saved, [second['progress_ref']], [first['progress_ref']])['credit'] == 0
    assert saved.store.db.execute('SELECT count(*) FROM runtime_hmmer_progress_operations').fetchone()[0] == 2
    assert saved.store.db.execute('SELECT count(*) FROM runtime_hmmer_progress_snapshots').fetchone()[0] == 1
    with pytest.raises(ContractError, match='identity_conflict'):
        observe(saved, 'first-status', fields=list(reversed(FIELDS)))
    assert len(status_calls(saved)) == 2


def test_selected_replay_restores_original_before_http_even_after_reopen(saved):
    submit(saved)
    first = observe(saved, 'original-selection')
    saved.http.status = 'SUCCESS'
    assert observe(saved, 'original-selection') == first
    assert len(status_calls(saved)) == 1
    with Store(saved.store.path) as reopened:
        tools = ToolRegistry(reopened, clients=saved.client)
        operations = ProviderJobOperations(reopened, tools.remote_searches,
                                          registry=saved.ports.registry)
        provider = HmmerProgressProvider(reopened, run_id=RUN,
            ports=PublicSearchPorts(saved.ports.registry, operations,
                PublicSearchResultPublisher(reopened, tools, operations=operations)))
        c8 = ProgressProvider(reopened, saved.durable, run_id=RUN, job_provider=provider)
        assert asyncio.run(c8.observe_async(saved.job, FIELDS, saved.scope,
            operation_key='original-selection')) == first
    assert len(status_calls(saved)) == 1
    with pytest.raises(ContractError, match='identity_conflict'):
        observe(saved, 'original-selection', fields=['execution_status'])


def test_raw_state_changes_only_earn_existing_lifecycle_availability_failure_categories(saved):
    submit(saved)
    values = [observe(saved, 'pending')]
    for state in ('RECEIVED', 'RETRY', 'STARTED', 'SUCCESS', 'FAILURE', 'REVOKED'):
        saved.http.status = state
        values.append(observe(saved, state))
    assert len({value['progress_ref'] for value in values}) == 7
    assert project(saved, [value['progress_ref'] for value in values[1:]],
        [values[0]['progress_ref']])['credit'] == .75
    assert project(saved, [values[1]['progress_ref'], values[2]['progress_ref']],
        [values[0]['progress_ref']])['credit'] == 0
    assert values[-1]['execution_status']['failure_code'] == 'remote_job_failed'
    assert not values[-1]['result_available']


def test_failed_response_retains_provider_receipt_without_c8_snapshot(saved):
    submit(saved)
    saved.http.invalid = True
    with pytest.raises(ContractError, match='external_progress_observation_failed') as failure:
        observe(saved, 'malformed-status')
    detail = failure.value.detail
    receipt = saved.operations.read_operation(detail['receipt_ref'])
    assert receipt['failure'] == detail['failure'] and receipt['failure']['code'] == 'response_invalid'
    assert saved.operations.read_snapshot(receipt['receipt_ref']).content == b'{}'
    assert saved.store.db.execute('SELECT count(*) FROM runtime_progress_observations').fetchone()[0] == 0
    assert saved.store.db.execute('SELECT count(*) FROM runtime_hmmer_progress_snapshots').fetchone()[0] == 0
    assert not [row for row in saved.store.list('source')
                if row['provider'].startswith('hmmer.progress.')]


def test_monitor_maps_external_failure_to_failed_provider_outcome(saved):
    submit(saved)
    saved.http.invalid = True

    class AsyncServices(Services):
        async def observe_progress(self, handle, fields, scope, **kwargs):
            return await self.provider.observe_async(handle, fields, scope, **kwargs)

    services = AsyncServices(saved.store, saved.c8)
    binding = MonitorEpisodes(services)
    context = BindingContext(RUN, 'monitor-fixture', 'monitor', (('monitor', 'monitor-fixture'),),
        saved.scope, assignment(saved.job), {})
    outcome = asyncio.run(binding.execute(context, 'progress.observe',
        {'requested_fields': list(FIELDS)}, 'failed-monitor-status'))
    assert outcome['status'] == 'failed' and outcome['progress_refs'] == []
    assert outcome['feedback']['category'] == 'provider_failure'
    assert outcome['feedback']['code'] == 'external_progress_observation_failed'
    assert saved.store.db.execute('SELECT count(*) FROM runtime_progress_observations').fetchone()[0] == 0


def test_same_key_status_contention_is_failed_provider_work_without_a_receipt(saved):
    submit(saved)
    saved.http.delay_next = True

    class AsyncServices(Services):
        async def observe_progress(self, handle, fields, scope, **kwargs):
            return await self.provider.observe_async(handle, fields, scope, **kwargs)

    binding = MonitorEpisodes(AsyncServices(saved.store, saved.c8))
    context = BindingContext(RUN, 'monitor-fixture', 'monitor', (('monitor', 'monitor-fixture'),),
        saved.scope, assignment(saved.job), {})

    async def selected():
        original = asyncio.create_task(saved.c8.observe_async(saved.job, FIELDS, saved.scope,
            operation_key='original-in-progress'))
        assert await asyncio.to_thread(saved.http.started.wait, 5)
        outcome = await binding.execute(context, 'progress.observe',
            {'requested_fields': list(FIELDS)}, 'original-in-progress')
        assert outcome == {'status': 'failed', 'record_refs': [], 'changed_record_refs': [],
            'progress_refs': [], 'feedback': {'category': 'provider_failure',
                'code': 'submission_in_progress', 'detail': {
                    'job_ref': saved.job, 'operation_key': 'original-in-progress'}}}
        assert saved.store.db.execute('SELECT count(*) FROM runtime_progress_observations').fetchone()[0] == 0
        assert saved.store.db.execute('SELECT count(*) FROM runtime_hmmer_progress_snapshots').fetchone()[0] == 0
        assert not [saved.operations.read_operation(ref) for ref in
            saved.operations.inspect(saved.job)['latest_operation_refs']
            if saved.operations.read_operation(ref)['operation'] == 'status']
        saved.http.release.set()
        return await asyncio.wait_for(original, 5)

    snapshot = asyncio.run(selected())
    assert len(status_calls(saved)) == 1
    assert snapshot['execution_status']['native_state'] == 'PENDING'
    statuses = [saved.operations.read_operation(ref) for ref in
        saved.operations.inspect(saved.job)['latest_operation_refs']
        if saved.operations.read_operation(ref)['operation'] == 'status']
    assert len(statuses) == 1 and statuses[0]['operation_key'] == 'original-in-progress'


def test_async_c8_preserves_existing_synchronous_native_provider_and_original_replay(tmp_path):
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence=PROTEIN, molecule='protein')
        scope = store.validate_scope({'subject_refs': store.problem()['subject_refs']})
        native = ContractJob(store, scope)
        provider = ProgressProvider(store, DurableExecutionStore(tmp_path / 'executions'),
            run_id=RUN, job_provider=native)
        snapshot = asyncio.run(provider.observe_async(native.handle, FIELDS, scope,
            operation_key='native-through-async'))
        assert snapshot['execution_status']['version'] == 'job_execution_status_v1'
        assert native.native_reads == 1
        native.native.update(state='returned', outcome='succeeded', elapsed_seconds=5)
        assert provider.observe(native.handle, FIELDS, scope,
            operation_key='native-through-async') == snapshot
        assert asyncio.run(provider.observe_async(native.handle, FIELDS, scope,
            operation_key='native-through-async')) == snapshot
        assert native.native_reads == 1


def test_no_store_transaction_spans_awaited_http_and_other_writer_can_commit(saved):
    submit(saved)
    saved.http.delay_next = True

    async def selected():
        task = asyncio.create_task(saved.c8.observe_async(saved.job, FIELDS, saved.scope,
            operation_key='delayed-status'))
        assert await asyncio.to_thread(saved.http.started.wait, 5)
        assert saved.store.db.in_transaction is False
        with Store(saved.store.path) as other:
            source = other._caller_source({'fixture': 'independent committed fact'}, 'fixture')
            assert other.db.in_transaction is False
        saved.http.release.set()
        return await asyncio.wait_for(task, 5), source

    snapshot, source = asyncio.run(selected())
    assert saved.store.get(source['id'])['provider'] == 'fixture'
    assert snapshot['execution_status']['native_state'] == 'PENDING'
    assert len(status_calls(saved)) == 1


@pytest.mark.parametrize('transaction', ['write', 'read'])
def test_existing_caller_transaction_fails_before_http(saved, transaction):
    submit(saved)
    manager = saved.store.transaction if transaction == 'write' else saved.store.read_snapshot
    with manager(), pytest.raises(ContractError, match='requires_committed_transaction'):
        observe(saved, 'not-dispatched')
    assert status_calls(saved) == []


def test_result_committed_during_earlier_pending_status_remains_available(saved):
    submit(saved)
    saved.http.status = 'SUCCESS'
    ready = observe(saved, 'ready')
    saved.http.status = 'PENDING'
    saved.http.delay_next = True

    async def selected():
        task = asyncio.create_task(saved.c8.observe_async(saved.job, FIELDS, saved.scope,
            operation_key='earlier-pending'))
        assert await asyncio.to_thread(saved.http.started.wait, 5)
        result = await saved.operations.result_once(saved.job, operation_key='selected-page',
            page=1, page_size=50)
        assert result['outcome'] == 'completed'
        saved.http.release.set()
        return await asyncio.wait_for(task, 5), result

    later, result = asyncio.run(selected())
    status = later['execution_status']
    assert status['native_state'] == 'PENDING' and status['lifecycle_state'] == 'returned'
    assert status['lifecycle_basis'] == 'validated_result_capture'
    assert status['result_cached'] and later['result_available']
    assert status['result_snapshot_refs'] == [result['snapshot_ref']]
    assert saved.operations.inspect(saved.job)['state'] == 'returned'
    assert ready['execution_status']['result_cached'] is False
    assert ready['execution_status']['result_snapshot_refs'] == []
    assert saved.c8.read_progress(ready['progress_ref'], saved.scope) == ready
    repeated = observe(saved, 'same-cached-facts')
    assert repeated == later
    assert project(saved, [later['progress_ref']], [ready['progress_ref']])['credit'] == 0
    custody = json.loads(saved.store.get_artifact(saved.store.get(next(ref for ref in
        later['provenance_refs'] if ref.startswith('source_')))['request_ref']))
    raw = saved.operations.read_snapshot(result['receipt_ref'])
    assert custody['result_captures'] == [[saved.job, saved.order['request_sha256'],
        1, 50, raw.sha256]]


def test_pending_observation_before_result_capture_is_not_repriced(saved):
    submit(saved)
    saved.http.status = 'SUCCESS'
    observe(saved, 'successful-status')
    saved.http.status = 'PENDING'
    before = observe(saved, 'before-result')
    # Explicit SUCCESS is selected again to authorize this separate acquisition.
    saved.http.status = 'SUCCESS'
    observe(saved, 'new-ready')
    asyncio.run(saved.operations.result_once(saved.job, operation_key='page-after', page=1, page_size=50))
    saved.http.status = 'PENDING'
    after = observe(saved, 'after-result')
    assert before['result_available'] is False and after['result_available'] is True
    assert before['execution_status']['lifecycle_state'] == 'pending'
    assert after['execution_status']['lifecycle_state'] == 'returned'
    assert saved.c8.read_progress(before['progress_ref'], saved.scope) == before


@pytest.mark.parametrize('key', [None, '', 1])
def test_external_observation_requires_original_selected_key_before_http(saved, key):
    submit(saved)
    with pytest.raises(ContractError, match='operation_key_required'):
        asyncio.run(saved.provider.observe(saved.job, FIELDS, saved.scope, operation_key=key))
    assert status_calls(saved) == []


@pytest.mark.parametrize('change', [
    {'remote_id': 'not-a-UUID'}, {'lifecycle_state': None}, {'native_state': 'unrecognized'},
    {'provider_chronology': 'ordered'}, {'result_available': True}, {'result_cached': True},
    {'lifecycle_basis': 'validated_result_capture'}, {'failure_code': 'guessed_failure'},
    {'observed_at': '2026-10-22T01:00:00-05:00'}, {'status_snapshot_ref': None},
])
def test_external_status_rejects_invalid_relationships_and_invented_facts(saved, change):
    submit(saved)
    status = observe(saved, 'valid')['execution_status']
    with pytest.raises((ContractError, ValueError)):
        validate_external_job_status({**status, **change})


def assigned_spec(saved, tmp_path, *, results=False):
    spec = commission_spec(tmp_path, key='assigned-api')
    role = 'results' if results else 'launch_api'
    spec['child']['path'][-1][0] = spec['child']['role'] = role
    spec['child']['episode_id'] = EpisodeRef(RUN, spec['child']['path']).episode_id
    spec['child']['scope'] = saved.scope
    selected = {'resource_id': saved.ports.registry['resource_id'], 'kind': 'api',
        'capability_binding_ref': saved.ports.registry['registry_ref'], 'allocation': {
            'cpu': None, 'memory_bytes': None, 'scratch_bytes': None, 'wall_seconds': None}}
    value = {'adapter_assignment': saved.order}
    if results:
        value['handoff'] = {'resource_selection': selected}
        spec['resource_selection'] = deepcopy(selected)
    else:
        value['resource_selection'] = spec['resource_selection'] = selected
    spec['child']['request']['message'] = {'episode_assignment': value}
    return spec


@pytest.mark.parametrize('results', [False, True])
def test_assigned_dependency_is_original_exact_source_without_status(saved, tmp_path, results):
    spec = assigned_spec(saved, tmp_path, results=results)
    relation = saved.provider.dependency(spec, operation_key='original-dependency')
    assert relation == saved.provider.dependency(spec, operation_key='replayed-dependency')
    assert relation == saved.provider.dependency(spec, operation_key='original-dependency')
    assert set(relation) == {'handle', 'kind', 'relation_ref', 'observed_at', 'state'}
    assert relation['handle'] == saved.job and relation['kind'] == 'job' and relation['state'] == 'pending'
    source = saved.store.get(relation['relation_ref'])
    body = json.loads(saved.store.get_artifact(source['request_ref']))
    assert body == {'version': 'api_job_dependency_v1', 'run_id': RUN,
        'owner_handle': spec['handle'], 'owner_episode_id': spec['child']['episode_id'],
        'commission_sha256': content_digest(spec), 'registry_ref': saved.ports.registry['registry_ref'],
        'job_ref': saved.job, 'request_sha256': saved.order['request_sha256'],
        'order_operation_key': saved.order['order_operation_key']}
    assert source['retrieved_at'] == relation['observed_at'] and source['operand_refs'] == [saved.query]
    assert saved.http.calls == []
    changed = deepcopy(spec)
    changed['constraints']['different'] = True
    with pytest.raises(ContractError, match='identity_conflict'):
        saved.provider.dependency(changed, operation_key='original-dependency')


def test_foreign_dependency_is_absent_and_recognized_order_conflicts_fail(saved, tmp_path):
    spec = assigned_spec(saved, tmp_path)
    foreign = deepcopy(spec)
    selected = foreign['child']['request']['message']['episode_assignment']['resource_selection']
    selected['resource_id'] = 'foreign resource'
    foreign['resource_selection'] = deepcopy(selected)
    assert saved.provider.dependency(foreign, operation_key='foreign') is None
    spec['child']['request']['message']['episode_assignment']['adapter_assignment']['request_sha256'] = 'f' * 64
    with pytest.raises(ContractError, match='identity_conflict'):
        saved.provider.dependency(spec, operation_key='conflicting-order')
    assert saved.http.calls == []


@pytest.mark.parametrize('results', [False, True])
@pytest.mark.parametrize('changed', [None, {'resource_id': 'foreign resource', 'kind': 'api',
    'capability_binding_ref': 'execution_registry_foreign', 'allocation': {
        'cpu': None, 'memory_bytes': None, 'scratch_bytes': None, 'wall_seconds': None}}])
def test_recognized_dependency_rejects_durable_resource_mismatch(saved, tmp_path, results, changed):
    spec = assigned_spec(saved, tmp_path, results=results)
    spec['resource_selection'] = deepcopy(changed)
    with pytest.raises(ContractError, match='assignment_registry_conflict'):
        saved.provider.dependency(spec, operation_key='conflicting-selection')
    assert saved.http.calls == []


def test_original_scope_is_not_reassigned_by_order_reuse_or_commission(saved, tmp_path):
    original = saved.operations.open_scope(saved.job)
    changed = deepcopy(saved.scope)
    changed['segments'][0]['end'] -= 1
    with pytest.raises(ContractError, match='identity_conflict'):
        saved.operations.order(operation_key='original-order', provider='hmmer',
            subject_ref=saved.query, query_fasta='>query\n' + PROTEIN + '\n',
            algorithm='phmmer', database='fixture', parameters={}, page_size=50, scope=changed)
    assert saved.operations.open_scope(saved.job) == original
    spec = assigned_spec(saved, tmp_path)
    # The original explicit scope is not replaced by a containing parent scope,
    # even if this full-input fixture happens to have equal covered positions.
    spec['child']['scope'] = {'subject_refs': saved.scope['subject_refs']}
    with pytest.raises(ContractError, match='assignment_scope_conflict'):
        saved.provider.dependency(spec, operation_key='changed-assigned-scope')
    assert saved.http.calls == []


@pytest.mark.parametrize('kind', ['feature', 'external_reference', 'unspecified_input', 'read_subject'])
def test_progress_uses_actual_sequence_reader_and_original_parent_scope(tmp_path, kind):
    with local_service() as (http, client), Store(tmp_path / 'state') as store:
        if kind == 'read_subject':
            material = tmp_path / 'reads.fastq'
            material.write_bytes(b'@fixture\nMKWAA\n+\nIIIII\n@other\nAAAAA\n+\nIIIII\n')
            store.create_problem(material, molecule='unspecified')
        else:
            store.create_problem(raw_sequence=PROTEIN,
                molecule='unspecified' if kind == 'unspecified_input' else 'protein')
        targets = store.problem()['subject_refs']
        tools = ToolRegistry(store, clients=client)
        if kind == 'feature':
            query = store.put('feature', {'subject_ref': targets[0], 'kind': 'sequence_region',
                'segments': [{'start': 1, 'end': 4}], 'strand': '+', 'context_refs': []},
                origin='reasoning')['id']
            assert not store.get(query).get('sequence_ref')
        elif kind == 'external_reference':
            source = store._caller_source({'sequence': PROTEIN, 'fixture_evidence': True},
                                          'fixture_external_sequence')
            query = store.put('reference', {'reference_type': 'protein', 'source_ref': source['id'],
                'accession': 'fixture_reference', 'label': 'Fixture evidence sequence',
                'sequence_ref': store.artifact(PROTEIN), 'molecule': 'protein', 'length': len(PROTEIN),
                'term_refs': [], 'context_refs': [], 'anchor': None}, origin='external')['id']
            assert store.roots(query) == []
        elif kind == 'read_subject':
            page = tools.execute('library.members', {'library_ref': targets[0]},
                                 operation_key='fixture-members')
            assert page['status'] == 'completed'
            query = page['result']['members'][0]['id']
            assert not store.get(query).get('sequence_ref')
            assert store.subject_unit(query) == 'symbol'
        else:
            query = targets[0]
            assert store.subject_unit(query) == 'symbol'
        if kind == 'external_reference':
            # This is the actual assigning parent's focused target scope. The
            # external sequence has no target geometry from which to derive it.
            original_scope = store.validate_scope({'subject_refs': targets,
                'segments': [{'target_ref': targets[0], 'start': 1, 'end': 4, 'unit': 'aa'}]})
        else:
            original_scope = store.validate_scope({'subject_refs': targets,
                                                   'segments': store.coverage(query)})
        registry = {'version': 'public_search_registry_v1',
            'registry_ref': 'execution_registry_fixture_api', 'resource_id': 'fixture_hmmer_service',
            'provider': 'hmmer', 'client_binding_sha256': hmmer_client_binding_sha256(client)}
        operations = ProviderJobOperations(store, tools.remote_searches, registry=registry)
        publisher = PublicSearchResultPublisher(store, tools, operations=operations)
        ports = PublicSearchPorts(registry, operations, publisher)
        symbols = ports.sequence_symbols(query, scope=original_scope)
        assert symbols == ('KWA' if kind == 'feature' else PROTEIN)
        order = operations.order(operation_key='original-parent-order', provider='hmmer',
            subject_ref=query, query_fasta='>' + query + '\n' + symbols, algorithm='phmmer',
            database='fixture', parameters={}, page_size=50, scope=original_scope)
        provider = HmmerProgressProvider(store, run_id=RUN, ports=ports)
        assert provider.scope(order['job_ref']) == original_scope
        assert operations.open_scope(order['job_ref'])['scope'] == original_scope
        assert http.calls == []
        outside = deepcopy(original_scope)
        outside['segments'][0]['end'] -= 1
        with pytest.raises(ContractError, match='outside_scope'):
            asyncio.run(provider.observe(order['job_ref'], FIELDS, outside,
                                         operation_key='outside-assigned-scope'))
        assert http.calls == []
        submitted = asyncio.run(operations.submit_once(order['job_ref'], operation_key='selected-submit'))
        assert submitted['outcome'] == 'completed'
        c8 = ProgressProvider(store, DurableExecutionStore(tmp_path / 'executions'),
                              run_id=RUN, job_provider=provider)
        snapshot = asyncio.run(c8.observe_async(order['job_ref'], FIELDS, original_scope,
                                               operation_key='selected-original-job-status'))
        assert snapshot['execution_status']['handle'] == order['job_ref']
        assert snapshot['execution_status']['native_state'] == 'PENDING'
        assert store.problem()['subject_refs'] == targets
        with Store(store.path) as reopened:
            reconstructed_tools = ToolRegistry(reopened, clients=client)
            reconstructed_operations = ProviderJobOperations(reopened,
                reconstructed_tools.remote_searches, registry=registry)
            reconstructed_ports = PublicSearchPorts(registry, reconstructed_operations,
                PublicSearchResultPublisher(reopened, reconstructed_tools,
                                            operations=reconstructed_operations))
            reconstructed = HmmerProgressProvider(reopened, run_id=RUN, ports=reconstructed_ports)
            assert reconstructed.scope(order['job_ref']) == original_scope
        assert len([row for row in http.calls if row[0] == 'GET']) == 1
