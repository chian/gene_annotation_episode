"""Pure readers for supplied ATAC bedGraph and native MACS2 2.2.9.1 tables.

The caller retains original bytes and opens streams. No path is opened here.
Decimal lexemes and native geometry survive independently of numerical validity.
Streaming summaries are sealed only after exhaustion and identity validation.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import re
from typing import BinaryIO, Iterable, Iterator

from .atac_differential_contracts import (
    AtacArtifact, AtacBedGraphEvent, AtacCallpeakBinding, AtacComparisonBinding,
    AtacRetainedTrackTable, AtacTableReadError, AtacTrackBinding, BedGraphRow,
    MAX_COORDINATE, ParsedAtacTrack, ParsedMacs2Bdgdiff, ParsedMacs2NarrowPeak,
    ParsedMacs2PeaksXls, ParsedMacs2Summits, REPORTED_NUMBER_FIELDS, issue,
    track_row_key, valid_track_geometry, validate_atac_artifact,
    validate_atac_callpeak_binding, validate_atac_comparison_binding,
    validate_atac_retained_track_table, validate_atac_track_binding,
    validate_bedgraph_row,
)

_DECIMAL = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z')
_INTEGER = re.compile(r'[+-]?[0-9]+\Z')
_XLS_HEADER = ('chr', 'start', 'end', 'length', 'abs_summit', 'pileup',
               '-log10(pvalue)', 'fold_enrichment', '-log10(qvalue)', 'name')


def _chunks(content):
    if content is None:
        return
    if type(content) is bytes:
        yield content
        return
    if not callable(getattr(content, 'read', None)):
        raise ValueError('atac_supplied_bytes_or_binary_stream_required')
    while True:
        chunk = content.read(65536)
        if type(chunk) is not bytes:
            raise ValueError('atac_binary_stream_required')
        if not chunk:
            return
        yield chunk


def _lines(chunks, stats):
    """At most one current physical line plus the caller's current chunk."""
    pending = bytearray()
    line_number = 0
    start = 0
    for chunk in chunks:
        if type(chunk) is not bytes:
            raise ValueError('atac_binary_chunks_required')
        stats['hash'].update(chunk)
        stats['bytes'] += len(chunk)
        offset = 0
        while True:
            stop = chunk.find(b'\n', offset)
            if stop < 0:
                pending.extend(chunk[offset:])
                break
            pending.extend(chunk[offset:stop + 1])
            line_number += 1
            stats['lines'] = line_number
            end = start + len(pending)
            yield bytes(pending), dict(line_number=line_number, byte_start=start, byte_end=end)
            pending.clear()
            start, offset = end, stop + 1
    if pending:
        line_number += 1
        stats['lines'] = line_number
        yield bytes(pending), dict(line_number=line_number, byte_start=start,
                                  byte_end=start + len(pending))


def _header(text, locator):
    if text == '' or text.isspace():
        kind = 'blank'
    elif text.startswith('#'):
        kind = 'comment'
    elif re.match(r'track(?:\s|$)', text):
        kind = 'track'
    elif re.match(r'browser(?:\s|$)', text):
        kind = 'browser'
    else:
        return None
    return dict(locator=dict(locator), kind=kind, text=text)


def _native_issue(code, artifact, key, ordinal=None, locator=None, field=None,
                  requirement='none'):
    return issue(code, artifact['artifact_ref'], key,
                 row_ordinals=() if ordinal is None else (ordinal,),
                 locations=() if locator is None else (locator,), field=field,
                 requirement=requirement)


def _number(token, issues, artifact, key, ordinal, locator, field,
            *, integer=False, minimum=None, sentinel=None):
    if sentinel is not None and token == sentinel:
        return None
    matcher = _INTEGER if integer else _DECIMAL
    if matcher.fullmatch(token) is None:
        code = 'nonfinite_number' if token.lower().lstrip('+-') in ('nan', 'inf', 'infinity') else 'invalid_number'
        issues.append(_native_issue(code, artifact, key, ordinal, locator, field))
        return None
    try:
        value = int(token) if integer else float(token)
        if not integer and (not math.isfinite(value) or value == 0 and Decimal(token) != 0):
            raise OverflowError
    except (OverflowError, ValueError, InvalidOperation):
        issues.append(_native_issue('numeric_out_of_range', artifact, key, ordinal, locator, field))
        return None
    if minimum is not None and value < minimum:
        issues.append(_native_issue('numeric_out_of_range', artifact, key, ordinal, locator, field))
    return value


def _coordinate(token, issues, artifact, key, ordinal, locator, field):
    if _INTEGER.fullmatch(token) is None:
        issues.append(_native_issue('invalid_coordinate', artifact, key, ordinal, locator, field))
        return None
    try:
        return int(token)
    except ValueError:
        issues.append(_native_issue('numeric_out_of_range', artifact, key, ordinal, locator, field))
        return None


def _geometry(start, end, issues, artifact, key, ordinal, locator, *, one_based=False):
    valid = (type(start) is int and type(end) is int and
             (1 <= start <= end <= MAX_COORDINATE if one_based else
              0 <= start < end <= MAX_COORDINATE))
    if not valid:
        issues.append(_native_issue('invalid_coordinate', artifact, key, ordinal, locator,
                                    'interval', 'explicit_reference_mapping'))
    return valid


