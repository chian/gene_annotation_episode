"""Source-free TF input decoding and retained Biopython score measurements.

Native model construction/scoring and all I/O belong to the selected producer.
Original File locators are distinct from genuine captured native locations.
"""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import base64
import hashlib
import json
import math
import re
import struct
import sys

from .blast_fasta_record_identity import parse_blast_fasta_source_records
from .bvbrc_alignment_values import diagnostic, numeric_cell, validate_numeric_cell
from .domain import ContractError, parse_sequences
from . import phylogeny_calculation_contracts as locations


OPERATION = 'identify_transcription_factor_binding_sites'
NUMERIC_CONVENTION = 'numpy_array_compare_pythonfloat_scalar_relative_v1'
SHEET_VERSION = 'tf_binding_sheet_v1'
COMPONENTS_VERSION = 'tf_binding_components_v1'
RETURN_VERSION = 'tf_binding_return_v1'
_BASES = 'ACGT'
_HEX = re.compile(r'[a-f0-9]{64}\Z')
_NUMBER = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z', re.ASCII)
_JSON_LEX = re.compile(r'"(?:\\[\s\S]|[^"\\])*"|(?P<number>-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)', re.ASCII)


def _need(condition, code):
    if not condition:
        raise ValueError('tf_binding_' + code)


def _shape(value, keys, code='shape_invalid'):
    _need(type(value) is dict and set(value) == set(keys), code)


def _text(value, *, nullable=False):
    _need(nullable and value is None or type(value) is str and bool(value), 'text_invalid')


def _integer(value, *, nullable=False):
    _need(nullable and value is None or type(value) is int and value >= 0, 'integer_invalid')


def _finite(value):
    return type(value) is int or type(value) is float and math.isfinite(value)


def _hash(value):
    _need(type(value) is str and _HEX.fullmatch(value) is not None, 'digest_invalid')


def _same(first, second):
    return json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(second, sort_keys=True, allow_nan=False)


