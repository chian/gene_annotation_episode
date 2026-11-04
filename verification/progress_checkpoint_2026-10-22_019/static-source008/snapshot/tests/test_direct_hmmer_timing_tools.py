"""Actual local provider/ledger/importer fixtures; no public/model/native calls."""
import asyncio
from copy import deepcopy
from dataclasses import FrozenInstanceError
import hashlib
import json
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.api_execution_planning import ApiExecutionPlanner
from gene_annotation_episode.api_reported_statistics import ApiReportedStatistics
from gene_annotation_episode.api_timing_information import ApiReportedTimingFactReader, PROVIDER
from gene_annotation_episode.api_timing_records import ApiTimingBinding, ApiTimingLedger
from gene_annotation_episode.direct_hmmer_timing import (
    DIRECT_BINDING_VERSION, DIRECT_MODE, KEY_VERSION, DirectHmmerAcquisition,
    DirectHmmerTiming, direct_operation_key)
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.hmmer_request_preparation import prepare_hmmer_request
from gene_annotation_episode.public_search_operations import ProviderOperationInProgress
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.resource_service_setup import bind_public_search_ports
from gene_annotation_episode.run_statistics import RunHistory
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_api_timing_custody import TimingClient, rows, shared_rows
from test_hmmer_api_operations import JOB, registry, snapshot


class Client(TimingClient):
    def __init__(self, states=('SUCCESS',)):
        super().__init__()
        self.states = list(states)

    def hmmer_status(self, job_id):
        self.calls.append(('status', job_id))
        state = self.states.pop(0) if len(self.states) > 1 else self.states[0]
        return snapshot({'id': job_id, 'task': {'status': state},
            'database': {'id': 'swissprot', 'version': 'fixture-original-release'}, 'algo': 'phmmer'})


def build(path, *, client=None, interval=0, history=True, bind=True, two_subjects=False):
    store = Store(path/'workspace')
    if two_subjects:
        fasta = path/'two.faa'
        fasta.write_text('>query\nMACDEFGH\n>other\nMMKKSSAA\n')
        problem = store.create_problem(fasta, molecule='protein', format='fasta')
    else:
        problem = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
    client = client or Client()
    tools = ToolRegistry(store, clients=client, provider_poll_interval_seconds=interval)
    owner = registry(client)
    binding = ApiTimingBinding(ledger_path=path/'timing.sqlite', history_path=path/'history.sqlite',
        resource_id=owner['resource_id'], monitoring_information_unit=.25)
    if history:
        RunHistory(binding.history_path).close()
    statistics = ApiReportedStatistics(binding, registry=owner)
    timing = ApiTimingLedger(store=store, run_id='direct_fixture', registry=owner,
        binding=binding, statistics=statistics)
    ports = bind_public_search_ports(store, tools, registry=owner, timing=timing)
    planner = ApiExecutionPlanner(store, run_id='direct_fixture', ports=ports, timing=timing,
        resource_estimator=ResourceToolEstimator.with_reported_results())
    reader = ApiReportedTimingFactReader(timing, ports=ports)
    direct = DirectHmmerTiming(planner, reader=reader)
    if bind:
        tools.bind_api_execution_planner(planner)
        tools.bind_api_direct_hmmer_timing(direct)
    arguments = {'subject_ref': problem['subject_refs'][0], 'algorithm': 'phmmer',
        'database': 'swissprot', 'page_size': 2}
    scope = store.validate_scope({'subject_refs': problem['subject_refs']})
    return SimpleNamespace(store=store, client=client, tools=tools, binding=binding,
        statistics=statistics, timing=timing, ports=ports, planner=planner, reader=reader,
        direct=direct, arguments=arguments, scope=scope)


@pytest.fixture
def host(tmp_path):
    h = build(tmp_path)
    try:
        yield h
    finally:
        h.store.close()


def order(h, parent='selected-search'):
    prepared = prepare_hmmer_request(h.arguments, sequence_symbols=h.ports.sequence_symbols, scope=h.scope)
    from gene_annotation_episode.communication import plain
    return h.ports.operations.order(operation_key=parent, provider='hmmer',
        query_fasta=prepared.query_fasta, scope=h.scope, **plain(prepared.normalized_arguments))


