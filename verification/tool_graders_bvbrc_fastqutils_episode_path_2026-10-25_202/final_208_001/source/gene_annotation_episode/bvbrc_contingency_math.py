"""Pure arithmetic shared by biological groups and native MetaCATS replay.

Group identity and source ordering belong to the callers. These kernels accept
only explicit physical row/group indices and supplied matrices. They neither
infer memberships nor acquire data, and never create a native GroupColumn.
"""
from __future__ import annotations

from collections import Counter
import math

from . import phylogeny_calculation_contracts as shared
from .phylogeny_format_contracts import validate_alignment_document


def _require(condition, code):
    if not condition:
        raise ValueError('bvbrc_contingency_' + code)


def _matrix(value):
    _require(type(value) in (tuple, list), 'matrix_invalid')
    columns = None
    for row in value:
        _require(type(row) in (tuple, list), 'matrix_row_invalid')
        if columns is None:
            columns = len(row)
        _require(len(row) == columns, 'matrix_not_rectangular')
        for number in row:
            _require(type(number) in (int, float), 'number_invalid')
            try:
                finite = math.isfinite(number)
            except OverflowError:
                finite = False
            _require(finite and number >= 0, 'nonnegative_finite_count_required')


def count_alignment_group_sites(alignment: dict, *, population: dict,
        row_groups: tuple[dict, ...], group_count: int, groups_complete: bool,
        case_policy: str, terminal_gap_policy: str, original_hash_policy: str) -> list[dict]:
    """Count each selected row once per site, retaining every exclusion.

Terminal bounds come from the whole supplied row before site selection. A
trailing dash after an observed residue is unresolved on incomplete input.
Literal '#' is excluded separately and is never relabelled a terminal dash.
"""
    try:
        alignment = validate_alignment_document(alignment)
        shared.alignment_population(population, alignment)
    except ValueError as exc:
        raise ValueError('bvbrc_contingency_' + str(exc)) from exc
    _require(type(group_count) is int and group_count >= 0, 'group_count_invalid')
    _require(type(groups_complete) is bool, 'group_completeness_invalid')
    _require(case_policy in ('preserve', 'uppercase') and
        terminal_gap_policy == 'exclude_terminal_dash' and
        original_hash_policy == 'exclude_hash', 'count_parameters_invalid')
    _require(type(row_groups) in (tuple, list), 'row_groups_invalid')
    mapping = {}
    for row in row_groups:
        _require(type(row) is dict and set(row) == {'row_index', 'group_index'}, 'row_group_shape_invalid')
        index, group = row['row_index'], row['group_index']
        _require(type(index) is int and index >= 0 and index not in mapping, 'row_group_index_invalid')
        _require(group is None or type(group) is int and 0 <= group < group_count, 'group_index_invalid')
        mapping[index] = group
    _require(set(mapping) == set(population['row_indices']), 'row_group_population_conflict')
    rows = {i: alignment['rows'][i]['sequence'] for i in population['row_indices']}
    if case_policy == 'uppercase':
        normalized = {i: sequence.upper() for i, sequence in rows.items()}
        _require(all(len(normalized[i]) == len(rows[i]) for i in rows), 'case_changes_coordinates')
        rows = normalized
    bounds = {}
    for i, sequence in rows.items():
        nongap = [j for j, symbol in enumerate(sequence) if symbol != '-']
        bounds[i] = (nongap[0], nongap[-1]) if nongap else None
    complete = alignment['completeness'] == population['completeness'] == 'complete'
    completeness = ('complete' if complete else 'truncated' if 'truncated' in
        (alignment['completeness'], population['completeness']) else 'partial')
    sites = []
    for column in population['columns_0based']:
        collections = {key: [[] for _ in range(group_count)] for key in (
            'included_rows_by_group', 'excluded_terminal_rows_by_group',
            'excluded_original_hash_rows_by_group', 'internal_gap_rows_by_group')}
        counts, unresolved = [Counter() for _ in range(group_count)], []
        for i, sequence in rows.items():
            group = mapping[i]
            if group is None or column >= len(sequence):
                unresolved.append(i)
                continue
            symbol = sequence[column]
            if symbol == '#':
                collections['excluded_original_hash_rows_by_group'][group].append(i)
            elif bounds[i] is None or column < bounds[i][0]:
                collections['excluded_terminal_rows_by_group'][group].append(i)
            elif column > bounds[i][1]:
                if complete:
                    collections['excluded_terminal_rows_by_group'][group].append(i)
                else:
                    unresolved.append(i)
            else:
                counts[group][symbol] += 1
                collections['included_rows_by_group'][group].append(i)
                if symbol == '-':
                    collections['internal_gap_rows_by_group'][group].append(i)
        symbols = sorted({symbol for group in counts for symbol in group})
        state = ('unresolved' if not complete or unresolved or not groups_complete else
                 'all_missing' if not symbols else 'conserved' if len(symbols) == 1 else 'variable')
        sites.append({'column_0based': column, 'state': state, 'symbols': symbols,
            'observed_counts': [[group[s] for group in counts] for s in symbols],
            **collections, 'unresolved_row_indices': unresolved, 'completeness': completeness})
    return sites


def expected_contingency_counts(matrix: tuple[tuple[float, ...], ...]) -> dict:
    """Return E_ij = row_total_i / total * column_total_j and the total."""
    _matrix(matrix)
    if not matrix or not matrix[0]:
        return {'expected_counts': [], 'total': 0}
    try:
        rows = [math.fsum(row) for row in matrix]
        columns = [math.fsum(row[j] for row in matrix) for j in range(len(matrix[0]))]
        total = math.fsum(rows)
    except OverflowError as exc:
        raise ValueError('bvbrc_contingency_table_total_nonfinite') from exc
    _require(math.isfinite(total), 'table_total_nonfinite')
    expected = ([[0.0 for _ in columns] for _ in rows] if total == 0 else
                [[(r / total) * col for col in columns] for r in rows])
    return {'expected_counts': expected, 'total': total}


def pearson_contingency_statistic(matrix: tuple[tuple[float, ...], ...], *,
        expected: tuple[tuple[float, ...], ...], continuity_delta: float) -> float | None:
    """Sum (abs(O-E)-delta)^2/E; no clipping of signed differences."""
    _matrix(matrix)
    _matrix(expected)
    _require(len(matrix) == len(expected) and all(len(a) == len(b) for a, b in zip(matrix, expected)),
             'expected_dimensions_conflict')
    _require(type(continuity_delta) in (int, float), 'continuity_delta_invalid')
    try:
        finite_delta = math.isfinite(continuity_delta)
    except OverflowError:
        finite_delta = False
    _require(finite_delta and continuity_delta >= 0, 'continuity_delta_invalid')
    if not matrix or not matrix[0] or any(e <= 0 for row in expected for e in row):
        return None
    terms = []
    try:
        for observed_row, expected_row in zip(matrix, expected):
            for observed, expect in zip(observed_row, expected_row):
                difference = abs(observed - expect) - continuity_delta
                terms.append((difference / math.sqrt(expect)) ** 2)
        value = math.fsum(terms)
    except OverflowError as exc:
        raise ValueError('bvbrc_contingency_statistic_nonfinite') from exc
    _require(math.isfinite(value), 'statistic_nonfinite')
    return value


__all__ = ['count_alignment_group_sites', 'expected_contingency_counts',
           'pearson_contingency_statistic']
