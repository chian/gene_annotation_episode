"""Receiver-selected numerical rows from the complete retained NMF sheet."""
from copy import deepcopy

from .expression_nmf_common import CALCULATION_SCHEMA, digest, finite, require
from .expression_nmf_sheet import validate_nmf_sheet

FIT_FIELDS = ('native_reconstruction_error', 'native_n_iter', 'fit_call_count', 'sse', 'cell_count',
    'frobenius_residual', 'rmse', 'mae', 'relative_frobenius_residual', 'native_minus_calculated_frobenius')
VIEWS = ('fit_diagnostics', 'gene_loadings', 'sample_contributions', 'residual_cells')
_POSITIONS = {'type': 'array', 'items': {'type': 'integer', 'minimum': 0}, 'uniqueItems': True}
SELECTOR_SCHEMA = {'type': 'object', 'properties': {'view': {'enum': list(VIEWS)},
    'gene_positions': _POSITIONS, 'sample_positions': _POSITIONS, 'component_positions': _POSITIONS,
    'fields': {'type': 'array', 'items': {'enum': list(FIT_FIELDS)}, 'uniqueItems': True},
    'row_window': {'type': 'object', 'properties': {'offset': {'type': 'integer', 'minimum': 0},
        'limit': {'type': 'integer', 'minimum': 1}}, 'required': ['offset', 'limit'], 'additionalProperties': False},
    'filter': {'anyOf': [{'type': 'null'}, {'type': 'object', 'properties': {'field': {'type': 'string'},
        'minimum': {'type': 'number'}}, 'required': ['field', 'minimum'], 'additionalProperties': False}]}},
    'required': ['view', 'row_window'], 'additionalProperties': False}


def _positions(selector, field, count, *, required=False):
    require(not required or field in selector, 'nmf_occurrence_selector_required')
    values = selector.get(field, list(range(count)))
    require(type(values) is list and all(type(i) is int and 0 <= i < count for i in values)
        and len(values) == len(set(values)), 'invalid_nmf_position_selector')
    return values


