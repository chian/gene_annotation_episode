"""Numerical populations, exact interval arithmetic and saved replay tests."""
from copy import deepcopy
import builtins
import json
import math
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.xmfa_calculators import xmfa_alignment_components, xmfa_interval_coverage
from gene_annotation_episode.xmfa_calculation_contracts import (
    validate_xmfa_selection, validate_xmfa_alignment_components, validate_xmfa_coverage_components)
from test_xmfa_coordinates import toy, concat_case, original, cell
from test_xmfa_sources import native_document, supplied, bind, BASE


def selection(document, members=None, blocks=None, *, completeness='complete'):
    if members is None:
        members = list(dict.fromkeys(row['member_number']['value'] for block in document['blocks']
                   for row in block['records'] if row['member_number'] and row['member_number']['state'] == 'available'))
    if blocks is None:
        blocks = [{'block_index': block['block_index'], 'columns_0based': list(range(max(
            (len(row['sequence']) for row in block['records']), default=0)))} for block in document['blocks']]
    return {'population_id': 'explicit-test-selection', 'document_id': document['document_id'],
        'member_numbers': members, 'block_columns': blocks, 'completeness': completeness, 'evidence': []}


def alignment(document, selected=None, pairs=(), policy='uppercase'):
    return xmfa_alignment_components(document, selection=selected or selection(document),
        selected_pairs=pairs, case_policy=policy)


def coverage(document, binding=None, selected=None, basis='represented'):
    return xmfa_interval_coverage(document, selection=selected or selection(document), bindings=binding, basis=basis)


def values(rows, field):
    return [row[field]['value'] for row in rows]


def test_combined_first_block_pair_counts_denominators_and_zero_members():
    document = native_document()
    rows = document['blocks'][0]['records']
    assert [r['gapped_character_count'] for r in rows] == [49, 49, 49]
    assert [r['nongap_character_count'] for r in rows] == [48, 0, 47]
    assert [r['span_matches_nongap'] for r in rows] == [True, True, True]
    result = alignment(document, pairs=((1, 3), (1, 2)))
    block = result['blocks'][0]; pair = block['pairs'][0]
    assert block['present_members'] == [1, 3] and block['zero_members'] == [2]
    assert block['selected_column_count']['value'] == 49
    assert (pair['identical_canonical']['value'], pair['substitutions']['value'], pair['comparable_canonical']['value']) == (39, 7, 46)
    assert values([pair], 'a_only_gap') == [1] and values([pair], 'b_only_gap') == [2]
    assert pair['identity_fraction']['value'] == 39 / 46
    assert (pair['identity_fraction']['numerator'], pair['identity_fraction']['denominator']) == (39, 46)
    assert block['pairs'][1]['state'] == 'not_coobserved'
    assert all(block['pairs'][1][field]['value'] is None for field in ('both_gap', 'a_only_gap', 'identity_fraction'))
    site = block['sites'][0]
    assert site['present_member_count']['value'] == 2 and site['absent_member_count']['value'] == 1
    assert site['symbol_counts'][0]['symbol'] == 'A' and site['symbol_counts'][0]['count']['value'] == 2
    assert site['gap_count']['value'] == 0 and site['literal_entropy_bits']['value'] == 0
    assert site['symbol_counts'][0]['count']['method_id'] == 'xmfa_symbol_count_v1'
    # An explicit zero-member row is not forty-nine artificial gap votes.
    assert sum(s['gap_count']['value'] for s in block['sites']) == 3
    assert result['blocks'][1]['omitted_members'] == [2, 3]


