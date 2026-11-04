"""Saved official-example protocol plus labelled local failure fixtures.

No test submits a new search, searches the unknown RNA candidate, or establishes
biological annotation accuracy. The 119 nt query is the official API example.
"""
import asyncio
import base64
from copy import deepcopy
from dataclasses import replace
from email.message import Message
from email.parser import BytesParser
from email.policy import default
import hashlib
import io
import json
from pathlib import Path
import threading
import urllib.error
import urllib.request

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, SourceSnapshot
from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.provider_jobs import RemoteSearches
from gene_annotation_episode.rfam_discovery import hit_row, result_body, result_url
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

FIXTURES = Path(__file__).resolve().parents[1] / 'validation/providers/rfam-batch-calibration'
NATIVE = (FIXTURES / 'result-response-01.body').read_bytes()
SUBMISSION = (FIXTURES / 'submission-response.body').read_bytes()
QUERY = (FIXTURES / 'official-api-example.seq').read_text().strip()
JOB = json.loads(SUBMISSION)['jobId']
URL = result_url(JOB)


def snapshot(content=NATIVE, *, status=200, url=URL):
    if isinstance(content, dict):
        content = json.dumps(content).encode()
    return SourceSnapshot('rfam_batch', url, {}, '2026-10-20T04:14:46.020299+00:00',
        content, 'application/json', {'status': status, 'effective_url': url,
        'representation': 'saved_official_example_or_labelled_local_protocol_fixture'})


class Client:
    """Synthetic transport serving the exact saved provider result by default."""
    ncbi_email = None
    def __init__(self, *, body=NATIVE, pending=()):
        self.submissions = 0
        self.gets = 0
        self.body = body
        self.pending = list(pending)
        self.sequences = []
        self.threads = []

    def rfam_submit(self, sequence):
        self.threads.append(threading.get_ident())
        self.submissions += 1
        self.sequences.append(sequence)
        return snapshot(SUBMISSION, url='https://batch.rfam.org/submit-job')

    def rfam_result(self, job_id):
        self.threads.append(threading.get_ident())
        assert job_id == JOB
        self.gets += 1
        if self.pending:
            return snapshot(self.pending.pop(0), status=202)
        return snapshot(self.body)


def test_saved_actual_protocol_sequence_and_model_axes_remain_distinct(tmp_path):
    metadata = json.loads((FIXTURES / 'result-response-01.json').read_text())
    assert hashlib.sha256(NATIVE).hexdigest() == metadata['sha256']
    assert hashlib.sha256(SUBMISSION).hexdigest() == json.loads((FIXTURES / 'submission-intent.json').read_text())['response_sha256']
    parsed = result_body(NATIVE, job_id=JOB, sequence_sha256=hashlib.sha256(QUERY.encode()).hexdigest())
    row = hit_row(parsed['hits']['5S_rRNA'][0], family_key='5S_rRNA', sequence_length=len(QUERY))
    assert row['sequence_interval'] == [0, 119]
    assert parsed['hits']['5S_rRNA'][0]['alignment']['hit_seq'].endswith('120')
    client = Client()
    with Store(tmp_path) as store:
        original = store.create_problem(raw_sequence=QUERY)  # Unspecified caller molecule/unit.
        subject = original['subject_refs'][0]
        tools = ToolRegistry(store, clients=client, provider_poll_interval_seconds=0)
        owner_thread = threading.get_ident()
        result = tools.execute('public.rfam.search', {'subject_ref': subject}, operation_key='discovery')
        assert result['status'] == 'completed', result
        data = result['result']
        assert data['database_release'] is None and data['model_release'] is None
        assert data['native_times'] == {k: parsed[k] for k in ('opened','started','closed')}
        assert data['native_times']['started'] > data['native_times']['closed']  # No invented duration.
        record = data['records'][0]
        family = store.get(record['family_ref'])
        assert family['accession'] == 'RF00001' and family['reference_type'] == 'family'
        assert family['length'] is None and family['sequence_ref'] is None
        obs = store.get(record['observation_ref'])
        assert obs['kind'] == 'profile_match' and obs['subject_refs'] == [subject]
        assert obs['source_subject_refs'] == [family['id']]
        assert obs['operand_intervals'] == [{'role':'query','subject_ref':subject,'start':0,'end':119,
                                            'unit':'symbol','model_unit':'nt'}]
        source = store.get(data['source_ref'])
        assert source['version'] is None and store.get_artifact(source['artifact_ref']) == NATIVE
        assert source['parent_source_refs'] == [data['submission_source_ref']]
        assert store.get_artifact(store.get(data['submission_source_ref'])['artifact_ref']) == SUBMISSION
        assert store.get(subject)['molecule'] == 'unspecified'
        assert not store.current_annotations() and project_credit(store).credit == 0
        assert tools.execute('public.rfam.search', {'subject_ref':subject}, operation_key='discovery') == result
        assert client.submissions == 1 and client.gets == 1 and client.sequences == [QUERY]
        assert all(t != owner_thread for t in client.threads)
        assert store.db.execute('SELECT COUNT(*) FROM tool_operations').fetchone()[0] == 1