def key(h, job, parent, operation, ordinal=0, page=None, page_size=None):
    return direct_operation_key(registry_ref=h.ports.registry['registry_ref'], job_ref=job,
        parent_operation_key=parent, operation=operation, ordinal=ordinal, page=page, page_size=page_size)


def search(h, parent='selected-search'):
    return h.tools.execute('public.hmmer.search', h.arguments, scope=h.scope, operation_key=parent)


def test_exact_keys_use_complete_digest_and_original_outer_identity(host):
    h = host
    made = order(h)
    job = made['job_ref']
    digest = hashlib.sha256(canonical({'version': KEY_VERSION,
        'registry_ref': h.ports.registry['registry_ref'], 'job_ref': job,
        'parent_operation_key': 'selected-search'}).encode()).hexdigest()
    assert key(h, job, 'selected-search', 'submit') == f'ordinary-hmmer-v1:{digest}:submit:0:-:-'
    assert key(h, job, 'selected-search', 'status', 31).endswith(':status:31:-:-')
    assert key(h, job, 'selected-search', 'result', page=1, page_size=2).endswith(':result:0:1:2')
    assert key(h, job, 'selected-search', 'recover_submission').endswith(':recover_submission:0:-:-')
    assert h.ports.operations.inspect(job)['order']['order_operation_key'] == 'selected-search'
    assert h.client.calls == []


@pytest.mark.parametrize('change', [
    {'registry_ref': ''}, {'job_ref': ' spaced'}, {'parent_operation_key': 'bad\nkey'},
    {'operation': []}, {'operation': 'retry'}, {'ordinal': True}, {'ordinal': -1},
    {'operation': 'submit', 'ordinal': 1}, {'operation': 'submit', 'page': 1},
    {'operation': 'status', 'page_size': 3}, {'operation': 'result'},
    {'operation': 'result', 'page': True, 'page_size': 2},
    {'operation': 'result', 'page': 2, 'page_size': 2},
    {'operation': 'result', 'page': 1, 'page_size': False},
])
def test_invalid_keys_fail_before_storage(change):
    arguments = dict(registry_ref='registry', job_ref='job', parent_operation_key='own',
        operation='status', ordinal=0, page=None, page_size=None)
    with pytest.raises(ContractError, match='direct_hmmer_protocol_arguments_invalid'):
        direct_operation_key(**{**arguments, **change})


def test_binding_is_actual_equal_handle_and_catalog_opt_in(host):
    h = host
    saved = h.direct.as_record()
    assert set(saved) == {'version','configuration','planner','reader','poll_interval_seconds','implementation_sha256'}
    assert saved['version'] == DIRECT_BINDING_VERSION and saved['configuration'] == DIRECT_MODE
    assert saved['poll_interval_seconds'] == 0 and type(saved['poll_interval_seconds']) is int
    assert h.tools.resource_binding().get('ordinary_hmmer_timing') is None
    replacement = DirectHmmerTiming(h.planner, reader=h.reader)
    assert h.tools.bind_api_direct_hmmer_timing(replacement) is replacement
    assert h.tools.api_direct_hmmer_timing is replacement
    for name in DIRECT_MODE['tools']:
        assert h.tools.catalog()[name]['configuration'] == {'ordinary_hmmer_timing': saved}
    assert 'ordinary_hmmer_timing' not in h.tools.catalog()['public.hmmer.page'].get('configuration', {})
    with pytest.raises(TypeError, match='typed_direct_hmmer_timing_binding_required'):
        h.tools.bind_api_direct_hmmer_timing(object())
    with pytest.raises(TypeError, match='typed_direct_hmmer_timing_owners_required'):
        DirectHmmerTiming(object(), reader=h.reader)
    assert h.client.calls == []


