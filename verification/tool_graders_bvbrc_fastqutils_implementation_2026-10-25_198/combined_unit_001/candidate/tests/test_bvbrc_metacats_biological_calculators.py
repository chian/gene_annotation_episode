from copy import deepcopy
import builtins
import hashlib
import itertools
import json
import math
from pathlib import Path
import socket
import subprocess

import pytest
import scipy

from gene_annotation_episode.bvbrc_metacats_input_formats import parse_metacats_input_fasta
from gene_annotation_episode.bvbrc_metacats_biological_calculators import (
    biological_group_counts, biological_group_statistics, biological_group_effects)
from gene_annotation_episode.bvbrc_metacats_biological_contracts import (
    validate_biological_group_population, validate_biological_assignments,
    validate_biological_counts, validate_biological_statistics, validate_biological_effects)
from gene_annotation_episode.bvbrc_contingency_math import (
    count_alignment_group_sites, expected_contingency_counts, pearson_contingency_statistic)
from gene_annotation_episode.bvbrc_metacats_calculators import metacats_statistics, adjust_p_values
from gene_annotation_episode.bvbrc_metacats_calculation_contracts import validate_test_family


ROOT = Path(__file__).resolve().parents[1]
SAVED = ROOT / 'verification/tool_graders_bvbrc_msa_metacats_implementation_2026-10-25'
BACKEND = {'name': 'scipy_chi2_integer_df_logtail_v1', 'version': scipy.__version__}
STAT_PARAMS = {'alphabet': 'aa', 'epsilon': .001, 'nucleotide_padding': 'ACGT_at_variable_sites',
    'omnibus_continuity': 'r_default_2x2_min_delta', 'pair_df_policy': 'standard_pair',
    'selected_pairs': (('A', 'B'),), 'distribution_backend': BACKEND}
EFFECT_PARAMS = {'selected_pairs': (('A', 'B'),), 'zero_margin_policy': 'drop_for_raw_effect_only'}


def make_inputs(sequences, membership, *, group_ids=None, columns=None, labels=None):
    labels = labels if labels is not None else ['s' + str(i) for i in range(len(sequences))]
    raw = ''.join('>' + name + '\n' + seq + '\n' for name, seq in zip(labels, sequences)).encode()
    artifact = {'raw_artifact_ref': 'alignment', 'source_ref': 'supplied', 'sha256': hashlib.sha256(raw).hexdigest()}
    alignment = parse_metacats_input_fasta(raw, artifact=artifact)['value']
    groups = group_ids if group_ids is not None else list(dict.fromkeys(x for x in membership if x is not None))
    population = {'population_id': 'selected', 'alignment_id': alignment['alignment_id'],
        'row_indices': list(range(len(sequences))), 'columns_0based': list(range(max(map(len, sequences), default=0)))
        if columns is None else columns, 'completeness': 'complete', 'evidence': []}
    args = {'analysis_id': 'analysis', 'population': population, 'category_id': 'category',
        'assignments': tuple({'category_id': 'category', 'alignment_id': alignment['alignment_id'],
            'row_index': i, 'member_key': None, 'group_id': group,
            'state': 'resolved' if group is not None else 'missing', 'evidence': []} for i, group in enumerate(membership)),
        'group_population': {'group_population_id': 'declared_groups', 'category_id': 'category',
            'groups': [{'group_id': group, 'raw_group_value': group, 'evidence': []} for group in groups],
            'completeness': 'complete', 'evidence': []}, 'case_policy': 'preserve',
        'terminal_gap_policy': 'exclude_terminal_dash', 'original_hash_policy': 'exclude_hash'}
    return alignment, args


def make_counts(sequences=None, membership=None, **kwargs):
    sequences = sequences if sequences is not None else ['A'] * 6 + ['C'] * 6
    membership = membership if membership is not None else ['A'] * 6 + ['B'] * 6
    alignment, args = make_inputs(sequences, membership, **kwargs)
    return biological_group_counts(alignment, **args)


