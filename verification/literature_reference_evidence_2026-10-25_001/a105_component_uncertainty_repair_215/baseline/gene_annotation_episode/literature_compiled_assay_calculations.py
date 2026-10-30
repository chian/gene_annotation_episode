"""Within-assay combination of authorized saved quantities, not a quality grade.

The existing activity calculator supplies the full correction and conditional
uncertainty model. This wrapper preserves supported partial normalizations,
scientific applicability, correction stages and shared input dependencies.
"""
from copy import deepcopy
from fractions import Fraction
import math

from .domain import identity
from .literature_activity_calculations import populate_corrected_activity
from .literature_compiled_assay_inputs import ROLES, UNITS, LINKS
from .literature_experimental_contracts import ExperimentalContractError

VERSION = 'a105_compiled_assay_sheet_v1'
PRIMITIVES = dict(q='net_rate', g='contaminant_rate', k='recovery', E='protein_amount',
                  u='condition_test_rate', v='condition_reference_rate')
COMPONENTS = (*PRIMITIVES.values(), 'attributed_rate', 'condition_response',
    'measured_endpoint_per_selected_amount', 'calibrated_measured_endpoint_per_selected_amount',
    'corrected_activity', 'effect_variance', 'effect_standard_uncertainty', 'effect_precision',
    'source_profile_log_ratio', 'source_presence_index')
FORMULAS = {**{name: 'selected_source_' + role for role, name in PRIMITIVES.items()},
    'attributed_rate': 'q-g', 'condition_response': 'u/v',
    'measured_endpoint_per_selected_amount': 'q/E',
    'calibrated_measured_endpoint_per_selected_amount': 'q/(k*E)',
    'corrected_activity': '(q-g)*v/(k*E*u)',
    'effect_variance': 'J*covariance*J_transpose+distinct_residual_variance',
    'effect_standard_uncertainty': 'sqrt(effect_variance)', 'effect_precision': '1/effect_variance',
    'source_profile_log_ratio': 'max(0,corrected_activity)^2/(2*effect_variance)',
    'source_presence_index': 'tanh(source_profile_log_ratio/2)'}
SECTIONS = {name: 'measurement' for name in PRIMITIVES.values()}
SECTIONS.update(recovery='validity', protein_amount='amount_normalization',
    condition_test_rate='comparability', condition_reference_rate='comparability',
    attributed_rate='attribution', condition_response='comparability',
    measured_endpoint_per_selected_amount='amount_normalization',
    calibrated_measured_endpoint_per_selected_amount='calibration_and_amount_normalization',
    corrected_activity='compiled_source_endpoint_effect',
    **{name: 'uncertainty' for name in COMPONENTS[-5:]})
DEPENDENCIES = {**{name: (role,) for role, name in PRIMITIVES.items()},
    'attributed_rate': ('q', 'g'), 'condition_response': ('u', 'v'),
    'measured_endpoint_per_selected_amount': ('q', 'E'),
    'calibrated_measured_endpoint_per_selected_amount': ('q', 'k', 'E'),
    **{name: ROLES for name in COMPONENTS[10:]}}
MEANINGS = {name: 'Selected source quantity; scientific eligibility for combination is separate.' for name in PRIMITIVES.values()}
MEANINGS.update(attributed_rate='Endpoint rate after the additional supported contaminant subtraction only.',
    condition_response='Applicable nuisance-condition test/reference response, excluding the intended change.',
    measured_endpoint_per_selected_amount='Measured endpoint rate per selected molecular amount; not contaminant-isolated or nuisance-corrected.',
    calibrated_measured_endpoint_per_selected_amount='Reporter-calibrated measured endpoint per selected molecular amount; not contaminant-isolated or nuisance-corrected.',
    corrected_activity='Compiled source-endpoint activity under the selected calibration, amount, attribution and nuisance-control meanings.',
    effect_variance='Conditional first-order propagated effect variance plus the selected distinct residual variance.',
    effect_standard_uncertainty='Square root of conditional effect variance, not an inferred confidence interval.',
    effect_precision='Reciprocal conditional effect variance; dependent on the same source measurements.',
    source_profile_log_ratio='Existing conditional known-normal nonnegative-presence profile; not a probability of function.',
    source_presence_index='Existing proposed bounded transform of that conditional profile; not annotation credit.')


def _float(value):
    try:
        result = float(value)
        return result if math.isfinite(result) and (result != 0 or value == 0) else None
    except (OverflowError, ValueError):
        return None


