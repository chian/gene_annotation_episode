"""Inspectable literal-site, selected-pair and interval XMFA measurements.

Native-axis coverage counts survive missing source files. Fractions and source
complements require a complete, matching source binding and selected population.
These pure calculations neither acquire data nor assign annotation credit.
"""
from collections import Counter
from copy import deepcopy
import math

from . import xmfa_calculation_contracts as c
from .bvbrc_alignment_values import numeric_cell
from .xmfa_coordinates import (_operands, _binding_indexes, _row_positions, _issue,
    _evidence, _original_projection, _source_coordinate, _block_qualifications,
    _binding_reports, _source_issue)
from .xmfa_format_contracts import validate_xmfa_document
from .xmfa_sources import _native_members, _positive


def _selection(document, selection):
    selection = c.validate_xmfa_selection(selection)
    c.require(selection['document_id'] == document['document_id'], 'selection_document_conflict')
    c.require(set(selection['member_numbers']) <= set(_native_members(document)), 'selection_member_unknown')
    for chosen in selection['block_columns']:
        index = chosen['block_index']
        c.require(index < len(document['blocks']), 'selection_block_outside_document')
        block = document['blocks'][index]
        bound = max((len(row['sequence']) for row in block['records']), default=0)
        c.require(all(column < bound for column in chosen['columns_0based']), 'selection_column_outside_block')
    return selection


def _cell(selection, field, unit, value=None, *, state='available', prefix='xmfa_',
          numerator=None, denominator=None, evidence=(), requirement_ids=()):
    return numeric_cell(value, state=state, unit=unit, origin='calculated',
        population_id=selection['population_id'], method_id=prefix + field + '_v1',
        numerator=numerator, denominator=denominator, uncertainty=None,
        evidence=_evidence(selection['evidence'], evidence), requirement_ids=requirement_ids)


def _fraction(selection, field, numerator, denominator, *, state=None, prefix='xmfa_', evidence=(), requirement_ids=()):
    if state is None:
        state = 'available' if denominator else 'not_measured'
    return _cell(selection, field, 'fraction', numerator / denominator if state == 'available' else None,
                 state=state, prefix=prefix, numerator=numerator, denominator=denominator,
                 evidence=evidence, requirement_ids=requirement_ids)


def _block_rows(block, members, columns):
    grouped = {number: [] for number in members}
    for row in block['records']:
        number = _positive(row['member_number'])
        if number in grouped:
            grouped[number].append(row)
    present, zero, omitted, conflicts, valid = [], [], [], [], {}
    for number in members:
        rows = grouped[number]
        if not rows:
            if block['terminated']:
                omitted.append(number)
        elif len(rows) > 1 or rows[0]['coordinate_state'] not in ('present', 'absent_zero'):
            conflicts.append(number)
        elif rows[0]['coordinate_state'] == 'present':
            valid[number] = rows[0]
            present.append(number)
        else:
            zero.append(number)
    widths = {len(row['sequence']) for row in valid.values()}
    width = next(iter(widths)) if len(widths) == 1 else None
    ragged = len(widths) > 1 or width is not None and any(
        len(grouped[number][0]['sequence']) not in (0, width) for number in zero)
    outside = [number for number, row in valid.items() if any(column >= len(row['sequence']) for column in columns)]
    aggregate_conflicts = set(conflicts) | set(outside)
    if ragged:
        aggregate_conflicts.update(present)
        aggregate_conflicts.update(n for n in zero if len(grouped[n][0]['sequence']) not in (0, width))
    classified = {
        'present_members': [n for n in members if n in present and n not in aggregate_conflicts],
        'zero_members': [n for n in members if n in zero and n not in aggregate_conflicts],
        'omitted_members': omitted,
        'conflicting_members': [n for n in members if n in aggregate_conflicts],
        'record_refs': [{'block_index': block['block_index'], 'record_index': row['record_index']}
            for row in block['records'] if _positive(row['member_number']) in grouped],
    }
    # Unknown native member tokens can conceal selected membership. They do not
    # become a fabricated member number or an omitted-member observation.
    unidentified = any(_positive(row['member_number']) is None for row in block['records'])
    unresolved = not block['terminated'] or unidentified or any(
        u for u in members if u not in present + zero + omitted + conflicts)
    return classified, valid, grouped, bool(aggregate_conflicts), unresolved, ragged


