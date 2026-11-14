"""Closed pure operands for MetaCATS counts and explicit statistical calculations."""
from copy import deepcopy
import math

from . import phylogeny_calculation_contracts as c
from .bvbrc_alignment_values import validate_numeric_cell, diagnostic, requirement


def require(ok, code):
    if not ok:
        raise ValueError('bvbrc_metacats_' + code)


def shape(value, keys, code='shape_invalid'):
    require(type(value) is dict and set(value) == set(keys), code)


def text(value, nullable=False):
    require(nullable and value is None or type(value) is str and bool(value), 'text_invalid')


def integer(value, minimum=0, nullable=False):
    require(nullable and value is None or type(value) is int and value >= minimum, 'integer_invalid')


def finite(value):
    require(type(value) is int or type(value) is float and math.isfinite(value), 'number_invalid')


def _reports(value):
    for key in ('requirements', 'diagnostics'):
        require(type(value[key]) is list, 'reports_invalid')
    for row in value['requirements']:
        shape(row, {'requirement_id', 'kind', 'role', 'source_refs', 'reason_code'})
        require(requirement(**row) == row, 'requirement_invalid')
    for row in value['diagnostics']:
        shape(row, {'code', 'phase', 'path', 'severity', 'evidence_refs'})
        require(diagnostic(**row) == row, 'diagnostic_invalid')


def _matrix(value, rows, columns):
    require(type(value) is list and len(value) == rows, 'matrix_rows_invalid')
    for row in value:
        require(type(row) is list and len(row) == columns, 'matrix_columns_invalid')
        for number in row:
            finite(number)
            require(number >= 0, 'negative_count')


def _cell(value, *, unit=None, population=None, method=None):
    validate_numeric_cell(value)
    require(unit is None or value['unit'] == unit, 'cell_unit_conflict')
    require(population is None or value['population_id'] == population, 'cell_population_conflict')
    require(method is None or value['method_id'] == method, 'cell_method_conflict')


def group_column(value):
    shape(value, {'category_id', 'r_column_index_0based', 'r_group_token', 'native_group_ordinal',
        'group_id', 'exported_heading_index_0based', 'exported_label_token', 'state', 'evidence'})
    text(value['category_id'])
    integer(value['r_column_index_0based'])
    text(value['r_group_token'])
    integer(value['native_group_ordinal'], minimum=1, nullable=True)
    integer(value['exported_heading_index_0based'], nullable=True)
    text(value['group_id'], nullable=True)
    require(value['exported_label_token'] is None or type(value['exported_label_token']) is str,
            'group_label_invalid')
    require(value['state'] in ('resolved', 'wrong_native_label', 'unresolved'), 'group_state_invalid')
    if value['state'] != 'unresolved':
        require(value['group_id'] is not None and value['native_group_ordinal'] is not None,
                'resolved_group_identity_missing')
    c.evidence(value['evidence'])


def validate_group_order(values, *, category_id):
    require(type(values) in (tuple, list), 'groups_invalid')
    for i, value in enumerate(values):
        group_column(value)
        require(value['category_id'] == category_id and value['r_column_index_0based'] == i,
                'group_column_order_conflict')
    for key in ('group_id', 'native_group_ordinal', 'r_group_token'):
        known = [row[key] for row in values if row[key] is not None]
        require(len(known) == len(set(known)), 'group_identity_duplicate')
    return deepcopy(list(values))


