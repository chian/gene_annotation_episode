"""Synthetic BLAST/native-byte fixtures; no public searches or model calls."""
import asyncio
from dataclasses import replace
import io
import json
from pathlib import Path
import zipfile

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, SourceSnapshot
from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.export import export_annotation
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def snapshot(body, *, content_type='text/plain'):
    return SourceSnapshot('ncbi_blast','https://example.invalid/synthetic-offline-blast',{},
        '2026-10-19T00:00:00Z',body,content_type,{'status':200,'representation':'synthetic_fixture_no_network'})


def native(subject, program='blastn', *, bad=False, missing=False):
    row={'num':1,'query_from':3,'query_to':9,'hit_from':11,'hit_to':5,
        'bit_score':0.,'score':12.,'evalue':0.,'query_strand':'Plus','hit_strand':'Minus',
        'qseq':'ACGTAGG','hseq':'ACGTAGG'}
    if program in ('blastx','tblastx'): row['query_frame']=-2
    if program in ('tblastn','tblastx'): row['hit_frame']=-1
    if bad: row['query_to']=99
    hits=[{'num':1,'description':[{'id':'synthetic_native','accession':'SYNTHETIC.1','title':'labelled synthetic hit',
        'taxid':2157,'sciname':'Archaea'}], 'len':18,'hsps':[row]}]
    search={'query_id':'Query_1','query_title':subject,'query_len':12,'hits':hits}
    if missing: search.pop('hits')
    return {'BlastOutput2':[{'report':{'program':program,'version':'synthetic_BLAST',
        'search_target':{'db':'core_nt'},'params':{'expect':10},'results':{'search':search}}}]}


class Client:
    ncbi_email=None
    def __init__(self, *, program='blastn', zipped=False):
        self.program=program; self.zipped=zipped; self.calls=[]; self.pending=0
        self.bad=False; self.wrong=False; self.missing=False; self.empty=False
    def blast(self,action,**kw):
        self.calls.append((action,kw))
        if action=='submit':
            self.subject=kw['query_fasta'].splitlines()[0][1:]
            return snapshot(b'\n RID = SYNTHETIC_RID\n RTOE = 0\n')
        if action=='status':
            if self.pending:
                self.pending-=1
                return snapshot(b'Status=WAITING\n')
            return snapshot(b'Status=READY\nThereAreHits=yes\n')
        body=native('wrong_subject' if self.wrong else self.subject,self.program,missing=self.missing)
        hsps=body['BlastOutput2'][0]['report']['results']['search'].get('hits',[])
        if self.empty: body['BlastOutput2'][0]['report']['results']['search']['hits']=[]
        if self.bad: hsps[0]['hsps'] += [native(self.subject,self.program,bad=True)['BlastOutput2'][0]['report']['results']['search']['hits'][0]['hsps'][0]]
        raw=json.dumps(body).encode()
        if self.zipped:
            buffer=io.BytesIO()
            with zipfile.ZipFile(buffer,'w') as archive:
                archive.writestr('manifest.json',json.dumps({'BlastJSON':[{'File':'one.json'}]}))
                archive.writestr('one.json',raw)
            self.zip_bytes=buffer.getvalue(); self.json_bytes=raw
            return snapshot(self.zip_bytes,content_type='application/zip')
        return snapshot(raw,content_type='application/json')


def setup(tmp_path,client):
    reads=tmp_path/'reads.fastq'
    reads.write_text('@a\nTTACGTAGGGGG\n+\nIIIIIIIIIIII\n@b\nGGTACCAACCGG\n+\n!!!!!!!!!!!!\n')
    store=Store(tmp_path/'state'); store.create_problem(reads,molecule='dna')
    target,=store.targets(); tools=ToolRegistry(store,clients=client,provider_poll_interval_seconds=0)
    members=tools.execute('library.members',{'library_ref':target['id']})['result']['members']
    return store,tools,target,members


