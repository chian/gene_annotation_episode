"""Research packet arithmetic/custody check; not a production grader or test."""
from pathlib import Path
from fractions import Fraction
import hashlib
import json


root = Path(__file__).resolve().parent
ledger = json.loads((root / 'SOURCE_WITNESSES_003.json').read_text())
checked = 0
for witness in ledger['witnesses']:
    if 'start' not in witness:
        continue
    data = (root / witness['artifact']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == witness['artifact_sha256']
    assert data[witness['start']:witness['end']].decode() == witness['literal']
    checked += 1

expected = {
    'reported_equilibrium_fraction_sum': Fraction('0.397') + Fraction('0.603'),
    'reported_equilibrium_R5P_Ru5P_ratio': Fraction('60.3') / Fraction('39.7'),
    'printed_S5_integral_R5P_fraction': Fraction('1.52') / (Fraction('1.00') + Fraction('1.52')),
    'nominal_HFP_bulk_mass_ratio_approximate': Fraction(5, 7),
    'nominal_bulk_HFP_denominator_multiplier_approximate': Fraction(7, 5),
    'other_preparations_positive_fraction_finite_cohort': Fraction(4, 5),
    'RpiA_covered_residue_fraction': Fraction(101, 219),
    'HFP_covered_residue_fraction': Fraction(161, 203),
    'main_text_time_bound_division_only': Fraction(18 * 60, 10),
}
actual = json.loads((root / 'ARITHMETIC_001.json').read_text())['values']
for key, value in expected.items():
    row = actual[key]
    assert Fraction(int(row['numerator']), int(row['denominator'])) == value
    assert row['decimal'] == float(value)

parts = json.loads((root / 'DOCX_PARTS_001.json').read_text())['paragraphs']
paragraphs = {row['paragraph']: row for row in parts}
assert paragraphs[130]['text'] == 'WP_164930753.1'
assert paragraphs[112]['text'] == 'WP_010881296.1'
assert paragraphs[311]['text'].startswith('Figure S7:')
assert 'media/image7.png' in paragraphs[310]['images']
assert 'room temperature' in paragraphs[289]['text']
assert '18 hours' in paragraphs[299]['text']

result = {
    'status': 'passed',
    'checked_primary_numeric_spans': checked,
    'checked_exact_arithmetic_values': len(expected),
    'checked_DOCX_locator_relationships': 6,
    'scope': 'owned research artifact custody, arithmetic and corrected locators only',
    'not_established': ['raw spectral reanalysis', 'independent experiments',
                        'quantitative contaminant activity', 'production registration or delivery',
                        'a completed scoring sheet or annotation-credit wiring'],
}
(root / 'PACKET_CHECK_001.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