def validate_group_counts(value):
    shape(value, {'status', 'analysis_id', 'population_id', 'alignment_id', 'category_id',
        'group_order', 'method_parameters', 'sites', 'requirements', 'diagnostics'})
    require(value['status'] in ('ok', 'partial', 'invalid'), 'status_invalid')
    for key in ('analysis_id', 'population_id', 'alignment_id', 'category_id'):
        text(value[key])
    groups = validate_group_order(value['group_order'], category_id=value['category_id'])
    params = value['method_parameters']
    shape(params, {'case_policy', 'terminal_mask', 'native_input_hash_policy'})
    require(params['case_policy'] in ('preserve', 'uppercase') and
        params['terminal_mask'] == 'native_terminal_dash_to_hash' and
        params['native_input_hash_policy'] == 'exclude_hash', 'count_parameters_invalid')
    require(type(value['sites']) is list, 'sites_invalid')
    seen_columns, seen_ids = set(), set()
    for site in value['sites']:
        shape(site, {'table_id', 'column_0based', 'state', 'symbols', 'observed_counts',
            'included_rows_by_group', 'excluded_terminal_rows_by_group',
            'excluded_original_hash_rows_by_group', 'internal_gap_rows_by_group',
            'unresolved_row_indices', 'completeness', 'evidence'})
        text(site['table_id'])
        integer(site['column_0based'])
        require(site['column_0based'] not in seen_columns and site['table_id'] not in seen_ids,
                'site_identity_duplicate')
        seen_columns.add(site['column_0based']); seen_ids.add(site['table_id'])
        require(site['state'] in ('all_missing', 'conserved', 'variable', 'unresolved'), 'site_state_invalid')
        require(site['completeness'] in c.COMPLETENESS, 'completeness_invalid')
        c.evidence(site['evidence'])
        symbols, counts = site['symbols'], site['observed_counts']
        require(type(symbols) is list and all(type(s) is str and len(s) == 1 and s != '#' for s in symbols)
                and len(symbols) == len(set(symbols)), 'symbols_invalid')
        require(type(counts) is list and len(counts) == len(symbols), 'count_dimensions_invalid')
        for row in counts:
            require(type(row) is list and len(row) == len(groups), 'count_dimensions_invalid')
            for n in row:
                integer(n)
            require(sum(row) > 0, 'unobserved_symbol_row')
        for key in ('included_rows_by_group', 'excluded_terminal_rows_by_group',
                    'excluded_original_hash_rows_by_group', 'internal_gap_rows_by_group'):
            require(type(site[key]) is list and len(site[key]) == len(groups), 'row_group_dimensions_invalid')
            for rows in site[key]:
                c.unique_indices(rows)
        c.unique_indices(site['unresolved_row_indices'])
        all_rows = set(site['unresolved_row_indices'])
        for j in range(len(groups)):
            included = set(site['included_rows_by_group'][j])
            require(sum(row[j] for row in counts) == len(included), 'count_membership_conflict')
            gap = set(site['internal_gap_rows_by_group'][j])
            require(gap <= included, 'gap_membership_conflict')
            expected_gap = counts[symbols.index('-')][j] if '-' in symbols else 0
            require(len(gap) == expected_gap, 'gap_count_conflict')
            for rows in (included, set(site['excluded_terminal_rows_by_group'][j]),
                         set(site['excluded_original_hash_rows_by_group'][j])):
                require(not all_rows.intersection(rows), 'row_membership_overlap')
                all_rows.update(rows)
        resolved = (site['completeness'] == 'complete' and not site['unresolved_row_indices']
                    and all(g['state'] != 'unresolved' for g in groups))
        expected = ('all_missing' if not symbols else 'conserved' if len(symbols) == 1 else 'variable')
        require(site['state'] == (expected if resolved else 'unresolved'), 'site_state_count_conflict')
    _reports(value)
    return deepcopy(value)


def validate_test_family(value):
    shape(value, {'family_id', 'analysis_ids', 'category_ids', 'test_kind', 'test_ids',
        'eligibility', 'population_state', 'total_test_count', 'assumption', 'p_value_basis', 'evidence'})
    text(value['family_id'])
    for key in ('analysis_ids', 'category_ids', 'test_ids'):
        c.strings(value[key])
    require(value['test_kind'] in ('omnibus', 'pairwise') and
        value['eligibility'] == 'variable_site_positive_df' and
        value['population_state'] in ('complete', 'known_count_only', 'declared_upper_bound', 'unknown') and
        value['p_value_basis'] in ('native_unadjusted', 'source_mathematical_recalculation',
                                 'biological_mathematical_recalculation'), 'family_invalid')
    integer(value['total_test_count'], nullable=True)
    c.evidence(value['evidence'])
    assumption = value['assumption']
    if assumption is not None:
        shape(assumption, {'kind', 'count', 'evidence'})
        require(assumption['kind'] in ('independently_known_count', 'parent_declared_upper_bound'), 'assumption_invalid')
        integer(assumption['count'])
        c.evidence(assumption['evidence'])
        require(assumption['count'] == value['total_test_count'], 'assumption_count_conflict')
    if value['population_state'] == 'complete':
        require(value['total_test_count'] == len(value['test_ids']) and assumption is None,
                'complete_family_count_conflict')
    return deepcopy(value)


