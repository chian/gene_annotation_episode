"""Detached checks for explicit legacy-Mauve selections and saved numbers.

Full component validation verifies numerical relationships for producers.
Saved component structure validation checks types, meaning and associations
without rederiving scientific quantities. Neither authenticates byte custody.
"""
from copy import deepcopy

from . import mauve_v4_format_contracts as f
from .bvbrc_alignment_values import diagnostic, requirement, validate_numeric_cell, validate_native_number
from .phylogeny_calculation_contracts import evidence as shared_evidence
from .xmfa_calculation_contracts import union_intervals, interval_length, multiplicity_bases, complement_intervals

ASSOCIATION_CODES = frozenset(('argument_invalid original_task_invalid application_mismatch '
    'genome_input_missing genome_occurrence_conflict duplicate_genome_occurrence recipe_conflict '
    'explicit_zero_not_forwarded source_option_unsupported invocation_missing invocation_conflict '
    'metadata_type_unsupported metadata_record_unverified metadata_task_conflict content_missing '
    'content_digest_conflict staged_file_missing staged_file_run_unverified native_path_missing '
    'native_path_conflict source_records_partial source_sequence_mismatch source_span_outside_input '
    'genome_census_unknown contig_identity_missing contig_identity_conflict feature_map_missing '
    'feature_map_conflict artifact_task_conflict artifact_version_unverified artifact_role_conflict '
    'artifact_format_conflict primary_output_missing duplicate_representation member_join_missing '
    'member_join_conflict interval_join_missing interval_join_conflict native_execution_unverified').split())
CALCULATION_CODES = frozenset(('selection_invalid selection_document_conflict selection_member_unknown '
    'selection_record_unknown selection_column_outside_record selection_population_incomplete '
    'pair_not_coobserved source_symbols_missing source_denominator_missing zero_denominator '
    'overlapping_placement bbcols_block_unbound bbcols_column_outside_block').split())
CODES = frozenset('mauve_v4_' + code for code in f.PARSER_CODES | CALCULATION_CODES) | frozenset(
    'bvbrc_genome_alignment_' + code for code in ASSOCIATION_CODES)
MEMBER_COUNTS = ('alignment_columns', 'selected_column_count', 'selected_nongap_count',
    'selected_gap_count', 'selected_canonical_count', 'selected_ambiguity_count', 'selected_other_count')
PAIR_COUNTS = ('identical_canonical', 'substitutions', 'a_only_gap', 'b_only_gap',
               'both_gap', 'ambiguous_or_other', 'comparable_canonical')


def require(condition, code='selection_invalid'):
    f.require(condition, code)


def evidence(value):
    try:
        shared_evidence(value)
    except ValueError as error:
        raise ValueError('mauve_v4_argument_invalid') from error


def member(value):
    f.shape(value, ('namespace', 'index')); f.uint(value['index'])
    require(value['namespace'] == 'mauve_v4_member_0based')
    return value['index']


def interval(value, *, nonempty=False):
    f.array(value); require(len(value) == 2)
    for number in value: f.uint(number)
    require(value[0] < value[1] if nonempty else value[0] <= value[1])


def pairs(value, members):
    f.array(value); keys = []
    for pair in value:
        f.shape(pair, ('member_a', 'member_b'))
        a, b = member(pair['member_a']), member(pair['member_b'])
        require(a < b and a in members and b in members)
        keys.append((a, b))
    require(len(keys) == len(set(keys)))


def validate_mauve_v4_selection(selection: dict) -> dict:
    f.shape(selection, ('schema_version', 'population_id', 'document_id', 'members', 'segments', 'pairs',
                        'case_policy', 'denominator', 'population_scope', 'evidence'), 'selection_invalid')
    require(selection['schema_version'] == 'mauve_v4_selection_v1')
    f.text(selection['population_id']); f.text(selection['document_id'])
    require(selection['case_policy'] in ('preserve', 'uppercase'))
    require(selection['denominator'] in ('none', 'native_declared_length', 'validated_staged_length'))
    require(selection['population_scope'] in ('selected_segments', 'all_observed_document_segments'))
    evidence(selection['evidence']); f.array(selection['members']); f.array(selection['segments'])
    members = [member(m) for m in selection['members']]
    require(len(members) == len(set(members))); pairs(selection['pairs'], members)
    refs = []
    for row in selection['segments']:
        f.shape(row, ('interval_index', 'segment_index', 'column_ranges_0based_half_open'), 'selection_invalid')
        for field in ('interval_index', 'segment_index'): f.uint(row[field])
        refs.append((row['interval_index'], row['segment_index']))
        ranges = row['column_ranges_0based_half_open']; f.array(ranges)
        for r in ranges: interval(r, nonempty=True)
        require(all(a[1] <= b[0] for a, b in zip(ranges, ranges[1:])))
    require(len(refs) == len(set(refs)))
    return deepcopy(selection)


