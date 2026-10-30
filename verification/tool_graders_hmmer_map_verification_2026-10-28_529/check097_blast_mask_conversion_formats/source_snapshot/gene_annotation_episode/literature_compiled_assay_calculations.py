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
VERSION_V2 = 'a105_compiled_assay_sheet_v2'
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
    if extraction['version'] == 'a105_compiled_assay_inputs_v2':
        return _populate_v2(extraction)
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

PROPAGATED_ESTIMANDS = {
    'measured_endpoint_per_selected_amount': ('q', 'E'),
    'calibrated_measured_endpoint_per_selected_amount': ('q', 'k', 'E'),
    'corrected_activity': ROLES,
}
PROPAGATED_COMPONENTS = tuple(estimand + suffix for estimand in PROPAGATED_ESTIMANDS
    for suffix in ('_propagated_variance', '_propagated_standard_uncertainty'))
COMPONENTS_V2 = (*COMPONENTS, *PROPAGATED_COMPONENTS)
MEANINGS_V2 = {**MEANINGS, **{estimand + suffix:
    ('First-order variance propagated from the actual joint operands of ' if suffix == '_propagated_variance'
     else 'Square root of the first-order propagated variance of ') + estimand
    + '; excludes distinct residual variability and uncertainty of other estimands.'
    for estimand in PROPAGATED_ESTIMANDS for suffix in ('_propagated_variance', '_propagated_standard_uncertainty')}}
FORMULAS_V2 = {**FORMULAS, **{estimand + suffix:
    ('J_' + estimand + '*selected_joint_covariance*J_' + estimand + '_transpose'
     if suffix == '_propagated_variance' else 'sqrt(' + estimand + '_propagated_variance)')
    for estimand in PROPAGATED_ESTIMANDS for suffix in ('_propagated_variance', '_propagated_standard_uncertainty')}}
SECTIONS_V2 = {**SECTIONS, **dict.fromkeys(PROPAGATED_COMPONENTS, 'uncertainty')}
REASONS_V2 = (*REASONS, 'component_covariance_unreported', 'component_joint_covariance_not_supplied',
    'component_covariance_status_unknown')


def _block_for(extraction, roles):
    blocks = extraction['covariance_sources']
    if not blocks:
        return None, 'component_covariance_unreported'
    for block in blocks:
        if set(roles) <= set(block['data']['primitive_order']):
            if block['data']['variance_status'] == 'unknown':
                return block, 'component_covariance_status_unknown'
            return block, None
    return None, 'component_joint_covariance_not_supplied'


def _uncertainty_metadata(estimand=None, block=None, roles=(), *, scope='not_applicable', status='unknown'):
    data = block['data'] if block else None
    return {'estimand_component': estimand, 'scope': scope,
        'covariance_source_ref': block['source_ref'] if block else None,
        'source_primitive_order': deepcopy(data['primitive_order']) if data else [],
        'operand_order': list(roles),
        'operand_keys': [data['operand_keys'][data['primitive_order'].index(role)] for role in roles] if data else [],
        'variance_status': data['variance_status'] if data else status,
        'covariance_origin': data['origin'] if data else None,
        'propagation_model': 'first_order_covariance_propagation' if estimand else 'none'}