def validate_test_p_values(values):
    require(type(values) in (tuple, list), 'p_values_invalid')
    ids = set()
    result = []
    for row in values:
        shape(row, {'test_id', 'value'})
        text(row['test_id'])
        require(row['test_id'] not in ids, 'duplicate_test_id')
        ids.add(row['test_id'])
        cell = validate_numeric_cell(row['value'])
        require(cell['unit'] == 'probability', 'p_unit_invalid')
        if cell['value'] is not None:
            require(0 <= cell['value'] <= 1, 'p_range_invalid')
        result.append(deepcopy(row))
    return result


def validate_statistics(value):
    shape(value, {'status', 'analysis_id', 'category_id', 'method_parameters',
        'omnibus', 'pairs', 'exclusions', 'requirements', 'diagnostics'})
    require(value['status'] in ('ok', 'partial', 'invalid'), 'status_invalid')
    text(value['analysis_id']); text(value['category_id'])
    params = value['method_parameters']
    shape(params, {'alphabet', 'epsilon', 'nucleotide_padding', 'omnibus_continuity',
        'pair_df_policy', 'pair_zero_policy', 'selected_pairs', 'distribution_backend'})
    finite(params['epsilon'])
    require(params['epsilon'] >= 0 and params['alphabet'] in ('na', 'aa') and
        params['nucleotide_padding'] == 'ACGT_at_variable_sites' and
        params['omnibus_continuity'] == 'r_default_2x2_min_delta' and
        params['pair_df_policy'] in ('native_source', 'standard_pair') and
        params['pair_zero_policy'] == 'retain_math_and_native_zero_to_one', 'parameters_invalid')
    shape(params['distribution_backend'], {'name', 'version'})
    text(params['distribution_backend']['name']); text(params['distribution_backend']['version'])
    require(type(params['selected_pairs']) is list, 'pairs_invalid')
    for pair in params['selected_pairs']:
        c.strings(pair)
        require(len(pair) == 2, 'pair_invalid')
    units = {'epsilon': 'pseudocount_per_cell', 'augmented_total': 'augmented_observations',
        'continuity_delta': 'augmented_observations', 'chi_square': 'chi_square',
        'df': 'degrees_of_freedom', 'mathematical_p': 'probability',
        'log_p': 'natural_log_probability', 'native_zero_rule_p': 'probability'}
    ids = set()
    for collection, kind in (('omnibus', 'omnibus'), ('pairs', 'pairwise')):
        require(type(value[collection]) is list, 'statistics_array_invalid')
        for row in value[collection]:
            shape(row, {'test_id', 'kind', 'category_id', 'column_0based', 'group_ids', 'raw_table_id',
                'raw_symbols', 'augmented_symbols', 'r_table_group_count', 'epsilon', 'augmented_counts',
                'expected_counts', 'augmented_total', 'continuity_delta', 'chi_square', 'df',
                'mathematical_p', 'log_p', 'native_zero_rule_p', 'numerical_state', 'method_id',
                'native_observation_ids', 'requirements'})
            text(row['test_id']); text(row['raw_table_id']); text(row['method_id'])
            require(row['test_id'] not in ids, 'duplicate_test_id'); ids.add(row['test_id'])
            require(row['kind'] == kind and row['category_id'] == value['category_id'], 'test_scope_conflict')
            integer(row['column_0based']); integer(row['r_table_group_count'], minimum=2)
            c.strings(row['group_ids']); c.strings(row['raw_symbols']); c.strings(row['augmented_symbols'])
            c.strings(row['native_observation_ids'])
            require(set(row['raw_symbols']) <= set(row['augmented_symbols']), 'symbol_population_conflict')
            require(all(len(x) == 1 for x in row['augmented_symbols']), 'symbol_invalid')
            r, k = len(row['augmented_symbols']), len(row['group_ids'])
            require((k == row['r_table_group_count']) if kind == 'omnibus' else
                    (k == 2 and row['group_ids'] in params['selected_pairs']), 'test_group_conflict')
            _matrix(row['augmented_counts'], r, k); _matrix(row['expected_counts'], r, k)
            for key, unit in units.items():
                _cell(row[key], unit=unit, population=row['test_id'], method=row['method_id'])
            require(row['epsilon']['value'] == params['epsilon'], 'epsilon_conflict')
            expected_df = (r - 1) * (row['r_table_group_count'] - 1) if kind == 'omnibus' or (
                params['alphabet'] == 'aa' and params['pair_df_policy'] == 'native_source') else r - 1
            require(row['df']['value'] == expected_df and expected_df > 0, 'df_conflict')
            require(row['augmented_total']['value'] == math.fsum(math.fsum(x) for x in row['augmented_counts']),
                    'augmented_total_conflict')
            require(row['numerical_state'] in ('finite', 'underflow', 'unavailable'), 'numerical_state_invalid')
            p, logp = row['mathematical_p']['value'], row['log_p']['value']
            if row['numerical_state'] == 'finite':
                require(p is not None and 0 < p <= 1 and logp is not None and
                        math.isclose(logp, math.log(p), rel_tol=1e-12, abs_tol=1e-14), 'p_log_conflict')
            elif row['numerical_state'] == 'underflow':
                require(p is None and row['mathematical_p']['state'] == 'failed' and logp is not None
                        and logp < 0, 'underflow_state_conflict')
            else:
                require(p is None and logp is None, 'unavailable_tail_conflict')
            if kind == 'omnibus':
                require(row['native_zero_rule_p']['value'] is None and
                        row['native_zero_rule_p']['state'] == 'not_measured', 'omnibus_pair_rule_conflict')
            else:
                require(row['native_zero_rule_p']['value'] == (1 if row['numerical_state'] == 'underflow' else p),
                        'native_zero_rule_conflict')
            _reports({'requirements': row['requirements'], 'diagnostics': []})
    require(type(value['exclusions']) is list, 'exclusions_invalid')
    for row in value['exclusions']:
        shape(row, {'column_0based', 'test_kind', 'group_pair', 'reason'})
        integer(row['column_0based'])
        require(row['test_kind'] in ('omnibus', 'pairwise') and row['reason'] in (
            'all_missing', 'conserved_placeholder', 'degenerate_df', 'unresolved'), 'exclusion_invalid')
        if row['test_kind'] == 'omnibus':
            require(row['group_pair'] is None, 'exclusion_pair_conflict')
        else:
            require(row['group_pair'] in params['selected_pairs'], 'exclusion_pair_conflict')
    _reports(value)
    return deepcopy(value)


