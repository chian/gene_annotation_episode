"""A103 measurement custody, scoped attribution and honest missing context."""
from copy import deepcopy
import json
import math

import pytest
from scipy.stats import fisher_exact

from gene_annotation_episode.a103_attachments import refresh,received_attachments,component_link
from gene_annotation_episode.a103_credit import A103ContextCredit
from gene_annotation_episode.a103_publication import publish,received_measurement
from gene_annotation_episode.a103_scoring import compare_neighborhoods,cooccurrence,fisher_enrichment,fusion,pair_organization,digest
from gene_annotation_episode.domain import ContractError,canonical
from gene_annotation_episode.evidence_root import NativeEvidenceRootCredit
from gene_annotation_episode.state import Store
from a103_test_support import source,protein,genomic_file,binding,measured_neighborhood,native_pair


@pytest.fixture
def context_case(tmp_path):
    with Store(tmp_path/'state') as store:
        target, = store.create_problem(raw_sequence='MDEAKG',molecule='protein')['subject_refs']
        known = {target}
        a,ab = binding(store,genomic_file(tmp_path/'A.1.gb','A.1'),target,known,supplied=True)
        b,bb = binding(store,genomic_file(tmp_path/'B.1.gb','B.1',anchor='MEEAKG'),target,known)
        na,sa = measured_neighborhood(store,a,ab,known)
        nb,sb = measured_neighborhood(store,b,bb,known)
        definition = source(store,'engineering.a103.definition',{'relationship':'declared adjacent same-strand loci; no real function'})
        known.add(definition)
        rows = [{'neighborhood_ref':ref,'neighborhood':sheet,'left_feature_index':0,'right_feature_index':1,
                 'sampling_group':group} for ref,sheet,group in ((na,sa,'groupA'),(nb,sb,'groupB'))]
        pattern = {'maximum_gap_bp':20,'maximum_intervening_genes':0,'orientation':'same','order':'left_before_right'}
        raw = compare_neighborhoods(rows,pattern)
        raw.update(target_ref=target,target_regions=[[0,6]],partner_reference_ref=sa['cds'][1]['protein_reference_ref'],
            definition_source_refs=[definition],comparison_group='engineered-pair-panel',comparison_variant=digest(raw))
        yield store,target,known,a,ab,b,bb,na,sa,nb,sb,raw,definition


def grade(store,target,known):
    generated,needs = refresh(store,known,{'subject_refs':[target]})
    known.update(generated)
    return A103ContextCredit()(store,{'subject_refs':[target]},known_record_refs=known),needs


def test_locus_inventory_and_neighbor_sequence_identity_alone_are_not_context_credit(context_case):
    store,target,known,a,ab,b,bb,*_ = context_case
    native_pair(store,target,bb['protein_reference_ref'],known)
    result,needs = grade(store,target,known)
    assert result['credit']==0
    assert result['source_contribution_count']==0
    assert result['a103_sheet']['locus_binding'] and result['a103_sheet']['organization']


def test_late_specific_sequence_map_qualifies_only_its_existing_context_cells(context_case):
    store,target,known,a,ab,b,bb,na,sa,nb,sb,raw,definition = context_case
    measured = publish(store,raw,[target]); known.add(measured)
    before,needs = grade(store,target,known)
    assert before['credit']==pytest.approx(.5) and needs
    original_count = store.db.execute('SELECT count(*) FROM a103_publications').fetchone()[0]
    native_pair(store,target,bb['protein_reference_ref'],known)
    after,needs = grade(store,target,known)
    assert after['credit']==pytest.approx((1+5/6)/2)
    assert not needs
    assert store.db.execute('SELECT count(*) FROM a103_publications').fetchone()[0]==original_count
    association = next(r for r in after['tool_attachments'] if r['measurement_ref']==measured)
    assert association['rows'][1]['target_link']['locus_application']=='inferred_reference_locus_context'
    assert association['rows'][1]['target_link']['target_organism_inferred'] is False
    narrow = {target,association['source_ref']}
    assert A103ContextCredit()(store,{'subject_refs':[target]},known_record_refs=narrow)['credit']==after['credit']


