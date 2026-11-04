"""Hand-worked measurements and missingness, without source acquisition."""
from copy import deepcopy
import json
import math

import numpy as np
import pytest

from gene_annotation_episode.chromatin_interaction_calculations import (
    calculate_chromatin_components, calculate_contact_enrichment, calculate_insulation_components,
)
from gene_annotation_episode.chromatin_interaction_contracts import chromatin_record_digest
from verification.tool_graders_chromatin_calculations_projection_2026-10-27_443.fixture_helpers import (
    case, insulation_case, readonly, record, replace_array, serialize_tables, set_contact,
)


def calc(sheet, tables, parameters):
    return calculate_chromatin_components(sheet, tables=tables, parameters=parameters)


@pytest.mark.parametrize('name,mode,collection', [('raw','contact','pairs'), ('weighted','contact','pairs'),
    ('partial','contact','pairs'), ('insulation','insulation','windows')])
def test_literal_worked_record_measurements(name, mode, collection):
    sheet, tables, parameters = case(name)
    before = chromatin_record_digest(sheet)
    actual = calc(sheet, tables, parameters)
    oracle = record(name + '.components')
    for field in ('source_sheet_sha256', 'table_identities', 'parameters'):
        assert actual[field] == oracle[field]
    for rows in (collection, 'distance_expectations' if mode == 'contact' else 'domains'):
        got, expected = actual[mode]['populations'][0][rows], oracle[mode]['populations'][0][rows]
        assert len(got) == len(expected)
        for row, wanted in zip(got, expected):
            for field, measurement in wanted['measurements'].items():
                for part, value in measurement.items():
                    if type(value) in (int, float):
                        assert row['measurements'][field][part] == pytest.approx(value, rel=1e-14)
                    else:
                        assert row['measurements'][field][part] == value
    summary = 'counts' if mode == 'contact' else 'statistics'
    for field, wanted in oracle[mode]['populations'][0][summary].items():
        value = actual[mode]['populations'][0][summary][field]
        assert value['value'] == pytest.approx(wanted['value']) if wanted['value'] is not None else value['value'] is None
        assert value['state'] == wanted['state']
    assert chromatin_record_digest(sheet) == before
    assert all(not a.flags.writeable for p in tables['populations'].values() for a in p.values() if isinstance(a, np.ndarray))


def test_raw_weighted_and_divisive_are_explicit_replaceable_calculations():
    sheet, tables, p = case('weighted')
    old = calc(sheet, tables, p)
    raw_parameters = deepcopy(p)
    raw_parameters['normalization'] = {'kind':'raw','weight_column':None,'convention':None}
    raw = calc(sheet, tables, raw_parameters)
    assert old['contact']['populations'][0]['pairs'][0]['measurements']['fold_enrichment']['value'] == pytest.approx(6/7)
    assert raw['contact']['populations'][0]['pairs'][0]['measurements']['fold_enrichment']['value'] == 1.5
    p['normalization']['convention'] = 'divisive'
    divided = calc(sheet, tables, p)['contact']['populations'][0]
    assert divided['distance_expectations'][1]['measurements']['expected_contact']['value'] == 3.25
    assert divided['pairs'][0]['measurements']['raw_contact']['value'] == 6


def test_missing_weights_keep_raw_and_do_not_fallback():
    sheet, tables, p = case('raw')
    p['normalization'] = {'kind':'precomputed_weighted','weight_column':'weight','convention':'multiplicative'}
    result = calc(sheet, tables, p)['contact']['populations'][0]
    row = result['pairs'][0]['measurements']
    assert row['raw_contact']['value'] == 6
    assert row['normalized_contact']['reason'] == row['fold_enrichment']['reason'] == 'normalization_missing'


def test_masks_exclude_entire_sparse_rows_but_invalid_weights_do_not():
    sheet, tables, p = case('weighted')
    weights = tables['populations']['p0']['weights'].copy()
    weights[1] = np.nan
    replace_array(sheet, tables, 'weights', weights)
    row = calc(sheet, tables, p)['contact']['populations'][0]['distance_expectations'][0]['measurements']
    assert row['nominal_distance_pair_count']['value'] == 3
    assert row['masked_distance_pair_count']['value'] == 2
    assert row['valid_distance_pair_count']['value'] == 1
    assert row['expected_contact']['value'] == 4  # raw2 * weight1 * weight2 at bins2/3
    for invalid in (0., -1., np.inf):
        weights[1] = invalid
        replace_array(sheet, tables, 'weights', weights.copy())
        row = calc(sheet, tables, p)['contact']['populations'][0]['distance_expectations'][0]['measurements']
        assert row['masked_distance_pair_count']['value'] == 0
        assert row['expected_contact']['reason'] == 'normalization_weight_invalid'


