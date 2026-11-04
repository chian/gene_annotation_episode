"""Actual Store/importer publication from synthetic captured HMMER entities."""
import asyncio
import json

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.public_search_publication import PublicSearchResultPublisher
from gene_annotation_episode.tools import ToolRegistry
from test_hmmer_api_operations import FixtureClient, result_body, setup, snapshot


class PublicationClient(FixtureClient):
    def __init__(self):
        super().__init__();self.body=result_body()
    def hmmer_result(self,job_id,**kwargs):
        self.calls.append(('result',job_id,kwargs)); return snapshot(self.body)


def publishable(path, body=None):
    client=PublicationClient()
    if body is not None:client.body=body
    store,client,ops,order=setup(path,client)
    async def acquire():
        await ops.submit_once(order['job_ref'],operation_key='submit')
        client.state='SUCCESS';await ops.status_once(order['job_ref'],operation_key='status')
        return await ops.result_once(order['job_ref'],operation_key='result',page=1,page_size=2)
    receipt=asyncio.run(acquire())
    tools=ToolRegistry(store,clients=client)
    return store,client,ops,order,receipt,PublicSearchResultPublisher(store,tools,operations=ops)


def test_no_network_publication_exact_original_source_and_rows(tmp_path):
    store,client,ops,order,receipt,publisher=publishable(tmp_path)
    with store:
        before=list(client.calls);scope={'subject_refs':store.problem()['subject_refs']}
        published=publisher.publish(receipt['receipt_ref'],scope=scope,operation_key='publication')
        assert client.calls==before
        result=published['result'];source=store.get(result['source_ref'])
        assert store.get_artifact(source['artifact_ref'])==snapshot(client.body).content
        rows=result['publication_rows'];assert [row['record_type'] for row in rows]==['reference','observation']
        assert rows[0]['hit_ordinal']==0 and rows[0]['domain_ordinal'] is None
        assert rows[1]['domain_ordinal'] is None
        expected={'version','registry_ref','job_ref','request_sha256','publication_operation_key',
            'acquisition_receipt_ref','source_ref','subject_ref','provider','page','page_size',
            'hit_ordinal','domain_ordinal','record_ref','record_type'}
        assert all(set(row)==expected and row['job_ref']==order['job_ref'] for row in rows)
        assert all(store.get(row['record_ref'])['source_ref']==source['id'] for row in rows)
        proof=store.get(result['publication_ref']);body=json.loads(store.get_artifact(proof['artifact_ref']))
        assert proof['provider']=='episode.api_search_result_publication'
        assert body['selector']['first_page']==body['selector']['last_page']==1
        assert body['publication_rows']==rows
        assert {result['publication_rows'][0]['record_ref']} <= set(published['record_refs'])
        assert publisher.publish(receipt['receipt_ref'],scope=scope,operation_key='publication')==published
        assert not store.current_annotations() and client.calls==before
        with pytest.raises(ContractError,match='operation_conflict'):
            publisher.publish(receipt['receipt_ref'],scope=None,operation_key='publication')


def test_two_accessionless_hits_preserve_actual_native_indices_and_array_witnesses(tmp_path):
    body=result_body();body['result']['hits']=[dict(index=13,score=2.,evalue=.1,domains=[]),
                                             dict(index=91,score=3.,evalue=.2,domains=[])]
    store,client,ops,order,receipt,publisher=publishable(tmp_path,body)
    with store:
        published=publisher.publish(receipt['receipt_ref'],scope={'subject_refs':store.problem()['subject_refs']},operation_key='publication')
        rows=published['result']['publication_rows'];refs=[r for r in rows if r['record_type']=='reference']
        assert len(refs)==2 and len({r['record_ref'] for r in refs})==2
        assert [r['hit_ordinal'] for r in refs]==[0,1]
        assert all(store.get(r['record_ref'])['accession'].startswith('source_local_hit_') for r in refs)


def test_bad_later_hit_retains_earlier_actual_publications_and_restricted_locator(tmp_path):
    body=result_body();body['result']['hits'].append({'index':4,'acc':'bad','domains':[{'alignment_display':{
        'hmmfrom':1,'hmmto':99,'m':8,'sqfrom':1,'sqto':8,'l':8}}]})
    store,client,ops,order,receipt,publisher=publishable(tmp_path,body)
    with store:
        result=publisher.publish(receipt['receipt_ref'],scope={'subject_refs':store.problem()['subject_refs']},operation_key='publication')['result']
        assert len(result['publication_rows'])==2
        assert result['projection_failures']==[{'hit_ordinal':1,'domain_ordinal':None,'code':'invalid_native_hit'}]
        assert store.count('reference')==1 and store.count('observation')==1
        assert store.get_artifact(store.get(result['source_ref'])['artifact_ref'])==snapshot(body).content


def test_domain_ordinals_match_native_array_and_actual_records(tmp_path):
    body=result_body();body['result']['hits'][0]['domains']=[{'bitscore':10.,'ievalue':.01},
        {'bitscore':11.,'ievalue':.02}]
    store,client,ops,order,receipt,publisher=publishable(tmp_path,body)
    with store:
        result=publisher.publish(receipt['receipt_ref'],scope={'subject_refs':store.problem()['subject_refs']},operation_key='publication')['result']
        rows=result['publication_rows'];assert [r['domain_ordinal'] for r in rows]==[None,0,1]
        assert all(store.get(row['record_ref'])['record_type']==row['record_type'] for row in rows)


def test_publication_scope_checked_without_new_network(tmp_path):
    store,client,ops,order,receipt,publisher=publishable(tmp_path)
    with store:
        before=list(client.calls); before_sources=store.count('source')
        with pytest.raises(ContractError):
            publisher.publish(receipt['receipt_ref'],scope={'subject_refs':[]},operation_key='wrong_scope')
        assert store.count('source')==before_sources and client.calls==before


def test_later_domain_failure_preserves_reference_and_earlier_observation(tmp_path):
    body=result_body()
    def aligned(length):
        return dict(bitscore=10.,ievalue=.01,alignment_display=dict(
            hmmfrom=1,hmmto=4,m=length,sqfrom=1,sqto=4,l=8))
    body['result']['hits'][0]['domains']=[aligned(8),aligned(9)]
    store,client,ops,order,receipt,publisher=publishable(tmp_path,body)
    with store:
        published=publisher.publish(receipt['receipt_ref'],scope={'subject_refs':store.problem()['subject_refs']},operation_key='publication')
        rows=published['result']['publication_rows']
        assert [(r['record_type'],r['domain_ordinal']) for r in rows]==[('reference',None),('observation',0)]
        assert published['result']['projection_failures']==[dict(hit_ordinal=0,domain_ordinal=None,
            code='provider_query_length_differs_from_submitted_subject')]
        assert store.count('reference')==store.count('observation')==1
        assert all(r['record_ref'] in published['record_refs'] for r in rows)
        assert store.get_artifact(store.get(published['result']['source_ref'])['artifact_ref'])==snapshot(body).content