def _population_state(selection, conflict, unresolved):
    if conflict:
        return 'incompatible'
    if unresolved or selection['completeness'] != 'complete':
        return 'truncated'
    return 'available'


def _entropy(counts):
    total = sum(counts)
    return -sum(n / total * math.log2(n / total) for n in counts) if total else None


def xmfa_alignment_components(document: dict, *, selection: dict,
    selected_pairs: tuple[tuple[int, int], ...], case_policy: str) -> dict:
    """Calculate literal sites and only the explicitly selected unordered pairs."""
    document = validate_xmfa_document(document)
    selection = _selection(document, selection)
    c.require(type(case_policy) is str and case_policy in ('preserve', 'uppercase'), 'case_policy_invalid')
    c.require(type(selected_pairs) is tuple and all(type(pair) is tuple for pair in selected_pairs), 'pairs_tuple_required')
    pairs = [list(pair) for pair in selected_pairs]
    c._pairs(pairs, selection['member_numbers'])
    result = {'schema_version': 'mauve_xmfa_alignment_components_v1', 'document_id': document['document_id'],
        'status': 'ok', 'selection': selection, 'parameters': {'case_policy': case_policy, 'selected_pairs': pairs},
        'blocks': [], 'requirements': [], 'diagnostics': []}
    if selection['completeness'] != 'complete' or not selection['block_columns'] and document['completeness'] == 'unknown':
        _issue(result, 'selected_population_partial', '/selection')
    for chosen in selection['block_columns']:
        block = document['blocks'][chosen['block_index']]
        columns, members = chosen['columns_0based'], selection['member_numbers']
        categories, valid, grouped, conflict, unresolved, ragged = _block_rows(block, members, columns)
        state = _population_state(selection, conflict, unresolved)
        path = '/blocks/' + str(block['block_index'])
        if block['completeness'] != 'complete':
            _block_qualifications(result, document, block)
        if state != 'available':
            _issue(result, 'selected_population_partial', path)
        if ragged:
            _issue(result, 'row_width_conflict', path)
        if any(len(rows) > 1 for rows in grouped.values()):
            _issue(result, 'duplicate_member_record', path)
        for number in categories['conflicting_members']:
            _issue(result, 'coordinate_invalid', path + '/members/' + str(number))
        output = {'block_index': block['block_index'], **categories,
            'selected_column_count': _cell(selection, 'selected_column_count', 'columns', len(columns)),
            'sites': [], 'pairs': []}
        for field, values in (('present_member_count', categories['present_members']),
                              ('zero_member_count', categories['zero_members']),
                              ('omitted_member_count', categories['omitted_members'])):
            output[field] = _cell(selection, field, 'members', len(values) if state == 'available' else None, state=state)
        for column in columns:
            symbols = Counter((valid[n]['sequence'][column].upper() if case_policy == 'uppercase'
                else valid[n]['sequence'][column]) for n in categories['present_members'])
            canonical = {symbol: count for symbol, count in symbols.items() if symbol in 'ACGT'}
            counts = {'present_member_count': len(categories['present_members']),
                'absent_member_count': len(categories['zero_members']) + len(categories['omitted_members']),
                'gap_count': symbols.get('-', 0), 'nongap_count': sum(symbols.values()) - symbols.get('-', 0),
                'canonical_count': sum(canonical.values()),
                'ambiguity_count': sum(n for symbol, n in symbols.items() if symbol in 'RYSWKMBDHVN'),
                'other_count': sum(n for symbol, n in symbols.items() if symbol not in 'ACGTRYSWKMBDHVN-')}
            site = {'column_0based': column, 'symbol_counts': [
                {'symbol': symbol, 'count': _cell(selection, 'symbol_count', 'characters', count if state == 'available' else None,
                                                 state=state)} for symbol, count in symbols.items()]}
            for field, count in counts.items():
                site[field] = _cell(selection, field, 'members' if 'member' in field else 'characters',
                                    count if state == 'available' else None, state=state)
            for field, values in (('literal_entropy_bits', symbols.values()), ('canonical_entropy_bits', canonical.values())):
                number = _entropy(list(values)) if state == 'available' else None
                site[field] = _cell(selection, field, 'bits', number,
                    state=state if state != 'available' else 'not_measured' if number is None else 'available')
            site['canonical_majority_fraction'] = _fraction(selection, 'canonical_majority_fraction',
                max(canonical.values(), default=0) if state == 'available' else None,
                counts['canonical_count'] if state == 'available' else None,
                state=None if state == 'available' else state)
            output['sites'].append(site)
        for a, b in selected_pairs:
            pair_state = 'available'; numeric_state = 'available'
            involved = [grouped[a], grouped[b]]
            if any(len(rows) > 1 or rows and rows[0]['coordinate_state'] not in ('present', 'absent_zero') for rows in involved):
                pair_state, numeric_state = 'incompatible', 'incompatible'
            elif any(n in categories['zero_members'] + categories['omitted_members'] for n in (a, b)):
                pair_state, numeric_state = 'not_coobserved', 'not_measured'
            elif unresolved or selection['completeness'] != 'complete':
                pair_state, numeric_state = 'incomplete', 'truncated'
            elif (a not in valid or b not in valid or len(valid[a]['sequence']) != len(valid[b]['sequence'])
                  or any(column >= len(valid[a]['sequence']) or column >= len(valid[b]['sequence']) for column in columns)):
                pair_state, numeric_state = 'incompatible', 'incompatible'
            pair = {'member_a': a, 'member_b': b, 'state': pair_state}
            counts = dict.fromkeys(c.PAIR_COUNTS, 0)
            if pair_state == 'available':
                for column in columns:
                    x, y = valid[a]['sequence'][column], valid[b]['sequence'][column]
                    if case_policy == 'uppercase':
                        x, y = x.upper(), y.upper()
                    category = ('both_gap' if x == y == '-' else 'a_only_gap' if x == '-' else
                        'b_only_gap' if y == '-' else 'identical_canonical' if x in 'ACGT' and y == x else
                        'substitutions' if x in 'ACGT' and y in 'ACGT' else 'ambiguous_or_other')
                    counts[category] += 1
                counts['comparable_canonical'] = counts['identical_canonical'] + counts['substitutions']
            else:
                _issue(result, 'pair_not_coobserved' if pair_state == 'not_coobserved' else 'selected_population_partial', path)
            for field, number in counts.items():
                pair[field] = _cell(selection, field, 'columns', number if pair_state == 'available' else None, state=numeric_state)
            pair['identity_fraction'] = _fraction(selection, 'identity_fraction',
                counts['identical_canonical'] if pair_state == 'available' else None,
                counts['comparable_canonical'] if pair_state == 'available' else None,
                state=None if pair_state == 'available' else numeric_state)
            if pair_state == 'available' and not counts['comparable_canonical']:
                _issue(result, 'empty_comparison_population', path)
            output['pairs'].append(pair)
        result['blocks'].append(output)
    return c.validate_xmfa_alignment_components(result)


