"""Bounded selected-operation engineering checks; no public service/model calls."""
import asyncio
from dataclasses import replace
import hashlib
import json
import multiprocessing
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, SourceSnapshot
from gene_annotation_episode.domain import ContractError, canonical, identity
from gene_annotation_episode.provider_jobs import RemoteSearches, build_search_request, provider_job_reference
from gene_annotation_episode.public_search_operations import (
    ProviderJobOperations, ProviderOperationInProgress, PublicSearchPorts,
    describe_hmmer_client_binding, hmmer_client_binding_sha256)
from gene_annotation_episode.state import Store

JOB = '81bddc6e-f6ef-4f16-a8c1-32d262016ccb'


def snapshot(body):
    return SourceSnapshot('fixture_hmmer', 'http://fixture.invalid/result/'+JOB, {},
        '2026-10-22T00:00:00+00:00', json.dumps(body).encode(), 'application/json',
        {'representation': 'synthetic_protocol_fixture', 'status': 200})


def result_body(page=1):
    return {'status':'SUCCESS','page_count':2,'result':{'stats':{'id':JOB,'algo':'phmmer','database':'swissprot'},
        'hits':[{'index':page-1,'acc':f'P0000{page}','score':20.,'evalue':.001,'domains':[]}]}}


class FixtureClient:
    hmmer_fixture_binding = dict(transport_timeout_seconds=20,
        submit_url_prefix='http://fixture.invalid/search/', status_url_prefix='http://fixture.invalid/search/',
        result_url_prefix='http://fixture.invalid/result/')
    def __init__(self):
        self.calls=[]
        self.state='PENDING'
        self.entered=threading.Event()
        self.release=threading.Event(); self.release.set()
        self.submit_error=None
        self.status_entered=threading.Event()
        self.status_release=threading.Event(); self.status_release.set()
        self.status_body=None
    def hmmer_submit(self, query_fasta, **kwargs):
        self.calls.append(('submit',query_fasta,kwargs)); self.entered.set(); self.release.wait(10)
        if self.submit_error:
            raise self.submit_error
        return snapshot({'id':JOB})
    def hmmer_status(self, job_id):
        self.calls.append(('status',job_id)); state=self.state
        self.status_entered.set(); self.status_release.wait(10)
        return snapshot(self.status_body if self.status_body is not None else {'id':JOB,'task':{'status':state}})
    def hmmer_result(self, job_id, **kwargs):
        self.calls.append(('result',job_id,kwargs)); return snapshot(result_body(kwargs['page']))


class LocalHTTPClient(PublicClients):
    def __init__(self, address):
        super().__init__(timeout=20)
        self.address=address
        self.hmmer_fixture_binding=dict(transport_timeout_seconds=self.timeout,
            submit_url_prefix=address+'/search/',status_url_prefix=address+'/search/',result_url_prefix=address+'/result/')
    def hmmer_submit(self, query_fasta, *, algorithm, database, parameters=None):
        return self._http('fixture_hmmer',self.address+'/search/'+algorithm,{},'application/json',
                          json_body=dict(input=query_fasta,database=database,**(parameters or {})))
    def hmmer_status(self, job_id):
        return self._http('fixture_hmmer',self.address+'/search/'+job_id,{},'application/json')
    def hmmer_result(self, job_id, **kwargs):
        return self._http('fixture_hmmer',self.address+'/result/'+job_id,kwargs,'application/json')


def registry(client):
    return dict(version='public_search_registry_v1',registry_ref='execution_registry_fixture',
        resource_id='fixture_hmmer_resource',provider='hmmer',client_binding_sha256=hmmer_client_binding_sha256(client))


def setup(path, client=None):
    store=Store(path); problem=store.create_problem(raw_sequence='MACDEFGH',molecule='protein')
    client=client or FixtureClient()
    operations=ProviderJobOperations(store, RemoteSearches(store,client),registry=registry(client))
    subject=problem['subject_refs'][0]
    order=operations.order(operation_key='order',provider='hmmer',subject_ref=subject,
        query_fasta=f'>{subject}\nMACDEFGH',algorithm='phmmer',database='swissprot',parameters={},page_size=2,scope={'subject_refs':problem['subject_refs']})
    return store,client,operations,order


