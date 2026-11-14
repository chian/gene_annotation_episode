"""Typed NMF result selections and recorded numerical projections.

No numerical sheet is calculated here. These declarations constrain the exact
outputs of project_nmf_result and the existing retained-file custody shape.
"""
from copy import deepcopy
from jsonschema import Draft202012Validator

from .expression_nmf_common import canonical, issue, SHEET_SCHEMA
from .expression_nmf_result_views import FIT_FIELDS, SELECTOR_SCHEMA, VIEWS


def require(condition, code='expression_nmf_result_authority_conflict'):
    if not condition:
        raise ValueError(code)


def obj(**fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


def arr(items, **extra):
    return {'type': 'array', 'items': items, **extra}


def nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


COUNT = {'type': 'integer', 'minimum': 0}
NUMBER = {'type': 'number'}
BOOL = {'type': 'boolean'}
SHA = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
LABEL = {'type': 'string', 'maxLength': 4096, 'pattern': '^[^\u0000-\u001f\u007f]*$'}
IDENTIFIER = {'type': 'string', 'minLength': 1, 'maxLength': 256, 'pattern': '^[A-Za-z0-9_][A-Za-z0-9_.:/+()=-]*$'}
UNIT = {'type': 'string', 'minLength': 1, 'maxLength': 130, 'pattern': '^[^\u0000-\u001f\u007f]+$'}
FILE_SCHEMA = obj(artifact_ref={'type': 'string', 'pattern': '^artifact_[0-9a-f]{64}$'},
    sha256=SHA, size_bytes=COUNT, format=IDENTIFIER)
SAVED_FILE_SCHEMA = deepcopy(FILE_SCHEMA)
SAVED_FILE_SCHEMA['properties']['format'] = {'const': SHEET_SCHEMA}

ISSUE_CODES = (
    'input_data_incompatible', 'prepared_data_incompatible', 'prepared_input_relation_mismatch',
    'native_result_incompatible', 'native_input_relation_mismatch', 'native_parameter_relation_mismatch',
    'native_parameters_invalid', 'factor_axis_association_mismatch', 'factor_missing',
    'factor_shape_or_values_incompatible', 'native_source_missing_or_incompatible',
    'native_diagnostics_incompatible', 'native_diagnostic_invalid', 'native_outcome_invalid',
    'native_factorization_unavailable', 'native_warning_records_invalid', 'negative_input_not_nmf_compatible',
    'negative_expression_input', 'invalid_fit_matrix', 'native_fit_failed', 'invalid_metadata_schema',
    'invalid_units', 'invalid_utf8_or_delimited_input', 'empty_expression_matrix',
    'nonrectangular_expression_row', 'nonnumeric_expression_cell', 'nonfinite_expression_cell',
    'invalid_axis_metadata', 'metadata_position_invalid', 'metadata_occurrence_conflict',
    'unused_column_sum_overflow', 'zero_column_scaling_denominator', 'nonfinite_column_denominator',
    'nonfinite_normalized_value', 'manifest_missing_or_malformed', 'artifact_missing_or_incompatible',
    'original_bytes_input_data_conflict', 'expected_input_identity_mismatch',
    'manifest_operand_relation_mismatch', 'manifest_shape_mismatch', 'factor_association_mismatch',
    'derived_numeric_overflow', 'residual_population_incomplete', 'zero_input_frobenius_denominator',
    'zero_component_loading_sum', 'zero_reconstructed_sample_denominator',
    'capture_file_unavailable', 'retained_artifact_mismatch', 'writer_not_closed',
    'original_execution_mismatch', 'original_parameters_mismatch', 'original_input_metadata_mismatch',
    'native_software_mismatch', 'worker_output_unavailable', 'worker_output_malformed',
    'worker_nonzero_exit', 'worker_resource_failure', 'saved_sheet_incompatible',
    'projection_selection_invalid', 'projection_contract_invalid', 'worker_input_unavailable',
)
ISSUE_SCHEMA = obj(code={'enum': list(ISSUE_CODES)}, stage={'enum': [
    'input', 'preparation', 'fit_validation', 'fit', 'sheet', 'artifact_loading', 'calculation',
    'capture', 'authority', 'worker', 'projection']}, field=nullable(IDENTIFIER),
    gene_position=nullable(COUNT), sample_position=nullable(COUNT), component_position=nullable(COUNT))
FILTER_FIELDS = {
    'fit_diagnostics': ('value',), 'gene_loadings': ('raw_loading', 'normalized_loading'),
    'sample_contributions': ('raw_coefficient', 'component_contribution', 'contribution_fraction'),
    'residual_cells': ('raw_value', 'fit_value', 'reconstructed_value', 'signed_residual'),
}
EXPRESSION_NMF_RESULT_SELECTOR_SCHEMA = obj(version={'const': 'expression_nmf_result_selector_v1'},
    mode={'enum': ['native_result', 'saved_sheet_recalculation']}, projection=deepcopy(SELECTOR_SCHEMA),
    saved_sheet_file=nullable(SAVED_FILE_SCHEMA))


def checked(value, schema, code):
    canonical(value)
    require(Draft202012Validator(schema).is_valid(value), code)
    return deepcopy(value)


def validate_file(value, *, saved=False):
    value = checked(value, SAVED_FILE_SCHEMA if saved else FILE_SCHEMA, 'invalid_expression_nmf_file')
    require(type(value['size_bytes']) is int and value['artifact_ref'] == 'artifact_' + value['sha256'],
        'expression_nmf_file_identity_mismatch')
    return value


def validate_projection_selector(value):
    value = checked(value, SELECTOR_SCHEMA, 'invalid_expression_nmf_projection_selector')
    view = value['view']
    for name in ('gene_positions', 'sample_positions', 'component_positions', 'fields'):
        allowed = {'gene_positions': ('gene_loadings', 'residual_cells'),
            'sample_positions': ('sample_contributions', 'residual_cells'),
            'component_positions': ('gene_loadings', 'sample_contributions'), 'fields': ('fit_diagnostics',)}[name]
        require(name not in value or view in allowed, 'irrelevant_nmf_selector')
        if name in value and name != 'fields':
            require(all(type(i) is int for i in value[name]), 'invalid_nmf_position_selector')
    require(view not in ('gene_loadings', 'residual_cells') or 'gene_positions' in value, 'nmf_occurrence_selector_required')
    require(view not in ('sample_contributions', 'residual_cells') or 'sample_positions' in value, 'nmf_occurrence_selector_required')
    require(view != 'fit_diagnostics' or 'fields' in value, 'requested_nmf_diagnostic_fields_required')
    require(all(type(value['row_window'][k]) is int for k in ('offset', 'limit')), 'invalid_nmf_row_window')
    if value.get('filter') is not None:
        require(value['filter']['field'] in FILTER_FIELDS[view], 'invalid_nmf_filter')
    return value


def validate_expression_nmf_result_selector(value, *, job=None):
    value = checked(value, EXPRESSION_NMF_RESULT_SELECTOR_SCHEMA, 'invalid_expression_nmf_result_selector')
    validate_projection_selector(value['projection'])
    require((value['saved_sheet_file'] is None) == (value['mode'] == 'native_result'), 'expression_nmf_saved_sheet_required')
    if value['saved_sheet_file'] is not None:
        validate_file(value['saved_sheet_file'], saved=True)
    if job is not None:
        from .native_expression_nmf_contracts import validate_expression_nmf_job
        validate_expression_nmf_job(job)
    return value


def validate_issue(value):
    return checked(value, ISSUE_SCHEMA, 'invalid_expression_nmf_issue')


def failure(code, stage, *, field=None, **positions):
    return validate_issue(issue(code, stage, field=field, **positions))


def projection_schema():
    key = lambda axis: {'type': 'string', 'pattern': '^' + axis + ':[0-9]+$'}
    gene_metadata = {'type': 'object', 'properties': {'target_key': nullable(IDENTIFIER)}, 'additionalProperties': False}
    sample_metadata = {'type': 'object', 'properties': {'condition': nullable(UNIT),
        'biological_replicate': nullable(IDENTIFIER), 'technical_replicate': nullable(IDENTIFIER)}, 'additionalProperties': False}
    gene = dict(gene_position=COUNT, gene_key=key('gene'), gene_label=LABEL)
    sample = dict(sample_position=COUNT, sample_key=key('sample'), sample_label=LABEL)
    component = dict(component_position=COUNT, component_key=key('component'))
    rows = {
        'fit_diagnostics': obj(field={'enum': list(FIT_FIELDS)}, value=nullable(NUMBER), units=nullable(UNIT), denominator=nullable(NUMBER)),
        'gene_loadings': obj(**gene, gene_metadata=gene_metadata, **component, raw_loading=nullable(NUMBER),
            normalized_loading=nullable(NUMBER), loading_sum=nullable(NUMBER)),
        'sample_contributions': obj(**sample, sample_metadata=sample_metadata, **component,
            raw_coefficient=nullable(NUMBER), component_contribution=nullable(NUMBER), contribution_fraction=nullable(NUMBER),
            reconstructed_sample_total=nullable(NUMBER), units=nullable(UNIT)),
        'residual_cells': obj(**gene, **sample, raw_value=nullable(NUMBER), fit_value=nullable(NUMBER),
            reconstructed_value=nullable(NUMBER), signed_residual=nullable(NUMBER), units=nullable(UNIT)),
    }
    selector = deepcopy(SELECTOR_SCHEMA)
    selector['properties']['filter']['anyOf'][1]['properties']['field'] = {'enum': sorted({f for v in FILTER_FIELDS.values() for f in v})}
    return {'oneOf': [obj(schema={'const': 'expression_nmf_result_view_v1'}, view={'const': view},
        selector=selector, status={'enum': ['calculated', 'unavailable']},
        native_outcome={'enum': ['complete', 'qualified', 'partial', 'failed', 'rejected_input', None]},
        total_available_rows=COUNT, selected_row_count=COUNT, filtered_row_count=COUNT, row_offset=COUNT,
        returned_row_count=COUNT, has_more=BOOL, rows=arr(rows[view]), qualifications=arr(ISSUE_SCHEMA),
        failures=arr(ISSUE_SCHEMA), warning_codes=arr({'enum': ['iteration_limit_warning', 'native_warning']})) for view in VIEWS]}


def validate_projection(value):
    value = checked(value, projection_schema(), 'invalid_expression_nmf_projection')
    selected = validate_projection_selector(value['selector'])
    require(selected['view'] == value['view'] and value['row_offset'] == selected['row_window']['offset'],
        'expression_nmf_projection_selection_mismatch')
    expected = min(selected['row_window']['limit'], max(0, value['filtered_row_count'] - value['row_offset']))
    require(value['returned_row_count'] == len(value['rows']) == expected
        and value['filtered_row_count'] <= value['selected_row_count'] <= value['total_available_rows']
        and value['has_more'] is (value['row_offset'] + expected < value['filtered_row_count']),
        'expression_nmf_projection_extent_mismatch')
    for row in value['rows']:
        for axis in ('gene', 'sample', 'component'):
            if axis + '_key' in row:
                require(row[axis + '_key'] == axis + ':' + str(row[axis + '_position']), 'expression_nmf_projection_axis_mismatch')
                positions = selected.get(axis + '_positions')
                require(positions is None or row[axis + '_position'] in positions, 'expression_nmf_projection_selection_mismatch')
        if value['view'] == 'fit_diagnostics':
            require(row['field'] in selected['fields'], 'expression_nmf_projection_selection_mismatch')
    return value


def validate_expression_nmf_native_capture(value, *, original_plan):
    from pathlib import Path
    from .expression_nmf_common import digest
    from .native_expression_nmf_contracts import ARTIFACT_FORMATS, ARTIFACT_NAMES, validate_expression_nmf_run_plan
    plan = validate_expression_nmf_run_plan(original_plan)
    require(type(value) is dict and set(value) == {'version', 'original_plan_sha256', 'files',
        'source_action_receipt_ref', 'writer_closure_receipt_ref', 'driver_started', 'failures'}, 'invalid_nmf_native_capture')
    require(value['version'] == 'expression_nmf_native_capture_v1' and value['original_plan_sha256'] == digest(plan)
        and value['driver_started'] in (True, False, None), 'invalid_nmf_native_capture')
    require(type(value['files']) is list and [r.get('role') for r in value['files']] == list(ARTIFACT_NAMES), 'invalid_nmf_capture_roles')
    for row in value['files']:
        require(set(row) == {'role', 'relative_path', 'format', 'retained'} and row['relative_path'] ==
            plan['requested_job']['native_expression_nmf']['output_prefix'] + '/' + ARTIFACT_NAMES[row['role']]
            and row['format'] == ARTIFACT_FORMATS[row['role']], 'invalid_nmf_capture_roles')
        if row['retained'] is not None:
            require(set(row['retained']) == {'file', 'path'} and Path(row['retained']['path']).is_absolute(), 'invalid_nmf_retained_path')
            file = validate_file(row['retained']['file'])
            require(file['format'] == row['format'], 'invalid_nmf_capture_format')
    for name in ('source_action_receipt_ref', 'writer_closure_receipt_ref'):
        require(type(value[name]) is str and value[name].startswith('artifact_'), 'invalid_nmf_capture_receipt')
    for row in value['failures']:
        validate_issue(row)
    return deepcopy(value)

