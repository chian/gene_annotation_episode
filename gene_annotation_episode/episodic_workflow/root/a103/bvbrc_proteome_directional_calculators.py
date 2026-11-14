"""Pure measurements of the complete displayed legacy BLASTP population.

Native measurements stay in the observed sheet. This module calculates from
that saved sheet and explicit parameters, without acquiring or parsing bytes,
choosing work, changing historical data, or assigning annotation credit.
"""
from copy import deepcopy
from decimal import Decimal
import json

from .bvbrc_proteome_directional_numerical_contracts import (
    DirectionalNumericalContractError, canonical_sheet_sha256,
    validate_directional_numerical,
)
from .bvbrc_proteome_directional_geometry import (
    calculate_protein_block, inspect_protein_correspondence,
    union_position_intervals,
)


TRACE_UNITS = {
    'alignment_columns': 'alignment_column',
    'paired_columns': 'paired_column',
    'displayed_symbol_identical_pairs': 'paired_column',
    'displayed_symbol_nonidentical_pairs': 'paired_column',
    'resolved_amino_acid_pairs': 'paired_column',
    'resolved_amino_acid_identical_pairs': 'paired_column',
    'resolved_amino_acid_substituted_pairs': 'paired_column',
    'unresolved_symbol_pairs': 'paired_column',
    'stop_containing_pairs': 'paired_column',
    'query_gap_columns': 'alignment_column',
    'subject_gap_columns': 'alignment_column',
    'query_gap_runs': 'gap_run', 'subject_gap_runs': 'gap_run',
    'query_non_gap_symbols': 'displayed_position',
    'subject_non_gap_symbols': 'displayed_position',
}
COVERAGE_FIELDS = tuple(side + '_' + basis + '_union'
    for side in ('query', 'subject')
    for basis in ('reported_interval', 'trace_occupied', 'trace_paired'))
COMPATIBLE_FIELDS = {
    'identical_symbol_pairs': None,
    'resolved_pairs': ('resolved_identical', 'resolved_substituted'),
    'resolved_identical_pairs': ('resolved_identical',),
    'resolved_substituted_pairs': ('resolved_substituted',),
    'unresolved_pairs': ('unresolved_pair',),
    'stop_containing_pairs': ('stop_containing_pair',),
}
_SEVERITY = {'value': 0, 'undefined': 1, 'missing': 2, 'invalid': 3, 'conflict': 4}


def _unique(values):
    result, seen = [], set()
    for value in values:
        encoded = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        if encoded not in seen:
            seen.add(encoded)
            result.append(deepcopy(value))
    return result


def _prefix(key):
    path = ''
    for name, array in (('query_ordinal', 'queries'), ('subject_ordinal', 'subjects'),
                        ('hsp_ordinal', 'hsps'), ('block_ordinal', 'traceback_blocks')):
        if name in key:
            path += '/' + array + '/' + str(key[name])
    return path


def _ref(key, suffix=''):
    return {'report_ordinal': key['report_ordinal'], 'pointer': _prefix(key) + suffix}


def _length_ref(key, side):
    names = ('report_ordinal', 'query_ordinal') + (('subject_ordinal',) if side == 'subject' else ())
    return _ref({n: key[n] for n in names}, '/length')


def _issue(code, fields=(), *, key=None, argument_pointer=None):
    hsp = ({n: key[n] for n in ('report_ordinal', 'query_ordinal', 'subject_ordinal', 'hsp_ordinal')}
        if key is not None and 'hsp_ordinal' in key else None)
    return {'code': code, 'fields': _unique(fields), 'columns': [],
        'hsps': [] if hsp is None else [hsp], 'argument_pointer': argument_pointer}


def _cell(value, unit, inputs=(), *, state='value', reasons=()):
    return {'state': state, 'value': value, 'unit': unit, 'inputs': _unique(inputs),
        'reasons': list(dict.fromkeys(reasons)), 'uncertainty': None}


def _unavailable(unit, inputs=(), *, state='missing', reasons=()):
    return _cell(None, unit, inputs, state=state, reasons=reasons)


def _operand_inputs(*cells):
    return _unique(ref for cell in cells for ref in cell['inputs'])


def _worst(cells, default='missing'):
    states = [cell['state'] for cell in cells if cell['state'] != 'value']
    return max(states, key=_SEVERITY.__getitem__) if states else default


