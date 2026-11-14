"""Pure CSV/TSV parsing, positional metadata joins and declared preprocessing.

Rows are gene occurrences and columns are sample occurrences, both zero-based
excluding the header/label column. Labels are never deduplicated or sorted.
All original cell tokens are retained, including rejected nonfinite tokens.
"""
from copy import deepcopy
import csv
import io
import math

from .expression_nmf_common import (INPUT_SCHEMA, PREPARED_SCHEMA, axis, axis_valid, canonical,
    digest, finite, identity, issue, matrix_valid, metadata_valid, require)


def parse_expression_matrix(raw: bytes, *, delimiter: str, metadata: dict | None = None) -> dict:
    require(type(raw) is bytes, 'expression_input_bytes_required')
    require(delimiter in (',', '\t'), 'explicit_csv_or_tsv_delimiter_required')
    require(metadata is None or type(metadata) is dict, 'expression_metadata_object_required')
    canonical(metadata)
    failures = []
    if not metadata_valid(metadata):
        failures.append(issue('invalid_metadata_schema', 'input', field='metadata'))
    result = {'schema': INPUT_SCHEMA, 'input_identity': identity(raw), 'delimiter': delimiter,
        'label_column_header': None, 'genes': [], 'samples': [], 'shape': [0, 0],
        'raw_cells': [], 'matrix': [], 'metadata': deepcopy(metadata),
        'units': (metadata or {}).get('units'), 'failures': failures, 'status': 'invalid'}
    if result['units'] is not None and (type(result['units']) is not str or not result['units']):
        failures.append(issue('invalid_units', 'input', field='metadata.units'))
    try:
        text = raw.decode('utf-8')
        rows = list(csv.reader(io.StringIO(text, newline=''), delimiter=delimiter, strict=True))
    except (UnicodeDecodeError, csv.Error):
        failures.append(issue('invalid_utf8_or_delimited_input', 'input'))
        return result
    if not rows or len(rows[0]) < 2 or len(rows) < 2:
        failures.append(issue('empty_expression_matrix', 'input'))
        return result
    header, records = rows[0], rows[1:]
    result['label_column_header'] = header[0]
    result['samples'] = axis(header[1:], 'sample')
    result['genes'] = axis([row[0] if row else '' for row in records], 'gene')
    result['shape'] = [len(records), len(header) - 1]
    for g, row in enumerate(records):
        cells = row[1:]
        result['raw_cells'].append(cells)
        if len(row) != len(header):
            failures.append(issue('nonrectangular_expression_row', 'input', gene_position=g))
        values = []
        for s, cell in enumerate(cells):
            try:
                value = float(cell)
            except ValueError:
                value = None
            if value is None or not math.isfinite(value):
                failures.append(issue('nonnumeric_expression_cell' if value is None else 'nonfinite_expression_cell',
                    'input', gene_position=g, sample_position=s))
                value = None
            values.append(value)
        result['matrix'].append(values)
    for name in ('genes', 'samples'):
        supplied = (metadata or {}).get(name, [])
        if type(supplied) is not list:
            failures.append(issue('invalid_axis_metadata', 'input', field='metadata.' + name))
            continue
        seen = set()
        for row in supplied:
            if type(row) is not dict or type(row.get('position')) is not int or not 0 <= row['position'] < len(result[name]):
                failures.append(issue('metadata_position_invalid', 'input', field='metadata.' + name))
                continue
            position = row['position']
            locator = {'gene_position' if name == 'genes' else 'sample_position': position}
            if position in seen or row.get('label') != result[name][position]['label']:
                failures.append(issue('metadata_occurrence_conflict', 'input', field='metadata.' + name, **locator))
            elif metadata_valid(metadata):
                result[name][position]['metadata'] = deepcopy({k: v for k, v in row.items() if k not in ('position', 'label')})
            seen.add(position)
    result['status'] = 'valid' if not failures else 'invalid'
    return result


def validate_expression_input(parsed):
    require(type(parsed) is dict and parsed.get('schema') == INPUT_SCHEMA, 'expression_input_schema_required')
    require(axis_valid(parsed.get('genes'), 'gene') and axis_valid(parsed.get('samples'), 'sample'),
        'expression_input_axis_mismatch')
    require(parsed.get('shape') == [len(parsed['genes']), len(parsed['samples'])], 'expression_input_shape_mismatch')
    require(type(parsed.get('failures')) is list, 'expression_input_failures_required')
    require(parsed.get('status') == ('invalid' if parsed['failures'] else 'valid'), 'expression_input_status_conflict')
    canonical(parsed)
    if not parsed['failures']:
        require(all(parsed['shape']) and matrix_valid(parsed.get('matrix'), *parsed['shape']), 'expression_input_matrix_invalid')
    return parsed


def prepare_expression_matrix(parsed: dict, *, normalization: str) -> dict:
    parsed = validate_expression_input(parsed)
    require(normalization in ('none', 'column_sum_1000'), 'unsupported_nmf_normalization')
    failures = deepcopy(parsed['failures'])
    result = {'schema': PREPARED_SCHEMA, 'input_identity': deepcopy(parsed['input_identity']),
        'input_data_sha256': digest(parsed), 'shape': deepcopy(parsed['shape']),
        'genes': deepcopy(parsed['genes']), 'samples': deepcopy(parsed['samples']),
        'raw_matrix': deepcopy(parsed['matrix']), 'fit_matrix': None, 'normalization': normalization,
        'column_denominators': [None] * len(parsed['samples']), 'raw_units': parsed['units'],
        'fit_units': parsed['units'] if normalization == 'none' else 'column_sum_scaled_to_1000',
        'failures': failures, 'qualifications': [], 'status': 'invalid'}
    if failures:
        return result
    matrix = parsed['matrix']
    denominators = []
    for s in range(parsed['shape'][1]):
        try:
            denominator = math.fsum(row[s] for row in matrix)
        except OverflowError:
            denominator = None
        denominators.append(denominator)
        if denominator is None and normalization == 'none':
            result['qualifications'].append(issue('unused_column_sum_overflow', 'preparation', sample_position=s))
    result['column_denominators'] = denominators
    if normalization == 'none':
        result['fit_matrix'] = deepcopy(matrix)
    else:
        for s, denominator in enumerate(denominators):
            if denominator == 0:
                failures.append(issue('zero_column_scaling_denominator', 'preparation', sample_position=s))
            elif not finite(denominator):
                failures.append(issue('nonfinite_column_denominator', 'preparation', sample_position=s))
        if not failures:
            fit = [[1000.0 * (value / denominators[s]) for s, value in enumerate(row)] for row in matrix]
            if not matrix_valid(fit, *parsed['shape']):
                failures.append(issue('nonfinite_normalized_value', 'preparation'))
            else:
                result['fit_matrix'] = fit
    result['status'] = 'invalid' if failures else 'valid'
    return result
