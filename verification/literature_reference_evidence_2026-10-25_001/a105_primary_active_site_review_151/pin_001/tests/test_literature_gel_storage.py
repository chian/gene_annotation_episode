"""Constructed original-image/Store fixtures, including manual runtime rows.

These tests establish repository custody and projection behavior. Inserted runtime
rows do not establish actual selected LiteratureEpisodes or model interpretation.
"""
from copy import deepcopy as cp
from dataclasses import replace
import json
import sqlite3
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.state import Store
from gene_annotation_episode import literature_gel_storage as storage
from gene_annotation_episode import literature_gel_inputs as inputs
from gene_annotation_episode import literature_gel_calculations as calculations
from test_literature_gel_inputs import make_case, select_v2


def source(store, data, *, parents=()):
    artifact=store.artifact(data)
    return store.put('source',{'provider':'constructed_gel_fixture','accession':None,'uri':None,
        'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,'version':None,
        'retrieved_at':None,'parent_source_refs':list(parents)},origin='caller')['id']


def native_case(path, *, alternatives=False, v2=True, assignment=None):
    store=Store(path);store.create_problem(raw_sequence='MKWAA',molecule='protein')
    selected,_,sources,_,comparison=make_case()
    caption=source(store,sources[('source_caption','text')]['content'])
    image=source(store,sources[('source_image','original')]['content'],parents=[caption])
    selected['image'].update(source_ref=image,artifact_ref=store.get(image)['artifact_ref'])
    for witness in inputs._witnesses(selected):witness['source_ref']=caption
    if v2:select_v2(selected)
    if alternatives:
        alternate=cp(selected['roi_assignments'][0]);alternate['assignment_id']='same:region / α'
        selected['roi_assignments'].append(alternate)
    assignment=assignment or {'requested_gel_components':['direct_competitor_sensitive_shift'],
        'requested_gel_views':['comparison']}
    scope=store.validate_scope()
    request={'goal':{'goal_id':'constructed-runtime-fixture'},'message':{
        'scope':plain(scope),'episode_assignment':assignment},'report_contract':None}
    context=BindingContext('gel-fixture-run','gel-fixture-child','literature',
        (('literature','gel-fixture-parent'),('literature','gel-fixture-child')),
        scope,assignment,request,(image,caption))
    return store,context,{'selection':selected,'comparison':comparison}


def repository(store,context):
    return storage.LiteratureGelRepository(store,context.run_id,evidence_origin='synthetic_fixture')


def owned(context,outcome):
    return replace(context,received_record_refs=(*context.received_record_refs,*outcome['record_refs']))


def runtime_case(path, *, completed=True, **kwargs):
    store,context,args=native_case(path,**kwargs);journal=Journal(store,context.run_id)
    journal.save('runtime_episodes',{'episode_id':context.episode_id,'path':canonical(context.path),
        'request':canonical(plain(context.request)),'initial_credit':0,'state':'active','completion':None,'archive':None})
    action={'kind':'tool','tool':storage.OPERATION,'arguments':args}
    journal.save('runtime_actions',{'episode_id':context.episode_id,'decision_index':4,
        'action':canonical(action),'result':None,'credit':None,'timing':None})
    repo=repository(store,context);key=context.run_id+':'+context.episode_id+':4'
    outcome=repo.populate(context,args,key)
    result={**outcome,'pending_work_after_action':{'constructed_original_snapshot':True}}
    if completed:
        journal.save('runtime_actions',{'episode_id':context.episode_id,'decision_index':4,
            'action':canonical(action),'result':canonical(result),'credit':None,'timing':None})
    return store,owned(context,outcome),args,repo,outcome,journal,action,result


def forbid_reexecution(monkeypatch):
    def forbidden(*a,**k):pytest.fail('scientific reexecution during saved access')
    for module,names in ((inputs,('read_gel_inputs','validate_gel_extraction','_decode')),
                         (calculations,('populate_gel_components','validate_gel_sheet'))):
        for name in names:monkeypatch.setattr(module,name,forbidden)


