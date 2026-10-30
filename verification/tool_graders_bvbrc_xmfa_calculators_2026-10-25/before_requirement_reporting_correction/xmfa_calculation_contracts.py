"""Closed, detached values for the accepted pure DNA XMFA calculations.

These checks validate saved numerical relationships, not external byte custody.
The functions consuming a document additionally check its exact native records
and the supplied source bindings. No validator opens files or reruns a parser.
"""
from copy import deepcopy
import math

from .bvbrc_alignment_values import diagnostic, requirement, validate_numeric_cell
from .phylogeny_calculation_contracts import evidence as _evidence

COMPLETENESS = ('complete', 'partial', 'truncated', 'unknown')
BASES = ('represented', 'multi_member_block', 'cooccupied_column')
COMPLEMENT = str.maketrans('ACGTRYSWKMBDHVNacgtryswkmbdhvn',
                         'TGCAYRSWMKVHDBNtgcayrswmkvhdbn')
DIAGNOSTIC_SUFFIXES = frozenset('digest_mismatch encoding_invalid version_missing '
    'version_unsupported header_malformed member_invalid coordinate_invalid strand_invalid '
    'sequence_symbol_invalid sequence_before_header span_mismatch row_width_conflict '
    'zero_record_has_residues all_zero_block missing_block_terminator unparsed_line '
    'duplicate_member_record metadata_duplicate metadata_conflict source_binding_missing '
    'source_binding_conflict invocation_mode_missing input_population_partial '
    'source_span_outside_input source_sequence_mismatch original_map_missing original_map_conflict '
    'overlapping_placement selected_population_partial empty_comparison_population '
    'pair_not_coobserved whole_genome_scope_unproved empty_input document_unrecognized '
    'metadata_integer_invalid'.split())


def require(condition, code):
    if not condition:
        raise ValueError('xmfa_' + code)


def shape(value, keys):
    require(type(value) is dict and set(value) == set(keys), 'calculation_shape_invalid')


def text(value, *, nullable=False):
    require(nullable and value is None or type(value) is str and bool(value), 'calculation_text_invalid')


def integer(value, *, minimum=0, nullable=False):
    require(nullable and value is None or type(value) is int and value >= minimum, 'calculation_integer_invalid')


def array(value):
    require(type(value) is list, 'calculation_array_invalid')


def unique_integers(value, *, minimum=0):
    array(value)
    for item in value:
        integer(item, minimum=minimum)
    require(len(value) == len(set(value)), 'duplicate_requested_index')


def evidence(value):
    try:
        _evidence(value)
    except ValueError as error:
        raise ValueError('xmfa_calculation_evidence_invalid') from error


def occurrence(value):
    shape(value, ('input_binding_id', 'member_id', 'occurrence_index'))
    text(value['input_binding_id']); text(value['member_id']); integer(value['occurrence_index'])
    return tuple(value[k] for k in ('input_binding_id', 'member_id', 'occurrence_index'))


def ref(value, *, cell=False):
    fields = ('block_index', 'record_index', 'column_0based') if cell else ('block_index', 'record_index')
    shape(value, fields)
    for field in fields:
        integer(value[field])
    return tuple(value[k] for k in fields)


def interval(value, *, nonempty=False):
    array(value)
    require(len(value) == 2, 'calculation_interval_invalid')
    for endpoint in value:
        integer(endpoint)
    require(value[0] < value[1] if nonempty else value[0] <= value[1], 'calculation_interval_invalid')


def union_intervals(intervals):
    result = []
    for start, end in sorted(intervals):
        if start == end:
            continue
        if result and start <= result[-1][1]:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return result


def interval_length(intervals):
    return sum(end - start for start, end in intervals)


def multiplicity_bases(intervals):
    events = {}
    for start, end in intervals:
        events[start] = events.get(start, 0) + 1
        events[end] = events.get(end, 0) - 1
    count, previous, total = 0, 0, 0
    for position, delta in sorted(events.items()):
        if count >= 2:
            total += position - previous
        count += delta
        previous = position
    return total


