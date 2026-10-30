"""Bounded research calculation from one retained crystallography packet.
No target correspondence, structural alignment, scientific credit or runtime integration.
"""
from pathlib import Path
import contextlib,io,runpy,json,math,hashlib
P=Path(__file__).parent
with contextlib.redirect_stdout(io.StringIO()):
    reader=runpy.run_path(str(P/'inspect_depositions_001.py'))
parse,category=reader['parse'],reader['category']
D={acc:parse(P/f'{acc}_cif') for acc in ['4HF0','4HF1','4HF2']}
# The source describes the same carboxylate/exocyclic amino-group interactions.
# Both oxygens are retained. Minimum is the declared group-distance observable,
# not selection among alternative fitted structures. All four pairs count once.
panel=[('A','D',7,'N4'),('A','D',8,'N6'),('B','C',7,'N4'),('B','C',8,'N4')]
atoms=category(D['4HF1'],'_atom_site')
def atom(chain,res,atom_name):
    xs=[a for a in atoms if a['pdbx_PDB_model_num']=='1' and a['auth_asym_id']==chain and a['auth_seq_id']==str(res) and a['auth_atom_id']==atom_name and a['label_alt_id']=='.']
    assert len(xs)==1,(chain,res,atom_name,len(xs))
    return xs[0]
def pos(a):return [float(a[k]) for k in ['Cartn_x','Cartn_y','Cartn_z']]
contacts=[]
for pc,dc,res,dna_atom in panel:
    ox=[atom(pc,43,n) for n in ['OE1','OE2']];nit=atom(dc,res,dna_atom)
    ds=[math.dist(pos(o),pos(nit)) for o in ox];distance=min(ds)
    contacts.append({'protein_auth_chain':pc,'protein_auth_residue':43,'protein_comp':'GLU','protein_atom_set':['OE1','OE2'],'DNA_auth_chain':dc,'DNA_auth_residue':res,'DNA_comp':nit['auth_comp_id'],'DNA_atom':dna_atom,'protein_atom_rows':ox,'DNA_atom_row':nit,'all_pair_distances_A':dict(zip(['OE1','OE2'],ds)),'group_distance_A':distance,'positive_predicate_at_3_5A':distance<=3.5,'incompatible_predicate_at_4_5A':distance>=4.5})
