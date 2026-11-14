"""Pure numerical measurements of explicitly selected native Mauve v4 segments.

No interval reconstruction is attempted. Coverage uses only actual selected
residue positions. Coordinates without characters never establish identity.
Source length is a staged-input denominator, not a whole-genome census.
"""
from copy import deepcopy
import hashlib

from . import mauve_v4_format_contracts as f
from . import mauve_v4_calculation_contracts as c
from .bvbrc_alignment_values import numeric_cell, diagnostic, requirement
from .bvbrc_genome_alignment_input_contracts import validate_genome_alignment_inputs
from .xmfa_calculation_contracts import (COMPLEMENT, union_intervals, interval_length,
    multiplicity_bases, complement_intervals)


def _evidence(*groups):
    result = []
    for group in groups:
        for row in group:
            if row not in result: result.append(deepcopy(row))
    return result


def _cell(selection, field, unit, value=None, *, state='available', origin='calculated',
          numerator=None, denominator=None, evidence=(), requirement_ids=()):
    return numeric_cell(value, state=state, unit=unit, origin=origin,
        population_id=selection['population_id'], method_id='mauve_v4_' + field + '_v1',
        numerator=numerator, denominator=denominator, evidence=_evidence(selection['evidence'], evidence),
        uncertainty=None, requirement_ids=list(dict.fromkeys(requirement_ids)))


def _issue(result, code, path, *, needed=False, kind='scientific_metadata', role='genome_alignment_primary'):
    full = code if code.startswith('bvbrc_genome_alignment_') else 'mauve_v4_' + code
    c.require(full in c.CODES)
    item = diagnostic(full, path=path)
    if item not in result['diagnostics']: result['diagnostics'].append(item)
    result['status'] = 'partial'
    if not needed: return None
    rid = 'mauve_v4_requirement:' + hashlib.sha256((result['document_id'] + '\0' + full + '\0' + path).encode()).hexdigest()
    req = requirement(rid, kind=kind, role=role, reason_code=full)
    if req not in result['requirements']: result['requirements'].append(req)
    return rid


def _width(segment):
    token = segment['native_width'] if segment['kind'] == 'gapped_rows' else segment['native_length']
    return token['value'] if f.available(token) else None


def _selection(document, selection):
    selected = c.validate_mauve_v4_selection(selection)
    c.require(selected['document_id'] == document['document_id'], 'selection_document_conflict')
    count = f.scalar(document['metadata'], 'sequence_count')
    observed_members = {r['member_index_token']['value'] for r in document['metadata']
                        if f.available(r['member_index_token'])}
    observed_members.update(i for interval in document['intervals'] for s in interval['segments']
                            for i in range(len(s['native_starts'])))
    for m in selected['members']:
        c.require(m['index'] < count if count is not None else m['index'] in observed_members,
                  'selection_member_unknown')
    records = {(i['interval_index'], s['segment_index']): s for i in document['intervals'] for s in i['segments']}
    for row in selected['segments']:
        key = row['interval_index'], row['segment_index']
        c.require(key in records, 'selection_record_unknown')
        width = _width(records[key]); ranges = row['column_ranges_0based_half_open']
        c.require(not ranges or width is not None and all(end <= width for start, end in ranges),
                  'selection_column_outside_record')
    if selected['population_scope'] == 'all_observed_document_segments':
        c.require({(r['interval_index'], r['segment_index']) for r in selected['segments']} == set(records),
                  'selection_population_incomplete')
        for row in selected['segments']:
            width = _width(records[row['interval_index'], row['segment_index']])
            c.require(union_intervals(row['column_ranges_0based_half_open']) == ([[0, width]] if width else []),
                      'selection_population_incomplete')
    return selected, records


