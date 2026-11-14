"""Closed saved values for Mauve backbone coordinates and column sidecars.

Full component validators verify numerical producer relationships. Separate
component structure validators inspect saved types, states and associations,
without rederiving quantities. Neither authenticates external byte custody.
Backbone model-derived regions and BBCols internal column axes remain distinct.
"""
from __future__ import annotations

from copy import deepcopy
from functools import wraps
import re

from .bvbrc_alignment_values import (document_id, validate_native_number,
    validate_numeric_cell, requirement, diagnostic)
from .phylogeny_calculation_contracts import evidence, location
from .xmfa_format_contracts import _artifact
from .xmfa_calculation_contracts import (union_intervals, interval_length,
    multiplicity_bases, complement_intervals)

BACKBONE_DIALECT = 'libmems_signed_coordinate_pairs_v1'
BBCOLS_DIALECT = 'libmems_interval_columns_members_v1'
SIDECAR_NAMESPACE = 'mauve_sidecar_member_0based'
COMPLETENESS = ('complete', 'partial', 'unknown')
MEMBER_STATES = ('present', 'absent_zero', 'missing', 'incompatible')
ASSOCIATION_STATES = ('bound', 'missing', 'unverified', 'conflicting')
PARSER_CODES = frozenset('bytes_required artifact_invalid encoding_unsupported dialect_unsupported '
    'digest_mismatch encoding_invalid empty_input format_unrecognized version_unsupported '
    'header_missing header_malformed metadata_duplicate metadata_conflict count_invalid '
    'count_conflict member_invalid member_duplicate interval_ordinal_invalid '
    'interval_ordinal_duplicate segment_header_malformed missing_sequence_row extra_sequence_row '
    'width_conflict sequence_symbol_invalid coordinate_invalid zero_member_has_residues '
    'header_member_conflict row_incomplete unparsed_line'.split())
CALCULATION_CODES = PARSER_CODES | frozenset('selection_invalid selection_document_conflict '
    'selection_member_unknown selection_record_unknown selection_column_outside_record '
    'selection_population_incomplete pair_not_coobserved source_symbols_missing '
    'source_denominator_missing zero_denominator overlapping_placement bbcols_block_unbound '
    'bbcols_column_outside_block'.split())
ASSOCIATION_CODES = frozenset('argument_invalid original_task_invalid application_mismatch '
    'genome_input_missing genome_occurrence_conflict duplicate_genome_occurrence recipe_conflict '
    'explicit_zero_not_forwarded source_option_unsupported invocation_missing invocation_conflict '
    'metadata_type_unsupported metadata_record_unverified metadata_task_conflict content_missing '
    'content_digest_conflict staged_file_missing staged_file_run_unverified native_path_missing '
    'native_path_conflict source_records_partial source_sequence_mismatch source_span_outside_input '
    'genome_census_unknown contig_identity_missing contig_identity_conflict feature_map_missing '
    'feature_map_conflict artifact_task_conflict artifact_version_unverified artifact_role_conflict '
    'artifact_format_conflict primary_output_missing duplicate_representation member_join_missing '
    'member_join_conflict interval_join_missing interval_join_conflict native_execution_unverified'.split())
ALLOWED_CODES = ({'mauve_backbone_' + s for s in CALCULATION_CODES}
    | {'mauve_bbcols_' + s for s in CALCULATION_CODES}
    | {'bvbrc_genome_alignment_' + s for s in ASSOCIATION_CODES})


class _Check:
    def __init__(self, family, code='selection_invalid'):
        self.prefix, self.code = 'mauve_' + family + '_', code

    def ok(self, condition, code=None):
        if not condition:
            raise ValueError(self.prefix + (code or self.code))

    def shape(self, value, keys):
        self.ok(type(value) is dict and set(value) == set(keys))

    def array(self, value):
        self.ok(type(value) is list)

    def text(self, value, *, empty=False, nullable=False):
        self.ok(nullable and value is None or type(value) is str and (empty or bool(value)))

    def integer(self, value, *, minimum=0, nullable=False):
        self.ok(nullable and value is None or type(value) is int and value >= minimum)

    def strings(self, value):
        self.array(value)
        for item in value:
            self.text(item)
        self.ok(len(value) == len(set(value)))

    def indices(self, value):
        self.array(value)
        for item in value:
            self.integer(item)
        self.ok(len(value) == len(set(value)))

    def interval(self, value, *, nullable=False, nonempty=False):
        if nullable and value is None:
            return
        self.array(value); self.ok(len(value) == 2)
        for item in value:
            self.integer(item)
        self.ok(value[0] < value[1] if nonempty else value[0] <= value[1])

    def member(self, value):
        self.shape(value, ('namespace', 'index'))
        self.ok(value['namespace'] == SIDECAR_NAMESPACE)
        self.integer(value['index'])
        return value['index']

    def members(self, value):
        self.array(value)
        indices = [self.member(item) for item in value]
        self.ok(len(indices) == len(set(indices)))
        return indices

    def evidence(self, value):
        try:
            evidence(value)
        except (ValueError, TypeError) as error:
            raise ValueError(self.prefix + self.code) from error

    def native(self, value, *, nullable=False):
        if nullable and value is None:
            return
        try:
            validate_native_number(value)
        except (ValueError, TypeError) as error:
            raise ValueError(self.prefix + self.code) from error


