"""Finite native phmmer text parsing. No hit selection or scientific judgment.

The documented HMMER3 tables and printed residue coordinates define this
representation. EOF is an ordinary boundary, including inside a damaged domain.
Complete preceding domains remain available. Native inclusion flags are data.
"""
import math
import re


VERSION = 'phmmer_printed_alignment_measurements_v1'
_QUERY = re.compile(r'^Query:\s*(\S+)\s+\[L=(\d+)\]')
_DOMAIN = re.compile(r'^\s*== domain (\d+)\s')
_RESIDUES = re.compile(r'^\s*(\S+)\s+(\d+|-)\s+([A-Za-z.*-]+)\s+(\d+|-)\s*$')


def paired_segments(alignment, query_sequence, reference_sequence):
    qs, qe = alignment['query_interval_aa_zero_based_half_open']
    rs, re_ = alignment['reference_interval_aa_zero_based_half_open']
    query, reference = alignment['query_aligned'], alignment['reference_aligned']
    gaps = '-.'
    if len(query) != len(reference):
        raise ValueError('native_alignment_column_count_mismatch')
    if ''.join(c for c in query if c not in gaps).upper() != query_sequence[qs:qe]:
        raise ValueError('native_query_alignment_does_not_match_fixed_query')
    if ''.join(c for c in reference if c not in gaps).upper() != reference_sequence[rs:re_]:
        raise ValueError('native_reference_alignment_does_not_match_acquired_sequence')
    intervals = {'query': [], 'reference': []}
    q, r, paired, identical = qs, rs, 0, 0
    for a, b in zip(query, reference):
        if a not in gaps and b not in gaps:
            paired += 1
            identical += a.upper() == b.upper()
            for role, position in (('query', q), ('reference', r)):
                rows = intervals[role]
                if rows and rows[-1][1] == position:
                    rows[-1][1] += 1
                else:
                    rows.append([position, position+1])
        q += a not in gaps
        r += b not in gaps
    if (q, r) != (qe, re_):
        raise ValueError('native_alignment_endpoints_disagree')
    return intervals, paired, identical


def numeric(value, *, nonnegative=False):
    number = float(value)
    if not math.isfinite(number) or nonnegative and number < 0:
        raise ValueError('invalid_native_numeric_value')
    return number


def hit_rows(path, *, query_id):
    """Each table row is independent; malformed rows do not erase siblings."""
    with open(path, 'rb') as stream:
        while True:
            start = stream.tell()
            line = stream.readline()
            if not line:
                return
            end = stream.tell()
            if not line.strip() or line.startswith(b'#'):
                continue
            try:
                fields = line.decode('utf-8').split(maxsplit=18)
                if len(fields) < 18 or fields[2] != query_id:
                    raise ValueError('native_hit_query_or_columns_mismatch')
                row = {'reference_id': fields[0], 'sequence_evalue': numeric(fields[4], nonnegative=True),
                    'sequence_bitscore': numeric(fields[5]),
                    'source_description': fields[18].rstrip() if len(fields) == 19 else '',
                    'table_byte_span': [start, end]}
                yield {'kind': 'hit', 'data': row}
            except (ValueError, UnicodeError) as error:
                code = (str(error) if type(error) is ValueError and str(error) in {
                    'native_hit_query_or_columns_mismatch', 'invalid_native_numeric_value'}
                    else 'native_hit_not_utf8' if isinstance(error, UnicodeError) else 'invalid_native_hit_row')
                yield {'kind': 'error', 'data': {'code': code,
                                               'role': 'hit_table', 'byte_span': [start, end]}}


def sequence_hits(path, *, query_id, query_length):
    """Available full-sequence scores when a failed job never flushed tblout."""
    query_seen, scores = False, False
    with open(path, 'rb') as stream:
        while True:
            start = stream.tell()
            raw = stream.readline()
            if not raw:
                return
            try:
                line = raw.decode('utf-8')
            except UnicodeError:
                continue  # The alignment pass reports the exact affected span.
            if line.startswith('Query:'):
                match = _QUERY.match(line)
                if query_seen or match is None or (match[1], int(match[2])) != (query_id, query_length):
                    return
                query_seen = True
            if query_seen and line.startswith('Scores for complete sequences'):
                scores = True
            if line.startswith('Domain annotation for each'):
                return
            fields = line.split(maxsplit=9)
            if not scores or len(fields) < 9:
                continue
            try:
                value, score = numeric(fields[0], nonnegative=True), numeric(fields[1])
                int(fields[7])
            except ValueError:
                continue
            yield {'reference_id': fields[8], 'sequence_evalue': value, 'sequence_bitscore': score,
                   'source_description': fields[9].rstrip() if len(fields) == 10 else '',
                   'text_byte_span': [start, stream.tell()]}