def _source(document, inputs, member, result):
    """Inspect C's validated binding, retaining native/path and same-run limits."""
    path = '/coverage/' + str(member['index']); ev, ids = [], []
    bindings = [] if inputs is None else [b for b in inputs['member_bindings'] if b['member'] == member]
    if not bindings or bindings[0]['state'] != 'bound':
        state = 'incompatible' if bindings and bindings[0]['state'] == 'conflicting' else 'missing'
        return {'length': None, 'parts': None, 'state': state, 'evidence': ev, 'requirement_ids': ids}
    binding = bindings[0]; ev = binding['evidence']; ids = list(binding['requirement_ids'])
    files = {row['file_id']: row for row in inputs['files']}
    native_path = f.file_token(document['metadata'], member['index'])
    parts = []
    for part in binding['components']:
        file = files[part['file_id']]
        if native_path is None or file['native_path_token'] != native_path:
            ids.append(_issue(result, 'bvbrc_genome_alignment_native_path_missing' if native_path is None else
                'bvbrc_genome_alignment_native_path_conflict', path, needed=True,
                kind='input_metadata', role='genome_alignment_staged_input'))
            return {'length': None, 'parts': None, 'state': 'incompatible', 'evidence': ev, 'requirement_ids': ids}
        record = next(r for r in file['records'] if r['record_id'] == part['record_id'])
        parts.append((part, record['sequence']))
        ev = _evidence(ev, file['path_evidence'], file['same_run_evidence'])
    return {'length': binding['source_length'], 'parts': parts, 'state': 'available', 'evidence': ev, 'requirement_ids': ids}


def _extract(source, span, strand):
    if source['parts'] is None: return None
    left, right = span; cursor = left; pieces = []
    for part, sequence in source['parts']:
        a, b = part['member_interval_0based_half_open']; x, y = max(left, a), min(right, b)
        if x >= y: continue
        if x != cursor: return None
        offset = part['record_interval_0based_half_open'][0]
        pieces.append(sequence[offset + x - a:offset + y - a]); cursor = y
    if cursor != right: return None
    result = ''.join(pieces)
    return result if strand == '+' else result.translate(COMPLEMENT)[::-1]


def _placements(ref, member, span, strand, sequence, ranges, evidence):
    if sequence is None:
        runs = [[span[0] + a, span[0] + b] if strand == '+' else [span[1] - b, span[1] - a] for a, b in ranges]
    else:
        runs, q, ri = [], 0, 0
        for column, symbol in enumerate(sequence):
            while ri < len(ranges) and column >= ranges[ri][1]: ri += 1
            selected = ri < len(ranges) and ranges[ri][0] <= column < ranges[ri][1]
            if symbol != '-':
                if selected:
                    position = span[0] + q if strand == '+' else span[1] - 1 - q
                    if runs and (runs[-1][1] == position if strand == '+' else runs[-1][0] == position + 1):
                        if strand == '+': runs[-1][1] += 1
                        else: runs[-1][0] -= 1
                    else: runs.append([position, position + 1])
                q += 1
    return [{'record': deepcopy(ref), 'member': deepcopy(member), 'interval_0based_half_open': run,
             'strand': strand, 'evidence': deepcopy(evidence)} for run in runs if run[0] < run[1]]


