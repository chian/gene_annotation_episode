"""Saved native pairwise measurements and separate deterministic calculations.

These functions accept already supplied data. They perform no I/O, acquisition,
execution, selection or model call. Native observations remain in the sheet;
shared correspondence arithmetic is used only after exact operand validation.
"""
from __future__ import annotations

from copy import deepcopy
import re

from .blast_pairwise_grader import build_pairwise_sheet
from .blast_program_context import resolve_blast_program_context
from .blast_search import PROGRAM_UNITS
from .native_blast_contracts import finite_json_copy

_SEARCH_FIELDS = {'search_key', 'program_context', 'stage', 'iteration', 'normalized',
    'row_map', 'operand_binding', 'reporting', 'native', 'issues'}
_DESCRIPTOR_FIELDS = {'subject_ref', 'length', 'molecule', 'artifact_key', 'native_id', 'selected_interval'}


def _text(value, *, nullable=False):
    return value is None and nullable or type(value) is str and bool(value.strip()) and '\0' not in value


def _descriptor(value):
    if (type(value) is not dict or set(value) != _DESCRIPTOR_FIELDS
            or not _text(value['subject_ref'], nullable=True) or not _text(value['native_id'], nullable=True)
            or not _text(value['artifact_key']) or type(value['length']) is not int or value['length'] <= 0
            or type(value['molecule']) is not str or value['molecule'] not in {'dna', 'rna', 'protein'}):
        raise ValueError('blast_pairwise_actual_operand_descriptor_required')
    interval = value['selected_interval']
    if interval is not None and (type(interval) is not list or len(interval) != 2
            or any(type(v) is not int for v in interval)
            or not 0 <= interval[0] < interval[1] <= value['length']):
        raise ValueError('blast_pairwise_selected_interval_invalid')


def _names(values):
    # The first FASTA defline token is its actual identifier.
    names = set()
    for value in values:
        if type(value) is str and value:
            names.add(value)
            names.add(value.split()[0])
    return names


def _observed_identity(names, descriptor, axis):
    identifier = descriptor['native_id']
    if identifier is not None and names and identifier not in names:
        raise ValueError('blast_pairwise_' + axis + '_native_identity_conflict')


def _selected_intervals(search, bindings):
    """Explicit supplied selections; the host authenticates original options."""
    return {axis: deepcopy(bindings[axis]['selected_interval']) for axis in ('query', 'reference')}


def _at_pointer(value, pointer):
    try:
        for token in pointer.split('/')[1:]:
            token = token.replace('~1', '/').replace('~0', '~')
            value = value[int(token)] if type(value) is list else value[token]
        return value
    except (TypeError, ValueError, KeyError, IndexError) as error:
        raise ValueError('blast_pairwise_original_search_pointer_conflict') from error