def _guard(family, code):
    """Malformed caller structures always produce the documented ValueError."""
    def decorate(function):
        @wraps(function)
        def checked(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except (KeyError, IndexError, TypeError, AttributeError, OverflowError) as error:
                raise ValueError('mauve_' + family + '_' + code) from error
            except ValueError as error:
                if str(error).startswith('mauve_' + family + '_'):
                    raise
                raise ValueError('mauve_' + family + '_' + code) from error
        return checked
    return decorate


def _available(number, minimum=None):
    return (number is not None and number['state'] == 'available'
            and type(number['value']) is int
            and (minimum is None or number['value'] >= minimum))


def _pair_geometry(left, right):
    """Signed 1-based closed endpoints; this is format validation, not scoring."""
    if left is None or right is None:
        return 'missing', None, None
    if not _available(left) or not _available(right):
        return 'incompatible', None, None
    a, b = left['value'], right['value']
    if a == b == 0:
        return 'absent_zero', None, None
    if a == 0 or b == 0 or (a > 0) != (b > 0) or abs(a) > abs(b):
        return 'incompatible', None, None
    return 'present', '+' if a > 0 else '-', [abs(a) - 1, abs(b)]


def _header_layout(columns):
    """Group explicit header labels; a duplicated endpoint never wins by order.

    The layout includes unidentified columns separately, retaining their tokens
    without assigning an arbitrary biological member.
    """
    groups, order = {}, []
    for col in columns:
        token = col['member_index_token']
        key = ('member', token['value']) if _available(token, 0) else ('unknown', col['column_index'])
        if key not in groups:
            groups[key] = {'member': key[1] if key[0] == 'member' else None,
                           'left': [], 'right': [], 'unrecognized': []}
            order.append(key)
        groups[key][col['endpoint']].append(col['column_index'])
    return [groups[key] for key in order]


def _source(c, loc, document):
    try:
        location(loc)
    except (ValueError, TypeError) as error:
        raise ValueError(c.prefix + 'header_malformed') from error
    c.ok(loc['artifact'] == document['artifact'], 'artifact_invalid')
    c.ok(loc['xml_path'] is None and all(type(loc[k]) is int for k in (
        'byte_start_0based', 'byte_end_0based_exclusive', 'line_start_1based',
        'line_end_1based_inclusive')))


def _atomic(c, raw, loc, document):
    c.text(raw, empty=True); c.ok('\n' not in raw and '\r' not in raw)
    _source(c, loc, document)
    try:
        size = len(raw.encode(document['encoding']))
    except UnicodeError as error:
        raise ValueError(c.prefix + 'encoding_invalid') from error
    c.ok(loc['byte_end_0based_exclusive'] - loc['byte_start_0based'] == size
         and loc['line_start_1based'] == loc['line_end_1based_inclusive'])


def _within(c, inner, outer):
    for a, b in (('byte_start_0based', 'byte_end_0based_exclusive'),
                 ('line_start_1based', 'line_end_1based_inclusive')):
        c.ok(outer[a] <= inner[a] <= inner[b] <= outer[b])


def _raw(c, value, document):
    c.shape(value, ('raw_line', 'source_location'))
    _atomic(c, value['raw_line'], value['source_location'], document)


def _native_source(c, number, document, parent, *, nullable=False):
    c.native(number, nullable=nullable)
    if number is not None:
        _atomic(c, number['raw_token'], number['source_location'], document)
        _within(c, number['source_location'], parent)
        if number['state'] == 'available':
            c.ok(type(number['value']) is int and re.fullmatch(r'[+-]?[0-9]+', number['raw_token']) is not None)


def _token_in_line(c, number, raw, loc, document):
    if number is None:
        return
    start = number['source_location']['byte_start_0based'] - loc['byte_start_0based']
    end = number['source_location']['byte_end_0based_exclusive'] - loc['byte_start_0based']
    c.ok(raw.encode(document['encoding'])[start:end] == number['raw_token'].encode(document['encoding']))


def _line_tokens(raw, loc, encoding):
    """Inspect stored token/byte correspondence without interpreting numbers."""
    result = []
    for match in re.finditer(r'\S+', raw):
        source = deepcopy(loc)
        source['byte_start_0based'] += len(raw[:match.start()].encode(encoding))
        source['byte_end_0based_exclusive'] = loc['byte_start_0based'] + len(raw[:match.end()].encode(encoding))
        result.append({'raw_line': match[0], 'source_location': source})
    return result


def _document_base(value, family, dialect, extra):
    c = _Check(family, 'header_malformed')
    c.shape(value, ('schema_version', 'document_id', 'artifact', 'dialect', 'encoding',
                    'rows', 'unparsed', 'completeness', *extra))
    c.ok(value['schema_version'] == 'mauve_' + family + '_document_v1')
    try:
        _artifact(value['artifact'])
    except (ValueError, TypeError) as error:
        raise ValueError(c.prefix + 'artifact_invalid') from error
    c.ok(value['encoding'] in ('ascii', 'utf-8'), 'encoding_unsupported')
    c.ok(value['dialect'] == dialect, 'dialect_unsupported')
    c.ok(value['document_id'] == document_id('mauve_' + family,
        artifact=value['artifact'], parameters={'dialect': dialect, 'encoding': value['encoding']}))
    c.ok(value['completeness'] in COMPLETENESS)
    c.array(value['rows']); c.array(value['unparsed'])
    for raw in value['unparsed']:
        _raw(c, raw, value)
    return c


@_guard('backbone', 'header_malformed')
def validate_mauve_backbone_document(document: dict) -> dict:
    c = _document_base(document, 'backbone', BACKBONE_DIALECT, ('header', 'columns'))
    c.array(document['columns'])
    if document['header'] is not None:
        _raw(c, document['header'], document)
        header_tokens = _line_tokens(document['header']['raw_line'], document['header']['source_location'], document['encoding'])
        c.ok(len(header_tokens) == len(document['columns']))
    else:
        c.ok(not document['columns'] and not document['rows'])
    for index, col in enumerate(document['columns']):
        c.shape(col, ('column_index', 'raw_token', 'member_index_token', 'endpoint', 'source_location'))
        c.ok(col['column_index'] == index and type(col['column_index']) is int)
        _atomic(c, col['raw_token'], col['source_location'], document)
        c.ok({'raw_line': col['raw_token'], 'source_location': col['source_location']} == header_tokens[index])
        _within(c, col['source_location'], document['header']['source_location'])
        c.ok(col['endpoint'] in ('left', 'right', 'unrecognized'))
        _native_source(c, col['member_index_token'], document, col['source_location'], nullable=True)
        match = re.fullmatch(r'seq_?(.*?)_(leftend|rightend)', col['raw_token'])
        if match:
            c.ok(col['member_index_token'] is not None
                 and col['member_index_token']['raw_token'] == match[1]
                 and col['endpoint'] == ('left' if match[2] == 'leftend' else 'right'))
        else:
            c.ok(col['member_index_token'] is None and col['endpoint'] == 'unrecognized')
    layout = _header_layout(document['columns'])
    header_good = bool(layout) and all(g['member'] is not None and len(g['left']) == len(g['right']) == 1
        and not g['unrecognized'] for g in layout)
    previous = document['header']['source_location']['byte_end_0based_exclusive'] if document['header'] else 0
    for index, row in enumerate(document['rows']):
        c.shape(row, ('row_index', 'raw_line', 'pairs', 'extra_tokens', 'source_location', 'completeness'))
        c.ok(type(row['row_index']) is int and row['row_index'] == index)
        _atomic(c, row['raw_line'], row['source_location'], document)
        c.ok(row['source_location']['byte_start_0based'] >= previous)
        previous = row['source_location']['byte_end_0based_exclusive']
        c.array(row['pairs']); c.array(row['extra_tokens'])
        c.ok(len(row['pairs']) == len(layout))
        tokens = _line_tokens(row['raw_line'], row['source_location'], document['encoding'])
        consumed = set()
        for pindex, (pair, group) in enumerate(zip(row['pairs'], layout)):
            c.shape(pair, ('pair_index', 'member_index_0based', 'native_left', 'native_right',
                'state', 'strand', 'interval_0based_half_open', 'source_location'))
            c.ok(type(pair['pair_index']) is int and pair['pair_index'] == pindex)
            c.integer(pair['member_index_0based'], nullable=True)
            c.ok(pair['member_index_0based'] == group['member'])
            _source(c, pair['source_location'], document)
            _within(c, pair['source_location'], row['source_location'])
            for field in ('native_left', 'native_right'):
                _native_source(c, pair[field], document, pair['source_location'], nullable=True)
                _token_in_line(c, pair[field], row['raw_line'], row['source_location'], document)
                indices = group['left' if field == 'native_left' else 'right']
                column = indices[0] if len(indices) == 1 else None
                expected_token = tokens[column] if column is not None and column < len(tokens) else None
                if expected_token is None:
                    c.ok(pair[field] is None)
                else:
                    consumed.add(column)
                    c.ok(pair[field] is not None and pair[field]['raw_token'] == expected_token['raw_line']
                        and pair[field]['source_location'] == expected_token['source_location'])
            state, strand, interval = _pair_geometry(pair['native_left'], pair['native_right'])
            if group['member'] is None or len(group['left']) != 1 or len(group['right']) != 1 or group['unrecognized']:
                state, strand, interval = 'incompatible', None, None
            c.ok((pair['state'], pair['strand'], pair['interval_0based_half_open']) == (state, strand, interval))
        for token in row['extra_tokens']:
            _raw(c, token, document); _within(c, token['source_location'], row['source_location'])
        c.ok(row['extra_tokens'] == [t for i, t in enumerate(tokens) if i not in consumed])
        good = header_good and not row['extra_tokens'] and all(p['state'] in ('present', 'absent_zero') for p in row['pairs'])
        c.ok(row['completeness'] == ('complete' if good else 'partial'))
    bad = not header_good or any(r['completeness'] != 'complete' for r in document['rows']) or any(
        u['raw_line'].strip() for u in document['unparsed'])
    expected = 'partial' if bad else 'complete' if document['rows'] else 'unknown'
    c.ok(document['completeness'] == expected)
    return deepcopy(document)


@_guard('bbcols', 'header_malformed')
def validate_mauve_bbcols_document(document: dict) -> dict:
    c = _document_base(document, 'bbcols', BBCOLS_DIALECT, ())
    previous = 0
    for index, row in enumerate(document['rows']):
        c.shape(row, ('row_index', 'raw_line', 'native_interval_index_0based',
            'native_left_column_1based', 'native_column_count', 'native_member_indices_0based',
            'columns_0based_half_open', 'state', 'source_location'))
        c.ok(type(row['row_index']) is int and row['row_index'] == index)
        _atomic(c, row['raw_line'], row['source_location'], document)
        c.ok(row['source_location']['byte_start_0based'] >= previous)
        previous = row['source_location']['byte_end_0based_exclusive']
        numbers = [row[k] for k in ('native_interval_index_0based', 'native_left_column_1based', 'native_column_count')]
        c.array(row['native_member_indices_0based'])
        numbers += row['native_member_indices_0based']
        for number in numbers:
            _native_source(c, number, document, row['source_location'], nullable=True)
            _token_in_line(c, number, row['raw_line'], row['source_location'], document)
        tokens = _line_tokens(row['raw_line'], row['source_location'], document['encoding'])
        c.ok([{'raw_line': n['raw_token'], 'source_location': n['source_location']} for n in numbers if n is not None] == tokens)
        c.ok(all(numbers[i] is None for i in range(min(len(tokens), 3), 3)))
        members = row['native_member_indices_0based']
        valid = (all(_available(n, m) for n, m in zip(numbers[:3], (0, 1, 1)))
            and all(_available(n, 0) for n in members)
            and len({n['value'] for n in members}) == len(members))
        incomplete = any(n is None for n in numbers[:3]) or not members
        c.ok(row['state'] == ('incomplete' if incomplete else 'parsed' if valid else 'incompatible'))
        left, width = numbers[1:3]
        expected = [left['value'] - 1, left['value'] - 1 + width['value']] if _available(left, 1) and _available(width, 1) else None
        c.ok(row['columns_0based_half_open'] == expected)
    bad = any(r['state'] != 'parsed' for r in document['rows']) or any(u['raw_line'].strip() for u in document['unparsed'])
    c.ok(document['completeness'] == ('partial' if bad else 'complete' if document['rows'] else 'unknown'))
    return deepcopy(document)


def _selection(selection, family):
    c = _Check(family)
    option = 'denominator' if family == 'backbone' else 'calculate_bound_block_fraction'
    c.shape(selection, ('schema_version', 'document_id', 'population_id', 'members', 'row_indices',
                       'minimum_selected_multiplicity', option, 'population_scope', 'evidence'))
    c.ok(selection['schema_version'] == 'mauve_' + family + '_selection_v1')
    c.text(selection['document_id']); c.text(selection['population_id'])
    members = c.members(selection['members']); c.indices(selection['row_indices'])
    c.integer(selection['minimum_selected_multiplicity'], minimum=1)
    c.ok(selection['minimum_selected_multiplicity'] <= len(members))
    c.ok(selection['population_scope'] in ('selected_rows', 'all_observed_document_rows'))
    c.evidence(selection['evidence'])
    if family == 'backbone':
        c.ok(selection[option] in ('none', 'validated_staged_length'))
    else:
        c.ok(type(selection[option]) is bool)
    return deepcopy(selection)


@_guard('backbone', 'selection_invalid')
def validate_mauve_backbone_selection(selection: dict) -> dict:
    return _selection(selection, 'backbone')


@_guard('bbcols', 'selection_invalid')
def validate_mauve_bbcols_selection(selection: dict) -> dict:
    return _selection(selection, 'bbcols')


def _reports(c, result):
    c.array(result['requirements']); c.array(result['diagnostics'])
    ids = []
    for row in result['requirements']:
        c.shape(row, ('requirement_id', 'kind', 'role', 'source_refs', 'reason_code'))
        c.ok(row['reason_code'] in ALLOWED_CODES)
        c.ok(requirement(**row) == row)
        ids.append(row['requirement_id'])
    c.ok(len(ids) == len(set(ids)))
    for row in result['diagnostics']:
        c.shape(row, ('code', 'phase', 'path', 'severity', 'evidence_refs'))
        c.ok(row['code'] in ALLOWED_CODES)
        c.ok(diagnostic(**row) == row)
    return set(ids)


def _cell(c, cell, selection, field, unit, *, expected=None, check_value=False,
          origin='calculated', fraction=False):
    try:
        validate_numeric_cell(cell)
    except (ValueError, TypeError) as error:
        raise ValueError(c.prefix + c.code) from error
    c.ok(cell['unit'] == unit and cell['origin'] == origin
        and cell['population_id'] == selection['population_id']
        and cell['method_id'] == c.prefix + field + '_v1'
        and cell['uncertainty'] is None)
    c.ok(all(e in cell['evidence'] for e in selection['evidence']))
    if fraction:
        for key in ('numerator', 'denominator'):
            c.integer(cell[key], nullable=True)
        if cell['state'] == 'available':
            c.ok(cell['denominator'] is not None and cell['denominator'] > 0
                and cell['numerator'] is not None and 0 <= cell['numerator'] <= cell['denominator']
                and cell['value'] == cell['numerator'] / cell['denominator'])
    else:
        c.ok(cell['numerator'] is None and cell['denominator'] is None)
        if cell['state'] == 'available':
            c.integer(cell['value'])
    if check_value and cell['state'] == 'available':
        c.ok(cell['value'] == expected)


def _requirement_links(c, value, ids):
    """Every nested requirement reference resolves within this saved result."""
    if type(value) is dict:
        if 'requirement_ids' in value:
            c.strings(value['requirement_ids']); c.ok(set(value['requirement_ids']) <= ids)
        for item in value.values():
            _requirement_links(c, item, ids)
    elif type(value) is list:
        for item in value:
            _requirement_links(c, item, ids)


def _component_base(value, family, fields):
    c = _Check(family)
    c.shape(value, ('schema_version', 'document_id', 'status', 'selection', 'rows',
                    'requirements', 'diagnostics', *fields))
    c.ok(value['schema_version'] == 'mauve_' + family + '_components_v1')
    selection = _selection(value['selection'], family)
    c.ok(value['document_id'] == selection['document_id'], 'selection_document_conflict')
    c.ok(value['status'] in ('ok', 'partial', 'invalid'))
    c.array(value['rows'])
    c.ok([r.get('row_index') if type(r) is dict else None for r in value['rows']] == selection['row_indices'])
    ids = _reports(c, value); _requirement_links(c, value, ids)
    if value['requirements'] or value['diagnostics']:
        c.ok(value['status'] != 'ok')
    return c, selection


def _coverage_counts(c, row, selection, *, intervals, known_field, placement_field, multiple_field, excess_field, unit, placement_unit):
    c.array(row['known_union_intervals'])
    for item in row['known_union_intervals']:
        c.interval(item, nonempty=True)
    union = union_intervals(intervals)
    c.ok(row['known_union_intervals'] == union)
    unique, total, multiple = interval_length(union), interval_length(intervals), multiplicity_bases(intervals)
    for key, value, units in ((known_field, unique, unit), (placement_field, total, placement_unit),
            (multiple_field, multiple, unit), (excess_field, total - unique, placement_unit)):
        _cell(c, row[key], selection, key, units, expected=value, check_value=True)
    c.ok(row['population_state'] in ('complete_selected', 'partial_selected', 'unknown'))
    if row['population_state'] == 'complete_selected' or intervals:
        c.ok(all(row[k]['state'] == 'available' for k in (known_field, placement_field, multiple_field, excess_field)))
    c.evidence(row['evidence'])
    return unique


@_guard('backbone', 'selection_invalid')
def validate_mauve_backbone_components(value: dict) -> dict:
    c, selection = _component_base(value, 'backbone', ('coverage',))
    members = selection['members']
    by_row = {}
    for row in value['rows']:
        c.shape(row, ('row_index', 'selected_present_members', 'selected_absent_members', 'unresolved_members',
            'selected_member_count', 'selected_by_multiplicity', 'member_spans'))
        c.integer(row['row_index'])
        lists = [row[k] for k in ('selected_present_members', 'selected_absent_members', 'unresolved_members')]
        for items in lists:
            c.members(items)
            c.ok(items == [m for m in members if m in items])
        c.ok(sorted(m['index'] for items in lists for m in items) == sorted(m['index'] for m in members))
        _cell(c, row['selected_member_count'], selection, 'selected_member_count', 'members', expected=len(lists[0]), check_value=True)
        c.ok(row['selected_member_count']['state'] == 'available')
        expected = None if lists[2] else len(lists[0]) >= selection['minimum_selected_multiplicity']
        c.ok(row['selected_by_multiplicity'] is expected)
        c.array(row['member_spans']); c.ok([s.get('member') for s in row['member_spans']] == members)
        for span in row['member_spans']:
            c.shape(span, ('member', 'state', 'interval_0based_half_open', 'strand', 'span_bases', 'evidence', 'requirement_ids'))
            c.member(span['member']); c.ok(span['state'] in MEMBER_STATES)
            category = 0 if span['state'] == 'present' else 1 if span['state'] == 'absent_zero' else 2
            c.ok(span['member'] in lists[category]); c.evidence(span['evidence'])
            if span['state'] == 'present':
                c.interval(span['interval_0based_half_open'], nonempty=True); c.ok(span['strand'] in ('+', '-'))
                count = span['interval_0based_half_open'][1] - span['interval_0based_half_open'][0]
                c.ok(span['span_bases']['state'] == 'available')
            else:
                c.ok(span['interval_0based_half_open'] is None and span['strand'] is None)
                count = 0 if span['state'] == 'absent_zero' else None
                c.ok(span['span_bases']['state'] == ('available' if count == 0 else 'incompatible' if span['state'] == 'incompatible' else 'missing'))
            _cell(c, span['span_bases'], selection, 'span_bases', 'nucleotides', expected=count, check_value=True)
        by_row[row['row_index']] = row
    c.array(value['coverage']); c.ok([r.get('member') for r in value['coverage']] == members)
    for row in value['coverage']:
        c.shape(row, ('member', 'placements', 'known_union_intervals', 'known_union_bases', 'placement_bases',
            'multiply_represented_bases', 'excess_placement_bases', 'denominator_kind', 'denominator_bases',
            'coverage_fraction', 'complement_intervals', 'complement_bases', 'population_state', 'evidence', 'requirement_ids'))
        c.member(row['member']); c.array(row['placements'])
        expected = [(r['row_index'], s) for r in value['rows'] if r['selected_by_multiplicity'] is True
            for s in r['member_spans'] if s['member'] == row['member'] and s['state'] == 'present']
        c.ok(len(row['placements']) == len(expected))
        for p, (index, span) in zip(row['placements'], expected):
            c.shape(p, ('document_id', 'row_index', 'member', 'interval_0based_half_open', 'strand', 'evidence'))
            c.ok(p['document_id'] == value['document_id'] and p['row_index'] == index and p['member'] == row['member']
                and p['interval_0based_half_open'] == span['interval_0based_half_open'] and p['strand'] == span['strand'])
            c.evidence(p['evidence'])
        count = _coverage_counts(c, row, selection, intervals=[p['interval_0based_half_open'] for p in row['placements']],
            known_field='known_union_bases', placement_field='placement_bases', multiple_field='multiply_represented_bases',
            excess_field='excess_placement_bases', unit='nucleotides', placement_unit='nucleotide_placements')
        c.ok(row['denominator_kind'] == selection['denominator'])
        _cell(c, row['denominator_bases'], selection, 'denominator_bases', 'nucleotides')
        _cell(c, row['coverage_fraction'], selection, 'coverage_fraction', 'fraction', fraction=True)
        _cell(c, row['complement_bases'], selection, 'complement_bases', 'nucleotides')
        length = row['denominator_bases']['value'] if row['denominator_bases']['state'] == 'available' else None
        frac = row['coverage_fraction']
        c.ok(frac['denominator'] == length)
        c.ok(frac['numerator'] == (count if row['known_union_bases']['state'] == 'available' else None))
        if row['denominator_kind'] == 'none':
            c.ok(all(row[k]['state'] == 'not_measured' for k in ('denominator_bases', 'coverage_fraction', 'complement_bases')))
        if frac['state'] == 'available':
            c.ok(row['population_state'] == 'complete_selected' and all(end <= length for start, end in row['known_union_intervals']))
        if row['complement_intervals'] is not None:
            c.ok(length is not None and row['population_state'] == 'complete_selected'
                and row['complement_intervals'] == complement_intervals(row['known_union_intervals'], length)
                and row['complement_bases']['state'] == 'available'
                and row['complement_bases']['value'] == length - count)
        else:
            c.ok(row['complement_bases']['state'] != 'available')
    return deepcopy(value)


@_guard('bbcols', 'selection_invalid')
def validate_mauve_bbcols_components(value: dict) -> dict:
    c, selection = _component_base(value, 'bbcols', ('intervals',))
    selected = selection['members']; by_interval = {}
    for row in value['rows']:
        c.shape(row, ('row_index', 'native_interval_index_0based', 'selected_present_members', 'unresolved_member_tokens',
            'selected_member_count', 'selected_by_multiplicity', 'column_count', 'xmfa_document_id', 'xmfa_block_index',
            'join_state', 'evidence', 'requirement_ids'))
        c.integer(row['row_index']); c.integer(row['native_interval_index_0based'], nullable=True)
        c.members(row['selected_present_members']); c.ok(all(m in selected for m in row['selected_present_members']))
        c.ok(row['selected_present_members'] == [m for m in selected if m in row['selected_present_members']])
        c.array(row['unresolved_member_tokens'])
        for n in row['unresolved_member_tokens']:
            c.native(n)
        _cell(c, row['selected_member_count'], selection, 'selected_member_count', 'members',
            expected=len(row['selected_present_members']), check_value=True)
        c.ok(row['selected_member_count']['state'] == 'available')
        c.ok(row['selected_by_multiplicity'] is None or type(row['selected_by_multiplicity']) is bool)
        if row['unresolved_member_tokens']:
            c.ok(row['selected_by_multiplicity'] is None)
        if row['selected_by_multiplicity'] is not None:
            c.ok(row['selected_by_multiplicity'] == (len(row['selected_present_members']) >= selection['minimum_selected_multiplicity']))
        _cell(c, row['column_count'], selection, 'column_count', 'columns', origin='native_observation')
        if row['column_count']['state'] == 'available':
            c.ok(row['column_count']['value'] >= 1)
        c.ok(row['join_state'] in ASSOCIATION_STATES)
        c.text(row['xmfa_document_id'], nullable=True); c.integer(row['xmfa_block_index'], nullable=True)
        if row['join_state'] == 'bound':
            c.ok(row['xmfa_document_id'] is not None and row['xmfa_block_index'] is not None)
        c.evidence(row['evidence'])
        if row['native_interval_index_0based'] is not None:
            by_interval.setdefault(row['native_interval_index_0based'], []).append(row)
    c.array(value['intervals']); seen = []
    for row in value['intervals']:
        c.shape(row, ('native_interval_index_0based', 'contributing_row_indices', 'known_union_intervals', 'union_columns',
            'column_placements', 'multiply_represented_columns', 'excess_column_placements', 'xmfa_document_id',
            'xmfa_block_index', 'bound_block_width', 'selected_block_fraction', 'population_state', 'evidence', 'requirement_ids'))
        index = row['native_interval_index_0based']; c.integer(index); seen.append(index)
        c.ok(index in by_interval); c.indices(row['contributing_row_indices'])
        candidates = by_interval[index]
        expected = [r for r in candidates if r['selected_by_multiplicity'] is True and r['column_count']['state'] == 'available']
        c.ok(all(i in [r['row_index'] for r in expected] for i in row['contributing_row_indices']))
        # Saved BBCols components preserve widths and the union, but not every
        # individual range. Validate the inspectable sum and bounds here; the
        # provider additionally binds each component to its saved document.
        c.array(row['known_union_intervals'])
        for interval in row['known_union_intervals']:
            c.interval(interval, nonempty=True)
        c.ok(union_intervals(row['known_union_intervals']) == row['known_union_intervals'])
        total = sum(r['column_count']['value'] for r in expected if r['row_index'] in row['contributing_row_indices'])
        unique = interval_length(row['known_union_intervals'])
        c.ok(unique <= total)
        for key, unit, number in (('union_columns', 'columns', unique), ('column_placements', 'column_placements', total),
                ('excess_column_placements', 'column_placements', total - unique)):
            _cell(c, row[key], selection, key, unit, expected=number, check_value=True)
        _cell(c, row['multiply_represented_columns'], selection, 'multiply_represented_columns', 'columns')
        if row['multiply_represented_columns']['state'] == 'available':
            c.ok(0 <= row['multiply_represented_columns']['value'] <= min(unique, total - unique))
        c.ok(row['population_state'] in ('complete_selected', 'partial_selected', 'unknown'))
        if row['population_state'] == 'complete_selected' or row['contributing_row_indices']:
            c.ok(all(row[k]['state'] == 'available' for k in ('union_columns', 'column_placements',
                'multiply_represented_columns', 'excess_column_placements')))
        c.text(row['xmfa_document_id'], nullable=True); c.integer(row['xmfa_block_index'], nullable=True)
        _cell(c, row['bound_block_width'], selection, 'bound_block_width', 'columns')
        _cell(c, row['selected_block_fraction'], selection, 'selected_block_fraction', 'fraction', fraction=True)
        width = row['bound_block_width']['value'] if row['bound_block_width']['state'] == 'available' else None
        frac = row['selected_block_fraction']
        c.ok(frac['denominator'] == width and frac['numerator'] == (unique if row['union_columns']['state'] == 'available' else None))
        if frac['state'] == 'available':
            c.ok(row['population_state'] == 'complete_selected' and row['xmfa_document_id'] is not None
                and row['xmfa_block_index'] is not None and all(end <= width for start, end in row['known_union_intervals'])
                and all(r['join_state'] == 'bound' and r['xmfa_document_id'] == row['xmfa_document_id']
                    and r['xmfa_block_index'] == row['xmfa_block_index'] for r in candidates))
        if not selection['calculate_bound_block_fraction']:
            c.ok(row['bound_block_width']['state'] == row['selected_block_fraction']['state'] == 'not_measured')
        c.evidence(row['evidence'])
    c.ok(seen == list(by_interval))
    return deepcopy(value)


def _cell_structure(c, cell, selection, field, unit, *, origin='calculated', fraction=False):
    """Validate meaning, state and bounds without evaluating a scientific formula."""
    try:
        validate_numeric_cell(cell)
    except (ValueError, TypeError) as error:
        raise ValueError(c.prefix + c.code) from error
    c.ok(cell['unit'] == unit and cell['origin'] == origin
        and cell['population_id'] == selection['population_id']
        and cell['method_id'] == c.prefix + field + '_v1'
        and cell['uncertainty'] is None)
    c.ok(all(e in cell['evidence'] for e in selection['evidence']))
    if fraction:
        for key in ('numerator', 'denominator'):
            c.integer(cell[key], nullable=True)
        if cell['state'] == 'available':
            c.ok(cell['denominator'] is not None and cell['denominator'] > 0
                and cell['numerator'] is not None and cell['numerator'] <= cell['denominator']
                and 0 <= cell['value'] <= 1)
    else:
        c.ok(cell['numerator'] is None and cell['denominator'] is None)
        if cell['value'] is not None:
            c.integer(cell['value'])


def _intervals_structure(c, value):
    """Check sorted, disjoint, nonadjacent saved intervals without constructing them."""
    c.array(value)
    for item in value:
        c.interval(item, nonempty=True)
    c.ok(all(a[1] < b[0] for a, b in zip(value, value[1:])))


def _coverage_structure(c, row, selection, *, has_placements, known_field, placement_field,
                        multiple_field, excess_field, unit, placement_unit):
    _intervals_structure(c, row['known_union_intervals'])
    for key, units in ((known_field, unit), (placement_field, placement_unit),
                       (multiple_field, unit), (excess_field, placement_unit)):
        _cell_structure(c, row[key], selection, key, units)
    c.ok(row['population_state'] in ('complete_selected', 'partial_selected', 'unknown'))
    fields = (known_field, placement_field, multiple_field, excess_field)
    expected_state = ('available' if row['population_state'] == 'complete_selected' or has_placements
                      else 'missing' if row['population_state'] == 'unknown' else 'truncated')
    c.ok(all(row[k]['state'] == expected_state for k in fields))
    if expected_state == 'available':
        c.ok(row[known_field]['value'] <= row[placement_field]['value']
            and row[multiple_field]['value'] <= row[known_field]['value']
            and row[multiple_field]['value'] <= row[excess_field]['value']
            and row[excess_field]['value'] <= row[placement_field]['value'])
    c.evidence(row['evidence'])


@_guard('backbone', 'selection_invalid')
def validate_mauve_backbone_component_structure(value: dict) -> dict:
    """Validate saved structure; full numerical verification remains a producer task."""
    c, selection = _component_base(value, 'backbone', ('coverage',))
    members = selection['members']
    by_row = {}
    for row in value['rows']:
        c.shape(row, ('row_index', 'selected_present_members', 'selected_absent_members', 'unresolved_members',
            'selected_member_count', 'selected_by_multiplicity', 'member_spans'))
        c.integer(row['row_index'])
        lists = [row[k] for k in ('selected_present_members', 'selected_absent_members', 'unresolved_members')]
        for items in lists:
            c.members(items)
            c.ok(items == [m for m in members if m in items])
        c.ok(sorted(m['index'] for items in lists for m in items) == sorted(m['index'] for m in members))
        _cell_structure(c, row['selected_member_count'], selection, 'selected_member_count', 'members')
        c.ok(row['selected_member_count']['value'] <= len(members))
        c.ok(row['selected_member_count']['state'] == 'available')
        expected = None if lists[2] else row['selected_member_count']['value'] >= selection['minimum_selected_multiplicity']
        c.ok(row['selected_by_multiplicity'] is expected)
        c.array(row['member_spans']); c.ok([s.get('member') for s in row['member_spans']] == members)
        for span in row['member_spans']:
            c.shape(span, ('member', 'state', 'interval_0based_half_open', 'strand', 'span_bases', 'evidence', 'requirement_ids'))
            c.member(span['member']); c.ok(span['state'] in MEMBER_STATES)
            category = 0 if span['state'] == 'present' else 1 if span['state'] == 'absent_zero' else 2
            c.ok(span['member'] in lists[category]); c.evidence(span['evidence'])
            if span['state'] == 'present':
                c.interval(span['interval_0based_half_open'], nonempty=True); c.ok(span['strand'] in ('+', '-'))
                c.ok(span['span_bases']['state'] == 'available')
            else:
                c.ok(span['interval_0based_half_open'] is None and span['strand'] is None)
                count = 0 if span['state'] == 'absent_zero' else None
                c.ok(span['span_bases']['state'] == ('available' if count == 0 else 'incompatible' if span['state'] == 'incompatible' else 'missing'))
            _cell_structure(c, span['span_bases'], selection, 'span_bases', 'nucleotides')
            if span['state'] == 'absent_zero':
                c.ok(span['span_bases']['value'] == 0)
        by_row[row['row_index']] = row
    c.array(value['coverage']); c.ok([r.get('member') for r in value['coverage']] == members)
    for row in value['coverage']:
        c.shape(row, ('member', 'placements', 'known_union_intervals', 'known_union_bases', 'placement_bases',
            'multiply_represented_bases', 'excess_placement_bases', 'denominator_kind', 'denominator_bases',
            'coverage_fraction', 'complement_intervals', 'complement_bases', 'population_state', 'evidence', 'requirement_ids'))
        c.member(row['member']); c.array(row['placements'])
        expected = [(r['row_index'], s) for r in value['rows'] if r['selected_by_multiplicity'] is True
            for s in r['member_spans'] if s['member'] == row['member'] and s['state'] == 'present']
        c.ok(len(row['placements']) == len(expected))
        for p, (index, span) in zip(row['placements'], expected):
            c.shape(p, ('document_id', 'row_index', 'member', 'interval_0based_half_open', 'strand', 'evidence'))
            c.ok(p['document_id'] == value['document_id'] and p['row_index'] == index and p['member'] == row['member']
                and p['interval_0based_half_open'] == span['interval_0based_half_open'] and p['strand'] == span['strand'])
            c.evidence(p['evidence'])
        _coverage_structure(c, row, selection, has_placements=bool(row['placements']),
            known_field='known_union_bases', placement_field='placement_bases', multiple_field='multiply_represented_bases',
            excess_field='excess_placement_bases', unit='nucleotides', placement_unit='nucleotide_placements')
        c.ok(row['denominator_kind'] == selection['denominator'])
        _cell_structure(c, row['denominator_bases'], selection, 'denominator_bases', 'nucleotides')
        _cell_structure(c, row['coverage_fraction'], selection, 'coverage_fraction', 'fraction', fraction=True)
        _cell_structure(c, row['complement_bases'], selection, 'complement_bases', 'nucleotides')
        length = row['denominator_bases']['value'] if row['denominator_bases']['state'] == 'available' else None
        frac = row['coverage_fraction']
        c.ok(frac['denominator'] == length)
        c.ok(frac['numerator'] == row['known_union_bases']['value'])
        if row['denominator_kind'] == 'none':
            c.ok(all(row[k]['state'] == 'not_measured' for k in ('denominator_bases', 'coverage_fraction', 'complement_bases')))
        if frac['state'] == 'available':
            c.ok(row['population_state'] == 'complete_selected' and all(end <= length for start, end in row['known_union_intervals']))
        if row['complement_intervals'] is not None:
            _intervals_structure(c, row['complement_intervals'])
            c.ok(length is not None and row['population_state'] == 'complete_selected'
                and all(end <= length for start, end in row['complement_intervals'])
                and all(end <= length for start, end in row['known_union_intervals'])
                and row['complement_bases']['state'] == 'available'
                and row['complement_bases']['value'] <= length)
        else:
            c.ok(row['complement_bases']['state'] != 'available')
    return deepcopy(value)


@_guard('bbcols', 'selection_invalid')
def validate_mauve_bbcols_component_structure(value: dict) -> dict:
    """Validate saved column associations and cells without recomputing quantities."""
    c, selection = _component_base(value, 'bbcols', ('intervals',))
    selected = selection['members']; by_interval = {}
    for row in value['rows']:
        c.shape(row, ('row_index', 'native_interval_index_0based', 'selected_present_members', 'unresolved_member_tokens',
            'selected_member_count', 'selected_by_multiplicity', 'column_count', 'xmfa_document_id', 'xmfa_block_index',
            'join_state', 'evidence', 'requirement_ids'))
        c.integer(row['row_index']); c.integer(row['native_interval_index_0based'], nullable=True)
        c.members(row['selected_present_members']); c.ok(all(m in selected for m in row['selected_present_members']))
        c.ok(row['selected_present_members'] == [m for m in selected if m in row['selected_present_members']])
        c.array(row['unresolved_member_tokens'])
        for n in row['unresolved_member_tokens']:
            c.native(n)
        _cell_structure(c, row['selected_member_count'], selection, 'selected_member_count', 'members')
        c.ok(row['selected_member_count']['value'] <= len(selected))
        c.ok(row['selected_member_count']['state'] == 'available')
        c.ok(row['selected_by_multiplicity'] is None or type(row['selected_by_multiplicity']) is bool)
        if row['unresolved_member_tokens']:
            c.ok(row['selected_by_multiplicity'] is None)
        if row['selected_by_multiplicity'] is not None:
            c.ok(row['selected_by_multiplicity'] == (row['selected_member_count']['value'] >= selection['minimum_selected_multiplicity']))
        _cell_structure(c, row['column_count'], selection, 'column_count', 'columns', origin='native_observation')
        if row['column_count']['state'] == 'available':
            c.ok(row['column_count']['value'] >= 1)
        c.ok(row['join_state'] in ASSOCIATION_STATES)
        c.text(row['xmfa_document_id'], nullable=True); c.integer(row['xmfa_block_index'], nullable=True)
        if row['join_state'] == 'bound':
            c.ok(row['xmfa_document_id'] is not None and row['xmfa_block_index'] is not None)
        c.evidence(row['evidence'])
        if row['native_interval_index_0based'] is not None:
            by_interval.setdefault(row['native_interval_index_0based'], []).append(row)
    c.array(value['intervals']); seen = []
    for row in value['intervals']:
        c.shape(row, ('native_interval_index_0based', 'contributing_row_indices', 'known_union_intervals', 'union_columns',
            'column_placements', 'multiply_represented_columns', 'excess_column_placements', 'xmfa_document_id',
            'xmfa_block_index', 'bound_block_width', 'selected_block_fraction', 'population_state', 'evidence', 'requirement_ids'))
        index = row['native_interval_index_0based']; c.integer(index); seen.append(index)
        c.ok(index in by_interval); c.indices(row['contributing_row_indices'])
        candidates = by_interval[index]
        expected = [r for r in candidates if r['selected_by_multiplicity'] is True and r['column_count']['state'] == 'available']
        c.ok(all(i in [r['row_index'] for r in expected] for i in row['contributing_row_indices']))
        c.ok(row['contributing_row_indices'] == [r['row_index'] for r in expected
            if r['row_index'] in row['contributing_row_indices']])
        _coverage_structure(c, row, selection, has_placements=bool(row['contributing_row_indices']),
            known_field='union_columns', placement_field='column_placements',
            multiple_field='multiply_represented_columns', excess_field='excess_column_placements',
            unit='columns', placement_unit='column_placements')
        c.text(row['xmfa_document_id'], nullable=True); c.integer(row['xmfa_block_index'], nullable=True)
        _cell_structure(c, row['bound_block_width'], selection, 'bound_block_width', 'columns')
        _cell_structure(c, row['selected_block_fraction'], selection, 'selected_block_fraction', 'fraction', fraction=True)
        width = row['bound_block_width']['value'] if row['bound_block_width']['state'] == 'available' else None
        frac = row['selected_block_fraction']
        c.ok(frac['denominator'] == width and frac['numerator'] == row['union_columns']['value'])
        if frac['state'] == 'available':
            c.ok(row['population_state'] == 'complete_selected' and row['xmfa_document_id'] is not None
                and row['xmfa_block_index'] is not None and all(end <= width for start, end in row['known_union_intervals'])
                and all(r['join_state'] == 'bound' and r['xmfa_document_id'] == row['xmfa_document_id']
                    and r['xmfa_block_index'] == row['xmfa_block_index'] for r in candidates))
        if not selection['calculate_bound_block_fraction']:
            c.ok(row['bound_block_width']['state'] == row['selected_block_fraction']['state'] == 'not_measured')
        c.evidence(row['evidence'])
    c.ok(seen == list(by_interval))
    return deepcopy(value)


__all__ = ['validate_mauve_backbone_document', 'validate_mauve_bbcols_document',
    'validate_mauve_backbone_selection', 'validate_mauve_bbcols_selection',
    'validate_mauve_backbone_components', 'validate_mauve_bbcols_components',
    'validate_mauve_backbone_component_structure', 'validate_mauve_bbcols_component_structure']
