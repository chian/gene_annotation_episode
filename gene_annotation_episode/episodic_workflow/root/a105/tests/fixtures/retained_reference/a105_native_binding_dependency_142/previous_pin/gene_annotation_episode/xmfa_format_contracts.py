"""Detached checks for the closed Mauve1 XMFA document.

Only supplied values are examined. This does not authenticate source custody,
open an artifact, call the text parser, bind input sequences, or calculate
alignment scores. Native coordinates remain distinct from source associations.
Atomic locations cover retained text excluding line endings; enclosing record
and block ranges include the intervening source bytes.
"""
from __future__ import annotations

from copy import deepcopy
import re

from .bvbrc_alignment_values import document_id, native_number, validate_native_number
from .phylogeny_format_contracts import _artifact as _shared_artifact
from .phylogeny_format_contracts import _location as _shared_location


DNA_SYMBOLS = frozenset('ACGTRYSWKMBDHVNacgtryswkmbdhvn-')
COMPLETENESS = ('complete', 'partial', 'truncated', 'unknown')
CALLER_ERROR_CODES = frozenset({
    'bytes_required', 'dialect_invalid', 'alphabet_invalid', 'encoding_invalid',
    'artifact_invalid', 'document_shape_invalid', 'schema_version_invalid',
    'document_identity_conflict', 'array_invalid', 'text_invalid',
    'encoding_conflict', 'index_invalid', 'index_order_conflict',
    'source_location_invalid', 'source_artifact_conflict',
    'source_location_outside_record', 'source_location_order_conflict',
    'source_text_location_conflict', 'metadata_shape_invalid',
    'metadata_token_conflict', 'native_number_invalid', 'native_token_conflict',
    'format_version_conflict', 'block_shape_invalid', 'record_shape_invalid',
    'sequence_part_shape_invalid', 'unparsed_shape_invalid',
    'header_token_conflict', 'sequence_parts_conflict', 'count_conflict',
    'coordinate_state_conflict', 'interval_conflict', 'span_conflict',
    'sequence_state_conflict', 'terminator_conflict', 'block_width_conflict',
    'completeness_conflict', 'unparsed_reference_conflict',
})

_DOCUMENT_KEYS = {'schema_version', 'document_id', 'artifact', 'dialect',
    'alphabet', 'encoding', 'format_version_token', 'completeness', 'metadata',
    'blocks', 'unparsed'}
_METADATA_KEYS = {'metadata_index', 'raw_line', 'kind', 'member_number',
    'value_token', 'integer_value', 'source_location'}
_BLOCK_KEYS = {'block_index', 'source_location', 'terminated', 'terminator_token',
    'terminator_location', 'records', 'alignment_column_count', 'completeness'}
_RECORD_KEYS = {'record_index', 'header_token', 'header_location', 'member_number',
    'start_1based', 'end_1based', 'strand', 'comment_token', 'sequence',
    'sequence_parts', 'source_location', 'coordinate_state',
    'interval_0based_half_open', 'span_matches_nongap', 'gapped_character_count',
    'nongap_character_count', 'sequence_state'}
_INTEGER = re.compile(r'[0-9]+\Z')
_HEADER = re.compile(r'>[ \t]*[0-9]+:[0-9]+-[0-9]+[ \t]+[+-](?:[ \t]+.*)?\Z')


def _require(condition, code):
    if not condition:
        raise ValueError('xmfa_' + code)


def _shape(value, keys, code):
    _require(type(value) is dict and set(value) == keys, code)


def _array(value):
    _require(type(value) is list, 'array_invalid')


def _index(value):
    _require(type(value) is int and value >= 0, 'index_invalid')


def _text(value, encoding):
    _require(type(value) is str and '\r' not in value and '\n' not in value,
             'text_invalid')
    try:
        return value.encode(encoding)
    except UnicodeError as error:
        raise ValueError('xmfa_encoding_conflict') from error


def _parameters(dialect, alphabet, encoding):
    _require(type(dialect) is str and dialect == 'mauve1', 'dialect_invalid')
    _require(type(alphabet) is str and alphabet == 'dna', 'alphabet_invalid')
    _require(type(encoding) is str and encoding in ('ascii', 'utf-8'), 'encoding_invalid')


