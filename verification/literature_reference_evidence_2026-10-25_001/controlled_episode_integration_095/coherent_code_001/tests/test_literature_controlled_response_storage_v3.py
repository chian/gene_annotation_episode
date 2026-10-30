"""Constructed Store/runtime-row fixtures, not model or primary-paper proof."""
from copy import deepcopy as cp
from dataclasses import replace
import json
import subprocess
import sys

import pytest

from gene_annotation_episode.domain import ContractError,canonical,obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.state import Store
from gene_annotation_episode import literature_controlled_response_storage as storage
from test_literature_controlled_response_v3_inputs import Fixture


def native_case(path,index=0,*,modify=None,**kwargs):
    fixture=Fixture(index,**kwargs)
    if modify:modify(fixture)
    store=Store(path)
    store.create_problem(raw_sequence='MKWAA',molecule='protein')
    sources={}
    for ref in [fixture.main_ref,*[ref for ref in fixture.data if ref!=fixture.main_ref]]:
        data=fixture.data[ref]
        artifact=store.artifact(data)
        sources[ref]=store.put('source',{'provider':'constructed_controlled_fixture','accession':ref,'uri':None,
            'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,'version':None,'retrieved_at':None,
            'parent_source_refs':[] if ref==fixture.main_ref else [sources[fixture.main_ref]]},origin='caller')['id']
    def remap(value):
        if isinstance(value,dict):return {k:remap(v) for k,v in value.items()}
        if isinstance(value,list):return [remap(v) for v in value]
        return sources.get(value,value) if isinstance(value,str) else value
    args=remap(fixture.args)
    assignment={'source_ref':args['source_ref'],'requested_controlled_response_components':list(storage.COMPONENTS),
        'requested_controlled_response_views':list(storage.VIEWS)}
    context=BindingContext('fixture-run','fixture-child','literature_page',
        (('literature','fixture-parent'),('literature_page','fixture-child')),store.validate_scope(),assignment,{},tuple(sources.values()))
    return store,context,args,fixture


def owned(context,outcome):
    return replace(context,received_record_refs=(*context.received_record_refs,*outcome['record_refs']))


@pytest.mark.parametrize('kwargs',[{}, {'index':6}, {'companion':True,'joints':True}, {'companion':True,'authority':True,'joints':True}])
def test_real_source_to_saved_projection_exact_keys_and_replay(tmp_path,monkeypatch,kwargs):
    store,context,args,_=native_case(tmp_path,**kwargs)
    try:
        repo=storage.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture')
        outcome=repo.populate_v3(context,args,'selected');ref=outcome['result']['sheet_ref'];saved=repo.read(ref)
        rows=outcome['result']['cells'];keys=outcome['result']['component_keys']
        assert len(keys)==len(set(keys))
        assert repo.project_cells([ref],permitted_record_refs=[ref],components=keys)==rows
        # Standalone consistency is not native runtime fact-publication proof.
        with pytest.raises(ContractError,match='original_runtime_required'):
            repo.fact_cells(owned(context,outcome),[ref],components=keys)
        assert all(r['context']['condition_control_applications']['condition0'] is None for r in rows if r['kind']=='native_raw')
        if kwargs.get('companion') and not kwargs.get('authority'):
            assert not any(r['kind']=='final' for r in rows)
            assert len([r for r in rows if r['kind']=='conditional'])==24
            assert [r['reading_assignment'] for r in rows if r['component_key']=='joint:1:protein_condition1_response'][0]['protein_condition1']=='A-display'
        # Saved reads may open their two private immutable JSON artifacts only.
        allowed={store.get(ref)['artifact_ref'],store.get(ref)['request_ref']};get=store.get_artifact
        monkeypatch.setattr(store,'get_artifact',lambda r:get(r) if r in allowed else pytest.fail('scientific source reacquisition'))
        monkeypatch.setattr(storage.source,'read_controlled_response_v3_inputs',lambda *_a,**_k:pytest.fail('source reader rerun'))
        monkeypatch.setattr(storage.population,'populate_controlled_response_v3',lambda *_a,**_k:pytest.fail('population rerun'))
        from gene_annotation_episode import literature_controlled_response_local_calculations as local
        from gene_annotation_episode import literature_controlled_response_owner_calculations as owner
        monkeypatch.setattr(local,'populate_controlled_response_local',lambda *_a,**_k:pytest.fail('local calculator rerun'))
        monkeypatch.setattr(owner,'populate_controlled_response_owner',lambda *_a,**_k:pytest.fail('whole calculator rerun'))
        before=store.db.total_changes
        assert repo.read(ref)==saved
        assert repo.populate_v3(context,args,'selected')==outcome
        assert store.db.total_changes==before
        changed=cp(args);changed['local_pair_assignments']=[]
        with pytest.raises(ContractError,match='operation_key_reused'):repo.populate_v3(context,changed,'selected')
    finally:store.close()