def _id(kind, values):
    raw = json.dumps(values, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return 'tf_' + kind + '_' + hashlib.sha256(raw).hexdigest()


def tf_binding_issue(code, *, path='', severity='qualification'):
    return diagnostic(code if code.startswith('tf_binding_') else 'tf_binding_' + code,
        phase='native_decode', path=path, severity=severity)


def _issues(values):
    _need(type(values) is list, 'issues_invalid')
    for value in values:
        _shape(value, ('code', 'phase', 'path', 'severity', 'evidence_refs'))
        _text(value['code'])
        _need(value['phase'] in ('custody', 'prepare', 'transport', 'native_decode', 'association', 'publication', 'recovery', 'return'), 'issue_phase_invalid')
        _need(type(value['path']) is str and (not value['path'] or value['path'].startswith('/')), 'issue_path_invalid')
        _need(value['severity'] in ('error', 'qualification') and type(value['evidence_refs']) is list, 'issue_invalid')
        for ref in value['evidence_refs']:
            _text(ref)


def _selection(value):
    _need(type(value) is dict, 'scan_selection_invalid')
    if value.get('mode') == 'all_supplied_occurrences_both_strands':
        _shape(value, ('mode',))
    else:
        _shape(value, ('mode', 'requests'))
        _need(value['mode'] == 'explicit' and type(value['requests']) is list, 'scan_selection_invalid')
        for row in value['requests']:
            _shape(row, ('sequence_input_id', 'sequence_record_ordinal_0based', 'matrix_input_id', 'matrix_record_ordinal_0based', 'strands'))
            _text(row['sequence_input_id']); _text(row['matrix_input_id'])
            _integer(row['sequence_record_ordinal_0based']); _integer(row['matrix_record_ordinal_0based'])
            _need(type(row['strands']) is list and bool(row['strands']) and len(set(row['strands'])) == len(row['strands']) and all(v in ('+', '-') for v in row['strands']), 'strand_selection_invalid')
    return deepcopy(value)


def _parameters(value):
    _shape(value, ('background', 'pseudocounts'))
    for field in ('background', 'pseudocounts'):
        _shape(value[field], _BASES)
        _need(all(_finite(v) and v >= 0 for v in value[field].values()), 'parameter_number_invalid')
    # Native normalization owns a zero-total failure; it is never repaired.


def validate_tf_binding_invocation(value):
    _shape(value, ('version', 'invocation_id', 'operation', 'scan_selection', 'parameters', 'software'))
    _need(value['version'] == 'tf_binding_invocation_v1' and value['operation'] == OPERATION, 'invocation_version_invalid')
    _text(value['invocation_id']); _selection(value['scan_selection']); _parameters(value['parameters'])
    _need(type(value['software']) is list, 'software_invalid')
    for row in value['software']:
        _shape(row, ('name', 'version', 'sha256'))
        _text(row['name']); _text(row['version'], nullable=True)
        if row['sha256'] is not None: _hash(row['sha256'])
    return deepcopy(value)


def _buffer(value, *, shape=None):
    _shape(value, ('dtype', 'byte_order', 'shape', 'data_base64', 'sha256', 'size_bytes'))
    _need(value['dtype'] == 'float64' and value['byte_order'] in ('little', 'big'), 'model_buffer_dtype_invalid')
    _need(type(value['shape']) is list and bool(value['shape']) and all(type(n) is int and n > 0 for n in value['shape']), 'model_buffer_shape_invalid')
    if shape is not None: _need(value['shape'] == shape, 'model_buffer_shape_conflict')
    _need(type(value['data_base64']) is str, 'base64_invalid')
    try: raw = base64.b64decode(value['data_base64'], validate=True)
    except (ValueError, TypeError) as error: raise ValueError('tf_binding_base64_invalid') from error
    _need(base64.b64encode(raw).decode('ascii') == value['data_base64'], 'base64_noncanonical')
    _hash(value['sha256']); _integer(value['size_bytes'])
    _need(len(raw) == value['size_bytes'] == 8 * math.prod(value['shape']) and hashlib.sha256(raw).hexdigest() == value['sha256'], 'model_buffer_identity_conflict')
    return raw


def _spec(value):
    _shape(value, ('scan_id', 'sequence_id', 'matrix_occurrence_id', 'model_id', 'strand', 'possible_positions'))
    for field in ('scan_id', 'sequence_id', 'matrix_occurrence_id', 'model_id'): _text(value[field])
    _need(value['strand'] in ('+', '-'), 'strand_invalid'); _integer(value['possible_positions'], nullable=True)


def validate_tf_binding_native_value(value):
    _shape(value, ('version', 'invocation_id', 'operation', 'scan_selection', 'biopython_version', 'numpy_version', 'numeric_convention', 'parameters', 'input_identities', 'outcome', 'returncode', 'models', 'scans', 'issues'))
    _need(value['version'] == 'tf_binding_native_result_v1' and value['operation'] == OPERATION and value['numeric_convention'] == NUMERIC_CONVENTION, 'native_version_invalid')
    for key in ('invocation_id', 'biopython_version', 'numpy_version'): _text(value[key])
    _selection(value['scan_selection']); _parameters(value['parameters']); _issues(value['issues'])
    _need(value['outcome'] in ('succeeded', 'failed', 'not_run', 'unknown') and value['returncode'] is None, 'native_outcome_invalid')
    _need(type(value['input_identities']) is list and type(value['models']) is list and type(value['scans']) is list, 'native_rows_invalid')
    for row in value['input_identities']:
        _shape(row, ('input_id', 'artifact_ref', 'sha256', 'size_bytes'))
        _text(row['input_id']); _hash(row['sha256']); _integer(row['size_bytes'])
        _need(row['artifact_ref'] == 'artifact_' + row['sha256'], 'input_artifact_identity_conflict')
    _need(len({r['input_id'] for r in value['input_identities']}) == len(value['input_identities']), 'duplicate_input_id')
    for row in value['models']:
        _shape(row, ('model_id', 'matrix_occurrence_id', 'state', 'length', 'reverse_convention', 'buffers', 'failure_code'))
        _text(row['model_id']); _text(row['matrix_occurrence_id']); _integer(row['length'], nullable=True); _text(row['failure_code'], nullable=True)
        _need(row['state'] in ('available', 'unavailable') and row['reverse_convention'] == 'computed_pssm_reverse_complement_v1', 'model_state_invalid')
        if row['state'] == 'unavailable':
            _need(row['buffers'] is None and row['failure_code'] is not None, 'model_unavailable_conflict')
        else:
            _need(type(row['length']) is int and row['length'] > 0 and row['failure_code'] is None, 'model_length_invalid')
            _shape(row['buffers'], ('counts', 'background', 'pseudocounts', 'pwm', 'pssm', 'rc_pssm', 'bounds_plus', 'bounds_minus'))
            for field, blob in row['buffers'].items():
                shape = [2] if field.startswith('bounds_') else [4] if field in ('background', 'pseudocounts') else [4, row['length']]
                _buffer(blob, shape=shape)
    _need(len({r['model_id'] for r in value['models']}) == len(value['models']), 'duplicate_model_id')
    for row in value['scans']:
        _shape(row, ('scan_id', 'sequence_id', 'matrix_occurrence_id', 'model_id', 'strand', 'possible_positions', 'state', 'score_file_id', 'dtype', 'byte_order', 'declared_count', 'sha256', 'size_bytes', 'failure_code'))
        _spec({k: row[k] for k in ('scan_id', 'sequence_id', 'matrix_occurrence_id', 'model_id', 'strand', 'possible_positions')})
        _need(row['state'] in ('complete', 'partial', 'zero_possible', 'unavailable') and row['dtype'] == 'float32' and row['byte_order'] in ('little', 'big'), 'scan_state_invalid')
        _integer(row['declared_count'], nullable=True); _integer(row['size_bytes'], nullable=True); _text(row['failure_code'], nullable=True); _text(row['score_file_id'], nullable=True)
        if row['score_file_id'] is None:
            _need(row['sha256'] is None and row['size_bytes'] is None and row['state'] == 'unavailable' and row['failure_code'] is not None, 'scan_missing_file_conflict')
        else:
            _hash(row['sha256']); _need(type(row['size_bytes']) is int, 'scan_file_identity_invalid')
        if row['state'] == 'zero_possible':
            _need(row['possible_positions'] == row['declared_count'] == row['size_bytes'] == 0, 'zero_possible_conflict')
    _need(len({r['scan_id'] for r in value['scans']}) == len(value['scans']), 'duplicate_scan_id')
    return deepcopy(value)


def _capture(value, retained_size):
    _shape(value, ('state', 'byte_start_0based', 'byte_end_0based_exclusive', 'original_size_bytes'))
    _need(value['state'] in ('complete', 'truncated', 'missing') and type(value['byte_start_0based']) is int and value['byte_start_0based'] == 0, 'capture_invalid')
    _integer(value['byte_end_0based_exclusive']); _integer(value['original_size_bytes'], nullable=True)
    _need(value['byte_end_0based_exclusive'] == retained_size, 'capture_size_conflict')
    if value['state'] == 'missing': _need(retained_size == 0, 'missing_capture_has_bytes')
    _need(value['original_size_bytes'] is None or value['original_size_bytes'] >= retained_size, 'capture_size_conflict')
    if value['state'] == 'complete': _need(value['original_size_bytes'] in (None, retained_size), 'capture_size_conflict')


def _input(value):
    _shape(value, ('input_id', 'role', 'format', 'content', 'artifact', 'capture'))
    _text(value['input_id']); _need(value['role'] in ('dna', 'matrix'), 'input_role_invalid')
    _need(value['format'] in (('fasta', 'raw_dna') if value['role'] == 'dna' else ('jaspar_json', 'jaspar_pfm', 'acgt_count_json')), 'input_format_invalid')
    a = value['artifact']; _shape(a, ('artifact_ref', 'sha256', 'size_bytes', 'source_ref'))
    _hash(a['sha256']); _integer(a['size_bytes']); _text(a['source_ref'], nullable=True)
    _need(a['artifact_ref'] == 'artifact_' + a['sha256'], 'input_artifact_identity_conflict')
    content = value['content']; _need(content is None or type(content) is bytes, 'input_bytes_required')
    size = 0 if content is None else len(content); _capture(value['capture'], size)
    _need((content is None) == (value['capture']['state'] == 'missing'), 'input_missing_conflict')
    if content is None: _need(value['capture']['state'] == 'missing', 'input_missing_conflict')
    else: _need(a['size_bytes'] == size and hashlib.sha256(content).hexdigest() == a['sha256'], 'input_bytes_identity_conflict')
    return deepcopy(value)


def _locator(item, start, end, line_start=None, line_end=None, pointer=None):
    return {'input_id': item['input_id'], 'artifact_ref': item['artifact']['artifact_ref'], 'sha256': item['artifact']['sha256'],
        'byte_start_0based': start, 'byte_end_0based_exclusive': end, 'line_start_1based': line_start,
        'line_end_1based_inclusive': line_end, 'json_pointer': pointer}


def _validate_locator(value, inputs):
    _shape(value, ('input_id', 'artifact_ref', 'sha256', 'byte_start_0based', 'byte_end_0based_exclusive', 'line_start_1based', 'line_end_1based_inclusive', 'json_pointer'))
    _need(value['input_id'] in inputs, 'locator_input_unknown'); a = inputs[value['input_id']]['artifact']
    _need(value['artifact_ref'] == a['artifact_ref'] and value['sha256'] == a['sha256'], 'locator_identity_conflict')
    _integer(value['byte_start_0based']); _integer(value['byte_end_0based_exclusive'])
    _need(value['byte_start_0based'] <= value['byte_end_0based_exclusive'] <= a['size_bytes'], 'locator_range_invalid')
    for key in ('line_start_1based', 'line_end_1based_inclusive'):
        _need(value[key] is None or type(value[key]) is int and value[key] >= 1, 'locator_line_invalid')
    _need((value['line_start_1based'] is None) == (value['line_end_1based_inclusive'] is None), 'locator_line_invalid')
    _need(value['line_start_1based'] is None or value['line_start_1based'] <= value['line_end_1based_inclusive'], 'locator_line_invalid')
    _need(value['json_pointer'] is None or type(value['json_pointer']) is str and (not value['json_pointer'] or value['json_pointer'].startswith('/')), 'locator_pointer_invalid')


def _sequence_rows(item):
    content = item['content']; rows, issues = [], []
    if content is None:
        return rows, [tf_binding_issue('input_bytes_missing')]
    if item['format'] == 'fasta':
        parsed = parse_blast_fasta_source_records(content)
        issues += [tf_binding_issue(code) for code in parsed['issues']]
        source_rows = parsed['records']
    else:
        try:
            parsed, = parse_sequences(content, format='raw', molecule='unspecified')
            source_rows = [{'record_ordinal': 0, 'byte_start': 0, 'byte_end': len(content), 'header': None,
                'symbols': parsed.sequence, 'sequence_sha256': hashlib.sha256(parsed.sequence.encode('ascii')).hexdigest(),
                'sequence_length': len(parsed.sequence), 'status': 'available', 'issues': []}]
        except ContractError as error:
            source_rows = [{'record_ordinal': 0, 'byte_start': 0, 'byte_end': len(content), 'header': None,
                'symbols': None, 'sequence_sha256': None, 'sequence_length': None, 'status': 'incompatible', 'issues': [str(error)]}]
    for position, row in enumerate(source_rows):
        header = row['header']; state = 'available' if row['status'] == 'available' else 'unavailable'
        ri = [tf_binding_issue(code) for code in row['issues']]
        if item['capture']['state'] != 'complete' and position == len(source_rows) - 1:
            state = 'unavailable'; ri.append(tf_binding_issue('input_final_record_truncated'))
        symbols = row['symbols']
        if symbols is not None and set(symbols) - set('ACGT'):
            ri.append(tf_binding_issue('native_non_acgt_windows_are_nan'))
        ordinal = row['record_ordinal']
        rows.append({'sequence_id': _id('sequence', [item['input_id'], item['artifact']['sha256'], ordinal]),
            'input_id': item['input_id'], 'record_ordinal_0based': ordinal, 'raw_header': header,
            'identifier': header.split()[0] if header and header.split() else None, 'symbols': symbols,
            'symbols_sha256': row['sequence_sha256'], 'length': row['sequence_length'], 'state': state,
            'locator': _locator(item, row['byte_start'], row['byte_end']), 'issues': ri})
    return rows, issues


class _ObjectPairs(list):
    pass


class _JsonNumber:
    def __init__(self, raw, start, end):
        self.raw, self.start, self.end = raw, start, end


def _json_input(content):
    text = content.decode('utf-8'); numbers = [m for m in _JSON_LEX.finditer(text) if m.group('number') is not None]; cursor = 0
    offsets = [0]
    for char in text: offsets.append(offsets[-1] + len(char.encode('utf-8')))
    def token(raw):
        nonlocal cursor
        match = numbers[cursor]; cursor += 1
        _need(match.group() == raw, 'json_token_conflict')
        return _JsonNumber(raw, offsets[match.start()], offsets[match.end()])
    def constant(raw): raise ValueError('tf_binding_non_json_number')
    return json.loads(text, parse_int=token, parse_float=token, parse_constant=constant, object_pairs_hook=_ObjectPairs)


def _member(value, key):
    if not isinstance(value, _ObjectPairs): return None
    matches = [v for k, v in value if k == key]
    return matches[0] if len(matches) == 1 else None


def _matrix_record(item, ordinal, start, end, header, raw_rows, *, native_id=None, name=None):
    issues = []; counts = {}; length = None
    for row in raw_rows:
        base = row['base']
        if base not in tuple(_BASES) or base in counts:
            issues.append(tf_binding_issue('matrix_row_binding_ambiguous')); continue
        counts[base] = row['tokens']
    valid = len(raw_rows) == 4 and set(counts) == set(_BASES) and all(counts[b] for b in _BASES)
    if valid:
        length = len(counts['A']); valid = all(len(counts[b]) == length for b in _BASES)
    if not valid: issues.append(tf_binding_issue('matrix_rows_incomplete_or_inconsistent'))
    key = _id('matrix', [item['input_id'], item['artifact']['sha256'], ordinal])
    return {'matrix_occurrence_id': key, 'model_id': _id('model', [key]), 'input_id': item['input_id'],
        'record_ordinal_0based': ordinal, 'raw_header': header, 'native_matrix_id': native_id, 'name': name,
        'alphabet': _BASES, 'length': length, 'rows': raw_rows, 'count_tokens': counts if valid else None,
        'state': 'available' if valid else 'unavailable', 'locator': _locator(item, start, end), 'issues': issues}


def _matrix_json(item):
    content = item['content']; rows = []; issues = []; native_id = name = None
    try:
        document = _json_input(content)
        root = _member(document, 'pfm') if item['format'] == 'jaspar_json' else document
        if item['format'] == 'jaspar_json':
            native_id, name = _member(document, 'matrix_id'), _member(document, 'name')
            _need(native_id is None or type(native_id) is str, 'matrix_label_invalid')
            _need(name is None or type(name) is str, 'matrix_label_invalid')
        _need(isinstance(root, _ObjectPairs), 'matrix_json_object_required')
        for ordinal, (base, values) in enumerate(root):
            tokens = []; pointer = ('/pfm' if item['format'] == 'jaspar_json' else '') + '/' + str(base).replace('~', '~0').replace('/', '~1')
            if type(values) is not list:
                issues.append(tf_binding_issue('matrix_json_row_not_array', path=pointer))
            else:
                for column, value in enumerate(values):
                    if not isinstance(value, _JsonNumber):
                        issues.append(tf_binding_issue('matrix_json_count_not_number', path=pointer + '/' + str(column))); continue
                    tokens.append({'raw_token': value.raw, 'locator': _locator(item, value.start, value.end, pointer=pointer + '/' + str(column))})
            rows.append({'row_ordinal_0based': ordinal, 'base': base if base in tuple(_BASES) else None,
                'raw_text': None, 'tokens': tokens, 'locator': _locator(item, 0, len(content), pointer=pointer)})
    except (ValueError, UnicodeError, IndexError, TypeError) as error:
        issues.append(tf_binding_issue('matrix_json_unavailable', severity='error'))
    record = _matrix_record(item, 0, 0, len(content), None, rows, native_id=native_id, name=name)
    record['issues'] += issues
    if issues or item['capture']['state'] != 'complete': record['state'], record['count_tokens'] = 'unavailable', None
    return [record]


def _matrix_pfm(item):
    content = item['content']; text = content.decode('utf-8'); lines = []; offset = 0
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        body = line.rstrip('\r\n'); lines.append((offset, offset + len(line.encode()), number, body)); offset += len(line.encode())
    headers = [i for i, row in enumerate(lines) if row[3].strip().startswith('>')]
    if headers:
        slots = [(start, headers[i + 1] if i + 1 < len(headers) else len(lines)) for i, start in enumerate(headers)]
        prefix = [i for i in range(headers[0]) if lines[i][3].strip()]
        slots = [(prefix[i], prefix[i + 4] if i + 4 < len(prefix) else headers[0]) for i in range(0, len(prefix), 4)] + slots
    else:
        nonempty = [i for i, row in enumerate(lines) if row[3].strip()]
        slots = [(nonempty[i], nonempty[min(i + 4, len(nonempty))] if i + 4 < len(nonempty) else len(lines)) for i in range(0, len(nonempty), 4)]
    result = []
    for ordinal, (start, end) in enumerate(slots):
        header = lines[start][3] if lines[start][3].strip().startswith('>') else None; words = header.lstrip()[1:].split(maxsplit=1) if header else []
        rows = []
        for line in lines[start + (1 if header is not None else 0):end]:
            if not line[3].strip(): continue
            match = re.fullmatch(r'\s*([ACGT])\s*\[\s*(.*?)\s*\]\s*', line[3])
            base, field, shift = (match.group(1), match.group(2), match.start(2)) if match else (_BASES[len(rows)] if len(rows) < 4 else None, line[3], 0)
            tokens = []
            for value in re.finditer(r'\S+', field):
                a = line[0] + len(line[3][:shift + value.start()].encode()); b = line[0] + len(line[3][:shift + value.end()].encode())
                tokens.append({'raw_token': value.group(), 'locator': _locator(item, a, b, line[2], line[2])})
            rows.append({'row_ordinal_0based': len(rows), 'base': base, 'raw_text': line[3], 'tokens': tokens,
                'locator': _locator(item, line[0], line[1], line[2], line[2])})
        record = _matrix_record(item, ordinal, lines[start][0], lines[end - 1][1], header, rows,
            native_id=words[0] if words else None, name=words[1] if len(words) == 2 else None)
        if header is not None and not words:
            record['state'], record['count_tokens'] = 'unavailable', None; record['issues'].append(tf_binding_issue('matrix_header_empty'))
        if item['capture']['state'] != 'complete' and ordinal == len(slots) - 1:
            record['state'], record['count_tokens'] = 'unavailable', None; record['issues'].append(tf_binding_issue('matrix_final_record_truncated'))
        result.append(record)
    return result


def decode_tf_binding_inputs(inputs):
    _need(type(inputs) is list, 'inputs_invalid'); checked = [_input(v) for v in inputs]
    _need(len({v['input_id'] for v in checked}) == len(checked), 'duplicate_input_id')
    sequences, matrices, issues = [], [], []
    for item in checked:
        if item['role'] == 'dna':
            rows, ri = _sequence_rows(item); sequences += rows; issues += ri
        elif item['content'] is None:
            issues.append(tf_binding_issue('matrix_bytes_missing'))
        else:
            try:
                rows = _matrix_json(item) if item['format'] != 'jaspar_pfm' else _matrix_pfm(item)
                matrices += rows
                if not rows: issues.append(tf_binding_issue('matrix_input_empty', severity='error'))
            except UnicodeError: issues.append(tf_binding_issue('matrix_input_not_utf8', severity='error'))
    specs = []
    for sequence in sequences:
        for matrix in matrices:
            n, m = sequence['length'], matrix['length']
            possible = max(0, n - m + 1) if n is not None and m is not None and sequence['state'] == matrix['state'] == 'available' else None
            for strand in ('+', '-'):
                specs.append({'scan_id': _id('scan', [sequence['sequence_id'], matrix['model_id'], strand]),
                    'sequence_id': sequence['sequence_id'], 'matrix_occurrence_id': matrix['matrix_occurrence_id'],
                    'model_id': matrix['model_id'], 'strand': strand, 'possible_positions': possible})
    return {'version': 'tf_binding_decoded_inputs_v1', 'inputs': [{k: deepcopy(v) for k, v in item.items() if k != 'content'} for item in checked],
        'sequences': sequences, 'matrices': matrices, 'scan_specs': specs, 'issues': issues}


def resolve_tf_binding_scan_selection(decoded, selection):
    selection = _selection(selection)
    if selection['mode'] == 'all_supplied_occurrences_both_strands': return deepcopy(decoded['scan_specs'])
    seq = {(v['input_id'], v['record_ordinal_0based']): v['sequence_id'] for v in decoded['sequences']}
    mat = {(v['input_id'], v['record_ordinal_0based']): v['matrix_occurrence_id'] for v in decoded['matrices']}
    specs = {(v['sequence_id'], v['matrix_occurrence_id'], v['strand']): v for v in decoded['scan_specs']}; selected = []
    for row in selection['requests']:
        sk = (row['sequence_input_id'], row['sequence_record_ordinal_0based']); mk = (row['matrix_input_id'], row['matrix_record_ordinal_0based'])
        _need(sk in seq and mk in mat, 'selected_original_occurrence_missing')
        selected += [deepcopy(specs[(seq[sk], mat[mk], strand)]) for strand in row['strands']]
    _need(len({v['scan_id'] for v in selected}) == len(selected), 'duplicate_selected_scan')
    return selected


def _file(value):
    _shape(value, ('file_id', 'role', 'content', 'artifact', 'capture'))
    _text(value['file_id']); _need(value['role'] in ('native_result', 'scores', 'native_log'), 'file_role_invalid')
    content = value['content']; _need(content is None or type(content) is bytes, 'file_bytes_invalid')
    _capture(value['capture'], 0 if content is None else len(content))
    _need((content is None) == (value['capture']['state'] == 'missing'), 'missing_file_conflict')
    if content is None:
        _need(value['artifact'] is None and value['capture']['state'] == 'missing', 'missing_file_conflict')
    else:
        a = value['artifact']; _shape(a, ('raw_artifact_ref', 'source_ref', 'sha256', 'size_bytes'))
        _text(a['source_ref']); _hash(a['sha256']); _integer(a['size_bytes'])
        _need(a['raw_artifact_ref'] == 'artifact_' + a['sha256'] and a['size_bytes'] == len(content)
            and hashlib.sha256(content).hexdigest() == a['sha256'], 'captured_file_identity_conflict')
    return deepcopy(value)


def _metadata(value):
    return {k: deepcopy(v) for k, v in value.items() if k != 'content'}


def _native_location(file, start=0, end=None):
    if file is None or file['artifact'] is None: return None
    a = file['artifact']; end = a['size_bytes'] if end is None else end
    return {'artifact': {k: a[k] for k in ('raw_artifact_ref', 'source_ref', 'sha256')},
        'byte_start_0based': start, 'byte_end_0based_exclusive': end,
        'line_start_1based': None, 'line_end_1based_inclusive': None, 'xml_path': None}


def _unpack64(buffer):
    raw = _buffer(buffer)
    return struct.unpack(('<' if buffer['byte_order'] == 'little' else '>') + 'd' * (len(raw) // 8), raw)


def _model_join(model, matrix):
    _need(model['model_id'] == matrix['model_id'] and model['matrix_occurrence_id'] == matrix['matrix_occurrence_id'], 'model_original_occurrence_conflict')
    if model['state'] != 'available': return
    _need(matrix['state'] == 'available' and model['length'] == matrix['length'], 'model_input_length_conflict')
    values = _unpack64(model['buffers']['counts']); width = matrix['length']
    for base_index, base in enumerate(_BASES):
        for column, token in enumerate(matrix['count_tokens'][base]):
            try:
                exact = Decimal(token['raw_token']); converted = float(token['raw_token'])
            except (ValueError, InvalidOperation, OverflowError) as error:
                raise ValueError('tf_binding_count_float64_unrepresentable') from error
            _need(exact.is_finite() and exact >= 0 and math.isfinite(converted) and not (exact != 0 and converted == 0), 'count_float64_unrepresentable')
            observed = values[base_index * width + column]
            _need(struct.pack('>d', observed) == struct.pack('>d', converted), 'native_count_conversion_conflict')


def tf_binding_model_normalization_issues(model, *, path=''):
    """Check retained native normalization eligibility; never repair or score."""
    if model['state'] != 'available': return []
    width = model['length']; buffers = model['buffers']; issues = []
    counts = _unpack64(buffers['counts']); pseudo = _unpack64(buffers['pseudocounts'])
    background = _unpack64(buffers['background']); pwm = _unpack64(buffers['pwm'])
    for column in range(width):
        # This is the native Python-float, ACGT ordered input-total check, not
        # a replacement normalization or a rescaled probability calculation.
        values = [counts[base * width + column] + pseudo[base] for base in range(4)]
        total = sum(values)
        if any(not math.isfinite(v) for v in values) or not math.isfinite(total) or total <= 0:
            issues.append(tf_binding_issue('native_normalization_column_total_invalid', path=path + '/buffers/counts', severity='error'))
        probabilities = [pwm[base * width + column] for base in range(4)]
        total = sum(probabilities)
        if any(not math.isfinite(v) or not 0 <= v <= 1 for v in probabilities) or not math.isfinite(total) or total <= 0:
            issues.append(tf_binding_issue('native_pwm_column_invalid', path=path + '/buffers/pwm', severity='error'))
    total = sum(background)
    if any(not math.isfinite(v) or not 0 <= v <= 1 for v in background) or not math.isfinite(total) or total <= 0:
        issues.append(tf_binding_issue('native_background_invalid', path=path + '/buffers/background', severity='error'))
    # A qualification need not repeat once per identical failing column.
    return [row for i, row in enumerate(issues) if row not in issues[:i]]


def _array_record(spec, scan, file):
    issues = []; blob = None; captured = usable = trailing = excess = 0
    possible = spec['possible_positions']; state = 'unavailable'
    if scan is not None and file is not None and file['content'] is not None:
        _need(file['role'] == 'scores', 'score_file_role_conflict')
        raw = file['content']; captured, trailing = divmod(len(raw), 4)
        usable = min(captured, possible) if possible is not None else 0
        excess = max(0, captured - possible) if possible is not None else 0
        blob = {'dtype': 'float32', 'byte_order': scan['byte_order'], 'data_base64': base64.b64encode(raw).decode('ascii'),
            'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}
        if file['capture']['state'] == 'complete':
            _need(scan['sha256'] == blob['sha256'] and scan['size_bytes'] == len(raw), 'score_original_file_identity_conflict')
        state = 'partial'
        if trailing: issues.append(tf_binding_issue('score_trailing_bytes'))
        if excess: issues.append(tf_binding_issue('score_excess_values'))
        if scan['declared_count'] is not None and scan['declared_count'] != captured:
            issues.append(tf_binding_issue('score_declared_actual_count_conflict'))
        if possible is not None and captured != possible:
            issues.append(tf_binding_issue('score_expected_actual_count_conflict'))
        if file['capture']['state'] != 'complete': issues.append(tf_binding_issue('score_capture_truncated'))
        if (file['capture']['state'] == 'truncated' and file['capture']['original_size_bytes'] is not None
                and scan['size_bytes'] is not None and file['capture']['original_size_bytes'] != scan['size_bytes']):
            issues.append(tf_binding_issue('score_capture_original_size_conflict'))
        if scan['state'] == 'complete' and (possible is None or scan['declared_count'] != possible
                or scan['size_bytes'] != 4 * possible or scan['failure_code'] is not None):
            issues.append(tf_binding_issue('native_complete_declaration_conflict'))
        if (file['capture']['state'] == 'complete' and scan['state'] in ('complete', 'zero_possible')
                and scan['declared_count'] == possible == captured and not trailing and not excess
                and scan['failure_code'] is None):
            state = 'zero_possible' if scan['state'] == 'zero_possible' else 'complete'
    else:
        issues.append(tf_binding_issue('native_scores_unavailable'))
    return {'spec': deepcopy(spec), 'native_scan': deepcopy(scan), 'file_id': None if file is None else file['file_id'],
        'blob': blob, 'location': _native_location(file), 'coverage': {'state': state,
            'expected_positions': possible, 'declared_count': None if scan is None else scan['declared_count'],
            'captured_complete_elements': captured, 'usable_elements': usable, 'trailing_bytes': trailing,
            'excess_elements': excess}, 'issues': issues}


def populate_tf_binding_sheet(*, inputs, invocation, execution, files):
    invocation = validate_tf_binding_invocation(invocation); decoded = decode_tf_binding_inputs(inputs)
    specs = resolve_tf_binding_scan_selection(decoded, invocation['scan_selection'])
    _need(type(files) is list, 'files_invalid'); checked = [_file(v) for v in files]
    file_map = {v['file_id']: v for v in checked}; _need(len(file_map) == len(checked), 'duplicate_file_id')
    _shape(execution, ('metadata_file_id', 'value')); native = execution['value']; issues = deepcopy(decoded['issues'])
    if native is None:
        _need(execution['metadata_file_id'] is None, 'native_metadata_unavailable_conflict')
        issues.append(tf_binding_issue('native_execution_unavailable'))
    else:
        native = validate_tf_binding_native_value(native)
        key = execution['metadata_file_id']; _need(key in file_map, 'native_metadata_file_missing')
        metadata = file_map[key]
        _need(metadata['role'] == 'native_result' and metadata['content'] is not None and metadata['capture']['state'] == 'complete', 'native_metadata_file_unavailable')
        try: literal = json.loads(metadata['content'].decode('utf-8'))
        except (ValueError, UnicodeError) as error: raise ValueError('tf_binding_native_metadata_invalid') from error
        _need(_same(literal, native), 'native_metadata_value_conflict')
    sheet = {'version': SHEET_VERSION, 'invocation': invocation, **{k: deepcopy(decoded[k]) for k in ('inputs', 'sequences', 'matrices')},
        'selected_scan_specs': specs, 'execution': {'metadata_file_id': execution['metadata_file_id'], 'value': native},
        'execution_sha256': None if native is None else hashlib.sha256(json.dumps(native, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest(),
        'files': [_metadata(v) for v in checked], 'score_arrays': [], 'issues': issues}
    scans = {} if native is None else {v['scan_id']: v for v in native['scans']}
    for spec in specs:
        scan = scans.get(spec['scan_id']); file = None if scan is None else file_map.get(scan['score_file_id'])
        sheet['score_arrays'].append(_array_record(spec, scan, file))
    return validate_tf_binding_sheet(sheet)


def validate_tf_binding_sheet(sheet):
    _shape(sheet, ('version', 'invocation', 'inputs', 'sequences', 'matrices', 'selected_scan_specs', 'execution', 'execution_sha256', 'files', 'score_arrays', 'issues'))
    _need(sheet['version'] == SHEET_VERSION, 'sheet_version_invalid'); invocation = validate_tf_binding_invocation(sheet['invocation']); _issues(sheet['issues'])
    for key in ('inputs', 'sequences', 'matrices', 'selected_scan_specs', 'files', 'score_arrays'):
        _need(type(sheet[key]) is list, 'sheet_rows_invalid')
    inputs = {v['input_id']: v for v in sheet['inputs']}; _need(len(inputs) == len(sheet['inputs']), 'duplicate_input_id')
    for value in sheet['inputs']:
        _shape(value, ('input_id', 'role', 'format', 'artifact', 'capture')); _text(value['input_id'])
        _need(value['role'] in ('dna', 'matrix') and value['format'] in (('fasta', 'raw_dna') if value['role'] == 'dna' else ('jaspar_json', 'jaspar_pfm', 'acgt_count_json')), 'input_format_invalid')
        a = value['artifact']; _shape(a, ('artifact_ref', 'sha256', 'size_bytes', 'source_ref')); _hash(a['sha256']); _integer(a['size_bytes']); _text(a['source_ref'], nullable=True)
        _need(a['artifact_ref'] == 'artifact_' + a['sha256'], 'input_artifact_identity_conflict')
        _capture(value['capture'], 0 if value['capture']['state'] == 'missing' else a['size_bytes'])
    sequences = {v['sequence_id']: v for v in sheet['sequences']}; matrices = {v['matrix_occurrence_id']: v for v in sheet['matrices']}
    _need(len(sequences) == len(sheet['sequences']) and len(matrices) == len(sheet['matrices']), 'duplicate_occurrence_id')
    for row in sheet['sequences']:
        _shape(row, ('sequence_id', 'input_id', 'record_ordinal_0based', 'raw_header', 'identifier', 'symbols', 'symbols_sha256', 'length', 'state', 'locator', 'issues'))
        _validate_locator(row['locator'], inputs); _issues(row['issues']); _integer(row['record_ordinal_0based']); _integer(row['length'], nullable=True)
        _need(row['locator']['input_id'] == row['input_id'], 'sequence_locator_input_conflict')
        _need(row['raw_header'] is None or type(row['raw_header']) is str, 'sequence_header_invalid')
        _text(row['identifier'], nullable=True)
        _need(inputs[row['input_id']]['role'] == 'dna' and row['sequence_id'] == _id('sequence', [row['input_id'], inputs[row['input_id']]['artifact']['sha256'], row['record_ordinal_0based']]), 'sequence_identity_conflict')
        _need(row['state'] in ('available', 'unavailable'), 'sequence_state_invalid')
        if row['symbols'] is not None:
            _need(type(row['symbols']) is str and row['symbols'].isascii() and len(row['symbols']) == row['length'] and hashlib.sha256(row['symbols'].encode('ascii')).hexdigest() == row['symbols_sha256'], 'sequence_symbols_identity_conflict')
        else: _need(row['symbols_sha256'] is None and row['length'] is None and row['state'] == 'unavailable', 'sequence_missing_conflict')
    for row in sheet['matrices']:
        _shape(row, ('matrix_occurrence_id', 'model_id', 'input_id', 'record_ordinal_0based', 'raw_header', 'native_matrix_id', 'name', 'alphabet', 'length', 'rows', 'count_tokens', 'state', 'locator', 'issues'))
        _validate_locator(row['locator'], inputs); _issues(row['issues']); _integer(row['record_ordinal_0based']); _integer(row['length'], nullable=True)
        _need(row['locator']['input_id'] == row['input_id'], 'matrix_locator_input_conflict')
        for key in ('raw_header', 'native_matrix_id', 'name'):
            _need(row[key] is None or type(row[key]) is str, 'matrix_label_invalid')
        key = _id('matrix', [row['input_id'], inputs[row['input_id']]['artifact']['sha256'], row['record_ordinal_0based']])
        _need(inputs[row['input_id']]['role'] == 'matrix' and row['matrix_occurrence_id'] == key and row['model_id'] == _id('model', [key]) and row['alphabet'] == _BASES, 'matrix_identity_conflict')
        _need(row['state'] in ('available', 'unavailable') and type(row['rows']) is list, 'matrix_state_invalid')
        for source_row in row['rows']:
            _shape(source_row, ('row_ordinal_0based', 'base', 'raw_text', 'tokens', 'locator')); _validate_locator(source_row['locator'], inputs); _integer(source_row['row_ordinal_0based'])
            _need(source_row['locator']['input_id'] == row['input_id'], 'matrix_locator_input_conflict')
            _need(source_row['base'] in (*_BASES, None) and type(source_row['tokens']) is list, 'matrix_row_invalid')
            for token in source_row['tokens']:
                _shape(token, ('raw_token', 'locator')); _text(token['raw_token']); _validate_locator(token['locator'], inputs)
                _need(token['locator']['input_id'] == row['input_id'] and row['locator']['byte_start_0based'] <= token['locator']['byte_start_0based'] <= token['locator']['byte_end_0based_exclusive'] <= row['locator']['byte_end_0based_exclusive'], 'matrix_token_location_conflict')
        if row['state'] == 'available':
            _need(type(row['length']) is int and row['length'] > 0 and type(row['count_tokens']) is dict and set(row['count_tokens']) == set(_BASES), 'matrix_counts_invalid')
            for base in _BASES:
                _need(len(row['count_tokens'][base]) == row['length'], 'matrix_count_length_conflict')
                matching = [v['tokens'] for v in row['rows'] if v['base'] == base]
                _need(len(matching) == 1 and _same(matching[0], row['count_tokens'][base]), 'matrix_count_row_conflict')
        else: _need(row['count_tokens'] is None, 'matrix_unavailable_counts_conflict')
    candidates = []
    for sequence in sheet['sequences']:
        for matrix in sheet['matrices']:
            possible = max(0, sequence['length'] - matrix['length'] + 1) if sequence['state'] == matrix['state'] == 'available' else None
            for strand in ('+', '-'):
                candidates.append({'scan_id': _id('scan', [sequence['sequence_id'], matrix['model_id'], strand]), 'sequence_id': sequence['sequence_id'], 'matrix_occurrence_id': matrix['matrix_occurrence_id'], 'model_id': matrix['model_id'], 'strand': strand, 'possible_positions': possible})
    expected = resolve_tf_binding_scan_selection({'sequences': sheet['sequences'], 'matrices': sheet['matrices'], 'scan_specs': candidates}, invocation['scan_selection'])
    _need(_same(sheet['selected_scan_specs'], expected), 'selected_population_conflict')
    files = {v['file_id']: v for v in sheet['files']}; _need(len(files) == len(sheet['files']), 'duplicate_file_id')
    for value in sheet['files']:
        _shape(value, ('file_id', 'role', 'artifact', 'capture')); _text(value['file_id']); _need(value['role'] in ('native_result', 'scores', 'native_log'), 'file_role_invalid')
        a = value['artifact']
        if a is not None:
            _shape(a, ('raw_artifact_ref', 'source_ref', 'sha256', 'size_bytes')); _text(a['source_ref']); _hash(a['sha256']); _integer(a['size_bytes'])
            _need(a['raw_artifact_ref'] == 'artifact_' + a['sha256'], 'captured_file_identity_conflict')
        _capture(value['capture'], 0 if a is None else a['size_bytes'])
        _need((a is None) == (value['capture']['state'] == 'missing'), 'missing_file_conflict')
    _shape(sheet['execution'], ('metadata_file_id', 'value')); native = sheet['execution']['value']
    if native is None:
        _need(sheet['execution']['metadata_file_id'] is None and sheet['execution_sha256'] is None, 'native_missing_conflict')
        models, scans = {}, {}
    else:
        validate_tf_binding_native_value(native)
        _need(native['invocation_id'] == invocation['invocation_id'] and _same(native['parameters'], invocation['parameters']) and _same(native['scan_selection'], invocation['scan_selection']), 'native_invocation_conflict')
        _need(sheet['execution_sha256'] == hashlib.sha256(json.dumps(native, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest(), 'native_value_digest_conflict')
        key = sheet['execution']['metadata_file_id']; _need(key in files and files[key]['role'] == 'native_result' and files[key]['artifact'] is not None and files[key]['capture']['state'] == 'complete', 'native_metadata_file_unavailable')
        capture_source = files[key]['artifact']['source_ref']
        _need(all(v['artifact'] is None or v['artifact']['source_ref'] == capture_source for v in files.values()), 'native_capture_source_conflict')
        identities = [{'input_id': v['input_id'], **{k: v['artifact'][k] for k in ('artifact_ref', 'sha256', 'size_bytes')}} for v in sheet['inputs']]
        _need(_same(native['input_identities'], identities), 'native_input_identity_conflict')
        model_ids = {v['model_id'] for v in expected}; models = {v['model_id']: v for v in native['models']}
        _need(set(models) <= model_ids, 'native_model_not_selected')
        for model in models.values():
            _need(model['matrix_occurrence_id'] in matrices, 'native_matrix_unknown'); _model_join(model, matrices[model['matrix_occurrence_id']])
        scans = {v['scan_id']: v for v in native['scans']}; expected_map = {v['scan_id']: v for v in expected}
        _need(set(scans) <= set(expected_map), 'native_scan_not_selected')
        for key, scan in scans.items():
            _need(_same({k: scan[k] for k in expected_map[key]}, expected_map[key]), 'native_scan_population_conflict')
            if scan['state'] != 'unavailable': _need(scan['model_id'] in models and models[scan['model_id']]['state'] == 'available', 'scan_model_unavailable_conflict')
    _need(len(sheet['score_arrays']) == len(expected), 'score_array_population_conflict')
    for row, spec in zip(sheet['score_arrays'], expected):
        _shape(row, ('spec', 'native_scan', 'file_id', 'blob', 'location', 'coverage', 'issues')); _issues(row['issues'])
        _need(_same(row['spec'], spec) and _same(row['native_scan'], scans.get(spec['scan_id'])), 'score_array_scan_conflict')
        file = None if row['file_id'] is None else files.get(row['file_id'])
        _need(row['file_id'] is None or file is not None, 'score_file_unknown')
        _need(file is None or row['native_scan'] is not None and row['file_id'] == row['native_scan']['score_file_id'], 'score_file_scan_conflict')
        blob = row['blob']; content = None
        _need(file is None or file['artifact'] is None or blob is not None, 'present_score_blob_missing')
        if blob is not None:
            _shape(blob, ('dtype', 'byte_order', 'data_base64', 'sha256', 'size_bytes')); _need(blob['dtype'] == 'float32', 'score_dtype_invalid')
            try: content = base64.b64decode(blob['data_base64'], validate=True)
            except (ValueError, TypeError) as error: raise ValueError('tf_binding_base64_invalid') from error
            _need(base64.b64encode(content).decode('ascii') == blob['data_base64'], 'base64_noncanonical')
            _need(file is not None and file['artifact'] is not None and blob['byte_order'] == row['native_scan']['byte_order'] and blob['sha256'] == hashlib.sha256(content).hexdigest() == file['artifact']['sha256'] and blob['size_bytes'] == len(content) == file['artifact']['size_bytes'], 'score_blob_identity_conflict')
        reconstructed = _array_record(spec, row['native_scan'], None if file is None else {**file, 'content': content})
        _need(_same(reconstructed, row), 'score_capture_consistency_conflict')
        if row['location'] is not None: locations.location(row['location'])
    return deepcopy(sheet)


def validate_tf_binding_selection(value):
    _shape(value, ('version', 'scan_ids', 'raw_threshold', 'offset', 'limit'))
    _need(value['version'] == 'tf_binding_selection_v1' and type(value['scan_ids']) is list, 'selection_invalid')
    for scan_id in value['scan_ids']: _text(scan_id)
    _need(len(set(value['scan_ids'])) == len(value['scan_ids']), 'duplicate_selected_scan')
    _need(_finite(value['raw_threshold']), 'threshold_not_finite'); _integer(value['offset']); _integer(value['limit'])
    result = deepcopy(value)
    try: result['raw_threshold'] = float(result['raw_threshold'])
    except (OverflowError, ValueError) as error: raise ValueError('tf_binding_threshold_not_finite') from error
    _need(math.isfinite(result['raw_threshold']), 'threshold_not_finite')
    return result


def _extended(value, *, dtype, byte_order, raw, unit, origin, location):
    classification = 'nan' if math.isnan(float(value)) else 'positive_infinity' if float(value) == math.inf else 'negative_infinity' if float(value) == -math.inf else 'finite'
    return {'classification': classification, 'value': float(value) if classification == 'finite' else None,
        'dtype': dtype, 'byte_order': byte_order, 'bits_hex': raw.hex(), 'unit': unit, 'origin': origin,
        'state': 'undefined' if classification == 'nan' else 'available', 'reason_code': None,
        'location': deepcopy(location)}


def _relative_normalization(model, metadata_file, index):
    bounds = model['buffers']['bounds_plus']; raw = _buffer(bounds); minimum, maximum = _unpack64(bounds)
    span = maximum - minimum
    reason = ('nonfinite_relative_bounds' if not math.isfinite(minimum) or not math.isfinite(maximum)
        else 'nonfinite_relative_span' if not math.isfinite(span) else 'zero_relative_span' if span == 0 else None)
    location = _native_location(metadata_file)
    descriptor = {'normalization_id': _id('relative', [model['model_id'], bounds['sha256']]), 'model_id': model['model_id'],
        'bounds_strand': '+', 'operand_dtype': 'python_float_binary64', 'scientific_state': 'defined' if reason is None else 'undefined',
        'reason_code': reason,
        'minimum': _extended(minimum, dtype='float64', byte_order=bounds['byte_order'], raw=raw[:8], unit='bits', origin='native_observation', location=location),
        'maximum': _extended(maximum, dtype='float64', byte_order=bounds['byte_order'], raw=raw[8:], unit='bits', origin='native_observation', location=location),
        'span': _extended(span, dtype='float64', byte_order=sys.byteorder, raw=struct.pack('=d', span), unit='bits', origin='calculated', location=None),
        'operand_evidence': {'bounds_location': location, 'bounds_json_pointer': '/models/' + str(index) + '/buffers/bounds_plus',
            'minimum_element_ordinal_0based': 0, 'maximum_element_ordinal_0based': 1}}
    return descriptor


def _cell(value, *, field, population, state='missing'):
    return numeric_cell(value, state='available' if value is not None else state, unit='count', origin='calculated', population_id=population, method_id='tf_binding_' + field)


def _public(value):
    if isinstance(value, dict):
        return {k: _public(v) for k, v in value.items() if k not in ('location', 'evidence', 'requirement_ids', 'evidence_refs', 'operand_evidence')}
    if isinstance(value, list): return [_public(v) for v in value]
    return value


def calculate_tf_binding_components(sheet, selection):
    sheet = validate_tf_binding_sheet(sheet); selection = validate_tf_binding_selection(selection)
    # NumPy itself owns promotion and both distinct operator conventions. A
    # later runtime must not silently reinterpret a retained native array.
    import numpy as np
    native = sheet['execution']['value']
    _need(native is not None, 'native_scores_unavailable')
    _need(np.__version__ == native['numpy_version'], 'numpy_promotion_version_unsupported')
    arrays = {v['spec']['scan_id']: v for v in sheet['score_arrays']}
    _need(set(selection['scan_ids']) <= set(arrays), 'selected_scan_unknown')
    sequences = {v['sequence_id']: v for v in sheet['sequences']}; matrices = {v['matrix_occurrence_id']: v for v in sheet['matrices']}; models = {v['model_id']: v for v in native['models']}
    rows = []; counts = dict(raw_complete_elements=0, observed_window_scores=0, finite_scores=0, nan_scores=0, positive_infinity_scores=0, negative_infinity_scores=0, extended_scorable_scores=0)
    available = False; complete = bool(selection['scan_ids']); possible = 0; possible_known = True; unique = {}; pair_order = {}; strand_order = {}; issues = deepcopy(sheet['issues']) + deepcopy(native['issues']); selected_arrays = []
    normalization = {model_id: tf_binding_model_normalization_issues(model, path='/models/' + str(i)) for i, (model_id, model) in enumerate(models.items())}
    invalid_selected_model = False
    metadata_file = next((v for v in sheet['files'] if v['file_id'] == sheet['execution']['metadata_file_id']), None)
    relative_descriptors = {model_id: _relative_normalization(model, metadata_file, i)
        for i, (model_id, model) in enumerate(models.items()) if model['state'] == 'available'}
    for scan_id in selection['scan_ids']:
        row = arrays[scan_id]; spec = row['spec']; selected_arrays.append({'scan_id': scan_id, 'coverage': deepcopy(row['coverage'])}); issues += deepcopy(row['issues'])
        for original in (sequences[spec['sequence_id']], matrices[spec['matrix_occurrence_id']]):
            issues += [deepcopy(v) for v in original['issues'] if v not in issues]
        model_issues = normalization.get(spec['model_id'], [])
        declared_failure = models.get(spec['model_id'], {}).get('failure_code')
        for code in (declared_failure, None if row['native_scan'] is None else row['native_scan']['failure_code']):
            if code is not None and not any(v['code'] == (code if code.startswith('tf_binding_') else 'tf_binding_' + code) for v in issues):
                issues.append(tf_binding_issue(code, severity='error'))
        if model_issues:
            invalid_selected_model = True
            issues += [v for v in model_issues if v not in issues]
        pair = (spec['sequence_id'], spec['matrix_occurrence_id']); pair_order.setdefault(pair, len(pair_order)); strand_order.setdefault((pair, spec['strand']), len(strand_order))
        n = spec['possible_positions']
        if n is None: possible_known = False
        else: possible += n; unique[pair] = n
        if row['coverage']['state'] not in ('complete', 'zero_possible'): complete = False
        if row['blob'] is None: continue
        available = True; counts['raw_complete_elements'] += row['coverage']['captured_complete_elements']
        blob = row['blob']; raw = base64.b64decode(blob['data_base64']); usable = row['coverage']['usable_elements']
        scores = np.frombuffer(raw[:usable * 4], dtype=('<' if blob['byte_order'] == 'little' else '>') + 'f4')
        counts['observed_window_scores'] += len(scores)
        counts['finite_scores'] += int(np.isfinite(scores).sum()); counts['nan_scores'] += int(np.isnan(scores).sum())
        counts['positive_infinity_scores'] += int(np.isposinf(scores).sum()); counts['negative_infinity_scores'] += int(np.isneginf(scores).sum())
        counts['extended_scorable_scores'] += int((~np.isnan(scores)).sum())
        with np.errstate(all='ignore'):
            matched = np.flatnonzero(scores >= selection['raw_threshold'])
        model = models.get(spec['model_id'])
        if model is None or model['state'] != 'available': continue
        minimum, maximum = _unpack64(model['buffers']['bounds_plus'])
        normalization_descriptor = relative_descriptors[model['model_id']]
        sequence, matrix = sequences[spec['sequence_id']], matrices[spec['matrix_occurrence_id']]
        for position in matched.tolist():
            score = scores[position]; original = sequence['symbols'][position:position + model['length']]
            with np.errstate(all='ignore'):
                relative = (score - minimum) / (maximum - minimum)
            dtype = 'float32' if getattr(relative, 'dtype', None) == np.dtype('float32') else 'float64'
            relative_bytes = struct.pack(('<' if sys.byteorder == 'little' else '>') + ('f' if dtype == 'float32' else 'd'), relative)
            native_location = deepcopy(row['location'])
            if native_location is not None:
                native_location['byte_start_0based'], native_location['byte_end_0based_exclusive'] = position * 4, position * 4 + 4
            relative_record = _extended(relative, dtype=dtype, byte_order=sys.byteorder, raw=relative_bytes,
                unit='dimensionless', origin='calculated', location=None)
            relative_record['relative_normalization_id'] = normalization_descriptor['normalization_id']
            relative_record['operand_evidence'] = {'score_location': native_location, 'score_operand_dtype': 'numpy_float32',
                'normalization_id': normalization_descriptor['normalization_id']}
            if normalization_descriptor['scientific_state'] == 'undefined':
                relative_record['state'], relative_record['reason_code'] = 'undefined', normalization_descriptor['reason_code']
            elif relative_record['classification'] != 'finite':
                relative_record['state'], relative_record['reason_code'] = 'undefined', 'nonfinite_relative_result'
            rows.append({'hit_id': _id('hit', [scan_id, position]), 'scan_id': scan_id, 'sequence_id': spec['sequence_id'],
                'matrix_occurrence_id': spec['matrix_occurrence_id'], 'sequence_record_ordinal_0based': sequence['record_ordinal_0based'],
                'matrix_record_ordinal_0based': matrix['record_ordinal_0based'], 'start_0based': position,
                'end_0based_exclusive': position + model['length'], 'strand': spec['strand'], 'forward_sequence': original,
                'model_normalization_eligible': not bool(model_issues),
                'motif_oriented_sequence': original if spec['strand'] == '+' else original.translate(str.maketrans('ACGT', 'TGCA'))[::-1],
                'score': _extended(score, dtype='float32', byte_order=blob['byte_order'], raw=raw[position * 4:position * 4 + 4], unit='bits', origin='native_observation', location=native_location),
                'relative_score': relative_record})
    rows.sort(key=lambda r: (pair_order[(r['sequence_id'], r['matrix_occurrence_id'])], r['start_0based'], strand_order[((r['sequence_id'], r['matrix_occurrence_id']), r['strand'])]))
    population = _id('population', [sheet['invocation']['invocation_id'], selection['scan_ids']])
    totals = {k: _cell(v, field=k, population=population) for k, v in counts.items()}
    totals['possible_strand_windows'] = _cell(possible if possible_known else None, field='possible_strand_windows', population=population)
    totals['possible_unique_windows'] = _cell(sum(unique.values()) if possible_known else None, field='possible_unique_windows', population=population)
    totals['matched_observed_scores'] = _cell(len(rows) if available else None, field='matched_observed_scores', population=population)
    totals['raw_full_threshold_matches'] = _cell(len(rows) if complete and available else None, field='raw_full_threshold_matches', population=population, state='truncated' if available else 'missing')
    totals['full_matched_scores'] = _cell(len(rows) if complete and available and not invalid_selected_model else None, field='full_matched_scores', population=population, state='incompatible' if invalid_selected_model else 'truncated' if available else 'missing')
    eligible = [row for row in rows if row['model_normalization_eligible']]
    totals['model_eligible_candidate_sites'] = _cell(len(eligible) if complete and available and not invalid_selected_model else None,
        field='model_eligible_candidate_sites', population=population, state='incompatible' if invalid_selected_model else 'missing')
    window = rows[selection['offset']:selection['offset'] + selection['limit']]
    candidate_window = [row for row in window if row['model_normalization_eligible']]
    totals['returned_raw_threshold_rows'] = _cell(len(window), field='returned_raw_threshold_rows', population=population)
    totals['returned_candidate_rows'] = _cell(len(candidate_window), field='returned_candidate_rows', population=population)
    status = 'unavailable' if not available else 'complete' if complete and native['outcome'] == 'succeeded' and not invalid_selected_model else 'partial'
    components = {'version': COMPONENTS_VERSION, 'status': status,
        'parameters': deepcopy(sheet['invocation']['parameters']), 'selection': selection,
        'execution': {'native_outcome': native['outcome'], 'returncode': native['returncode']},
        'numeric_authority': {'convention': NUMERIC_CONVENTION, 'numpy_version': native['numpy_version'], 'biopython_version': native['biopython_version'],
            'threshold_operand': 'python_float', 'threshold_binary64_hex': struct.pack('>d', selection['raw_threshold']).hex(),
            'comparison': 'float32_ndarray_ge_python_float', 'relative': 'numpy_float32_scalar_minus_python_float_div_python_float',
            'relative_bounds': 'forward_pssm_bounds_for_both_strands'},
        'available_scans': [{**deepcopy(v['spec']), 'coverage': deepcopy(v['coverage'])} for v in sheet['score_arrays']],
        'relative_normalizations': list(relative_descriptors.values()),
        'inputs': [{'input_id': v['input_id'], 'role': v['role'], 'format': v['format'],
            'artifact_id': v['artifact']['artifact_ref'], 'sha256': v['artifact']['sha256'],
            'size_bytes': v['artifact']['size_bytes'], 'upstream_source_id': v['artifact']['source_ref'],
            'capture': deepcopy(v['capture'])} for v in sheet['inputs']],
        'sequences': [{'sequence_id': v['sequence_id'], 'input_id': v['input_id'], 'record_ordinal_0based': v['record_ordinal_0based'], 'identifier': v['identifier'], 'length': v['length'], 'state': v['state']} for v in sheet['sequences']],
        'matrices': [{'matrix_occurrence_id': v['matrix_occurrence_id'], 'model_id': v['model_id'], 'input_id': v['input_id'], 'record_ordinal_0based': v['record_ordinal_0based'], 'native_matrix_id': v['native_matrix_id'], 'name': v['name'], 'length': v['length'], 'state': v['state']} for v in sheet['matrices']],
        'selected_scans': selected_arrays, 'totals': totals, 'raw_threshold_matches': window,
        'hits': candidate_window, 'issues': issues}
    return validate_tf_binding_components(components)


def _validate_extended(value, *, relative=False, public=False):
    fields = ('classification', 'value', 'dtype', 'byte_order', 'bits_hex', 'unit', 'origin', 'state', 'reason_code')
    if not public: fields += ('location',)
    if relative: fields += ('relative_normalization_id',) + (() if public else ('operand_evidence',))
    _shape(value, fields)
    _need(value['dtype'] in ('float32', 'float64') and value['byte_order'] in ('little', 'big'), 'extended_dtype_invalid')
    _need(type(value['bits_hex']) is str, 'extended_bits_invalid')
    try: raw = bytes.fromhex(value['bits_hex'])
    except ValueError as error: raise ValueError('tf_binding_extended_bits_invalid') from error
    size = 4 if value['dtype'] == 'float32' else 8
    _need(len(raw) == size and raw.hex() == value['bits_hex'], 'extended_bits_invalid')
    observed, = struct.unpack(('<' if value['byte_order'] == 'little' else '>') + ('f' if size == 4 else 'd'), raw)
    classification = 'nan' if math.isnan(observed) else 'positive_infinity' if observed == math.inf else 'negative_infinity' if observed == -math.inf else 'finite'
    _need(value['classification'] == classification, 'extended_classification_conflict')
    if classification == 'finite':
        _need(_finite(value['value']) and struct.pack('>d', float(value['value'])) == struct.pack('>d', observed), 'extended_value_conflict')
    else: _need(value['value'] is None, 'extended_nonfinite_value')
    _need(value['state'] in ('available', 'undefined') and (classification != 'nan' or value['state'] == 'undefined'), 'extended_state_invalid')
    _text(value['reason_code'], nullable=True)
    _need(value['origin'] in ('native_observation', 'calculated') and value['unit'] in ('bits', 'dimensionless'), 'extended_meaning_invalid')
    if not public and value['location'] is not None: locations.location(value['location'])
    if relative:
        _text(value['relative_normalization_id'])
        _need(value['unit'] == 'dimensionless' and value['origin'] == 'calculated' and (public or value['location'] is None), 'relative_meaning_invalid')
        if not public:
            evidence = value['operand_evidence']; _shape(evidence, ('score_location', 'score_operand_dtype', 'normalization_id'))
            _need(evidence['score_operand_dtype'] == 'numpy_float32' and evidence['normalization_id'] == value['relative_normalization_id'], 'relative_operand_conflict')
            if evidence['score_location'] is not None: locations.location(evidence['score_location'])


def _validate_tf_binding_values(value, *, public=False):
    """One numerical/cross-field authority for stored and public records."""
    _shape(value, (() if public else ('version',)) + ('status', 'parameters', 'selection', 'execution', 'numeric_authority', 'available_scans',
        'relative_normalizations', 'inputs', 'sequences', 'matrices', 'selected_scans', 'totals',
        'raw_threshold_matches', 'hits', 'issues'))
    _need((public or value['version'] == COMPONENTS_VERSION) and value['status'] in ('complete', 'partial', 'unavailable'), 'components_version_invalid')
    _parameters(value['parameters']); selection = validate_tf_binding_selection(value['selection'])
    if public:
        _need(type(value['issues']) is list, 'issues_invalid')
        for issue in value['issues']: _shape(issue, ('code', 'phase', 'path', 'severity'))
        _issues([{**issue, 'evidence_refs': []} for issue in value['issues']])
    else: _issues(value['issues'])
    _shape(value['execution'], ('native_outcome', 'returncode'))
    _need(value['execution']['native_outcome'] in ('succeeded', 'failed', 'not_run', 'unknown') and value['execution']['returncode'] is None, 'components_execution_invalid')
    authority = value['numeric_authority']
    _shape(authority, ('convention', 'numpy_version', 'biopython_version', 'threshold_operand', 'threshold_binary64_hex', 'comparison', 'relative', 'relative_bounds'))
    _text(authority['numpy_version']); _text(authority['biopython_version'])
    _need(authority['convention'] == NUMERIC_CONVENTION and authority['threshold_operand'] == 'python_float'
        and authority['threshold_binary64_hex'] == struct.pack('>d', selection['raw_threshold']).hex()
        and authority['comparison'] == 'float32_ndarray_ge_python_float'
        and authority['relative'] == 'numpy_float32_scalar_minus_python_float_div_python_float'
        and authority['relative_bounds'] == 'forward_pssm_bounds_for_both_strands', 'numeric_authority_conflict')
    for key in ('inputs', 'sequences', 'matrices', 'available_scans', 'selected_scans', 'relative_normalizations', 'raw_threshold_matches', 'hits'):
        _need(type(value[key]) is list, 'components_rows_invalid')
    inputs = {}
    for row in value['inputs']:
        _shape(row, ('input_id', 'role', 'format', 'artifact_id', 'sha256', 'size_bytes', 'upstream_source_id', 'capture'))
        _text(row['input_id']); _hash(row['sha256']); _integer(row['size_bytes']); _text(row['upstream_source_id'], nullable=True)
        _need(row['role'] in ('dna', 'matrix') and row['format'] in (('fasta', 'raw_dna') if row['role'] == 'dna' else ('jaspar_json', 'jaspar_pfm', 'acgt_count_json')), 'input_format_invalid')
        _need(row['artifact_id'] == 'artifact_' + row['sha256'] and row['input_id'] not in inputs, 'component_input_identity_conflict')
        _capture(row['capture'], 0 if row['capture']['state'] == 'missing' else row['size_bytes']); inputs[row['input_id']] = row
    catalogs = []
    for field, kind in (('sequences', 'sequence'), ('matrices', 'matrix')):
        catalog = {}
        for row in value[field]:
            fields = ('sequence_id', 'input_id', 'record_ordinal_0based', 'identifier', 'length', 'state') if kind == 'sequence' else ('matrix_occurrence_id', 'model_id', 'input_id', 'record_ordinal_0based', 'native_matrix_id', 'name', 'length', 'state')
            _shape(row, fields); _integer(row['record_ordinal_0based']); _integer(row['length'], nullable=True)
            _need(row['input_id'] in inputs and inputs[row['input_id']]['role'] == ('dna' if kind == 'sequence' else 'matrix'), 'component_occurrence_input_conflict')
            _need(row['state'] in ('available', 'unavailable') and (row['state'] != 'available' or row['length'] is not None), 'component_occurrence_state_invalid')
            for key in (('identifier',) if kind == 'sequence' else ('native_matrix_id', 'name')):
                _need(row[key] is None or type(row[key]) is str, 'component_occurrence_label_invalid')
            key = _id(kind, [row['input_id'], inputs[row['input_id']]['sha256'], row['record_ordinal_0based']])
            _need(row['sequence_id' if kind == 'sequence' else 'matrix_occurrence_id'] == key and key not in catalog, 'component_occurrence_identity_conflict')
            if kind == 'matrix': _need(row['model_id'] == _id('model', [key]), 'component_model_identity_conflict')
            catalog[key] = row
        catalogs.append(catalog)
    sequences, matrices = catalogs; scans = {}
    for row in value['available_scans']:
        _shape(row, ('scan_id', 'sequence_id', 'matrix_occurrence_id', 'model_id', 'strand', 'possible_positions', 'coverage'))
        _spec({k: row[k] for k in row if k != 'coverage'})
        _need(row['sequence_id'] in sequences and row['matrix_occurrence_id'] in matrices and row['scan_id'] not in scans, 'component_scan_identity_conflict')
        matrix = matrices[row['matrix_occurrence_id']]
        _need(row['model_id'] == matrix['model_id'] and row['scan_id'] == _id('scan', [row['sequence_id'], row['model_id'], row['strand']]), 'component_scan_identity_conflict')
        sequence = sequences[row['sequence_id']]
        possible = max(0, sequence['length'] - matrix['length'] + 1) if sequence['state'] == matrix['state'] == 'available' else None
        _need(row['possible_positions'] == possible, 'component_scan_geometry_conflict')
        coverage = row['coverage']
        _shape(coverage, ('state', 'expected_positions', 'declared_count', 'captured_complete_elements', 'usable_elements', 'trailing_bytes', 'excess_elements'))
        _need(coverage['state'] in ('complete', 'partial', 'zero_possible', 'unavailable') and coverage['expected_positions'] == row['possible_positions'], 'coverage_state_invalid')
        for key in ('expected_positions', 'declared_count'): _integer(coverage[key], nullable=True)
        for key in ('captured_complete_elements', 'usable_elements', 'trailing_bytes', 'excess_elements'): _integer(coverage[key])
        _need(coverage['trailing_bytes'] <= 3 and coverage['usable_elements'] <= coverage['captured_complete_elements'], 'coverage_extent_invalid')
        scans[row['scan_id']] = row
    _need(set(selection['scan_ids']) <= set(scans), 'selected_scan_unknown')
    _need(_same(value['selected_scans'], [{'scan_id': k, 'coverage': scans[k]['coverage']} for k in selection['scan_ids']]), 'selected_scan_coverage_conflict')
    normalizations = {}
    for row in value['relative_normalizations']:
        _shape(row, ('normalization_id', 'model_id', 'bounds_strand', 'operand_dtype', 'scientific_state', 'reason_code', 'minimum', 'maximum', 'span') + (() if public else ('operand_evidence',)))
        _text(row['normalization_id']); _text(row['model_id']); _text(row['reason_code'], nullable=True)
        _need(row['normalization_id'] not in normalizations and row['model_id'] in {m['model_id'] for m in matrices.values()}
            and row['bounds_strand'] == '+' and row['operand_dtype'] == 'python_float_binary64'
            and row['scientific_state'] in ('defined', 'undefined')
            and ((row['reason_code'] is None) == (row['scientific_state'] == 'defined')), 'relative_normalization_invalid')
        for key in ('minimum', 'maximum', 'span'):
            _validate_extended(row[key], public=public); _need(row[key]['dtype'] == 'float64' and row[key]['unit'] == 'bits'
                and row[key]['origin'] == ('calculated' if key == 'span' else 'native_observation'), 'relative_bounds_meaning_invalid')
        _need(row['minimum']['byte_order'] == row['maximum']['byte_order'] and (public or row['span']['location'] is None)
            and row['normalization_id'] == _id('relative', [row['model_id'], hashlib.sha256(bytes.fromhex(row['minimum']['bits_hex'] + row['maximum']['bits_hex'])).hexdigest()]), 'relative_bounds_identity_conflict')
        if not public:
            evidence = row['operand_evidence']; _shape(evidence, ('bounds_location', 'bounds_json_pointer', 'minimum_element_ordinal_0based', 'maximum_element_ordinal_0based'))
            _need(type(evidence['bounds_json_pointer']) is str and evidence['bounds_json_pointer'].startswith('/models/') and evidence['minimum_element_ordinal_0based'] == 0 and evidence['maximum_element_ordinal_0based'] == 1, 'relative_bounds_evidence_invalid')
            if evidence['bounds_location'] is not None: locations.location(evidence['bounds_location'])
            _need(_same(evidence['bounds_location'], row['minimum']['location']) and _same(row['minimum']['location'], row['maximum']['location']), 'relative_bounds_evidence_conflict')
        normalizations[row['normalization_id']] = row
    total_fields = ('raw_complete_elements', 'observed_window_scores', 'finite_scores', 'nan_scores', 'positive_infinity_scores', 'negative_infinity_scores', 'extended_scorable_scores', 'possible_strand_windows', 'possible_unique_windows', 'matched_observed_scores', 'raw_full_threshold_matches', 'full_matched_scores', 'model_eligible_candidate_sites', 'returned_raw_threshold_rows', 'returned_candidate_rows')
    _shape(value['totals'], total_fields); numbers = {}
    for key, cell in value['totals'].items():
        if public:
            _shape(cell, ('value', 'state', 'unit', 'origin', 'numerator', 'denominator', 'population_id', 'method_id', 'uncertainty'))
            validate_numeric_cell({**cell, 'evidence': [], 'requirement_ids': []})
        else: validate_numeric_cell(cell)
        _need(cell['unit'] == 'count' and cell['origin'] == 'calculated' and cell['method_id'] == 'tf_binding_' + key, 'total_meaning_invalid')
        _integer(cell['value'], nullable=key not in total_fields[:7]); numbers[key] = cell['value']
    _need(numbers['observed_window_scores'] == sum(numbers[k] for k in ('finite_scores', 'nan_scores', 'positive_infinity_scores', 'negative_infinity_scores'))
        and numbers['extended_scorable_scores'] == numbers['observed_window_scores'] - numbers['nan_scores']
        and numbers['raw_complete_elements'] >= numbers['observed_window_scores'], 'score_population_count_conflict')
    _need(len(value['raw_threshold_matches']) == numbers['returned_raw_threshold_rows'] and len(value['hits']) == numbers['returned_candidate_rows']
        and len(value['raw_threshold_matches']) <= selection['limit'], 'returned_row_count_conflict')
    hit_ids = set()
    for row in value['raw_threshold_matches']:
        _shape(row, ('hit_id', 'scan_id', 'sequence_id', 'matrix_occurrence_id', 'sequence_record_ordinal_0based', 'matrix_record_ordinal_0based', 'start_0based', 'end_0based_exclusive', 'strand', 'forward_sequence', 'model_normalization_eligible', 'motif_oriented_sequence', 'score', 'relative_score'))
        _need(row['scan_id'] in selection['scan_ids'] and row['hit_id'] not in hit_ids, 'hit_selected_scan_conflict'); scan = scans[row['scan_id']]
        _need(all(row[k] == scan[k] for k in ('sequence_id', 'matrix_occurrence_id', 'strand')), 'hit_population_conflict')
        sequence, matrix = sequences[row['sequence_id']], matrices[row['matrix_occurrence_id']]
        for key in ('start_0based', 'end_0based_exclusive', 'sequence_record_ordinal_0based', 'matrix_record_ordinal_0based'): _integer(row[key])
        _need(row['sequence_record_ordinal_0based'] == sequence['record_ordinal_0based'] and row['matrix_record_ordinal_0based'] == matrix['record_ordinal_0based']
            and row['end_0based_exclusive'] - row['start_0based'] == matrix['length'] and row['end_0based_exclusive'] <= sequence['length']
            and row['hit_id'] == _id('hit', [row['scan_id'], row['start_0based']]), 'hit_interval_conflict')
        _need(type(row['forward_sequence']) is str and row['forward_sequence'].isascii() and len(row['forward_sequence']) == matrix['length'] and type(row['model_normalization_eligible']) is bool, 'hit_sequence_invalid')
        _need(row['motif_oriented_sequence'] == (row['forward_sequence'] if row['strand'] == '+' else row['forward_sequence'].translate(str.maketrans('ACGT', 'TGCA'))[::-1]), 'hit_orientation_conflict')
        _validate_extended(row['score'], public=public); _validate_extended(row['relative_score'], relative=True, public=public)
        _need(row['score']['dtype'] == 'float32' and row['score']['origin'] == 'native_observation' and row['score']['unit'] == 'bits'
            and row['score']['classification'] != 'nan', 'hit_score_meaning_invalid')
        relative = row['relative_score']; descriptor = normalizations.get(relative['relative_normalization_id'])
        _need(descriptor is not None and descriptor['model_id'] == scan['model_id']
            and (public or _same(relative['operand_evidence']['score_location'], row['score']['location'])), 'hit_relative_operand_conflict')
        if descriptor['scientific_state'] == 'undefined':
            _need(relative['state'] == 'undefined' and relative['reason_code'] == descriptor['reason_code'], 'relative_state_conflict')
        hit_ids.add(row['hit_id'])
    _need(_same(value['hits'], [row for row in value['raw_threshold_matches'] if row['model_normalization_eligible']]), 'candidate_row_conflict')
    _need(value['status'] != 'complete' or value['execution']['native_outcome'] == 'succeeded', 'complete_execution_conflict')
    return deepcopy(value)


def validate_tf_binding_components(value):
    """Validate private calculation records without scoring or I/O."""
    return _validate_tf_binding_values(value)


def validate_tf_binding_public_value(value):
    """Validate the literal source-free public value, without inventing custody."""
    return _validate_tf_binding_values(value, public=True)


def project_tf_binding_return(components, source_ref):
    components = validate_tf_binding_components(components)
    _text(source_ref)
    return {'version': RETURN_VERSION, 'source_ref': source_ref,
        **{k: _public(deepcopy(v)) for k, v in components.items() if k != 'version'}}
