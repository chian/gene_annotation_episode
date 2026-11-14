"""Loss-preserving reader for the native legacy Mauve v4 segment format.

The suffix of the artifact is immaterial. No inferred inter-anchor alignment,
source fetch, native execution, or biological-completion claim is made here.
"""
from copy import deepcopy
import hashlib
import re

from . import mauve_v4_format_contracts as c
from .bvbrc_alignment_values import diagnostic, document_id


def _lines(data, encoding, artifact):
    lines, offset = [], 0
    for i, raw in enumerate(data.splitlines(keepends=True)):
        body = raw[:-2] if raw.endswith(b'\r\n') else raw[:-1] if raw.endswith((b'\r', b'\n')) else raw
        lines.append({'raw_line': body.decode(encoding), 'source_location': {
            'artifact': deepcopy(artifact), 'byte_start_0based': offset,
            'byte_end_0based_exclusive': offset + len(body), 'line_start_1based': i + 1,
            'line_end_1based_inclusive': i + 1, 'xml_path': None}})
        offset += len(raw)
    return lines


def _span(first, last):
    result = deepcopy(first)
    for key in ('byte_end_0based_exclusive', 'line_end_1based_inclusive'):
        result[key] = last[key]
    return result


def _metadata(raw):
    return re.match(r'(?:FormatVersion|Sequence|IntervalCount)(?:\S*|$)', raw) is not None


def _coordinates(raw):
    fields = raw.split()
    return bool(fields) and (re.match(r'[+-]?[0-9.]', fields[0]) is not None
        or fields[0].lower() in ('nan', 'inf', 'infinity', 'na')
        or len(fields) > 1 and all(re.fullmatch(r'[+-]?[0-9]+', s) for s in fields[1:]))


def _structural(raw):
    return raw == 'GappedAlignment' or re.match(r'Interval(?:[ \t]|$)', raw) or _metadata(raw) or _coordinates(raw)


