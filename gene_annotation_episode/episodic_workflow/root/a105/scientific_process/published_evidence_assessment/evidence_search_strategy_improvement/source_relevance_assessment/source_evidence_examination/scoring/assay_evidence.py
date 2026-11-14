"""Assay component arithmetic and evidence comparison; original formulas preserved."""
from __future__ import annotations
from copy import deepcopy
import math
from scipy.special import log_ndtr
from scipy.stats import t as student_t
from gene_annotation_episode.episodic_workflow.root.a105.domain import obj, validate_schema
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.grading.literature_assay_grading import DIMENSIONS, FORMULAS, MEANINGS, _fail, _uncertainty_qualification, _unique, _validate_bound

def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except (OverflowError, ValueError):
        return False

def _variance_units(unit):
    aliases = {'per_min': 'per_min_squared', 'dimensionless': 'dimensionless_squared', 'fraction': 'fraction_squared', 'min': 'min_squared', 'uM/min': 'uM_squared/min_squared', 'uM': 'uM_squared', 'uM^-1min^-1': 'uM_inverse_squared_min_inverse_squared', 'uM_inverse_min_inverse': 'uM_inverse_squared_min_inverse_squared'}
    result = {unit + '^2', '(' + unit + ')^2', unit + '_squared'}
    if unit in aliases:
        result.add(aliases[unit])
    if unit == 'fraction':
        result.add('dimensionless_squared')
    return result

def _shift_bound(bound, shift):
    return {'relation': bound['relation'], 'lower': None if bound['lower'] is None else bound['lower'] - shift, 'upper': None if bound['upper'] is None else bound['upper'] - shift}

def _log_difference(larger, smaller):
    if smaller == -math.inf:
        return larger
    if not larger > smaller:
        return -math.inf
    return larger + math.log(-math.expm1(smaller - larger))

def _log_event_probability(bound, prediction, scale, kind, df):

    def cdf(value):
        z = (value - prediction) / scale
        return float(student_t.logcdf(z, df)) if kind == 'fixed_predictions_student_t' else float(log_ndtr(z))

    def survival(value):
        z = (value - prediction) / scale
        return float(student_t.logsf(z, df)) if kind == 'fixed_predictions_student_t' else float(log_ndtr(-z))
    lower, upper = (bound['lower'], bound['upper'])
    if lower is None:
        return cdf(upper)
    if upper is None:
        return survival(lower)
    if lower >= prediction:
        return _log_difference(survival(lower), survival(upper))
    return _log_difference(cdf(upper), cdf(lower))

def _evidence_comparison(effect, assertion, alternative, variance, model, df):
    kind, bound = (model['kind'], effect.get('bound'))
    scale = math.sqrt(variance)
    if bound is not None:
        value = _log_event_probability(bound, assertion, scale, kind, df) - _log_event_probability(bound, alternative, scale, kind, df)
        formula = 'log(P(observed_censoring_event|assertion)/P(observed_censoring_event|alternative))'
    elif kind == 'fixed_predictions_student_t':
        value = float(student_t.logpdf((effect['value'] - assertion) / scale, df)) - float(student_t.logpdf((effect['value'] - alternative) / scale, df))
        formula = 'log(t_df((effect-assertion)/sqrt(estimated_variance))/t_df((effect-alternative)/sqrt(estimated_variance)))'
    else:
        difference = assertion - alternative
        midpoint_residual = effect['value'] - alternative - difference / 2
        value = difference * midpoint_residual / variance
        formula = FORMULAS['source_log_evidence_ratio']
    return (value, formula)