def reports(value):
    f.array(value['requirements']); f.array(value['diagnostics']); ids = set()
    for row in value['requirements']:
        f.shape(row, ('requirement_id', 'kind', 'role', 'source_refs', 'reason_code'))
        f.text(row['reason_code'])
        require(row['reason_code'] in CODES)
        require(requirement(**row) == row and row['requirement_id'] not in ids)
        ids.add(row['requirement_id'])
    for row in value['diagnostics']:
        f.shape(row, ('code', 'phase', 'path', 'severity', 'evidence_refs'))
        f.text(row['code'])
        require(row['code'] in CODES and diagnostic(**row) == row)
    require(value['status'] in ('ok', 'partial', 'invalid'))
    require(value['status'] != 'ok' or not ids and not value['diagnostics'])
    return ids


def _ids(row, ids):
    f.array(row['requirement_ids'])
    for rid in row['requirement_ids']: f.text(rid)
    require(len(set(row['requirement_ids'])) == len(row['requirement_ids'])
            and set(row['requirement_ids']) <= ids)
    evidence(row['evidence'])


def _cell(value, field, unit, selection, ids, *, origin='calculated', fraction=False):
    try:
        validate_numeric_cell(value)
    except ValueError as error:
        raise ValueError('mauve_v4_argument_invalid') from error
    require(value['unit'] == unit and value['origin'] == origin and value['uncertainty'] is None
            and value['population_id'] == selection['population_id']
            and value['method_id'] == 'mauve_v4_' + field + '_v1')
    _ids(value, ids)
    number = value['value']
    if fraction:
        n, d = value['numerator'], value['denominator']
        if n is not None: f.uint(n)
        if d is not None: f.uint(d)
        if value['state'] == 'available':
            require(n is not None and d is not None and 0 < d and n <= d and number == n / d)
    else:
        require(value['numerator'] is None and value['denominator'] is None)
        if number is not None: f.uint(number)
    return number


def _ref(value, document):
    f.shape(value, ('document_id', 'interval_index', 'segment_index'))
    require(value['document_id'] == document, 'selection_document_conflict')
    f.uint(value['interval_index']); f.uint(value['segment_index'])
    return value['interval_index'], value['segment_index']


