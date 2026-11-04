"""Actual saved provider bytes reused offline; synthetic Store/transport binding.

No public submissions, status requests, result fetches or model calls are made.
"""
import asyncio
from dataclasses import replace
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
import base64
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, SourceSnapshot
from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.provider_jobs import HMMER_IDENTITY_VERSION, RemoteSearches
from gene_annotation_episode.rfam_discovery import submission_failure_feedback
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from api_execution_fixture import APIHarness

FIXTURES=Path(__file__).resolve().parents[1]/'validation/fixtures/provider_identity_feedback'
CUSTODY=json.loads((FIXTURES/'CUSTODY.json').read_text())
SAVED_JOB=CUSTODY['hmmer']['job']
SEQUENCE=(FIXTURES/'hmmer_product.txt').read_text()



class SavedHmmer:
    ncbi_email=None
    def __init__(self): self.calls=[];self.echo=None
    def hmmer_submit(self,query_fasta,**kwargs):
        self.calls.append(('submit',query_fasta,kwargs))
        return saved_snapshot('submission')
    def hmmer_status(self,remote_id):
        self.calls.append(('status',remote_id))
        snapshot=saved_snapshot('status')
        if self.echo is not None:
            body=json.loads(snapshot.content);body['input']=self.echo
            snapshot=replace(snapshot,content=json.dumps(body).encode())
        return snapshot
    def hmmer_result(self,remote_id,**kwargs):
        self.calls.append(('result',remote_id,kwargs))
        return saved_snapshot('result')


# Saved metadata keys differ from the concise fixture body filenames.
def saved_snapshot(name):
    metadata=SAVED_JOB['latest_status' if name=='status' else name].copy(); metadata.pop('content_ref')
    return SourceSnapshot(**metadata,content=(FIXTURES/f'hmmer_{name}.json').read_bytes())


def new_tools(tmp_path,client,sequence=SEQUENCE,molecule='protein'):
    store=Store(tmp_path/'state');problem=store.create_problem(raw_sequence=sequence,molecule=molecule)
    tools=ToolRegistry(store,clients=client,provider_poll_interval_seconds=0)
    return store,tools,problem['subject_refs'][0]


