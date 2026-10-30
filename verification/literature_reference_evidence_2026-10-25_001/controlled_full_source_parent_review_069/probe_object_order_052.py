"""Constructed public source API probe; no paper/native/model execution."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import runpy
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
fixture = runpy.run_path(str(ROOT / 'tests/test_literature_controlled_response_v2_inputs.py'))['Fixture']
from gene_annotation_episode import literature_controlled_response_v2_inputs as reader
from gene_annotation_episode import literature_controlled_response_inputs as shared

f = fixture(0)
extraction = f.read()
cases = []
def check(label, arguments, result):
    try:
        reader.validate_controlled_response_v2_extraction(arguments, result)
    except Exception as error:
        cases.append({'case': label, 'status': 'failed', 'error_type': type(error).__name__,
                      'error': str(error), 'traceback': traceback.format_exc()})
    else:
        cases.append({'case': label, 'status': 'passed'})

check('original', f.args, extraction)
check('canonical_saved_json', json.loads(json.dumps(f.args, sort_keys=True)),
      json.loads(json.dumps(extraction, sort_keys=True)))
wrong = []
for group in extraction['representation_reconciliations']:
    for role in group['roles']:
        arm = extraction['arms'][role]
        actual = arm['calculation_operand']['physical_observation_id'] if arm else None
        if actual != group['physical_observation_id']:
            wrong.append({'role': role, 'actual_operand_owner': actual,
                          'group_owner': group['physical_observation_id']})
reordered = deepcopy(f.args)
reordered['arms'] = {r: reordered['arms'][r] for r in shared.PRIMITIVE_ORDER}
other = reader.read_controlled_response_v2_inputs(reordered, read_source=f.source)
check('explicit_primitive_order', reordered, other)
row = {'scope': 'Constructed073 Fixture0 public API only; no scientific source evidence',
    'code_hashes': {p: hashlib.sha256((ROOT / 'gene_annotation_episode' / p).read_bytes()).hexdigest()
        for p in ('literature_controlled_response_inputs.py', 'literature_controlled_response_v2_inputs.py')},
    'original_arm_object_order': list(f.args['arms']), 'validation_cases': cases,
    'actual_group_owner_mismatches': wrong,
    'reordered_arguments_change_reconciliations': other['representation_reconciliations'] != extraction['representation_reconciliations'],
    'calculation_inputs_equal': other['calculation_inputs'] == extraction['calculation_inputs']}
with (HERE / 'OBJECT_ORDER_COUNTEREXAMPLE_052.json').open('x') as stream:
    json.dump(row, stream, indent=2); stream.write('\n')
print(json.dumps({k:v for k,v in row.items() if k != 'validation_cases'}))
print(json.dumps([{'case': c['case'], 'status': c['status'], 'error': c.get('error')} for c in cases]))
