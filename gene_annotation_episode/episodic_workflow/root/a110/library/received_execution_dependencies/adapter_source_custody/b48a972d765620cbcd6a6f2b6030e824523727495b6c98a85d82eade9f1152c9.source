"""Closed, detached native Mauve FormatVersion 4 records.

These checks examine supplied records, token correspondence and source ranges.
They do not open artifacts, run the native parser or authenticate task custody.
Membership in a gapped section is positional and is trusted only when the
entire declared N-row section is syntactically complete.
"""
from copy import deepcopy
import re

from .bvbrc_alignment_values import document_id, native_number, validate_native_number
from .phylogeny_calculation_contracts import location as shared_location
from .xmfa_format_contracts import _artifact as shared_artifact

DNA = frozenset('ACGTRYSWKMBDHVNacgtryswkmbdhvn-')
COMPLETENESS = ('complete', 'partial', 'unknown')
PARSER_CODES = frozenset(('bytes_required artifact_invalid encoding_unsupported '
    'dialect_unsupported digest_mismatch encoding_invalid empty_input format_unrecognized '
    'version_unsupported header_missing header_malformed metadata_duplicate metadata_conflict '
    'count_invalid count_conflict member_invalid member_duplicate interval_ordinal_invalid '
    'interval_ordinal_duplicate segment_header_malformed missing_sequence_row extra_sequence_row '
    'width_conflict sequence_symbol_invalid coordinate_invalid zero_member_has_residues '
    'header_member_conflict row_incomplete unparsed_line').split())


def require(condition, code='argument_invalid'):
    if not condition:
        raise ValueError('mauve_v4_' + code)


def shape(value, keys, code='argument_invalid'):
    require(type(value) is dict and set(value) == set(keys), code)


def array(value):
    require(type(value) is list)


def uint(value):
    require(type(value) is int and value >= 0)


def text(value, *, empty=False):
    require(type(value) is str and (empty or bool(value)))


def artifact(value):
    try:
        shared_artifact(value)
    except ValueError as error:
        raise ValueError('mauve_v4_artifact_invalid') from error


def location(value, owner):
    try:
        shared_location(value)
    except ValueError as error:
        raise ValueError('mauve_v4_argument_invalid') from error
    require(value['artifact'] == owner and value['xml_path'] is None)
    require(all(type(value[key]) is int for key in ('byte_start_0based',
        'byte_end_0based_exclusive', 'line_start_1based', 'line_end_1based_inclusive')))


def contained(inner, outer):
    for a, b in (('byte_start_0based', 'byte_end_0based_exclusive'),
                 ('line_start_1based', 'line_end_1based_inclusive')):
        require(outer[a] <= inner[a] <= inner[b] <= outer[b])


def atomic(raw, loc, owner, encoding):
    text(raw, empty=True)
    require('\n' not in raw and '\r' not in raw)
    location(loc, owner)
    try:
        length = len(raw.encode(encoding))
    except UnicodeError as error:
        raise ValueError('mauve_v4_argument_invalid') from error
    require(loc['byte_end_0based_exclusive'] - loc['byte_start_0based'] == length
            and loc['line_start_1based'] == loc['line_end_1based_inclusive'])


def sliced(raw, loc, start, end, encoding):
    out = deepcopy(loc)
    out['byte_start_0based'] += len(raw[:start].encode(encoding))
    out['byte_end_0based_exclusive'] = loc['byte_start_0based'] + len(raw[:end].encode(encoding))
    return out


def integer_token(token, loc, minimum=None):
    # Native integer syntax excludes decimal/scientific notation even when its
    # mathematical value is integral; the original token is always retained.
    decimal_integer = re.fullmatch(r'[+-]?[0-9]+', token) is not None
    result = native_number(token, source_location=loc, integer=decimal_integer, minimum=minimum)
    if not decimal_integer and result['state'] == 'available':
        result['state'] = 'incompatible'
    return result


def available(number):
    return number is not None and number['state'] == 'available' and type(number['value']) is int


def scalar(metadata, kind, member=None):
    rows = [r for r in metadata if r['kind'] == kind and (member is None or
        available(r['member_index_token']) and r['member_index_token']['value'] == member)]
    if not rows or any(not available(r['number']) for r in rows):
        return None
    values = {r['number']['value'] for r in rows}
    return next(iter(values)) if len(values) == 1 else None


def file_token(metadata, member):
    rows = [r for r in metadata if r['kind'] == 'sequence_file' and
            available(r['member_index_token']) and r['member_index_token']['value'] == member]
    values = {r['value_token'] for r in rows}
    return next(iter(values)) if len(values) == 1 and '' not in values else None