def complement_intervals(intervals, length):
    cursor, result = 0, []
    for start, end in intervals:
        if start > cursor:
            result.append([cursor, start])
        cursor = end
    if cursor < length:
        result.append([cursor, length])
    return result


def _union(value):
    array(value)
    for row in value:
        interval(row, nonempty=True)
    require(value == union_intervals(value), 'calculation_union_invalid')


def reports(value):
    array(value['requirements']); array(value['diagnostics'])
    ids = []
    for row in value['requirements']:
        shape(row, ('requirement_id', 'kind', 'role', 'source_refs', 'reason_code'))
        try:
            require(requirement(**row) == row, 'calculation_requirement_invalid')
        except ValueError as error:
            raise ValueError('xmfa_calculation_requirement_invalid') from error
        require(row['reason_code'] in {'xmfa_' + code for code in DIAGNOSTIC_SUFFIXES},
                'calculation_diagnostic_invalid')
        ids.append(row['requirement_id'])
    require(len(ids) == len(set(ids)), 'calculation_requirement_duplicate')
    for row in value['diagnostics']:
        shape(row, ('code', 'phase', 'path', 'severity', 'evidence_refs'))
        try:
            require(diagnostic(**row) == row, 'calculation_diagnostic_invalid')
        except ValueError as error:
            raise ValueError('xmfa_calculation_diagnostic_invalid') from error
        require(row['code'] in {'xmfa_' + code for code in DIAGNOSTIC_SUFFIXES},
                'calculation_diagnostic_invalid')
    require(value['status'] != 'ok' or not value['requirements'], 'calculation_status_conflict')
    return set(ids)


def _envelope(value, keys):
    shape(value, keys)
    text(value['document_id'])
    require(value['status'] in ('ok', 'partial', 'invalid'), 'calculation_status_invalid')
    return reports(value)


def _cell(value, field, unit, population, ids, *, prefix='xmfa_', fraction=False):
    try:
        validate_numeric_cell(value)
    except ValueError as error:
        raise ValueError('xmfa_calculation_cell_invalid') from error
    require(value['unit'] == unit and value['population_id'] == population
            and value['method_id'] == prefix + field + '_v1'
            and value['origin'] == 'calculated' and value['uncertainty'] is None,
            'calculation_cell_meaning_conflict')
    require(set(value['requirement_ids']) <= ids, 'calculation_requirement_unknown')
    n, d, number = value['numerator'], value['denominator'], value['value']
    if fraction:
        integer(n, nullable=True); integer(d, nullable=True)
        if value['state'] == 'available':
            require(n is not None and d is not None and d > 0 and n <= d
                    and number == n / d, 'calculation_fraction_conflict')
        if d == 0:
            require(value['state'] != 'available', 'calculation_fraction_conflict')
    else:
        require(n is None and d is None, 'calculation_count_denominator_conflict')
        if number is not None:
            if unit == 'bits':
                require(number >= 0, 'calculation_entropy_invalid')
            else:
                integer(number)
    return number


def validate_xmfa_selection(value: dict) -> dict:
    shape(value, ('population_id', 'document_id', 'member_numbers', 'block_columns', 'completeness', 'evidence'))
    text(value['population_id']); text(value['document_id'])
    unique_integers(value['member_numbers'], minimum=1)
    require(value['completeness'] in COMPLETENESS, 'selection_completeness_invalid')
    evidence(value['evidence']); array(value['block_columns'])
    blocks = []
    for entry in value['block_columns']:
        shape(entry, ('block_index', 'columns_0based'))
        integer(entry['block_index']); blocks.append(entry['block_index'])
        unique_integers(entry['columns_0based'])
    require(len(blocks) == len(set(blocks)), 'duplicate_requested_index')
    return deepcopy(value)


