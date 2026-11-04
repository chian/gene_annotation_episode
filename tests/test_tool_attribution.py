"""Engineering fixtures exercise attribution; they are not real native runs."""
from copy import deepcopy
import json
import math

import pytest

from gene_annotation_episode.a102_attachments import request,refresh,received_attachments
from gene_annotation_episode.a102_credit import A102StructuralCredit
from gene_annotation_episode.a102_native_worker import _native
from gene_annotation_episode.a102_publication import publish_comparison
from gene_annotation_episode.a102_structures import bind_structure,binding_summary
from gene_annotation_episode.a102_tools import A102ToolRegistry
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.a102_scoring import digest
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import retain_tool_grading


AMINO={'M':'MET','D':'ASP','E':'GLU','A':'ALA','K':'LYS','G':'GLY','N':'ASN','Q':'GLN'}


def binding(registry,sequence,*,target=None,shift=0.,chain='A',data=None):
    if data is None:
        data=(''.join(f'ATOM  {i+1:5d}  CA  {AMINO[a]:3s} {chain}{i+1:4d}    '
            f'{float(i):8.3f}{float(i%2)+shift:8.3f}{float(i%3):8.3f}  1.00 20.00           C  \n'
            for i,a in enumerate(sequence))+'TER\nEND\n').encode()
    artifact=registry.store.artifact(data,'chemical/x-pdb')
    file=registry.store.put('source',{'provider':'engineering.coordinate_fixture','accession':None,'uri':None,
        'artifact_ref':artifact,'text_ref':None,'request_ref':None,'version':'test','retrieved_at':None},origin='tool')['id']
    body=bind_structure(data,{'format':'pdb_3x_text','artifact_ref':artifact,'file_source_ref':file,
        'target_ref':target,'supplied_sequence':sequence if target else None,'block_ordinal':0,
        'model_ordinal':0,'chain_id':chain,'model_metadata':{'origin':'supplied_unknown'}})
    ref=registry._source('native.a102.structure_binding',binding_summary(body))
    registry.store.db.execute('INSERT INTO a102_structure_bindings VALUES(?,?)',(ref,canonical(body)))
    return ref,body


def alignment(store,target,query,reference,*,bits=50.,subset=None,reference_start=0,subject=None):
    """Explicit synthetic grader cells with real residue identities."""
    artifact=store.artifact(reference,'text/plain')
    origin=store.put('source',{'provider':'engineering.reference_fixture','accession':None,'uri':None,
        'artifact_ref':artifact,'text_ref':None,'request_ref':None,'version':'test','retrieved_at':None},origin='tool')['id']
    ref=store.put('reference',{'reference_type':'protein','source_ref':origin,'accession':'engineering-'+reference,
        'label':'Engineering fixture','sequence_ref':artifact,'molecule':'protein','length':len(reference),
        'term_refs':[],'context_refs':[]},origin='tool')['id']
    start,end=subset or (0,len(query))
    key='engineering-domain'
    grading={'sheet':{'schema':'hmmer_search_sheet_v1','operation':{'program':'phmmer'},
        'domains':[{'record_key':key,'target_name':'engineering-'+reference,
            'alignment':{'model':query[start:end],'aseq':reference[reference_start+start:reference_start+end]}}]},
        'scores':{'schema':'hmmer_search_scores_v1','domains':[{'record_key':key,
            'intervals':{'model':[start,end],'sequence':[reference_start+start,reference_start+end]},'paired_positions':end-start,
            'sequence_length':len(reference),'model_length':len(query),'native_domain_score_bits':bits,
            'native_independent_evalue':1e-10,'sequence_identity_fraction':sum(a==b for a,b in zip(query[start:end],reference[reference_start+start:reference_start+end]))/(end-start)}]}}
    native=store.artifact('Engineering-only native grading fixture','text/plain')
    grade=retain_tool_grading(store,provider='native.phmmer.alignment',native_artifact_ref=native,grading=grading)
    source=store.put('source',{'provider':'native.phmmer.alignment','accession':digest([bits,reference,subset]),'uri':None,
        'artifact_ref':native,'text_ref':None,'request_ref':None,'version':'engineering_fixture',
        'retrieved_at':None,'auxiliary_artifact_refs':[grade]},origin='tool')['id']
    obs=store.put('observation',{'subject_refs':[subject or target],'source_subject_refs':[ref],'kind':'alignment',
        'source_ref':source,'measurements':[],'dependencies':[subject or target,ref],'anchor':None},origin='tool')['id']
    return {obs,source,ref,origin,subject or target},obs