def _ratio(numerator, denominator, inputs, parameters, *, empty_reason='zero_paired_population'):
    if denominator == 0:
        return _unavailable('fraction', inputs, state='undefined', reasons=[empty_reason])
    if numerator < 0 or denominator < 0 or numerator > denominator:
        return _unavailable('fraction', inputs, state='invalid', reasons=['count_exceeds_denominator'])
    places = parameters['ratio_decimal_places']
    # Integer division avoids inherited Decimal precision, exponent bounds and
    # traps. The exact rational remains saved separately from its rendering.
    scale = 10 ** places
    quotient, remainder = divmod(numerator * scale, denominator)
    twice = remainder * 2
    if twice > denominator or twice == denominator and quotient % 2:
        quotient += 1
    rendered = str(quotient) if not places else f'{quotient // scale}.{quotient % scale:0{places}d}'
    return _cell({'numerator': numerator, 'denominator': denominator,
        'decimal': rendered}, 'fraction', inputs)


def _ratio_cells(numerator, denominator, parameters, *, empty_reason='zero_paired_population'):
    inputs = _operand_inputs(numerator, denominator)
    if numerator['state'] != 'value' or denominator['state'] != 'value':
        return _unavailable('fraction', inputs, state=_worst([numerator, denominator]),
            reasons=numerator['reasons'] + denominator['reasons'])
    return _ratio(numerator['value'], denominator['value'], inputs, parameters, empty_reason=empty_reason)


def _trace_fractions(counts, parameters):
    qgap, sgap = counts['query_gap_columns'], counts['subject_gap_columns']
    if qgap['state'] == sgap['state'] == 'value':
        gaps = _cell(qgap['value'] + sgap['value'], 'alignment_column', _operand_inputs(qgap, sgap))
    else:
        gaps = _unavailable('alignment_column', _operand_inputs(qgap, sgap),
            state=_worst([qgap, sgap]), reasons=qgap['reasons'] + sgap['reasons'])
    return {
        'trace_symbol_identity_over_columns': _ratio_cells(counts['displayed_symbol_identical_pairs'], counts['alignment_columns'], parameters),
        'trace_symbol_identity_over_pairs': _ratio_cells(counts['displayed_symbol_identical_pairs'], counts['paired_columns'], parameters),
        'trace_resolved_amino_acid_identity': _ratio_cells(counts['resolved_amino_acid_identical_pairs'], counts['resolved_amino_acid_pairs'], parameters, empty_reason='zero_resolved_population'),
        'trace_resolved_pair_fraction': _ratio_cells(counts['resolved_amino_acid_pairs'], counts['paired_columns'], parameters),
        'trace_unresolved_pair_fraction': _ratio_cells(counts['unresolved_symbol_pairs'], counts['paired_columns'], parameters),
        'trace_gap_fraction': _ratio_cells(gaps, counts['alignment_columns'], parameters),
    }


def _native_count_ratio(hsp, prefix, parameters):
    key = hsp['key']
    count, denominator = hsp[prefix + '_count'], hsp[prefix + '_denominator']
    inputs = [_ref(key, '/' + prefix + '_count'), _ref(key, '/' + prefix + '_denominator')]
    reasons = []
    if 'missing' in (count['state'], denominator['state']):
        reasons.append('missing_native_count')
    if 'invalid' in (count['state'], denominator['state']):
        reasons.append('invalid_native_count')
    n = count['value'] if count['state'] == 'present' else None
    d = denominator['value'] if denominator['state'] == 'present' else None
    if d == 0:
        reasons.append('zero_native_denominator')
    if n is not None and d is not None and n > d:
        reasons.append('count_exceeds_denominator')
    if reasons:
        return _unavailable('fraction', inputs,
            state='invalid' if any(r != 'missing_native_count' for r in reasons) else 'missing', reasons=reasons)
    return _ratio(n, d, inputs, parameters)


