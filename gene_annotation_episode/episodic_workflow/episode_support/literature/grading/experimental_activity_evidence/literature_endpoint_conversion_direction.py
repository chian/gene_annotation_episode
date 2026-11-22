"""Direction, magnitude and effect support of one converted result of the endpoint_conversion class (DRAFT, owner to correct). The
class-scoped counterpart of literature_direction.direction_and_ratio, modelled on literature_activity_direction. It follows the same
paradigm; it differs in what the effect is and which way is stronger.

The class asks how much of the substrate was converted, or how much product there was, at an end point, and how long completion took.
It is a single time point or a yield, not a rate (rates belong to activity_rate).

QUANTITATIVE (the extraction carries an effect operand): the effect is ONE stated quantity, chosen by the converter with
select_endpoint_effect (the best-determined stated one, in ENDPOINT_EFFECT_ORDER). Its position on the quantity's own scale
(ENDPOINT_STRENGTH_ANCHORS; anchors are per QUANTITY, not per experiment type) is
    p = (log10 e - log10 noise_end) / (log10 strong_end - log10 noise_end), clipped to [0, 1]
    s = (3 p^2 - 2 p^3) / (1 + r^2),   r = sqrt(v) / e the relative uncertainty (0 when no variance is stated)
For the conversion quantities and the amount a LARGER value is stronger; for the completion time a SMALLER one is stronger. The same
formula serves both: for the completion time the noise end is the larger number and the strong end the smaller, so p still runs from 0 to 1.
s > 0 supports; s == 0 is neutral (no better than the quantity's noise end); log_ratio = QUALITATIVE_LOG_RATIO[type] * s. A quantitative
result never opposes. Controls, blanks, the endpoint alignment, the denominator and the other sheet criteria lower the WEIGHT only and never
the direction (literature_resolution.row_weight). The paper itself stating that no conversion was seen above its own control or detection
limit is the not-detected case: the qualitative path ('interaction_not_detected', read "conversion not detected", opposes), delegated to
literature_direction, as are the result stated in words alone ("conversion detected": counted at STATED_ONLY_STRENGTH of the type's value)
and the unstated case.

The effect must be a positive point value in the anchors' unit and the variance (when stated) a positive number in that unit squared; a
fraction cannot exceed 1; anything else is a converter error and raises ValueError. No unit is converted here: the converter turns percent
into fraction, hours and seconds into minutes, and a stated amount into micromolar (with the stated volume) by exact factors.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_direction import (
    _check_output,
    _effect_support,
    direction_and_ratio,
)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    CLASS_OF_EXPERIMENT_TYPE,
    ENDPOINT_EFFECT_ORDER,
    ENDPOINT_QUANTITY_OF_KIND,
    ENDPOINT_STRENGTH_ANCHORS,
    NEUTRAL_LOG_RATIO,
    QUALITATIVE_LOG_RATIO,
)


def select_endpoint_effect(stated):
    """The effect among several stated quantities: the first of ENDPOINT_EFFECT_ORDER whose operand is a point.
    stated: {quantity in ENDPOINT_EFFECT_ORDER: operand or None}. Returns (quantity, operand). Raises when none is stated: a
    converter that has no stated quantity fills no effect and does not call this."""
    unknown = sorted(set(stated) - set(ENDPOINT_EFFECT_ORDER))
    if unknown:
        raise ValueError(f'stated quantities outside ENDPOINT_EFFECT_ORDER: {unknown}')
    for quantity in ENDPOINT_EFFECT_ORDER:
        operand = stated.get(quantity)
        if operand is not None and operand['status'] == 'point':
            return quantity, operand
    raise ValueError('no stated quantity of ENDPOINT_EFFECT_ORDER is a point value')


def endpoint_strength(quantity, effect, variance):
    """The graded strength s in [0, 1] of one stated endpoint quantity on its own scale."""
    if quantity not in ENDPOINT_EFFECT_ORDER:
        raise ValueError(f'endpoint quantity outside ENDPOINT_EFFECT_ORDER: {quantity!r}')
    anchors = ENDPOINT_STRENGTH_ANCHORS[quantity]
    unit = anchors['unit']
    if effect['status'] != 'point' or effect['unit'] != unit:
        raise ValueError(f'{quantity} effect must be a point value in {unit}: {effect["status"]!r}, {effect["unit"]!r}')
    value = float(effect['value'])
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{quantity} effect must be a positive number: {value!r}')
    if 'maximum' in anchors and value > anchors['maximum']:
        raise ValueError(f'{quantity} effect cannot exceed {anchors["maximum"]!r} {unit}: {value!r}')
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


def endpoint_direction_and_ratio(converted):
    """direction_and_ratio for a converted result of an endpoint_conversion type. converted['extraction']['quantity_kind'] names the
    effect's kind (a key of ENDPOINT_QUANTITY_OF_KIND). The qualitative and unstated paths are literature_direction's."""
    if CLASS_OF_EXPERIMENT_TYPE[converted['experiment_type']] != 'endpoint_conversion':
        raise ValueError(f"not an endpoint_conversion type: {converted['experiment_type']!r}")
    quantities = converted['extraction']['quantities']
    if quantities['effect'] is None:
        return direction_and_ratio(converted)
    kind = converted['extraction']['quantity_kind']
    if kind not in ENDPOINT_QUANTITY_OF_KIND:
        raise ValueError(f'the effect kind {kind!r} has no endpoint anchors; expected one of {sorted(ENDPOINT_QUANTITY_OF_KIND)}')
    graded = endpoint_strength(ENDPOINT_QUANTITY_OF_KIND[kind], quantities['effect'], quantities['effect_variance'])
    effect_support = _effect_support(converted)
    if graded == 0.0:
        return _check_output({'direction': 'neutral', 'log_ratio': NEUTRAL_LOG_RATIO, 'effect_support': effect_support})
    return _check_output({'direction': 'supports', 'log_ratio': QUALITATIVE_LOG_RATIO[converted['experiment_type']] * graded,
                          'effect_support': effect_support})
