"""A105 resolution: the weight rule and the credit rule, as pure functions (no Store, no I/O).

Two separate outputs, never mixed (contract docstring): the WEIGHT (criterion_resolution, row_weight) feeds the
per-annotation scores and counts a conflicting or unknown criterion as 0; the RESOLUTION (criterion_resolved,
row_resolution, credit_change) feeds the credit and counts a conflicting criterion as resolved. Credit never reads the
sign or the magnitude of a score; the score never reads credit.

All constants come from literature_row_contract (WEIGHT_*, RESOLVED_*, CREDIT_QUESTIONS_EXTRA, CRITERION_STATUS).
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bearing import identified_closeness
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    CREDIT_QUESTIONS_EXTRA,
    CRITERION_STATUS,
    RESOLVED_CONFLICTING,
    RESOLVED_NO_DEGREE,
    RESOLVED_UNKNOWN,
    ROW_WEIGHT_RULE,
    WEIGHT_CONFLICTING,
    WEIGHT_NO_DEGREE,
    WEIGHT_POOLED_DEGREE,
    WEIGHT_UNKNOWN_BY_TYPE,
    weight_unknown,
)


def _check_status_degree(status, degree):
    if status not in CRITERION_STATUS:
        raise ValueError(f'criterion status is outside CRITERION_STATUS: {status!r}')
    if status == 'not_applicable':
        raise ValueError('a not_applicable criterion is dropped by the caller and has no resolution')
    if degree is not None:
        if isinstance(degree, bool) or not isinstance(degree, (int, float)) or not math.isfinite(degree) or not 0.0 <= degree <= 1.0:
            raise ValueError(f'criterion degree must be a number in 0..1 or None: {degree!r}')


def criterion_resolution(status, degree, experiment_type, criterion):
    """OWNER_DECISION 4 (weight rule): r_c for the WEIGHT. supported = its degree, or WEIGHT_NO_DEGREE (1.0) when the
    degree is absent; conflicting = WEIGHT_CONFLICTING (0); unknown = this type's weight for this criterion
    (weight_unknown: WEIGHT_UNKNOWN_BY_CRITERION, else WEIGHT_UNKNOWN_BY_TYPE). not_applicable is refused."""
    _check_status_degree(status, degree)
    if status == 'supported':
        return float(WEIGHT_NO_DEGREE if degree is None else degree)
    if status == 'conflicting':
        return float(WEIGHT_CONFLICTING)
    return float(weight_unknown(experiment_type, criterion))


def criterion_resolved(status, degree):
    """OWNER_DECISION 5 (credit rule): r_c for the CREDIT. supported = its degree, or RESOLVED_NO_DEGREE (1.0) when
    the degree is absent; conflicting = RESOLVED_CONFLICTING (1.0, a definite answer lessens uncertainty); unknown =
    RESOLVED_UNKNOWN (0). not_applicable is refused: the caller drops it."""
    _check_status_degree(status, degree)
    if status == 'supported':
        return float(RESOLVED_NO_DEGREE if degree is None else degree)
    if status == 'conflicting':
        return float(RESOLVED_CONFLICTING)
    return float(RESOLVED_UNKNOWN)


def row_weight(results):
    """OWNER_DECISION 4 (weight rule): w in [0, 1] = sum r_c / N_applicable per result, then the MEAN over the results
    (4c, ROW_WEIGHT_RULE). `results` is a list of converted results (RESULT_FIELDS); each result's optional 'interpretations'
    ({criterion: {'status': CRITERION_STATUS, 'degree': 0..1 or null}}) gives its criteria; r_c is criterion_resolution.
    not_applicable criteria are dropped from the sum and from N_applicable. A result with no applicable criterion (all
    not_applicable, or no interpretations) has w = its type's unknown weight (WEIGHT_UNKNOWN_BY_TYPE, 4b): an unvetted
    measurement, and 1.0 is never invented; an empty list gives 0.0. Each result names its experiment_type."""
    if ROW_WEIGHT_RULE != 'mean_of_per_result_weights':
        raise ValueError('ROW_WEIGHT_RULE changed: row_weight must follow it')
    results = list(results)
    if not results:
        return 0.0
    weights = []
    for result in results:
        interpretations = result.get('interpretations') or {}
        applicable = [(name, item) for name, item in interpretations.items() if item['status'] != 'not_applicable']
        experiment_type = result['experiment_type']
        # 2026-11-21: the result's weight is scaled by how far its assayed protein is the target (identified_closeness, 0..1,
        # smooth in the sequence closeness; never a gate), so the score (which reads the result's weight) scales with it.
        standing = identified_closeness(result)
        if not applicable:
            weights.append(float(WEIGHT_UNKNOWN_BY_TYPE[experiment_type]) * standing)
            continue
        weights.append(standing * sum(criterion_resolution(item['status'], item.get('degree'), experiment_type, name)
                                      for name, item in applicable) / len(applicable))
    return sum(weights) / len(weights)


def _row_criterion_degree(row, name):
    # A pooled criterion keeps one degree per experiment and never combines them (ROW_FIELDS.interpretation_degrees).
    # OWNER_DECISION 4a (WEIGHT_POOLED_DEGREE): the weakest experiment's degree limits the resolution, matching the
    # pooled status rule (supported only if all experiments are supported).
    if WEIGHT_POOLED_DEGREE != 'minimum_over_experiments':
        raise ValueError('WEIGHT_POOLED_DEGREE changed: _row_criterion_degree must follow it')
    by_experiment = (row.get('interpretation_degrees') or {}).get(name)
    if not by_experiment:
        return None
    return min(by_experiment.values())


def row_resolution(row):
    """OWNER_DECISION 5 (credit rule): R in [0, 1] = mean over the open questions: each applicable row criterion
    (row['criteria'], criterion_resolved with its degree), plus the CREDIT_QUESTIONS_EXTRA questions: direction_known
    (1 if row_status is measured or measured_zero, else 0) and independence_known (1 if no dependence group rests on
    an unknown preparation, else 0). independence_known is the stored boolean ROW_FIELDS.independence_known of the row
    (a partial row from merge_row holds it too); a missing or non-boolean value is refused. A pooled supported criterion
    takes the minimum degree over its experiments (OWNER_DECISION 4a)."""
    if 'independence_known' not in row or not isinstance(row['independence_known'], bool):
        raise ValueError("row_resolution needs the boolean row field 'independence_known' (no dependence group rests on an unknown preparation)")
    if row['row_status'] not in ('measured', 'measured_zero', 'unknown'):
        raise ValueError(f"row_status is outside ROW_STATUS: {row['row_status']!r}")
    answers = {
        'direction_known': 1.0 if row['row_status'] in ('measured', 'measured_zero') else 0.0,
        'independence_known': 1.0 if row['independence_known'] else 0.0,
    }
    if set(answers) != set(CREDIT_QUESTIONS_EXTRA):
        raise ValueError('CREDIT_QUESTIONS_EXTRA changed: row_resolution must answer every extra question')
    values = list(answers.values())
    for name, status in (row.get('criteria') or {}).items():
        if status == 'not_applicable':
            continue
        values.append(criterion_resolved(status, _row_criterion_degree(row, name) if status == 'supported' else None))
    # 2026-11-21: every answer of the row is only as resolved as its best identified experiment is the target's protein
    # (row['identified_closeness'] = the greatest identified_closeness over the member results: adding a result never lowers
    # it, so credit is never lost to an added result). Smooth, never a gate: an unidentified subject stands at the bottom value.
    return row['identified_closeness'] * sum(values) / len(values)


def credit_change(before_row, after_row):
    """OWNER_DECISION 5 and 14 (credit): R(after) - R(before), never clamped. before_row may be None for a first fill
    (R_before = 0). Both rows are stored rows and are read through their 'resolution' field (R, computed by
    row_resolution when the row was merged). A row that did not change, or a repeat of a held fact, has the same R and so
    earns exactly 0.0 (CREDIT_FOR_REPEATED_FACT)."""
    def resolution_of(row):
        value = row['resolution']
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(f'row.resolution must be a number in 0..1: {value!r}')
        return float(value)
    if after_row is None:
        raise ValueError('credit_change needs the after row')
    before = 0.0 if before_row is None else resolution_of(before_row)
    return resolution_of(after_row) - before
