"""Native, supplied-source and original-occurrence nucleotide coordinates.

Explicit cell references retain a physical row even when another row in its
block is defective. Source associations additionally require current, exact
source checks. No input is acquired and no native parser is invoked here.
"""
from copy import deepcopy

from . import xmfa_calculation_contracts as c
from .bvbrc_alignment_values import diagnostic, requirement
from .xmfa_format_contracts import validate_xmfa_document
from .xmfa_sources import _native_members, _positive, validate_xmfa_bindings_for_document


def _operands(document, bindings):
    document = validate_xmfa_document(document)
    if bindings is not None:
        bindings = validate_xmfa_bindings_for_document(document, bindings)
    return document, bindings


def _evidence(*groups):
    result = []
    for group in groups:
        for entry in group:
            if entry not in result:
                result.append(deepcopy(entry))
    return result


def _issue(result, suffix, path, *, kind=None, role=None):
    code = 'xmfa_' + suffix
    entry = diagnostic(code, path=path)
    if entry not in result['diagnostics']:
        result['diagnostics'].append(entry)
    result['status'] = 'partial'
    if kind is not None:
        identity = result['document_id'] + ':' + path + ':' + code
        needed = requirement(identity, kind=kind, role=role, reason_code=code)
        if needed not in result['requirements']:
            result['requirements'].append(needed)
        return needed['requirement_id']
    return None


def _row_positions(row):
    """One entry per full physical aligned character, never subset offsets."""
    if row['coordinate_state'] != 'present':
        return [None] * len(row['sequence'])
    start, end = row['interval_0based_half_open']
    cursor, step = (start, 1) if row['strand'] == '+' else (end - 1, -1)
    result = []
    for symbol in row['sequence']:
        result.append(None if symbol == '-' else cursor)
        if symbol != '-':
            cursor += step
    return result


def _block_qualifications(result, document, block):
    """Retain native defects without making them a new numerical population."""
    path = '/blocks/' + str(block['block_index'])
    if not block['terminated']:
        _issue(result, 'missing_block_terminator', path)
    numbers = [_positive(row['member_number']) for row in block['records']]
    known = [n for n in numbers if n is not None]
    if len(known) != len(set(known)):
        _issue(result, 'duplicate_member_record', path)
    if len({len(row['sequence']) for row in block['records'] if row['nongap_character_count'] > 0}) > 1:
        _issue(result, 'row_width_conflict', path)
    if all(row['coordinate_state'] == 'absent_zero' for row in block['records']):
        _issue(result, 'all_zero_block', path)
    for row in block['records']:
        if row['coordinate_state'] not in ('present', 'absent_zero'):
            _issue(result, 'coordinate_invalid', path + '/records/' + str(row['record_index']))
    if any(line['block_index'] == block['block_index'] for line in document['unparsed']):
        _issue(result, 'unparsed_line', path)


def _binding_indexes(bindings):
    if bindings is None:
        return {}, {}
    return ({m['member_number']: m for m in bindings['members']},
            {(s['record']['block_index'], s['record']['record_index']): s for s in bindings['source_checks']})


def _binding_reports(result, bindings):
    """Preserve actual input needs; missing association is not missing bytes."""
    if bindings is not None:
        result['requirements'] = deepcopy(bindings['requirements'])
        result['diagnostics'] = deepcopy(bindings['diagnostics'])
        if bindings['status'] != 'ok' or result['requirements'] or result['diagnostics']:
            result['status'] = 'partial'


def _source_issue(result, bindings, number, reason, path):
    if bindings is None:
        return [_issue(result, reason, path, kind='input_bytes', role='xmfa_staged_input')]
    _issue(result, reason, path)
    # Requirement IDs are opaque shared-host IDs. Retain them rather than
    # decoding/recreating the binder's current hash convention. A reason may
    # describe the same dependency of several members; all its supplied records
    # remain inspectable together with their original scoped diagnostics.
    codes = {d['code'] for d in bindings['diagnostics']
             if d['path'] in (path, '/members/' + str(number))}
    ids = [r['requirement_id'] for r in bindings['requirements'] if r['reason_code'] in codes]
    if not ids:
        ids = [_issue(result, reason, path, kind='scientific_metadata', role='xmfa_input_binding')]
    return ids