@pytest.mark.parametrize('program',['blastn','blastp','blastx','tblastn','tblastx'])
def test_program_native_intervals_zero_metrics_and_source_only_reference(tmp_path,program):
    client=Client(program=program)
    store,tools,target,(a,b)=setup(tmp_path,client)
    with store:
        response=tools.execute('public.blast.search',{'subject_ref':a['id'],'program':program,'database':'nt'},operation_key='one')
        assert response['status']=='completed',response
        row,=response['result']['records']; obs=store.get(row['observation_ref'])
        assert obs['subject_refs']==[a['id']] and obs['native_blast']['hit_from']==11
        q,r=obs['operand_intervals']
        assert [q['start'],q['end']]==[2,9] and [r['start'],r['end']]==[4,11]
        assert q['subject_ref']==a['id'] and q['unit']=='nt'
        assert q['model_unit']==('nt' if program=='blastn' else 'aa')
        values={v['name']:v['value'] for v in obs['measurements']}
        assert values['bitscore']['value']==values['evalue']['value']==0
        assert 'identity_fraction' not in values
        ref=store.get(row['reference_ref'])
        assert ref['sequence_ref'] is None and ref['length']==18 and store.coverage(ref['id'])==[]
        assert response['result']['requested_database']=='nt'
        assert response['result']['effective_search_target']=={'db':'core_nt'}
        assert store.map_segments(a['id'],[{'start':q['start'],'end':q['end']}])==[
            {'target_ref':target['id'],'member_ref':a['member_ref'],'start':2,'end':9,'unit':'nt'}]
        assert project_credit(store).credit==0 and not store.current_annotations()
        assert tools.execute('public.blast.search',{'subject_ref':a['id'],'program':program,'database':'nt'},operation_key='one')==response
        assert [c[0] for c in client.calls]==['submit','status','fetch']


def test_zip_exact_bytes_partial_hsps_export_and_owned_collect(tmp_path):
    client=Client(zipped=True);client.bad=True;client.pending=2
    store,tools,target,(a,b)=setup(tmp_path,client)
    with store:
        result=tools.execute('public.blast.search',{'subject_ref':a['id'],'program':'blastn','database':'core_nt'})
        assert result['status']=='partial',result
        assert result['result']['projected_hsp_count']==1 and len(result['result']['projection_errors'])==1
        assert result['result']['projection_errors'][0]['code']=='blast_hsp_interval_outside_actual_operand'
        source=store.get(result['result']['source_ref'])
        assert store.get_artifact(source['artifact_ref'])==client.json_bytes
        parents=[store.get(ref) for ref in source['parent_source_refs']]
        archive=next(p for p in parents if p['provider']=='ncbi_blast_archive')
        assert store.get_artifact(archive['artifact_ref'])==client.zip_bytes
        meta=json.loads(store.get_artifact(source['request_ref']))
        assert meta['transport']['archive_member']=={'ordinal':1,'name':'one.json'}
        child=tools.execute('library.select',{'library_ref':target['id'],'member_refs':[b['member_ref']]})['result']['scope']
        before=len(client.calls)
        rejected=tools.execute('public.blast.collect',{'job_ref':result['result']['job_ref']},scope=child)
        assert rejected['status']=='invalid' and len(client.calls)==before
        assert rejected['feedback']['code']=='requested_measurement_outside_assigned_segments_or_members'
        export=tmp_path/'export.json'; export_annotation(store,export,include_artifacts=True)
        records={r['id']:r for r in json.loads(export.read_text())['records']}
        assert source['id'] in records and archive['id'] in records and parents[0]['id'] in records
        assert len(tools.remote_searches.jobs(active_only=False))==1


