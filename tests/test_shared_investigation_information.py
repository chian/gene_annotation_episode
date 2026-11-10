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
        store.db.execute('CREATE TABLE runtime_episodes (run_id TEXT,episode_id TEXT,path TEXT,request TEXT,state TEXT)')
        def context(path):
            path=tuple(map(tuple,path));episode=EpisodeRef('run-shared-test',path).episode_id
            request={'message':{'scope':scope,'episode_assignment':{}}}
            store.db.execute('INSERT INTO runtime_episodes VALUES(?,?,?,?,?)',
                ('run-shared-test',episode,canonical(path),canonical(request),'active'))
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
        'evidence_refs':[target]},
        known_record_refs=[target],operation_key='publish')['result']['publication_ref']
    read=shared.execute(parent,'shared.read_information',{'publication_ref':published},
        known_record_refs=[],operation_key='parent-read')
    assert read['record_refs']==[published,target]
    with pytest.raises(ContractError,match='not_received'):
        shared.execute(parent,'shared.resolve_information_need',{'need_ref':need,'status':'partially_fulfilled',
            'evidence_refs':[target]},known_record_refs=[],operation_key='not-received')
    result=shared.execute(parent,'shared.resolve_information_need',{'need_ref':need,'status':'partially_fulfilled',
        'evidence_refs':[target]},known_record_refs=read['record_refs'],operation_key='deliver')
    view=shared.context_view(child)
    assert view['needs'][0]['status']=='partially_fulfilled'
    disposition=result['result']['publication_ref']
    selected=shared.execute(child,'shared.read_information',{'publication_ref':disposition},
        known_record_refs=[],operation_key='child-read')
    assert selected['record_refs']==[disposition,target]
    assert 'reason' not in selected['result'] and 'qualification' not in read['result']
    store.db.execute("UPDATE runtime_episodes SET state='yielded' WHERE episode_id=?", (child.episode_id,))
    assert 'shared.resolve_information_need' not in {entry['name'] for entry in shared.catalog(parent)}
    assert shared.context_view(parent)['needs'][0]['response_route']=='retained_limitation_for_parent_next_commission'
    with pytest.raises(ContractError,match='requester_not_active'):
        shared.execute(parent,'shared.resolve_information_need',{'need_ref':need,'status':'unavailable',
            'evidence_refs':[],'reason':'Cannot deliver to a closed child.'},
            known_record_refs=[],operation_key='closed-requester')


def test_publication_requires_original_context_and_cannot_be_forged(family):
    store,target,parent,child,sibling,shared=family
    forged=BindingContext(child.run_id,child.episode_id,child.role,child.path,child.scope,{},
        {'message':{'scope':child.scope,'episode_assignment':{}},'forged':True})
    with pytest.raises(ValueError,match='original_context_conflict'):
        shared.context_view(forged)


def test_root_catalog_has_no_recipientless_requests_or_empty_message_poll(family):
    store, target, parent, child, sibling, shared = family
    assert shared.catalog(parent) == []
    with pytest.raises(ContractError, match='parent_recipient_unavailable'):
        shared.execute(parent, 'shared.request_information', {'target_ref': target,
            'question': 'Which organism was sampled?', 'required_information': 'Sample provenance.',
            'reason': 'Evaluate organism-context applicability.', 'blocking': False,
            'available_record_refs': []}, known_record_refs=[], operation_key='root-no-parent')
    publication = shared.execute(child, 'shared.publish_information', {'target_ref': target,
        'evidence_refs': [target]},
        known_record_refs=[target], operation_key='explicit-offer')['result']['publication_ref']
    assert [entry['name'] for entry in shared.catalog(parent)] == ['shared.read_information']
    preview = shared.context_view(parent)['information_available'][0]
    assert preview['publication_ref'] == publication and preview['evidence_count'] == 1
    assert 'evidence_refs' not in preview
    assert 'qualification' not in preview
    assert len(preview['offered_material']) == 1
    assert preview['offered_material'][0]['record_type'] == 'input'
    assert 'value' not in preview['offered_material'][0]