def retained_inputs(case):
    path = SAVED / ('EXAMPLES_002' if case == 'twelve_groups' else 'EXAMPLES_001') / (case + '-inputs.json')
    old = json.loads(path.read_text())
    # Join the supplied original metadata by unique actual identifier. No R
    # token, matrix ordinal or independently sorted list supplies membership.
    metadata_rows = old['original_metadata_rows']
    metadata = {row[0]: (i, row[1]) for i, row in enumerate(metadata_rows[1:])}
    assert len(metadata) == len(metadata_rows) - 1
    groups = list(dict.fromkeys(row[1] for row in metadata_rows[1:]))
    category = metadata_rows[0][1]
    metadata_evidence = deepcopy(old['counts_arguments']['assignments'][0]['evidence'][:1])
    assignments = []
    for row in old['alignment']['rows']:
        _, group = metadata[row['member_label']]
        assignments.append({'category_id': category, 'alignment_id': old['alignment']['alignment_id'],
            'row_index': row['row_index'], 'member_key': None, 'group_id': group,
            'state': 'resolved', 'evidence': metadata_evidence})
    args = {'analysis_id': case, 'population': deepcopy(old['counts_arguments']['population']),
        'category_id': category, 'assignments': tuple(assignments),
        'group_population': {'group_population_id': case + '/biological_groups', 'category_id': category,
            'groups': [{'group_id': group, 'raw_group_value': group, 'evidence': metadata_evidence} for group in groups],
            'completeness': 'complete', 'evidence': metadata_evidence},
        'case_policy': 'preserve', 'terminal_gap_policy': 'exclude_terminal_dash', 'original_hash_policy': 'exclude_hash'}
    params = {**STAT_PARAMS, 'alphabet': old['statistical_parameters']['alphabet'],
              'selected_pairs': tuple(itertools.combinations(groups, 2))}
    return old, args, params


def family_for(statistics):
    rows = statistics['omnibus']
    return {'family_id': 'explicit_family', 'analysis_ids': [statistics['analysis_id']],
        'category_ids': [statistics['category_id']], 'test_kind': 'omnibus',
        'test_ids': [row['test_id'] for row in rows], 'eligibility': 'variable_site_positive_df',
        'population_state': 'complete', 'total_test_count': len(rows), 'assumption': None,
        'p_value_basis': 'biological_mathematical_recalculation', 'evidence': []}


def test_two_group_numerical_sheet_and_signed_effects_without_original_member_keys():
    counts = make_counts()
    assert counts['sites'][0]['observed_counts'] == [[6, 0], [0, 6]]
    assert counts['status'] == 'ok' and len(counts['diagnostics']) == 12
    stats = biological_group_statistics(counts, **STAT_PARAMS)
    omni, pair = stats['omnibus'][0], stats['pairs'][0]
    assert omni['chi_square']['value'] == pytest.approx(8.330556481172945)
    assert omni['mathematical_p']['value'] == pytest.approx(.00389837142433717)
    assert pair['chi_square']['value'] == pytest.approx(11.99600133288904)
    assert pair['mathematical_p']['value'] == pytest.approx(.000533148220906465)
    assert omni['continuity_delta']['value'] == .5 and pair['continuity_delta']['value'] == 0
    effect = biological_group_effects(counts, **EFFECT_PARAMS)['sites'][0]
    assert effect['raw_chi_square']['value'] == pytest.approx(12)
    assert effect['cramers_v']['value'] == pytest.approx(1)
    assert [x['value']['value'] for x in effect['pairs'][0]['frequency_deltas']] == [1, -1]
    assert effect['pairs'][0]['total_variation']['value'] == 1
    assert effect['positive_observed_cells_below_5'] == 0
    assert effect['raw_adequacy']['cells_below_5']['value'] == 4
    dumped = json.dumps([counts, stats, effect], allow_nan=False)
    for forbidden in ('r_column', 'r_group_token', 'r_table_group_count', 'native_zero_rule_p',
                      'native_observation_ids', 'native_fewer_5', 'augmented_adequacy', 'metacats_native_'):
        assert forbidden not in dumped


