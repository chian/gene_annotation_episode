"""Hand-worked measurements and missingness, without source acquisition."""
from copy import deepcopy
from importlib import import_module
import json
import math

import numpy as np
import pytest

from gene_annotation_episode.chromatin_interaction_calculations import (
    calculate_chromatin_components, calculate_contact_enrichment, calculate_insulation_components,
)
from gene_annotation_episode.chromatin_interaction_contracts import chromatin_record_digest
_fixtures = import_module('verification.tool_graders_chromatin_calculations_projection_2026-10-27_443.fixture_helpers')
case, insulation_case, record = _fixtures.case, _fixtures.insulation_case, _fixtures.record
replace_array, serialize_tables, set_contact = _fixtures.replace_array, _fixtures.serialize_tables, _fixtures.set_contact
native_case = _fixtures.native_case


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
    assert result['counts']['above_threshold_pair_count']['reason'] == 'normalization_missing'


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
        weights = weights.copy()
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


def test_complete_empty_sparse_matrix_is_a_real_zero_not_missing():
    sheet,tables,p = case('raw')
    replace_array(sheet,tables,'contacts',tables['populations']['p0']['contacts'][:0].copy())
    population = sheet['populations'][0]
    population['raw_cell_population'].update(stored_rows=0,explicit_zero_rows=0,
        implicit_zero_directed_cells=16,validated_observed_row_count=0)
    for pair in population['pair_rows']:
        pair['raw_contact']['value'] = 0
        pair['cell_origin'] = 'validated_implicit_zero'
        pair['source_locators'] = []
    result = calc(sheet,tables,p)['contact']['populations'][0]
    assert population['raw_cell_population']['directed_cells'] == 16
    assert population['raw_cell_population']['unique_unordered_cells'] == 10
    assert result['pairs'][0]['measurements']['raw_contact']['value'] == 0
    assert result['pairs'][0]['measurements']['fold_enrichment']['reason'] == 'zero_denominator'
    assert [r['measurements']['valid_distance_pair_count']['value'] for r in result['distance_expectations']] == [3,2,1]


def test_declared_mask_includes_sparse_omissions_and_all_masked_is_undefined():
    sheet,tables,p = case('weighted')
    weights = np.array([1.,np.nan,1.,1.])
    replace_array(sheet,tables,'weights',weights)
    row = calc(sheet,tables,p)['contact']['populations'][0]['distance_expectations'][0]['measurements']
    assert row['distance_sum']['value'] == row['expected_contact']['value'] == 2
    replace_array(sheet,tables,'weights',np.full(4,np.nan))
    row = calc(sheet,tables,p)['contact']['populations'][0]['distance_expectations'][0]['measurements']
    assert row['valid_distance_pair_count']['value'] == 0
    assert row['expected_contact']['reason'] == 'no_valid_distance_pairs'


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
    set_contact(sheet,tables,1,3,10**16+1)
    row = calc(sheet,tables,p)['contact']['populations'][0]['distance_expectations'][1]['measurements']
    assert row['distance_population_variance']['value'] == .25
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
    sheet,tables,p = case()
    sheet['populations'][0]['pair_rows'][0]['promoter_bin_ordinal'] = 1
    with pytest.raises(ValueError,match='pair_bin_ordinal'):
        calc(sheet,tables,p)


def test_unrepresentable_positive_moments_do_not_become_exact_zero():
    sheet,tables,p = case()
    set_contact(sheet,tables,0,2,1e-200)
    set_contact(sheet,tables,1,3,2e-200)
    row = calc(sheet,tables,p)['contact']['populations'][0]['distance_expectations'][1]['measurements']
    assert row['expected_contact']['value'] == pytest.approx(1.5e-200,abs=0)
    assert row['distance_sum_squares']['reason'] == 'numerical_overflow'
    assert row['distance_population_variance']['reason'] == 'numerical_overflow'


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


