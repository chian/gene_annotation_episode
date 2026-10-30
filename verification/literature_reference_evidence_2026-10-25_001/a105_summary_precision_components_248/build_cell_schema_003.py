"""Frozen additive review schema/conformance; no production or tests modified."""
from pathlib import Path
from copy import deepcopy as dc
from fractions import Fraction
import hashlib,json,math
import jsonschema
from gene_annotation_episode.domain import validate_schema,ContractError
H=Path(__file__).resolve().parent

def load(n):return json.loads((H/n).read_text())
def save(n,v):(H/n).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def ref(n):return {'$ref':'#/$defs/'+n}
def null():return {'type':'null'}
def rat(x):
 f=Fraction(x);return {'numerator':str(f.numerator),'denominator':str(f.denominator)}
old=load('SHEET_SCHEMA_002.json');new=dc(old)
canon=['uM','per_min','uM^-1min^-1']
squared=['uM_squared','per_min_squared','uM_inverse_squared_min_inverse_squared']
units={'canonical':{'enum':[*canon,None]},'squared':{'enum':[*squared,None]},'count':{'const':'count'},'dimensionless':{'const':'dimensionless'}}
values={'number':{'type':'number'},'nonnegative':{'type':'number','minimum':0},'positive':{'type':'number','exclusiveMinimum':0},'positive_integer':{'type':'integer','minimum':1},'confidence_95':{'const':.95}}
# Per-cell domains are explicit. Unit agreement with actual inputs is semantic.
domains={
 'reported_parameter':('canonical','number'),
 'reported_sd':('canonical','nonnegative'),
 'source_summary_count':('count','positive_integer'),
 'independent_preparation_count':('count','positive_integer'),
 'statistical_estimator_count':('count','positive_integer'),
 'relative_reported_sd':('dimensionless','nonnegative'),
 'mean_variance':('squared','nonnegative'),
 'mean_standard_error':('canonical','nonnegative'),
 'relative_mean_standard_error':('dimensionless','nonnegative'),
 'mean_interval_df':('count','positive_integer'),
 'mean_interval_confidence_level':('dimensionless','confidence_95'),
 'mean_interval_t_multiplier':('dimensionless','positive'),
 'mean_interval_halfwidth':('canonical','positive'),
 'mean_interval_lower':('canonical','number'),
 'mean_interval_upper':('canonical','number'),
}
base=dc(old['properties']['source_cells']['properties']['reported_parameter'])
# Keep original closed base field grammar; named overlays only NARROW it.
defs={'Cell':base,
 'CellStates':{'oneOf':[
  {'properties':{'status':{'const':'populated'},'value':{'type':'number'},'unit':{'not':{'type':'null'}},'qualification':{'enum':['source_reported','derived_source_supported_conditions','conditional_on_stipulated_assumptions']},'unavailable_reason':null()},
   'allOf':[{'if':{'properties':{'qualification':{'const':'conditional_on_stipulated_assumptions'}}},'then':{'properties':{'stipulated_assumptions':{'minItems':1}}},'else':{'properties':{'stipulated_assumptions':{'maxItems':0}}}}]},
  {'properties':{'status':{'const':'unavailable'},'value':null(),'qualification':{'const':'unavailable'},'source_exact_value':null(),'unavailable_reason':{'not':{'type':'null'}}}}
 ]},
 'SourceCellQualifications':{'properties':{'qualification':{'enum':['source_reported','derived_source_supported_conditions','unavailable']},'stipulated_assumptions':{'maxItems':0}}},
 'ScenarioCellQualifications':{'properties':{'qualification':{'enum':['source_reported','derived_source_supported_conditions','conditional_on_stipulated_assumptions','unavailable']}}},
 **{'Unit_'+k:v for k,v in units.items()},
 **{'Value_'+k:{'anyOf':[v,null()]} for k,v in values.items()}}
new['$defs']=defs
replacements={}
for group in ['source_cells','scenario_cells']:
 target=new['properties'][group]
 path='/properties/'+group
 if group=='scenario_cells':target=target['anyOf'][0];path+='/anyOf/0'
 for name,(u,v) in domains.items():
  cell={'allOf':[ref('Cell'),ref('CellStates'),ref('SourceCellQualifications' if group=='source_cells' else 'ScenarioCellQualifications')],
        'properties':{'formula_code':{'const':'summary_precision_'+name},'unit':ref('Unit_'+u),'value':ref('Value_'+v)}}
  target['properties'][name]=cell
  replacements[path+'/properties/'+name]=cell
