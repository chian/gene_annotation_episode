"""Closed v2 summary return view over the one A106 operation/sheet store."""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a108.domain import ContractError, obj
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_perturbation_inputs import ENDPOINT_UNITS, EXPOSURE_UNITS
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_perturbation_storage import perturbation_cells_schema
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_perturbation_summary import COMPONENTS, ROLES, SUMMARY_KINDS, SCALES, SPREAD_KINDS, UNIT_KINDS, VARIANCE_STATUSES, VARIANCE_SCOPES, INTERPRETATION_BASIS_FIELDS, INTERPRETATION_BASES
NAMESPACE = 'literature_perturbation_summary_cells'
FORMULA_CODES = {name: 'perturbation_summary_' + name + '_v2' for name in COMPONENTS}
NEW_REASONS = ('summary_value_unreported', 'spread_value_unreported', 'count_unreported', 'raw_unit_variation_unavailable', 'mean_variance_unavailable', 'cross_arm_covariance_unknown', 'shared_contrast_covariance_unavailable', 'no_bar_pixels', 'ambiguous_bar_runs', 'truncated_mean_edge', 'pixel_tolerance_outside_image', 'truncated_error_cap', 'graph_spread_scale_unresolved', 'asymmetric_graph_error_readings', 'graph_spread_unavailable')
METHODS = ('none', 'point_component', 'equal_unit_descriptive_mean', 'selected_reported_summary', 'reported_count', 'descriptive_sample_sd', 'raw_independent_unit_mean', 'reported_sem_squared', 'sd_squared_over_independent_n', 'mean_covariance_contrast', 'conditional_marginal_covariance_enclosure', 'shared_control_mean_covariance', *('reported_' + name for name in SPREAD_KINDS))
BOUND_KINDS = ('none', 'conditional_digitization_not_confidence_interval', 'reported_confidence_interval', 'reported_detection_limit', 'covariance_enclosure_not_confidence_interval')
_PHYSICAL_UNITS = tuple(dict.fromkeys((*ENDPOINT_UNITS, *EXPOSURE_UNITS, 'unreported', 'dimensionless')))
UNITS = (*_PHYSICAL_UNITS, 'count', *(f'{scale}_{u}' for scale in ('log10', 'ln') for u in _PHYSICAL_UNITS))
UNITS = (*UNITS, *(u + '_squared' for u in UNITS if u != 'count'))

def _contributing_roles(component):
    """Statistical premise custody, including operands of derived components.

    Include roles used by validity prerequisites as well as the arithmetic.
    This mapping does not select work or assign scientific credit.
    """
    for role in ROLES:
        if component.startswith(role + '_'):
            return (role,)
    endpoints = {'reference_endpoint': 'W', 'perturbed_endpoint': 'K', 'restored_endpoint': 'R'}
    if component in endpoints:
        return (endpoints[component],)
    if component in ('perturbation_difference', 'symmetric_effect', 'perturbation_mean_variance', 'perturbation_variance_lower', 'perturbation_variance_upper'):
        return ('W', 'K')
    if component in ('restoration_difference', 'restoration_mean_variance', 'restoration_variance_lower', 'restoration_variance_upper'):
        return ('K', 'R')
    if component in ('restoration_fraction_raw', 'restoration_agreement', 'shared_contrast_covariance'):
        return ('W', 'K', 'R')
    if component == 'amount_comparability':
        return ('A_reference', 'A_restored')
    if component == 'perturbation_isolation':
        return ('W', 'K', 'B_pert')
    if component == 'restoration_isolation':
        return ('W', 'K', 'R', 'B_rest')
    if component == 'effect_isolation':
        return ('W', 'K', 'R', 'B_pert', 'B_rest')
    if component in ('reference_restoration_index', 'reference_index_lower', 'reference_index_upper'):
        return ROLES
    raise ContractError('literature_perturbation_summary_component_selection_invalid')

def _basis_map_schema(roles):
    basis = {'type': 'object', 'properties': {name: {'type': 'string', 'enum': list(INTERPRETATION_BASES)} for name in INTERPRETATION_BASIS_FIELDS}, 'required': list(INTERPRETATION_BASIS_FIELDS), 'additionalProperties': False}
    return {'type': 'object', 'properties': {role: deepcopy(basis) for role in roles}, 'required': [], 'minProperties': 1, 'additionalProperties': False}