@pytest.mark.parametrize('interval', [True, float('nan'), float('inf')])
def test_binding_rejects_nonfinite_bool_existing_protocol_interval(host, interval):
    host.tools.remote_searches.poll_interval_seconds = interval
    with pytest.raises(ContractError, match='api_direct_hmmer_timing_identity_conflict'):
        DirectHmmerTiming(host.planner, reader=host.reader)
    assert host.client.calls == []


def test_actual_search_keeps_ordinary_payload_and_result_replay_exact(tmp_path):
    direct, legacy = build(tmp_path/'direct'), build(tmp_path/'legacy', bind=False)
    try:
        result = search(direct)
        original = search(legacy)
        assert result['status'] == original['status'] == 'completed', result
        assert result['result'] == original['result'] and result['record_refs'] == original['record_refs']
        assert result['operation_ref'] == original['operation_ref']
        assert not ({'api_timing_disposition','api_timing_refs','provider_operation_refs'} & original.keys())
        assert result['api_timing_disposition']['state'] == 'available' and len(result['api_timing_refs']) == 1
        assert result['api_timing_refs'][0] not in result['record_refs']
        assert len(result['provider_operation_refs']) == 3
        assert [call[0] for call in direct.client.calls] == ['submit','status','result']
        before = canonical(result), list(direct.client.calls)
        direct.direct.acquire = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('outer replay called acquisition'))
        assert canonical(search(direct)) == before[0] and direct.client.calls == before[1]
        assert len(rows(direct.timing,'api_timing_measurements')) == len(shared_rows(direct.timing)) == 1
    finally:
        direct.store.close(); legacy.store.close()


def test_multiple_pending_reads_use_new_exact_ordinals_and_configured_sleep(tmp_path, monkeypatch):
    h = build(tmp_path, client=Client(('PENDING','STARTED','RETRY','SUCCESS')), interval=.125)
    sleeps = []
    async def slept(interval):
        sleeps.append(interval)
    monkeypatch.setattr('gene_annotation_episode.direct_hmmer_timing.asyncio.sleep', slept)
    try:
        result = search(h)
        assert result['status'] == 'completed', result
        assert sleeps == [.125, .125, .125]
        operations = [h.ports.operations.read_operation(ref) for ref in result['provider_operation_refs']]
        assert [row['operation_key'].split(':')[-3] for row in operations if row['operation']=='status'] == ['0','1','2','3']
        assert len(h.client.calls) == 6 and len([c for c in h.client.calls if c[0]=='submit']) == 1
    finally:
        h.store.close()


def test_cancel_at_pending_sleep_resumes_without_historical_sleep_or_post(tmp_path, monkeypatch):
    h = build(tmp_path, client=Client(('PENDING','SUCCESS')), interval=.75)
    sleeps = []
    async def cut(interval):
        sleeps.append(interval)
        raise asyncio.CancelledError
    monkeypatch.setattr('gene_annotation_episode.direct_hmmer_timing.asyncio.sleep', cut)
    try:
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(h.tools.execute_async('public.hmmer.search',h.arguments,scope=h.scope,operation_key='selected-search'))
        assert h.store.db.execute('SELECT count(*) FROM tool_operations').fetchone()[0] == 0
        assert [c[0] for c in h.client.calls] == ['submit','status']
        result = search(h)
        assert result['status']=='completed' and sleeps == [.75], result
        assert [c[0] for c in h.client.calls] == ['submit','status','status','result']
        assert h.tools._direct_hmmer_acquisitions.get() is None
    finally:
        h.store.close()


@pytest.mark.parametrize('terminal', ['FAILURE','REVOKED'])
def test_completed_terminal_status_is_failed_science_and_prefix_stays_failed(host, terminal):
    h = host
    h.client.states = [terminal]
    failed = search(h)
    assert failed['status']=='failed' and failed['feedback']['code']=='remote_search_failed'
    assert failed['feedback']['phase']=='status_response'
    assert len(failed['provider_operation_refs'])==2 and failed['api_timing_refs']==[]
    assert not h.store.count('observation') and len(shared_rows(h.timing))==0
    job = failed['feedback']['job_ref']
    h.client.states = ['SUCCESS']
    later = h.tools.execute('public.hmmer.collect',{'job_ref':job},scope=h.scope,operation_key='new-collect')
    assert later['status']=='completed', later
    calls = list(h.client.calls)
    replay = asyncio.run(h.direct.acquire('public.hmmer.search',h.arguments,scope=h.scope,operation_key='selected-search'))
    assert replay.failure.code=='remote_search_failed' and h.client.calls==calls
    assert search(h)==failed


