"""Selected source-cell operation, saved numerical sheet and exact subset custody."""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a101.domain import obj
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_rate_observation_inputs import SOURCE_KINDS, TEXT, STATUSES, ENTRY_REASONS
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_rate_observation_calculations import COMPONENTS, REASONS, FORMULAS, QUALIFICATIONS
NAMESPACE = 'literature_rate_observation_cells'
ALL_REASONS = (*REASONS, *ENTRY_REASONS)

def _array(schema, unique=False):
    return {'type': 'array', 'items': deepcopy(schema), **({'uniqueItems': True} if unique else {})}

def _nullable(schema):
    return {'anyOf': [deepcopy(schema), {'type': 'null'}]}

def _exact():
    return _nullable(obj({'numerator': {'type': 'string', 'pattern': '^-?[0-9]+$'}, 'denominator': {'type': 'string', 'pattern': '^[1-9][0-9]*$'}}))

def _custody():
    return obj({name: deepcopy(TEXT) for name in ('source_ref', 'artifact_ref', 'workbook_sha256', 'worksheet', 'member', 'member_sha256')})

def _witness():
    formula = obj({'text': {'type': ['string', 'null']}, 'attributes': {'type': 'object', 'additionalProperties': {'type': 'string'}}})
    return obj({**_custody()['properties'], 'cell': deepcopy(TEXT), 'cell_type': deepcopy(TEXT), **{name: {'type': ['string', 'null']} for name in ('value', 'raw_value', 'style_index', 'error')}, 'formula': _nullable(formula), 'value_is_formula_cache': {'type': 'boolean'}})

def _cell():
    return obj({'value': {'type': ['number', 'null']}, 'unit': deepcopy(TEXT), 'formula': {'enum': list(dict.fromkeys(FORMULAS.values()))}, 'origin': {'const': 'derived'}, 'status': {'enum': ['populated', 'unavailable']}, 'unavailable_reason': {'enum': [*ALL_REASONS, None]}, 'source_exact_value': _exact()})

def _group(numeric=False):
    observation = obj({'record_identity': deepcopy(TEXT), 'label': deepcopy(TEXT), 'status': {'enum': list(STATUSES)}, 'conflicting': {'type': 'boolean'}, 'association_unresolved': {'type': 'boolean'}, 'unavailable_reason': {'enum': [*ENTRY_REASONS, None]}, 'label_source': _witness(), 'group_source': _witness()})
    fields = {'label': deepcopy(TEXT), **{name: {'type': 'integer', 'minimum': 0} for name in ('selected_row_count', 'known_entry_count', 'representation_count', 'point_entry_count')}, 'entry_count': {'type': ['integer', 'null'], 'minimum': 0}, 'association_unresolved': {'type': 'boolean'}, 'complete': {'type': 'boolean'}, 'observation_labels': _array(observation), 'limitations': _array({'enum': list(ALL_REASONS)}, True)}
    if numeric:
        fields['cells'] = obj({name: _cell() for name in ('rate', 'sample_sd', 'cv', 'observed_point_mean', 'observed_point_sd')})
    return obj(fields)

def rate_observation_cells_schema():
    ref = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    group = obj({'requested_label': deepcopy(TEXT), 'status': {'enum': ['observed', 'not_observed']}, 'observed': _nullable(_group())})
    row = obj({'sheet_ref': deepcopy(ref), 'evidence_source_ref': deepcopy(ref), 'evaluation_scope': {'const': 'source_reported_rate_observations'}, 'component': {'enum': list(COMPONENTS)}, **_cell()['properties'], **{name: deepcopy(TEXT) for name in ('subject', 'panel', 'source_native_unit')}, 'source_kind': {'enum': list(SOURCE_KINDS)}, 'groups': obj({role: deepcopy(group) for role in ('reference', 'test')}), 'grouping': {'const': 'unknown'}, 'physical_conversion': {'const': 'unknown'}, 'qualifications': {'const': list(QUALIFICATIONS)}, 'input_origins': _array({'enum': ['reported', 'synthetic']}, True)})
    return {**_array(row), 'x-source': NAMESPACE}
GRID_RECORD = 'literature_reported_rate_observation_record_v2'
GRID_NAMESPACE = 'literature_rate_grid_cells'
GRID_SCOPE = 'source_reported_curve_precision'

