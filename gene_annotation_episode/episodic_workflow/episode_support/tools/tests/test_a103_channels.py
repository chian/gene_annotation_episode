"""Engineered transport/attribution controls; no biological validation claimed."""
import json
from urllib.parse import urlencode

import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.episodic_workflow.episode_support.tools.channels import publish_channels
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import ContractError
from gene_annotation_episode.molecular_provider_acquisition import provider_request_spec, provider_value
from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.tests.test_a103_context import context_case,grade
from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.tests.a103_test_support import source

IDS=['9606.ENSP00000269305','9606.ENSP00000266970']


def string_snapshot(raw):
    """A STRING network transfer of the given engineered body, as the acquisition layer records it."""
    arguments={'string_ids':IDS,'taxon_id':9606,'required_score':400,'max_bytes':10000}
    spec=provider_request_spec('public.string.network',arguments,string_caller_identity='configured_app')
    address=spec['url']+('?'+urlencode(spec['params'],doseq=True) if spec['params'] else '')
    transport={'status':200,'headers':{'content-type':spec['media_type']},
        'request':{'method':'GET','url':address},
        'request_policy':{'timeout_seconds':90,'automatic_redirects':False},
        'body_complete':True,'retained_body_bytes':len(raw),'observed_body_bytes':len(raw),
        'declared_body_bytes':len(raw),'response_byte_limit':arguments['max_bytes']}
    return SourceSnapshot(spec['service'],spec['url'],arguments,'2026-10-31T00:00:00Z',raw,spec['media_type'],transport)


def capture(store,fields):
    raw=json.dumps([{'stringId_A':IDS[0],'stringId_B':IDS[1],'ncbiTaxonId':9606,'score':.99,**fields}]).encode()
    native=string_snapshot(raw)
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
    canonical=source(store,'retained.uniprot',{'results':[
        {'sequence':{'value':'MDEAKG'},'uniProtKBCrossReferences':[{'database':'STRING','id':IDS[0]}]},
        {'sequence':{'value':'MKQQ'},'uniProtKBCrossReferences':[{'database':'STRING','id':IDS[1]}]}]})
    known.add(canonical)
    after,needs=grade(store,target,known)
    assert after['credit']==pytest.approx(.7)
    assert not [r for r,out in needs if r in refs]
    assert {r['channel'] for r in after['tool_attachments'] if r['producer_operation']=='context.association_channels'}=={
        'neighborhood','fusion','phylogenetic_profile'}


def test_combined_string_score_cannot_create_context_measurement(context_case):
    store,target,known,a,ab,b,bb,na,sa,*_=context_case
    origin=capture(store,{'ascore':.8,'escore':.9,'tscore':.99})
    with pytest.raises(ContractError,match='no_native_context_channels'):
        publish_channels(store,arguments(target,sa['cds'][1]['protein_reference_ref'],origin))
