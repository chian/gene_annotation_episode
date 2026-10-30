"""Standalone design arithmetic and original-byte checks, not production code."""
from pathlib import Path
from fractions import Fraction as F
from math import log
import json, hashlib
BASE=Path(__file__).resolve().parent
CASE=BASE.parent/'a105_identified_product_scoring_case_207'
packet=json.loads((CASE/'SOURCE_PACKET_001.json').read_text())
raw=(CASE/'acquisition_001.bin').read_bytes()
assert hashlib.sha256(raw).hexdigest()==packet['paper']['sha256']
checked=[]
def check(node):
    if isinstance(node,dict):
        if {'start','end','quote','artifact_ref'}<=node.keys():
            assert raw[node['start']:node['end']].decode()==node['quote']
            checked.append([node['start'],node['end']])
        else:
            for v in node.values():check(v)
    elif isinstance(node,list):
        for v in node:check(v)
check(packet)
def quantity(table,arm,col):
    rows=packet['tables'][table]['rows']
    row=next(r for r in rows if r['cells'][0]['visible_text']==arm)
    return row['cells'][col]
def number(table,arm,col,token):
    cell=quantity(table,arm,col)
    # The independent transcription is checked against complete source cell,
    # not inferred from an already computed child output.
    assert cell['visible_text'].split(' ±')[0]==str(token)
    return F(str(token)),cell['witness']
def cell(value,unit,formula,meaning,status='derived_descriptive'):
    return {'exact':{'numerator':str(value.numerator),'denominator':str(value.denominator)},
            'display':float(value),'unit':unit,'formula':formula,'meaning':meaning,'status':status}
source=[];out={}
S=F(2000);KD0=F('1.8');P0=F(206);H0=F(289);K0=F(124);M0=F(30)
for arm,p,h,kd,kcat,km,printed in [
    ('Wild-type','206','289','1.8','124','30',71),
    ('T252N','92','216','34','54','96',42),
    ('T252N/V253T','132','343','12','165','388',38),
    ('T252A','0','427','2.9',None,None,0)]:
    row={}; vals={}
    for role,tab,col,tok in [('P','T3',1,p),('H','T3',2,h),('Kd','T4',1,kd)]:
        val,w=number(tab,arm,col,tok);vals[role]=val
        source.append({'arm':arm,'role':role,'value':tok,'table':tab,'column':col,'witness':w})
    P,H,Kd=(vals[x] for x in ('P','H','Kd'))
    row['reporter_reference_contrast']=cell(H/H0,'dimensionless','H/H_WT','Observed reporter contrast, not productive-function evidence grade.')
    theta=S/(S+Kd);theta0=S/(S+KD0);Rtheta=theta/theta0
    row['scenario_occupancy']=cell(theta,'fraction','S/(S+Kd)','Conditional single-site equilibrium occupancy.','conditional_sensitivity')
    row['scenario_occupancy_reference_contrast']=cell(Rtheta,'dimensionless','theta/theta_WT','Binding-only predicted turnover contrast under declared assumptions.','conditional_sensitivity')
    if arm!='T252A':
        rho=P/H;RP=P/P0;RH=H/H0;Rrho=rho/(P0/H0);Ra=RP/Rtheta
        assert RP==RH*Rrho
        row['product_per_reporter']=cell(rho,'product_per_NADH','P/H','Descriptive endpoint comparison, detailed matching unknown.')
        row['product_reference_contrast']=cell(RP,'dimensionless','P/P_WT','Observed same-product contrast, not causal isolation.')
        row['productive_use_reference_contrast']=cell(Rrho,'dimensionless','(P/H)/(P_WT/H_WT)','Dependent endpoint-specificity decomposition.')
        row['scenario_binding_only_prediction_error']=cell(RP-Rtheta,'dimensionless','R_P-R_theta','Discrepancy with named binding-only alternative.','conditional_sensitivity')
        row['scenario_post_binding_residual_ratio']=cell(Ra,'dimensionless','R_P/R_theta','Residual can include active amount, bias, nuisance or chemistry.','conditional_sensitivity')
        row['scenario_binding_only_log_residual']={'display':log(float(Ra)),'exact_precursor':str(Ra),'formula':'ln(R_P/R_theta)','unit':'dimensionless','status':'conditional_sensitivity'}
        row['local_displayed_coupling_difference_pp']=cell(100*rho-printed,'percentage_points','100*P/H-source_percent','Local discrepancy; no calibrated error penalty.')
        k,w=number('T2',arm,1,kcat);source.append({'arm':arm,'role':'kcat','value':kcat,'witness':w})
        m,w=number('T2',arm,2,km);source.append({'arm':arm,'role':'Km','value':km,'witness':w})
        row['saturation_turnover_reference_contrast']=cell(k/K0,'dimensionless','kcat/kcat_WT','Saturation-turnover resolution; fitted-parameter covariance absent.')
        row['low_substrate_efficiency_reference_contrast']=cell((k/m)/(K0/M0),'dimensionless','(kcat/Km)/(kcat_WT/Km_WT)','Low-substrate functional resolution, not physiological compatibility.')
    else:
        for name in ['product_reference_contrast','product_per_reporter','productive_use_reference_contrast','scenario_binding_only_prediction_error','scenario_post_binding_residual_ratio','scenario_binding_only_log_residual']:
            row[name]={'display':None,'status':'unavailable','source_missing':['quantitative_nondetection_limit'],'meaning':'Printed zero is qualified negligible/ND, not physical point zero.'}
    row['measurement_quality_and_full_isolation']={'fully_corrected_intrinsic_activity_ratio':None,
        'isolated_signal_fraction':None,'calibration_loss':None,'nuisance_response_correction':None,
        'active_fraction':None,'residual_variance':None,'standardized_residual':None,
        'source_missing':['same_scale_blank','applicable_recovery','active_fraction','nuisance_response_control','joint_estimate_covariance'],
        'implementation_missing':['common_assertion_assay_binding','cross_assay_common_calculator','selected_storage_and_typed_common_return']}
    out[arm]=row
