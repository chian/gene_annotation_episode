"""Reusable assay-type assessments feeding the same A105 dimensions.

Readers/calculators supply native estimates, corrections and uncertainty. This
module assesses their scientific applicability and calculates the requested
evidence comparison. It never parses a paper or repeats a source correction.
"""
from __future__ import annotations
from copy import deepcopy
import math
from scipy.special import log_ndtr
from scipy.stats import t as student_t
from gene_annotation_episode.episodic_workflow.root.a105.domain import obj, validate_schema
from gene_annotation_episode.domain import ContractError
INPUT_VERSION = 'a105_assay_grading_inputs_v1'
VERSION = 'a105_assay_grading_sheet_v1'
EVALUATION_SCOPE = 'assay_type_experimental_evidence'
ASSAY_TYPES = ('activity_rate', 'endpoint_conversion', 'product_distribution', 'reaction_coupling', 'ligand_binding', 'transport_response', 'protein_signal', 'protein_amount')
ASSAY_TYPE_LABELS = {'activity_rate': 'Enzyme activity and rate comparisons', 'endpoint_conversion': 'Reaction progress and endpoint conversion', 'product_distribution': 'Product distribution and equilibrium', 'reaction_coupling': 'Reaction coupling and stoichiometric balance', 'ligand_binding': 'Ligand binding and binding discrimination', 'transport_response': 'Transport and substrate-response comparisons', 'protein_signal': 'Reported protein signals and band measurements', 'protein_amount': 'Protein amount and preparation composition'}
QUANTITY_KINDS = {'activity_rate': ('rate', 'rate_difference', 'rate_ratio', 'turnover', 'catalytic_efficiency', 'kinetic_parameter', 'kinetic_parameter_difference', 'kinetic_parameter_ratio', 'log_kinetic_parameter_ratio', 'partner_rate_difference', 'partner_response_fraction'), 'endpoint_conversion': ('conversion_fraction', 'conversion_difference', 'endpoint_amount', 'completion_time', 'completion_time_ratio'), 'product_distribution': ('product_fraction', 'product_fraction_ratio', 'equilibrium_fraction', 'equilibrium_ratio'), 'reaction_coupling': ('productive_fraction', 'stoichiometric_ratio', 'balance_residual'), 'ligand_binding': ('binding_parameter', 'binding_parameter_ratio', 'log_binding_parameter_ratio', 'binding_discrimination_ratio', 'log_binding_discrimination', 'band_display_fraction', 'relative_binding_response', 'log_relative_binding_response'), 'transport_response': ('transport_rate', 'transport_rate_ratio', 'log_transport_rate_ratio', 'accumulated_amount', 'transport_parameter', 'substrate_saturation', 'substrate_response_ratio', 'log_substrate_response', 'electrical_current', 'electrical_conductance', 'charge_equivalent_rate'), 'protein_signal': ('signal_ratio', 'signal_difference', 'log_signal_ratio', 'band_display_fraction', 'band_display_darkness'), 'protein_amount': ('protein_amount', 'protein_amount_difference', 'protein_amount_ratio', 'sites_per_monomer', 'active_fraction')}
REQUIRED_ROLES = ('effect', 'effect_variance', 'recovery', 'attributed_signal', 'total_signal', 'condition_test', 'condition_reference', 'assertion_prediction', 'alternative_prediction')
ROLES = (*REQUIRED_ROLES, 'effect_degrees_of_freedom')
COMPONENTS = ('measured_effect', 'effect_variance', 'effect_precision', 'recovery_deviation', 'attributed_fraction', 'condition_response', 'assertion_prediction_error', 'alternative_prediction_error', 'source_log_evidence_ratio')
COMMON_CRITERIA = ('measurement_identity', 'calibration_applicability', 'matrix_interference', 'background_alternatives', 'attribution_supported', 'assertion_relevance', 'condition_scope', 'variance_correspondence', 'sampling_basis')
CRITERIA_BY_TYPE = {'activity_rate': (*COMMON_CRITERIA, 'rate_regime', 'normalization_basis', 'kinetic_model', 'partner_perturbation'), 'endpoint_conversion': (*COMMON_CRITERIA, 'endpoint_alignment', 'conversion_denominator', 'product_identity'), 'product_distribution': (*COMMON_CRITERIA, 'species_identity', 'response_factors', 'common_denominator', 'equilibrium_state'), 'reaction_coupling': (*COMMON_CRITERIA, 'product_identity', 'stoichiometry', 'matched_windows', 'reporter_specificity'), 'ligand_binding': (*COMMON_CRITERIA, 'binding_parameter_definition', 'binding_species', 'binding_controls', 'binding_regime', 'binding_comparison'), 'transport_response': (*COMMON_CRITERIA, 'membrane_system', 'transport_endpoint', 'transport_driving_force', 'transport_specificity', 'transport_response_model'), 'protein_signal': (*COMMON_CRITERIA, 'signal_assignment', 'signal_response_range', 'signal_normalization', 'signal_representation'), 'protein_amount': (*COMMON_CRITERIA, 'amount_basis', 'preparation_relationship', 'amount_calibration', 'active_site_stoichiometry')}
CRITERIA = tuple(dict.fromkeys((c for cs in CRITERIA_BY_TYPE.values() for c in cs)))
CRITERION_QUESTIONS = {'measurement_identity': 'Do source subject, construct, preparation, endpoint, units and denominator identify this estimate?', 'calibration_applicability': 'Do calibration, sensitivity, response range and recovery apply to this detector and selected estimate?', 'matrix_interference': 'Are matrix effects, detector interference and sample handling addressed for this measured quantity?', 'background_alternatives': 'Do matched controls or quantified corrections address spontaneous chemistry and competing contributions?', 'attribution_supported': 'Does the selected quantity and its controls isolate the claimed contribution of the studied molecule, with the same endpoint and denominator for an attributed/total signal fraction?', 'assertion_relevance': 'Does this endpoint at its actual functional resolution address the selected assertion?', 'condition_scope': 'Do substrate, pH, temperature, heating, cofactors and in-vitro/in-vivo preparation support the asserted conditions? For a condition-response ratio, do same-molecule, same-endpoint controls isolate nuisance conditions outside the intended experimental change?', 'variance_correspondence': 'Is this variance for this exact estimate, including its corrections and shared measurements?', 'sampling_basis': 'Are sampling units, technical repeats, independent preparations and dependence correctly represented?', 'rate_regime': 'Does the time/concentration regime justify the reported initial, interval or steady-state rate interpretation?', 'normalization_basis': 'Is rate normalization tied to the actual assayed amount without equating mass purity and active fraction?', 'kinetic_model': 'Do fitted parameter model, concentration range, held-fixed partners and uncertainty justify the kinetic claim?', 'endpoint_alignment': 'Do comparisons use the same endpoint definition and actual observation times?', 'conversion_denominator': 'Does the measured initial amount or reported denominator support the claimed conversion fraction?', 'product_identity': 'Is the claimed product chemically identified rather than inferred from substrate or reporter disappearance?', 'species_identity': 'Are the measured product species and their assignment established?', 'response_factors': 'Are species-specific detector responses calibrated to the stated amount-fraction or signal-fraction basis?', 'common_denominator': 'Do selected fractions share a defined denominator and stated species coverage, without treating closure as independent mass balance?', 'equilibrium_state': 'Does time/stability or reverse-approach evidence establish equilibrium rather than a single endpoint?', 'stoichiometry': 'Are reaction coefficients and productive-use normalization supported for the claimed reaction?', 'matched_windows': 'Do product and reporter measurements refer to compatible reaction windows, preparations and normalization?', 'reporter_specificity': 'Are reporter chemistry, coupling capacity and side consumption compatible with the claimed productive flux?', 'partner_perturbation': 'Do omission and addback isolate the intended partner change, retain matched nonpartner factors and molecular roles, and distinguish genuine restoration from reuse of the baseline or chemical bypass?', 'binding_parameter_definition': 'Is the selected binding response, deposited score or fitted parameter defined on its actual assay scale and response model, keeping relative binding scores, competition IC50, reported Hill Kd and direct-binding Kd distinct?', 'binding_species': 'Are the protein state, tracer, competitor and ligand identities and concentration roles established, with separately assayed proteins distinguished from mixtures?', 'binding_controls': 'Do baselines, self/noncognate competitors and nonspecific-binding controls address the alternatives relevant to this binding claim?', 'binding_regime': 'Do equilibration or observation time, concentration range, ligand depletion and fit adequacy support the reported parameter?', 'binding_comparison': 'Do the compared fits share the supported parameter definition and intended ligand/protein mapping, while retaining differences in input amounts and conditions?', 'membrane_system': 'Are the actual membrane, preparation and cellular or reconstituted system established, including integrity and background controls?', 'transport_endpoint': 'Is the measurement identified as accumulation, initial flux, saturation response, current, conductance or charge equivalents without silently converting one into another?', 'transport_driving_force': 'Do substrate concentrations or activities, voltage conventions, gradients and reversal conditions apply to this measurement?', 'transport_specificity': 'Do ion/substrate controls and attribution support the claimed transported species, keeping charge flow distinct from identified-ion flux?', 'transport_response_model': 'Do the selected concentrations and apparent Km belong to the same supported kinetic curve, with shared-fit uncertainty and actual saturation-model applicability?', 'signal_assignment': 'Are measured bands or signals assigned to the intended species and lane or construct, with the relevant loading/background controls?', 'signal_response_range': 'Do exposure, saturation, detector linearity and background treatment support this signal comparison on its stated display or calibrated scale?', 'signal_normalization': 'Do numerator and reference share a supported signal scale and denominator, keeping loading/expression differences outside the intended change explicit?', 'signal_representation': 'Are repeated displays, ambiguous readings, joint alternatives and ROI choices preserved as representations of their actual physical measurements?', 'amount_basis': 'Are target versus total protein, mass versus molar amount, nominal recipe versus measured amount, and active versus total sites distinguished?', 'preparation_relationship': 'Do amount comparisons refer to the established same stock or intended experimental arms, rather than inferred equality from units or protein names?', 'amount_calibration': 'Do measurement calibration, sample handling, molecular-weight assumptions and uncertainty apply to these actual amount estimates?', 'active_site_stoichiometry': 'Do titrant standardization, binding stoichiometry and site-per-monomer assumptions support the active-site interpretation without treating mass purity as active fraction?'}
ORIGINS = ('reported', 'derived', 'graph_derived', 'synthetic', 'proposed')

