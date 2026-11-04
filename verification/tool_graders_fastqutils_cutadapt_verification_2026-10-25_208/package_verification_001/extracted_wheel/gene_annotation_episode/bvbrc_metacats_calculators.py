"""MetaCATS arithmetic from saved counts, never from an acquired service result.

Native observations remain in their native tables. These explicit calculations
preserve pseudocounts, contingency populations, native-source df and alternative
df separately. No result here is an annotation probability or execution choice.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math

import scipy
from scipy.special import log_ndtr
from scipy.stats import chi2

from . import phylogeny_calculation_contracts as shared
from .phylogeny_format_contracts import validate_alignment_document
from . import bvbrc_metacats_calculation_contracts as c
from .bvbrc_alignment_values import numeric_cell, diagnostic, requirement
from .bvbrc_contingency_math import (count_alignment_group_sites,
    expected_contingency_counts, pearson_contingency_statistic)


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
                       role='metacats_population', reason_code=reason)


def _pairs(selected_pairs, groups):
    c.require(type(selected_pairs) in (tuple, list), 'pairs_invalid')
    known = {g['group_id']: j for j, g in enumerate(groups) if g['group_id'] is not None}
    result, seen = [], set()
    for pair in selected_pairs:
        c.require(type(pair) in (tuple, list) and len(pair) == 2, 'pair_invalid')
        a, b = pair
        c.text(a); c.text(b)
        c.require(a != b and a in known and b in known, 'pair_group_invalid')
        c.require((a, b) not in seen, 'pair_duplicate')
        seen.add((a, b))
        result.append((a, b, known[a], known[b]))
    return result


def metacats_group_counts(alignment: dict, *, analysis_id: str, population: dict,
                         assignments: tuple[dict, ...], category_id: str,
                         group_order: tuple[dict, ...], case_policy: str,
                         terminal_mask: str, native_input_hash_policy: str) -> dict:
    alignment = validate_alignment_document(alignment)
    shared.alignment_population(population, alignment)
    c.text(analysis_id); c.text(category_id)
    groups = c.validate_group_order(group_order, category_id=category_id)
    c.require(case_policy in ('preserve', 'uppercase') and
              terminal_mask == 'native_terminal_dash_to_hash' and
              native_input_hash_policy == 'exclude_hash', 'count_parameters_invalid')
    c.require(type(assignments) in (list, tuple), 'assignments_invalid')
    mapped = {}
    for assignment in assignments:
        c.shape(assignment, {'category_id', 'alignment_id', 'row_index', 'member_key',
            'metadata_row_index', 'metadata_column_index', 'raw_group_value',
            'native_group_ordinal', 'displayed_group_label', 'state', 'evidence'})
        c.require(assignment['category_id'] == category_id and
                  assignment['alignment_id'] == alignment['alignment_id'], 'assignment_scope_conflict')
        c.integer(assignment['row_index'])
        c.require(assignment['row_index'] < len(alignment['rows']), 'assignment_row_outside_alignment')
        c.require(assignment['row_index'] not in mapped, 'duplicate_row_assignment')
        c.integer(assignment['metadata_row_index'], nullable=True)
        c.integer(assignment['metadata_column_index'], nullable=True)
        c.integer(assignment['native_group_ordinal'], minimum=1, nullable=True)
        for key in ('raw_group_value', 'displayed_group_label'):
            c.require(assignment[key] is None or type(assignment[key]) is str, 'assignment_label_invalid')
        c.require(assignment['state'] in ('resolved', 'missing', 'conflicting', 'native_unlabeled'), 'assignment_state_invalid')
        if assignment['member_key'] is not None:
            c.shape(assignment['member_key'], {'input_binding_id', 'member_id', 'occurrence_index'})
            c.text(assignment['member_key']['input_binding_id']); c.text(assignment['member_key']['member_id'])
            c.integer(assignment['member_key']['occurrence_index'])
        shared.evidence(assignment['evidence'])
        mapped[assignment['row_index']] = assignment
    ordinals = {g['native_group_ordinal']: j for j, g in enumerate(groups)
                if g['state'] != 'unresolved'}
    row_groups = []
    for i in population['row_indices']:
        assignment = mapped.get(i)
        group = (ordinals.get(assignment['native_group_ordinal']) if assignment is not None
                 and assignment['state'] == 'resolved' and assignment['member_key'] is not None else None)
        row_groups.append({'row_index': i, 'group_index': group})
    counted = count_alignment_group_sites(alignment, population=population,
        row_groups=tuple(row_groups), group_count=len(groups),
        groups_complete=all(g['state'] != 'unresolved' for g in groups),
        case_policy=case_policy, terminal_gap_policy='exclude_terminal_dash',
        original_hash_policy=native_input_hash_policy)
    params = {'case_policy': case_policy, 'terminal_mask': terminal_mask,
              'native_input_hash_policy': native_input_hash_policy}
    sites, requirements = [], []
    for site in counted:
        column = site['column_0based']
        # Future calculations have a new identity incorporating the complete
        # validated membership records. Saved v1 counts are never migrated.
        table_id = _id('metacats_counts_v2', {'analysis_id': analysis_id, 'population': population,
            'alignment_id': alignment['alignment_id'], 'artifact': alignment['artifact'], 'category_id': category_id,
            'group_order': groups, 'column': column, 'parameters': params,
            'assignments': [mapped[i] for i in sorted(mapped)]})
        if site['state'] == 'unresolved':
            requirements.append(_requirement(table_id, 'complete_group_population_required'))
        sites.append({'table_id': table_id, **site,
            'evidence': deepcopy(population['evidence'])})
    return c.validate_group_counts({'status': 'partial' if requirements else 'ok',
        'analysis_id': analysis_id, 'population_id': population['population_id'],
        'alignment_id': alignment['alignment_id'], 'category_id': category_id,
        'group_order': groups, 'method_parameters': params, 'sites': sites,
        'requirements': requirements, 'diagnostics': []})


def _expected(matrix):
    result = expected_contingency_counts(matrix)
    return result['expected_counts'], result['total']


def _chi_square(matrix, expected, delta=0.0):
    return pearson_contingency_statistic(matrix, expected=expected, continuity_delta=delta)


def chi_square_tail(statistic: float, df: int, *, distribution_backend: dict) -> dict:
    """Ordinary chi-square upper tail plus a finite log tail on binary underflow."""
    c.shape(distribution_backend, {'name', 'version'})
    c.require(distribution_backend == {'name': 'scipy_chi2_integer_df_logtail_v1',
        'version': scipy.__version__}, 'distribution_backend_unavailable')
    c.finite(statistic); c.integer(df, minimum=1)
    c.require(statistic >= 0, 'negative_chi_square')
    p = float(chi2.sf(statistic, df))
    if p > 0:
        return {'p': p, 'log_p': math.log(p), 'numerical_state': 'finite'}
    z = statistic / 2
    if df % 2 == 0:
        a, log_q = 1.0, -z
    else:
        a, log_q = 0.5, math.log(2) + float(log_ndtr(-math.sqrt(statistic)))
    target = df / 2
    while a < target:
        term = a * math.log(z) - z - math.lgamma(a + 1)
        greater, lesser = max(log_q, term), min(log_q, term)
        log_q = greater + math.log1p(math.exp(lesser - greater))
        a += 1
    c.require(math.isfinite(log_q), 'log_tail_nonfinite')
    return {'p': None, 'log_p': log_q, 'numerical_state': 'underflow'}


def metacats_statistics(counts: dict, *, alphabet: str, epsilon: float,
                       nucleotide_padding: str, omnibus_continuity: str,
                       pair_df_policy: str, pair_zero_policy: str,
                       selected_pairs: tuple[tuple[str, str], ...],
                       distribution_backend: dict) -> dict:
    counts = c.validate_group_counts(counts)
    c.require(alphabet in ('na', 'aa'), 'alphabet_invalid')
    c.finite(epsilon); c.require(epsilon >= 0, 'epsilon_negative')
    c.require(nucleotide_padding == 'ACGT_at_variable_sites' and
        omnibus_continuity == 'r_default_2x2_min_delta' and
        pair_df_policy in ('native_source', 'standard_pair') and
        pair_zero_policy == 'retain_math_and_native_zero_to_one', 'statistics_parameters_invalid')
    chi_square_tail(0, 1, distribution_backend=distribution_backend)
    groups = counts['group_order']
    pairs = _pairs(selected_pairs, groups)
    params = {'alphabet': alphabet, 'epsilon': epsilon, 'nucleotide_padding': nucleotide_padding,
        'omnibus_continuity': omnibus_continuity, 'pair_df_policy': pair_df_policy,
        'pair_zero_policy': pair_zero_policy, 'selected_pairs': [list(p[:2]) for p in pairs],
        'distribution_backend': deepcopy(distribution_backend)}
    result = {'status': 'ok', 'analysis_id': counts['analysis_id'], 'category_id': counts['category_id'],
        'method_parameters': params, 'omnibus': [], 'pairs': [], 'exclusions': [],
        'requirements': deepcopy(counts['requirements']), 'diagnostics': []}
    for site in counts['sites']:
        k = len(groups)
        tests = [('omnibus', [g['group_id'] for g in groups], list(range(k)))]
        tests += [('pairwise', [a, b], [i, j]) for a, b, i, j in pairs]
        symbols = list(site['symbols'])
        raw = deepcopy(site['observed_counts'])
        if alphabet == 'na' and site['state'] == 'variable':
            for symbol in 'ACGT':
                if symbol not in symbols:
                    symbols.append(symbol); raw.append([0] * k)
        augmented = [[n + epsilon for n in row] for row in raw]
        for kind, ids, indices in tests:
            reason = ('unresolved' if site['state'] == 'unresolved' else 'all_missing' if site['state'] == 'all_missing'
                      else 'conserved_placeholder' if site['state'] == 'conserved' else None)
            df = ((len(symbols) - 1) * (k - 1) if kind == 'omnibus' or
                  alphabet == 'aa' and pair_df_policy == 'native_source' else len(symbols) - 1)
            if reason is None and (df <= 0 or len(indices) < 2):
                reason = 'degenerate_df'
            if reason:
                result['exclusions'].append({'column_0based': site['column_0based'], 'test_kind': kind,
                    'group_pair': ids if kind == 'pairwise' else None, 'reason': reason})
                if reason in ('unresolved', 'degenerate_df'):
                    result['requirements'].append(_requirement(site['table_id'], 'complete_positive_df_table_required'))
                continue
            matrix = [[row[j] for j in indices] for row in augmented]
            expected, total = _expected(matrix)
            delta = (min(0.5, min(abs(matrix[i][j] - expected[i][j]) for i in range(2) for j in range(2)))
                     if kind == 'omnibus' and len(matrix) == len(indices) == 2 else 0.0)
            statistic = _chi_square(matrix, expected, delta)
            method = 'metacats_' + kind + '_' + alphabet + '_' + pair_df_policy + '_v1'
            tid = _id('metacats_test', {'raw_table_id': site['table_id'], 'kind': kind,
                'groups': ids, 'parameters': params})
            requirements = []
            if statistic is None or not math.isfinite(statistic):
                requirements.append(_requirement(tid, 'nondegenerate_expected_counts_required'))
                tail = {'p': None, 'log_p': None, 'numerical_state': 'unavailable'}
                statistic = None
            else:
                tail = chi_square_tail(statistic, df, distribution_backend=distribution_backend)
            if tail['numerical_state'] == 'underflow':
                result['diagnostics'].append(diagnostic('metacats_calculated_p_underflow', path='/sites/' + str(site['column_0based'])))
            kwargs = {'evidence': site['evidence'], 'requirements': [r['requirement_id'] for r in requirements]}
            def cell(value, unit, **extra):
                return _cell(value, tid, method, unit, **kwargs, **extra)
            native_rule = (1.0 if tail['numerical_state'] == 'underflow' else tail['p']) if kind == 'pairwise' else None
            result['omnibus' if kind == 'omnibus' else 'pairs'].append({
                'test_id': tid, 'kind': kind, 'category_id': counts['category_id'],
                'column_0based': site['column_0based'], 'group_ids': ids, 'raw_table_id': site['table_id'],
                'raw_symbols': list(site['symbols']), 'augmented_symbols': symbols,
                'r_table_group_count': k, 'epsilon': cell(epsilon, 'pseudocount_per_cell'),
                'augmented_counts': matrix, 'expected_counts': expected,
                'augmented_total': cell(total, 'augmented_observations'),
                'continuity_delta': cell(delta, 'augmented_observations'),
                'chi_square': cell(statistic, 'chi_square'), 'df': cell(df, 'degrees_of_freedom'),
                'mathematical_p': cell(tail['p'], 'probability',
                    state='failed' if tail['numerical_state'] == 'underflow' else 'missing'),
                'log_p': cell(tail['log_p'], 'natural_log_probability'),
                'native_zero_rule_p': cell(native_rule, 'probability',
                    state='not_measured' if kind == 'omnibus' else 'missing'),
                'numerical_state': tail['numerical_state'], 'method_id': method,
                'native_observation_ids': [], 'requirements': requirements})
            result['requirements'].extend(requirements)
    result['requirements'] = list({r['requirement_id']: r for r in result['requirements']}.values())
    if result['requirements']:
        result['status'] = 'partial'
    return c.validate_statistics(result)


def _adequacy(expected, table_id, method, evidence):
    flat = [x for row in expected for x in row]
    return {'table_id': table_id,
        'minimum_expected': _cell(min(flat) if flat else None, table_id, method, 'expected_observations', evidence=evidence),
        'cells_below_5': _cell(sum(x < 5 for x in flat), table_id, method, 'cells', evidence=evidence),
        'cells_below_1': _cell(sum(x < 1 for x in flat), table_id, method, 'cells', evidence=evidence),
        'cell_denominator': _cell(len(flat), table_id, method, 'cells', evidence=evidence)}


def metacats_effects(counts: dict, *, selected_pairs: tuple[tuple[str, str], ...],
                    zero_margin_policy: str) -> dict:
    counts = c.validate_group_counts(counts)
    c.require(zero_margin_policy == 'drop_for_raw_effect_only', 'effect_policy_invalid')
    pairs = _pairs(selected_pairs, counts['group_order'])
    result = {'status': 'ok', 'analysis_id': counts['analysis_id'], 'category_id': counts['category_id'],
        'zero_margin_policy': zero_margin_policy, 'sites': [], 'requirements': deepcopy(counts['requirements']), 'diagnostics': []}
    for site in counts['sites']:
        matrix, symbols, tid = site['observed_counts'], site['symbols'], site['table_id']
        ncols = len(counts['group_order'])
        totals = [sum(row[j] for row in matrix) for j in range(ncols)]
        included = [j for j, total in enumerate(totals) if total > 0]
        reduced = [[row[j] for j in included] for row in matrix if sum(row) > 0]
        expected, total = _expected(reduced)
        r, k = len(reduced), len(included)
        method = 'metacats_raw_descriptive_effect_v1'
        known = site['state'] != 'unresolved'
        statistic = _chi_square(reduced, expected) if known and r >= 2 and k >= 2 else None
        denominator = total * min(r - 1, k - 1) if r and k else 0
        effect = math.sqrt(statistic / denominator) if statistic is not None and denominator > 0 else None
        def cell(value, unit, **kwargs):
            return _cell(value if known else None, tid, method, unit, evidence=site['evidence'], **kwargs)
        pair_rows = []
        for a, b, i, j in pairs:
            deltas = [row[i] / totals[i] - row[j] / totals[j] for row in matrix] if totals[i] and totals[j] and known else None
            pair_rows.append({'group_ids': [a, b], 'frequency_deltas': [
                {'symbol': s, 'value': cell(deltas[n] if deltas is not None else None, 'signed_fraction')}
                for n, s in enumerate(symbols)], 'total_variation': cell(
                    0.5 * math.fsum(abs(x) for x in deltas) if deltas is not None else None, 'fraction')})
        sparse = sum(0 < x < 5 for row in matrix for x in row)
        if statistic is None:
            result['requirements'].append(_requirement(tid, 'nondegenerate_raw_effect_required'))
        # Adequacy belongs to the exact reduced raw table, not a pseudocount fit.
        adequacy = _adequacy(expected, tid, method, site['evidence'])
        if not known:
            for key in ('minimum_expected', 'cells_below_5', 'cells_below_1', 'cell_denominator'):
                adequacy[key] = cell(None, adequacy[key]['unit'])
        result['sites'].append({'raw_table_id': tid, 'column_0based': site['column_0based'],
            'raw_chi_square': cell(statistic, 'chi_square'),
            'cramers_v': cell(effect, 'fraction', numerator=statistic, denominator=denominator),
            'effective_symbol_count': r, 'effective_group_count': k, 'raw_expected': expected,
            'augmented_adequacy': None, 'raw_adequacy': adequacy,
            'positive_observed_cells_below_5': sparse,
            'native_fewer_5_recalculated': ('Y' if sparse else 'N') if known else None,
            'pairs': pair_rows})
    result['requirements'] = list({r['requirement_id']: r for r in result['requirements']}.values())
    if result['requirements']:
        result['status'] = 'partial'
    return c.validate_effects(result)


def adjust_p_values(p_values: tuple[dict, ...], *, family: dict, method: str,
                    alpha: float, dependence_assumption: str) -> dict:
    """Adjust only an explicitly supplied testing family, preserving its order."""
    family = c.validate_test_family(family)
    rows = c.validate_test_p_values(p_values)
    c.require(method in ('none', 'bonferroni', 'holm', 'bh', 'by'), 'adjustment_method_invalid')
    c.finite(alpha); c.require(0 <= alpha <= 1, 'alpha_invalid')
    c.require(dependence_assumption in ('none_required_between_tests',
        'independent_or_positive_regression_dependence_assumed'), 'dependence_assumption_invalid')
    ids = [row['test_id'] for row in rows]
    c.require(set(ids) <= set(family['test_ids']), 'test_outside_family')
    valid = [row for row in rows if row['value']['state'] == 'available']
    complete = (family['population_state'] == 'complete' and set(ids) == set(family['test_ids'])
                and len(valid) == len(rows))
    n = family['total_test_count']
    assumed_count = (family['population_state'] == 'known_count_only' and family['assumption'] is not None
        and family['assumption']['kind'] == 'independently_known_count'
        or family['population_state'] == 'declared_upper_bound' and family['assumption'] is not None
        and family['assumption']['kind'] == 'parent_declared_upper_bound')
    if n is not None:
        c.require(n >= len(family['test_ids']) and n >= len(rows), 'family_count_too_small')
    usable = method == 'none' or complete or method == 'bonferroni' and assumed_count
    reasons = []
    if not usable:
        reasons.append(_requirement(family['family_id'], 'complete_test_population_required'))
    if method == 'bh' and dependence_assumption != 'independent_or_positive_regression_dependence_assumed':
        usable = False
        reasons.append(_requirement(family['family_id'], 'dependence_assumption_required'))
    ordered = sorted(valid, key=lambda row: (row['value']['value'], row['test_id']))
    calculated = {}
    harmonic = math.fsum(1 / i for i in range(1, n + 1)) if method == 'by' and complete else None
    if usable:
        if method == 'none':
            calculated = {row['test_id']: row['value']['value'] for row in ordered}
        elif method == 'bonferroni':
            calculated = {row['test_id']: min(1.0, n * row['value']['value']) for row in ordered}
        elif method == 'holm':
            previous = 0.0
            for i, row in enumerate(ordered):
                previous = max(previous, min(1.0, (n - i) * row['value']['value']))
                calculated[row['test_id']] = previous
        else:
            following = 1.0
            for i in range(len(ordered) - 1, -1, -1):
                row = ordered[i]
                following = min(following, (harmonic if method == 'by' else 1) * n * row['value']['value'] / (i + 1))
                calculated[row['test_id']] = following
    results = []
    for row in rows:
        p = calculated.get(row['test_id'])
        results.append({'test_id': row['test_id'], 'input_p': deepcopy(row['value']),
            'adjusted_p': _cell(p, family['family_id'], 'metacats_' + method + '_v1', 'probability',
                evidence=family['evidence'], requirements=[r['requirement_id'] for r in reasons]),
            'rejected_at_alpha': p <= alpha if p is not None else None})
    return c.validate_multiplicity({'status': 'partial' if reasons or len(valid) != len(rows) else 'ok', 'family': family,
        'method': method, 'alpha': alpha, 'dependence_assumption': dependence_assumption,
        'observed_p_count': len(valid), 'total_test_count': n, 'harmonic_factor': harmonic,
        'results': results, 'requirements': reasons, 'diagnostics': []})