def test_order_exact_preimages_and_read_ports_detach(tmp_path):
    store,client,ops,order=setup(tmp_path)
    with store:
        info=ops.inspect(order['job_ref']); assert info['state']=='not_submitted'
        assert info['remote_id'] is None and info['latest_operation_refs']==info['submission_claim_refs']==[]
        assert client.calls==[]
        assert store.get_artifact(order['request_ref'])==canonical(info['request']).encode()
        assert hashlib.sha256(store.get_artifact(order['query_fasta_ref'])).hexdigest()==info['request']['query_sha256']
        assert provider_job_reference('order',info['request'])==order['job_ref']
        info['order']['registry_ref']='changed'; info['request']['database']='changed'
        assert ops.inspect(order['job_ref'])['order']==order
        assert ops.inspect(order['job_ref'])['request']['database']=='swissprot'
        with pytest.raises(ContractError,match='unknown_job'): ops.inspect('absent')
        with pytest.raises(ContractError,match='unsupported_provider'):
            ops.order(operation_key='bad',provider='blast',subject_ref='x',query_fasta='>x\nMAC',algorithm='blastp',database='nr',scope={'subject_refs':store.problem()['subject_refs']})
        assert store.db.execute('SELECT count(*) FROM provider_jobs').fetchone()[0]==1


@pytest.mark.parametrize('provider,algorithm,database,expected',[
 ('hmmer','phmmer','swissprot',{'identity_version':'hmmer_single_fasta_sequence_v2','query_length':8,'page_size':50}),
 ('blast','blastp','nr',{'provider':'blast','query_length':8,'molecule_model':'protein','molecule_assignment':'not_performed'}),
 ('rfam','cmscan','Rfam',{'provider':'rfam','molecule_model':'rna','molecule_assignment':'not_performed',
                         'search_parameters':'provider_defaults_not_exposed','database_release':None,'model_release':None})])
def test_extracted_normalizer_preserves_original_bytes_and_ids(provider,algorithm,database,expected):
    fasta='>original header\nMACDEFGH\n'
    request, sequences=build_search_request(subject_ref='subject',query_fasta=fasta,algorithm=algorithm,database=database,provider=provider)
    base=dict(subject_ref='subject',query_sha256=hashlib.sha256(fasta.encode()).hexdigest(),algorithm=algorithm,database=database,parameters={})
    base.update(expected,sequence_sha256=hashlib.sha256(b'MACDEFGH').hexdigest())
    if provider=='hmmer':
        base.update(query_sha256_representation='submitted_fasta_utf8_bytes',sequence_sha256_representation='single_fasta_sequence_uppercase_whitespace_removed_ascii')
    assert canonical(request)==canonical(base)
    assert provider_job_reference('key',request)==identity('provider_job',{'operation_key':'key','request':base})
    assert sequences[0].sequence=='MACDEFGH'


def test_binding_requires_actual_client_and_registry_digest(tmp_path):
    client=FixtureClient(); binding=describe_hmmer_client_binding(client)
    assert set(binding)=={'version','provider','transport_timeout_seconds','implementation_sha256','submit_url_prefix','status_url_prefix','result_url_prefix'}
    with Store(tmp_path) as store:
        bad=registry(client);bad['client_binding_sha256']='0'*64
        with pytest.raises(ContractError,match='identity_conflict'):
            ProviderJobOperations(store,RemoteSearches(store,client),registry=bad)
    with pytest.raises(ContractError,match='unavailable_binding'): describe_hmmer_client_binding(object())


def test_one_submit_status_pending_no_result_fetch_and_replay(tmp_path):
    async def run():
        store,client,ops,order=setup(tmp_path)
        with store:
            job=order['job_ref']; submitted=await ops.submit_once(job,operation_key='submit')
            assert submitted['state']=='accepted' and submitted['remote_id']==JOB
            assert await ops.submit_once(job,operation_key='submit')==submitted
            assert (await ops.submit_once(job,operation_key='another_submit'))['remote_id']==JOB
            progress=await ops.status_once(job,operation_key='status')
            assert progress['state']=='PENDING' and progress['result_ready'] is False
            failed=await ops.result_once(job,operation_key='result',page=1,page_size=2)
            assert failed['failure']['code']=='result_not_ready'
            assert [c[0] for c in client.calls]==['submit','status']
            client.state='SUCCESS'
            assert await ops.status_once(job,operation_key='status')==progress
            assert await ops.result_once(job,operation_key='result',page=1,page_size=2)==failed
            assert [c[0] for c in client.calls]==['submit','status']
            with pytest.raises(ContractError,match='operation_conflict'):
                await ops.result_once(job,operation_key='result',page=2,page_size=2)
    asyncio.run(run())


