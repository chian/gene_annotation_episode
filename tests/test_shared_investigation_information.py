"""Shared facts and requests retain parent ownership and explicit receipts."""
import json

import pytest
from method_loop.identities import EpisodeRef

from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.shared_information import SharedInformation
from gene_annotation_episode.state import Store


@pytest.fixture
def family(tmp_path):
    with Store(tmp_path/'state') as store:
        target,=store.create_problem(raw_sequence='MAAA',molecule='protein')['subject_refs']
        scope={'subject_refs':[target]}
        store.db.execute('CREATE TABLE runtime_episodes (run_id TEXT,episode_id TEXT,path TEXT,request TEXT)')
        def context(path):
            path=tuple(map(tuple,path));episode=EpisodeRef('run-shared-test',path).episode_id
            request={'message':{'scope':scope,'episode_assignment':{}}}
            store.db.execute('INSERT INTO runtime_episodes VALUES(?,?,?,?)',
                ('run-shared-test',episode,canonical(path),canonical(request)))
            return BindingContext('run-shared-test',episode,path[-1][0],path,scope,{},request)
        parent=context([['annotation','root']])
        child=context([['annotation','root'],['scientific_process','a102']])
        sibling=context([['annotation','root'],['scientific_process','a101']])
        yield store,target,parent,child,sibling,SharedInformation(store,parent.run_id)


def test_parent_sees_need_but_sibling_cannot_read_it_or_resolve_it(family):
    store,target,parent,child,sibling,shared=family
    args={'target_ref':target,'question':'Which sequence homolog structures are available?',
        'required_information':'Homolog identifiers and retained sequence-correspondence sources.',
        'reason':'Choose structural comparators.','blocking':False,'available_record_refs':[target]}
    result=shared.execute(child,'shared.request_information',args,known_record_refs=[target],operation_key='need-0')
    assert shared.execute(child,'shared.request_information',args,known_record_refs=[target],operation_key='need-0')==result
    need=result['result']['publication_ref']
    assert shared.context_view(parent)['needs'][0]['publication_ref']==need
    assert shared.context_view(sibling)['needs']==[]
    with pytest.raises(ContractError,match='not_authorized'):
        shared.execute(sibling,'shared.read_information',{'publication_ref':need},
            known_record_refs=[target],operation_key='bad-read')
    with pytest.raises(ContractError,match='owned_by_parent'):
        shared.execute(child,'shared.resolve_information_need',{'need_ref':need,'status':'unavailable',
            'evidence_refs':[],'reason':'Unknown'},known_record_refs=[target],operation_key='bad-resolve')
    assert store.count('observation')==0


def test_parent_delivers_actual_received_evidence_explicitly(family):
    store,target,parent,child,sibling,shared=family
    need=shared.execute(child,'shared.request_information',{'target_ref':target,'question':'Need model',
        'required_information':'Coordinates with origin.','reason':'No target model yet.',
        'blocking':True,'available_record_refs':[]},known_record_refs=[],operation_key='need')['result']['publication_ref']
    published=shared.execute(sibling,'shared.publish_information',{'target_ref':target,
        'evidence_refs':[target],'qualification':'Supplied sequence only; coordinates remain unknown.'},
        known_record_refs=[target],operation_key='publish')['result']['publication_ref']
    read=shared.execute(parent,'shared.read_information',{'publication_ref':published},
        known_record_refs=[],operation_key='parent-read')
    assert read['record_refs']==[published,target]
    with pytest.raises(ContractError,match='not_received'):
        shared.execute(parent,'shared.resolve_information_need',{'need_ref':need,'status':'partially_fulfilled',
            'evidence_refs':[target],'reason':'Have sequence.'},known_record_refs=[],operation_key='not-received')
    result=shared.execute(parent,'shared.resolve_information_need',{'need_ref':need,'status':'partially_fulfilled',
        'evidence_refs':[target],'reason':'Sequence received; no model.'},known_record_refs=read['record_refs'],operation_key='deliver')
    view=shared.context_view(child)
    assert view['needs'][0]['status']=='partially_fulfilled'
    disposition=result['result']['publication_ref']
    selected=shared.execute(child,'shared.read_information',{'publication_ref':disposition},
        known_record_refs=[],operation_key='child-read')
    assert selected['record_refs']==[disposition,target]


def test_publication_requires_original_context_and_cannot_be_forged(family):
    store,target,parent,child,sibling,shared=family
    forged=BindingContext(child.run_id,child.episode_id,child.role,child.path,child.scope,{},
        {'message':{'scope':child.scope,'episode_assignment':{}},'forged':True})
    with pytest.raises(ValueError,match='original_context_conflict'):
        shared.context_view(forged)