class HTTPResponse:
    def __init__(self, body, url, status=200):
        self.body, self.url, self.status = body, url, status
        self.headers = Message(); self.headers['Content-Type']='application/json'
    def read(self): return self.body
    def geturl(self): return self.url
    def __enter__(self): return self
    def __exit__(self,*args): pass


def test_multipart_transport_retains_exact_native_submission_and_failed_http_bytes(monkeypatch):
    requests = []
    def received(request, **kwargs):
        requests.append(request)
        return HTTPResponse(SUBMISSION, request.full_url)
    monkeypatch.setattr(urllib.request,'urlopen',received)
    client = PublicClients()
    captured = client.rfam_submit(QUERY)
    request = requests[0]
    envelope = BytesParser(policy=default).parsebytes(('Content-Type: '+request.headers['Content-type']+'\r\n\r\n').encode()+request.data)
    parts = list(envelope.iter_parts())
    assert len(parts)==1 and parts[0].get_param('name',header='content-disposition')=='sequence_file'
    assert parts[0].get_payload(decode=True)==(QUERY+'\n').encode()
    assert base64.b64decode(captured.transport['request']['body_base64']) == request.data
    assert captured.transport['request']['body_sha256'] == hashlib.sha256(request.data).hexdigest()
    assert request.get_method()=='POST' and request.full_url=='https://batch.rfam.org/submit-job'
    error_body=b'{"error":"labelled provider fixture, not target biology"}'
    def failed(request,**kwargs):
        raise urllib.error.HTTPError(request.full_url,503,'unavailable',Message(),io.BytesIO(error_body))
    monkeypatch.setattr(urllib.request,'urlopen',failed)
    with pytest.raises(AcquisitionError) as failed_request:
        client.rfam_submit(QUERY)
    assert failed_request.value.snapshot.content == error_body
    assert failed_request.value.snapshot.transport['request']['body_base64']
    assert failed_request.value.submission_outcome is None  # No assumed no-POST from HTTP status.


@pytest.mark.parametrize('pending', [b'PEND', b'RUN', b'"PEND"'])
def test_protocol_pending_checks_are_one_durable_action(tmp_path,pending):
    client=Client(pending=[pending])
    with Store(tmp_path) as store:
        subject=store.create_problem(raw_sequence=QUERY,molecule='dna')['subject_refs'][0]
        tools=ToolRegistry(store,clients=client,provider_poll_interval_seconds=0)
        response=tools.execute('public.rfam.search',{'subject_ref':subject},operation_key='wait')
        assert response['status']=='completed',response
        assert client.submissions==1 and client.gets==2
        assert store.db.execute('SELECT COUNT(*) FROM tool_operations').fetchone()[0]==1
        assert len(tools.remote_searches.jobs(active_only=False))==1
        assert tools.remote_searches.jobs()==[]