def _strings():
    return {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'uniqueItems': True}

def interpretation_schema():
    return obj({'status': {'enum': ['supported', 'unknown', 'conflicting', 'not_applicable']}, 'support_refs': _strings()})

def operand_schema():
    result = obj({'value': {'type': ['number', 'null']}, 'unit': {'type': 'string', 'minLength': 1}, 'status': {'enum': ['point', 'bounded', 'unavailable']}, 'reason': {'type': ['string', 'null']}, 'measurement_keys': _strings(), 'source_refs': _strings(), 'origin': {'enum': list(ORIGINS)}, 'native_component': {'type': 'string', 'minLength': 1}})
    result['properties']['qualifications'] = _strings()
    result['properties']['bound'] = {'anyOf': [bound_schema(), {'type': 'null'}]}
    return result

def bound_schema():
    return obj({'relation': {'enum': ['lt', 'le', 'gt', 'ge', 'interval']}, 'lower': {'type': ['number', 'null']}, 'upper': {'type': ['number', 'null']}})

def prediction_model_schema():
    return obj({'kind': {'enum': ['fixed_predictions_known_normal', 'fixed_predictions_estimated_normal', 'fixed_predictions_student_t']}, 'variance_interpretation': {'enum': ['known', 'estimated', 'unknown']}, 'support_refs': _strings()})

