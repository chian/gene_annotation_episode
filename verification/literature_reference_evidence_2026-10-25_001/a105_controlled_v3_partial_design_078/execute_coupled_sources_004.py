"""Actual v2 source cases + constructed v3 joint nominations, not a v3 reader."""
from copy import deepcopy as cp
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
from jsonschema import Draft202012Validator
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;PIN=BASE/'a105_controlled_source_reader_073/pin_002'
sys.dont_write_bytecode=True;sys.path.insert(0,str(PIN))
from gene_annotation_episode import literature_controlled_response_inputs as shared
from gene_annotation_episode import literature_controlled_response_v2_inputs as reader
from gene_annotation_episode import literature_controlled_response_owner_calculations as owner
spec=importlib.util.spec_from_file_location('_coupled_fixture',PIN/'tests/test_literature_controlled_response_v2_inputs.py')
fmod=importlib.util.module_from_spec(spec);spec.loader.exec_module(fmod)
ROLES=list(shared.PRIMITIVE_ORDER)
def put(n,x):
 with (HERE/n).open('x') as f:json.dump(x,f,indent=2);f.write('\n')
results=[]
for supported in [True,False]:
 f=fmod.Fixture(6)
 f.append('Bundle Q C response: 8.1 nmol/min.')
 clause=('Display bundle P jointly uses printed A and original C; display bundle Q jointly uses graphical A and bundle Q C. Both bundles use the identical stated normalization and same linear calibration. The original full covariance applies to the source means in each of P and Q. No cross-bundle combination is supported.' if supported else
  'Printed A, graphical A, original C and bundle Q C are retained alternatives. Their joint normalization, calibration and covariance-scope relationship is not established.')
 f.append(clause)
 graph_A=cp(f.args['arms'][ROLES[0]])
 primary=cp(fmod.CASES[0]['selection']['arms'][ROLES[0]]['measurement'])
 f.args['arms'][ROLES[0]]['measurement']=primary
 px=f.read();ps=owner.populate_controlled_response_owner(px['calculation_inputs'])
 primary_args=cp(f.args)
 cQ=cp(f.args['arms'][ROLES[2]])
 cQ['measurement']=dict(kind='source_literal',literal=dict(status='exact',candidates=[f.number('Bundle Q C response: 8.1 nmol/min.','8.1')],fragments=[]),unit=f.witness('nmol/min',tagged=False,start=f.data[f.main_ref].index(b'Bundle Q C response')))
 f.args['arms'][ROLES[0]]=graph_A;f.args['arms'][ROLES[2]]=cQ
 qx=f.read();qs=owner.populate_controlled_response_owner(qx['calculation_inputs'])
 witness=f.witness(clause)
 # Shared HOST witness authentication, separate from source semantic interpretation.
 with shared.open_controlled_response_sources(primary_args,read_source=f.source) as context:
  authenticated=context.witness(witness,'constructed_joint_scope')
 assert authenticated['authentication']=='exact_utf8_byte_span'
 s=cp(primary_args);s['version']='controlled_response_source_selection_v3'
 s['companion_readings']=[dict(reading_key='A_graph',primary_role=ROLES[0],reading=graph_A),dict(reading_key='C_bundle_Q',primary_role=ROLES[2],reading=cQ)]
 assignments=[dict.fromkeys(ROLES),{ROLES[0]:'A_graph',ROLES[1]:None,ROLES[2]:'C_bundle_Q',ROLES[3]:None}]
 s['joint_reading_assignments']=[dict(assignment=a,admissibility=dict(value='compatible' if supported else 'unknown',witnesses=[witness] if supported else [])) for a in assignments]
 relation=dict(value='same' if supported else 'unknown',witnesses=[witness] if supported else [])
 s['joint_scopes']=[dict(assignment_index=i,normalization=cp(relation),calibration=cp(relation),revision=cp(relation),
  covariance_scope=cp(relation),model_scope=cp(relation),covariance_selection=cp(primary_args['covariance']),
  variance_status=cp(primary_args['variance_status']),model_kind=cp(primary_args['model_kind'])) for i in range(2)]
 s['reading_reconciliations']=[dict(role=role,relationship=dict(value='alternative_estimates',witnesses=[witness]),
  authority=dict(status='not_established',reading=None,witnesses=[]),normalization=cp(relation),calibration=cp(relation),revision=cp(relation),model_scope=cp(relation)) for role in [ROLES[0],ROLES[2]]]
 s['local_pair_assignments']=[]
 Draft202012Validator(json.loads((HERE/'SELECTION_SCHEMA_V3_004.json').read_text())).validate(s)
 assert ps['cells']['controlled_response_difference']['value']==.002
 assert qs['cells']['controlled_response_difference']['value']==.00195
 assert qs['cells']['controlled_response_difference']['lower']==.00185
 assert qs['cells']['controlled_response_difference']['upper']==.00205
 assert ps['cells']['contrast_variance']['value']==qs['cells']['contrast_variance']['value']==3e-7
 results.append(dict(scenario='supported_coupled_bundles' if supported else 'unknown_joint_support',
  actual_source_text_utf8=f.data[f.main_ref].decode(),actual_source_scope_witness=authenticated,
  proposed_v3_nomination=s,controlled_source_meaning_labels_constructed=True,v3_source_interpretation_executed=False,
  primary=dict(extraction=px,sheet=ps),bundle_Q=dict(extraction=qx,sheet=qs),
  v3_alternative_input_count_if_policy_accepted=2 if supported else 0,
  unsupported_cross_assignments_never_generated=True,callback_calls=f.calls))
put('COUPLED_SCOPE_ACTUAL_V2_AND_V3_DESIGN_004.json',results)
print(json.dumps({'actual_v2_reads':4,'actual_shared_scope_witness_authentications':2,'supported_nominated_assignments':2,'unknown_nominated_assignments':2,
 'unknown_supported_alternative_sheets':0,'v3_reader_executed':False}))