def validate_mauve_v4_components(value: dict) -> dict:
    """Check saved relationships without recomputing alignments or source joins."""
    f.shape(value, ('schema_version', 'document_id', 'status', 'selection', 'member_segments',
                    'pair_segments', 'coverage', 'requirements', 'diagnostics'))
    require(value['schema_version'] == 'mauve_v4_segment_components_v1')
    selection = validate_mauve_v4_selection(value['selection'])
    require(value['document_id'] == selection['document_id'], 'selection_document_conflict')
    ids = reports(value)
    for field in ('member_segments', 'pair_segments', 'coverage'): f.array(value[field])
    members = [member(m) for m in selection['members']]
    chosen = {(r['interval_index'], r['segment_index']): r for r in selection['segments']}
    expected = [(key, m) for key in chosen for m in members]; observed = []; records = {}
    for row in value['member_segments']:
        f.shape(row, ('segment', 'member', 'state', 'native_start', 'strand', 'native_interval_0based_half_open',
            'symbols_origin', 'aligned_sequence', *MEMBER_COUNTS, 'source_comparison', 'evidence', 'requirement_ids'))
        key = _ref(row['segment'], value['document_id']); mi = member(row['member']); observed.append((key, mi))
        require(key in chosen and mi in members); records[(key, mi)] = row; _ids(row, ids)
        require(row['state'] in ('present', 'absent_zero', 'missing', 'incompatible'))
        require(row['symbols_origin'] in ('native_rows', 'source_extracted', 'unavailable'))
        require(row['source_comparison'] in ('match', 'mismatch', 'not_checked', 'not_applicable'))
        require(row['strand'] in ('+', '-', None))
        if row['native_start'] is not None:
            try:
                validate_native_number(row['native_start'])
            except ValueError as error:
                raise ValueError('mauve_v4_argument_invalid') from error
        if row['native_interval_0based_half_open'] is not None: interval(row['native_interval_0based_half_open'])
        numbers = {field: _cell(row[field], field, 'columns' if field in MEMBER_COUNTS[:2] else 'characters',
                               selection, ids) for field in MEMBER_COUNTS}
        count = interval_length(chosen[key]['column_ranges_0based_half_open'])
        require(numbers['selected_column_count'] == count)
        if numbers['alignment_columns'] is not None:
            require(all(b <= numbers['alignment_columns'] for a, b in chosen[key]['column_ranges_0based_half_open']))
        sequence = row['aligned_sequence']
        require((sequence is None) == (row['symbols_origin'] == 'unavailable'))
        if sequence is not None:
            f.text(sequence, empty=True)
            require(all(s in f.DNA for s in sequence))
            require(len(sequence) == numbers['alignment_columns'])
            require(all(numbers[name] is not None for name in MEMBER_COUNTS[2:]))
        if row['state'] == 'present':
            require(f.available(row['native_start']) and row['native_start']['value'] != 0
                    and row['native_interval_0based_half_open'] is not None)
            start = row['native_start']['value']; span = row['native_interval_0based_half_open']
            require(row['strand'] == ('+' if start > 0 else '-') and span[0] == abs(start) - 1)
            if sequence is not None: require(span[1] - span[0] == len(sequence.replace('-', '')))
            else: require(span[1] - span[0] == numbers['alignment_columns'])
        else:
            require(row['strand'] is None and row['native_interval_0based_half_open'] is None)
        if row['state'] == 'absent_zero':
            require(f.available(row['native_start']) and row['native_start']['value'] == 0
                    and numbers['selected_nongap_count'] == 0)
        if row['source_comparison'] in ('match', 'mismatch'):
            require(row['symbols_origin'] == 'native_rows' and row['state'] == 'present' and bool(row['evidence']))
        if row['symbols_origin'] == 'source_extracted':
            require(row['state'] == 'present' and row['source_comparison'] == 'not_applicable' and bool(row['evidence']))
        n, g = numbers['selected_nongap_count'], numbers['selected_gap_count']
        if n is not None and g is not None: require(n + g == count)
        categories = [numbers[name] for name in MEMBER_COUNTS[4:]]
        if all(n is not None for n in categories): require(n is not None and sum(categories) == numbers['selected_nongap_count'])
        if row['symbols_origin'] == 'unavailable' and row['state'] == 'present':
            require(numbers['selected_nongap_count'] == count and numbers['selected_gap_count'] == 0
                    and all(row[field]['state'] == 'missing' for field in MEMBER_COUNTS[4:]))
        if row['state'] in ('missing', 'incompatible'):
            require(sequence is None and all(numbers[field] is None for field in MEMBER_COUNTS[2:]))
    require(observed == expected)
    expected_pairs = [(key, (p['member_a']['index'], p['member_b']['index'])) for key in chosen for p in selection['pairs']]
    observed_pairs = []
    for row in value['pair_segments']:
        f.shape(row, ('segment', 'pair', 'state', 'counts', 'evidence', 'requirement_ids'))
        key = _ref(row['segment'], value['document_id']); pairs([row['pair']], members)
        pair = row['pair']['member_a']['index'], row['pair']['member_b']['index']; observed_pairs.append((key, pair))
        require(key in chosen); _ids(row, ids)
        require(row['state'] in ('available', 'not_coobserved', 'missing_symbols', 'incomplete', 'incompatible'))
        involved = [records[key, mi] for mi in pair]
        expected_state = ('incompatible' if any(r['state'] == 'incompatible' for r in involved) else
            'incomplete' if any(r['state'] == 'missing' for r in involved) else
            'not_coobserved' if any(r['state'] == 'absent_zero' for r in involved) else
            'missing_symbols' if any(r['aligned_sequence'] is None for r in involved) else 'available')
        require(row['state'] == expected_state)
        f.shape(row['counts'], (*PAIR_COUNTS, 'identity_fraction'))
        numbers = {name: _cell(row['counts'][name], name, 'columns', selection, ids) for name in PAIR_COUNTS}
        fraction = row['counts']['identity_fraction']; _cell(fraction, 'identity_fraction', 'fraction', selection, ids, fraction=True)
        if row['state'] == 'available':
            require(all(n is not None for n in numbers.values())
                and numbers['comparable_canonical'] == numbers['identical_canonical'] + numbers['substitutions']
                and sum(numbers[k] for k in PAIR_COUNTS[:-1]) == interval_length(chosen[key]['column_ranges_0based_half_open']))
            require(fraction['numerator'] == numbers['identical_canonical'] and fraction['denominator'] == numbers['comparable_canonical']
                    and fraction['state'] == ('available' if numbers['comparable_canonical'] else 'not_measured'))
            require(all(records[key, mi]['state'] == 'present' and records[key, mi]['aligned_sequence'] is not None for mi in pair))
        else:
            state = {'not_coobserved': 'not_measured', 'missing_symbols': 'missing', 'incomplete': 'truncated', 'incompatible': 'incompatible'}[row['state']]
            require(all(cell['state'] == state for cell in row['counts'].values()))
    require(observed_pairs == expected_pairs)
    require(len(value['coverage']) == len(members))
    for index, row in enumerate(value['coverage']):
        f.shape(row, ('member', 'placements', 'known_union_intervals', 'known_union_bases', 'placement_bases',
            'multiply_represented_bases', 'excess_placement_bases', 'denominator_kind', 'denominator_bases',
            'coverage_fraction', 'complement_intervals', 'complement_bases', 'population_state', 'evidence', 'requirement_ids'))
        mi = member(row['member']); _ids(row, ids); f.array(row['placements']); spans = []
        require(mi == members[index])
        require(row['denominator_kind'] == selection['denominator'])
        require(row['population_state'] in ('complete_selected', 'partial_selected', 'unknown'))
        seen = set(); placed_by_record = {}
        for placement in row['placements']:
            f.shape(placement, ('record', 'member', 'interval_0based_half_open', 'strand', 'evidence'))
            key = _ref(placement['record'], value['document_id'])
            require(key in chosen and member(placement['member']) == mi)
            interval(placement['interval_0based_half_open'], nonempty=True); evidence(placement['evidence'])
            source = records[key, mi]; span = placement['interval_0based_half_open']
            require(source['state'] == 'present' and placement['strand'] == source['strand']
                    and source['native_interval_0based_half_open'][0] <= span[0] < span[1] <= source['native_interval_0based_half_open'][1])
            fingerprint = (key, *span); require(fingerprint not in seen); seen.add(fingerprint); spans.append(span)
            placed_by_record[key] = placed_by_record.get(key, 0) + span[1] - span[0]
        require(row['known_union_intervals'] == union_intervals(spans))
        numbers = {}
        for name in ('known_union_bases', 'placement_bases', 'multiply_represented_bases', 'excess_placement_bases', 'denominator_bases', 'complement_bases'):
            origin = 'native_observation' if name == 'denominator_bases' and row['denominator_kind'] == 'native_declared_length' else 'calculated'
            numbers[name] = _cell(row[name], name, 'nucleotide_placements' if name in ('placement_bases', 'excess_placement_bases') else 'nucleotides', selection, ids, origin=origin)
        total, union = interval_length(spans), interval_length(row['known_union_intervals'])
        for key in chosen:
            known = records[key, mi]
            require(placed_by_record.get(key, 0) == (known['selected_nongap_count']['value'] if known['state'] == 'present' else 0))
        require(numbers['known_union_bases'] == union and numbers['placement_bases'] == total
                and numbers['multiply_represented_bases'] == multiplicity_bases(spans) and numbers['excess_placement_bases'] == total - union)
        fraction = row['coverage_fraction']; _cell(fraction, 'coverage_fraction', 'fraction', selection, ids, fraction=True)
        require(fraction['numerator'] == union and fraction['denominator'] == numbers['denominator_bases'])
        if any(records[key, mi]['state'] in ('missing', 'incompatible') for key in chosen):
            require(row['population_state'] != 'complete_selected')
        if row['denominator_kind'] == 'none':
            require(row['denominator_bases']['state'] == fraction['state'] == row['complement_bases']['state'] == 'not_measured')
        if fraction['state'] == 'available':
            require(row['population_state'] == 'complete_selected' and row['complement_intervals'] is not None)
            if row['denominator_kind'] == 'validated_staged_length':
                require(all(records[key, mi]['source_comparison'] != 'mismatch' for key in chosen))
        if row['complement_intervals'] is not None:
            length = numbers['denominator_bases']; require(length is not None)
            require(all(end <= length for start, end in row['known_union_intervals'])
                    and row['population_state'] == 'complete_selected'
                    and fraction['state'] == ('available' if length else 'not_measured'))
            require(row['complement_intervals'] == complement_intervals(row['known_union_intervals'], length)
                    and numbers['complement_bases'] == interval_length(row['complement_intervals']))
        else: require(numbers['complement_bases'] is None)
    return deepcopy(value)