Gplus=sum(x['positive_predicate_at_3_5A'] for x in contacts)/4
Gminus=sum(x['incompatible_predicate_at_4_5A'] for x in contacts)/4
out={'version':'research_iscr_structure_components_001','origin':'source_coordinate_derived_and_explicit_proposals','source_locator':'4HF1_cif/_atom_site, model 1, auth selectors in contact rows; article Fig2b/c, Results recognition section','source_sha256':hashlib.sha256((P/'4HF1_cif').read_bytes()).hexdigest(),'question':'Within deposited 4HF1 model, proximity of Glu43 carboxylate to the four named hya exocyclic amines','scope':'reference_only_conditional_model_geometry','geometry_panel':{'fixed_J':4,'positive_set_A':'[0,3.5]','incompatible_set_A':'[4.5,infinity)','gap_A':'(3.5,4.5)','threshold_origin':'proposed illustrative geometric criteria, not paper thresholds or calibrated H-bond proof','contacts':contacts,'G_plus':Gplus,'G_minus':Gminus,'calculation':'G_plus=sum(distance<=3.5)/4; G_minus=sum(distance>=4.5)/4','uncertainty':'model-conditional arithmetic; coordinate errors and donor-angle uncertainty not supplied','threshold_sensitivity':[{ 'positive_upper_A':t,'G_plus':sum(x['group_distance_A']<=t for x in contacts)/4} for t in [3.4,3.5,3.6]]},'paired_extraction':{'q':{'conditional_point':1,'unconditional_point':None,'definition':'conditioned on the selected deposited atom model, not measured population occupancy','all_selected_deposited_atom_occupancy_parameters':sorted({a['occupancy'] for x in contacts for a in x['protein_atom_rows']+[x['DNA_atom_row']]}),'refinement_status':'not_established','population_uncertainty':'unreported'},'D_X':{'point':None,'lower':0,'upper':1,'formula':'min_j(max(0,RSCC_j)^2)','required_panel':['A43','B43','D7','D8','C7','C8'],'panel_granularity':'residue','missing_reason':'local_RSCC_not_in_retained_article_or_coordinate_fields; validation/map analysis not performed'},'C':{'conditional_point':1,'definition':'single deposited state; no between-condition causal comparison','between_crystal_comparison_point':None},'I':{'conditional_point':1,'definition':'conditioned on deposited atom assignments; Y=1 model event, B=0 alternative-assignment contribution under this explicit conditioning','unconditional_point':None,'unconditional_missing_reason':'alternative_assignment_upper_bound_not_measured'},'T':{'point':None,'status':'outside_source_literature_scope; no target role mapping attempted'},'N':{'point':None,'missing_reason':'no calibrated occupancy upper bound; omitted residues/Fe-S atoms are not quantitative nondetections'}},'reference_product':{'formula_proposed':'p_ref=q_conditioned*D_X*G_plus*C_conditioned*I_conditioned; o_ref=q_conditioned*D_X*G_minus*C_conditioned*I_conditioned','p_ref':None,'p_ref_logical_lower':0,'p_ref_logical_upper':Gplus,'o_ref_conditional_geometry':0,'unknown_operands':['D_X'],'bounds_kind':'logical bound under selected model/assignments and proposed thresholds, not confidence interval','target_A111':None},'global_diagnostics':[],'model_coverage_diagnostics':[]}
# Native table values are manually transcribed; original HTML Table1 is retained.
reported={'4HF0':{'paper_resolution_A':1.90,'paper_Rwork_percent':19.33,'paper_Rfree_percent':22.05,'paper_completeness_percent':99.98,'paper_outer_completeness_percent':100.0},'4HF1':{'paper_resolution_A':2.22,'paper_Rwork_percent':20.28,'paper_Rfree_percent':22.79,'paper_completeness_percent':94.0,'paper_outer_completeness_percent':72.1},'4HF2':{'paper_resolution_A':2.99,'paper_Rwork_percent':22.94,'paper_Rfree_percent':26.11,'paper_completeness_percent':98.8,'paper_outer_completeness_percent':95.0}}
for acc,d in D.items():
    r=category(d,'_refine')[0];native=reported[acc]
    out['global_diagnostics'].append({'accession':acc,'paper_locator':'T1_original_element.html, refinement row and actual source-specific column','paper_origin':'manual_transcription_original_table','native_paper':native,'paper_R_gap_percentage_points':native['paper_Rfree_percent']-native['paper_Rwork_percent'],'deposited_Rwork':float(r['ls_R_factor_R_work']),'deposited_Rfree':float(r['ls_R_factor_R_free']),'deposited_R_gap':float(r['ls_R_factor_R_free'])-float(r['ls_R_factor_R_work']),'Rfree_difference_paper_minus_deposition_percentage_points':native['paper_Rfree_percent']-100*float(r['ls_R_factor_R_free']),'uncertainty':'unreported; source disagreement retained; no choice by best score','enters_D_X':False})
    aa=category(d,'_atom_site'); seq=category(d,'_entity_poly')[0]['pdbx_seq_one_letter_code_can'].replace('\n','');source_length=133 if acc=='4HF0' else 162
    for chain in ['A','B']:
        rows=[a for a in aa if a['auth_asym_id']==chain and a['group_PDB']=='ATOM' and a['label_seq_id'] not in ['.','?']]
        native_positions={int(a['auth_seq_id']) for a in rows if 1<=int(a['auth_seq_id'])<=source_length}
        out['model_coverage_diagnostics'].append({'accession':acc,'chain':chain,'modeled_source_residue_count':len(native_positions),'declared_source_residue_denominator':source_length,'model_coverage_fraction':len(native_positions)/source_length,'construct_polymer_length_including_linker_tag':len(seq),'definition':'source construct coordinate coverage excluding linker/tag; not sequence similarity, local density fit, occupancy or target-transfer factor','origin':'coordinate_derived_with_source_construct_boundary','source_locators':['article crystallization methods','_entity_poly','_atom_site','_pdbx_unobs_or_zero_occ_residues']})
checks={'checks':[]}
def check(name,predicate):
    assert predicate,name;checks['checks'].append({'name':name,'passed':True})
check('all selected endpoint atoms unique',len(contacts)==4)
check('four distances finite and positive',all(math.isfinite(x['group_distance_A']) and x['group_distance_A']>0 for x in contacts))
check('geometry panel numerator denominator',Gplus==3/4 and Gminus==0/4)
check('paired positive opposite sets disjoint',all(not(x['positive_predicate_at_3_5A'] and x['incompatible_predicate_at_4_5A']) for x in contacts))
check('Gplus remains threshold-sensitive',out['geometry_panel']['threshold_sensitivity'][2]['G_plus']==1)
check('missing local fit preserved',out['paired_extraction']['D_X']['point'] is None and out['reference_product']['p_ref'] is None)
check('target mapping stays out of scope',out['paired_extraction']['T']['point'] is None and out['reference_product']['target_A111'] is None)
check('occupancy remains conditional',out['paired_extraction']['q']['unconditional_point'] is None)
check('coverage excludes tags and water',all(0<=x['modeled_source_residue_count']<=x['declared_source_residue_denominator'] for x in out['model_coverage_diagnostics']))
check('paper deposition conflict retained',any(abs(x['Rfree_difference_paper_minus_deposition_percentage_points'])>0.001 for x in out['global_diagnostics']))
checks['bounded_check_count']=len(checks['checks']);checks['status']='research arithmetic checks only; no production reader, LiteratureEpisode, or model-backed extraction tested'
(P/'NUMERICAL_COMPONENTS_001.json').write_text(json.dumps(out,indent=2)+'\n');(P/'ARITHMETIC_CHECKS_001.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps({'G_plus':Gplus,'G_minus':Gminus,'distances_A':[x['group_distance_A'] for x in contacts],'source_product':out['reference_product'],'global_diagnostics':out['global_diagnostics'],'coverage':out['model_coverage_diagnostics'],'checks':checks},indent=2))