def test_cached_collect_reuses_first_fact_and_page_stays_selected_fresh_get(host):
    h = host
    original = search(h)
    assert original['status']=='completed', original
    witness = canonical(rows(h.timing,'api_timing_measurements')[0])
    job = original['result']['job_ref']; calls=list(h.client.calls)
    collected=h.tools.execute('public.hmmer.collect',{'job_ref':job},scope=h.scope,operation_key='collect')
    assert collected['status']=='completed' and h.client.calls==calls
    assert collected['api_timing_refs']==original['api_timing_refs']
    assert len(collected['provider_operation_refs'])==1
    page=h.tools.execute('public.hmmer.page',{'job_ref':job,'page':2},scope=h.scope,operation_key='page')
    assert page['status']=='completed' and len(h.client.calls)==len(calls)+1
    assert not ({'api_timing_refs','api_timing_disposition','provider_operation_refs'} & page.keys())
    assert canonical(rows(h.timing,'api_timing_measurements')[0])==witness
    assert len(shared_rows(h.timing))==1


@pytest.mark.parametrize('whole', [False,True])
def test_timing_survives_partial_or_wholly_failed_scientific_publication(host, monkeypatch, whole):
    h=host
    def broken(*args,**kwargs):
        raise RuntimeError('synthetic scientific publication cut')
    monkeypatch.setattr(h.tools,'_perform' if whole else '_observation',broken)
    result=search(h)
    assert result['status']==('failed' if whole else 'partial'), result
    assert len(result['api_timing_refs'])==1 and result['api_timing_disposition']['state']=='available'
    assert h.store.get(result['api_timing_refs'][0])['provider']==PROVIDER
    assert result['api_timing_refs'][0] not in result['record_refs']
    assert bool(result['record_refs']) is (not whole)
    assert len(shared_rows(h.timing))==1 and not h.store.count('observation')
    assert h.tools._direct_hmmer_acquisitions.get() is None


def test_publication_failure_is_recoverable_on_new_cached_collect_without_backfill(host, monkeypatch):
    h=host
    real=h.reader.publish
    monkeypatch.setattr(h.reader,'publish',lambda *_: (_ for _ in ()).throw(OSError('publication unavailable')))
    original=search(h)
    assert original['status']=='completed' and original['api_timing_refs']==[]
    assert original['api_timing_disposition']['code']=='timing_source_publication_unavailable'
    assert len(shared_rows(h.timing))==1
    before=canonical(original);calls=list(h.client.calls)
    monkeypatch.setattr(h.reader,'publish',real)
    later=h.tools.execute('public.hmmer.collect',{'job_ref':original['result']['job_ref']},scope=h.scope,operation_key='new-collect')
    assert later['status']=='completed' and len(later['api_timing_refs'])==1 and h.client.calls==calls
    assert canonical(search(h))==before and len(shared_rows(h.timing))==1


@pytest.mark.parametrize('elapsed,code', [(None,'reported_duration_missing'),(-1,'reported_duration_invalid'),('bad','reported_duration_invalid')])
def test_missing_invalid_duration_never_replaces_valid_science(host, elapsed, code):
    h=host
    if elapsed is None:
        h.client.omit_elapsed=True
    else:
        h.client.seconds=elapsed
    result=search(h)
    assert result['status']=='completed' and result['api_timing_refs']==[], result
    assert result['api_timing_disposition']['code']==code and len(shared_rows(h.timing))==0
    assert h.store.count('observation')==1