@pytest.mark.parametrize('basis,counts,unions', [
    ('represented', [50, 41, 49], [[[0, 50]], [[0, 41]], [[0, 49]]]),
    ('multi_member_block', [48, 0, 47], [[[1, 49]], [], [[1, 48]]]),
    ('cooccupied_column', [46, 0, 46], [[[1, 38], [40, 49]], [], [[1, 27], [28, 48]]]),
])
def test_all_six_combined_blocks_have_distinct_exact_coverage_bases(basis, counts, unions):
    document = native_document(); bindings = bind(document)
    result = coverage(document, bindings, basis=basis)
    assert values(result['members'], 'source_length') == [50, 41, 49]
    assert values(result['members'], 'known_union_bases') == counts
    assert [m['known_union_intervals'] for m in result['members']] == unions
    assert values(result['members'], 'selected_coverage_fraction') == [n / d for n, d in zip(counts, (50, 41, 49))]
    assert values(result['members'], 'placement_bases') == counts
    assert values(result['members'], 'multiply_represented_bases') == [0, 0, 0]
    assert values(result['members'], 'complement_bases') == [d - n for n, d in zip(counts, (50, 41, 49))]
    for member in result['members']:
        assert member['placement_bases']['unit'] == 'nucleotide_placements'
        assert member['known_union_bases']['unit'] == 'nucleotides'
        assert member['selected_coverage_fraction']['method_id'] == f'xmfa_{basis}_selected_coverage_fraction_v1'
        assert member['membership_completeness'] == 'complete'


def test_separate_native_files_retain_native_number_order_and_full_coverage():
    document = native_document('separate.xmfa')
    result = coverage(document, bind(document, supplied('multiple_files_concatenated')))
    assert values(result['members'], 'known_union_bases') == [50, 49, 41]
    assert values(result['members'], 'selected_coverage_fraction') == [1, 1, 1]
    # No sorting by file/name may swap canFam2 and mm9.
    selected = selection(document, [3, 1])
    result = coverage(document, bind(document, supplied('multiple_files_concatenated')), selected)
    assert [m['member_number'] for m in result['members']] == [3, 1]
    assert values(result['members'], 'source_length') == [41, 50]


def test_literal_and_canonical_entropy_case_policy_and_zero_comparable_are_distinct():
    document, _ = toy(b'#FormatVersion Mauve1\n>1:1-3 +\naRN-\n>2:1-3 +\nATN-\n=\n')
    preserve = alignment(document, pairs=((1, 2),), policy='preserve')['blocks'][0]
    upper = alignment(document, pairs=((1, 2),), policy='uppercase')['blocks'][0]
    assert preserve['sites'][0]['literal_entropy_bits']['value'] == 1
    assert upper['sites'][0]['literal_entropy_bits']['value'] == 0
    assert preserve['sites'][0]['other_count']['value'] == 1
    assert upper['sites'][0]['canonical_count']['value'] == 2
    assert preserve['pairs'][0]['identity_fraction']['state'] == 'not_measured'
    assert preserve['pairs'][0]['identity_fraction']['denominator'] == 0
    assert upper['pairs'][0]['identical_canonical']['value'] == 1
    assert upper['pairs'][0]['identity_fraction']['value'] == 1
    assert upper['pairs'][0]['ambiguous_or_other']['value'] == 2
    assert upper['pairs'][0]['both_gap']['value'] == 1
    assert upper['sites'][2]['canonical_entropy_bits']['state'] == 'not_measured'


def test_selected_column_order_and_full_row_offsets_do_not_reindex_positions():
    document, bindings = toy(b'#FormatVersion Mauve1\n#Sequence1File x.fa\n'
        b'>1:1-4 -\nA-CGT\n=\n', [('x.fa', b'>x\nACGT\n')])
    chosen = selection(document, [1], [{'block_index': 0, 'columns_0based': [4, 0, 3]}])
    result = coverage(document, bindings, chosen)['members'][0]
    assert result['known_union_intervals'] == [[0, 2], [3, 4]]
    assert result['selected_coverage_fraction']['value'] == 3 / 4
    assert result['complement_intervals'] == [[2, 3]]
    assert [s['column_0based'] for s in alignment(document, chosen)['blocks'][0]['sites']] == [4, 0, 3]
    # Selecting every residue in a shuffled order still gives one maximal run.
    chosen['block_columns'][0]['columns_0based'] = [4, 0, 2, 3]
    result = coverage(document, bindings, chosen)['members'][0]
    assert result['known_union_intervals'] == [[0, 4]] and len(result['placements']) == 1


