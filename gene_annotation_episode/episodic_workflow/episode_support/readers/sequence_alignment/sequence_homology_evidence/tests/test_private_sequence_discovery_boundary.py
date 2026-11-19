"""Controlled source snapshots through actual own Store/ToolRegistry custody."""
import hashlib
import json
from copy import deepcopy
from dataclasses import fields
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sequence_homology_evidence import literature_sequence_discovery as discovery
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_alignment.sequence_homology_evidence import read_mapping
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.sequence_homology_evidence.acquisition import PublicClients, SourceSnapshot
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import ContractError
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_homology_evidence.tools import ToolRegistry


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
        scope=store.validate_scope({'subject_refs': store.problem()['subject_refs']})
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


def test_native_mapping_public_type_and_cleanup_stay_at_acquisition_owner(tmp_path):
    directory=tmp_path/'owned-native';directory.mkdir();(directory/'retained.txt').write_text('controlled')
    metadata={'version':'controlled-metadata'};mapping=read_mapping.NativeMapping(directory,metadata)
    assert type(mapping) is read_mapping.NativeMapping
    assert [field.name for field in fields(mapping)]==['directory','metadata']
    assert mapping.metadata is metadata and mapping.path('retained.txt')==directory/'retained.txt'
    mapping.close();assert not directory.exists()
