"""Reusable assay-type assessments feeding the same A105 dimensions.

Readers/calculators supply native estimates, corrections and uncertainty. This
module assesses their scientific applicability and calculates the requested
evidence comparison. It never parses a paper or repeats a source correction.
"""
from copy import deepcopy
import math

from scipy.special import log_ndtr
from scipy.stats import t as student_t

from .domain import ContractError, obj, validate_schema

INPUT_VERSION = 'a105_assay_grading_inputs_v1'
VERSION = 'a105_assay_grading_sheet_v1'
EVALUATION_SCOPE = 'assay_type_experimental_evidence'
ASSAY_TYPES = ('activity_rate', 'endpoint_conversion', 'product_distribution', 'reaction_coupling',
               'ligand_binding', 'transport_response', 'protein_signal', 'protein_amount')
ASSAY_TYPE_LABELS = {
    'activity_rate': 'Enzyme activity and rate comparisons',
    'endpoint_conversion': 'Reaction progress and endpoint conversion',
    'product_distribution': 'Product distribution and equilibrium',
    'reaction_coupling': 'Reaction coupling and stoichiometric balance',
    'ligand_binding': 'Ligand binding and binding discrimination',
    'transport_response': 'Transport and substrate-response comparisons',
    'protein_signal': 'Reported protein signals and band measurements',
    'protein_amount': 'Protein amount and preparation composition',
}
QUANTITY_KINDS = {
    'activity_rate': ('rate', 'rate_difference', 'rate_ratio', 'turnover', 'catalytic_efficiency',
        'kinetic_parameter', 'kinetic_parameter_difference', 'kinetic_parameter_ratio', 'log_kinetic_parameter_ratio',
        'partner_rate_difference', 'partner_response_fraction'),
    'endpoint_conversion': ('conversion_fraction', 'conversion_difference', 'endpoint_amount',
                            'completion_time', 'completion_time_ratio'),
    'product_distribution': ('product_fraction', 'product_fraction_ratio',
                             'equilibrium_fraction', 'equilibrium_ratio'),
    'reaction_coupling': ('productive_fraction', 'stoichiometric_ratio', 'balance_residual'),
    'ligand_binding': ('binding_parameter', 'binding_parameter_ratio', 'log_binding_parameter_ratio',
        'binding_discrimination_ratio', 'log_binding_discrimination', 'band_display_fraction',
        'relative_binding_response', 'log_relative_binding_response'),
    'transport_response': ('transport_rate', 'transport_rate_ratio', 'log_transport_rate_ratio',
        'accumulated_amount', 'transport_parameter', 'substrate_saturation', 'substrate_response_ratio',
        'log_substrate_response', 'electrical_current', 'electrical_conductance', 'charge_equivalent_rate'),
    'protein_signal': ('signal_ratio', 'signal_difference', 'log_signal_ratio', 'band_display_fraction',
        'band_display_darkness'),
    'protein_amount': ('protein_amount', 'protein_amount_difference', 'protein_amount_ratio',
        'sites_per_monomer', 'active_fraction'),
}
REQUIRED_ROLES = ('effect', 'effect_variance', 'recovery', 'attributed_signal', 'total_signal',
                  'condition_test', 'condition_reference', 'assertion_prediction', 'alternative_prediction')
ROLES = (*REQUIRED_ROLES, 'effect_degrees_of_freedom')
COMPONENTS = ('measured_effect', 'effect_variance', 'effect_precision', 'recovery_deviation',
              'attributed_fraction', 'condition_response', 'assertion_prediction_error',
              'alternative_prediction_error', 'source_log_evidence_ratio')
COMMON_CRITERIA = ('measurement_identity', 'calibration_applicability', 'matrix_interference',
    'background_alternatives', 'attribution_supported', 'assertion_relevance', 'condition_scope',
    'variance_correspondence', 'sampling_basis')
