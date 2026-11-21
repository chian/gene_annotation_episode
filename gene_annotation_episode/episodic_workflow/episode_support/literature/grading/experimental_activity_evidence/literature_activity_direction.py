"""Direction, magnitude and effect support of one converted result of the activity_rate class (decided 2026-11-21, owner to
confirm). The class-scoped counterpart of literature_direction.direction_and_ratio, which reads binding constants only (a
smaller constant is stronger). It follows the same paradigm; it differs in what the effect is and which way is stronger.

QUANTITATIVE (the extraction carries an effect operand): the effect is ONE stated quantity, chosen by the converter with
select_activity_effect (the best-determined stated one, in ACTIVITY_EFFECT_ORDER). Its position on the quantity's own scale
(ACTIVITY_STRENGTH_ANCHORS; the physics of a rate is the same in every assay, so the anchors are per quantity, not per type) is
    p = (log10 e - log10 noise_end) / (log10 strong_end - log10 noise_end), clipped to [0, 1]     (a LARGER rate is stronger)
    s = (3 p^2 - 2 p^3) / (1 + r^2),   r = sqrt(v) / e the relative uncertainty (0 when no variance is stated)
s > 0 supports; s == 0 is neutral (no better than the quantity's noise end); log_ratio = QUALITATIVE_LOG_RATIO[type] * s.
A stated rate supports by its graded strength. A quantitative result never opposes. Controls, blanks, the initial-rate regime
and the other sheet criteria lower the WEIGHT only and never the direction (literature_resolution.row_weight).
The paper itself showing no activity above its own control or detection limit is the measured-zero / not-detected case: the
qualitative path ('interaction_not_detected', read "activity not detected", opposes), delegated to literature_direction.

SPECIFIC ACTIVITY (U/mg) has no ends of its own: its ends are the kcat ends at the enzyme's molar mass (specific_activity_ends),
the mass the record states, else REFERENCE_ENZYME_MASS_G_PER_MOL.

The effect must be a positive point value in the anchors' unit and the variance (when stated) a positive number in that unit
squared; anything else is a converter error and raises ValueError. No unit is converted here.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_direction import (
    _check_output,
    _effect_support,
    direction_and_ratio,
)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    ACTIVITY_EFFECT_ORDER,
    ACTIVITY_QUANTITY_OF_KIND,
    ACTIVITY_STRENGTH_ANCHORS,
    CLASS_OF_EXPERIMENT_TYPE,
    NEUTRAL_LOG_RATIO,
    QUALITATIVE_LOG_RATIO,
    REFERENCE_ENZYME_MASS_G_PER_MOL,
    SECONDS_PER_MINUTE,
    UMOL_PER_MMOL,
)

SPECIFIC_ACTIVITY_UNIT = 'U/mg'


def specific_activity_ends(enzyme_mass_g_per_mol):
    """The (noise_end, strong_end) of specific activity in U/mg: the kcat ends at the enzyme's molar mass.
    U/mg = kcat [s^-1] * 60 [s/min] * 1000 [umol/mmol] / M [g/mol]; with M given, or else the reference mass."""
    mass = REFERENCE_ENZYME_MASS_G_PER_MOL if enzyme_mass_g_per_mol is None else enzyme_mass_g_per_mol
    if not isinstance(mass, (int, float)) or isinstance(mass, bool) or not math.isfinite(mass) or mass <= 0:
        raise ValueError(f'the enzyme molar mass must be a positive number in g/mol: {mass!r}')
    turnover = ACTIVITY_STRENGTH_ANCHORS['turnover']
    factor = SECONDS_PER_MINUTE * UMOL_PER_MMOL / mass
    return turnover['noise_end'] * factor, turnover['strong_end'] * factor


def _ends(quantity, enzyme_mass_g_per_mol):
    if quantity == 'specific_activity':
        noise, strong = specific_activity_ends(enzyme_mass_g_per_mol)
        return SPECIFIC_ACTIVITY_UNIT, noise, strong
    anchors = ACTIVITY_STRENGTH_ANCHORS[quantity]
    return anchors['unit'], anchors['noise_end'], anchors['strong_end']


def select_activity_effect(stated):
    """The effect among several stated quantities: the first of ACTIVITY_EFFECT_ORDER whose operand is a point.
    stated: {quantity in ACTIVITY_EFFECT_ORDER: operand or None}. Returns (quantity, operand). Raises when none is stated: a
    converter that has no stated quantity fills no effect and does not call this."""
    unknown = sorted(set(stated) - set(ACTIVITY_EFFECT_ORDER))
    if unknown:
        raise ValueError(f'stated quantities outside ACTIVITY_EFFECT_ORDER: {unknown}')
    for quantity in ACTIVITY_EFFECT_ORDER:
        operand = stated.get(quantity)
        if operand is not None and operand['status'] == 'point':
            return quantity, operand
    raise ValueError('no stated quantity of ACTIVITY_EFFECT_ORDER is a point value')


def activity_strength(quantity, effect, variance, enzyme_mass_g_per_mol=None):
    """The graded strength s in [0, 1] of one stated activity quantity on its own scale (larger is stronger)."""
    if quantity not in ACTIVITY_EFFECT_ORDER:
        raise ValueError(f'activity quantity outside ACTIVITY_EFFECT_ORDER: {quantity!r}')
    unit, noise_end, strong_end = _ends(quantity, enzyme_mass_g_per_mol)
    if effect['status'] != 'point' or effect['unit'] != unit:
        raise ValueError(f'{quantity} effect must be a point value in {unit}: {effect["status"]!r}, {effect["unit"]!r}')
    value = float(effect['value'])
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{quantity} effect must be a positive number: {value!r}')
    noise, strong = math.log10(noise_end), math.log10(strong_end)
    position = min(1.0, max(0.0, (math.log10(value) - noise) / (strong - noise)))
    relative = 0.0
    if variance is not None:
        if variance['status'] != 'point' or variance['unit'] != unit + '_squared':
            raise ValueError(f'{quantity} effect variance must be a point value in {unit}_squared: {variance["status"]!r}, {variance["unit"]!r}')
        if not math.isfinite(variance['value']) or variance['value'] <= 0:
            raise ValueError(f'{quantity} effect variance must be a positive number: {variance["value"]!r}')
        relative = math.sqrt(variance['value']) / value
    return (3.0 * position ** 2 - 2.0 * position ** 3) / (1.0 + relative ** 2)


def activity_direction_and_ratio(converted, enzyme_mass_g_per_mol=None):
    """direction_and_ratio for a converted result of an activity_rate type. converted['extraction']['quantity_kind'] names the
    effect's kind (a key of ACTIVITY_QUANTITY_OF_KIND). The qualitative and unstated paths are literature_direction's."""
    if CLASS_OF_EXPERIMENT_TYPE[converted['experiment_type']] != 'activity_rate':
        raise ValueError(f"not an activity_rate type: {converted['experiment_type']!r}")
    quantities = converted['extraction']['quantities']
    if quantities['effect'] is None:
        return direction_and_ratio(converted)
    kind = converted['extraction']['quantity_kind']
    if kind not in ACTIVITY_QUANTITY_OF_KIND:
        raise ValueError(f'the effect kind {kind!r} has no activity anchors; expected one of {sorted(ACTIVITY_QUANTITY_OF_KIND)}')
    graded = activity_strength(ACTIVITY_QUANTITY_OF_KIND[kind], quantities['effect'], quantities['effect_variance'], enzyme_mass_g_per_mol)
    effect_support = _effect_support(converted)
    if graded == 0.0:
        return _check_output({'direction': 'neutral', 'log_ratio': NEUTRAL_LOG_RATIO, 'effect_support': effect_support})
    return _check_output({'direction': 'supports', 'log_ratio': QUALITATIVE_LOG_RATIO[converted['experiment_type']] * graded,
                          'effect_support': effect_support})