def _adequacy(value, table_id):
    shape(value, {'table_id', 'minimum_expected', 'cells_below_5', 'cells_below_1', 'cell_denominator'})
    require(value['table_id'] == table_id, 'adequacy_table_conflict')
    for key in ('minimum_expected', 'cells_below_5', 'cells_below_1', 'cell_denominator'):
        _cell(value[key], unit='expected_observations' if key == 'minimum_expected' else 'cells', population=table_id)


def validate_effects(value):
    shape(value, {'status', 'analysis_id', 'category_id', 'zero_margin_policy', 'sites', 'requirements', 'diagnostics'})
    require(value['status'] in ('ok', 'partial', 'invalid') and
            value['zero_margin_policy'] == 'drop_for_raw_effect_only', 'effect_policy_invalid')
    text(value['analysis_id']); text(value['category_id'])
    require(type(value['sites']) is list, 'sites_invalid')
    seen = set()
    for row in value['sites']:
        shape(row, {'raw_table_id', 'column_0based', 'raw_chi_square', 'cramers_v',
            'effective_symbol_count', 'effective_group_count', 'raw_expected', 'augmented_adequacy',
            'raw_adequacy', 'positive_observed_cells_below_5', 'native_fewer_5_recalculated', 'pairs'})
        text(row['raw_table_id']); integer(row['column_0based'])
        require(row['raw_table_id'] not in seen, 'effect_table_duplicate'); seen.add(row['raw_table_id'])
        for key in ('effective_symbol_count', 'effective_group_count', 'positive_observed_cells_below_5'):
            integer(row[key])
        _matrix(row['raw_expected'], row['effective_symbol_count'], row['effective_group_count'])
        for key, unit in (('raw_chi_square', 'chi_square'), ('cramers_v', 'fraction')):
            _cell(row[key], unit=unit, population=row['raw_table_id'])
        require(row['native_fewer_5_recalculated'] in ('Y', 'N', None), 'sparse_flag_invalid')
        _adequacy(row['raw_adequacy'], row['raw_table_id'])
        if row['augmented_adequacy'] is not None:
            _adequacy(row['augmented_adequacy'], row['augmented_adequacy']['table_id'])
        require(type(row['pairs']) is list, 'pairs_invalid')
        for pair in row['pairs']:
            shape(pair, {'group_ids', 'frequency_deltas', 'total_variation'})
            c.strings(pair['group_ids']); require(len(pair['group_ids']) == 2, 'pair_invalid')
            require(type(pair['frequency_deltas']) is list, 'deltas_invalid')
            for delta in pair['frequency_deltas']:
                shape(delta, {'symbol', 'value'}); text(delta['symbol'])
                _cell(delta['value'], unit='signed_fraction', population=row['raw_table_id'])
            _cell(pair['total_variation'], unit='fraction', population=row['raw_table_id'])
    _reports(value)
    return deepcopy(value)