def test_original_image_exact_rows_methods_and_original_scientific_ids(tmp_path):
    store,context,args=native_case(tmp_path,alternatives=True)
    try:
        repo=repository(store,context);outcome=repo.populate(context,args,'engineering');ref=outcome['result']['sheet_ref']
        saved=repo.read(ref);rows=outcome['result']['cells']
        Draft202012Validator.check_schema(storage.gel_cells_schema())
        Draft202012Validator(storage.gel_cells_schema()).validate(rows)
        direct=[r for r in rows if r['view']=='comparison' and r['component']=='direct_competitor_sensitive_shift']
        assert [r['component_key'] for r in direct]==['comparison:declared:direct_competitor_sensitive_shift',
            'comparison:same%3Aregion%20%2F%20%CE%B1:direct_competitor_sensitive_shift']
        assert all(r['cell']['exact']=={'numerator':'3','denominator':'5'} for r in direct)
        assert direct[0]['cell']['value']==pytest.approx(.6)
        assert [l['observation_id'] for l in direct[0]['scientific_context']['lanes']]==[
            'observation_baseline','observation_protein','observation_competitor']
        assert all(m['background_method']=='mean' and m['method_basis']=='explicit_v2_nomination' for m in direct[0]['roi_methods'])
        raw=next(r for r in rows if r['component_key']=='raw:declared:protein:band:shifted:sum_darkness')
        assert type(raw['cell']['value']) is int and raw['cell']['value']==80
        assert saved['extraction']['origin']=='synthetic'
        bindings=repo.semantic_bindings(direct[:1])
        for binding in bindings[ref].values():assert store.get(binding['record_ref'])['record_type']=='reference'
        assert repo.requested_component_keys(ref,{})==[]
        assert repo.requested_component_keys(ref,context.assignment)==[r['component_key'] for r in direct]
        assert not store.list('observation')
        with pytest.raises(ContractError,match='original_runtime_required'):
            repo.fact_cells(owned(context,outcome),[ref],components=[direct[0]['component_key']])
    finally:store.close()


def test_names_views_and_exact_keys_do_not_grant_other_alternatives(tmp_path):
    store,context,args=native_case(tmp_path,alternatives=True)
    try:
        repo=repository(store,context);outcome=repo.populate(context,args,'engineering');ref=outcome['result']['sheet_ref']
        request={'requested_gel_components':['direct_competitor_sensitive_shift'],'requested_gel_views':['sensitivity']}
        assert repo.requested_component_keys(ref,request)==['sensitivity:direct_competitor_sensitive_shift']
        assert repo.project_cells([ref],permitted_record_refs=[ref],components=['sensitivity:direct_competitor_sensitive_shift'])[0]['cell']['lower']=={'numerator':'3','denominator':'5'}
        for keys in (['comparison:declared:direct_competitor_sensitive_shift'],['missing'],[True]):
            with pytest.raises(ContractError):repo.requested_component_keys(ref,{**request,'requested_gel_component_keys':keys})
        request['requested_gel_views']=['comparison'];request['requested_gel_component_keys']=['comparison:declared:direct_competitor_sensitive_shift']
        assert repo.requested_component_keys(ref,request)==request['requested_gel_component_keys']
    finally:store.close()


def test_invalid_comparison_and_missing_authorization_fail_before_source_bytes(tmp_path,monkeypatch):
    store,context,args=native_case(tmp_path)
    try:
        repo=repository(store,context)
        monkeypatch.setattr(repo,'_bytes',lambda *_:pytest.fail('bytes opened before complete input validation'))
        bad=cp(args);bad['comparison']['protein_lane_id']='absent'
        with pytest.raises(ContractError):repo.populate(context,bad,'bad-comparison')
        denied=replace(context,received_record_refs=context.received_record_refs[:1])
        with pytest.raises(ContractError):repo.populate(denied,args,'denied-caption')
        assert not store.db.execute('SELECT 1 FROM literature_gel_operations').fetchall()
    finally:store.close()