def _artifact(value):
    try:
        _shared_artifact(value)
    except ValueError as error:
        raise ValueError('xmfa_artifact_invalid') from error


def _location(value, artifact):
    try:
        _shared_location(value, artifact=artifact)
    except ValueError as error:
        code = ('source_artifact_conflict' if str(error) == 'phylogeny_source_artifact_conflict'
                else 'source_location_invalid')
        raise ValueError('xmfa_' + code) from error
    # This text format has actual byte and line locations, never XML paths.
    _require(value['xml_path'] is None and all(type(value[key]) is int for key in (
        'byte_start_0based', 'byte_end_0based_exclusive', 'line_start_1based',
        'line_end_1based_inclusive')), 'source_location_invalid')


def _contained(inner, outer):
    for start, end in (('byte_start_0based', 'byte_end_0based_exclusive'),
                       ('line_start_1based', 'line_end_1based_inclusive')):
        _require(outer[start] <= inner[start] <= inner[end] <= outer[end],
                 'source_location_outside_record')


def _atomic(text, location, artifact, encoding):
    raw = _text(text, encoding)
    _location(location, artifact)
    _require(location['byte_end_0based_exclusive'] - location['byte_start_0based'] == len(raw)
             and location['line_start_1based'] == location['line_end_1based_inclusive'],
             'source_text_location_conflict')


def _slice_location(text, location, start, end, encoding):
    result = deepcopy(location)
    result['byte_start_0based'] += len(text[:start].encode(encoding))
    result['byte_end_0based_exclusive'] = (location['byte_start_0based']
                                        + len(text[:end].encode(encoding)))
    return result


def _integer_token(token, location, *, minimum):
    """Retain generic numeric evidence while disallowing nondecimal XMFA syntax."""
    decimal = _INTEGER.fullmatch(token) is not None
    result = native_number(token, source_location=location, integer=decimal, minimum=minimum)
    # Conversion limits must remain a native unavailable number, not an uncaught
    # exception. The shared generic reader preserves overflow tokens as such.
    if decimal and result['token_kind'] == 'malformed':
        result = native_number(token, source_location=location, minimum=minimum)
        if result['state'] == 'available':
            result['state'] = 'incompatible'
    if not decimal and result['state'] == 'available':
        result['state'] = 'incompatible'
    return result


def _number_equal(actual, expected):
    if expected is None:
        _require(actual is None, 'native_token_conflict')
        return
    try:
        validate_native_number(actual)
    except ValueError as error:
        raise ValueError('xmfa_native_number_invalid') from error
    _require(actual == expected and type(actual['value']) is type(expected['value']),
             'native_token_conflict')


def _metadata_fields(raw, location, encoding):
    """Decode a recognized key plus the entire remaining value, without joins."""
    kind, member, integer, value = 'comment', None, None, raw[1:]
    # The native writer supplies one tab. Consume exactly one separator so
    # leading payload spaces/tabs are not lost from filenames or raw numbers.
    key_match = re.fullmatch(r'#([^ \t]+)[ \t](.*)', raw)
    if key_match:
        key, token = key_match.group(1, 2)
        if key in ('FormatVersion', 'BackboneFile'):
            kind = 'format_version' if key == 'FormatVersion' else 'backbone_file'
        else:
            named = re.fullmatch(r'(Sequence|Annotation)(.*?)(File|Entry|Format)', key)
            if named and (named[1] == 'Sequence' or named[3] != 'Entry'):
                kind = named[1].lower() + '_' + named[3].lower()
                start = 1 + len(named[1])
                member = _integer_token(named[2],
                    _slice_location(raw, location, start, start + len(named[2]), encoding), minimum=1)
        if kind != 'comment':
            value = token
            if kind == 'sequence_entry':
                integer = _integer_token(value,
                    _slice_location(raw, location, key_match.start(2), len(raw), encoding), minimum=1)
    return {'kind': kind, 'member_number': member, 'value_token': value,
            'integer_value': integer}