def test_possession_exact_tokens_roster_and_semantic_identity(tmp_path):
    store,context,args,_=native_case(tmp_path,companion=True,joints=True)
    try:
        key='display %:/β';pair='paired %:/β'
        args['companion_readings'][0]['reading_key']=key
        for assignment in args['joint_reading_assignments']:
            if assignment['assignment']['protein_condition1'] is not None:assignment['assignment']['protein_condition1']=key
        args['local_pair_assignments'][0]['pair_key']=pair
        repo=storage.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture')
        with pytest.raises(ContractError,match='not_received'):
            repo.populate_v3(replace(context,received_record_refs=()),args,'missing')
        result=repo.populate_v3(context,args,'tokens');ref=result['result']['sheet_ref'];rows=result['result']['cells']
        keys=result['result']['component_keys']
        assert 'raw:protein_condition1:companion:display%20%25%3A%2F%CE%B2' in keys
        assert 'local:paired%20%25%3A%2F%CE%B2:difference' in keys
        with pytest.raises(ContractError,match='key_unknown'):repo.project_cells([ref],permitted_record_refs=[ref],components=['raw:protein_condition1:companion:display %:/β'])
        selected=[rows[0]];bindings=repo.semantic_bindings(selected)
        for cid,binding in bindings[ref].items():
            record=store.get(binding['record_ref'])
            assert cid==record['accession'] and cid!=record['id']
        assert set(repo.cell_record_refs(selected))=={ref,*[b['record_ref'] for b in bindings[ref].values()]}
        with pytest.raises(ContractError,match='runtime_admission_required'):repo.receive_cells(context,selected,'manual-proof')
        bad=cp(selected);bad[0]['cell']['value']=98
        with pytest.raises(ContractError,match='differs_from_original'):repo.validate_returned_values(bad,permitted_record_refs=[ref])
    finally:store.close()


def seed_runtime_rows(store,context,outcome,cells,*,child_id=None):
    """Manual journal rows exercise custody rejection only; not a native run."""
    child_id=child_id or context.episode_id
    parent=replace(context,episode_id='fixture-parent',role='literature',path=context.path[:-1],assignment={})
    contract={'decision':'Requested fixture quantities','measurements':{'schema':obj({'quantities':storage.controlled_response_cells_schema()})}}
    journal=Journal(store,context.run_id)
    child_request={'message':{'scope':dict(context.scope),'episode_assignment':dict(context.assignment)},'report_contract':contract}
    parent_request={'message':{'scope':dict(parent.scope),'episode_assignment':{}}}
    for ctx,request in ((context,child_request),(parent,parent_request)):
        journal.save('runtime_episodes',{'episode_id':ctx.episode_id,
            'path':canonical(ctx.path),'request':canonical(request),'initial_credit':0,'state':'closed','completion':None,'archive':None})
    if child_id!=context.episode_id:
        journal.save('runtime_episodes',{'episode_id':child_id,'path':canonical([*context.path[:-1],[context.role,child_id]]),
            'request':canonical(child_request),'initial_credit':0,'state':'closed','completion':None,'archive':None})
    original=json.loads(store.get_artifact(store.get(outcome['result']['sheet_ref'])['request_ref']))
    prefix=context.run_id+':'+context.episode_id+':'
    assert original['operation_key'].startswith(prefix)
    original_index=int(original['operation_key'][len(prefix):])
    journal.save('runtime_actions',{'episode_id':context.episode_id,'decision_index':original_index,
        'action':canonical({'kind':'tool','tool':'literature.controlled_response.source_v3.populate','arguments':original['arguments']}),
        'result':canonical({**outcome,'pending_work_after_action':{'constructed_fixture':True}}),'credit':None,'timing':None})
    journal.save('runtime_report_attempts',{'parent_episode_id':parent.episode_id,'decision_index':12,
        'delivery_ref':'constructed-delivery','child_episode_id':child_id,'contract':canonical(contract),
        'form':canonical({'quantities':cells}),'failure':None,'timing_receipts':None})
    receipts=EpisodeReceipts(store,context.run_id);receipts.bind(parent.episode_id);receipts.bind(child_id,parent.episode_id)
    receipts.receive(child_id,outcome['record_refs'],kind='own_action')
    return parent,'fixture-run:fixture-parent:12:typed_form'


