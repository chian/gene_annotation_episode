"""Explicit biological group counts, standard statistics and raw effects.

All operands are supplied data. Native R-order/df/zero-tail quirks remain in
the separate native reproduction functions. These calculations do not assign
annotation credit, acquire records, launch work or select a resource.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math

from . import bvbrc_metacats_biological_contracts as c
from . import phylogeny_calculation_contracts as shared
from .phylogeny_format_contracts import validate_alignment_document
from .bvbrc_alignment_values import numeric_cell, requirement, diagnostic
from .bvbrc_contingency_math import (count_alignment_group_sites,
    expected_contingency_counts, pearson_contingency_statistic)
from .bvbrc_metacats_calculators import chi_square_tail


def _id(kind, payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True, allow_nan=False).encode()
    return kind + ':' + hashlib.sha256(encoded).hexdigest()


def _cell(value, population, method, unit, *, state='missing', numerator=None,
          denominator=None, evidence=(), requirements=()):
    return numeric_cell(value, state='available' if value is not None else state,
        unit=unit, origin='calculated', population_id=population, method_id=method,
        numerator=numerator, denominator=denominator, evidence=evidence,
        requirement_ids=requirements)


def _requirement(scope, reason):
    return requirement(scope + '/' + reason, kind='scientific_metadata',
                       role='biological_group_population', reason_code=reason)


def _pairs(selected_pairs, groups):
    c.require(type(selected_pairs) in (tuple, list), 'pairs_invalid')
    known = {g['group_id']: i for i, g in enumerate(groups)}
    result, seen = [], set()
    for pair in selected_pairs:
        c.require(type(pair) in (tuple, list) and len(pair) == 2, 'pair_invalid')
        a, b = pair
        c.text(a); c.text(b)
        c.require(a != b and a in known and b in known, 'pair_group_invalid')
        c.require((a, b) not in seen, 'pair_duplicate'); seen.add((a, b))
        result.append((a, b, known[a], known[b]))
    return result


def _finish(result, validator):
    result['requirements'] = list({r['requirement_id']: r for r in result['requirements']}.values())
    if result['requirements']:
        result['status'] = 'partial'
    return validator(result)


def biological_group_counts(alignment: dict, *, analysis_id: str, population: dict,
        category_id: str, assignments: tuple[dict, ...], group_population: dict,
        case_policy: str, terminal_gap_policy: str, original_hash_policy: str) -> dict:
    """Count literal symbols using explicit physical row/group membership.

The supplied group list defines column order, including groups without observed
rows. Original member identity may remain unknown without erasing a resolved
physical-row association. Input assignment order cannot change table identity.
"""
    alignment = c._shared(validate_alignment_document, alignment)
    c._shared(shared.alignment_population, population, alignment)
    c.text(analysis_id); c.text(category_id)
    group_population = c.validate_biological_group_population(group_population, category_id=category_id)
    assignments = c.validate_biological_assignments(assignments, alignment=alignment,
        category_id=category_id, group_population=group_population)
    c.require(case_policy in ('preserve', 'uppercase') and
        terminal_gap_policy == 'exclude_terminal_dash' and original_hash_policy == 'exclude_hash',
        'count_parameters_invalid')
    groups = {group['group_id']: i for i, group in enumerate(group_population['groups'])}
    mapping = {row['row_index']: row for row in assignments}
    row_groups = []
    for i in population['row_indices']:
        row = mapping.get(i)
        row_groups.append({'row_index': i, 'group_index': groups[row['group_id']]
                           if row is not None and row['state'] == 'resolved' else None})
    counted = count_alignment_group_sites(alignment, population=population,
        row_groups=tuple(row_groups), group_count=len(groups),
        groups_complete=group_population['completeness'] == 'complete',
        case_policy=case_policy, terminal_gap_policy=terminal_gap_policy,
        original_hash_policy=original_hash_policy)
    params = {'case_policy': case_policy, 'terminal_gap_policy': terminal_gap_policy,
              'original_hash_policy': original_hash_policy}
    result = {'status': 'ok', 'analysis_id': analysis_id, 'population_id': population['population_id'],
        'alignment_id': alignment['alignment_id'], 'category_id': category_id,
        'group_population': group_population, 'method_parameters': params, 'sites': [],
        'requirements': [], 'diagnostics': []}
    selected = set(population['row_indices'])
    for row in sorted(assignments, key=lambda assignment: assignment['row_index']):
        if row['row_index'] in selected and row['state'] == 'resolved' and row['member_key'] is None:
            result['diagnostics'].append(diagnostic('biological_group_original_member_identity_unknown',
                path='/rows/' + str(row['row_index']) + '/member_key',
                evidence_refs=list(dict.fromkeys(e['content']['source_ref'] for e in row['evidence']))))
    for site in counted:
        tid = _id('biological_group_counts', {'analysis_id': analysis_id, 'population': population,
            'alignment_id': alignment['alignment_id'], 'artifact': alignment['artifact'],
            'category_id': category_id, 'group_population': group_population,
            'column': site['column_0based'], 'parameters': params,
            'assignments': sorted(assignments, key=lambda row: row['row_index'])})
        if site['state'] == 'unresolved':
            result['requirements'].append(_requirement(tid, 'complete_group_population_required'))
        result['sites'].append({'table_id': tid, **site, 'evidence': deepcopy(population['evidence'])})
    if not counted and (alignment['completeness'] != 'complete' or population['completeness'] != 'complete'
                       or group_population['completeness'] != 'complete'):
        result['requirements'].append(_requirement(population['population_id'], 'complete_group_population_required'))
    return _finish(result, c.validate_biological_counts)


def biological_group_statistics(counts: dict, *, alphabet: str, epsilon: float,
        nucleotide_padding: str, omnibus_continuity: str, pair_df_policy: str,
        selected_pairs: tuple[tuple[str, str], ...], distribution_backend: dict) -> dict:
    """Pearson tests with explicit augmentation and standard two-group df.

