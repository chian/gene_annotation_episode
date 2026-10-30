"""Real frozen073/076 reads on constructed069 bytes. NOT a v3 reader."""
from copy import deepcopy as cp
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
PIN=BASE/'a105_controlled_source_reader_073/pin_002'
sys.dont_write_bytecode=True
sys.path.insert(0,str(PIN))
from gene_annotation_episode import literature_controlled_response_v2_inputs as source
from gene_annotation_episode import literature_controlled_response_owner_calculations as owner
from gene_annotation_episode import literature_controlled_response_calculations as primitives
from gene_annotation_episode import literature_controlled_response_inputs as shared
manifest=json.loads((BASE/'a105_controlled_source_reader_073/PIN_MANIFEST_002.json').read_text())
def fp(p):
    b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
assert all(fp(PIN/n)==v for n,v in manifest.items())
spec=importlib.util.spec_from_file_location('_constructed073_fixture',PIN/'tests/test_literature_controlled_response_v2_inputs.py')
fmod=importlib.util.module_from_spec(spec);spec.loader.exec_module(fmod)
def put(n,x):
    with (HERE/n).open('x') as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n')
outputs=[]
for index in range(14):
    f=fmod.Fixture(index)
    x=f.read();s=owner.populate_controlled_response_owner(x['calculation_inputs'])
    assert source.validate_controlled_response_v2_extraction(f.args,x)==x
    outputs.append(dict(name=f.case['name'],proof_kind='actual_v2_reader_on_constructed_bytes_separate_owner_sheet',
        callback_calls=f.calls,selection=f.args,extraction=x,sheet=s))
# Same unchanged construction; execute original actual A text and actual A graph.
f=fmod.Fixture(6)
primary=cp(fmod.CASES[0]['selection']['arms']['protein_condition1']['measurement'])
f.args['arms']['protein_condition1']['measurement']=primary
text_x=f.read();text_s=owner.populate_controlled_response_owner(text_x['calculation_inputs'])
g=fmod.Fixture(6);graph_x=g.read();graph_s=owner.populate_controlled_response_owner(graph_x['calculation_inputs'])
a,b=(text_x['arms']['protein_condition1'],graph_x['arms']['protein_condition1'])
assert a['calculation_operand']['value']==10
assert b['calculation_operand']['value']==10.05
assert b['calculation_operand']['digitization_interval']==dict(lower=9.95,upper=10.15)
assert a['meanings']==b['meanings']
# Actual partial raw and local values obtainable with read-only numeric primitives;
# this explicitly exercises primitives, not the proposed component-local API.
rows=graph_x['calculation_inputs']['arms'];pair=[rows['protein_condition0'],rows['empty_condition0']]
pair_range=primitives._linear(pair,(1,-1))
local_cell=primitives._cell(pair_range,primitives._unit(pair),'condition_control_difference',pair,
    qualifications={'synthetic_fixture','approximate_source_reading','conditional_digitization','shared_reference_assumption'})
assert local_cell==graph_s['cells']['condition0_controlled_response']
assert text_s['cells']['condition0_controlled_response']==local_cell
unaffected=['empty_condition1_response','protein_condition0_response','empty_condition0_response','condition0_controlled_response']
assert all(text_s['cells'][n]==graph_s['cells'][n] for n in unaffected)
put('ACTUAL_SOURCE_OUTPUTS_001.json',outputs)
put('ACTIVE_A_ACTUAL_SOURCE_PAIR_001.json',dict(
    proof_kind='two_actual_v2_source_reads_same_constructed_roster_not_v3_execution',
    primary=dict(selection=f.args,extraction=text_x,sheet=text_s,callback_calls=f.calls),
    companion=dict(selection=g.args,extraction=graph_x,sheet=graph_s,callback_calls=g.calls),
    same_source_meanings=True,unchanged_complete_cell_names=unaffected,
    local_primitive_cell=local_cell,local_API_implemented=False,source_authority_interpreted=False,joint_support_interpreted=False))
# Explicit unknown source ownership: arithmetic magnitude survives, V not inferred.
unknown=outputs[4];assert unknown['sheet']['cells']['controlled_response_difference']['value']==.00205
assert unknown['sheet']['cells']['contrast_variance']['value'] is None
imports={n:dict(path=str(Path(m.__file__).resolve()),**fp(Path(m.__file__))) for n,m in sys.modules.items()
    if n.startswith('gene_annotation_episode') and getattr(m,'__file__',None)}
assert all(Path(r['path']).is_relative_to(PIN) for r in imports.values())
assert all(fp(PIN/n)==v for n,v in manifest.items())
put('SOURCE_EXECUTION_RECEIPT_001.json',dict(actual_v2_source_cases=16,case_count_including_both_active_A_reads=16,
    actual_separate_owner_sheets=16,actual_source_free_saved_validations=14,
    project_imports=imports,pin_file_count=len(manifest),pin_unchanged=True,
    local_primitive_checks=1,local_API_implemented=False,v3_reader_implemented=False,
    synthetic_controller_observations=0,models_or_external_services=False))
put('NUMERICAL_TABLE_001.json',[
    dict(name=r['name'],cells={n:r['sheet']['cells'][n] for n in primitives.COMPONENTS},
        source_C_validation=r['extraction']['covariance']['source_validation'],
        source_C_variable_count=len(r['extraction']['covariance']['variables']),
        source_C_provided_owner_projection=r['extraction']['covariance']['provided_owner_projection']) for r in outputs])
print(json.dumps({'actual_v2_source_reads':16,'separate_owner_sheets':16,'actual_A_values':[a['calculation_operand']['value'],b['calculation_operand']['value']],
    'same_meaning':True,'complete_unaffected_cells':len(unaffected),'local_primitive_check':1}))
