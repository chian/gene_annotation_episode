from copy import deepcopy
import builtins
import hashlib
import json
import math
from pathlib import Path
import re
import socket
import subprocess

import pytest
import scipy

from gene_annotation_episode.phylogeny_formats import parse_aligned_fasta
from gene_annotation_episode.bvbrc_alignment_values import numeric_cell
from gene_annotation_episode.bvbrc_metacats_calculators import (
    metacats_group_counts, metacats_statistics, metacats_effects,
    adjust_p_values, chi_square_tail)
from gene_annotation_episode.bvbrc_metacats_calculation_contracts import (
    validate_group_counts, validate_statistics, validate_effects, validate_multiplicity)


ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / 'verification/tool_graders_bvbrc_metacats_native_execution_2026-10-25/cases'
BACKEND = {'name': 'scipy_chi2_integer_df_logtail_v1', 'version': scipy.__version__}
PARAMS = {'alphabet': 'aa', 'epsilon': .001, 'nucleotide_padding': 'ACGT_at_variable_sites',
          'omnibus_continuity': 'r_default_2x2_min_delta', 'pair_df_policy': 'native_source',
          'pair_zero_policy': 'retain_math_and_native_zero_to_one', 'selected_pairs': (('A', 'B'),),
          'distribution_backend': BACKEND}


def make_counts(sequences, membership, group_ids=None, *, columns=None):
    group_ids = group_ids or list(dict.fromkeys(membership))
    data = ''.join('>s' + str(i) + '\n' + sequence + '\n' for i, sequence in enumerate(sequences)).encode()
    artifact = {'raw_artifact_ref': 'input', 'source_ref': 'source', 'sha256': hashlib.sha256(data).hexdigest()}
    alignment = parse_aligned_fasta(data, artifact=artifact, id_rule='first_whitespace_token')['value']
    groups = [{'category_id': 'category', 'r_column_index_0based': i, 'r_group_token': str(i + 1),
        'native_group_ordinal': i + 1, 'group_id': name, 'exported_heading_index_0based': i,
        'exported_label_token': name, 'state': 'resolved', 'evidence': []} for i, name in enumerate(group_ids)]
    assignments = [{'category_id': 'category', 'alignment_id': alignment['alignment_id'], 'row_index': i,
        'member_key': {'input_binding_id': 'input', 'member_id': 's' + str(i), 'occurrence_index': 0},
        'metadata_row_index': i, 'metadata_column_index': 1, 'raw_group_value': name,
        'native_group_ordinal': group_ids.index(name) + 1, 'displayed_group_label': name,
        'state': 'resolved', 'evidence': []} for i, name in enumerate(membership)]
    population = {'population_id': 'p', 'alignment_id': alignment['alignment_id'],
        'row_indices': list(range(len(sequences))),
        'columns_0based': list(range(len(sequences[0]))) if columns is None else columns,
        'completeness': 'complete', 'evidence': []}
    args = {'analysis_id': 'analysis', 'population': population, 'assignments': tuple(assignments),
        'category_id': 'category', 'group_order': tuple(groups), 'case_policy': 'preserve',
        'terminal_mask': 'native_terminal_dash_to_hash', 'native_input_hash_policy': 'exclude_hash'}
    return metacats_group_counts(alignment, **args), alignment, args