def test_missing_background_and_baseline_preserve_valid_partial_rows(tmp_path):
    store,context,args=native_case(tmp_path)
    try:
        args['comparison']['baseline_lane_id']=None
        args['selection']['roi_assignments'][0]['lanes'][0]['background']=None
        repo=repository(store,context);outcome=repo.populate(context,args,'partial')
        rows={r['component_key']:r for r in outcome['result']['cells']}
        assert rows['raw:declared:baseline:band:free:sum_darkness']['cell']['value']==100
        assert rows['lane:declared:baseline:display_black_pixel_fraction']['cell']['value']==0
        assert rows['corrected:declared:baseline:free']['cell']['value'] is None
        assert rows['comparison:declared:direct_competitor_sensitive_shift']['cell']['value']==pytest.approx(.6)
        assert rows['comparison:declared:factorized_competitor_sensitive_shift']['cell']['value'] is None
        assert repo.read(outcome['result']['sheet_ref'])
    finally:store.close()


def test_prejournal_crash_replay_then_full_runtime_binding(tmp_path,monkeypatch):
    store,context,args,repo,outcome,journal,action,result=runtime_case(tmp_path,completed=False)
    try:
        ref=outcome['result']['sheet_ref'];key='comparison:declared:direct_competitor_sensitive_shift'
        assert repo.read(ref)
        with pytest.raises(ContractError,match='runtime_uncommitted'):repo.fact_cells(context,[ref],components=[key])
        forbid_reexecution(monkeypatch)
        assert repo.populate(context,args,context.run_id+':'+context.episode_id+':4')==outcome
        journal.save('runtime_actions',{'episode_id':context.episode_id,'decision_index':4,
            'action':canonical(action),'result':canonical(result),'credit':None,'timing':None})
        cells=repo.fact_cells(context,[ref],components=[key]);repo.validate_fact_values(context,cells)
        assert cells[0]['cell']['value']==pytest.approx(.6)
        assert store.db.execute('SELECT count(*) FROM literature_gel_runtime_bindings').fetchone()[0]==1
    finally:store.close()


def test_readonly_first_projection_and_native_binding_replay(tmp_path,monkeypatch):
    store,context,args,repo,outcome,*_=runtime_case(tmp_path)
    try:
        ref=outcome['result']['sheet_ref'];key='comparison:declared:direct_competitor_sensitive_shift'
        forbid_reexecution(monkeypatch);store.db.execute('PRAGMA query_only=1');before=store.db.total_changes
        assert repo.project_cells([ref],permitted_record_refs=[ref],components=[key])
        with pytest.raises(ContractError,match='runtime_binding_unavailable'):repo.fact_cells(context,[ref],components=[key])
        assert store.db.total_changes==before
        store.db.execute('PRAGMA query_only=0');cells=repo.fact_cells(context,[ref],components=[key])
        store.db.execute('PRAGMA query_only=1');before=store.db.total_changes
        detached=storage.LiteratureGelRepository(store,context.run_id,evidence_origin='synthetic_fixture',expected_descriptor=repo.descriptor())
        assert detached.fact_cells(context,[ref],components=[key])==cells
        assert store.db.total_changes==before
    finally:store.close()


@pytest.mark.parametrize('mutation',['pending','action','context','cell'])
def test_original_completed_runtime_tamper_is_rejected(tmp_path,mutation):
    store,context,args,repo,outcome,journal,action,result=runtime_case(tmp_path)
    try:
        ref=outcome['result']['sheet_ref'];key='comparison:declared:direct_competitor_sensitive_shift'
        repo.fact_cells(context,[ref],components=[key])
        if mutation=='pending':result['pending_work_after_action']={'constructed_original_snapshot':False}
        elif mutation=='action':action['arguments']['comparison']['baseline_lane_id']=None
        elif mutation=='cell':result['result']['cells'][0]['cell']['value']=700
        else:
            request=plain(context.request);request['message']['episode_assignment']['extra']='rewrite'
            store.db.execute('UPDATE runtime_episodes SET request=?',(canonical(request),))
        if mutation!='context':journal.save('runtime_actions',{'episode_id':context.episode_id,'decision_index':4,
            'action':canonical(action),'result':canonical(result),'credit':None,'timing':None})
        with pytest.raises(ContractError,match='runtime_'):repo.read(ref)
    finally:store.close()