def _header_fields(raw, location, encoding):
    """Recover delimited tokens even when their native syntax is malformed."""
    fields = {key: None for key in ('member_number', 'start_1based', 'end_1based',
                                    'strand', 'comment_token')}
    tokens = list(re.finditer(r'[^ \t]+', raw[1:]))
    if not tokens:
        return fields
    first, start = tokens[0].group(), tokens[0].start() + 1
    if ':' in first:
        colon = first.index(':')
        fields['member_number'] = _integer_token(first[:colon],
            _slice_location(raw, location, start, start + colon, encoding), minimum=1)
        endpoints = first[colon + 1:]
        # A leading minus belongs to a malformed negative start token. Any
        # further ambiguity remains in that token and in the full defline.
        separator = endpoints.find('-', 1 if endpoints.startswith('-') else 0)
        if separator >= 0:
            base = start + colon + 1
            for key, a, b in (('start_1based', 0, separator),
                              ('end_1based', separator + 1, len(endpoints))):
                fields[key] = _integer_token(endpoints[a:b],
                    _slice_location(raw, location, base + a, base + b, encoding), minimum=0)
    if len(tokens) > 1:
        strand = tokens[1].group()
        fields['strand'] = strand if strand in ('+', '-') else None
        end = tokens[1].end() + 1
        if end < len(raw):
            fields['comment_token'] = raw[end:].lstrip(' \t')
    return fields


def _available(number):
    return number is not None and number['state'] == 'available'


def _zero_pair(record):
    return (all(_available(record[key]) for key in ('start_1based', 'end_1based'))
            and record['start_1based']['value'] == record['end_1based']['value'] == 0)


def _record_facts(record, *, supported, unparsed=False):
    sequence = record['sequence']
    nongap = len(sequence) - sequence.count('-')
    sequence_state = 'dna_iupac' if all(s in DNA_SYMBOLS for s in sequence) else 'incompatible'
    member, start, end = (record[key] for key in ('member_number', 'start_1based', 'end_1based'))
    valid_header = _HEADER.fullmatch(record['header_token']) is not None
    codes = []
    if not valid_header:
        codes.append('header_malformed')
    if not _available(member):
        codes.append('member_invalid')
    if record['strand'] is None:
        codes.append('strand_invalid')
    if sequence_state == 'incompatible':
        codes.append('sequence_symbol_invalid')
    if unparsed:
        codes.append('unparsed_line')
    endpoints = all(_available(x) for x in (start, end))
    valid_endpoints = endpoints and (start['value'] == end['value'] == 0
        or 1 <= start['value'] <= end['value'])
    if not valid_endpoints:
        codes.append('coordinate_invalid')
    span_matches, interval = None, None
    if supported and valid_endpoints:
        span = 0 if _zero_pair(record) else end['value'] - start['value'] + 1
        span_matches = span == nongap
        if not span_matches:
            codes.append('zero_record_has_residues' if _zero_pair(record) else 'span_mismatch')
    if not supported or start is None and end is None:
        state = 'unknown'
    elif (unparsed or not valid_header or not _available(member) or record['strand'] is None
          or not valid_endpoints or span_matches is not True or sequence_state != 'dna_iupac'):
        state = 'incompatible'
    elif _zero_pair(record):
        state = 'absent_zero'
    else:
        state, interval = 'present', [start['value'] - 1, end['value']]
    return {'coordinate_state': state, 'interval_0based_half_open': interval,
            'span_matches_nongap': span_matches, 'gapped_character_count': len(sequence),
            'nongap_character_count': nongap, 'sequence_state': sequence_state}, codes


def _metadata_facts(metadata):
    versions, seen, issues = [], {}, []
    for entry in metadata:
        index, kind = entry['metadata_index'], entry['kind']
        if kind == 'comment':
            continue
        member = entry['member_number']
        if member is not None and not _available(member):
            issues.append(('member_invalid', index))
        if entry['integer_value'] is not None and not _available(entry['integer_value']):
            issues.append(('metadata_integer_invalid', index))
        if kind == 'format_version':
            versions.append(entry['value_token'])
        key = (kind, None if member is None else (
            member['value'] if _available(member) else member['raw_token']))
        value = entry['value_token']
        if kind == 'sequence_entry' and _available(entry['integer_value']):
            value = entry['integer_value']['value']
        previous = seen.setdefault(key, [])
        if previous:
            issues.append(('metadata_duplicate', index))
            if any(value != other for other in previous):
                issues.append(('metadata_conflict', index))
        previous.append(value)
    token = versions[0] if versions and len(set(versions)) == 1 else None
    if not versions:
        issues.append(('version_missing', None))
    elif token != 'Mauve1':
        issues.append(('version_unsupported', None))
    return token, issues


