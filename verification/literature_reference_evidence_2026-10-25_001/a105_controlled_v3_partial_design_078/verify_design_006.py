"""Schema and numeric design proof; no proposed API is implemented here."""
from pathlib import Path
from copy import deepcopy as cp
import ast
import json
import sys
from fractions import Fraction
from jsonschema import Draft202012Validator
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT))
from gene_annotation_episode import literature_controlled_response_v2_inputs as v2
from gene_annotation_episode import literature_controlled_response_calculations as p

def put(n,x):
 with (HERE/n).open('x') as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n')
code=ast.parse((HERE/'build_declarations_006.py').read_text())
for node in code.body:
 if isinstance(node,ast.FunctionDef) and node.name=='put':node.body=ast.parse('CAPTURE[n]=cp(x)').body
captured={};ns={'__file__':str(HERE/'build_declarations_006.py'),'__name__':'_reconstruct_design','CAPTURE':captured}
exec(compile(ast.fix_missing_locations(code),str(HERE/'build_declarations_006.py'),'exec'),ns)
checks=[]
for name,s in captured.items():
 assert s==json.loads((HERE/name).read_text()),name
 if '$schema' not in s:continue
 Draft202012Validator.check_schema(s)
 def walk(x):
  if isinstance(x,dict):
   if '$ref' in x and x['$ref'].startswith('#/$defs/'):assert x['$ref'][8:] in s.get('$defs',{}),(name,x['$ref'])
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(s);checks.append(name)
S=captured['SELECTION_SCHEMA_V3_006.json'];baseline=v2.controlled_response_v2_arguments_schema();reduced=cp(S)
for k in set(reduced['properties'])-set(baseline['properties']):reduced['properties'].pop(k)
reduced['required']=cp(baseline['required']);reduced['properties']['version']=cp(baseline['properties']['version'])
for k in set(reduced['$defs'])-set(baseline['$defs']):reduced['$defs'].pop(k)
assert reduced==baseline
active=json.loads((HERE/'ACTIVE_A_ACTUAL_SOURCE_PAIR_001.json').read_text())
text=active['primary']['extraction'];graph=active['companion']['extraction']
R=list(text['arms']);readings=[]
for role in R:
 arm=text['arms'][role];readings.append(dict(reading=dict(role=role,reading_key=None),arm=arm['calculation_operand'],
  reported_uncertainty=arm['reported_uncertainty']['canonical'],source_kind=arm['selection']['source_kind'],
  measurement_method='graph' if arm['graph_details'] else 'text'))
arm=graph['arms'][R[0]]
readings.append(dict(reading=dict(role=R[0],reading_key='A_graph'),arm=arm['calculation_operand'],
 reported_uncertainty=arm['reported_uncertainty']['canonical'],source_kind=arm['selection']['source_kind'],measurement_method='graph'))
L=dict(version='controlled_response_local_inputs_v1',readings=readings,pairs=[dict(pair_key='condition0_original',condition='condition0',
 protein=dict(role=R[2],reading_key=None),control=dict(role=R[3],reading_key=None),
 target=text['calculation_inputs']['relationships']['condition0_target'],control_application='shared_reference_assumption',
 joint_admissibility='compatible',scope_state='same',covariance_index=0,
 protein_binding=text['covariance']['bindings'][R[2]],control_binding=text['covariance']['bindings'][R[3]],variance_status='known')],source_covariances=[{**{k:text['covariance'][k] for k in ['source_ref','artifact_ref','byte_sha256','raw_text','variables','matrix_tokens','exact_matrix','source_model','source_validation','diagnostics']},'document_state':'available'}])