def test_triple_overlap_distinguishes_union_multiply_covered_and_excess_placements():
    document, bindings = toy(b'#FormatVersion Mauve1\n#Sequence1File x.fa\n'
        b'>1:1-4 +\nACGT\n=\n>1:2-5 +\nCGTA\n=\n>1:3-4 +\nGT\n=\n', [('x.fa', b'>x\nACGTAA\n')])
    result = coverage(document, bindings)
    row = result['members'][0]
    assert len(row['placements']) == 3
    assert row['known_union_intervals'] == [[0, 5]]
    assert [row[f]['value'] for f in ('known_union_bases', 'placement_bases', 'multiply_represented_bases', 'excess_placement_bases')] == [5, 10, 3, 5]
    assert row['selected_coverage_fraction']['value'] == 5 / 6
    assert row['complement_intervals'] == [[5, 6]]
    assert any(d['code'] == 'xmfa_overlapping_placement' for d in result['diagnostics'])


def test_distinct_original_occurrences_and_concat_scope_have_independent_denominators():
    document, bindings = concat_case()
    result = coverage(document, bindings)
    left = result['members'][0]['original_coverage']
    assert [r['original_member']['occurrence_index'] for r in left] == [0, 1]
    assert [r['known_union_intervals'] for r in left] == [[[11, 13]], [[2, 4]]]
    assert values(left, 'coverage_fraction') == [2 / 100, 2 / 8]
    assert all(r['mapping_completeness'] == 'complete' for r in left)
    assert left[0]['known_union_bases']['method_id'] == 'xmfa_represented_original_known_union_bases_v1'
    right = result['members'][1]['original_coverage'][0]
    assert right['known_union_intervals'] == [[2, 6]] and right['coverage_fraction']['value'] == 0.4


def test_partial_original_map_preserves_union_but_not_full_fraction():
    document, bindings = concat_case([original('left.fa', 'row:0', 0, 2)])
    row = coverage(document, bindings)['members'][0]['original_coverage'][0]
    assert row['known_union_intervals'] == [[11, 12]]
    assert row['known_union_bases']['value'] == 1
    assert row['mapping_completeness'] == 'partial' and row['coverage_fraction']['value'] is None


def test_other_occurrence_map_accounts_for_selected_bases_in_same_component():
    maps = [original('left.fa', 'row:0', 0, 2, occurrence=0),
            original('left.fa', 'row:0', 2, 3, occurrence=1, original_start=30)]
    doc, binding = concat_case(maps)
    originals = coverage(doc, binding)['members'][0]['original_coverage']
    assert values(originals, 'known_union_bases') == [1, 1]
    assert all(row['mapping_completeness'] == 'complete' for row in originals)
    assert values(originals, 'coverage_fraction') == [0.01, 0.01]


def test_original_conflict_preserves_independent_occurrence_and_invalidates_only_its_denominator():
    maps = [original('left.fa', 'row:0', 0, 3, occurrence=0),
            original('left.fa', 'row:0', 0, 3, occurrence=0, length=101),
            original('left.fa', 'row:0', 0, 3, occurrence=1)]
    doc, binding = concat_case(maps)
    originals = coverage(doc, binding)['members'][0]['original_coverage']
    assert originals[0]['original_length']['state'] == 'incompatible'
    assert originals[0]['coverage_fraction']['state'] == 'incompatible'
    assert originals[1]['mapping_completeness'] == 'complete'
    assert originals[1]['coverage_fraction']['value'] == 2 / 100