def test_accepted_cancelled_search_reopens_same_handle_and_replays_measurement(tmp_path):
    async def check():
        client=Client()
        with Store(tmp_path) as store:
            subject=store.create_problem(raw_sequence=QUERY,molecule='dna')['subject_refs'][0]
            tools=ToolRegistry(store,clients=client,provider_poll_interval_seconds=60)
            action=asyncio.create_task(tools.execute_async('public.rfam.search',{'subject_ref':subject},operation_key='durable'))
            while not tools.remote_searches.jobs() or tools.remote_searches.jobs()[0]['remote_id'] is None:
                await asyncio.sleep(.005)
            action.cancel()
            with pytest.raises(asyncio.CancelledError): await action
            assert client.submissions==1 and client.gets==0
            assert tools.remote_searches.jobs()[0]['state']=='accepted'
        with Store(tmp_path) as store:
            resumed=Client()
            tools=ToolRegistry(store,clients=resumed,provider_poll_interval_seconds=0)
            response=await tools.execute_async('public.rfam.search',{'subject_ref':subject},operation_key='durable')
            assert response['status']=='completed' and resumed.submissions==0 and resumed.gets==1
            assert await tools.execute_async('public.rfam.search',{'subject_ref':subject},operation_key='durable')==response
            collected=await tools.execute_async('public.rfam.collect',{'job_ref':response['result']['job_ref']})
            assert collected['result']['records']==response['result']['records']
            assert resumed.gets==1 and resumed.submissions==0
            assert project_credit(store).credit==0
    asyncio.run(check())


def test_uncertain_post_is_not_repeated_and_known_handle_failures_are_collectable(tmp_path):
    class Uncertain(Client):
        def rfam_submit(self,sequence):
            self.submissions+=1
            raise TimeoutError('labelled uncertain POST fixture')
    async def check():
        with Store(tmp_path) as store:
            subject=store.create_problem(raw_sequence=QUERY,molecule='dna')['subject_refs'][0]
            client=Uncertain(); jobs=RemoteSearches(store,client,poll_interval_seconds=0)
            request={'subject_ref':subject,'query_fasta':f'>q\n{QUERY}','algorithm':'cmscan','database':'Rfam','provider':'rfam'}
            for _ in range(2):
                with pytest.raises(AcquisitionError) as failure: await jobs.search('uncertain',**request)
                assert failure.value.operational['submission_state']=='submission_uncertain'
            assert client.submissions==1 and not jobs.jobs()[0]['collectable']
    asyncio.run(check())
    class FailingGet(Client):
        def rfam_result(self,job_id):
            self.gets+=1
            raise AcquisitionError('provider_http_503',snapshot=snapshot(b'HOLD',status=503),phase='http_response')
    with Store(tmp_path/'known') as store:
        subject=store.create_problem(raw_sequence=QUERY,molecule='dna')['subject_refs'][0]
        client=FailingGet(); tools=ToolRegistry(store,clients=client,provider_poll_interval_seconds=0)
        failed=tools.execute('public.rfam.search',{'subject_ref':subject},operation_key='known-failure')
        assert failed['status']=='failed' and not failed['record_refs']
        assert failed['feedback']['code']=='provider_http_503' and failed['feedback']['remote_handle_known']
        assert failed['feedback']['cause']['http_status']==503
        assert failed['feedback']['submission_state']=='HOLD' and tools.remote_searches.jobs()[0]['state']=='HOLD'
        client.rfam_result=Client().rfam_result
        recovered=tools.execute('public.rfam.collect',{'job_ref':failed['feedback']['job_ref']})
        assert recovered['status']=='completed' and client.submissions==1
        assert tools.execute('public.rfam.search',{'subject_ref':subject},operation_key='known-failure')==failed
        assert tools.remote_searches.describe(failed['feedback']['job_ref'])['cause'] is None


@pytest.mark.parametrize('url', [
    'https://elsewhere.invalid/result/'+JOB,
    URL+'?different=1', URL+'#fragment',
    'https://batch.rfam.org/result/infernal_cmscan-different-job'])
def test_submission_result_url_cannot_change_provider_or_job(tmp_path,url):
    client=Client()
    def submit(sequence):
        client.submissions+=1
        return snapshot({'jobId':JOB,'resultURL':url},url='https://batch.rfam.org/submit-job')
    client.rfam_submit=submit
    with Store(tmp_path) as store:
        subject=store.create_problem(raw_sequence=QUERY,molecule='dna')['subject_refs'][0]
        tools=ToolRegistry(store,clients=client,provider_poll_interval_seconds=0)
        result=tools.execute('public.rfam.search',{'subject_ref':subject},operation_key='url-check')
        assert result['status']=='failed' and result['feedback']['code']=='provider_submission_response_invalid'
        assert not result['feedback']['remote_handle_known'] and client.gets==0
        assert tools.execute('public.rfam.search',{'subject_ref':subject},operation_key='url-check')==result
        assert client.submissions==1 and not store.count('observation')


