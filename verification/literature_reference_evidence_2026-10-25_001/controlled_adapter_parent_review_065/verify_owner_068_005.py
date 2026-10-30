"""Independent root pin/custody proof and new parsed-input arithmetic probes."""
from copy import deepcopy
from datetime import datetime, timezone
import difflib
from fractions import Fraction
import hashlib
import inspect
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
DELIVERY = BASE / 'a105_controlled_owner_calculator_068'
PIN = DELIVERY / 'pin_002'
DESIGN = BASE / 'a105_controlled_adapter_design_065'
sys.path.insert(0, str(PIN))
sys.dont_write_bytecode = True


def fp(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    manifest_path = DELIVERY / 'MANIFEST_002.json'
    assert fp(manifest_path)['sha256'] == 'cc1ece1cdac9d1a64c6915823ddc3013d3bf3fdf2017656556cc71b8e111d708'
    manifest = json.loads(manifest_path.read_bytes())['files']
    for name, row in manifest.items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert fp(DELIVERY / name) == row, name
    assert {str(p.relative_to(DELIVERY)) for p in DELIVERY.rglob('*') if p.is_file()} == set(manifest) | {'MANIFEST_002.json', 'SHA256SUMS_002.txt'}
    checksums = dict(line.split('  ', 1)[::-1] for line in (DELIVERY / 'SHA256SUMS_002.txt').read_text().splitlines())
    assert checksums == {**{name: row['sha256'] for name, row in manifest.items()}, 'MANIFEST_002.json': fp(manifest_path)['sha256']}
    pin_manifest = json.loads((DELIVERY / 'PIN_MANIFEST_002.json').read_bytes())
    assert {str(p.relative_to(PIN)) for p in PIN.rglob('*') if p.is_file()} == set(pin_manifest)
    for name, row in pin_manifest.items():
        assert fp(PIN / name) == row == fp(ROOT / name), name
    before = json.loads((DELIVERY / 'BEFORE_001.json').read_bytes())
    for name, row in before.items():
        assert fp(ROOT / name) == row
    design_manifest = json.loads((DESIGN / 'MANIFEST_006.json').read_bytes())['entries']
    for row in design_manifest:
        assert fp(DESIGN / row['path']) == {'bytes': row['bytes'], 'sha256': row['sha256']}
    generated_patch = ''
    for name in ('gene_annotation_episode/literature_controlled_response_owner_calculations.py',
                 'tests/test_literature_controlled_response_owner_calculations.py'):
        generated_patch += ''.join(difflib.unified_diff([], (ROOT / name).read_text().splitlines(True),
            fromfile='/dev/null', tofile='b/' + name))
    assert generated_patch.encode() == (DELIVERY / 'IMPLEMENTATION_002.patch').read_bytes()
    process = json.loads((DELIVERY / 'PIN_TEST_PROCESS_002.json').read_bytes())
    assert process['actual_exit_code'] == 0 and process['actual_passed_count'] == 70
    assert '70 passed in 0.56s' in (DELIVERY / 'PIN_TEST_RUN_002.txt').read_text()
    assert json.loads((DELIVERY / 'COVARIANCE_GUARD_FAILURE_002.json').read_bytes())['actual_exit_code'] == 1
    from jsonschema import Draft202012Validator
    from gene_annotation_episode import literature_controlled_response_owner_calculations as owner
    from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
    input_schema = json.loads((DESIGN / 'OWNER_INPUT_SCHEMA_004.json').read_bytes())
    output_schema = json.loads((DESIGN / 'OWNER_OUTPUT_SCHEMA_004.json').read_bytes())
    assert owner.controlled_response_owner_arguments_schema() == input_schema
    shapes = json.loads((DESIGN / 'OWNER_SHAPE_EXAMPLES_004.json').read_bytes())['examples']
    fixture = deepcopy(shapes['active_owner_covariance_only'])
    roles = ('protein_condition1', 'empty_condition1', 'protein_condition0', 'empty_condition0')
    fixture['arms'][roles[0]].update(value=13.5, unit='nmol/min')
    fixture['arms'][roles[2]].update(value=9.25, unit='nmol/min')
    for i in (1, 3):
        fixture['arms'][roles[i]].update(value=None, threshold=None, relation='none', approximate=False,
            unit=None, status='missing', source_observation_id=None, digitization_interval=None)
    a, c = (fixture['arms'][roles[i]]['physical_observation_id'] for i in (0, 2))
    fixture.update(covariance={'physical_observation_ids': [a, c], 'units': ['nmol/min', 'nmol/min'],
        'matrix': [[.36, .12], [.12, .49]]}, variance_status='known', model_kind='known_joint_normal_source_means')
    actual = {}

    def run(name, inputs):
        Draft202012Validator(input_schema).validate(inputs)
        original = deepcopy(inputs)
        result = owner.populate_controlled_response_owner(inputs)
        assert inputs == original and result['inputs'] == original
        Draft202012Validator(output_schema).validate(result)
        json.dumps(result, allow_nan=False)
        actual[name] = result
        return result

    e, v = Fraction(17, 4000), Fraction(61, 100_000_000)
    result = run('new_13_5_minus_9_25_missing_shared_control', fixture)
    cells = result['cells']
    assert cells['controlled_response_difference']['value'] == float(e)
    assert cells['contrast_variance']['value'] == float(v)
    assert math.isclose(cells['contrast_standard_uncertainty']['value'], math.sqrt(float(v)), rel_tol=1e-15)
    assert cells['source_profile_log_ratio']['value'] == float(e * abs(e) / (2 * v))
    assert all(cells[name]['value'] is None for name in ('condition1_controlled_response', 'condition0_controlled_response'))
    assert result['contrast_dependencies']['active_roles'] == [roles[0], roles[2]]
    unknown = deepcopy(fixture)
    unknown['arms'][roles[2]]['physical_observation_id'] = None
    unknown['arms'][roles[2]]['meaning_statuses']['physical_observation'] = 'unknown'
    unknown['covariance'] = {'physical_observation_ids': [a], 'units': ['nmol/min'], 'matrix': [[.36]]}
    result = run('new_unknown_active_owner', unknown)
    assert result['cells']['controlled_response_difference']['value'] == float(e)
    assert result['contrast_dependencies']['covariance_state'] == 'incomplete_active_coverage'
    assert result['cells']['contrast_variance']['value'] is None
    blocked = deepcopy(fixture)
    blocked['relationships']['condition0_control_application'] = 'unknown'
    result = run('new_scientific_application_unknown', blocked)
    assert result['cells']['controlled_response_difference']['value'] is None
    assert 'unknown_control_application' in result['cells']['controlled_response_difference']['unavailable_reason']
    invalid = deepcopy(fixture)
    b = invalid['arms'][roles[1]]['physical_observation_id']
    invalid['covariance'] = {'primitive_order': list(roles), 'physical_observation_ids': [a, b, c, b],
        'units': ['nmol/min'] * 4,
        'matrix': [[.36, 0, .12, 0], [0, -.04, 0, -.04], [.12, 0, .49, 0], [0, -.04, 0, -.04]]}
    try:
        owner.populate_controlled_response_owner(invalid)
    except ExperimentalContractError as error:
        assert error.code == 'positive_semidefinite_covariance_required'
        actual['new_invalid_full_canceled_covariance'] = {'code': error.code, 'field': error.field}
    else:
        raise AssertionError('invalid full covariance was rescued')
    imports = []
    for name, module in sorted(sys.modules.items()):
        if name.startswith('gene_annotation_episode') and getattr(module, '__file__', None):
            path = Path(inspect.getfile(module)).resolve()
            assert path.is_relative_to(PIN)
            imports.append({'module': name, 'path': str(path), **fp(path)})
    assert len(imports) == 4
    receipt = {'utc': datetime.now(timezone.utc).isoformat(), 'sealed_payloads': len(manifest),
        'pin_files': len(pin_manifest), 'original_baseline_files': len(before),
        'unchanged_design_payloads': len(design_manifest), 'exact_patch_reconstructed': True,
        'reviewed_actual_targeted_tests': 70, 'root_new_constructed_cases': len(actual),
        'actual_project_imports': imports, 'new_case_effect_umol_per_min': float(e),
        'new_case_variance_umol_squared_per_min_squared': float(v),
        'full_code_tests_and_helpers_read': True, 'paper_source_or_model_execution': False,
        'native_or_typed_delivery_proved': False, 'runtime_observations': 0,
        'scope': 'Pure owner calculator accepted only; source/native integration remains unfinished'}
    for filename, value in (('ROOT_CONSTRUCTED_CASES_005.json', actual), ('OWNER_CALCULATOR_ROOT_RECEIPT_005.json', receipt)):
        with (HERE / filename).open('x') as stream:
            json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({key: receipt[key] for key in ('sealed_payloads', 'pin_files', 'original_baseline_files',
        'unchanged_design_payloads', 'root_new_constructed_cases', 'new_case_effect_umol_per_min',
        'new_case_variance_umol_squared_per_min_squared', 'native_or_typed_delivery_proved')}))


if __name__ == '__main__':
    main()
