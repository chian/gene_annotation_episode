"""MSA numerical cases, independent hand answers, failures and offline replay."""
from copy import deepcopy
import builtins
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import bvbrc_msa_formats, phylogeny_formats
from gene_annotation_episode.bvbrc_msa_calculation_contracts import (
    CATEGORIES, validate_msa_entropy_components, validate_msa_reference_components,
)
from gene_annotation_episode.bvbrc_msa_calculators import msa_native_entropy, msa_reference_differences
from gene_annotation_episode.bvbrc_msa_formats import parse_msa_frequency_table
from gene_annotation_episode.phylogeny_calculators import alignment_components
from gene_annotation_episode.phylogeny_formats import parse_aligned_fasta


NATIVE = Path(__file__).resolve().parents[1] / 'verification/tool_graders_bvbrc_msa_metacats_boundaries_2026-10-25/native_examples'
ROUNDING = 'binary64_fixed_2_ties_to_even'


def artifact(data, label):
    return {'raw_artifact_ref': label, 'source_ref': 'test:' + label,
            'sha256': hashlib.sha256(data).hexdigest()}


def parse_alignment(data):
    return parse_aligned_fasta(data, artifact=artifact(data, 'alignment'),
        id_rule='first_whitespace_token', encoding='ascii')['value']


def alignment(*sequences):
    return parse_alignment(''.join('>m' + str(i) + '\n' + sequence + '\n'
                                  for i, sequence in enumerate(sequences)).encode())


def population(al, rows=None, columns=None, completeness='complete'):
    return {'population_id': 'selected', 'alignment_id': al['alignment_id'],
        'row_indices': list(range(len(al['rows']))) if rows is None else list(rows),
        'columns_0based': list(range(al['observed_column_count'])) if columns is None else list(columns),
        'completeness': completeness, 'evidence': []}


def native(alphabet):
    al = parse_alignment((NATIVE / alphabet / 'output.afa').read_bytes())
    data = (NATIVE / alphabet / 'foma.table').read_bytes()
    table = parse_msa_frequency_table(data, artifact=artifact(data, 'native-table'),
        alphabet=alphabet, layout='current_without_reference', encoding='ascii')['value']
    return al, table


def entropy(al, alphabet='dna', table=None, pop=None, rounding=ROUNDING):
    return msa_native_entropy(al, analysis_id='analysis', population=population(al) if pop is None else pop,
        alphabet=alphabet, case_policy='uppercase', terminal_gap='-', observed_table=table, native_rounding=rounding)


def reference(al, row=0, resolved=True, member=None):
    return {'alignment_id': al['alignment_id'], 'row_index': row, 'original_member': member,
        'native_ref_type': 'string', 'native_ref_string': '>reference\nA-CGN--',
        'identity_state': 'resolved' if resolved else 'unresolved', 'evidence': []}


def maps(al):
    result = []
    for row in al['rows']:
        offset = 0
        for column, char in enumerate(row['sequence']):
            if char == '-':
                continue
            result.append({'alignment_id': al['alignment_id'], 'row_index': row['row_index'],
                'column_0based': column, 'staged_ungapped_position_0based': offset,
                'original_member': {'input_binding_id': 'original', 'member_id': row['member_label']},
                'original_interval_0based_half_open': [100 * (row['row_index'] + 1) + offset,
                                                     100 * (row['row_index'] + 1) + offset + 1],
                'strand': '+', 'translation_table': None, 'transformation_id': 'explicit-test-trim', 'evidence': []})
            offset += 1
    return tuple(result)


def differences(al, *, pop=None, ref=None, correspondence=(), case_policy='uppercase', members=(1,), alphabet='dna'):
    return msa_reference_differences(al, analysis_id='analysis', population=population(al) if pop is None else pop,
        reference=reference(al) if ref is None else ref, member_row_indices=members,
        alphabet=alphabet, case_policy=case_policy, original_correspondences=correspondence)