def _cell_structure(value, field, unit, selection, ids, *, origin='calculated', fraction=False):
    """Validate a saved cell's meaning and bounds, without evaluating its formula."""
    try:
        validate_numeric_cell(value)
    except ValueError as error:
        raise ValueError('mauve_v4_argument_invalid') from error
    require(value['unit'] == unit and value['origin'] == origin and value['uncertainty'] is None
            and value['population_id'] == selection['population_id']
            and value['method_id'] == 'mauve_v4_' + field + '_v1')
    _ids(value, ids)
    number = value['value']
    if fraction:
        n, d = value['numerator'], value['denominator']
        if n is not None: f.uint(n)
        if d is not None: f.uint(d)
        if value['state'] == 'available':
            require(n is not None and d is not None and 0 < d and n <= d and 0 <= number <= 1)
    else:
        require(value['numerator'] is None and value['denominator'] is None)
        if number is not None: f.uint(number)
    return number


def _intervals_structure(value):
    """Check the stored canonical interval representation; never construct a union."""
    f.array(value)
    for span in value: interval(span, nonempty=True)
    require(all(a[1] < b[0] for a, b in zip(value, value[1:])))


def validate_mauve_v4_component_structure(value: dict) -> dict:
    """Check saved shapes and associations, not the correctness of their science.

    Original producer/content custody authenticates numbers on a saved host
    path. A structurally valid caller-authored value is not that authentication.
    Use validate_mauve_v4_components for full numerical producer verification.
    """
    f.shape(value, ('schema_version', 'document_id', 'status', 'selection', 'member_segments',
                    'pair_segments', 'coverage', 'requirements', 'diagnostics'))
    require(value['schema_version'] == 'mauve_v4_segment_components_v1')
    selection = validate_mauve_v4_selection(value['selection'])
    require(value['document_id'] == selection['document_id'], 'selection_document_conflict')
    ids = reports(value)
    for field in ('member_segments', 'pair_segments', 'coverage'): f.array(value[field])
    members = [member(m) for m in selection['members']]
    chosen = {(r['interval_index'], r['segment_index']): r for r in selection['segments']}
    expected = [(key, m) for key in chosen for m in members]; observed = []; records = {}
    for row in value['member_segments']:
        f.shape(row, ('segment', 'member', 'state', 'native_start', 'strand', 'native_interval_0based_half_open',
            'symbols_origin', 'aligned_sequence', *MEMBER_COUNTS, 'source_comparison', 'evidence', 'requirement_ids'))
        key = _ref(row['segment'], value['document_id']); mi = member(row['member']); observed.append((key, mi))
        require(key in chosen and mi in members); records[(key, mi)] = row; _ids(row, ids)
        require(row['state'] in ('present', 'absent_zero', 'missing', 'incompatible'))
        require(row['symbols_origin'] in ('native_rows', 'source_extracted', 'unavailable'))
        require(row['source_comparison'] in ('match', 'mismatch', 'not_checked', 'not_applicable'))
        require(row['strand'] in ('+', '-', None))
        if row['native_start'] is not None:
            try:
                validate_native_number(row['native_start'])
            except ValueError as error:
                raise ValueError('mauve_v4_argument_invalid') from error
        if row['native_interval_0based_half_open'] is not None: interval(row['native_interval_0based_half_open'])
        numbers = {field: _cell_structure(row[field], field, 'columns' if field in MEMBER_COUNTS[:2] else 'characters',
                                         selection, ids) for field in MEMBER_COUNTS}
        count = numbers['selected_column_count']
        require(row['selected_column_count']['state'] == 'available')
        if numbers['alignment_columns'] is not None:
            require(count <= numbers['alignment_columns'] and all(
                b <= numbers['alignment_columns'] for a, b in chosen[key]['column_ranges_0based_half_open']))
        require(all(n is None or n <= count for name, n in numbers.items() if name in MEMBER_COUNTS[2:]))
        sequence = row['aligned_sequence']
        require((sequence is None) == (row['symbols_origin'] == 'unavailable'))
        if sequence is not None:
            f.text(sequence, empty=True)
            require(all(s in f.DNA for s in sequence) and len(sequence) == numbers['alignment_columns'])
            require(all(numbers[name] is not None for name in MEMBER_COUNTS[2:]))
        if row['state'] == 'present':
            require(f.available(row['native_start']) and row['native_start']['value'] != 0
                    and row['native_interval_0based_half_open'] is not None)
            start = row['native_start']['value']; span = row['native_interval_0based_half_open']
            # This checks the stored coordinate convention, not a residue count.
            require(row['strand'] == ('+' if start > 0 else '-') and span[0] == abs(start) - 1)
        else:
            require(row['strand'] is None and row['native_interval_0based_half_open'] is None)
        if row['state'] == 'absent_zero':
            require(f.available(row['native_start']) and row['native_start']['value'] == 0
                    and numbers['selected_nongap_count'] == 0)
        if row['source_comparison'] in ('match', 'mismatch'):
            require(row['symbols_origin'] == 'native_rows' and row['state'] == 'present' and bool(row['evidence']))
        if row['symbols_origin'] == 'source_extracted':
            require(row['state'] == 'present' and row['source_comparison'] == 'not_applicable' and bool(row['evidence']))
        if row['symbols_origin'] == 'unavailable' and row['state'] == 'present':
            require(numbers['selected_nongap_count'] == count and numbers['selected_gap_count'] == 0
                    and all(row[field]['state'] == 'missing' for field in MEMBER_COUNTS[4:]))
        if row['state'] in ('missing', 'incompatible'):
            state = 'truncated' if row['state'] == 'missing' else 'incompatible'
            require(sequence is None and all(row[field]['state'] == state for field in MEMBER_COUNTS[2:]))
    require(observed == expected)
    expected_pairs = [(key, (p['member_a']['index'], p['member_b']['index'])) for key in chosen for p in selection['pairs']]
    observed_pairs = []
    for row in value['pair_segments']:
        f.shape(row, ('segment', 'pair', 'state', 'counts', 'evidence', 'requirement_ids'))
        key = _ref(row['segment'], value['document_id']); pairs([row['pair']], members)
        pair = row['pair']['member_a']['index'], row['pair']['member_b']['index']; observed_pairs.append((key, pair))
        require(key in chosen); _ids(row, ids)
        require(row['state'] in ('available', 'not_coobserved', 'missing_symbols', 'incomplete', 'incompatible'))
        involved = [records[key, mi] for mi in pair]
        expected_state = ('incompatible' if any(r['state'] == 'incompatible' for r in involved) else
            'incomplete' if any(r['state'] == 'missing' for r in involved) else
            'not_coobserved' if any(r['state'] == 'absent_zero' for r in involved) else
            'missing_symbols' if any(r['aligned_sequence'] is None for r in involved) else 'available')
        require(row['state'] == expected_state)
        f.shape(row['counts'], (*PAIR_COUNTS, 'identity_fraction'))
        numbers = {name: _cell_structure(row['counts'][name], name, 'columns', selection, ids) for name in PAIR_COUNTS}
        fraction = row['counts']['identity_fraction']
        _cell_structure(fraction, 'identity_fraction', 'fraction', selection, ids, fraction=True)
        if row['state'] == 'available':
            require(all(n is not None for n in numbers.values()))
            require(fraction['numerator'] == numbers['identical_canonical'] and fraction['denominator'] == numbers['comparable_canonical']
                    and fraction['state'] == ('available' if numbers['comparable_canonical'] else 'not_measured'))
            require(all(n <= involved[0]['selected_column_count']['value'] for n in numbers.values()))
        else:
            state = {'not_coobserved': 'not_measured', 'missing_symbols': 'missing', 'incomplete': 'truncated', 'incompatible': 'incompatible'}[row['state']]
            require(all(cell['state'] == state for cell in row['counts'].values()))
    require(observed_pairs == expected_pairs)
    require(len(value['coverage']) == len(members))
    for index, row in enumerate(value['coverage']):
        f.shape(row, ('member', 'placements', 'known_union_intervals', 'known_union_bases', 'placement_bases',
            'multiply_represented_bases', 'excess_placement_bases', 'denominator_kind', 'denominator_bases',
            'coverage_fraction', 'complement_intervals', 'complement_bases', 'population_state', 'evidence', 'requirement_ids'))
        mi = member(row['member']); _ids(row, ids); f.array(row['placements'])
        require(mi == members[index] and row['denominator_kind'] == selection['denominator'])
        require(row['population_state'] in ('complete_selected', 'partial_selected', 'unknown'))
        seen = set()
        for placement in row['placements']:
            f.shape(placement, ('record', 'member', 'interval_0based_half_open', 'strand', 'evidence'))
            key = _ref(placement['record'], value['document_id'])
            require(key in chosen and member(placement['member']) == mi)
            interval(placement['interval_0based_half_open'], nonempty=True); evidence(placement['evidence'])
            source = records[key, mi]; span = placement['interval_0based_half_open']
            require(source['state'] == 'present' and placement['strand'] == source['strand']
                    and source['native_interval_0based_half_open'][0] <= span[0] < span[1] <= source['native_interval_0based_half_open'][1])
            fingerprint = (key, *span); require(fingerprint not in seen); seen.add(fingerprint)
        _intervals_structure(row['known_union_intervals'])
        numbers = {}
        for name in ('known_union_bases', 'placement_bases', 'multiply_represented_bases', 'excess_placement_bases', 'denominator_bases', 'complement_bases'):
            origin = 'native_observation' if name == 'denominator_bases' and row['denominator_kind'] == 'native_declared_length' else 'calculated'
            numbers[name] = _cell_structure(row[name], name, 'nucleotide_placements' if name in ('placement_bases', 'excess_placement_bases') else 'nucleotides', selection, ids, origin=origin)
        require(all(row[name]['state'] == 'available' for name in (
            'known_union_bases', 'placement_bases', 'multiply_represented_bases', 'excess_placement_bases')))
        require(numbers['known_union_bases'] <= numbers['placement_bases']
                and numbers['multiply_represented_bases'] <= numbers['known_union_bases']
                and numbers['excess_placement_bases'] <= numbers['placement_bases'])
        fraction = row['coverage_fraction']; _cell_structure(fraction, 'coverage_fraction', 'fraction', selection, ids, fraction=True)
        require(fraction['numerator'] == numbers['known_union_bases'] and fraction['denominator'] == numbers['denominator_bases'])
        if any(records[key, mi]['state'] in ('missing', 'incompatible') for key in chosen):
            require(row['population_state'] != 'complete_selected')
        if row['denominator_kind'] == 'none':
            require(row['denominator_bases']['state'] == fraction['state'] == row['complement_bases']['state'] == 'not_measured')
        if fraction['state'] == 'available':
            require(row['population_state'] == 'complete_selected' and row['complement_intervals'] is not None)
            if row['denominator_kind'] == 'validated_staged_length':
                require(all(records[key, mi]['source_comparison'] != 'mismatch' for key in chosen))
        if row['complement_intervals'] is not None:
            _intervals_structure(row['complement_intervals'])
            length = numbers['denominator_bases']; require(length is not None)
            require(all(end <= length for start, end in row['known_union_intervals'])
                    and all(end <= length for start, end in row['complement_intervals'])
                    and row['population_state'] == 'complete_selected'
                    and fraction['state'] == ('available' if length else 'not_measured')
                    and row['complement_bases']['state'] == 'available' and numbers['complement_bases'] <= length)
        else: require(numbers['complement_bases'] is None)
    return deepcopy(value)


__all__ = ['validate_mauve_v4_selection', 'validate_mauve_v4_components',
           'validate_mauve_v4_component_structure']