def perturbation_summary_cells_schema():
    """Original point meanings plus numerical summary and covariance cells."""
    schema = deepcopy(perturbation_cells_schema())
    properties = schema['items']['properties']
    properties['component']['enum'] = list(COMPONENTS)
    properties['component']['description'] = 'Source perturbation/restoration point components, retained reported summary/spread/count, descriptive raw-unit variation, conditional mean-variance estimates and shared-control covariance. Digitization constraints, covariance enclosures and reported confidence intervals have separate meanings; none is a probability of function or annotation credit.'
    properties['unit']['enum'] = list(UNITS)
    properties['formula_code']['enum'] = list(FORMULA_CODES.values())
    properties['unavailable_reason']['enum'] += list(NEW_REASONS)
    properties['conditional_on']['items']['enum'] += ['selected_same_endpoint_mean_estimators', 'retained_marginal_mean_variances', 'shared_K_measurement']
    properties['uncertainty_basis']['enum'] = ['per_measurement']
    properties.update({'statistic_method': {'type': 'string', 'enum': list(METHODS)}, 'variance_status': {'type': 'string', 'enum': list(VARIANCE_STATUSES)}, 'variance_scope': {'type': 'string', 'enum': list(VARIANCE_SCOPES)}, 'lower': {'type': ['number', 'null']}, 'upper': {'type': ['number', 'null']}, 'bound_kind': {'type': 'string', 'enum': list(BOUND_KINDS)}, 'lower_error_cap': {'type': ['number', 'null']}, 'upper_error_cap': {'type': ['number', 'null']}, 'error_cap_scale': {'type': 'string', 'enum': list(SCALES)}, 'spread_reading': {'type': 'string', 'enum': ['not_applicable', 'unresolved', 'symmetric_compatible', 'asymmetric_readings', 'reported_interval']}, 'measurement_role': {'type': ['string', 'null'], 'enum': [None, *ROLES]}, 'summary_kind': {'type': 'string', 'enum': list(SUMMARY_KINDS)}, 'value_scale': {'type': 'string', 'enum': list(SCALES)}, 'summary_scale': {'type': 'string', 'enum': list(SCALES)}, 'spread_kind': {'type': 'string', 'enum': list(SPREAD_KINDS)}, 'spread_scale': {'type': 'string', 'enum': list(SCALES)}, 'count_unit': {'type': 'string', 'enum': list(UNIT_KINDS)}, 'independence': {'type': 'string', 'enum': ['independent', 'not_independent', 'unknown']}, 'n': {'type': ['integer', 'null'], 'minimum': 1}, 'reported_coverage': {'type': ['number', 'null'], 'exclusiveMinimum': 0, 'exclusiveMaximum': 1}})
    schema['items']['required'] = list(properties)
    schema['x-source'] = NAMESPACE
    properties['statistical_interpretation_basis'] = _basis_map_schema(ROLES)
    groups = {}
    for component in COMPONENTS:
        groups.setdefault(_contributing_roles(component), []).append(component)
    schema['items']['allOf'] = [{'if': {'properties': {'component': {'enum': names}}}, 'then': {'properties': {'statistical_interpretation_basis': _basis_map_schema(roles)}}} for roles, names in groups.items()]
    properties['covariance_interpretations'] = _covariance_schema()
    for pairs in ((), (('W', 'K'),), (('K', 'R'),), (('W', 'K'), ('W', 'R'), ('K', 'R'))):
        names = [name for name in COMPONENTS if _covariance_pairs(name) == pairs]
        schema['items']['allOf'].append({'if': {'properties': {'component': {'enum': names}}}, 'then': {'properties': {'covariance_interpretations': _covariance_schema(pairs) if pairs else False}}})
    return schema
_COVARIANCE_USES = ('used_selected_covariance', 'unknown_covariance_enclosure', 'component_unavailable')

def _covariance_pairs(component):
    if component in ('perturbation_mean_variance', 'perturbation_variance_lower', 'perturbation_variance_upper'):
        return (('W', 'K'),)
    if component in ('restoration_mean_variance', 'restoration_variance_lower', 'restoration_variance_upper'):
        return (('K', 'R'),)
    if component == 'shared_contrast_covariance':
        return (('W', 'K'), ('W', 'R'), ('K', 'R'))
    return ()

def _covariance_schema(pairs=None):
    reference = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'reference'}
    fields = {'first': {'type': 'string', 'enum': ['W', 'K', 'R']}, 'second': {'type': 'string', 'enum': ['W', 'K', 'R']}, 'selection': {'type': 'string', 'enum': ['selected', 'unreported']}, 'kind': {'type': 'string', 'enum': ['unknown', 'mean_covariance', 'uncorrelated', 'paired_units']}, 'interpretation_basis': {'type': ['string', 'null'], 'enum': [None, *INTERPRETATION_BASES]}, 'variance_status': {'type': 'string', 'enum': list(VARIANCE_STATUSES)}, 'use': {'type': 'string', 'enum': list(_COVARIANCE_USES)}, 'support_refs': {'type': 'array', 'uniqueItems': True, 'items': reference}}
    result = {'type': 'array', 'minItems': 1, 'maxItems': 3, 'items': obj(fields)}
    if pairs is not None:
        result.update(minItems=len(pairs), maxItems=len(pairs), items=False, prefixItems=[obj({**deepcopy(fields), 'first': {'type': 'string', 'const': first}, 'second': {'type': 'string', 'const': second}}) for first, second in pairs])
    return result
