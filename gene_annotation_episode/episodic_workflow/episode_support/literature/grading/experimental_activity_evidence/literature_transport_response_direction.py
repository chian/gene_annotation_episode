"""Direction, magnitude and effect support of one converted result of the transport_response class (DRAFT 2026-11-22, owner to
correct). The class-scoped counterpart of literature_direction.direction_and_ratio, which reads binding constants only. It follows
the same paradigm as literature_activity_direction; it differs in what the effect is and which way is stronger.

QUANTITATIVE (the extraction carries an effect operand): the effect is ONE stated quantity, chosen by the converter with
select_transport_effect (the best-determined stated one, in TRANSPORT_EFFECT_ORDER). Its position on the quantity's own scale
(TRANSPORT_STRENGTH_ANCHORS; the physics of a transport constant is the same in every assay, so the anchors are per quantity, not per
type) is
    p = (log10 e - log10 noise_end) / (log10 strong_end - log10 noise_end), clipped to [0, 1]
    s = (3 p^2 - 2 p^3) / (1 + r^2),   r = sqrt(v) / e the relative uncertainty (0 when no variance is stated)
For most quantities a LARGER value is stronger (noise_end < strong_end); for the transport Km a SMALLER value is stronger
(noise_end > strong_end); the same formula holds for both, as for the binding constants. s > 0 supports; s == 0 is neutral (no better
than the quantity's noise end); log_ratio = QUALITATIVE_LOG_RATIO[type] * s. A quantitative result never opposes. Controls, blanks,
the initial-rate regime, the driving force and the other sheet criteria lower the WEIGHT only and never the direction
(literature_resolution.row_weight). A transport no larger than the paper's own matched control (a fold at or under 1) is neutral
here; the paper STATING that the protein shows no transport above its control is the qualitative path ('interaction_not_detected',
read "transport not detected", opposes), delegated to literature_direction.

The record's quantity kind (QUANTITY_KINDS['transport_response']) names the effect's kind. The kind 'transport_rate' holds two
different quantities; the effect's unit tells them apart (TRANSPORT_RATE_QUANTITY_OF_UNIT): 's^-1' is a turnover per transporter
molecule or channel, 'nmol/min/mg' a rate per mass of the preparation. The effect must be a positive point value in the anchors' unit
and the variance (when stated) a positive number in that unit squared; anything else is a converter error and raises ValueError.
No unit is converted here.
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
    QUALITATIVE_LOG_RATIO,
    TRANSPORT_EFFECT_ORDER,
    TRANSPORT_QUANTITY_OF_KIND,
    TRANSPORT_RATE_QUANTITY_OF_UNIT,
    TRANSPORT_STRENGTH_ANCHORS,
)


def select_transport_effect(stated):
    """The effect among several stated quantities: the first of TRANSPORT_EFFECT_ORDER whose operand is a point.
    stated: {quantity in TRANSPORT_EFFECT_ORDER: operand or None}. Returns (quantity, operand). Raises when none is stated: a
    converter that has no stated quantity fills no effect and does not call this."""
    unknown = sorted(set(stated) - set(TRANSPORT_EFFECT_ORDER))
    if unknown:
        raise ValueError(f'stated quantities outside TRANSPORT_EFFECT_ORDER: {unknown}')
    for quantity in TRANSPORT_EFFECT_ORDER:
        operand = stated.get(quantity)
        if operand is not None and operand['status'] == 'point':
            return quantity, operand
    raise ValueError('no stated quantity of TRANSPORT_EFFECT_ORDER is a point value')


def transport_quantity(kind, unit):
    """The anchor quantity of an effect of the given record kind (and unit, for the kind 'transport_rate')."""
    if kind == 'transport_rate':
        if unit not in TRANSPORT_RATE_QUANTITY_OF_UNIT:
            raise ValueError(f'a transport_rate effect must be in one of {sorted(TRANSPORT_RATE_QUANTITY_OF_UNIT)}: {unit!r}')
        return TRANSPORT_RATE_QUANTITY_OF_UNIT[unit]
    if kind not in TRANSPORT_QUANTITY_OF_KIND:
        raise ValueError(f'the effect kind {kind!r} has no transport anchors; expected one of {sorted((*TRANSPORT_QUANTITY_OF_KIND, "transport_rate"))}')
    return TRANSPORT_QUANTITY_OF_KIND[kind]


def transport_strength(quantity, effect, variance):
    """The graded strength s in [0, 1] of one stated transport quantity on its own scale."""
    if quantity not in TRANSPORT_EFFECT_ORDER:
        raise ValueError(f'transport quantity outside TRANSPORT_EFFECT_ORDER: {quantity!r}')
    anchors = TRANSPORT_STRENGTH_ANCHORS[quantity]
    if effect['status'] != 'point' or effect['unit'] != anchors['unit']:
        raise ValueError(f"{quantity} effect must be a point value in {anchors['unit']}: {effect['status']!r}, {effect['unit']!r}")
    value = float(effect['value'])
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{quantity} effect must be a positive number: {value!r}')
    noise, strong = math.log10(anchors['noise_end']), math.log10(anchors['strong_end'])
    position = min(1.0, max(0.0, (math.log10(value) - noise) / (strong - noise)))
    relative = 0.0
    if variance is not None:
        if variance['status'] != 'point' or variance['unit'] != anchors['unit'] + '_squared':
            raise ValueError(f"{quantity} effect variance must be a point value in {anchors['unit']}_squared: {variance['status']!r}, {variance['unit']!r}")
        if not math.isfinite(variance['value']) or variance['value'] <= 0:
            raise ValueError(f"{quantity} effect variance must be a positive number: {variance['value']!r}")
        relative = math.sqrt(variance['value']) / value
    return (3.0 * position ** 2 - 2.0 * position ** 3) / (1.0 + relative ** 2)


def transport_direction_and_ratio(converted):
    """direction_and_ratio for a converted result of a transport_response type. converted['extraction']['quantity_kind'] names the
    effect's kind. The qualitative and unstated paths are literature_direction's."""
    if CLASS_OF_EXPERIMENT_TYPE[converted['experiment_type']] != 'transport_response':
        raise ValueError(f"not a transport_response type: {converted['experiment_type']!r}")
    quantities = converted['extraction']['quantities']
    if quantities['effect'] is None:
        return direction_and_ratio(converted)
    quantity = transport_quantity(converted['extraction']['quantity_kind'], quantities['effect']['unit'])
    graded = transport_strength(quantity, quantities['effect'], quantities['effect_variance'])
    effect_support = _effect_support(converted)
    if graded == 0.0:
        return _check_output({'direction': 'neutral', 'log_ratio': NEUTRAL_LOG_RATIO, 'effect_support': effect_support})
    return _check_output({'direction': 'supports', 'log_ratio': QUALITATIVE_LOG_RATIO[converted['experiment_type']] * graded,
                          'effect_support': effect_support})