def validate_xmfa_coordinates(value: dict) -> dict:
    _envelope(value, ('document_id', 'status', 'cells', 'requirements', 'diagnostics'))
    array(value['cells']); seen = set()
    for row in value['cells']:
        shape(row, ('cell', 'member_number', 'aligned_symbol', 'state', 'native_position_1based',
            'native_position_0based', 'native_strand', 'forward_symbol', 'source_state',
            'source_coordinate', 'original_coordinates', 'evidence'))
        key = ref(row['cell'], cell=True)
        require(key not in seen, 'duplicate_requested_index'); seen.add(key)
        integer(row['member_number'], minimum=1, nullable=True)
        require(type(row['aligned_symbol']) is str and len(row['aligned_symbol']) == 1,
                'coordinate_symbol_invalid')
        require(row['state'] in ('residue', 'gap', 'absent_zero', 'incompatible'), 'coordinate_state_invalid')
        integer(row['native_position_1based'], minimum=1, nullable=True)
        integer(row['native_position_0based'], nullable=True)
        require(row['native_strand'] in ('+', '-', None), 'coordinate_strand_invalid')
        require(row['source_state'] in ('resolved', 'missing', 'conflicting', 'not_applicable'),
                'coordinate_source_state_invalid')
        evidence(row['evidence']); array(row['original_coordinates'])
        if row['state'] == 'residue':
            require(row['member_number'] is not None and row['native_strand'] in ('+', '-')
                    and row['aligned_symbol'] in 'ACGTRYSWKMBDHVNacgtryswkmbdhvn'
                    and row['native_position_0based'] is not None
                    and row['native_position_1based'] == row['native_position_0based'] + 1,
                    'coordinate_position_conflict')
            forward = row['aligned_symbol'] if row['native_strand'] == '+' else row['aligned_symbol'].translate(COMPLEMENT)
            require(row['forward_symbol'] == forward, 'coordinate_symbol_conflict')
            require(row['source_state'] != 'not_applicable', 'coordinate_source_state_invalid')
        else:
            require(row['native_position_0based'] is row['native_position_1based'] is row['forward_symbol'] is None,
                    'coordinate_position_conflict')
            require(row['source_state'] == 'not_applicable' and not row['original_coordinates'],
                    'coordinate_source_state_invalid')
            if row['state'] in ('gap', 'absent_zero'):
                require(row['aligned_symbol'] == '-', 'coordinate_symbol_conflict')
        sc = row['source_coordinate']
        require((sc is not None) == (row['source_state'] == 'resolved'), 'coordinate_source_conflict')
        if sc is not None:
            shape(sc, ('file_id', 'record_id', 'entry_1based', 'position_0based', 'strand'))
            text(sc['file_id']); text(sc['record_id']); integer(sc['entry_1based'], minimum=1)
            integer(sc['position_0based'])
            require(sc['strand'] == row['native_strand'], 'coordinate_strand_conflict')
        else:
            require(not row['original_coordinates'], 'coordinate_original_without_source')
        originals = []
        associations = {}
        for original in row['original_coordinates']:
            shape(original, ('original_member', 'position_0based', 'original_length', 'strand', 'transformation_id', 'evidence'))
            ok = occurrence(original['original_member'])
            integer(original['position_0based']); integer(original['original_length'])
            require(original['position_0based'] < original['original_length'], 'coordinate_original_outside_source')
            require(original['strand'] in ('+', '-'), 'coordinate_strand_invalid')
            text(original['transformation_id']); evidence(original['evidence'])
            require(bool(original['evidence']), 'coordinate_original_evidence_missing')
            facts = (original['position_0based'], original['original_length'], original['strand'])
            require(ok not in associations or associations[ok] == facts, 'coordinate_original_conflict')
            associations[ok] = facts
            require(original not in originals, 'coordinate_original_duplicate'); originals.append(original)
    return deepcopy(value)