def _member_segment(document, segment, chosen, member, source, selection, result):
    ref = {'document_id': document['document_id'], 'interval_index': chosen['interval_index'],
           'segment_index': chosen['segment_index']}
    path = '/member_segments/' + str(len(result['member_segments']))
    width, ranges = _width(segment), chosen['column_ranges_0based_half_open']
    selected_count = interval_length(ranges); mi = member['index']; starts = segment['native_starts']
    token = starts[mi] if mi < len(starts) else None
    gapped = segment['kind'] == 'gapped_rows'
    row = next((r for r in segment['sequence_rows'] if r['member_index_0based'] == mi), None) if gapped else None
    sequence = None; origin = 'unavailable'; span = None; strand = None; ids = []
    comparison = 'not_checked'; source_bad = source['state'] == 'incompatible'; ev = source['evidence']
    if f.scalar(document['metadata'], 'format_version') != 4:
        state = 'incompatible'
        ids.append(_issue(result, 'metadata_conflict', path, needed=True, kind='output_bytes'))
    elif gapped and segment['completeness'] != 'complete':
        incomplete = (segment['expected_member_count'] is None or
                      len(segment['sequence_rows']) < segment['expected_member_count'])
        state = 'missing' if incomplete else 'incompatible'
        ids.append(_issue(result, 'missing_sequence_row' if incomplete else 'row_incomplete', path,
                          needed=True, kind='output_bytes'))
    elif width is None or not f.available(token):
        state = 'missing' if token is None else 'incompatible'
        ids.append(_issue(result, 'coordinate_invalid', path, needed=True, kind='output_bytes'))
    elif segment['completeness'] != 'complete':
        state = 'incompatible'; ids.append(_issue(result, 'header_member_conflict', path, needed=True, kind='output_bytes'))
    elif token['value'] == 0:
        state, comparison = 'absent_zero', 'not_applicable'
        if gapped: sequence, origin = row['sequence'], 'native_rows'
    else:
        state = 'present'; strand = '+' if token['value'] > 0 else '-'
        sequence = row['sequence'] if gapped else None
        residues = len(sequence.replace('-', '')) if gapped else width
        span = [abs(token['value']) - 1, abs(token['value']) - 1 + residues]
        extracted = _extract(source, span, strand)
        if source['parts'] is not None and extracted is None:
            source_bad = True
            ids.append(_issue(result, 'bvbrc_genome_alignment_source_span_outside_input', path,
                needed=True, kind='input_bytes', role='genome_alignment_staged_input'))
        if gapped:
            origin = 'native_rows'
            if extracted is not None:
                comparison = 'match' if sequence.replace('-', '').upper() == extracted.upper() else 'mismatch'
                if comparison == 'mismatch':
                    source_bad = True
                    ids.append(_issue(result, 'bvbrc_genome_alignment_source_sequence_mismatch', path,
                        needed=True, kind='input_bytes', role='genome_alignment_staged_input'))
        elif extracted is not None:
            sequence, origin, comparison = extracted, 'source_extracted', 'not_applicable'
        else:
            ids.append(_issue(result, 'source_symbols_missing', path, needed=True,
                kind='input_bytes', role='genome_alignment_staged_input'))
    numbers = {name: None for name in c.MEMBER_COUNTS[2:]}
    numeric_state = 'truncated' if state == 'missing' else 'incompatible' if state == 'incompatible' else 'missing'
    if sequence is not None:
        symbols = ''.join(sequence[a:b] for a, b in ranges)
        if selection['case_policy'] == 'uppercase': symbols = symbols.upper()
        numbers.update(selected_nongap_count=len(symbols) - symbols.count('-'), selected_gap_count=symbols.count('-'),
            selected_canonical_count=sum(s in 'ACGT' for s in symbols), selected_ambiguity_count=sum(s in 'RYSWKMBDHVN' for s in symbols),
            selected_other_count=sum(s not in 'ACGTRYSWKMBDHVN-' for s in symbols))
    elif state == 'present':
        numbers.update(selected_nongap_count=selected_count, selected_gap_count=0)
    elif state == 'absent_zero':
        numbers['selected_nongap_count'] = 0; numeric_state = 'not_measured'
    output = {'segment': ref, 'member': deepcopy(member), 'state': state, 'native_start': deepcopy(token),
        'strand': strand, 'native_interval_0based_half_open': span, 'symbols_origin': origin,
        'aligned_sequence': sequence, 'alignment_columns': _cell(selection, 'alignment_columns', 'columns', width,
            state='available' if width is not None else 'incompatible'),
        'selected_column_count': _cell(selection, 'selected_column_count', 'columns', selected_count),
        'source_comparison': comparison, 'evidence': ev, 'requirement_ids': ids}
    for name, number in numbers.items():
        output[name] = _cell(selection, name, 'characters', number,
                            state='available' if number is not None else numeric_state, evidence=ev, requirement_ids=ids)
    placements = _placements(ref, member, span, strand, sequence, ranges, ev) if state == 'present' else []
    return output, placements, source_bad


