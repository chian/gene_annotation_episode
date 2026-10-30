from pathlib import Path
import json,sys
from copy import deepcopy
from jsonschema import Draft202012Validator
B=Path('verification/literature_reference_evidence_2026-10-25_001');O=B/'a105_controlled_adapter_design_065'
sys.path.insert(0,str((B/'a105_controlled_response_design_056/implementation_stage_008/execution_pin_008').resolve()))
from gene_annotation_episode import literature_controlled_response_calculations as c
from gene_annotation_episode.literature_experimental_contracts import RATE_UNITS
T={'type':'string','minLength':1};N={'type':'number'}
def obj(p):return {'type':'object','properties':p,'required':list(p),'additionalProperties':False}
def arr(t,**kw):return {'type':'array','items':t,**kw}
def en(v):return {'enum':list(v)}
def null(t):return {'anyOf':[t,{'type':'null'}]}
def ref(n):return {'$ref':'#/$defs/'+n}
roles=list(c.PRIMITIVE_ORDER);meanings=['endpoint','normalization','subject_construct','condition','physical_observation']
state=en(['known','unknown','conflicting']);ordering={'const':roles}
arm=obj({'value':null(N),'threshold':null(N),'relation':en(['eq','lt','le','gt','ge','interval','none']),
'approximate':{'type':'boolean'},'unit':null(en(RATE_UNITS)),'status':en(['point','bound','missing','ambiguous','conflicting','unsupported']),
**{m+'_id':null(T) for m in meanings},'source_observation_id':null(T),'origin':en(['reported','graph_derived','synthetic']),
'digitization_interval':null(obj({'lower':N,'upper':N})),
'protein_arrangement':en(['protein_present','protein_free_control','empty_vector_control','other_specified','unknown','conflicting']),
'meaning_statuses':obj({m:state for m in meanings})})
assert set(arm['properties'])==set(c.ARM_FIELDS)
target=obj({'status':state,'canonical_id':null(T)})
rel=obj({'condition1_target':target,'condition0_target':target,
'condition_levels_relation':en(['same','different','unknown','conflicting']),
'subject_construct_across_conditions':en(['same','different','unknown','conflicting']),
**{k:en(['matched_condition_control','shared_reference_assumption','unknown','conflicting']) for k in ['condition1_control_application','condition0_control_application']},
'control_reference_reuse':en(['distinct_observations','same_reference_with_stated_invariance','unknown','conflicting']),
'nonintended_conditions':en(['matched','different','unknown','conflicting']),'intended_factor':null(T)})
assert set(rel['properties'])==set(c.RELATIONSHIP_FIELDS)
rolecov=obj({'primitive_order':ordering,'physical_observation_ids':arr(T,minItems=4,maxItems=4),
'units':arr(en(RATE_UNITS),minItems=4,maxItems=4),'matrix':arr(arr(N,minItems=4,maxItems=4),minItems=4,maxItems=4)})
ownercov=obj({'physical_observation_ids':arr(T,minItems=1,maxItems=4,uniqueItems=True),
'units':arr(en(RATE_UNITS),minItems=1,maxItems=4),'matrix':arr(arr(N,minItems=1,maxItems=4),minItems=1,maxItems=4)})
schema=obj({'version':{'const':'controlled_response_owner_inputs_v2'},'arms':obj({r:null(ref('Arm')) for r in roles}),
'relationships':ref('Relationships'),'covariance':null({'oneOf':[ref('RoleCovariance'),ref('OwnerCovariance')]}),
'variance_status':en(['known','estimated','unknown']),'model_kind':en(['none','known_joint_normal_source_means'])})
schema['$defs']={'Arm':arm,'Relationships':rel,'RoleCovariance':rolecov,'OwnerCovariance':ownercov};schema['$schema']='https://json-schema.org/draft/2020-12/schema'
newreasons=['incomplete_active_covariance','unresolved_active_reading_model','conflicting_owner_context','conflicting_source_owner_binding']
reasons=list(c.REASONS)+newreasons
quals=['synthetic_fixture','approximate_source_reading','conditional_digitization','nonintended_conditions_different','nonintended_conditions_unknown','nonintended_conditions_conflicting','unknown_control_reuse','estimated_covariance','known_normal_source_means','shared_reference_assumption','owner_cancellation','canceled_reading_unavailable','canceled_unit_unknown','canceled_representation_difference','canceled_graph_reading']
units=['umol/min','uM/min','per_min','umol/min/mg'];unitlist=units+['('+u+')^2' for u in units]+['('+u+')^-2' for u in units]+['dimensionless']
cell=obj({'value':null(N),'lower':null(N),'upper':null(N),'relation':en(['none','eq','lt','le','gt','ge','interval']),
'approximate':{'type':'boolean'},'unit':null(en(unitlist)),'status':en(['available','bounded','partial','unavailable','unsupported','conflicting']),
'origin':en(['reported','graph_derived','synthetic','calculated']),'unavailable_reason':null(arr(en(reasons),minItems=1,uniqueItems=True)),
'formula_code':en(sorted(set(c._FORMULAS))),'conditional_on':arr(en(quals),uniqueItems=True),'bound_kind':en(['none','reported_limit','conditional_digitization','mixed']),
'bound_state':obj({k:en(['unknown','unbounded','available','numeric_range_failure','not_applicable']) for k in ['lower','upper']})})
assert set(cell['properties'])==set(c.CELL_FIELDS)
group=obj({'physical_observation_id':null(T),'roles':arr(en(roles),minItems=1,maxItems=4,uniqueItems=True),
'coefficient':{'type':'integer','minimum':-2,'maximum':2},'known_owner':{'type':'boolean'}})
dep=obj({'coefficient_order':ordering,'role_coefficients':{'const':[1,-1,-1,1]},'groups':arr(group,minItems=1,maxItems=4),
'active_roles':arr(en(roles),uniqueItems=True),'canceled_roles':arr(en(roles),uniqueItems=True),
'scientific_reasons':arr(en(reasons),uniqueItems=True),'active_reading_reasons':arr(en(reasons),uniqueItems=True),
'canceled_reading_qualifications':arr(en(quals),uniqueItems=True),'reading_conflict_roles':arr(en(roles),uniqueItems=True),
'required_covariance_owner_ids':arr(T,uniqueItems=True),'provided_covariance_owner_ids':arr(T,uniqueItems=True),
'covariance_state':en(['unavailable','available','incomplete_active_coverage','scientific_blocked']),
'model_active_roles':arr(en(roles),uniqueItems=True)})
out=obj({'version':{'const':'controlled_response_owner_sheet_v2'},'primitive_order':ordering,
'inputs':{'$ref':'#/$defs/OwnerInputs'},'cells':obj({k:ref('Cell') for k in c.COMPONENTS}),'contrast_dependencies':ref('ContrastDependencies')})
# Prefix local refs in the fully embedded input schema; no unresolved external namespace.
def prefix(n):
 if isinstance(n,dict):return {k:('#/$defs/Input_'+v.split('/')[-1] if k=='$ref' and v.startswith('#/$defs/') else prefix(v)) for k,v in n.items()}
 if isinstance(n,list):return [prefix(x) for x in n]
 return n