def test_same_and_different_key_busy_submission_no_competing_post(tmp_path):
    async def run():
        store,client,ops,order=setup(tmp_path); client.release.clear()
        with store:
            task=asyncio.create_task(ops.submit_once(order['job_ref'],operation_key='submit'))
            assert await asyncio.to_thread(client.entered.wait,3)
            with pytest.raises(ProviderOperationInProgress): await ops.submit_once(order['job_ref'],operation_key='submit')
            other=await ops.submit_once(order['job_ref'],operation_key='other')
            assert other['failure']['code']=='submission_in_progress'
            assert len(ops.inspect(order['job_ref'])['latest_operation_refs'])==1
            client.release.set(); original=await task
            assert original['outcome']=='completed' and len([c for c in client.calls if c[0]=='submit'])==1
    asyncio.run(run())


def test_cancellation_during_http_retains_capsule_and_recovers_original_uuid(tmp_path):
    async def run():
        store,client,ops,order=setup(tmp_path);client.release.clear()
        with store:
            job=order['job_ref'];task=asyncio.create_task(ops.submit_once(job,operation_key='submit'))
            assert await asyncio.to_thread(client.entered.wait,3)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):await task
            assert ops.inspect(job)['state']=='submitting'
            client.release.set()
            # Await the executor's actual completion, not a timing assumption.
            await asyncio.get_running_loop().shutdown_default_executor()
            assert ops._capsule_path('submit').is_dir()
            recovered=ops.recover_submission(job,operation_key='recover')
            assert recovered['remote_id']==JOB and recovered['outcome']=='completed'
            original=await ops.submit_once(job,operation_key='submit')
            assert original['snapshot_ref'] and len(client.calls)==1
            assert ops.read_snapshot(original['receipt_ref']).content==snapshot({'id':JOB}).content
    asyncio.run(run())


def test_not_sent_requires_explicit_current_predecessor_and_uncertainty_never_retries(tmp_path):
    async def run():
        store,client,ops,order=setup(tmp_path)
        with store:
            job=order['job_ref']; client.submit_error=AcquisitionError('unsupported_hmmer_search_parameter',submission_outcome='not_sent')
            first=await ops.submit_once(job,operation_key='first')
            assert first['failure']['submission_outcome']=='not_sent' and ops.inspect(job)['state']=='not_submitted'
            client.submit_error=None
            forbidden=await ops.submit_once(job,operation_key='forbidden')
            assert forbidden['failure']['code']=='retry_not_authorized' and len(client.calls)==1
            repaired=await ops.submit_once(job,operation_key='repair',retry_of=first['receipt_ref'])
            assert repaired['remote_id']==JOB and len(client.calls)==2
        store,client,ops,order=setup(tmp_path/'uncertain')
        with store:
            client.submit_error=TimeoutError('actual outcome unknown')
            first=await ops.submit_once(order['job_ref'],operation_key='first')
            assert first['failure']['code']=='submission_uncertain'
            second=await ops.submit_once(order['job_ref'],operation_key='second',retry_of=first['receipt_ref'])
            assert second['failure']['code']=='submission_uncertain' and len(client.calls)==1
    asyncio.run(run())


@pytest.mark.parametrize('body',[{}, {'task':{}}, {'task':{'status':'nonsense'}}, {'task':{'status':False}}])
def test_invalid_status_is_saved_failure_not_pending(body,tmp_path):
    async def run():
        store,client,ops,order=setup(tmp_path)
        with store:
            await ops.submit_once(order['job_ref'],operation_key='submit');client.status_body=body
            receipt=await ops.status_once(order['job_ref'],operation_key='status')
            assert receipt['outcome']=='failed' and receipt['failure']['code']=='response_invalid'
            assert ops.read_snapshot(receipt['receipt_ref']).content==snapshot(body).content
    asyncio.run(run())