def _selected_placements(document, selection, basis):
    placements = {number: [] for number in selection['member_numbers']}
    states = {number: {'conflict': False, 'unresolved': False} for number in selection['member_numbers']}
    qualifications = []
    for chosen in selection['block_columns']:
        block = document['blocks'][chosen['block_index']]
        columns = chosen['columns_0based']
        _, valid, grouped, bad, unknown, ragged = _block_rows(block, selection['member_numbers'], columns)
        if ragged:
            qualifications.append(('row_width_conflict', '/blocks/' + str(block['block_index'])))
        native_conflict = any(len(rows) > 1 or rows and rows[0]['coordinate_state'] not in ('present', 'absent_zero')
                              for rows in grouped.values())
        for number, rows in grouped.items():
            own_bad = len(rows) > 1 or bool(rows) and rows[0]['coordinate_state'] not in ('present', 'absent_zero')
            own_outside = number in valid and any(column >= len(valid[number]['sequence']) for column in columns)
            states[number]['conflict'] |= own_bad or own_outside or (basis == 'multi_member_block' and native_conflict) or (
                basis == 'cooccupied_column' and bad)
            states[number]['unresolved'] |= unknown
        # Keep independently valid physical native coordinates even when a
        # neighboring selected row makes the complete population unavailable.
        positions = {n: _row_positions(row) for n, row in valid.items()}
        for number, row in valid.items():
            retained = []
            for column in columns:
                if column >= len(row['sequence']) or positions[number][column] is None:
                    continue
                include = basis == 'represented' or basis == 'multi_member_block' and len(valid) >= 2
                if basis == 'cooccupied_column':
                    include = not ragged and any(other != number and column < len(other_positions)
                        and other_positions[column] is not None for other, other_positions in positions.items())
                if include:
                    retained.append([positions[number][column], positions[number][column] + 1])
            runs = c.union_intervals(retained)
            if row['strand'] == '-':
                runs.reverse()
            placements[number].extend({'record': {'block_index': block['block_index'], 'record_index': row['record_index']},
                'interval_0based_half_open': run, 'strand': row['strand']} for run in runs)
    if not selection['block_columns'] and document['completeness'] == 'unknown':
        for state in states.values():
            state['unresolved'] = True
    return placements, states, qualifications