def _block_facts(block, *, supported, unparsed=False):
    rows, codes = block['records'], []
    if unparsed:
        codes.append('unparsed_line')
    widths = {row['gapped_character_count'] for row in rows if row['nongap_character_count'] > 0}
    width = next(iter(widths)) if len(widths) == 1 else None
    if len(widths) > 1:
        codes.append('row_width_conflict')
    if width is not None:
        for row in rows:
            allowed_empty = _zero_pair(row) and row['nongap_character_count'] == 0
            if row['gapped_character_count'] != width and not (
                    allowed_empty and row['gapped_character_count'] == 0):
                width = None
                codes.append('row_width_conflict')
                break
    if rows and all(_zero_pair(row) and row['nongap_character_count'] == 0 for row in rows):
        codes.append('all_zero_block')
    members = [row['member_number']['value'] for row in rows if _available(row['member_number'])]
    if len(set(members)) != len(members):
        codes.append('duplicate_member_record')
    if not block['terminated']:
        codes.append('missing_block_terminator')
    qualified = bool(codes) or not supported or any(_record_facts(row, supported=supported)[1] for row in rows)
    completeness = 'truncated' if not block['terminated'] else 'partial' if qualified else 'complete'
    return width, completeness, codes


def _document_completeness(document, metadata_issues):
    if any(not block['terminated'] for block in document['blocks']):
        return 'truncated'
    if metadata_issues or document['unparsed'] or any(
            block['completeness'] != 'complete' for block in document['blocks']):
        return 'partial'
    return 'complete' if document['blocks'] else 'unknown'