@pytest.mark.parametrize('terminal',['FAILURE','REVOKED'])
def test_remote_failure_is_completed_status_observation(terminal,tmp_path):
    async def run():
        store,client,ops,order=setup(tmp_path)
        with store:
            await ops.submit_once(order['job_ref'],operation_key='submit');client.state=terminal
            receipt=await ops.status_once(order['job_ref'],operation_key='status')
            assert receipt['outcome']=='completed' and receipt['failure'] is None and receipt['state']==terminal
            failed=await ops.result_once(order['job_ref'],operation_key='result',page=1,page_size=2)
            assert failed['failure']['code']=='remote_job_failed'
    asyncio.run(run())


def test_late_pending_preserves_validated_result_and_old_receipts(tmp_path):
    async def run():
        store,client,ops,order=setup(tmp_path)
        with store:
            job=order['job_ref'];await ops.submit_once(job,operation_key='submit')
            client.state='SUCCESS';success=await ops.status_once(job,operation_key='success')
            client.state='PENDING';client.status_release.clear();client.status_entered.clear()
            pending=asyncio.create_task(ops.status_once(job,operation_key='late'))
            assert await asyncio.to_thread(client.status_entered.wait,3)
            result=await ops.result_once(job,operation_key='result',page=1,page_size=2)
            assert result['result_cached']
            client.status_release.set();late=await pending
            assert late['state']=='PENDING' and late['result_cached'] and late['result_ready'] is False
            assert ops.inspect(job)['state']=='returned'
            assert ops.read_operation(success['receipt_ref'])==success
            cached=await ops.result_once(job,operation_key='cached',page=1,page_size=2)
            assert cached['snapshot_ref']==result['snapshot_ref']
            assert len([c for c in client.calls if c[0]=='result'])==1
            snapshot_=ops.read_snapshot(result['receipt_ref'])
            assert snapshot_.request['page']==1 and snapshot_.request['page_size']==2
            assert snapshot_.transport['job_ref']==job
    asyncio.run(run())


def test_awaited_http_has_no_transaction_and_other_connection_can_commit(tmp_path):
    async def run():
        store,client,ops,order=setup(tmp_path);client.release.clear()
        with store:
            with store.transaction():
                with pytest.raises(ContractError,match='provider_http_in_transaction'):
                    await ops.submit_once(order['job_ref'],operation_key='forbidden')
            task=asyncio.create_task(ops.submit_once(order['job_ref'],operation_key='submit'))
            assert await asyncio.to_thread(client.entered.wait,3)
            assert not store.db.in_transaction
            with Store(tmp_path) as other:
                with other.transaction(): other.artifact(b'independent actual commit')
            client.release.set();assert (await task)['outcome']=='completed'
    asyncio.run(run())


def _process_submit(path,address,queue):
    with Store(path) as store:
        client=LocalHTTPClient(address);ops=ProviderJobOperations(store,RemoteSearches(store,client),registry=registry(client))
        job=store.db.execute('SELECT job_ref FROM public_search_orders').fetchone()[0]
        receipt=asyncio.run(ops.submit_once(job,operation_key='process-'+str(__import__('os').getpid())))
        queue.put(receipt)


def test_two_real_processes_one_actual_local_http_post(tmp_path):
    entered=threading.Event(); release=threading.Event();count=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            count.append(self.rfile.read(int(self.headers['Content-Length'])));entered.set();release.wait(10)
            raw=json.dumps({'id':JOB}).encode();self.send_response(200);self.end_headers();self.wfile.write(raw)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    address=f'http://127.0.0.1:{server.server_port}'
    store,_,_,_=setup(tmp_path,LocalHTTPClient(address));store.close()
    ctx=multiprocessing.get_context('spawn');queue=ctx.Queue();first=ctx.Process(target=_process_submit,args=(str(tmp_path),address,queue));second=ctx.Process(target=_process_submit,args=(str(tmp_path),address,queue))
    try:
        first.start();assert entered.wait(5);second.start()
        busy=queue.get(timeout=5);assert busy['failure']['code']=='submission_in_progress'
        release.set();accepted=queue.get(timeout=5);assert accepted['remote_id']==JOB
        first.join(5);second.join(5);assert first.exitcode==second.exitcode==0 and len(count)==1
    finally:
        release.set();server.shutdown();thread.join(5);server.server_close()


