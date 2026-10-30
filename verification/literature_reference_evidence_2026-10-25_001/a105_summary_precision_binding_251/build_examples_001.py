"""Schema-conformance illustrations from clarification002; no science execution."""
from pathlib import Path
from copy import deepcopy
import json
from jsonschema import Draft202012Validator

HERE = Path(__file__).parent
schema = json.loads((HERE/'RETURN_ROWS_SCHEMA_001.json').read_text())
names = schema['items']['properties']['cell_name']['enum']
row_applicability = ['row_footnote_applicability']
ownership = [*row_applicability, 'statistical_count_matches_sd', 'one_estimate_per_preparation',
    'reported_sd_summarizes_counted_preparation_estimates']
mean = [*ownership, 'sample_sd_n_minus_one', 'iid_common_mean_finite_variance']
model = {
    'reported_parameter': [], 'reported_sd': [], 'source_summary_count': [],
    'independent_preparation_count': row_applicability,
    'statistical_estimator_count': ownership, 'relative_reported_sd': [],
    'mean_variance': mean, 'mean_standard_error': mean,
    'relative_mean_standard_error': [*mean, 'equal_weight_arithmetic_mean'],
    'mean_interval_df': [*ownership, 'sample_sd_n_minus_one'],
    'mean_interval_confidence_level': [],
    'mean_interval_t_multiplier': [*mean, 'normal_sampling_units'],
    'mean_interval_halfwidth': [*mean, 'normal_sampling_units'],
    'mean_interval_lower': [*mean, 'normal_sampling_units', 'equal_weight_arithmetic_mean'],
    'mean_interval_upper': [*mean, 'normal_sampling_units', 'equal_weight_arithmetic_mean'],
}
# The branch-specific actual route further narrows this maximum dependency set.
deps = {
    'reported_parameter': ['parameter_source', 'parameter_unit_source'],
    'reported_sd': ['spread_source', 'spread_unit_source'],
    'source_summary_count': ['count_source'],
    'independent_preparation_count': ['count_source'],
    'statistical_estimator_count': ['count_source', 'statistical_count_source'],
    'relative_reported_sd': ['parameter_source', 'parameter_unit_source', 'spread_source', 'spread_unit_source'],
    'mean_variance': ['spread_source', 'spread_unit_source', 'count_source', 'statistical_count_source'],
    'mean_standard_error': ['spread_source', 'spread_unit_source', 'count_source', 'statistical_count_source'],
    'relative_mean_standard_error': ['parameter_source', 'parameter_unit_source', 'spread_source', 'spread_unit_source', 'count_source', 'statistical_count_source'],
    'mean_interval_df': ['count_source', 'statistical_count_source'],
    'mean_interval_confidence_level': [],
    'mean_interval_t_multiplier': ['count_source', 'statistical_count_source'],
    'mean_interval_halfwidth': ['spread_source', 'spread_unit_source', 'count_source', 'statistical_count_source'],
    'mean_interval_lower': ['parameter_source', 'parameter_unit_source', 'spread_source', 'spread_unit_source', 'count_source', 'statistical_count_source'],
    'mean_interval_upper': ['parameter_source', 'parameter_unit_source', 'spread_source', 'spread_unit_source', 'count_source', 'statistical_count_source'],
}
(HERE/'COMPONENT_DEPENDENCY_MAP_001.json').write_text(json.dumps({name: {
    'maximum_condition_names': model[name], 'maximum_numeric_dependency_names': deps[name],
    'rule': 'Return only members actually used by the selected source/statistical-count route; absent dependencies remain absent. Condition states do not carry witness quotes or unrequested numerical inputs.'}
    for name in names}, indent=2)+'\n')

def cell(name, value, unit, reason=None, exact=None):
    return {'value': value, 'unit': unit, 'status': 'unavailable' if reason else 'populated',
        'qualification': 'unavailable' if reason else 'derived_source_supported_conditions',
        'formula_code': 'summary_precision_'+name, 'origin': 'synthetic', 'approximate': False,
        'source_exact_value': exact, 'conditional_on': [], 'stipulated_assumptions': [], 'unavailable_reason': reason}

def row(name, content):
    return {'row_version': 'kinetic_summary_precision_return_v1', 'sheet_ref': 'source_'+'a'*64,
        'evidence_source_ref': 'source_'+'b'*64, 'evaluation_scope': 'source_kinetic_summary_precision',
        'component': 'source_'+name, 'population': 'source_cells', 'cell_name': name, 'cell': content,
        'source_kind': 'synthetic_fixture', 'parameter_kind': 'kcat',
        'source_context': {name: {'status': 'not_selected', 'fragments': []}
            for name in schema['items']['properties']['source_context']['properties']},
        'sampling_basis': {'source_count_meaning': 'both_same_count', 'repetition_basis': 'biological_preparations', 'estimate_basis': 'between_fitted_parameters'},
        'model_conditions': [], 'contribution': {'kind': 'one_summary_precision_contribution',
            'physical_measurement_id': None, 'independence_inferred': False,
            'variance_meaning': 'estimated_random_mean_precision_not_known_population_variance',
            'shared_systematic_uncertainty': 'not_established_by_summary_precision'},
        'dependency_locations': [], 'withheld_locations': [], 'bounds_kind': 'no_additional_bounds_in_this_return', 'limits': []}

examples = [row('reported_parameter', cell('reported_parameter', None, None, 'source_measurement_unreported')),
    row('reported_sd', cell('reported_sd', 12, 'per_min', exact={'numerator': '12', 'denominator': '1'})),
    row('mean_variance', cell('mean_variance', 36, 'per_min_squared', exact={'numerator': '36', 'denominator': '1'})),
    row('mean_standard_error', cell('mean_standard_error', 6, 'per_min', exact={'numerator': '6', 'denominator': '1'})),
    row('relative_mean_standard_error', cell('relative_mean_standard_error', None, 'dimensionless', 'source_measurement_unreported'))]
for example in examples:
    Draft202012Validator(schema).validate([example])
bad = deepcopy(examples[2]); bad['cell']['formula_code'] = 'summary_precision_reported_parameter'
bad_unit = deepcopy(examples[2]); bad_unit['cell']['unit'] = 'count'
for value in (bad, bad_unit):
    assert not Draft202012Validator(schema).is_valid([value])
(HERE/'PROPOSED_SCHEMA_EXAMPLES_001.json').write_text(json.dumps({
    'classification': 'PROPOSED_SCHEMA_CONFORMANCE_ONLY_NOT_AUTHENTICATED_SOURCE_ROWS',
    'basis': 'Explicit hypothetical missing-central-value arithmetic printed in reviewed248 CLARIFICATION002: reported SD0.2/sec, exact n4 with supported sample/IID/ownership conditions; SD12/min, mean variance36/min², SE6/min. No fixture source, extraction, selected operation or calculator executed here.',
    'request_roster': [r['component'] for r in examples],
    'proposed_output_rows': examples,
    'important_limit': 'These illustrate exact closed wire shapes; identity/location/condition receipts will be populated from finalized248 fixtures after root pin review, not treated as authenticated facts now.'}, indent=2)+'\n')
(HERE/'SCHEMA_CHECKS_001.json').write_text(json.dumps({'all_json_schema_documents_compile': all(
    Draft202012Validator.check_schema(json.loads(p.read_text())) is None
    for p in HERE.glob('*SCHEMA_001.json')), 'illustrative_rows_validate': True,
    'wrong_formula_and_unit_rejected': True, 'production_or_test_execution': False}, indent=2)+'\n')