def _populate_v2(extraction):
    """Versioned same-sheet extension; no completion of missing joint blocks."""
    full_block, full_cov_reason = _block_for(extraction, ROLES)
    legacy = deepcopy(extraction)
    legacy['version'] = 'a105_compiled_assay_inputs_v1'
    legacy.pop('covariance_sources')
    legacy['covariance_source'] = None
    if full_block and not full_cov_reason:
        legacy['covariance_source'] = deepcopy(full_block)
        data = legacy['covariance_source']['data']
        order = data['primitive_order']
        data['covariance'] = [[data['covariance'][order.index(a)][order.index(b)] for b in ROLES] for a in ROLES]
        # The v1 arithmetic wrapper only consumes the matrix after its reader
        # has checked ownership. V2 has already validated the actual named block.
        legacy['variance_status'] = ('unknown' if extraction['variance_status'] == 'unknown'
            else 'estimated' if 'estimated' in (data['variance_status'], extraction['variance_status']) else 'known')
    sheet = populate_compiled_assay(legacy)
    sheet.update(version=VERSION_V2, original_extraction=deepcopy(extraction))
    sheet['uncertainty'] = {name: _uncertainty_metadata() for name in COMPONENTS}
    for estimand, roles in PROPAGATED_ESTIMANDS.items():
        mean = sheet['cells'][estimand]
        block, why = _block_for(extraction, roles)
        why = mean['unavailable_reason'] or why
        if any(role in sheet['algebraic_stage_identities'] for role in roles):
            why = 'covariance_for_bypassed_correction_stages_unimplemented'
        if extraction['operands']['q'] is not None and extraction['operands']['q']['native_normalized']:
            why = 'normalized_native_uncertainty_not_selected'
        propagated = None
        if why is None:
            values = {role: Fraction(str(sheet['effective_values'][role])) for role in roles}
            q, amount = values['q'], values['E']
            if roles == ('q', 'E'):
                gradient = (1 / amount, -q / amount**2)
            elif roles == ('q', 'k', 'E'):
                k = values['k']
                gradient = (1 / (k * amount), -q / (k**2 * amount), -q / (k * amount**2))
            else:
                g, k, u, v = (values[r] for r in ('g', 'k', 'u', 'v'))
                a = (q - g) * v / (k * amount * u)
                factor = v / (k * amount * u)
                gradient = (factor, -factor, -a/k, -a/amount, -a/u, a/v)
            data = block['data']; order = data['primitive_order']
            propagated = sum(gradient[i] * Fraction(str(data['covariance'][order.index(a)][order.index(b)])) * gradient[j]
                for i, a in enumerate(roles) for j, b in enumerate(roles))
            if propagated < 0:
                propagated, why = None, 'invalid_propagated_variance'
        variance_name = estimand + '_propagated_variance'
        variance = _cell(estimand, propagated, 'per_min_squared', reason=why,
            formula=FORMULAS_V2[variance_name], conditional=('first_order_covariance_propagation',))
        for suffix, unit, value in (('_propagated_variance', 'per_min_squared', variance['value']),
                ('_propagated_standard_uncertainty', 'per_min', math.sqrt(variance['value']) if variance['value'] is not None else None)):
            name = estimand + suffix
            cell = _cell(estimand, value, unit, reason=variance['unavailable_reason'],
                formula=FORMULAS_V2[name], conditional=('first_order_covariance_propagation',))
            cell.update(section='uncertainty', meaning=MEANINGS_V2[name], qualifications=deepcopy(mean['qualifications']))
            sheet['cells'][name] = cell
            sheet['dependencies'][name] = deepcopy(sheet['dependencies'][estimand])
            sheet['uncertainty'][name] = _uncertainty_metadata(estimand, block, roles, scope='operand_propagated')
    # The legacy total/profile still require the distinct residual and supported
    # full model. A smaller component covariance cannot supply those quantities.
    for name in COMPONENTS[11:]:
        sheet['uncertainty'][name] = _uncertainty_metadata('corrected_activity', full_block, ROLES if full_block else (), scope='total_with_distinct_residual')
        if full_cov_reason and sheet['cells']['corrected_activity']['status'] == 'populated':
            sheet['cells'][name].update(value=None, status='unavailable', unavailable_reason=full_cov_reason)
    sheet['remaining_implementation_limits'] = [limit for limit in sheet['remaining_implementation_limits']
        if limit != 'partial_normalization_uncertainty_unimplemented']
    sheet['remaining_implementation_limits'].append('normalized_native_uncertainty_not_selected')
    return sheet

# Pure common scientific assessment, not yet bound to a selected operation.
COMMON_SHEET = 'a105_common_assessment_sheet_v1'
_COMMON_FORMULAS = {
    'product_reference_contrast':'P_test/P_reference',
    'reporter_reference_contrast':'H_test/H_reference',
    'productive_use_reference_contrast':'(P_test/H_test)/(P_reference/H_reference)',
    'saturation_turnover_reference_contrast':'kcat_test/kcat_reference',
    'low_substrate_efficiency_reference_contrast':'(kcat_test/Km_test)/(kcat_reference/Km_reference)',
    'occupancy_reference':'S_reference/(S_reference+Kd_reference)',
    'occupancy_test':'S_test/(S_test+Kd_test)',
    'occupancy_reference_contrast':'theta_test/theta_reference',
    'binding_only_prediction_error':'P_test/P_reference-theta_test/theta_reference',
    'post_binding_residual_ratio':'(P_test/P_reference)/(theta_test/theta_reference)',
    'binding_only_log_residual':'ln(P_test/P_reference)-ln(theta_test/theta_reference)',
    'binding_only_residual_variance':'J_D*joint_selected_estimate_covariance*J_D_transpose',
    'binding_only_standardized_residual':'D/sqrt(variance_D)',
    'binding_only_squared_standardized_residual':'D^2/variance_D',
    'fully_corrected_activity_reference_contrast':'((Pt-Bt)/(Pr-Br))*(kr/kt)*(fr/ft)*(cr/ct)*(theta_r/theta_t)',
}
_COMMON_MEANINGS = dict(zip(_COMMON_FORMULAS, (
    'Descriptive contrast of the selected identified-product endpoint, not molecular effect isolation.',
    'Descriptive reporter-turnover contrast; reporter consumption alone does not establish product formation.',
    'Relative productive use of the selected reporter; reuses both product and reporter measurements.',
    'Relative fitted saturation turnover of the selected constructs under their stated protocols.',
    'Relative low-substrate efficiency under the selected kinetic interpretation; not an observed physiological rate.',
    'Reference occupancy under the declared one-site/free-substrate model.',
    'Test occupancy under the declared one-site/free-substrate model.',
    'Relative occupancy under the declared binding model, not relative catalytic activity.',
    'Signed discrepancy between product contrast and the occupancy-only alternative.',
    'Relative activity remaining after the modeled occupancy difference; its cause is not identified.',
    'Log discrepancy with the occupancy-only alternative; not a causal fraction or function probability.',
    'First-order variance of that log discrepancy, using the actual joint selected-estimate owners.',
    'Signed standardized discrepancy under the declared uncertainty model; no reference distribution assumed.',
    'Squared standardized discrepancy under the same model; not a p-value or independent contribution.',
    'Relative post-binding activity under the declared multiplicative response model with actual applicable background, recovery, active-fraction and nuisance operands.',
)))
_COMMON_NATIVE_ROLES = tuple(base+'_'+arm for base in ('product','reporter','kcat','Km','Kd','free_substrate','background','recovery','active_fraction','nuisance_response') for arm in ('reference','test'))
COMMON_COMPONENTS = (*('estimate_'+role for role in _COMMON_NATIVE_ROLES), *_COMMON_FORMULAS)


