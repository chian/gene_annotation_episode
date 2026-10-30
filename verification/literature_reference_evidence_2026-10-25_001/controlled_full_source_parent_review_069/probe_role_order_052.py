"""A JSON object's key order must not change role/owner scientific meanings."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import runpy
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
fixture = runpy.run_path(str(ROOT / 'tests/test_literature_controlled_response_v2_inputs.py'))['Fixture']
from gene_annotation_episode import literature_controlled_response_v2_inputs as reader
from gene_annotation_episode import literature_controlled_response_owner_calculations as calculator

rows = []
for order in ('original', 'canonical_object_keys', 'reversed_arm_keys'):
    f = fixture(0)
    if order == 'canonical_object_keys':
        f.args = json.loads(json.dumps(f.args, sort_keys=True))
    elif order == 'reversed_arm_keys':
        f.args['arms'] = dict(reversed(list(f.args['arms'].items())))
    e = f.read()
    mismatches = []
    for group in e['representation_reconciliations']:
        for role in group['roles']:
            operand = e['arms'][role]['calculation_operand']
            if operand['physical_observation_id'] != group['physical_observation_id']:
                mismatches.append({'role': role, 'actual_owner': operand['physical_observation_id'],
                                   'reconciliation_owner': group['physical_observation_id']})
    rows.append({'order': order, 'arm_keys': list(f.args['arms']), 'mismatches': mismatches,
        'representations': e['representation_reconciliations'],
        'sheet': calculator.populate_controlled_response_owner(e['calculation_inputs'])})
out = {'scope': 'Actual public API on constructed073 Fixture0 only', 'results': rows,
    'source_sha256': hashlib.sha256((ROOT / 'gene_annotation_episode/literature_controlled_response_inputs.py').read_bytes()).hexdigest(),
    'reconciliation_invariant': all(r['representations'] == rows[0]['representations'] for r in rows[1:]),
    'numerical_sheet_invariant': all(r['sheet'] == rows[0]['sheet'] for r in rows[1:])}
with (HERE / 'ROLE_ORDER_COUNTEREXAMPLE_052.json').open('x') as stream:
    json.dump(out, stream, indent=2); stream.write('\n')
print(json.dumps({'reconciliation_invariant': out['reconciliation_invariant'],
    'numerical_sheet_invariant': out['numerical_sheet_invariant'],
    'cases': [{'order': r['order'], 'owner_mismatches': r['mismatches']} for r in rows]}))