def test_two_group_source_statistics_and_raw_effect_have_distinct_populations():
    counts, _, _ = make_counts(['A'] * 6 + ['C'] * 6, ['A'] * 6 + ['B'] * 6)
    result = metacats_statistics(counts, **PARAMS)
    omni, pair = result['omnibus'][0], result['pairs'][0]
    assert omni['chi_square']['value'] == pytest.approx(8.330556481172945)
    assert omni['mathematical_p']['value'] == pytest.approx(.00389837142433717)
    assert omni['continuity_delta']['value'] == .5
    assert pair['chi_square']['value'] == pytest.approx(11.99600133288904)
    assert pair['mathematical_p']['value'] == pytest.approx(.000533148220906465)
    assert pair['continuity_delta']['value'] == 0
    assert omni['native_zero_rule_p']['state'] == 'not_measured'
    assert pair['r_table_group_count'] == 2
    assert pair['augmented_counts'] == [[6.001, .001], [.001, 6.001]]
    effect = metacats_effects(counts, selected_pairs=(('A', 'B'),), zero_margin_policy='drop_for_raw_effect_only')['sites'][0]
    assert effect['raw_chi_square']['value'] == pytest.approx(12)
    assert effect['cramers_v']['value'] == pytest.approx(1)
    assert effect['pairs'][0]['total_variation']['value'] == 1
    assert [x['value']['value'] for x in effect['pairs'][0]['frequency_deltas']] == [1, -1]
    assert effect['positive_observed_cells_below_5'] == 0
    assert effect['raw_adequacy']['cells_below_5']['value'] == 4
    assert effect['augmented_adequacy'] is None


def test_three_group_native_df_is_not_standard_pair_df():
    counts, _, _ = make_counts(['A'] * 6 + ['C'] * 6 + ['D'] * 6, ['A'] * 6 + ['B'] * 6 + ['C'] * 6)
    source = metacats_statistics(counts, **PARAMS)['pairs'][0]
    standard = metacats_statistics(counts, **{**PARAMS, 'pair_df_policy': 'standard_pair'})['pairs'][0]
    assert source['df']['value'] == 4 and standard['df']['value'] == 2
    assert source['mathematical_p']['value'] == pytest.approx(.017381025135296442)
    assert standard['mathematical_p']['value'] == pytest.approx(.00248371298657324)
    assert source['test_id'] != standard['test_id']
    assert source['method_id'] != standard['method_id']


def test_represented_group_with_no_site_residues_still_counts_in_native_df():
    counts, _, _ = make_counts(['A'] * 6 + ['C'] * 6 + ['-'], ['A'] * 6 + ['B'] * 6 + ['C'])
    result = metacats_statistics(counts, **PARAMS)['pairs'][0]
    assert result['r_table_group_count'] == 3
    assert result['df']['value'] == 2
    assert result['augmented_symbols'] == ['A', 'C']


def test_group_display_error_does_not_replace_source_backed_member_identity():
    _, alignment, args = make_counts(['A'] * 6 + ['C'] * 6, ['B'] * 6 + ['C'] * 6)
    args = deepcopy(args)
    for group, wrong_label in zip(args['group_order'], ['A', 'B']):
        group['native_group_ordinal'] += 1
        group['r_group_token'] = str(group['native_group_ordinal'])
        group['exported_label_token'] = wrong_label
        group['state'] = 'wrong_native_label'
    for row in args['assignments']:
        row['native_group_ordinal'] += 1
    counts = metacats_group_counts(alignment, **args)
    pair = metacats_statistics(counts, **{**PARAMS, 'selected_pairs': (('B', 'C'),)})['pairs'][0]
    assert pair['group_ids'] == ['B', 'C']
    assert pair['r_table_group_count'] == 2
    assert pair['df']['value'] == 1


@pytest.mark.parametrize('field,value', [('df', 99), ('mathematical_p', .9),
    ('native_zero_rule_p', .7), ('augmented_total', 12)])
def test_saved_statistical_relationships_reject_changed_fields(field, value):
    counts, _, _ = make_counts(['A'] * 6 + ['C'] * 6, ['A'] * 6 + ['B'] * 6)
    result = metacats_statistics(counts, **PARAMS)
    result['pairs'][0][field]['value'] = value
    with pytest.raises(ValueError):
        validate_statistics(result)


def test_zero_pseudocount_preserves_degenerate_padded_table_without_fabricated_test():
    counts, _, _ = make_counts(['A', 'C'], ['A', 'B'])
    result = metacats_statistics(counts, **{**PARAMS, 'alphabet': 'na', 'epsilon': 0})
    assert result['status'] == 'partial'
    assert result['omnibus'][0]['mathematical_p']['value'] is None
    assert result['omnibus'][0]['augmented_counts'] == [[1, 0], [0, 1], [0, 0], [0, 0]]