def test_local_fact_is_usable_when_original_history_missing(tmp_path):
    h=build(tmp_path,history=False)
    try:
        result=search(h)
        assert result['status']=='completed' and len(result['api_timing_refs'])==1, result
        assert result['api_timing_disposition']['state']=='unavailable'
        start=h.reader.read_source(result['api_timing_refs'][0],scope=h.scope)['witness']['start_context']
        assert start['condition_capture']=='unavailable_before_submission' and start['condition_ref'] is None
        assert not h.binding.history_path.exists()
    finally:
        h.store.close()


def test_narrow_receiving_scope_withholds_all_timing_identities(tmp_path):
    h=build(tmp_path,two_subjects=True)
    try:
        original=search(h)
        assert original['status']=='completed', original
        narrow=h.store.validate_scope({'subject_refs':[h.arguments['subject_ref']]})
        result=h.tools.execute('public.hmmer.collect',{'job_ref':original['result']['job_ref']},
            scope=narrow,operation_key='narrow-collect')
        assert result['status']=='completed' and result['api_timing_refs']==[], result
        assert result['api_timing_disposition']=={
            'version':'api_timing_disposition_v1','state':'unavailable','code':'timing_binding_unavailable',
            **{field:None for field in ['order_binding_ref','intent_ref','submission_binding_ref','measurement_ref','source_ref']}}
        assert h.reader.read_source(original['api_timing_refs'][0],scope=h.scope)
    finally:
        h.store.close()


@pytest.mark.parametrize('mode',['gap','malformed','after-terminal','collect-submit'])
def test_malformed_own_protocol_prefix_fails_before_more_http(host,mode):
    h=host;parent='selected-search';job=order(h,parent)['job_ref'];ops=h.ports.operations
    async def prepare():
        await ops.submit_once(job,operation_key=key(h,job,parent,'submit'))
        if mode=='gap':
            await ops.status_once(job,operation_key=key(h,job,parent,'status',1))
        elif mode=='malformed':
            await ops.status_once(job,operation_key=key(h,job,parent,'status')+'-tampered')
        elif mode=='after-terminal':
            await ops.status_once(job,operation_key=key(h,job,parent,'status'))
            await ops.status_once(job,operation_key=key(h,job,parent,'status',1))
    asyncio.run(prepare());calls=list(h.client.calls)
    tool='public.hmmer.collect' if mode=='collect-submit' else 'public.hmmer.search'
    args={'job_ref':job} if mode=='collect-submit' else h.arguments
    with pytest.raises(ContractError,match='direct_hmmer_protocol_identity_conflict'):
        asyncio.run(h.direct.acquire(tool,args,scope=h.scope,operation_key=parent))
    assert h.client.calls==calls


def test_in_progress_is_explicit_failed_tool_and_original_claim_continues(host,monkeypatch):
    h=host
    async def busy(job_ref,*,operation_key,retry_of):
        raise ProviderOperationInProgress(job_ref,operation_key)
    monkeypatch.setattr(h.ports.operations,'submit_once',busy)
    result=search(h)
    assert result['status']=='failed' and result['feedback']['code']=='submission_in_progress', result
    assert result['feedback']['phase']=='provider_operation' and result['feedback']['operation_key'].endswith(':submit:0:-:-')
    assert result['provider_operation_refs']==[] and result['api_timing_refs']==[]
    assert h.client.calls==[] and not h.store.count('observation')


def test_carrier_is_frozen_and_exactly_one_science_outcome(host):
    acquired=asyncio.run(host.direct.acquire('public.hmmer.search',host.arguments,scope=host.scope,operation_key='raw-acquisition'))
    assert isinstance(acquired,DirectHmmerAcquisition) and acquired.snapshot is not None and acquired.failure is None
    with pytest.raises(FrozenInstanceError):
        acquired.snapshot=None
    with pytest.raises(TypeError,match='typed_direct_hmmer_acquisition_required'):
        DirectHmmerAcquisition(None,None,{},(),())
    assert host.store.count('observation')==0