def comparison(registry,qref,q,tref,t,*,direct=False):
    subject=q['target_ref'] if direct else qref
    native=_native({'target_binding_ref':qref,'reference_binding_ref':tref,
        'comparison_group':qref+tref,'variant_ref':qref+tref,'primary':True},
        {**q,'target_ref':subject},t,[(i,i) for i in range(len(q['coordinates']))],
        [[1.,0,0],[0,1.,0],[0,0,1.]],[0.,0,0.],{},'US-align',{'version':'engineering-fixture'})
    return publish_comparison(registry.store,native)['source_ref']


@pytest.fixture
def case(tmp_path):
    with Store(tmp_path/'state') as store:
        target,=store.create_problem(raw_sequence='MDEAKG',molecule='protein')['subject_refs']
        registry=A102ToolRegistry(store,a102_work_directory=tmp_path/'native')
        y,ybody=binding(registry,'MDDAKG')
        z,zbody=binding(registry,'MDDAKG',shift=.1)
        native=comparison(registry,y,ybody,z,zbody)
        known={target,y,z,native}
        yield store,registry,target,y,z,native,known


def fold_request(store,target,y,native):
    return request(store,{'operation':'structure.reference_align','target_ref':target,
        'measurement_ref':native,'measured_binding_ref':y,'regions':[[0,6]],'sequence_alignment_ref':None},[target,y,native])


def test_exact_entity_link_is_required_and_updates_without_another_measurement(case):
    store,registry,target,y,z,native,known=case
    req=fold_request(store,target,y,native);known.add(req);scope={'subject_refs':[target]}
    added,needs=refresh(store,known,scope);known.update(added)
    assert needs and A102StructuralCredit()(store,scope,known_record_refs=known)['credit']==0
    wrong,_=alignment(store,target,'MDEAKG','MNNQKG',bits=500.)
    added,_=refresh(store,known|wrong,scope)
    assert A102StructuralCredit()(store,scope,known_record_refs=known|wrong|set(added))['credit']==0
    correct,_=alignment(store,target,'MDEAKG','MDDAKG')
    added,needs=refresh(store,known|correct,scope);known.update(correct|set(added))
    assert not needs
    result=A102StructuralCredit()(store,scope,known_record_refs=known)
    expected=1/(1+(.1/2)**2)*(1-math.exp(-1))*5/6
    assert result['credit']==pytest.approx(expected)
    assert result['target_sheets'][target]['native_value']==0
    attachment=next(r for r in result['tool_attachments'] if r['producer_operation']=='structure.reference_align')
    assert attachment['sequence_link']['witnesses'][0]['bits']==50
    assert attachment['region_scores'][0]['local_sequence_distance']['sequence_distance']==pytest.approx(1/6)
    again,_=refresh(store,known,scope)
    assert set(again)<=known
    assert A102StructuralCredit()(store,scope,known_record_refs=list(known)*2)['credit']==result['credit']