def metadata_fields(raw, loc, encoding):
    match = re.fullmatch(r'([^ \t]+)(?:[ \t](.*))?', raw)
    key, value = match.groups() if match else ('', raw)
    value = '' if value is None else value
    kinds = {'FormatVersion': 'format_version', 'SequenceCount': 'sequence_count',
             'IntervalCount': 'interval_count'}
    kind, member, number = kinds.get(key, 'unknown'), None, None
    named = re.fullmatch(r'Sequence(.*?)(File|Length)', key)
    if named:
        kind = 'sequence_' + named[2].lower()
        member = integer_token(named[1], sliced(raw, loc, 8, 8 + len(named[1]), encoding), 0)
    if kind in ('format_version', 'sequence_count', 'sequence_length', 'interval_count'):
        start = match.start(2) if match and match[2] is not None else len(raw)
        number = integer_token(value, sliced(raw, loc, start, len(raw), encoding), 0)
    return dict(kind=kind, member_index_token=member, value_token=value, number=number)


def header_numbers(raw, loc, encoding):
    tokens = list(re.finditer(r'\S+', raw))
    if not tokens:
        return integer_token('', sliced(raw, loc, len(raw), len(raw), encoding), 0), []
    numbers = [integer_token(t[0], sliced(raw, loc, t.start(), t.end(), encoding),
                             0 if i == 0 else None) for i, t in enumerate(tokens)]
    return numbers[0], numbers[1:]


def segment_issues(segment, expected):
    codes = []
    gapped = segment['kind'] == 'gapped_rows'
    width = segment['native_width'] if gapped else segment['native_length']
    if not available(width):
        codes.append('segment_header_malformed')
    starts = segment['native_starts']
    if expected is None or len(starts) != expected:
        codes.append('header_member_conflict')
    if any(not available(n) for n in starts):
        codes.append('coordinate_invalid')
    if gapped:
        rows = segment['sequence_rows']
        ordinals = [r['member_index_0based'] for r in rows]
        if expected is None or len(ordinals) != expected or any(n != i for i, n in enumerate(ordinals)):
            codes.append('missing_sequence_row' if expected is None or len(rows) < expected else 'extra_sequence_row')
        for row in rows:
            if available(width) and len(row['sequence']) != width['value']:
                codes.append('width_conflict')
            if any(c not in DNA for c in row['sequence']):
                codes.append('sequence_symbol_invalid')
            index = row['member_index_0based']
            if index < len(starts) and available(starts[index]) and starts[index]['value'] == 0 and row['sequence'].strip('-'):
                codes.append('zero_member_has_residues')
    return list(dict.fromkeys(codes))


def _number(actual, expected):
    if expected is None:
        require(actual is None)
    else:
        try:
            validate_native_number(actual)
        except ValueError as error:
            raise ValueError('mauve_v4_argument_invalid') from error
        require(actual == expected and type(actual['value']) is type(expected['value']))


def _raw(row, owner, encoding, outer=None):
    shape(row, ('raw_line', 'source_location'))
    atomic(row['raw_line'], row['source_location'], owner, encoding)
    if outer is not None:
        contained(row['source_location'], outer)