def assay_grading_input_schema():
    result = obj({'version': {'const': INPUT_VERSION}, 'assay_type': {'enum': list(ASSAY_TYPES)}, 'assertion_ref': {'type': 'string', 'minLength': 1}, 'quantity_kind': {'enum': list(dict.fromkeys((k for ks in QUANTITY_KINDS.values() for k in ks)))}, 'quantities': obj({role: {'anyOf': [operand_schema(), {'type': 'null'}]} for role in ROLES}, required=list(REQUIRED_ROLES)), 'interpretations': {'type': 'object', 'properties': {c: interpretation_schema() for c in CRITERIA}, 'additionalProperties': False}, 'prediction_model': {'anyOf': [prediction_model_schema(), {'type': 'null'}]}})
    result['allOf'] = [{'if': {'properties': {'assay_type': {'const': kind}}}, 'then': {'properties': {'quantity_kind': {'enum': list(quantities)}, 'interpretations': {'propertyNames': {'enum': list(CRITERIA_BY_TYPE[kind])}}}}} for kind, quantities in QUANTITY_KINDS.items()]
    return result

def assay_grading_cell_schema():
    result = obj({'component': {'enum': list(COMPONENTS)}, 'dimension': {'enum': ['measurement', 'reliability', 'validity', 'attribution', 'comparability', 'relevance', 'experimental_evidence']}, 'value': {'type': ['number', 'null']}, 'unit': {'type': 'string'}, 'status': {'enum': ['populated', 'conditional', 'bounded', 'unavailable']}, 'reasons': _strings(), 'formula': {'type': 'string'}, 'meaning': {'type': 'string'}, 'measurement_keys': _strings(), 'source_refs': _strings(), 'input_origins': {'type': 'array', 'items': {'enum': list(ORIGINS)}, 'uniqueItems': True}, 'conditions': _strings()})
    result['properties']['bound'] = bound_schema()
    return result