def test_unknown_conflicting_meanings_and_schema_relationships_survive(tmp_path):
    store,context,args=native_case(tmp_path,v2=False)
    try:
        args['selection']['context']['organism']={'state':'unknown','value':None,'witnesses':[]}
        args['selection']['context']['genotype'].update(state='conflicting',value=None)
        args['selection']['lanes'][1]['condition'].update(state='conflicting',value=None)
        repo=repository(store,context);outcome=repo.populate(context,args,'states')
        row=next(r for r in outcome['result']['cells'] if r['view']=='comparison')
        assert row['scientific_context']['global']['organism']=={'state':'unknown','value_ref':None,'witness_refs':[]}
        assert row['scientific_context']['global']['genotype']['state']=='conflicting'
        assert row['scientific_context']['global']['genotype']['witness_refs']
        assert row['scientific_context']['interpretation']['status']=='conflicting'
        assert all(m['method_basis']=='v1_mean_definition' for m in row['roi_methods'])
        bad=cp(row);bad['scientific_context']['global']['organism']['state']='known'
        with pytest.raises(ContractError):repo.validate_returned_values([bad],permitted_record_refs=[row['sheet_ref']])
        bad=cp(row);bad['cell']['value']=True
        with pytest.raises(ContractError):repo.validate_returned_values([bad],permitted_record_refs=[row['sheet_ref']])
    finally:store.close()


def seed_admission(store,context,outcome,cells,*,child_id=None):
    """Manually seeded ordinary typed-form records, not actual episode proof."""
    child_id=child_id or context.episode_id
    parent=replace(context,episode_id='gel-fixture-parent',path=context.path[:-1],assignment={})
    contract={'decision':'Requested gel fixture quantities','measurements':{'schema':{
        'type':'object','properties':{'quantities':storage.gel_cells_schema()},
        'required':['quantities'],'additionalProperties':False}}}
    child_request={'message':{'scope':plain(context.scope),'episode_assignment':plain(context.assignment)},
        'report_contract':contract}
    parent_request={'message':{'scope':plain(parent.scope),'episode_assignment':{}}}
    journal=Journal(store,context.run_id)
    for ctx,request in ((context,child_request),(parent,parent_request)):
        journal.save('runtime_episodes',{'episode_id':ctx.episode_id,'path':canonical(ctx.path),
            'request':canonical(request),'initial_credit':0,'state':'closed','completion':None,'archive':None})
    if child_id!=context.episode_id:
        journal.save('runtime_episodes',{'episode_id':child_id,
            'path':canonical([*context.path[:-1],[context.role,child_id]]),'request':canonical(child_request),
            'initial_credit':0,'state':'closed','completion':None,'archive':None})
    request=json.loads(store.get_artifact(store.get(outcome['result']['sheet_ref'])['request_ref']))
    journal.save('runtime_actions',{'episode_id':context.episode_id,'decision_index':4,
        'action':canonical({'kind':'tool','tool':storage.OPERATION,'arguments':request['arguments']}),
        'result':canonical({**outcome,'pending_work_after_action':{'constructed_fixture':True}}),'credit':None,'timing':None})
    journal.save('runtime_report_attempts',{'parent_episode_id':parent.episode_id,'decision_index':12,
        'delivery_ref':'constructed-gel-delivery','child_episode_id':child_id,'contract':canonical(contract),
        'form':canonical({'quantities':cells}),'failure':None,'timing_receipts':None})
    receipts=EpisodeReceipts(store,context.run_id);receipts.bind(parent.episode_id);receipts.bind(child_id,parent.episode_id)
    receipts.receive(child_id,outcome['record_refs'],kind='own_action')
    return replace(parent,request=parent_request),context.run_id+':'+parent.episode_id+':12:typed_form'