def test_runtime_row_fixture_subset_original_digest_and_no_expansion(tmp_path):
    store,context,args,_=native_case(tmp_path)
    try:
        repo=storage.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture');outcome=repo.populate_v3(context,args,'fixture-run:fixture-child:4')
        ref=outcome['result']['sheet_ref'];cells=[outcome['result']['cells'][0]]
        parent,key=seed_runtime_rows(store,context,outcome,cells)
        repo.receive_cells(parent,cells,key);assert repo.received_cells(parent)==cells
        possessed=replace(parent,received_record_refs=tuple(repo.cell_record_refs(cells)))
        assert repo.fact_cells(possessed,[ref],components=outcome['result']['component_keys'])==cells
        before=store.db.total_changes;repo.receive_cells(parent,cells,key);assert store.db.total_changes==before
        with pytest.raises(ContractError,match='binding_mismatch'):repo.receive_cells(parent,outcome['result']['cells'],key)
        with pytest.raises(ContractError,match='parent_context_mismatch'):repo.received_cells(replace(parent,assignment={'invented':True}))
        # Altering an unrelated original form field must invalidate its FULL digest.
        form={'quantities':cells,'unrelated':'forged'}
        store.db.execute('UPDATE runtime_report_attempts SET form=?',(canonical(form),))
        with pytest.raises(ContractError,match='binding_mismatch'):repo.received_cells(parent)
    finally:store.close()


def test_original_outcome_association_cannot_be_replaced_by_self_hash(tmp_path):
    store,context,args,_=native_case(tmp_path)
    try:
        repo=storage.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture');outcome=repo.populate_v3(context,args,'selected')
        ref=outcome['result']['sheet_ref'];saved=repo.read(ref);record=store.get(ref)
        saved['population']['local_sheet']['raw'][0]['cell']['value']=123
        artifact=store.artifact(canonical(saved),'application/json')
        forged={k:v for k,v in record.items() if k not in ('id','record_type','origin')}
        forged.update(artifact_ref=artifact,text_ref=artifact)
        forged_ref=store.put('source',forged,origin='tool')['id']
        with pytest.raises(ContractError,match='original_outcome_mismatch'):repo.read(forged_ref)
    finally:store.close()


def test_detached_read_only_reconstruction_and_private_roster_possession(tmp_path):
    store,context,args,_=native_case(tmp_path,companion=True,joints=True)
    repo=storage.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture')
    outcome=repo.populate_v3(context,args,'detached');ref=outcome['result']['sheet_ref']
    expected=repo.project_cells([ref],permitted_record_refs=[ref],components=[outcome['result']['component_keys'][-1]])
    descriptor=repo.descriptor();store.close()
    script='''import json,sys
from gene_annotation_episode.state import Store
from gene_annotation_episode import literature_controlled_response_storage as m
from gene_annotation_episode import literature_controlled_response_local_calculations as local
from gene_annotation_episode import literature_controlled_response_owner_calculations as owner
path,ref,key,descriptor=sys.argv[1:]
store=Store(path);store.db.execute('PRAGMA query_only=1')
repo=m.LiteratureControlledResponseRepository(store,'fixture-run',evidence_origin='synthetic_fixture',expected_descriptor=json.loads(descriptor))
record=store.get(ref);allowed={record['artifact_ref'],record['request_ref']};get=store.get_artifact
def forbidden(*a,**k):raise AssertionError('scientific recomputation or acquisition')
store.get_artifact=lambda r:get(r) if r in allowed else forbidden()
m.source.read_controlled_response_v3_inputs=forbidden
m.population.populate_controlled_response_v3=forbidden
local.populate_controlled_response_local=forbidden
owner.populate_controlled_response_owner=forbidden
print(json.dumps(repo.project_cells([ref],permitted_record_refs=[ref],components=[key]),sort_keys=True))
store.close()
'''
    result=subprocess.run([sys.executable,'-B','-c',script,str(tmp_path),ref,expected[0]['component_key'],canonical(descriptor)],
        text=True,capture_output=True,check=True)
    assert json.loads(result.stdout)==expected