def _cell(name, value, unit, *, reason=None, formula=None, origin='derived', conditional=(), qualifiers=()):
    if value is not None and reason is None:
        value = _float(value)
        if value is None:
            reason = 'numerical_model_range'
    if reason is not None:
        value = None
    return {'value': value, 'unit': unit, 'status': 'unavailable' if value is None else 'populated',
        'unavailable_reason': reason, 'formula': formula or FORMULAS[name], 'origin': origin,
        'section': SECTIONS[name], 'meaning': MEANINGS[name], 'conditional_on': list(conditional),
        'qualifications': list(qualifiers)}


def _role_reason(extraction, role):
    operand = extraction['operands'][role]
    if operand is None:
        return 'operand_not_selected'
    if operand['unavailable_reason']:
        return operand['unavailable_reason']
    relation = extraction['relationships'][role]['value']
    if relation not in LINKS[role]:
        return 'operand_relationship_' + relation
    if role == 'E' and operand['selection']['namespace'] == 'literature_active_site_cells':
        wanted = 'same_assay_active_molecules' if operand['selection']['component'] == 'active_site_concentration' else 'same_assay_total_molecules'
        if relation != wanted:
            return 'amount_basis_relationship_mismatch'
    if role in ('k', 'E', 'u', 'v') and operand['value'] is not None and operand['value'] <= 0:
        return 'positive_normalization_operand_required'
    return None


def _stage_reason(stages, name, wanted):
    value = stages[name]['value']
    return None if value == wanted else name + '_stage_' + value


def _matrix(extraction, values):
    source = extraction['covariance_source']
    if source is None:
        return None
    raw = source['data']['covariance']
    if not isinstance(raw, list) or len(raw) != 6 or any(not isinstance(row, list) or len(row) != 6 for row in raw):
        raise ExperimentalContractError('six_by_six_covariance_required', 'covariance')
    for row in raw:
        for value in row:
            try:
                valid = type(value) in (int, float) and math.isfinite(value)
            except OverflowError:
                valid = False
            if not valid:
                raise ExperimentalContractError('finite_number_required', 'covariance')
    owners = [extraction['operands'][role]['quantity_key'] for role in ROLES]
    for i in range(6):
        for j in range(i):
            if owners[i] == owners[j]:
                if UNITS[ROLES[i]] != UNITS[ROLES[j]] or values[ROLES[i]] != values[ROLES[j]]:
                    raise ExperimentalContractError('shared_compilation_quantity_mismatch', 'covariance')
                if raw[i] != raw[j] or any(row[i] != row[j] for row in raw):
                    raise ExperimentalContractError('shared_measurement_covariance_mismatch', 'covariance')
    return deepcopy(raw)