def project_nmf_result(sheet: dict, calculations: dict, *, selector: dict) -> dict:
    validate_nmf_sheet(sheet)
    require(type(calculations) is dict and calculations.get('schema') == CALCULATION_SCHEMA
        and calculations.get('sheet_sha256') == digest(sheet), 'nmf_calculation_sheet_mismatch')
    require(type(selector) is dict and not set(selector) - set(SELECTOR_SCHEMA['properties'])
        and selector.get('view') in VIEWS, 'invalid_nmf_selector')
    view = selector['view']
    window = selector.get('row_window')
    require(type(window) is dict and set(window) == {'offset', 'limit'} and type(window['offset']) is int
        and window['offset'] >= 0 and type(window['limit']) is int and window['limit'] > 0, 'invalid_nmf_row_window')
    G, S, K = len(sheet['genes']), len(sheet['samples']), len(sheet['components'])
    genes = _positions(selector, 'gene_positions', G, required=view in ('gene_loadings', 'residual_cells'))
    samples = _positions(selector, 'sample_positions', S, required=view in ('sample_contributions', 'residual_cells'))
    components = _positions(selector, 'component_positions', K)
    require('fields' not in selector or view == 'fit_diagnostics', 'irrelevant_nmf_selector')
    require('gene_positions' not in selector or view in ('gene_loadings', 'residual_cells'), 'irrelevant_nmf_selector')
    require('sample_positions' not in selector or view in ('sample_contributions', 'residual_cells'), 'irrelevant_nmf_selector')
    require('component_positions' not in selector or view in ('gene_loadings', 'sample_contributions'), 'irrelevant_nmf_selector')
    c = calculations
    def cell(matrix, first, second):
        return matrix[first][second] if (type(matrix) is list and len(matrix) > first
            and type(matrix[first]) is list and len(matrix[first]) > second and finite(matrix[first][second])) else None
    def at(array, index):
        return array[index] if array is not None else None
    rows = []
    if view == 'fit_diagnostics':
        fields = selector.get('fields')
        require(type(fields) is list and len(fields) == len(set(fields)) and all(f in FIT_FIELDS for f in fields),
            'requested_nmf_diagnostic_fields_required')
        values = {**c, 'native_n_iter': sheet['native_diagnostics'].get('n_iter_'),
            'fit_call_count': sheet['native_diagnostics'].get('fit_call_count')}
        for field in fields:
            units = ('count' if field in ('cell_count', 'native_n_iter', 'fit_call_count') else
                'dimensionless' if field == 'relative_frobenius_residual' else
                c['units']['squared_error'] if field == 'sse' else sheet['fit_units'])
            denominator = c['cell_count'] if field in ('rmse', 'mae') else c['relative_frobenius_denominator'] if field == 'relative_frobenius_residual' else None
            rows.append({'field': field, 'value': values.get(field), 'units': units, 'denominator': denominator})
        available, filter_fields = len(FIT_FIELDS), {'value'}
    elif view == 'gene_loadings':
        for g in genes:
            for k in components:
                rows.append({'gene_position': g, 'gene_key': sheet['genes'][g]['key'], 'gene_label': sheet['genes'][g]['label'],
                    'gene_metadata': deepcopy(sheet['genes'][g]['metadata']), 'component_position': k,
                    'component_key': sheet['components'][k]['key'], 'raw_loading': cell(sheet['W'], g, k),
                    'normalized_loading': cell(c['normalized_gene_loadings'], g, k),
                    'loading_sum': at(c['component_loading_sums'], k)})
        available, filter_fields = G*K, {'raw_loading', 'normalized_loading'}
    elif view == 'sample_contributions':
        for s in samples:
            for k in components:
                rows.append({'sample_position': s, 'sample_key': sheet['samples'][s]['key'], 'sample_label': sheet['samples'][s]['label'],
                    'sample_metadata': deepcopy(sheet['samples'][s]['metadata']), 'component_position': k,
                    'component_key': sheet['components'][k]['key'], 'raw_coefficient': cell(sheet['H'], k, s),
                    'component_contribution': cell(c['sample_component_contributions'], k, s),
                    'contribution_fraction': cell(c['sample_component_fractions'], k, s),
                    'reconstructed_sample_total': at(c['sample_contribution_denominators'], s), 'units': sheet['fit_units']})
        available, filter_fields = S*K, {'raw_coefficient', 'component_contribution', 'contribution_fraction'}
    else:
        for g in genes:
            for s in samples:
                rows.append({'gene_position': g, 'gene_key': sheet['genes'][g]['key'], 'gene_label': sheet['genes'][g]['label'],
                    'sample_position': s, 'sample_key': sheet['samples'][s]['key'], 'sample_label': sheet['samples'][s]['label'],
                    'raw_value': cell(sheet['raw_matrix'], g, s), 'fit_value': cell(sheet['fit_matrix'], g, s),
                    'reconstructed_value': cell(c['reconstructed'], g, s), 'signed_residual': cell(c['residuals'], g, s),
                    'units': sheet['fit_units']})
        available, filter_fields = G*S, {'raw_value', 'fit_value', 'reconstructed_value', 'signed_residual'}
    selected_count = len(rows)
    threshold = selector.get('filter')
    if threshold is not None:
        require(type(threshold) is dict and set(threshold) == {'field', 'minimum'}
            and threshold['field'] in filter_fields and finite(threshold['minimum']), 'invalid_nmf_filter')
        rows = [r for r in rows if r[threshold['field']] is not None and r[threshold['field']] >= threshold['minimum']]
    filtered_count = len(rows)
    offset, limit = window['offset'], window['limit']
    returned = rows[offset:offset+limit]
    return {'schema': 'expression_nmf_result_view_v1', 'view': view, 'selector': deepcopy(selector),
        'status': c['status'], 'native_outcome': sheet['outcome'], 'total_available_rows': available,
        'selected_row_count': selected_count, 'filtered_row_count': filtered_count, 'row_offset': offset,
        'returned_row_count': len(returned), 'has_more': offset + len(returned) < filtered_count, 'rows': returned,
        'qualifications': deepcopy(c['qualifications']), 'failures': deepcopy(c['failures']),
        'warning_codes': [r['code'] for r in sheet['warnings'] if type(r) is dict and r.get('code') in
            ('iteration_limit_warning', 'native_warning')] if type(sheet['warnings']) is list else []}