def _reported(hsp, parameters):
    identity, positive, gaps = [_native_count_ratio(hsp, prefix, parameters)
        for prefix in ('identity', 'positive', 'gap')]
    if gaps['state'] == 'value':
        pair_count = gaps['value']['denominator'] - gaps['value']['numerator']
        paired = _cell(pair_count, 'paired_column', gaps['inputs'])
    else:
        paired = _unavailable('paired_column', gaps['inputs'], state=gaps['state'], reasons=gaps['reasons'])
    inputs = _operand_inputs(identity, paired)
    reasons = identity['reasons'] + paired['reasons']
    conflict = False
    di, dg, native_identity = hsp['identity_denominator'], hsp['gap_denominator'], hsp['identity_count']
    if di['state'] == dg['state'] == 'present' and di['value'] != dg['value']:
        conflict = True
        reasons.append('incompatible_native_denominators')
    if native_identity['state'] == 'present' and paired['state'] == 'value' and native_identity['value'] > paired['value']:
        conflict = True
        reasons.append('identity_exceeds_paired_count')
    if reasons:
        state = 'conflict' if conflict else _worst([identity, paired])
        nonidentical = _unavailable('paired_column', inputs, state=state, reasons=reasons)
        among = _unavailable('fraction', inputs, state=state, reasons=reasons)
    else:
        nonidentical = _cell(paired['value'] - identity['value']['numerator'], 'paired_column', inputs)
        among = _ratio(identity['value']['numerator'], paired['value'], inputs, parameters)
    return {'reported_identity_fraction': identity, 'reported_positive_fraction': positive,
        'reported_gap_fraction': gaps, 'reported_paired_column_count': paired,
        'reported_nonidentical_paired_count': nonidentical,
        'reported_identity_among_paired_fraction': among}


def _support(included=(), excluded=(), absent=()):
    included, excluded, absent = _unique(included), _unique(excluded), _unique(absent)
    return {'included_blocks': included, 'excluded_blocks': excluded,
        'hsps_without_traceback': absent,
        'complete_for_displayed_blocks': not excluded and not absent}


def _combine_support(supports):
    return _support((k for s in supports for k in s['included_blocks']),
        (k for s in supports for k in s['excluded_blocks']),
        (k for s in supports for k in s['hsps_without_traceback']))


def _coverage(count, length, length_ref, parameters):
    inputs = _unique(count['inputs'] + [length_ref])
    states = [count['state']]
    reasons = list(count['reasons'])
    if length['state'] != 'present' or length['value'] <= 0:
        invalid = length['state'] == 'invalid' or length['state'] == 'present'
        states.append('invalid' if invalid else 'missing')
        reasons.append('invalid_reported_length' if invalid else 'missing_reported_length')
    if any(state != 'value' for state in states):
        return _unavailable('fraction', inputs, state=max(states, key=_SEVERITY.__getitem__), reasons=reasons)
    return _ratio(count['value'], length['value'], inputs, parameters)


def _union(parts, length, length_ref, parameters, *, absent=()):
    inputs = _unique(ref for part in parts for ref in part['count']['inputs'])
    support = _combine_support([part['support'] for part in parts] + [_support(absent=absent)])
    usable = [part for part in parts if part['count']['state'] == 'value']
    intervals = union_position_intervals([pair for part in usable for pair in part['intervals']])
    if usable:
        count = _cell(sum(end - start for start, end in intervals), 'displayed_position', inputs)
    else:
        cells = [part['count'] for part in parts]
        reasons = [reason for cell in cells for reason in cell['reasons']] or ['missing_traceback']
        count = _unavailable('displayed_position', inputs, state=_worst(cells), reasons=reasons)
    return {'intervals': intervals, 'count': count, 'reported_length': deepcopy(length),
        'coverage': _coverage(count, length, length_ref, parameters), 'support': support}


def _scope_coverage(children, query_length, subject_length, key, parameters, *, absent=()):
    return {field: _union([child['coverage'][field] for child in children],
        query_length if field.startswith('query_') else subject_length,
        _length_ref(key, 'query' if field.startswith('query_') else 'subject'), parameters,
        absent=absent) for field in COVERAGE_FIELDS}


def _continuity(blocks, observed):
    if not blocks:
        return 'unknown'
    if len(blocks) == 1:
        return 'yes' if blocks[0]['counts']['alignment_columns']['state'] == 'value' else 'unknown'
    # Native endpoint claims can contradict continuation independently of
    # whether enough symbols exist to construct an actual column map.
    for left, right, a, b in zip(blocks, blocks[1:], observed, observed[1:]):
        for side in ('query', 'subject'):
            if all(part['coverage'][side + '_reported_interval_union']['count']['state'] == 'value'
                    for part in (left, right)):
                if b[side + '_start']['value'] != a[side + '_end']['value'] + 1:
                    return 'no'
    if any(b['counts']['alignment_columns']['state'] != 'value' for b in blocks):
        return 'unknown'
    unknown = False
    for left, right, a, b in zip(blocks, blocks[1:], observed, observed[1:]):
        for side in ('query', 'subject'):
            if any(part['coverage'][side + '_trace_occupied_union']['count']['state'] != 'value'
                    for part in (left, right)):
                unknown = True
                continue
            end, start = a[side + '_end'], b[side + '_start']
            if end['state'] != 'present' or start['state'] != 'present':
                unknown = True
            elif start['value'] != end['value'] + 1:
                return 'no'
    return 'unknown' if unknown else 'yes'