def alignment_rows(path, *, query_id, query_length):
    """Stream domain measurements; memory holds just one printed domain.

    Printed chunk endpoints and labels are checked independently of the
    subsequent exact input-sequence comparison. Negative scores and native
    below-inclusion domains remain valid representation values.
    """
    reference_id, metadata, current = None, {}, None
    query_seen, program_seen, sequence_inclusion = False, False, True
    included = {}

    def finish(end):
        nonlocal current
        if current is None:
            return None
        row, current = current, None
        error = row.pop('error')
        row['source_byte_span'][1] = end
        expected = row.pop('next_role')
        qparts, rparts = row.pop('query_parts'), row.pop('reference_parts')
        if error or expected != 'query' or not qparts or not rparts:
            return {'kind': 'error', 'data': {'code': error or 'incomplete_native_alignment',
                'role': 'native_text', 'byte_span': row['source_byte_span'],
                'reference_id': row['reference_id'], 'domain_index': row['domain_index']}}
        row.update(query_aligned=''.join(qparts), reference_aligned=''.join(rparts))
        return {'kind': 'alignment', 'data': row}

    with open(path, 'rb') as stream:
        while True:
            start = stream.tell()
            raw = stream.readline()
            if not raw:
                last = finish(start)
                if last:
                    yield last
                if not query_seen:
                    yield {'kind': 'error', 'data': {'code': 'native_query_header_unavailable',
                                                    'role': 'native_text', 'byte_span': [0, start]}}
                return
            try:
                line = raw.decode('utf-8')
            except UnicodeError:
                yield {'kind': 'error', 'data': {'code': 'native_alignment_not_utf8',
                    'role': 'native_text', 'byte_span': [start, stream.tell()]}}
                if current:
                    current['error'] = 'native_alignment_not_utf8'
                continue
            if line.startswith('# phmmer ::'):
                program_seen = True
            if line.startswith('Query:'):
                match = _QUERY.match(line)
                if query_seen or not program_seen or match is None or (match[1], int(match[2])) != (query_id, query_length):
                    yield {'kind': 'error', 'data': {'code': 'native_query_identity_mismatch',
                        'role': 'native_text', 'byte_span': [start, stream.tell()]}}
                    return
                query_seen = True
            if not query_seen:
                continue
            if line.startswith('  ------ inclusion'):
                sequence_inclusion = False
            if reference_id is None:
                fields = line.split(maxsplit=9)
                if len(fields) >= 9:
                    try:
                        numeric(fields[0], nonnegative=True)
                        included[fields[8]] = sequence_inclusion
                    except ValueError:
                        pass
            if line.startswith('>>') or line.startswith(('Internal pipeline', '//', '[ok]')):
                last = finish(start)
                if last:
                    yield last
                metadata = {}
                reference_id = line[2:].strip().split(maxsplit=1)[0] if line.startswith('>>') else None
                continue
            if reference_id is None:
                continue
            fields = line.split()
            if len(fields) == 16 and fields[0].isdigit() and fields[1] in {'!', '?'}:
                try:
                    index = int(fields[0])
                    metadata[index] = {'domain_index': index, 'domain_bitscore': numeric(fields[2]),
                        'conditional_domain_evalue': numeric(fields[4], nonnegative=True),
                        'independent_domain_evalue': numeric(fields[5], nonnegative=True),
                        'query_interval_aa_zero_based_half_open': [int(fields[6])-1, int(fields[7])],
                        'reference_interval_aa_zero_based_half_open': [int(fields[9])-1, int(fields[10])],
                        'native_inclusion_flag': fields[1] == '!',
                        'native_sequence_inclusion_flag': included.get(reference_id)}
                except ValueError:
                    yield {'kind': 'error', 'data': {'code': 'invalid_native_domain_table_row',
                        'role': 'native_text', 'byte_span': [start, stream.tell()], 'reference_id': reference_id}}
                continue
            domain = _DOMAIN.match(line)
            if domain:
                last = finish(start)
                if last:
                    yield last
                index = int(domain[1])
                if index not in metadata:
                    yield {'kind': 'error', 'data': {'code': 'native_domain_metadata_missing',
                        'role': 'native_text', 'byte_span': [start, stream.tell()], 'reference_id': reference_id,
                        'domain_index': index}}
                    continue
                current = {**metadata[index], 'reference_id': reference_id, 'source_byte_span': [start, None],
                    'query_parts': [], 'reference_parts': [], 'next_role': 'query', 'error': None}
                continue
            match = _RESIDUES.match(line) if current else None
            if match:
                role = current['next_role']
                expected_id = query_id if role == 'query' else reference_id
                if match[1] != expected_id:
                    current['error'] = 'native_alignment_operand_label_mismatch'
                parts = current[role+'_parts']
                begin, end = current[role+'_interval_aa_zero_based_half_open']
                consumed = sum(sum(c not in '-.' for c in part) for part in parts)
                count = sum(c not in '-.' for c in match[3])
                expected_positions = ('-', '-') if not count else (str(begin+consumed+1), str(begin+consumed+count))
                if (match[2], match[4]) != expected_positions:
                    current['error'] = 'native_alignment_chunk_coordinate_mismatch'
                parts.append(match[3])
                current['next_role'] = 'reference' if role == 'query' else 'query'