def _grid_ref(kind):
    return {'type': 'string', 'format': 'reference', 'x-reference-namespace': kind}

def _grid_location_schema():
    return obj({'source_ref': _grid_ref('source'), 'artifact_ref': _grid_ref('artifact'), 'member': deepcopy(TEXT), 'cell': {'type': 'string', 'pattern': '^[A-Z]+[1-9][0-9]*$'}})

def rate_grid_cells_schema():
    from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_rate_observation_calculations import reported_curve_precision_sheet_schema
    from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_rate_observation_inputs import GRID_SOURCE_STATUSES
    cell = deepcopy(reported_curve_precision_sheet_schema()['properties']['cells']['items']['properties'])
    loc = _grid_location_schema()
    label = obj({'display_text': {'type': ['string', 'null']}, 'status': {'enum': ['exact_source_label', 'unrequested_numbers_withheld', 'numerical_scope_unresolved']}, 'implementation_reason': {'enum': [None, 'unrequested_numerical_scope_unresolved']}, 'location': loc})
    coordinate = obj({'role': {'enum': ['point', 'left', 'right']}, 'location': loc, 'measurement_key': deepcopy(TEXT), 'unit': {'enum': ['M', 'mM', 'uM', 'nM', 'unknown']}, 'status': {'enum': list(GRID_SOURCE_STATUSES)}, 'exact_value': deepcopy(cell['exact_value']), 'exact_limit': deepcopy(cell['exact_value']), 'bound': {'enum': ['none', '<', '>', '<=', '>=', '≤', '≥']}, 'origin': {'enum': ['reported', 'synthetic']}})
    span = obj({'source_ref': _grid_ref('source'), 'artifact_ref': _grid_ref('artifact'), 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}})
    props = {'sheet_ref': _grid_ref('source'), 'evidence_source_ref': _grid_ref('source'), 'record_version': {'const': GRID_RECORD}, 'scientific_sheet_version': {'const': 'a105_reported_curve_precision_v1'}, 'evaluation_scope': {'const': GRID_SCOPE}, 'component': deepcopy(TEXT), **cell, 'origin': {'const': 'derived'}, 'source_context': obj({name: deepcopy(label) for name in ('subject', 'panel', 'native_endpoint')}), 'coordinate_context': _array(coordinate), 'sampling': obj({'status': {'enum': ['supported', 'stipulated_sensitivity', 'unknown', 'conflicting']}, 'assumption': {'enum': ['none', 'iid_reported_curve_vectors']}, 'source_claim': {'enum': ['iid_reporting_vectors_supported', 'not_established', 'unknown', 'conflicting']}}), 'reporting_counts': obj({name: {'type': ['integer', 'null'], 'minimum': 0} for name in ('selected_reporting_entries', 'available_numeric_entries', 'selected_concentrations', 'reporting_curves')}), 'model_meaning': obj({'fit_model': {'enum': ['none', 'unweighted_positive_km_mm']}, 'estimator': {'enum': ['not_applicable', 'per_reported_curve_fit', 'mean_of_reported_curve_fits', 'fit_of_point_means', 'reported_curve_fit_distribution']}, 'weighting': {'enum': ['not_applicable', 'unweighted']}, 'solver_scope': {'const': 'finite_numerical_domain_not_global_certification'}}), 'scientific_scope': obj({'concentration_basis': {'const': 'fixed_reported_concentrations_when_fitted'}, 'precision_basis': {'enum': ['not_applicable', 'descriptive_reported_entries', 'descriptive_fitted_curve_distribution', 'conditional_iid_reporting_curve_vectors']}, 'physical_preparation_count': {'type': 'null'}, 'published_estimate_covariance': {'type': 'null'}, 'excluded_uncertainty': {'const': 'blank_recovery_active_amount_and_concentration_uncertainty_not_propagated'}, 'endpoint_meaning': {'const': 'reporter_to_product_meaning_not_resolved_by_precision'}, 'endpoint_relationship': {'enum': ['reported_convention_only', 'supported', 'unknown', 'conflicting']}}), 'host_custody': obj({'context_locations': _array(span), 'selected_cell_locations': _array(loc)}), 'source_kind': {'enum': list(SOURCE_KINDS)}}
    return {**_array(obj(props)), 'x-source': GRID_NAMESPACE}