Draft202012Validator(captured['LOCAL_INPUT_SCHEMA_006.json']).validate(L)
cov=L['source_covariances'][0];full=[[Fraction(int(v['numerator']),int(v['denominator'])) for v in row] for row in cov['exact_matrix']]
a,b=[r['arm'] for r in readings[2:4]];ia,ib=[L['pairs'][0][n]['source_variable_index'] for n in ['protein_binding','control_binding']]
sa,sb=p._scale(a['unit']),p._scale(b['unit'])
V=full[ia][ia]*sa*sa+full[ib][ib]*sb*sb-2*full[ia][ib]*sa*sb
assert V==Fraction(45,100000000)
qual={'synthetic_fixture','approximate_source_reading','conditional_digitization','shared_reference_assumption'}
local_pair=dict(pair_key='condition0_original',difference=p._cell(p._linear([a,b],(1,-1)),p._unit([a,b]),'condition_control_difference',[a,b],qualifications=qual),
 variance=p._cell(p._point(V),'(umol/min)^2','local_joint_covariance',[a,b],qualifications=qual),
 standard_uncertainty=p._cell(p._point(p._sqrt(V)),'umol/min','local_square_root_variance',[a,b],qualifications=qual))
assert local_pair['difference']==active['local_primitive_cell']
selectors=[dict(role=r,reading_key=None) for r in [R[2],R[3]]]
def deps(covariance=False):return dict(scientific_readings=selectors,numeric_readings=selectors,uncertainty_readings=[],
 covariance_index=0 if covariance else None,covariance_owner_ids=[a['physical_observation_id'],b['physical_observation_id']] if covariance else [],
 source_variable_indices=[ia,ib] if covariance else [],model_readings=[],unresolved_readings=[],
 numeric_fields=[dict(reading=r,fields=['unit','status','relation','approximate','origin','digitization_interval_presence'] if covariance else ['value','threshold','relation','approximate','unit','status','origin','digitization_interval']) for r in selectors],
 full_source_covariance_required=covariance)
local_pair['dependencies']={n:deps(n!='difference') for n in ['difference','variance','standard_uncertainty']}
raw=[]
for reading in readings:
 ar=reading['arm'];rs=reading['reading'];q=set()
 if ar['origin']=='synthetic':q.add('synthetic_fixture')
 if ar['approximate']:q.add('approximate_source_reading')
 if ar['digitization_interval'] is not None:q.add('conditional_digitization')
 cell=p._cell(p._range(ar),p._unit([ar]),'source_response',[ar],raw=True,qualifications=q)
 raw.append(dict(reading=rs,cell=cell,reported_uncertainty=reading['reported_uncertainty'],
  dependencies=dict(scientific_readings=[rs],numeric_readings=[rs],uncertainty_readings=[],covariance_index=None,
    covariance_owner_ids=[],source_variable_indices=[],model_readings=[],unresolved_readings=[],
    numeric_fields=[dict(reading=rs,fields=['value','threshold','relation','approximate','unit','status','origin','digitization_interval'])],full_source_covariance_required=False)))
local=dict(version='controlled_response_local_sheet_v1',inputs=L,raw=raw,pairs=[local_pair],
 full_covariance_checks=[dict(covariance_index=0,source_validation='valid',document_state=cov['document_state'])])
Draft202012Validator(captured['LOCAL_OUTPUT_SCHEMA_006.json']).validate(local)
put('CONSTRUCTED_LOCAL_INPUT_006.json',L)
put('CONSTRUCTED_LOCAL_EXPECTED_OUTPUT_006.json',local)
put('DESIGN_VERIFICATION_006.json',dict(schema_count=len(checks),schemas=checks,complete_constructor_reconstruction=True,
 exact_v2_base_preserved=True,all_local_ref_targets_present=True,actual_source_backed_local_input_schema=True,
 actual_source_backed_expected_local_result_schema=True,actual_local_numeric_primitives=True,
 proposed_local_API_executed=False,proposed_v3_reader_executed=False,
 actual_pair_difference=local_pair['difference'],actual_pair_variance=local_pair['variance'],actual_pair_standard_uncertainty=local_pair['standard_uncertainty']))
print(json.dumps({'schemas_checked':len(checks),'complete_reconstruction':True,'local_difference':local_pair['difference']['value'],
 'local_V':local_pair['variance']['value'],'local_SE':local_pair['standard_uncertainty']['value'],'local_API_implemented':False}))