def _coverage_originals(member, placements, check_index, bindings, selection, prefix, membership, source_state, result):
    if member is None or member['state'] != 'resolved':
        return []
    component_keys = {(part['file_id'], part['record_id']) for part in member['components']}
    maps = bindings['original_maps']
    grouped = {}
    for mapping in maps:
        if (mapping['file_id'], mapping['record_id']) in component_keys:
            grouped.setdefault(c.occurrence(mapping['original_member']), []).append(mapping)
    if not grouped:
        return []
    projection = []
    for placement in placements:
        key = tuple(placement['record'][field] for field in ('block_index', 'record_index'))
        check = check_index[key]
        for position in range(*placement['interval_0based_half_open']):
            state, source, _ = _source_coordinate(member, check, position, placement['strand'])
            if state == 'resolved':
                originals, conflicts, _ = _original_projection(source, maps)
                projection.append((source, originals, conflicts, False))
            else:
                # Locate the component only to describe which projection is
                # missing. This is never returned as a validated coordinate.
                for component in member['components']:
                    a, b = component['member_interval_0based_half_open']
                    if a <= position < b:
                        projection.append(({'file_id': component['file_id'], 'record_id': component['record_id']}, [], set(), True))
    output = []
    for occurrence_key, own_maps in grouped.items():
        occurrence_value = own_maps[0]['original_member']
        lengths = {m['original_length'] for m in maps if c.occurrence(m['original_member']) == occurrence_key}
        participating = {(m['file_id'], m['record_id']) for m in own_maps}
        intervals, missing, conflict = [], source_state != 'available', len(lengths) != 1
        for source, originals, conflicts, source_failed in projection:
            if (source['file_id'], source['record_id']) not in participating:
                continue
            own = [o for o in originals if c.occurrence(o['original_member']) == occurrence_key]
            intervals.extend([o['position_0based'], o['position_0based'] + 1] for o in own)
            conflict |= occurrence_key in conflicts
            # Mapping a selected base explicitly to a different occurrence is
            # accounted for. Unmapped selected bases in this component are not.
            missing |= source_failed or not originals and occurrence_key not in conflicts
        union = c.union_intervals(intervals); count = c.interval_length(union)
        length = next(iter(lengths)) if len(lengths) == 1 else None
        complete = membership == 'complete' and not missing and not conflict
        mapping_completeness = 'complete' if complete else 'truncated' if membership == 'truncated' else 'partial'
        path = '/members/' + str(member['member_number']) + '/original_coverage/' + str(len(output))
        ids = []
        if conflict or missing:
            ids.append(_issue(result, 'original_map_conflict' if conflict else 'original_map_missing', path,
                              kind='scientific_metadata', role='xmfa_original_map'))
        ev = _evidence(*(m['evidence'] for m in own_maps))
        state = None if complete else 'incompatible' if conflict or source_state == 'incompatible' else (
            'truncated' if membership != 'complete' else 'missing')
        output.append({'original_member': deepcopy(occurrence_value),
            'original_length': _cell(selection, 'original_length', 'nucleotides', length,
                state='available' if length is not None else 'incompatible', prefix=prefix + 'original_', evidence=ev, requirement_ids=ids),
            'known_union_intervals': union,
            'known_union_bases': _cell(selection, 'known_union_bases', 'nucleotides', count, prefix=prefix + 'original_', evidence=ev),
            'coverage_fraction': _fraction(selection, 'coverage_fraction', count, length, state=state,
                prefix=prefix + 'original_', evidence=ev, requirement_ids=ids),
            'mapping_completeness': mapping_completeness, 'evidence': ev})
    return output


