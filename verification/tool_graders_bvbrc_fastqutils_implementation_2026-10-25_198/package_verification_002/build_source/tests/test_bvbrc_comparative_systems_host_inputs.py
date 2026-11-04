"""Real Data and AppService custodians, explicit inputs and honest source identity."""
import asyncio
from copy import deepcopy
import json
import hashlib

import pytest
from gene_annotation_episode.api_bvbrc import DATA_QUERY_OPERATION, DATA_RESULT_OPERATION
from gene_annotation_episode.bvbrc_comparative_systems_host_inputs import collect_comparative_systems_inputs, _SelectedDataHost, _materialize_producers
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.state import Store
from gene_annotation_episode.acquisition import SourceSnapshot
from test_bvbrc_comparative_systems_bundle import arguments
from test_bvbrc_comparative_systems_episode_flow import ComparativeDriver, requested_form, parameters, FIXTURES


def data_selector():
    return {'version':'bvbrc_data_result_selector_v2','page':None,'projection':{'family':'query_metadata'},
        'inputs':[],'supplied_metadata':[]}


def snapshot(prepared,body):
    native=prepared['native_request']
    return SourceSnapshot('bvbrc_data',native['url'],deepcopy(prepared['effective_request']),
        '2026-10-24T20:00:00+00:00',body,'application/solr+json',{
            'status':200,'body_complete':True,'automatic_redirects':False,'effective_url':native['url'],
            'request':{key:deepcopy(native[key]) for key in ('method','url','headers','body')},'header_items':[]})


def execute(d, context, name):
    key = f'{context.run_id}:{context.episode_id}:0'
    action = {'kind':'tool','tool':name,'arguments':{}}
    d.saved.journal.save('runtime_actions', {'episode_id':context.episode_id,'decision_index':0,
        'action':canonical(action),'result':None,'credit':None})
    outcome = asyncio.run(d.api.execute(context, name, {}, key))
    assert outcome['status'] in {'completed','partial'}, outcome
    d.saved.journal.save('runtime_actions', {'episode_id':context.episode_id,'decision_index':0,
        'action':canonical(action),'result':canonical(outcome),'credit':0})
    d.saved.receipts.receive(context.episode_id,outcome['record_refs'],kind='own_action',source_index=0)
    return outcome


def data_input(d, monkeypatch):
    case = arguments()
    template = case['qualified_data_inputs'][0]
    query = deepcopy(template['qualified_result']['grading']['prepared']['original_request'])
    raw = case['artifact_bytes'][template['raw_binding']['bytes_key']]
    calls = []
    def response(client, prepared):
        calls.append(deepcopy(prepared))
        return snapshot(prepared, raw)
    monkeypatch.setattr('gene_annotation_episode.api_bvbrc.BVBRCDataClient.query_prepared', response)
    assignment = {'version':'api_service_assignment_v1','resource_id':'data','service':'bvbrc_data',
        'request':query,'endpoint':'usable_handoff','constraints':{}}
    launch = d.saved.child(d.parent,'launch',{'version':'execution_launch_assignment_v1',
        'requests':{'data':assignment},'immutable_input_versions':[],'constraints':{}},0)
    child = d.saved.child(launch,'launch_api',assignment,0)
    handed = execute(d,child,DATA_QUERY_OPERATION)
    handoff = handed['result']['handoff_ref']
    d.freeze_refs(launch,child,[handoff])
    d.freeze_refs(d.parent,launch,[handoff])
    results = d.saved.child(d.parent,'results',{'version':'execution_results_assignment_v1',
        'handoff_ref':handoff,'selector':data_selector()},1)
    acquired = execute(d,results,DATA_RESULT_OPERATION)
    reference = acquired['result']['source_ref']
    d.freeze_refs(d.parent,results,[reference])
    qualified = d.api.bvbrc_data.read(reference,context=d.parent)
    content = d.content(reference)
    selection = deepcopy(case['parameters']['supplied_data_selection'])
    row, = selection['record_sets']
    row['source_refs'] = [reference]
    row['query_population_key'] = qualified['grading']['prepared']['query_population']['population_key']
    for loc in row['snapshot_evidence']['source_locations']:
        loc.update(source_ref=reference,raw_artifact_ref=content['artifact_ref'])
    d.selected['adapter']['parameters']['supplied_data_selection'] = selection
    d.selected['supplied_contents'].append(content)
    d.data_qualified,d.data_content,d.data_raw,d.data_calls = qualified,content,raw,calls
    producer_input(d)