@pytest.mark.parametrize('case', ['aa_two_groups', 'aa_three_groups', 'twelve_groups', 'official_na'])
def test_actual_retained_alignment_metadata_arithmetic_matches_standard_native_policy(case):
    old, args, params = retained_inputs(case)
    counts = biological_group_counts(old['alignment'], **args)
    assert len(counts['sites']) == len(old['counts']['sites'])
    for biological, native in zip(counts['sites'], old['counts']['sites']):
        assert {k: v for k, v in biological.items() if k != 'table_id'} == {
            k: v for k, v in native.items() if k != 'table_id'}
    stats = biological_group_statistics(counts, **params)
    native = metacats_statistics(old['counts'], **{**old['statistical_parameters'], 'pair_df_policy': 'standard_pair'})
    for key in ('omnibus', 'pairs'):
        assert len(stats[key]) == len(native[key])
        for a, b in zip(stats[key], native[key]):
            for field in ('augmented_counts', 'expected_counts', 'augmented_symbols', 'raw_symbols'):
                assert a[field] == b[field]
            for field in ('epsilon', 'augmented_total', 'continuity_delta', 'chi_square', 'df', 'mathematical_p', 'log_p'):
                assert a[field]['value'] == b[field]['value']
    if case in ('aa_two_groups', 'aa_three_groups', 'twelve_groups'):
        assert len(counts['sites']) == 4 and len(stats['omnibus']) == 1


def test_three_group_biological_pair_df_does_not_copy_native_aa_anomaly():
    old, args, params = retained_inputs('aa_three_groups')
    counts = biological_group_counts(old['alignment'], **args)
    biological = biological_group_statistics(counts, **params)['pairs'][0]
    native = metacats_statistics(old['counts'], **old['statistical_parameters'])['pairs'][0]
    assert biological['group_population_count'] == 3
    assert biological['df']['value'] == 2 and native['df']['value'] == 4
    assert biological['mathematical_p']['value'] == pytest.approx(.00248371298657324)
    assert native['mathematical_p']['value'] == pytest.approx(.017381025135296442)


@pytest.mark.parametrize('policy', ['native_source', 'full_category_group_count'])
def test_biological_df_rejects_native_source_policies(policy):
    with pytest.raises(ValueError, match='^bvbrc_biological_'):
        biological_group_statistics(make_counts(), **{**STAT_PARAMS, 'pair_df_policy': policy})


def test_metadata_only_groups_are_retained_without_r_order():
    old, args, params = retained_inputs('metadata_only_first_group')
    counts = biological_group_counts(old['alignment'], **args)
    assert [g['group_id'] for g in counts['group_population']['groups']] == ['B', 'C', 'A']
    assert all(row[2] == 0 for site in counts['sites'] for row in site['observed_counts'])
    stats = biological_group_statistics(counts, **params)
    assert stats['omnibus'][0]['group_population_count'] == 3
    assert stats['omnibus'][0]['df']['value'] == 2
    effects = biological_group_effects(counts, selected_pairs=(('B', 'C'), ('A', 'B')),
                                       zero_margin_policy='drop_for_raw_effect_only')
    site = effects['sites'][1]
    assert site['effective_group_count'] == 2 and site['cramers_v']['value'] == pytest.approx(1)
    assert site['pairs'][0]['total_variation']['value'] == 1
    assert site['pairs'][1]['total_variation']['value'] is None


def test_group_order_and_membership_identities_are_explicit():
    alignment, args = make_inputs(['A', 'A', 'C', 'C'], ['A', 'A', 'B', 'B'])
    original = biological_group_counts(alignment, **args)
    permuted = biological_group_counts(alignment, **{**args, 'assignments': tuple(reversed(args['assignments']))})
    assert original['sites'] == permuted['sites']
    changed = deepcopy(args)
    changed['assignments'][1]['group_id'], changed['assignments'][2]['group_id'] = 'B', 'A'
    mixed = biological_group_counts(alignment, **changed)
    assert mixed['sites'][0]['observed_counts'] == [[1, 1], [1, 1]]
    assert original['sites'][0]['table_id'] != mixed['sites'][0]['table_id']
    reordered = deepcopy(args)
    reordered['group_population']['groups'].reverse()
    swapped = biological_group_counts(alignment, **reordered)
    assert swapped['sites'][0]['observed_counts'] == [[0, 2], [2, 0]]
    assert original['sites'][0]['table_id'] != swapped['sites'][0]['table_id']