def _hsp(hsp, query_length, subject_length, parameters):
    key = hsp['key']
    observed = hsp['traceback_blocks']
    blocks = [calculate_protein_block(block, key={**key, 'block_ordinal': index},
        query_length=query_length, subject_length=subject_length,
        amino_acid_alphabet=parameters['amino_acid_alphabet'],
        ratio_decimal_places=parameters['ratio_decimal_places'], rounding=parameters['rounding'])
        for index, block in enumerate(observed)]
    usable = [b for b in blocks if b['counts']['alignment_columns']['state'] == 'value']
    excluded = [b for b in blocks if b['counts']['alignment_columns']['state'] != 'value']
    support = _support((b['key'] for b in usable), (b['key'] for b in excluded), [] if blocks else [key])
    continuity = _continuity(blocks, observed)
    counts = {}
    for field, unit in TRACE_UNITS.items():
        cells = [b['counts'][field] for b in usable]
        inputs = _unique([ref for cell in cells for ref in cell['inputs']] +
            [ref for b in excluded for ref in (_ref(b['key'], '/query_symbols'), _ref(b['key'], '/subject_symbols'))])
        if field.endswith('_gap_runs') and len(blocks) > 1:
            inputs = _unique(inputs + [
                _ref(b['key'], '/' + side + endpoint)
                for b in blocks for side in ('query', 'subject') for endpoint in ('_start', '_end')])
            inputs = _unique(inputs + [ref for b in blocks for side in ('query', 'subject')
                for ref in b['coverage'][side + '_trace_occupied_union']['count']['inputs']])
        if field.endswith('_gap_runs') and len(blocks) > 1 and (excluded or continuity != 'yes'):
            prerequisites = [b['counts'][field] for b in blocks] + [
                b['coverage'][side + '_trace_occupied_union']['count']
                for b in blocks for side in ('query', 'subject')]
            reasons = [reason for cell in prerequisites for reason in cell['reasons']]
            reasons.append('block_continuity_conflict' if continuity == 'no' else 'incomplete_displayed_geometry')
            counts[field] = _unavailable(unit, inputs,
                state='conflict' if continuity == 'no' else _worst(prerequisites), reasons=reasons)
        elif not usable:
            reasons = [reason for b in excluded for reason in b['counts'][field]['reasons']] or ['missing_traceback']
            counts[field] = _unavailable(unit, inputs,
                state=_worst([b['counts'][field] for b in excluded]), reasons=reasons)
        else:
            total = sum(cell['value'] for cell in cells)
            if field.endswith('_gap_runs'):
                side = field.split('_')[0]
                total -= sum(a[side + '_symbols']['value'][-1] == b[side + '_symbols']['value'][0] == '-'
                    for a, b in zip(observed, observed[1:]))
            counts[field] = _cell(total, unit, inputs)
    coverage = _scope_coverage(blocks, query_length, subject_length, key, parameters,
        absent=[] if blocks else [key])
    pair_included = [b['key'] for b in blocks
        if all(b['coverage'][side + '_trace_paired_union']['count']['state'] == 'value' for side in ('query', 'subject'))]
    pair_support = _support(pair_included, (b['key'] for b in blocks if b['key'] not in pair_included),
        [] if blocks else [key])
    reported = _reported(hsp, parameters)
    diagnostics = [issue for b in blocks for issue in b['diagnostics']]
    for cell in reported.values():
        diagnostics.extend(_issue(code, cell['inputs'], key=key) for code in cell['reasons'])
    denom_cells = [hsp[name + '_denominator'] for name in ('identity', 'positive', 'gap')]
    denom_refs = [_ref(key, '/' + name + '_denominator') for name in ('identity', 'positive', 'gap')]
    denominators = [cell['value'] for cell in denom_cells if cell['state'] == 'present' and cell['value'] > 0]
    if len(set(denominators)) > 1:
        diagnostics.append(_issue('incompatible_native_denominators', denom_refs, key=key))
    extent = 'unknown'
    if support['complete_for_displayed_blocks'] and blocks and denominators:
        extent = 'agrees' if all(d == counts['alignment_columns']['value'] for d in denominators) else 'disagrees'
        if extent == 'disagrees':
            diagnostics.append(_issue('native_denominator_extent_conflict', denom_refs, key=key))
    if continuity == 'no':
        diagnostics.append(_issue('block_continuity_conflict',
            [_ref(b['key'], '/' + side + endpoint) for b in blocks
                for side in ('query', 'subject') for endpoint in ('_start', '_end')], key=key))
    if not support['complete_for_displayed_blocks']:
        diagnostics.append(_issue('incomplete_displayed_strings', [_ref(key, '/traceback_blocks')], key=key))
    if not pair_support['complete_for_displayed_blocks']:
        diagnostics.append(_issue('incomplete_displayed_geometry', [_ref(key, '/traceback_blocks')], key=key))
    for prefix, field in (('identity', 'displayed_symbol_identical_pairs'),
                          ('gap', None)):
        native = hsp[prefix + '_count']
        if support['complete_for_displayed_blocks'] and blocks and native['state'] == 'present':
            total = counts[field]['value'] if field else counts['query_gap_columns']['value'] + counts['subject_gap_columns']['value']
            if native['value'] != total:
                diagnostics.append(_issue('reported_count_traceback_conflict',
                    [_ref(key, '/' + prefix + '_count'), _ref(key, '/traceback_blocks')], key=key))
    if all(hsp[p + '_count']['state'] == 'present' for p in ('identity', 'positive')):
        if hsp['positive_count']['value'] < hsp['identity_count']['value']:
            diagnostics.append(_issue('positive_below_identity',
                [_ref(key, '/identity_count'), _ref(key, '/positive_count')], key=key))
    paired = reported['reported_paired_column_count']
    if paired['state'] == 'value' and hsp['positive_count']['state'] == 'present':
        if hsp['positive_count']['value'] > paired['value']:
            diagnostics.append(_issue('positive_exceeds_paired_count',
                [_ref(key, '/positive_count')] + paired['inputs'], key=key))
    scores = {name: deepcopy(hsp[name]) for name in ('bit_score', 'raw_score', 'expect', 'expect_group_count')}
    expect = hsp['expect']
    if expect['state'] == 'missing':
        display = 'missing'
    elif expect['state'] == 'invalid' or Decimal(expect['value']) < 0:
        display = 'invalid'
    else:
        display = 'printed_zero_precision_unknown' if Decimal(expect['value']) == 0 else 'positive_reported_decimal'
        if display == 'printed_zero_precision_unknown':
            diagnostics.append(_issue('printed_zero_expectation', [_ref(key, '/expect')], key=key))
    scores['expectation_display'] = display
    return {'key': deepcopy(key), 'reported': reported, 'native_scores': scores,
        'blocks': blocks, 'trace_counts': counts, 'trace_fractions': _trace_fractions(counts, parameters),
        'strings_support': support, 'coverage': coverage, 'pair_geometry_support': pair_support,
        'contiguous_blocks': continuity, 'native_denominator_extent': extent,
        'diagnostics': _unique(diagnostics)}