def producer_input(d):
    commit = '670b3b6dd09509ebc62fb6f1b1caf3e38c33bd33'
    repository = 'https://github.com/BV-BRC/comparative_systems_service'
    raw = (FIXTURES/'compare_systems_lib.py.txt').read_bytes()
    code = d.saved.source(raw,uri=repository+'/blob/'+commit+'/lib/compare_systems_lib.py')
    d.saved.own(d.parent,code['source_ref'],index=2)
    evidence = {'evidence_id':'examined_source','identity_kind':'source_examined','repository_url':repository,
        'commit':commit,'source_sha256':hashlib.sha256(raw).hexdigest(),'runtime_version':None,
        'dependency_version':None,'reference_release':None,'source_locations':[{
            'source_ref':code['source_ref'],'raw_artifact_ref':code['artifact_ref'],'document_id':None,
            'json_pointer':'','table':None,'row_ordinal':None,'column_ordinal':None,'native_field':None}]}
    content = d.saved.source(canonical({'producer':evidence}).encode(),accession='retained-source-description')
    d.saved.own(d.parent,content['source_ref'],index=3)
    selection = {'evidence_id':'examined_source','source_ref':content['source_ref'],
        'raw_artifact_ref':content['artifact_ref'],'record_path':'/producer'}
    d.selected['adapter']['parameters']['producer_evidence_selections'] = [selection]
    d.selected['adapter']['parameters']['document_selection']['documents'][0]['producer_evidence_id']='examined_source'
    d.selected['supplied_contents'].append(code)
    d.selected['supplied_metadata'].append({'content':content,'pointer':'/producer'})
    # Explicitly retained false claims remain available for hostile selection
    # tests; they cannot attest any producing execution or remote task.
    d.false_producers=[]
    for index,kind in enumerate(('source_executed','deployed_attested'),4):
        false=deepcopy(evidence)
        false['identity_kind']=kind
        value=d.saved.source(canonical({'producer':false}).encode(),accession='false-'+kind)
        d.saved.own(d.parent,value['source_ref'],index=index)
        d.selected['supplied_metadata'].append({'content':value,'pointer':'/producer'})
        d.false_producers.append({**selection,'source_ref':value['source_ref'],'raw_artifact_ref':value['artifact_ref']})
    d.producer_evidence=evidence


def collect(d, body=None):
    body = d.body if body is None else body
    receipt = d.records.read(body['bundle']['acquisition_receipt_refs'][-1])
    return collect_comparative_systems_inputs(d.api.appservice.publications,d.context,
        body['publication_inputs'],body['bundle'],current_acquisition=receipt)


def test_actual_data_read_supplies_exact_retained_bytes_and_rejects_false_wrappers(tmp_path,monkeypatch):
    def forbidden(*args,**kwargs): raise AssertionError('controlled host test attempted live network')
    monkeypatch.setattr('socket.create_connection',forbidden)
    with Store(tmp_path/'state') as store:
        d=ComparativeDriver(store,tmp_path,resources={'data':{'kind':'api','service':'bvbrc_data'}})
        d.start(form=requested_form(False),prepare_parent=lambda d:data_input(d,monkeypatch))
        d.acquire_manifest()
        d.acquire_native()
        qualified,producers,raw=collect(d)
        assert len(d.data_calls)==1 and len(producers)==1
        assert producers[0]['evidence']==d.producer_evidence
        assert producers[0]['qualification']['basis']=='source_only'
        assert producers[0]['qualification']['original_task_ref'] is None
        assert any(row['code']=='producer_version_unverified' for row in d.sheet['diagnostics'])
        assert len(qualified)==1
        value=qualified[0]
        assert value['qualified_result']['binding']==d.data_qualified['binding']
        assert value['qualified_result']['host_qualification']['possession_basis']=='parent_assignment'
        assert raw[value['raw_binding']['bytes_key']]==d.data_raw
        assert value['raw_binding']['source_ref']==d.data_content['source_ref']
        assert value['raw_binding']['byte_count']==len(d.data_raw)
        assert d.sheet['supplied_record_sets']['record_sets'][0]['rows']
        # Metadata wrappers do not bypass original Data publication authentication.
        fake=d.saved.source(canonical(d.data_qualified).encode(),accession='fabricated-qualified-result')
        d.saved.own(d.parent,fake['source_ref'],index=6)
        with pytest.raises(ValueError): _SelectedDataHost(d.api).read(fake['source_ref'],context=d.parent)
        with pytest.raises(ValueError,match='reference_not_received'):
            _SelectedDataHost(d.api).read(d.data_content['source_ref'],context=d.grandparent)
        original=d.body
        for change in ('parameters','source','bytes','pointer','pin','task','raw_binding'):
            altered=deepcopy(original)
            if change=='parameters': altered['publication_inputs']['adapter']['parameters']['reference_memberships']=[] if parameters()['reference_memberships'] else [{'invented':True}]
            elif change=='source': altered['publication_inputs']['selector']['supplied_contents'][0]['source_ref']=fake['source_ref']
            elif change=='bytes': altered['bundle']['supplied_contents'][0]['sha256']='0'*64
            elif change=='pointer': altered['bundle']['supplied_scientific_metadata'][0]['pointer']='/invented'
            elif change=='pin': altered['publication_inputs']['adapter_implementation_sha256']='0'*64
            elif change=='task': altered['bundle']['original_task']['task_id']='other'
            else: altered['bundle']['supplied_contents'][0]['artifact_ref']=fake['artifact_ref']
            with pytest.raises(ValueError): collect(d,altered)
        all_bindings=[*d.body['bundle']['supplied_contents'],*(row['content'] for row in d.body['bundle']['supplied_scientific_metadata'])]
        receipt=d.records.read(d.body['bundle']['acquisition_receipt_refs'][-1])
        index=int(receipt['value']['origin']['operation_key'].rsplit(':',1)[1])
        for selected in d.false_producers:
            altered=deepcopy(d.selected['adapter']['parameters'])
            altered['producer_evidence_selections']=[selected]
            with pytest.raises(ValueError,match='producer_execution_attestation_unbound'):
                _materialize_producers(d.api.appservice.publications,d.context,altered,d.body['bundle'],all_bindings,raw,index)
        before=store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0]
        assert collect(d)[0]==qualified
        assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0]==before
