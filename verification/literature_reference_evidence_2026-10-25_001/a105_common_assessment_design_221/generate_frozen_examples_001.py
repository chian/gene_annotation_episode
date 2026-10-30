"""Generate frozen pure common examples; not selected common execution."""
import hashlib,json,os,sys
from fractions import Fraction
from pathlib import Path
OUT=Path(__file__).resolve().parent
PIN=OUT/'pin_001'
os.chdir(PIN)
sys.path[:0]=[str(PIN),str(PIN/'tests')]
from test_literature_common_assessment_221 import Case,cells,exact,ORACLE
from gene_annotation_episode.literature_compiled_assay_calculations import populate_common_assessment
import gene_annotation_episode.literature_compiled_assay_calculations as calcs
assert Path(calcs.__file__).is_relative_to(PIN)
base=OUT/'examples_002';base.mkdir(exist_ok=False)
oracle=json.loads(ORACLE.read_text());receipt=[]
def write(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
for index,label,directory in [(1,'T252N','T252N'),(2,'T252N/V253T','T252N_V253T')]:
 p=base/directory;p.mkdir();case=Case(p/'component_store',index)
 args=case.args();data=case.read(args);sheet=populate_common_assessment(data);rows=cells(sheet);o=oracle['results'][label]
 pairs={'product_reference_contrast':'product_contrast','saturation_turnover_reference_contrast':'saturation_turnover_contrast','low_substrate_efficiency_reference_contrast':'low_substrate_efficiency_contrast','occupancy_reference_contrast':'conditional_occupancy_contrast','post_binding_residual_ratio':'conditional_residual_ratio'}
 comparisons={}
 for component,key in pairs.items():
  conditional=key.startswith('conditional_');got=exact(rows[component],conditional);expected=Fraction(int(o[key]['numerator']),int(o[key]['denominator']))
  assert got==expected
  comparisons[component]={'actual_exact':str(got),'root219_exact':str(expected),'match':True,'conditional_sensitivity':conditional}
 write(p/'common_request.json',args);write(p/'host_bound_inputs.json',data);write(p/'common_sheet.json',sheet)
 covargs=case.args(['binding_only_residual_variance']);covargs['model']['substrate_uncertainty']='selected_estimate_covariance';covdata=case.read(covargs)
 roles=['product_test','product_reference','Kd_test','Kd_reference','free_substrate_test']
 modes=((Fraction(1),Fraction('0.5'),Fraction(2),Fraction('0.1'),Fraction(20)),(Fraction('-0.2'),Fraction('0.4'),Fraction(1),Fraction('0.3'),Fraction(-10)))
 matrix=[[float(sum(mode[i]*mode[j] for mode in modes)) for j in range(5)] for i in range(5)]
 covargs['covariance_source_refs']=[case.covariance(covdata,roles,matrix,'known')]
 covdata=case.read(covargs);covsheet=populate_common_assessment(covdata);got=exact(covsheet['cells'][0],True);expected=Fraction(int(o['synthetic_error_mode_variance_exact']['numerator']),int(o['synthetic_error_mode_variance_exact']['denominator']));assert got==expected
 write(p/'synthetic_covariance_request.json',covargs);write(p/'synthetic_covariance_host_inputs.json',covdata);write(p/'synthetic_covariance_sheet.json',covsheet)
 comparisons['binding_only_residual_variance']={'actual_exact':str(got),'root219_synthetic_exact':str(expected),'match':True,'covariance_origin':'synthetic_two_joint_error_modes_not_paper_uncertainty'}
 write(p/'root219_comparisons.json',comparisons)
 receipt.append({'example':label,'status':'frozen_pure_calculation_from_actual_existing_received_native_rows','source_case':'retained207','source_html_sha256':hashlib.sha256(case.raw).hexdigest(),'scenario_origin':'proposed_shared_free_S_2000_uM_sensitivity_not_established_product_assay_S','comparisons':comparisons,'selected_common_operation':False,'model_calls':0,'annotation_credit':None})
write(base/'EXAMPLES.json',receipt)
print('Wrote2 frozen pure cases and2 separately synthetic joint-covariance examples; all exact root219 comparisons match.')
