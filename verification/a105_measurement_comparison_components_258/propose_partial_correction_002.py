"""Additive plan correction only. Reads001; writes only new002 review resources."""
from pathlib import Path
from copy import deepcopy
from fractions import Fraction
import hashlib,json,math
import jsonschema
P=Path(__file__).parent
oldfiles={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in P.glob('*001*') if p.is_file()}
def read(name):return json.loads((P/name).read_text())
def write(name,obj):
 target=P/name
 if target.exists():raise RuntimeError('Additive proposal refuses to overwrite '+str(target))
 target.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
def Q(x):
 x=Fraction(x);return {'numerator':str(x.numerator),'denominator':str(x.denominator)}
F=read('COMPONENT_FORMULAS_AND_MEANINGS_001.json')
F['difference_variance']['meaning']='Variance of the linked reported-protocol difference under the actual joint selected-estimator covariance; no common-condition or common-mean equivalence is required.'
F['difference_standard_uncertainty']['meaning']='Square root of that reported-protocol difference variance; no common-mean model or sampling distribution is inferred.'
F['combined_estimate']={'formula':'if(V_D>0,w_L*L+w_R*R,if(V_D==0&&D==0,L,unavailable))','meaning':'Common unbiased quantity estimate under the declared covariance model; for V_D=0 and L=R the shared value is unique even when the unbiased weight allocation is nonunique.'}
F['combined_variance']={'formula':'if(V_D>0,(V_L*V_R-C_LR^2)/V_D,if(V_D==0&&D==0,V_L,unavailable))','meaning':'Variance of the common estimate under the declared covariance model; for V_D=0 and L=R, PSD implies V_L=V_R=C_LR=v and every unbiased weight allocation has variance v.'}
F['combined_standard_uncertainty']['meaning']='Square root of that common-estimate variance, including zero under a declared known zero-variance model; nonunique weights do not erase this quantity.'
D=read('PLAN_DOMAINS_001.json')
D['reasons']['domain']=[('nonunique_gls_weights' if x=='degenerate_equal_estimate_covariance' else x) for x in D['reasons']['domain']]
D['interpretations'] += ['protocol_difference_uncertainty_known_covariance','protocol_difference_uncertainty_estimated_covariance']
changes={'combined_estimate':F['combined_estimate']['formula'],'combined_variance':F['combined_variance']['formula']}
resources={}
for name in ('SELECTION','EXTRACTION','CALCULATION_INPUTS','SHEET','COVARIANCE_DOCUMENT'):
 s=read(name+'_SCHEMA_001.json');s['$id']=s['$id'].replace(':plan001:',':plan002:')
 if 'domain_reasons' in s.get('$defs',{}):s['$defs']['domain_reasons']['items']['enum']=D['reasons']['domain']
 if name=='SHEET':
  cell=s['$defs']['cell'];cell['properties']['interpretation']['enum']=D['interpretations']
  cell['properties']['formula']['enum']=list(dict.fromkeys(v['formula'] for v in F.values()))
  for rule in cell['allOf']:
   component=rule.get('if',{}).get('properties',{}).get('component',{}).get('const')
   if component in changes:rule['then']['properties']['formula']={'const':changes[component]}
 jsonschema.Draft202012Validator.check_schema(s);resources[name]=s
 write(name+'_SCHEMA_002.json',s)