def test_recovery_wins_post_capture_import_race_without_duplicate_receipt(tmp_path):
    async def run():
        store,client,ops,order=setup(tmp_path)
        with store:
            original_dispatch=ops._dispatch
            recovered=[]
            async def dispatch(*args):
                result=await original_dispatch(*args)
                # The real worker has published its capsule and released the OS
                # lock. A second real Store imports before the original resumes.
                with Store(tmp_path) as other:
                    other_client=FixtureClient()
                    other_ops=ProviderJobOperations(other,RemoteSearches(other,other_client),registry=registry(other_client))
                    recovered.append(await other_ops.submit_once(order['job_ref'],operation_key='submit'))
                    assert other_client.calls==[]
                return result
            ops._dispatch=dispatch
            receipt=await ops.submit_once(order['job_ref'],operation_key='submit')
            assert receipt==recovered[0] and receipt['remote_id']==JOB
            assert len(ops.inspect(order['job_ref'])['latest_operation_refs'])==1
            assert len(client.calls)==1
    asyncio.run(run())


def test_missing_capture_after_process_loss_stays_uncertain_without_post(tmp_path):
    async def run():
        store,client,ops,order=setup(tmp_path)
        with store:
            # Fault injection at the already-committed claim boundary: dispatch
            # fails without an HTTP entity. No fabricated preflight outcome.
            async def crash(*args):
                __import__('os').close(args[-1])
                raise RuntimeError('synthetic process loss before capsule')
            ops._dispatch=crash
            receipt=await ops.submit_once(order['job_ref'],operation_key='submit')
            assert receipt['failure']['code']=='submission_uncertain' and client.calls==[]
            recovery=ops.recover_submission(order['job_ref'],operation_key='recover')
            assert recovery['failure']['code']=='submission_uncertain'
            later=await ops.submit_once(order['job_ref'],operation_key='later')
            assert later['failure']['code']=='submission_uncertain' and client.calls==[]
    asyncio.run(run())


def test_status_before_result_retains_each_original_snapshot(tmp_path):
    async def run():
        store,client,ops,order=setup(tmp_path)
        with store:
            job=order['job_ref']; await ops.submit_once(job,operation_key='submit')
            client.state='SUCCESS'; ready=await ops.status_once(job,operation_key='ready')
            page=await ops.result_once(job,operation_key='page',page=2,page_size=2)
            assert ready['result_cached'] is False and page['result_cached'] is True
            assert ops.read_operation(ready['receipt_ref'])==ready
            assert ops.read_snapshot(page['receipt_ref']).request['page']==2
            assert ops.inspect(job)['state']=='returned'
    asyncio.run(run())


def test_executor_rejection_is_explicit_not_sent_and_selected_retry_can_repair(tmp_path,monkeypatch):
    async def run():
        store,client,ops,order=setup(tmp_path)
        with store:
            loop=asyncio.get_running_loop()
            def reject(*args,**kwargs):raise RuntimeError('synthetic executor rejection before scheduling')
            with monkeypatch.context() as patch:
                patch.setattr(loop,'run_in_executor',reject)
                failed=await ops.submit_once(order['job_ref'],operation_key='rejected')
            assert failed['failure']['submission_outcome']=='not_sent' and client.calls==[]
            assert ops.inspect(order['job_ref'])['state']=='not_submitted'
            repaired=await ops.submit_once(order['job_ref'],operation_key='repair',retry_of=failed['receipt_ref'])
            assert repaired['remote_id']==JOB and len(client.calls)==1
    asyncio.run(run())