def common_assessment_sheet_schema():
    """Closed numerical section and scoped context; raw input custody is separate."""
    from .domain import obj, REF
    from .literature_compiled_assay_inputs import (_common_array, _common_exact_schema,
        _common_location_schema, _nullable, COMMON_REASONS, COMMON_ROLES, COMMON_GROUPS, COMMON_LINKS, COMMON_MODEL_STATUSES, COMMON_ASSUMPTIONS)
    cell=obj({'component':{'enum':list(COMMON_COMPONENTS)},'value':{'type':['number','null']},
        'exact_value':_nullable(_common_exact_schema()),'conditional_value':{'type':['number','null']},
        'conditional_exact_value':_nullable(_common_exact_schema()),'unit':{'type':['string','null']},
        'status':{'enum':['populated','conditional_scenario','unavailable']},
        'formula':{'enum':['selected_native_estimate',*_COMMON_FORMULAS.values()]},
        'meaning':{'enum':['Native selected source report; qualified nondetection is not exact physical absence.',*_COMMON_MEANINGS.values()]},'origin':{'enum':['reported','derived','calculated','synthetic','proposed']},
        'input_origins':_common_array({'enum':['reported','derived','calculated','synthetic','proposed']},True),
        'source_missing_reasons':_common_array({'enum':list(COMMON_REASONS)},True),
        'relationship_reasons':_common_array({'enum':list(COMMON_REASONS)},True),
        'implementation_reasons':_common_array({'enum':list(COMMON_REASONS)},True),
        'operand_roles':_common_array({'enum':list(COMMON_ROLES)},True),
        'operand_keys':_common_array({'type':'string'},True),'model_keys':_common_array({'type':'string'},True),
        'contribution_key':{'type':'string'},'native_semantics':{'enum':['reported_point','reported_nondetection','reported_negligible','unknown','conflicting',None]},
        'numeric_origin':{'enum':['received_exact_component','original_source_token','saved_canonical_decimal','derived']},
        'reported_uncertainty':_nullable(obj({'exact_magnitude':_nullable(_common_exact_schema()),
            'unit':{'type':['string','null']},'statistic':{'enum':['sd','sem','unspecified']},
            'meaning':{'const':'source_reported_spread_not_joint_estimate_covariance'}})),
        'uncertainty':obj({'scope':{'enum':['not_applicable','log_residual_operand_propagation']},
            'variance_status':{'enum':['not_selected','known','estimated','unknown']},
            'covariance_source_ref':_nullable(REF),'basis':{'enum':['joint_covariance_of_selected_estimates',None]},
            'model':{'enum':['none','first_order_covariance_propagation']}})})
    context=obj({'field':{'type':'string'},'location':_common_location_schema(),'display_text':{'type':'string'},
        'implementation_status':{'enum':['scoped','unrequested_numbers_withheld','numerical_scope_unresolved']},
        'implementation_reason':{'enum':['unrequested_numerical_scope_unresolved',None]}})
    return obj({'version':{'const':COMMON_SHEET},'axis':{'const':'A105'},
        'evaluation_scope':{'const':'common_assertion_contrast'},'cells':_common_array(cell),
        'context':_common_array(context),'numerical_scope_implementation_status':{'enum':['scoped','partial_unresolved']},
        'host_custody':obj({'source_refs':_common_array(REF,True), 'source_artifacts':_common_array(obj({
            'source_ref':REF,'representation':{'enum':['original','text']},'artifact_ref':REF})),
            'withheld_locations':_common_array(_common_location_schema())}),
        'assertion_resolution':{'enum':['identified_product_formation','saturation_turnover','low_substrate_efficiency','binding_occupancy_alternative']},
        'question':{'enum':['existence','relative_effect','named_alternative']},
        'dependence':_common_array(obj({'roles':_common_array({'enum':list(COMMON_ROLES)}),
            'relation':{'enum':['shared_primitive','sampling_unknown','shared_units','paired_units_supported','independent_units_supported','conflicting','complementary_endpoint']}})),
        'relationship_meanings':obj({'subject':{'enum':['same_construct_supported','intended_variant','different','unknown','conflicting']},
            'product_reporter':{'enum':['author_assigned_pair','different','unknown','conflicting']},
            'sampling':{'enum':['shared_units','paired_units_supported','independent_units_supported','unknown','conflicting']},
            'groups':obj({group:obj({name:{'enum':list(COMMON_LINKS)} for name in ('endpoint','normalization','preparation','conditions')}) for group in COMMON_GROUPS}),
            'correction_factorization':{'enum':list(COMMON_MODEL_STATUSES)},
            'model_assumptions':_nullable(obj({name:{'enum':list(COMMON_MODEL_STATUSES)} for name in COMMON_ASSUMPTIONS}))}),
        'model_meanings':_nullable(obj({'kind':{'const':'one_site_equilibrium'},
            'scope':{'enum':['supported_physical','conditional_sensitivity']},
            'substrate_ownership':{'enum':['shared_owner','separate_owners']},
            'substrate_uncertainty':{'enum':['fixed_scenario','selected_estimate_covariance']}})),
        'estimate_bindings':_common_array(obj({'role':{'enum':list(COMMON_ROLES)},'owner_key':{'type':'string'},
            'physical_owner_key':{'type':['string','null']},'population_key':{'type':['string','null']},'assay_key':{'type':['string','null']},
            'unit':{'type':['string','null']},'numeric_origin':{'enum':['received_exact_component','original_source_token','saved_canonical_decimal']}})),
        'annotation_credit':{'type':'null'},'remaining_implementation_limits':_common_array({'enum':[
            'selected_path_binding_is_host_responsibility','general_quality_compilation_unfinished',
            'same_estimand_contradiction_compilation_unfinished','no_target_correspondence_or_final_credit']})})