The retained category symbol rows also occur in each selected pair. Nucleotide
padding applies at variable sites only. Mathematical underflow retains a finite
log tail; it never becomes the native program's zero-to-one pair value.
"""
    counts = c.validate_biological_counts(counts)
    c.finite(epsilon)
    c.require(epsilon >= 0 and alphabet in ('na', 'aa') and
        nucleotide_padding == 'ACGT_at_variable_sites' and
        omnibus_continuity == 'r_default_2x2_min_delta' and pair_df_policy == 'standard_pair',
        'statistics_parameters_invalid')
    c._shared(chi_square_tail, 0, 1, distribution_backend=distribution_backend)
    groups = counts['group_population']['groups']
    pairs = _pairs(selected_pairs, groups)
    params = {'alphabet': alphabet, 'epsilon': epsilon, 'nucleotide_padding': nucleotide_padding,
        'omnibus_continuity': omnibus_continuity, 'pair_df_policy': pair_df_policy,
        'selected_pairs': [list(p[:2]) for p in pairs], 'distribution_backend': deepcopy(distribution_backend)}
    result = {'status': 'ok', 'analysis_id': counts['analysis_id'], 'category_id': counts['category_id'],
        'method_parameters': params, 'omnibus': [], 'pairs': [], 'exclusions': [],
        'requirements': deepcopy(counts['requirements']), 'diagnostics': deepcopy(counts['diagnostics'])}
    k = len(groups)
    for site in counts['sites']:
        tests = [('omnibus', [g['group_id'] for g in groups], list(range(k)))]
        tests += [('pairwise', [a, b], [i, j]) for a, b, i, j in pairs]
        symbols, raw = list(site['symbols']), deepcopy(site['observed_counts'])
        if alphabet == 'na' and site['state'] == 'variable':
            for symbol in 'ACGT':
                if symbol not in symbols:
                    symbols.append(symbol); raw.append([0] * k)
        augmented = [[n + epsilon for n in row] for row in raw]
        for kind, ids, indices in tests:
            reason = ('unresolved' if site['state'] == 'unresolved' else 'all_missing' if site['state'] == 'all_missing'
                      else 'conserved_placeholder' if site['state'] == 'conserved' else None)
            df = (len(symbols) - 1) * (len(indices) - 1)
            if reason is None and (df <= 0 or len(indices) < 2):
                reason = 'degenerate_df'
            if reason:
                result['exclusions'].append({'column_0based': site['column_0based'], 'test_kind': kind,
                    'group_pair': ids if kind == 'pairwise' else None, 'reason': reason})
                if reason in ('unresolved', 'degenerate_df'):
                    result['requirements'].append(_requirement(site['table_id'], 'complete_positive_df_table_required'))
                continue
            matrix = [[row[j] for j in indices] for row in augmented]
            expected_result = expected_contingency_counts(matrix)
            expected, total = expected_result['expected_counts'], expected_result['total']
            delta = (min(.5, min(abs(matrix[i][j] - expected[i][j]) for i in range(2) for j in range(2)))
                     if kind == 'omnibus' and len(matrix) == len(indices) == 2 else 0.0)
            statistic = pearson_contingency_statistic(matrix, expected=expected, continuity_delta=delta)
            method = 'biological_group_' + kind + '_' + alphabet + '_standard_pair_v1'
            tid = _id('biological_group_test', {'raw_table_id': site['table_id'], 'kind': kind,
                'groups': ids, 'parameters': params})
            requirements = []
            if statistic is None:
                requirements.append(_requirement(tid, 'nondegenerate_expected_counts_required'))
                tail = {'p': None, 'log_p': None, 'numerical_state': 'unavailable'}
            else:
                tail = c._shared(chi_square_tail, statistic, df, distribution_backend=distribution_backend)
            if tail['numerical_state'] == 'underflow':
                result['diagnostics'].append(diagnostic('biological_group_calculated_p_underflow',
                                                       path='/sites/' + str(site['column_0based'])))
            def cell(value, unit, **extra):
                return _cell(value, tid, method, unit, evidence=site['evidence'],
                    requirements=[r['requirement_id'] for r in requirements], **extra)
            result['omnibus' if kind == 'omnibus' else 'pairs'].append({
                'test_id': tid, 'kind': kind, 'category_id': counts['category_id'],
                'column_0based': site['column_0based'], 'group_ids': ids, 'raw_table_id': site['table_id'],
                'raw_symbols': list(site['symbols']), 'augmented_symbols': symbols,
                'group_population_count': k, 'epsilon': cell(epsilon, 'pseudocount_per_cell'),
                'augmented_counts': matrix, 'expected_counts': expected,
                'augmented_total': cell(total, 'augmented_observations'),
                'continuity_delta': cell(delta, 'augmented_observations'),
                'chi_square': cell(statistic, 'chi_square'), 'df': cell(df, 'degrees_of_freedom'),
                'mathematical_p': cell(tail['p'], 'probability',
                    state='failed' if tail['numerical_state'] == 'underflow' else 'missing'),
                'log_p': cell(tail['log_p'], 'natural_log_probability'),
                'numerical_state': tail['numerical_state'], 'method_id': method, 'requirements': requirements})
            result['requirements'].extend(requirements)
    return _finish(result, c.validate_biological_statistics)


def biological_group_effects(counts: dict, *, selected_pairs: tuple[tuple[str, str], ...],
                             zero_margin_policy: str) -> dict:
    """Raw Pearson/V and signed frequencies, with no pseudocount or Yates delta."""
    counts = c.validate_biological_counts(counts)
    c.require(zero_margin_policy == 'drop_for_raw_effect_only', 'effect_policy_invalid')
    pairs = _pairs(selected_pairs, counts['group_population']['groups'])
    result = {'status': 'ok', 'analysis_id': counts['analysis_id'], 'category_id': counts['category_id'],
        'zero_margin_policy': zero_margin_policy, 'sites': [],
        'requirements': deepcopy(counts['requirements']), 'diagnostics': deepcopy(counts['diagnostics'])}
    for site in counts['sites']:
        matrix, symbols, tid = site['observed_counts'], site['symbols'], site['table_id']
        ncols = len(counts['group_population']['groups'])
        totals = [sum(row[j] for row in matrix) for j in range(ncols)]
        included = [j for j, total in enumerate(totals) if total > 0]
        reduced = [[row[j] for j in included] for row in matrix if sum(row) > 0]
        expected_result = expected_contingency_counts(reduced)
        expected, total = expected_result['expected_counts'], expected_result['total']
        r, k = len(reduced), len(included)
        method = 'biological_group_raw_descriptive_effect_v1'
        known = site['state'] != 'unresolved'
        statistic = (pearson_contingency_statistic(reduced, expected=expected, continuity_delta=0)
                     if known and r >= 2 and k >= 2 else None)
        denominator = total * min(r - 1, k - 1) if r and k else 0
        effect = math.sqrt(statistic / denominator) if statistic is not None and denominator > 0 else None
        requirements = []
        if statistic is None:
            requirements.append(_requirement(tid, 'nondegenerate_raw_effect_required'))
        def cell(value, unit, **extra):
            return _cell(value if known else None, tid, method, unit, evidence=site['evidence'],
                         requirements=[row['requirement_id'] for row in requirements], **extra)
        pair_rows = []
        for a, b, i, j in pairs:
            deltas = [row[i] / totals[i] - row[j] / totals[j] for row in matrix] if totals[i] and totals[j] and known else None
            if deltas is None:
                requirements.append(_requirement(_id('biological_group_pair', {'table': tid, 'groups': [a, b]}),
                                                 'nonempty_resolved_pair_margins_required'))
            pair_rows.append({'group_ids': [a, b], 'frequency_deltas': [
                {'symbol': s, 'value': cell(deltas[n] if deltas is not None else None, 'signed_fraction')}
                for n, s in enumerate(symbols)], 'total_variation': cell(
                    .5 * math.fsum(abs(x) for x in deltas) if deltas is not None else None, 'fraction')})
        flat = [x for row in expected for x in row]
        adequacy = {'table_id': tid,
            'minimum_expected': cell(min(flat) if flat else None, 'expected_observations'),
            'cells_below_5': cell(sum(x < 5 for x in flat), 'cells'),
            'cells_below_1': cell(sum(x < 1 for x in flat), 'cells'),
            'cell_denominator': cell(len(flat), 'cells')}
        result['sites'].append({'raw_table_id': tid, 'column_0based': site['column_0based'],
            'raw_chi_square': cell(statistic, 'chi_square'),
            'cramers_v': cell(effect, 'fraction', numerator=statistic, denominator=denominator),
            'effective_symbol_count': r, 'effective_group_count': k, 'raw_expected': expected,
            'raw_adequacy': adequacy, 'positive_observed_cells_below_5': sum(0 < x < 5 for row in matrix for x in row),
            'pairs': pair_rows})
        result['requirements'].extend(requirements)
    return _finish(result, c.validate_biological_effects)


__all__ = ['biological_group_counts', 'biological_group_statistics', 'biological_group_effects']