def test_conflicting_selected_operands_fail_before_original_http_finishes(tmp_path):
    async def run():
        store,client,ops,order=setup(tmp_path);client.release.clear()
        with store:
            task=asyncio.create_task(ops.submit_once(order['job_ref'],operation_key='selected'))
            assert await asyncio.to_thread(client.entered.wait,3)
            with pytest.raises(ContractError,match='operation_conflict'):
                await ops.status_once(order['job_ref'],operation_key='selected')
            with pytest.raises(ContractError,match='operation_conflict'):
                await ops.submit_once(order['job_ref'],operation_key='selected',retry_of='different')
            client.release.set();assert (await task)['remote_id']==JOB
            assert len(client.calls)==1
    asyncio.run(run())


def test_corrupted_response_capture_cannot_authorize_a_second_post(tmp_path):
    async def run():
        store,client,ops,order=setup(tmp_path)
        with store:
            original_dispatch=ops._dispatch
            async def cancel_after_capture(*args):
                await original_dispatch(*args)
                raise asyncio.CancelledError()
            ops._dispatch=cancel_after_capture
            with pytest.raises(asyncio.CancelledError):
                await ops.submit_once(order['job_ref'],operation_key='submit')
            (ops._capsule_path('submit')/'response.entity').write_bytes(b'corrupt retained bytes')
            recovered=ops.recover_submission(order['job_ref'],operation_key='recover')
            assert recovered['failure']['code']=='submission_uncertain'
            assert recovered['failure']['native_code']=='http_capture_invalid'
            later=await ops.submit_once(order['job_ref'],operation_key='later')
            assert later['failure']['code']=='submission_uncertain' and len(client.calls)==1
    asyncio.run(run())


def test_killed_request_process_keeps_claim_and_never_resubmits(tmp_path):
    entered=threading.Event();release=threading.Event();requests=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(self.rfile.read(int(self.headers['Content-Length'])))
            entered.set();release.wait(10)
            try:
                self.send_response(200);self.end_headers();self.wfile.write(json.dumps({'id':JOB}).encode())
            except (BrokenPipeError,ConnectionResetError):pass
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    address=f'http://127.0.0.1:{server.server_port}'
    store,_,_,order=setup(tmp_path,LocalHTTPClient(address));store.close()
    ctx=multiprocessing.get_context('spawn');queue=ctx.Queue()
    owner=ctx.Process(target=_process_submit,args=(str(tmp_path),address,queue))
    try:
        owner.start();assert entered.wait(5)
        owner.terminate();owner.join(5);assert owner.exitcode is not None
        with Store(tmp_path) as reopened:
            client=LocalHTTPClient(address)
            ops=ProviderJobOperations(reopened,RemoteSearches(reopened,client),registry=registry(client))
            before=ops.inspect(order['job_ref'])
            assert before['state']=='submitting' and len(before['submission_claim_refs'])==1
            recovery=ops.recover_submission(order['job_ref'],operation_key='recover_after_process_death')
            assert recovery['failure']['code']=='submission_uncertain' and recovery['remote_id'] is None
            repeat=asyncio.run(ops.submit_once(order['job_ref'],operation_key='explicit_later_submit'))
            assert repeat['failure']['code']=='submission_uncertain'
            assert len(requests)==1
    finally:
        release.set()
        if owner.is_alive():owner.terminate();owner.join(5)
        server.shutdown();thread.join(5);server.server_close();queue.close()


def test_no_claim_recovery_is_missing_prerequisite_and_preserves_first_submit(tmp_path):
    store,client,ops,order=setup(tmp_path)
    with store:
        job=order['job_ref']
        recovery=ops.recover_submission(job,operation_key='recover_without_claim')
        assert recovery['outcome']=='failed' and recovery['state']=='not_submitted'
        assert recovery['failure']==dict(code='prerequisite_missing',
            native_code='submission_claim_unavailable',phase='recovery',submission_outcome=None,
            prerequisite=None,retry_after_seconds=None,http_status=None,diagnostic_ref=None,
            response_snapshot_ref=None,affected_refs=[job],partial_record_refs=[])
        assert client.calls==[] and ops.inspect(job)['submission_claim_refs']==[]
        assert ops.inspect(job)['state']=='not_submitted'
    with Store(tmp_path) as reopened:
        later_client=FixtureClient()
        later_ops=ProviderJobOperations(reopened,RemoteSearches(reopened,later_client),registry=registry(later_client))
        assert later_ops.recover_submission(job,operation_key='recover_without_claim')==recovery
        submitted=asyncio.run(later_ops.submit_once(job,operation_key='first_selected_submit'))
        assert submitted['outcome']=='completed' and submitted['remote_id']==JOB
        assert len(later_client.calls)==1 and len(later_ops.inspect(job)['submission_claim_refs'])==1
        assert later_ops.recover_submission(job,operation_key='recover_without_claim')==recovery
        assert later_ops.inspect(job)['state']=='accepted'