def _pair(result, selection, chosen, pair, rows):
    a, b = (rows[pair[k]['index']] for k in ('member_a', 'member_b'))
    path = '/pair_segments/' + str(len(result['pair_segments']))
    state = ('incompatible' if 'incompatible' in (a['state'], b['state']) else
             'incomplete' if 'missing' in (a['state'], b['state']) else
             'not_coobserved' if 'absent_zero' in (a['state'], b['state']) else
             'missing_symbols' if a['aligned_sequence'] is None or b['aligned_sequence'] is None else 'available')
    ids = list(dict.fromkeys(a['requirement_ids'] + b['requirement_ids']))
    if state != 'available':
        _issue(result, 'pair_not_coobserved' if state == 'not_coobserved' else
               'source_symbols_missing' if state == 'missing_symbols' else 'selection_population_incomplete', path)
    counts = dict.fromkeys(c.PAIR_COUNTS, 0)
    if state == 'available':
        for start, end in chosen['column_ranges_0based_half_open']:
            for x, y in zip(a['aligned_sequence'][start:end], b['aligned_sequence'][start:end]):
                if selection['case_policy'] == 'uppercase': x, y = x.upper(), y.upper()
                field = ('both_gap' if x == y == '-' else 'a_only_gap' if x == '-' else 'b_only_gap' if y == '-' else
                         'identical_canonical' if x in 'ACGT' and y == x else 'substitutions' if x in 'ACGT' and y in 'ACGT' else 'ambiguous_or_other')
                counts[field] += 1
        counts['comparable_canonical'] = counts['identical_canonical'] + counts['substitutions']
    ns = {'available': 'available', 'incompatible': 'incompatible', 'incomplete': 'truncated',
          'not_coobserved': 'not_measured', 'missing_symbols': 'missing'}[state]
    ev = _evidence(a['evidence'], b['evidence'])
    cells = {name: _cell(selection, name, 'columns', value if state == 'available' else None,
                        state=ns, evidence=ev, requirement_ids=ids) for name, value in counts.items()}
    n, d = (counts['identical_canonical'], counts['comparable_canonical']) if state == 'available' else (None, None)
    cells['identity_fraction'] = _cell(selection, 'identity_fraction', 'fraction', n / d if d else None,
        state=ns if state != 'available' else 'available' if d else 'not_measured', numerator=n, denominator=d,
        evidence=ev, requirement_ids=ids)
    if state == 'available' and d == 0: _issue(result, 'zero_denominator', path)
    return {'segment': deepcopy(a['segment']), 'pair': deepcopy(pair), 'state': state,
            'counts': cells, 'evidence': ev, 'requirement_ids': ids}