def _start(artifact, key, version, expected_format, *, missing=False):
    validate_atac_artifact(artifact, missing=missing)
    result = dict(version=version, artifact=deepcopy(artifact), binding_key=key,
                  state=dict(availability='missing' if missing else 'present',
                             byte_extent='unknown' if missing else artifact['supplied_extent'],
                             identity='unverified', format='compatible', output_extent='unknown'),
                  parsed_sha256=None, parsed_byte_count=0, physical_line_count=0,
                  data_row_count=None, readable_data_row_count=0, malformed_data_row_count=0,
                  headers=[], rows=[], invalid_records=[], issues=[])
    if artifact['format'] != expected_format:
        result['state']['format'] = 'unsupported'
        result['issues'].append(_native_issue('unsupported_format', artifact, key,
                                            requirement='compatible_native_mode'))
    if missing:
        result['issues'].append(_native_issue('artifact_missing', artifact, key,
                                            requirement='complete_artifact'))
    if artifact['producer_outcome'] == 'failed':
        result['issues'].append(_native_issue('producer_failed', artifact, key,
                                            requirement='complete_artifact'))
    if artifact['producer_run_ref'] is not None and artifact['writer_closed'] is not True:
        result['issues'].append(_native_issue('writer_not_closed', artifact, key,
                                            requirement='complete_artifact'))
    return result


def _seal(result, stats, *, read_failed=False):
    artifact, state = result['artifact'], result['state']
    if state['availability'] == 'missing':
        return result
    result['parsed_sha256'] = stats['hash'].hexdigest()
    result['parsed_byte_count'] = stats['bytes']
    result['physical_line_count'] = stats['lines']
    mismatch = ((artifact['expected_sha256'] is not None and
                 artifact['expected_sha256'] != result['parsed_sha256']) or
                (artifact['expected_size_bytes'] is not None and
                 artifact['expected_size_bytes'] != stats['bytes']))
    state['identity'] = ('mismatch' if mismatch else 'verified' if
                         artifact['expected_sha256'] is not None and
                         artifact['expected_size_bytes'] is not None else 'unverified')
    if mismatch:
        result['issues'].append(_native_issue('identity_mismatch', artifact, result['binding_key'],
                                            requirement='matching_artifact'))
    if read_failed or artifact['supplied_extent'] == 'partial' or (
            artifact['expected_size_bytes'] is not None and stats['bytes'] < artifact['expected_size_bytes']):
        state['byte_extent'] = 'partial'
        result['issues'].append(_native_issue('captured_bytes_partial', artifact, result['binding_key'],
                                            requirement='complete_artifact'))
    elif mismatch:
        state['byte_extent'] = 'unknown'
    supplied_track = result['version'] in ('atac_bedgraph_parsed_v1', 'atac_bedgraph_stream_summary_v1') and artifact['producer_run_ref'] is None
    complete_source = (state['byte_extent'] == 'complete' and state['identity'] == 'verified'
                       and not read_failed and (supplied_track or
                       artifact['producer_run_ref'] is not None and artifact['producer_outcome'] == 'succeeded'
                       and artifact['writer_closed'] is True))
    if complete_source and state['format'] == 'compatible':
        state['output_extent'] = 'complete'
    elif state['byte_extent'] == 'partial' or result['malformed_data_row_count'] or state['format'] == 'malformed' or read_failed:
        state['output_extent'] = 'partial'
    else:
        state['output_extent'] = 'unknown'
    count = result['readable_data_row_count'] + len(result['invalid_records'])
    # Streaming results do not retain invalid records; their occurrence count is explicit.
    count = stats.get('data', count)
    result['data_row_count'] = (count if complete_source and (count or state['output_extent'] == 'complete') else None)
    return result


def _stats():
    return dict(hash=hashlib.sha256(), bytes=0, lines=0, data=0)


def _track_fields(result, binding):
    result.update(binding=deepcopy(binding), coordinate_convention='zero_based_half_open',
                  numeric_storage='native_decimal_lexeme_plus_binary64_parse',
                  native_writer_precision=('unknown' if result['state']['availability'] == 'missing' else 'fixed_5_decimal_places' if
                      result['artifact']['producer_name'] == 'MACS2' and
                      result['artifact']['producer_version'] == '2.2.9.1' and
                      binding['callpeak_run_key'] is not None else 'supplied_lexical'
                      if result['artifact']['producer_run_ref'] is None else 'unknown'),
                  row_order='native_file_order', ordered_row_index=None,
                  chromosome_extents=[], overlap_groups=[], geometry_inspection='unknown',
                  unlocated_invalid_row_count=0)


def _extent(chromosome):
    return dict(chromosome=chromosome, first_reported_start=None, last_reported_end=None,
                readable_row_count=0, has_unreported_leading_span=None,
                has_unreported_internal_span=False, has_unreported_tail=None,
                reference_length_bp=None)


def _track_row(fields, ordinal, locator, artifact, key):
    issues = []
    start = _coordinate(fields[1], issues, artifact, key, ordinal, locator, 'start')
    end = _coordinate(fields[2], issues, artifact, key, ordinal, locator, 'end')
    _geometry(start, end, issues, artifact, key, ordinal, locator)
    value = _number(fields[3], issues, artifact, key, ordinal, locator, 'value_numeric')
    if value is not None and value < 0:
        issues.append(_native_issue('negative_pileup', artifact, key, ordinal, locator, 'value_numeric'))
    if not fields[0]:
        issues.append(_native_issue('invalid_coordinate', artifact, key, ordinal, locator, 'chromosome'))
    return (ordinal, locator['line_number'], locator['byte_start'], locator['byte_end'],
            fields[0], start, end, value, fields[3]), issues


