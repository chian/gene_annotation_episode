"""Direction, magnitude and effect support of one converted result of the product_distribution class (DRAFT 2026-11-22, owner to
confirm). The class-scoped counterpart of literature_direction.direction_and_ratio, which reads binding constants only (a smaller
constant is stronger), and the sibling of literature_activity_direction. It follows the same paradigm; it differs in what the effect
is: the share of the CLAIMED product among the products of a reaction, or where the reaction's equilibrium lies.

QUANTITATIVE (the extraction carries an effect operand): the effect is ONE stated quantity, chosen by the converter with
select_product_distribution_effect (the best-determined stated one, in PRODUCT_DISTRIBUTION_EFFECT_ORDER). The quantity's kind is the
extraction's quantity_kind (product_fraction, product_fraction_ratio, equilibrium_fraction, equilibrium_ratio: the four kinds of
QUANTITY_KINDS['product_distribution']); each has its own ends in PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS. The effect is always read FOR the
claimed product: the fraction is the claimed product's share, a ratio has the claimed product in the numerator, an equilibrium ratio has it
on the product side. Its position on the quantity's scale is
    p = (log10 e - log10 noise_end) / (log10 strong_end - log10 noise_end), clipped to [0, 1]     (a LARGER share is stronger)
    s = (3 p^2 - 2 p^3) / (1 + r^2),   r = sqrt(v) / e the relative uncertainty (0 when no variance is stated)
s > 0 supports; s == 0 is neutral (no more than the quantity's noise end); log_ratio = QUALITATIVE_LOG_RATIO[type] * s.
A stated share supports by its graded strength. A quantitative result never opposes. Controls, response factors, the common denominator,
the equilibrium evidence and the other sheet criteria lower the WEIGHT only and never the direction (literature_resolution.row_weight).
The paper itself showing that the claimed product was not found among the products is the not-detected case: the qualitative path
(statement 'interaction_not_detected', read "product not detected", opposes), delegated to literature_direction. A share of exactly 0 is
not a quantitative result here: the converter states it as "product not detected" (a zero is never an effect operand).

The ends of the four quantities are the same two points seen four ways: for two species a ratio r corresponds to the fraction
f = r / (1 + r), and the ratio ends are the fraction ends carried through that function (section 5d of the contract). Between the
ends the fraction is read on log f and the ratio on log r, so the two curves differ (a share of 0.5 gives about 0.95, the equal ratio
1 about 0.76); this is an open question for the owner.

The effect must be a positive point value in the anchors' unit (a fraction also at most 1) and the variance (when stated) a positive
number in that unit squared; anything else is a converter error and raises ValueError. No unit is converted here.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_direction import (
    _check_output,
    _effect_support,
    direction_and_ratio,
)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    CLASS_OF_EXPERIMENT_TYPE,
    NEUTRAL_LOG_RATIO,
    PRODUCT_DISTRIBUTION_EFFECT_ORDER,
    PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS,
    QUALITATIVE_LOG_RATIO,
)

FRACTION_UNIT = 'fraction'


def select_product_distribution_effect(stated):
    """The effect among several stated quantities: the first of PRODUCT_DISTRIBUTION_EFFECT_ORDER whose operand is a point.
    stated: {quantity in PRODUCT_DISTRIBUTION_EFFECT_ORDER: operand or None}. Returns (quantity, operand). Raises when none is stated: a
    converter that has no stated quantity fills no effect and does not call this."""
    unknown = sorted(set(stated) - set(PRODUCT_DISTRIBUTION_EFFECT_ORDER))
    if unknown:
        raise ValueError(f'stated quantities outside PRODUCT_DISTRIBUTION_EFFECT_ORDER: {unknown}')
    for quantity in PRODUCT_DISTRIBUTION_EFFECT_ORDER:
        operand = stated.get(quantity)
        if operand is not None and operand['status'] == 'point':
            return quantity, operand
    raise ValueError('no stated quantity of PRODUCT_DISTRIBUTION_EFFECT_ORDER is a point value')


def product_distribution_strength(quantity, effect, variance):
    """The graded strength s in [0, 1] of one stated product-distribution quantity on its own scale (larger is stronger)."""
    if quantity not in PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS:
        raise ValueError(f'product_distribution quantity outside PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS: {quantity!r}')
    anchors = PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS[quantity]
    unit = anchors['unit']
    if effect['status'] != 'point' or effect['unit'] != unit:
        raise ValueError(f'{quantity} effect must be a point value in {unit}: {effect["status"]!r}, {effect["unit"]!r}')
    value = float(effect['value'])
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{quantity} effect must be a positive number: {value!r}')
    if unit == FRACTION_UNIT and value > 1.0:
        raise ValueError(f'{quantity} effect is a fraction and must be at most 1: {value!r}')
    noise, strong = math.log10(anchors['noise_end']), math.log10(anchors['strong_end'])
    position = min(1.0, max(0.0, (math.log10(value) - noise) / (strong - noise)))
    relative = 0.0
    if variance is not None:
        if variance['status'] != 'point' or variance['unit'] != unit + '_squared':
            raise ValueError(f'{quantity} effect variance must be a point value in {unit}_squared: {variance["status"]!r}, {variance["unit"]!r}')
        if not math.isfinite(variance['value']) or variance['value'] <= 0:
            raise ValueError(f'{quantity} effect variance must be a positive number: {variance["value"]!r}')
        relative = math.sqrt(variance['value']) / value
    return (3.0 * position ** 2 - 2.0 * position ** 3) / (1.0 + relative ** 2)


def product_distribution_direction_and_ratio(converted):
    """direction_and_ratio for a converted result of a product_distribution type. converted['extraction']['quantity_kind'] names the
    effect's kind (a key of PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS). The qualitative and unstated paths are literature_direction's."""
    if CLASS_OF_EXPERIMENT_TYPE[converted['experiment_type']] != 'product_distribution':
        raise ValueError(f"not a product_distribution type: {converted['experiment_type']!r}")
    quantities = converted['extraction']['quantities']
    if quantities['effect'] is None:
        return direction_and_ratio(converted)
    kind = converted['extraction']['quantity_kind']
    if kind not in PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS:
        raise ValueError(f'the effect kind {kind!r} has no product_distribution anchors; expected one of {sorted(PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS)}')
    graded = product_distribution_strength(kind, quantities['effect'], quantities['effect_variance'])
    effect_support = _effect_support(converted)
    if graded == 0.0:
        return _check_output({'direction': 'neutral', 'log_ratio': NEUTRAL_LOG_RATIO, 'effect_support': effect_support})
    return _check_output({'direction': 'supports', 'log_ratio': QUALITATIVE_LOG_RATIO[converted['experiment_type']] * graded,
                          'effect_support': effect_support})