@pytest.mark.parametrize('name,fold', [('raw',1.5),('weighted',6/7)])
def test_actual440_native_parse_sheet_arrays_calculation_and_saved_rerun(name,fold,monkeypatch,tmp_path):
    from gene_annotation_episode.chromatin_interaction_tables import read_chromatin_sheet_tables
    sheet,streams,p = native_case(name)
    before = chromatin_record_digest(sheet)
    import gene_annotation_episode.chromatin_cooler_inputs as native_reader
    def no_native(*args,**kwargs):
        raise AssertionError('saved calculation reran native parsing')
    monkeypatch.setattr(native_reader,'read_cooler_contacts',no_native)
    with read_chromatin_sheet_tables(sheet,streams=streams) as tables:
        c = calc(sheet,tables,p)
        (tmp_path / 'sheet.json').write_text(json.dumps(sheet,indent=2,allow_nan=False))
        (tmp_path / 'components.json').write_text(json.dumps(c,indent=2,allow_nan=False))
        row = c['contact']['populations'][0]['pairs'][0]
        assert row['pair_key'] == 'p0.e0.p1'
        assert row['measurements']['raw_contact']['value'] == 6
        assert row['measurements']['fold_enrichment']['value'] == pytest.approx(fold)
        p['contact']['fold_threshold'] = .5
        newer = calc(sheet,tables,p)
        assert newer['contact']['populations'][0]['pairs'][0]['measurements']['above_fold_threshold']['value'] is True
    assert chromatin_record_digest(sheet) == before


def test_actual440_sparse_insulation_includes_final_full_window(tmp_path):
    from gene_annotation_episode.chromatin_interaction_tables import read_chromatin_sheet_tables
    sheet,streams,p = native_case('insulation')
    assert sheet['populations'][0]['raw_cell_population']['implicit_zero_directed_cells'] == 25
    with read_chromatin_sheet_tables(sheet,streams=streams) as tables:
        components = calc(sheet,tables,p)
        result = components['insulation']['populations'][0]
    (tmp_path / 'sheet.json').write_text(json.dumps(sheet,indent=2,allow_nan=False))
    (tmp_path / 'components.json').write_text(json.dumps(components,indent=2,allow_nan=False))
    assert [r['measurements']['cross_contact_sum']['value'] for r in result['windows']] == [5,1,5,1,5]
    assert result['statistics']['z_population_variance']['value'] == pytest.approx(3.84)
    assert result['domains'][0]['measurements']['domain_length_bp']['value'] == 20


def test_actual_native_same_bin_and_duplicate_occurrence_population_retained():
    from gene_annotation_episode.chromatin_interaction_tables import read_chromatin_sheet_tables
    bed = b'chrA\t1\t2\tE\nchrA\t1\t2\tP\nchrA\t21\t22\tQ\nchrA\t1\t2\tE\n'
    assignments = [{'element_key':key,'source_data_row':i,'class':kind,'gene_links':[],
                    'anchor':{'policy':'interval_start'}} for i,(key,kind) in
                   enumerate([('E','enhancer'),('P','promoter'),('Q','promoter'),('E2','enhancer')])]
    sheet,streams,p = native_case('raw',bed=bed,assignments=assignments)
    with read_chromatin_sheet_tables(sheet,streams=streams) as tables:
        result = calc(sheet,tables,p)['contact']['populations'][0]
    assert len(result['pairs']) == 4
    assert result['counts']['distinct_bin_pair_count']['value'] == 2
    assert result['pairs'][0]['measurements']['raw_contact']['value'] == 4
    assert result['pairs'][0]['measurements']['fold_enrichment']['reason'] == 'same_bin_not_evaluated'
    assert all(r['measurements']['occurrence_multiplicity']['value'] == 2 for r in result['pairs'])


def test_actual_lower_triangle_malformed_row_is_retained_and_qualified_not_reinterpreted():
    import io
    import h5py
    from gene_annotation_episode.chromatin_interaction_tables import read_chromatin_sheet_tables
    def malformed(raw):
        stream = io.BytesIO(raw)
        with h5py.File(stream,'r+') as file:
            file['pixels/bin2_id'][4] = 0  # Original source row4 becomes (1,0).
        return stream.getvalue()
    sheet,streams,p = native_case('raw',raw_transform=malformed)
    assert sheet['populations'][0]['extent'] == 'partial'
    with read_chromatin_sheet_tables(sheet,streams=streams) as tables:
        contacts = tables['populations']['p0']['contacts']
        assert any(int(r['bin1_id']) == 1 and int(r['bin2_id']) == 0 and int(r['source_row']) == 4 for r in contacts)
        result = calc(sheet,tables,p)['contact']['populations'][0]
        assert result['pairs'][0]['measurements']['raw_contact']['value'] == 6
        assert result['pairs'][0]['measurements']['fold_enrichment']['reason'] == 'incomplete_comparison_population'
        changed = deepcopy(sheet)
        changed['populations'][0]['failures'] = []
        with pytest.raises(ValueError,match='upper_triangle'):
            calc(changed,tables,p)