CRITERIA_BY_TYPE = {
    'activity_rate': (*COMMON_CRITERIA, 'rate_regime', 'normalization_basis', 'kinetic_model',
                      'partner_perturbation'),
    'endpoint_conversion': (*COMMON_CRITERIA, 'endpoint_alignment', 'conversion_denominator', 'product_identity'),
    'product_distribution': (*COMMON_CRITERIA, 'species_identity', 'response_factors',
                             'common_denominator', 'equilibrium_state'),
    'reaction_coupling': (*COMMON_CRITERIA, 'product_identity', 'stoichiometry',
                         'matched_windows', 'reporter_specificity'),
    'ligand_binding': (*COMMON_CRITERIA, 'binding_parameter_definition', 'binding_species',
        'binding_controls', 'binding_regime', 'binding_comparison'),
    'transport_response': (*COMMON_CRITERIA, 'membrane_system', 'transport_endpoint',
        'transport_driving_force', 'transport_specificity', 'transport_response_model'),
    'protein_signal': (*COMMON_CRITERIA, 'signal_assignment', 'signal_response_range',
        'signal_normalization', 'signal_representation'),
    'protein_amount': (*COMMON_CRITERIA, 'amount_basis', 'preparation_relationship',
        'amount_calibration', 'active_site_stoichiometry'),
}
CRITERIA = tuple(dict.fromkeys(c for cs in CRITERIA_BY_TYPE.values() for c in cs))
CRITERION_QUESTIONS = {
    'measurement_identity': 'Do source subject, construct, preparation, endpoint, units and denominator identify this estimate?',
    'calibration_applicability': 'Do calibration, sensitivity, response range and recovery apply to this detector and selected estimate?',
    'matrix_interference': 'Are matrix effects, detector interference and sample handling addressed for this measured quantity?',
    'background_alternatives': 'Do matched controls or quantified corrections address spontaneous chemistry and competing contributions?',
    'attribution_supported': 'Does the selected quantity and its controls isolate the claimed contribution of the studied molecule, with the same endpoint and denominator for an attributed/total signal fraction?',
    'assertion_relevance': 'Does this endpoint at its actual functional resolution address the selected assertion?',
    'condition_scope': 'Do substrate, pH, temperature, heating, cofactors and in-vitro/in-vivo preparation support the asserted conditions? For a condition-response ratio, do same-molecule, same-endpoint controls isolate nuisance conditions outside the intended experimental change?',
    'variance_correspondence': 'Is this variance for this exact estimate, including its corrections and shared measurements?',
    'sampling_basis': 'Are sampling units, technical repeats, independent preparations and dependence correctly represented?',
    'rate_regime': 'Does the time/concentration regime justify the reported initial, interval or steady-state rate interpretation?',
    'normalization_basis': 'Is rate normalization tied to the actual assayed amount without equating mass purity and active fraction?',
    'kinetic_model': 'Do fitted parameter model, concentration range, held-fixed partners and uncertainty justify the kinetic claim?',
    'endpoint_alignment': 'Do comparisons use the same endpoint definition and actual observation times?',
    'conversion_denominator': 'Does the measured initial amount or reported denominator support the claimed conversion fraction?',
    'product_identity': 'Is the claimed product chemically identified rather than inferred from substrate or reporter disappearance?',
    'species_identity': 'Are the measured product species and their assignment established?',
    'response_factors': 'Are species-specific detector responses calibrated to the stated amount-fraction or signal-fraction basis?',
    'common_denominator': 'Do selected fractions share a defined denominator and stated species coverage, without treating closure as independent mass balance?',
    'equilibrium_state': 'Does time/stability or reverse-approach evidence establish equilibrium rather than a single endpoint?',
    'stoichiometry': 'Are reaction coefficients and productive-use normalization supported for the claimed reaction?',
    'matched_windows': 'Do product and reporter measurements refer to compatible reaction windows, preparations and normalization?',
    'reporter_specificity': 'Are reporter chemistry, coupling capacity and side consumption compatible with the claimed productive flux?',
    'partner_perturbation': 'Do omission and addback isolate the intended partner change, retain matched nonpartner factors and molecular roles, and distinguish genuine restoration from reuse of the baseline or chemical bypass?',
    'binding_parameter_definition': 'Is the selected binding response, deposited score or fitted parameter defined on its actual assay scale and response model, keeping relative binding scores, competition IC50, reported Hill Kd and direct-binding Kd distinct?',
    'binding_species': 'Are the protein state, tracer, competitor and ligand identities and concentration roles established, with separately assayed proteins distinguished from mixtures?',
    'binding_controls': 'Do baselines, self/noncognate competitors and nonspecific-binding controls address the alternatives relevant to this binding claim?',
    'binding_regime': 'Do equilibration or observation time, concentration range, ligand depletion and fit adequacy support the reported parameter?',
    'binding_comparison': 'Do the compared fits share the supported parameter definition and intended ligand/protein mapping, while retaining differences in input amounts and conditions?',
    'membrane_system': 'Are the actual membrane, preparation and cellular or reconstituted system established, including integrity and background controls?',
    'transport_endpoint': 'Is the measurement identified as accumulation, initial flux, saturation response, current, conductance or charge equivalents without silently converting one into another?',
    'transport_driving_force': 'Do substrate concentrations or activities, voltage conventions, gradients and reversal conditions apply to this measurement?',
    'transport_specificity': 'Do ion/substrate controls and attribution support the claimed transported species, keeping charge flow distinct from identified-ion flux?',
    'transport_response_model': 'Do the selected concentrations and apparent Km belong to the same supported kinetic curve, with shared-fit uncertainty and actual saturation-model applicability?',
    'signal_assignment': 'Are measured bands or signals assigned to the intended species and lane or construct, with the relevant loading/background controls?',
    'signal_response_range': 'Do exposure, saturation, detector linearity and background treatment support this signal comparison on its stated display or calibrated scale?',
    'signal_normalization': 'Do numerator and reference share a supported signal scale and denominator, keeping loading/expression differences outside the intended change explicit?',
    'signal_representation': 'Are repeated displays, ambiguous readings, joint alternatives and ROI choices preserved as representations of their actual physical measurements?',
    'amount_basis': 'Are target versus total protein, mass versus molar amount, nominal recipe versus measured amount, and active versus total sites distinguished?',
    'preparation_relationship': 'Do amount comparisons refer to the established same stock or intended experimental arms, rather than inferred equality from units or protein names?',
    'amount_calibration': 'Do measurement calibration, sample handling, molecular-weight assumptions and uncertainty apply to these actual amount estimates?',
    'active_site_stoichiometry': 'Do titrant standardization, binding stoichiometry and site-per-monomer assumptions support the active-site interpretation without treating mass purity as active fraction?',
}
ORIGINS = ('reported', 'derived', 'graph_derived', 'synthetic', 'proposed')


