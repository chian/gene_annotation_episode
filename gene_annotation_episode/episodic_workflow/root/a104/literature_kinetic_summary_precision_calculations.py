"""Estimated random precision of ONE source kinetic summary, not assay credit.

Sample SD yields an ESTIMATED mean variance. It is never known population
covariance or total uncertainty. Normality is needed only for the optional
proposed95% Student-t interval. Its level/df/quantile are calculation parameters,
not additional experiments. Source facts and explicit stipulations stay apart.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from math import isqrt

from scipy.stats import t as student_t

from .literature_kinetic_calculations import _finite, _sqrt
from .literature_kinetic_summary_precision_inputs import (
    _schema, _check, _fraction, _rational, _validate_input_relationships,
)

VERSION = 'a105_kinetic_summary_precision_sheet_v1'
EVALUATION_SCOPE = 'source_kinetic_summary_precision'
COMPONENTS = tuple(_schema('sheet')['properties']['source_cells']['properties'])
FORMULA_CODES = {name: 'summary_precision_' + name for name in COMPONENTS}
SQUARED_UNITS = {'uM': 'uM_squared', 'per_min': 'per_min_squared',
                 'uM^-1min^-1': 'uM_inverse_squared_min_inverse_squared'}
COUNT_COMPONENTS = ('source_summary_count', 'independent_preparation_count',
                    'statistical_estimator_count', 'mean_interval_df')
DIMENSIONLESS_COMPONENTS = ('relative_reported_sd', 'relative_mean_standard_error',
                            'mean_interval_confidence_level', 'mean_interval_t_multiplier')
_COUNT_MAPPING = ('one_estimate_per_preparation',
                  'reported_sd_summarizes_counted_preparation_estimates')
_UNKNOWN = {
    'one_estimate_per_preparation': 'statistical_estimator_count_unknown',
    'reported_sd_summarizes_counted_preparation_estimates': 'sd_preparation_estimator_ownership_unknown',
    'sample_sd_n_minus_one': 'sample_sd_convention_unknown',
    'iid_common_mean_finite_variance': 'iid_model_unknown',
    'equal_weight_arithmetic_mean': 'mean_identity_unknown',
    'normal_sampling_units': 'normality_unknown',
}


def summary_precision_inputs_schema():
    return _schema('inputs')


def summary_precision_sheet_schema():
    """Standalone sheet; local $defs must retain this resource scope."""
    return _schema('sheet')


def validate_kinetic_summary_precision_inputs(inputs):
    return _validate_input_relationships(inputs)


def _unique(values):
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _exact_count(reading):
    return reading['value'] if reading is not None and reading['status'] == 'exact' else None


def _row_reason(data):
    state = data['assessments']['row_footnote_applicability']
    return None if state == 'source_supported' else 'row_footnote_applicability_' + {
        'source_contradicted': 'contradicted', 'unknown': 'unknown', 'conflicting': 'conflicting'}[state]


def _assumptions(data, codes, scenario):
    for code in codes:
        state = data['assessments'][code]
        if state == 'source_supported':
            continue
        if state in ('source_contradicted', 'conflicting'):
            return ('scenario_assumption_conflicts_with_source' if scenario is not None else
                    'source_condition_contradicted' if state == 'source_contradicted' else
                    'source_condition_conflicting')
        if scenario is None or code not in scenario['stipulated_assumptions']:
            return _UNKNOWN[code]
    return None


def _physical_count(data):
    reason = _row_reason(data)
    if reason:
        return None, reason
    n = _exact_count(data['source_count'])
    if (n is None or data['source_count_meaning'] not in (
            'physical_preparation_count', 'both_same_count')
            or data['repetition_basis'] != 'biological_preparations'):
        return None, 'physical_preparation_count_unknown'
    return n, None


def _source_statistical_candidates(data):
    """Only already supported counts, not a physical count silently relabelled."""
    candidates, reason = [], None
    original = data['source_count']
    n = _exact_count(original)
    if data['source_count_meaning'] in (
            'statistical_estimator_count', 'technical_measurement_count', 'both_same_count'):
        if n is not None:
            candidates.append(n)
        elif original is not None:
            reason = 'source_count_not_exact'
    separate = data['source_statistical_count']
    if separate is not None:
        state = data['assessments']['statistical_count_matches_sd']
        if state == 'source_supported':
            selected = _exact_count(separate)
            if selected is not None:
                candidates.append(selected)
            else:
                reason = reason or 'source_count_not_exact'
        else:
            reason = reason or ('statistical_count_conflicting' if state in (
                'conflicting', 'source_contradicted') else 'statistical_count_sd_relationship_unknown')
    return candidates, reason


def _statistical_count(data, scenario):
    row_reason = _row_reason(data)
    if row_reason:
        return None, row_reason, []
    candidates, selection_reason = _source_statistical_candidates(data)
    if len(set(candidates)) > 1:
        return None, 'statistical_count_conflicting', []
    physical, physical_reason = _physical_count(data)
    mapped, mapping_reason = None, None
    mapping_codes = list(_COUNT_MAPPING)
    if physical is not None:
        mapping_reason = _assumptions(data, mapping_codes, scenario)
        if mapping_reason is None:
            mapped = physical
    if scenario is not None and scenario['count_rule'] == 'one_per_physical_preparation':
        if physical_reason:
            return None, physical_reason, mapping_codes
        if mapping_reason:
            return None, mapping_reason, mapping_codes
        if candidates and candidates[0] != mapped:
            return None, 'statistical_count_conflicting', mapping_codes
        return mapped, None, mapping_codes
    if mapped is not None:
        candidates.append(mapped)
    if len(set(candidates)) > 1:
        return None, 'statistical_count_conflicting', mapping_codes
    if selection_reason and not candidates:
        return None, selection_reason, []
    if candidates:
        return candidates[0], None, mapping_codes if mapped is not None and len(candidates) == 1 else []
    return None, 'statistical_estimator_count_unknown', []


def _parameter(data):
    reason = data['source_parameter_reason']
    if reason:
        return None, reason
    if data['source_parameter_status'] == 'censored':
        return None, 'censored_parameter'
    if data['source_parameter_status'] == 'conflicting':
        return None, 'conflicting_parameter'
    native = _fraction(data['parameter_native_exact'], 'parameter_native_exact')
    scale = _fraction(data['canonical_scale_exact'], 'canonical_scale_exact')
    if native is None:
        return None, 'source_measurement_unreported'
    if scale is None:
        return None, 'source_kinetic_unit_unreported'
    return native * scale, None


def _sd(data):
    if data['parameter_kind'] in ('unknown', 'conflicting'):
        return None, 'source_parameter_kind_' + data['parameter_kind']
    if data['uncertainty_statistic'] != 'sd':
        return None, 'reported_statistic_not_sd'
    if data['uncertainty_reason']:
        return None, data['uncertainty_reason']
    native = _fraction(data['sd_native_exact'], 'sd_native_exact')
    scale = _fraction(data['sd_scale_exact'], 'sd_scale_exact')
    if native is None:
        return None, 'reported_sd_unreported'
    if scale is None:
        return None, 'source_uncertainty_unit_unavailable'
    return native * scale, None


def _sqrt_exact(value):
    numerator, denominator = isqrt(value.numerator), isqrt(value.denominator)
    return (Fraction(numerator, denominator) if numerator * numerator == value.numerator
            and denominator * denominator == value.denominator else None)


def _populate_cells(data, scenario):
    cells = {}
    pu, su = data['canonical_unit'], data['sd_canonical_unit']
    variance_unit = SQUARED_UNITS.get(su)
    p, pr = _parameter(data)
    s, sr = _sd(data)
    pn, pnr = _physical_count(data)
    n, nr, count_conditions = _statistical_count(data, scenario)
    source_origin = data['source_origin']

    def put(name, value, unit, *, reason=None, exact=None, conditions=(),
            source=False, proposed=False, approximate=False, converted=False):
        conditions = _unique(conditions)
        stips = ([c for c in conditions if c in scenario['stipulated_assumptions']]
                 if scenario is not None else [])
        if value is not None:
            value, numerical_reason = _finite(value)
            if numerical_reason:
                reason = numerical_reason
            if name in COUNT_COMPONENTS and value is not None:
                # Count cells preserve actual integer identity, not a rounded float.
                value = int(exact if exact is not None else value)
        if reason is not None:
            value = None
        if name in COUNT_COMPONENTS:
            unit = 'count'
        elif name in DIMENSIONLESS_COMPONENTS:
            unit = 'dimensionless'
        cells[name] = {'value': value, 'unit': unit,
            'status': 'unavailable' if value is None else 'populated',
            'qualification': 'unavailable' if value is None else
                'conditional_on_stipulated_assumptions' if stips else
                'source_reported' if source else 'derived_source_supported_conditions',
            'formula_code': FORMULA_CODES[name],
            'origin': 'proposed' if proposed else 'derived' if converted and source_origin == 'reported'
                else source_origin if source else 'derived',
            'approximate': approximate,
            'source_exact_value': _rational(exact) if exact is not None and value is not None else None,
            'conditional_on': conditions, 'stipulated_assumptions': stips,
            'unavailable_reason': reason}

    put('reported_parameter', p, pu, reason=pr, exact=p, source=True,
        approximate=data['parameter_approximate'],
        converted=_fraction(data['canonical_scale_exact'], 'canonical_scale_exact') not in (None, 1))
    put('reported_sd', s, su, reason=sr, exact=s, source=True,
        converted=_fraction(data['sd_scale_exact'], 'sd_scale_exact') not in (None, 1))
    raw_count = _exact_count(data['source_count'])
    put('source_summary_count', raw_count, 'count', exact=Fraction(raw_count) if raw_count is not None else None,
        reason=None if raw_count is not None else 'source_summary_count_unreported' if data['source_count'] is None else 'source_count_not_exact', source=True)
    put('independent_preparation_count', pn, 'count', reason=pnr,
        exact=Fraction(pn) if pn is not None else None, source=True)
    put('statistical_estimator_count', n, 'count', reason=nr,
        exact=Fraction(n) if n is not None else None, conditions=count_conditions,
        source=not count_conditions)
    relative_reason = pr or sr or ('zero_parameter_for_relative_precision' if p == 0 else None)
    relative = s / abs(p) if relative_reason is None else None
    put('relative_reported_sd', relative, 'dimensionless', reason=relative_reason,
        exact=relative, approximate=data['parameter_approximate'])

    mean_conditions = _unique([*count_conditions, 'sample_sd_n_minus_one',
                               'iid_common_mean_finite_variance'])
    mean_reason = sr or nr or ('insufficient_estimator_count' if n is not None and n < 2 else None)
    mean_reason = mean_reason or _assumptions(data, mean_conditions, scenario)
    variance = s * s / n if mean_reason is None else None
    se, se_reason = (None, mean_reason) if variance is None else _sqrt(variance)
    put('mean_variance', variance, variance_unit, reason=mean_reason, exact=variance,
        conditions=mean_conditions)
    put('mean_standard_error', se, su, reason=se_reason,
        exact=_sqrt_exact(variance) if variance is not None else None, conditions=mean_conditions)
    relative_conditions = _unique([*mean_conditions, 'equal_weight_arithmetic_mean'])
    rse_reason = pr or mean_reason or ('zero_parameter_for_relative_precision' if p == 0 else None)
    rse_reason = rse_reason or _assumptions(data, relative_conditions, scenario)
    rse, rse_exact = None, None
    if rse_reason is None:
        # Calculate this ratio independently from the exact variance; dimensional
        # SE underflow must not erase a representable dimensionless result.
        rse, rse_reason = _sqrt(variance / (p * p))
        rse_exact = _sqrt_exact(variance / (p * p))
    put('relative_mean_standard_error', rse, 'dimensionless', reason=rse_reason,
        exact=rse_exact, conditions=relative_conditions, approximate=data['parameter_approximate'])

    interval_names = ('mean_interval_df', 'mean_interval_confidence_level',
                     'mean_interval_t_multiplier', 'mean_interval_halfwidth',
                     'mean_interval_lower', 'mean_interval_upper')
    if data['interval_request'] == 'none':
        for name in interval_names:
            put(name, None, su, reason='interval_not_requested')
        return cells
    put('mean_interval_confidence_level', .95, 'dimensionless', exact=Fraction(19, 20), proposed=True)
    df_conditions = _unique([*count_conditions, 'sample_sd_n_minus_one'])
    df_reason = ('reported_statistic_not_sd' if data['uncertainty_statistic'] != 'sd' else None)
    df_reason = df_reason or nr or ('insufficient_estimator_count' if n is not None and n < 2 else None)
    df_reason = df_reason or _assumptions(data, df_conditions, scenario)
    df = n - 1 if df_reason is None else None
    put('mean_interval_df', df, 'count', reason=df_reason,
        exact=Fraction(df) if df is not None else None, conditions=df_conditions)
    t_conditions = _unique([*df_conditions, 'iid_common_mean_finite_variance', 'normal_sampling_units'])
    tr = df_reason or _assumptions(data, t_conditions, scenario)
    quantile = None
    if tr is None:
        try:
            quantile, tr = _finite(student_t.ppf(.975, df))
        except (ArithmeticError, ValueError, TypeError):
            tr = 'numerical_model_range'
    put('mean_interval_t_multiplier', quantile, 'dimensionless', reason=tr, conditions=t_conditions)
    width_conditions = _unique([*mean_conditions, 'normal_sampling_units'])
    width_reason = mean_reason or tr or ('positive_sd_required_for_student_t' if s == 0 else None)
    halfwidth = None
    if width_reason is None:
        halfwidth, width_reason = _sqrt(variance * Fraction(quantile) ** 2)
    put('mean_interval_halfwidth', halfwidth, su, reason=width_reason, conditions=width_conditions)
    endpoint_conditions = _unique([*width_conditions, 'equal_weight_arithmetic_mean'])
    endpoint_reason = pr or width_reason or _assumptions(data, endpoint_conditions, scenario)
    for name, direction in (('mean_interval_lower', -1), ('mean_interval_upper', 1)):
        endpoint = p + direction * Fraction(halfwidth) if endpoint_reason is None else None
        put(name, endpoint, pu or su, reason=endpoint_reason, conditions=endpoint_conditions,
            approximate=data['parameter_approximate'])
    return cells


def populate_kinetic_summary_precision(inputs):
    """Populate source cells and an explicitly selected conditional scenario.

    A count, SD, variance, SE and interval describe one dependent contribution.
    Shared systematics remain unknown. No cross-construct contrast, error
    probability, calibrated confidence, annotation credit or continuation.
    """
    inputs = validate_kinetic_summary_precision_inputs(inputs)
    source_cells = _populate_cells(inputs, None)
    scenario = inputs['scenario']
    scenario_cells = _populate_cells(inputs, scenario) if scenario is not None else None
    locators = _unique([v for k, v in inputs['dependencies'].items()
                        if k != 'physical_measurement_id' and v is not None])
    result = {'version': VERSION, 'axis': 'A105', 'evaluation_scope': EVALUATION_SCOPE,
        'inputs': inputs, 'source_cells': source_cells, 'scenario_cells': scenario_cells,
        'contribution': {'kind': 'one_summary_precision_contribution',
            'dependency_sources': locators,
            'physical_measurement_id': inputs['dependencies']['physical_measurement_id'],
            'independence_inferred': False},
        'limits': _schema('sheet')['properties']['limits']['items']['enum'],
        'total_uncertainty': None, 'assay_error_probability': None, 'annotation_credit': None}
    _check(result, _schema('sheet'), 'sheet')
    return deepcopy(result)


__all__ = ['VERSION', 'EVALUATION_SCOPE', 'COMPONENTS', 'FORMULA_CODES',
    'summary_precision_inputs_schema', 'summary_precision_sheet_schema',
    'validate_kinetic_summary_precision_inputs', 'populate_kinetic_summary_precision']