@pytest.mark.parametrize('operation',['status','result'])
@pytest.mark.parametrize('submission',['none','not_sent','ambiguous'])
def test_status_result_without_handle_preserve_actual_submission_meaning(tmp_path,operation,submission):
    async def run():
        store,client,ops,order=setup(tmp_path)
        with store:
            job=order['job_ref'];original=None
            if submission=='not_sent':
                client.submit_error=AcquisitionError('unsupported_hmmer_search_parameter',submission_outcome='not_sent')
                original=await ops.submit_once(job,operation_key='submit')
                assert original['failure']['submission_outcome']=='not_sent'
            elif submission=='ambiguous':
                client.submit_error=TimeoutError('actual selected POST outcome unknown')
                original=await ops.submit_once(job,operation_key='submit')
                assert original['failure']['submission_outcome']=='unknown'
            before=list(client.calls);sources=store.count('source')
            async def selected():
                if operation=='status':return await ops.status_once(job,operation_key='observe')
                return await ops.result_once(job,operation_key='observe',page=1,page_size=2)
            receipt=await selected()
            assert receipt['outcome']=='failed' and receipt['remote_id'] is None
            assert client.calls==before and store.count('source')==sources
            assert receipt['snapshot_ref'] is None and receipt['result_ready'] is None
            if submission=='ambiguous':
                assert receipt['failure']['code']=='submission_uncertain'
                assert receipt['failure']['submission_outcome']=='unknown'
            else:
                assert receipt['failure']==dict(code='prerequisite_missing',
                    native_code='submission_claim_unavailable' if submission=='none' else 'submission_not_sent',
                    phase=operation,submission_outcome=None,prerequisite=None,retry_after_seconds=None,
                    http_status=None,diagnostic_ref=None,response_snapshot_ref=None,
                    affected_refs=[job],partial_record_refs=[])
                assert ops.inspect(job)['state']=='not_submitted'
            if original is not None:assert ops.read_operation(original['receipt_ref'])==original
            if submission!='ambiguous':
                client.submit_error=None
                repaired=await ops.submit_once(job,operation_key='explicit_submit',
                    retry_of=None if submission=='none' else original['receipt_ref'])
                assert repaired['remote_id']==JOB
                assert await selected()==receipt
    asyncio.run(run())


def test_original_scope_sidecar_is_detached_and_cannot_change_order_identity(tmp_path):
    store,client,ops,order=setup(tmp_path)
    with store:
        job=order['job_ref'];scope={'subject_refs':store.problem()['subject_refs']}
        saved=ops.open_scope(job)
        assert saved==dict(version='public_search_order_scope_v1',registry_ref=registry(client)['registry_ref'],
            job_ref=job,scope=store.validate_scope(scope),scope_sha256=hashlib.sha256(canonical(store.validate_scope(scope)).encode()).hexdigest())
        saved['scope']['subject_refs'].clear()
        assert ops.open_scope(job)['scope']==scope
        request=ops.inspect(job)['request']
        kwargs=dict(operation_key='order',provider='hmmer',subject_ref=request['subject_ref'],
            query_fasta=store.get_artifact(order['query_fasta_ref']).decode(),algorithm='phmmer',database='swissprot',parameters={},page_size=2)
        assert ops.order(**kwargs,scope=scope)==order
        assert set(order)=={'version','registry_ref','job_ref','order_operation_key','request_sha256','request_ref','query_fasta_ref'}
        assert provider_job_reference('order',request)==job and 'scope' not in request
        narrow=dict(subject_refs=scope['subject_refs'],segments=[dict(target_ref=scope['subject_refs'][0],start=0,end=4,unit='aa')])
        with pytest.raises(ContractError,match='identity_conflict'):ops.order(**kwargs,scope=narrow)
        assert ops.open_scope(job)['scope']==scope and client.calls==[]
        with pytest.raises(TypeError):ops.order(**kwargs)
        with pytest.raises(ContractError,match='invalid_scope'):ops.order(**kwargs,scope=None)


