"""Independent regression of root265's failures; explicit synthetic inputs only."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
manifest_path = Path(sys.argv[1]).resolve()
manifest = json.loads(manifest_path.read_text())
shared_manifest_path = ROOT / 'verification/a105_measurement_comparison_components_258/FINAL_PIN_AND_SCOPE_010.json'
shared_manifest = json.loads(shared_manifest_path.read_text())


def check_pin():
    rows = manifest['owned_files'] + shared_manifest['frozen_shared_implementation_files']
    for row in rows:
        assert sha256((ROOT / row['path']).read_bytes()).hexdigest() == row['sha256'], row['path']
    return len(rows)


pin_count = check_pin()
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from test_literature_measurement_comparison_components_258 import source_fixture, bind_covariance, exact
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_measurement_comparison_inputs import (
    read_measurement_comparison_inputs, compile_measurement_comparison_inputs,
)
from gene_annotation_episode.literature_measurement_comparison_calculations import populate_measurement_comparison


def cells(extraction):
    return {c['component']: c for c in populate_measurement_comparison(
        compile_measurement_comparison_inputs(extraction))['cells']}


selection, sources, read = source_fixture()
bind_covariance(selection, sources, read, [[4, 1], [1, 9]])
original = read_measurement_comparison_inputs(selection, read_source=read)
assert cells(original)['difference_variance']['exact_value'] == exact(11)
checks = []
for alteration in ('changed_document_and_matrix', 'available_without_raw_document'):
    changed = deepcopy(original)
    block = changed['covariance_blocks'][0]
    if alteration == 'changed_document_and_matrix':
        document = json.loads(block['raw_document_utf8'])
        document['covariance'][0][0] = 9
        block['raw_document_utf8'] = json.dumps(document, separators=(',', ':')) + '\n'
        block['matrix_exact'][0][0] = exact(9)
    else:
        block['raw_document_utf8'] = None
    try:
        cells(changed)
    except ExperimentalContractError as error:
        checks.append({'case': alteration, 'rejected': True, 'code': str(error)})
    else:
        raise AssertionError('Tampered covariance accepted: ' + alteration)


def qualified_coefficient(*, tight):
    selection, sources, read = source_fixture()
    old_ref = selection['source_ref']
    old_bytes = sources[(old_ref, 'original')]['content']
    clause = 'Reaction coefficient approximately 2.'
    new_bytes = old_bytes + ('<p>' + clause + '</p>').encode()
    digest = sha256(new_bytes).hexdigest()
    new_ref = 'source_' + digest

    def remap(value):
        if isinstance(value, dict):
            return {key: remap(child) for key, child in value.items()}
        if isinstance(value, list):
            return [remap(child) for child in value]
        return new_ref if value == old_ref else value

    selection = remap(selection)
    sources.clear()
    sources[(new_ref, 'original')] = {'artifact_ref': 'artifact_' + digest, 'content': new_bytes}
    start = len(old_bytes) + 3
    witness = {'source_ref': new_ref, 'representation': 'original', 'start': start,
               'end': start + len(clause.encode()), 'quote': clause}
    number_witness = deepcopy(witness)
    offset = clause.index('2')
    if tight:
        number_witness.update(start=start + offset, end=start + offset + 1, quote='2')
        offset = 0
    conversion = selection['common_quantity']['left_conversion']
    conversion.update(kind='fixed_reaction_scale', reaction=deepcopy(witness))
    conversion['endpoint_coefficient'] = {
        'origin': 'explicit_source_token', 'implicit_value': None, 'support': [deepcopy(witness)],
        'number': {'witness': number_witness, 'number_start': offset, 'number_end': offset + 1}}
    conversion['common_coefficient'] = {
        'origin': 'implicit_unit_coefficient', 'implicit_value': exact(1),
        'number': None, 'support': [deepcopy(witness)]}
    extraction = read_measurement_comparison_inputs(selection, read_source=read)
    sources.clear()  # No original-source callback can supply detached compilation.
    result = cells(extraction)
    assert result['native_left']['value'] == 20
    assert result['native_right']['value'] == 22
    assert result['converted_left']['value'] is None
    assert 'uncertain_conversion_unimplemented' in result['converted_left']['reasons']['implementation']
    assert result['converted_right']['value'] == 22
    return {'case': 'approximate_coefficient_tight' if tight else 'approximate_coefficient_full_field',
            'native_left': 20, 'native_right': 22, 'converted_left': None,
            'implementation_reason': 'uncertain_conversion_unimplemented',
            'source_callbacks_removed_before_compile': True}


checks.extend(qualified_coefficient(tight=tight) for tight in (False, True))
assert check_pin() == pin_count
record = {'scope': 'independent explicit synthetic regression; no paper or selected episode',
          'implementation_manifest': str(manifest_path.relative_to(ROOT)),
          'implementation_manifest_sha256': sha256(manifest_path.read_bytes()).hexdigest(),
          'unchanged_shared_manifest_sha256': sha256(shared_manifest_path.read_bytes()).hexdigest(),
          'pinned_files_checked_before_and_after': pin_count, 'checks': checks,
          'production_modified': False, 'goal_modified': False}
with (HERE / 'ROOT_REPAIRED_PARTIALS_005.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
print(json.dumps(record, indent=2))