def validate_xmfa_inverse_coordinates(value: dict) -> dict:
    _envelope(value, ('document_id', 'status', 'queries', 'requirements', 'diagnostics'))
    array(value['queries']); seen = set()
    for row in value['queries']:
        shape(row, ('member_number', 'position_0based', 'state', 'matches', 'search_completeness', 'evidence'))
        integer(row['member_number'], minimum=1); integer(row['position_0based'])
        key = row['member_number'], row['position_0based']
        require(key not in seen, 'duplicate_requested_index'); seen.add(key)
        require(row['state'] in ('unique', 'multiple', 'none_in_document', 'unknown'), 'inverse_state_invalid')
        require(row['search_completeness'] in COMPLETENESS, 'inverse_completeness_invalid')
        array(row['matches']); refs = [ref(match, cell=True) for match in row['matches']]
        require(len(refs) == len(set(refs)), 'inverse_match_duplicate')
        require(refs == sorted(refs), 'inverse_match_order_invalid'); evidence(row['evidence'])
        if row['search_completeness'] != 'complete':
            require(row['state'] == 'unknown' and value['status'] != 'ok', 'inverse_completeness_conflict')
        else:
            expected = 'multiple' if len(refs) > 1 else 'unique' if refs else 'none_in_document'
            require(row['state'] == expected, 'inverse_state_conflict')
    return deepcopy(value)


def _pairs(value, members):
    array(value); seen = set()
    for pair in value:
        array(pair)
        require(len(pair) == 2, 'pair_shape_invalid')
        for number in pair:
            integer(number, minimum=1)
        require(pair[0] != pair[1] and all(n in members for n in pair), 'pair_member_invalid')
        key = tuple(sorted(pair))
        require(key not in seen, 'pair_duplicate'); seen.add(key)


SITE_COUNTS = ('present_member_count', 'absent_member_count', 'gap_count', 'nongap_count',
               'canonical_count', 'ambiguity_count', 'other_count')
PAIR_COUNTS = ('identical_canonical', 'substitutions', 'a_only_gap', 'b_only_gap',
               'both_gap', 'ambiguous_or_other', 'comparable_canonical')