def validate_mauve_v4_document(document: dict) -> dict:
    """Validate a saved document without decoding its original artifact again."""
    shape(document, ('schema_version', 'document_id', 'artifact', 'encoding', 'metadata',
                     'intervals', 'unparsed', 'completeness'))
    require(document['schema_version'] == 'mauve_v4_document_v1')
    artifact(document['artifact']); owner = document['artifact']; encoding = document['encoding']
    require(type(encoding) is str and encoding in ('ascii', 'utf-8'), 'encoding_unsupported')
    require(document['document_id'] == document_id('mauve_v4', artifact=owner,
                                                  parameters={'encoding': encoding}))
    require(document['completeness'] in COMPLETENESS)
    for key in ('metadata', 'intervals', 'unparsed'):
        array(document[key])
    for index, row in enumerate(document['metadata']):
        shape(row, ('metadata_index', 'raw_line', 'kind', 'member_index_token', 'value_token',
                    'number', 'source_location'))
        uint(row['metadata_index']); require(row['metadata_index'] == index)
        atomic(row['raw_line'], row['source_location'], owner, encoding)
        expected = metadata_fields(row['raw_line'], row['source_location'], encoding)
        for key in ('member_index_token', 'number'):
            _number(row[key], expected[key])
        require(row['kind'] == expected['kind'] and row['value_token'] == expected['value_token'])
    require(any(r['kind'] == 'format_version' and available(r['number']) and r['number']['value'] == 4
                for r in document['metadata']), 'format_unrecognized')
    expected_count = scalar(document['metadata'], 'sequence_count')
    last_end = -1
    for index, interval in enumerate(document['intervals']):
        shape(interval, ('interval_index', 'raw_header', 'native_interval_ordinal', 'header_location',
                         'segments', 'unparsed', 'source_location', 'completeness'))
        uint(interval['interval_index']); require(interval['interval_index'] == index)
        require(interval['completeness'] in COMPLETENESS)
        location(interval['source_location'], owner)
        atomic(interval['raw_header'], interval['header_location'], owner, encoding)
        contained(interval['header_location'], interval['source_location'])
        require(interval['source_location']['byte_start_0based'] > last_end)
        last_end = interval['source_location']['byte_end_0based_exclusive'] - 1
        m = re.fullmatch(r'Interval(?:[ \t]+(.*))?', interval['raw_header'])
        require(m is not None)
        token = m[1] or ''; start = m.start(1) if m[1] is not None else len(m[0])
        _number(interval['native_interval_ordinal'], integer_token(token,
            sliced(m[0], interval['header_location'], start, len(m[0]), encoding), 0))
        array(interval['segments']); array(interval['unparsed'])
        last_segment_end = interval['header_location']['byte_end_0based_exclusive']
        for si, segment in enumerate(interval['segments']):
            gapped = type(segment) is dict and segment.get('kind') == 'gapped_rows'
            keys = ('kind', 'segment_index', 'raw_header', 'header_location', 'native_starts',
                    'source_location', 'completeness')
            shape(segment, (*keys, 'marker', 'native_width', 'expected_member_count', 'sequence_rows')
                  if gapped else (*keys, 'native_length'))
            require(segment['kind'] in ('gapped_rows', 'ungapped_coordinates'))
            uint(segment['segment_index']); require(segment['segment_index'] == si)
            require(segment['completeness'] in COMPLETENESS)
            location(segment['source_location'], owner)
            contained(segment['source_location'], interval['source_location'])
            require(segment['source_location']['byte_start_0based'] >= last_segment_end)
            last_segment_end = segment['source_location']['byte_end_0based_exclusive']
            if segment['raw_header'] is None:
                require(gapped and segment['header_location'] is None and segment['native_width'] is None
                        and segment['native_starts'] == [])
            else:
                atomic(segment['raw_header'], segment['header_location'], owner, encoding)
                contained(segment['header_location'], segment['source_location'])
                width, starts = header_numbers(segment['raw_header'], segment['header_location'], encoding)
                _number(segment['native_width' if gapped else 'native_length'], width)
                array(segment['native_starts']); require(len(starts) == len(segment['native_starts']))
                for actual, number in zip(segment['native_starts'], starts):
                    _number(actual, number)
            if gapped:
                _raw(segment['marker'], owner, encoding, segment['source_location'])
                require(segment['marker']['raw_line'] == 'GappedAlignment')
                if segment['expected_member_count'] is not None: uint(segment['expected_member_count'])
                require(segment['expected_member_count'] == expected_count)
                array(segment['sequence_rows']); ordinals = []
                previous = segment['header_location'] or segment['marker']['source_location']
                for row in segment['sequence_rows']:
                    shape(row, ('member_index_0based', 'sequence', 'sequence_parts', 'source_location'))
                    uint(row['member_index_0based']); ordinals.append(row['member_index_0based'])
                    text(row['sequence'], empty=True); array(row['sequence_parts'])
                    require(len(row['sequence_parts']) == 1)
                    _raw(row['sequence_parts'][0], owner, encoding, segment['source_location'])
                    require(row['sequence'] == row['sequence_parts'][0]['raw_line']
                            and row['source_location'] == row['sequence_parts'][0]['source_location'])
                    require(row['source_location']['line_start_1based'] > previous['line_end_1based_inclusive'])
                    previous = row['source_location']
                require(ordinals == sorted(set(ordinals)))
            issues = segment_issues(segment, expected_count)
            require(not issues or segment['completeness'] != 'complete')
            if segment['completeness'] == 'complete':
                require(not any(r['raw_line'].strip() and
                    segment['source_location']['byte_start_0based'] <= r['source_location']['byte_start_0based'] <
                    segment['source_location']['byte_end_0based_exclusive'] for r in interval['unparsed']))
        for row in interval['unparsed']:
            _raw(row, owner, encoding, interval['source_location'])
        if interval['completeness'] == 'complete':
            require(all(s['completeness'] == 'complete' for s in interval['segments'])
                    and all(not r['raw_line'].strip() for r in interval['unparsed'])
                    and available(interval['native_interval_ordinal']))
    for row in document['unparsed']:
        _raw(row, owner, encoding)
    if document['completeness'] == 'complete':
        require(scalar(document['metadata'], 'format_version') == 4 and expected_count is not None
                and scalar(document['metadata'], 'interval_count') == len(document['intervals'])
                and all(i['completeness'] == 'complete' for i in document['intervals'])
                and all(not r['raw_line'].strip() for r in document['unparsed']))
        ordinals = [i['native_interval_ordinal']['value'] for i in document['intervals']]
        require(len(ordinals) == len(set(ordinals)))
        for row in document['metadata']:
            if row['number'] is not None: require(available(row['number']))
            if row['member_index_token'] is not None:
                require(available(row['member_index_token']) and row['member_index_token']['value'] < expected_count)
        files = {r['member_index_token']['value'] for r in document['metadata']
                 if r['kind'] == 'sequence_file' and available(r['member_index_token'])}
        lengths = {r['member_index_token']['value'] for r in document['metadata']
                   if r['kind'] == 'sequence_length' and available(r['member_index_token'])}
        require(len(files) == len(lengths) == expected_count and files == lengths)
        require(all(file_token(document['metadata'], i) is not None and
                    scalar(document['metadata'], 'sequence_length', i) is not None for i in files))
    return deepcopy(document)


__all__ = ['validate_mauve_v4_document']