def grade_experimental_measurement(extraction, *, input_schema, sheet_schema, required_criteria, quantity_unit_supported, version, axis, evaluation_scope):
    """Shared native diagnostics and fixed-prediction evidence calculation.

    Axis-specific contracts supply the scientific criteria and admissible
    quantity meanings. Numerical formulas, uncertainty and censoring semantics
    are identical for every caller; no axis is relabeled as another assay.
    """
    validate_schema(extraction, input_schema)
    data = deepcopy(extraction)
    quantities = data['quantities']
    quantities.setdefault('effect_degrees_of_freedom', None)
    interpretations = data['interpretations']
    assay_type, quantity_kind = (data['assay_type'], data['quantity_kind'])
    model = data['prediction_model']
    required, optional = required_criteria(assay_type, quantity_kind)
    explicit_applicability = {'product_identity'} if assay_type == 'endpoint_conversion' and quantity_kind == 'endpoint_amount' else set()
    for role, operand in quantities.items():
        if operand is None:
            continue
        if operand['value'] is not None and (not _finite(operand['value'])):
            _fail('finite_number_required')
        if operand['status'] == 'point' and (operand['value'] is None or operand['reason'] is not None):
            _fail('point_operand_inconsistent')
        if not operand['source_refs']:
            _fail('operand_source_required')
        if operand['status'] == 'point' and (not operand['measurement_keys']):
            _fail('operand_identity_required')
        _validate_bound(operand)
    for name, interpretation in interpretations.items():
        if interpretation['status'] in ('supported', 'not_applicable') and (not interpretation['support_refs']):
            _fail('interpretation_support_required')
        if name not in required:
            _fail('criterion_from_different_assay_type')
        if interpretation['status'] == 'not_applicable' and name not in optional:
            _fail('required_criterion_not_applicable')

    def criteria_reasons(names):
        reasons = []
        for name in names:
            if name in optional and name not in explicit_applicability:
                continue
            item = interpretations.get(name)
            if item is None:
                reasons.append(name + '_not_selected')
            elif item['status'] != 'supported' and (not (name in optional and item['status'] == 'not_applicable')):
                reasons.append(name + '_' + item['status'])
        return reasons

    def operand_reasons(roles, *, bounded_roles=()):
        reasons = []
        for role in roles:
            operand = quantities[role]
            if operand is None:
                reasons.append(role + '_not_selected')
            elif operand['status'] != 'point' and (not (role in bounded_roles and operand['status'] == 'bounded' and (operand.get('bound') is not None))):
                reasons.append(role + '_' + operand['status'])
                if operand['reason']:
                    reasons.append(operand['reason'])
        return _unique(reasons)

    def number(role):
        return quantities[role]['value']

    def unit(role, fallback='unknown'):
        return fallback if quantities[role] is None else quantities[role]['unit']

    def sources(roles, criteria=(), use_model=False):
        refs = [ref for role in roles if quantities[role] is not None for ref in quantities[role]['source_refs']]
        refs += [ref for name in criteria for ref in interpretations.get(name, {}).get('support_refs', ())]
        if use_model and model is not None:
            refs += model['support_refs']
        return _unique(refs)

    def cell(name, value, roles, output_unit, *, reasons=(), criteria=(), conditions=(), conditional=False, use_model=False, bounded_roles=(), bound=None, formula=None):
        failures = _unique([*operand_reasons(roles, bounded_roles=bounded_roles), *reasons])
        if value is not None and (not _finite(value)):
            failures.append('numerical_model_range')
        if bound is not None and any((v is not None and (not _finite(v)) for v in (bound['lower'], bound['upper']))):
            failures.append('numerical_model_range')
        if failures:
            value = None
            bound = None
        if value is None and bound is None and (not failures):
            failures.append('calculation_unavailable')
        result = {'component': name, 'dimension': DIMENSIONS[name], 'value': value, 'unit': output_unit, 'status': 'bounded' if bound is not None else 'unavailable' if value is None else 'conditional' if conditional else 'populated', 'reasons': _unique(failures), 'formula': FORMULAS[name] if formula is None else formula, 'meaning': MEANINGS[name], 'measurement_keys': _unique([key for role in roles if quantities[role] is not None for key in quantities[role]['measurement_keys']]), 'source_refs': sources(roles, criteria, use_model), 'input_origins': _unique([quantities[role]['origin'] for role in roles if quantities[role] is not None]), 'conditions': _unique([*conditions, *[qualification for role in roles if quantities[role] is not None for qualification in quantities[role].get('qualifications', ())]])}
        if bound is not None:
            result['bound'] = deepcopy(bound)
        return result
    cells = {}
    effect_bound = (quantities['effect'] or {}).get('bound')
    effect_reason = operand_reasons(('effect',), bounded_roles=('effect',))
    cells['measured_effect'] = cell('measured_effect', None if effect_reason else number('effect'), ('effect',), unit('effect'), conditions=('native_corrections_are_not_applied_again',), bounded_roles=('effect',), bound=effect_bound)
    variance_roles = ('effect', 'effect_variance')
    variance_criteria = ('variance_correspondence',)
    variance_reasons = [*operand_reasons(variance_roles, bounded_roles=('effect',)), *criteria_reasons(variance_criteria)]
    variance = None
    if not operand_reasons(variance_roles, bounded_roles=('effect',)):
        if unit('effect_variance') not in _variance_units(unit('effect')):
            variance_reasons.append('variance_unit_mismatch')
        if number('effect_variance') < 0:
            variance_reasons.append('negative_variance')
        if not variance_reasons:
            variance = number('effect_variance')
    variance_conditions = ('variance_of_the_selected_estimate_only', 'unknown_systematic_error_is_not_zero')
    cells['effect_variance'] = cell('effect_variance', variance, variance_roles, unit('effect_variance'), reasons=variance_reasons, criteria=variance_criteria, conditions=variance_conditions, bounded_roles=('effect',))
    precision_reasons = list(variance_reasons)
    if variance == 0:
        precision_reasons.append('positive_variance_required')
    precision = None if variance is None or variance <= 0 else 1 / variance
    cells['effect_precision'] = cell('effect_precision', precision, variance_roles, '1/(' + unit('effect_variance') + ')', reasons=precision_reasons, criteria=variance_criteria, conditions=(*variance_conditions, 'precision_is_scale_dependent_not_a_quality_probability'), bounded_roles=('effect',), conditional=model is None or model['variance_interpretation'] != 'known' or any((_uncertainty_qualification(q) for role in variance_roles if quantities[role] is not None for q in quantities[role].get('qualifications', ()))))
    calibration_criteria = ('calibration_applicability',)
    calibration_reasons = [*operand_reasons(('recovery',)), *criteria_reasons(calibration_criteria)]
    recovery_deviation = None
    if not operand_reasons(('recovery',)):
        if unit('recovery') not in ('dimensionless', 'fraction'):
            calibration_reasons.append('recovery_unit_mismatch')
        elif number('recovery') <= 0:
            calibration_reasons.append('positive_recovery_required')
        else:
            recovery_deviation = number('recovery') - 1
    cells['recovery_deviation'] = cell('recovery_deviation', recovery_deviation, ('recovery',), 'dimensionless', reasons=calibration_reasons, criteria=calibration_criteria, conditions=('diagnostic_not_a_validity_multiplier', 'do_not_reapply_calibration'))
    attribution_roles = ('attributed_signal', 'total_signal')
    attribution_criteria = ('measurement_identity', 'attribution_supported')
    attribution_reasons = [*operand_reasons(attribution_roles), *criteria_reasons(attribution_criteria)]
    fraction = None
    if not operand_reasons(attribution_roles):
        if unit('attributed_signal') != unit('total_signal'):
            attribution_reasons.append('attribution_unit_mismatch')
        elif number('total_signal') <= 0:
            attribution_reasons.append('positive_total_signal_required')
        else:
            fraction = number('attributed_signal') / number('total_signal')
    attribution_conditions = ['same_endpoint_denominator_and_source_attribution_model', 'activity_fraction_is_not_mass_purity', 'do_not_reapply_attribution']
    if fraction is not None and (not 0 <= fraction <= 1):
        attribution_conditions.append('outside_physical_fraction_range_not_clamped')
    cells['attributed_fraction'] = cell('attributed_fraction', fraction, attribution_roles, 'fraction', reasons=attribution_reasons, criteria=attribution_criteria, conditions=attribution_conditions)
    comparison_roles = ('condition_test', 'condition_reference')
    comparison_criteria = ('measurement_identity', 'condition_scope')
    comparison_reasons = [*operand_reasons(comparison_roles), *criteria_reasons(comparison_criteria)]
    response = None
    if not operand_reasons(comparison_roles):
        if unit('condition_test') != unit('condition_reference'):
            comparison_reasons.append('condition_response_unit_mismatch')
        elif number('condition_reference') <= 0 or number('condition_test') < 0:
            comparison_reasons.append('physical_condition_response_required')
        else:
            response = number('condition_test') / number('condition_reference')
    cells['condition_response'] = cell('condition_response', response, comparison_roles, 'dimensionless', reasons=comparison_reasons, criteria=comparison_criteria, conditions=('nuisance_conditions_outside_the_intended_change', 'do_not_reapply_condition_correction'))
    prediction_criteria = tuple((c for c in required if c not in ('variance_correspondence', 'sampling_basis')))
    for role, name in (('assertion_prediction', 'assertion_prediction_error'), ('alternative_prediction', 'alternative_prediction_error')):
        roles = ('effect', role)
        reasons = [*operand_reasons(roles, bounded_roles=('effect',)), *criteria_reasons(prediction_criteria)]
        difference, difference_bound = (None, None)
        if not operand_reasons(roles, bounded_roles=('effect',)):
            if not quantity_unit_supported(quantity_kind, unit('effect')):
                reasons.append('quantity_kind_unit_unsupported')
            if unit('effect') != unit(role):
                reasons.append('prediction_unit_mismatch')
            elif effect_bound is not None:
                difference_bound = _shift_bound(effect_bound, number(role))
            else:
                difference = number('effect') - number(role)
            if set(quantities['effect']['measurement_keys']) & set(quantities[role]['measurement_keys']):
                reasons.append('prediction_reuses_observed_measurement')
        cells[name] = cell(name, difference, roles, unit('effect'), reasons=reasons, criteria=prediction_criteria, bounded_roles=('effect',), bound=difference_bound, conditions=('same_selected_reference_assertion_and_experimental_conditions', 'fixed_prediction_not_inferred_from_this_observation'), conditional=any((quantities[r] is not None and quantities[r]['origin'] == 'proposed' for r in roles)))
    evidence_roles = ('effect', 'effect_variance', 'assertion_prediction', 'alternative_prediction')
    if model is not None and model['kind'] == 'fixed_predictions_student_t':
        evidence_roles += ('effect_degrees_of_freedom',)
    evidence_reasons = [*operand_reasons(evidence_roles, bounded_roles=('effect',)), *criteria_reasons(required), *precision_reasons, *cells['assertion_prediction_error']['reasons'], *cells['alternative_prediction_error']['reasons']]
    estimated_model = model is not None and model['kind'] in ('fixed_predictions_estimated_normal', 'fixed_predictions_student_t')
    for role in evidence_roles:
        operand = quantities[role]
        if operand is None:
            continue
        for qualification in operand.get('qualifications', ()):
            if qualification == 'physical_measurement_identity_unknown':
                continue
            if _uncertainty_qualification(qualification):
                lowered = qualification.lower()
                if estimated_model and 'estimated' in lowered and (not any((word in lowered for word in ('unknown', 'unresolved', 'conflicting')))):
                    continue
                evidence_reasons.append(role + '_source_qualification:' + qualification)
    if model is None:
        evidence_reasons.append('prediction_model_not_selected')
    else:
        if not model['support_refs']:
            evidence_reasons.append('prediction_model_support_missing')
        if model['kind'] == 'fixed_predictions_known_normal' and model['variance_interpretation'] != 'known':
            evidence_reasons.append('normal_model_requires_known_variance')
        if estimated_model and model['variance_interpretation'] != 'estimated':
            evidence_reasons.append('estimated_model_requires_estimated_variance')
    df = None
    if model is not None and model['kind'] == 'fixed_predictions_student_t':
        role = 'effect_degrees_of_freedom'
        if not operand_reasons((role,)):
            df = number(role)
            if unit(role) not in ('count', 'dimensionless'):
                evidence_reasons.append('degrees_of_freedom_unit_mismatch')
            if df <= 0:
                evidence_reasons.append('positive_degrees_of_freedom_required')
    score, formula = (None, FORMULAS['source_log_evidence_ratio'])
    if not evidence_reasons:
        try:
            score, formula = _evidence_comparison(quantities['effect'], number('assertion_prediction'), number('alternative_prediction'), variance, model, df)
        except (ArithmeticError, ValueError):
            evidence_reasons.append('numerical_model_range')
    model_conditions = [] if model is None else [model['kind'] + '_model']
    if model is not None and model['kind'] == 'fixed_predictions_estimated_normal':
        model_conditions.extend(('estimated_variance_plugin_normal_approximation', 'variance_estimation_uncertainty_not_integrated'))
    elif model is not None and model['kind'] == 'fixed_predictions_student_t':
        model_conditions.extend(('explicit_student_t_residual_model', 'estimated_mean_variance_used_as_squared_t_scale', 't_sampling_model_is_not_inferred_from_reported_sd'))
    if effect_bound is not None:
        model_conditions.append('probability_of_reported_censoring_event_not_density_at_limit_or_zero')
    cells['source_log_evidence_ratio'] = cell('source_log_evidence_ratio', score, evidence_roles, 'dimensionless', reasons=evidence_reasons, criteria=required, use_model=True, conditional=True, bounded_roles=('effect',), formula=formula, conditions=(*model_conditions, 'conditional_log_likelihood_not_annotation_probability', 'one_selected_observation_not_independent_of_its_derived_diagnostics', 'no_target_correspondence_or_W05_aggregation'))
    sheet = {'version': version, 'axis': axis, 'evaluation_scope': evaluation_scope, 'assay_type': assay_type, 'assertion_ref': data['assertion_ref'], 'quantity_kind': quantity_kind, 'cells': cells, 'interpretations': deepcopy(interpretations), 'prediction_model': deepcopy(model), 'annotation_credit': None}
    validate_schema(sheet, sheet_schema)
    return sheet