def validate_xmfa_alignment_components(value: dict) -> dict:
    ids = _envelope(value, ('schema_version', 'document_id', 'status', 'selection', 'parameters',
                           'blocks', 'requirements', 'diagnostics'))
    require(value['schema_version'] == 'mauve_xmfa_alignment_components_v1', 'calculation_version_invalid')
    selection = validate_xmfa_selection(value['selection'])
    require(selection['document_id'] == value['document_id'], 'selection_document_conflict')
    p, members = selection['population_id'], selection['member_numbers']
    shape(value['parameters'], ('case_policy', 'selected_pairs'))
    require(value['parameters']['case_policy'] in ('preserve', 'uppercase'), 'case_policy_invalid')
    _pairs(value['parameters']['selected_pairs'], members)
    array(value['blocks'])
    require(len(value['blocks']) == len(selection['block_columns']), 'selection_blocks_conflict')
    for block, chosen in zip(value['blocks'], selection['block_columns']):
        shape(block, ('block_index', 'present_members', 'zero_members', 'omitted_members', 'conflicting_members',
            'record_refs', 'selected_column_count', 'present_member_count', 'zero_member_count',
            'omitted_member_count', 'sites', 'pairs'))
        integer(block['block_index'])
        require(block['block_index'] == chosen['block_index'], 'selection_blocks_conflict')
        classified = []
        for field in ('present_members', 'zero_members', 'omitted_members', 'conflicting_members'):
            unique_integers(block[field], minimum=1)
            require(all(n in members for n in block[field]) and block[field] == [n for n in members if n in block[field]],
                    'selection_members_conflict')
            classified += block[field]
        require(len(classified) == len(set(classified)), 'selection_members_conflict')
        array(block['record_refs']); refs = [ref(row) for row in block['record_refs']]
        require(len(refs) == len(set(refs)) and refs == sorted(refs)
                and all(k[0] == block['block_index'] for k in refs), 'record_reference_conflict')
        for field, expected, unit in (
            ('selected_column_count', len(chosen['columns_0based']), 'columns'),
            ('present_member_count', len(block['present_members']), 'members'),
            ('zero_member_count', len(block['zero_members']), 'members'),
            ('omitted_member_count', len(block['omitted_members']), 'members')):
            number = _cell(block[field], field, unit, p, ids)
            require(number is None or number == expected, 'calculation_count_conflict')
        require(block['selected_column_count']['state'] == 'available', 'calculation_count_conflict')
        member_state = block['present_member_count']['state']
        require(all(block[field]['state'] == member_state for field in ('zero_member_count', 'omitted_member_count')),
                'calculation_population_state_conflict')
        if block['conflicting_members']:
            require(member_state == 'incompatible', 'calculation_population_state_conflict')
        elif selection['completeness'] != 'complete':
            require(member_state == 'truncated', 'calculation_population_state_conflict')
        require(member_state == 'available' or value['status'] != 'ok', 'calculation_status_conflict')
        array(block['sites'])
        require(len(block['sites']) == len(chosen['columns_0based']), 'selection_columns_conflict')
        for site, column in zip(block['sites'], chosen['columns_0based']):
            shape(site, ('column_0based', 'symbol_counts', *SITE_COUNTS, 'literal_entropy_bits',
                         'canonical_entropy_bits', 'canonical_majority_fraction'))
            integer(site['column_0based'])
            require(site['column_0based'] == column, 'selection_columns_conflict')
            array(site['symbol_counts']); symbols = {}
            for entry in site['symbol_counts']:
                shape(entry, ('symbol', 'count'))
                require(type(entry['symbol']) is str and len(entry['symbol']) == 1 and entry['symbol'] not in symbols,
                        'site_symbol_invalid')
                if value['parameters']['case_policy'] == 'uppercase':
                    require(entry['symbol'] == entry['symbol'].upper(), 'site_case_conflict')
                symbols[entry['symbol']] = _cell(entry['count'], 'symbol_count', 'characters', p, ids)
            counts = {field: _cell(site[field], field, 'members' if 'member' in field else 'characters', p, ids)
                      for field in SITE_COUNTS}
            require(all(site[field]['state'] == member_state for field in SITE_COUNTS)
                    and all(entry['count']['state'] == member_state for entry in site['symbol_counts']),
                    'calculation_population_state_conflict')
            for field in ('literal_entropy_bits', 'canonical_entropy_bits'):
                _cell(site[field], field, 'bits', p, ids)
            _cell(site['canonical_majority_fraction'], 'canonical_majority_fraction', 'fraction', p, ids, fraction=True)
            if member_state != 'available':
                require(all(site[field]['state'] == member_state for field in (
                    'literal_entropy_bits', 'canonical_entropy_bits', 'canonical_majority_fraction')),
                    'calculation_population_state_conflict')
            if all(number is not None for number in counts.values()):
                require(all(n is not None and n > 0 for n in symbols.values()), 'site_symbol_count_conflict')
                canonical = {s: n for s, n in symbols.items() if s in 'ACGT'}
                total = sum(symbols.values()); can = sum(canonical.values())
                require(counts == dict(present_member_count=len(block['present_members']),
                    absent_member_count=len(block['zero_members']) + len(block['omitted_members']),
                    gap_count=symbols.get('-', 0), nongap_count=total - symbols.get('-', 0),
                    canonical_count=can, ambiguity_count=sum(n for s, n in symbols.items() if s in 'RYSWKMBDHVN'),
                    other_count=sum(n for s, n in symbols.items() if s not in 'ACGTRYSWKMBDHVN-'))
                    and total == counts['present_member_count'], 'site_count_conflict')
                for field, observed in (('literal_entropy_bits', list(symbols.values())),
                                        ('canonical_entropy_bits', list(canonical.values()))):
                    denominator = sum(observed)
                    if denominator:
                        expected = -sum((n / denominator) * math.log2(n / denominator) for n in observed)
                        require(site[field]['state'] == 'available' and math.isclose(site[field]['value'], expected,
                                rel_tol=1e-13, abs_tol=1e-13), 'site_entropy_conflict')
                    else:
                        require(site[field]['state'] == 'not_measured', 'site_entropy_conflict')
                majority = site['canonical_majority_fraction']
                require(majority['numerator'] == max(canonical.values(), default=0)
                        and majority['denominator'] == can, 'site_majority_conflict')
                require(majority['state'] == ('available' if can else 'not_measured'), 'site_majority_conflict')
        array(block['pairs'])
        require(len(block['pairs']) == len(value['parameters']['selected_pairs']), 'pair_population_conflict')
        for pair, selected in zip(block['pairs'], value['parameters']['selected_pairs']):
            shape(pair, ('member_a', 'member_b', 'state', *PAIR_COUNTS, 'identity_fraction'))
            integer(pair['member_a'], minimum=1); integer(pair['member_b'], minimum=1)
            require([pair['member_a'], pair['member_b']] == selected, 'pair_population_conflict')
            require(pair['state'] in ('available', 'not_coobserved', 'incompatible', 'incomplete'), 'pair_state_invalid')
            numbers = {field: _cell(pair[field], field, 'columns', p, ids) for field in PAIR_COUNTS}
            _cell(pair['identity_fraction'], 'identity_fraction', 'fraction', p, ids, fraction=True)
            if pair['state'] == 'available':
                require(all(n is not None for n in numbers.values())
                    and numbers['comparable_canonical'] == numbers['identical_canonical'] + numbers['substitutions']
                    and sum(numbers[field] for field in PAIR_COUNTS[:-1]) == len(chosen['columns_0based']),
                    'pair_count_conflict')
                fraction = pair['identity_fraction']
                require(fraction['numerator'] == numbers['identical_canonical']
                        and fraction['denominator'] == numbers['comparable_canonical']
                        and fraction['state'] == ('available' if numbers['comparable_canonical'] else 'not_measured'),
                        'pair_fraction_conflict')
            else:
                require(all(n is None for n in numbers.values()) and pair['identity_fraction']['value'] is None,
                        'pair_state_conflict')
                expected_state = {'incompatible': 'incompatible', 'incomplete': 'truncated',
                                  'not_coobserved': 'not_measured'}[pair['state']]
                require(all(pair[field]['state'] == expected_state for field in (*PAIR_COUNTS, 'identity_fraction'))
                        and value['status'] != 'ok', 'pair_state_conflict')
    return deepcopy(value)