def test_wrong_query_preserves_native_failure_then_recovers_same_job_after_reopen(tmp_path):
    client=Client();client.wrong=True
    store,tools,target,(a,b)=setup(tmp_path,client)
    with store:
        args={'subject_ref':a['id'],'program':'blastn','database':'core_nt'}
        failed=tools.execute('public.blast.search',args,operation_key='same')
        assert failed['status']=='failed' and failed['feedback']['code']=='blast_query_title_conflicts_with_submitted_subject'
        assert failed['feedback']['remote_handle_known'] and failed['feedback']['collectable']
        assert not store.count('observation')
        diagnostic=json.loads(store.get_artifact(failed['feedback']['diagnostic_ref']))
        assert b'wrong_subject' in store.get_artifact(diagnostic['content_ref'])
        job=failed['feedback']['job_ref']
    with Store(tmp_path/'state') as reopened:
        # Same provider handle, with a corrected labelled synthetic response.
        fresh=Client();fresh.subject=a['id']
        registry=ToolRegistry(reopened,clients=fresh,provider_poll_interval_seconds=0)
        result=registry.execute('public.blast.collect',{'job_ref':job})
        assert result['status']=='completed',result
        assert [c[0] for c in fresh.calls]==['status','fetch']
        assert registry.execute('public.blast.search',args,operation_key='same')==failed
        assert registry.remote_searches.describe(job)['cause'] is None


@pytest.mark.parametrize('missing',[False,True])
def test_explicit_empty_hits_and_absent_hits_stay_distinct(tmp_path,missing):
    client=Client(); client.missing=missing; client.empty=not missing
    store,tools,target,(a,b)=setup(tmp_path,client)
    with store:
        response=tools.execute('public.blast.search',{'subject_ref':a['id'],'program':'blastn','database':'nt'})
        assert response['status']=='completed',response
        result=response['result']
        assert result['native_hit_count']==(None if missing else 0)
        assert result['reported_hit_array_empty'] is (not missing)
        assert (result['no_hit_meaning'] is None) is missing
        assert result['records']==[] and store.count('observation')==0 and project_credit(store).credit==0


def test_missing_contact_is_durable_known_not_sent_and_old_rid_paths_removed(tmp_path):
    client=PublicClients(access_dir=tmp_path/'access');client.ncbi_email=None
    store,tools,target,(a,b)=setup(tmp_path,client)
    with store:
        failed=tools.execute('public.blast.search',{'subject_ref':a['id'],'program':'blastn','database':'core_nt'},operation_key='no-contact')
        assert failed['status']=='unavailable' and failed['feedback']['submission_state']=='not_submitted'
        assert failed['feedback']['cause']['submission_outcome']=='not_sent'
        assert not failed['feedback']['collectable']
        assert all(name not in tools.catalog() for name in ['public.blast.submit','public.blast.fetch','public.blast.status'])