def test_missing_or_mutated_scope_proof_fails_without_http(tmp_path):
    store,client,ops,order=setup(tmp_path)
    with store:
        job=order['job_ref'];original=ops.open_scope(job)
        bad={**original,'scope_sha256':'0'*64}
        with store.transaction():store.db.execute('UPDATE public_search_order_scopes SET data=? WHERE job_ref=?',(canonical(bad),job))
        with pytest.raises(ContractError,match='identity_conflict'):ops.open_scope(job)
        with pytest.raises(ContractError,match='identity_conflict'):asyncio.run(ops.submit_once(job,operation_key='bad_scope'))
        with store.transaction():store.db.execute('DELETE FROM public_search_order_scopes WHERE job_ref=?',(job,))
        with pytest.raises(ContractError,match='unavailable_binding'):ops.open_order(job)
        assert client.calls==[]


def test_sequence_symbols_reads_actual_feature_and_rootless_reference_without_new_targets(tmp_path):
    from gene_annotation_episode.public_search_publication import PublicSearchResultPublisher
    from gene_annotation_episode.tools import ToolRegistry
    store,client,ops,order=setup(tmp_path)
    with store:
        target=store.problem()['subject_refs'][0];scope={'subject_refs':[target]}
        feature=store.put('feature',dict(subject_ref=target,kind='sequence_region',
            segments=[dict(start=1,end=4)],strand='+',context_refs=[]),origin='tool')
        source=store.put('source',dict(provider='fixture_external_sequence',accession=None,uri=None,
            artifact_ref=store.artifact(b'original fixture protein symbols'),text_ref=None,request_ref=None,
            version=None,retrieved_at='2026-10-22T00:00:00+00:00'),origin='external')
        reference=store.put('reference',dict(reference_type='protein',source_ref=source['id'],accession='FIXTURE',
            label='Synthetic source-grounded protein',sequence_ref=store.artifact('YYYY','text/plain'),
            molecule='protein',length=4,term_refs=[],context_refs=[]),origin='external')
        tools=ToolRegistry(store,clients=client)
        ports=PublicSearchPorts(registry(client),ops,PublicSearchResultPublisher(store,tools,operations=ops))
        before=[dict(row) for row in store.targets()];before_refs=store.count('reference')
        assert 'sequence_ref' not in feature and store.roots(reference['id'])==[]
        assert ports.sequence_symbols(feature['id'],scope=scope)=='ACD'
        assert ports.sequence_symbols(reference['id'],scope=scope)=='YYYY'
        assert [dict(row) for row in store.targets()]==before and store.count('reference')==before_refs
        assert client.calls==[]
        excluded=dict(subject_refs=[target],segments=[dict(target_ref=target,start=5,end=8,unit='aa')])
        with pytest.raises(ContractError):ports.sequence_symbols(feature['id'],scope=excluded)
        assert ports.sequence_symbols(reference['id'],scope=excluded)=='YYYY'


def test_absent_client_outcome_projects_unknown_without_changing_raw_capture(tmp_path):
    async def run():
        store,client,ops,order=setup(tmp_path)
        with store:
            client.submit_error=TimeoutError('selected POST may have reached fixture')
            receipt=await ops.submit_once(order['job_ref'],operation_key='submit')
            assert receipt['failure']['code']=='submission_uncertain'
            assert receipt['failure']['submission_outcome']=='unknown'
            raw=json.loads((ops._capsule_path('submit')/'manifest.json').read_bytes())
            assert raw['client_failure']['submission_outcome'] is None
            assert ops.read_operation(receipt['receipt_ref'])==receipt
            repeat=await ops.submit_once(order['job_ref'],operation_key='later')
            assert repeat['failure']['code']=='submission_uncertain' and len(client.calls)==1
    asyncio.run(run())