def test_family_query_map_is_inverted_per_component_without_inventing_reverse_statistics(context_case):
    from gene_annotation_episode.sequence_attribution import sequence_link
    store,target,known,a,ab,b,bb,na,sa,nb,sb,raw,definition = context_case
    actual = ab['protein_reference_ref']
    expected = protein(store,'MMDEAKG',definition,'engineering-family-query');known.add(expected)
    observation = native_pair(store,expected,actual,known)
    native = sequence_link(store,expected,'MDEAKG',known,alignment_ref=observation)
    count = store.count('observation')
    link = component_link(store,actual,expected,known,alignment_ref=observation)
    assert link['state']=='evaluated' and link['factor']==pytest.approx(6/7)
    assert sorted(link['pairs'])==sorted([[j,i,b,a,s] for i,j,a,b,s in native['pairs']])
    assert link['pairs'][-1][:2]==[5,6]
    assert link['witnesses']==native['witnesses']
    assert link['native_statistics_direction']=={'query_ref':expected,'reference_sequence_ref':actual}
    local = component_link(store,actual,expected,known,positions=[3,4,5],alignment_ref=observation)
    assert {p[0] for p in local['pairs']}=={3,4,5}
    assert local['factor']==pytest.approx(3/7)
    assert store.count('observation')==count


def test_native_feature_placement_lifts_fragment_positions_without_a_new_alignment(context_case,tmp_path):
    from gene_annotation_episode.a103_scoring import bind_locus,binding_summary
    store,target,known,a,ab,b,bb,na,sa,nb,sb,raw,definition = context_case
    feature = store.put('feature',{'subject_ref':target,'kind':'sequence_region',
        'segments':[{'start':1,'end':5}],'strand':'.','context_refs':[]},origin='tool')['id']
    known.add(feature)
    body = bind_locus({'input_path':str(tmp_path/'A.1.gb'),'target_ref':target,
        'file_source_ref':ab['file_source_ref'],'accession':'A.1','selector':{'locus_tag':'anchor'},
        'format':'genbank','query_sequence':'DEAK','query_molecule':'protein'})
    body.update(target_regions=[[1,5]],material_ref=feature,supplied_target_genome=True,
        protein_reference_ref=ab['protein_reference_ref'])
    bound = publish(store,binding_summary(body),[target,feature])
    store.db.execute('INSERT INTO a103_bindings VALUES(?,?)',(bound,canonical(body)));known.add(bound)
    result,_ = grade(store,target,known)
    link = next(r['target_link'] for r in received_attachments(store,known) if r['measurement_ref']==bound)
    assert link['factor']==1 and link['route']=='native_exact_input_placement_in_acquired_cds_inventory'
    assert [p[:2] for p in link['pairs']]==[[1,1],[2,2],[3,3],[4,4]]
    assert store.count('observation')==0 and result['credit']==0


def test_comparison_of_another_cds_cannot_reuse_the_focal_placement(context_case,tmp_path):
    from gene_annotation_episode.a103_scoring import bind_locus,binding_summary
    store,target,known,a,ab,b,bb,na,sa,nb,sb,raw,definition=context_case
    body=bind_locus({'input_path':str(tmp_path/'A.1.gb'),'target_ref':target,
        'file_source_ref':ab['file_source_ref'],'accession':'A.1','selector':{'locus_tag':'anchor'},
        'format':'genbank','query_sequence':'MDEAKG','query_molecule':'protein'})
    assert body['native_input_placement']['state']=='unique'
    assert body['native_input_placement']['placements'][0]['feature_index']==0
    body.update(material_ref=target,supplied_target_genome=True,target_regions=[[0,6]],
        protein_reference_ref=ab['protein_reference_ref'])
    bound=publish(store,binding_summary(body),[target]);known.add(bound)
    store.db.execute('INSERT INTO a103_bindings VALUES(?,?)',(bound,canonical(body)))
    nref,neighborhood=measured_neighborhood(store,bound,body,known)
    measured=compare_neighborhoods([{'neighborhood_ref':nref,'neighborhood':neighborhood,
        'left_feature_index':1,'right_feature_index':0,'sampling_group':'one-genome'}],
        {**raw['definition'],'order':'any'})
    measured.update(target_ref=target,target_regions=[[0,6]],partner_reference_ref=ab['protein_reference_ref'],
        definition_source_refs=[definition],comparison_group='nonfocal-comparison',comparison_variant=digest(measured))
    ref=publish(store,measured,[target]);known.add(ref)
    result,_=grade(store,target,known)
    row=next(r for r in received_attachments(store,known) if r['measurement_ref']==ref)['rows'][0]
    assert row['target_link']['factor'] is None and row['qualified_value'] is None
    assert result['credit']==0


