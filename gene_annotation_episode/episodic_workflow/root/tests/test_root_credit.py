"""The root credit on real numbers: ``prod_i (1 + K * v_i) ** w_i - 1`` over the nine axis credits, with ``K``
derived from epsilon 0.5 and every weight 1. The expected values are computed here in exact rational arithmetic
from the definition, never by the function under test. Axis credits are used as they are: none is bounded, clamped
or rescaled, also at 1e6 and far above."""
from fractions import Fraction

import pytest

from ..credit import AXIS_CREDIT_UNITS, AXIS_WEIGHTS, EPSILON, K, annotation_credit, credit

AXES = ('sequence_homology_evidence', 'structural_homology_evidence', 'gene_context_evidence',
        'evolutionary_history_evidence', 'experimental_activity_evidence', 'perturbation_evidence',
        'partner_presence_evidence', 'sample_context_evidence', 'biochemical_feasibility_evidence')

VECTORS = {
    'none': (0, 0, 0, 0, 0, 0, 0, 0, 0),
    'fractions': (0.25, 0.5, 0.125, 0.75, 0.0625, 0.375, 0.875, 0.625, 0.1875),
    'mixed_scales': (0.8, 3, 0, 12.5, 2, 0, 41, 0.3, 7),
    'above_one_everywhere': (2, 3, 5, 7, 11, 13, 17, 19, 23),
    'one_million_on_one_axis': (0.5, 1e6, 0.25, 0, 3, 0, 1, 0, 2),
    'one_million_on_every_axis': (1e6,) * 9,
    'millions_to_trillions': (1e6, 2e6, 5e7, 1e8, 3e9, 1e10, 4e11, 1e12, 7e12),
    'ten_to_the_thirty': (1e30,) * 9,
    'huge_beside_tiny': (1e15, 1e-9, 0, 1e-3, 1e9, 0, 2.5e-7, 0, 1e12),
}


def credits(values):
    return dict(zip(AXES, values))


def by_definition(values):
    """``prod_i (1 + k * v_i) ** w_i - 1`` in exact rational arithmetic, with ``k = (1 - epsilon) / epsilon``."""
    k = (1 - Fraction(EPSILON)) / Fraction(EPSILON)
    product = Fraction(1)
    for slot, value in zip(AXES, values):
        weight = Fraction(AXIS_WEIGHTS[slot])
        assert weight.denominator == 1
        product *= (1 + k * Fraction(value)) ** weight.numerator
    return product - 1


def offset_product_rescaled_and_calibrated(values):
    """The definition the formula is derived from: the offset product ``prod_i (epsilon + (1 - epsilon) * v_i)``
    divided by its value when no axis has credit, minus 1 (exact rational arithmetic)."""
    epsilon = Fraction(EPSILON)
    with_credit = empty = Fraction(1)
    for value in values:
        with_credit *= epsilon + (1 - epsilon) * Fraction(value)
        empty *= epsilon
    return with_credit / empty - 1


def test_k_is_derived_from_epsilon_one_half():
    assert EPSILON == 0.5
    assert K == (1 - EPSILON) / EPSILON == 1.0


def test_the_nine_axes_have_weight_one_and_a_credit_unit_each():
    assert tuple(AXIS_WEIGHTS) == AXES and tuple(AXIS_CREDIT_UNITS) == AXES
    assert set(AXIS_WEIGHTS.values()) == {1.0}
    assert all(unit > 0 for unit in AXIS_CREDIT_UNITS.values())


@pytest.mark.parametrize('name', VECTORS)
def test_the_credit_is_the_formula(name):
    values = VECTORS[name]
    expected = by_definition(values)
    assert annotation_credit(credits(values)) == pytest.approx(float(expected), rel=1e-12, abs=0.0)


@pytest.mark.parametrize('name', VECTORS)
def test_the_formula_is_the_rescaled_calibrated_offset_product_with_epsilon_one_half(name):
    """The derivation of ``K``: the formula with ``K = (1 - epsilon) / epsilon`` equals the offset product divided
    by its empty value, minus one, exactly, also where axis credits are far above 1."""
    values = VECTORS[name]
    assert by_definition(values) == offset_product_rescaled_and_calibrated(values)


@pytest.mark.parametrize('slot', AXES)
@pytest.mark.parametrize('value', (1e-9, 0.25, 0.3, 1.0, 7.5, 1e6, 3e12, 1e30, 1e300, -0.25))
def test_one_axis_alone_is_exactly_linear(slot, value):
    alone = {axis: 0.0 for axis in AXES}
    alone[slot] = value
    assert annotation_credit(alone) == K * value
    alone[slot] = 2 * value
    assert annotation_credit(alone) == 2 * (K * value)


@pytest.mark.parametrize('total', (0.9, 9.0, 4.5e3, 9e6, 9e12))
def test_an_equal_split_of_the_same_total_beats_concentration_and_more_axes_beat_fewer(total):
    concentrated = annotation_credit(credits((total,) + (0,) * 8))
    assert concentrated == K * total
    previous = concentrated
    for count in range(2, 10):
        share = total / count
        split = annotation_credit(credits((share,) * count + (0,) * (9 - count)))
        assert split > previous > 0
        assert split == pytest.approx(float((1 + Fraction(K) * Fraction(share)) ** count - 1), rel=1e-12)
        previous = split


def test_credit_spent_on_an_empty_axis_earns_more_than_the_same_credit_on_an_axis_that_has_some():
    """One axis at ``a``, the others empty; spend ``d``: on the same axis the gain is ``K * d``, on an empty one
    ``K * d + K**2 * a * d``."""
    a, d = 4.0, 0.5
    before = annotation_credit(credits((a,) + (0,) * 8))
    same = annotation_credit(credits((a + d,) + (0,) * 8)) - before
    other = annotation_credit(credits((a, d) + (0,) * 7)) - before
    assert same == K * d
    assert other == K * d + K ** 2 * a * d
    assert other > same


def test_an_axis_credit_is_never_bounded_clamped_or_rescaled():
    """The credit keeps growing with one axis's credit through 1, a million and beyond, and with nine axes at a
    million each it is of the order 1e54: nothing limits an axis credit or the annotation credit."""
    base = credits((2, 3, 0.5, 0, 1, 0, 4, 0, 1))
    seen = []
    for value in (0.5, 1.0, 1.5, 2.0, 1e3, 1e6, 1e9, 1e12):
        seen.append(annotation_credit({**base, 'gene_context_evidence': value}))
        assert seen[-1] == pytest.approx(float(by_definition(
            tuple({**base, 'gene_context_evidence': value}[axis] for axis in AXES))), rel=1e-12)
    assert seen == sorted(seen) and len(set(seen)) == len(seen)
    everywhere = annotation_credit(credits((1e6,) * 9))
    assert 1e54 < everywhere < 1.0001e54


def test_the_credit_member_reads_the_axis_credits_of_the_summary():
    values = VECTORS['millions_to_trillions']
    summary = {'axes': {slot: {'credit': value} for slot, value in zip(AXES, values)}}
    assert credit(summary, None) == annotation_credit(credits(values))
    assert credit(summary, None) == pytest.approx(float(by_definition(values)), rel=1e-12)