def test_underflow_keeps_log_tail_and_separate_native_emulation():
    counts, _, _ = make_counts(['A'] * 2000 + ['C'] * 2000, ['A'] * 2000 + ['B'] * 2000)
    pair = metacats_statistics(counts, **PARAMS)['pairs'][0]
    assert pair['chi_square']['value'] == pytest.approx(3999.996000004)
    assert pair['mathematical_p']['value'] is None
    assert pair['mathematical_p']['state'] == 'failed'
    assert pair['numerical_state'] == 'underflow'
    assert math.isfinite(pair['log_p']['value']) and pair['log_p']['value'] < -2000
    assert pair['native_zero_rule_p']['value'] == 1
    assert pair['native_zero_rule_p']['origin'] == 'calculated'


@pytest.mark.parametrize('df', [1, 2, 3, 4, 17, 100])
def test_log_tail_recurrence_underflow_and_finite_range(df):
    ordinary = chi_square_tail(8.0, df, distribution_backend=BACKEND)
    assert ordinary['p'] > 0 and ordinary['log_p'] == pytest.approx(math.log(ordinary['p']))
    extreme = chi_square_tail(4000, df, distribution_backend=BACKEND)
    assert extreme['p'] is None and math.isfinite(extreme['log_p'])
    if df == 2:
        assert extreme['log_p'] == -2000
    if df == 4:
        assert extreme['log_p'] == pytest.approx(-2000 + math.log(2001))


def test_terminal_mask_is_based_on_whole_row_before_column_subset():
    counts, alignment, args = make_counts(['-A-C-', 'CA-CC'], ['A', 'B'])
    subset = metacats_group_counts(alignment, **{**args, 'population': {**args['population'], 'columns_0based': [2]}})
    site = subset['sites'][0]
    assert site['symbols'] == ['-'] and site['observed_counts'] == [[1, 1]]
    assert site['internal_gap_rows_by_group'] == [[0], [1]]
    assert site['excluded_terminal_rows_by_group'] == [[], []]
    assert counts['sites'][0]['excluded_terminal_rows_by_group'] == [[0], []]


def test_partial_trailing_dash_is_not_claimed_as_terminal():
    counts, _, _ = make_counts(['CAAAA', 'AC-'], ['A', 'B'], columns=[2])
    site = counts['sites'][0]
    assert site['state'] == 'unresolved'
    assert site['unresolved_row_indices'] == [1]
    assert site['excluded_terminal_rows_by_group'] == [[], []]


def test_original_hash_exclusion_is_not_terminal_gap_exclusion():
    _, alignment, args = make_counts(['AC-', 'AAA'], ['A', 'B'])
    # This saved document represents a declared MetaCATS input parser's literal
    # '#' support, not an invocation of the shared FASTA parser with altered bytes.
    alignment['rows'][0]['sequence'] = 'A#-'
    alignment['artifact']['sha256'] = hashlib.sha256(b'>s0\nA#-\n>s1\nAAA\n').hexdigest()
    for row in alignment['rows']:
        row['source_location']['artifact'] = deepcopy(alignment['artifact'])
    counts = metacats_group_counts(alignment, **args)
    assert counts['sites'][1]['excluded_original_hash_rows_by_group'] == [[0], []]
    assert counts['sites'][1]['excluded_terminal_rows_by_group'] == [[], []]
    assert counts['sites'][2]['excluded_terminal_rows_by_group'] == [[0], []]


def test_missing_membership_is_unknown_not_smaller_complete_population():
    _, alignment, args = make_counts(['A', 'C'], ['A', 'B'])
    counts = metacats_group_counts(alignment, **{**args, 'assignments': args['assignments'][:1]})
    assert counts['status'] == 'partial' and counts['sites'][0]['state'] == 'unresolved'
    assert counts['sites'][0]['unresolved_row_indices'] == [1]
    result = metacats_statistics(counts, **PARAMS)
    assert result['status'] == 'partial' and result['omnibus'] == result['pairs'] == []