def test_identical_copies_do_not_make_a_selected_candidate_the_actual_target_locus(context_case,tmp_path):
    from gene_annotation_episode.a103_scoring import bind_locus
    from gene_annotation_episode.a103_attachments import target_link
    store,target,known,*_=context_case
    path=genomic_file(tmp_path/'COPIES.1.gb','COPIES.1',partner='MDEAKG')
    bound,body=binding(store,path,target,known,supplied=True)
    native=bind_locus({'input_path':str(path),'target_ref':target,'file_source_ref':body['file_source_ref'],
        'accession':'COPIES.1','selector':{'locus_tag':'anchor'},'format':'genbank',
        'query_sequence':'MDEAKG','query_molecule':'protein'})
    assert native['native_input_placement']['state']=='ambiguous'
    assert len(native['native_input_placement']['placements'])==2
    body['native_input_placement']=native['native_input_placement']
    link=target_link(store,target,body,known)
    assert link['factor'] is None and link['state']=='unresolved'
    assert link['target_organism_inferred'] is False
    assert link['native_placement']==native['native_input_placement']


def test_unrelated_strong_map_does_not_qualify_a_context_measurement(context_case):
    store,target,known,a,ab,b,bb,na,sa,nb,sb,raw,definition = context_case
    unrelated = protein(store,'MNNQKG',definition,'unrelated')
    native_pair(store,target,unrelated,known)
    measured = publish(store,raw,[target]); known.add(measured)
    result,needs = grade(store,target,known)
    assert result['credit']==.5 and needs


def test_synthesis_returns_received_retained_context_without_new_measurements(context_case):
    from gene_annotation_episode.a103_investigation import received_context_records,initial_report,resolve_report
    store,target,known,a,ab,b,bb,na,sa,nb,sb,raw,definition=context_case
    measured=publish(store,raw,[target]);known.add(measured)
    before,_=grade(store,target,known)
    grant=next(r for r in received_attachments(store,known) if r['measurement_ref']==measured)['source_ref']
    narrow={target,measured,grant}
    total=store.db.total_changes
    refs=received_context_records(store,narrow,{'subject_refs':[target]})
    report={**initial_report(),'context_summary':'association_measured','scope_status':'partial',
        'records':refs,'context_credit':before['credit']}
    resolved=resolve_report(store,report,scope={'subject_refs':[target]})
    assert resolved['receiving_scope_credit']==before['credit']==.5
    assert set(refs)==narrow and a not in refs and b not in refs
    assert store.db.total_changes==total


def test_measurement_redelivery_keeps_credit_without_admitting_an_unsupported_function(context_case):
    from gene_annotation_episode.a103_investigation import (received_context_records,initial_report,
        resolve_report,resolve_measurement_report)
    store,target,known,a,ab,b,bb,na,sa,nb,sb,raw,definition=context_case
    measured=publish(store,raw,[target]);known.add(measured)
    value,_=grade(store,target,known)
    report={**initial_report(),'context_summary':'association_measured','scope_status':'partial',
        'functional_support':'system_association','records':received_context_records(store,known,{'subject_refs':[target]}),
        'context_credit':value['credit']}
    total=store.db.total_changes
    with pytest.raises(ContractError,match='a103_function_interpretation_requires_explicit_hypothesis_and_assessment'):
        resolve_report(store,report,scope={'subject_refs':[target]})
    measurements={name:report[name] for name in ('records','context_credit')}
    assert resolve_measurement_report(store,measurements,scope={'subject_refs':[target]})==.5
    with pytest.raises(ContractError,match='a103_returned_measurement_credit_conflict'):
        resolve_measurement_report(store,{**measurements,'context_credit':1},scope={'subject_refs':[target]})
    assert store.db.total_changes==total


def _single_locus_comparison(case, right_index, partner_ref=None):
    store,target,known,a,ab,b,bb,na,sa,nb,sb,raw,definition = case
    result = compare_neighborhoods([{'neighborhood_ref':na,'neighborhood':sa,
        'left_feature_index':0,'right_feature_index':right_index,'sampling_group':'one-genome'}],raw['definition'])
    result.update(target_ref=target,target_regions=[[0,6]],
        partner_reference_ref=partner_ref or raw['partner_reference_ref'],definition_source_refs=[definition],
        comparison_group='engineering-late-detection',comparison_variant=digest(result))
    ref = publish(store,result,[target]);known.add(ref)
    return ref,result


def _detector_receipt(case, measured, **changes):
    """Host-publication contract fixture; no biological search is claimed."""
    store,target,known,*_ = case
    proof = {'schema':'a103_detection_v1','producer_operation':'context.detection_inventory',
        'target_ref':target,'target_regions':[[0,6]],'component_ref':measured['partner_reference_ref'],
        'neighborhood_ref':measured['rows'][0]['neighborhood_ref'],'present':False,
        'native_search_complete':True,'all_actual_cds_in_search':True,
        'scope':'engineering_exact_neighborhood_CDS_inventory',**changes}
    return publish(store,proof,[target])


