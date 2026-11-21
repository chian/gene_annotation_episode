"""Direction, magnitude and effect support of one converted result for one candidate claim (A105 contract,
SIGNATURES['direction_and_ratio']). Pure: arguments in, a controlled record out.

converted  one converter output (convert_<type>): 'experiment_type', 'extraction' (grade_assay's input, with the effect
           and its variance), optional 'qualitative_effect' ({'statement', ...}), and the key this function needs
           beside them, 'direction_field_support' (see below).
claim      the candidate claim (contract CLAIM_FIELDS); here only the prediction pair and its unit are read.

Result: {'direction': DIRECTION, 'log_ratio': number >= 0 or None, 'effect_support': number 0..1 or None}.

QUANTITATIVE (the extraction carries an effect operand): the signed natural-log likelihood ratio of the claim against
its alternative is computed HERE, directly from the measured effect e, its variance v and the claim's prediction pair
(a under the claim, b under the alternative), under the plug-in normal model (the effect is N(prediction, v), v the
estimated variance): LR = log N(e | a, v) - log N(e | b, v) = (a - b) * (e - b - (a - b) / 2) / v. Positive ->
supports, negative -> opposes, exactly 0.0 -> neutral (a measured zero); log_ratio is its absolute value. It needs only a
point effect, a positive variance in the effect's own variance unit, and a prediction pair in the effect's own unit. It
does NOT depend on the grader's criteria: the owner's paradigm is that criteria statuses and degrees lower the WEIGHT
(literature_resolution.py), they never remove a direction. (The old sheet, grade_assay, gated this cell on every
required criterion being supported; that gate belongs to the old paradigm and is not used here.) When the effect is
bounded (a censored value), has no variance, a variance of 0 or less, a unit mismatch, or the claim gives no pair, the
direction is unknown and log_ratio and effect_support are null. Nothing is invented and no unit is converted.

QUALITATIVE (no effect operand, converted['qualitative_effect']['statement']): interaction_detected -> supports,
interaction_not_detected -> opposes, both with log_ratio = QUALITATIVE_LOG_RATIO[experiment_type];
interaction_not_stated -> unknown with null. A missing result is never opposition.

Neither case present (no effect and no qualitative statement): unknown with null.

EFFECT SUPPORT (OWNER_DECISION 8, EFFECT_SUPPORT_FROM): the quote-support factor (SUPPORT_FACTORS) of the field that fixes
the direction (the KD value for a quantitative result, the detected / not-detected statement for a qualitative one).
That support is NOT on the converted result today: the converters keep the per-field 'support' only in the grader's
native record and use it for the criteria. This function therefore reads converted['direction_field_support'], one value of
SUPPORT_CLASSES, which the converter must add. It is required whenever the direction is known; when it is absent the call
fails with a ValueError (no default of 1.0: the contract does not give one). It is not needed, and not read, when the
direction is unknown.

A bearing other than 'direct' must force direction unknown: the caller assembles the result and the contract validator
(validate_result) enforces it; this function does not read the bearing.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    CLAIM_FIELDS,
    DIRECTION,
    NEUTRAL_LOG_RATIO,
    QUALITATIVE_LOG_RATIO,
    QUALITATIVE_STATEMENT,
    REF_PATTERN,
    SUPPORT_CLASSES,
    SUPPORT_FACTORS,
)

# The unit spellings a variance may carry for an effect of unit u (the same spellings the old sheet accepted: u^2,
# (u)^2, u_squared). EXPERT_REVIEW: a unit outside these makes the direction unknown rather than guessing a conversion.
def _variance_unit_matches(variance_unit, effect_unit):
    return variance_unit in {effect_unit + '^2', '(' + effect_unit + ')^2', effect_unit + '_squared'}


def _unknown():
    return {'direction': 'unknown', 'log_ratio': None, 'effect_support': None}


def _check_claim_predictions(claim):
    """The prediction pair of the claim: None when the claim gives none, else (under_claim, under_alternative, unit)."""
    if not isinstance(claim, dict):
        raise ValueError('direction claim must be a mapping')
    extra = sorted(set(claim) - set(CLAIM_FIELDS))
    if extra:
        raise ValueError(f'direction claim has fields outside CLAIM_FIELDS: {extra}')
    under_claim = claim['prediction_under_claim']
    under_alternative = claim['prediction_under_alternative']
    unit = claim['prediction_unit']
    if under_claim is None and under_alternative is None:
        if unit is not None:
            raise ValueError('direction claim.prediction_unit is given without a prediction pair')
        return None
    if under_claim is None or under_alternative is None:
        raise ValueError('direction claim must give both predictions of the pair or neither')
    for name, value in (('prediction_under_claim', under_claim), ('prediction_under_alternative', under_alternative)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f'direction claim.{name} must be a finite number: {value!r}')
    if unit is None or not isinstance(unit, str) or not REF_PATTERN.match(unit):
        raise ValueError('direction claim.prediction_unit is required when a prediction is given and must be a reference')
    return under_claim, under_alternative, unit


def _effect_support(converted):
    if 'direction_field_support' not in converted:
        raise ValueError("converted result lacks 'direction_field_support' (the support class of the direction-fixing field), "
                         'which the converter must add; there is no default')
    support = converted['direction_field_support']
    if support not in SUPPORT_CLASSES:
        raise ValueError(f"converted['direction_field_support'] is outside SUPPORT_CLASSES: {support!r}")
    return SUPPORT_FACTORS[support]


def _log_ratio(effect, variance, under_claim, under_alternative):
    """Signed natural-log likelihood ratio of the claim against its alternative under the plug-in normal model."""
    difference = under_claim - under_alternative
    return difference * (effect - under_alternative - difference / 2.0) / variance


def _quantitative(converted, claim, pair):
    if pair is None:
        return _unknown()
    under_claim, under_alternative, unit = pair
    quantities = converted['extraction']['quantities']
    effect, variance = quantities['effect'], quantities['effect_variance']
    if effect['status'] != 'point' or effect['value'] is None or effect['unit'] != unit:
        return _unknown()
    if variance is None or variance['status'] != 'point' or variance['value'] is None or variance['value'] <= 0:
        return _unknown()
    if not _variance_unit_matches(variance['unit'], effect['unit']):
        return _unknown()
    value = _log_ratio(float(effect['value']), float(variance['value']), float(under_claim), float(under_alternative))
    if not math.isfinite(value):
        return _unknown()
    effect_support = _effect_support(converted)
    if value > 0:
        return {'direction': 'supports', 'log_ratio': float(value), 'effect_support': effect_support}
    if value < 0:
        return {'direction': 'opposes', 'log_ratio': float(-value), 'effect_support': effect_support}
    return {'direction': 'neutral', 'log_ratio': NEUTRAL_LOG_RATIO, 'effect_support': effect_support}


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


def direction_and_ratio(converted, claim):
    pair = _check_claim_predictions(claim)
    if not isinstance(converted, dict):
        raise ValueError('direction converted result must be a mapping')
    if converted['extraction']['quantities']['effect'] is not None:
        return _check_output(_quantitative(converted, claim, pair))
    if 'qualitative_effect' in converted:
        return _check_output(_qualitative(converted))
    return _check_output(_unknown())