def _common_scoped_context(extraction):
    """Coordinates mask selected numeric owners; broad other numbers stay withheld.

    This deliberately exposes a partial implementation-scope state rather than
    calling scientific content absent. The original request/witnesses are kept
    in the separately saved inputs, never rewritten into a new source quote.
    """
    import re
    from .literature_product_coupling_storage import _meaning
    result=[];locations=extraction['numerical_scope_locations']
    def visit(value,path):
        if isinstance(value,dict):
            if set(value)=={'source_ref','representation','start','end','quote'}:
                artifacts=[v['artifact_ref'] for v in extraction['source_artifacts']
                    if (v['source_ref'],v['representation'])==(value['source_ref'],value['representation'])]
                if not artifacts: return
                # Separately selected bounded semantic names preserve chemical
                # locants beyond218's case-specific camphor grammar. Broad prose
                # still takes the numerical-scope guard, never this name path.
                name_field=path.rsplit('.',1)[-1] in ('molecule','construct','substrate','product_or_ligand','endpoint')
                token=value['quote'].strip()
                # Bounded supported name families, not a universal chemical or
                # identifier parser. Other digit-bearing text remains subject
                # to statistical guards and explicit partial scope.
                variant=re.fullmatch(r'[A-Z][0-9]+[A-Z](?:/[A-Z][0-9]+[A-Z])*',token)
                chemical=re.fullmatch(r'[0-9]+(?:,[0-9]+)*-(?:(?:exo|endo|cis|trans|R|S)-)?'
                    r'(?:(?:methyl|hydroxy|oxo|amino|deoxy)-?)(?:camphor|uridine)',token,re.I)
                semantic_name=bool(name_field and (variant or chemical or token=='P450cam'))
                shown=_meaning({**value,'artifact_ref':artifacts[0]},locations,unit=semantic_name,condition=path.endswith('.conditions'))
                # Attached parameter statistics can evade ordinary word/number
                # boundaries (Kd34uM, IC50_5uM). They are never certified names
                # by this finite name grammar. Preserve the original in custody.
                attached=re.compile(r'(?<![A-Za-z])(?:K[_ ]?d|K[_ ]?m|kcat|IC50|EC50|SEM|SD|CV|mean)'
                    r'[_:= ]*[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?'
                    r'(?:[A-Za-zµμ%][A-Za-z0-9µμ%/^−-]*)?',re.I)
                if attached.search(token):
                    shown['display_text']=attached.sub('[unclassified numerical context withheld]',shown['display_text'])
                    shown['status']='numerical_scope_unresolved'
                    shown['unavailable_reason']='unrequested_numerical_scope_unresolved'
                result.append({'field':path,'location':{k:shown[k] for k in ('source_ref','artifact_ref','representation','start','end')},
                    'display_text':shown['display_text'],'implementation_status':{'selected':'scoped',
                        'unrequested_numbers_withheld':'unrequested_numbers_withheld','numerical_scope_unresolved':'numerical_scope_unresolved'}[shown['status']],
                    'implementation_reason':shown['unavailable_reason']})
            else:
                for name,child in value.items():
                    # Population selects numerical operands via separate fields.
                    # Rendering those selections as context would expose their
                    # raw quotes again. Only instructional/scientific context is
                    # emitted here, under a bounded numerical guard.
                    if name not in ('estimates','covariance_source_refs'): visit(child,path+'.'+name)
        elif isinstance(value,list):
            for i,child in enumerate(value): visit(child,path+'.support')
    visit(extraction['request'],'assessment');return result