embedded=prefix({k:v for k,v in schema.items() if k not in ['$defs','$schema']})
out['$defs']={'OwnerInputs':embedded,'Cell':cell,'ContrastDependencies':dep,**{'Input_'+k:prefix(v) for k,v in schema['$defs'].items()}};out['$schema']=schema['$schema']
Draft202012Validator.check_schema(schema);Draft202012Validator.check_schema(out)
def emit(name,value):
 with (O/name).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
emit('OWNER_INPUT_SCHEMA_003.json',schema);emit('OWNER_OUTPUT_SCHEMA_003.json',out)
root=json.loads((B/'controlled_adapter_parent_review_065/shared_representation_probe_001/RESULT_001.json').read_text())
base=deepcopy(root['mixed_compatible_readings']['inputs']);base['version']='controlled_response_owner_inputs_v2'
known=deepcopy(base);known.update(variance_status='known',covariance={'physical_observation_ids':['main1','main0'],'units':['nmol/min','nmol/min'],'matrix':[[.25,.1],[.1,.25]]})
missing=deepcopy(known)
for r in ['empty_condition1','empty_condition0']:
 missing['arms'][r].update(value=None,threshold=None,relation='none',approximate=False,status='missing',unit=None,source_observation_id=None,digitization_interval=None)
unknown=deepcopy(base);unknown['arms']['empty_condition0']['physical_observation_id']=None;unknown['arms']['empty_condition0']['meaning_statuses']['physical_observation']='unknown'
different=deepcopy(missing);different['arms']['empty_condition0']['unit']='uM/min'
absent=deepcopy(missing);absent['arms']['empty_condition0']=None
cases={'compatible_canceled_renderings':base,'active_owner_covariance_only':known,'canceled_numbers_AND_units_missing':missing,'unknown_control_owner':unknown,'explicit_incompatible_canceled_dimension':different,'whole_control_arm_absent':absent}
v=Draft202012Validator(schema)
for x in cases.values():v.validate(x)
# Shape checks do not purport to implement scientific validation/calculation.
bad=deepcopy(base);bad['reading_relationships']=[];assert not v.is_valid(bad)
emit('OWNER_SHAPE_EXAMPLES_003.json',{'scope':'proposed closed input-shape fixtures only; no owner calculator exists','examples':cases,
'expected_semantics':{'compatible_canceled_renderings':{'effect_umol_per_min':.002,'B_reading_selected':False},
'active_owner_covariance_only':{'effect_umol_per_min':.002,'variance_umol_squared_per_min_squared':3e-7},
'canceled_numbers_AND_units_missing':{'effect_umol_per_min':.002,'variance_umol_squared_per_min_squared':3e-7,'local_pairs_available':False},
'unknown_control_owner':{'effect':None,'why':'actual shared owner cannot be established'},
'explicit_incompatible_canceled_dimension':{'effect':None,'why':'explicit incompatible dimension differs from missing unused unit'},
'whole_control_arm_absent':{'effect':None,'why':'required scientific arm absent'}},'actual_semantic_validator_or_calculator_executed':False})
api={'status':'exact design declaration only, no implementation','module':'gene_annotation_episode/literature_controlled_response_owner_calculations.py','signatures':['controlled_response_owner_arguments_schema() -> dict','validate_controlled_response_owner_inputs(inputs) -> dict','populate_controlled_response_owner(inputs) -> dict'],'input':'OWNER_INPUT_SCHEMA_003.json','output':'OWNER_OUTPUT_SCHEMA_003.json','semantic_contract':'OWNER_CONTRACT_003.md','existing006_changed':False,'source_stage_or_native_integration_released':False}
emit('OWNER_API_003.json',api)
emit('OWNER_DECLARATION_CHECK_003.json',{'input_schema_meta_valid':True,'output_schema_meta_valid':True,'shape_examples_validated':len(cases),'extra_reading_relationships_rejected':True,'arm_fields_exactly006':True,'relationship_fields_exactly006':True,'cell_fields_exactly006':True,'full_ownercalculator_implemented_or_run':False,'scientific_semantic_checks':'explicit OWNER_CONTRACT_003, required implementation remains unfinished'})
print({'closed_owner_schemas':2,'shape_cases':len(cases),'pure_semantic_implementation':False})
