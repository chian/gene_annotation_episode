"""Owner043 research arithmetic; no production records or scientific run."""
from pathlib import Path
import json, math, hashlib,sys
R=Path(__file__).resolve().parents[3];sys.path.insert(0,str(R))
from gene_annotation_episode.literature_transport_calculations import populate_transport_response
O=Path(__file__).resolve().parent / "reproduced_001"

def cell(value,unit,formula,origin,meaning,source,limits):
 return dict(value=value,unit=unit,formula=formula,origin=origin,evaluates=meaning,source=source,limits=limits)
c={}
c['whole_cell_reported_rate_fold']=cell(6,'dimensionless','reported fold','reported','BtsT-expression arm / empty-vector arm uptake-rate ratio','Results before Fig3','Rounded narrative fold; no native rates/covariance')
c['whole_cell_increment_fraction']=cell(1-1/6,'dimensionless','1-1/reported_rate_fold','derived','Increment over comparator as fraction of observed BtsT-arm rate','Results before Fig3','Conditional comparable-background diagnostic, not a molecular attribution fraction or confidence')
c['plateau_reported_amount']=cell(.5,'nmol/mg_total_cell_protein','reported prose amount','reported','Narrative approximate accumulated amount','Results before Fig3','Graph plateau nearer .6; not rate')
c['plateau_comparator_amount']=cell(.5/4,'nmol/mg_total_cell_protein','0.5/4','derived','Comparator accumulation inferred from reported approximate plateau and fourfold relation','Results before Fig3','Not directly extracted comparator observation; not initial flux')
c['plateau_increment']=cell(.5-.5/4,'nmol/mg_total_cell_protein','0.5-0.5/4','derived','Difference of reported approximate plateau amounts','Results before Fig3','Shares same observations as fourfold ratio')
c['plateau_increment_fraction']=cell(1-1/4,'dimensionless','1-1/4','derived','Comparator-associated fraction of reported plateau difference','Results before Fig3','Not rate contribution or molecular attribution')
for name,height in [('cold_pyruvate',.06),('Br_pyruvate',.04)]:
 c[name+'_remaining_fraction']=cell(height/.80,'dimensionless',f'{height}/0.80','derived','Remaining tracer uptake fraction relative to shared control','Fig4B manual visual heights','Graph-derived numerator and denominator, no background correction; not other-substrate transport')
 c[name+'_reduction_fraction']=cell(1-height/.8,'dimensionless',f'1-{height}/0.80','derived','Reduction in tracer uptake under compound challenge','Fig4B manual visual heights','Not Ki/Kd or biological confidence')
 # monotone ratio at independent visual-reading intervals; shared control identity retained.
 c[name+'_reduction_reading_interval']=dict(value=None,unit='dimensionless',interval=[1-(height+.02)/(.8-.02),1-max(0,height-.02)/(.8+.02)],origin='derived',bound_kind='visual_reading_resolution',not_sampling_uncertainty=True,formula='[1-Iupper/Clower,1-Ilower/Cupper]',source='Fig4B visual reading allowance ±0.02 nmol/mg/min',shared_control='fig4B_control')
c['relative_km_printed_spread']=cell(6.4/16.5,'dimensionless','6.4/16.5','derived','Relative magnitude of printed Km spread','Results characterization final sentence','Unspecified parameter error; not SD/SEM/variance')
c['gradient_reported_both_rate']=cell(27.7,'nmol/mg_reconstituted_protein/min','reported27.7; rate dimension from Fig5B','reported','Initial uptake-rate bar under both gradients','Results gradient section; Fig5B','Prose omits time denominator; figure supplies/min')
c['gradient_prose_half_rate']=cell(27.7/2,'nmol/mg_reconstituted_protein/min','27.7/2','derived','Approximate individual-gradient rate using narrative twofold relation','Results/discussion gradients','Not independent raw observation; Fig5B visual ΔpH bar differs')
c['gradient_individual_to_both_ratio']=cell(.5,'dimensionless','(27.7/2)/27.7','derived','Reported approximate gradient response ratio','Results/discussion gradients','A physical response, not a quality coefficient or H+ stoichiometry')
c['nominal_delta_pH']=cell(7.6-5.8,'pH_units','7.6-5.8','derived','Nominal internal-minus-external buffer pH','Proteoliposome Methods','Not observed maintained gradient')
c['nominal_proton_concentration_ratio']=cell(10**(7.6-5.8),'dimensionless','10^(7.6-5.8)','derived','Nominal external/internal H+ activity ratio from buffer pH','Proteoliposome Methods','pH/activity context only; no proton flux')
c['nominal_diluted_protein']=cell(4/200,'mg/mL','4/200','derived','Protein concentration after dilution','Proteoliposome Methods','Not active incorporated BtsT count')
c['counterflow_cold_carryover']=cell(10000/200,'uM','10000/200','derived','Cold pyruvate carryover matching reported external total','Counterflow Methods','Applies to pyruvate-loaded arm, not lactate-loaded arm')
c['counterflow_total_external_pyruvate']=cell(10000/200+4.7,'uM','10000/200+4.7','derived','Total external pyruvate matching stated54.7','Counterflow Methods','Not4.7 total; no whole-cell Km correction')
c['counterflow_labeled_fraction']=cell(4.7/(10000/200+4.7),'dimensionless','4.7/54.7','derived','Nominal labeled/total external pyruvate','Counterflow Methods','Does not establish tracer recovery or count calibration')
for key,reason in [('source_profile_log_ratio','Effect covariance and supported sampling model unavailable'),('source_signed_index','No profile log ratio'),('protein_specific_gradient_effect','Numeric matched empty-liposome rates unavailable'),('proton_pyruvate_stoichiometry','No paired proton and pyruvate flux'),('counterflow_initial_rate','Prose rate vs graph accumulation endpoint, nonzero intercept and missing window'),('alternative_substrate_transport_rate','Competition does not measure this endpoint')]:
 c[key]=dict(value=None,status='unavailable',reason=reason)