def test_zero_denominator_and_observed_zero_with_positive_expectation():
    sheet, tables, p = case('raw')
    set_contact(sheet, tables, 0, 2, 0)
    result = calc(sheet, tables, p)['contact']['populations'][0]
    assert result['pairs'][0]['measurements']['fold_enrichment']['value'] == 0
    assert result['pairs'][1]['measurements']['fold_enrichment']['reason'] == 'zero_denominator'
    set_contact(sheet, tables, 1, 3, 0)
    result = calc(sheet, tables, p)['contact']['populations'][0]
    assert result['pairs'][0]['measurements']['fold_enrichment']['value'] is None
    assert result['counts']['eligible_pair_count']['value'] == 2
    assert result['counts']['fold_defined_pair_count']['value'] == 0


def test_duplicate_occurrences_are_not_independent_bin_pairs_and_near_pairs_remain():
    sheet, tables, p = case('raw')
    population = sheet['populations'][0]
    duplicate = deepcopy(population['pair_rows'][0])
    duplicate['pair_key'] = 'p0.E2.P'
    duplicate['enhancer_element_key'] = 'E2'
    population['pair_rows'].append(duplicate)
    result = calc(sheet, tables, p)['contact']['populations'][0]
    assert result['counts']['requested_pair_count']['value'] == 3
    assert result['counts']['distinct_bin_pair_count']['value'] == 2
    assert [r['measurements']['occurrence_multiplicity']['value'] for r in result['pairs']] == [2,1,2]
    p['contact']['minimum_separation_bins'] = 3
    result = calc(sheet, tables, p)['contact']['populations'][0]
    assert result['pairs'][0]['measurements']['raw_contact']['value'] == 6
    assert result['pairs'][0]['measurements']['fold_enrichment']['reason'] == 'below_minimum_separation'


@pytest.mark.parametrize('bad,reason', [(-3,'native_value_negative'), (float('nan'),'native_value_nonfinite'),
                                       (float('inf'),'native_value_nonfinite')])
def test_bad_cells_are_not_summed_or_clamped(bad, reason):
    sheet, tables, p = case('raw')
    set_contact(sheet, tables, 1, 3, bad)
    row = calc(sheet, tables, p)['contact']['populations'][0]
    assert row['distance_expectations'][1]['measurements']['expected_contact']['reason'] == reason
    assert row['distance_expectations'][1]['measurements']['raw_distance_sum']['value'] == 6
    assert row['pairs'][0]['measurements']['fold_enrichment']['value'] is None


def test_duplicate_native_pixels_are_malformed_without_summation():
    sheet, tables, p = case('raw')
    contacts = tables['populations']['p0']['contacts']
    duplicate = contacts[6:7].copy()
    duplicate['source_row'] = 100
    contacts = np.concatenate([contacts[:7], duplicate, contacts[7:]])
    replace_array(sheet, tables, 'contacts', contacts)
    row = calc(sheet, tables, p)['contact']['populations'][0]['distance_expectations'][1]['measurements']
    assert row['expected_contact']['reason'] == 'duplicate_native_pixel'
    assert row['valid_distance_pair_count']['value'] == 1


def test_insulation_all_full_windows_exact_boundaries_and_recalculation():
    sheet, tables, p = case('insulation')
    before = chromatin_record_digest(sheet)
    result = calc(sheet, tables, p)['insulation']['populations'][0]
    assert [r['measurements']['cross_contact_sum']['value'] for r in result['windows']] == [5,1,5,1,5]
    assert result['statistics']['z_population_mean']['value'] == 3.4
    assert result['statistics']['z_population_variance']['value'] == pytest.approx(3.84)
    assert result['windows'][1]['measurements']['insulation_z']['value'] == pytest.approx(-3/math.sqrt(6))
    assert [r['measurements']['boundary_position_bp']['value'] for r in result['windows'] if r['measurements']['is_boundary']['value']] == [20,40]
    assert result['domains'][0]['measurements']['domain_length_bp']['value'] == 20
    p['insulation']['z_threshold'] = -1.3
    changed = calc(sheet, tables, p)['insulation']['populations'][0]
    assert changed['domains'] == []
    assert changed['statistics']['selected_boundary_count']['value'] == 0
    assert chromatin_record_digest(sheet) == before


@pytest.mark.parametrize('adjacent,w,windows', [([5],1,1), ([0,0,0],1,3), ([1,1],2,0)])
def test_zero_variance_and_no_full_window_are_not_missing_matrices(adjacent,w,windows):
    sheet, tables, p = insulation_case(adjacent)
    p['insulation']['window_bins'] = w
    result = calc(sheet, tables, p)['insulation']['populations'][0]
    assert len(result['windows']) == windows
    assert result['statistics']['nominal_window_count']['value'] == windows
    assert result['domains'] == []
    if windows:
        assert all(r['measurements']['insulation_z']['reason'] == 'zero_variance' for r in result['windows'])
    else:
        assert result['statistics']['z_population_mean']['reason'] == 'no_full_windows'


