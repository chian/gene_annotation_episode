"""Parent dispatch controls; no models or biological algorithms run here."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from a103_parent_dispatch import pending_sequence_requests


class Subjects:
    def __init__(self, peptides):
        self.peptides = peptides

    def get(self, ref):
        return {'sequence_ref':ref} if ref in self.peptides else {}

    def get_artifact(self, ref):
        return self.peptides[ref].encode('ascii')

    def subject_molecule(self, ref):
        return 'protein'


def test_parent_dispatch_preserves_the_actual_bioy_episode_family_search_request():
    fixture = json.loads((Path(__file__).parent/'fixtures/a103/bioy_parent_need.json').read_text())
    target,query = fixture['target_ref'],fixture['query_ref']
    store = Subjects({target:'MDEAKG',query:'MKQQ'})
    requests = pending_sequence_requests(store,target,{target,query,'need'},[],[('need',fixture['published_need'])])
    assert len(requests)==1 and requests[0]['query_ref']==query
    assert requests[0]['need_refs']==['need']
    assert requests[0]['purposes']==['explicit_received_search_query']


def test_parent_dispatch_prioritizes_the_required_family_over_the_unidentified_neighbor():
    store = Subjects({'target':'MDEAKG','expected':'MKQQ','neighbor':'MNNQKG'})
    known = {'target','expected','neighbor','need','neighborhood','measurement'}
    attachment = {'target_ref':'target','measurement_ref':'measurement','partner_link':{
        'factor':None,'actual_subject_ref':'neighbor','reference_subject_ref':'expected'}}
    need = {'required_information':json.dumps({'measurement_or_request_ref':'measurement','required_operands':[
        {'use':'partner_in_exact_neighborhood','query_ref':'expected',
            'actual_component_ref':'neighbor','neighborhood_ref':'neighborhood'}]})}
    requests = pending_sequence_requests(store,'target',known,[attachment],[('need',need)])
    assert [r['query_ref'] for r in requests]==['expected','neighbor']
    assert requests[0]['reference_refs']==['neighbor']
    assert requests[0]['neighborhood_refs']==['neighborhood']
    assert requests[0]['need_refs']==requests[1]['need_refs']==['need']


def test_parent_dispatch_canonicalizes_identical_peptides_and_retains_each_reference_use():
    store = Subjects({'target':'MDEAKG','alias':'MDEAKG','left':'MDE','right':'AKG'})
    known = {'target','alias','left','right','measurement'}
    attachments = [{'target_ref':'target','measurement_ref':'measurement','regions':[
        {'factor':None,'actual_subject_ref':'alias','reference_subject_ref':'left'},
        {'factor':None,'actual_subject_ref':'target','reference_subject_ref':'right'}]}]
    requests = pending_sequence_requests(store,'target',known,attachments,[])
    assert len(requests)==1 and requests[0]['query_ref']=='target'
    assert set(requests[0]['requested_query_refs'])=={'target','alias'}
    assert requests[0]['reference_refs']==['left','right']
    assert set(requests[0]['evidence_refs'])=={'target','alias','left','right'}
    key = hashlib.sha256(b'MDEAKG').hexdigest()
    assert pending_sequence_requests(store,'target',known,attachments,[],submitted_queries={key})==[]


def test_parent_dispatch_does_not_borrow_unreceived_queries_or_neighborhoods():
    store = Subjects({'target':'MDEAKG','expected':'MKQQ'})
    need = {'required_information':json.dumps({'required_operands':[{
        'use':'partner_in_exact_neighborhood','query_ref':'expected',
        'actual_component_ref':None,'neighborhood_ref':'neighborhood'}]})}
    for known in ({'target','need','neighborhood'},{'target','expected','need'},{'target','expected','neighborhood'}):
        assert pending_sequence_requests(store,'target',known,[],[('need',need)])==[]


def test_parent_dispatch_alignment_request_keeps_the_original_target_query():
    target = 'input_'+'a'*24
    reference = 'reference_'+'b'*24
    store = Subjects({target:'MDEAKG',reference:'MEEAKG'})
    need = {'question':'Align the target to the supplied homolog.',
        'required_information':'Return sequence correspondence and coordinates.',
        'available_record_refs':[reference]}
    requests = pending_sequence_requests(store,target,{target,reference,'need'},[],[('need',need)])
    assert len(requests)==1 and requests[0]['query_ref']==target
    assert requests[0]['reference_refs']==[reference]


def test_parent_dispatch_family_search_does_not_require_or_borrow_an_unreceived_candidate():
    store = Subjects({'target':'MDEAKG','expected':'MKQQ','private-candidate':'MNNQKG'})
    need = {'required_information':json.dumps({'required_operands':[{
        'use':'partner_in_exact_neighborhood','query_ref':'expected',
        'actual_component_ref':'private-candidate','neighborhood_ref':'neighborhood'}]})}
    requests = pending_sequence_requests(store,'target',{'target','expected','need','neighborhood'},[],[('need',need)])
    assert len(requests)==1 and requests[0]['query_ref']=='expected'
    assert requests[0]['reference_refs']==[]
    assert 'private-candidate' not in requests[0]['evidence_refs']


def test_parent_dispatch_keeps_different_family_queries_separate():
    store = Subjects({'target':'MDEAKG','family1':'MKQQ','family2':'MKQG'})
    known = {'target','family1','family2','need','neighborhood'}
    need = {'required_information':json.dumps({'required_operands':[{
        'use':'partner_in_exact_neighborhood','query_ref':query,
        'actual_component_ref':None,'neighborhood_ref':'neighborhood'} for query in ('family1','family2')]})}
    original = deepcopy(need)
    requests = pending_sequence_requests(store,'target',known,[],[('need',need)])
    assert [r['query_ref'] for r in requests]==['family1','family2']
    assert need==original


def test_parent_dispatch_identifies_each_actual_component_in_a_multi_component_need():
    store=Subjects({'target':'MDEAKG','componentT':'MKQQ','componentATPase':'MNNQKG'})
    need={'question':'Identify the two adjacent CDS products.',
        'required_information':'Actual sequence-to-reference or profile matches with mapped residues.',
        'available_record_refs':['componentT','componentATPase','neighborhood']}
    requests=pending_sequence_requests(store,'target',{'target','componentT','componentATPase','neighborhood','need'},
        [],[('need',need)],native_component_refs={'componentT','componentATPase'})
    assert {r['query_ref'] for r in requests}=={'componentT','componentATPase'}
    assert all(r['query_ref']!='target' for r in requests)


def test_parent_dispatch_external_domain_leads_keep_the_fused_target_as_query():
    store=Subjects({'target':'MDEAKG','domain1':'MDE','domain2':'AKG'})
    need={'question':'Map both domains on the supplied protein.',
        'required_information':'Native sequence correspondence and mapped domain boundaries.',
        'available_record_refs':['domain1','domain2']}
    requests=pending_sequence_requests(store,'target',{'target','domain1','domain2','need'},[],[('need',need)])
    assert len(requests)==1 and requests[0]['query_ref']=='target'
    assert requests[0]['reference_refs']==['domain1','domain2']