def test_direct_target_geometry_does_not_depend_on_sequence_axis(case):
    store,registry,target,y,z,native,known=case
    x,xbody=binding(registry,'MDEAKG',target=target,shift=.2)
    t=json.loads(store.db.execute('SELECT body FROM a102_structure_bindings WHERE source_ref=?',(z,)).fetchone()[0])
    direct=comparison(registry,x,xbody,z,t,direct=True);known.update({x,direct})
    req=fold_request(store,target,y,native);known.add(req)
    added,needs=refresh(store,known,{'subject_refs':[target]});known.update(added)
    result=A102StructuralCredit()(store,{'subject_refs':[target]},known_record_refs=known)
    assert needs and result['credit']==pytest.approx(1/(1+(.1/2)**2))
    assert any(r['policy']=='direct_native_geometry_v1' and r['state']=='direct' for r in result['tool_attachments'])


def trait(key,kind,positions,definition,**changes):
    return {'physical_feature_key':key,'kind':kind,'reference_positions':positions,
        'chemical_role':None,'allowed_symbols':None,'measurement_source_ref':None,
        'definition_source_refs':[definition],**changes}


def test_residue_chemical_motif_and_discontinuous_traits_belong_to_subparts(case):
    store,registry,target,y,z,native,known=case
    refs,_=alignment(store,target,'MDEAKG','MDDAKG');known.update(refs)
    definition=registry._source('engineering.trait_definition',{'meaning':'Engineering tests only, not a functional characterization.'})
    rows=[trait('residue','residue_identity',[2],definition),
        trait('acidic-role','chemical_role',[2],definition,chemical_role='acidic'),
        trait('discontinuous-motif','motif',[1,2,5],definition,allowed_symbols=['DE','DE','G']),
        trait('region','region_identity',[1,2],definition)]
    req=request(store,{'operation':'structure.reference_traits','target_ref':target,'reference_binding_ref':y,
        'sequence_alignment_ref':None,'comparison_source_ref':None,'traits':rows},[target,y,definition])
    known.update({req,definition});added,needs=refresh(store,known,{'subject_refs':[target]});known.update(added)
    sheets={r['physical_feature_key']:r for r in received_attachments(store,known)}
    assert not needs
    assert sheets['residue']['score']==0
    assert sheets['acidic-role']['trait_match']==1
    assert sheets['discontinuous-motif']['trait_match']==1
    assert sheets['region']['trait_match']==.5
    assert sheets['acidic-role']['score']==pytest.approx(1-math.exp(-1))
    motif=store.get(sheets['discontinuous-motif']['target_feature_ref'])
    assert motif['segments']==[{'start':1,'end':2},{'start':2,'end':3},{'start':5,'end':6}]
    site=store.get(sheets['acidic-role']['target_feature_ref'])
    assert site['kind']=='protein_site' and site['segments']==[{'start':2,'end':3}]
    observations=[store.get(ref) for ref in added if store.get(ref)['record_type']=='observation']
    assert all(store.get(row['subject_refs'][0])['record_type']=='feature' for row in observations)
    assert store.count('annotation')==store.count('hypothesis')==0
    assert A102StructuralCredit()(store,{'subject_refs':[target]},known_record_refs=known)['credit']==0


def test_missing_local_position_keeps_required_denominator_and_other_trait(case):
    store,registry,target,y,z,native,known=case
    refs,_=alignment(store,target,'MDEAKG','MDDAKG',subset=(0,3));known.update(refs)
    definition=registry._source('engineering.trait_definition',{'meaning':'Known and unobserved local positions.'})
    req=request(store,{'operation':'structure.reference_traits','target_ref':target,'reference_binding_ref':y,
        'sequence_alignment_ref':None,'comparison_source_ref':None,'traits':[
            trait('known','residue_identity',[0],definition),trait('partial','region_identity',[0,5],definition)]},[target,y,definition])
    known.update({req,definition});added,needs=refresh(store,known,{'subject_refs':[target]});known.update(added)
    sheets={r['physical_feature_key']:r for r in received_attachments(store,known)}
    strength=1-math.exp(-1)
    assert sheets['known']['trait_match']==1
    assert sheets['partial']['score'] is None and sheets['partial']['bounds']==pytest.approx([strength/2,(strength+1)/2])
    assert sheets['partial']['target_positions']==[0,None] and needs