@pytest.mark.parametrize("redirect", [False, True])
def test_installed_client_observer_preserves_each_http_entity_and_actual_timing(tmp_path,monkeypatch,redirect):
    """Execute the actual installed client through an in-process HTTP fixture."""
    import contextlib
    import requests
    import subprocess
    import sys
    import time
    from gene_annotation_episode import acquisition
    clock=[1000.]; calls=[]
    query='input_'+'a'*24
    body=json.dumps(native(query)).encode()
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as archive:
        archive.writestr('manifest.json',json.dumps({'BlastJSON':[{'File':'one.json'}]}))
        archive.writestr('one.json',body)
    entities=[b'RID = FIXTURE_RID\nRTOE = 2\n',b'Status=READY\nThereAreHits=yes\n',buffer.getvalue()]
    def http(session,method,url,**kwargs):
        calls.append((method,kwargs))
        assert kwargs['allow_redirects'] is False
        response=requests.Response();response.status_code=302 if redirect else 200
        if redirect: response.headers['Location']='https://example.invalid/never-follow-this-fixture'
        response._content=entities[len(calls)-1]
        response.url=url;response.headers['Content-Type']='application/zip' if len(calls)==3 else 'text/plain'
        response.request=requests.Request(method,url,data=kwargs.get('data'),params=kwargs.get('params')).prepare()
        return response
    # The observer still loads the unmodified installed script. Only its local
    # Session.request transport is replaced; no request leaves this process.
    monkeypatch.setattr(requests.Session,'request',http)
    def run(command,*,input,text,capture_output,timeout):
        previous_args,previous_in=sys.argv,sys.stdin
        stdout=io.StringIO()
        try:
            sys.argv=command[2:];sys.stdin=io.StringIO(input)
            with contextlib.redirect_stdout(stdout):
                exec(compile(command[2],'<installed-blast-observer>','exec'),{'__name__':'__main__'})
        finally:
            sys.argv,sys.stdin=previous_args,previous_in
            monkeypatch.setattr(requests.Session,'request',http)
        return subprocess.CompletedProcess(command,0,stdout.getvalue(),'')
    # Python -c assigns sys.argv[0] to '-c', then the three positional paths.
    launches=[]
    def run_with_argv(command,**kwargs):
        if not launches: clock[0]+=15  # delayed worker, actual HTTP occurs late
        launches.append(command)
        adjusted=[*command]; original=adjusted[2]
        adjusted[2]="import sys; sys.argv=['-c',*sys.argv[1:]]\n"+original
        return run(adjusted,**kwargs)
    monkeypatch.setattr(acquisition.subprocess,'run',run_with_argv)
    monkeypatch.setattr(time,'time',lambda:clock[0])
    client=PublicClients(ncbi_email='fixture@example.invalid',access_dir=tmp_path/'access')
    if redirect:
        with pytest.raises(AcquisitionError,match='provider_redirect_not_followed') as failure:
            client.blast('submit',query_fasta=f'>{query}\nTTACGTAGGGGG',program='blastn',database='nt')
        assert failure.value.snapshot.content==entities[0]
        assert failure.value.snapshot.transport['status']==302
        assert failure.value.snapshot.transport['headers']['Location']=='https://example.invalid/never-follow-this-fixture'
        assert len(calls)==1 and client.blast_delay('submit')==10
        return
    submitted=client.blast('submit',query_fasta=f'>{query}\nTTACGTAGGGGG',program='blastn',database='nt')
    assert submitted.content==entities[0] and len(calls)==1
    assert clock[0]==1015 and client.blast_delay('submit')==10
    with pytest.raises(AcquisitionError,match='provider_spacing_required'):
        client.blast('status',rid='FIXTURE_RID')
    second=PublicClients(ncbi_email='fixture@example.invalid',access_dir=tmp_path/'access')
    with pytest.raises(AcquisitionError,match='provider_spacing_required'):
        second.blast('status',rid='FIXTURE_RID')
    assert len(calls)==1 and second.blast_delay('status','FIXTURE_RID')==10
    clock[0]+=10
    checked=client.blast('status',rid='FIXTURE_RID')
    assert checked.content==entities[1] and client.blast_delay('status','FIXTURE_RID')==60
    assert client.blast_delay('fetch','FIXTURE_RID')==10
    clock[0]+=10
    fetched=client.blast('fetch',rid='FIXTURE_RID')
    assert fetched.content==entities[2] and fetched.media_type=='application/zip'
    assert len(calls)==3  # fetch did not secretly check SearchInfo again.
    assert calls[2][1]['params']['FORMAT_TYPE']=='JSON2'
    assert fetched.transport['representation']=='http_entity_bytes_via_installed_blast_client'
    assert fetched.transport['script_sha256']
    assert client.blast_delay('status','FIXTURE_RID')==50
    assert json.loads((tmp_path/'access/ncbi-blast.json').read_text())['last_request']==clock[0]