def test_late_scoped_nondetection_resolves_retained_unknown_without_context_rerun(context_case):
    store,target,known,*_ = context_case
    ref,raw = _single_locus_comparison(context_case,None)
    before,needs = grade(store,target,known)
    first = next(r for r in before['tool_attachments'] if r['measurement_ref']==ref)
    assert first['bounds']==[0.,1.]
    assert first['required_operands'][0]['query_ref']==raw['partner_reference_ref']
    proof = _detector_receipt(context_case,raw)
    count = store.db.execute('SELECT count(*) FROM a103_publications').fetchone()[0]
    unreceived,_ = grade(store,target,known)
    assert next(r for r in unreceived['tool_attachments'] if r['measurement_ref']==ref)['bounds']==[0.,1.]
    known.add(proof)
    after,_ = grade(store,target,known)
    final = next(r for r in after['tool_attachments'] if r['measurement_ref']==ref)
    assert final['state']=='evaluated' and final['bounds']==[0.,0.]
    assert final['rows'][0]['raw_relationship_holds'] is None
    assert final['rows'][0]['relationship_holds'] is False
    assert final['rows'][0]['partner_link']['scope']=='exact_received_neighborhood_CDS_inventory_only'
    assert proof in final['evidence_refs']
    assert store.db.execute('SELECT count(*) FROM a103_publications').fetchone()[0]==count
    assert before['credit']==after['credit']==0


def test_runtime_parent_receives_exact_component_operands_from_automatic_grading(context_case):
    from types import SimpleNamespace
    from method_loop.identities import EpisodeRef
    from gene_annotation_episode.episode_bindings import BindingContext
    from gene_annotation_episode.runtime import Workflow
    from gene_annotation_episode.shared_information import SharedInformation
    store,target,known,a,ab,b,bb,na,sa,nb,sb,raw,definition = context_case
    expected = protein(store,'MNNQKG',definition,'engineering-required-family');known.add(expected)
    measured,raw = _single_locus_comparison(context_case,1,expected)
    store.db.execute('CREATE TABLE runtime_episodes (run_id TEXT,episode_id TEXT,path TEXT,request TEXT)')
    def context(path):
        path = tuple(map(tuple,path))
        episode = EpisodeRef('runtime-a103-needs',path).episode_id
        scope = {'subject_refs':[target]}
        request = {'message':{'scope':scope,'episode_assignment':{}}}
        store.db.execute('INSERT INTO runtime_episodes VALUES(?,?,?,?)',
            ('runtime-a103-needs',episode,canonical(path),canonical(request)))
        return BindingContext('runtime-a103-needs',episode,path[-1][0],path,scope,{},request)
    parent = context([['annotation','root']])
    child = context([['annotation','root'],['scientific_process','a103']])
    class Receipts:
        def known(self,episode):return list(known)
        def receive(self,episode,references,**kwargs):known.update(references)
    workflow = SimpleNamespace(store=store,run_id=child.run_id,receipts=Receipts(),
        tools=SimpleNamespace(received_attributions=lambda context,records:
            refresh(store,records,{'subject_refs':[target]})),binding_context=lambda source:child)
    source = SimpleNamespace(path=child.path,episode_id=child.episode_id)
    generated = Workflow.receive_tool_attributions(workflow,source,0,kind='own_action')
    assert generated
    needs = SharedInformation(store,child.run_id).context_view(parent)['needs']
    required = next(json.loads(row['required_information']) for row in needs
        if json.loads(row['required_information'])['measurement_or_request_ref']==measured)
    operand, = required['required_operands']
    assert operand['query_ref']==expected
    assert operand['neighborhood_ref']==na
    assert operand['actual_component_ref']==sa['cds'][1]['protein_reference_ref']
    assert A103ContextCredit()(store,{'subject_refs':[target]},known_record_refs=known)['credit']==0


@pytest.mark.parametrize('mismatch',['target','component','neighborhood','incomplete_search','incomplete_inventory','unknown'])
def test_detection_cannot_cross_its_subject_or_scope_or_promote_unknown_to_absence(context_case,mismatch):
    store,target,known,a,ab,b,bb,na,sa,nb,sb,raw,definition = context_case
    ref,raw = _single_locus_comparison(context_case,None)
    changes = {'target':{'target_ref':ab['protein_reference_ref']},
        'component':{'component_ref':target},'neighborhood':{'neighborhood_ref':nb},
        'incomplete_search':{'native_search_complete':False},
        'incomplete_inventory':{'all_actual_cds_in_search':False},'unknown':{'present':None}}[mismatch]
    known.add(_detector_receipt(context_case,raw,**changes))
    result,_ = grade(store,target,known)
    sheet = next(r for r in result['tool_attachments'] if r['measurement_ref']==ref)
    assert sheet['bounds']==[0.,1.] and sheet['state']=='partial'
    assert sheet['rows'][0]['relationship_holds'] is None