def test_assignment_evidence_and_original_identity_are_part_of_table_id():
    alignment, args = make_inputs(['A', 'C'], ['A', 'B'])
    original = biological_group_counts(alignment, **args)
    args['assignments'][0]['member_key'] = {'input_binding_id': 'source', 'member_id': 'member', 'occurrence_index': 0}
    amended = biological_group_counts(alignment, **args)
    assert original['sites'][0]['observed_counts'] == amended['sites'][0]['observed_counts']
    assert original['sites'][0]['table_id'] != amended['sites'][0]['table_id']


def test_duplicate_labels_and_cross_category_members_are_not_deduplicated():
    alignment, args = make_inputs(['A', 'C'], ['A', 'B'], labels=['same', 'same'])
    first = biological_group_counts(alignment, **args)
    args = deepcopy(args)
    args['category_id'] = args['group_population']['category_id'] = 'second_category'
    for row in args['assignments']:
        row['category_id'] = 'second_category'
    second = biological_group_counts(alignment, **args)
    assert first['sites'][0]['observed_counts'] == second['sites'][0]['observed_counts'] == [[1, 0], [0, 1]]
    assert first['sites'][0]['table_id'] != second['sites'][0]['table_id']


@pytest.mark.parametrize('missing', ['absent', 'missing', 'conflicting'])
def test_missing_or_conflicting_membership_keeps_partial_counts(missing):
    alignment, args = make_inputs(['A', 'C'], ['A', 'B'])
    if missing == 'absent':
        args['assignments'] = args['assignments'][:1]
    else:
        args['assignments'][1].update(state=missing, group_id=None)
    counts = biological_group_counts(alignment, **args)
    site = counts['sites'][0]
    assert counts['status'] == 'partial' and site['observed_counts'] == [[1, 0]]
    assert site['unresolved_row_indices'] == [1]
    stats = biological_group_statistics(counts, **STAT_PARAMS)
    assert stats['omnibus'] == stats['pairs'] == []
    assert {r['reason'] for r in stats['exclusions']} == {'unresolved'}
    effect = biological_group_effects(counts, **EFFECT_PARAMS)['sites'][0]
    assert effect['raw_chi_square']['value'] is None and effect['raw_expected'] == [[1.0]]
    assert effect['raw_adequacy']['cell_denominator']['value'] is None


@pytest.mark.parametrize('tamper', ['duplicate_row', 'foreign_alignment', 'foreign_category', 'unknown_group',
                                  'resolved_null_group', 'invalid_member', 'invalid_evidence'])
def test_contradictory_assignment_operands_raise_specific_errors(tamper):
    alignment, args = make_inputs(['A', 'C'], ['A', 'B'])
    if tamper == 'duplicate_row':
        args['assignments'] += (deepcopy(args['assignments'][0]),)
    elif tamper == 'foreign_alignment':
        args['assignments'][0]['alignment_id'] = 'other'
    elif tamper == 'foreign_category':
        args['assignments'][0]['category_id'] = 'other'
    elif tamper == 'unknown_group':
        args['assignments'][0]['group_id'] = 'unknown'
    elif tamper == 'resolved_null_group':
        args['assignments'][0]['group_id'] = None
    elif tamper == 'invalid_member':
        args['assignments'][0]['member_key'] = {'input_binding_id': 'i', 'member_id': 'm', 'occurrence_index': True}
    else:
        args['assignments'][0]['evidence'] = [{'content': {}, 'pointer': ''}]
    with pytest.raises(ValueError, match='^bvbrc_biological_'):
        biological_group_counts(alignment, **args)