def test_accepted_cancelled_search_resumes_one_handle_and_one_runtime_action(tmp_path):
    from test_runtime import FixtureController,ScriptedProvider
    from gene_annotation_episode.runtime import run_workflow
    pending=Client();pending.pending=100
    store,tools,target,(a,b)=setup(tmp_path,pending)
    args={'subject_ref':a['id'],'program':'blastn','database':'core_nt'}
    async def exercise():
        with store:
            tools.remote_searches.poll_interval_seconds=60
            task=asyncio.create_task(tools.execute_async('public.blast.search',args,operation_key='interrupted'))
            while not tools.remote_searches.jobs() or tools.remote_searches.jobs()[0]['remote_id'] is None:
                await asyncio.sleep(.001)
            task.cancel()
            with pytest.raises(asyncio.CancelledError): await task
            assert [c[0] for c in pending.calls].count('submit')==1
        with Store(tmp_path/'state') as reopened:
            fresh=Client();fresh.subject=a['id']
            registry=ToolRegistry(reopened,clients=fresh,provider_poll_interval_seconds=0)
            recovered=await registry.execute_async('public.blast.search',args,operation_key='interrupted')
            assert recovered['status']=='completed',recovered
            assert all(c[0]!='submit' for c in fresh.calls)
            # A separately selected cached collect is one own operation under
            # the actual shared runtime, with no repeated native evidence credit.
            provider=ScriptedProvider([{'selection':{'kind':'tool','tool':'public.blast.collect',
                'arguments':{'job_ref':recovered['result']['job_ref']}},'report_update':{}}])
            result=await run_workflow(reopened,registry,provider=provider,run_dir=tmp_path/'run',
                controller_factory=lambda path,initial:FixtureController(str(path),initial,1))
            assert result['completed_actions']==1 and result['credit']==0
            assert reopened.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==1
    asyncio.run(exercise())


def test_uncertain_submit_never_repeats_and_native_field_requires_trusted_origin(tmp_path):
    class Uncertain(Client):
        def blast(self,action,**kw):
            self.calls.append((action,kw))
            if action=='submit': raise TimeoutError('synthetic possible transmission')
            return super().blast(action,**kw)
    client=Uncertain();store,tools,target,(a,b)=setup(tmp_path,client)
    with store:
        args={'subject_ref':a['id'],'program':'blastn','database':'nt'}
        failed=tools.execute('public.blast.search',args,operation_key='uncertain')
        assert failed['feedback']['submission_state']=='submission_uncertain'
        assert tools.execute('public.blast.collect',{'job_ref':failed['feedback']['job_ref']})['status']=='failed'
        assert [c[0] for c in client.calls]==['submit']
        fresh=Client();registry=ToolRegistry(store,clients=fresh,provider_poll_interval_seconds=0)
        valid=registry.execute('public.blast.search',args)
        observed=store.get(valid['result']['records'][0]['observation_ref'])
        proposed={k:v for k,v in observed.items() if k not in ('id','record_type','origin')}
        with pytest.raises(Exception,match='native_blast_requires_native_tool_source'):
            store.put('observation',proposed,origin='extracted')


def test_reasoned_native_hsp_uses_exact_original_member_extent_and_existing_parent_form(tmp_path):
    from gene_annotation_episode.runtime import Workflow
    client=Client(program='blastx');store,tools,target,(a,b)=setup(tmp_path,client)
    with store:
        result=tools.execute('public.blast.search',{'subject_ref':a['id'],'program':'blastx','database':'swissprot'})
        observation=result['result']['records'][0]['observation_ref']
        selected=tools.execute('library.select',{'library_ref':target['id'],'member_refs':[a['member_ref']]})['result']['scope']
        h=store.put('hypothesis',{'subject_refs':[a['id']],'predicate':'biological_role',
            'value':{'type':'enum','value':'coding'},'context_refs':[]},origin='reasoning',scope=selected)
        assessment=store.put('assessment',{'hypothesis_ref':h['id'],'observation_ref':observation,
            'relation':'strengthens','applicability':'direct','extent_basis':'observed_extent',
            'condition_refs':[],'assumption_refs':[],'expected_revision':0},origin='reasoning',scope=selected)
        account=store.put('annotation',{'subject_ref':a['id'],'footprint_kind':'localized',
            'coherent_sets':[{'interpretations':[{'hypothesis_ref':h['id'],'disposition':'supported',
                'assessment_refs':[assessment['id']]}],'context_refs':[]}], 'alternative_refs':[],
            'resolution':'selected','expected_revision':0},origin='reasoning',scope=selected)
        projection=project_credit(store,details_limit=12)
        assert projection.credit>0
        rows=projection.as_record()['source_contributions']
        assert rows and all(row['target_ref']==target['id'] for row in rows)
        assert all(sum(span['end']-span['start'] for span in row['contributing_segments'])==7 for row in rows)
        workflow=Workflow.__new__(Workflow); workflow.store=store
        resolver=workflow.resolver(selected)
        assert resolver(observation,'observation') and resolver(assessment['id'],'assessment')
        assert resolver(account['id'],'annotation')
        other=tools.execute('library.select',{'library_ref':target['id'],'member_refs':[b['member_ref']]})['result']['scope']
        assert project_credit(store,other).credit==0


