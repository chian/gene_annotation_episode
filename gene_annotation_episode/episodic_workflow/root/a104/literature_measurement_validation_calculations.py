"""Numerical measurement-validation section; no acquisition or final credit.

A conditional plug-in loss is distinct from a supported estimated population
measurement variance. Neither supplies uncertainty of the mean, CV or loss.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
from math import isqrt

from .domain import REF, identity, obj, validate_schema
from .literature_calibration_recovery_calculations import _float, _q
from .literature_measurement_validation_inputs import (
    RELATIONSHIPS, RELATIONS, PAIR_REASONS, NUMBER_REASONS, _exact, _exact_schema, _nullable,
    _array, measurement_validation_extraction_schema, validate_measurement_validation_extraction,
)

VERSION = 'a105_measurement_validation_components_v1'
PRECISION_COMPONENTS = ('reported_cv', 'cv_fraction', 'relative_bias_squared',
    'relative_variance_plugin', 'relative_squared_deviation_plugin', 'relative_rms_percent')
ZPRIME_COMPONENTS = ('reported_zprime', 'control_band_ratio')
COMPONENTS = (*PRECISION_COMPONENTS, *ZPRIME_COMPONENTS, 'raw_control_zprime')
FORMULAS = {
    'reported_cv': 'source_reported_CV', 'cv_fraction': 'CV_percent/100_or_CV_fraction',
    'relative_bias_squared': 'received_relative_bias^2',
    'relative_variance_plugin': '(CV_fraction*received_recovery)^2',
    'relative_squared_deviation_plugin': 'received_relative_bias^2+(CV_fraction*received_recovery)^2',
    'relative_rms_percent': '100*sqrt(relative_squared_deviation_plugin)',
    'reported_zprime': 'source_reported_Zprime', 'control_band_ratio': '(1-reported_Zprime)/3',
    'raw_control_zprime': '1-3*(SDpos+SDneg)/abs(meanpos-meanneg)',
}
MEANINGS = {
    'reported_cv': 'source_relative_precision_statistic',
    'cv_fraction': 'same_source_relative_precision_in_fraction_units',
    'relative_bias_squared': 'squared_displayed_relative_calibration_bias_lower_is_smaller',
    'relative_variance_plugin': 'estimated_relative_variance_of_specified_measurement_population',
    'relative_squared_deviation_plugin': 'estimated_relative_squared_measurement_deviation_from_stated_nominal',
    'relative_rms_percent': 'same_squared_deviation_contribution_in_percent_RMS_display',
    'reported_zprime': 'reported_positive_negative_control_separation_statistic',
    'control_band_ratio': 'same_statistic_as_sum_of_control_SDs_over_absolute_mean_separation',
    'raw_control_zprime': 'unimplemented_raw_control_recomputation',
}
REASONS = (*PAIR_REASONS, *NUMBER_REASONS, 'numerical_model_range',
    'bounded_precision_plugin_unimplemented', 'negative_reported_CV_incompatible',
    'nonpositive_displayed_measured_mean', 'raw_control_inputs_and_route_unimplemented',
    'zprime_above_one_incompatible_with_formula', 'zprime_bound_crosses_formula_domain',
    'source_formula_different', 'source_formula_unknown', 'source_formula_conflicting',
    *(name + '_' + value for name in ('mean_precision_population', 'cv_denominator', 'recovery_context')
      for value in RELATIONSHIPS[name] if value not in ('same', 'displayed_measured_mean')))
QUALIFICATIONS = (
    'native_statistics_do_not_establish_scientific_role_assignments',
    'within_and_between_precision_are_alternative_bases_never_added',
    'plugin_is_population_measurement_variance_not_SE_of_mean_or_uncertainty_of_CV_or_loss',
    'plugin_from_displayed_summaries_is_not_unbiased_empirical_or_verified_predictive_MSE',
    'nominal_stock_uncertainty_not_quantified', 'validation_independence_is_not_inferred',
    'loss_and_RMS_are_same_contribution_not_independent_support',
    'recovery_bias_and_precision_components_reuse_original_measurements',
    'Zprime_and_band_ratio_are_same_statistic_not_independent_support',
    'no_raw_control_SD_borrowed_from_CV', 'no_residual_variance_from_R_squared',
    'standard_validation_does_not_establish_complete_assay_matrix_applicability',
    'reporter_response_does_not_identify_product_or_productive_coupling',
    'target_correspondence_and_final_annotation_credit_are_outside_this_operation',
)
ASSUMPTIONS = ('displayed_measured_amount_substitutes_for_population_mean',
    'CV_equals_population_SD_over_displayed_measured_mean',
    'recovery_and_precision_describe_same_standard_measurement_population',
    'stated_nominal_is_the_reference_value_not_established_error_free_truth',
    'displayed_summaries_supply_plugin_estimates_not_known_population_moments')


def measurement_validation_cell_schema(component=None):
    return obj({'value': {'type': ['number', 'null']}, 'exact_value': _nullable(_exact_schema()),
        'conditional_value': {'type': ['number', 'null']}, 'conditional_exact_value': _nullable(_exact_schema()),
        'status': {'enum': ['populated', 'conditional', 'unavailable']},
        'interpretation': {'enum': ['native_statistic', 'deterministic_reexpression', 'estimated_plugin', 'conditional_plugin', 'unimplemented']},
        'origin': {'enum': ['reported', 'derived', 'synthetic', 'proposed']},
        'input_origins': _array({'enum': ['reported', 'derived', 'synthetic']}, True),
        'relation': {'enum': list(RELATIONS)},
        'unit': {'enum': ['percent', 'fraction', 'fraction_squared']},
        'formula': {'const': FORMULAS[component]} if component else {'enum': list(FORMULAS.values())},
        'meaning': {'const': MEANINGS[component]} if component else {'enum': list(MEANINGS.values())},
        'input_measurement_keys': _array(REF, True), 'contribution_key': deepcopy(REF),
        'assumptions': _array({'enum': list(ASSUMPTIONS)}, True),
        'unavailable_reasons': _array({'enum': list(REASONS)}, True)})


def measurement_validation_sheet_schema():
    return obj({'version': {'const': VERSION}, 'axis': {'const': 'A105'},
        'section': {'const': 'measurement_validation'}, 'extraction': measurement_validation_extraction_schema(),
        'precision': _array(obj({'measurement_key': deepcopy(REF),
            'basis': {'enum': list(RELATIONSHIPS['basis'])},
            'cells': obj({name: measurement_validation_cell_schema(name) for name in PRECISION_COMPONENTS})})),
        'zprime': _array(obj({'measurement_key': deepcopy(REF),
            'cells': obj({name: measurement_validation_cell_schema(name) for name in ZPRIME_COMPONENTS})})),
        'raw_control_zprime': measurement_validation_cell_schema('raw_control_zprime'),
        'qualifications': {'const': list(QUALIFICATIONS)}, 'annotation_credit': {'type': 'null'}})


def _root_percent(value):
    n, d = isqrt(value.numerator), isqrt(value.denominator)
    if n*n == value.numerator and d*d == value.denominator:
        exact = 100 * Fraction(n, d)
        return _float(exact), _exact(exact)
    with localcontext() as ctx:
        ctx.prec = 65
        root = 100 * (Decimal(value.numerator) / Decimal(value.denominator)).sqrt()
        floating = _float(root)
    return floating, None


def populate_measurement_validation(extraction):
    """Populate distinct native/conditional/estimated cells without source IO.

    The arithmetic identity needs no normality or independence assumption.
    Population/denominator relationships determine whether displayed-summary
    substitution can be interpreted as an estimated measurement-error component.
    No replicate-count division, finite-sample correction or weighting is added.
    """
    validate_measurement_validation_extraction(extraction)
    data = deepcopy(extraction)
    pair_reasons = data['pair_unavailable_reasons']
    rrow = None if data['recovery'] is None else data['recovery']['row']
    brow = None if data['relative_bias'] is None else data['relative_bias']['row']
    r = None if pair_reasons else _q(rrow['exact_value'])
    b = None if pair_reasons else _q(brow['exact_value'])
    pair_keys = [] if rrow is None else list(rrow['input_measurement_keys'])
    pair_origins = [] if rrow is None else list(rrow['input_origins'])
    pair_contribution = identity('measurement_validation_bias', {'dependencies': pair_keys,
        'sheet_ref': None if rrow is None else rrow['sheet_ref']})

    def cell(name, value=None, *, conditional=None, reasons=(), unit='fraction',
             interpretation='deterministic_reexpression', origin='derived', origins=(),
             keys=(), contribution=None, assumptions=(), relation='point', root=False):
        exact = None if value is None else _exact(value)
        floating = None if value is None else _float(value)
        conditional_exact = None if conditional is None else _exact(conditional)
        conditional_float = None if conditional is None else _float(conditional)
        if root:
            if value is not None:
                floating, exact = _root_percent(value)
            if conditional is not None:
                conditional_float, conditional_exact = _root_percent(conditional)
        why = list(dict.fromkeys(reasons))
        if value is not None and floating is None or conditional is not None and conditional_float is None:
            why.append('numerical_model_range')
        status = 'populated' if floating is not None else 'conditional' if conditional_float is not None else 'unavailable'
        return {'value': floating, 'exact_value': exact, 'conditional_value': conditional_float,
            'conditional_exact_value': conditional_exact, 'status': status,
            'interpretation': interpretation, 'origin': origin, 'input_origins': list(dict.fromkeys(origins)),
            'relation': relation, 'unit': unit, 'formula': FORMULAS[name], 'meaning': MEANINGS[name],
            'input_measurement_keys': list(dict.fromkeys(keys)),
            'contribution_key': contribution or identity('measurement_validation_component', {'name': name, 'keys': list(keys)}),
            'assumptions': list(assumptions), 'unavailable_reasons': list(dict.fromkeys(why))}

    precision = []
    for item in data['precision']:
        number = item['number']; key = number['measurement_key']
        native = None if number['native_exact_value'] is None else _q(number['native_exact_value'])
        native_reason = [] if number['capability_reason'] is None else [number['capability_reason']]
        usable_native = native if not native_reason else None
        c = None if usable_native is None else usable_native / (100 if item['unit']['value'] == 'percent' else 1)
        origins = list(dict.fromkeys([*data['input_origins'], *pair_origins]))
        keys = list(dict.fromkeys([*pair_keys, key]))
        contribution = identity('measurement_validation_precision_model', {'pair': pair_contribution, 'precision': key})
        cells = {
            'reported_cv': cell('reported_cv', usable_native, reasons=native_reason, unit=item['unit']['value'],
                interpretation='native_statistic', origin=number['origin'], origins=data['input_origins'], keys=[key],
                contribution=key, relation=number['relation']),
            'cv_fraction': cell('cv_fraction', c, reasons=native_reason, origins=data['input_origins'], keys=[key],
                contribution=key, relation=number['relation']),
            'relative_bias_squared': cell('relative_bias_squared', None if b is None else b*b,
                reasons=pair_reasons, unit='fraction_squared', origins=pair_origins,
                keys=pair_keys, contribution=pair_contribution),
        }
        arithmetic_reasons = [*pair_reasons, *native_reason]
        if number['relation'] in ('lt', 'le', 'gt', 'ge'):
            arithmetic_reasons.append('bounded_precision_plugin_unimplemented')
        impossible_cv = (native is not None and (
            native < 0 and number['relation'] in ('point', 'lt', 'le')
            or native == 0 and number['relation'] == 'lt'))
        if impossible_cv:
            arithmetic_reasons.append('negative_reported_CV_incompatible')
            for name in ('reported_cv', 'cv_fraction'):
                cells[name]['unavailable_reasons'].append('negative_reported_CV_incompatible')
        if r is not None and r <= 0:
            arithmetic_reasons.append('nonpositive_displayed_measured_mean')
        interpretation_reasons = []
        for name, expected in (('mean_precision_population', 'same'),
                               ('cv_denominator', 'displayed_measured_mean'), ('recovery_context', 'same')):
            if item[name]['value'] != expected:
                interpretation_reasons.append(name + '_' + item[name]['value'])
        variance = None if arithmetic_reasons else (c*r)**2
        loss = None if variance is None else b*b + variance
        supported = not interpretation_reasons
        for name, proposed, unit, root in (
                ('relative_variance_plugin', variance, 'fraction_squared', False),
                ('relative_squared_deviation_plugin', loss, 'fraction_squared', False),
                ('relative_rms_percent', loss, 'percent', True)):
            cells[name] = cell(name, proposed if supported else None,
                conditional=None if supported else proposed,
                reasons=[*arithmetic_reasons, *interpretation_reasons], unit=unit,
                interpretation='estimated_plugin' if supported else 'conditional_plugin', origin='proposed',
                origins=origins, keys=keys, contribution=contribution, assumptions=ASSUMPTIONS, root=root)
        precision.append({'measurement_key': key, 'basis': item['basis']['value'], 'cells': cells})

    zprime = []
    inverse = {'point': 'point', 'lt': 'gt', 'le': 'ge', 'gt': 'lt', 'ge': 'le',
               'approximate': 'approximate', 'range': 'range', 'unresolved': 'unresolved'}
    for item in data['zprime']:
        number = item['number']; key = number['measurement_key']
        z = None if number['native_exact_value'] is None else _q(number['native_exact_value'])
        reasons = [] if number['capability_reason'] is None else [number['capability_reason']]
        native = cell('reported_zprime', None if reasons else z, reasons=reasons,
            origin=number['origin'], interpretation='native_statistic', origins=data['input_origins'],
            keys=[key], contribution=key, relation=number['relation'])
        formula = item['formula_relation']['value']
        band_reasons = [*reasons]
        if formula != 'conventional_zprime':
            band_reasons.append('source_formula_' + formula)
        if z is not None and (z > 1 or z == 1 and number['relation'] == 'gt'):
            reason = ('zprime_above_one_incompatible_with_formula' if number['relation'] in ('point', 'gt', 'ge')
                      else 'zprime_bound_crosses_formula_domain')
            band_reasons.append(reason)
            native['unavailable_reasons'].append(reason)
        ratio = None if band_reasons or z is None else (1-z)/3
        cells = {'reported_zprime': native,
            'control_band_ratio': cell('control_band_ratio', ratio, reasons=band_reasons,
                origins=data['input_origins'], keys=[key], contribution=key, relation=inverse[number['relation']])}
        zprime.append({'measurement_key': key, 'cells': cells})
    result = {'version': VERSION, 'axis': 'A105', 'section': 'measurement_validation', 'extraction': data,
        'precision': precision, 'zprime': zprime,
        'raw_control_zprime': cell('raw_control_zprime', reasons=['raw_control_inputs_and_route_unimplemented'],
            interpretation='unimplemented'), 'qualifications': list(QUALIFICATIONS), 'annotation_credit': None}
    validate_schema(result, measurement_validation_sheet_schema())
    return result


__all__ = ['VERSION', 'PRECISION_COMPONENTS', 'ZPRIME_COMPONENTS', 'COMPONENTS', 'FORMULAS', 'MEANINGS',
    'REASONS', 'QUALIFICATIONS', 'ASSUMPTIONS', 'measurement_validation_cell_schema',
    'measurement_validation_sheet_schema', 'populate_measurement_validation']
