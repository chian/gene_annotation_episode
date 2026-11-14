"""Closed biological-group operands and saved numerical results.

These validators check supplied relationships, not external custody. They do
not require R column tokens or infer original sequence identity from labels.
Saved validation is independent of calculation, acquisition and SciPy calls.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math

from . import phylogeny_calculation_contracts as shared
from .phylogeny_format_contracts import validate_alignment_document
from .bvbrc_alignment_values import validate_numeric_cell, diagnostic, requirement


def require(condition, code):
    if not condition:
        raise ValueError('bvbrc_biological_' + code)


def shape(value, keys, code='shape_invalid'):
    require(type(value) is dict and set(value) == set(keys), code)


def text(value, *, nullable=False, empty=False):
    require(nullable and value is None or type(value) is str and (empty or bool(value)), 'text_invalid')


def integer(value, *, minimum=0, nullable=False):
    require(nullable and value is None or type(value) is int and value >= minimum, 'integer_invalid')


def finite(value):
    require(type(value) in (int, float), 'number_invalid')
    try:
        valid = math.isfinite(value)
    except OverflowError:
        valid = False
    require(valid, 'number_invalid')


def _sum(values):
    try:
        result = math.fsum(values)
    except OverflowError as exc:
        raise ValueError('bvbrc_biological_total_nonfinite') from exc
    finite(result)
    return result


def _shared(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except ValueError as exc:
        raise ValueError('bvbrc_biological_' + str(exc)) from exc


def evidence(value):
    _shared(shared.evidence, value)


def strings(value):
    _shared(shared.strings, value)


def indices(value):
    _shared(shared.unique_indices, value)


def reports(value):
    for key in ('requirements', 'diagnostics'):
        require(type(value[key]) is list, 'reports_invalid')
    seen = set()
    for row in value['requirements']:
        shape(row, {'requirement_id', 'kind', 'role', 'source_refs', 'reason_code'})
        require(_shared(requirement, **row) == row, 'requirement_invalid')
        require(row['requirement_id'] not in seen, 'requirement_duplicate')
        seen.add(row['requirement_id'])
    for row in value['diagnostics']:
        shape(row, {'code', 'phase', 'path', 'severity', 'evidence_refs'})
        require(_shared(diagnostic, **row) == row, 'diagnostic_invalid')
    return seen


def matrix(value, rows, columns, *, counts=False):
    require(type(value) is list and len(value) == rows, 'matrix_rows_invalid')
    for row in value:
        require(type(row) is list and len(row) == columns, 'matrix_columns_invalid')
        for n in row:
            integer(n) if counts else finite(n)
            require(n >= 0, 'negative_count')


def cell(value, *, population, unit, method=None, requirements=None):
    _shared(validate_numeric_cell, value)
    require(value['unit'] == unit and value['population_id'] == population, 'cell_population_or_unit_conflict')
    require(value['origin'] == 'calculated', 'cell_origin_conflict')
    require(value['method_id'] == method if method else value['method_id'].startswith('biological_group_'),
            'cell_method_conflict')
    if requirements is not None:
        require(set(value['requirement_ids']) <= set(requirements), 'cell_requirement_unresolved')


def _envelope(value):
    require(value['status'] in ('ok', 'partial', 'invalid'), 'status_invalid')
    text(value['analysis_id']); text(value['category_id'])
    ids = reports(value)
    require(not ids or value['status'] != 'ok', 'status_requirements_conflict')
    return ids


def validate_biological_group_population(value: dict, *, category_id: str) -> dict:
    text(category_id)
    shape(value, {'group_population_id', 'category_id', 'groups', 'completeness', 'evidence'})
    text(value['group_population_id'])
    require(value['category_id'] == category_id, 'group_category_conflict')
    require(value['completeness'] in shared.COMPLETENESS, 'group_completeness_invalid')
    evidence(value['evidence'])
    require(type(value['groups']) is list, 'groups_invalid')
    seen = set()
    for group in value['groups']:
        shape(group, {'group_id', 'raw_group_value', 'evidence'})
        text(group['group_id']); text(group['raw_group_value'], empty=True)
        evidence(group['evidence'])
        require(group['group_id'] not in seen, 'group_identity_duplicate')
        seen.add(group['group_id'])
    return deepcopy(value)


def validate_biological_assignments(values, *, alignment: dict, category_id: str,
                                    group_population: dict) -> list[dict]:
    alignment = _shared(validate_alignment_document, alignment)
    groups = validate_biological_group_population(group_population, category_id=category_id)
    known = {g['group_id'] for g in groups['groups']}
    require(type(values) in (tuple, list), 'assignments_invalid')
    seen = set()
    for row in values:
        shape(row, {'category_id', 'alignment_id', 'row_index', 'member_key', 'group_id', 'state', 'evidence'})
        require(row['category_id'] == category_id and row['alignment_id'] == alignment['alignment_id'],
                'assignment_scope_conflict')
        integer(row['row_index'])
        require(row['row_index'] < len(alignment['rows']), 'assignment_row_outside_alignment')
        require(row['row_index'] not in seen, 'duplicate_row_assignment')
        seen.add(row['row_index'])
        require(row['state'] in ('resolved', 'missing', 'conflicting'), 'assignment_state_invalid')
        text(row['group_id'], nullable=True)
        require(row['group_id'] is None or row['group_id'] in known, 'assignment_group_unknown')
        require(row['state'] != 'resolved' or row['group_id'] is not None, 'resolved_group_identity_missing')
        require(row['state'] != 'missing' or row['group_id'] is None, 'missing_group_identity_conflict')
        # A recorded conflict is unresolved evidence. Repeated physical-row
        # records are rejected above; no first/last candidate is selected.
        if row['member_key'] is not None:
            shape(row['member_key'], {'input_binding_id', 'member_id', 'occurrence_index'})
            text(row['member_key']['input_binding_id']); text(row['member_key']['member_id'])
            integer(row['member_key']['occurrence_index'])
        evidence(row['evidence'])
    return deepcopy(list(values))


def validate_biological_counts(value: dict) -> dict:
    shape(value, {'status', 'analysis_id', 'population_id', 'alignment_id', 'category_id',
        'group_population', 'method_parameters', 'sites', 'requirements', 'diagnostics'})
    _envelope(value)
    text(value['population_id']); text(value['alignment_id'])
    population = validate_biological_group_population(value['group_population'], category_id=value['category_id'])
    groups = population['groups']
    params = value['method_parameters']
    shape(params, {'case_policy', 'terminal_gap_policy', 'original_hash_policy'})
    require(params['case_policy'] in ('preserve', 'uppercase') and
            params['terminal_gap_policy'] == 'exclude_terminal_dash' and
            params['original_hash_policy'] == 'exclude_hash', 'count_parameters_invalid')
    require(type(value['sites']) is list, 'sites_invalid')
    seen_ids, seen_columns, known_groups = set(), set(), {}
    selected_rows = None
    for site in value['sites']:
        shape(site, {'table_id', 'column_0based', 'state', 'symbols', 'observed_counts',
            'included_rows_by_group', 'excluded_terminal_rows_by_group',
            'excluded_original_hash_rows_by_group', 'internal_gap_rows_by_group',
            'unresolved_row_indices', 'completeness', 'evidence'})
        text(site['table_id']); integer(site['column_0based'])
        require(site['table_id'].startswith('biological_group_counts:'), 'count_identity_kind_conflict')
        require(site['table_id'] not in seen_ids and site['column_0based'] not in seen_columns, 'site_identity_duplicate')
        seen_ids.add(site['table_id']); seen_columns.add(site['column_0based'])
        require(site['completeness'] in shared.COMPLETENESS, 'completeness_invalid')
        evidence(site['evidence'])
        symbols, counts = site['symbols'], site['observed_counts']
        strings(symbols)
        require(symbols == sorted(symbols) and all(len(s) == 1 and s != '#' for s in symbols), 'symbols_invalid')
        matrix(counts, len(symbols), len(groups), counts=True)
        require(all(sum(row) > 0 for row in counts), 'unobserved_symbol_row')
        for key in ('included_rows_by_group', 'excluded_terminal_rows_by_group',
                    'excluded_original_hash_rows_by_group', 'internal_gap_rows_by_group'):
            require(type(site[key]) is list and len(site[key]) == len(groups), 'row_group_dimensions_invalid')
            for rows in site[key]:
                indices(rows)
        indices(site['unresolved_row_indices'])
        all_rows = set(site['unresolved_row_indices'])
        for j in range(len(groups)):
            included = set(site['included_rows_by_group'][j])
            require(sum(row[j] for row in counts) == len(included), 'count_membership_conflict')
            gaps = set(site['internal_gap_rows_by_group'][j])
            require(gaps <= included and len(gaps) == (counts[symbols.index('-')][j] if '-' in symbols else 0),
                    'gap_membership_conflict')
            for rows in (included, set(site['excluded_terminal_rows_by_group'][j]),
                         set(site['excluded_original_hash_rows_by_group'][j])):
                require(not all_rows.intersection(rows), 'row_membership_overlap')
                all_rows.update(rows)
                for index in rows:
                    require(index not in known_groups or known_groups[index] == j, 'row_group_across_sites_conflict')
                    known_groups[index] = j
        require(selected_rows is None or all_rows == selected_rows, 'site_row_population_conflict')
        selected_rows = all_rows
        resolved = (site['completeness'] == population['completeness'] == 'complete'
                    and not site['unresolved_row_indices'])
        state = 'all_missing' if not symbols else 'conserved' if len(symbols) == 1 else 'variable'
        require(site['state'] == (state if resolved else 'unresolved'), 'site_state_count_conflict')
        require(site['state'] != 'unresolved' or value['requirements'], 'unresolved_requirement_missing')
    return deepcopy(value)


STATISTIC_UNITS = {'epsilon': 'pseudocount_per_cell', 'augmented_total': 'augmented_observations',
    'continuity_delta': 'augmented_observations', 'chi_square': 'chi_square',
    'df': 'degrees_of_freedom', 'mathematical_p': 'probability', 'log_p': 'natural_log_probability'}


def _selected_pairs(value):
    require(type(value) is list, 'pairs_invalid')
    seen = set()
    for pair in value:
        strings(pair)
        require(len(pair) == 2, 'pair_invalid')
        require(tuple(pair) not in seen, 'pair_duplicate')
        seen.add(tuple(pair))
    return seen


def validate_biological_statistics(value: dict) -> dict:
    shape(value, {'status', 'analysis_id', 'category_id', 'method_parameters', 'omnibus',
                  'pairs', 'exclusions', 'requirements', 'diagnostics'})
    requirement_ids = _envelope(value)
    params = value['method_parameters']
    shape(params, {'alphabet', 'epsilon', 'nucleotide_padding', 'omnibus_continuity',
                  'pair_df_policy', 'selected_pairs', 'distribution_backend'})
    finite(params['epsilon'])
    require(params['epsilon'] >= 0 and params['alphabet'] in ('na', 'aa') and
        params['nucleotide_padding'] == 'ACGT_at_variable_sites' and
        params['omnibus_continuity'] == 'r_default_2x2_min_delta' and
        params['pair_df_policy'] == 'standard_pair', 'statistics_parameters_invalid')
    shape(params['distribution_backend'], {'name', 'version'})
    require(params['distribution_backend']['name'] == 'scipy_chi2_integer_df_logtail_v1', 'distribution_backend_invalid')
    text(params['distribution_backend']['version'])
    _selected_pairs(params['selected_pairs'])
    seen, selectors, sites = set(), set(), {}
    for collection, kind in (('omnibus', 'omnibus'), ('pairs', 'pairwise')):
        require(type(value[collection]) is list, 'statistics_array_invalid')
        for row in value[collection]:
            shape(row, {'test_id', 'kind', 'category_id', 'column_0based', 'group_ids', 'raw_table_id',
                'raw_symbols', 'augmented_symbols', 'group_population_count', 'epsilon',
                'augmented_counts', 'expected_counts', 'augmented_total', 'continuity_delta',
                'chi_square', 'df', 'mathematical_p', 'log_p', 'numerical_state', 'method_id', 'requirements'})
            for key in ('test_id', 'raw_table_id', 'method_id'):
                text(row[key])
            require(row['test_id'].startswith('biological_group_test:') and
                    row['raw_table_id'].startswith('biological_group_counts:'), 'test_identity_kind_conflict')
            method = 'biological_group_' + kind + '_' + params['alphabet'] + '_standard_pair_v1'
            require(row['method_id'] == method, 'test_method_conflict')
            strings(row['group_ids'])
            identity_payload = {'raw_table_id': row['raw_table_id'], 'kind': kind,
                'groups': row['group_ids'], 'parameters': params}
            expected_id = 'biological_group_test:' + hashlib.sha256(json.dumps(identity_payload,
                sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest()
            require(row['test_id'] == expected_id, 'test_identity_parameters_conflict')
            require(row['test_id'] not in seen, 'duplicate_test_id'); seen.add(row['test_id'])
            require(row['kind'] == kind and row['category_id'] == value['category_id'], 'test_scope_conflict')
            integer(row['column_0based']); integer(row['group_population_count'], minimum=2)
            strings(row['group_ids']); strings(row['raw_symbols']); strings(row['augmented_symbols'])
            require(all(len(s) == 1 and s != '#' for s in row['augmented_symbols']) and
                    row['raw_symbols'] == sorted(row['raw_symbols']) and len(row['raw_symbols']) >= 2,
                    'symbol_population_conflict')
            augmented_symbols = list(row['raw_symbols'])
            if params['alphabet'] == 'na':
                augmented_symbols += [s for s in 'ACGT' if s not in augmented_symbols]
            require(row['augmented_symbols'] == augmented_symbols, 'augmented_symbols_conflict')
            r, k = len(augmented_symbols), len(row['group_ids'])
            require(k == row['group_population_count'] if kind == 'omnibus' else
                k == 2 and row['group_ids'] in params['selected_pairs'], 'test_group_conflict')
            selector = (row['column_0based'], kind, tuple(row['group_ids']) if kind == 'pairwise' else None)
            require(selector not in selectors, 'duplicate_test_selector'); selectors.add(selector)
            site = sites.setdefault(row['column_0based'], (row['raw_table_id'], row['raw_symbols'],
                row['augmented_symbols'], row['group_population_count']))
            require(site == (row['raw_table_id'], row['raw_symbols'], row['augmented_symbols'],
                row['group_population_count']), 'statistical_site_identity_conflict')
            matrix(row['augmented_counts'], r, k); matrix(row['expected_counts'], r, k)
            row_requirements = reports({'requirements': row['requirements'], 'diagnostics': []})
            require(row_requirements <= requirement_ids, 'test_requirement_unresolved')
            for key, unit in STATISTIC_UNITS.items():
                cell(row[key], population=row['test_id'], unit=unit, method=method, requirements=requirement_ids)
            require(row['epsilon']['value'] == params['epsilon'], 'epsilon_conflict')
            expected_df = (r - 1) * (k - 1)
            require(row['df']['value'] == expected_df and expected_df > 0, 'df_conflict')
            totals = [_sum(x) for x in row['augmented_counts']]
            total = _sum(totals)
            require(row['augmented_total']['value'] == total, 'augmented_total_conflict')
            for i in range(r):
                for j in range(k):
                    expect = (totals[i] / total) * _sum(x[j] for x in row['augmented_counts']) if total else 0.0
                    require(row['expected_counts'][i][j] == expect, 'expected_counts_conflict')
            delta = (min(.5, min(abs(row['augmented_counts'][i][j] - row['expected_counts'][i][j])
                         for i in range(2) for j in range(2))) if kind == 'omnibus' and r == k == 2 else 0.0)
            require(row['continuity_delta']['value'] == delta, 'continuity_delta_conflict')
            statistic = row['chi_square']['value']
            require(statistic is None or statistic >= 0, 'chi_square_invalid')
            state, p, logp = row['numerical_state'], row['mathematical_p']['value'], row['log_p']['value']
            require(state in ('finite', 'underflow', 'unavailable'), 'numerical_state_invalid')
            nondegenerate = all(x > 0 for xrow in row['expected_counts'] for x in xrow)
            require(nondegenerate or state == 'unavailable', 'degenerate_tail_conflict')
            if nondegenerate and statistic is not None:
                try:
                    terms = [((abs(observed - expect) - delta) / math.sqrt(expect)) ** 2
                             for observed_row, expected_row in zip(row['augmented_counts'], row['expected_counts'])
                             for observed, expect in zip(observed_row, expected_row)]
                except OverflowError as exc:
                    raise ValueError('bvbrc_biological_statistic_nonfinite') from exc
                require(statistic == _sum(terms), 'chi_square_matrix_conflict')
            if state == 'finite':
                require(statistic is not None and p is not None and 0 < p <= 1 and logp is not None and
                    math.isclose(logp, math.log(p), rel_tol=1e-12, abs_tol=1e-14), 'p_log_conflict')
            elif state == 'underflow':
                require(statistic is not None and p is None and row['mathematical_p']['state'] == 'failed'
                    and logp is not None and logp < 0, 'underflow_state_conflict')
            else:
                require(statistic is None and p is None and logp is None and row_requirements,
                        'unavailable_tail_conflict')
    require(type(value['exclusions']) is list, 'exclusions_invalid')
    for row in value['exclusions']:
        shape(row, {'column_0based', 'test_kind', 'group_pair', 'reason'})
        integer(row['column_0based'])
        require(row['test_kind'] in ('omnibus', 'pairwise') and row['reason'] in (
            'all_missing', 'conserved_placeholder', 'degenerate_df', 'unresolved'), 'exclusion_invalid')
        require(row['group_pair'] is None if row['test_kind'] == 'omnibus' else
                row['group_pair'] in params['selected_pairs'], 'exclusion_pair_conflict')
        selector = (row['column_0based'], row['test_kind'],
                    tuple(row['group_pair']) if row['group_pair'] is not None else None)
        require(selector not in selectors, 'duplicate_test_selector'); selectors.add(selector)
    columns = {selector[0] for selector in selectors}
    for column in columns:
        require((column, 'omnibus', None) in selectors and all(
            (column, 'pairwise', tuple(pair)) in selectors for pair in params['selected_pairs']),
            'site_test_enumeration_incomplete')
    omnibus = {row['column_0based']: row for row in value['omnibus']}
    for row in value['pairs']:
        parent = omnibus.get(row['column_0based'])
        require(parent is not None and set(row['group_ids']) <= set(parent['group_ids']), 'pair_omnibus_groups_conflict')
        positions = [parent['group_ids'].index(group) for group in row['group_ids']]
        require(row['augmented_counts'] == [[counts[j] for j in positions] for counts in parent['augmented_counts']],
                'pair_omnibus_counts_conflict')
    return deepcopy(value)


def adequacy(value, *, table_id, method, expected, requirements):
    shape(value, {'table_id', 'minimum_expected', 'cells_below_5', 'cells_below_1', 'cell_denominator'})
    require(value['table_id'] == table_id, 'adequacy_table_conflict')
    flat = [x for row in expected for x in row]
    answers = {'minimum_expected': min(flat) if flat else None, 'cells_below_5': sum(x < 5 for x in flat),
               'cells_below_1': sum(x < 1 for x in flat), 'cell_denominator': len(flat)}
    for key, answer in answers.items():
        cell(value[key], population=table_id, unit='expected_observations' if key == 'minimum_expected' else 'cells',
             method=method, requirements=requirements)
        require(value[key]['value'] is None or value[key]['value'] == answer, 'adequacy_value_conflict')


def validate_biological_effects(value: dict) -> dict:
    shape(value, {'status', 'analysis_id', 'category_id', 'zero_margin_policy', 'sites', 'requirements', 'diagnostics'})
    requirement_ids = _envelope(value)
    require(value['zero_margin_policy'] == 'drop_for_raw_effect_only', 'effect_policy_invalid')
    require(type(value['sites']) is list, 'sites_invalid')
    seen, columns = set(), set()
    method = 'biological_group_raw_descriptive_effect_v1'
    for row in value['sites']:
        shape(row, {'raw_table_id', 'column_0based', 'raw_chi_square', 'cramers_v',
            'effective_symbol_count', 'effective_group_count', 'raw_expected', 'raw_adequacy',
            'positive_observed_cells_below_5', 'pairs'})
        text(row['raw_table_id']); integer(row['column_0based'])
        require(row['raw_table_id'].startswith('biological_group_counts:'), 'effect_identity_kind_conflict')
        require(row['raw_table_id'] not in seen and row['column_0based'] not in columns, 'effect_table_duplicate')
        seen.add(row['raw_table_id']); columns.add(row['column_0based'])
        for key in ('effective_symbol_count', 'effective_group_count', 'positive_observed_cells_below_5'):
            integer(row[key])
        r, k = row['effective_symbol_count'], row['effective_group_count']
        matrix(row['raw_expected'], r, k)
        require(all(x > 0 for erow in row['raw_expected'] for x in erow), 'raw_zero_margin_not_dropped')
        for key, unit in (('raw_chi_square', 'chi_square'), ('cramers_v', 'fraction')):
            cell(row[key], population=row['raw_table_id'], unit=unit, method=method, requirements=requirement_ids)
        statistic, v = row['raw_chi_square']['value'], row['cramers_v']['value']
        require((statistic is None) == (v is None), 'effect_availability_conflict')
        if statistic is not None:
            require(r >= 2 and k >= 2 and statistic >= 0 and 0 <= v <= 1 + 1e-12, 'effect_range_conflict')
            denominator = row['cramers_v']['denominator']
            require(row['cramers_v']['numerator'] == statistic and denominator is not None and denominator > 0
                and math.isclose(v, math.sqrt(statistic / denominator), rel_tol=1e-12, abs_tol=1e-14),
                'cramers_v_relationship_conflict')
            require(math.isclose(denominator, _sum(_sum(x) for x in row['raw_expected']) * min(r-1, k-1),
                                 rel_tol=1e-12, abs_tol=1e-14), 'effect_denominator_conflict')
        else:
            require(requirement_ids, 'unavailable_effect_requirement_missing')
        adequacy(row['raw_adequacy'], table_id=row['raw_table_id'], method=method,
                 expected=row['raw_expected'], requirements=requirement_ids)
        require(type(row['pairs']) is list, 'pairs_invalid')
        pair_ids = set()
        for pair in row['pairs']:
            shape(pair, {'group_ids', 'frequency_deltas', 'total_variation'})
            strings(pair['group_ids']); require(len(pair['group_ids']) == 2, 'pair_invalid')
            require(tuple(pair['group_ids']) not in pair_ids, 'pair_duplicate'); pair_ids.add(tuple(pair['group_ids']))
            require(type(pair['frequency_deltas']) is list and len(pair['frequency_deltas']) == r, 'deltas_invalid')
            symbols, deltas = [], []
            for delta in pair['frequency_deltas']:
                shape(delta, {'symbol', 'value'}); text(delta['symbol'])
                require(len(delta['symbol']) == 1 and delta['symbol'] != '#', 'delta_symbol_invalid')
                symbols.append(delta['symbol'])
                cell(delta['value'], population=row['raw_table_id'], unit='signed_fraction', method=method,
                     requirements=requirement_ids)
                n = delta['value']['value']
                require(n is None or -1 <= n <= 1, 'delta_range_invalid'); deltas.append(n)
            require(symbols == sorted(set(symbols)), 'delta_symbols_invalid')
            cell(pair['total_variation'], population=row['raw_table_id'], unit='fraction', method=method,
                 requirements=requirement_ids)
            tv = pair['total_variation']['value']
            if tv is not None:
                require(all(n is not None for n in deltas) and 0 <= tv <= 1 + 1e-12, 'variation_range_invalid')
                require(math.isclose(tv, .5 * math.fsum(abs(n) for n in deltas), rel_tol=1e-12, abs_tol=1e-14)
                        and math.isclose(math.fsum(deltas), 0, abs_tol=1e-12), 'variation_delta_conflict')
            else:
                require(all(n is None for n in deltas) and requirement_ids, 'variation_availability_conflict')
    return deepcopy(value)


__all__ = ['validate_biological_group_population', 'validate_biological_assignments',
           'validate_biological_counts', 'validate_biological_statistics', 'validate_biological_effects']