def test_family_nondetection_preserves_unrelated_neighbors_actual_geometry(context_case):
    store,target,known,a,ab,b,bb,na,sa,nb,sb,raw,definition = context_case
    expected = protein(store,'MNNQKG',definition,'engineering-other-family');known.add(expected)
    ref,raw = _single_locus_comparison(context_case,1,expected)
    before,_ = grade(store,target,known)
    old = next(r for r in before['tool_attachments'] if r['measurement_ref']==ref)
    assert old['bounds']==[0.,1.] and old['rows'][0]['relationship_holds'] is True
    known.add(_detector_receipt(context_case,raw))
    after,_ = grade(store,target,known)
    final = next(r for r in after['tool_attachments'] if r['measurement_ref']==ref)
    assert final['bounds']==[0.,0.]
    assert final['raw_value']==1 and final['rows'][0]['raw_relationship_holds'] is True
    assert final['rows'][0]['organization']['gap_bp']==9
    assert final['rows'][0]['relationship_holds'] is False


def test_scoped_nondetection_accepts_only_received_identical_query_aliases(context_case):
    store,target,known,a,ab,b,bb,na,sa,nb,sb,raw,definition=context_case
    ref,raw=_single_locus_comparison(context_case,None)
    alias=protein(store,'MKQQ',definition,'engineering-identical-query-alias')
    proof=_detector_receipt(context_case,raw,component_ref=alias)
    known.add(proof)
    before,_=grade(store,target,known)
    assert next(r for r in before['tool_attachments'] if r['measurement_ref']==ref)['bounds']==[0.,1.]
    known.add(alias)
    after,_=grade(store,target,known)
    sheet=next(r for r in after['tool_attachments'] if r['measurement_ref']==ref)
    assert sheet['bounds']==[0.,0.] and sheet['score']==0
    binding,=sheet['rows'][0]['partner_link']['query_bindings']
    assert binding['actual_query_ref']==alias and binding['required_query_ref']==raw['partner_reference_ref']
    assert binding['route']=='exact_received_query_peptide_identity'


def test_a_single_cds_cannot_mint_a_neighbor_association(context_case):
    store,target,known,a,ab,b,bb,na,sa,nb,sb,raw,definition=context_case
    with pytest.raises(ContractError,match='distinct_neighbor_cds_required'):
        compare_neighborhoods([{'neighborhood_ref':na,'neighborhood':sa,
            'left_feature_index':0,'right_feature_index':0,'sampling_group':'one'}],raw['definition'])
    assert A103ContextCredit()(store,{'subject_refs':[target]},known_record_refs=known)['credit']==0


@pytest.mark.parametrize('contradiction',['opposing_detection','verified_component'])
def test_conflicting_native_component_evidence_stays_unresolved(context_case,contradiction):
    store,target,known,*_ = context_case
    ref,raw = _single_locus_comparison(context_case,1 if contradiction=='verified_component' else None)
    known.add(_detector_receipt(context_case,raw))
    if contradiction=='opposing_detection':
        known.add(_detector_receipt(context_case,raw,present=True,all_actual_cds_in_search=False))
    result,_ = grade(store,target,known)
    sheet = next(r for r in result['tool_attachments'] if r['measurement_ref']==ref)
    assert sheet['bounds']==[0.,1.]
    assert sheet['rows'][0]['relationship_holds'] is None
    assert 'conflicting_specific_component_detection' in sheet['missing']


def test_coordinates_or_prose_cannot_mint_native_context_grades(context_case):
    store,target,known,*_ = context_case
    fake = source(store,'native.a103.measurement',{'context_score':1.,'target_ref':target})
    with pytest.raises(ContractError,match='scoring_grant_unavailable'):
        received_measurement(store,fake)
    assert A103ContextCredit()(store,{'subject_refs':[target]},known_record_refs=known)['credit']==0