def test_literal_case_hash_internal_and_terminal_gaps_with_site_subset():
    alignment, args = make_inputs(['-a-#C-', 'AA-CC-'], ['A', 'B'])
    counts = biological_group_counts(alignment, **args)
    assert counts['sites'][0]['excluded_terminal_rows_by_group'] == [[0], []]
    assert counts['sites'][1]['symbols'] == ['A', 'a']
    assert counts['sites'][3]['excluded_original_hash_rows_by_group'] == [[0], []]
    assert counts['sites'][5]['excluded_terminal_rows_by_group'] == [[0], [1]]
    subset = biological_group_counts(alignment, **{**args, 'population': {**args['population'], 'columns_0based': [2]}})
    assert subset['sites'][0]['symbols'] == ['-']
    assert subset['sites'][0]['internal_gap_rows_by_group'] == [[0], [1]]
    upper = biological_group_counts(alignment, **{**args, 'case_policy': 'uppercase'})
    assert upper['sites'][1]['symbols'] == ['A'] and upper['sites'][1]['state'] == 'conserved'
    assert upper['sites'][1]['table_id'] != counts['sites'][1]['table_id']


@pytest.mark.parametrize('state', ['partial', 'truncated', 'unknown'])
def test_incomplete_rows_do_not_establish_trailing_dash_terminality(state):
    alignment, args = make_inputs(['CAAAA', 'AC-'], ['A', 'B'], columns=[1, 2, 4])
    alignment['completeness'] = state
    counts = biological_group_counts(alignment, **args)
    assert all(site['state'] == 'unresolved' for site in counts['sites'])
    assert counts['sites'][1]['unresolved_row_indices'] == [1]
    assert counts['sites'][1]['excluded_terminal_rows_by_group'] == [[], []]
    assert counts['sites'][2]['unresolved_row_indices'] == [1]
    assert counts['sites'][0]['completeness'] == ('truncated' if state == 'truncated' else 'partial')


def test_incomplete_group_population_keeps_counts_and_withholds_inference():
    alignment, args = make_inputs(['A', 'C'], ['A', 'B'])
    args['group_population']['completeness'] = 'unknown'
    counts = biological_group_counts(alignment, **args)
    assert counts['sites'][0]['observed_counts'] == [[1, 0], [0, 1]]
    assert counts['sites'][0]['state'] == 'unresolved'
    assert biological_group_statistics(counts, **STAT_PARAMS)['omnibus'] == []


@pytest.mark.parametrize('sequence', ['-A-', '###', ''])
def test_all_missing_conserved_and_zero_column_populations_have_no_eligible_tests(sequence):
    counts = make_counts([sequence, sequence], ['A', 'B'])
    stats = biological_group_statistics(counts, **STAT_PARAMS)
    assert stats['omnibus'] == stats['pairs'] == []
    assert len(stats['exclusions']) == 2 * len(sequence)
    family = family_for(stats)
    result = adjust_p_values((), family=family, method='holm', alpha=.05,
                             dependence_assumption='none_required_between_tests')
    assert result['status'] == 'ok' and result['results'] == [] and result['total_test_count'] == 0


def test_one_group_variable_site_is_explicit_degenerate_df_exclusion():
    counts = make_counts(['A', 'C'], ['A', 'A'])
    stats = biological_group_statistics(counts, **{**STAT_PARAMS, 'selected_pairs': ()})
    assert stats['status'] == 'partial' and stats['omnibus'] == []
    assert stats['exclusions'][0]['reason'] == 'degenerate_df'


def test_raw_effect_is_signed_and_reverses_with_pair_order():
    counts = make_counts(['A', 'A', 'C', 'C', 'C', 'A'], ['A'] * 3 + ['B'] * 3)
    effect = biological_group_effects(counts, selected_pairs=(('A', 'B'), ('B', 'A')),
                                       zero_margin_policy='drop_for_raw_effect_only')['sites'][0]
    forward, reverse = effect['pairs']
    assert [d['value']['value'] for d in forward['frequency_deltas']] == pytest.approx([1/3, -1/3])
    assert [d['value']['value'] for d in reverse['frequency_deltas']] == pytest.approx([-1/3, 1/3])
    assert forward['total_variation']['value'] == reverse['total_variation']['value'] == pytest.approx(1/3)
    assert effect['cramers_v']['value'] == pytest.approx(1/3)