def iter_atac_bedgraph_records(chunks: Iterable[bytes], *, artifact: AtacArtifact,
                              binding: AtacTrackBinding) -> Iterator[AtacBedGraphEvent]:
    """Stream exact occurrences; an interrupted iterator never emits a sealed summary.

    Ordered sources use an active-overlap window. Unsorted sources retain rows
    and explicitly make geometry inspection partial; they are never secretly sorted.
    """
    validate_atac_track_binding(binding)
    result = _start(artifact, binding['track_key'], 'atac_bedgraph_stream_summary_v1', 'bedgraph4')
    _track_fields(result, binding)
    if binding['source_artifact_ref'] != artifact['artifact_ref']:
        result['issues'].append(_native_issue('metadata_conflict', artifact, binding['track_key'],
                                            field='source_artifact_ref', requirement='matching_artifact'))
    for item in result['issues']:
        yield dict(kind='issue', issue=item)
    result['issues'] = []
    stats = _stats()
    extents = {}
    previous = None
    active = []
    ordered = True
    try:
        for raw, locator in _lines(chunks, stats):
            ordinal = stats['data']
            try:
                text = raw.rstrip(b'\n').removesuffix(b'\r').decode('utf-8')
            except UnicodeDecodeError:
                fields, row_issues = None, [_native_issue('invalid_utf8', artifact, binding['track_key'], ordinal, locator)]
            else:
                header = _header(text, locator)
                if header is not None:
                    yield dict(kind='header', header=header)
                    continue
                fields = text.split('\t')
                row_issues = []
                if len(fields) != 4:
                    row_issues.append(_native_issue('wrong_column_count', artifact, binding['track_key'], ordinal, locator))
            stats['data'] += 1
            if fields is None or len(fields) != 4 or not fields[0]:
                if not row_issues:
                    row_issues.append(_native_issue('invalid_coordinate', artifact, binding['track_key'], ordinal, locator, 'chromosome'))
                record = dict(row_ordinal=ordinal, locator=locator, fields=fields,
                              reason_codes=[i['code'] for i in row_issues])
                result['malformed_data_row_count'] += 1
                result['unlocated_invalid_row_count'] += 1
                if result['state']['format'] != 'unsupported':
                    result['state']['format'] = 'malformed'
                yield dict(kind='invalid', record=record)
            else:
                row, row_issues = _track_row(fields, ordinal, locator, artifact, binding['track_key'])
                result['readable_data_row_count'] += 1
                if row_issues:
                    result['malformed_data_row_count'] += 1
                    if result['state']['format'] != 'unsupported':
                        result['state']['format'] = 'malformed'
                if not valid_track_geometry(row):
                    result['unlocated_invalid_row_count'] += 1
                else:
                    key = track_row_key(row)
                    if previous is not None and key < previous:
                        ordered = False
                        for prior_extent in extents.values():
                            # A later out-of-order row may fill an apparent gap.
                            # False with partial inspection is not proof of continuity.
                            prior_extent['has_unreported_internal_span'] = False
                        row_issues.append(_native_issue('unsorted_track_rows', artifact, binding['track_key'], ordinal, locator,
                                                        requirement='unambiguous_track_values'))
                    if ordered:
                        active = [r for r in active if r[4] == row[4] and r[6] > row[5]]
                        for old in active:
                            code = 'duplicate_record' if old[4:] == row[4:] else 'overlapping_track_rows'
                            row_issues.append(issue(code, artifact['artifact_ref'], binding['track_key'],
                                                    row_ordinals=(old[0], row[0]),
                                                    locations=(_row_locator(old), locator),
                                                    requirement='unambiguous_track_values'))
                        active.append(row)
                    else:
                        active.clear()
                    previous = key
                    extent = extents.setdefault(row[4], _extent(row[4]))
                    if ordered and extent['last_reported_end'] is not None and row[5] > extent['last_reported_end']:
                        extent['has_unreported_internal_span'] = True
                    extent['first_reported_start'] = min(extent['first_reported_start'], row[5]) if extent['first_reported_start'] is not None else row[5]
                    extent['last_reported_end'] = max(extent['last_reported_end'] or 0, row[6])
                    extent['has_unreported_leading_span'] = extent['first_reported_start'] > 0
                    extent['readable_row_count'] += 1
                yield dict(kind='row', row=row)
            for item in row_issues:
                yield dict(kind='issue', issue=item)
    except OSError as error:
        _seal(result, stats, read_failed=True)
        result['chromosome_extents'] = list(extents.values())
        result['geometry_inspection'] = 'partial'
        failure = AtacTableReadError(_native_issue('stream_read_failed', artifact, binding['track_key'],
                                                  requirement='complete_artifact'),
                                     result['readable_data_row_count'], stats['bytes'])
        failure.partial_summary = result
        raise failure from error
    _seal(result, stats)
    for item in result['issues']:
        yield dict(kind='issue', issue=item)
    result['chromosome_extents'] = list(extents.values())
    result['geometry_inspection'] = 'complete' if ordered and not result['unlocated_invalid_row_count'] else 'partial'
    for name in ('headers', 'rows', 'invalid_records', 'issues', 'ordered_row_index', 'overlap_groups'):
        result.pop(name)
    yield dict(kind='summary', summary=result)


def _row_locator(row):
    return dict(line_number=row[1], byte_start=row[2], byte_end=row[3])


