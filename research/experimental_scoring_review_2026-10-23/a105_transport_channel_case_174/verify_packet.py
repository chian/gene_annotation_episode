"""Reproduce source custody and research arithmetic; no production integration."""
from pathlib import Path
from fractions import Fraction
from decimal import Decimal, localcontext
import hashlib
import json
import math
import re

HERE = Path(__file__).resolve().parent


def main():
    raw = (HERE / 'source/elife-01084-v1.xml').read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    witnesses = json.loads((HERE / 'OPERAND_WITNESSES_001.json').read_text())
    by_name = {row['id']: row for row in witnesses}
    for row in witnesses:
        assert row['artifact_sha256'] == digest
        assert raw[row['start']:row['end']].decode('utf-8') == row['quote']
    table = json.loads((HERE / 'TABLE1_IDENTITY_WITNESS_001.json').read_text())
    assert raw[table['start']:table['end']].decode('utf-8') == table['quote']
    sections = json.loads((HERE / 'SOURCE_WITNESSES_001.json').read_text())['sections']
    for row in sections:
        assert raw[row['start_bytes']:row['end_bytes']].decode('utf-8') == row['quote']

    # Research-only, explicitly declared English thousands grouping. This is not
    # a production numeric/limit reader and does not interpret scientific roles.
    number = re.compile(r'[+−-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?')
    def token(name, index=0):
        text = number.findall(by_name[name]['quote'])[index]
        return Fraction(text.replace('−', '-').replace(',', ''))

    step, voltage, reversal = token('step_amplitude'), token('voltage'), token('salt_reversal')
    charge = Fraction('1.602176634e-19')  # Exact SI definition, not a source datum.
    occupancy = token('full_open_occupancy') / 100
    chloride, fluoride = token('liposome_limits'), token('liposome_limits', 1)
    delta = voltage - reversal
    derived = {
        'driving_potential_mV': delta,
        'nominal_conductance_pS': 1000 * step / abs(delta),
        'monovalent_charge_equivalent_rate_per_s': step * Fraction('1e-12') / charge,
        'naive_zero_reversal_conductance_pS': 1000 * step / abs(voltage),
        'naive_to_driving_corrected_ratio': abs(delta) / abs(voltage),
        'open_main_state_contribution_threshold_per_s': occupancy * step * Fraction('1e-12') / charge,
        'matched_liposome_limit_quotient': fluoride / chloride,
    }
    artifact = json.loads((HERE / 'ARITHMETIC_VERIFICATION_002.json').read_text())
    for name, value in derived.items():
        assert artifact['values'][name]['exact'] == str(value)
        assert math.isclose(artifact['values'][name]['float'], float(value), rel_tol=1e-14)
    with localcontext() as context:
        context.prec = 60
        direct = Decimal(1000) * Decimal(step.numerator) / Decimal(step.denominator) / (
            abs(Decimal(voltage.numerator) / Decimal(voltage.denominator)
                - Decimal(reversal.numerator) / Decimal(reversal.denominator)))
        exact = derived['nominal_conductance_pS']
        assert abs(direct - Decimal(exact.numerator) / Decimal(exact.denominator)) < Decimal('1e-55')
    assert derived['monovalent_charge_equivalent_rate_per_s'] * charge == step * Fraction('1e-12')
    record = json.loads((HERE / 'EXTRACTION_AND_COMPONENTS_002.json').read_text())
    assert record['recorded_inputs']['dominant_step']['value'] == float(step)
    assert record['recorded_inputs']['recording_voltage']['value'] == float(voltage)
    assert record['recorded_inputs']['salt_reversal']['value'] == float(reversal)
    assert record['production_implementation'] is False
    assert record['a105_adequacy_claim'] is False
    result = {
        'original_source_byte_witnesses_verified': len(witnesses) + len(sections) + 1,
        'source_token_arithmetic_outputs_verified': len(derived),
        'independent_decimal_and_dimension_checks': 2,
        'all_passed': True,
        'scope': 'Research source custody and arithmetic only. Scientific linkage, production readers, episode integration and A105 adequacy are not established by these checks.',
    }
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    main()
