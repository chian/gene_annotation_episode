"""Direction, magnitude and effect support of one converted result of the reaction_coupling class (DRAFT 2026-11-22, owner to
correct). The class-scoped counterpart of literature_direction.direction_and_ratio, modelled on literature_activity_direction. It
follows the same paradigm; it differs in what the effect is. For this class the effect is the stoichiometric link between two
things measured in the same reaction (how much of the claimed product forms per unit of cofactor, co-substrate or substrate
consumed), and a LARGER link is stronger.

QUANTITATIVE (the extraction carries an effect operand): the effect is ONE stated quantity, chosen by the converter with
select_coupling_effect (the best-determined stated one, in COUPLING_EFFECT_ORDER). Its position on the quantity's own scale
(COUPLING_STRENGTH_ANCHORS; the physics of a coupling fraction is the same in every protocol, so the anchors are per quantity, not
per type) is
    p = (log10 e - log10 noise_end) / (log10 strong_end - log10 noise_end), clipped to [0, 1]     (a LARGER link is stronger)
    s = (3 p^2 - 2 p^3) / (1 + r^2),   r = sqrt(v) / e the relative uncertainty (0 when no variance is stated)
s > 0 supports; s == 0 is neutral (no better than the quantity's noise end); log_ratio = QUALITATIVE_LOG_RATIO[type] * s.
A stated link supports by its graded strength. A quantitative result never opposes. Controls, blanks, matched windows, the
stoichiometric coefficient, the reporter's capacity and the other sheet criteria lower the WEIGHT only and never the direction
(literature_resolution.row_weight). A value above the top of the physical range (a productive fraction above 1) is read at the
strong end here; that it is beyond the stoichiometric bound is the criteria's business (stoichiometry, matched_windows), not the
direction's.
The paper itself showing no product formed above its own control or detection limit is the measured-zero / not-detected case:
the qualitative path (statement 'interaction_not_detected', read "conversion not detected", opposes), delegated to
literature_direction. The balance_residual kind (an amount left unaccounted for) has no anchors of its own: an amount has no
common scale, so a converter of this class that has a closure states it as a productive_fraction (accounted for over consumed).

The effect must be a positive point value in the anchors' unit ('fraction') and the variance (when stated) a positive number in
that unit squared; anything else is a converter error and raises ValueError. No unit is converted here.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_direction import (
    _check_output,
    _effect_support,
    direction_and_ratio,
)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    CLASS_OF_EXPERIMENT_TYPE,
    COUPLING_EFFECT_ORDER,
    COUPLING_QUANTITY_OF_KIND,
    COUPLING_STRENGTH_ANCHORS,
    NEUTRAL_LOG_RATIO,
    QUALITATIVE_LOG_RATIO,
)


def select_coupling_effect(stated):
    """The effect among several stated quantities: the first of COUPLING_EFFECT_ORDER whose operand is a point.
    stated: {quantity in COUPLING_EFFECT_ORDER: operand or None}. Returns (quantity, operand). Raises when none is stated: a
    converter that has no stated quantity fills no effect and does not call this."""
    unknown = sorted(set(stated) - set(COUPLING_EFFECT_ORDER))
    if unknown:
        raise ValueError(f'stated quantities outside COUPLING_EFFECT_ORDER: {unknown}')
    for quantity in COUPLING_EFFECT_ORDER:
        operand = stated.get(quantity)
        if operand is not None and operand['status'] == 'point':
            return quantity, operand
    raise ValueError('no stated quantity of COUPLING_EFFECT_ORDER is a point value')


def coupling_strength(quantity, effect, variance):
    """The graded strength s in [0, 1] of one stated coupling quantity on its own scale (larger is stronger)."""
    if quantity not in COUPLING_EFFECT_ORDER:
        raise ValueError(f'coupling quantity outside COUPLING_EFFECT_ORDER: {quantity!r}')
    anchors = COUPLING_STRENGTH_ANCHORS[quantity]
    unit = anchors['unit']
    if effect['status'] != 'point' or effect['unit'] != unit:
        raise ValueError(f'{quantity} effect must be a point value in {unit}: {effect["status"]!r}, {effect["unit"]!r}')
    value = float(effect['value'])
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{quantity} effect must be a positive number: {value!r}')
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


def coupling_direction_and_ratio(converted):
    """direction_and_ratio for a converted result of a reaction_coupling type. converted['extraction']['quantity_kind'] names the
    effect's kind (a key of COUPLING_QUANTITY_OF_KIND). The qualitative and unstated paths are literature_direction's."""
    if CLASS_OF_EXPERIMENT_TYPE[converted['experiment_type']] != 'reaction_coupling':
        raise ValueError(f"not a reaction_coupling type: {converted['experiment_type']!r}")
    quantities = converted['extraction']['quantities']
    if quantities['effect'] is None:
        return direction_and_ratio(converted)
    kind = converted['extraction']['quantity_kind']
    if kind not in COUPLING_QUANTITY_OF_KIND:
        raise ValueError(f'the effect kind {kind!r} has no coupling anchors; expected one of {sorted(COUPLING_QUANTITY_OF_KIND)}')
    graded = coupling_strength(COUPLING_QUANTITY_OF_KIND[kind], quantities['effect'], quantities['effect_variance'])
    effect_support = _effect_support(converted)
    if graded == 0.0:
        return _check_output({'direction': 'neutral', 'log_ratio': NEUTRAL_LOG_RATIO, 'effect_support': effect_support})
    return _check_output({'direction': 'supports', 'log_ratio': QUALITATIVE_LOG_RATIO[converted['experiment_type']] * graded,
                          'effect_support': effect_support})