def test_actual_admitted_subset_replays_readonly_without_expansion_or_mutation(tmp_path,monkeypatch):
    store,context,args=native_case(tmp_path,alternatives=True)
    try:
        repo=repository(store,context);outcome=repo.populate(context,args,context.run_id+':'+context.episode_id+':4')
        ref=outcome['result']['sheet_ref']
        cells=[r for r in outcome['result']['cells'] if r['component_key']=='comparison:declared:direct_competitor_sensitive_shift']
        parent,key=seed_admission(store,context,outcome,cells)
        repo.receive_cells(parent,cells,key)
        assert repo.received_cells(parent)==cells
        possessed=replace(parent,received_record_refs=tuple(repo.cell_record_refs(cells)))
        assert repo.fact_cells(possessed,[ref],components=outcome['result']['component_keys'])==cells
        before=store.db.total_changes;repo.receive_cells(parent,cells,key);assert store.db.total_changes==before
        with pytest.raises(ContractError):repo.receive_cells(parent,outcome['result']['cells'],key)
        forbid_reexecution(monkeypatch);store.db.execute('PRAGMA query_only=1');before=store.db.total_changes
        assert repo.received_cells(parent)==cells
        assert repo.fact_cells(possessed,[ref],components=outcome['result']['component_keys'])==cells
        assert store.db.total_changes==before
        store.db.execute('PRAGMA query_only=0')
        store.db.execute('UPDATE runtime_report_attempts SET form=?',(canonical({'quantities':cells,'unrelated':'forged'}),))
        with pytest.raises(ContractError,match='binding_mismatch'):repo.received_cells(parent)
    finally:store.close()


def test_manual_admission_and_reporting_sibling_are_rejected(tmp_path):
    store,context,args=native_case(tmp_path)
    try:
        repo=repository(store,context);outcome=repo.populate(context,args,context.run_id+':'+context.episode_id+':4')
        cells=[r for r in outcome['result']['cells'] if r['component_key']=='comparison:declared:direct_competitor_sensitive_shift']
        with pytest.raises(ContractError,match='runtime_admission_required'):repo.receive_cells(context,cells,'manual-proof')
        parent,key=seed_admission(store,context,outcome,cells,child_id='gel-fixture-sibling')
        with pytest.raises(ContractError,match='not_received'):repo.receive_cells(parent,cells,key)
        assert not store.db.execute('SELECT 1 FROM literature_gel_component_received').fetchone()
    finally:store.close()


def test_coordinated_resigning_private_payload_cannot_replace_original_runtime(tmp_path):
    store,context,args,repo,outcome,*_=runtime_case(tmp_path)
    try:
        ref=outcome['result']['sheet_ref'];saved=repo.read(ref);record=store.get(ref)
        saved['sheet']['assignments'][0]['cells']['direct_competitor_sensitive_shift']['value']=.91
        saved['sheet']['sheet_digest']=inputs._hash(inputs._canonical({k:v for k,v in saved['sheet'].items() if k!='sheet_digest'}))
        artifact=store.artifact(canonical(saved),'application/json')
        body={k:v for k,v in record.items() if k not in ('id','record_type','origin')}
        body.update(artifact_ref=artifact,text_ref=artifact)
        forged_ref=store.put('source',body,origin='tool')['id']
        forged=cp(outcome);forged['result'].update(sheet_ref=forged_ref,payload_sha256=storage._sha(saved),
            cells=storage._component_rows(saved,forged_ref))
        for field in ('record_refs','changed_record_refs'):forged[field]=[forged_ref if r==ref else r for r in forged[field]]
        store.db.execute('UPDATE literature_gel_operations SET outcome=?',(canonical(forged),))
        with pytest.raises(ContractError,match='original_runtime_mismatch'):repo.read(forged_ref)
    finally:store.close()