@pytest.mark.parametrize('field,value,code',[
    ('jobId','infernal_cmscan-other','rfam_result_job_identity_conflict'),
    ('searchSequence','A'*119,'rfam_result_sequence_identity_conflict')])
def test_contradictory_native_identity_not_published_and_explicit_collect_recovers(tmp_path,field,value,code):
    body=json.loads(NATIVE);body[field]=value; client=Client(body=body)
    with Store(tmp_path) as store:
        subject=store.create_problem(raw_sequence=QUERY,molecule='dna')['subject_refs'][0]
        tools=ToolRegistry(store,clients=client,provider_poll_interval_seconds=0)
        source_count_before = store.count('source')  # The caller input already owns a source.
        failed=tools.execute('public.rfam.search',{'subject_ref':subject})
        assert failed['status']=='failed' and failed['feedback']['code']==code
        assert not store.count('observation') and store.count('source') == source_count_before
        metadata=json.loads(store.get_artifact(failed['feedback']['diagnostic_ref']))
        assert json.loads(store.get_artifact(metadata['content_ref']))[field]==value
        client.body=NATIVE
        recovered=tools.execute('public.rfam.collect',{'job_ref':failed['feedback']['job_ref']})
        assert recovered['status']=='completed' and client.submissions==1


def test_partial_bad_native_rows_retain_every_independent_valid_hit_including_reverse(tmp_path):
    body=json.loads(NATIVE); row=body['hits']['5S_rRNA'][0]
    reverse={**deepcopy(row),'start':110,'end':10,'strand':'-','score':-1.2,'E':30.0}
    bad={**deepcopy(row),'end':120}
    body['hits']['5S_rRNA']=[row,bad,reverse];body['numHits']=3
    with Store(tmp_path) as store:
        subject=store.create_problem(raw_sequence=QUERY,molecule='rna')['subject_refs'][0]
        tools=ToolRegistry(store,clients=Client(body=body),provider_poll_interval_seconds=0)
        response=tools.execute('public.rfam.search',{'subject_ref':subject})
        assert response['status']=='partial',response
        assert response['feedback']['code']=='rfam_rows_partially_projected'
        assert response['feedback']['rows']==[{'family_key':'5S_rRNA','native_index':1,'code':'rfam_hit_sequence_coordinates_invalid'}]
        assert response['result']['native_hit_count']==3 and response['result']['projected_hit_count']==2
        records=response['result']['records'];assert len(records)==2
        assert records[1]['sequence_interval']==[9,110] and records[1]['strand']=='-'
        assert records[1]['evalue']==30.0  # No extra reporting/quality threshold.
        assert store.count('observation')==2 and not store.current_annotations()
        assert json.loads(store.get_artifact(store.get(response['result']['source_ref'])['artifact_ref']))==body


def test_zero_hits_are_a_completed_local_scope_result_without_absence_annotation(tmp_path):
    body={**json.loads(NATIVE),'numHits':0,'hits':{}}
    with Store(tmp_path) as store:
        subject=store.create_problem(raw_sequence=QUERY,molecule='dna')['subject_refs'][0]
        response=ToolRegistry(store,clients=Client(body=body),provider_poll_interval_seconds=0).execute('public.rfam.search',{'subject_ref':subject})
        assert response['status']=='completed' and response['result']['records']==[]
        assert response['result']['searched_scope']=={'subject_ref':subject,'start':0,'end':119,'unit':'nt'}
        assert not store.count('observation') and not store.current_annotations() and project_credit(store).credit==0