def assay_grading_sheet_schema():
    return obj({'version': {'const': VERSION}, 'axis': {'const': 'A105'}, 'evaluation_scope': {'const': EVALUATION_SCOPE}, 'assay_type': {'enum': list(ASSAY_TYPES)}, 'assertion_ref': {'type': 'string', 'minLength': 1}, 'quantity_kind': {'enum': list(dict.fromkeys((k for ks in QUANTITY_KINDS.values() for k in ks)))}, 'cells': obj({name: assay_grading_cell_schema() for name in COMPONENTS}), 'interpretations': assay_grading_input_schema()['properties']['interpretations'], 'prediction_model': {'anyOf': [prediction_model_schema(), {'type': 'null'}]}, 'annotation_credit': {'type': 'null'}})
DIMENSIONS = dict(zip(COMPONENTS, ('measurement', 'reliability', 'reliability', 'validity', 'attribution', 'comparability', 'relevance', 'relevance', 'experimental_evidence')))
FORMULAS = dict(zip(COMPONENTS, ('selected_native_effect', 'selected_variance_of_native_effect', '1/variance', 'recovery-1', 'attributed_signal/total_signal', 'condition_test/condition_reference', 'effect-assertion_prediction', 'effect-alternative_prediction', '((effect-alternative_prediction)^2-(effect-assertion_prediction)^2)/(2*variance)')))
MEANINGS = dict(zip(COMPONENTS, ('The selected native measurement or contrast, with its original functional resolution; not a quality score.', 'Variance of the selected estimate, including only uncertainty represented by the supplied source/model.', 'Inverse variance of that estimate on its native scale; not an assay success probability.', 'Measured recovery deviation from unity; a calibration diagnostic, not a universal validity grade.', 'Fraction of the selected total signal assigned to the studied molecular contribution by the supported attribution model.', 'Measured nuisance-condition test/reference response; comparability information, not an additional correction or penalty.', 'Signed difference between the selected estimate and the explicit prediction of the asserted function.', 'Signed difference between the selected estimate and the explicit prediction of the named alternative.', 'Signed log likelihood ratio for two fixed predictions under the declared measurement model, using the observed value or censoring event. Estimated-normal comparisons are plug-in approximations; Student-t comparisons use the explicitly selected residual model. Positive values support the assertion relative to that alternative; not annotation probability.')))

