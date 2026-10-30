"""Independent complete reconstruction of corrected007 literature contracts."""
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
sys.path.insert(0, str(ROOT))
manifest = json.loads((PACKAGE / 'FINAL_MANIFEST_009.json').read_text())
for name, expected in manifest['files'].items():
    digest = expected['sha256'] if isinstance(expected, dict) else expected
    assert hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() == digest, name
old = json.loads((PACKAGE / 'FINAL_MANIFEST_008.json').read_text())
for name, expected in old['files'].items():
    digest = expected['sha256'] if isinstance(expected, dict) else expected
    assert hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() == digest, name
def capture(filename):
    tree = ast.parse((PACKAGE / filename).read_bytes())
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'put':
            node.body = ast.parse('CAPTURE[n] = DEEPCOPY(x)').body
    values = {}
    exec(compile(ast.fix_missing_locations(tree), str(PACKAGE / filename), 'exec'),
        {'__file__': str(PACKAGE / filename), '__name__': '_root_contract_review',
         'CAPTURE': values, 'DEEPCOPY': deepcopy})
    for name, value in values.items():
        assert json.loads(json.dumps(value)) == json.loads((PACKAGE / name).read_text()), name
    return values
declarations = capture('build_declarations_007.py')
checks = capture('verify_correction_009.py')
from jsonschema import Draft202012Validator
schemas = {n: s for n, s in declarations.items() if '$schema' in s}
assert len(schemas) == 7
def refs(value, schema):
    if isinstance(value, dict):
        if '$ref' in value and value['$ref'].startswith('#/$defs/'):
            assert value['$ref'][8:] in schema['$defs'], value['$ref']
        for child in value.values(): refs(child, schema)
    elif isinstance(value, list):
        for child in value: refs(child, schema)
for schema in schemas.values():
    Draft202012Validator.check_schema(schema)
    refs(schema, schema)
from gene_annotation_episode import literature_controlled_response_v2_inputs as v2
original = v2.controlled_response_v2_arguments_schema()
reduced = deepcopy(declarations['SELECTION_SCHEMA_V3_007.json'])
for key in set(reduced['properties']) - set(original['properties']): reduced['properties'].pop(key)
for key in set(reduced['$defs']) - set(original['$defs']): reduced['$defs'].pop(key)
reduced['required'] = deepcopy(original['required'])
reduced['properties']['version'] = deepcopy(original['properties']['version'])
assert reduced == original
result = {'utc': datetime.now(timezone.utc).isoformat(), 'final009_payloads_verified': len(manifest['files']),
    'original008_payloads_preserved': len(old['files']), 'complete_schemas_reconstructed': len(schemas),
    'complete_api_reconstructed': True, 'complete_correction_examples_reexecuted': True,
    'all_schema_refs_resolve': True, 'exact_v2_selection_base_preserved': True,
    'reviewed_contract': 'Closed witnessed selection basis, explicit model eligibility, truthful absent primary/source-kind/origin and distinct selected-missing semantics',
    'implementation_status': 'No proposed v3/local/native API has executed; design examples do not prove implementation',
    'accepted_scope': 'Corrected007/009 design contract for explicit coordinated implementation release',
    'goal_complete': False}
with (HERE / 'CORRECTED_DESIGN078_ROOT_RECEIPT_056.json').open('x') as stream:
    json.dump(result, stream, indent=2); stream.write('\n')
print(json.dumps(result))
