"""Direction, magnitude and effect support of one converted result (A105 contract, SIGNATURES['direction_and_ratio']).
Pure: arguments in, a controlled record out.

converted  one converter output (convert_<type>): 'experiment_type', 'extraction' (with the effect and its variance),
           optional 'qualitative_effect' ({'statement', ...}), and 'direction_field_support' (see below).

The claim is not an argument: a claim names molecules only and carries no physical prediction or threshold (owner ruling
of 2026-11-21). Whether the result bears on the claim is bearing's question; the caller calls this only for a direct result.

Result: {'direction': DIRECTION, 'log_ratio': number >= 0 or None, 'effect_support': number 0..1 or None}.

QUANTITATIVE (the extraction carries an effect operand): a graded STRENGTH s in [0, 1] is computed from the measurement
itself on the experiment type's own scale (contract QUANTITATIVE_STRENGTH, QUANTITATIVE_STRENGTH_ANCHORS). Every converter
reports its effect as a binding or engagement constant, so the position is read on the log scale (a smaller constant is
stronger):
    p = (log10 e - log10 noise_end) / (log10 strong_end - log10 noise_end), clipped to [0, 1]
    s = (3 p^2 - 2 p^3) / (1 + r^2),   r = sqrt(v) / e the relative uncertainty (0 when no variance is stated)
The anchors are the two ends of a gray scale, never thresholds: s rises smoothly from 0 at the noise end to 1 at the strong
end. s > 0 supports, s == 0 is neutral (indistinguishable from the type's noise end); log_ratio = QUALITATIVE_LOG_RATIO[type]
* s. A quantitative result never opposes: opposition comes only from a stated non-detection (the qualitative path). The
criteria never gate the direction; they lower the WEIGHT only (literature_resolution.py). The effect must be a positive
point value in the anchors' unit and the variance (when stated) a positive number in that unit squared; anything else is a
converter error and raises ValueError. No unit is converted.

QUALITATIVE (no effect operand, converted['qualitative_effect']['statement']): interaction_detected -> supports,
interaction_not_detected -> opposes, both with log_ratio = QUALITATIVE_LOG_RATIO[experiment_type];
interaction_not_stated -> unknown with null. A missing result is never opposition.

Neither case present (no effect and no qualitative statement): unknown with null.

EFFECT SUPPORT (OWNER_DECISIONS 8 and 17): SUPPORT_FACTORS[converted['direction_field_support']], the quote-support factor of
the field that fixes the direction. Required whenever the direction is known (ValueError when absent; no default).
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    DIRECTION,
    NEUTRAL_LOG_RATIO,
    QUALITATIVE_LOG_RATIO,
    QUALITATIVE_STATEMENT,
    QUANTITATIVE_STRENGTH_ANCHORS,
    SUPPORT_CLASSES,
    SUPPORT_FACTORS,
)


def _unknown():
    return {'direction': 'unknown', 'log_ratio': None, 'effect_support': None}


def _effect_support(converted):
    if 'direction_field_support' not in converted:
        raise ValueError("converted result lacks 'direction_field_support' (the support class of the direction-fixing field), "
                         'which the converter must add; there is no default')
    support = converted['direction_field_support']
    if support not in SUPPORT_CLASSES:
        raise ValueError(f"converted['direction_field_support'] is outside SUPPORT_CLASSES: {support!r}")
    return SUPPORT_FACTORS[support]


def strength(experiment_type, effect, variance):
    """The graded strength s in [0, 1] of one measured effect on its type's scale (contract QUANTITATIVE_STRENGTH)."""
    anchors = QUANTITATIVE_STRENGTH_ANCHORS[experiment_type]
    if effect['status'] != 'point' or effect['unit'] != anchors['unit']:
        raise ValueError(f"{experiment_type} effect must be a point value in {anchors['unit']}: {effect['status']!r}, {effect['unit']!r}")
    value = float(effect['value'])
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{experiment_type} effect must be a positive constant: {value!r}')
    noise, strong = math.log10(anchors['noise_end']), math.log10(anchors['strong_end'])
    position = min(1.0, max(0.0, (math.log10(value) - noise) / (strong - noise)))
    relative = 0.0
    if variance is not None:
        if variance['status'] != 'point' or variance['unit'] != anchors['unit'] + '_squared':
            raise ValueError(f"{experiment_type} effect variance must be a point value in {anchors['unit']}_squared: {variance['status']!r}, {variance['unit']!r}")
        if not math.isfinite(variance['value']) or variance['value'] <= 0:
            raise ValueError(f"{experiment_type} effect variance must be a positive number: {variance['value']!r}")
        relative = math.sqrt(variance['value']) / value
    return (3.0 * position ** 2 - 2.0 * position ** 3) / (1.0 + relative ** 2)


def _quantitative(converted):
    quantities = converted['extraction']['quantities']
    graded = strength(converted['experiment_type'], quantities['effect'], quantities['effect_variance'])
    effect_support = _effect_support(converted)
    if graded == 0.0:
        return {'direction': 'neutral', 'log_ratio': NEUTRAL_LOG_RATIO, 'effect_support': effect_support}
    return {'direction': 'supports', 'log_ratio': QUALITATIVE_LOG_RATIO[converted['experiment_type']] * graded, 'effect_support': effect_support}


def _qualitative(converted):
    statement = converted['qualitative_effect']['statement']
    if statement not in QUALITATIVE_STATEMENT:
        raise ValueError(f'qualitative_effect.statement is outside QUALITATIVE_STATEMENT: {statement!r}')
    if statement == 'interaction_not_stated':
        return _unknown()
    return {'direction': 'supports' if statement == 'interaction_detected' else 'opposes',
            'log_ratio': QUALITATIVE_LOG_RATIO[converted['experiment_type']], 'effect_support': _effect_support(converted)}


def _check_output(result):
    direction, log_ratio, effect_support = result['direction'], result['log_ratio'], result['effect_support']
    if direction not in DIRECTION:
        raise ValueError(f'direction outside DIRECTION: {direction!r}')
    if direction == 'unknown':
        if log_ratio is not None or effect_support is not None:
            raise ValueError('log_ratio and effect_support must be null when direction is unknown')
        return result
    if log_ratio is None or log_ratio < 0 or not math.isfinite(log_ratio):
        raise ValueError(f'log_ratio must be a finite number >= 0 when direction is known: {log_ratio!r}')
    if effect_support is None or not 0.0 <= effect_support <= 1.0:
        raise ValueError(f'effect_support must be a number in 0..1 when direction is known: {effect_support!r}')
    if direction == 'neutral' and log_ratio != NEUTRAL_LOG_RATIO:
        raise ValueError('log_ratio must be exactly 0.0 for a neutral result')
    return result


def direction_and_ratio(converted):
    if not isinstance(converted, dict):
        raise ValueError('direction converted result must be a mapping')
    if converted['extraction']['quantities']['effect'] is not None:
        return _check_output(_quantitative(converted))
    if 'qualitative_effect' in converted:
        return _check_output(_qualitative(converted))
    return _check_output(_unknown())
