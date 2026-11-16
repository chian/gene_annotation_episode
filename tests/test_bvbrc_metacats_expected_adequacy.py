from copy import deepcopy
import json

import pytest

from gene_annotation_episode.episodic_workflow.root.library.bvbrc_metacats_adequacy import (
    expected_count_adequacy, validate_expected_count_adequacy)
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_metacats_biological_calculators import (
    biological_group_statistics, biological_group_counts, biological_group_effects)
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_metacats_calculators import metacats_statistics, metacats_effects
from test_bvbrc_metacats_biological_calculators import make_counts, make_inputs, STAT_PARAMS


@pytest.mark.parametrize('epsilon,below5,minimum', [(0, 4, 3.), (.001, 4, 3.001), (2, 0, 5.)])
def test_pseudocount_changes_expected_adequacy_from_saved_matrix(epsilon, below5, minimum):
    stats = biological_group_statistics(make_counts(), **{**STAT_PARAMS, 'epsilon': epsilon})
    result = expected_count_adequacy(stats, statistics_kind='biological')
    assert result['rows'][0]['cells_below_5']['value'] == below5
    assert result['rows'][0]['minimum_expected']['value'] == pytest.approx(minimum)


def test_all_zero_pair_expected_matrix_has_actual_zero_cells():
    counts = make_counts(['A', 'C'], ['A', 'A'], group_ids=['A', 'B', 'C'])
    stats = biological_group_statistics(counts, **{**STAT_PARAMS, 'epsilon': 0, 'selected_pairs': (('B', 'C'),)})
    assert stats['pairs'][0]['expected_counts'] == [[0, 0], [0, 0]]
    result = expected_count_adequacy(stats, statistics_kind='biological')['rows'][1]
    assert result['minimum_expected']['value'] == 0
    assert result['cells_below_5']['value'] == result['cells_below_1']['value'] == result['cell_denominator']['value'] == 4


@pytest.mark.parametrize('incomplete', [False, True])
def test_no_eligible_tests_yield_empty_adequacy_rows_with_inherited_requirements(incomplete):
    alignment, args = make_inputs(['-A-', '-A-'], ['A', 'B'])
    if incomplete:
        args['assignments'] = args['assignments'][:1]
    stats = biological_group_statistics(biological_group_counts(alignment, **args), **STAT_PARAMS)
    original = deepcopy(stats)
    result = expected_count_adequacy(stats, statistics_kind='biological')
    assert result['rows'] == []
    assert result['requirements'] == stats['requirements']
    assert result['status'] == ('partial' if incomplete else 'ok')
    assert stats == original and len(stats['exclusions']) == 6


@pytest.mark.parametrize('tamper', ['population', 'denominator', 'minimum', 'counts', 'method', 'extra', 'duplicate'])
def test_closed_adequacy_result_rejects_invalid_relationships(tamper):
    result = expected_count_adequacy(biological_group_statistics(make_counts(), **STAT_PARAMS), statistics_kind='biological')
    row = result['rows'][0]
    if tamper == 'population': row['minimum_expected']['population_id'] = 'other'
    elif tamper == 'denominator': row['cell_denominator']['value'] = 3
    elif tamper == 'minimum': row['minimum_expected']['value'] = 10
    elif tamper == 'counts': row['cells_below_1']['value'] = 99
    elif tamper == 'method': row['minimum_expected']['method_id'] = 'observed_sparse'
    elif tamper == 'extra': row['observed_sparse_count'] = 0
    else: result['rows'].append(deepcopy(row))
    with pytest.raises(ValueError, match='^bvbrc_metacats_adequacy_'):
        validate_expected_count_adequacy(result)


def test_kind_selector_is_exact_and_does_not_relabel_native_as_biological():
    stats = biological_group_statistics(make_counts(), **STAT_PARAMS)
    for kind in ('native_reproduction', 'auto', 'expected'):
        with pytest.raises(ValueError, match='^bvbrc_metacats_adequacy_'):
            expected_count_adequacy(stats, statistics_kind=kind)


def test_adequacy_and_saved_validation_do_not_call_calculators(monkeypatch):
    stats = biological_group_statistics(make_counts(), **STAT_PARAMS)
    before = json.dumps(stats, sort_keys=True, allow_nan=False)
    expected = expected_count_adequacy(stats, statistics_kind='biological')
    def forbidden(*args, **kwargs): raise AssertionError('recalculation_forbidden')
    for module, names in (
        ('bvbrc_metacats_calculators', ('metacats_statistics', 'metacats_effects', 'chi_square_tail')),
        ('bvbrc_metacats_biological_calculators', ('biological_group_statistics', 'biological_group_effects', 'chi_square_tail')),
        ('bvbrc_contingency_math', ('expected_contingency_counts', 'pearson_contingency_statistic'))):
        for name in names:
            monkeypatch.setattr('gene_annotation_episode.episodic_workflow.root.library.' + module + '.' + name, forbidden)
    assert expected_count_adequacy(stats, statistics_kind='biological') == expected
    assert validate_expected_count_adequacy(json.loads(json.dumps(expected))) == expected
    assert json.dumps(stats, sort_keys=True, allow_nan=False) == before
