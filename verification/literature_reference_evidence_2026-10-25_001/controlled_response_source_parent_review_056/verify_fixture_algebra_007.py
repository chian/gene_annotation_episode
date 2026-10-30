"""Independent exact oracle for the proposal's invented four-arm source fixtures."""
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
STAGE = BASE / 'a105_controlled_response_design_056/reader_stage_007'
ROLES = ('protein_condition1', 'empty_condition1', 'protein_condition0', 'empty_condition0')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rational(value):
    return Fraction(str(value))


def main():
    files = ['COMPATIBILITY_RECEIPT_007.json', 'SOURCE_TEXT_007.txt',
             'SOURCE_COVARIANCE_007.json', 'SOURCE_SHARED_COVARIANCE_007.json',
             'SELECTED_ARGUMENT_EXAMPLE_007.json', 'SELECTION_SCHEMA_007.json']
    hashes = {name: digest(STAGE / name) for name in files}
    receipt = json.loads((STAGE / files[0]).read_bytes())
    source = (STAGE / 'SOURCE_TEXT_007.txt').read_bytes()
    selected = json.loads((STAGE / 'SELECTED_ARGUMENT_EXAMPLE_007.json').read_bytes())
    assert receipt['ordinary']['selection'] == selected
    assert not receipt['new_reader_implemented'] and not receipt['graph_reader_implemented']
    assert not receipt['scientific_source_or_model_run'] and receipt['runtime_observations'] == 0
    coefficient = (1, -1, -1, 1)
    expected = {'ordinary': (Fraction(6), Fraction(17, 10)),
                'shared_control': (Fraction(7), Fraction(34, 25))}
    results = []
    for name, filename in [('ordinary', 'SOURCE_COVARIANCE_007.json'),
                           ('shared_control', 'SOURCE_SHARED_COVARIANCE_007.json')]:
        case = receipt[name]
        data = json.loads((STAGE / filename).read_bytes(), parse_float=Decimal)
        raw_covariance = (STAGE / filename).read_bytes()
        values, indices, owners = [], [], []
        for role in ROLES:
            arm = case['selection']['arms'][role]
            measurement = arm['measurement']
            assert measurement['kind'] == 'source_literal'
            candidate, = measurement['literal']['candidates']
            witness = candidate['witness']
            quote = source[witness['start']:witness['end']].decode('utf-8')
            assert quote == witness['quote']
            literal = quote[candidate['number_start']:candidate['number_end']]
            value = Fraction(literal)
            operand = case['calculation_inputs']['arms'][role]
            assert rational(operand['value']) == value and operand['unit'] == 'nmol/min/mg'
            values.append(value)
            binding = case['selection']['covariance']['bindings'][role]
            index = binding['variable_index']
            indices.append(index)
            nominated = binding['label_witness']
            actual = raw_covariance[nominated['start']:nominated['end']].decode('utf-8')
            assert actual == nominated['quote']
            assert json.loads(actual) == data['variables'][index]['label']
            owner = operand['physical_observation_id']
            assert owner.encode() not in raw_covariance
            owners.append(owner)
        matrix = [[rational(data['covariance'][i][j]) for j in indices] for i in indices]
        saved = case['calculation_inputs']['covariance']
        assert saved['physical_observation_ids'] == owners
        assert matrix == [[rational(value) for value in row] for row in saved['matrix']]
        contrast = sum(c * y for c, y in zip(coefficient, values))
        variance = sum(coefficient[i] * coefficient[j] * matrix[i][j]
                       for i in range(4) for j in range(4))
        assert (contrast, variance) == expected[name]
        cells = case['sheet']['cells']
        assert rational(cells['controlled_response_difference']['value']) == contrast / 1000
        assert rational(cells['contrast_variance']['value']) == variance / 1000000
        assert cells['source_profile_log_ratio']['value'] is None
        assert cells['source_signed_index']['value'] is None
        assert case['calculation_inputs']['model_kind'] == 'none'
        if name == 'shared_control':
            assert indices == [0, 1, 2, 1] and owners[1] == owners[3]
            assert len(set(owners)) == 3
            assert case['calculation_inputs']['relationships']['control_reference_reuse'] == 'same_reference_with_stated_invariance'
        results.append({'case': name, 'native_contrast': str(contrast),
                        'native_contrast_variance': str(variance),
                        'contrast_unit': 'nmol/min/mg', 'variance_unit': '(nmol/min/mg)^2',
                        'source_variable_count': len(data['variables']),
                        'four_role_source_indices': indices})
    assert receipt['reported_uncertainty_not_used_to_construct_covariance']['count']['value'] == 3
    assert receipt['clipping_failure']['code'] == 'partial_source_numeric_token'
    assert hashes == {name: digest(STAGE / name) for name in files}
    output = {'passed': True, 'input_hashes': hashes, 'independent_exact_results': results,
              'scientific_source_review': False, 'new_reader_execution': False,
              'scope': 'Exact witness/role-map/contrast/covariance/unit oracle on two invented proposal fixtures. No covariance inference or normal-profile claim.'}
    with Path(__file__).with_name('FIXTURE_ALGEBRA_RECEIPT_007.json').open('x') as stream:
        json.dump(output, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'passed': True, 'invented_fixtures': len(results),
                      'source_variables_projected': [4, 3], 'input_artifacts_unchanged': len(files)}))


if __name__ == '__main__':
    main()