def test_zero_epsilon_na_padding_preserves_known_expected_zeros_and_null_inference():
    stats = biological_group_statistics(make_counts(['A', 'C'], ['A', 'B']),
                                       **{**STAT_PARAMS, 'alphabet': 'na', 'epsilon': 0})
    row = stats['omnibus'][0]
    assert stats['status'] == 'partial'
    assert row['augmented_symbols'] == ['A', 'C', 'G', 'T']
    assert row['expected_counts'] == [[.5, .5], [.5, .5], [0, 0], [0, 0]]
    assert row['numerical_state'] == 'unavailable' and row['mathematical_p']['value'] is None


@pytest.mark.parametrize('key,bad', [('epsilon', -1), ('epsilon', True), ('epsilon', math.nan),
    ('alphabet', 'dna'), ('nucleotide_padding', 'none'), ('omnibus_continuity', 'none'),
    ('selected_pairs', (('A', 'A'),)), ('selected_pairs', (('A', 'missing'),)),
    ('selected_pairs', (('A', 'B'), ('A', 'B'))),
    ('distribution_backend', {'name': 'unverified', 'version': scipy.__version__})])
def test_statistics_reject_invalid_parameters(key, bad):
    with pytest.raises(ValueError, match='^bvbrc_biological_'):
        biological_group_statistics(make_counts(), **{**STAT_PARAMS, key: bad})


@pytest.mark.parametrize('tamper', ['extra_native', 'counts', 'membership', 'gap', 'symbol_order', 'category', 'state'])
def test_saved_count_relationships_and_closed_schema_reject_corruption(tamper):
    counts = make_counts()
    if tamper == 'extra_native': counts['group_order'] = []
    elif tamper == 'counts': counts['sites'][0]['observed_counts'][0][0] += 1
    elif tamper == 'membership': counts['sites'][0]['included_rows_by_group'][1][0] = 0
    elif tamper == 'gap': counts['sites'][0]['internal_gap_rows_by_group'][0] = [0]
    elif tamper == 'symbol_order': counts['sites'][0]['symbols'].reverse()
    elif tamper == 'category': counts['group_population']['category_id'] = 'other'
    else: counts['sites'][0]['state'] = 'conserved'
    with pytest.raises(ValueError, match='^bvbrc_biological_'):
        validate_biological_counts(counts)


@pytest.mark.parametrize('tamper', ['expected', 'df', 'p', 'population', 'method', 'extra_native', 'empty_expected',
                                  'delta', 'statistic', 'test_id', 'missing_pair', 'unserializable_groups', 'overflow'])
def test_saved_statistical_relationships_reject_corruption(tamper):
    stats = biological_group_statistics(make_counts(), **STAT_PARAMS)
    row = stats['pairs'][0]
    if tamper == 'expected': row['expected_counts'][0][0] += 1
    elif tamper == 'df': row['df']['value'] = 99
    elif tamper == 'p': row['mathematical_p']['value'] = .9
    elif tamper == 'population': row['df']['population_id'] = 'other'
    elif tamper == 'method': row['method_id'] = 'metacats_native_df'
    elif tamper == 'extra_native': row['native_zero_rule_p'] = deepcopy(row['mathematical_p'])
    elif tamper == 'empty_expected': row['expected_counts'] = []
    elif tamper == 'delta': row['continuity_delta']['value'] = .5
    elif tamper == 'statistic': row['chi_square']['value'] = 1
    elif tamper == 'test_id': row['test_id'] = 'biological_group_test:forged'
    elif tamper == 'missing_pair': stats['pairs'] = []
    elif tamper == 'unserializable_groups': row['group_ids'] = {'A', 'B'}
    else: row['augmented_counts'] = [[1e308, 1e308], [1e308, 1e308]]
    with pytest.raises(ValueError, match='^bvbrc_biological_'):
        validate_biological_statistics(stats)