def test_legacy_collect_is_never_registered_or_given_timing_fields(host):
    h=host
    h.tools.api_direct_hmmer_timing=None
    legacy=search(h,'legacy')
    assert legacy['status']=='completed'
    h.tools.bind_api_direct_hmmer_timing(h.direct)
    result=h.tools.execute('public.hmmer.collect',{'job_ref':legacy['result']['job_ref']},scope=h.scope,operation_key='legacy-collect')
    assert result['status']=='completed' and 'api_timing_refs' not in result
    assert h.store.db.execute('SELECT count(*) FROM public_search_orders').fetchone()[0]==0
    assert rows(h.timing,'api_timing_measurements')==[] and shared_rows(h.timing)==[]


@pytest.mark.parametrize('state,code', [('conflict','public_search_registration_incomplete'),('conflict','identity_conflict'),('unavailable','public_search_storage_unavailable')])
def test_nonlegacy_membership_never_falls_back(host,monkeypatch,state,code):
    h=host
    made=order(h)
    monkeypatch.setattr(h.ports.operations,'classify_order',lambda job:{'version':'public_search_order_membership_v1',
        'job_ref':job,'registry_ref':h.ports.registry['registry_ref'],'state':state,'code':code})
    result=h.tools.execute('public.hmmer.collect',{'job_ref':made['job_ref']},scope=h.scope,operation_key='collect')
    assert result['status']=='failed' and result['feedback']['code']==code and result['feedback']['phase']=='local_preflight'
    assert 'api_timing_refs' not in result and h.client.calls==[]


def test_raw_helper_invalid_preparation_is_named_contract_error(host):
    with pytest.raises(ContractError,match='direct_hmmer_protocol_arguments_invalid'):
        asyncio.run(host.direct.acquire('public.hmmer.search',
            {**host.arguments,'page_size':False},scope=host.scope,operation_key='invalid-raw'))
    assert host.client.calls==[]
    assert host.store.db.execute('SELECT count(*) FROM public_search_orders').fetchone()[0]==0


@pytest.mark.parametrize('orphan',[False,True])
def test_bound_collect_missing_job_uses_actual_membership_without_legacy(host,orphan):
    h=host
    job=order(h)['job_ref'] if orphan else 'provider_job_'+'0'*24
    if orphan:
        with h.store.transaction():
            h.store.db.execute('DELETE FROM provider_jobs WHERE id=?',(job,))
    result=h.tools.execute('public.hmmer.collect',{'job_ref':job},scope=h.scope,operation_key='missing-collect')
    assert result['feedback']['code']==('public_search_registration_incomplete' if orphan else 'unknown_job'),result
    assert result['status']==('failed' if orphan else 'invalid')
    if orphan:
        assert result['feedback']['phase']=='local_preflight'
    assert h.client.calls==[] and 'api_timing_refs' not in result


def test_retained_pending_status_capsule_is_imported_without_replayed_sleep(host,monkeypatch):
    h=host;h.client.states=['PENDING','SUCCESS']
    operations=h.ports.operations;original=operations._dispatch
    async def captured_then_cancelled(*args,**kwargs):
        result=await original(*args,**kwargs)
        if args[1]=='status':
            raise asyncio.CancelledError
        return result
    async def no_historical_sleep(_interval):
        raise AssertionError('retained pending status capsule was slept again')
    monkeypatch.setattr(operations,'_dispatch',captured_then_cancelled)
    monkeypatch.setattr('gene_annotation_episode.direct_hmmer_timing.asyncio.sleep',no_historical_sleep)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(h.tools.execute_async('public.hmmer.search',h.arguments,scope=h.scope,operation_key='selected-search'))
    assert [c[0] for c in h.client.calls]==['submit','status']
    job=h.store.db.execute('SELECT job_ref FROM public_search_orders').fetchone()[0]
    status_key=key(h,job,'selected-search','status')
    assert operations._capsule_path(status_key).is_dir()
    assert len(operations.inspect(job)['latest_operation_refs'])==1
    monkeypatch.setattr(operations,'_dispatch',original)
    result=search(h)
    assert result['status']=='completed' and len(result['api_timing_refs'])==1,result
    assert [c[0] for c in h.client.calls]==['submit','status','status','result']
    assert len(rows(h.timing,'api_timing_submission_intents'))==1