def _validate(search, bindings):
    if type(search) is not dict or set(search) != _SEARCH_FIELDS:
        raise ValueError('blast_pairwise_search_envelope_required')
    if type(bindings) is not dict or set(bindings) != {'query', 'reference'}:
        raise ValueError('blast_pairwise_query_reference_bindings_required')
    for value in bindings.values():
        _descriptor(value)
    context = search['program_context']
    if type(context) is not dict or set(context) != {'execution_program', 'reported_program', 'scientific_mode',
            'query_kind', 'reference_kind', 'native_version', 'geometry_program'}:
        raise ValueError('blast_pairwise_program_context_required')
    if context['geometry_program'] is None:
        raise ValueError('blast_pairwise_geometry_unresolved')
    resolved = resolve_blast_program_context(**{k: v for k, v in context.items() if k != 'geometry_program'})
    if (resolved != context or context['scientific_mode'] != 'pairwise'
            or context['query_kind'] != 'sequence' or context['reference_kind'] != 'sequence'):
        raise ValueError('blast_pairwise_program_context_conflict')
    normalized = search['normalized']
    if (type(normalized) is not dict or set(normalized) != {'schema', 'mode', 'resource', 'format',
            'query', 'search', 'hits', 'native', 'issues'} or normalized.get('schema') != 'blast_normalized_result_v1'
            or normalized.get('mode') != 'pairwise' or type(normalized.get('search')) is not dict
            or normalized['search'].get('program') != context['execution_program']
            or type(normalized.get('query')) is not dict or type(normalized.get('hits')) is not list
            or type(normalized.get('native')) is not dict or normalized.get('format') not in ('json2', 'tabular')
            or normalized.get('resource') not in ('local', 'api', 'hpc')):
        raise ValueError('blast_pairwise_normalized_search_conflict')
    if len(normalized['hits']) > 1:
        raise ValueError('blast_pairwise_single_reference_required')
    key = search['search_key']
    if (type(key) is not dict or set(key) != {'artifact_key', 'member_ordinal', 'report_index', 'search_pointer'}
            or not _text(key['artifact_key']) or type(key['report_index']) is not int or key['report_index'] < 0
            or key['member_ordinal'] is not None and (type(key['member_ordinal']) is not int or key['member_ordinal'] < 0)
            or not _text(key['search_pointer']) or not key['search_pointer'].startswith('/')):
        raise ValueError('blast_pairwise_original_search_key_required')
    native = search['native']
    if (type(native) is not dict or set(native) != {'report', 'search', 'line_numbers'}
            or type(native['report']) is not dict or type(native['search']) is not dict):
        raise ValueError('blast_pairwise_original_native_objects_required')
    if native['report'].get('program') != context['reported_program']:
        raise ValueError('blast_pairwise_original_program_context_conflict')
    qunit, runit, _ = PROGRAM_UNITS[context['geometry_program']]
    for axis, unit in (('query', qunit), ('reference', runit)):
        if bindings[axis]['molecule'] not in ({'protein'} if unit == 'aa' else {'dna', 'rna'}):
            raise ValueError('blast_pairwise_' + axis + '_molecule_conflict')
    query, binding = normalized['query'], search['operand_binding']
    interval = bindings['query']['selected_interval']
    if binding is not None:
        if (type(binding) is not dict or set(binding) != {'role', 'artifact_key', 'record_ordinal',
                'native_id', 'native_title', 'subject_ref', 'molecule', 'length', 'selected_interval', 'identity'}
                or binding.get('role') != 'query'):
            raise ValueError('blast_pairwise_selected_query_binding_required')
        for field in ('artifact_key', 'subject_ref', 'native_id', 'length', 'molecule'):
            actual = binding.get(field)
            if actual is not None and actual != 'unknown' and actual != bindings['query'][field]:
                raise ValueError('blast_pairwise_query_operand_binding_conflict:' + field)
        if binding['selected_interval'] != interval:
            raise ValueError('blast_pairwise_query_selected_interval_conflict')
    observed_length = query.get('length')
    if observed_length is not None and (type(observed_length) is not int or observed_length <= 0):
        raise ValueError('blast_pairwise_query_length_conflict')
    query_names = _names([query.get('title')])
    identifier = query.get('id')
    # Generated query identifiers qualify no input by themselves. An actual
    # supplied title that happens to be Query_1 remains an exact title match.
    if type(identifier) is str and re.fullmatch(r'Query_\d+', identifier) is None:
        query_names |= _names([identifier])
    if observed_length is not None and observed_length != bindings['query']['length']:
        if (interval is None or observed_length != interval[1] - interval[0]
                or bindings['query']['native_id'] is None or bindings['query']['native_id'] not in query_names):
            raise ValueError('blast_pairwise_query_length_conflict')
    _observed_identity(query_names, bindings['query'], 'query')
    if normalized.get('format') == 'json2':
        document = normalized.get('native', {}).get('document')
        pointer = key['search_pointer']
        report_pointer = pointer.split('/results/', 1)[0]
        if (_at_pointer(document, pointer) != native['search']
                or _at_pointer(document, report_pointer) != native['report']):
            raise ValueError('blast_pairwise_original_search_pointer_conflict')
        for field, source in (('id', 'query_id'), ('title', 'query_title'), ('length', 'query_len')):
            value = native['search'].get(source)
            if (type(value) is str if field != 'length' else type(value) is int and value > 0):
                if query.get(field) != value:
                    raise ValueError('blast_pairwise_original_query_conflict:' + field)
    if type(search['row_map']) is not list or len(search['row_map']) != len(normalized['hits']):
        raise ValueError('blast_pairwise_native_row_map_required')
    if normalized['format'] == 'tabular':
        lines, rows = native['line_numbers'], native['search'].get('rows')
        if (type(lines) is not list or any(type(v) is not int or v <= 0 for v in lines)
                or sorted(set(lines)) != lines or type(rows) is not list or len(rows) != len(lines)
                or any(type(row) is not dict or row.get('line') != line for row, line in zip(rows, lines))):
            raise ValueError('blast_pairwise_original_tabular_lines_conflict')
    for hit, mapping in zip(normalized['hits'], search['row_map']):
        if (type(hit) is not dict or type(mapping) is not dict
                or set(mapping) != {'hit_index', 'description_ordinals', 'hsp_ordinals'}
                or mapping['hit_index'] != hit.get('hit_index')
                or type(mapping['hit_index']) is not int or mapping['hit_index'] < 0):
            raise ValueError('blast_pairwise_native_hit_map_conflict')
        for field, target in (('description_ordinals', 'descriptions'), ('hsp_ordinals', 'hsps')):
            ordinals = mapping[field]
            if (type(hit.get(target)) is not list or type(ordinals) is not list
                    or len(ordinals) != len(hit[target]) or any(type(x) is not int or x < 0 for x in ordinals)
                    or len(set(ordinals)) != len(ordinals) or any(type(row) is not dict for row in hit[target])):
                raise ValueError('blast_pairwise_native_row_map_conflict:' + field)
        if normalized['format'] == 'tabular' and any(i >= len(native['line_numbers']) for i in mapping['hsp_ordinals']):
            raise ValueError('blast_pairwise_original_row_map_conflict')
        if hit.get('length') is not None and hit['length'] != bindings['reference']['length']:
            raise ValueError('blast_pairwise_reference_length_conflict')
        names = _names([d.get(k) for d in hit['descriptions'] if type(d) is dict for k in ('id', 'accession', 'title')])
        _observed_identity(names, bindings['reference'], 'reference')
        if normalized.get('format') == 'json2':
            rows = native['search'].get('hits')
            if type(rows) is not list or mapping['hit_index'] >= len(rows) or type(rows[mapping['hit_index']]) is not dict:
                raise ValueError('blast_pairwise_original_hit_map_conflict')
            original = rows[mapping['hit_index']]
            if type(original.get('len')) is int and original['len'] > 0 and original['len'] != hit.get('length'):
                raise ValueError('blast_pairwise_original_reference_length_conflict')
            for source, target, ordinals in (('description', 'descriptions', mapping['description_ordinals']), ('hsps', 'hsps', mapping['hsp_ordinals'])):
                original_rows = original.get(source)
                if original_rows is None and not ordinals:
                    continue
                if type(original_rows) is not list or any(i >= len(original_rows) for i in ordinals):
                    raise ValueError('blast_pairwise_original_row_map_conflict')
                for row, ordinal in zip(hit[target], ordinals):
                    original_row = original_rows[ordinal]
                    if type(row) is not dict or type(original_row) is not dict or any(original_row.get(k) != v for k, v in row.items()):
                        raise ValueError('blast_pairwise_original_measurement_conflict')
    if type(search['issues']) is not list or type(normalized.get('issues')) is not list:
        raise ValueError('blast_pairwise_issues_array_required')
    reporting = search['reporting']
    if (type(reporting) is not dict or set(reporting) != {'native_hit_array_present', 'native_hit_count',
            'requested_hit_limit', 'requested_hsp_limit', 'native_returncode', 'producer_complete'}
            or type(reporting['native_hit_array_present']) is not bool
            or reporting['producer_complete'] is not None and type(reporting['producer_complete']) is not bool
            or reporting['native_returncode'] is not None and type(reporting['native_returncode']) is not int):
        raise ValueError('blast_pairwise_reporting_required')
    if reporting['native_hit_array_present'] != normalized['search'].get('hit_array_present'):
        raise ValueError('blast_pairwise_reporting_conflict')
    for field in ('native_hit_count', 'requested_hit_limit', 'requested_hsp_limit'):
        if reporting[field] is not None and (type(reporting[field]) is not int or reporting[field] < 0):
            raise ValueError('blast_pairwise_reporting_count_invalid')
    if reporting['native_hit_count'] != normalized['search'].get('reported_hit_count'):
        raise ValueError('blast_pairwise_reporting_conflict')
    return normalized