def _fail(reason):
    raise ContractError('assay_grading_' + reason)

def _unique(values):
    return list(dict.fromkeys(values))

def _uncertainty_qualification(text):
    lowered = text.lower()
    return any((word in lowered for word in ('unknown', 'unresolved', 'conflicting'))) or ('estimated' in lowered and any((word in lowered for word in ('variance', 'covariance'))))

def _quantity_unit_supported(kind, unit):
    dimensionless = {'fraction', 'dimensionless'}
    if kind in ('rate_ratio', 'conversion_fraction', 'conversion_difference', 'completion_time_ratio', 'product_fraction', 'product_fraction_ratio', 'equilibrium_fraction', 'equilibrium_ratio', 'productive_fraction', 'stoichiometric_ratio', 'kinetic_parameter_ratio', 'log_kinetic_parameter_ratio', 'partner_response_fraction', 'binding_parameter_ratio', 'log_binding_parameter_ratio', 'binding_discrimination_ratio', 'log_binding_discrimination', 'transport_rate_ratio', 'log_transport_rate_ratio', 'substrate_saturation', 'substrate_response_ratio', 'log_substrate_response', 'signal_ratio', 'signal_difference', 'log_signal_ratio', 'protein_amount_ratio', 'sites_per_monomer', 'active_fraction'):
        return unit in dimensionless
    if kind == 'band_display_fraction':
        return unit == 'display_fraction'
    if kind == 'band_display_darkness':
        return unit == 'display_darkness_sum'
    if kind in ('binding_parameter', 'transport_parameter'):
        return unit in {'M', 'mM', 'uM', 'nM'}
    if kind in ('kinetic_parameter', 'kinetic_parameter_difference'):
        return unit in {'M', 'mM', 'uM', 'nM', 'per_min', 'per_s', 's^-1', 'min^-1', 'U/mg', 'umol/min/mg', 'uM_inverse_min_inverse'}
    if kind == 'electrical_current':
        return unit in {'pA', 'nA', 'uA', 'A'}
    if kind == 'electrical_conductance':
        return unit in {'pS', 'nS', 'uS', 'S'}
    if kind == 'charge_equivalent_rate':
        return unit == 'elementary_charge_equivalents_per_s'
    if kind == 'completion_time':
        return unit in {'s', 'sec', 'min', 'h', 'hour'}
    if kind in ('endpoint_amount', 'balance_residual', 'accumulated_amount', 'protein_amount', 'protein_amount_difference'):
        return unit in {'M', 'mM', 'uM', 'nM', 'mol', 'mmol', 'umol', 'nmol', 'pmol', 'molecules', 'count', 'mg', 'ug', 'ng', 'mg/ml', 'mg/mL'}
    if kind in ('rate', 'rate_difference', 'partner_rate_difference', 'transport_rate'):
        return unit in {'U/mg', 'U/mL', 'uM/min', 'uM/s', 'mM/min', 'mM/s', 'nM/min', 'nM/s', 'mmol/min', 'umol/min', 'nmol/min', 'nmol/s', 'pmol/min', 'umol/min/mg', 'nmol/min/mg', 'pmol/min/mg', 'per_min', 'per_s', 's^-1', 'min^-1'}
    if kind == 'turnover':
        return unit in {'per_min', 'per_s', 's^-1', 'min^-1', '1/s', '1/min'}
    if kind == 'catalytic_efficiency':
        return unit in {'uM^-1min^-1', 'uM_inverse_min_inverse', 'M^-1s^-1', 'uM^-1s^-1', 'M^-1min^-1', 'mM^-1s^-1', 'mM^-1min^-1'}
    return False