@pytest.mark.parametrize('tamper', ['v', 'delta', 'variation', 'adequacy', 'native_label', 'denominator'])
def test_saved_effect_relationships_reject_corruption(tamper):
    effects = biological_group_effects(make_counts(), **EFFECT_PARAMS)
    row = effects['sites'][0]
    if tamper == 'v': row['cramers_v']['value'] = .5
    elif tamper == 'delta': row['pairs'][0]['frequency_deltas'][0]['value']['value'] = -1
    elif tamper == 'variation': row['pairs'][0]['total_variation']['value'] = .4
    elif tamper == 'adequacy': row['raw_adequacy']['cells_below_5']['value'] = 0
    elif tamper == 'native_label': row['native_fewer_5_recalculated'] = 'Y'
    else: row['cramers_v']['denominator'] = 1
    with pytest.raises(ValueError, match='^bvbrc_biological_'):
        validate_biological_effects(effects)


def test_underflow_has_log_tail_without_native_zero_to_one():
    old, args, params = retained_inputs('native_pair_tail_underflow')
    counts = biological_group_counts(old['alignment'], **args)
    stats = biological_group_statistics(counts, **params)
    row = stats['pairs'][0]
    assert row['numerical_state'] == 'underflow' and row['mathematical_p']['state'] == 'failed'
    assert row['mathematical_p']['value'] is None and math.isfinite(row['log_p']['value'])
    assert row['log_p']['value'] < -2000 and 'native_zero_rule_p' not in row
    family = family_for(stats)
    p = tuple({'test_id': r['test_id'], 'value': r['mathematical_p']} for r in stats['omnibus'])
    result = adjust_p_values(p, family=family, method='holm', alpha=.05,
                             dependence_assumption='none_required_between_tests')
    assert result['status'] == 'partial' and result['observed_p_count'] == 0
    assert result['results'][0]['adjusted_p']['value'] is None


@pytest.mark.parametrize('basis', ['native_unadjusted', 'source_mathematical_recalculation',
                                 'biological_mathematical_recalculation'])
def test_multiplicity_provenance_is_additive_without_reinterpreting_old_values(basis):
    family = family_for(biological_group_statistics(make_counts(), **STAT_PARAMS))
    family['p_value_basis'] = basis
    assert validate_test_family(family)['p_value_basis'] == basis
    family['p_value_basis'] = 'invented_probability'
    with pytest.raises(ValueError): validate_test_family(family)


@pytest.mark.parametrize('state,assumption', [('known_count_only', 'independently_known_count'),
                                            ('declared_upper_bound', 'parent_declared_upper_bound')])
def test_biological_known_count_bonferroni_exception_and_bh_assumption_preserved(state, assumption):
    stats = biological_group_statistics(make_counts(), **STAT_PARAMS)
    family = family_for(stats)
    p = tuple({'test_id': r['test_id'], 'value': r['mathematical_p']} for r in stats['omnibus'])
    result = adjust_p_values(p, family=family, method='bh', alpha=.05,
                             dependence_assumption='none_required_between_tests')
    assert result['status'] == 'partial'
    family.update(population_state=state, total_test_count=10,
                  assumption={'kind': assumption, 'count': 10, 'evidence': []})
    bonferroni = adjust_p_values(p, family=family, method='bonferroni', alpha=.05,
                                dependence_assumption='none_required_between_tests')
    assert bonferroni['results'][0]['adjusted_p']['value'] == 10 * p[0]['value']['value']
    holm = adjust_p_values(p, family=family, method='holm', alpha=.05,
                          dependence_assumption='none_required_between_tests')
    assert holm['status'] == 'partial' and holm['results'][0]['adjusted_p']['value'] is None


