"""Deterministic, separately selectable measurements of native Mauve sidecars.

Backbone spans use signed 1-based closed endpoints normalized to a forward
half-open axis. BBCols ranges use the native internal interval and column axis.
Unions, placement sums, multiply represented positions and excess placements
are separate quantities. No backbone/BBCols row-index correspondence is used.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib

from . import mauve_backbone_contracts as c
from .bvbrc_alignment_values import numeric_cell, diagnostic, requirement
from .bvbrc_genome_alignment_input_contracts import (validate_genome_alignment_inputs,
    validate_genome_alignment_associations)
from .xmfa_format_contracts import validate_xmfa_document
from .xmfa_calculation_contracts import (union_intervals, interval_length,
    multiplicity_bases, complement_intervals)


def _member(index):
    return {'namespace': c.SIDECAR_NAMESPACE, 'index': index}


def _evidence(*groups):
    result = []
    for group in groups:
        for row in group:
            if row not in result:
                result.append(deepcopy(row))
    return result


def _base(document, selection, family, tail):
    check = c._Check(family)
    check.ok(selection['document_id'] == document['document_id'], 'selection_document_conflict')
    check.ok(all(i < len(document['rows']) for i in selection['row_indices']), 'selection_record_unknown')
    if selection['population_scope'] == 'all_observed_document_rows':
        check.ok(set(selection['row_indices']) == set(range(len(document['rows']))), 'selection_population_incomplete')
    return {'schema_version': 'mauve_' + family + '_components_v1',
        'document_id': document['document_id'], 'status': 'ok', 'selection': selection,
        'rows': [], tail: [], 'requirements': [], 'diagnostics': []}


def _cell(selection, family, field, unit, value=None, *, state='available', origin='calculated',
          numerator=None, denominator=None, evidence=(), ids=()):
    return numeric_cell(value, state=state, unit=unit, origin=origin,
        population_id=selection['population_id'], method_id='mauve_' + family + '_' + field + '_v1',
        numerator=numerator, denominator=denominator, evidence=_evidence(selection['evidence'], evidence),
        requirement_ids=list(dict.fromkeys(ids)), uncertainty=None)


def _fraction(selection, family, field, count, denominator, *, state, evidence=(), ids=()):
    if state == 'available' and denominator == 0:
        state = 'not_measured'
    return _cell(selection, family, field, 'fraction',
        count / denominator if state == 'available' else None, state=state,
        numerator=count, denominator=denominator, evidence=evidence, ids=ids)


def _issue(result, document, family, code, path, *, kind=None, role=None, prefix=None):
    full = (prefix or 'mauve_' + family + '_') + code
    assert full in c.ALLOWED_CODES
    diagnostic_row = diagnostic(full, path=path, evidence_refs=[document['artifact']['source_ref']])
    if diagnostic_row not in result['diagnostics']:
        result['diagnostics'].append(diagnostic_row)
    result['status'] = 'partial'
    if kind is None:
        return []
    identity = hashlib.sha256((document['document_id'] + '\n' + full + '\n' + path).encode()).hexdigest()
    item = requirement('mauve_' + family + ':' + identity, kind=kind, role=role,
        source_refs=[document['artifact']['source_ref']], reason_code=full)
    if item not in result['requirements']:
        result['requirements'].append(item)
    return [item['requirement_id']]


def _inherit(result, records):
    if records is None:
        return
    for field in ('requirements', 'diagnostics'):
        for item in records[field]:
            if item not in result[field]:
                result[field].append(deepcopy(item))
    if records['requirements'] or records['diagnostics']:
        result['status'] = 'partial'


def _population(document, selection, local_partial):
    if not selection['row_indices'] and document['completeness'] == 'unknown':
        return 'unknown'
    if local_partial:
        return 'partial_selected'
    return 'complete_selected'


def _native_counts(row, selection, family, intervals, state, fields, *, evidence=(), ids=()):
    union = union_intervals(intervals)
    unique, total, multiple = interval_length(union), interval_length(intervals), multiplicity_bases(intervals)
    row['known_union_intervals'] = union
    known = bool(intervals) or state == 'complete_selected'
    numeric_state = 'available' if known else 'missing' if state == 'unknown' else 'truncated'
    for (key, unit), number in zip(fields, (unique, total, multiple, total - unique)):
        row[key] = _cell(selection, family, key, unit, number if known else None,
            state=numeric_state, evidence=evidence, ids=ids)
    return unique if known else None, multiple


def calculate_mauve_backbone_components(document: dict, *, selection: dict, inputs: dict | None) -> dict:
    """Measure explicitly selected backbone regions, conditional on multiplicity.

    The fraction is region-union length / verified staged member length. It is
    neither HMM posterior confidence nor a whole-genome completeness estimate.
    Input validation authenticates shapes; C/host own recorded source custody.
    """
    document = c.validate_mauve_backbone_document(document)
    selection = c.validate_mauve_backbone_selection(selection)
    if inputs is not None:
        inputs = validate_genome_alignment_inputs(inputs)
    result = _base(document, selection, 'backbone', 'coverage')
    known_members = {g['member'] for g in c._header_layout(document['columns']) if g['member'] is not None}
    c._Check('backbone').ok(all(m['index'] in known_members for m in selection['members']), 'selection_member_unknown')
    _inherit(result, inputs)
    bindings = {} if inputs is None else {(m['member']['namespace'], m['member']['index']): m for m in inputs['member_bindings']}
    placements = {m['index']: [] for m in selection['members']}
    unresolved = {m['index']: False for m in selection['members']}
    per_member_ids = {m['index']: [] for m in selection['members']}
    for index in selection['row_indices']:
        native = document['rows'][index]
        pairs = {p['member_index_0based']: p for p in native['pairs'] if p['member_index_0based'] is not None}
        row = {'row_index': index, 'selected_present_members': [], 'selected_absent_members': [],
            'unresolved_members': [], 'member_spans': []}
        selected_indices = {m['index'] for m in selection['members']}
        for pair in native['pairs']:
            if pair['member_index_0based'] not in selected_indices and pair['state'] in ('missing', 'incompatible'):
                _issue(result, document, 'backbone', 'row_incomplete' if pair['state'] == 'missing' else 'coordinate_invalid',
                    f'/rows/{index}/pairs/{pair["pair_index"]}', kind='output_bytes', role='genome_alignment_backbone')
        if native['extra_tokens']:
            _issue(result, document, 'backbone', 'count_conflict', f'/rows/{index}',
                kind='output_bytes', role='genome_alignment_backbone')
        for member in selection['members']:
            pair = pairs.get(member['index'])
            state = pair['state'] if pair is not None else 'missing'
            interval = pair['interval_0based_half_open'] if pair is not None else None
            strand = pair['strand'] if pair is not None else None
            ids = []
            if state == 'present':
                row['selected_present_members'].append(member); count = interval[1] - interval[0]
                numeric_state = 'available'
            elif state == 'absent_zero':
                row['selected_absent_members'].append(member); count = 0; numeric_state = 'available'
            else:
                row['unresolved_members'].append(member); count = None
                numeric_state = 'missing' if state == 'missing' else 'incompatible'
                ids = _issue(result, document, 'backbone', 'row_incomplete' if state == 'missing' else 'coordinate_invalid',
                    f'/rows/{index}/members/{member["index"]}', kind='output_bytes', role='genome_alignment_backbone')
                per_member_ids[member['index']].extend(ids)
            row['member_spans'].append({'member': member, 'state': state,
                'interval_0based_half_open': interval, 'strand': strand,
                'span_bases': _cell(selection, 'backbone', 'span_bases', 'nucleotides', count,
                    state=numeric_state, ids=ids), 'evidence': deepcopy(selection['evidence']), 'requirement_ids': ids})
        row['selected_member_count'] = _cell(selection, 'backbone', 'selected_member_count', 'members',
            len(row['selected_present_members']))
        row['selected_by_multiplicity'] = (None if row['unresolved_members'] else
            len(row['selected_present_members']) >= selection['minimum_selected_multiplicity'])
        if row['selected_by_multiplicity'] is None:
            for member in selection['members']:
                unresolved[member['index']] = True
                for span in row['member_spans']:
                    per_member_ids[member['index']].extend(span['requirement_ids'])
        elif row['selected_by_multiplicity']:
            for span in row['member_spans']:
                if span['state'] == 'present':
                    placements[span['member']['index']].append({'document_id': document['document_id'],
                        'row_index': index, 'member': span['member'], 'interval_0based_half_open': span['interval_0based_half_open'],
                        'strand': span['strand'], 'evidence': deepcopy(span['evidence'])})
        result['rows'].append(row)
    for member in selection['members']:
        index = member['index']; path = f'/coverage/{index}'
        unexplained = (selection['population_scope'] == 'all_observed_document_rows'
            and any(u['raw_line'].strip() for u in document['unparsed']))
        population = _population(document, selection, unresolved[index] or unexplained)
        ids = list(dict.fromkeys(per_member_ids[index]))
        if population != 'complete_selected':
            ids.extend(_issue(result, document, 'backbone', 'selection_population_incomplete', path,
                kind='output_bytes', role='genome_alignment_backbone'))
        row = {'member': member, 'placements': placements[index], 'population_state': population,
            'denominator_kind': selection['denominator'], 'evidence': deepcopy(selection['evidence']), 'requirement_ids': []}
        intervals = [p['interval_0based_half_open'] for p in placements[index]]
        count, overlap = _native_counts(row, selection, 'backbone', intervals, population,
            (('known_union_bases', 'nucleotides'), ('placement_bases', 'nucleotide_placements'),
             ('multiply_represented_bases', 'nucleotides'), ('excess_placement_bases', 'nucleotide_placements')), ids=ids)
        if overlap:
            _issue(result, document, 'backbone', 'overlapping_placement', path)
        binding = bindings.get((member['namespace'], index))
        ev = [] if binding is None else binding['evidence']
        length = None
        if selection['denominator'] == 'none':
            source_state = 'not_measured'
        elif binding is None or binding['state'] != 'bound' or binding['source_length'] is None:
            source_state = 'incompatible' if binding is not None and binding['state'] == 'conflicting' else 'missing'
            ids.extend(_issue(result, document, 'backbone', 'source_denominator_missing', path,
                kind='input_bytes', role='genome_alignment_staged_input'))
            if binding is not None:
                ids.extend(binding['requirement_ids'])
        else:
            length = binding['source_length']; source_state = 'available'
            for selected_row in result['rows']:
                for span in selected_row['member_spans']:
                    if span['member'] == member and span['state'] == 'present' and span['interval_0based_half_open'][1] > length:
                        source_state = 'incompatible'
                        ids.extend(_issue(result, document, 'backbone', 'source_span_outside_input',
                            f'/rows/{selected_row["row_index"]}/members/{index}', prefix='bvbrc_genome_alignment_',
                            kind='scientific_metadata', role='genome_alignment_staged_input'))
        denominator_state = 'available' if length is not None else source_state
        row['denominator_bases'] = _cell(selection, 'backbone', 'denominator_bases', 'nucleotides', length,
            state=denominator_state, evidence=ev, ids=ids)
        fraction_state = source_state if source_state != 'available' else 'available' if population == 'complete_selected' else 'truncated'
        if source_state == 'available' and length == 0:
            _issue(result, document, 'backbone', 'zero_denominator', path)
        row['coverage_fraction'] = _fraction(selection, 'backbone', 'coverage_fraction', count, length,
            state=fraction_state, evidence=ev, ids=ids)
        complement = complement_intervals(row['known_union_intervals'], length) if fraction_state == 'available' else None
        row['complement_intervals'] = complement
        row['complement_bases'] = _cell(selection, 'backbone', 'complement_bases', 'nucleotides',
            interval_length(complement) if complement is not None else None,
            state='available' if complement is not None else fraction_state, evidence=ev, ids=ids)
        row['evidence'] = _evidence(selection['evidence'], ev); row['requirement_ids'] = list(dict.fromkeys(ids))
        result['coverage'].append(row)
    return c.validate_mauve_backbone_components(result)


def _artifact_key(artifact):
    return tuple(artifact[k] for k in ('raw_artifact_ref', 'source_ref', 'sha256'))


def _join(document, native, selected_members, xmfa_document, associations, result):
    """Validate an explicit internal interval join; never infer block by index."""
    path = '/rows/' + str(native['row_index']); ids, ev = [], []
    joined_id = joined_index = width = None
    state, fraction_state = 'missing', 'missing'
    interval = native['native_interval_index_0based']
    if not c._available(interval, 0):
        ids.extend(_issue(result, document, 'bbcols', 'interval_ordinal_invalid', path,
            kind='output_bytes', role='genome_alignment_bbcols'))
        return 'conflicting', None, None, None, 'incompatible', ev, ids
    joins = [] if associations is None else [j for j in associations['bbcols_interval_joins']
        if j['bbcols_document_id'] == document['document_id'] and j['native_interval_index_0based'] == interval['value']]
    join = joins[0] if len(joins) == 1 else None
    if join is not None:
        state = join['state']; joined_id, joined_index = join['xmfa_document_id'], join['xmfa_block_index']
        ev = _evidence(ev, join['evidence']); ids.extend(join['requirement_ids'])
    if join is None or state != 'bound' or xmfa_document is None:
        ids.extend(_issue(result, document, 'bbcols', 'bbcols_block_unbound', path,
            kind='scientific_metadata', role='genome_alignment_interval_mapping'))
        if state == 'bound':
            state = 'missing'
        fraction_state = 'incompatible' if state == 'conflicting' else 'missing'
        return state, joined_id, joined_index, None, fraction_state, ev, list(dict.fromkeys(ids))
    artifacts = {_artifact_key(r['artifact']): r for r in associations['artifacts']}
    side = artifacts.get(_artifact_key(document['artifact'])); primary = artifacts.get(_artifact_key(xmfa_document['artifact']))
    if (side is None or primary is None or side['state'] != 'bound' or primary['state'] != 'bound'
            or side['document_id'] != document['document_id'] or primary['document_id'] != xmfa_document['document_id']
            or joined_id != xmfa_document['document_id'] or joined_index >= len(xmfa_document['blocks'])):
        ids.extend(_issue(result, document, 'bbcols', 'interval_join_conflict', path,
            prefix='bvbrc_genome_alignment_', kind='scientific_metadata', role='genome_alignment_interval_mapping'))
        return 'conflicting', joined_id, joined_index, None, 'incompatible', ev, list(dict.fromkeys(ids))
    block = xmfa_document['blocks'][joined_index]
    width = block['alignment_column_count']
    fraction_state = 'available' if block['completeness'] == 'complete' else 'truncated'
    if width is None:
        fraction_state = 'incompatible'
    native_range = native['columns_0based_half_open']
    if native_range is None or width is None or native_range[1] > width:
        ids.extend(_issue(result, document, 'bbcols', 'bbcols_column_outside_block', path,
            kind='output_bytes', role='genome_alignment_bbcols'))
        state = 'conflicting'; fraction_state = 'incompatible'
    member_joins = {(_artifact_key(j['artifact']), j['member']['namespace'], j['member']['index']): j
        for j in associations['native_member_joins']}
    selected_indices = {m['index'] for m in selected_members}
    for token in native['native_member_indices_0based']:
        if not c._available(token, 0):
            continue
        index = token['value']
        side_join = member_joins.get((_artifact_key(document['artifact']), c.SIDECAR_NAMESPACE, index))
        primary_join = member_joins.get((_artifact_key(xmfa_document['artifact']), 'mauve1_member_1based', index + 1))
        missing = any(j is None or j['state'] not in ('bound', 'conflicting') for j in (side_join, primary_join))
        conflict = any(j is not None and j['state'] == 'conflicting' for j in (side_join, primary_join))
        if not missing and not conflict:
            conflict = side_join['input_member'] != primary_join['input_member']
            records = [r for r in block['records'] if c._available(r['member_number'], 1) and r['member_number']['value'] == index + 1]
            conflict = conflict or len(records) != 1 or records[0]['coordinate_state'] != 'present'
        for j in (side_join, primary_join):
            if j is not None:
                ev = _evidence(ev, j['evidence']); ids.extend(j['requirement_ids'])
        if missing or conflict:
            ids.extend(_issue(result, document, 'bbcols', 'member_join_conflict' if conflict else 'member_join_missing',
                path + '/members/' + str(index), prefix='bvbrc_genome_alignment_',
                kind='scientific_metadata', role='genome_alignment_member_mapping'))
            if conflict:
                state = 'conflicting'; fraction_state = 'incompatible'
            elif index in selected_indices and fraction_state != 'incompatible':
                state = 'missing'; fraction_state = 'missing'
    if fraction_state == 'truncated':
        ids.extend(_issue(result, document, 'bbcols', 'selection_population_incomplete', path,
            kind='output_bytes', role='genome_alignment_primary'))
    return state, joined_id, joined_index, width, fraction_state, ev, list(dict.fromkeys(ids))


def calculate_mauve_bbcols_components(document: dict, *, selection: dict,
    xmfa_document: dict | None, associations: dict | None) -> dict:
    """Measure native columns; optional fractions need verified explicit joins.

    Native widths and interval unions survive absent or incompatible external
    mappings. A syntactically empty sidecar never becomes measured zero coverage.
    """
    document = c.validate_mauve_bbcols_document(document)
    selection = c.validate_mauve_bbcols_selection(selection)
    if xmfa_document is not None:
        xmfa_document = validate_xmfa_document(xmfa_document)
    if associations is not None:
        associations = validate_genome_alignment_associations(associations)
    result = _base(document, selection, 'bbcols', 'intervals'); _inherit(result, associations)
    groups, row_details = {}, {}
    unknown_interval = False
    if not selection['row_indices'] and document['completeness'] == 'unknown':
        _issue(result, document, 'bbcols', 'selection_population_incomplete', '/selection',
            kind='output_bytes', role='genome_alignment_bbcols')
    for index in selection['row_indices']:
        native = document['rows'][index]; tokens = native['native_member_indices_0based']
        counts = Counter(t['value'] for t in tokens if c._available(t, 0))
        unresolved = [t for t in tokens if not c._available(t, 0) or counts[t['value']] > 1]
        present = [m for m in selection['members'] if m['index'] in counts]
        eligible = None if unresolved or not tokens else len(present) >= selection['minimum_selected_multiplicity']
        interval_token = native['native_interval_index_0based']; width_token = native['native_column_count']
        interval = interval_token['value'] if c._available(interval_token, 0) else None
        if interval is None:
            unknown_interval = True
        state, joined_id, joined_index, width, fraction_state, ev, ids = _join(
            document, native, present if eligible else [], xmfa_document, associations, result)
        if native['state'] != 'parsed':
            ids += _issue(result, document, 'bbcols', 'row_incomplete' if native['state'] == 'incomplete' else 'coordinate_invalid',
                f'/rows/{index}', kind='output_bytes', role='genome_alignment_bbcols')
        value = width_token['value'] if c._available(width_token, 1) else None
        count_state = 'available' if value is not None else 'missing' if width_token is None else 'incompatible'
        row = {'row_index': index, 'native_interval_index_0based': interval,
            'selected_present_members': present, 'unresolved_member_tokens': deepcopy(unresolved),
            'selected_member_count': _cell(selection, 'bbcols', 'selected_member_count', 'members', len(present)),
            'selected_by_multiplicity': eligible,
            'column_count': _cell(selection, 'bbcols', 'column_count', 'columns', value, state=count_state,
                origin='native_observation', ids=ids), 'xmfa_document_id': joined_id, 'xmfa_block_index': joined_index,
            'join_state': state, 'evidence': _evidence(selection['evidence'], ev), 'requirement_ids': list(dict.fromkeys(ids))}
        result['rows'].append(row)
        row_details[index] = (native, width, fraction_state)
        if interval is not None:
            groups.setdefault(interval, []).append(row)
    for interval, rows in groups.items():
        path = '/intervals/' + str(interval)
        native_rows = [row_details[r['row_index']][0] for r in rows]
        contributing = [r for r in rows if r['selected_by_multiplicity'] is True
            and row_details[r['row_index']][0]['state'] == 'parsed']
        intervals = [row_details[r['row_index']][0]['columns_0based_half_open'] for r in contributing]
        partial = unknown_interval or any(n['state'] != 'parsed' for n in native_rows)
        population = _population(document, selection, partial)
        ids = list(dict.fromkeys(i for r in rows for i in r['requirement_ids']))
        ev = _evidence(*(r['evidence'] for r in rows))
        if population != 'complete_selected':
            ids += _issue(result, document, 'bbcols', 'selection_population_incomplete', path,
                kind='output_bytes', role='genome_alignment_bbcols')
        row = {'native_interval_index_0based': interval,
            'contributing_row_indices': [r['row_index'] for r in contributing], 'population_state': population,
            'xmfa_document_id': None, 'xmfa_block_index': None, 'evidence': ev, 'requirement_ids': []}
        unique, overlap = _native_counts(row, selection, 'bbcols', intervals, population,
            (('union_columns', 'columns'), ('column_placements', 'column_placements'),
             ('multiply_represented_columns', 'columns'), ('excess_column_placements', 'column_placements')), evidence=ev, ids=ids)
        if overlap:
            _issue(result, document, 'bbcols', 'overlapping_placement', path)
        references = {(r['xmfa_document_id'], r['xmfa_block_index']) for r in rows}
        if len(references) == 1:
            row['xmfa_document_id'], row['xmfa_block_index'] = next(iter(references))
        widths = {row_details[r['row_index']][1] for r in rows}
        width = next(iter(widths)) if len(widths) == 1 else None
        states = [row_details[r['row_index']][2] for r in rows]
        if not selection['calculate_bound_block_fraction']:
            width, fraction_state = None, 'not_measured'
        elif 'incompatible' in states or len(references) != 1 or len(widths) != 1:
            fraction_state = 'incompatible'
        elif 'missing' in states:
            fraction_state = 'missing'
        elif 'truncated' in states or population != 'complete_selected':
            fraction_state = 'truncated'
        else:
            fraction_state = 'available'
        row['bound_block_width'] = _cell(selection, 'bbcols', 'bound_block_width', 'columns', width,
            state='available' if width is not None else fraction_state, evidence=ev, ids=ids)
        row['selected_block_fraction'] = _fraction(selection, 'bbcols', 'selected_block_fraction', unique, width,
            state=fraction_state, evidence=ev, ids=ids)
        if width == 0 and fraction_state == 'available':
            _issue(result, document, 'bbcols', 'zero_denominator', path)
        row['requirement_ids'] = list(dict.fromkeys(ids)); result['intervals'].append(row)
    return c.validate_mauve_bbcols_components(result)


__all__ = ['calculate_mauve_backbone_components', 'calculate_mauve_bbcols_components']