def _strings():
    return {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'uniqueItems': True}


def interpretation_schema():
    return obj({'status': {'enum': ['supported', 'unknown', 'conflicting', 'not_applicable']},
                'support_refs': _strings()})


def operand_schema():
    result = obj({'value': {'type': ['number', 'null']}, 'unit': {'type': 'string', 'minLength': 1},
        'status': {'enum': ['point', 'bounded', 'unavailable']},
        'reason': {'type': ['string', 'null']}, 'measurement_keys': _strings(),
        'source_refs': _strings(), 'origin': {'enum': list(ORIGINS)},
        'native_component': {'type': 'string', 'minLength': 1}})
    result['properties']['qualifications'] = _strings()
    result['properties']['bound'] = {'anyOf': [bound_schema(), {'type': 'null'}]}
    return result


def bound_schema():
    return obj({'relation': {'enum': ['lt', 'le', 'gt', 'ge', 'interval']},
        'lower': {'type': ['number', 'null']}, 'upper': {'type': ['number', 'null']}})


def prediction_model_schema():
    return obj({'kind': {'enum': ['fixed_predictions_known_normal',
        'fixed_predictions_estimated_normal', 'fixed_predictions_student_t']},
        'variance_interpretation': {'enum': ['known', 'estimated', 'unknown']},
        'support_refs': _strings()})


def assay_grading_input_schema():
    result = obj({'version': {'const': INPUT_VERSION}, 'assay_type': {'enum': list(ASSAY_TYPES)},
        'assertion_ref': {'type': 'string', 'minLength': 1},
        'quantity_kind': {'enum': list(dict.fromkeys(k for ks in QUANTITY_KINDS.values() for k in ks))},
        'quantities': obj({role: {'anyOf': [operand_schema(), {'type': 'null'}]} for role in ROLES},
                          required=list(REQUIRED_ROLES)),
        'interpretations': {'type': 'object', 'properties': {c: interpretation_schema() for c in CRITERIA},
                            'additionalProperties': False},
        'prediction_model': {'anyOf': [prediction_model_schema(), {'type': 'null'}]}})
    result['allOf'] = [{'if': {'properties': {'assay_type': {'const': kind}}},
        'then': {'properties': {'quantity_kind': {'enum': list(quantities)},
            'interpretations': {'propertyNames': {'enum': list(CRITERIA_BY_TYPE[kind])}}}}}
        for kind, quantities in QUANTITY_KINDS.items()]
    return result