def _extremum(hsps, field, *, minimum=False):
    eligible, excluded, reasons = [], [], []
    for hsp in hsps:
        cell = hsp[field]
        if cell['state'] == 'present' and (field != 'expect' or Decimal(cell['value']) >= 0):
            eligible.append((Decimal(cell['value']), hsp['key']))
        else:
            excluded.append(deepcopy(hsp['key']))
            reasons.append('missing_native_score' if cell['state'] == 'missing' else 'invalid_native_score')
    if not eligible:
        return {'state': 'invalid' if 'invalid_native_score' in reasons else 'missing',
            'selected_field': None, 'tied_hsps': [], 'excluded_hsps': excluded,
            'reason_codes': list(dict.fromkeys(reasons or ['missing_native_score']))}
    value = (min if minimum else max)(number for number, _ in eligible)
    ties = [key for number, key in eligible if number == value]
    return {'state': 'value', 'selected_field': _ref(ties[0], '/' + field),
        'tied_hsps': deepcopy(ties), 'excluded_hsps': excluded,
        'reason_codes': list(dict.fromkeys(reasons))}


def _compatible_counts(graph, hsps):
    inputs = graph['distinct_pair_count']['inputs']
    if graph['mapping_state'] != 'compatible_displayed_partial_map':
        conflicting = graph['mapping_state'] == 'observed_conflict'
        reasons = [c['code'] for c in graph['conflicts']] if conflicting else ['incomplete_displayed_geometry']
        return {name: _unavailable('coordinate_pair', inputs,
            state='conflict' if conflicting else 'missing', reasons=reasons) for name in COMPATIBLE_FIELDS}
    key_fields = ('report_ordinal', 'query_ordinal', 'subject_ordinal', 'hsp_ordinal', 'block_ordinal', 'column_ordinal')
    columns = {tuple(c['key'][field] for field in key_fields): c
        for h in hsps for b in h['blocks'] for c in b['columns']}
    counts = dict.fromkeys(COMPATIBLE_FIELDS, 0)
    for edge in graph['edges']:
        column = columns[tuple(edge['supports'][0][field] for field in key_fields)]
        counts['identical_symbol_pairs'] += column['displayed_symbol_equal']
        for name, kinds in COMPATIBLE_FIELDS.items():
            if kinds is not None:
                counts[name] += column['kind'] in kinds
    return {name: _cell(count, 'coordinate_pair', inputs) for name, count in counts.items()}