def parse_mauve_v4(data: bytes, *, artifact: dict, encoding: str) -> dict:
    """Read supplied bytes; local malformed sections return retained partial data."""
    c.require(type(data) is bytes, 'bytes_required'); c.artifact(artifact)
    c.require(type(encoding) is str and encoding in ('ascii', 'utf-8'), 'encoding_unsupported')
    result = {'status': 'ok', 'value': None, 'diagnostics': []}

    def issue(code, path=''):
        c.require(code in c.PARSER_CODES)
        item = diagnostic('mauve_v4_' + code, phase='native_decode', path=path,
                          evidence_refs=[artifact['source_ref']])
        if item not in result['diagnostics']:
            result['diagnostics'].append(item)

    if hashlib.sha256(data).hexdigest() != artifact['sha256']:
        issue('digest_mismatch'); result['status'] = 'invalid'; return result
    try:
        lines = _lines(data, encoding, artifact)
    except UnicodeError:
        issue('encoding_invalid'); result['status'] = 'invalid'; return result
    first = next((l for l in lines if l['raw_line'].strip()), None)
    if first is None:
        issue('empty_input'); result['status'] = 'invalid'; return result
    fields = c.metadata_fields(first['raw_line'], first['source_location'], encoding)
    if fields['kind'] != 'format_version' or not c.available(fields['number']) or fields['number']['value'] != 4:
        issue('version_unsupported' if fields['kind'] == 'format_version' else 'format_unrecognized')
        result['status'] = 'invalid'; return result
    document = {'schema_version': 'mauve_v4_document_v1',
        'document_id': document_id('mauve_v4', artifact=artifact, parameters={'encoding': encoding}),
        'artifact': deepcopy(artifact), 'encoding': encoding, 'metadata': [], 'intervals': [],
        'unparsed': [], 'completeness': 'complete'}
    # Resolve every declaration before interpreting row cardinality. A later
    # conflicting count must not retroactively certify an earlier row section.
    for line in lines:
        if _metadata(line['raw_line']):
            document['metadata'].append({'metadata_index': len(document['metadata']), **deepcopy(line),
                **c.metadata_fields(line['raw_line'], line['source_location'], encoding)})
    seen = {}
    for row in document['metadata']:
        path = '/metadata/' + str(row['metadata_index'])
        number, member = row['number'], row['member_index_token']
        if number is not None and not c.available(number): issue('count_invalid', path)
        if member is not None and not c.available(member): issue('member_invalid', path)
        key = (row['kind'], member['value'] if c.available(member) else member['raw_token'] if member is not None else None)
        value = number['value'] if c.available(number) else row['value_token']
        if key in seen:
            issue('metadata_duplicate' if seen[key] == value else 'metadata_conflict', path)
        seen[key] = value
    count = c.scalar(document['metadata'], 'sequence_count')
    for key in ('sequence_count', 'interval_count'):
        if c.scalar(document['metadata'], key) is None: issue('header_missing', '/metadata')
    if c.scalar(document['metadata'], 'format_version') != 4: issue('metadata_conflict', '/metadata')
    if count is not None:
        members = {r['member_index_token']['value'] for r in document['metadata'] if c.available(r['member_index_token'])}
        if len({m for m in members if m < count}) != count: issue('header_missing', '/metadata')
        for member in members:
            if c.file_token(document['metadata'], member) is None or c.scalar(document['metadata'], 'sequence_length', member) is None:
                issue('header_missing', '/metadata')
        for row in document['metadata']:
            n = row['member_index_token']
            if c.available(n) and n['value'] >= count: issue('member_invalid', '/metadata/' + str(row['metadata_index']))
    current, i, ordinals = None, 0, set()
    while i < len(lines):
        line = lines[i]; raw, loc = line['raw_line'], line['source_location']
        if current is not None: current['source_location'] = _span(current['header_location'], loc)
        if _metadata(raw):
            i += 1; continue
        m = re.fullmatch(r'Interval(?:[ \t]+(.*))?', raw)
        if m:
            # The preceding interval excludes this new structural header.
            if current is not None:
                current['source_location'] = _span(current['header_location'], lines[i - 1]['source_location'])
            token = m[1] or ''; start = m.start(1) if m[1] is not None else len(raw)
            number = c.integer_token(token, c.sliced(raw, loc, start, len(raw), encoding), 0)
            current = {'interval_index': len(document['intervals']), 'raw_header': raw,
                'native_interval_ordinal': number, 'header_location': deepcopy(loc), 'segments': [],
                'unparsed': [], 'source_location': deepcopy(loc), 'completeness': 'complete'}
            document['intervals'].append(current)
            if not c.available(number): issue('interval_ordinal_invalid', '/intervals/' + str(current['interval_index']))
            elif number['value'] in ordinals: issue('interval_ordinal_duplicate', '/intervals/' + str(current['interval_index']))
            else: ordinals.add(number['value'])
            i += 1; continue
        if current is None:
            document['unparsed'].append(deepcopy(line))
            if raw.strip(): issue('unparsed_line', '/unparsed')
            i += 1; continue
        path = '/intervals/' + str(current['interval_index'])
        if raw == 'GappedAlignment':
            segment = {'kind': 'gapped_rows', 'segment_index': len(current['segments']),
                'marker': deepcopy(line), 'raw_header': None, 'header_location': None,
                'native_width': None, 'native_starts': [], 'expected_member_count': count,
                'sequence_rows': [], 'source_location': deepcopy(loc), 'completeness': 'complete'}
            i += 1
            if i < len(lines) and _coordinates(lines[i]['raw_line']):
                header = lines[i]; segment['raw_header'] = header['raw_line']; segment['header_location'] = deepcopy(header['source_location'])
                segment['native_width'], segment['native_starts'] = c.header_numbers(header['raw_line'], header['source_location'], encoding)
                segment['source_location'] = _span(loc, header['source_location']); i += 1
            else: issue('segment_header_malformed', path)
            ordinal = 0
            while i < len(lines) and not _structural(lines[i]['raw_line']):
                candidate = lines[i]; seq = candidate['raw_line']
                # A blank after the complete N rows is the interval separator.
                if not seq and count is not None and ordinal >= count: break
                if all(s in c.DNA for s in seq):
                    segment['sequence_rows'].append({'member_index_0based': ordinal, 'sequence': seq,
                        'sequence_parts': [deepcopy(candidate)], 'source_location': deepcopy(candidate['source_location'])})
                else:
                    current['unparsed'].append(deepcopy(candidate)); issue('sequence_symbol_invalid', path)
                    segment['completeness'] = 'partial'
                ordinal += 1; segment['source_location'] = _span(loc, candidate['source_location']); i += 1
            current['segments'].append(segment)
            current['source_location'] = _span(current['header_location'], segment['source_location'])
        elif _coordinates(raw):
            width, starts = c.header_numbers(raw, loc, encoding)
            current['segments'].append({'kind': 'ungapped_coordinates', 'segment_index': len(current['segments']),
                'raw_header': raw, 'header_location': deepcopy(loc), 'native_length': width,
                'native_starts': starts, 'source_location': deepcopy(loc), 'completeness': 'complete'})
            i += 1
        else:
            current['unparsed'].append(deepcopy(line))
            if raw.strip(): issue('unparsed_line', path + '/unparsed')
            i += 1
    for interval in document['intervals']:
        path = '/intervals/' + str(interval['interval_index'])
        for segment in interval['segments']:
            codes = c.segment_issues(segment, count)
            for code in codes: issue(code, path + '/segments/' + str(segment['segment_index']))
            if codes: segment['completeness'] = 'partial'
        if (not c.available(interval['native_interval_ordinal']) or any(s['completeness'] != 'complete' for s in interval['segments'])
                or any(r['raw_line'].strip() for r in interval['unparsed'])):
            interval['completeness'] = 'partial'
    if c.scalar(document['metadata'], 'interval_count') != len(document['intervals']): issue('count_conflict', '/intervals')
    # Duplicate agreeing metadata is retained with a qualification but does not
    # make an otherwise complete native population incomplete.
    if any(d['code'] != 'mauve_v4_metadata_duplicate' for d in result['diagnostics']):
        document['completeness'] = 'partial'; result['status'] = 'partial'
    result['value'] = c.validate_mauve_v4_document(document)
    return result


__all__ = ['parse_mauve_v4']
