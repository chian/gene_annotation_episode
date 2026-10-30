"""Populate an NMF numerical sheet from supplied decoded native data.

This layer preserves observed/fitted numbers and associations. It never fits,
loads files, downloads inputs or calculates an annotation score. The separate
file loader is re-exported lazily only for the explicit acquisition caller.
"""
from copy import deepcopy

from .expression_nmf_common import (MODE, NATIVE_SCHEMA, PREPARED_SCHEMA, SHEET_SCHEMA,
    axis, axis_valid, canonical, digest, finite, fit_parameters, issue, matrix_valid,
    require, unique_issues, validate_parameters)
from .expression_nmf_inputs import prepare_expression_matrix, validate_expression_input


def _relations(input_data, prepared_data, native_result):
    failures = []
    try:
        validate_expression_input(input_data)
    except (ValueError, TypeError, KeyError):
        failures.append(issue('input_data_incompatible', 'sheet'))
    if type(prepared_data) is not dict or prepared_data.get('schema') != PREPARED_SCHEMA:
        failures.append(issue('prepared_data_incompatible', 'sheet'))
    else:
        try:
            expected = prepare_expression_matrix(input_data, normalization=prepared_data['normalization'])
            if digest(expected) != digest(prepared_data):
                failures.append(issue('prepared_input_relation_mismatch', 'sheet'))
        except (ValueError, TypeError, KeyError):
            failures.append(issue('prepared_input_relation_mismatch', 'sheet'))
    if type(native_result) is not dict or native_result.get('schema') != NATIVE_SCHEMA or native_result.get('mode') != MODE:
        failures.append(issue('native_result_incompatible', 'sheet'))
        return failures
    if (native_result.get('input_identity') != input_data.get('input_identity') or
            native_result.get('prepared_data_sha256') != digest(prepared_data)):
        failures.append(issue('native_input_relation_mismatch', 'sheet'))
    try:
        parameters = validate_parameters(native_result['parameters'])
        if (parameters['normalization'] != prepared_data.get('normalization') or
                native_result.get('estimator_parameters') != fit_parameters(parameters)):
            failures.append(issue('native_parameter_relation_mismatch', 'sheet'))
        components = axis([f'component_{k}' for k in range(parameters['rank'])], 'component')
    except (ValueError, TypeError, KeyError):
        failures.append(issue('native_parameters_invalid', 'sheet'))
        return failures
    axes = {'genes': [r['key'] for r in input_data.get('genes', [])] if axis_valid(input_data.get('genes'), 'gene') else [],
        'samples': [r['key'] for r in input_data.get('samples', [])] if axis_valid(input_data.get('samples'), 'sample') else [],
        'components': [r['key'] for r in components]}
    if native_result.get('axes') != axes or native_result.get('components') != components:
        failures.append(issue('factor_axis_association_mismatch', 'sheet'))
    G, S, K = len(axes['genes']), len(axes['samples']), parameters['rank']
    for name, rows, columns in (('W', G, K), ('H', K, S)):
        factor = native_result.get(name)
        if factor is None:
            failures.append(issue('factor_missing', 'sheet', field=name))
        elif not matrix_valid(factor, rows, columns, nonnegative=True):
            failures.append(issue('factor_shape_or_values_incompatible', 'sheet', field=name))
    source = native_result.get('source')
    if not (type(source) is dict and source.get('kind') in ('sklearn_fit', 'supplied_factor_fixture')
            and source.get('estimator') == 'sklearn.decomposition.NMF'
            and (source['kind'] != 'sklearn_fit' or type(source.get('versions')) is dict
                and type(source['versions'].get('scikit-learn')) is str)):
        failures.append(issue('native_source_missing_or_incompatible', 'sheet'))
    diagnostics = native_result.get('diagnostics', {})
    if type(diagnostics) is not dict:
        failures.append(issue('native_diagnostics_incompatible', 'sheet'))
        diagnostics = {}
    for name in ('reconstruction_err_', 'n_iter_'):
        value = diagnostics.get(name)
        if value is None:
            continue
        if not finite(value) or value < 0 or (name == 'n_iter_' and (type(value) is not int or value > parameters['max_iter'])):
            failures.append(issue('native_diagnostic_invalid', 'sheet', field=name))
    outcome = native_result.get('outcome')
    if outcome not in ('complete', 'qualified', 'partial', 'failed', 'rejected_input'):
        failures.append(issue('native_outcome_invalid', 'sheet'))
    if outcome in ('failed', 'rejected_input'):
        failures.append(issue('native_factorization_unavailable', 'sheet'))
    if not (type(native_result.get('warnings')) is list and all(type(w) is dict and set(w) == {'category', 'code', 'message'}
            and all(type(v) is str for v in w.values()) and w['code'] in ('iteration_limit_warning', 'native_warning')
            for w in native_result['warnings'])):
        failures.append(issue('native_warning_records_invalid', 'sheet'))
    if matrix_valid(input_data.get('matrix'), G, S) and any(v < 0 for row in input_data['matrix'] for v in row):
        failures.append(issue('negative_input_not_nmf_compatible', 'sheet'))
    return failures