def _scientific_source(store, accession):
    artifact=store.artifact('Original source content', 'text/plain')
    return store.put('source', {'provider':'fixture.scientific_source',
        'accession':accession,'uri':None,'artifact_ref':artifact,'text_ref':artifact,
        'request_ref':None,'version':'v1','retrieved_at':None}, origin='tool')['id']


def test_producer_can_identify_offered_records_without_granting_recipient_access(family):
    store,target,parent,child,sibling,shared=family
    source=_scientific_source(store, 'source-1')
    result=shared.execute(child, 'shared.publish_information',
        {'target_ref':target,'evidence_refs':[target,source]},
        known_record_refs=[target,source], operation_key='own-offer')
    own=shared.context_view(child)['information_available'][0]
    recipient=shared.context_view(parent)['information_available'][0]
    assert own['offered_evidence_refs']==[target,source]
    assert 'offered_evidence_refs' not in recipient and 'evidence_refs' not in recipient
    assert shared.context_view(sibling)['information_available']==[]
    assert result['record_refs']==[own['publication_ref']]
    assert result['changed_record_refs']==[]
    received=shared.execute(parent, 'shared.read_information',
        {'publication_ref':own['publication_ref']}, known_record_refs=[], operation_key='read-own-offer')
    assert received['record_refs']==[own['publication_ref'],target,source]


def test_repeated_record_set_is_explicit_while_original_publications_and_replay_survive(family):
    store,target,parent,child,sibling,shared=family
    source=_scientific_source(store, 'source-1')
    args={'target_ref':target,'evidence_refs':[target,source]}
    first=shared.execute(child, 'shared.publish_information', args,
        known_record_refs=[target,source], operation_key='first')
    repeated=shared.execute(child, 'shared.publish_information',
        {'target_ref':target,'evidence_refs':[source,target]},
        known_record_refs=[target,source], operation_key='reordered')
    again=shared.execute(child, 'shared.publish_information', args,
        known_record_refs=[target,source], operation_key='again')
    first_ref=first['result']['publication_ref']
    assert first['result']['offer_history']['equivalent_prior_offer_count']==0
    assert first['result']['offer_history']['first_equivalent_publication_ref'] is None
    assert repeated['result']['offer_history']['equivalent_prior_offer_count']==1
    assert again['result']['offer_history']['equivalent_prior_offer_count']==2
    assert repeated['result']['offer_history']['first_equivalent_publication_ref']==first_ref
    assert again['result']['offer_history']['first_equivalent_publication_ref']==first_ref
    assert len({result['result']['publication_ref'] for result in (first,repeated,again)})==3
    assert all(result['changed_record_refs']==[] for result in (first,repeated,again))
    assert shared.execute(child, 'shared.publish_information', args,
        known_record_refs=[target,source], operation_key='first')==first
    assert shared.context_view(parent)['total_information']==3
    assert store.count('observation')==0


def test_equivalent_offer_history_does_not_merge_other_producers_or_revised_sources(family):
    store,target,parent,child,sibling,shared=family
    original=_scientific_source(store, 'original')
    revised=_scientific_source(store, 'revised')
    assert original!=revised
    for owner,source,key in ((child,original,'child-original'),
            (sibling,original,'sibling-original'), (child,revised,'child-revised')):
        result=shared.execute(owner, 'shared.publish_information',
            {'target_ref':target,'evidence_refs':[target,source]},
            known_record_refs=[target,source], operation_key=key)
        assert result['result']['offer_history']['equivalent_prior_offer_count']==0
    assert shared.context_view(child)['total_information']==2
    assert shared.context_view(sibling)['total_information']==1


def test_equivalent_offer_does_not_replace_current_receipt_eligibility(family):
    store,target,parent,child,sibling,shared=family
    source=_scientific_source(store, 'source-1')
    args={'target_ref':target,'evidence_refs':[target,source]}
    shared.execute(child, 'shared.publish_information', args,
        known_record_refs=[target,source], operation_key='received')
    with pytest.raises(ContractError, match='evidence_not_received'):
        shared.execute(child, 'shared.publish_information', args,
            known_record_refs=[target], operation_key='not-currently-received')