def test_local_structural_map_can_support_a_trait_without_global_sequence_link(case):
    store,registry,target,y,z,native,known=case
    x,xbody=binding(registry,'MDEAKG',target=target,shift=.2)
    ybody=json.loads(store.db.execute('SELECT body FROM a102_structure_bindings WHERE source_ref=?',(y,)).fetchone()[0])
    direct=comparison(registry,x,xbody,y,ybody,direct=True)
    definition=registry._source('engineering.trait_definition',{'meaning':'Local structural correspondence.'})
    req=request(store,{'operation':'structure.reference_traits','target_ref':target,'reference_binding_ref':y,
        'sequence_alignment_ref':None,'comparison_source_ref':direct,
        'traits':[trait('acidic','chemical_role',[2],definition,chemical_role='acidic')]},[target,y,direct,definition])
    known.update({x,direct,definition,req});added,needs=refresh(store,known,{'subject_refs':[target]});known.update(added)
    result=next(r for r in received_attachments(store,known) if r.get('physical_feature_key')=='acidic')
    assert result['score']==1 and result['correspondence']['route']=='native_structural_residue_correspondence'
    assert not needs


def test_shape_trait_uses_target_geometry_and_allows_changed_residue_identity(case):
    store,registry,target,y,z,native,known=case
    definition=registry._source('engineering.trait_definition',{'meaning':'A local geometric constraint, not a whole-protein function.'})
    function=store.put('term',{'namespace':'engineering','accession':'shape','label':'Shape constraint',
        'term_type':'other','source_ref':definition,'anchor':None},origin='external')['id']
    known.update({definition,function})
    result,refs=registry._features({'comparison_source_ref':native,'function_ref':function,
        'definition_source_refs':[definition],'features':[{'physical_feature_key':'shape-site','state':'measure',
            'target_position':2,'reference_position':2,'target_atom':'CA','reference_atom':'CA',
            'witness_refs':[definition],'reason':'Engineering-only local geometry.'}]},known,{'subject_refs':[target]})
    known.update(refs)
    data=(''.join(f'ATOM  {i+1:5d}  CA  {AMINO[a]:3s} A{i+1:4d}    '
        f'{float(i):8.3f}{float(i%2)+(2. if i==2 else 0.):8.3f}{float(i%3):8.3f}  1.00 20.00           C  \n'
        for i,a in enumerate('MDEAKG'))+'TER\nEND\n').encode()
    x,xbody=binding(registry,'MDEAKG',target=target,data=data)
    ybody=json.loads(store.db.execute('SELECT body FROM a102_structure_bindings WHERE source_ref=?',(y,)).fetchone()[0])
    direct=comparison(registry,x,xbody,y,ybody,direct=True)
    req=request(store,{'operation':'structure.reference_traits','target_ref':target,'reference_binding_ref':y,
        'sequence_alignment_ref':None,'comparison_source_ref':direct,'traits':[
            trait('shape-site','geometry_constraint',[2],definition,measurement_source_ref=result['feature_source_ref'])]},[target,y,direct,definition])
    known.update({x,direct,req});added,_=refresh(store,known,{'subject_refs':[target]});known.update(added)
    sheet=next(r for r in received_attachments(store,known) if r.get('physical_feature_key')=='shape-site')
    assert sheet['target_symbols']=='E' and sheet['reference_symbols']=='D'
    assert sheet['target_geometry']['distance_A']==pytest.approx(1.9)
    assert sheet['score']==pytest.approx(1/(1+1.9**2))
    assert sheet['inference_kind']=='measured_target_model_shape_trait'
    assert sheet['target_geometry']['fit']=='existing_native_transforms_composed_without_refit'