def test_same_labels_and_positions_do_not_alias_different_input_bytes():
    first, _, _ = make_counts(['A', 'C'], ['A', 'B'])
    changed, _, _ = make_counts(['A', 'D'], ['A', 'B'])
    assert first['alignment_id'] == changed['alignment_id']
    assert first['sites'][0]['table_id'] != changed['sites'][0]['table_id']


def test_all_missing_and_conserved_sites_are_exclusions():
    counts, _, _ = make_counts(['-A-', '-A-'], ['A', 'B'])
    result = metacats_statistics(counts, **PARAMS)
    assert result['omnibus'] == result['pairs'] == []
    assert [r['reason'] for r in result['exclusions']] == ['all_missing', 'all_missing',
        'conserved_placeholder', 'conserved_placeholder', 'all_missing', 'all_missing']


@pytest.mark.parametrize('tamper', ['counts', 'members', 'groups', 'classification'])
def test_saved_count_relationships_are_checked(tamper):
    counts, _, _ = make_counts(['A', 'C'], ['A', 'B'])
    if tamper == 'counts':
        counts['sites'][0]['observed_counts'][0][0] += 1
    elif tamper == 'members':
        counts['sites'][0]['included_rows_by_group'][1] = [0]
    elif tamper == 'groups':
        counts['group_order'].reverse()
    else:
        counts['sites'][0]['state'] = 'conserved'
    with pytest.raises(ValueError):
        validate_group_counts(counts)


def family_and_p(values):
    family = {'family_id': 'family', 'analysis_ids': ['analysis'], 'category_ids': ['category'],
        'test_kind': 'omnibus', 'test_ids': ['t' + str(i) for i in range(len(values))],
        'eligibility': 'variable_site_positive_df', 'population_state': 'complete',
        'total_test_count': len(values), 'assumption': None,
        'p_value_basis': 'source_mathematical_recalculation', 'evidence': []}
    rows = tuple({'test_id': 't' + str(i), 'value': numeric_cell(value, state='available',
        unit='probability', origin='calculated', population_id='test', method_id='fixture')}
        for i, value in enumerate(values))
    return family, rows


@pytest.mark.parametrize('method,expected', [
    ('none', [.01, .04, .03]), ('bonferroni', [.03, .12, .09]),
    ('holm', [.03, .06, .06]), ('bh', [.03, .04, .04]),
    ('by', [.055, .07333333333333333, .07333333333333333])])
def test_adjustments_use_complete_family_and_original_test_order(method, expected):
    family, rows = family_and_p([.01, .04, .03])
    result = adjust_p_values(rows, family=family, method=method, alpha=.05,
        dependence_assumption='independent_or_positive_regression_dependence_assumed')
    assert [r['adjusted_p']['value'] for r in result['results']] == pytest.approx(expected)
    assert [r['test_id'] for r in result['results']] == ['t0', 't1', 't2']


def test_incomplete_family_cannot_use_bh_or_infer_test_count():
    family, rows = family_and_p([.01, .04, .03])
    result = adjust_p_values(rows[:1], family=family, method='bh', alpha=.05,
        dependence_assumption='independent_or_positive_regression_dependence_assumed')
    assert result['status'] == 'partial' and result['results'][0]['adjusted_p']['value'] is None
    family.update(population_state='declared_upper_bound', total_test_count=10,
        assumption={'kind': 'parent_declared_upper_bound', 'count': 10, 'evidence': []})
    bounded = adjust_p_values(rows[:1], family=family, method='bonferroni', alpha=.05,
                             dependence_assumption='none_required_between_tests')
    assert bounded['results'][0]['adjusted_p']['value'] == .1
    assert bounded['total_test_count'] == 10 and bounded['observed_p_count'] == 1


def test_bh_requires_explicit_assumption_and_zero_is_not_missing():
    family, rows = family_and_p([0, 1])
    result = adjust_p_values(rows, family=family, method='bh', alpha=.05,
                            dependence_assumption='none_required_between_tests')
    assert result['status'] == 'partial'
    result = adjust_p_values(rows, family=family, method='bonferroni', alpha=.05,
                            dependence_assumption='none_required_between_tests')
    assert [r['adjusted_p']['value'] for r in result['results']] == [0, 1]