# Shared WT normalization means distinct mutant ratios cannot imply independence.
assert out['T252N']['scenario_post_binding_residual_ratio']['exact']=={'numerator':'467820','denominator':'1030927'}
result={'purpose':'Research/design oracle only; common scientific functions remain future implementation.',
 'paper':packet['paper'],'original_byte_witness_occurrences_checked':len(checked),
 'unique_original_byte_spans_checked':len(set(map(tuple,checked))),
 'source_operand_witnesses':source,'model':{'free_substrate_uM':'2000',
 'source_scope':'Reported for NADH assay; stipulated for product sensitivity scenario.',
 'assumptions':['one_site_equilibrium','binding_Kd_applicable_to_catalytic_preparation_and_conditions',
 'free_substrate_equals_stipulated_2000uM','equal_active_fraction','equal_recovery','equal_nuisance_response',
 'same_scope_product_comparison','turnover_proportional_to_occupancy']},'cells':out,
 'source_conditions':['No numerical Table3 uncertainty or preparation count.',
 'Table2 and Table4 plus/minus parameter-spread type is not established by Fig5 point SD.',
 'No quantitative no-P450 blank or active fraction.',
 'Product assay 2mM camphor not explicitly established.',
 'Fig4 V253N conflicts with text/table V253T; no panel reassignment.',
 'Inferred water reuses reporter/product/peroxide and is not independent balance.'],
 'executed':'Standard-library original-byte validation and rational/log arithmetic only; no model, episode or production calculator execution.'}
(BASE/'NUMERICAL_ORACLES_001.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'source_witness_occurrences':len(checked),'source_unique_spans':len(set(map(tuple,checked))), 'arms':list(out),'arithmetic_assertions':'passed'}))
