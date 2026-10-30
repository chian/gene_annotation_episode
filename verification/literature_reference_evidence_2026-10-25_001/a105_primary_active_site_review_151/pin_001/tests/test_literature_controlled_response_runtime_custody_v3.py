"""Manual runtime-row engineering fixtures; actual episodes are tested by095."""
from copy import deepcopy as cp
from dataclasses import replace
import json

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError,canonical
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode import literature_controlled_response_storage as storage
from gene_annotation_episode import literature_controlled_response_local_calculations as local
from gene_annotation_episode import literature_controlled_response_owner_calculations as owner
from test_literature_controlled_response_storage_v3 import native_case,owned


def runtime_case(path,*,completed=True):
    store,context,args,_=native_case(path)
    request={'goal':{'goal_id':'constructed-runtime-fixture'},'message':{
        'scope':plain(context.scope),'episode_assignment':plain(context.assignment)},'report_contract':None}
    context=replace(context,request=request)
    journal=Journal(store,context.run_id)
    journal.save('runtime_episodes',{'episode_id':context.episode_id,'path':canonical(context.path),
        'request':canonical(request),'initial_credit':0,'state':'active','completion':None,'archive':None})
    action={'kind':'tool','tool':'literature.controlled_response.source_v3.populate','arguments':args}
    journal.save('runtime_actions',{'episode_id':context.episode_id,'decision_index':4,
        'action':canonical(action),'result':None,'credit':None,'timing':None})
    repo=storage.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture')
    outcome=repo.populate_v3(context,args,'fixture-run:fixture-child:4')
    result={**outcome,'pending_work_after_action':{'constructed_original_snapshot':True}}
    if completed:
        journal.save('runtime_actions',{'episode_id':context.episode_id,'decision_index':4,
            'action':canonical(action),'result':canonical(result),'credit':None,'timing':None})
    return store,owned(context,outcome),args,repo,outcome,journal,action,result


def forbid_scientific_reexecution(monkeypatch):
    def forbidden(*a,**k):raise AssertionError('scientific reexecution during custody/replay')
    monkeypatch.setattr(storage.source,'read_controlled_response_v3_inputs',forbidden)
    monkeypatch.setattr(storage.population,'populate_controlled_response_v3',forbidden)
    monkeypatch.setattr(local,'populate_controlled_response_local',forbidden)
    monkeypatch.setattr(owner,'populate_controlled_response_owner',forbidden)


def test_repository_before_runtime_commit_replays_without_reexecution_and_then_binds(tmp_path,monkeypatch):
    store,context,args,repo,outcome,journal,action,result=runtime_case(tmp_path,completed=False)
    try:
        ref=outcome['result']['sheet_ref'];key=outcome['result']['component_keys'][0]
        assert repo.read(ref)['selection']==args
        assert not repo._has_table(repo.runtime_binding_table)
        with pytest.raises(ContractError,match='runtime_uncommitted'):repo.fact_cells(context,[ref],components=[key])
        forbid_scientific_reexecution(monkeypatch)
        assert repo.populate_v3(context,args,'fixture-run:fixture-child:4')==outcome
        journal.save('runtime_actions',{'episode_id':context.episode_id,'decision_index':4,
            'action':canonical(action),'result':canonical(result),'credit':None,'timing':None})
        assert repo.fact_cells(context,[ref],components=[key])==[outcome['result']['cells'][0]]
        assert store.db.execute('SELECT count(*) FROM literature_controlled_response_runtime_bindings').fetchone()[0]==1
        assert not store.list('observation')
    finally:store.close()


def test_full_runtime_pending_snapshot_tamper_rejected_after_native_publication(tmp_path):
    store,context,args,repo,outcome,journal,action,result=runtime_case(tmp_path)
    try:
        ref=outcome['result']['sheet_ref'];key=outcome['result']['component_keys'][0]
        assert repo.fact_cells(context,[ref],components=[key])
        changed=cp(result);changed['pending_work_after_action']={'constructed_original_snapshot':False}
        journal.save('runtime_actions',{'episode_id':context.episode_id,'decision_index':4,
            'action':canonical(action),'result':canonical(changed),'credit':None,'timing':None})
        with pytest.raises(ContractError,match='runtime_digest_mismatch'):repo.read(ref)
    finally:store.close()


@pytest.mark.parametrize('new_request',[False,True])
def test_coordinated_private_payload_source_repository_rewrite_cannot_replace_original_runtime(tmp_path,new_request):
    store,context,args,repo,outcome,journal,action,result=runtime_case(tmp_path)
    try:
        ref=outcome['result']['sheet_ref'];key=outcome['result']['component_keys'][0]
        assert repo.fact_cells(context,[ref],components=[key])
        saved=repo.read(ref);source=store.get(ref);request=json.loads(store.get_artifact(source['request_ref']))
        saved['population']['local_sheet']['raw'][0]['cell']['value']=123
        if new_request:request['signature']['assignment']['forged_configuration']=True
        artifact=store.artifact(canonical(saved),'application/json')
        request_ref=store.artifact(canonical(request),'application/json')
        body={k:v for k,v in source.items() if k not in ('id','record_type','origin')}
        body.update(artifact_ref=artifact,text_ref=artifact,request_ref=request_ref)
        forged_ref=store.put('source',body,origin='tool')['id']
        forged=cp(outcome);forged['result'].update(sheet_ref=forged_ref,payload_sha256=storage._sha(saved),
            cells=storage._component_rows(saved['extraction'],saved['population'],forged_ref))
        for field in ('record_refs','changed_record_refs'):forged[field]=[forged_ref if r==ref else r for r in forged[field]]
        store.db.execute('UPDATE literature_controlled_response_operations SET signature=?,outcome=?',
            (canonical(request['signature']),canonical(forged)))
        assert json.loads(store.db.execute('SELECT result FROM runtime_actions').fetchone()[0])==result
        with pytest.raises(ContractError,match='original_runtime_(mismatch|context_mismatch)'):repo.read(forged_ref)
    finally:store.close()


def test_readonly_cannot_backfill_native_runtime_binding_but_existing_binding_replays(tmp_path):
    store,context,args,repo,outcome,journal,action,result=runtime_case(tmp_path)
    try:
        ref=outcome['result']['sheet_ref'];key=outcome['result']['component_keys'][0]
        store.db.execute('PRAGMA query_only=1')
        assert repo.read(ref)
        before=store.db.total_changes
        with pytest.raises(ContractError,match='runtime_binding_unavailable'):repo.fact_cells(context,[ref],components=[key])
        assert store.db.total_changes==before
        store.db.execute('PRAGMA query_only=0');assert repo.fact_cells(context,[ref],components=[key])
        store.db.execute('PRAGMA query_only=1');before=store.db.total_changes
        assert repo.fact_cells(context,[ref],components=[key])
        assert store.db.total_changes==before
    finally:store.close()