def _inspect_track_rows(result):
    """Small-table geometry inspection using a separate ordinal index."""
    ordered = sorted((row for row in result['rows'] if valid_track_geometry(row)), key=track_row_key)
    result['ordered_row_index'] = [row[0] for row in ordered]
    extents, groups, group, active = {}, [], [], []
    seen_pairs = {(item['code'], tuple(item['row_ordinals'])) for item in result['issues']}
    for row in ordered:
        extent = extents.setdefault(row[4], _extent(row[4]))
        active = [r for r in active if r[4] == row[4] and r[6] > row[5]]
        for old in active:
            code = 'duplicate_record' if old[4:] == row[4:] else 'overlapping_track_rows'
            if (code, (old[0], row[0])) not in seen_pairs:
                result['issues'].append(issue(code, result['artifact']['artifact_ref'], result['binding_key'],
                                              row_ordinals=(old[0], row[0]),
                                              locations=(_row_locator(old), _row_locator(row)),
                                              requirement='unambiguous_track_values'))
        if active:
            if not group:
                group = [r[0] for r in active]
            group.append(row[0])
        elif group:
            groups.append(group)
            group = []
        active.append(row)
        if extent['last_reported_end'] is not None and row[5] > extent['last_reported_end']:
            extent['has_unreported_internal_span'] = True
        if extent['first_reported_start'] is None:
            extent['first_reported_start'] = row[5]
        extent['last_reported_end'] = max(extent['last_reported_end'] or 0, row[6])
        extent['has_unreported_leading_span'] = extent['first_reported_start'] > 0
        extent['readable_row_count'] += 1
    if group:
        groups.append(group)
    result['overlap_groups'] = groups
    result['chromosome_extents'] = list(extents.values())
    result['geometry_inspection'] = 'partial' if result['unlocated_invalid_row_count'] else 'complete'
    seen_groups = {tuple(item['row_ordinals']) for item in result['issues'] if item['code'] in ('overlapping_track_rows', 'duplicate_record')}
    by_ordinal = {row[0]: row for row in ordered}
    for group in groups:
        if tuple(group) not in seen_groups:
            result['issues'].append(issue('overlapping_track_rows', result['artifact']['artifact_ref'],
                                          result['binding_key'], row_ordinals=group,
                                          locations=(_row_locator(by_ordinal[o]) for o in group),
                                          requirement='unambiguous_track_values'))


def parse_atac_bedgraph(content: bytes | BinaryIO | None, *, artifact: AtacArtifact,
                       binding: AtacTrackBinding) -> ParsedAtacTrack:
    validate_atac_track_binding(binding, missing=content is None)
    if content is None:
        result = _start(artifact, binding['track_key'], 'atac_bedgraph_parsed_v1', 'bedgraph4', missing=True)
        _track_fields(result, binding)
        return result
    arrays = dict(headers=[], rows=[], invalid_records=[], issues=[])
    try:
        for event in iter_atac_bedgraph_records(_chunks(content), artifact=artifact, binding=binding):
            if event['kind'] == 'summary':
                result = event['summary']
            else:
                field, value = {'row': ('rows', 'row'), 'header': ('headers', 'header'),
                                'invalid': ('invalid_records', 'record'), 'issue': ('issues', 'issue')}[event['kind']]
                arrays[field].append(event[value])
    except AtacTableReadError as error:
        result = error.partial_summary
        arrays['issues'].extend(result['issues'])
        arrays['issues'].append(error.issue)
    result.update(arrays, version='atac_bedgraph_parsed_v1')
    _inspect_track_rows(result)
    return result