def assay_grading_cell_schema():
    result = obj({'component': {'enum': list(COMPONENTS)},
        'dimension': {'enum': ['measurement', 'reliability', 'validity', 'attribution', 'comparability', 'relevance', 'experimental_evidence']},
        'value': {'type': ['number', 'null']}, 'unit': {'type': 'string'},
        'status': {'enum': ['populated', 'conditional', 'bounded', 'unavailable']}, 'reasons': _strings(),
        'formula': {'type': 'string'}, 'meaning': {'type': 'string'},
        'measurement_keys': _strings(), 'source_refs': _strings(),
        'input_origins': {'type': 'array', 'items': {'enum': list(ORIGINS)}, 'uniqueItems': True},
        'conditions': _strings()})
    result['properties']['bound'] = bound_schema()
    return result


def assay_grading_sheet_schema():
    return obj({'version': {'const': VERSION}, 'axis': {'const': 'A105'},
        'evaluation_scope': {'const': EVALUATION_SCOPE}, 'assay_type': {'enum': list(ASSAY_TYPES)},
        'assertion_ref': {'type': 'string', 'minLength': 1},
        'quantity_kind': {'enum': list(dict.fromkeys(k for ks in QUANTITY_KINDS.values() for k in ks))},
        'cells': obj({name: assay_grading_cell_schema() for name in COMPONENTS}),
        'interpretations': assay_grading_input_schema()['properties']['interpretations'],
        'prediction_model': {'anyOf': [prediction_model_schema(), {'type': 'null'}]},
        'annotation_credit': {'type': 'null'}})


DIMENSIONS = dict(zip(COMPONENTS, ('measurement', 'reliability', 'reliability', 'validity',
    'attribution', 'comparability', 'relevance', 'relevance', 'experimental_evidence')))
FORMULAS = dict(zip(COMPONENTS, ('selected_native_effect', 'selected_variance_of_native_effect',
    '1/variance', 'recovery-1', 'attributed_signal/total_signal',
    'condition_test/condition_reference', 'effect-assertion_prediction',
    'effect-alternative_prediction',
    '((effect-alternative_prediction)^2-(effect-assertion_prediction)^2)/(2*variance)')))
MEANINGS = dict(zip(COMPONENTS, (
    'The selected native measurement or contrast, with its original functional resolution; not a quality score.',
    'Variance of the selected estimate, including only uncertainty represented by the supplied source/model.',
    'Inverse variance of that estimate on its native scale; not an assay success probability.',
    'Measured recovery deviation from unity; a calibration diagnostic, not a universal validity grade.',
    'Fraction of the selected total signal assigned to the studied molecular contribution by the supported attribution model.',
    'Measured nuisance-condition test/reference response; comparability information, not an additional correction or penalty.',
    'Signed difference between the selected estimate and the explicit prediction of the asserted function.',
    'Signed difference between the selected estimate and the explicit prediction of the named alternative.',
    'Signed log likelihood ratio for two fixed predictions under the declared measurement model, using the observed value or censoring event. Estimated-normal comparisons are plug-in approximations; Student-t comparisons use the explicitly selected residual model. Positive values support the assertion relative to that alternative; not annotation probability.',
)))


def _fail(reason):
    raise ContractError('assay_grading_' + reason)


def _unique(values):
    return list(dict.fromkeys(values))


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except (OverflowError, ValueError):
        return False


def _uncertainty_qualification(text):
    lowered = text.lower()
    return (any(word in lowered for word in ('unknown', 'unresolved', 'conflicting'))
            or 'estimated' in lowered and any(word in lowered for word in ('variance', 'covariance')))


def _variance_units(unit):
    aliases = {'per_min': 'per_min_squared', 'dimensionless': 'dimensionless_squared',
               'fraction': 'fraction_squared', 'min': 'min_squared',
               'uM/min': 'uM_squared/min_squared', 'uM': 'uM_squared',
               'uM^-1min^-1': 'uM_inverse_squared_min_inverse_squared',
               'uM_inverse_min_inverse': 'uM_inverse_squared_min_inverse_squared'}
    result = {unit + '^2', '(' + unit + ')^2', unit + '_squared'}
    if unit in aliases:
        result.add(aliases[unit])
    # Fractions are dimensionless, but a fraction must not be confused with a
    # percent scale. The adapter preserves native units in its saved custody.
    if unit == 'fraction':
        result.add('dimensionless_squared')
    return result