def test_external_operand_remains_source_only_and_assigned_input_segments_are_not_broadened(tmp_path):
    with Store(tmp_path) as store:
        problem=store.create_problem(raw_sequence='ACGT',molecule='dna')
        source=store.put('source',{'provider':'explicit_test_fixture','accession':None,'uri':None,
            'artifact_ref':store.artifact(QUERY,'text/plain'),'text_ref':None,'request_ref':None,'version':None,
            'retrieved_at':'2026-10-20T00:00:00Z'},origin='external')
        reference=store.put('reference',{'reference_type':'rna','source_ref':source['id'],'accession':'fixture_rna',
            'label':'labelled external test material','sequence_ref':source['artifact_ref'],'molecule':'rna','length':len(QUERY),
            'term_refs':[],'context_refs':[]},origin='external')
        client=Client();tools=ToolRegistry(store,clients=client,provider_poll_interval_seconds=0)
        result=tools.execute('public.rfam.search',{'subject_ref':reference['id']})
        assert result['status']=='completed',result
        obs=store.get(result['result']['records'][0]['observation_ref'])
        assert obs['subject_refs']==[reference['id']] and store.roots(reference['id'])==[]
        assert all(store.coverage(operand['subject_ref'])==[] for operand in obs['operand_intervals'])
        assert project_credit(store).credit==0
        assert store.problem()['subject_refs']==problem['subject_refs']
    with Store(tmp_path/'scoped') as store:
        subject=store.create_problem(raw_sequence=QUERY,molecule='dna')['subject_refs'][0]
        client=Client();tools=ToolRegistry(store,clients=client,provider_poll_interval_seconds=0)
        response=tools.execute('public.rfam.search',{'subject_ref':subject},scope={'subject_refs':[subject],
            'segments':[{'target_ref':subject,'start':0,'end':20,'unit':'nt'}]})
        assert response['status']=='invalid' and response['feedback']['code']=='requested_measurement_outside_assigned_segments'
        assert client.submissions==0


def test_collect_entrypoints_cannot_silently_reinterpret_other_provider_jobs(tmp_path):
    from test_public_search import Client as HmmerClient
    with Store(tmp_path) as store:
        subject=store.create_problem(raw_sequence=QUERY,molecule='dna')['subject_refs'][0]
        tools=ToolRegistry(store,clients=Client(),provider_poll_interval_seconds=0)
        rfam=tools.execute('public.rfam.search',{'subject_ref':subject})
        job=rfam['result']['job_ref']
        assert tools.execute('public.hmmer.collect',{'job_ref':job})['feedback']['code']=='unknown_tool'
        assert tools.execute('public.hmmer.page',{'job_ref':job,'page':1})['feedback']['code']=='unknown_tool'
        jobs=RemoteSearches(store,HmmerClient(),poll_interval_seconds=0)
        with pytest.raises(Exception, match='hmmer_requires_api_execution_episode'):
            asyncio.run(jobs.search('hmmer',subject_ref=subject,query_fasta='>q\nMACDEFGH',algorithm='phmmer',database='swissprot'))
        # Historical HMMER records remain discoverable, but cannot execute an
        # old private wait loop or enter an unrelated provider's collector.
        other='historical-hmmer'
        store.db.execute('INSERT INTO provider_jobs VALUES(?,?,?,?,?,?,?,?,?)',
            (other,'historical-hmmer-key',json.dumps({'subject_ref':subject}), 'accepted',None,None,None,None,None))
        assert tools.execute('public.rfam.collect',{'job_ref':other})['feedback']['code']=='provider_job_does_not_belong_to_rfam'



def test_real_runtime_boundary_one_selected_search_one_observation_no_progress_manufactured(tmp_path):
    from test_runtime import FixtureController,ScriptedProvider
    from gene_annotation_episode.runtime import run_workflow
    with Store(tmp_path/'state') as store:
        subject=store.create_problem(raw_sequence=QUERY,molecule='dna')['subject_refs'][0]
        client=Client(pending=[b'PEND',b'RUN'])
        tools=ToolRegistry(store,clients=client,provider_poll_interval_seconds=0)
        provider=ScriptedProvider([{'selection':{'kind':'tool','tool':'public.rfam.search',
            'arguments':{'subject_ref':subject}},'report_update':{}}])
        result=asyncio.run(run_workflow(store,tools,provider=provider,run_dir=tmp_path/'run',
            controller_factory=lambda path,initial:FixtureController(str(path),initial,1)))
        assert result['completed_actions']==1 and result['credit']==0
        assert client.submissions==1 and client.gets==3 and len(provider.contexts)==1
        observations=store.db.execute('SELECT observation FROM runtime_observations').fetchall()
        assert len(observations)==1
        assert json.loads(observations[0][0])['label']=='tool:0'
        assert not store.current_annotations()