def iter_atac_track_table_rows(chunks: Iterable[bytes], *, table: AtacRetainedTrackTable) -> Iterator[BedGraphRow]:
    """Validate JSONL occurrence arrays and final byte/hash/count identities.

    Consumers must exhaust this iterator before claiming complete calculations.
    A late failure leaves earlier yielded rows available but unsealed.
    """
    validate_atac_retained_track_table(table)
    stats = _stats()
    rows_read = 0
    previous = None
    def failure(code, locator=None):
        return AtacTableReadError(issue(code, table['artifact_ref'], table['source_artifact_ref'],
                                       locations=() if locator is None else (locator,),
                                       requirement='matching_artifact'), rows_read, stats['bytes'])
    try:
        for raw, locator in _lines(chunks, stats):
            if not raw.endswith(b'\n'):
                raise failure('incomplete_track_table_row', locator)
            try:
                row = json.loads(raw.decode('utf-8'), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
                validate_bedgraph_row(row)
            except (ValueError, UnicodeDecodeError, TypeError, RecursionError) as error:
                raise failure('invalid_atac_track_table_row', locator) from error
            row = tuple(row)
            if table['order'] == 'chromosome_start_end_source_ordinal':
                if not valid_track_geometry(row):
                    raise failure('invalid_ordered_track_geometry', locator)
                key = track_row_key(row)
            else:
                key = row[0]
            if previous is not None and key <= previous:
                raise failure('unsorted_track_table_rows', locator)
            previous = key
            rows_read += 1
            yield row
    except OSError as error:
        raise failure('stream_read_failed') from error
    if stats['bytes'] != table['byte_count'] or stats['hash'].hexdigest() != table['sha256']:
        raise failure('identity_mismatch')
    if rows_read != table['row_count']:
        raise failure('track_table_row_count_mismatch')


def iter_atac_track_rows(track: ParsedAtacTrack, *, chromosome: str,
                         ordered_rows: Iterable[BedGraphRow] | None = None) -> Iterator[BedGraphRow]:
    if type(chromosome) is not str or not chromosome:
        raise ValueError('atac_chromosome_required')
    if ordered_rows is None:
        if not isinstance(track['rows'], list) or not isinstance(track['ordered_row_index'], list):
            raise ValueError('atac_ordered_rows_required')
        by_ordinal = {row[0]: row for row in track['rows']}
        if len(by_ordinal) != len(track['rows']):
            raise ValueError('duplicate_track_row_ordinal')
        expected = {row[0] for row in track['rows'] if valid_track_geometry(row)}
        if set(track['ordered_row_index']) != expected or len(track['ordered_row_index']) != len(expected):
            raise ValueError('invalid_atac_ordered_row_index')
        ordered_rows = (by_ordinal[o] for o in track['ordered_row_index'])
    previous = None
    for row in ordered_rows:
        validate_bedgraph_row(row)
        if not valid_track_geometry(row):
            raise ValueError('invalid_ordered_track_geometry')
        key = track_row_key(row)
        if previous is not None and key <= previous:
            raise ValueError('unsorted_track_rows')
        previous = key
        if row[4] == chromosome:
            yield tuple(row)
    # Do not stop at a later chromosome: exhausting validates final table identity.


def _mode_issues(artifact, binding, key):
    items = []
    p = binding['selected_parameters']
    if (binding['selected_format'] != 'BAM' or binding['paired_end'] is not False
            or p['broad'] is not False or p['downsample'] is not False or p['nomodel'] is not True
            or binding['supplied_control_sample_ids'] != [] or binding['supplied_control_input_refs'] != []):
        items.append(_native_issue('unsupported_mode', artifact, key, requirement='compatible_native_mode'))
    if p['spmr'] is not False:
        items.append(_native_issue('unsupported_normalization', artifact, key, field='spmr',
                                   requirement='compatible_native_mode'))
    if artifact['producer_version'] != '2.2.9.1' or artifact['producer_name'] != 'MACS2':
        items.append(_native_issue('unsupported_mode', artifact, key, field='producer_version',
                                   requirement='compatible_native_mode'))
    return items


def _score_basis(callpeak):
    p = callpeak['selected_parameters']
    if p['pvalue_cutoff'] is not None:
        return 'minus_log10_pvalue'
    if p['qvalue_cutoff'] is not None:
        return 'minus_log10_qvalue'
    return 'unknown'


def _parse_table(content, artifact, binding, kind, category=None):
    xls = kind == 'xls'
    differential = kind == 'bdgdiff'
    if differential:
        validate_atac_comparison_binding(binding)
        key = binding['comparison_key']
        if category not in ('condition1', 'condition2', 'common'):
            raise ValueError('invalid_atac_bdgdiff_category')
    else:
        validate_atac_callpeak_binding(binding)
        key = binding['run_key']
    version, fmt, columns = {
        'xls': ('macs2_peaks_xls_parsed_v1', 'macs2_peaks_xls_narrow', 10),
        'narrowpeak': ('macs2_narrowpeak_parsed_v1', 'macs2_narrowpeak10', 10),
        'summits': ('macs2_summits_parsed_v1', 'macs2_summits_bed5', 5),
        'bdgdiff': ('macs2_bdgdiff_parsed_v1', 'macs2_bdgdiff_bed5', 5),
    }[kind]
    result = _start(artifact, key, version, fmt, missing=content is None)
    expected_ref = binding['artifact_roles'][category if differential else 'peaks_xls' if xls else kind]
    if expected_ref != artifact['artifact_ref'] and content is not None:
        result['issues'].append(_native_issue('metadata_conflict', artifact, key,
                                            field='artifact_roles', requirement='matching_artifact'))
    if artifact['producer_run_ref'] not in (None, binding['producer_ref']):
        result['issues'].append(_native_issue('metadata_conflict', artifact, key,
                                            field='producer_run_ref', requirement='matching_artifact'))
    if differential:
        pinned = artifact['producer_name'] == 'MACS2' and artifact['producer_version'] == '2.2.9.1'
        result.update(comparison_key=key, category=category,
                      coordinate_convention='zero_based_half_open_as_reported',
                      coordinate_qualification=('macs2_2_2_9_1_native_endpos_displacement_demonstrated' if pinned else 'unverified_native_version'),
                      score_precision='native_float32_then_6_significant_decimal_digits' if pinned else 'unknown')
        result['issues'].append(_native_issue('native_bdgdiff_coordinate_displacement' if pinned else 'unsupported_mode',
                                            artifact, key, requirement='compatible_native_mode'))
    else:
        result['issues'].extend(_mode_issues(artifact, binding, key))
        result.update(callpeak_run_key=key, coordinate_convention='one_based_inclusive' if xls else 'zero_based_half_open')
        if xls:
            result.update(reported_metadata=_metadata(), reported_numbers=_reported_numbers(), peak_geometry=[])
        else:
            result['score_basis'] = _score_basis(binding)
    if content is None:
        return result
    stats = _stats()
    header_seen = False
    read_failed = False
    try:
        for raw, locator in _lines(_chunks(content), stats):
            ordinal = stats['data']
            row_issues = []
            try:
                text = raw.rstrip(b'\n').removesuffix(b'\r').decode('utf-8')
            except UnicodeDecodeError:
                fields = None
                row_issues.append(_native_issue('invalid_utf8', artifact, key, ordinal, locator))
            else:
                header = _header(text, locator)
                if header is not None:
                    result['headers'].append(header)
                    if xls:
                        _read_metadata(text, locator, result)
                    elif differential and header['kind'] == 'track':
                        native_category = re.search(r'name="(condition [12]|common) \(peaks\)"', text)
                        if native_category and native_category[1].replace(' ', '') != category:
                            result['issues'].append(_native_issue('condition_binding_conflict', artifact, key,
                                                                locator=locator, field='category', requirement='condition_mapping'))
                    continue
                fields = text.split('\t')
                if xls and tuple(fields) == _XLS_HEADER:
                    result['headers'].append(dict(locator=locator, kind='column_header', text=text))
                    header_seen = True
                    continue
                if len(fields) != columns:
                    row_issues.append(_native_issue('wrong_column_count', artifact, key, ordinal, locator))
                if xls and not header_seen:
                    row_issues.append(_native_issue('missing_column_header', artifact, key, ordinal, locator,
                                                    requirement='compatible_native_mode'))
            stats['data'] += 1
            if fields is None or len(fields) != columns:
                result['invalid_records'].append(dict(row_ordinal=ordinal, locator=locator, fields=fields,
                                                       reason_codes=[x['code'] for x in row_issues]))
            else:
                row = _peak_row(fields, ordinal, locator, result, kind, row_issues)
                result['rows'].append(row)
                result['readable_data_row_count'] += 1
            if row_issues:
                result['malformed_data_row_count'] += 1
                if result['state']['format'] != 'unsupported':
                    result['state']['format'] = 'malformed'
                result['issues'].extend(row_issues)
    except OSError:
        read_failed = True
        result['issues'].append(_native_issue('stream_read_failed', artifact, key, requirement='complete_artifact'))
    if xls:
        if not header_seen:
            if result['state']['format'] != 'unsupported':
                result['state']['format'] = 'malformed'
            result['issues'].append(_native_issue('missing_column_header', artifact, key, requirement='compatible_native_mode'))
        _finish_metadata(result, binding)
    return _seal(result, stats, read_failed=read_failed)


def _peak_row(fields, ordinal, locator, result, kind, issues):
    artifact, key = result['artifact'], result['binding_key']
    row = dict(row_ordinal=ordinal, locator=locator, original_fields=fields, chromosome=fields[0])
    start = _coordinate(fields[1], issues, artifact, key, ordinal, locator, 'start')
    end = _coordinate(fields[2], issues, artifact, key, ordinal, locator, 'end')
    valid = _geometry(start, end, issues, artifact, key, ordinal, locator, one_based=kind == 'xls')
    if not fields[0]:
        issues.append(_native_issue('invalid_coordinate', artifact, key, ordinal, locator, 'chromosome'))
        valid = False
    def number(index, name, **kwargs):
        return _number(fields[index], issues, artifact, key, ordinal, locator, name, **kwargs)
    if kind == 'xls':
        row.update(start1=start, end1=end, length_bp=number(3, 'length_bp', integer=True, minimum=1),
                   abs_summit1=number(4, 'abs_summit1', integer=True, minimum=0),
                   pileup=number(5, 'pileup', minimum=0),
                   minus_log10_pvalue=number(6, 'minus_log10_pvalue', minimum=0, sentinel='-1'),
                   fold_enrichment=number(7, 'fold_enrichment', minimum=0),
                   minus_log10_qvalue=number(8, 'minus_log10_qvalue', minimum=0, sentinel='-1'), name=fields[9])
        span = end - start + 1 if valid else None
        summit = row['abs_summit1']
        summit0 = summit - 1 if valid and summit is not None and start <= summit <= end else None
        geometry_status = 'valid' if valid else 'invalid'
        if valid and row['length_bp'] != span:
            geometry_status = 'invalid'
            issues.append(_native_issue('peak_representation_conflict', artifact, key, ordinal, locator, 'length_bp'))
        if summit0 is None:
            if summit not in (None, 0):
                geometry_status = 'invalid'
                issues.append(_native_issue('invalid_coordinate', artifact, key, ordinal, locator, 'abs_summit1'))
            elif geometry_status == 'valid':
                geometry_status = 'partial'
        result['peak_geometry'].append(dict(row_ordinal=ordinal, start0=start - 1 if valid else None,
                                           end0=end if valid else None, summit0=summit0,
                                           span_bp=span, status=geometry_status))
    elif kind == 'narrowpeak':
        row.update(start0=start, end0=end, name=fields[3],
                   display_score=number(4, 'display_score', integer=True, minimum=0), strand=fields[5],
                   signal_value=number(6, 'signal_value', minimum=0),
                   minus_log10_pvalue=number(7, 'minus_log10_pvalue', minimum=0, sentinel='-1'),
                   minus_log10_qvalue=number(8, 'minus_log10_qvalue', minimum=0, sentinel='-1'),
                   summit_offset0=number(9, 'summit_offset0', integer=True, minimum=0, sentinel='-1'))
        if row['strand'] != '.':
            issues.append(_native_issue('unsupported_mode', artifact, key, ordinal, locator, 'strand', 'compatible_native_mode'))
        if valid and row['summit_offset0'] is not None and not 0 <= row['summit_offset0'] < end - start:
            issues.append(_native_issue('invalid_coordinate', artifact, key, ordinal, locator, 'summit_offset0'))
    elif kind == 'summits':
        row.update(start0=start, end0=end, name=fields[3], score=number(4, 'score', minimum=0, sentinel='-1'))
        if valid and end != start + 1:
            issues.append(_native_issue('invalid_coordinate', artifact, key, ordinal, locator, 'summit_width'))
    else:
        row.update(reported_start0=start, reported_end0=end, name=fields[3], reported_score=number(4, 'reported_score'))
    return row


def _metadata():
    return dict(macs_version=None, command_line=None, name=None, format=None,
                treatment_paths=None, control_paths=None, control_presence='unknown',
                paired_end=None, broad=None, scaling_direction='unknown', local_lambda='unknown',
                field_locations={})


def _reported_numbers():
    return {name: dict(value=None, lexeme=None, state='missing', locations=[]) for name in REPORTED_NUMBER_FIELDS}


def _store_metadata(result, field, value, locator):
    metadata = result['reported_metadata']
    locations = metadata['field_locations'].setdefault(field, [])
    if locations and metadata[field] != value:
        metadata[field] = 'unknown' if field in ('control_presence', 'scaling_direction', 'local_lambda') else None
        result['issues'].append(_native_issue('metadata_conflict', result['artifact'], result['binding_key'],
                                            locator=locator, field=field, requirement='original_native_metadata'))
    elif not locations:
        metadata[field] = value
    locations.append(dict(locator))


def _store_number(result, field, token, locator, *, integer=False, sign=1):
    row = result['reported_numbers'][field]
    errors = []
    value = _number(token, errors, result['artifact'], result['binding_key'], None, locator, field,
                    integer=integer, minimum=None if field == 'shift_bp' else 0)
    if value is not None:
        value *= sign
    if row['locations'] and (row['state'] != 'present' or value != row['value']):
        row.update(value=None, lexeme=None, state='conflicting')
        errors.append(_native_issue('metadata_conflict', result['artifact'], result['binding_key'],
                                    locator=locator, field=field, requirement='original_native_metadata'))
    elif not row['locations']:
        row.update(value=value, lexeme=token, state='invalid' if errors else 'present')
    row['locations'].append(dict(locator))
    result['issues'].extend(errors)


def _read_metadata(text, locator, result):
    if text == '# MACS will save fragment pileup signal per million reads':
        result['issues'].append(_native_issue('unsupported_normalization', result['artifact'], result['binding_key'],
                                            locator=locator, field='spmr', requirement='compatible_native_mode'))
        return
    if text == '# Larger dataset will be randomly sampled towards smaller dataset.':
        result['issues'].append(_native_issue('unsupported_mode', result['artifact'], result['binding_key'],
                                            locator=locator, field='downsample', requirement='compatible_native_mode'))
        return
    for prefix, field in (('# This file is generated by MACS version ', 'macs_version'),
                          ('# Command line: ', 'command_line'), ('# name = ', 'name'), ('# format = ', 'format')):
        if text.startswith(prefix):
            _store_metadata(result, field, text[len(prefix):], locator)
            return
    for prefix, field in (('# ChIP-seq file = ', 'treatment_paths'), ('# control file = ', 'control_paths')):
        if text.startswith(prefix):
            try:
                value = ast.literal_eval(text[len(prefix):])
                if value is not None and (type(value) is not list or any(type(v) is not str for v in value)):
                    raise ValueError
            except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
                result['issues'].append(_native_issue('metadata_conflict', result['artifact'], result['binding_key'],
                                                    locator=locator, field=field, requirement='original_native_metadata'))
                return
            _store_metadata(result, field, value, locator)
            if field == 'control_paths':
                _store_metadata(result, 'control_presence', 'present' if value else 'absent', locator)
            return
    for prefix, field in (('# Paired-End mode is ', 'paired_end'), ('# Broad region calling is ', 'broad')):
        if text.startswith(prefix) and text[len(prefix):] in ('on', 'off'):
            _store_metadata(result, field, text[len(prefix):] == 'on', locator)
            return
    scaling = {'# Larger dataset will be scaled towards smaller dataset.': 'larger_to_smaller',
               '# Smaller dataset will be scaled towards larger dataset.': 'smaller_to_larger'}
    if text in scaling:
        _store_metadata(result, 'scaling_direction', scaling[text], locator)
        return
    if text == '# local lambda is disabled!':
        _store_metadata(result, 'local_lambda', 'disabled', locator)
        return
    prefixes = {'# effective genome size = ': ('effective_genome_size_bp', False),
                '# band width = ': ('band_width_bp', True), '# qvalue cutoff = ': ('qvalue_cutoff', False),
                '# pvalue cutoff = ': ('pvalue_cutoff', False), '# d = ': ('d_bp', True)}
    for prefix, (field, integer) in prefixes.items():
        if text.startswith(prefix):
            _store_number(result, field, text[len(prefix):], locator, integer=integer)
            return
    match = re.fullmatch(r'# model fold = \[([^,]+),\s*([^\]]+)\]', text)
    if match:
        for field, token in zip(('model_fold_lower', 'model_fold_upper'), match.groups()):
            _store_number(result, field, token.strip(), locator)
        return
    match = re.fullmatch(r'# Range for calculating regional lambda is: (?:[0-9]+ bps and )?([^ ]+) bps', text)
    if match:
        _store_number(result, 'large_local_window_bp', match[1], locator, integer=True)
        return
    match = re.fullmatch(r'# (tag|fragment) size is determined as ([^ ]+) bps', text)
    if match:
        _store_number(result, match[1] + '_size_bp', match[2], locator, integer=True)
        return
    match = re.fullmatch(r'# total (tags|fragments) in (treatment|control): (.+)', text)
    if match:
        _store_number(result, match[2] + '_total_' + match[1], match[3], locator, integer=True)
        return
    match = re.fullmatch(r'# (tags|fragments) after filtering in (treatment|control): (.+)', text)
    if match:
        _store_number(result, match[2] + '_postfilter_' + match[1], match[3], locator, integer=True)
        return
    match = re.fullmatch(r'# maximum duplicate (?:tags at the same position|fragments) in (treatment|control) = (.+)', text)
    if match:
        _store_number(result, match[1] + '_max_duplicates', match[2], locator, integer=True)
        return
    match = re.fullmatch(r'# Redundant rate in (treatment|control): (.+)', text)
    if match:
        _store_number(result, match[1] + '_redundant_rate', match[2], locator)
        return
    match = re.fullmatch(r"# Sequencing ends will be shifted towards ([35])' by ([^ ]+) bp\(s\)", text)
    if match:
        _store_number(result, 'shift_bp', match[2], locator, integer=True, sign=-1 if match[1] == '5' else 1)


def _finish_metadata(result, callpeak):
    metadata, numbers = result['reported_metadata'], result['reported_numbers']
    artifact, key = result['artifact'], result['binding_key']
    def conflict(field):
        result['issues'].append(_native_issue('metadata_conflict', artifact, key, field=field,
                                            requirement='original_native_metadata'))
    for reported, selected in (('format', callpeak['selected_format']), ('paired_end', callpeak['paired_end']),
                               ('broad', callpeak['selected_parameters']['broad']), ('macs_version', artifact['producer_version'])):
        if metadata[reported] is not None and selected is not None and metadata[reported] != selected:
            conflict(reported)
    if metadata['format'] is not None and metadata['paired_end'] is not None:
        if (metadata['format'] in ('BAMPE', 'BEDPE')) != metadata['paired_end']:
            conflict('paired_end')
    controls = callpeak['supplied_control_input_refs']
    if controls is not None and metadata['control_presence'] != 'unknown':
        if bool(controls) != (metadata['control_presence'] == 'present'):
            conflict('control_presence')
    # Compare file paths only against actual argv paths. Artifact references need not be paths.
    argv = callpeak['selected_argv']
    for field, flags in (('treatment_paths', ('-t', '--treatment')), ('control_paths', ('-c', '--control'))):
        paths = []
        for index, token in enumerate(argv):
            if token in flags:
                for path in argv[index + 1:]:
                    if path.startswith('-'):
                        break
                    paths.append(path)
        if paths and metadata[field] is not None and paths != metadata[field]:
            conflict(field)
    for field in ('qvalue_cutoff', 'pvalue_cutoff', 'shift_bp', 'large_local_window_bp'):
        selected = callpeak['selected_parameters'][field]
        reported = numbers[field]
        if selected is not None and reported['state'] == 'present' and selected != reported['value']:
            # Native cutoff comments use %.2e, unlike the retained selected
            # parameter. A legitimate rounded header is not a contradiction.
            rounded_match = field in ('qvalue_cutoff', 'pvalue_cutoff') and float(format(selected, '.2e')) == reported['value']
            if not rounded_match:
                conflict(field)
    if metadata['paired_end'] is not None:
        unused = 'tags' if metadata['paired_end'] else 'fragments'
        for field in numbers:
            if field.endswith('_' + unused) or field == ('tag_size_bp' if unused == 'tags' else 'fragment_size_bp'):
                if numbers[field]['state'] == 'missing':
                    numbers[field]['state'] = 'not_measured'
                elif numbers[field]['state'] == 'present':
                    conflict(field)
    if metadata['control_presence'] == 'absent':
        for field in numbers:
            if field.startswith('control_') and numbers[field]['state'] == 'missing':
                numbers[field]['state'] = 'not_measured'
            elif field.startswith('control_') and numbers[field]['state'] == 'present':
                conflict(field)
    for role in ('treatment', 'control'):
        for unit in ('tags', 'fragments'):
            total, filtered = numbers[f'{role}_total_{unit}'], numbers[f'{role}_postfilter_{unit}']
            if total['state'] == filtered['state'] == 'present' and filtered['value'] > total['value']:
                conflict(f'{role}_postfilter_{unit}')


def parse_macs2_peaks_xls(content: bytes | BinaryIO | None, *, artifact: AtacArtifact,
                          callpeak: AtacCallpeakBinding) -> ParsedMacs2PeaksXls:
    return _parse_table(content, artifact, callpeak, 'xls')


def parse_macs2_narrowpeak(content: bytes | BinaryIO | None, *, artifact: AtacArtifact,
                          callpeak: AtacCallpeakBinding) -> ParsedMacs2NarrowPeak:
    return _parse_table(content, artifact, callpeak, 'narrowpeak')


def parse_macs2_summits_bed(content: bytes | BinaryIO | None, *, artifact: AtacArtifact,
                           callpeak: AtacCallpeakBinding) -> ParsedMacs2Summits:
    return _parse_table(content, artifact, callpeak, 'summits')


def parse_macs2_bdgdiff_bed(content: bytes | BinaryIO | None, *, artifact: AtacArtifact,
                           comparison: AtacComparisonBinding,
                           category: str) -> ParsedMacs2Bdgdiff:
    return _parse_table(content, artifact, comparison, 'bdgdiff', category)