def _quantity_unit_supported(kind, unit):
    dimensionless = {'fraction', 'dimensionless'}
    if kind in ('rate_ratio', 'conversion_fraction', 'conversion_difference', 'completion_time_ratio',
                'product_fraction', 'product_fraction_ratio', 'equilibrium_fraction', 'equilibrium_ratio',
                'productive_fraction', 'stoichiometric_ratio', 'kinetic_parameter_ratio',
                'log_kinetic_parameter_ratio', 'partner_response_fraction', 'binding_parameter_ratio',
                'log_binding_parameter_ratio', 'binding_discrimination_ratio', 'log_binding_discrimination',
                'transport_rate_ratio', 'log_transport_rate_ratio', 'substrate_saturation',
                'substrate_response_ratio', 'log_substrate_response', 'signal_ratio', 'signal_difference',
                'log_signal_ratio', 'protein_amount_ratio', 'sites_per_monomer', 'active_fraction'):
        return unit in dimensionless
    if kind == 'band_display_fraction':
        return unit == 'display_fraction'
    if kind == 'band_display_darkness':
        return unit == 'display_darkness_sum'
    if kind in ('binding_parameter', 'transport_parameter'):
        return unit in {'M', 'mM', 'uM', 'nM'}
    if kind in ('kinetic_parameter', 'kinetic_parameter_difference'):
        return unit in {'M', 'mM', 'uM', 'nM', 'per_min', 'per_s', 's^-1', 'min^-1',
            'U/mg', 'umol/min/mg', 'uM_inverse_min_inverse'}
    if kind == 'electrical_current':
        return unit in {'pA', 'nA', 'uA', 'A'}
    if kind == 'electrical_conductance':
        return unit in {'pS', 'nS', 'uS', 'S'}
    if kind == 'charge_equivalent_rate':
        return unit == 'elementary_charge_equivalents_per_s'
    if kind == 'completion_time':
        return unit in {'s', 'sec', 'min', 'h', 'hour'}
    if kind in ('endpoint_amount', 'balance_residual', 'accumulated_amount',
                'protein_amount', 'protein_amount_difference'):
        return unit in {'M', 'mM', 'uM', 'nM', 'mol', 'mmol', 'umol', 'nmol', 'pmol',
                        'molecules', 'count', 'mg', 'ug', 'ng', 'mg/ml', 'mg/mL'}
    if kind in ('rate', 'rate_difference', 'partner_rate_difference', 'transport_rate'):
        return unit in {'U/mg', 'U/mL', 'uM/min', 'uM/s', 'mM/min', 'mM/s', 'nM/min', 'nM/s',
                        'mmol/min', 'umol/min', 'nmol/min', 'nmol/s', 'pmol/min',
                        'umol/min/mg', 'nmol/min/mg', 'pmol/min/mg',
                        'per_min', 'per_s', 's^-1', 'min^-1'}
    if kind == 'turnover':
        return unit in {'per_min', 'per_s', 's^-1', 'min^-1', '1/s', '1/min'}
    if kind == 'catalytic_efficiency':
        return unit in {'uM^-1min^-1', 'uM_inverse_min_inverse', 'M^-1s^-1', 'uM^-1s^-1',
                        'M^-1min^-1', 'mM^-1s^-1', 'mM^-1min^-1'}
    return False


def _required_criteria(assay_type, quantity_kind):
    required = list(CRITERIA_BY_TYPE[assay_type])
    optional = set()
    if assay_type == 'activity_rate':
        if quantity_kind not in ('turnover', 'catalytic_efficiency', 'kinetic_parameter', 'kinetic_parameter_difference',
                                 'kinetic_parameter_ratio', 'log_kinetic_parameter_ratio'):
            optional.add('kinetic_model')
        if quantity_kind.startswith('kinetic_parameter') or quantity_kind == 'log_kinetic_parameter_ratio':
            optional.update(('rate_regime', 'normalization_basis'))
        if not quantity_kind.startswith('partner_'):
            optional.add('partner_perturbation')
    if assay_type == 'endpoint_conversion':
        # Disappearance/conversion is not a chemically identified-product
        # assertion. That broader inference is not made by this quantity kind.
        optional.add('product_identity')
        if quantity_kind in ('endpoint_amount', 'completion_time', 'completion_time_ratio'):
            optional.add('conversion_denominator')
    if assay_type == 'product_distribution' and not quantity_kind.startswith('equilibrium_'):
        optional.add('equilibrium_state')
    if assay_type == 'transport_response' and quantity_kind not in (
            'transport_parameter', 'substrate_saturation', 'substrate_response_ratio', 'log_substrate_response'):
        optional.add('transport_response_model')
    if assay_type == 'protein_amount' and quantity_kind not in ('sites_per_monomer', 'active_fraction'):
        optional.add('active_site_stoichiometry')
    if assay_type == 'ligand_binding' and quantity_kind == 'band_display_fraction':
        # A controlled gel-shift readout addresses binding without fitting Kd
        # or IC50. Species, competition controls, regime and mapping still apply.
        optional.add('binding_parameter_definition')
    return required, optional