def xmfa_interval_coverage(document: dict, *, selection: dict,
    bindings: dict | None, basis: str) -> dict:
    """Measure three explicit bases separately, preserving placement multiplicity."""
    document, bindings = _operands(document, bindings)
    selection = _selection(document, selection)
    c.require(type(basis) is str and basis in c.BASES, 'coverage_basis_invalid')
    result = {'schema_version': 'mauve_xmfa_coverage_components_v1', 'document_id': document['document_id'],
        'status': 'ok', 'selection': selection, 'parameters': {'basis': basis}, 'members': [],
        'requirements': [], 'diagnostics': []}
    _binding_reports(result, bindings)
    placements, states, qualifications = _selected_placements(document, selection, basis)
    for chosen in selection['block_columns']:
        block = document['blocks'][chosen['block_index']]
        if block['completeness'] != 'complete':
            _block_qualifications(result, document, block)
    for reason, path in qualifications:
        _issue(result, reason, path)
    members, checks = _binding_indexes(bindings)
    prefix = 'xmfa_' + basis + '_'
    for number in selection['member_numbers']:
        numeric_state = _population_state(selection, **states[number])
        membership = ('complete' if numeric_state == 'available' else 'truncated'
            if selection['completeness'] == 'truncated' or any(not document['blocks'][b['block_index']]['terminated']
                for b in selection['block_columns']) else 'unknown' if not selection['block_columns']
                and document['completeness'] == 'unknown' else 'partial')
        if membership != 'complete':
            _issue(result, 'selected_population_partial', '/members/' + str(number))
        member = members.get(number); known = placements[number]
        intervals = [placement['interval_0based_half_open'] for placement in known]
        union = c.union_intervals(intervals); count = c.interval_length(union)
        total = c.interval_length(intervals); multiple = c.multiplicity_bases(intervals)
        path = '/members/' + str(number); ids = []
        length = member['source_length'] if member is not None else None
        ev = member['evidence'] if member is not None else []
        source_state = 'available'
        if length is None:
            source_state = 'incompatible' if member is not None and member['state'] == 'conflicting' else 'missing'
            ids.extend(_source_issue(result, bindings, number,
                'source_binding_conflict' if source_state == 'incompatible' else 'source_binding_missing', path))
        # Every selected positive row must agree with source bytes, including
        # rows whose contribution under this coverage basis happens to be zero.
        for chosen in selection['block_columns']:
            block = document['blocks'][chosen['block_index']]
            for row in block['records']:
                if _positive(row['member_number']) == number and row['coordinate_state'] == 'present' and length is not None:
                    check = checks[(block['block_index'], row['record_index'])]
                    if check['state'] != 'match':
                        source_state = 'incompatible'
                        ids.extend(_source_issue(result, bindings, number,
                            'source_sequence_mismatch' if check['state'] == 'mismatch' else 'source_span_outside_input',
                            '/blocks/' + str(block['block_index']) + '/records/' + str(row['record_index'])))
        ids = list(dict.fromkeys(ids))
        state = ('incompatible' if 'incompatible' in (source_state, numeric_state) else
                 'truncated' if 'truncated' in (source_state, numeric_state) else source_state)
        complete = state == 'available'
        complement = c.complement_intervals(union, length) if complete else None
        output = {'member_number': number,
            'source_length': _cell(selection, 'source_length', 'nucleotides', length,
                state='available' if length is not None else source_state, prefix=prefix, evidence=ev, requirement_ids=ids),
            'placements': known, 'known_union_intervals': union, 'membership_completeness': membership,
            'selected_coverage_fraction': _fraction(selection, 'selected_coverage_fraction', count, length,
                state=None if complete else state, prefix=prefix, evidence=ev, requirement_ids=ids),
            'complement_intervals': complement,
            'complement_bases': _cell(selection, 'complement_bases', 'nucleotides',
                c.interval_length(complement) if complete else None, state=state, prefix=prefix, evidence=ev, requirement_ids=ids)}
        for field, value in (('known_union_bases', count), ('placement_bases', total),
                             ('multiply_represented_bases', multiple), ('excess_placement_bases', total - count)):
            output[field] = _cell(selection, field,
                'nucleotide_placements' if field in ('placement_bases', 'excess_placement_bases') else 'nucleotides',
                value, prefix=prefix)
        if multiple:
            _issue(result, 'overlapping_placement', path)
        output['original_coverage'] = _coverage_originals(member, known, checks, bindings, selection, prefix, membership, source_state, result)
        result['members'].append(output)
    return c.validate_xmfa_coverage_components(result)


__all__ = ['xmfa_alignment_components', 'xmfa_interval_coverage']
