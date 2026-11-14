"""Original reported-curve precision contracts; no fitter or covariance execution."""
from copy import deepcopy

GRID_SHEET_VERSION = 'a105_reported_curve_precision_v1'
GRID_SOLVER_VERSION = 'dimensionless_profile_stationarity_log2_32_v1'
GRID_REASONS = ('incomplete_selected_roster', 'no_point_observations', 'insufficient_entry_count',
    'nonpositive_mean', 'numerical_model_range', 'model_not_selected', 'concentration_unit_unknown',
    'positive_concentrations_required', 'insufficient_distinct_concentrations',
    'fit_nonpositive_response', 'fit_domain_exhausted', 'fit_solution_unresolved',
    'fit_nonidentifiable', 'fit_solver_failed', 'sampling_model_unknown', 'sampling_model_conflicting',
    'not_applicable_to_estimator', 'zero_covariance_variance', 'source_measurement_unavailable',
    'nondetection_without_point', 'censored_measurement', 'formula_measurement_unsupported',
    'numeric_cell_type_required', 'source_cell_error', 'source_error_cell', 'invalid_numeric_lexeme')
_GRID_POINT_COMPONENTS = ('mean', 'sample_variance', 'sample_sd', 'cv', 'available_point_mean',
    'available_point_variance', 'available_point_sd', 'available_point_cv', 'selected_entry_count', 'available_point_count')
_GRID_ESTIMATORS = ('mean_of_reported_curve_fits', 'fit_of_point_means')


def reported_curve_precision_selector_schema():
    from gene_annotation_episode.domain import obj
    from .literature_rate_observation_input_contracts import CELL
    def choices(values): return {'enum': list(values)}
    fields = [
        obj({'scope': {'const': 'point'}, 'concentration_cell': CELL, 'component': choices(_GRID_POINT_COMPONENTS)}),
        obj({'scope': {'const': 'curve'}, 'curve_header_cell': CELL, 'component': choices(
            ('Vmax', 'Km', 'SSE', 'stationarity_error', 'selected_point_count', 'available_point_count'))}),
        obj({'scope': {'const': 'estimator'}, 'estimator': choices(_GRID_ESTIMATORS), 'component': choices(
            ('Vmax', 'Km', 'native_efficiency', 'SSE', 'log_efficiency_variance',
             'log_efficiency_standard_uncertainty', 'diagonal_only_log_efficiency_variance'))}),
        obj({'scope': {'const': 'reported_curve_covariance'}, 'left_concentration_cell': CELL,
            'right_concentration_cell': CELL, 'component': choices(('sample_covariance', 'conditional_mean_curve_covariance'))}),
        obj({'scope': {'const': 'parameter_covariance'}, 'estimator': choices(('reported_curve_fit_distribution', *_GRID_ESTIMATORS)),
            'left_parameter': choices(('Vmax', 'Km')), 'right_parameter': choices(('Vmax', 'Km')),
            'component': choices(('covariance', 'correlation'))}),
        obj({'scope': {'const': 'sensitivity'}, 'estimator': {'const': 'fit_of_point_means'},
            'parameter': choices(('Vmax', 'Km')), 'concentration_cell': CELL,
            'component': {'const': 'd_parameter_d_point_mean'}}),
        obj({'scope': {'const': 'variance_term'}, 'estimator': choices(_GRID_ESTIMATORS),
            'left_parameter': choices(('Vmax', 'Km')), 'right_parameter': choices(('Vmax', 'Km')),
            'component': {'const': 'signed_log_efficiency_variance_term'}}),
        obj({'scope': {'const': 'grid'}, 'component': choices(('all_reported_residual_SS',
            'within_concentration_reported_entry_SS', 'mean_curve_fit_residual_SS_times_curve_count',
            'reported_curve_count', 'complete_curve_count'))})]
    return {'anyOf': fields}


def reported_curve_precision_request_schema():
    from gene_annotation_episode.domain import obj
    return obj({'version': {'const': 'a105_reported_curve_precision_request_v1'},
        'fit_model': {'enum': ['none', 'unweighted_positive_km_mm']},
        'requested_components': {'type': 'array', 'uniqueItems': True,
                                 'items': reported_curve_precision_selector_schema()}})


def reported_curve_precision_sheet_schema():
    from gene_annotation_episode.domain import obj
    from .literature_rate_observation_input_contracts import (_grid_array, _grid_nullable,
        _grid_exact_schema, reported_rate_grid_extraction_schema, TEXT)
    array = _grid_array; nullable = _grid_nullable
    cell = obj({'selector': reported_curve_precision_selector_schema(), 'cell_key': TEXT,
        'value': {'type': ['number', 'null']}, 'exact_value': nullable(_grid_exact_schema()),
        'conditional_value': {'type': ['number', 'null']}, 'conditional_exact_value': nullable(_grid_exact_schema()),
        'unit': TEXT, 'formula_id': TEXT, 'meaning_id': TEXT,
        'numeric_basis': {'enum':['source_decimal_arithmetic','canonical_numeric_fit_operands_not_exact_fits']},
        'status': {'enum': ['populated', 'conditional_scenario', 'unavailable']},
        **{name: array({'enum': list(GRID_REASONS)}) for name in
            ('source_missing_reasons', 'relationship_reasons', 'implementation_reasons')},
        'input_measurement_keys': array(TEXT), 'input_origins': array({'enum': ['reported', 'synthetic']}),
        'estimator_key': nullable(TEXT), 'model_keys': array(TEXT), 'contribution_key': TEXT,
        'variance_status': {'enum': ['not_applicable', 'estimated', 'unknown']},
        'count_basis': {'const': 'distinct_reported_cells_and_columns_not_physical_preparations'},
        'scope': {'enum': ['full_selected_roster', 'available_points', 'not_applicable']}})
    diagnostics = obj({'label': TEXT, 'reason': {'enum': [*GRID_REASONS, None]},
        'log2_Km_domain': {'const': [-32, 32]}, 'stationarity_error': {'type': ['number', 'null']},
        'curvature_determinant': {'type': ['number', 'null']}})
    return obj({'version': {'const': GRID_SHEET_VERSION}, 'axis': {'const': 'A105'},
        'evaluation_scope': {'const': 'reported_curve_precision'},
        'extraction': reported_rate_grid_extraction_schema(), 'request': reported_curve_precision_request_schema(),
        'cells': array(cell), 'calculation_metadata': obj({'solver_version': {'const': GRID_SOLVER_VERSION},
            'solver_scope': {'const': 'finite_numerical_domain_not_global_certification'},
            'diagnostics': array(diagnostics), 'sampling': deepcopy(reported_rate_grid_extraction_schema()['properties']['original_arguments']['properties']['curve_sampling']),
            'physical_preparation_count': {'type': 'null'}, 'published_estimate_covariance': {'type': 'null'}}),
        'remaining_implementation_limits': {'const': ['selected_typed_binding_unimplemented',
            'general_quality_compilation_unfinished', 'same_estimand_contradiction_compilation_unfinished',
            'no_target_correspondence_or_final_credit']}})