def _source_coordinate(member, check, p0, strand):
    if member is None or member['state'] == 'missing':
        return 'missing', None, 'source_binding_missing'
    if member['state'] == 'conflicting':
        return 'conflicting', None, 'source_binding_conflict'
    if check['state'] != 'match':
        reason = 'source_sequence_mismatch' if check['state'] == 'mismatch' else 'source_span_outside_input'
        return 'conflicting', None, reason
    for component in member['components']:
        start, end = component['member_interval_0based_half_open']
        if start <= p0 < end:
            return 'resolved', {'file_id': component['file_id'], 'record_id': component['record_id'],
                'entry_1based': component['entry_1based'], 'position_0based': p0 - start, 'strand': strand}, None
    # Already-validated bindings partition the whole source. This cannot be
    # turned into clipping or a guessed neighboring component.
    c.require(False, 'source_component_position_conflict')


def _original_projection(source, maps):
    """Return all consistent occurrences; conflicts affect only that occurrence.

    Same-occurrence length disagreement prevents an authoritative mapping even
    where only one of the conflicting segments currently contains the base.
    Distinct transformations supporting the same coordinate remain inspectable.
    """
    lengths = {}
    for mapping in maps:
        key = c.occurrence(mapping['original_member'])
        lengths.setdefault(key, set()).add(mapping['original_length'])
    applicable = {}
    for mapping in maps:
        a, b = mapping['staged_interval_0based_half_open']
        if ((mapping['file_id'], mapping['record_id']) == (source['file_id'], source['record_id'])
                and a <= source['position_0based'] < b):
            key = c.occurrence(mapping['original_member'])
            applicable.setdefault(key, []).append(mapping)
    result, conflicts, unevidenced = [], set(), False
    for key, candidates in applicable.items():
        values = []
        for mapping in candidates:
            offset = source['position_0based'] - mapping['staged_interval_0based_half_open'][0]
            x, y = mapping['original_interval_0based_half_open']
            position = x + offset if mapping['strand'] == '+' else y - 1 - offset
            strand = '+' if mapping['strand'] == source['strand'] else '-'
            values.append((position, strand))
        if len(set(values)) != 1 or len(lengths[key]) != 1:
            conflicts.add(key)
            continue
        for mapping, (position, strand) in zip(candidates, values):
            if not mapping['evidence']:
                unevidenced = True
                continue
            item = {'original_member': deepcopy(mapping['original_member']), 'position_0based': position,
                'original_length': mapping['original_length'], 'strand': strand,
                'transformation_id': mapping['transformation_id'], 'evidence': deepcopy(mapping['evidence'])}
            if item not in result:
                result.append(item)
    return result, conflicts, unevidenced