def test_native_dna_values_and_distinct_canonical_only_population():
    al, table = native('dna')
    result = entropy(al, table=table)
    second, third = result['sites'][1:3]
    assert result['status'] == 'ok'
    assert second['symbol_counts'] == [{'symbol': '-', 'count': 1}, {'symbol': 'A', 'count': 2}]
    assert second['eligible_count']['value'] == 3
    assert second['internal_gap_count']['value'] == 1
    assert second['terminal_gap_excluded_count']['value'] == 1
    assert second['literal_entropy_bits']['value'] == pytest.approx(0.9182958340544896)
    assert second['native_score_recalculated']['value'] == 92
    assert third['symbol_counts'] == [{'symbol': 'C', 'count': 3}, {'symbol': 'T', 'count': 1}]
    assert third['literal_entropy_bits']['value'] == pytest.approx(0.8112781244591328)
    assert third['native_score_recalculated']['value'] == 81
    assert all(site['score_residual']['value'] == 0 for site in result['sites'])
    canonical = alignment_components(al, population=population(al), alphabet='dna', case_policy='uppercase')
    assert canonical['sites'][1]['canonical_entropy_bits']['value'] == 0
    assert canonical['sites'][1]['canonical_entropy_bits']['denominator'] == 2
    assert second['literal_entropy_bits']['denominator'] == 3


def test_native_protein_internal_deletion_tie_has_literal_entropy_one():
    al, table = native('protein')
    result = entropy(al, alphabet='protein', table=table)
    site = result['sites'][3]
    assert result['status'] == 'ok'
    assert site['symbol_counts'] == [{'symbol': '-', 'count': 2}, {'symbol': 'G', 'count': 2}]
    assert site['literal_entropy_bits']['value'] == 1
    assert site['native_score_recalculated']['value'] == 100
    assert site['strict_majority_consensus'] == 'X'
    assert table['rows'][3]['consensus_token'] == 'Xaa'


def test_terminal_gap_classification_is_invariant_to_column_subset_and_order():
    al = alignment('--A--C--', 'TA----CG', '--------')
    whole = entropy(al)
    subset = entropy(al, pop=population(al, columns=[4, 3, 0]))
    by_column = {row['column_0based']: row for row in whole['sites']}
    assert subset['sites'] == [by_column[4], by_column[3], by_column[0]]
    assert subset['sites'][0]['internal_gap_count']['value'] == 2
    assert subset['sites'][0]['excluded_terminal_row_indices'] == [2]
    assert subset['sites'][2]['included_row_indices'] == [1]
    assert subset['sites'][2]['excluded_terminal_row_indices'] == [0, 2]


def test_all_gap_ambiguous_stop_and_empty_site_populations_are_explicit():
    al = alignment('--N-*--', '--X-A--', '-------')
    result = entropy(al, alphabet='protein')
    assert result['status'] == 'partial'
    assert result['sites'][0]['eligible_count']['value'] == 0
    assert result['sites'][0]['literal_entropy_bits']['value'] is None
    assert result['sites'][0]['literal_entropy_bits']['denominator'] == 0
    assert result['sites'][0]['strict_majority_consensus'] is None
    assert result['sites'][2]['literal_entropy_bits']['value'] == 1
    assert result['sites'][3]['internal_gap_count']['value'] == 2
    assert result['sites'][3]['literal_entropy_bits']['value'] == 0
    assert result['sites'][3]['strict_majority_consensus'] == '-'
    assert result['sites'][4]['symbol_counts'] == [{'symbol': '*', 'count': 1}, {'symbol': 'A', 'count': 1}]
    assert result['sites'][4]['literal_entropy_bits']['value'] == 1
    empty_rows = entropy(al, pop=population(al, rows=[], columns=[2]))
    assert empty_rows['sites'][0]['literal_entropy_bits']['value'] is None
    assert empty_rows['sites'][0]['eligible_count']['value'] == 0
    empty_columns = entropy(alignment('', ''))
    assert empty_columns['sites'] == [] and empty_columns['status'] == 'ok'


def test_uppercase_literals_and_optional_rounding_do_not_replace_native_values():
    al, table = native('dna')
    for row in al['rows']:
        row['sequence'] = row['sequence'].lower()
    original = deepcopy(table)
    result = entropy(al, table=table, rounding=None)
    assert result['sites'][1]['literal_entropy_bits']['value'] == pytest.approx(0.9182958340544896)
    assert result['sites'][1]['native_score_recalculated']['state'] == 'not_measured'
    assert result['sites'][1]['score_residual']['state'] == 'not_measured'
    assert table == original and table['rows'][1]['score']['value'] == 92