args=dict(values=dict(substrate_test=10.,substrate_reference=40.,km=16.5),curve_keys=dict.fromkeys(('substrate_test','substrate_reference','km'),'declared_fig4C_whole_cell_curve'),measurement_keys=dict(substrate_test='fig4C_10uM',substrate_reference='fig4C_40uM',km='fig4C_Km'),covariance=None,variance_status='unknown',observation_model='michaelis_menten',origin='derived')
within=populate_transport_response(args)
assert math.isclose(within['cells']['condition_response']['value'],.5330188679245284)
assert within['cells']['condition_response_variance']['value'] is None
args['curve_keys']['substrate_reference']='fig5_proteoliposome_curve'
cross=populate_transport_response(args)
assert cross['cells']['condition_response']['value'] is None
assert cross['cells']['condition_response']['unavailable_reason']=='different_kinetic_curves'
assert math.isclose(c['counterflow_total_external_pyruvate']['value'],54.7)
assert c['whole_cell_increment_fraction']['value'] == 5/6
result=dict(version='owner043_transport_research_v1',primary_doi='10.1128/JB.00599-17',synthetic_scientific_measurements=False,cells=c,manual_graph_inputs=dict(control=.80,cold_pyruvate=.06,Br_pyruvate=.04,unit='nmol/mg/min',origin='graph_derived',method='manual visual approximate bar height, Figure4B',reading_allowance=.02,allowance_is_sampling_uncertainty=False,control_identity='fig4B_control'),same_curve_conditional_example=within,cross_physical_preparation_rejection=cross,proposal_equations=dict(whole_cell_difference='d_i=vB_i-vEV_i; Var(mean_d)=sample_var(d)/n only for actual independent matched pairs',gradient_difference_of_differences='e=[1,-1,-1,1] x; V=l C l^T',competition_logcontrast='z_j=log((vcontrol-bcontrol)/(vj-bj)); full common-control covariance',known_normal_signed_route='S=e*abs(e)/(2V), B=tanh(S/2), only supported known-normal positive variance',not_computed='No source-to-target or W05 aggregation'),checks=dict(status='passed',scope='native arithmetic and existing pure same-curve response/rejection only; no source-native repository or model execution'))
(O/'NUMERICAL_CASE.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
# Exact source extraction spans from the one already fully read retained primary text.
p=Path('/home/chia/repos/gene_annotation_episode/verification/literature_reference_evidence_2026-10-25_001/a105_transport_case_043/source/PMC5738728_retained_primary.txt');raw=p.read_bytes();text=raw.decode();needles={
'whole_cell_arrangement':'Uptake of [ 14 C]pyruvate into intact cells of E. coli MG1655 Δ btsT',
'whole_cell_rate_fold':'Cells transformed with pBAD24- btsT displayed a 6-fold higher linear uptake rate for 30 s',
'km':'16.5 ± 6.4 μM',
'whole_cell_methods':'Cells grown in LB medium in the absence of arabinose',
'counterflow_total':'final external pyruvate concentration of 54.7 μM',
'global_uncertainty':'All experiments were repeated at least three times with independently prepared samples.',
'fig3_uncertainty':'Standard deviations are estimated from three biological replicates.',
'fig4_uncertainty':'Standard deviations in panels A and B are estimated from three biological replicates with no background correction.',
'fig5_uncertainty':'Standard deviations are estimated from three technical replicates.',
'counterflow_prose':'0.28 nmol × mg −1 × min −1',
}
loc=[]
for key,needle in needles.items():
 start=text.index(needle);end=start+len(needle);loc.append(dict(field=key,source='source/PMC5738728_retained_primary.txt',source_sha256=hashlib.sha256(raw).hexdigest(),line_start=text[:start].count('\n')+1,line_end=text[:end].count('\n')+1,unicode_start=start,unicode_end=end,utf8_byte_start=len(text[:start].encode()),utf8_byte_end=len(text[:end].encode()),quote=needle))
(O/'SOURCE_LOCATORS.json').write_text(json.dumps(loc,indent=2,ensure_ascii=False)+'\n')
print('Owner043 numerical artifact generated; conditional arithmetic checks passed. No production mutation.')
