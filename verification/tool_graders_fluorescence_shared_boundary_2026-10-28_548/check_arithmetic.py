"""Synthetic boundary examples only; no production imports, parser or assay run."""
from fractions import Fraction
import json
from pathlib import Path
from statistics import mean, median


def main():
    values = [90, 100, 125, 150, 200, 250, 300, 350]
    ordinals = [i for i, value in enumerate(values) if 100 <= value <= 250]
    selected = [values[i] for i in ordinals]
    assert ordinals == [1, 2, 3, 4, 5]
    assert Fraction(len(selected), len(values)) == Fraction(5, 8)
    assert sum(selected) == 825 and mean(selected) == 165 and median(selected) == 150

    missing_values = [*values[:-1], None]
    finite = [i for i, value in enumerate(missing_values) if value is not None]
    assert finite == list(range(7))
    assert Fraction(len(selected), len(finite)) == Fraction(5, 7)

    # Synthetic, explicitly supplied gates. These are not default parameters.
    target = [(900, 900), (1000, 800), (1100, 500), (1300, 501), (1200, 800), (1500, 100)]
    control = [(900, 900), (1000, 800), (1100, 600), (1300, 501), (1200, 800), (1500, 100)]
    target_parent = [i for i, row in enumerate(target) if row[0] > 1000]
    control_parent = [i for i, row in enumerate(control) if row[0] > 1000]
    target_positive = [i for i in target_parent if target[i][1] > 500]
    control_positive = [i for i in control_parent if control[i][1] > 500]
    assert target_parent == control_parent == [2, 3, 4, 5]
    assert target_positive == [3, 4] and control_positive == [2, 3, 4]
    target_fraction = Fraction(len(target_positive), len(target_parent))
    control_fraction = Fraction(len(control_positive), len(control_parent))
    delta = target_fraction - control_fraction
    assert target_fraction == Fraction(1, 2) and control_fraction == Fraction(3, 4)
    assert delta == Fraction(-1, 4) and 100 * delta == -25
    assert max(0, 100 * delta) == 0
    assert Fraction(0, 4) == 0
    assert format(float(Fraction(1, 3) * 100), '.2f') == '33.33'

    result = {
        'verification_kind': 'synthetic_stdlib_arithmetic_only',
        'production_modules_imported': False,
        'native_operations_invoked': False,
        'parser_or_episode_verification': False,
        'complete_facs': {
            'values': values, 'declared_domain': 'synthetic_raw_arbitrary_instrument_units',
            'gate': {'lower': 100, 'lower_inclusive': True, 'upper': 250, 'upper_inclusive': True},
            'selected_ordinals': ordinals, 'selected_count': 5, 'parent_count': 8,
            'fraction_exact': '5/8', 'fraction': 0.625, 'percent': 62.5,
            'selected_sum': 825, 'selected_mean': 165, 'selected_median': 150,
        },
        'missing_facs': {
            'values': missing_values, 'missing_ordinals': [7], 'selected_ordinals': ordinals,
            'selected_count': 5, 'parent_count': 8, 'evaluable_count': 7,
            'whole_parent_fraction': None, 'reason': 'unknown_gate_membership',
            'explicit_evaluable_fraction_exact': '5/7',
            'explicit_evaluable_fraction': float(Fraction(5, 7)),
            'explicit_evaluable_percent': float(Fraction(500, 7)),
            'native_wrapper_percentage_token_if_run': '62.50%',
            'native_wrapper_was_run': False,
        },
        'cytokine_control': {
            'target_values_cd4_ifn': target, 'control_values_cd4_ifn': control,
            'parent_gate': {'lower': 1000, 'lower_inclusive': False},
            'marker_gate': {'lower': 500, 'lower_inclusive': False},
            'target_parent_ordinals': target_parent, 'target_positive_ordinals': target_positive,
            'control_parent_ordinals': control_parent, 'control_positive_ordinals': control_positive,
            'target_fraction_exact': '2/4', 'target_percent': 50,
            'control_fraction_exact': '3/4', 'control_percent': 75,
            'signed_difference_exact': '-1/4', 'signed_difference_percentage_points': -25,
            'native_legacy_clipped_if_run': 0, 'native_wrapper_was_run': False,
        },
        'missingness': [
            {'numerator': 0, 'denominator': 4, 'value': 0, 'reason': None},
            {'numerator': 0, 'denominator': 0, 'value': None, 'reason': 'empty_parent_population'},
            {'numerator': None, 'denominator': None, 'value': None, 'reason': 'source_unavailable'},
        ],
        'rounded_native_report_example': {
            'calculated_fraction_exact': '1/3', 'calculated_percent': float(Fraction(100, 3)),
            'native_token_if_formatted': '33.33%', 'native_precision_decimal_places': 2,
            'source_native_output': False,
        },
    }
    destination = Path(__file__).with_name('arithmetic-examples.json')
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    print('PASS: complete/missing populations, strict thresholds, signed control difference, zero distinction, rounding.')
    print('Only synthetic Python standard-library arithmetic was checked; no scientific operation, parser or episode was run.')


if __name__ == '__main__':
    main()
