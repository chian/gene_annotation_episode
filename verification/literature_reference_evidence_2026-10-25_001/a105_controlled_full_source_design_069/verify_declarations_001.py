"""Design reconstruction/checks only, never a full-v2 source/native execution."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, ValidationError

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = HERE.parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.literature_controlled_response_owner_calculations import controlled_response_owner_arguments_schema

def read(path): return json.loads(path.read_text())
def h(data): return hashlib.sha256(data).hexdigest()
def write(name,value): (HERE/name).write_text(json.dumps(value,indent=2)+"\n")

original = BASE/'a105_controlled_graph_design_061/SELECTION_SCHEMA_V2_001.json'
copied = HERE/'SELECTION_SCHEMA_V2_001.json'
copied.write_bytes(original.read_bytes())
assert copied.read_bytes() == original.read_bytes()
owner = read(BASE/'a105_controlled_adapter_design_065/OWNER_INPUT_SCHEMA_004.json')
assert controlled_response_owner_arguments_schema() == owner

schemas = ['EXTRACTION_SCHEMA_V2_001.json','COMPANION_SELECTION_SCHEMA_V3_PROPOSAL_001.json',
    'COMPANION_EXTRACTION_SCHEMA_V3_PROPOSAL_001.json','CONDITIONAL_POPULATION_SCHEMA_V3_PROPOSAL_001.json']
object_count=0
for name in schemas:
    schema=read(HERE/name)
    Draft202012Validator.check_schema(schema)
    def walk(value):
        global object_count
        if isinstance(value,dict):
            if value.get('type')=='object':
                assert value.get('additionalProperties') is False
                assert set(value['required'])==set(value['properties'])
                object_count += 1
            if '$ref' in value:
                r=value['$ref']
                assert r.startswith('#/$defs/') and r[8:] in schema['$defs'],r
            for v in value.values():walk(v)
        elif isinstance(value,list):
            for v in value:walk(v)
    walk(schema)

v3=read(HERE/'COMPANION_SELECTION_SCHEMA_V3_PROPOSAL_001.json')
recovered=deepcopy(v3)
recovered['properties']['version']=deepcopy(read(original)['properties']['version'])
for name in ('companion_readings','joint_reading_assignments'):
    del recovered['properties'][name];recovered['required'].remove(name)
assert recovered==read(original)

cases=read(HERE/'CONSTRUCTED_SOURCE_CASES_001.json')
assert len(cases)==14
for case in cases:Draft202012Validator(read(original)).validate(case['selection'])
bad=deepcopy(cases[0]['selection']);bad['arms']['empty_condition0']['measurement']['axis'].pop('scale')
try: Draft202012Validator(read(original)).validate(bad)
except ValidationError: pass
else: raise AssertionError('axis.scale not required')
bad=deepcopy(cases[0]['selection']);bad['covariance']['matrix']=[[1]]
try: Draft202012Validator(read(original)).validate(bad)
except ValidationError: pass
else: raise AssertionError('selected numeric C accepted')

partial=read(HERE/'ACTIVE_COMPANION_CONDITIONAL_PROJECTION_001.json')
no_joint=read(HERE/'ACTIVE_COMPANION_NO_JOINT_PROJECTION_001.json')
population_schema=read(HERE/'CONDITIONAL_POPULATION_SCHEMA_V3_PROPOSAL_001.json')
for obj in (partial,no_joint):
    p=obj['population'];Draft202012Validator(population_schema).validate(p)
    assert p['final_sheet'] is None
    for component,cell in p['unaffected_cells'].items():
        if cell is None:continue
        assert cell==p['partial_sheet']['cells'][component]
        deps=p['component_dependencies'][component]
        assert not set(p['unresolved_roles']) & set(deps['numeric_roles']+deps['scientific_roles'])
        assert all(a['sheet']['cells'][component]==cell for a in p['alternatives'])
    for row in p['conditional_cells']:
        assert row['cell']==p['alternatives'][row['alternative_index']]['sheet']['cells'][row['component']]
    for c in ('controlled_response_difference','source_profile_log_ratio','source_signed_index'):
        assert p['unaffected_cells'][c] is None
assert no_joint['alternative_inputs']==[] and no_joint['population']['alternatives']==[]

request=read(HERE/'ACTIVE_COMPANION_REQUEST_V3_PROPOSAL_001.json')['selection']
Draft202012Validator(v3).validate(request)
keys={r['reading_key']:r['primary_role'] for r in request['companion_readings']}
assert len(keys)==len(request['companion_readings'])
admissible=[]
for row in request['joint_reading_assignments']:
    for role,key in row['assignment'].items():assert key is None or keys[key]==role
    if row['admissibility']['value']=='compatible':
        assert row['admissibility']['witnesses']
        admissible.append(row['assignment'])
assert [x['reading_assignment'] for x in partial['alternative_inputs']]==admissible

# Re-execute exact retained construction sources in an OWNED new directory.
# AST changes only output/base/root path assignments, never science or arithmetic.
out=HERE/'reconstructed_001';out.mkdir(exist_ok=True)
assignments=[]
for source in ('build_declarations_001.py','build_constructed_examples_001.py'):
    tree=ast.parse((HERE/source).read_text())
    replacements={'HERE':out,'BASE':BASE,'ROOT':ROOT}
    for statement in tree.body:
        if isinstance(statement,ast.Assign) and len(statement.targets)==1 and isinstance(statement.targets[0],ast.Name):
            key=statement.targets[0].id
            if key in replacements:
                statement.value=ast.Call(func=ast.Name(id='Path',ctx=ast.Load()),args=[ast.Constant(str(replacements[key]))],keywords=[])
                assignments.append(dict(source=source,assignment=key,value=str(replacements[key])))
    ast.fix_missing_locations(tree)
    namespace={'__name__':'__main__','__file__':str(HERE/source)}
    exec(compile(tree,str(HERE/source),'exec'),namespace)
generated=sorted(p.name for p in out.iterdir() if p.is_file())
for name in generated:assert (out/name).read_bytes()==(HERE/name).read_bytes(),name
write('DECLARATION_CHECK_001.json',dict(exact061_bytes=True,actual068_input_schema_equal004=True,
    schema_count=len(schemas),closed_object_schema_occurrences=object_count,all_local_refs_resolved=True,
    v3_complete_base_recovered=True,constructed_v2_cases=len(cases),active_partial_without_joint_preserved=True,
    joint_alternatives_are_exact_nominated_assignments=True,generated_payloads_byte_equal=generated,
    reconstruction_path_assignments=assignments,source_reader_executed=False,native_executed=False,model_executed=False))
print('Design declarations and retained builders reconstructed byte-for-byte; no full source/native/model execution.')