def test_exact_saved_custody_and_actual_hmmer_zero_hits_are_preserved(tmp_path):
    for name,entry in CUSTODY['custody'].items():
        raw=(FIXTURES/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==entry['sha256'] and len(raw)==entry['bytes']
    native=json.loads((FIXTURES/'hmmer_result.json').read_bytes())
    assert native['status']=='SUCCESS' and native['result']['hits']==[] and native['result']['stats']['nhits']==0
    echo=json.loads((FIXTURES/'hmmer_status.json').read_bytes())['input']
    old=SAVED_JOB['request']
    assert hashlib.sha256(echo.encode()).hexdigest()==old['query_sha256']
    assert hashlib.sha256(''.join(echo.split()).upper().encode()).hexdigest()==old['sequence_sha256']
    assert hashlib.sha256(SEQUENCE.encode()).hexdigest()!=old['sequence_sha256']
    client=SavedHmmer();store,tools,subject=new_tools(tmp_path,client)
    with store:
        owner=APIHarness(tools,subject_ref=subject,algorithm='hmmscan',database='pfam',page_size=20)
        handoff=owner.handoff()
        receiver=owner.results(handoff)
        response=receiver.act('api.hmmer.result')
        assert response['status']=='completed',response
        assert response['result']['status']=='SUCCESS' and response['result']['records']==[]
        assert response['result']['database']['version']=='37.2'
        assert response['result']['native_search_stats']['nhits']==0
        assert store.count('observation')==0 and project_credit(store).credit==0
        job=tools.remote_searches.describe(response['result']['job_ref']);request=job['request']
        assert request['sequence_sha256']==hashlib.sha256(SEQUENCE.encode()).hexdigest()
        assert request['query_sha256']==hashlib.sha256(client.calls[0][1].encode()).hexdigest()
        assert request['query_length']==279 and request['identity_version']==HMMER_IDENTITY_VERSION
        assert request['query_sha256_representation']=='submitted_fasta_utf8_bytes'
        assert request['sequence_sha256_representation']=='single_fasta_sequence_uppercase_whitespace_removed_ascii'
        source=store.get(response['result']['source_ref'])
        assert store.get_artifact(source['artifact_ref'])==(FIXTURES/'hmmer_result.json').read_bytes()
        source_request=json.loads(store.get_artifact(source['request_ref']))['request']
        assert all(source_request[key]==value for key,value in request.items())
        assert source_request['sequence_sha256']!=source_request['query_sha256']
        assert receiver.act('api.hmmer.result',index=0)==response
        assert [call[0] for call in client.calls]==['submit','status','result']


@pytest.mark.parametrize('echo',[SEQUENCE.lower(),'>different_source_header\n'+SEQUENCE.lower()[:100]+'\n'+SEQUENCE.lower()[100:],'>different\n'+SEQUENCE[:-1]+'Y'])
def test_echo_identity_uses_actual_sequence_with_explicit_wrapper_meanings(tmp_path,echo):
    client=SavedHmmer();client.echo=echo
    store,tools,subject=new_tools(tmp_path,client)
    with store:
        owner=APIHarness(tools,subject_ref=subject,algorithm='hmmscan',database='pfam')
        assert owner.act('api.hmmer.submit')['status']=='completed'
        response=owner.act('api.hmmer.check_handoff')
        if echo.endswith('Y'):
            assert response['status']=='failed' and response['feedback']['code']=='remote_identity_conflict_input'
            assert response['feedback']['status_addressable'] and response['feedback']['remote_handle_known']
        else:
            assert response['status']=='completed',response
            assert owner.results(response['result']['handoff_ref']).act('api.hmmer.result')['result']['records']==[]


@pytest.mark.parametrize('cached',[False,True])
def test_historical_unversioned_request_not_reinterpreted_mutated_or_resubmitted(tmp_path,cached):
    client=SavedHmmer();store,tools,subject=new_tools(tmp_path,client)
    with store:
        old=dict(SAVED_JOB['request'],subject_ref=subject)
        result=tools.remote_searches._snapshot(saved_snapshot('result')) if cached else None
        job_ref=SAVED_JOB['id']
        store.db.execute('INSERT INTO provider_jobs VALUES(?,?,?,?,?,?,?,?,?)',
            (job_ref,'historical_op',canonical(old),'returned' if cached else 'accepted',SAVED_JOB['remote_id'],None,None,result,None))
        store.db.commit()
        before=dict(store.db.execute('SELECT * FROM provider_jobs WHERE id=?',(job_ref,)).fetchone())
        before_sources=store.count('source')
        assert tools.execute('public.search.jobs',{'active_only':False})['status']=='completed'
        for name,args in [('public.hmmer.collect',{'job_ref':job_ref}),('public.hmmer.page',{'job_ref':job_ref,'page':1})]:
            response=tools.execute(name,args)
            assert response['status']=='invalid' and response['feedback']['code']=='unknown_tool'
        with pytest.raises(Exception,match='hmmer_requires_api_execution_episode'):
            asyncio.run(tools.remote_searches.search('historical_op',subject_ref=subject,
                query_fasta=f'>{subject}\n{SEQUENCE}',algorithm='hmmscan',database='pfam',page_size=20))
        assert dict(store.db.execute('SELECT * FROM provider_jobs WHERE id=?',(job_ref,)).fetchone())==before
        assert client.calls==[] and store.count('source')==before_sources
    with Store(tmp_path/'state') as reopened:
        later=SavedHmmer();registry=ToolRegistry(reopened,clients=later,provider_poll_interval_seconds=0)
        listed=registry.remote_searches.jobs(active_only=False)[0]
        described=registry.remote_searches.describe(job_ref)
        for state in (listed,described):
            assert state['remote_handle_known'] and not state['collectable']
            assert state['identity_compatibility']=='unsupported_historical_hmmer_request'
            assert state['stored_identity_version'] is None
        error=registry.execute('public.hmmer.collect',{'job_ref':job_ref})
        assert error['status']=='invalid' and error['feedback']['code']=='unknown_tool'
        assert later.calls==[]
        assert dict(reopened.db.execute('SELECT * FROM provider_jobs WHERE id=?',(job_ref,)).fetchone())==before


def rfam_saved():
    metadata=json.loads((FIXTURES/'rfam_error_snapshot.json').read_bytes());metadata.pop('content_ref')
    return SourceSnapshot(**metadata,content=(FIXTURES/'rfam_error.json').read_bytes())


def rfam_submitted_sequence():
    saved=rfam_saved();request=saved.transport['request']
    content_type=next(value for key,value in request['headers'].items() if key.lower()=='content-type')
    body=base64.b64decode(request['body_base64'])
    message=BytesParser(policy=policy.default).parsebytes(('Content-Type: '+content_type+'\r\nMIME-Version: 1.0\r\n\r\n').encode()+body)
    part,=message.iter_parts()
    assert part.get_param('name',header='content-disposition')=='sequence_file'
    return part.get_payload(decode=True).decode('ascii').strip()


class SavedRfamFailure:
    ncbi_email=None
    def __init__(self):self.submissions=[]
    def rfam_submit(self,sequence):
        self.submissions.append(sequence)
        raise AcquisitionError('provider_http_400',snapshot=rfam_saved(),phase='http_response')


def test_saved_rfam_length_reason_reaches_owner_reopen_and_no_automatic_followup(tmp_path):
    sequence=rfam_submitted_sequence(); assert len(sequence)==32098
    client=SavedRfamFailure();store,tools,subject=new_tools(tmp_path,client,sequence,'dna')
    with store:
        failed=tools.execute('public.rfam.search',{'subject_ref':subject},operation_key='oversized')
        assert failed['status']=='failed' and failed['record_refs']==[]
        cause=failed['feedback']['cause'];info=cause['provider_feedback']
        assert failed['feedback']['code']==cause['code']=='provider_http_400'
        assert info=={'version':'rfam_native_submission_feedback_v1','kind':'submitted_sequence_length_limit',
            'basis':'native_error_detail','native_field':'detail','unit':'nt','maximum_length':7000,
            'submitted_length':32098,'submitted_exceeds_reported_maximum':True}
        assert cause['submission_outcome']=='unknown' and failed['feedback']['submission_state']=='submission_uncertain'
        assert not failed['feedback']['remote_handle_known'] and not failed['feedback']['collectable']
        diagnostic=json.loads(store.get_artifact(failed['feedback']['diagnostic_ref']))
        assert store.get_artifact(diagnostic['content_ref'])==(FIXTURES/'rfam_error.json').read_bytes()
        assert client.submissions==[sequence] and project_credit(store).credit==0
        job=failed['feedback']['job_ref']
    with Store(tmp_path/'state') as reopened:
        later=SavedRfamFailure();registry=ToolRegistry(reopened,clients=later,provider_poll_interval_seconds=0)
        assert registry.execute('public.rfam.search',{'subject_ref':subject},operation_key='oversized')==failed
        result=registry.execute('public.rfam.collect',{'job_ref':job})
        assert result['feedback']['cause']['provider_feedback']==info and later.submissions==[]
        assert registry.remote_searches.describe(job)['cause']['provider_feedback']==info


@pytest.mark.parametrize('status,body,submitted,expected',[(400,b'{"detail":"unrelated native failure"}',32098,None),
    (400,b'not JSON',32098,None),(503,(FIXTURES/'rfam_error.json').read_bytes(),32098,None),
    (400,json.dumps({'detail':'Sequence length must be less than or equal to '+'9'*5000+' nucleotides'}).encode(),32098,None),
    (400,(FIXTURES/'rfam_error.json').read_bytes(),7000,False),(400,(FIXTURES/'rfam_error.json').read_bytes(),7001,True)])
def test_only_known_native_length_detail_gets_typed_length_meaning(status,body,submitted,expected):
    info=submission_failure_feedback(body,http_status=status,submitted_length=submitted)
    assert info is None if expected is None else info['submitted_exceeds_reported_maximum'] is expected


def test_same_http400_detail_is_not_interpreted_as_rfam_limit_for_other_provider(tmp_path):
    class OtherProvider(SavedHmmer):
        def hmmer_submit(self,query_fasta,**kwargs):
            self.calls.append(('submit',query_fasta,kwargs))
            raise AcquisitionError('provider_http_400',snapshot=replace(rfam_saved(),service='ebi_hmmer'),phase='http_response')
    client=OtherProvider();store,tools,subject=new_tools(tmp_path,client)
    with store:
        result=APIHarness(tools,subject_ref=subject,algorithm='hmmscan',database='pfam').act('api.hmmer.submit')
        assert result['status']=='failed' and result['feedback']['code']=='provider_http_400'
        assert 'provider_feedback' not in result['feedback']['cause']
        assert len(client.calls)==1 and project_credit(store).credit==0


def test_unversioned_rfam_request_reopens_same_operation_without_identity_rewrite(tmp_path):
    from test_rfam_discovery import Client, QUERY
    client=Client();store,tools,subject=new_tools(tmp_path,client,QUERY,'dna')
    with store:
        result=tools.execute('public.rfam.search',{'subject_ref':subject},operation_key='unversioned')
        assert result['status']=='completed',result
        job=result['result']['job_ref'];before=tools.remote_searches._get(job)
        request=json.loads(before['request'])
        assert request['provider']=='rfam' and 'identity_version' not in request and 'query_length' not in request
    with Store(tmp_path/'state') as reopened:
        later=Client();registry=ToolRegistry(reopened,clients=later,provider_poll_interval_seconds=0)
        described=registry.remote_searches.describe(job)
        assert described['collectable'] and 'identity_compatibility' not in described
        snapshot=asyncio.run(registry.remote_searches.search('unversioned',subject_ref=subject,
            query_fasta=f'>{subject}\n{QUERY}',algorithm='cmscan',database='Rfam',provider='rfam'))
        assert snapshot.content==registry.remote_searches._load_snapshot(before['result']).content
        assert later.submissions==later.gets==0
        assert registry.remote_searches._get(job)==before


def test_native_failure_feedback_reaches_next_owned_choice_without_failed_action_observation(tmp_path):
    from test_runtime import FixtureController,ScriptedProvider
    from gene_annotation_episode.runtime import run_workflow
    sequence=rfam_submitted_sequence();client=SavedRfamFailure()
    store,tools,subject=new_tools(tmp_path,client,sequence,'dna')
    with store:
        def selected_view(context):
            info=context['feedback']['cause']['provider_feedback']
            assert info['maximum_length']==7000 and info['submitted_length']==32098
            assert context['controller']['scores']==[]
            return {'selection':{'kind':'tool','tool':'sequence.view',
                'arguments':{'subject_ref':subject,'molecule':'dna','segments':[{'start':0,'end':6000}]}},'report_update':{}}
        provider=ScriptedProvider([{'selection':{'kind':'tool','tool':'public.rfam.search','arguments':{'subject_ref':subject}},'report_update':{}},selected_view])
        summary=asyncio.run(run_workflow(store,tools,provider=provider,run_dir=tmp_path/'run',
            controller_factory=lambda path,initial:FixtureController(str(path),initial,1)))
        assert summary['completed_actions']==1 and summary['credit']==0
        assert client.submissions==[sequence] and len(provider.contexts)==2
        actions=store.db.execute('SELECT action,result FROM runtime_actions ORDER BY decision_index').fetchall()
        assert [json.loads(row['result'])['status'] for row in actions]==['failed','completed']
        assert json.loads(actions[1]['action'])['arguments']['segments']==[{'start':0,'end':6000}]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==1
        assert not store.current_annotations()