def populate_compiled_assay(extraction):
    """Combine only physically eligible source operands, preserving partials."""
    operands = extraction['operands']; stages = extraction['correction_stages']
    reasons = {role: _role_reason(extraction, role) for role in ROLES}
    values = {role: None if operands[role] is None else operands[role]['value'] for role in ROLES}
    cells = {}
    for role, name in PRIMITIVES.items():
        operand = operands[role]
        cells[name] = _cell(name, values[role], operand['unit'] if operand else UNITS[role],
            reason='operand_not_selected' if operand is None else operand['unavailable_reason'] if values[role] is None else None,
            origin=operand['row'].get('origin', 'derived') if operand else 'derived',
            qualifiers=() if reasons[role] is None else (reasons[role],))
    # Sample-minus-blank is the meaning of q. This operation does not read or
    # subtract an additional blank from a gross signal.
    q_reason = reasons['q'] or _stage_reason(stages, 'background', 'already_applied')
    raw_normalized = operands['q'] is not None and operands['q']['native_normalized']
    amount_applied = stages['molecule_amount']['value'] == 'already_applied'
    identities = {}
    effective = {role: values[role] if reasons[role] is None else None for role in ROLES}
    effective_reasons = dict(reasons); effective_reasons['q'] = q_reason
    if q_reason:
        effective['q'] = None
    for stage, role_values in (('contaminant', {'g': 0}), ('recovery', {'k': 1}),
                               ('nuisance_condition', {'u': 1, 'v': 1})):
        state = stages[stage]['value']
        if state == 'already_applied':
            for role, value in role_values.items():
                effective[role], effective_reasons[role] = value, None
                identities[role] = {'stage': stage, 'value': value,
                    'meaning': 'algebraic_identity_of_already_applied_correction_not_a_measurement'}
        elif state != 'not_applied':
            for role in role_values:
                effective[role], effective_reasons[role] = None, stage + '_stage_' + state
    if not amount_applied:
        er = _stage_reason(stages, 'molecule_amount', 'not_applied')
        if er:
            effective['E'], effective_reasons['E'] = None, er
    if raw_normalized:
        # Preserve native turnover/specific activity rather than forging a
        # concentration-rate q or a one-micromolar denominator.
        effective['q'] = None
        effective_reasons['q'] = 'already_amount_normalized_native_rate'
    elif amount_applied:
        effective['E'], effective_reasons['E'] = None, 'normalization_stage_unit_conflict'

    def reason_for(roles):
        return next((effective_reasons[role] for role in roles if effective_reasons[role]), None)
    attributed_reason = reason_for(('q', 'g'))
    attributed = None if attributed_reason else Fraction(str(effective['q']))-Fraction(str(effective['g']))
    cells['attributed_rate'] = _cell('attributed_rate', attributed, 'uM/min', reason=attributed_reason,
        formula='q_after_already_applied_contaminant_correction' if 'g' in identities else None)
    response_reason = reason_for(('u', 'v'))
    response = None if response_reason else Fraction(str(effective['u']))/Fraction(str(effective['v']))
    cells['condition_response'] = _cell('condition_response', response, 'dimensionless', reason=response_reason,
        formula='identity_of_already_applied_nuisance_correction' if 'u' in identities else None,
        origin='definition_identity' if 'u' in identities else 'derived')

    for name, roles in (('measured_endpoint_per_selected_amount', ('q', 'E')),
                        ('calibrated_measured_endpoint_per_selected_amount', ('q', 'k', 'E'))):
        why = reason_for(roles)
        value = None
        formula = None
        if raw_normalized and amount_applied and q_reason is None:
            if name == 'measured_endpoint_per_selected_amount':
                value, why, formula = values['q'], None, 'source_already_amount_normalized_value'
            elif stages['recovery']['value'] == 'already_applied':
                value, why, formula = values['q'], None, 'source_already_calibrated_amount_normalized_value'
            else:
                why = 'additional_correction_of_normalized_rate_unimplemented'
        elif why is None:
            denominator = Fraction(str(effective['E']))
            if 'k' in roles:
                denominator *= Fraction(str(effective['k']))
            value = Fraction(str(effective['q']))/denominator
        cells[name] = _cell(name, value, 'per_min', reason=why, formula=formula,
            qualifiers=('source_already_contaminant_corrected' if stages['contaminant']['value'] == 'already_applied' else 'not_contaminant_isolated',
                        'source_already_nuisance_corrected' if stages['nuisance_condition']['value'] == 'already_applied' else 'not_nuisance_corrected'))

    matrix = _matrix(extraction, values)
    variance_reason = None
    if identities and matrix is not None:
        matrix = None
        variance_reason = 'covariance_for_bypassed_correction_stages_unimplemented'
    if extraction['variance_status'] == 'unknown' and matrix is not None:
        matrix = None
        variance_reason = 'covariance_status_unknown'
    residual = extraction['distinct_residual_observation']
    residual_value = residual['value'] if residual and extraction['residual_relationship']['value'] == 'additional_corrected_scale_variance' else None
    if residual and residual_value is None:
        variance_reason = variance_reason or 'residual_variance_relationship_' + extraction['residual_relationship']['value']
    full_reason = reason_for(ROLES)
    if raw_normalized and amount_applied and q_reason is None and all(
            stages[name]['value'] == 'already_applied' for name in ('contaminant', 'recovery', 'nuisance_condition')):
        full_reason = None
        native_result = True
    else:
        native_result = False
    scope = extraction['assay']['endpoint']['value']
    if scope in ('growth', 'abundance', 'ligand_binding', 'other_measured_endpoint'):
        full_reason = 'endpoint_requires_different_model'
    calculation = populate_corrected_activity({'values': effective, 'covariance': matrix,
        'variance_status': extraction['variance_status'], 'distinct_residual_variance': residual_value,
        'observation_model': extraction['observation_model']})
    for name, cell in calculation['cells'].items():
        why = full_reason or cell['unavailable_reason']
        if name != 'corrected_activity' and variance_reason and full_reason is None:
            why = variance_reason
        value = cell['value']
        formula = cell['formula']
        if native_result and scope not in ('growth', 'abundance', 'ligand_binding', 'other_measured_endpoint'):
            if name == 'corrected_activity':
                value, why, formula = values['q'], None, 'source_already_corrected_amount_normalized_value'
            else:
                why = 'normalized_native_uncertainty_not_selected'
        if name in ('source_profile_log_ratio', 'source_presence_index') and (
                extraction['assay']['molecule'] is None or scope in ('unknown', 'conflicting')):
            why = 'source_scientific_scope_unresolved'
        cells[name] = _cell(name, value, cell['unit'], reason=why, formula=formula,
            origin=cell['origin'], conditional=cell['conditional_on'])
    dependencies = {}
    for name in COMPONENTS:
        selected = []
        for role in DEPENDENCIES[name]:
            if role in identities and name not in PRIMITIVES.values():
                selected.append({'role': role, 'selection': None, 'component_key': None, 'quantity_key': None,
                    'canonical_physical_keys': [], 'recorded_dependency_keys': [],
                    'physical_identity_status': 'definition_identity', 'identity_stage': identities[role]['stage']})
            elif operands[role] is not None:
                source = operands[role]
                selected.append({'role': role, **{field: deepcopy(source[field]) for field in (
                    'selection', 'component_key', 'quantity_key', 'canonical_physical_keys', 'recorded_dependency_keys', 'physical_identity_status')},
                    'identity_stage': None})
        dependencies[name] = selected
    return {'version': VERSION, 'axis': 'A105', 'scope': 'compiled_source_endpoint',
        'cells': cells, 'dependencies': dependencies, 'operand_eligibility_reasons': reasons,
        'effective_operand_reasons': effective_reasons, 'algebraic_stage_identities': identities,
        'effective_values': effective, 'original_extraction': deepcopy(extraction),
        'variance_status': extraction['variance_status'], 'observation_model': extraction['observation_model'],
        'annotation_credit': None, 'universal_reliability_grade': None,
        'remaining_implementation_limits': ['no_cross_assay_grand_score',
            'bounded_operand_combination_unimplemented', 'partial_normalization_uncertainty_unimplemented',
            'covariance_for_bypassed_correction_stages_unimplemented', 'no_target_correspondence_or_annotation_credit']}