def test_parent_recomputes_original_scope_and_credit_reads_have_no_grading_side_effect(context_case):
    store,target,known,a,ab,b,bb,na,sa,nb,sb,raw,definition = context_case
    raw.update(target_regions=[[0,3]])
    measured = publish(store,raw,[target]); known.add(measured)
    full,_ = grade(store,target,known)
    before = store.db.total_changes
    small = A103ContextCredit()(store,{'subject_refs':[target],'segments':[
        {'target_ref':target,'start':0,'end':3,'unit':'aa'}]},known_record_refs=known)
    assert full['credit']==.25 and small['credit']==.5
    assert store.db.total_changes==before
    root = NativeEvidenceRootCredit()(store,{'subject_refs':[target]},known_record_refs=known)
    assert root['axis_components']['A103']==full['credit']
    assert root['axis_components']['A101']==root['axis_components']['A102']==0
    assert root['credit']==full['credit']


def test_receiving_a_narrow_grade_does_not_require_or_implicitly_read_private_upstream_inputs(context_case):
    store,target,known,a,ab,b,bb,na,sa,nb,sb,raw,definition = context_case
    measured = publish(store,raw,[target]);known.add(measured)
    result,_ = grade(store,target,known)
    attachment = next(r for r in result['tool_attachments'] if r['measurement_ref']==measured)
    narrow = {target,measured,attachment['source_ref']}
    generated,_ = refresh(store,narrow,{'subject_refs':[target]})
    assert not generated
    assert A103ContextCredit()(store,{'subject_refs':[target]},known_record_refs=narrow)['credit']==result['credit']


def test_genomic_input_and_gff3_bind_real_nucleotide_placements_without_inventing_a_protein_target(tmp_path):
    from Bio import SeqIO
    from gene_annotation_episode.a103_scoring import bind_locus,parse_records
    path = genomic_file(tmp_path/'DNA.1.gb','DNA.1')
    record = next(SeqIO.parse(path,'genbank'))
    query = str(record.features[0].extract(record.seq))
    body = bind_locus({'input_path':str(path),'target_ref':'engineering','file_source_ref':'engineering',
        'accession':'DNA.1','selector':{'locus_tag':'anchor'},'format':'genbank',
        'query_sequence':query,'query_molecule':'dna'})
    placement = body['native_input_placement']
    assert placement['state']=='unique' and placement['placements'][0]['reference_start']==100
    gff = '##gff-version 3\nDNA.1\tfixture\tCDS\t101\t121\t.\t+\t0\tID=cds;Parent=gene;protein_id=protein\n##FASTA\n>DNA.1\n'+str(record.seq)+'\n'
    parsed = parse_records(gff,format='gff3',genetic_code=11)
    assert len(parsed)==1 and parsed[0].features[0].qualifiers['locus_tag']==['gene']
    assert str(parsed[0].features[0].extract(parsed[0].seq))==query


def test_fragment_placement_retains_its_exact_offset_and_duplicate_loci_stay_ambiguous(tmp_path):
    from gene_annotation_episode.a103_scoring import bind_locus
    path = genomic_file(tmp_path/'FRAGMENT.1.gb','FRAGMENT.1')
    request = {'input_path':str(path),'target_ref':'engineering','file_source_ref':'engineering',
        'accession':'FRAGMENT.1','selector':{'locus_tag':'anchor'},'format':'genbank',
        'query_sequence':'DEAK','query_molecule':'protein'}
    body = bind_locus(request)
    assert body['native_input_placement']['state']=='unique'
    assert body['native_input_placement']['placements'][0]['reference_start']==1
    repeated = genomic_file(tmp_path/'REPEATED.1.gb','REPEATED.1',partner='MDEAKG')
    body = bind_locus({**request,'input_path':str(repeated),'accession':'REPEATED.1'})
    assert body['native_input_placement']['state']=='ambiguous'


def test_circular_compound_gene_uses_its_actual_origin_spanning_arc(tmp_path):
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqFeature import SimpleLocation,CompoundLocation
    from gene_annotation_episode.a103_scoring import bind_locus,neighborhood
    path = genomic_file(tmp_path/'CIRCLE.1.gb','CIRCLE.1',circular=True)
    record = next(SeqIO.parse(path,'genbank'))
    anchor = str(record.features[0].extract(record.seq));partner = str(record.features[1].extract(record.seq))
    data = list('A'*400)
    data[390:] = anchor[:10];data[:11] = anchor[10:];data[20:20+len(partner)] = partner
    record.seq = Seq(''.join(data))
    record.features[0].location = CompoundLocation([SimpleLocation(390,400,strand=1),SimpleLocation(0,11,strand=1)])
    record.features[1].location = SimpleLocation(20,20+len(partner),strand=1)
    SeqIO.write(record,path,'genbank')
    body = bind_locus({'input_path':str(path),'target_ref':'engineering','file_source_ref':'engineering',
        'accession':'CIRCLE.1','selector':{'locus_tag':'anchor'},'format':'genbank'})
    sheet = neighborhood(body,20,100)
    measured = pair_organization(sheet,0,1)
    assert measured['gap_bp']==9 and measured['overlap_bp']==0
    assert measured['orientation']=='same' and measured['right_direction_from_left']==1