@pytest.mark.parametrize('configured',[False,True])
def test_cli_selects_shared_access_directory_once_and_exposes_effective_path(tmp_path,monkeypatch,configured):
    from gene_annotation_episode import cli
    workspace=tmp_path/'workspace'
    with Store(workspace) as store: store.create_problem(raw_sequence='ACGT',molecule='dna')
    home=tmp_path/'home';monkeypatch.setattr(Path,'home',classmethod(lambda cls:home))
    selected=[]
    class Registry:
        def __init__(self,store,*,clients,**kwargs): selected.append(clients.access_dir)
        def catalog(self): return {}
    monkeypatch.setattr(cli,'ToolRegistry',Registry)
    monkeypatch.setattr(cli,'_print',lambda value:None)
    args=['capabilities','--workspace',str(workspace)]
    expected=home/'.cache/gene_annotation_episode/provider_access'
    if configured:
        expected=tmp_path/'explicit_shared'; config=tmp_path/'config.toml'
        config.write_text('[public]\nprovider_access_dir = '+json.dumps(str(expected))+'\n')
        args += ['--config',str(config)]
    assert cli.main(args)==0 and selected==[expected]


def test_optional_invalid_taxonomy_does_not_discard_valid_hsp(tmp_path):
    class BadTaxonomy(Client):
        def blast(self,action,**kw):
            result=super().blast(action,**kw)
            if action=='fetch':
                body=json.loads(result.content)
                hit=body['BlastOutput2'][0]['report']['results']['search']['hits'][0]
                hit['description'][0]['taxid']=0
                hit['description'][0].pop('accession')
                hit['description'][0]['id']='gnl|synthetic|native'
                hit['description'].insert(0,'malformed independent alias metadata')
                return replace(result,content=json.dumps(body).encode())
            return result
    client=BadTaxonomy();store,tools,target,(a,b)=setup(tmp_path,client)
    with store:
        response=tools.execute('public.blast.search',{'subject_ref':a['id'],'program':'blastn','database':'nt'})
        assert response['status']=='partial',response
        assert response['result']['projected_hsp_count']==1
        assert {error['code'] for error in response['result']['projection_errors']}=={'blast_invalid_taxid','blast_hit_description_object_required'}
        row,=response['result']['records']
        assert row['accession_basis']=='source_local_hit'
        taxon_error=next(error for error in response['result']['projection_errors'] if error['code']=='blast_invalid_taxid')
        assert taxon_error['description_ordinal']==1
        assert store.get(row['reference_ref'])['term_refs']==[]
        assert store.get(row['observation_ref'])['native_blast']['hit_coordinate_unit']=='nt'


@pytest.mark.parametrize('body',[b'PK\x03\x04broken native archive',b'{"BlastOutput2":[{"report":{"program":"blastn","results":{"iterations":[]}}}]}'])
def test_uninterpretable_native_shape_retains_bytes_and_same_handle_feedback(tmp_path,body):
    class Malformed(Client):
        def blast(self,action,**kw):
            result=super().blast(action,**kw)
            return replace(result,content=body) if action=='fetch' else result
    client=Malformed();store,tools,target,(a,b)=setup(tmp_path,client)
    with store:
        result=tools.execute('public.blast.search',{'subject_ref':a['id'],'program':'blastn','database':'nt'})
        assert result['status']=='failed' and not result['record_refs']
        assert result['feedback']['remote_handle_known'] and result['feedback']['collectable']
        diagnostic=json.loads(store.get_artifact(result['feedback']['diagnostic_ref']))
        assert store.get_artifact(diagnostic['content_ref'])==body
        assert store.count('observation')==0 and project_credit(store).credit==0