def test_saved_recalculation_and_detached_validation_need_no_io_or_parser(monkeypatch):
    alignment, args = make_inputs(['A'] * 6 + ['C'] * 6, ['A'] * 6 + ['B'] * 6)
    original = json.dumps([alignment, args], allow_nan=False, sort_keys=True)
    counts = biological_group_counts(alignment, **args)
    stats = biological_group_statistics(counts, **STAT_PARAMS)
    effects = biological_group_effects(counts, **EFFECT_PARAMS)
    def forbidden(*args, **kwargs): raise AssertionError('io_or_parser_or_calculator_forbidden')
    monkeypatch.setattr(builtins, 'open', forbidden)
    monkeypatch.setattr(Path, 'open', forbidden)
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    monkeypatch.setattr(Path, 'read_text', forbidden)
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr('gene_annotation_episode.bvbrc_metacats_input_formats.parse_metacats_input_fasta', forbidden)
    assert biological_group_counts(alignment, **args) == counts
    assert biological_group_statistics(json.loads(json.dumps(counts)), **STAT_PARAMS) == stats
    changed = biological_group_statistics(counts, **{**STAT_PARAMS, 'epsilon': .5})
    assert changed['omnibus'][0]['test_id'] != stats['omnibus'][0]['test_id']
    assert changed['omnibus'][0]['chi_square']['value'] != stats['omnibus'][0]['chi_square']['value']
    assert biological_group_effects(counts, **EFFECT_PARAMS) == effects
    for name in ('biological_group_counts', 'biological_group_statistics', 'biological_group_effects', 'chi_square_tail'):
        monkeypatch.setattr('gene_annotation_episode.bvbrc_metacats_biological_calculators.' + name, forbidden)
    for value, validator in ((counts, validate_biological_counts), (stats, validate_biological_statistics),
                             (effects, validate_biological_effects)):
        saved = json.loads(json.dumps(value, allow_nan=False))
        detached = validator(saved)
        assert detached == value and detached is not saved
    assert json.dumps([alignment, args], allow_nan=False, sort_keys=True) == original


def test_shared_expected_and_pearson_kernels_preserve_numerical_formulas():
    matrix = ((6., 0.), (0., 6.))
    result = expected_contingency_counts(matrix)
    assert result == {'expected_counts': [[3., 3.], [3., 3.]], 'total': 12.}
    assert pearson_contingency_statistic(matrix, expected=result['expected_counts'], continuity_delta=0) == pytest.approx(12)
    assert pearson_contingency_statistic(matrix, expected=result['expected_counts'], continuity_delta=.5) == pytest.approx(25/3)
    # Delta is an explicit parameter; no clamp replaces negative O-E-delta.
    assert pearson_contingency_statistic(((1.,),), expected=((1.,),), continuity_delta=.5) == .25
    assert expected_contingency_counts(((0., 0.),)) == {'expected_counts': [[0., 0.]], 'total': 0.}
    assert pearson_contingency_statistic(((0., 0.),), expected=((0., 0.),), continuity_delta=0) is None
    assert expected_contingency_counts(()) == {'expected_counts': [], 'total': 0}
    assert pearson_contingency_statistic((), expected=(), continuity_delta=0) is None
    large = expected_contingency_counts(((1e200, 1e200), (1e200, 1e200)))
    assert all(math.isfinite(n) for row in large['expected_counts'] for n in row)


@pytest.mark.parametrize('matrix', [((1, 2), (3,)), ((True,),), ((-1,),), ((math.inf,),), ((math.nan,),), (('1',),)])
def test_shared_matrix_kernels_reject_invalid_operands(matrix):
    with pytest.raises(ValueError, match='^bvbrc_contingency_'):
        expected_contingency_counts(matrix)


def test_count_kernel_requires_exact_selected_row_population():
    alignment, args = make_inputs(['A', 'C'], ['A', 'B'])
    common = {'population': args['population'], 'group_count': 2, 'groups_complete': True,
              'case_policy': 'preserve', 'terminal_gap_policy': 'exclude_terminal_dash', 'original_hash_policy': 'exclude_hash'}
    rows = ({'row_index': 0, 'group_index': 0}, {'row_index': 1, 'group_index': 1})
    assert count_alignment_group_sites(alignment, row_groups=rows, **common)[0]['observed_counts'] == [[1, 0], [0, 1]]
    for malformed in (rows[:1], rows + rows[:1], ({'row_index': 0, 'group_index': 5}, rows[1])):
        with pytest.raises(ValueError, match='^bvbrc_contingency_'):
            count_alignment_group_sites(alignment, row_groups=malformed, **common)