write('COMPONENT_FORMULAS_AND_MEANINGS_002.json',F)
write('PLAN_DOMAINS_002.json',D)
# Individual expected cells conform to the new cell definition. They are labelled
# mathematical illustrations, not source extraction or production execution.
S=resources['SHEET'];cell_resource={'$schema':S['$schema'],'$defs':S['$defs'],**deepcopy(S['$defs']['cell'])}
reasonempty=lambda:{k:[] for k in D['reasons']}
examples=[]
def example(name,L,R,v=None,protocol_only=False):
 L,R=Fraction(L),Fraction(R)
 C=[[Fraction(4),Fraction(1)],[Fraction(1),Fraction(9)]] if protocol_only else [[Fraction(v)]*2 for _ in range(2)]
 a,b,c=C[0][0],C[0][1],C[1][1];VD=a+c-2*b;delta=L-R
 if VD==0:assert a==b==c and a>=0
 ids={r:'measurement_'+hashlib.sha256((name+r).encode()).hexdigest() for r in ('left','right')}
 contribution='contribution_'+hashlib.sha256(name.encode()).hexdigest()
 def cell(comp,val=None,reason=None,interp='known_covariance_common_estimate',unit='dimensionless',exact=True):
  reasons=reasonempty()
  if reason:reasons[reason[0]]=[reason[1]]
  result={'component':comp,'value':None if val is None else float(val),'exact_value':None if val is None or not exact else Q(val),'conditional_value':None,'conditional_exact_value':None,'status':'unavailable' if val is None else 'populated','unit':unit,'relation':'point','approximate':False,'interpretation':'unavailable' if val is None else interp,'formula':F[comp]['formula'],'meaning_code':comp,'origin':'derived','input_origins':['synthetic'],'operand_roles':['left','right'],'operand_keys':list(ids.values()),'model_keys':[],'contribution_key':contribution,'uncertainty':{'covariance_source_refs':[],'variance_status':'known','scope':'selected_estimator_covariance','sampling_distribution':'not_assumed'},'reasons':reasons}
  jsonschema.Draft202012Validator(cell_resource).validate(result);return result
 cells=[cell('protocol_difference',delta,interp='descriptive_protocol_comparison',unit='umol/min/mg'),cell('difference_variance',VD,interp='protocol_difference_uncertainty_known_covariance',unit='(umol/min/mg)^2'),cell('difference_standard_uncertainty',math.sqrt(float(VD)),interp='protocol_difference_uncertainty_known_covariance',unit='umol/min/mg',exact=VD==0)]
 if protocol_only:
  for comp in ('common_difference','standardized_difference','squared_standardized_difference','weight_left','weight_right','combined_estimate','combined_variance','combined_standard_uncertainty'):
   cells.append(cell(comp,reason=('relationship','common_model_not_selected')))
 elif delta==0:
  for comp in ('standardized_difference','squared_standardized_difference'):cells.append(cell(comp,reason=('domain','positive_discrepancy_variance_required')))
  for comp in ('weight_left','weight_right'):cells.append(cell(comp,reason=('domain','nonunique_gls_weights')))
  cells += [cell('combined_estimate',L,unit='umol/min/mg'),cell('combined_variance',a,unit='(umol/min/mg)^2'),cell('combined_standard_uncertainty',int(math.isqrt(a.numerator)) if a.denominator==1 and math.isqrt(a.numerator)**2==a.numerator else math.sqrt(float(a)),unit='umol/min/mg',exact=a.denominator==1 and math.isqrt(a.numerator)**2==a.numerator)]
 else:
  for comp in ('standardized_difference','squared_standardized_difference','weight_left','weight_right','combined_estimate','combined_variance','combined_standard_uncertainty'):
   cells.append(cell(comp,reason=('domain','inconsistent_deterministic_constraint')))
 examples.append({'case':name,'origin':'synthetic_mathematical_schema_illustration','actual_source_fixture_or_component_execution':False,'calculation_input_summary':{'left_exact':Q(L),'right_exact':Q(R),'converted_covariance_exact':[[Q(x) for x in row] for row in C],'covariance_status':'known','covariance_is_actual_selected_estimator_covariance_in_this_synthetic_model':True,'common_model':'not_selected' if protocol_only else 'supported_common_unbiased_quantity','protocol':'additional_differences' if protocol_only else 'matched_except_intended_change'},'expected_cells':cells,'weight_allocation':'not_selected' if protocol_only else 'model_inconsistent' if delta else 'nonunique_unbiased_weights_no_arbitrary_choice'})
example('singular_shared_random_v4_equal20',20,20,4)
example('singular_zero_v0_equal20',20,20,0)
example('singular_v4_unequal20_22_common_model_contradiction',20,22,4)
example('different_protocols_known_joint_covariance_no_common_model',20,22,protocol_only=True)
write('SINGULAR_AND_PROTOCOL_PARTIAL_EXAMPLES_002.json',examples)
# Verify all old001 bytes are still intact after producing additive artifacts.
assert all(hashlib.sha256((P/n).read_bytes()).hexdigest()==h for n,h in oldfiles.items())
write('ADDITIVE_CORRECTION_CHECKS_002.json',{'old001_file_count':len(oldfiles),'all_old001_hashes_unchanged':True,'standalone_002_resources_metaschema_checked':list(resources),'expected_cells_validated':sum(len(e['expected_cells']) for e in examples),'production_or_test_files_created_or_edited':False,'component_implementation_executed':False,'note':'Schema and hand-constructed mathematical proposal checks only. Selection shape remains unchanged; draft resource identity is plan002.'})
print('Additive002: five resources, four mathematical cases, original001 hashes preserved; no production/test coding.')