def test_unknown_source_length_preserves_native_union_without_implying_fraction():
    result = coverage(native_document())
    assert values(result['members'], 'known_union_bases') == [50, 41, 49]
    assert values(result['members'], 'source_length') == [None, None, None]
    assert values(result['members'], 'selected_coverage_fraction') == [None, None, None]
    assert all(row['complement_intervals'] is None for row in result['members'])


def test_wrong_source_check_blocks_fraction_and_reused_stale_match_is_rejected():
    document = native_document(); inputs = supplied()
    inputs['files'][0]['records'][0]['sequence'] = 'A' + inputs['files'][0]['records'][0]['sequence'][1:]
    bindings = bind(document, inputs)
    result = coverage(document, bindings)
    assert result['members'][0]['known_union_bases']['value'] == 50
    assert result['members'][0]['selected_coverage_fraction']['state'] == 'incompatible'
    assert result['members'][1]['selected_coverage_fraction']['value'] == 1
    stale = bind(document); stale['members'][0]['source_sequence'] = bindings['members'][0]['source_sequence']
    with pytest.raises(ValueError, match='source_checks_conflict'):
        coverage(document, stale)


def test_out_of_source_bounds_are_not_clipped():
    document, bindings = toy(b'#FormatVersion Mauve1\n#Sequence1File x.fa\n>1:1-4 +\nACGT\n=\n',
                             [('x.fa', b'>x\nACG\n')])
    member = coverage(document, bindings)['members'][0]
    assert member['known_union_intervals'] == [[0, 4]]
    assert member['source_length']['value'] == 3
    assert member['selected_coverage_fraction']['state'] == 'incompatible'
    assert member['complement_intervals'] is None


def test_duplicate_selected_member_is_conflict_not_two_votes_or_omission():
    document, _ = toy(b'#FormatVersion Mauve1\n>1:1-2 +\nAC\n>1:1-2 +\nAC\n>2:1-2 +\nAT\n=\n')
    block = alignment(document, pairs=((1, 2),))['blocks'][0]
    assert block['conflicting_members'] == [1] and block['omitted_members'] == []
    assert len(block['record_refs']) == 3
    assert block['present_member_count']['value'] is None
    assert block['sites'][0]['canonical_count']['state'] == 'incompatible'
    assert block['pairs'][0]['state'] == 'incompatible'
    result = coverage(document)
    assert result['members'][0]['known_union_bases']['value'] == 0
    assert result['members'][1]['known_union_bases']['value'] == 2
    # Selecting the independent row alone defines a narrower valid population.
    narrower = alignment(document, selection(document, [2]))['blocks'][0]
    assert narrower['present_member_count']['value'] == 1


@pytest.mark.parametrize('bad', [b'>2:1-4 +\nACG\n', b'>2:0-3 +\nACG\n', b'>2:1-3 +\nA?G\n'])
def test_invalid_identifiable_selected_rows_cannot_improve_denominator(bad):
    doc, _ = toy(b'#FormatVersion Mauve1\n>1:1-3 +\nACG\n' + bad + b'=\n')
    result = alignment(doc)['blocks'][0]
    assert result['conflicting_members'] == [2] and result['omitted_members'] == []
    assert all(s['present_member_count']['state'] == 'incompatible' for s in result['sites'])


def test_ragged_coverage_uses_actual_formula_dependencies():
    doc, binding = toy(b'#FormatVersion Mauve1\n#Sequence1File a.fa\n#Sequence2File b.fa\n'
        b'>1:1-3 +\nACG\n>2:1-2 +\nAC\n=\n', [('a.fa', b'>a\nACG\n'), ('b.fa', b'>b\nAC\n')])
    chosen = selection(doc, [1, 2], [{'block_index': 0, 'columns_0based': [0, 1]}])
    assert alignment(doc, chosen)['blocks'][0]['sites'][0]['canonical_count']['state'] == 'incompatible'
    assert values(coverage(doc, binding, chosen)['members'], 'selected_coverage_fraction') == [2 / 3, 1]
    assert values(coverage(doc, binding, chosen, 'multi_member_block')['members'], 'selected_coverage_fraction') == [2 / 3, 1]
    cooccupied = coverage(doc, binding, chosen, 'cooccupied_column')
    assert values(cooccupied['members'], 'selected_coverage_fraction') == [None, None]
    assert all(m['selected_coverage_fraction']['state'] == 'incompatible' for m in cooccupied['members'])


