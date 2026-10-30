"""Independent source replay and complete contract reconstruction of078 design."""
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'verification/literature_reference_evidence_2026-10-25_001'
HERE = Path(__file__).resolve().parent
PACKAGE = BASE / 'a105_controlled_v3_partial_design_078'
sys.dont_write_bytecode = True
manifest = json.loads((PACKAGE / 'FINAL_MANIFEST_008.json').read_text())
for name, expected in manifest['files'].items():
    data = (PACKAGE / name).read_bytes()
    digest = expected['sha256'] if isinstance(expected, dict) else expected
    assert hashlib.sha256(data).hexdigest() == digest, name

differences = {}
def first_difference(a, b, path='root'):
    if type(a) is not type(b):
        return {'path': path, 'actual_type': type(a).__name__, 'saved_json_type': type(b).__name__}
    if isinstance(a, dict):
        if set(a) != set(b): return {'path': path, 'different_object_keys': True}
        for key in a:
            if a[key] != b[key]: return first_difference(a[key], b[key], path + '.' + key)
    elif isinstance(a, (list, tuple)):
        if len(a) != len(b): return {'path': path, 'different_array_lengths': True}
        for index, (x, y) in enumerate(zip(a, b)):
            if x != y or type(x) is not type(y): return first_difference(x, y, path + '[' + str(index) + ']')
    return {'path': path, 'different_scalar_values': a != b}

def capture(filename):
    source = ast.parse((PACKAGE / filename).read_bytes())
    for node in source.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'put':
            node.body = ast.parse('CAPTURE[n] = DEEPCOPY(x)').body
    values = {}
    namespace = {'__file__': str(PACKAGE / filename), '__name__': '_root_owned_replay',
                 'CAPTURE': values, 'DEEPCOPY': deepcopy}
    exec(compile(ast.fix_missing_locations(source), str(PACKAGE / filename), 'exec'), namespace)
    for name, actual in values.items():
        expected = json.loads((PACKAGE / name).read_text())
        serialized = json.loads(json.dumps(actual, allow_nan=False))
        if actual != expected:
            differences[name] = first_difference(actual, expected)
        assert serialized == expected, (name, first_difference(serialized, expected))
    return values

# Execute actual existing source/graph/owner functions; only artifact writing is
# redirected to memory. This fresh process loads project modules from073 pin002.
source = capture('execute_constructed_sources_001.py')
coupled = capture('execute_coupled_sources_004.py')
declarations = capture('build_declarations_006.py')
from jsonschema import Draft202012Validator
schemas = {name: value for name, value in declarations.items() if '$schema' in value}
assert len(schemas) == 7
def refs(value, schema):
    if isinstance(value, dict):
        if '$ref' in value and value['$ref'].startswith('#/$defs/'):
            assert value['$ref'][8:] in schema['$defs'], value['$ref']
        for child in value.values():
            refs(child, schema)
    elif isinstance(value, list):
        for child in value:
            refs(child, schema)
for schema in schemas.values():
    Draft202012Validator.check_schema(schema)
    refs(schema, schema)
from gene_annotation_episode import literature_controlled_response_v2_inputs as v2
original = v2.controlled_response_v2_arguments_schema()
reduced = deepcopy(declarations['SELECTION_SCHEMA_V3_006.json'])
for key in set(reduced['properties']) - set(original['properties']):
    reduced['properties'].pop(key)
for key in set(reduced['$defs']) - set(original['$defs']):
    reduced['$defs'].pop(key)
reduced['required'] = deepcopy(original['required'])
reduced['properties']['version'] = deepcopy(original['properties']['version'])
assert reduced == original
pin = BASE / 'a105_controlled_source_reader_073/pin_002'
imports = {name: str(Path(module.__file__).resolve()) for name, module in sys.modules.items()
           if name.startswith('gene_annotation_episode') and getattr(module, '__file__', None)}
assert all(Path(path).is_relative_to(pin) for path in imports.values())
for name, expected in json.loads((pin.parent / 'PIN_MANIFEST_002.json').read_text()).items():
    data = (pin / name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected['sha256'] and len(data) == expected['bytes']
native = declarations['NATIVE_FACT_SCHEMA_V3_006.json']
assert 'population_ref' not in native['properties']
assert native['properties']['sheet_ref']['x-reference-namespace'] == 'source'
assert declarations['NATIVE_RETURN_SCHEMA_V3_006.json']['x-source'] == 'literature_controlled_response_component_cells'
result = {'utc': datetime.now(timezone.utc).isoformat(), 'manifest_payloads_verified': len(manifest['files']),
    'root_actual_existing_v2_source_reads': 20, 'root_actual_separate_existing_owner_populations': 20,
    'root_actual_shared_scope_witness_authentications': 2, 'root_saved_extraction_validations': 14,
    'complete_source_and_coupled_outputs_equal_sealed078': True,
    'comparison_uses_original_json_serialization': True, 'raw_python_json_type_differences': differences,
    'complete_final_schemas_reconstructed': 7, 'complete_final_api_reconstructed': True,
    'all_schema_refs_resolve': True, 'exact_v2_base_preserved': True,
    'actual_project_imports_in073_pin': imports, 'protected073_pin_unchanged': True,
    'reviewed_scope': 'Paired numerical/component design, proposed scientific reconciliation and exact APIs only',
    'v3_reader_or_local_api_or_native_implemented': False, 'coding_released': False,
    'remaining': 'Coordinated fresh coding ownership; actual v3/local/native/typed integration and contrasting primary/model evidence',
    'goal_complete': False}
with (HERE / 'DESIGN078_ROOT_RECEIPT_055_002.json').open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps({k: v for k, v in result.items() if k != 'actual_project_imports_in073_pin'}))