def test_interface_requires_both_component_attachments_and_keeps_assembly_limit(case):
    store,registry,target,y,z,native,known=case
    data=(''.join(f'ATOM  {ordinal*6+i+1:5d}  CA  {AMINO[a]:3s} {chain}{i+1:4d}    '
        f'{float(i):8.3f}{float(i%2)+ordinal*3:8.3f}{float(i%3):8.3f}  1.00 20.00           C  \n'
        for ordinal,chain in enumerate(('A','B')) for i,a in enumerate('MDEAKG'))+'TER\nEND\n').encode()
    left,_=binding(registry,'MDEAKG',target=target,data=data,chain='A')
    right,_=binding(registry,'MDEAKG',target=target,data=data,chain='B')
    definition=registry._source('engineering.interface_definition',{'meaning':'A coordinate contact maximum, not a demonstrated biological assembly.'})
    known.update({left,right,definition})
    args={'binding_refs':[left,right],'target_refs':[target,None],'contacts':[{
        'physical_feature_key':'contact','left_position':2,'left_atom':'CA','right_position':2,'right_atom':'CA',
        'maximum_distance_A':4.,'definition_source_refs':[definition]}]}
    raw,refs=registry._interface(args,known,{'subject_refs':[target]});known.update(refs)
    added,needs=refresh(store,known,{'subject_refs':[target]});known.update(added)
    sheets=received_attachments(store,known)
    unresolved=next(r for r in sheets if r.get('measurement_ref')==raw['interface_source_ref'])
    assert raw['raw_score']==1 and raw['contacts'][0]['distance_A']==3
    assert unresolved['score'] is None and needs
    args['target_refs']=[target,target]
    raw,refs=registry._interface(args,known,{'subject_refs':[target]});known.update(refs)
    added,_=refresh(store,known,{'subject_refs':[target]});known.update(added)
    complete=next(r for r in received_attachments(store,known) if r.get('measurement_ref')==raw['interface_source_ref'])
    assert complete['score']==1 and 'unestablished' in complete['assembly_context']


def test_region_query_coordinates_are_lifted_before_local_trait_attribution(case):
    store,registry,target,y,z,native,known=case
    region=store.put('feature',{'subject_ref':target,'kind':'sequence_region','segments':[{'start':2,'end':6}],
        'strand':'.','context_refs':[]},origin='tool')['id']
    refs,_=alignment(store,target,'EAKG','MDDAKG',reference_start=2,subject=region);known.update(refs)
    definition=registry._source('engineering.trait_definition',{'meaning':'A region-query site, not a whole-sequence query.'})
    req=request(store,{'operation':'structure.reference_traits','target_ref':target,'reference_binding_ref':y,
        'sequence_alignment_ref':None,'comparison_source_ref':None,
        'traits':[trait('region-acidic-site','chemical_role',[2],definition,chemical_role='acidic')]},[target,y,definition])
    known.update({req,definition});added,needs=refresh(store,known,{'subject_refs':[target]});known.update(added)
    sheet=next(r for r in received_attachments(store,known) if r.get('physical_feature_key')=='region-acidic-site')
    assert not needs and sheet['target_positions']==[2] and sheet['trait_match']==1
    assert store.get(sheet['target_feature_ref'])['segments']==[{'start':2,'end':3}]


def test_conflicting_site_maps_do_not_disable_other_sites_or_native_fold(case):
    store,registry,target,y,z,native,known=case
    x,xbody=binding(registry,'MDEAKG',target=target,shift=.2)
    ybody=json.loads(store.db.execute('SELECT body FROM a102_structure_bindings WHERE source_ref=?',(y,)).fetchone()[0])
    direct=comparison(registry,x,xbody,y,ybody,direct=True)
    refs,_=alignment(store,target,'MDEAKG','MDDAKG',subset=(1,2),reference_start=1);known.update(refs)
    definition=registry._source('engineering.trait_definition',{'meaning':'Compare a consistent site and a locally conflicting site.'})
    req=request(store,{'operation':'structure.reference_traits','target_ref':target,'reference_binding_ref':y,
        'sequence_alignment_ref':None,'comparison_source_ref':direct,'traits':[
            trait('consistent','residue_identity',[0],definition),trait('conflicting','chemical_role',[2],definition,chemical_role='acidic')]},[target,y,direct,definition])
    known.update({x,direct,req,definition});added,needs=refresh(store,known,{'subject_refs':[target]});known.update(added)
    sheets={r['physical_feature_key']:r for r in received_attachments(store,known) if r.get('physical_feature_key')}
    assert sheets['consistent']['score']==1
    assert sheets['conflicting']['score'] is None and needs
    assert A102StructuralCredit()(store,{'subject_refs':[target]},known_record_refs=known)['credit']>0