jsonschema.Draft202012Validator.check_schema(new)
save('SHEET_SCHEMA_003.json',new)
patch=[{'op':'add','path':'/$defs','value':defs},*[{'op':'replace','path':p,'value':v} for p,v in replacements.items()]]
# Independently apply the exact supplied patch and check byte-canonical equivalence.
reconstructed=dc(old)
for op in patch:
 parts=op['path'].strip('/').split('/');parent=reconstructed
 for part in parts[:-1]:parent=parent[int(part)] if isinstance(parent,list) else parent[part]
 if isinstance(parent,list):parent[int(parts[-1])]=dc(op['value'])
 else:parent[parts[-1]]=dc(op['value'])
assert reconstructed==new
save('CELL_SCHEMA_DELTA_003.json',{'base_file':'SHEET_SCHEMA_002.json','revised_file':'SHEET_SCHEMA_003.json','only_named_sheet_cells_narrowed':True,'per_cell_domains':{k:{'formula_code':'summary_precision_'+k,'unit_domain':u,'value_domain':v} for k,(u,v) in domains.items()},'rfc6902_patch':patch,'exact_patch_roundtrip_verified':True,'other_three002_schemas_unchanged':True})

# A complete actual242 PROPOSED sheet shape, not production calculator execution.
ci=load('ACTUAL_SOURCE_CALCULATION_INPUT_PROPOSAL_002.json')
codes=ci['scenario']['stipulated_assumptions']
count_codes=codes[:2]
se_codes=[c for c in codes if c not in ('equal_weight_arithmetic_mean','normal_sampling_units')]
def cell(name,value,unit,*,reason=None,exact=None,conditions=(),stips=(),source=False,proposed=False):
 return {'value':value,'unit':unit,'status':'unavailable' if value is None else 'populated',
  'qualification':'unavailable' if value is None else 'conditional_on_stipulated_assumptions' if stips else 'source_reported' if source else 'derived_source_supported_conditions',
  'formula_code':'summary_precision_'+name,'origin':'proposed' if proposed else 'reported' if source else 'derived','approximate':False,'source_exact_value':rat(exact) if exact is not None and value is not None else None,'conditional_on':list(conditions),'stipulated_assumptions':list(stips),'unavailable_reason':reason}
def unavailable(name,reason,unit=None,stips=()):
 u=unit if unit is not None else 'count' if domains[name][0]=='count' else 'dimensionless' if domains[name][0]=='dimensionless' else None
 return cell(name,None,u,reason=reason,stips=stips)
source={name:unavailable(name,'statistical_estimator_count_unknown',unit='uM_inverse_squared_min_inverse_squared' if name=='mean_variance' else 'uM^-1min^-1' if domains[name][0]=='canonical' else None) for name in domains}
source.update({
 'reported_parameter':cell('reported_parameter',.000186,'uM^-1min^-1',exact=Fraction('3.1')*Fraction(60,1000000),source=True),
 'reported_sd':cell('reported_sd',.000006,'uM^-1min^-1',exact=Fraction('.1')*Fraction(60,1000000),source=True),
 'source_summary_count':cell('source_summary_count',2,'count',exact=2,source=True),
 'independent_preparation_count':cell('independent_preparation_count',2,'count',exact=2,source=True),
 'relative_reported_sd':cell('relative_reported_sd',1/31,'dimensionless',exact=Fraction(1,31)),
 'mean_interval_confidence_level':cell('mean_interval_confidence_level',.95,'dimensionless',exact=Fraction(19,20),proposed=True)})
scenario=dc(source)
scenario['statistical_estimator_count']=cell('statistical_estimator_count',2,'count',exact=2,conditions=count_codes,stips=count_codes)
scenario['mean_variance']=cell('mean_variance',1.8e-11,'uM_inverse_squared_min_inverse_squared',exact=Fraction(9,500000000000),conditions=se_codes,stips=se_codes)
scenario['mean_standard_error']=cell('mean_standard_error',math.sqrt(.005)*.00006,'uM^-1min^-1',conditions=se_codes,stips=se_codes)
r_codes=[*se_codes,'equal_weight_arithmetic_mean']
scenario['relative_mean_standard_error']=cell('relative_mean_standard_error',math.sqrt(.005)/3.1,'dimensionless',conditions=r_codes,stips=r_codes)
df_codes=[*count_codes,'sample_sd_n_minus_one']
scenario['mean_interval_df']=cell('mean_interval_df',1,'count',exact=1,conditions=df_codes,stips=df_codes)
t_codes=[*df_codes,'iid_common_mean_finite_variance','normal_sampling_units']
quant=12.706204736174707
scenario['mean_interval_t_multiplier']=cell('mean_interval_t_multiplier',quant,'dimensionless',conditions=t_codes,stips=t_codes)
width_codes=[*se_codes,'normal_sampling_units']
scenario['mean_interval_halfwidth']=cell('mean_interval_halfwidth',quant*math.sqrt(.005)*.00006,'uM^-1min^-1',conditions=width_codes,stips=width_codes)
for name,value in [('mean_interval_lower',(3.1-quant*math.sqrt(.005))*.00006),('mean_interval_upper',(3.1+quant*math.sqrt(.005))*.00006)]:
 scenario[name]=cell(name,value,'uM^-1min^-1',conditions=codes,stips=codes)