def _validate_bound(operand):
    bound = operand.get('bound')
    if bound is None:
        return
    if operand['status'] != 'bounded' or operand['value'] is not None:
        _fail('bound_operand_inconsistent')
    lower, upper = bound['lower'], bound['upper']
    if any(value is not None and not _finite(value) for value in (lower, upper)):
        _fail('finite_bound_required')
    relation = bound['relation']
    if (relation in ('lt', 'le') and (lower is not None or upper is None)
            or relation in ('gt', 'ge') and (lower is None or upper is not None)
            or relation == 'interval' and (lower is None or upper is None or lower >= upper)):
        _fail('bound_limits_inconsistent')
    if not operand['measurement_keys']:
        _fail('operand_identity_required')


def _shift_bound(bound, shift):
    return {'relation': bound['relation'],
        'lower': None if bound['lower'] is None else bound['lower'] - shift,
        'upper': None if bound['upper'] is None else bound['upper'] - shift}


def _log_difference(larger, smaller):
    # log(exp(larger)-exp(smaller)); expm1 preserves a narrow interval.
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
    lower, upper = bound['lower'], bound['upper']
    if lower is None:
        return cdf(upper)
    if upper is None:
        return survival(lower)
    # Use the nearer tail, rather than subtracting two CDFs rounded to one.
    if lower >= prediction:
        return _log_difference(survival(lower), survival(upper))
    return _log_difference(cdf(upper), cdf(lower))


def _evidence_comparison(effect, assertion, alternative, variance, model, df):
    kind, bound = model['kind'], effect.get('bound')
    scale = math.sqrt(variance)
    if bound is not None:
        value = (_log_event_probability(bound, assertion, scale, kind, df)
                 - _log_event_probability(bound, alternative, scale, kind, df))
        formula = 'log(P(observed_censoring_event|assertion)/P(observed_censoring_event|alternative))'
    elif kind == 'fixed_predictions_student_t':
        value = (float(student_t.logpdf((effect['value'] - assertion) / scale, df))
                 - float(student_t.logpdf((effect['value'] - alternative) / scale, df)))
        formula = 'log(t_df((effect-assertion)/sqrt(estimated_variance))/t_df((effect-alternative)/sqrt(estimated_variance)))'
    else:
        difference = assertion - alternative
        midpoint_residual = (effect['value'] - alternative) - difference / 2
        value = difference * midpoint_residual / variance
        formula = FORMULAS['source_log_evidence_ratio']
    return value, formula


def grade_assay(extraction):
    """Convert native reader outputs into one common numerical A105 assessment.

    The variance must describe the exact selected effect, including whatever
    corrections were already applied upstream. None of recovery, attribution,
    or condition response is multiplied into that effect a second time.
    Scientific interpretations determine which uses are warranted; they are
    never turned into categorical numerical quality weights.
    """
    return grade_experimental_measurement(extraction,
        input_schema=assay_grading_input_schema(), sheet_schema=assay_grading_sheet_schema(),
        required_criteria=_required_criteria, quantity_unit_supported=_quantity_unit_supported,
        version=VERSION, axis='A105', evaluation_scope=EVALUATION_SCOPE)