def test_bound_cds_disambiguates_gene_with_different_native_extent(tmp_path):
    from Bio import SeqIO
    from Bio.SeqFeature import SeqFeature,SimpleLocation
    from gene_annotation_episode.a103_scoring import bind_locus,neighborhood
    path=genomic_file(tmp_path/'GENE.1.gb','GENE.1')
    record=next(SeqIO.parse(path,'genbank'))
    record.features.insert(0,SeqFeature(SimpleLocation(100,125,strand=1),type='gene',qualifiers={'locus_tag':['anchor']}))
    SeqIO.write(record,path,'genbank')
    body=bind_locus({'input_path':str(path),'target_ref':'engineering','file_source_ref':'engineering',
        'accession':'GENE.1','selector':{'locus_tag':'anchor'},'format':'genbank'})
    sheet=neighborhood(body,100,200)
    assert sheet['raw_neighborhood']['context_status']=='available'
    assert [r['source_feature_index'] for r in sheet['cds']]==[1,2]


def test_same_genome_cannot_be_split_into_independent_sampling_groups(context_case):
    *_,raw,definition = context_case
    store,target,known,a,ab,b,bb,na,sa,nb,sb,_,_ = context_case
    rows = [dict(neighborhood_ref=na,neighborhood=sa,left_feature_index=0,right_feature_index=1,sampling_group='A'),
            dict(neighborhood_ref=na,neighborhood=sa,left_feature_index=0,right_feature_index=1,sampling_group='B')]
    with pytest.raises(ContractError,match='same_genome_conflicting_sampling_groups'):
        compare_neighborhoods(rows,raw['definition'])


def test_protein_domain_traits_lift_to_original_nucleotide_codons(tmp_path):
    from gene_annotation_episode.a103_scoring import binding_summary
    with Store(tmp_path/'state') as store:
        target, = store.create_problem(raw_sequence='ATGGATGAAGCTAAAGGTTAA',molecule='dna')['subject_refs']
        known = {target}
        from gene_annotation_episode.tools import ToolRegistry
        translation = ToolRegistry(store).execute('sequence.translate',
            {'subject_ref':target,'code':11,'cds':True},operation_key='actual-codon-translation')
        assert translation['status']=='completed',translation
        product = translation['result']['records'][0]['product_ref']
        parent_source = store.get(product)['mapping_source_ref']
        known.update({parent_source,product})
        old,body = binding(store,genomic_file(tmp_path/'CODONS.1.gb','CODONS.1'),target,known,supplied=True)
        body.update(material_ref=product,target_regions=[[0,18]])
        bound = publish(store,binding_summary(body),[target,product])
        store.db.execute('INSERT INTO a103_bindings VALUES(?,?)',(bound,canonical(body)));known.add(bound)
        left = protein(store,'MDE',parent_source,'codon-left');right = protein(store,'AKG',parent_source,'codon-right')
        known.update({left,right})
        regions = [dict(start=0,end=3,component_ref=left,alignment_ref=None),dict(start=3,end=6,component_ref=right,alignment_ref=None)]
        raw = fusion(body,regions)
        raw.update(target_ref=target,target_regions=[[0,18]],binding_ref=bound,definition_source_refs=[parent_source],
            comparison_group='codon-fusion',comparison_variant='actual-codons')
        ref = publish(store,raw,[target]);known.add(ref)
        value,_ = grade(store,target,known)
        sheet = next(r for r in value['tool_attachments'] if r['measurement_ref']==ref)
        assert sheet['score']==1 and value['credit']==pytest.approx(18/21)
        assert sheet['regions'][0]['target_positions']==list(range(9))
        assert sheet['regions'][1]['target_positions']==list(range(9,18))