def _overlap(left, right):
    return any(max(a, c) < min(b, d) for a, b in left for c, d in right)


def _native_disjoint(observed, hsps, parameters):
    inputs = _unique([ref for h in observed for ref in (_ref(h['key'], '/identity_count'), _ref(h['key'], '/identity_denominator'))]
        + [ref for h in hsps for side in ('query', 'subject') for ref in h['coverage'][side + '_trace_occupied_union']['count']['inputs']]
        + [ref for h in hsps for ref in h['trace_counts']['alignment_columns']['inputs']])
    reasons, state = [], 'missing'
    if not hsps:
        reasons.append('missing_traceback')
    for index, (original, hsp) in enumerate(zip(observed, hsps)):
        prerequisites = [block['counts']['alignment_columns'] for block in hsp['blocks']] + [
            block['coverage'][side + '_trace_occupied_union']['count']
            for block in hsp['blocks'] for side in ('query', 'subject')]
        for cell in prerequisites:
            reasons.extend(cell['reasons'])
            if _SEVERITY[cell['state']] > _SEVERITY[state]:
                state = cell['state']
        if not hsp['strings_support']['complete_for_displayed_blocks'] or not hsp['pair_geometry_support']['complete_for_displayed_blocks']:
            reasons.append('incomplete_displayed_geometry')
        if hsp['contiguous_blocks'] != 'yes':
            reasons.append('block_continuity_conflict' if hsp['contiguous_blocks'] == 'no' else 'incomplete_displayed_geometry')
        identity = hsp['reported']['reported_identity_fraction']
        if identity['state'] != 'value':
            reasons.extend(identity['reasons'])
            if _SEVERITY[identity['state']] > _SEVERITY[state]:
                state = identity['state']
        elif hsp['strings_support']['complete_for_displayed_blocks']:
            if (identity['value']['numerator'] != hsp['trace_counts']['displayed_symbol_identical_pairs']['value']
                    or identity['value']['denominator'] != hsp['trace_counts']['alignment_columns']['value']):
                reasons.append('reported_count_traceback_conflict')
        for other in hsps[:index]:
            if any(_overlap(hsp['coverage'][side + '_trace_occupied_union']['intervals'],
                    other['coverage'][side + '_trace_occupied_union']['intervals']) for side in ('query', 'subject')):
                reasons.append('overlapping_hsp_occupied_positions')
    if reasons:
        if any(reason in {'reported_count_traceback_conflict', 'overlapping_hsp_occupied_positions', 'block_continuity_conflict'} for reason in reasons):
            state = 'conflict'
        return (_unavailable('paired_column', inputs, state=state, reasons=reasons),
            _unavailable('alignment_column', inputs, state=state, reasons=reasons),
            _unavailable('fraction', inputs, state=state, reasons=reasons))
    identical = sum(h['identity_count']['value'] for h in observed)
    denominator = sum(h['identity_denominator']['value'] for h in observed)
    return (_cell(identical, 'paired_column', inputs), _cell(denominator, 'alignment_column', inputs),
        _ratio(identical, denominator, inputs, parameters))