def populate_blast_pairwise_sheet(search, *, operand_bindings):
    search, operand_bindings = finite_json_copy(search), finite_json_copy(operand_bindings)
    _validate(search, operand_bindings)
    _selected_intervals(search, operand_bindings)
    return {'schema': 'blast_pairwise_result_sheet_v1', 'search': search, 'operand_bindings': operand_bindings}


def calculate_blast_pairwise_components(sheet):
    sheet = finite_json_copy(sheet)
    if (type(sheet) is not dict or set(sheet) != {'schema', 'search', 'operand_bindings'}
            or sheet['schema'] != 'blast_pairwise_result_sheet_v1'):
        raise ValueError('blast_pairwise_result_sheet_required')
    search, bindings = sheet['search'], sheet['operand_bindings']
    normalized = deepcopy(_validate(search, bindings))
    intervals = _selected_intervals(search, bindings)
    qunit, runit, _ = PROGRAM_UNITS[search['program_context']['geometry_program']]
    coordinate_context = {}
    for axis, unit in (('query', qunit), ('reference', runit)):
        reported = (normalized['query'].get('length') if axis == 'query'
            else normalized['hits'][0].get('length') if normalized['hits'] else None)
        coordinate_context[axis] = {'reported_length': reported, 'full_length': bindings[axis]['length'],
            'selected_interval': intervals[axis], 'coordinate_unit': unit}
    # A detached calculation input supplies the actual full coordinate bounds.
    # The original sheet/native lengths, endpoints and frames remain untouched.
    normalized['query']['length'] = bindings['query']['length']
    for hit in normalized['hits']:
        hit['length'] = bindings['reference']['length']
        for hsp in hit['hsps']:
            for axis, prefix in (('query', 'query'), ('reference', 'hit')):
                interval = intervals[axis]
                start, end = hsp.get(prefix + '_from'), hsp.get(prefix + '_to')
                if interval is not None and type(start) is int and type(end) is int:
                    if min(start, end) - 1 < interval[0] or max(start, end) > interval[1]:
                        raise ValueError('blast_pairwise_correspondence_outside_selected_interval:' + axis)
    reporting = search['reporting']
    if reporting['native_returncode'] not in (None, 0):
        normalized['issues'].append({'code': 'blast_pairwise_native_execution_failed', 'native_returncode': reporting['native_returncode']})
    if reporting['producer_complete'] is False:
        normalized['issues'].append({'code': 'blast_pairwise_producer_incomplete'})
    components = build_pairwise_sheet(normalized)
    components['calculations']['reference_paired_coverage'] = 'union_of_paired_reference_positions / actual_full_reference_length'
    components['coordinate_context'] = coordinate_context
    rows_complete = components['union']['complete_for_reported_hsps']
    if normalized.get('format') == 'json2':
        for hit, mapping in zip(normalized['hits'], search['row_map']):
            original = search['native']['search']['hits'][mapping['hit_index']].get('hsps')
            rows_complete &= type(original) is list and len(original) == len(mapping['hsp_ordinals'])
    elif normalized.get('format') == 'tabular':
        lines = search['native']['line_numbers']
        rows_complete &= type(lines) is list and len(lines) == sum(len(row['hsp_ordinals']) for row in search['row_map'])
    rows_complete &= reporting['native_returncode'] in (None, 0) and reporting['producer_complete'] is not False
    established_zero = (not normalized['hits'] and reporting['native_hit_array_present']
        and reporting['native_hit_count'] == 0 and reporting['native_returncode'] == 0
        and reporting['producer_complete'] is True and not search['issues'])
    selected_coverage = {}
    for axis in ('query', 'reference'):
        interval = intervals[axis] or [0, bindings[axis]['length']]
        denominator = interval[1] - interval[0]
        # Geometry has already been checked against these explicit intervals.
        # Existing unions merge overlaps, including alternative HSP mappings.
        numerator = components['union']['counts']['paired_' + axis + '_positions'] if rows_complete else 0 if established_zero else None
        selected_coverage[axis] = {'numerator': numerator, 'denominator': denominator,
            'value': numerator / denominator if numerator is not None else None, 'unit': 'fraction'}
    components['selected_operand_coverage'] = selected_coverage
    return {'schema': 'blast_pairwise_result_components_v1', 'components': components}