def test_contrast_regrades_from_received_maps_without_new_context_measurements(context_case):
    store,target,known,a,ab,b,bb,na,sa,nb,sb,raw,definition = context_case
    first = publish(store,raw,[target]);known.add(first)
    opposite = deepcopy(raw)
    opposite.update(comparison_group='opposing-pattern',comparison_variant='opposing-geometry')
    opposite['rows'][1]['relationship_holds'] = False
    second = publish(store,opposite,[target]);known.add(second)
    grade(store,target,known)
    function = store.put('term',{'namespace':'engineering','accession':'bounded-context-role','label':'Engineering alternative',
        'term_type':'other','source_ref':definition,'anchor':None},origin='external')['id'];known.add(function)
    panel = {'schema':'a103_contrast_v1','producer_operation':'context.contrast','target_ref':target,'target_regions':[[0,6]],
        'function_ref':function,'supporting_source_refs':[first],'opposing_source_refs':[second],
        'incompatibility_witness_refs':[definition]}
    contrast = publish(store,panel,[target]);known.add(contrast)
    before,_ = grade(store,target,known)
    old_panel = before['a103_sheet']['functional_contrast'][0]['qualified_panel']
    count = store.db.execute('SELECT count(*) FROM a103_publications').fetchone()[0]
    native_pair(store,target,bb['protein_reference_ref'],known)
    after,_ = grade(store,target,known)
    new_panel = after['a103_sheet']['functional_contrast'][0]['qualified_panel']
    assert old_panel['contrast_bounds'][0]==0
    assert new_panel['contrast']==pytest.approx(5/12)
    assert new_panel['contrast_bounds'][0]==pytest.approx(5/12)
    assert after['credit']==pytest.approx(11/12)
    assert store.db.execute('SELECT count(*) FROM a103_publications').fetchone()[0]==count


def test_duplicate_measurements_do_not_add_credit_and_conflicting_variants_stay_unresolved(context_case):
    store,target,known,a,ab,b,bb,na,sa,nb,sb,raw,definition = context_case
    first = publish(store,raw,[target]);known.add(first)
    assert publish(store,raw,[target])==first
    one,_ = grade(store,target,known)
    assert one['credit']==.5
    changed = deepcopy(raw)
    changed.update(comparison_variant='competing-native-variant',group_balanced_fraction=0.)
    for row in changed['rows']:row['relationship_holds']=False
    second = publish(store,changed,[target]);known.add(second)
    result,_ = grade(store,target,known)
    assert result['credit']==0
    assert result['target_sheets'][target]['unresolved_variant_groups']==['engineered-pair-panel']


def test_organization_keeps_signed_overlap_orientation_and_gene_counts(context_case):
    *_,sheet,raw,definition = context_case
    pair = pair_organization(sheet,0,1)
    assert pair['gap_bp']==9 and pair['orientation']=='same' and pair['intervening_annotated_cds']==0
    changed = deepcopy(sheet)
    changed['cds'][1]['strand']='-'
    assert pair_organization(changed,0,1)['orientation']=='convergent'
    changed['cds'][1]['segments']=[[115,130]]
    result = pair_organization(changed,0,1)
    assert result['gap_bp']==-6 and result['overlap_bp']==6


@pytest.mark.parametrize('counts',[(3,1,1,3),(8,2,1,9),(1,7,6,2),(0,4,3,8)])
def test_exact_association_test_matches_an_independent_statistics_implementation(counts):
    a,b,c,d = counts
    assert fisher_enrichment(*counts)==pytest.approx(fisher_exact([[a,b],[c,d]],alternative='greater').pvalue)


def test_related_genomes_and_unknown_detections_do_not_create_independent_significance():
    rows = [dict(genome_key=str(i),sampling_group='same-clade' if i<2 else str(i),
        left_present=i<2,right_present=i<2) for i in range(4)]
    result = cooccurrence(rows)
    assert result['p_value'] is not None and result['native_significance_index'] is None
    rows[0]['right_present']=None
    result = cooccurrence(rows)
    assert result['unknown_genomes']==1 and sum(result['contingency'].values())==3


def test_fusion_traits_attach_to_their_required_subparts(context_case):
    store,target,known,a,ab,b,bb,na,sa,nb,sb,raw,definition = context_case
    left = protein(store,'MDE',definition,'left-domain')
    right = protein(store,'AKG',definition,'right-domain')
    known.update({left,right})
    regions = [dict(start=0,end=3,component_ref=left,alignment_ref=None),
               dict(start=3,end=6,component_ref=right,alignment_ref=None)]
    measured = fusion(ab,regions)
    measured.update(target_ref=target,target_regions=[[0,6]],binding_ref=a,
        definition_source_refs=[definition],comparison_group='one-fusion',comparison_variant='actual-domains')
    ref = publish(store,measured,[target]);known.add(ref)
    result,needs = grade(store,target,known)
    attachment = next(r for r in result['tool_attachments'] if r['measurement_ref']==ref)
    assert attachment['score']==1
    assert attachment['regions'][0]['target_positions']==[0,1,2]
    assert attachment['regions'][1]['target_positions']==[3,4,5]
    assert all(store.get(r['target_feature_ref'])['record_type']=='feature' for r in attachment['regions'])
    assert store.count('annotation')==store.count('hypothesis')==0