def calculate_mauve_v4_segments(document: dict, *, selection: dict, inputs: dict | None) -> dict:
    """Calculate explicit selected columns and placements from retained values.

    Count units are columns, characters, nucleotides, or nucleotide placements.
    Canonical identity divides identical A/C/G/T columns by comparable A/C/G/T
    columns. Coverage divides unique selected native positions by the separately
    selected denominator. No denominator means fractions are not measured.
    """
    document = f.validate_mauve_v4_document(document)
    selection, records = _selection(document, selection)
    if inputs is not None:
        inputs = validate_genome_alignment_inputs(inputs)
    result = {'schema_version': 'mauve_v4_segment_components_v1', 'document_id': document['document_id'],
        'status': 'ok', 'selection': selection, 'member_segments': [], 'pair_segments': [], 'coverage': [],
        'requirements': deepcopy(inputs['requirements']) if inputs is not None else [],
        'diagnostics': deepcopy(inputs['diagnostics']) if inputs is not None else []}
    if result['requirements'] or result['diagnostics']: result['status'] = 'partial'
    all_scope_partial = (selection['population_scope'] == 'all_observed_document_segments'
                         and document['completeness'] != 'complete')
    if all_scope_partial: _issue(result, 'selection_population_incomplete', '/selection')
    sources = {m['index']: _source(document, inputs, m, result) for m in selection['members']}
    coverage = {m['index']: {'placements': [], 'partial': all_scope_partial, 'incompatible': False,
                            'source_bad': False, 'ids': []}
                for m in selection['members']}
    for chosen in selection['segments']:
        segment = records[chosen['interval_index'], chosen['segment_index']]; rows = {}
        for member in selection['members']:
            mi = member['index']
            output, placements, source_bad = _member_segment(document, segment, chosen, member, sources[mi], selection, result)
            result['member_segments'].append(output); rows[mi] = output
            coverage[mi]['placements'].extend(placements)
            coverage[mi]['partial'] |= output['state'] in ('missing', 'incompatible')
            coverage[mi]['incompatible'] |= output['state'] == 'incompatible'
            coverage[mi]['source_bad'] |= source_bad
            coverage[mi]['ids'].extend(output['requirement_ids'])
        for pair in selection['pairs']: result['pair_segments'].append(_pair(result, selection, chosen, pair, rows))
    for member in selection['members']:
        mi = member['index']; work, source = coverage[mi], sources[mi]
        path = '/coverage/' + str(len(result['coverage']))
        spans = [p['interval_0based_half_open'] for p in work['placements']]
        union = union_intervals(spans); count, total = interval_length(union), interval_length(spans)
        multiple = multiplicity_bases(spans); ids = list(dict.fromkeys(work['ids'] + source['requirement_ids']))
        kind = selection['denominator']; length = None; denominator_state = 'not_measured'
        if kind == 'native_declared_length':
            length = f.scalar(document['metadata'], 'sequence_length', mi)
            declared = [r for r in document['metadata'] if r['kind'] == 'sequence_length'
                        and f.available(r['member_index_token']) and r['member_index_token']['value'] == mi]
            denominator_state = 'available' if length is not None else 'incompatible' if declared else 'missing'
        elif kind == 'validated_staged_length':
            length, denominator_state = source['length'], source['state']
        if kind != 'none' and length is None:
            ids.append(_issue(result, 'source_denominator_missing', path, needed=True,
                kind='output_bytes' if kind == 'native_declared_length' else 'input_metadata',
                role='genome_alignment_primary' if kind == 'native_declared_length' else 'genome_alignment_staged_input'))
        population = 'partial_selected' if work['partial'] else 'complete_selected'
        fraction_state = denominator_state
        if kind != 'none':
            if denominator_state == 'incompatible' or work['incompatible']:
                fraction_state = 'incompatible'
            elif length is not None and any(end > length for start, end in union):
                fraction_state = 'incompatible'
                _issue(result, 'coordinate_invalid', path)
            elif kind == 'validated_staged_length' and work['source_bad']: fraction_state = 'incompatible'
            elif work['partial']: fraction_state = 'truncated'
            elif denominator_state == 'available': fraction_state = 'available' if length else 'not_measured'
        good = kind != 'none' and length is not None and fraction_state in ('available', 'not_measured') and not work['partial']
        complement = complement_intervals(union, length) if good else None
        ev = source['evidence'] if kind == 'validated_staged_length' else selection['evidence']
        output = {'member': deepcopy(member), 'placements': work['placements'], 'known_union_intervals': union,
            'denominator_kind': kind, 'denominator_bases': _cell(selection, 'denominator_bases', 'nucleotides', length,
                state=denominator_state, origin='native_observation' if kind == 'native_declared_length' else 'calculated',
                evidence=ev, requirement_ids=ids),
            'coverage_fraction': _cell(selection, 'coverage_fraction', 'fraction', count / length if fraction_state == 'available' else None,
                state=fraction_state, numerator=count, denominator=length, evidence=ev, requirement_ids=ids),
            'complement_intervals': complement, 'complement_bases': _cell(selection, 'complement_bases', 'nucleotides',
                interval_length(complement) if good else None, state='available' if good else fraction_state,
                evidence=ev, requirement_ids=ids),
            'population_state': population, 'evidence': ev, 'requirement_ids': ids}
        for name, number in (('known_union_bases', count), ('placement_bases', total),
                             ('multiply_represented_bases', multiple), ('excess_placement_bases', total - count)):
            output[name] = _cell(selection, name, 'nucleotide_placements' if name in ('placement_bases', 'excess_placement_bases') else 'nucleotides', number)
        if multiple: _issue(result, 'overlapping_placement', path)
        if kind != 'none' and length == 0 and fraction_state == 'not_measured': _issue(result, 'zero_denominator', path)
        result['coverage'].append(output)
    return c.validate_mauve_v4_components(result)


__all__ = ['calculate_mauve_v4_segments']
