"""Focused schema-only verification; no source reads or scientific calculations."""
import ast
from copy import deepcopy
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from gene_annotation_episode import literature_controlled_response_v2_inputs as v2
from gene_annotation_episode import literature_controlled_response_v3_inputs as v3

ROOT = Path(__file__).resolve().parents[3]
DESIGN = ROOT / 'verification/literature_reference_evidence_2026-10-25_001/a105_controlled_v3_partial_design_078'
OUT = Path(__file__).resolve().parent
results = {}
schemas = v3._schemas()
assert len(schemas) == 7

def check_refs(value, root):
    if isinstance(value, dict):
        if '$ref' in value:
            reference = value['$ref']
            assert reference.startswith('#/'), reference
            node = root
            for token in reference[2:].split('/'):
                node = node[token.replace('~1', '/').replace('~0', '~')]
        for child in value.values():
            check_refs(child, root)
    elif isinstance(value, list):
        for child in value:
            check_refs(child, root)

for name, schema in schemas.items():
    Draft202012Validator.check_schema(schema)
    check_refs(schema, schema)
    text = json.dumps(schema)
    assert 'selection_basis' not in text and 'AuthoritySelectionBasis' not in text
    assert 'model_excluded_by_reading_selection' not in text
    results[name] = 'metavalid; local references complete; removed policy absent'

base = v2.controlled_response_v2_arguments_schema()
derived = deepcopy(schemas['SELECTION_SCHEMA_V3_007'])
derived['properties']['version'] = deepcopy(base['properties']['version'])
for key in set(derived['properties']) - set(base['properties']):
    del derived['properties'][key]
for key in set(derived['$defs']) - set(base['$defs']):
    del derived['$defs'][key]
derived['required'] = deepcopy(base['required'])
assert derived == base
results['original_v2_selection_base'] = 'exact equality after removal of additive v3 fields/definitions and restoration of version'

# Capture the current constructor in memory, replacing only its output function.
tree = ast.parse((DESIGN / 'build_declarations_007.py').read_text())
replacement = ast.parse('def put(n, x):\n    CAPTURE[n] = cp(x)\n').body[0]
tree.body = [replacement if isinstance(node, ast.FunctionDef) and node.name == 'put' else node
             for node in tree.body
             if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                     and isinstance(node.value.func, ast.Name) and node.value.func.id == 'print')]
ast.fix_missing_locations(tree)
captured = {}
namespace = {'__file__': str(DESIGN / 'build_declarations_007.py'), 'CAPTURE': captured}
exec(compile(tree, str(DESIGN / 'build_declarations_007.py'), 'exec'), namespace)
for name, schema in schemas.items():
    assert captured[name + '.json'] == schema, name
assert 'authority_selection_basis_contract' not in captured['API_007.json']
assert captured['API_007.json'] == json.loads((DESIGN / 'API_007.json').read_text())
results['current_constructor'] = 'all seven schemas exactly match live constructor; API matches; no files generated'

# Validate an existing entirely constructed request; no read_source callback runs.
request = json.loads((DESIGN / 'COUPLED_SCOPE_ACTUAL_V2_AND_V3_DESIGN_004.json').read_text())[0]['proposed_v3_nomination']
assert v3.validate_controlled_response_v3_selection(request) == request
results['constructed_v3_request_without_selection_basis'] = 'passes schema and selection validator; zero source IO'

local = json.loads((DESIGN / 'CONSTRUCTED_LOCAL_INPUT_007.json').read_text())
schema = schemas['LOCAL_INPUT_SCHEMA_007']
validator = Draft202012Validator(schema)
validator.validate(local)
absent = deepcopy(local)
row = absent['readings'][0]
row.update(arm=None, source_kind=None, measurement_method='not_selected')
validator.validate(absent)
fabricated = deepcopy(absent)
fabricated['readings'][0]['source_kind'] = 'primary_source'
assert list(validator.iter_errors(fabricated))
wrong_method = deepcopy(absent)
wrong_method['readings'][0]['measurement_method'] = 'text'
assert list(validator.iter_errors(wrong_method))
selected_null_kind = deepcopy(local)
selected_null_kind['readings'][0]['source_kind'] = None
assert list(validator.iter_errors(selected_null_kind))
assert schemas['LOCAL_OUTPUT_SCHEMA_007']['$defs']['LocalCell']['properties']['origin']['anyOf'][1] == {'type': 'null'}
results['nullable_absence_rules'] = 'absent arm/null source kind/not_selected accepted; fabricated source kind, wrong method and selected arm/null kind rejected; local cell null origin retained'

removed = ['TASK_AND_STEERING_009.md', 'FINAL_HANDOFF_009.md', 'construct_generation_007.py',
           'construct_task_009.py', 'make_verifier_007.py', 'verify_correction_009.py', 'verify_design_007.py']
assert all(not (DESIGN / name).exists() for name in removed)
results['deleted_policy_build_inputs'] = removed
(OUT / 'VERIFICATION.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps({'schema_count': len(schemas), 'checks': len(results), 'status': 'passed'}))
