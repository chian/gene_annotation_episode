"""Finite source-threshold domains must survive a failed float projection."""
from fractions import Fraction
import pytest

from gene_annotation_episode.literature_ion_discrimination_render import _domain
from test_literature_ion_discrimination_components_194 import (
    SOURCE, common, source_quantity, calculate,
)


@pytest.mark.parametrize('preferred,alternative', [('1e308', '1e-308'), ('1e-308', '1e308')])
def test_actual_nominal_ratio_keeps_exact_finite_endpoint_in_display(preferred, alternative):
    text = f'Synthetic preferred rate >{preferred} per_s; alternative rate <{alternative} ions/s.'
    arguments = {**common(text), 'route': 'reported_threshold_pair', 'thresholds': {
        'preferred': source_quantity(text, preferred, 'per_s'),
        'alternative': source_quantity(text, alternative, 'ions/s'),
    }}
    _, sheet = calculate(arguments, [], {SOURCE: text.encode()})
    domain = sheet['cells']['nominal_threshold_ratio']['nominal_domain']
    expected = Fraction(preferred) / Fraction(alternative)
    assert domain['lower'] is None and not domain['lower_unbounded']
    assert domain['lower_exact'] == {'numerator': str(expected.numerator), 'denominator': str(expected.denominator)}
    shown = _domain(domain)
    assert str(expected) in shown and 'None' not in shown
    assert shown.startswith('(') and shown.endswith(', +∞)')
    assert sheet['cells']['nominal_threshold_ratio']['physical_domain'] is None


def test_infinity_is_open_while_unknown_finite_inclusivity_remains_unknown():
    domain = {'lower': 3, 'upper': None, 'lower_exact': {'numerator': '3', 'denominator': '1'},
              'upper_exact': None, 'lower_unbounded': False, 'upper_unbounded': True,
              'lower_inclusive': None, 'upper_inclusive': None}
    assert _domain(domain) == '?3, +∞)'
    assert _domain(None) == 'unavailable'