def test_documented_deleted_job_is_terminal_remote_ownership_not_episode_completion(tmp_path):
    class Deleted(Client):
        def rfam_result(self,job_id):
            self.gets+=1
            raise AcquisitionError('provider_http_410',snapshot=snapshot(b'DEL',status=410),phase='http_response')
    with Store(tmp_path) as store:
        subject=store.create_problem(raw_sequence=QUERY,molecule='dna')['subject_refs'][0]
        client=Deleted();tools=ToolRegistry(store,clients=client,provider_poll_interval_seconds=0)
        result=tools.execute('public.rfam.search',{'subject_ref':subject},operation_key='deleted-job')
        assert result['status']=='failed' and not result['record_refs']
        assert result['feedback']['code']=='provider_http_410'
        assert result['feedback']['submission_state']=='DEL'
        assert result['feedback']['remote_handle_known'] and result['feedback']['collectable']
        assert tools.remote_searches.jobs()==[]
        saved=tools.remote_searches.jobs(active_only=False)[0]
        assert saved['state']=='DEL' and saved['remote_id']==JOB
        metadata=json.loads(store.get_artifact(result['feedback']['diagnostic_ref']))
        assert store.get_artifact(metadata['content_ref'])==b'DEL'
        again=tools.execute('public.rfam.collect',{'job_ref':saved['job_ref']})
        assert again['status']=='failed' and again['feedback']['submission_state']=='DEL'
        assert client.submissions==1 and client.gets==2
        assert not store.count('observation') and not store.current_annotations() and project_credit(store).credit==0


@pytest.mark.parametrize('body',[b'not JSON',b'[]',b'{}',b'{"jobId":"../bad","resultURL":"https://batch.rfam.org/result/../bad"}'])
def test_malformed_accepted_submission_is_saved_and_never_automatically_resubmitted(tmp_path,body):
    client=Client()
    def submit(sequence):
        client.submissions+=1
        return snapshot(body,url='https://batch.rfam.org/submit-job')
    client.rfam_submit=submit
    with Store(tmp_path) as store:
        subject=store.create_problem(raw_sequence=QUERY,molecule='dna')['subject_refs'][0]
        tools=ToolRegistry(store,clients=client,provider_poll_interval_seconds=0)
        failed=tools.execute('public.rfam.search',{'subject_ref':subject},operation_key='malformed')
        assert failed['status']=='failed' and failed['feedback']['code']=='provider_submission_response_invalid'
        assert failed['feedback']['submission_state']=='submission_uncertain' and not failed['feedback']['remote_handle_known']
        row=tools.remote_searches._get(failed['feedback']['job_ref'])
        assert tools.remote_searches._load_snapshot(row['submission']).content==body
        assert tools.execute('public.rfam.collect',{'job_ref':row['id']})['feedback']['code']=='provider_submission_response_invalid'
        assert tools.execute('public.rfam.search',{'subject_ref':subject},operation_key='malformed')==failed
        assert client.submissions==1 and client.gets==0 and not store.count('observation')


def test_native_sources_and_exact_multipart_provenance_export_through_existing_forward_closure(tmp_path,monkeypatch):
    from gene_annotation_episode.export import export_annotation
    requests=[]
    def serve(request,**kwargs):
        requests.append(request)
        return HTTPResponse(SUBMISSION if request.get_method()=='POST' else NATIVE,request.full_url)
    monkeypatch.setattr(urllib.request,'urlopen',serve)
    with Store(tmp_path/'store') as store:
        subject=store.create_problem(raw_sequence=QUERY,molecule='dna')['subject_refs'][0]
        tools=ToolRegistry(store,clients=PublicClients(),provider_poll_interval_seconds=0)
        response=tools.execute('public.rfam.search',{'subject_ref':subject})
        assert response['status']=='completed',response
        document=tmp_path/'portable.json'
        export_annotation(store,document,include_artifacts=True)
        exported=json.loads(document.read_text())
        records={row['id']:row for row in exported['records']}
        artifacts={row['id']:row for row in exported['artifacts']}
        source=records[response['result']['source_ref']]
        submission=records[source['parent_source_refs'][0]]
        def contents(ref):return (document.parent/artifacts[ref]['relative_path']).read_bytes()
        assert contents(source['artifact_ref'])==NATIVE
        assert contents(submission['artifact_ref'])==SUBMISSION
        request_metadata=json.loads(contents(submission['request_ref']))
        assert base64.b64decode(request_metadata['transport']['request']['body_base64'])==requests[0].data
        assert not exported['membership']['current_annotation_refs']
