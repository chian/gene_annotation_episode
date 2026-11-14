"""Controlled source snapshots through actual own Store/ToolRegistry custody."""
import hashlib
import json
from copy import deepcopy
from dataclasses import fields
import pytest
from gene_annotation_episode.episodic_workflow.root.a101 import literature_sequence_discovery as discovery
from gene_annotation_episode.episodic_workflow.root.a101 import read_mapping
from gene_annotation_episode.episodic_workflow.root.a101.acquisition import PublicClients, SourceSnapshot
from gene_annotation_episode.episodic_workflow.root.a101.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a101.state import Store
from gene_annotation_episode.episodic_workflow.root.a101.tools import ToolRegistry


class ObservedRegistry(ToolRegistry):
    def _source(self, *args, **kwargs):
        self.source_calls.append((args, kwargs))
        return super()._source(*args, **kwargs)


class ControlledClients(PublicClients):
    def uniprot_search(self, query, *, size=10, cursor=None):
        request={'query':query,'size':size,**({'cursor':cursor} if cursor is not None else {})}
        assert request==self.supplied.request
        return self.supplied


@pytest.fixture
def case(tmp_path):
    with Store(tmp_path/'state') as store:
        subject,=store.create_problem(raw_sequence='MACDEFGHIK',molecule='protein')['subject_refs']
        registry=ObservedRegistry(store,clients=ControlledClients());registry.source_calls=[]
        scope=store.validate_scope()
        yield store,registry,subject,scope


def snapshot(body,request):
    content=json.dumps(body,separators=(',',':')).encode() if isinstance(body,dict) else body
    return SourceSnapshot(service='uniprot',url='https://rest.uniprot.org/uniprotkb/search',
        request=request,retrieved_at='2026-11-12T00:00:00+00:00',content=content,
        media_type='application/json',transport={'response':{'headers':{
            'x-total-results':'2','link':'<https://rest.uniprot.org/uniprotkb/search?cursor=next-original>; rel="next"'}}})


def records():
    return {'results':[{'primaryAccession':'P00001','uniProtkbId':'CONTROLLED_MATCH',
        'entryType':'UniProtKB reviewed (Swiss-Prot)','sequence':{'value':'MACDEFGHIK'},
        'proteinDescription':{'recommendedName':{'fullName':{'value':'Original source name'},'ecNumbers':[{'value':'1.2.3.4'}]}},
        'genes':[{'geneName':{'value':'named_by_source'}}],
        'uniProtKBCrossReferences':[{'database':'ChEMBL','id':'CONTROLLED_LEAD'}],
        'references':[{'citation':{'title':'Controlled citation title','publicationDate':'2020',
            'journal':'Controlled journal','citationType':'journal article','citationCrossReferences':[{'database':'PubMed','id':'123'}]},
            'referencePositions':['SEQUENCE'],'referenceComments':[{'type':'TISSUE','value':'source tissue'}]}]},
        {'primaryAccession':'P00002','sequence':{'value':'MACDEFGHIL'}}]}


def publish(case):
    store,registry,subject,scope=case;arguments={'subject_ref':subject,'reviewed':True}
    selected,request=discovery.identity_request(registry,arguments,scope)
    assert selected==registry.clients.uniprot_search
    assert request['query']=='checksum:'+hashlib.md5(b'MACDEFGHIK').hexdigest().upper()+' AND reviewed:true'
    source=snapshot(records(),request)
    registry.clients.supplied=source
    outcome=registry.execute('public.literature.sequence_identity',arguments,scope=scope,
                             operation_key='controlled-sequence-discovery')
    assert outcome['status']=='completed',outcome
    result,refs=outcome['result'],outcome['record_refs']
    return arguments,source,result,refs


