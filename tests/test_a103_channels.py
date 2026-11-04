"""Engineered transport/attribution controls; no biological validation claimed."""
import json

import pytest

from gene_annotation_episode.a103_channels import publish_channels
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.molecular_provider_acquisition import provider_value
from test_molecular_provider_acquisition import snapshot,IDS
from test_a103_context import context_case,grade
from a103_test_support import source


def capture(store,fields):
    raw=json.dumps([{'stringId_A':IDS[0],'stringId_B':IDS[1],'ncbiTaxonId':9606,'score':.99,**fields}]).encode()
    native=snapshot('public.string.network',raw=raw)
    artifact=store.artifact(raw,'application/json')
    value=provider_value('public.string.network',native,artifact_ref=artifact)
    receipt=store.artifact(json.dumps(value),'application/json')
    return store.put('source',{'provider':'string','accession':'explicit-engineered-transport-fixture',
        'uri':native.url,'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,
        'version':'engineered-transport-control','retrieved_at':None,'auxiliary_artifact_refs':[receipt]},origin='external')['id']


def arguments(target,partner,origin):
    return {'target_ref':target,'target_regions':[[0,6]],'source_ref':origin,
        'left_native_id':IDS[0],'right_native_id':IDS[1],
        'left_reference_ref':target,'right_actual_ref':partner,'right_reference_ref':partner}


def test_native_channels_need_exact_endpoint_sequences_and_late_receipt_regrades(context_case):
    store,target,known,a,ab,b,bb,na,sa,*_=context_case
    partner=sa['cds'][1]['protein_reference_ref']
    origin=capture(store,{'nscore':.7,'fscore':.2,'pscore':.4})
    output,refs=publish_channels(store,arguments(target,partner,origin));known.update([origin,*refs])
    assert output['combined_score_used'] is False
    before,needs=grade(store,target,known)
    assert before['credit']==0 and needs
    count=store.db.execute('SELECT count(*) FROM a103_publications').fetchone()[0]
    canonical=source(store,'retained.uniprot',{'results':[
        {'sequence':{'value':'MDEAKG'},'uniProtKBCrossReferences':[{'database':'STRING','id':IDS[0]}]},
        {'sequence':{'value':'MKQQ'},'uniProtKBCrossReferences':[{'database':'STRING','id':IDS[1]}]}]})
    known.add(canonical)
    after,needs=grade(store,target,known)
    assert after['credit']==pytest.approx(.7)
    assert not [r for r,out in needs if r in refs]
    assert store.db.execute('SELECT count(*) FROM a103_publications').fetchone()[0]==count
    assert {r['channel'] for r in after['tool_attachments'] if r['producer_operation']=='context.association_channels'}=={
        'neighborhood','fusion','phylogenetic_profile'}


def test_combined_string_score_cannot_create_context_measurement(context_case):
    store,target,known,a,ab,b,bb,na,sa,*_=context_case
    origin=capture(store,{'ascore':.8,'escore':.9,'tscore':.99})
    with pytest.raises(ContractError,match='no_native_context_channels'):
        publish_channels(store,arguments(target,sa['cds'][1]['protein_reference_ref'],origin))