def test_sequence_only_mapping_conflicts_remain_local_to_affected_traits(case):
    store,registry,target,y,z,native,known=case
    main,_=alignment(store,target,'MDEAKG','MDDAKG')
    competing,_=alignment(store,target,'MDEAKG','MDDAKG',subset=(1,2),reference_start=1)
    definition=registry._source('engineering.trait_definition',{'meaning':'One ambiguous site with an unaffected local trait.'})
    req=request(store,{'operation':'structure.reference_traits','target_ref':target,'reference_binding_ref':y,
        'sequence_alignment_ref':None,'comparison_source_ref':None,'traits':[
            trait('stable','residue_identity',[0],definition),
            trait('ambiguous','chemical_role',[2],definition,chemical_role='acidic')]},[target,y,definition])
    fold=fold_request(store,target,y,native)
    known.update({req,fold,definition,*main,*competing})
    added,needs=refresh(store,known,{'subject_refs':[target]});known.update(added)
    sheets={r['physical_feature_key']:r for r in received_attachments(store,known) if r.get('physical_feature_key')}
    assert sheets['stable']['score']==pytest.approx(1-math.exp(-1))
    assert sheets['stable']['missing']==[]
    assert sheets['stable']['correspondence']['required_scope_state']=='evaluated'
    assert sheets['ambiguous']['score'] is None and needs
    assert next(r for r in received_attachments(store,known)
        if r['producer_operation']=='structure.reference_align')['score'] is None
    assert A102StructuralCredit()(store,{'subject_refs':[target]},known_record_refs=known)['credit']==0


def test_existing_real_pairwise_alignment_can_supply_local_attribution_without_blast_or_phmmer(case):
    from gene_annotation_episode.biopython_pairwise_grader import grade_biopython_pairwise
    from gene_annotation_episode.sequence_ops import align_pair
    store,registry,target,y,z,native,known=case
    canonical_ref=store.artifact('MDDAKG','text/plain')
    definition=registry._source('engineering.trait_definition',{'meaning':'Local role using an actual small native pairwise alignment.'})
    reference=store.put('reference',{'reference_type':'protein','source_ref':definition,'accession':'pairwise-reference',
        'label':'Pairwise reference','sequence_ref':canonical_ref,'molecule':'protein','length':6,'term_refs':[],'context_refs':[]},origin='tool')['id']
    result=align_pair('MDEAKG','MDDAKG',molecule='protein',mode='global')
    grading=grade_biopython_pairwise(result,molecule='protein',_retain_correspondence=True)
    artifact=store.artifact(canonical(result),'application/json')
    retained=retain_tool_grading(store,provider='biopython.alignment',native_artifact_ref=artifact,grading=grading)
    source=store.put('source',{'provider':'biopython.alignment','accession':'actual-small-pair','uri':None,
        'artifact_ref':artifact,'text_ref':None,'request_ref':None,'version':'test','retrieved_at':None,
        'auxiliary_artifact_refs':[retained]},origin='tool')['id']
    observed=store.put('observation',{'subject_refs':[target],'source_subject_refs':[reference],'kind':'alignment',
        'source_ref':source,'measurements':[],'dependencies':[target,reference],'anchor':None},origin='tool')['id']
    req=request(store,{'operation':'structure.reference_traits','target_ref':target,'reference_binding_ref':y,
        'sequence_alignment_ref':None,'comparison_source_ref':None,
        'traits':[trait('pairwise-acidic','chemical_role',[2],definition,chemical_role='acidic')]},[target,y,definition])
    known.update({req,definition,reference,source,observed});added,needs=refresh(store,known,{'subject_refs':[target]});known.update(added)
    sheet=next(r for r in received_attachments(store,known) if r.get('physical_feature_key')=='pairwise-acidic')
    assert sheet['trait_match']==sheet['score']==1 and not needs
    assert sheet['correspondence']['witnesses'][0]['strength_profile']=='identity_distance_only_no_bit_statistic'