def populate_common_assessment(extraction):
    """Deterministic requested components of one bounded A105 assessment.

    Does not assign policy probabilities, infer missing controls/covariance,
    invoke IO/models, or perform registration, storage, delivery or continuation.
    """
    from .domain import validate_schema
    from .literature_compiled_assay_inputs import (COMMON_REASONS, COMMON_ASSUMPTIONS, COMMON_UNITS,
        common_assessment_inputs_schema, _common_q, _common_exact, _common_float)
    validate_schema(extraction,common_assessment_inputs_schema())
    data=deepcopy(extraction);args=data['request'];estimates=data['estimates'];model=args['model']
    model_key=[] if model is None else [identity('common_selected_model',model)]
    def q(role):
        e=estimates[role]
        return None if e is None or e['status']!='point' or e['exact_value'] is None else _common_q(e['exact_value'])
    def reason_roles(roles):
        missing=[];impl=[]
        for role in roles:
            e=estimates[role]
            if e is None: missing.append('estimate_not_selected')
            else:
                missing.extend(e['source_missing_reasons']);impl.extend(e['implementation_reasons'])
                if e['status']=='point' and (e['exact_value'] is None or _common_float(_common_q(e['exact_value']))!=e['value']):
                    raise ExperimentalContractError('common_bound_number_mismatch',role)
        return missing,impl
    def links(group):
        rel=args['relationships'][group];why=[]
        for name in ('endpoint','normalization'):
            status=rel[name]['value']
            if status in ('unknown',): why.append('endpoint_relationship_unknown' if name=='endpoint' else 'normalization_relationship_unknown')
            elif status=='incompatible': why.append('relationship_incompatible')
            elif status=='conflicting': why.append('relationship_conflicting')
            elif status=='different_with_declared_model': why.append('relationship_incompatible')
        if args['subject_relationship']['value'] not in ('same_construct_supported','intended_variant'):
            why.append('subject_relationship_unresolved')
        return why
    def model_reasons(required=COMMON_ASSUMPTIONS):
        if model is None:return ['model_not_selected'],False
        statuses=[model['assumptions'][name]['value'] for name in required]
        why=[]
        if 'unknown' in statuses:why.append('model_assumption_unknown')
        if 'conflicting' in statuses:why.append('model_assumption_conflicting')
        conditional='stipulated_sensitivity' in statuses or model['scope']=='conditional_sensitivity'
        conditional=conditional or any(estimates['free_substrate_'+arm] is not None and estimates['free_substrate_'+arm]['origin']=='proposed' for arm in ('reference','test'))
        if model['scope']=='supported_physical' and 'stipulated_sensitivity' in statuses:
            raise ExperimentalContractError('common_supported_model_has_stipulated_assumptions','model')
        return why,conditional
    def cell(name,value,roles,*,missing=(),relationship=(),implementation=(),conditional=False,unit='dimensionless',uncertainty=None,native=None):
        ms,im=reason_roles(roles);ms+=list(missing);im+=list(implementation);rel=list(relationship)
        if ms or im or rel:value=None
        exact=None
        if isinstance(value,Fraction):exact=_common_exact(value);floating=_common_float(value)
        else:floating=value
        if floating is not None and (not math.isfinite(floating) or floating==0 and value!=0):
            floating=None;im.append('numerical_model_range')
        if floating is None:exact=None
        owners=list(dict.fromkeys(estimates[r]['owner_key'] for r in roles if estimates[r] is not None))
        origins=list(dict.fromkeys(estimates[r]['origin'] for r in roles if estimates[r] is not None))
        return {'component':name,'value':None if conditional else floating,'exact_value':None if conditional else exact,
            'conditional_value':floating if conditional else None,'conditional_exact_value':exact if conditional else None,
            'unit':unit,'status':'unavailable' if floating is None else 'conditional_scenario' if conditional else 'populated',
            'formula':'selected_native_estimate' if name.startswith('estimate_') else _COMMON_FORMULAS[name],
            'meaning':'Native selected source report; qualified nondetection is not exact physical absence.' if name.startswith('estimate_') else _COMMON_MEANINGS[name],
            'origin':native['origin'] if native else 'derived','input_origins':origins,
            'source_missing_reasons':list(dict.fromkeys(ms)),'relationship_reasons':list(dict.fromkeys(rel)),
            'implementation_reasons':list(dict.fromkeys(im)),'operand_roles':list(roles),'operand_keys':owners,
            'model_keys':model_key if name.startswith(('occupancy','binding_only','post_binding','fully_corrected')) else [],
            'contribution_key':identity('common_contribution',{'operands':owners,'model':model_key if name.startswith(('occupancy','binding_only','post_binding','fully_corrected')) else []}),
            'native_semantics':native['native_semantics'] if native else None,
            'numeric_origin':native['numeric_origin'] if native else 'derived',
            'reported_uncertainty':None if not native or native['reported_spread'] is None else {
                'exact_magnitude':deepcopy(native['reported_spread']['exact_value']),
                'unit':native['reported_spread']['unit'],'statistic':native['reported_spread']['statistic'],
                'meaning':'source_reported_spread_not_joint_estimate_covariance'},
            'uncertainty':uncertainty or {'scope':'not_applicable','variance_status':'not_selected',
                'covariance_source_ref':None,'basis':None,'model':'none'}}
    values={};all_cells={}
    def inherited(names):
        return tuple([reason for name in names for reason in all_cells[name][field]]
            for field in ('source_missing_reasons','relationship_reasons','implementation_reasons'))
    def ratio(name,numerator,denominator,group):
        roles=(*numerator,*denominator);why=links(group);missing,impl=reason_roles(roles);value=None
        if not missing and not impl:
            a=math.prod(q(r) for r in numerator);b=math.prod(q(r) for r in denominator)
            if b==0:impl.append('zero_denominator')
            else:value=a/b
        all_cells[name]=cell(name,value,roles,relationship=why,implementation=impl)
        values[name]=None if why or missing or impl else value
    for role,e in estimates.items():
        base=role.rsplit('_',1)[0];name='estimate_'+role
        if e is None:all_cells[name]=cell(name,None,(role,),unit=COMMON_UNITS[base])
        else:
            # Native ND/negative findings survive; the arithmetic operand remains
            # unavailable. Native display does not convert a detection report to
            # a physical zero or reuse it in a point ratio/log.
            native=deepcopy(e);native['source_missing_reasons']=[];native['implementation_reasons']=[]
            saved=estimates[role];estimates[role]=native
            all_cells[name]=cell(name,None if e['native_exact_value'] is None else _common_q(e['native_exact_value']),
                (role,),unit=e['native_unit'],native=e)
            estimates[role]=saved
    ratio('product_reference_contrast',('product_test',),('product_reference',),'product')
    ratio('reporter_reference_contrast',('reporter_test',),('reporter_reference',),'reporter')
    ratio('productive_use_reference_contrast',('product_test','reporter_reference'),('reporter_test','product_reference'),'product')
    # Productive-use also needs the separately scoped reporter meanings.
    reporter_why=links('reporter')
    if args['product_reporter_relationship']['value']!='author_assigned_pair':reporter_why.append('endpoint_relationship_unknown')
    if reporter_why:
        all_cells['productive_use_reference_contrast']=cell('productive_use_reference_contrast',None,
            ('product_test','reporter_reference','reporter_test','product_reference'),relationship=reporter_why)
        values['productive_use_reference_contrast']=None
    ratio('saturation_turnover_reference_contrast',('kcat_test',),('kcat_reference',),'kinetic')
    ratio('low_substrate_efficiency_reference_contrast',('kcat_test','Km_reference'),('Km_test','kcat_reference'),'kinetic')
    occupancy_why,occupancy_cond=model_reasons(('equilibrium','one_site','free_substrate_treatment'))
    theta={}
    for arm in ('reference','test'):
        roles=('free_substrate_'+arm,'Kd_'+arm);ms,im=reason_roles(roles);value=None
        if not ms and not im:
            s,k=(q(r) for r in roles)
            if s<=0 or k<=0:im.append('positive_operand_required')
            else:value=s/(s+k)
        name='occupancy_'+arm;all_cells[name]=cell(name,value,roles,relationship=occupancy_why,
            implementation=im,conditional=occupancy_cond)
        theta[arm]=None if occupancy_why or ms or im else value
    binding_roles=('free_substrate_test','Kd_test','free_substrate_reference','Kd_reference')
    rt=None if any(v is None for v in theta.values()) else theta['test']/theta['reference']
    oms,ore,oi=inherited(('occupancy_test','occupancy_reference'))
    binding_why=links('binding')
    if binding_why: rt=None
    all_cells['occupancy_reference_contrast']=cell('occupancy_reference_contrast',rt,binding_roles,
        missing=oms,relationship=(*ore,*binding_why),implementation=oi,conditional=occupancy_cond)

    why,conditional=model_reasons();why+=links('product')+links('binding')
    product_roles=('product_test','product_reference');roles=(*product_roles,*binding_roles)
    parent_ms,parent_rel,parent_impl=inherited(('product_reference_contrast','occupancy_reference_contrast'))
    why+=parent_rel
    rp=values['product_reference_contrast'];ra=None if rp is None or rt is None else rp/rt
    error=None if rp is None or rt is None else rp-rt
    log_value=None;impl=[]
    if ra is not None:
        if ra<=0:impl.append('positive_operand_required')
        else:
            # Logs do not require projecting an extreme rational ratio first.
            log_value=math.log(ra.numerator)-math.log(ra.denominator)
            if abs(ra-1)<=Fraction(1,2):
                delta=_common_float(ra-1)
                if delta is not None:log_value=math.log1p(delta)
            if log_value==0 and ra!=1:impl.append('numerical_model_range')
    for name,v,more in (('binding_only_prediction_error',error,()),('post_binding_residual_ratio',ra,()),('binding_only_log_residual',log_value,impl)):
        all_cells[name]=cell(name,v,roles,missing=parent_ms,relationship=why,implementation=(*parent_impl,*more),conditional=conditional)
    # Exact gradient for the declared shared/separate physical S owners. Fixed
    # scenario S is held fixed only in this conditional propagation.
    variance=None;cov_reason=[];block=None;cov_roles=product_roles+('Kd_test','Kd_reference')
    if model is not None and model['substrate_uncertainty']!='fixed_scenario':
        cov_roles+=('free_substrate_test','free_substrate_reference')
    if ra is not None and not why and not impl:
        required_owners={estimates[r]['owner_key'] for r in cov_roles}
        for candidate in data['covariance_blocks']:
            if required_owners<=set(candidate['owner_keys']):block=candidate;break
        if block is None:cov_reason.append('joint_covariance_not_selected' if not data['covariance_blocks'] else 'joint_covariance_incomplete')
        elif block['variance_status']=='unknown':cov_reason.append('covariance_status_unknown')
        else:
            pt,pr,kdt,kdr,st,sr=(q(r) for r in ('product_test','product_reference','Kd_test','Kd_reference','free_substrate_test','free_substrate_reference'))
            if pt<=0 or pr<=0:cov_reason.append('positive_operand_required')
            else:
                grad=dict(product_test=1/pt,product_reference=-1/pr,Kd_test=1/(st+kdt),Kd_reference=-1/(sr+kdr),
                    free_substrate_test=-1/st+1/(st+kdt),free_substrate_reference=1/sr-1/(sr+kdr))
                by_owner={}
                for role in cov_roles:
                    owner=estimates[role]['owner_key'];by_owner[owner]=by_owner.get(owner,Fraction(0))+grad[role]
                order=block['owner_keys'];matrix=block['matrix_exact']
                variance=sum(ga*_common_q(matrix[order.index(a)][order.index(b)])*gb
                    for a,ga in by_owner.items() for b,gb in by_owner.items())
    uncertainty={'scope':'log_residual_operand_propagation','variance_status':'not_selected' if block is None else block['variance_status'],
        'covariance_source_ref':None if block is None else block['source_ref'],
        'basis':None if block is None else block['basis'],'model':'first_order_covariance_propagation'}
    z=z2=None
    if variance is not None:
        if variance<=0:cov_reason.append('positive_variance_required')
        else:
            fv=_common_float(variance)
            if fv is None:cov_reason.append('numerical_model_range')
            else:z=log_value/math.sqrt(fv);z2=log_value*log_value/fv
    log_ms,log_rel,log_impl=inherited(('binding_only_log_residual',))
    for name,v,more in (('binding_only_residual_variance',variance,()),
            ('binding_only_standardized_residual',z,cov_reason),('binding_only_squared_standardized_residual',z2,cov_reason)):
        all_cells[name]=cell(name,v,roles,missing=log_ms,relationship=log_rel,
            implementation=(*log_impl,*(tuple(r for r in cov_reason if r!='positive_variance_required') if name=='binding_only_residual_variance' else more)),
            conditional=conditional or model is not None and model['substrate_uncertainty']=='fixed_scenario',unit='dimensionless_squared' if name=='binding_only_residual_variance' else 'dimensionless',uncertainty=deepcopy(uncertainty))
        if block is not None and block['origin'] not in all_cells[name]['input_origins']:all_cells[name]['input_origins'].append(block['origin'])
    correction_roles=tuple(base+'_'+arm for base in ('background','recovery','active_fraction','nuisance_response') for arm in ('test','reference'))
    full_roles=(*product_roles,*binding_roles,*correction_roles);ms,im=reason_roles(full_roles)
    correction_model_why,correction_cond=model_reasons(('equilibrium','one_site','free_substrate_treatment','binding_catalysis_applicability','turnover_proportional_to_occupancy'))
    fullwhy=links('product')+links('correction')+links('binding')+correction_model_why
    full_ms,full_rel,full_impl=inherited(('occupancy_reference_contrast',))
    fullwhy+=full_rel;im+=full_impl
    if args['correction_factorization']['value']!='supported':fullwhy.append('correction_factorization_unresolved')
    if any(args['relationships']['correction'][name]['value'] not in ('compatible_supported','same_estimand') for name in ('endpoint','normalization','preparation','conditions')):
        fullwhy.append('correction_applicability_unresolved')
    full=None
    if not ms and not im and rt is not None:
        net_t=q('product_test')-q('background_test');net_r=q('product_reference')-q('background_reference')
        factors=[q(base+'_'+arm) for base in ('recovery','active_fraction','nuisance_response') for arm in ('test','reference')]
        if net_r==0:im.append('zero_denominator')
        elif any(v<=0 for v in factors) or any(q('background_'+arm)<0 for arm in ('test','reference')) or any(q('active_fraction_'+arm)>1 for arm in ('test','reference')):
            im.append('positive_operand_required')
        else:
            full=net_t/net_r/rt
            for base in ('recovery','active_fraction','nuisance_response'):full*=q(base+'_reference')/q(base+'_test')
    all_cells['fully_corrected_activity_reference_contrast']=cell('fully_corrected_activity_reference_contrast',full,full_roles,
        missing=full_ms,relationship=fullwhy,implementation=im,conditional=correction_cond)
    context=_common_scoped_context(data)
    groups={}
    for role,e in estimates.items():
        if e is not None:groups.setdefault(e['owner_key'],[]).append(role)
    dependence=[{'roles':r,'relation':'shared_primitive'} for r in groups.values() if len(r)>1]
    dependence.append({'roles':[r for r,e in estimates.items() if e is not None],
        'relation':'sampling_unknown' if args['sampling_relationship']['value']=='unknown' else args['sampling_relationship']['value']})
    if estimates['product_test'] is not None and estimates['Kd_test'] is not None:
        dependence.append({'roles':['product_test','Kd_test'],'relation':'complementary_endpoint'})
    result={'version':COMMON_SHEET,'axis':'A105','evaluation_scope':'common_assertion_contrast',
        'cells':[all_cells[name] for name in args['requested_cells']], 'context':context,
        'numerical_scope_implementation_status':'partial_unresolved' if any(r['implementation_status']=='numerical_scope_unresolved' for r in context) else 'scoped',
        'host_custody':{'source_refs':deepcopy(data['source_refs']),'source_artifacts':deepcopy(data['source_artifacts']),
            'withheld_locations':deepcopy(data['numerical_scope_locations'])},
        'assertion_resolution':args['assertion']['resolution'],'question':args['assertion']['question'],
        'dependence':dependence,'relationship_meanings':{'subject':args['subject_relationship']['value'],
            'product_reporter':args['product_reporter_relationship']['value'],'sampling':args['sampling_relationship']['value'],
            'groups':{group:{name:meaning['value'] for name,meaning in links.items()} for group,links in args['relationships'].items()},
            'correction_factorization':args['correction_factorization']['value'],
            'model_assumptions':None if model is None else {name:value['value'] for name,value in model['assumptions'].items()}},
        'model_meanings':None if model is None else {name:model[name] for name in ('kind','scope','substrate_ownership','substrate_uncertainty')},
        'estimate_bindings':[{name:e[name] for name in ('role','owner_key','physical_owner_key','population_key','assay_key','unit','numeric_origin')}
            for e in estimates.values() if e is not None],
        'annotation_credit':None,'remaining_implementation_limits':[
            'selected_path_binding_is_host_responsibility','general_quality_compilation_unfinished',
            'same_estimand_contradiction_compilation_unfinished','no_target_correspondence_or_final_credit']}
    validate_schema(result,common_assessment_sheet_schema());return result