# Finite interpretation/failure codes are distinct from original source literals.
REASONS = tuple(sorted({
    'operand_not_selected', 'selected_component_unavailable', 'approximate_operand_requires_unimplemented_compilation',
    'bounded_operand_compilation_unimplemented', 'operand_unit_incompatible_with_compilation', 'numerical_model_range',
    'enzyme_activity_spike_is_not_reporter_recovery', 'reporter_recovery_meaning_unknown', 'reporter_recovery_meaning_conflicting',
    'recovery_control_scope_unavailable', 'active_sites_to_molecules_not_established', 'molar_amount_basis_not_established',
    'amount_correction_already_applied', 'amount_basis_relationship_mismatch', 'endpoint_requires_different_model', 'positive_normalization_operand_required',
    'already_amount_normalized_native_rate', 'normalization_stage_unit_conflict',
    'additional_correction_of_normalized_rate_unimplemented', 'covariance_for_bypassed_correction_stages_unimplemented',
    'covariance_status_unknown', 'normalized_native_uncertainty_not_selected', 'source_scientific_scope_unresolved',
    'correction_inputs_not_supplied', 'primitive_covariance_not_supplied', 'distinct_residual_variance_not_supplied',
    'invalid_propagated_variance', 'positive_effect_variance_required', 'known_variance_required', 'observation_model_unspecified',
    *('operand_relationship_' + state for state in ('different_assay_or_endpoint', 'unknown', 'conflicting')),
    *('recovery_applicability_' + state for state in ('different_matrix_or_endpoint', 'unknown', 'conflicting')),
    *('active_amount_linkage_' + state for state in ('different', 'unknown', 'conflicting')),
    *(stage + '_stage_' + state for stage in ('background', 'contaminant', 'recovery', 'molecule_amount', 'nuisance_condition')
      for state in ('not_applied', 'already_applied', 'unknown', 'conflicting')),
    *('residual_variance_relationship_' + state for state in ('different_or_already_included', 'unknown', 'conflicting')),
}))
FORMULA_VARIANTS = tuple(dict.fromkeys((*FORMULAS.values(),
    'q_after_already_applied_contaminant_correction', 'identity_of_already_applied_nuisance_correction',
    'source_already_amount_normalized_value', 'source_already_calibrated_amount_normalized_value',
    'source_already_corrected_amount_normalized_value')))
QUALIFICATIONS = (*REASONS, 'not_contaminant_isolated', 'not_nuisance_corrected',
                  'source_already_contaminant_corrected', 'source_already_nuisance_corrected')