def test_complete_official_input_matches_all_312_native_variable_tests():
    text = (NATIVE / 'official_na/original.fasta').read_text()
    rows = [(record.splitlines()[0].split()[0], ''.join(record.splitlines()[1:]))
            for record in text.split('>')[1:]]
    metadata = dict(line.split('\t') for line in (NATIVE / 'official_na/metadata.tsv').read_text().splitlines()[1:])
    counts, _, _ = make_counts([r[1] for r in rows], [metadata[r[0]] for r in rows])
    native = {}
    for line in (NATIVE / 'official_na/output/retained_raw/GROUP-chisqTable.txt').read_text().splitlines():
        match = re.match(r'^\s*Site(\d+)\s*\t(.*)', line)
        if match:
            cells = [cell.strip() for cell in match[2].split('\t')]
            if cells[0] != 'NA':
                native[int(match[1]) - 1] = (float(cells[0]), float(cells[1]), int(cells[2]))
    actual = metacats_statistics(counts, **{**PARAMS, 'alphabet': 'na', 'selected_pairs': (('1', '2'),)})
    assert len(native) == len(actual['omnibus']) == 312
    for row in actual['omnibus']:
        expected = native[row['column_0based']]
        assert row['chi_square']['value'] == pytest.approx(expected[0], rel=1e-12, abs=1e-12)
        assert row['mathematical_p']['value'] == pytest.approx(expected[1], rel=1e-12, abs=1e-14)
        assert row['df']['value'] == expected[2]


def test_saved_counts_recalculate_with_changed_parameters_without_io(monkeypatch):
    counts, _, _ = make_counts(['A'] * 6 + ['C'] * 6, ['A'] * 6 + ['B'] * 6)
    serialized = json.dumps(counts)
    initial = metacats_statistics(counts, **PARAMS)
    def forbidden(*args, **kwargs):
        raise AssertionError('acquisition_or_parsing_forbidden')
    monkeypatch.setattr(builtins, 'open', forbidden)
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    monkeypatch.setattr(Path, 'read_text', forbidden)
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr('gene_annotation_episode.phylogeny_formats.parse_aligned_fasta', forbidden)
    saved = json.loads(serialized)
    assert metacats_statistics(saved, **PARAMS) == initial
    changed = metacats_statistics(saved, **{**PARAMS, 'epsilon': .5})
    assert changed['omnibus'][0]['chi_square']['value'] != initial['omnibus'][0]['chi_square']['value']
    assert json.dumps(saved) == serialized


def test_saved_outputs_validate_detached_without_recalculation(monkeypatch):
    counts, _, _ = make_counts(['A'] * 6 + ['C'] * 6, ['A'] * 6 + ['B'] * 6)
    stats = metacats_statistics(counts, **PARAMS)
    effects = metacats_effects(counts, selected_pairs=(('A', 'B'),), zero_margin_policy='drop_for_raw_effect_only')
    family, rows = family_and_p([.01, .04, .03])
    multiplicity = adjust_p_values(rows, family=family, method='holm', alpha=.05,
                                  dependence_assumption='none_required_between_tests')
    def forbidden(*args, **kwargs):
        raise AssertionError('calculation_or_io_forbidden')
    monkeypatch.setattr(builtins, 'open', forbidden)
    monkeypatch.setattr('gene_annotation_episode.bvbrc_metacats_calculators.metacats_statistics', forbidden)
    monkeypatch.setattr('gene_annotation_episode.bvbrc_metacats_calculators.metacats_effects', forbidden)
    monkeypatch.setattr('gene_annotation_episode.bvbrc_metacats_calculators.adjust_p_values', forbidden)
    for value, validate in ((stats, validate_statistics), (effects, validate_effects),
                             (multiplicity, validate_multiplicity)):
        saved = json.loads(json.dumps(value, allow_nan=False))
        detached = validate(saved)
        assert detached == value and detached is not saved