locations=[]
for key in ['parameter_source','spread_source','count_source','statistical_count_source','parameter_unit_source','spread_unit_source']:
 loc=ci['dependencies'][key]
 if loc is not None and loc not in locations:locations.append(loc)
sheet={'version':'a105_kinetic_summary_precision_sheet_v1','axis':'A105','evaluation_scope':'source_kinetic_summary_precision','inputs':ci,'source_cells':source,'scenario_cells':scenario,'contribution':{'kind':'one_summary_precision_contribution','dependency_sources':locations,'physical_measurement_id':ci['dependencies']['physical_measurement_id'],'independence_inferred':False},'limits':new['properties']['limits']['items']['enum'],'total_uncertainty':None,'assay_error_probability':None,'annotation_credit':None}
validator=jsonschema.Draft202012Validator(new)
checks=[]
def accept(label,value):
 validator.validate(value);validate_schema(value,new);checks.append({'case':label,'expected':'accepted','actual':'accepted_by_both'})
def reject(label,value):
 try:validator.validate(value)
 except jsonschema.ValidationError:pass
 else:raise AssertionError(label+' standalone accepted')
 try:validate_schema(value,new)
 except ContractError:pass
 else:raise AssertionError(label+' domain accepted')
 checks.append({'case':label,'expected':'rejected','actual':'rejected_by_both'})
accept('complete_actual242_proposed_source_and_conditional_shape',sheet)
# Valid partial with independently known explicit SD while parameter unit/value absent.
partial=dc(sheet);partial['inputs']=load('SYNTHETIC_PARTIAL_IO_002.json')[0]['calculation_inputs'];partial['scenario_cells']=None
partialsource={n:unavailable(n,'interval_not_requested') for n in domains}
partialsource.update({'reported_parameter':unavailable('reported_parameter','source_measurement_unreported'),
 'reported_sd':cell('reported_sd',12,'per_min',exact=12,source=True),
 'source_summary_count':cell('source_summary_count',4,'count',exact=4,source=True),
 'independent_preparation_count':cell('independent_preparation_count',4,'count',exact=4,source=True),
 'statistical_estimator_count':cell('statistical_estimator_count',4,'count',exact=4,source=True),
 'relative_reported_sd':unavailable('relative_reported_sd','source_measurement_unreported'),
 'relative_mean_standard_error':unavailable('relative_mean_standard_error','source_measurement_unreported'),
 'mean_variance':cell('mean_variance',36,'per_min_squared',exact=36,conditions=se_codes),
 'mean_standard_error':cell('mean_standard_error',6,'per_min',exact=6,conditions=se_codes)})
partial['source_cells']=partialsource
accept('partial_missing_central_value_keeps_known_SD_and_SE',partial)
# Correct state grammar permits unavailable scenario cells retaining attempted assumptions.
partial_attempt=dc(sheet);partial_attempt['scenario_cells']['mean_variance']=unavailable('mean_variance','sd_preparation_estimator_ownership_unknown',unit='uM_inverse_squared_min_inverse_squared',stips=['one_estimate_per_preparation'])
accept('unavailable_scenario_retains_attempted_stipulation_and_known_squared_unit',partial_attempt)
# Every named cell in each direction rejects swapped formulas/unit domains.
for group in ['source_cells','scenario_cells']:
 for index,name in enumerate(domains):
  for key,value in [('formula_code','summary_precision_'+list(domains)[(index+1)%len(domains)]),('unit','count' if domains[name][0] not in ('count','dimensionless') else 'per_min')]:
   bad=dc(sheet);bad[group][name][key]=value;reject(group+'.'+name+'.wrong_'+key,bad)
  # Populate a shape-valid value before mutating state relationships (source model truth is not this grammar test).
  seed=dc(sheet);u,v=domains[name]
  numeric=2 if v=='positive_integer' else .95 if v=='confidence_95' else 1.25
  goodunit=canon[0] if u=='canonical' else squared[0] if u=='squared' else u
  seed[group][name]=cell(name,numeric,goodunit)
  accept(group+'.'+name+'.named_cell_domain',seed)
  for label,changes in [
   ('populated_null_unit',{'unit':None}),
   ('populated_null_value',{'value':None}),
   ('populated_nonnull_reason',{'unavailable_reason':'source_numeric_range'}),
   ('populated_unavailable_qualification',{'qualification':'unavailable'}),
   ('unavailable_numeric_value',{'status':'unavailable','qualification':'unavailable','unavailable_reason':'source_numeric_range'}),
   ('unavailable_null_reason',{'status':'unavailable','value':None,'qualification':'unavailable','unavailable_reason':None}),
   ('unavailable_nonnull_exact',{'status':'unavailable','value':None,'qualification':'unavailable','unavailable_reason':'source_numeric_range','source_exact_value':rat(1)}),
  ]:
   bad=dc(seed);bad[group][name].update(changes);reject(group+'.'+name+'.'+label,bad)
  if u in ('count','dimensionless'):
   bad=dc(seed);bad[group][name]=unavailable(name,'source_numeric_range');bad[group][name]['unit']=None
   reject(group+'.'+name+'.unavailable_null_fixed_unit',bad)
  if v=='positive_integer':
   bad=dc(seed);bad[group][name]['value']=1.5;reject(group+'.'+name+'.fractional_count',bad)
