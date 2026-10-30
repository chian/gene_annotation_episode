"""Root probes of the frozen258 implementation using explicit synthetic sources."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OWNER = ROOT / 'verification/a105_measurement_comparison_components_258'
manifest = json.loads((OWNER / 'FINAL_PIN_AND_SCOPE_010.json').read_text())
for row in manifest['owned_files'] + manifest['frozen_shared_implementation_files']:
    assert sha256((ROOT / row['path']).read_bytes()).hexdigest() == row['sha256'], row['path']
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from test_literature_measurement_comparison_components_258 import source_fixture, bind_covariance, exact
from gene_annotation_episode.literature_measurement_comparison_inputs import (
    read_measurement_comparison_inputs, compile_measurement_comparison_inputs,
)
from gene_annotation_episode.literature_measurement_comparison_calculations import populate_measurement_comparison

selection, sources, read = source_fixture()
bind_covariance(selection, sources, read, [[4, 1], [1, 9]])
original = read_measurement_comparison_inputs(selection, read_source=read)
changed = deepcopy(original)
block = changed['covariance_blocks'][0]
document = json.loads(block['raw_document_utf8'])
document['covariance'][0][0] = 9
block['raw_document_utf8'] = json.dumps(document, separators=(',', ':')) + '\n'
block['matrix_exact'][0][0] = exact(9)
try:
    calculated = populate_measurement_comparison(compile_measurement_comparison_inputs(changed))
    cells = {cell['component']: cell for cell in calculated['cells']}
    detached = {'changed_raw_document_under_unchanged_artifact_accepted': True,
                'original_artifact_ref': block['artifact_ref'],
                'actual_changed_bytes_sha256': sha256(block['raw_document_utf8'].encode()).hexdigest(),
                'difference_variance_after_tamper': cells['difference_variance']['value']}
except Exception as error:
    detached = {'changed_raw_document_under_unchanged_artifact_accepted': False,
                'exception': type(error).__name__, 'code': str(error)}

selection, sources, read = source_fixture()
old_ref = selection['source_ref']
old_bytes = sources[(old_ref, 'original')]['content']
clause = 'Reaction coefficient approximately 2.'
new_bytes = old_bytes + ('<p>' + clause + '</p>').encode()
new_digest = sha256(new_bytes).hexdigest()
new_ref = 'source_' + new_digest
def remap(value):
    if isinstance(value, dict): return {key: remap(child) for key, child in value.items()}
    if isinstance(value, list): return [remap(child) for child in value]
    return new_ref if value == old_ref else value
selection = remap(selection)
sources.clear()
sources[(new_ref, 'original')] = {'artifact_ref': 'artifact_' + new_digest, 'content': new_bytes}
start = len(old_bytes) + 3
witness = {'source_ref': new_ref, 'representation': 'original', 'start': start,
           'end': start + len(clause.encode()), 'quote': clause}
conversion = selection['common_quantity']['left_conversion']
conversion['kind'] = 'fixed_reaction_scale'
conversion['reaction'] = deepcopy(witness)
conversion['endpoint_coefficient'] = {
    'origin': 'explicit_source_token', 'implicit_value': None, 'support': [deepcopy(witness)],
    'number': {'witness': deepcopy(witness), 'number_start': clause.index('2'),
               'number_end': clause.index('2') + 1}}
conversion['common_coefficient'] = {'origin': 'implicit_unit_coefficient',
    'implicit_value': exact(1), 'number': None, 'support': [deepcopy(witness)]}
try:
    result = read_measurement_comparison_inputs(selection, read_source=read)
    inputs = compile_measurement_comparison_inputs(result)
    sheet = populate_measurement_comparison(inputs)
    cells = {cell['component']: cell for cell in sheet['cells']}
    qualified = {'valid_native_partials_survive_qualified_coefficient': True,
                 'native_left': cells['native_left'], 'converted_left': cells['converted_left']}
except Exception as error:
    qualified = {'valid_native_partials_survive_qualified_coefficient': False,
                 'exception': type(error).__name__, 'code': str(error)}

record = {'scope': 'explicit synthetic engineering probes; no new paper interpretation',
          'final_owner_manifest_sha256': sha256((OWNER / 'FINAL_PIN_AND_SCOPE_010.json').read_bytes()).hexdigest(),
          'detached_covariance_snapshot': detached, 'qualified_conversion': qualified,
          'source_bytes_changed': False, 'production_changed': False, 'goal_changed': False}
with (HERE / 'ROOT_PROBES_001.json').open('x') as output:
    json.dump(record, output, indent=2)
    output.write('\n')
print(json.dumps(record, indent=2))