def test_changed_rows_and_subsets_keep_signed_residual_and_qualify_population():
    al, table = native('dna')
    subset = entropy(al, table=table, pop=population(al, rows=[0, 1], columns=[1]))
    assert subset['sites'][0]['eligible_count']['value'] == 2
    assert subset['sites'][0]['score_residual']['value'] == 92
    assert any(d['code'].endswith('native_comparison_selected_row_subset') for d in subset['diagnostics'])
    al['rows'][0]['sequence'] = 'ATCGT--'
    result = entropy(al, table=table)
    site = result['sites'][1]
    assert site['literal_entropy_bits']['value'] == pytest.approx(math.log2(3))
    assert site['native_score_recalculated']['value'] == 158
    assert site['score_residual']['value'] == -66
    assert table['rows'][1]['score']['value'] == 92
    assert any(d['path'].endswith('/dna_counts/A') for d in result['diagnostics'])


def test_duplicate_native_positions_do_not_choose_arbitrary_score():
    al, _ = native('dna')
    original = (NATIVE / 'dna/foma.table').read_bytes()
    data = original + original.splitlines(keepends=True)[2]
    table = parse_msa_frequency_table(data, artifact=artifact(data, 'duplicate'), alphabet='dna',
        layout='current_without_reference', encoding='ascii')['value']
    site = entropy(al, table=table)['sites'][1]
    assert site['score_residual']['value'] is None and site['score_residual']['state'] == 'incompatible'
    assert site['native_observation_ids'] == [table['table_id'] + '/rows/1/score', table['table_id'] + '/rows/7/score']
    assert site['literal_entropy_bits']['value'] == pytest.approx(0.9182958340544896)


def test_partial_native_table_and_bad_native_score_keep_independent_entropy():
    al, _ = native('dna')
    data = (NATIVE / 'dna/foma.table').read_bytes().replace(b'2\t92', b'2\tNaN').replace(b'3\t81', b'3\twrong')
    table = parse_msa_frequency_table(data, artifact=artifact(data, 'invalid-score'), alphabet='dna',
        layout='current_without_reference', encoding='ascii')['value']
    result = entropy(al, table=table)
    assert result['status'] == 'partial'
    assert result['sites'][1]['native_score_recalculated']['value'] == 92
    assert result['sites'][1]['score_residual']['state'] == 'failed'
    assert result['sites'][2]['score_residual']['state'] == 'failed'


def test_incomplete_alignment_keeps_observed_symbols_without_complete_denominators():
    al = alignment('A-C', 'A')
    result = entropy(al, pop=population(al, columns=[0, 1, 2], completeness='truncated'))
    assert result['status'] == 'partial'
    site = result['sites'][2]
    assert site['symbol_counts'] == [{'symbol': 'C', 'count': 1}]
    assert site['eligible_count']['value'] is None
    assert site['eligible_count']['state'] == 'truncated'
    assert site['literal_entropy_bits']['value'] is None
    assert result['requirements'][0]['role'] == 'final_alignment'


def test_incomplete_trailing_run_does_not_claim_terminal_exclusion():
    al = alignment('A--', 'A--C', '--AC')
    result = entropy(al, pop=population(al, columns=[0, 2]))
    assert result['sites'][0]['excluded_terminal_row_indices'] == [2]
    assert result['sites'][1]['included_row_indices'] == [1, 2]
    assert result['sites'][1]['excluded_terminal_row_indices'] == []
    assert result['sites'][1]['symbol_counts'] == [{'symbol': '-', 'count': 1}, {'symbol': 'A', 'count': 1}]
    assert result['sites'][1]['eligible_count']['value'] is None


def test_reference_categories_and_staged_original_coordinates():
    al = alignment('A-CGN--', 'AT-TNA-')
    result = differences(al, correspondence=maps(al))
    assert result['status'] == 'ok'
    assert [r['category'] for r in result['differences']] == [
        'identical_canonical', 'insertion_relative_to_reference', 'deletion_relative_to_reference',
        'substitution', 'ambiguous_or_other', 'insertion_relative_to_reference', 'both_gap']
    assert [r['member_ungapped_position_0based'] for r in result['differences']] == [0, 1, None, 2, 3, 4, None]
    assert [r['reference_ungapped_position_0based'] for r in result['differences']] == [0, None, 1, 2, 3, None, None]
    assert result['differences'][3]['member_original_correspondence']['original_interval_0based_half_open'] == [202, 203]
    assert result['differences'][3]['reference_original_correspondence']['original_interval_0based_half_open'] == [102, 103]
    counts = {r['category']: r['count']['value'] for r in result['counts']}
    assert counts == dict(zip(CATEGORIES, [1, 1, 2, 1, 1, 1]))