def test_selected_search_with_protocol_wait_is_exactly_one_shared_runtime_observation(tmp_path):
    from test_runtime import FixtureController,ScriptedProvider
    from gene_annotation_episode.runtime import run_workflow
    client=Client();client.pending=2
    store,tools,target,(a,b)=setup(tmp_path,client)
    with store:
        provider=ScriptedProvider([{'selection':{'kind':'tool','tool':'public.blast.search',
            'arguments':{'subject_ref':a['id'],'program':'blastn','database':'nt'}},'report_update':{}}])
        result=asyncio.run(run_workflow(store,tools,provider=provider,run_dir=tmp_path/'run',
            controller_factory=lambda path,initial:FixtureController(str(path),initial,1)))
        assert result['completed_actions']==1 and result['credit']==0
        assert [c[0] for c in client.calls]==['submit','status','status','status','fetch']
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==1
        assert store.count('observation')==1 and not store.current_annotations()


def test_zero_native_frames_remain_integer_source_metadata(tmp_path):
    class ZeroFrames(Client):
        def blast(self,action,**kw):
            response=super().blast(action,**kw)
            if action=='fetch':
                body=json.loads(response.content)
                hsp=body['BlastOutput2'][0]['report']['results']['search']['hits'][0]['hsps'][0]
                hsp.update(query_frame=0,hit_frame=0)
                return replace(response,content=json.dumps(body).encode())
            return response
    client=ZeroFrames(program='blastp');store,tools,target,(a,b)=setup(tmp_path,client)
    with store:
        result=tools.execute('public.blast.search',{'subject_ref':a['id'],'program':'blastp','database':'swissprot'})
        assert result['status']=='completed',result
        obs=store.get(result['result']['records'][0]['observation_ref'])
        assert obs['native_blast']['query_frame']==obs['native_blast']['hit_frame']==0
        assert 'native_blast' not in store.reasoning_schema()['properties']['observations']['items']['properties']
        from gene_annotation_episode.domain import RECORD_SCHEMAS
        assert 'native_blast' in RECORD_SCHEMAS['observation']['properties']


def test_inferred_transfer_keeps_source_without_sequence_and_runtime_credit_read_works(tmp_path):
    from test_runtime import FixtureController,ScriptedProvider
    from gene_annotation_episode.runtime import run_workflow
    client=Client(program='blastx');store,tools,target,(a,b)=setup(tmp_path,client)
    with store:
        search=tools.execute('public.blast.search',{'subject_ref':a['id'],'program':'blastx','database':'swissprot'})
        observation=search['result']['records'][0]['observation_ref']
        reference=search['result']['records'][0]['reference_ref']
        scope=tools.execute('library.select',{'library_ref':target['id'],'member_refs':[a['member_ref']]})['result']['scope']
        h=store.put('hypothesis',{'subject_refs':[a['id']],'predicate':'biological_role',
            'value':{'type':'enum','value':'coding'},'context_refs':[]},origin='reasoning',scope=scope)
        assessed=store.put('assessment',{'hypothesis_ref':h['id'],'observation_ref':observation,'relation':'strengthens',
            'applicability':'transfer','extent_basis':'inferred_extent','target_footprint':[
                {'target_ref':target['id'],'member_ref':a['member_ref'],'start':2,'end':9,'unit':'nt'}],
            'condition_refs':[],'assumption_refs':[],'expected_revision':0},origin='reasoning',scope=scope)
        store.put('annotation',{'subject_ref':a['id'],'footprint_kind':'localized','coherent_sets':[
            {'interpretations':[{'hypothesis_ref':h['id'],'disposition':'supported','assessment_refs':[assessed['id']]}],
             'context_refs':[]}],'alternative_refs':[],'resolution':'selected','expected_revision':0},origin='reasoning',scope=scope)
        assert store.has_exact_mapping(a['id']) and store.has_exact_mapping(reference) is False
        assert tools.execute('sequence.inspect',{'subject_ref':reference})['feedback']['code']=='referenced_record_has_no_sequence'
        projected=project_credit(store,scope,details_limit=20)
        assert projected.credit>0
        row,=projected.as_record()['source_contributions']
        query_path,reference_path=row['source_operand_mappings']
        assert query_path['mapping_status']=='exact_physical_source_path'
        assert reference_path['mapping_status']=='subregion_mapping_unavailable'
        assert reference_path['operand_interval']['subject_ref']==reference
        assert reference_path['operand_interval']['start']==4 and reference_path['operand_interval']['end']==11
        assert store.get(reference)['length']==18 and store.get(reference)['sequence_ref'] is None
        provider=ScriptedProvider([{'selection':{'kind':'tool','tool':'episode.credit',
            'arguments':{'limit':20,'offset':0}},'report_update':{}}])
        summary=asyncio.run(run_workflow(store,tools,provider=provider,run_dir=tmp_path/'run',
            controller_factory=lambda path,initial:FixtureController(str(path),initial,1)))
        assert summary['completed_actions']==1 and summary['credit']>0
        action=store.db.execute('SELECT result FROM runtime_actions WHERE result IS NOT NULL').fetchone()
        outcome=json.loads(action[0])
        assert outcome['status']=='completed' and outcome['result']['source_contributions']
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==1