def _subject(subject, query_length, parameters):
    key, length = subject['key'], subject['reported_length']
    hsps = [_hsp(h, query_length, length, parameters) for h in subject['hsps']]
    graph = inspect_protein_correspondence(hsps, key=key)
    counts = _compatible_counts(graph, hsps)
    pair_ratios = {
        'compatible_unique_pair_symbol_identity': _ratio_cells(counts['identical_symbol_pairs'], graph['distinct_pair_count'], parameters),
        'compatible_unique_pair_resolved_identity': _ratio_cells(counts['resolved_identical_pairs'], counts['resolved_pairs'], parameters, empty_reason='zero_resolved_population'),
        'compatible_unique_pair_resolved_fraction': _ratio_cells(counts['resolved_pairs'], graph['distinct_pair_count'], parameters),
    }
    if graph['mapping_state'] != 'compatible_displayed_partial_map':
        for cell in pair_ratios.values():
            cell['state'] = 'conflict' if graph['mapping_state'] == 'observed_conflict' else 'missing'
            cell['value'] = None
    disjoint = _native_disjoint(subject['hsps'], hsps, parameters)
    membership = [_ref(key, '/hsps')]
    diagnostics = [issue for h in hsps for issue in h['diagnostics']]
    for conflict in graph['conflicts']:
        issue = _issue(conflict['code'], graph['distinct_pair_count']['inputs'])
        issue['columns'] = deepcopy(conflict['columns'])
        issue['hsps'] = _unique({n: column[n] for n in
            ('report_ordinal', 'query_ordinal', 'subject_ordinal', 'hsp_ordinal')}
            for column in conflict['columns'])
        diagnostics.append(issue)
    if graph['mapping_state'] == 'incomplete_geometry':
        diagnostics.append(_issue('incomplete_displayed_geometry', membership))
    diagnostics.extend(_issue(code, disjoint[0]['inputs']) for code in disjoint[0]['reasons'])
    return {'key': deepcopy(key),
        'displayed_hsp_count': _cell(len(hsps), 'hsp_occurrence', membership),
        'displayed_block_count': _cell(sum(len(h['blocks']) for h in hsps), 'block_occurrence', membership),
        'hsps': hsps, 'coverage': _scope_coverage(hsps, query_length, length, key, parameters),
        'correspondence': graph, 'compatible_pair_counts': counts,
        **pair_ratios,
        'nonoverlapping_hsp_reported_identity_count': disjoint[0],
        'nonoverlapping_hsp_reported_alignment_columns': disjoint[1],
        'nonoverlapping_hsp_reported_identity_over_columns': disjoint[2],
        'maximum_reported_hsp_bit_score': _extremum(subject['hsps'], 'bit_score'),
        'maximum_reported_hsp_raw_score': _extremum(subject['hsps'], 'raw_score'),
        'minimum_reported_hsp_expectation': _extremum(subject['hsps'], 'expect', minimum=True),
        'diagnostics': _unique(diagnostics)}


def _query(query, parameters):
    key, length = query['key'], query['reported_length']
    subjects = [_subject(s, length, parameters) for s in query['subjects']]
    marker = query['no_hits_marker']['state'] == 'present'
    if marker:
        display = 'contradictory_native_no_hit_claim' if subjects or query['descriptions'] else 'native_no_hit_claim'
    elif subjects:
        display = 'alignments_displayed'
    elif query['descriptions']:
        display = 'descriptions_only'
    else:
        display = 'empty_without_native_no_hit_claim'
    coverage = _union([s['coverage']['query_trace_paired_union'] for s in subjects],
        length, _ref(key, '/length'), parameters)
    if display == 'native_no_hit_claim':
        inputs = [_ref(key, '/' + field) for field in ('no_hits_marker', 'descriptions', 'subjects', 'length')]
        count = _cell(0, 'displayed_position', inputs)
        coverage = {'intervals': [], 'count': count, 'reported_length': deepcopy(length),
            'coverage': _coverage(count, length, _ref(key, '/length'), parameters), 'support': _support()}
    diagnostics = [i for s in subjects for i in s['diagnostics']]
    if display in {'contradictory_native_no_hit_claim', 'empty_without_native_no_hit_claim', 'descriptions_only'}:
        code = {'contradictory_native_no_hit_claim': 'native_no_hit_with_displayed_population',
            'empty_without_native_no_hit_claim': 'empty_without_native_no_hit',
            'descriptions_only': 'descriptions_without_subject_blocks'}[display]
        diagnostics.append(_issue(code, [_ref(key, '/' + n) for n in ('no_hits_marker', 'descriptions', 'subjects')]))
    statistic_values = {}
    statistic_fields = ('integer_value', 'decimal_value', 'text_value', 'bits', 'lambda', 'k', 'h')
    threshold_kinds = {'sequences_better_than', 'hsps_better_than_without_gapping'}
    for index, statistic in enumerate(query['statistics']):
        value = {field: (Decimal(statistic[field]['value']) if field not in ('integer_value', 'text_value') else statistic[field]['value'])
            for field in statistic_fields if statistic[field]['state'] == 'present'}
        threshold = statistic['threshold']
        if statistic['kind'] in threshold_kinds:
            scope = Decimal(threshold['value']) if threshold['state'] == 'present' else ('unknown', index)
        else:
            scope = None
        previous = statistic_values.setdefault((statistic['kind'], scope), [])
        if previous and any(any(v[field] != value[field] for field in v.keys() & value.keys()) for _, v in previous):
            diagnostics.append(_issue('statistic_occurrences_disagree',
                [_ref(key, '/statistics/' + str(i)) for i, _ in previous] + [_ref(key, '/statistics/' + str(index))]))
        previous.append((index, value))
    membership = [_ref(key, '/subjects')]
    return {'key': deepcopy(key), 'display_state': display,
        'displayed_description_count': _cell(len(query['descriptions']), 'description_occurrence', [_ref(key, '/descriptions')]),
        'displayed_subject_count': _cell(len(subjects), 'subject_occurrence', membership),
        'displayed_hsp_count': _cell(sum(len(s['hsps']) for s in subjects), 'hsp_occurrence', membership),
        'displayed_block_count': _cell(sum(s['displayed_block_count']['value'] for s in subjects), 'block_occurrence', membership),
        'subjects': subjects, 'any_displayed_subject_query_paired_union': coverage,
        'diagnostics': _unique(diagnostics)}