def test_reference_may_be_outside_selected_members_and_column_subset_keeps_offsets():
    al = alignment('A-CGN--', 'AT-TNA-')
    result = differences(al, pop=population(al, rows=[1], columns=[5, 3]), correspondence=maps(al))
    assert [r['member_ungapped_position_0based'] for r in result['differences']] == [4, 2]
    assert [r['reference_ungapped_position_0based'] for r in result['differences']] == [None, 2]
    assert result['status'] == 'ok'


def test_missing_original_maps_and_unresolved_reference_preserve_staged_results():
    al = alignment('A-CGN--', 'AT-TNA-')
    result = differences(al, ref=reference(al, resolved=False))
    assert result['status'] == 'partial'
    assert all(r['member_original_correspondence'] is None for r in result['differences'])
    assert all(r['count']['state'] == 'available' for r in result['counts'])
    assert {r['reason_code'] for r in result['requirements']} == {
        'bvbrc_msa_requested_reference_unresolved', 'bvbrc_msa_original_residue_map_required'}
    assert len(result['requirements']) == 3


def test_reference_partial_ragged_data_preserves_valid_pairs_but_not_whole_counts():
    al = alignment('ACG', 'A')
    result = differences(al, pop=population(al, columns=[0, 1, 2]))
    assert len(result['differences']) == 1
    assert result['differences'][0]['category'] == 'identical_canonical'
    assert all(r['count']['value'] is None for r in result['counts'])


def test_reference_case_policy_is_explicit():
    al = alignment('acD', 'ACD')
    preserved = differences(al, alphabet='protein', case_policy='preserve')
    upper = differences(al, alphabet='protein', case_policy='uppercase')
    assert [r['category'] for r in preserved['differences']] == ['ambiguous_or_other', 'ambiguous_or_other', 'identical_canonical']
    assert all(r['category'] == 'identical_canonical' for r in upper['differences'])


@pytest.mark.parametrize('problem', ['wrong_alignment', 'wrong_row', 'duplicate_rows', 'member_outside',
    'duplicate_map', 'bad_staged', 'gap_original', 'wrong_member', 'bool_index'])
def test_reference_rejects_wrong_identity_and_coordinate_relationships(problem):
    al = alignment('A-CGN--', 'AT-TNA-')
    pop, ref, correspondence, members = population(al), reference(al), list(maps(al)), (1,)
    if problem == 'wrong_alignment': ref['alignment_id'] = 'wrong'
    elif problem == 'wrong_row': ref['row_index'] = 9
    elif problem == 'duplicate_rows': members = (1, 1)
    elif problem == 'member_outside': pop['row_indices'] = [0]
    elif problem == 'duplicate_map': correspondence.append(deepcopy(correspondence[0]))
    elif problem == 'bad_staged': correspondence[0]['staged_ungapped_position_0based'] = 99
    elif problem == 'gap_original': correspondence[0]['column_0based'] = 1; correspondence[0]['staged_ungapped_position_0based'] = None
    elif problem == 'wrong_member': ref['original_member'] = {'input_binding_id': 'original', 'member_id': 'wrong'}
    elif problem == 'bool_index': members = (True,)
    with pytest.raises(ValueError): differences(al, pop=pop, ref=ref, correspondence=tuple(correspondence), members=members)


@pytest.mark.parametrize('problem', ['wrong_id', 'extra_field', 'count', 'entropy', 'score', 'origin', 'duplicate_column'])
def test_saved_entropy_validator_rejects_mutated_numerical_meaning(problem):
    al, table = native('dna')
    result = entropy(al, table=table)
    if problem == 'wrong_id': result['sites'][1]['eligible_count']['population_id'] = 'wrong'
    elif problem == 'extra_field': result['extra'] = True
    elif problem == 'count': result['sites'][1]['eligible_count']['value'] = 99
    elif problem == 'entropy': result['sites'][1]['literal_entropy_bits']['value'] = 7
    elif problem == 'score': result['sites'][1]['native_score_recalculated']['value'] = 91
    elif problem == 'origin': result['sites'][1]['literal_entropy_bits']['origin'] = 'native_observation'
    elif problem == 'duplicate_column': result['sites'][1]['column_0based'] = 0
    with pytest.raises(ValueError): validate_msa_entropy_components(result)