def test_zero_omitted_and_empty_zero_never_make_artificial_gap_rows():
    doc, _ = toy(b'#FormatVersion Mauve1\n>1:0-0 +\n\n>2:1-2 +\nAC\n>3:0-0 -\n--\n=\n>4:1-1 +\nT\n=\n')
    block = alignment(doc, selection(doc, [1, 2, 3, 4]), pairs=((2, 3),))['blocks'][0]
    assert block['present_members'] == [2] and block['zero_members'] == [1, 3] and block['omitted_members'] == [4]
    assert values(block['sites'], 'gap_count') == [0, 0]
    assert values(block['sites'], 'absent_member_count') == [3, 3]
    assert block['pairs'][0]['state'] == 'not_coobserved'


def test_partial_selection_and_truncated_document_retain_known_union_and_narrower_valid_subset():
    doc, binding = toy(b'#FormatVersion Mauve1\n#Sequence1File x.fa\n>1:1-2 +\nAC\n=\n>1:3-4 +\nGT\n',
                       [('x.fa', b'>x\nACGT\n')])
    row = coverage(doc, binding)['members'][0]
    assert row['known_union_bases']['value'] == 4
    assert row['selected_coverage_fraction']['state'] == 'truncated'
    assert row['membership_completeness'] == 'truncated'
    chosen = selection(doc, [1], [{'block_index': 0, 'columns_0based': [0, 1]}])
    row = coverage(doc, binding, chosen)['members'][0]
    assert row['selected_coverage_fraction']['value'] == 0.5
    chosen['completeness'] = 'partial'
    row = coverage(doc, binding, chosen)['members'][0]
    assert row['known_union_bases']['value'] == 2 and row['selected_coverage_fraction']['state'] == 'truncated'


def test_larger_native_and_abbreviated_output_keep_native_measurements_separate():
    doc = native_document('simple.xmfa')
    result = coverage(doc)
    assert [len(b['records']) for b in doc['blocks']] == [2, 2, 1, 1, 1]
    assert values(result['members'], 'known_union_bases') == [14910, 12880]
    assert all(m['source_length']['state'] == 'missing' for m in result['members'])
    assert any(m['known_union_bases']['value'] > 0 for m in result['members'])
    short = native_document('simple_short.xmfa')
    measured = coverage(short)
    assert all(m['selected_coverage_fraction']['value'] is None for m in measured['members'])
    assert all(m['known_union_bases']['value'] == 0 for m in measured['members'])


@pytest.mark.parametrize('pairs', [((1, 1),), ((1, 3), (3, 1)), ((1, 99),), ([1, 3],), [[1, 3]]])
def test_pair_selection_is_explicit_unique_unordered_and_within_members(pairs):
    with pytest.raises(ValueError, match='xmfa_'):
        alignment(native_document(), pairs=pairs)


@pytest.mark.parametrize('change', ['foreign_document', 'duplicate_member', 'unknown_member', 'duplicate_block',
    'duplicate_column', 'outside_column', 'outside_block', 'extra_key', 'bool_member'])
