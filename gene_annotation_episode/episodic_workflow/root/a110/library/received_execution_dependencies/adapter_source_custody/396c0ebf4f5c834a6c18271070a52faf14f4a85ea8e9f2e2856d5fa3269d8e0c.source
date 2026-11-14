"""Expected-cell adequacy from saved native or biological statistical rows.

The operand is the stored augmented expected matrix, including its known zeros.
Observed sparse cells, native labels and p values do not supply this quantity.
No original results or historical effects.augmented_adequacy fields are changed.
"""
from __future__ import annotations

from copy import deepcopy

from .bvbrc_alignment_values import numeric_cell, requirement
from .bvbrc_metacats_calculation_contracts import validate_statistics
from .bvbrc_metacats_biological_contracts import validate_biological_statistics
from . import bvbrc_metacats_biological_contracts as c


_UNITS = {'minimum_expected': 'expected_observations', 'cells_below_5': 'cells',
          'cells_below_1': 'cells', 'cell_denominator': 'cells'}
_METHOD = 'expected_count_adequacy_v1'


def _require(condition, code):
    if not condition:
        raise ValueError('bvbrc_metacats_adequacy_' + code)


def _checked(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except ValueError as exc:
        raise ValueError('bvbrc_metacats_adequacy_' + str(exc)) from exc


def expected_count_adequacy(statistics: dict, *, statistics_kind: str) -> dict:
    """Retain one adequacy row per supplied test, including pair populations."""
    _require(statistics_kind in ('native_reproduction', 'biological'), 'statistics_kind_invalid')
    validate = validate_statistics if statistics_kind == 'native_reproduction' else validate_biological_statistics
    statistics = _checked(validate, statistics)
    result = {'status': statistics['status'], 'analysis_id': statistics['analysis_id'],
        'category_id': statistics['category_id'], 'statistics_kind': statistics_kind,
        'rows': [], 'requirements': deepcopy(statistics['requirements']),
        'diagnostics': deepcopy(statistics['diagnostics'])}
    for row in statistics['omnibus'] + statistics['pairs']:
        flat = [n for erow in row['expected_counts'] for n in erow]
        evidence = []
        for key in ('epsilon', 'augmented_total', 'continuity_delta', 'chi_square', 'df', 'mathematical_p', 'log_p'):
            for item in row[key]['evidence']:
                if item not in evidence:
                    evidence.append(deepcopy(item))
        requirements = [r['requirement_id'] for r in row['requirements']]
        if not flat:
            missing = requirement(row['test_id'] + '/expected_matrix_required', kind='scientific_metadata',
                                  role='expected_contingency_matrix', reason_code='expected_matrix_required')
            result['requirements'].append(missing)
            requirements.append(missing['requirement_id'])
        values = {'minimum_expected': min(flat) if flat else None,
            'cells_below_5': sum(n < 5 for n in flat) if flat else None,
            'cells_below_1': sum(n < 1 for n in flat) if flat else None,
            'cell_denominator': len(flat) if flat else None}
        cells = {key: numeric_cell(value, state='available' if value is not None else 'missing',
            unit=_UNITS[key], origin='calculated', population_id=row['test_id'], method_id=_METHOD,
            evidence=evidence, requirement_ids=requirements) for key, value in values.items()}
        result['rows'].append({key: deepcopy(row[key]) for key in (
            'test_id', 'raw_table_id', 'kind', 'column_0based', 'group_ids')} |
            {'basis': 'augmented_expected', **cells})
    result['requirements'] = list({r['requirement_id']: r for r in result['requirements']}.values())
    if result['requirements'] and result['status'] == 'ok':
        result['status'] = 'partial'
    return validate_expected_count_adequacy(result)


def validate_expected_count_adequacy(value: dict) -> dict:
    """Validate saved adequacy shapes/relationships without recalculating tests."""
    _checked(c.shape, value, {'status', 'analysis_id', 'category_id', 'statistics_kind',
                             'rows', 'requirements', 'diagnostics'})
    _require(value['status'] in ('ok', 'partial', 'invalid') and
             value['statistics_kind'] in ('native_reproduction', 'biological'), 'kind_or_status_invalid')
    _checked(c.text, value['analysis_id']); _checked(c.text, value['category_id'])
    requirements = _checked(c.reports, value)
    _require(not requirements or value['status'] != 'ok', 'status_requirements_conflict')
    _require(type(value['rows']) is list, 'rows_invalid')
    seen, selectors = set(), set()
    for row in value['rows']:
        _checked(c.shape, row, {'test_id', 'raw_table_id', 'kind', 'column_0based', 'group_ids',
                               'basis', *_UNITS})
        _checked(c.text, row['test_id']); _checked(c.text, row['raw_table_id'])
        _checked(c.integer, row['column_0based']); _checked(c.strings, row['group_ids'])
        _require(row['basis'] == 'augmented_expected' and row['kind'] in ('omnibus', 'pairwise'), 'row_kind_invalid')
        _require(len(row['group_ids']) >= 2 and (row['kind'] != 'pairwise' or len(row['group_ids']) == 2),
                 'row_groups_invalid')
        selector = (row['column_0based'], row['kind'], tuple(row['group_ids']))
        _require(row['test_id'] not in seen and selector not in selectors, 'row_identity_duplicate')
        seen.add(row['test_id']); selectors.add(selector)
        for key, unit in _UNITS.items():
            _checked(c.cell, row[key], population=row['test_id'], unit=unit, method=_METHOD,
                     requirements=requirements)
        values = {key: row[key]['value'] for key in _UNITS}
        if values['cell_denominator'] is None:
            _require(all(n is None for n in values.values()) and requirements, 'missing_matrix_state_conflict')
            continue
        for key in ('cells_below_5', 'cells_below_1', 'cell_denominator'):
            _checked(c.integer, values[key])
        minimum = values['minimum_expected']
        _require(minimum is not None and minimum >= 0, 'minimum_expected_invalid')
        denominator = values['cell_denominator']
        _require(denominator > 0 and denominator % len(row['group_ids']) == 0, 'cell_denominator_invalid')
        _require(0 <= values['cells_below_1'] <= values['cells_below_5'] <= denominator,
                 'threshold_counts_conflict')
        for limit in (1, 5):
            _require((values['cells_below_' + str(limit)] > 0) == (minimum < limit),
                     'threshold_minimum_conflict')
    return deepcopy(value)


__all__ = ['expected_count_adequacy', 'validate_expected_count_adequacy']
