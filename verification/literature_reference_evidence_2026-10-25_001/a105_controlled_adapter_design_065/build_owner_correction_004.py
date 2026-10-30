from pathlib import Path
from copy import deepcopy
import json
from jsonschema import Draft202012Validator
B=Path('verification/literature_reference_evidence_2026-10-25_001');O=B/'a105_controlled_adapter_design_065'
def emit(name,v):
 with (O/name).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
ins=json.loads((O/'OWNER_INPUT_SCHEMA_003.json').read_text());outs=json.loads((O/'OWNER_OUTPUT_SCHEMA_003.json').read_text())
for node in [outs['$defs']['Cell']['properties']['conditional_on']['items'],outs['$defs']['ContrastDependencies']['properties']['canceled_reading_qualifications']['items']]:
 for q in ['canceled_source_reading_conflict','canceled_reading_domain_conflict']:
  if q not in node['enum']:node['enum'].append(q)
Draft202012Validator.check_schema(ins);Draft202012Validator.check_schema(outs)
with (O/'OWNER_INPUT_SCHEMA_004.json').open('xb') as f:f.write((O/'OWNER_INPUT_SCHEMA_003.json').read_bytes())
emit('OWNER_OUTPUT_SCHEMA_004.json',outs)
prior=json.loads((O/'OWNER_SHAPE_EXAMPLES_003.json').read_text());cases=deepcopy(prior['examples'])
b=deepcopy(cases['active_owner_covariance_only'])
disjoint=deepcopy(b);disjoint['arms']['empty_condition0'].update(value=8.05,digitization_interval={'lower':7.95,'upper':8.15})
status=deepcopy(b);status['arms']['empty_condition0'].update(value=None,relation='none',status='conflicting',digitization_interval=None)
owner=deepcopy(disjoint);owner['arms']['empty_condition0']['physical_observation_id']=None;owner['arms']['empty_condition0']['meaning_statuses']['physical_observation']='conflicting'
active=deepcopy(b);active['arms']['protein_condition1'].update(value=None,relation='none',status='conflicting',digitization_interval=None)
invalid=deepcopy(b);invalid['covariance']={'primitive_order':list(b['arms']),'physical_observation_ids':['main1','controlB','main0','controlB'],'units':['nmol/min']*4,'matrix':[[.25,0,.1,0],[0,-.04,0,-.04],[.1,0,.25,0],[0,-.04,0,-.04]]}
cases.update({'disjoint_canceled_readings':disjoint,'canceled_numeric_status_conflicting':status,'actual_owner_meaning_conflicting':owner,'active_numeric_conflict':active,'invalid_FULL_covariance_despite_canceled_B':invalid})
v=Draft202012Validator(ins)
for name,x in cases.items():v.validate(x)
expected=deepcopy(prior['expected_semantics']);expected.update({
'disjoint_canceled_readings':{'effect_umol_per_min':.002,'variance_umol_squared_per_min_squared':3e-7,'required_qualification':'canceled_reading_domain_conflict','B_value_selected':False},
'canceled_numeric_status_conflicting':{'effect_umol_per_min':.002,'variance_umol_squared_per_min_squared':3e-7,'required_qualification':'canceled_source_reading_conflict','B_value_selected':False},
'actual_owner_meaning_conflicting':{'effect':None,'why':'scientific owner meaning truly conflicting'},
'active_numeric_conflict':{'effect':None,'why':'an active numerical operand is conflicting'},
'invalid_FULL_covariance_despite_canceled_B':{'semantic_validation':'invalid full covariance; no favorable active submatrix rescue','new_semantic_validation_run':False}})
emit('OWNER_SHAPE_EXAMPLES_004.json',{'scope':'closed input-shape fixtures plus explicit expected semantics; no new owner calculator executed','examples':cases,'expected_semantics':expected,'actual_semantic_validator_or_calculator_executed':False})
root=json.loads((B/'controlled_adapter_parent_review_065/shared_representation_probe_001/RESULT_001.json').read_text())
cells=deepcopy(root['mixed_compatible_readings']['sheet']['cells'])
num=root['same_graph_known_covariance']['cells'];ef=root['same_text']['sheet']['cells']['controlled_response_difference']
cells['controlled_response_difference']=deepcopy(ef)
q=['canceled_graph_reading','canceled_representation_difference','owner_cancellation','shared_reference_assumption','synthetic_fixture']
for key in ['controlled_response_difference','contrast_variance','contrast_standard_uncertainty','contrast_precision','source_profile_log_ratio','source_signed_index']:
 if key!='controlled_response_difference':cells[key]=deepcopy(num[key])
 cells[key]['approximate']=False;cells[key]['conditional_on']=q
 if key in ['source_profile_log_ratio','source_signed_index']:cells[key]['unavailable_reason']=['observation_model_unselected']
roles=['protein_condition1','empty_condition1','protein_condition0','empty_condition0']
sheet={'version':'controlled_response_owner_sheet_v2','primitive_order':roles,'inputs':b,'cells':cells,
'contrast_dependencies':{'coefficient_order':roles,'role_coefficients':[1,-1,-1,1],
'groups':[{'physical_observation_id':'main1','roles':[roles[0]],'coefficient':1,'known_owner':True},
{'physical_observation_id':'controlB','roles':[roles[1],roles[3]],'coefficient':0,'known_owner':True},
{'physical_observation_id':'main0','roles':[roles[2]],'coefficient':-1,'known_owner':True}],
'active_roles':[roles[0],roles[2]],'canceled_roles':[roles[1],roles[3]],'scientific_reasons':[],'active_reading_reasons':[],
'canceled_reading_qualifications':['canceled_graph_reading','canceled_representation_difference','owner_cancellation'],
'reading_conflict_roles':[],'required_covariance_owner_ids':['main1','main0'],'provided_covariance_owner_ids':['main1','main0'],
'covariance_state':'available','model_active_roles':[roles[0],roles[2]]}}
Draft202012Validator(outs).validate(sheet);emit('OWNER_EXPECTED_SHEET_004.json',sheet)
api=json.loads((O/'OWNER_API_003.json').read_text());api.update(input='OWNER_INPUT_SCHEMA_004.json',output='OWNER_OUTPUT_SCHEMA_004.json',semantic_contract=['OWNER_CONTRACT_003.md','OWNER_CONTRACT_CORRECTION_004.md']);emit('OWNER_API_004.json',api)
def refs(node):
 if isinstance(node,dict):
  if '$ref' in node:yield node['$ref']
  for item in node.values():yield from refs(item)
 elif isinstance(node,list):
  for item in node:yield from refs(item)
for name,s in [('input',ins),('output',outs)]:
 for r in refs(s):assert r.startswith('#/$defs/') and r.split('/')[-1] in s['$defs'],(name,r)
emit('OWNER_DECLARATION_CHECK_004.json',{'input_schema_meta_valid':True,'output_schema_meta_valid':True,'input_bytes_unchanged_from003':True,'all_local_schema_references_resolve':True,'shape_cases':len(cases),'expected_sheet_closed_shape_valid':True,'expected_sheet_origin':'HAND-CONSTRUCTED proposed output, borrowing actual frozen006 numerical cell records; not actual new owner calculator result','canceled_numeric_conflicts_are_qualifications':True,'true_scientific_owner_conflicts_still_block':True,'new_owner_semantic_implementation_or_execution':False})
print({'closed_schemas':2,'shape_cases':len(cases),'expected_sheet_shape_valid':True,'new_owner_calculator_implemented':False})