def test_selection_saved_and_document_bound_contracts_reject_misuse(change):
    doc = native_document(); chosen = selection(doc)
    if change == 'foreign_document': chosen['document_id'] = 'foreign'
    if change == 'duplicate_member': chosen['member_numbers'].append(1)
    if change == 'unknown_member': chosen['member_numbers'].append(999)
    if change == 'duplicate_block': chosen['block_columns'].append(deepcopy(chosen['block_columns'][0]))
    if change == 'duplicate_column': chosen['block_columns'][0]['columns_0based'].append(0)
    if change == 'outside_column': chosen['block_columns'][0]['columns_0based'].append(49)
    if change == 'outside_block': chosen['block_columns'][0]['block_index'] = 6
    if change == 'extra_key': chosen['unknown'] = 0
    if change == 'bool_member': chosen['member_numbers'][0] = True
    for function in (alignment, coverage):
        with pytest.raises(ValueError, match='xmfa_'):
            if function is alignment: function(doc, chosen)
            else: function(doc, selected=chosen)


@pytest.mark.parametrize('change', ['count', 'fraction', 'method', 'unit', 'symbol', 'entropy', 'pair_order', 'requirement'])
def test_alignment_validator_checks_full_numerical_relationships(change):
    doc = native_document(); result = alignment(doc, pairs=((1, 3),))
    site = result['blocks'][0]['sites'][0]; pair = result['blocks'][0]['pairs'][0]
    if change == 'count': pair['comparable_canonical']['value'] = 47
    if change == 'fraction': pair['identity_fraction']['value'] = 1
    if change == 'method': site['gap_count']['method_id'] = 'made_up'
    if change == 'unit': site['canonical_count']['unit'] = 'members'
    if change == 'symbol': site['symbol_counts'].append(deepcopy(site['symbol_counts'][0]))
    if change == 'entropy': site['literal_entropy_bits']['value'] = 1
    if change == 'pair_order': pair['member_a'] = 3
    if change == 'requirement': site['gap_count']['requirement_ids'] = ['unknown']
    with pytest.raises(ValueError, match='xmfa_'):
        validate_xmfa_alignment_components(result)


@pytest.mark.parametrize('change', ['union', 'placement', 'excess', 'multiply', 'complement', 'fraction', 'unit', 'population'])
def test_coverage_validator_checks_stored_intervals_counts_and_denominators(change):
    doc = native_document(); result = coverage(doc, bind(doc)); row = result['members'][0]
    if change == 'union': row['known_union_intervals'] = [[0, 49]]
    if change == 'placement': row['placements'].append(deepcopy(row['placements'][0]))
    if change == 'excess': row['excess_placement_bases']['value'] = 2
    if change == 'multiply': row['multiply_represented_bases']['value'] = 2
    if change == 'complement': row['complement_intervals'] = [[49, 50]]
    if change == 'fraction': row['selected_coverage_fraction']['denominator'] = 49
    if change == 'unit': row['placement_bases']['unit'] = 'nucleotides'
    if change == 'population': row['source_length']['population_id'] = 'other'
    with pytest.raises(ValueError, match='xmfa_'):
        validate_xmfa_coverage_components(result)


def test_saved_recalculation_changes_only_explicit_parameters_with_io_and_parser_disabled(monkeypatch):
    doc = native_document(); bindings = bind(doc); chosen = selection(doc)
    outputs = [alignment(doc, chosen, pairs=((1, 3),))] + [coverage(doc, bindings, chosen, basis) for basis in (
        'represented', 'multi_member_block', 'cooccupied_column')]
    saved_doc, saved_binding, saved_selection = json.loads(json.dumps([doc, bindings, chosen]))
    before = deepcopy((saved_doc, saved_binding, saved_selection))
    def forbidden(*args, **kwargs):
        raise AssertionError('Saved recalculation cannot acquire or parse native inputs')
    with monkeypatch.context() as locked:
        for target, name in ((builtins, 'open'), (Path, 'open'), (Path, 'read_bytes'),
                             (socket, 'socket'), (subprocess, 'Popen')):
            locked.setattr(target, name, forbidden)
        locked.setattr('gene_annotation_episode.xmfa_formats.parse_mauve_xmfa', forbidden)
        locked.setattr('gene_annotation_episode.xmfa_sources.bind_xmfa_sources', forbidden)
        assert alignment(saved_doc, saved_selection, pairs=((1, 3),)) == outputs[0]
        for expected in outputs[1:]:
            assert coverage(saved_doc, saved_binding, saved_selection, expected['parameters']['basis']) == expected
            assert validate_xmfa_coverage_components(json.loads(json.dumps(expected))) == expected
        assert validate_xmfa_alignment_components(json.loads(json.dumps(outputs[0]))) == outputs[0]
        assert validate_xmfa_selection(saved_selection) == chosen
    assert (saved_doc, saved_binding, saved_selection) == before
    detached = validate_xmfa_alignment_components(outputs[0]); detached['selection']['member_numbers'].append(999)
    assert outputs[0]['selection']['member_numbers'] == [1, 2, 3]