def xmfa_column_coordinates(document: dict, *, cells: tuple[dict, ...],
                            bindings: dict | None) -> dict:
    """Map requested literal cells without changing their full-row offsets."""
    document, bindings = _operands(document, bindings)
    c.require(type(cells) is tuple, 'cells_tuple_required')
    refs = [c.ref(cell, cell=True) for cell in cells]
    c.require(len(refs) == len(set(refs)), 'duplicate_requested_index')
    members, checks = _binding_indexes(bindings)
    result = {'document_id': document['document_id'], 'status': 'ok', 'cells': [],
              'requirements': [], 'diagnostics': []}
    _binding_reports(result, bindings)
    positions = {}
    for cell, (bi, ri, column) in zip(cells, refs):
        c.require(bi < len(document['blocks']), 'cell_block_outside_document')
        block = document['blocks'][bi]
        c.require(ri < len(block['records']), 'cell_record_outside_block')
        row = block['records'][ri]
        c.require(column < len(row['sequence']), 'cell_column_outside_record')
        symbol, number = row['sequence'][column], _positive(row['member_number'])
        item = {'cell': deepcopy(cell), 'member_number': number, 'aligned_symbol': symbol,
            'state': 'incompatible', 'native_position_1based': None, 'native_position_0based': None,
            'native_strand': row['strand'], 'forward_symbol': None, 'source_state': 'not_applicable',
            'source_coordinate': None, 'original_coordinates': [], 'evidence': []}
        path = f'/cells/{len(result["cells"])}'
        if row['coordinate_state'] == 'absent_zero':
            item['state'] = 'absent_zero'
        elif row['coordinate_state'] != 'present':
            _issue(result, 'coordinate_invalid', path)
        elif symbol == '-':
            item['state'] = 'gap'
        else:
            if (bi, ri) not in positions:
                positions[bi, ri] = _row_positions(row)
            p0 = positions[bi, ri][column]
            item.update(state='residue', native_position_0based=p0, native_position_1based=p0 + 1,
                        forward_symbol=symbol if row['strand'] == '+' else symbol.translate(c.COMPLEMENT))
            member, check = members.get(number), checks.get((bi, ri))
            state, sc, reason = _source_coordinate(member, check, p0, row['strand'])
            item.update(source_state=state, source_coordinate=sc)
            if reason:
                source_path = '/members/' + str(number) if state == 'missing' else f'/blocks/{bi}/records/{ri}'
                _source_issue(result, bindings, number, reason, source_path)
            else:
                item['evidence'] = _evidence(member['evidence'], check['evidence'])
                originals, conflicts, unevidenced = _original_projection(sc, bindings['original_maps'])
                item['original_coordinates'] = originals
                if conflicts:
                    _issue(result, 'original_map_conflict', f'/blocks/{bi}/records/{ri}',
                           kind='scientific_metadata', role='xmfa_original_map')
                if not originals and not conflicts or unevidenced:
                    _issue(result, 'original_map_missing', f'/blocks/{bi}/records/{ri}',
                           kind='scientific_metadata', role='xmfa_original_map')
        if block['completeness'] != 'complete':
            _block_qualifications(result, document, block)
        result['cells'].append(item)
    return c.validate_xmfa_coordinates(result)


def xmfa_source_positions(document: dict, *, queries: tuple[dict, ...],
                          bindings: dict | None) -> dict:
    """Return every retained native placement; incomplete searches stay unknown."""
    document, bindings = _operands(document, bindings)
    c.require(type(queries) is tuple, 'queries_tuple_required')
    native_members = set(_native_members(document)); seen = set()
    members, _ = _binding_indexes(bindings)
    result = {'document_id': document['document_id'], 'status': 'ok', 'queries': [],
              'requirements': [], 'diagnostics': []}
    # Index the native axis once. Repeated records deliberately remain repeated
    # physical matches; they are never collapsed by source identity or content.
    placements = {}
    for block in document['blocks']:
        for row in block['records']:
            number = _positive(row['member_number'])
            if row['coordinate_state'] == 'present':
                for column, position in enumerate(_row_positions(row)):
                    if position is not None:
                        placements.setdefault((number, position), []).append({'block_index': block['block_index'],
                            'record_index': row['record_index'], 'column_0based': column})
    for query in queries:
        c.shape(query, ('member_number', 'position_0based'))
        number, position = query['member_number'], query['position_0based']
        c.integer(number, minimum=1); c.integer(position)
        c.require(number in native_members, 'query_member_unknown')
        key = number, position
        c.require(key not in seen, 'duplicate_requested_index'); seen.add(key)
        member = members.get(number)
        if member is not None and member['source_length'] is not None:
            c.require(position < member['source_length'], 'query_outside_source')
        complete = document['completeness']
        matches = placements.get(key, [])
        if complete != 'complete':
            state = 'unknown'
            _issue(result, 'selected_population_partial', '/queries/' + str(len(result['queries'])))
        else:
            state = 'multiple' if len(matches) > 1 else 'unique' if matches else 'none_in_document'
        result['queries'].append({'member_number': number, 'position_0based': position, 'state': state,
            'matches': matches, 'search_completeness': complete, 'evidence': []})
    return c.validate_xmfa_inverse_coordinates(result)


__all__ = ['xmfa_column_coordinates', 'xmfa_source_positions']