def populate_nmf_sheet(*, input_data: dict, prepared_data: dict, native_result: dict) -> dict:
    require(all(type(value) is dict for value in (input_data, prepared_data, native_result)), 'decoded_nmf_artifact_objects_required')
    canonical([input_data, prepared_data, native_result])
    failures = unique_issues(input_data.get('failures', []), prepared_data.get('failures', []),
        native_result.get('failures', []), _relations(input_data, prepared_data, native_result))
    diagnostics = native_result.get('diagnostics') if type(native_result.get('diagnostics')) is dict else {}
    result = {'schema': SHEET_SCHEMA, 'mode': MODE, 'input_data': deepcopy(input_data),
        'prepared_data': deepcopy(prepared_data), 'native_result': deepcopy(native_result),
        'input_identity': deepcopy(input_data.get('input_identity')), 'shape': deepcopy(input_data.get('shape', [0, 0])),
        'genes': deepcopy(input_data.get('genes', [])), 'samples': deepcopy(input_data.get('samples', [])),
        'components': deepcopy(native_result.get('components', [])), 'raw_matrix': deepcopy(input_data.get('matrix')),
        'fit_matrix': deepcopy(prepared_data.get('fit_matrix')), 'W': deepcopy(native_result.get('W')),
        'H': deepcopy(native_result.get('H')), 'raw_units': input_data.get('units'),
        'fit_units': prepared_data.get('fit_units'), 'normalization': prepared_data.get('normalization'),
        'column_denominators': deepcopy(prepared_data.get('column_denominators')),
        'preparation_qualifications': deepcopy(prepared_data.get('qualifications', [])),
        'metadata': deepcopy(input_data.get('metadata')), 'parameters': deepcopy(native_result.get('parameters')),
        'native_diagnostics': deepcopy(diagnostics),
        'warnings': deepcopy(native_result.get('warnings', [])), 'outcome': native_result.get('outcome'),
        'source': deepcopy(native_result.get('source')), 'failures': failures,
        'missing_fields': [name for name, value in (('W', native_result.get('W')), ('H', native_result.get('H')),
            ('native.reconstruction_err_', diagnostics.get('reconstruction_err_')),
            ('native.n_iter_', diagnostics.get('n_iter_')), ('units', input_data.get('units')))
            if value is None], 'calculation_eligible': not failures,
        'uncertainty': None, 'measurement_kinds': {'raw_matrix': 'supplied_measurements',
            'fit_matrix': 'supplied_measurements' if prepared_data.get('normalization') == 'none' else 'normalized_measurements',
            'W': 'fitted_factor', 'H': 'fitted_factor', 'native_diagnostics': 'native_fit_diagnostics'}}
    return result


def validate_nmf_sheet(sheet):
    """Validate saved operand joins without reparsing original files or fitting."""
    require(type(sheet) is dict and sheet.get('schema') == SHEET_SCHEMA and sheet.get('mode') == MODE, 'nmf_sheet_required')
    inp, prep, native = (sheet[k] for k in ('input_data', 'prepared_data', 'native_result'))
    mirrors = {'input_identity': inp.get('input_identity'), 'shape': inp.get('shape', [0, 0]),
        'genes': inp.get('genes', []), 'samples': inp.get('samples', []), 'components': native.get('components', []),
        'raw_matrix': inp.get('matrix'), 'fit_matrix': prep.get('fit_matrix'), 'W': native.get('W'), 'H': native.get('H'),
        'raw_units': inp.get('units'), 'fit_units': prep.get('fit_units'), 'normalization': prep.get('normalization'),
        'column_denominators': prep.get('column_denominators'), 'metadata': inp.get('metadata'),
        'preparation_qualifications': prep.get('qualifications', []),
        'parameters': native.get('parameters'), 'native_diagnostics': native.get('diagnostics') if type(native.get('diagnostics')) is dict else {},
        'warnings': native.get('warnings', []), 'outcome': native.get('outcome'), 'source': native.get('source')}
    require(all(canonical(sheet.get(k)) == canonical(v) for k, v in mirrors.items()), 'nmf_saved_sheet_operand_conflict')
    failures = unique_issues(inp.get('failures', []), prep.get('failures', []), native.get('failures', []), _relations(inp, prep, native))
    require(sheet.get('failures') == failures and sheet.get('calculation_eligible') is (not failures), 'nmf_saved_sheet_validation_conflict')
    return sheet


def load_expression_nmf_artifacts(manifest_path, *, expected_input_identity=None):
    """Explicit file-based loader, separate from the pure population function."""
    from .expression_nmf_artifacts import load_expression_nmf_artifacts as load
    return load(manifest_path, expected_input_identity=expected_input_identity)