def validate_multiplicity(value):
    shape(value, {'status', 'family', 'method', 'alpha', 'dependence_assumption', 'observed_p_count',
        'total_test_count', 'harmonic_factor', 'results', 'requirements', 'diagnostics'})
    family = validate_test_family(value['family'])
    require(value['status'] in ('ok', 'partial', 'invalid') and value['method'] in (
        'none', 'bonferroni', 'holm', 'bh', 'by'), 'multiplicity_invalid')
    finite(value['alpha']); require(0 <= value['alpha'] <= 1, 'alpha_invalid')
    require(value['dependence_assumption'] in ('none_required_between_tests',
        'independent_or_positive_regression_dependence_assumed'), 'dependence_assumption_invalid')
    integer(value['observed_p_count']); integer(value['total_test_count'], nullable=True)
    require(value['total_test_count'] == family['total_test_count'], 'test_count_conflict')
    if value['harmonic_factor'] is not None:
        finite(value['harmonic_factor'])
        require(value['method'] == 'by' and family['population_state'] == 'complete', 'harmonic_method_conflict')
    require(type(value['results']) is list, 'results_invalid')
    inputs = []
    for row in value['results']:
        shape(row, {'test_id', 'input_p', 'adjusted_p', 'rejected_at_alpha'})
        inputs.append({'test_id': row['test_id'], 'value': row['input_p']})
        require(row['test_id'] in family['test_ids'], 'test_outside_family')
        _cell(row['adjusted_p'], unit='probability', population=family['family_id'])
        p = row['adjusted_p']['value']
        if p is None:
            require(row['rejected_at_alpha'] is None, 'unknown_rejection_conflict')
        else:
            require(0 <= p <= 1 and type(row['rejected_at_alpha']) is bool and
                row['rejected_at_alpha'] == (p <= value['alpha']), 'rejection_conflict')
    validate_test_p_values(inputs)
    require(value['observed_p_count'] == sum(row['value']['state'] == 'available' for row in inputs),
            'observed_p_count_conflict')
    _reports(value)
    return deepcopy(value)