def test_forged_reporting_sibling_and_unrequested_key_reject(tmp_path):
    store,context,args,_=native_case(tmp_path)
    try:
        repo=storage.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture');outcome=repo.populate_v3(context,args,'fixture-run:fixture-child:4')
        cells=[outcome['result']['cells'][0]]
        parent,key=seed_runtime_rows(store,context,outcome,cells,child_id='fixture-sibling')
        with pytest.raises(ContractError,match='cell_not_received'):repo.receive_cells(parent,cells,key)
        assert not store.db.execute('SELECT 1 FROM literature_controlled_response_component_received').fetchone()
        restricted=replace(owned(context,outcome),assignment={**dict(context.assignment),'requested_controlled_response_components':[]})
        with pytest.raises(ContractError,match='not_requested'):repo.validate_fact_values(restricted,cells)
        assert not store.list('observation')
    finally:store.close()


@pytest.mark.parametrize('mode',['absent','empty_covariance'])
def test_saved_partial_read_preserves_missing_values_and_empty_covariance(tmp_path,mode):
    def modify(f):
        if mode=='absent':
            f.args['arms']['protein_condition1']=None
            f.args['covariance']['bindings']['protein_condition1']=None
        else:
            f.data[f.cov_ref]=b''
            f.args['covariance']['bindings']=dict.fromkeys(storage.shared.PRIMITIVE_ORDER)
            f.args['variance_status']={'value':'unknown','witnesses':[]}
            f.args['model_kind']={'value':'none','witnesses':[]}
            f.args['local_pair_assignments'][0]['covariance_selection']=cp(f.args['covariance'])
            f.args['local_pair_assignments'][0]['variance_status']=cp(f.args['variance_status'])
    store,context,args,_=native_case(tmp_path,modify=modify)
    try:
        repo=storage.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture');outcome=repo.populate_v3(context,args,mode)
        saved=repo.read(outcome['result']['sheet_ref'])
        if mode=='absent':
            row=outcome['result']['cells'][0]
            assert row['cell']['value'] is None and row['cell']['origin'] is None and row['native_reading'] is None
        else:
            document=saved['extraction']['covariance_document_scopes'][0]['document']
            assert document['raw_text']=='' and document['document_state']=='unsupported_format'
            variance=next(r for r in outcome['result']['cells'] if r['kind']=='local_variance')
            assert variance['cell']['value'] is None
            assert document['exact_matrix'] is None
    finally:store.close()


def test_declared_evidence_profile_is_bound_without_claiming_publication_truth(tmp_path):
    store,context,args,_=native_case(tmp_path,companion=True)
    try:
        repo=storage.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture')
        reported=storage.LiteratureControlledResponseRepository(store,context.run_id)
        with pytest.raises(ContractError,match='evidence_profile_mismatch'):reported.populate_v3(context,args,'profile')
        relabeled=cp(args);relabeled['companion_readings'][0]['reading']['source_kind']='primary_source'
        with pytest.raises(ContractError,match='evidence_profile_mismatch'):repo.populate_v3(context,relabeled,'profile')
        outcome=repo.populate_v3(context,args,'profile');ref=outcome['result']['sheet_ref']
        assert repo.read(ref)['evidence_origin']=='synthetic_fixture'
        assert repo.descriptor()['evidence_origin']=='synthetic_fixture'
        with pytest.raises(ContractError,match='evidence_profile_mismatch'):reported.read(ref)
        with pytest.raises(ContractError,match='implementation_binding_mismatch'):
            storage.LiteratureControlledResponseRepository(store,context.run_id,expected_descriptor=repo.descriptor())
    finally:store.close()


def test_component_specific_variance_model_metadata_matches_dependencies(tmp_path):
    store,context,args,_=native_case(tmp_path,companion=True,joints=True,authority=True)
    try:
        repo=storage.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture')
        outcome=repo.populate_v3(context,args,'metadata');saved=repo.read(outcome['result']['sheet_ref'])
        for row in outcome['result']['cells']:
            if row['kind'] not in ('final','conditional'):continue
            index=storage.arithmetic.COMPONENTS.index(row['component'])
            if index<7:
                assert row['context']['variance_status']=='unknown' and row['context']['model_kind']=='none'
                assert not row['dependencies']['model_readings'] and not row['dependencies']['covariance_owner_ids']
            elif index<10:
                assert row['context']['variance_status']=='known' and row['context']['model_kind']=='none'
                assert not row['dependencies']['model_readings']
            else:
                assert row['context']['model_kind']=='known_joint_normal_source_means'
                assert row['dependencies']['model_readings']
        assert saved['population']['final_sheet']['inputs']['model_kind']=='known_joint_normal_source_means'
    finally:store.close()