@pytest.mark.parametrize('program',['blastx','tblastn','tblastx'])
def test_coherent_six_nt_two_aa_reverse_translated_geometry(tmp_path,program):
    class Coherent(Client):
        def blast(self,action,**kw):
            result=super().blast(action,**kw)
            if action=='fetch':
                body=json.loads(result.content)
                hsp=body['BlastOutput2'][0]['report']['results']['search']['hits'][0]['hsps'][0]
                for key in ['query_strand','hit_strand','query_frame','hit_frame']:
                    hsp.pop(key,None)
                # Physical nt interval [2,8) translates to two aligned residues.
                # The DNA query substring ACGTAG reverse-complements to CTACGT,
                # whose two codons encode LR; a protein query has actual LR at3..4.
                hsp.update(query_from=3 if program=='tblastn' else 8,
                    query_to=4 if program=='tblastn' else 3,
                    hit_from=3 if program=='blastx' else 8,
                    hit_to=4 if program=='blastx' else 3,
                    qseq='LR',hseq='LR',align_len=2,identity=2,gaps=0)
                if program!='tblastn': hsp['query_frame']=-2
                if program!='blastx': hsp['hit_frame']=-2
                return replace(result,content=json.dumps(body).encode())
            return result
    with Store(tmp_path/'state') as store:
        molecule='protein' if program=='tblastn' else 'dna'
        problem=store.create_problem(raw_sequence='MALRQQQQQQQQ' if molecule=='protein' else 'TTACGTAGGGGG',molecule=molecule)
        subject=problem['subject_refs'][0]
        client=Coherent(program=program);tools=ToolRegistry(store,clients=client,provider_poll_interval_seconds=0)
        result=tools.execute('public.blast.search',{'subject_ref':subject,'program':program,'database':'synthetic_db'})
        assert result['status']=='completed',result
        observation=store.get(result['result']['records'][0]['observation_ref'])
        q,r=observation['operand_intervals']; native_fields=observation['native_blast']
        assert [q['start'],q['end']]==([2,4] if program=='tblastn' else [2,8])
        assert q['unit']==('aa' if program=='tblastn' else 'nt') and q['model_unit']=='aa'
        assert [r['start'],r['end']]==([2,4] if program=='blastx' else [2,8])
        assert r['model_unit']=='aa'
        assert native_fields['query_coordinate_unit']==('aa' if program=='tblastn' else 'nt')
        assert native_fields['hit_coordinate_unit']==('aa' if program=='blastx' else 'nt')
        if program!='tblastn': assert native_fields['query_from']>native_fields['query_to'] and native_fields['query_frame']==-2
        if program!='blastx': assert native_fields['hit_from']>native_fields['hit_to'] and native_fields['hit_frame']==-2
        mapped,=store.map_segments(subject,[{'start':q['start'],'end':q['end']}])
        assert mapped['end']-mapped['start']==(2 if program=='tblastn' else 6)
        assert store.get(result['result']['records'][0]['reference_ref'])['sequence_ref'] is None