def test_literal_entropy_includes_observed_gap_and_canonical_entropy_has_own_denominator():
    doc, _ = toy(b'#FormatVersion Mauve1\n>1:1-2 +\nAC\n>2:1-2 +\nAC\n'
                 b'>3:1-2 +\nGC\n>4:1-1 +\n-T\n=\n')
    site = alignment(doc)['blocks'][0]['sites'][0]
    assert site['literal_entropy_bits']['value'] == 1.5
    expected = -(2 / 3 * math.log2(2 / 3) + 1 / 3 * math.log2(1 / 3))
    assert site['canonical_entropy_bits']['value'] == expected
    assert site['canonical_majority_fraction']['value'] == 2 / 3
    assert (site['gap_count']['value'], site['canonical_count']['value'], site['present_member_count']['value']) == (1, 3, 4)


def test_all_zero_empty_source_has_measured_zero_counts_and_unmeasured_zero_denominator():
    doc, binding = toy(b'#FormatVersion Mauve1\n#Sequence1File x.fa\n>1:0-0 +\n--\n=\n', [('x.fa', b'>x\n')])
    row = coverage(doc, binding)['members'][0]
    assert row['source_length']['value'] == 0
    assert row['known_union_bases']['value'] == row['complement_bases']['value'] == 0
    assert row['selected_coverage_fraction']['value'] is None
    assert row['selected_coverage_fraction']['state'] == 'not_measured'
    assert row['selected_coverage_fraction']['numerator'] == row['selected_coverage_fraction']['denominator'] == 0
    site = alignment(doc)['blocks'][0]['sites'][0]
    assert site['present_member_count']['value'] == site['gap_count']['value'] == 0
    assert site['absent_member_count']['value'] == 1
    assert site['literal_entropy_bits']['state'] == 'not_measured'


def test_header_only_document_does_not_establish_completed_negative_coverage():
    doc, binding = toy(b'#FormatVersion Mauve1\n#Sequence1File x.fa\n', [('x.fa', b'>x\nAC\n')])
    chosen = selection(doc, [1])
    assert alignment(doc, chosen)['status'] == 'partial'
    row = coverage(doc, binding, chosen)['members'][0]
    assert row['known_union_bases']['value'] == 0
    assert row['membership_completeness'] == 'unknown'
    assert row['selected_coverage_fraction']['value'] is None and row['complement_intervals'] is None


def test_empty_selected_columns_are_a_complete_explicit_subset_of_a_readable_document():
    doc = native_document(); chosen = selection(doc, [1], [{'block_index': 0, 'columns_0based': []}])
    row = coverage(doc, bind(doc), chosen)['members'][0]
    assert row['selected_coverage_fraction']['value'] == 0
    assert row['complement_intervals'] == [[0, 50]]
    assert alignment(doc, chosen)['blocks'][0]['sites'] == []