def grade_experimental_measurement(extraction, *, input_schema, sheet_schema,
        required_criteria, quantity_unit_supported, version, axis, evaluation_scope):
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
    assay_type, quantity_kind = data['assay_type'], data['quantity_kind']
    model = data['prediction_model']
    required, optional = required_criteria(assay_type, quantity_kind)
    # An amount endpoint may be substrate loss or product formation. That
    # distinction needs an explicit supported identity or witnessed statement
    # that chemical product identity does not apply to the narrower endpoint.
    explicit_applicability = {'product_identity'} if (
        assay_type == 'endpoint_conversion' and quantity_kind == 'endpoint_amount') else set()
    for role, operand in quantities.items():
        if operand is None:
            continue
        if operand['value'] is not None and not _finite(operand['value']):
            _fail('finite_number_required')
        if operand['status'] == 'point' and (operand['value'] is None or operand['reason'] is not None):
            _fail('point_operand_inconsistent')
        if not operand['source_refs']:
            _fail('operand_source_required')
        if operand['status'] == 'point' and not operand['measurement_keys']:
            _fail('operand_identity_required')
        _validate_bound(operand)
    for name, interpretation in interpretations.items():
        if interpretation['status'] in ('supported', 'not_applicable') and not interpretation['support_refs']:
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
            elif item['status'] != 'supported' and not (name in optional and item['status'] == 'not_applicable'):
                reasons.append(name + '_' + item['status'])
        return reasons

    def operand_reasons(roles, *, bounded_roles=()):
        reasons = []
        for role in roles:
            operand = quantities[role]
            if operand is None:
                reasons.append(role + '_not_selected')
            elif (operand['status'] != 'point' and not
                    (role in bounded_roles and operand['status'] == 'bounded' and operand.get('bound') is not None)):
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

    def cell(name, value, roles, output_unit, *, reasons=(), criteria=(), conditions=(), conditional=False,
             use_model=False, bounded_roles=(), bound=None, formula=None):
        failures = _unique([*operand_reasons(roles, bounded_roles=bounded_roles), *reasons])
        if value is not None and not _finite(value):
            failures.append('numerical_model_range')
        if bound is not None and any(v is not None and not _finite(v) for v in (bound['lower'], bound['upper'])):
            failures.append('numerical_model_range')
        if failures:
            value = None
            bound = None
        if value is None and bound is None and not failures:
            failures.append('calculation_unavailable')
        result = {'component': name, 'dimension': DIMENSIONS[name], 'value': value, 'unit': output_unit,
            'status': 'bounded' if bound is not None else 'unavailable' if value is None else 'conditional' if conditional else 'populated',
            'reasons': _unique(failures), 'formula': FORMULAS[name] if formula is None else formula, 'meaning': MEANINGS[name],
            'measurement_keys': _unique([key for role in roles if quantities[role] is not None
                                        for key in quantities[role]['measurement_keys']]),
            'source_refs': sources(roles, criteria, use_model),
            'input_origins': _unique([quantities[role]['origin'] for role in roles if quantities[role] is not None]),
            'conditions': _unique([*conditions, *[qualification for role in roles if quantities[role] is not None
                for qualification in quantities[role].get('qualifications', ())]])}
        if bound is not None:
            result['bound'] = deepcopy(bound)
        return result

    cells = {}
    effect_bound = (quantities['effect'] or {}).get('bound')
    effect_reason = operand_reasons(('effect',), bounded_roles=('effect',))
    cells['measured_effect'] = cell('measured_effect', None if effect_reason else number('effect'),
        ('effect',), unit('effect'), conditions=('native_corrections_are_not_applied_again',),
        bounded_roles=('effect',), bound=effect_bound)

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
    cells['effect_variance'] = cell('effect_variance', variance, variance_roles, unit('effect_variance'),
        reasons=variance_reasons, criteria=variance_criteria, conditions=variance_conditions,
        bounded_roles=('effect',))
    precision_reasons = list(variance_reasons)
    if variance == 0:
        precision_reasons.append('positive_variance_required')
    precision = None if variance is None or variance <= 0 else 1 / variance
    cells['effect_precision'] = cell('effect_precision', precision, variance_roles,
        '1/(' + unit('effect_variance') + ')', reasons=precision_reasons, criteria=variance_criteria,
        conditions=(*variance_conditions, 'precision_is_scale_dependent_not_a_quality_probability'),
        bounded_roles=('effect',),
        conditional=model is None or model['variance_interpretation'] != 'known'
            or any(_uncertainty_qualification(q) for role in variance_roles if quantities[role] is not None
                   for q in quantities[role].get('qualifications', ())))

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
    cells['recovery_deviation'] = cell('recovery_deviation', recovery_deviation, ('recovery',), 'dimensionless',
        reasons=calibration_reasons, criteria=calibration_criteria,
        conditions=('diagnostic_not_a_validity_multiplier', 'do_not_reapply_calibration'))

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
    attribution_conditions = ['same_endpoint_denominator_and_source_attribution_model',
                              'activity_fraction_is_not_mass_purity', 'do_not_reapply_attribution']
    if fraction is not None and not 0 <= fraction <= 1:
        attribution_conditions.append('outside_physical_fraction_range_not_clamped')
    cells['attributed_fraction'] = cell('attributed_fraction', fraction, attribution_roles, 'fraction',
        reasons=attribution_reasons, criteria=attribution_criteria, conditions=attribution_conditions)

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
    cells['condition_response'] = cell('condition_response', response, comparison_roles, 'dimensionless',
        reasons=comparison_reasons, criteria=comparison_criteria,
        conditions=('nuisance_conditions_outside_the_intended_change', 'do_not_reapply_condition_correction'))

    prediction_criteria = tuple(c for c in required if c not in ('variance_correspondence', 'sampling_basis'))
    for role, name in (('assertion_prediction', 'assertion_prediction_error'),
                       ('alternative_prediction', 'alternative_prediction_error')):
        roles = ('effect', role)
        reasons = [*operand_reasons(roles, bounded_roles=('effect',)), *criteria_reasons(prediction_criteria)]
        difference, difference_bound = None, None
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
        cells[name] = cell(name, difference, roles, unit('effect'), reasons=reasons,
            criteria=prediction_criteria,
            bounded_roles=('effect',), bound=difference_bound,
            conditions=('same_selected_reference_assertion_and_experimental_conditions',
                        'fixed_prediction_not_inferred_from_this_observation'),
            conditional=any(quantities[r] is not None and quantities[r]['origin'] == 'proposed' for r in roles))

    evidence_roles = ('effect', 'effect_variance', 'assertion_prediction', 'alternative_prediction')
    if model is not None and model['kind'] == 'fixed_predictions_student_t':
        evidence_roles += ('effect_degrees_of_freedom',)
    evidence_reasons = [*operand_reasons(evidence_roles, bounded_roles=('effect',)), *criteria_reasons(required), *precision_reasons,
        *cells['assertion_prediction_error']['reasons'], *cells['alternative_prediction_error']['reasons']]
    estimated_model = model is not None and model['kind'] in (
        'fixed_predictions_estimated_normal', 'fixed_predictions_student_t')
    for role in evidence_roles:
        operand = quantities[role]
        if operand is None:
            continue
        for qualification in operand.get('qualifications', ()):
            # A saved component can support one measurement-model comparison
            # without proving its independence from every other experiment.
            # Keep that limitation in the row; never turn it into a claim of
            # independent replication or an extra contribution.
            if qualification == 'physical_measurement_identity_unknown':
                continue
            if _uncertainty_qualification(qualification):
                lowered = qualification.lower()
                if (estimated_model and 'estimated' in lowered
                        and not any(word in lowered for word in ('unknown', 'unresolved', 'conflicting'))):
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
    score, formula = None, FORMULAS['source_log_evidence_ratio']
    if not evidence_reasons:
        try:
            score, formula = _evidence_comparison(quantities['effect'], number('assertion_prediction'),
                number('alternative_prediction'), variance, model, df)
        except (ArithmeticError, ValueError):
            evidence_reasons.append('numerical_model_range')
    model_conditions = [] if model is None else [model['kind'] + '_model']
    if model is not None and model['kind'] == 'fixed_predictions_estimated_normal':
        model_conditions.extend(('estimated_variance_plugin_normal_approximation',
            'variance_estimation_uncertainty_not_integrated'))
    elif model is not None and model['kind'] == 'fixed_predictions_student_t':
        model_conditions.extend(('explicit_student_t_residual_model',
            'estimated_mean_variance_used_as_squared_t_scale',
            't_sampling_model_is_not_inferred_from_reported_sd'))
    if effect_bound is not None:
        model_conditions.append('probability_of_reported_censoring_event_not_density_at_limit_or_zero')
    cells['source_log_evidence_ratio'] = cell('source_log_evidence_ratio', score, evidence_roles,
        'dimensionless', reasons=evidence_reasons, criteria=required, use_model=True,
        conditional=True, bounded_roles=('effect',), formula=formula,
        conditions=(*model_conditions,
            'conditional_log_likelihood_not_annotation_probability',
            'one_selected_observation_not_independent_of_its_derived_diagnostics',
            'no_target_correspondence_or_W05_aggregation'))
    sheet = {'version': version, 'axis': axis, 'evaluation_scope': evaluation_scope,
        'assay_type': assay_type, 'assertion_ref': data['assertion_ref'], 'quantity_kind': quantity_kind,
        'cells': cells, 'interpretations': deepcopy(interpretations),
        'prediction_model': deepcopy(model), 'annotation_credit': None}
    validate_schema(sheet, sheet_schema)
    return sheet


__all__ = ['INPUT_VERSION', 'VERSION', 'EVALUATION_SCOPE', 'ASSAY_TYPES', 'QUANTITY_KINDS',
    'ROLES', 'COMPONENTS', 'COMMON_CRITERIA', 'CRITERIA_BY_TYPE', 'CRITERIA', 'CRITERION_QUESTIONS',
    'assay_grading_input_schema', 'assay_grading_sheet_schema', 'assay_grading_cell_schema',
    'operand_schema', 'bound_schema', 'interpretation_schema', 'prediction_model_schema', 'grade_assay']