@pytest.mark.parametrize('problem', ['category', 'count', 'gap_position', 'wrong_map', 'missing_category'])
def test_saved_reference_validator_rejects_mutated_relationships(problem):
    al = alignment('A-CGN--', 'AT-TNA-')
    result = differences(al, correspondence=maps(al))
    if problem == 'category': result['differences'][0]['category'] = 'substitution'
    elif problem == 'count': result['counts'][0]['count']['value'] = 99
    elif problem == 'gap_position': result['differences'][1]['reference_ungapped_position_0based'] = 1
    elif problem == 'wrong_map': result['differences'][0]['member_original_correspondence']['row_index'] = 0
    elif problem == 'missing_category': result['counts'].pop()
    with pytest.raises(ValueError): validate_msa_reference_components(result)


def test_saved_document_replay_no_file_network_subprocess_or_parser_access(monkeypatch):
    al, table = native('dna')
    arguments = json.loads(json.dumps({'alignment': al, 'population': population(al), 'observed_table': table}))
    original = deepcopy(arguments)
    expected = entropy(al, table=table)
    reference_al = alignment('A-CGN--', 'AT-TNA-')
    reference_maps = maps(reference_al)
    expected_reference = differences(reference_al, correspondence=reference_maps)
    def forbidden(*args, **kwargs):
        raise AssertionError('pure recalculation attempted I/O, parsing or execution')
    for obj, name in ((builtins, 'open'), (os, 'open'), (Path, 'open'), (Path, 'read_text'), (Path, 'read_bytes'),
                      (socket, 'socket'), (socket, 'create_connection'), (subprocess, 'Popen'), (subprocess, 'run'),
                      (bvbrc_msa_formats, 'parse_msa_frequency_table'), (phylogeny_formats, 'parse_aligned_fasta')):
        monkeypatch.setattr(obj, name, forbidden)
    replay = msa_native_entropy(**arguments, analysis_id='analysis', alphabet='dna', case_policy='uppercase',
                               terminal_gap='-', native_rounding=ROUNDING)
    assert replay == expected and arguments == original
    assert differences(reference_al, correspondence=reference_maps) == expected_reference
    saved = validate_msa_entropy_components(json.loads(json.dumps(replay)))
    saved['sites'][0]['eligible_count']['value'] = 999
    assert replay['sites'][0]['eligible_count']['value'] == 3
    copied = validate_msa_reference_components(expected_reference)
    copied['reference']['row_index'] = 99
    assert expected_reference['reference']['row_index'] == 0
    changed = entropy(arguments['alignment'], table=arguments['observed_table'], pop=arguments['population'], rounding=None)
    assert changed['sites'][1]['literal_entropy_bits'] == replay['sites'][1]['literal_entropy_bits']
    assert changed['sites'][1]['native_score_recalculated']['value'] is None
    assert arguments['observed_table']['rows'][1]['score']['value'] == 92


def test_saved_reference_repeated_row_coordinates_must_agree():
    al = alignment('AC', 'AT', 'AG')
    result = differences(al, members=(1, 2))
    # The reference coordinate at the same column cannot change across members.
    result['differences'][2]['reference_ungapped_position_0based'] = 9
    with pytest.raises(ValueError, match='repeated_coordinate_conflict'):
        validate_msa_reference_components(result)


@pytest.mark.parametrize('field,value', [('case_policy', 'preserve'), ('terminal_gap', '.'),
    ('native_rounding', 'perl_sprintf_two_decimals_verified'), ('alphabet', 'rna')])
def test_entropy_rejects_undeclared_method_parameters(field, value):
    al = alignment('AC', 'AT')
    arguments = dict(alignment=al, analysis_id='analysis', population=population(al), alphabet='dna',
                     case_policy='uppercase', terminal_gap='-', observed_table=None, native_rounding=ROUNDING)
    arguments[field] = value
    with pytest.raises(ValueError): msa_native_entropy(**arguments)


def test_missing_native_rows_keep_no_fake_zero_residual():
    al, _ = native('dna')
    data = (NATIVE / 'dna/foma.table').read_bytes().splitlines(keepends=True)[0]
    table = parse_msa_frequency_table(data, artifact=artifact(data, 'header-only'), alphabet='dna',
        layout='current_without_reference', encoding='ascii')['value']
    result = entropy(al, table=table)
    assert result['status'] == 'partial'
    assert all(site['score_residual']['value'] is None for site in result['sites'])
    assert all(site['score_residual']['state'] == 'missing' for site in result['sites'])
    assert result['sites'][1]['native_score_recalculated']['value'] == 92
