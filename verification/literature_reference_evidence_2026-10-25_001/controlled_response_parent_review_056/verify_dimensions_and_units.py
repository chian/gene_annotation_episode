"""Independent synthetic unit-invariance and dimension-failure oracle."""
from copy import deepcopy
from fractions import Fraction
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.literature_controlled_response_calculations import (
    populate_controlled_response, PRIMITIVE_ORDER, COMPONENTS)


def main():
    source = ROOT / 'gene_annotation_episode/literature_controlled_response_calculations.py'
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    original = json.loads((BASE / 'a105_controlled_response_design_056/pure_stage_003/INPUT_CONTRACT_EXAMPLE_003.json').read_bytes())
    failures = []
    for left, right in (('umol/min', 'uM/min'), ('per_min', 'umol/min/mg'),
                        ('umol/min/mg', 'uM/min')):
        data = deepcopy(original)
        data.update(covariance=None, variance_status='unknown', model_kind='none')
        for i, role in enumerate(PRIMITIVE_ORDER):
            data['arms'][role]['unit'] = left if i < 2 else right
        result = populate_controlled_response(data)['cells']
        assert result[COMPONENTS[4]]['value'] == 10
        assert result[COMPONENTS[5]]['value'] == 4
        assert all(result[name]['value'] is None and 'incompatible_unit_dimension' in
                   result[name]['unavailable_reason'] for name in COMPONENTS[6:])
        failures.append([left, right])
    checks = 0
    for bits in product((0, 1), repeat=8):
        data = deepcopy(original)
        data['model_kind'] = 'known_joint_normal_source_means'
        arm_scales = [Fraction(1, 1000) if bit else Fraction(1) for bit in bits[:4]]
        covariance_scales = [Fraction(1, 1000) if bit else Fraction(1) for bit in bits[4:]]
        for i, role in enumerate(PRIMITIVE_ORDER):
            data['arms'][role]['unit'] = 'umol/min/mg' if bits[i] else 'nmol/min/mg'
            data['arms'][role]['value'] = float(Fraction((12, 2, 5, 1)[i]) * arm_scales[i])
            data['covariance']['units'][i] = 'umol/min/mg' if bits[i + 4] else 'nmol/min/mg'
        diagonal = [Fraction(1), Fraction(1, 4), Fraction(9, 25), Fraction(9, 100)]
        data['covariance']['matrix'] = [[float(diagonal[i] * covariance_scales[i] ** 2)
            if i == j else 0 for j in range(4)] for i in range(4)]
        result = populate_controlled_response(data)['cells']
        expected = {COMPONENTS[6]: .006, COMPONENTS[7]: .0000017,
                    COMPONENTS[8]: math.sqrt(.0000017), COMPONENTS[9]: 1/.0000017,
                    COMPONENTS[10]: 36/3.4, COMPONENTS[11]: math.tanh((36/3.4)/2)}
        for name, number in expected.items():
            assert math.isclose(result[name]['value'], number, rel_tol=1e-14, abs_tol=0), (bits, name)
        checks += 1
    assert original_hash == hashlib.sha256(source.read_bytes()).hexdigest()
    receipt = {'passed': True, 'calculator_sha256': original_hash,
        'independent_arm_and_covariance_unit_representations_checked': checks,
        'incompatible_cross_pair_dimensions_checked': failures,
        'valid_local_pairs_preserved': True, 'effect_and_variance_and_profile_unit_invariant': True,
        'scope': 'Pure synthetic oracle, no source papers, model, Episode observations or scientific credit'}
    with (OUT / 'DIMENSION_AND_UNIT_RECEIPT_001.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