def _required_criteria(assay_type, quantity_kind):
    required = list(CRITERIA_BY_TYPE[assay_type])
    optional = set()
    if assay_type == 'activity_rate':
        if quantity_kind not in ('turnover', 'catalytic_efficiency', 'kinetic_parameter', 'kinetic_parameter_difference', 'kinetic_parameter_ratio', 'log_kinetic_parameter_ratio'):
            optional.add('kinetic_model')
        if quantity_kind.startswith('kinetic_parameter') or quantity_kind == 'log_kinetic_parameter_ratio':
            optional.update(('rate_regime', 'normalization_basis'))
        if not quantity_kind.startswith('partner_'):
            optional.add('partner_perturbation')
    if assay_type == 'endpoint_conversion':
        optional.add('product_identity')
        if quantity_kind in ('endpoint_amount', 'completion_time', 'completion_time_ratio'):
            optional.add('conversion_denominator')
    if assay_type == 'product_distribution' and (not quantity_kind.startswith('equilibrium_')):
        optional.add('equilibrium_state')
    if assay_type == 'transport_response' and quantity_kind not in ('transport_parameter', 'substrate_saturation', 'substrate_response_ratio', 'log_substrate_response'):
        optional.add('transport_response_model')
    if assay_type == 'protein_amount' and quantity_kind not in ('sites_per_monomer', 'active_fraction'):
        optional.add('active_site_stoichiometry')
    if assay_type == 'ligand_binding' and quantity_kind == 'band_display_fraction':
        optional.add('binding_parameter_definition')
    return (required, optional)

def _validate_bound(operand):
    from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.assay_evidence import _finite
    bound = operand.get('bound')
    if bound is None:
        return
    if operand['status'] != 'bounded' or operand['value'] is not None:
        _fail('bound_operand_inconsistent')
    lower, upper = (bound['lower'], bound['upper'])
    if any((value is not None and (not _finite(value)) for value in (lower, upper))):
        _fail('finite_bound_required')
    relation = bound['relation']
    if relation in ('lt', 'le') and (lower is not None or upper is None) or (relation in ('gt', 'ge') and (lower is None or upper is not None)) or (relation == 'interval' and (lower is None or upper is None or lower >= upper)):
        _fail('bound_limits_inconsistent')
    if not operand['measurement_keys']:
        _fail('operand_identity_required')

def grade_assay(extraction):
    """Convert native reader outputs into one common numerical A105 assessment.

    The variance must describe the exact selected effect, including whatever
    corrections were already applied upstream. None of recovery, attribution,
    or condition response is multiplied into that effect a second time.
    Scientific interpretations determine which uses are warranted; they are
    never turned into categorical numerical quality weights.
    """
    from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.assay_evidence import grade_experimental_measurement
    return grade_experimental_measurement(extraction, input_schema=assay_grading_input_schema(), sheet_schema=assay_grading_sheet_schema(), required_criteria=_required_criteria, quantity_unit_supported=_quantity_unit_supported, version=VERSION, axis='A105', evaluation_scope=EVALUATION_SCOPE)
__all__ = ['INPUT_VERSION', 'VERSION', 'EVALUATION_SCOPE', 'ASSAY_TYPES', 'QUANTITY_KINDS', 'ROLES', 'COMPONENTS', 'COMMON_CRITERIA', 'CRITERIA_BY_TYPE', 'CRITERIA', 'CRITERION_QUESTIONS', 'assay_grading_input_schema', 'assay_grading_sheet_schema', 'assay_grading_cell_schema', 'operand_schema', 'bound_schema', 'interpretation_schema', 'prediction_model_schema', 'grade_assay']