def test_actual_publication_preserves_source_leads_and_custom_registry_callback(case):
    store,registry,subject,scope=case
    arguments,source,result,refs=publish(case)
    assert len(registry.source_calls)==1
    assert registry.source_calls[0][0]==('uniprot',None)
    assert registry.source_calls[0][1]['operand_refs']==[subject]
    assert refs==[result['source_ref']]
    saved=store.get(refs[0]);assert store.get_artifact(saved['artifact_ref'])==source.content
    assert json.loads(store.get_artifact(saved['request_ref']))=={'request':source.request,'transport':source.transport}
    assert result['returned_records']==2 and result['rejected_records']==[{'record_index':1,'reason':'full_sequence_not_equal'}]
    assert result['matches'][0]['sequence_comparison']=='full_string_equal'
    assert result['matches'][0]['ec_numbers']==['1.2.3.4']
    assert result['matches'][0]['experimental_database_links']==[{'database':'ChEMBL','id':'CONTROLLED_LEAD'}]
    assert result['experimental_assessment'] is None
    assert result['next_query']=={**arguments,'cursor':'next-original'}
    assert store.count('observation')==0 and store.count('assessment')==0


def test_received_citations_use_original_pointers_and_no_new_records(case):
    store,registry,subject,scope=case;arguments,source,result,refs=publish(case)
    query={'subject_ref':subject,'source_ref':refs[0],'record_index':0}
    before=list(store.db.iterdump())
    value,created=discovery.references(registry,query,scope,refs)
    assert not created and value['total_references']==1 and value['next_query'] is None
    citation,=value['references'];assert citation['source_pointer']=='/results/0/references/0'
    assert citation['reported_scope']==['SEQUENCE']
    assert citation['reported_source']==[{'type':'TISSUE','value':'source tissue'}]
    assert 'discovery metadata' in value['qualification']
    assert list(store.db.iterdump())==before
    with pytest.raises(ContractError,match='source_location_source_not_received'):
        discovery.references(registry,query,scope,[])
    with pytest.raises(ContractError,match='sequence_identity_full_sequence_not_equal'):
        discovery.references(registry,{**query,'record_index':1},scope,refs)
    assert list(store.db.iterdump())==before


def test_malformed_response_preserves_original_source_before_failure_order(case):
    store,registry,subject,scope=case;arguments={'subject_ref':subject}
    _,request=discovery.identity_request(registry,arguments,scope)
    original=snapshot(b'not json',request);before=store.count('source')
    registry.clients.supplied=original
    outcome=registry.execute('public.literature.sequence_identity',arguments,scope=scope,
                             operation_key='controlled-malformed-discovery')
    assert outcome['status']=='partial'
    assert outcome['feedback']['code']=='sequence_identity_response_not_json'
    assert len(registry.source_calls)==1 and store.count('source')==before+1
    assert store.count('observation')==0 and store.count('assessment')==0


def test_projection_helpers_do_not_mutate_returned_source_metadata(case):
    store,registry,subject,scope=case;original=records();retained=deepcopy(original)
    _,request=discovery.identity_request(registry,{'subject_ref':subject},scope)
    source=snapshot(original,request)
    registry.clients.supplied=source
    outcome=registry.execute('public.literature.sequence_identity',{'subject_ref':subject},scope=scope,
                             operation_key='controlled-unmodified-source')
    assert outcome['status']=='completed',outcome
    assert original==retained
    assert discovery.ContractError is ContractError
    assert read_mapping.ContractError is ContractError


def test_native_mapping_public_type_and_cleanup_stay_at_acquisition_owner(tmp_path):
    directory=tmp_path/'owned-native';directory.mkdir();(directory/'retained.txt').write_text('controlled')
    metadata={'version':'controlled-metadata'};mapping=read_mapping.NativeMapping(directory,metadata)
    assert type(mapping) is read_mapping.NativeMapping
    assert mapping.__class__.__module__=='gene_annotation_episode.episodic_workflow.root.a101.read_mapping'
    assert [field.name for field in fields(mapping)]==['directory','metadata']
    assert mapping.metadata is metadata and mapping.path('retained.txt')==directory/'retained.txt'
    mapping.close();assert not directory.exists()