def test_reference_self_control_cannot_be_laundered_into_target_credit(case):
    store,registry,target,y,z,native,known=case
    body=json.loads(store.db.execute('SELECT body FROM a102_structure_bindings WHERE source_ref=?',(y,)).fetchone()[0])
    control=comparison(registry,y,body,y,body)
    req=fold_request(store,target,y,control)
    refs,_=alignment(store,target,'MDEAKG','MDDAKG');known.update({control,req,*refs})
    added,needs=refresh(store,known,{'subject_refs':[target]});known.update(added)
    sheet=next(r for r in received_attachments(store,known) if r.get('measurement_ref')==control)
    assert sheet['raw_score']==1 and sheet['state']=='excluded' and sheet['score'] is None
    assert not needs and A102StructuralCredit()(store,{'subject_refs':[target]},known_record_refs=known)['credit']==0


def test_model_binding_and_reported_metric_have_their_own_non_native_policies(case):
    store,registry,target,y,z,native,known=case
    x,_=binding(registry,'MDEAKG',target=target)
    paper=registry._source('engineering.reported_source',{'meaning':'A reported value fixture, not a newly executed target comparison.'})
    reported=registry._derived('reported_comparison',{'schema':'a102_reported_comparison_v1','target_ref':target,
        'source_refs':[paper],'description':'Engineering reported structural metric.',
        'matched_extent':'Six residues of the reference models.','metric_name':'RMSD','metric_value':1.2,
        'metric_unit':'angstrom','transfer_limits':'Reference subjects still need binding.','native_B':None})
    known.update({x,paper,reported});added,needs=refresh(store,known,{'subject_refs':[target]});known.update(added)
    sheets=received_attachments(store,known)
    binding_grade=next(r for r in sheets if r['producer_operation']=='structure.bind')
    report_grade=next(r for r in sheets if r['producer_operation']=='structure.reported_comparison')
    assert binding_grade['sequence_distance']==0 and binding_grade['score'] is None
    assert report_grade['reported_metric']['metric_value']==1.2 and report_grade['native_B'] is None
    assert 'actual_reported_subject_pair' in report_grade['missing'] and needs
    assert A102StructuralCredit()(store,{'subject_refs':[target]},known_record_refs=known)['credit']==0


def test_competing_reference_model_variants_do_not_select_the_best_score(case):
    store,registry,target,y,z,native,known=case
    other,body=binding(registry,'MDDAKG',shift=.3)
    zbody=json.loads(store.db.execute('SELECT body FROM a102_structure_bindings WHERE source_ref=?',(z,)).fetchone()[0])
    second=comparison(registry,other,body,z,zbody)
    first_request=fold_request(store,target,y,native);second_request=fold_request(store,target,other,second)
    refs,_=alignment(store,target,'MDEAKG','MDDAKG');known.update({other,second,first_request,second_request,*refs})
    added,_=refresh(store,known,{'subject_refs':[target]});known.update(added)
    view=A102StructuralCredit()(store,{'subject_refs':[target]},known_record_refs=known)
    assert view['credit']==0 and len(view['target_sheets'][target]['unresolved_reference_variants'])==1