def validate_xmfa_document(value: dict) -> dict:
    """Validate every saved redundancy and return a completely detached dict.

    Atomic text and integer token locations must agree exactly. All stored
    numeric/coordinate flags are recomputed from the retained fields, including
    malformed tokens. This supplies no evidence that external bytes or input
    source sequences match; those are separate caller-owned checks.
    """
    _shape(value, _DOCUMENT_KEYS, 'document_shape_invalid')
    _parameters(value['dialect'], value['alphabet'], value['encoding'])
    _artifact(value['artifact'])
    artifact, encoding = value['artifact'], value['encoding']
    _require(value['schema_version'] == 'mauve_xmfa_document_v1', 'schema_version_invalid')
    expected_id = document_id('mauve_xmfa', artifact=artifact,
        parameters={key: value[key] for key in ('dialect', 'alphabet', 'encoding')})
    _require(value['document_id'] == expected_id, 'document_identity_conflict')
    for key in ('metadata', 'blocks', 'unparsed'):
        _array(value[key])
    atoms = []
    def atom(raw, loc):
        _atomic(raw, loc, artifact, encoding)
        atoms.append(loc)
    for index, entry in enumerate(value['metadata']):
        _shape(entry, _METADATA_KEYS, 'metadata_shape_invalid')
        _index(entry['metadata_index'])
        _require(entry['metadata_index'] == index, 'index_order_conflict')
        atom(entry['raw_line'], entry['source_location'])
        _require(entry['raw_line'].startswith('#'), 'metadata_token_conflict')
        expected = _metadata_fields(entry['raw_line'], entry['source_location'], encoding)
        for key in ('member_number', 'integer_value'):
            _number_equal(entry[key], expected[key])
        _require(entry['kind'] == expected['kind'] and entry['value_token'] == expected['value_token'],
                 'metadata_token_conflict')
        if index:
            _require(entry['source_location']['line_start_1based'] >
                     value['metadata'][index - 1]['source_location']['line_start_1based'],
                     'source_location_order_conflict')
    version, metadata_issues = _metadata_facts(value['metadata'])
    _require(value['format_version_token'] == version, 'format_version_conflict')
    supported = version == 'Mauve1'
    unparsed_blocks, unparsed_records = set(), {}
    previous_line = 0
    for entry in value['unparsed']:
        _shape(entry, {'raw_line', 'source_location', 'block_index', 'record_index'}, 'unparsed_shape_invalid')
        atom(entry['raw_line'], entry['source_location'])
        _require(not entry['raw_line'].startswith(('#', '>')), 'unparsed_reference_conflict')
        _require(entry['source_location']['line_start_1based'] > previous_line, 'source_location_order_conflict')
        previous_line = entry['source_location']['line_start_1based']
        block_index, record_index = entry['block_index'], entry['record_index']
        if block_index is None:
            _require(record_index is None, 'unparsed_reference_conflict')
            continue
        _index(block_index)
        _require(block_index < len(value['blocks']) and not entry['raw_line'].startswith('='),
                 'unparsed_reference_conflict')
        unparsed_blocks.add(block_index)
        if record_index is not None:
            _index(record_index)
            block = value['blocks'][block_index]
            _shape(block, _BLOCK_KEYS, 'block_shape_invalid')
            _array(block['records'])
            _require(record_index < len(block['records']), 'unparsed_reference_conflict')
            unparsed_records.setdefault((block_index, record_index), []).append(entry['source_location'])
    previous_block = None
    for index, block in enumerate(value['blocks']):
        _shape(block, _BLOCK_KEYS, 'block_shape_invalid')
        _index(block['block_index'])
        _require(block['block_index'] == index, 'index_order_conflict')
        _location(block['source_location'], artifact)
        if previous_block is not None:
            _require(previous_block['terminated'] and
                previous_block['source_location']['byte_end_0based_exclusive'] <
                block['source_location']['byte_start_0based'] and
                previous_block['source_location']['line_end_1based_inclusive'] <
                block['source_location']['line_start_1based'], 'source_location_order_conflict')
        previous_block = block
        _require(type(block['terminated']) is bool, 'terminator_conflict')
        _array(block['records'])
        _require(bool(block['records']), 'block_shape_invalid')
        previous_record = None
        for record_index, row in enumerate(block['records']):
            _shape(row, _RECORD_KEYS, 'record_shape_invalid')
            _index(row['record_index'])
            _require(row['record_index'] == record_index, 'index_order_conflict')
            atom(row['header_token'], row['header_location'])
            _require(row['header_token'].startswith('>'), 'header_token_conflict')
            _location(row['source_location'], artifact)
            _contained(row['source_location'], block['source_location'])
            _contained(row['header_location'], row['source_location'])
            _require(all(row['source_location'][key] == row['header_location'][key]
                         for key in ('byte_start_0based', 'line_start_1based')),
                     'source_text_location_conflict')
            if previous_record is not None:
                _require(previous_record['byte_end_0based_exclusive'] < row['source_location']['byte_start_0based']
                         and previous_record['line_end_1based_inclusive'] < row['source_location']['line_start_1based'],
                         'source_location_order_conflict')
            previous_record = row['source_location']
            expected = _header_fields(row['header_token'], row['header_location'], encoding)
            for key in ('member_number', 'start_1based', 'end_1based'):
                _number_equal(row[key], expected[key])
            _require(row['strand'] == expected['strand'] and row['comment_token'] == expected['comment_token'],
                     'header_token_conflict')
            _text(row['sequence'], encoding)
            _array(row['sequence_parts'])
            texts, previous = [], row['header_location']
            for part in row['sequence_parts']:
                _shape(part, {'text', 'source_location'}, 'sequence_part_shape_invalid')
                atom(part['text'], part['source_location'])
                _require(not part['text'].startswith(('#', '>', '=')), 'sequence_parts_conflict')
                _contained(part['source_location'], row['source_location'])
                _require(part['source_location']['byte_start_0based'] > previous['byte_end_0based_exclusive']
                         and part['source_location']['line_start_1based'] > previous['line_end_1based_inclusive'],
                         'source_location_order_conflict')
                previous = part['source_location']
                texts.append(part['text'])
            _require(row['sequence'] == ''.join(texts), 'sequence_parts_conflict')
            unknown_parts = unparsed_records.get((index, record_index), [])
            end_location = max([previous, *unknown_parts], key=lambda loc: loc['byte_end_0based_exclusive'])
            _require(all(row['source_location'][key] == end_location[key] for key in (
                'byte_end_0based_exclusive', 'line_end_1based_inclusive')), 'source_text_location_conflict')
            facts, _ = _record_facts(row, supported=supported, unparsed=bool(unknown_parts))
            for key in ('gapped_character_count', 'nongap_character_count'):
                _index(row[key])
                _require(row[key] == facts[key], 'count_conflict')
            _require(row['coordinate_state'] == facts['coordinate_state'], 'coordinate_state_conflict')
            interval = row['interval_0based_half_open']
            if interval is not None:
                _array(interval)
                _require(len(interval) == 2, 'interval_conflict')
                for endpoint in interval:
                    _index(endpoint)
            _require(interval == facts['interval_0based_half_open'], 'interval_conflict')
            _require(row['span_matches_nongap'] is facts['span_matches_nongap'], 'span_conflict')
            _require(row['sequence_state'] == facts['sequence_state'], 'sequence_state_conflict')
        first = block['records'][0]['header_location']
        _require(all(block['source_location'][key] == first[key] for key in (
            'byte_start_0based', 'line_start_1based')), 'source_text_location_conflict')
        if block['terminated']:
            atom(block['terminator_token'], block['terminator_location'])
            _require(block['terminator_token'].startswith('='), 'terminator_conflict')
            _contained(block['terminator_location'], block['source_location'])
            last = block['records'][-1]['source_location']
            _require(block['terminator_location']['line_start_1based'] > last['line_end_1based_inclusive']
                     and block['terminator_location']['byte_start_0based'] > last['byte_end_0based_exclusive'],
                     'terminator_conflict')
            _require(all(block['source_location'][key] == block['terminator_location'][key]
                         for key in ('byte_end_0based_exclusive', 'line_end_1based_inclusive')),
                     'source_text_location_conflict')
        else:
            _require(block['terminator_token'] is None and block['terminator_location'] is None
                     and index == len(value['blocks']) - 1, 'terminator_conflict')
        width, completeness, _ = _block_facts(block, supported=supported, unparsed=index in unparsed_blocks)
        if block['alignment_column_count'] is not None:
            _index(block['alignment_column_count'])
        _require(block['alignment_column_count'] == width, 'block_width_conflict')
        _require(block['completeness'] == completeness, 'completeness_conflict')
    for entry in value['unparsed']:
        block_index, record_index, loc = entry['block_index'], entry['record_index'], entry['source_location']
        if block_index is None:
            for block in value['blocks']:
                _require(not (block['source_location']['line_start_1based'] <= loc['line_start_1based'] <=
                              block['source_location']['line_end_1based_inclusive']), 'unparsed_reference_conflict')
        else:
            block = value['blocks'][block_index]
            _contained(loc, block['source_location'])
            if record_index is not None:
                _contained(loc, block['records'][record_index]['source_location'])
            else:
                # A block-only locator cannot conceal unknown text inside a
                # row whose coordinates are claimed to be complete.
                for row in block['records']:
                    _require(not (row['source_location']['line_start_1based'] <= loc['line_start_1based'] <=
                                  row['source_location']['line_end_1based_inclusive']), 'unparsed_reference_conflict')
    # Check all atomic source items together, including interleaved metadata.
    atoms.sort(key=lambda loc: (loc['byte_start_0based'], loc['line_start_1based']))
    for previous, current in zip(atoms, atoms[1:]):
        line_gap = current['line_start_1based'] - previous['line_end_1based_inclusive']
        byte_gap = current['byte_start_0based'] - previous['byte_end_0based_exclusive']
        _require(line_gap > 0 and byte_gap >= line_gap, 'source_location_order_conflict')
    if value['blocks'] and not value['blocks'][-1]['terminated']:
        _require(all(value['blocks'][-1]['source_location'][key] == atoms[-1][key]
                     for key in ('byte_end_0based_exclusive', 'line_end_1based_inclusive')),
                 'source_text_location_conflict')
    _require(any(entry['kind'] == 'format_version' for entry in value['metadata']) or bool(value['blocks']),
             'document_shape_invalid')
    _require(value['completeness'] == _document_completeness(value, metadata_issues), 'completeness_conflict')
    return deepcopy(value)


__all__ = ['validate_xmfa_document']