def test_source_failure_cannot_leave_original_fraction_available():
    maps = [original('left.fa', 'row:0', 0, 3)]
    doc, binding = concat_case(maps)
    # Regenerate the binding from an independently supplied mismatching input,
    # rather than falsifying its saved match flag.
    data = (b'#FormatVersion Mauve1\n#Sequence1File left.fa\n>1:1-4 +\nACGT\n=\n')
    doc, binding = toy(data, [('left.fa', b'>x\nACG\n')], original_maps=maps)
    row = coverage(doc, binding)['members'][0]
    assert row['selected_coverage_fraction']['state'] == 'incompatible'
    assert row['original_coverage'][0]['coverage_fraction']['state'] == 'incompatible'
    assert row['original_coverage'][0]['known_union_bases']['value'] == 0


def test_consistent_overlapping_original_maps_do_not_double_count_original_bases():
    maps = [original('left.fa', 'row:0', 0, 3, transformation='whole'),
            original('left.fa', 'row:0', 1, 3, original_start=11, transformation='overlap')]
    doc, binding = concat_case(maps)
    row = coverage(doc, binding)['members'][0]['original_coverage'][0]
    assert row['known_union_intervals'] == [[11, 13]]
    assert row['known_union_bases']['value'] == 2 and row['coverage_fraction']['value'] == 0.02


@pytest.mark.parametrize('policy', ['lowercase', None, ['uppercase']])
def test_unsupported_case_parameters_fail_explicitly(policy):
    with pytest.raises(ValueError, match='xmfa_case_policy_invalid'):
        alignment(native_document(), policy=policy)


@pytest.mark.parametrize('basis', ['all', None, ['represented']])
def test_unsupported_coverage_parameters_fail_explicitly(basis):
    with pytest.raises(ValueError, match='xmfa_coverage_basis_invalid'):
        coverage(native_document(), basis=basis)


@pytest.mark.parametrize('target', ['block_index', 'site_column', 'pair_member', 'coverage_member'])
def test_result_identity_integers_never_accept_boolean_aliases(target):
    doc = native_document()
    if target == 'coverage_member':
        result = coverage(doc, bind(doc)); result['members'][0]['member_number'] = True
        validator = validate_xmfa_coverage_components
    else:
        result = alignment(doc, pairs=((1, 3),)); validator = validate_xmfa_alignment_components
        if target == 'block_index': result['blocks'][0]['block_index'] = False
        if target == 'site_column': result['blocks'][0]['sites'][0]['column_0based'] = False
        if target == 'pair_member': result['blocks'][0]['pairs'][0]['member_a'] = True
    with pytest.raises(ValueError, match='xmfa_'):
        validator(result)


@pytest.mark.parametrize('field', ['canonical_count', 'gap_count', 'present_member_count'])
def test_one_missing_site_cell_cannot_bypass_numerical_consistency_checks(field):
    result = alignment(native_document())
    cell = result['blocks'][0]['sites'][0][field]
    cell.update(state='missing', value=None)
    with pytest.raises(ValueError, match='xmfa_calculation_population_state_conflict'):
        validate_xmfa_alignment_components(result)


def test_unavailable_fraction_cannot_retain_authoritative_complement():
    doc = native_document(); result = coverage(doc, bind(doc))
    result['members'][0]['selected_coverage_fraction'].update(state='missing', value=None)
    with pytest.raises(ValueError, match='xmfa_coverage_complement_conflict'):
        validate_xmfa_coverage_components(result)


def test_partial_mapping_conflict_in_one_occurrence_is_not_a_usable_map_for_another():
    maps = [original('left.fa', 'row:0', 0, 2, occurrence=0),
            original('left.fa', 'row:0', 2, 3, occurrence=1, original_start=30),
            original('left.fa', 'row:0', 2, 3, occurrence=1, original_start=31)]
    doc, binding = concat_case(maps)
    rows = coverage(doc, binding)['members'][0]['original_coverage']
    assert rows[0]['known_union_bases']['value'] == 1
    assert rows[0]['mapping_completeness'] == 'partial' and rows[0]['coverage_fraction']['value'] is None
    assert rows[1]['coverage_fraction']['state'] == 'incompatible'