def test_tied_minima_and_threshold_equality_are_not_boundaries():
    sheet, tables, p = insulation_case([5,1,1,5])
    p['insulation']['z_threshold'] = 2
    assert calc(sheet, tables, p)['insulation']['populations'][0]['domains'] == []
    sheet, tables, p = case('insulation')
    p['insulation']['z_threshold'] = calc(sheet,tables,p)['insulation']['populations'][0]['windows'][1]['measurements']['insulation_z']['value']
    assert calc(sheet,tables,p)['insulation']['populations'][0]['statistics']['selected_boundary_count']['value'] == 0


def test_missing_window_does_not_become_zero_or_skip_neighbor():
    sheet, tables, p = case('insulation')
    states = np.array([(2,3,5)],dtype=tables['populations']['p0']['cell_states'].dtype)
    replace_array(sheet,tables,'cell_states',states)
    result = calc(sheet,tables,p)['insulation']['populations'][0]
    assert result['windows'][2]['measurements']['cross_contact_sum']['value'] is None
    assert result['windows'][1]['measurements']['is_boundary']['reason'] == 'boundary_neighbor_unavailable'
    assert result['statistics']['omitted_window_count']['value'] == 1
    assert result['domains'] == []


def test_stable_centered_variance_and_component_specific_overflow():
    sheet, tables, p = case('raw')
    set_contact(sheet,tables,0,2,10**16)
    set_contact(sheet,tables,1,3,10**16+4)
    row = calc(sheet,tables,p)['contact']['populations'][0]['distance_expectations'][1]['measurements']
    assert row['distance_population_variance']['value'] == 4
    set_contact(sheet,tables,0,2,1e200)
    set_contact(sheet,tables,1,3,1e200)
    row = calc(sheet,tables,p)['contact']['populations'][0]['distance_expectations'][1]['measurements']
    assert row['expected_contact']['value'] == 1e200
    assert row['distance_sum_squares']['reason'] == 'numerical_overflow'
    assert row['distance_population_variance']['value'] == 0


def test_wrong_readonly_array_contract_and_parameters_reject():
    sheet,tables,p = case()
    tables['populations']['p0']['bins'] = tables['populations']['p0']['bins'].copy()
    with pytest.raises(ValueError,match='readonly'):
        calc(sheet,tables,p)
    sheet,tables,p = case()
    p['contact']['minimum_separation_bins'] = True
    with pytest.raises(ValueError):
        calc(sheet,tables,p)


def test_unknown_reference_is_qualified_and_conflict_blocks_pairs_only():
    sheet,tables,p = case()
    sheet['references']['relations'][0]['relation'] = 'unknown'
    for pair in sheet['populations'][0]['pair_rows']:
        pair['reference_relation'] = 'unknown'
    result = calc(sheet,tables,p)['contact']['populations'][0]
    assert result['pairs'][0]['measurements']['fold_enrichment']['value'] == 1.5
    assert result['pairs'][0]['qualifications']['reference_relation'] == 'unknown'
    sheet['references']['relations'][0]['relation'] = 'conflicting_assertions'
    for pair in sheet['populations'][0]['pair_rows']:
        pair['reference_relation'] = 'conflicting_assertions'
    result = calc(sheet,tables,p)['contact']['populations'][0]
    assert result['pairs'][0]['measurements']['fold_enrichment']['reason'] == 'reference_conflict'
    assert result['distance_expectations'][1]['measurements']['expected_contact']['value'] == 4


def test_saved_real_table_encodings_recalculate_without_original_input(monkeypatch):
    from gene_annotation_episode.chromatin_interaction_tables import read_chromatin_sheet_tables
    sheet,tables,p = case('weighted')
    streams = serialize_tables(sheet,tables)
    before = json.dumps(sheet,sort_keys=True)
    with read_chromatin_sheet_tables(sheet,streams=streams) as loaded:
        import builtins
        def no_open(*args,**kwargs):
            raise AssertionError('calculator attempted file acquisition')
        monkeypatch.setattr(builtins,'open',no_open)
        old = calc(sheet,loaded,p)
        p['contact']['fold_threshold'] = .5
        new = calc(sheet,loaded,p)
    assert old['contact']['populations'][0]['pairs'][0]['measurements']['above_fold_threshold']['value'] is False
    assert new['contact']['populations'][0]['pairs'][0]['measurements']['above_fold_threshold']['value'] is True
    assert json.dumps(sheet,sort_keys=True) == before
