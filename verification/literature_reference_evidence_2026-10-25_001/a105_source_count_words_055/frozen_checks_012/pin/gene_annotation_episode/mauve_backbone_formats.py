"""Pure readers for the two different native libMems backbone sidecars.

Raw tokens and byte/line locations survive local malformation. The complete
artifact hash is checked against supplied bytes; the caller retains those bytes.
No path is opened, no producer is run and no external correspondence is inferred.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re

from .bvbrc_alignment_values import native_number, document_id, diagnostic
from .xmfa_format_contracts import _artifact
from . import mauve_backbone_contracts as c


def _diagnostic(family, code, artifact, *, path='', error=False):
    return diagnostic('mauve_' + family + '_' + code, phase='native_decode',
        severity='error' if error else 'qualification', path=path,
        evidence_refs=[artifact['source_ref']])


def _operands(data, artifact, dialect, encoding, family, expected):
    check = c._Check(family)
    check.ok(type(data) is bytes, 'bytes_required')
    try:
        _artifact(artifact)
    except (TypeError, ValueError) as error:
        raise ValueError(check.prefix + 'artifact_invalid') from error
    check.ok(type(dialect) is str and dialect == expected, 'dialect_unsupported')
    check.ok(type(encoding) is str and encoding in ('ascii', 'utf-8'), 'encoding_unsupported')
    if hashlib.sha256(data).hexdigest() != artifact['sha256']:
        return None, [_diagnostic(family, 'digest_mismatch', artifact, error=True)]
    try:
        data.decode(encoding)
    except UnicodeError:
        return None, [_diagnostic(family, 'encoding_invalid', artifact, error=True)]
    rows, offset = [], 0
    for index, line in enumerate(data.splitlines(keepends=True)):
        raw = line.rstrip(b'\r\n')
        loc = {'artifact': deepcopy(artifact), 'byte_start_0based': offset,
            'byte_end_0based_exclusive': offset + len(raw), 'line_start_1based': index + 1,
            'line_end_1based_inclusive': index + 1, 'xml_path': None}
        rows.append({'raw_line': raw.decode(encoding), 'source_location': loc})
        offset += len(line)
    return rows, []


def _tokens(raw, encoding):
    result = []
    for match in re.finditer(r'\S+', raw['raw_line']):
        loc = deepcopy(raw['source_location'])
        loc['byte_start_0based'] += len(raw['raw_line'][:match.start()].encode(encoding))
        loc['byte_end_0based_exclusive'] = loc['byte_start_0based'] + len(match[0].encode(encoding))
        result.append({'raw_line': match[0], 'source_location': loc})
    return result


def _number(token, minimum=None):
    if token is None:
        return None
    integer = re.fullmatch(r'[+-]?[0-9]+', token['raw_line']) is not None
    value = native_number(token['raw_line'], source_location=token['source_location'], integer=integer, minimum=minimum)
    # Match the shared token validator after Python's decimal-int conversion
    # limit. Noninteger syntax never requests an enormous exponent as an int.
    if integer and value['token_kind'] == 'malformed':
        value = native_number(token['raw_line'], source_location=token['source_location'], minimum=minimum)
        if value['state'] == 'available':
            value['state'] = 'incompatible'
    # Native C++ integer fields do not accept scientific notation or decimals.
    if value['state'] == 'available' and not integer:
        value['state'] = 'incompatible'
    return value


def _new_document(family, dialect, artifact, encoding):
    return {'schema_version': 'mauve_' + family + '_document_v1',
        'document_id': document_id('mauve_' + family, artifact=artifact,
            parameters={'dialect': dialect, 'encoding': encoding}),
        'artifact': deepcopy(artifact), 'dialect': dialect, 'encoding': encoding,
        'rows': [], 'unparsed': [], 'completeness': 'unknown'}


def parse_mauve_backbone(data: bytes, *, artifact: dict, dialect: str, encoding: str) -> dict:
    """Read signed closed coordinate pairs using the explicit member header.

    Both final ``seq0_leftend`` and intermediate ``seq_0_leftend`` spellings are
    retained. Producer identity is deliberately not inferred from either one.
    """
    lines, diagnostics = _operands(data, artifact, dialect, encoding, 'backbone', c.BACKBONE_DIALECT)
    if lines is None:
        return {'status': 'invalid', 'value': None, 'diagnostics': diagnostics}
    header_index = next((i for i, raw in enumerate(lines) if any(
        re.fullmatch(r'seq_?.*?_(leftend|rightend)', t['raw_line']) for t in _tokens(raw, encoding))), None)
    if header_index is None:
        code = 'empty_input' if not any(raw['raw_line'].strip() for raw in lines) else 'header_missing'
        return {'status': 'invalid', 'value': None,
            'diagnostics': [_diagnostic('backbone', code, artifact, error=True)]}
    doc = _new_document('backbone', dialect, artifact, encoding)
    doc.update(header=lines[header_index], columns=[])
    doc['unparsed'].extend(lines[:header_index])
    for raw in lines[:header_index]:
        if raw['raw_line'].strip():
            diagnostics.append(_diagnostic('backbone', 'unparsed_line', artifact, path='/unparsed'))
    for index, token in enumerate(_tokens(doc['header'], encoding)):
        match = re.fullmatch(r'seq_?(.*?)_(leftend|rightend)', token['raw_line'])
        number, endpoint = None, 'unrecognized'
        if match:
            loc = deepcopy(token['source_location'])
            loc['byte_start_0based'] += len(token['raw_line'][:match.start(1)].encode(encoding))
            loc['byte_end_0based_exclusive'] = loc['byte_start_0based'] + len(match[1].encode(encoding))
            number = _number({'raw_line': match[1], 'source_location': loc}, 0)
            endpoint = 'left' if match[2] == 'leftend' else 'right'
        doc['columns'].append({'column_index': index, 'raw_token': token['raw_line'],
            'member_index_token': number, 'endpoint': endpoint, 'source_location': token['source_location']})
        if not c._available(number, 0):
            diagnostics.append(_diagnostic('backbone', 'header_malformed', artifact, path='/columns/' + str(index)))
    layout = c._header_layout(doc['columns'])
    header_good = True
    for group in layout:
        if group['member'] is None or len(group['left']) != 1 or len(group['right']) != 1 or group['unrecognized']:
            header_good = False
            diagnostics.append(_diagnostic('backbone', 'header_member_conflict', artifact, path='/columns'))
    for raw in lines[header_index + 1:]:
        if not raw['raw_line'].strip():
            doc['unparsed'].append(raw)
            continue
        index = len(doc['rows']); tokens = _tokens(raw, encoding)
        row = {'row_index': index, **raw, 'pairs': [], 'extra_tokens': [], 'completeness': 'complete'}
        consumed = set()
        for pindex, group in enumerate(layout):
            ends = []
            for key in ('left', 'right'):
                column = group[key][0] if len(group[key]) == 1 else None
                token = tokens[column] if column is not None and column < len(tokens) else None
                if token is not None:
                    consumed.add(column)
                ends.append(_number(token))
            state, strand, interval = c._pair_geometry(*ends)
            if group['member'] is None or len(group['left']) != 1 or len(group['right']) != 1 or group['unrecognized']:
                state, strand, interval = 'incompatible', None, None
            pairloc = deepcopy(raw['source_location'])
            available = [n['source_location'] for n in ends if n is not None]
            if available:
                pairloc['byte_start_0based'] = min(n['byte_start_0based'] for n in available)
                pairloc['byte_end_0based_exclusive'] = max(n['byte_end_0based_exclusive'] for n in available)
            row['pairs'].append({'pair_index': pindex, 'member_index_0based': group['member'],
                'native_left': ends[0], 'native_right': ends[1], 'state': state, 'strand': strand,
                'interval_0based_half_open': interval, 'source_location': pairloc})
            if state in ('missing', 'incompatible'):
                diagnostics.append(_diagnostic('backbone', 'row_incomplete' if state == 'missing' else 'coordinate_invalid',
                    artifact, path=f'/rows/{index}/pairs/{pindex}'))
        row['extra_tokens'] = [token for i, token in enumerate(tokens) if i not in consumed]
        if row['extra_tokens']:
            diagnostics.append(_diagnostic('backbone', 'count_conflict', artifact, path=f'/rows/{index}'))
        if not header_good or row['extra_tokens'] or any(p['state'] in ('missing', 'incompatible') for p in row['pairs']):
            row['completeness'] = 'partial'
        doc['rows'].append(row)
    doc['completeness'] = ('partial' if not header_good or diagnostics else 'complete' if doc['rows'] else 'unknown')
    value = c.validate_mauve_backbone_document(doc)
    return {'status': 'partial' if doc['completeness'] == 'partial' else 'ok', 'value': value, 'diagnostics': diagnostics}


def parse_mauve_bbcols(data: bytes, *, artifact: dict, dialect: str, encoding: str) -> dict:
    """Read internal interval0, left-column1, width, member0 tokens.

    An explicit empty dialect result preserves unknown completeness. It does not
    establish a zero backbone measurement or an XMFA block mapping.
    """
    lines, diagnostics = _operands(data, artifact, dialect, encoding, 'bbcols', c.BBCOLS_DIALECT)
    if lines is None:
        return {'status': 'invalid', 'value': None, 'diagnostics': diagnostics}
    doc = _new_document('bbcols', dialect, artifact, encoding)
    for raw in lines:
        tokens = _tokens(raw, encoding)
        if not tokens:
            doc['unparsed'].append(raw)
            continue
        index = len(doc['rows'])
        first = [_number(tokens[i], minimum) if i < len(tokens) else None for i, minimum in enumerate((0, 1, 1))]
        members = [_number(token, 0) for token in tokens[3:]]
        row = {'row_index': index, **raw, 'native_interval_index_0based': first[0],
            'native_left_column_1based': first[1], 'native_column_count': first[2],
            'native_member_indices_0based': members, 'columns_0based_half_open': None, 'state': 'parsed'}
        for i, (number, minimum, code) in enumerate(zip(first, (0, 1, 1),
                ('interval_ordinal_invalid', 'coordinate_invalid', 'count_invalid'))):
            if not c._available(number, minimum):
                diagnostics.append(_diagnostic('bbcols', 'row_incomplete' if number is None else code,
                    artifact, path=f'/rows/{index}/' + ('native_interval_index_0based', 'native_left_column_1based', 'native_column_count')[i]))
        if c._available(first[1], 1) and c._available(first[2], 1):
            row['columns_0based_half_open'] = [first[1]['value'] - 1, first[1]['value'] - 1 + first[2]['value']]
        valid_members = [n['value'] for n in members if c._available(n, 0)]
        if len(valid_members) != len(members):
            diagnostics.append(_diagnostic('bbcols', 'member_invalid', artifact, path=f'/rows/{index}/native_member_indices_0based'))
        if len(set(valid_members)) != len(valid_members):
            diagnostics.append(_diagnostic('bbcols', 'member_duplicate', artifact, path=f'/rows/{index}/native_member_indices_0based'))
        incomplete = any(n is None for n in first) or not members
        if incomplete:
            row['state'] = 'incomplete'
            diagnostics.append(_diagnostic('bbcols', 'row_incomplete', artifact, path=f'/rows/{index}'))
        elif (any(not c._available(n, m) for n, m in zip(first, (0, 1, 1)))
                or len(valid_members) != len(members) or len(set(valid_members)) != len(members)):
            row['state'] = 'incompatible'
        doc['rows'].append(row)
    if not doc['rows']:
        diagnostics.append(_diagnostic('bbcols', 'empty_input', artifact))
    doc['completeness'] = ('partial' if any(r['state'] != 'parsed' for r in doc['rows'])
                           else 'complete' if doc['rows'] else 'unknown')
    value = c.validate_mauve_bbcols_document(doc)
    return {'status': 'partial' if doc['completeness'] == 'partial' else 'ok', 'value': value, 'diagnostics': diagnostics}


__all__ = ['parse_mauve_backbone', 'parse_mauve_bbcols']