def validate_xmfa_coverage_components(value: dict) -> dict:
    ids = _envelope(value, ('schema_version', 'document_id', 'status', 'selection', 'parameters',
                           'members', 'requirements', 'diagnostics'))
    require(value['schema_version'] == 'mauve_xmfa_coverage_components_v1', 'calculation_version_invalid')
    selection = validate_xmfa_selection(value['selection'])
    require(selection['document_id'] == value['document_id'], 'selection_document_conflict')
    shape(value['parameters'], ('basis',))
    require(value['parameters']['basis'] in BASES, 'coverage_basis_invalid')
    prefix = 'xmfa_' + value['parameters']['basis'] + '_'
    p = selection['population_id']; array(value['members'])
    require(len(value['members']) == len(selection['member_numbers']), 'selection_members_conflict')
    blocks = {b['block_index'] for b in selection['block_columns']}
    for member, number in zip(value['members'], selection['member_numbers']):
        shape(member, ('member_number', 'source_length', 'placements', 'known_union_intervals', 'known_union_bases',
            'placement_bases', 'multiply_represented_bases', 'excess_placement_bases', 'selected_coverage_fraction',
            'complement_intervals', 'complement_bases', 'membership_completeness', 'original_coverage'))
        integer(member['member_number'], minimum=1)
        require(member['member_number'] == number, 'selection_members_conflict')
        require(member['membership_completeness'] in COMPLETENESS, 'coverage_completeness_invalid')
        array(member['placements']); intervals = []; by_record = {}
        for placement in member['placements']:
            shape(placement, ('record', 'interval_0based_half_open', 'strand'))
            key = ref(placement['record'])
            require(key[0] in blocks, 'placement_record_unknown')
            interval(placement['interval_0based_half_open'], nonempty=True)
            require(placement['strand'] in ('+', '-'), 'placement_strand_invalid')
            intervals.append(placement['interval_0based_half_open'])
            previous = by_record.setdefault(key, {'strand': placement['strand'], 'intervals': []})
            require(previous['strand'] == placement['strand'], 'placement_strand_conflict')
            previous['intervals'].append(placement['interval_0based_half_open'])
        for record in by_record.values():
            require(len(union_intervals(record['intervals'])) == len(record['intervals']), 'placement_runs_conflict')
        _union(member['known_union_intervals'])
        require(member['known_union_intervals'] == union_intervals(intervals), 'coverage_union_conflict')
        numbers = {}
        for field in ('source_length', 'known_union_bases', 'placement_bases', 'multiply_represented_bases',
                      'excess_placement_bases', 'complement_bases'):
            unit = 'nucleotide_placements' if field in ('placement_bases', 'excess_placement_bases') else 'nucleotides'
            numbers[field] = _cell(member[field], field, unit, p, ids, prefix=prefix)
        union = interval_length(member['known_union_intervals']); total = interval_length(intervals)
        require(numbers['known_union_bases'] == union and numbers['placement_bases'] == total
                and numbers['multiply_represented_bases'] == multiplicity_bases(intervals)
                and numbers['excess_placement_bases'] == total - union, 'coverage_count_conflict')
        fraction = member['selected_coverage_fraction']
        _cell(fraction, 'selected_coverage_fraction', 'fraction', p, ids, prefix=prefix, fraction=True)
        if fraction['state'] == 'available':
            require(member['membership_completeness'] == 'complete' and fraction['numerator'] == union
                    and fraction['denominator'] == numbers['source_length'], 'coverage_fraction_conflict')
        complement = member['complement_intervals']
        if complement is not None:
            _union(complement)
            require(numbers['source_length'] is not None and member['membership_completeness'] == 'complete'
                    and all(end <= numbers['source_length'] for _, end in member['known_union_intervals']),
                    'coverage_complement_conflict')
            require(complement == complement_intervals(member['known_union_intervals'], numbers['source_length'])
                    and numbers['complement_bases'] == interval_length(complement), 'coverage_complement_conflict')
            require(fraction['state'] == 'available' or fraction['state'] == 'not_measured'
                    and numbers['source_length'] == 0, 'coverage_complement_conflict')
            require(fraction['numerator'] == union and fraction['denominator'] == numbers['source_length'],
                    'coverage_fraction_conflict')
        else:
            require(numbers['complement_bases'] is None and fraction['state'] != 'available', 'coverage_complement_conflict')
        array(member['original_coverage']); seen = set()
        for original in member['original_coverage']:
            shape(original, ('original_member', 'original_length', 'known_union_intervals', 'known_union_bases',
                'coverage_fraction', 'mapping_completeness', 'evidence'))
            key = occurrence(original['original_member'])
            require(key not in seen, 'original_coverage_duplicate'); seen.add(key)
            require(original['mapping_completeness'] in COMPLETENESS, 'coverage_completeness_invalid')
            evidence(original['evidence']); _union(original['known_union_intervals'])
            length = _cell(original['original_length'], 'original_length', 'nucleotides', p, ids, prefix=prefix + 'original_')
            count = _cell(original['known_union_bases'], 'known_union_bases', 'nucleotides', p, ids, prefix=prefix + 'original_')
            require(count == interval_length(original['known_union_intervals']), 'coverage_count_conflict')
            _cell(original['coverage_fraction'], 'coverage_fraction', 'fraction', p, ids, prefix=prefix + 'original_', fraction=True)
            if length is not None:
                require(all(end <= length for _, end in original['known_union_intervals']), 'original_coverage_outside_source')
            if original['coverage_fraction']['state'] == 'available':
                require(original['mapping_completeness'] == member['membership_completeness'] == 'complete'
                        and fraction['state'] in ('available', 'not_measured')
                        and original['coverage_fraction']['numerator'] == count
                        and original['coverage_fraction']['denominator'] == length, 'original_coverage_fraction_conflict')
    return deepcopy(value)


__all__ = ['validate_xmfa_coordinates', 'validate_xmfa_inverse_coordinates',
           'validate_xmfa_selection', 'validate_xmfa_alignment_components', 'validate_xmfa_coverage_components']