def test_fresh_process_sqlite_readonly_projection_forbids_original_bytes_and_calculators(tmp_path):
    store,context,args=native_case(tmp_path)
    repo=repository(store,context);outcome=repo.populate(context,args,'engineering');ref=outcome['result']['sheet_ref']
    key='comparison:declared:direct_competitor_sensitive_shift'
    expected=repo.project_cells([ref],permitted_record_refs=[ref],components=[key]);descriptor=repo.descriptor();store.close()
    script='''import json,sqlite3,sys
from pathlib import Path
from gene_annotation_episode.state import Store
from gene_annotation_episode import literature_gel_storage as m
path,ref,key,descriptor=sys.argv[1:]
store=Store.__new__(Store);store.path=Path(path);store._savepoint=0
store.db=sqlite3.connect('file:'+str(store.path/'state.sqlite3')+'?mode=ro',uri=True,isolation_level=None)
store.db.row_factory=sqlite3.Row;store.db.execute('PRAGMA query_only=1')
repo=m.LiteratureGelRepository(store,'gel-fixture-run',evidence_origin='synthetic_fixture',expected_descriptor=json.loads(descriptor))
record=store.get(ref);allowed={record['artifact_ref'],record['request_ref']};get=store.get_artifact
def forbidden(*a,**k):raise AssertionError('original-byte access, science reexecution, or mutation')
store.get_artifact=lambda r:get(r) if r in allowed else forbidden()
store.put=store.artifact=repo.receive_cells=forbidden
for name in ('read_gel_inputs','validate_gel_extraction','_decode'):setattr(m.inputs,name,forbidden)
for name in ('populate_gel_components','validate_gel_sheet'):setattr(m.calculations,name,forbidden)
before=store.db.total_changes
rows=repo.project_cells([ref],permitted_record_refs=[ref],components=[key])
assert before==store.db.total_changes
print(json.dumps(rows,sort_keys=True));store.close()
'''
    result=subprocess.run([sys.executable,'-B','-c',script,str(tmp_path),ref,key,canonical(descriptor)],
        text=True,capture_output=True,check=True)
    assert json.loads(result.stdout)==expected


def test_long_authenticated_passage_and_value_keep_full_spans_without_store_anchor_limit(tmp_path,monkeypatch):
    store,context,args=native_case(tmp_path)
    try:
        long_value='X'*17001
        caption=('Protein P construct C DNA shift. '+long_value+'; full source passage.').encode()
        caption_ref=source(store,caption)
        for w in inputs._witnesses(args['selection']):w.update(source_ref=caption_ref,end=len(caption),quote=caption.decode())
        args['selection']['context']['experiment']['value']=long_value
        context=replace(context,received_record_refs=(*context.received_record_refs,caption_ref))
        repo=repository(store,context);outcome=repo.populate(context,args,'long-passage');ref=outcome['result']['sheet_ref']
        saved=repo.read(ref);assert saved['extraction']['authenticated_witnesses'][0]['quote']==caption.decode()
        experiment=saved['meanings']['global']['experiment'];record=store.get(experiment['value_ref'])
        assert record['anchor'] is None and len(record['label'])==512
        assert saved['semantic_bindings'][experiment['value_ref']]['label_preview'] is True
        location=saved['semantic_bindings'][experiment['value_ref']]['canonical_witness_locations'][0]
        start=caption.index(long_value.encode())
        assert (location['start'],location['end'])==(start,start+len(long_value))
        for witness_ref in experiment['witness_refs']:
            witness=store.get(witness_ref);binding=saved['semantic_bindings'][witness_ref]
            assert witness['anchor'] is None and binding['canonical_witness_locations'][0]['end']==len(caption)
        row=next(r for r in outcome['result']['cells'] if r['component_key']=='comparison:declared:direct_competitor_sensitive_shift')
        assert row['cell']['exact']=={'numerator':'3','denominator':'5'}
        allowed={store.get(ref)['artifact_ref'],store.get(ref)['request_ref']};get=store.get_artifact
        def saved_only(reference):
            assert reference in allowed,'original source bytes opened during saved replay'
            return get(reference)
        monkeypatch.setattr(store,'get_artifact',saved_only);forbid_reexecution(monkeypatch)
        store.db.execute('PRAGMA query_only=1');before=store.db.total_changes
        assert repo.project_cells([ref],permitted_record_refs=[ref],components=[row['component_key']])==[row]
        assert store.db.total_changes==before
    finally:store.close()