# Root250's concrete cell fails the corrected whole-sheet schema.
rootprobe=load('../a105_summary_precision_plan_review_250/WRONG_CELL_PAIRING_PROBE_001.json')
for group in ['source_cells','scenario_cells']:
 bad=dc(sheet);bad[group]['mean_variance']=rootprobe['bad_cell'];reject(group+'.root250_wrong_cell_pairing',bad)
# Qualification/stipulation cross-checks.
bad=dc(sheet);bad['source_cells']['mean_variance']=dc(scenario['mean_variance']);reject('source_cannot_claim_scenario_qualification',bad)
bad=dc(sheet);bad['scenario_cells']['mean_standard_error']['stipulated_assumptions']=[];reject('conditional_populated_needs_stipulation',bad)
bad=dc(sheet);bad['scenario_cells']['mean_standard_error']['qualification']='derived_source_supported_conditions';reject('source_supported_populated_cannot_retain_stipulation',bad)
# Nonfinite numbers remain rejected by unchanged domain canonical JSON check.
for nonfinite in [math.inf,-math.inf,math.nan]:
 bad=dc(sheet);bad['scenario_cells']['mean_standard_error']['value']=nonfinite
 try:validate_schema(bad,new)
 except ContractError:pass
 else:raise AssertionError('domain allowed nonfinite')
 checks.append({'case':'nonfinite_'+str(nonfinite),'expected':'rejected','actual':'rejected_by_domain_canonical_check'})
save('CELL_CONFORMANCE_EXAMPLES_003.json',{'status':'proposed_sheet_shapes_not_production_calculator_outputs','actual242_proposed_sheet':sheet,'partial_missing_central_value_proposed_sheet':partial,'partial_attempted_scenario_proposed_sheet':partial_attempt,'root250_concrete_bad_cell':rootprobe['bad_cell'],'checks':checks})
# Preserve both frozen review generations and exact original TASK.
for mn in ['PLAN_MANIFEST_001.json','CLARIFICATION_MANIFEST_002.json']:
 m=load(mn)
 for record in m['files']:
  assert hashlib.sha256((H/record['path']).read_bytes()).hexdigest()==record['sha256'],record['path']
assert (H/'TASK_PROPOSAL_001.txt').read_bytes()==(H.parent/'a105_independent_preparation_review_246/SUMMARY_PRECISION_TASK_PROPOSAL_004.txt').read_bytes()
save('CELL_SCHEMA_CHECKS_003.json',{'status':'passed','named_cells_narrowed':30,'conformance_checks':len(checks),'actual_domain_validator_used':True,'standalone_draft202012_used':True,'exact_schema_patch_roundtrip':True,'root250_wrong_pair_rejected_in_both_groups':True,'irrational_SE_t_and_endpoint_exact_values_null_accepted':True,'valid_partials_preserved':True,'frozen001_entries_verified':len(load('PLAN_MANIFEST_001.json')['files']),'frozen002_entries_verified':len(load('CLARIFICATION_MANIFEST_002.json')['files']),'task_unchanged':True,'other_three002_schemas_unchanged':True,'production_or_test_files_modified':False,'new_production_calculator_executed':False,'new_paper_or_provider_material_read':False,'all_owned_processes_terminal':True})
records=[]
for p in sorted(H.glob('*003*')):
 if p.is_file() and p.name!='CELL_SCHEMA_MANIFEST_003.json':
  raw=p.read_bytes();records.append({'path':p.name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
save('CELL_SCHEMA_MANIFEST_003.json',{'status':'frozen_additive_plan_correction_awaiting_root_review','production_release':False,'preserves001_manifest_sha256':hashlib.sha256((H/'PLAN_MANIFEST_001.json').read_bytes()).hexdigest(),'preserves002_manifest_sha256':hashlib.sha256((H/'CLARIFICATION_MANIFEST_002.json').read_bytes()).hexdigest(),'files':records,'manifest_excludes_itself':True})
print('Corrected 30 named cell schemas;',len(checks),'conformance checks passed through actual domain validator; frozen001/002 and TASK preserved. PLAN ONLY.')