def calculate_directional_components(sheet: dict, *, parameters: dict) -> dict:
    """Calculate from validated saved observations and an explicit formula version."""
    try:
        observed = validate_directional_numerical('DirectionalSheet', sheet)
    except DirectionalNumericalContractError as error:
        return {'state': 'failure', 'components': None, 'diagnostics': [
            _issue('invalid_input_contract', argument_pointer='/sheet' + error.pointer)]}
    try:
        options = validate_directional_numerical('DirectionalCalculationParameters', parameters)
    except DirectionalNumericalContractError as error:
        return {'state': 'failure', 'components': None, 'diagnostics': [
            _issue('invalid_parameters', argument_pointer='/parameters' + error.pointer)]}
    reports, diagnostics = [], deepcopy(observed['diagnostics'])
    for report in observed['reports']:
        ordinal = report['report_ordinal']
        queries = [_query(query, options) for query in report['query_rows']]
        inputs = [{'report_ordinal': ordinal, 'pointer': '/queries'}]
        record = {'report_ordinal': ordinal,
            'displayed_query_count': _cell(len(queries), 'query_occurrence', inputs), 'queries': queries,
            'diagnostics': _unique(i for query in queries for i in query['diagnostics'])}
        for kind, unit in (('description', 'description_occurrence'), ('subject', 'subject_occurrence'),
                            ('hsp', 'hsp_occurrence'), ('block', 'block_occurrence')):
            field = 'displayed_' + kind + '_count'
            record[field] = _cell(sum(q[field]['value'] for q in queries), unit, inputs)
        reports.append(record)
        diagnostics.extend(record['diagnostics'])
    components = {'version': 'bvbrc_proteome_directional_components_v1',
        'formula_version': 'displayed_blastp_correspondence_v1',
        'sheet_sha256': canonical_sheet_sha256(observed), 'parameters': options,
        'reports': reports, 'diagnostics': _unique(diagnostics),
        'correspondence_used_inputs': ['native_counts', 'traceback_symbols', 'traceback_coordinates',
            'reported_lengths', 'amino_acid_alphabet'],
        'correspondence_unused_retained_inputs': ['database_expectations', 'native_alignment_scores',
            'native_positives', 'native_midlines', 'description_scores', 'database_statistics', 'method_text']}
    # A's validator checks saved data relationships independently of this module.
    validated = validate_directional_numerical('DirectionalComponents', components, sheet=observed)
    partial_codes = {i['code'] for i in diagnostics} - {'printed_zero_expectation', 'no_execution_or_occurrence_evidence'}
    state = 'partial' if partial_codes else 'available'
    return {'state': state, 'components': validated, 'diagnostics': deepcopy(validated['diagnostics'])}


__all__ = ['calculate_directional_components']
