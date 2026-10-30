"""Exact NMF fixture arithmetic and pure input/association counterexamples."""
from copy import deepcopy
import json
import math
from pathlib import Path
import socket
import subprocess
import urllib.request

import pytest

from gene_annotation_episode.expression_nmf_common import (MODE, NATIVE_SCHEMA, axis, default_nmf_parameters,
    digest, fit_parameters)
from gene_annotation_episode.expression_nmf_inputs import parse_expression_matrix, prepare_expression_matrix
from gene_annotation_episode.expression_nmf_sheet import populate_nmf_sheet
from gene_annotation_episode.expression_nmf_calculations import calculate_nmf_sheet
from gene_annotation_episode.expression_nmf_result_views import project_nmf_result

W = [[1., 0.], [0., 1.], [1., 1.]]
H = [[1., 2., 0.], [0., 1., 3.]]
RAW = b'gene,A,B,B\ng,1,2,0\ng,0,1,3\ng3,1,3,3\n'


def fixture_sheet(raw=RAW, W=W, H=H, *, native_error=0.0):
    inp = parse_expression_matrix(raw, delimiter=',', metadata={'units': 'counts'})
    prepared = prepare_expression_matrix(inp, normalization='none')
    parameters = default_nmf_parameters(rank=len(H), normalization='none')
    components = axis([f'component_{k}' for k in range(len(H))], 'component')
    native = {'schema': NATIVE_SCHEMA, 'mode': MODE, 'input_identity': inp['input_identity'],
        'prepared_data_sha256': digest(prepared), 'parameters': parameters, 'estimator_parameters': fit_parameters(parameters),
        'components': components, 'axes': {'genes': [r['key'] for r in inp['genes']],
            'samples': [r['key'] for r in inp['samples']], 'components': [r['key'] for r in components]},
        'W': deepcopy(W), 'H': deepcopy(H), 'source': {'kind': 'supplied_factor_fixture',
            'estimator': 'sklearn.decomposition.NMF', 'versions': {}},
        'diagnostics': {'reconstruction_err_': native_error, 'n_iter_': None, 'fit_call_count': 0,
            'iteration_limit_reached': None, 'convergence_warning': None},
        'warnings': [], 'failures': [], 'outcome': 'complete'}
    return populate_nmf_sheet(input_data=inp, prepared_data=prepared, native_result=native)


def repopulate(sheet):
    return populate_nmf_sheet(input_data=sheet['input_data'], prepared_data=sheet['prepared_data'], native_result=sheet['native_result'])


def test_exact_factor_fixture_and_component_fractions():
    sheet = fixture_sheet()
    assert sheet['calculation_eligible']
    c = calculate_nmf_sheet(sheet)
    assert c['sse'] == c['rmse'] == c['mae'] == 0
    assert c['component_loading_sums'] == [2, 2]
    assert [row[1] for row in c['sample_component_contributions']] == [4, 2]
    assert [row[1] for row in c['sample_component_fractions']] == [2/3, 1/3]
    assert c['gene_observation_counts'] == c['sample_observation_counts'] == [3, 3, 3]
    assert c['reconstructed'] == sheet['raw_matrix']


def test_single_changed_cell_exact_denominators_and_signed_residual():
    c = calculate_nmf_sheet(fixture_sheet(RAW.replace(b'g,1,2,0', b'g,1,3,0')))
    assert c['sse'] == 1
    assert c['rmse'] == 1/3
    assert c['mae'] == 1/9
    assert c['relative_frobenius_residual'] == pytest.approx(1/math.sqrt(39))
    assert c['residuals'][0][1] == 1
    assert c['native_minus_calculated_frobenius'] == -1


def test_factor_rescaling_invariance():
    a = calculate_nmf_sheet(fixture_sheet())
    b = calculate_nmf_sheet(fixture_sheet(W=[[w[0]*8, w[1]/2] for w in W], H=[[v/8 for v in H[0]], [v*2 for v in H[1]]]))
    for field in ('reconstructed', 'sample_component_contributions', 'normalized_gene_loadings', 'sample_component_fractions'):
        assert a[field] == b[field]


def test_zero_values_are_not_missing():
    sheet = fixture_sheet(b'gene,s\ng,0\n', W=[[0]], H=[[0]], native_error=0)
    c = calculate_nmf_sheet(sheet)
    assert c['sse'] == c['mae'] == c['rmse'] == c['frobenius_residual'] == 0
    assert c['relative_frobenius_residual'] is None
    assert c['normalized_gene_loadings'] == [[None]]
    assert c['sample_component_contributions'] == [[0]]
    assert c['sample_component_fractions'] == [[None]]
    assert len(c['qualifications']) == 3
    sheet['native_result']['H'] = None
    assert calculate_nmf_sheet(repopulate(sheet))['sse'] is None


def test_overflow_component_sum_preserves_reconstruction_and_ratios():
    sheet = fixture_sheet(b'gene,s\ng,1\nh,1\n', W=[[1e308], [1e308]], H=[[1e-308]])
    c = calculate_nmf_sheet(sheet)
    assert c['status'] == 'calculated'
    assert c['component_loading_sums'] == [None]
    assert c['normalized_gene_loadings'] == [[0.5], [0.5]]
    assert c['sample_component_contributions'][0][0] == pytest.approx(2)
    assert c['sample_component_fractions'] == [[1]]
    assert c['sse'] < 1e-30


def test_squared_overflow_does_not_erase_representable_norm_or_rmse():
    sheet = fixture_sheet(b'gene,s\ng,1e200\n', W=[[0]], H=[[0]])
    c = calculate_nmf_sheet(sheet)
    assert c['sse'] is None
    assert c['frobenius_residual'] == c['rmse'] == c['mae'] == 1e200
    assert c['relative_frobenius_residual'] == 1


def test_unscaled_input_survives_unused_column_sum_overflow():
    sheet = fixture_sheet(b'gene,s\ng,1e308\nh,1e308\n', W=[[1e308], [1e308]], H=[[0]])
    assert sheet['calculation_eligible']
    assert sheet['column_denominators'] == [None]
    c = calculate_nmf_sheet(sheet)
    assert c['rmse'] == pytest.approx(1e308)
    assert c['mae'] == 1e308 and c['relative_frobenius_residual'] == 1
    assert c['sse'] is None
    assert c['frobenius_residual'] == pytest.approx(math.sqrt(2)*1e308)


def test_negative_signed_residual_is_preserved():
    c = calculate_nmf_sheet(fixture_sheet(RAW.replace(b'g,1,2,0', b'g,1,1,0')))
    assert c['residuals'][0][1] == -1
    assert c['sse'] == 1


@pytest.mark.parametrize('raw,code', [(b'', 'empty_expression_matrix'), (b'gene,s\n', 'empty_expression_matrix'),
    (b'gene,s\ng,1,2\n', 'nonrectangular_expression_row'), (b'gene,s\ng,NaN\n', 'nonfinite_expression_cell'),
    (b'gene,s\ng,inf\n', 'nonfinite_expression_cell'), (b'gene,s\ng,no\n', 'nonnumeric_expression_cell'),
    (b'\xff', 'invalid_utf8_or_delimited_input')])
def test_located_input_failures(raw, code):
    value = parse_expression_matrix(raw, delimiter=',')
    assert value['status'] == 'invalid'
    assert code in {r['code'] for r in value['failures']}
    assert prepare_expression_matrix(value, normalization='none')['fit_matrix'] is None


def test_duplicate_labels_and_positional_metadata():
    value = parse_expression_matrix(RAW, delimiter=',', metadata={'units': 'counts',
        'genes': [{'position': 1, 'label': 'g', 'target_key': 'target_2'}],
        'samples': [{'position': 2, 'label': 'B', 'condition': 'treated', 'biological_replicate': 'r2', 'technical_replicate': None}]})
    assert value['status'] == 'valid'
    assert [r['key'] for r in value['genes']] == ['gene:0', 'gene:1', 'gene:2']
    assert value['genes'][0]['metadata'] == {}
    assert value['genes'][1]['metadata']['target_key'] == 'target_2'
    assert value['samples'][1]['metadata'] == {}
    assert value['samples'][2]['metadata']['biological_replicate'] == 'r2'


@pytest.mark.parametrize('metadata', [{'instructions': 'do another analysis'},
    {'genes': [{'position': 0, 'label': 'g', 'anything': 3}]},
    {'samples': [{'position': 2, 'label': 'B', 'biological_replicate': 'two words'}]},
    {'genes': [{'position': 0, 'label': 'different'}]},
    {'samples': [{'position': 9, 'label': 'B'}]},
    {'genes': [{'position': 0, 'label': 'g'}, {'position': 0, 'label': 'g'}]}])
def test_metadata_conflicts(metadata):
    assert parse_expression_matrix(RAW, delimiter=',', metadata=metadata)['failures']


def test_normalization_exact_denominators_and_zeros():
    inp = parse_expression_matrix(RAW, delimiter=',')
    p = prepare_expression_matrix(inp, normalization='column_sum_1000')
    assert p['column_denominators'] == [2, 6, 6]
    assert p['fit_matrix'][0] == [500, 1000/3, 0]
    assert p['raw_matrix'] == inp['matrix']
    assert p['fit_units'] == 'column_sum_scaled_to_1000'
    z = parse_expression_matrix(b'gene,s\ng,0\n', delimiter=',')
    assert prepare_expression_matrix(z, normalization='none')['fit_matrix'] == [[0]]
    scaled = prepare_expression_matrix(z, normalization='column_sum_1000')
    assert scaled['fit_matrix'] is None
    assert scaled['failures'][0]['sample_position'] == 0


@pytest.mark.parametrize('change', ['axes', 'shape', 'prepared', 'input_identity', 'rank', 'negative_factor', 'nan_factor', 'source'])
def test_factor_and_operand_associations_are_rechecked(change):
    sheet = fixture_sheet()
    native = sheet['native_result']
    if change == 'axes':
        native['axes']['genes'].reverse()
    elif change == 'shape':
        native['H'][0].pop()
    elif change == 'prepared':
        sheet['prepared_data']['fit_matrix'][0][0] += 1
    elif change == 'input_identity':
        native['input_identity']['sha256'] = '0'*64
    elif change == 'rank':
        native['parameters']['rank'] = 3
    elif change == 'negative_factor':
        native['W'][0][0] = -1
    elif change == 'nan_factor':
        native['W'][0][0] = float('nan')
        with pytest.raises(ValueError):
            repopulate(sheet)
        return
    else:
        native['source'] = None
    assert not repopulate(sheet)['calculation_eligible']


def test_requested_projection_rows_and_filter_extent():
    sheet = fixture_sheet()
    result = project_nmf_result(sheet, calculate_nmf_sheet(sheet), selector={'view': 'sample_contributions',
        'sample_positions': [1], 'row_window': {'offset': 0, 'limit': 1}})
    assert result['total_available_rows'] == 6 and result['selected_row_count'] == 2
    assert result['returned_row_count'] == 1 and result['has_more']
    assert result['rows'][0]['component_contribution'] == 4
    assert result['rows'][0]['contribution_fraction'] == 2/3
    assert 'W' not in result and 'reconstructed' not in result
    selected = project_nmf_result(sheet, calculate_nmf_sheet(sheet), selector={'view': 'gene_loadings',
        'gene_positions': [0, 1], 'component_positions': [0], 'filter': {'field': 'normalized_loading', 'minimum': 0.1},
        'row_window': {'offset': 0, 'limit': 10}})
    assert selected['filtered_row_count'] == 1
    assert selected['rows'][0]['gene_position'] == 0


def test_saved_recalculation_forbids_native_network_subprocess_and_files(monkeypatch):
    from gene_annotation_episode import native_expression_nmf_driver, expression_nmf_sheet
    from sklearn.decomposition import NMF
    sheet = json.loads(json.dumps(fixture_sheet()))
    def forbidden(*args, **kwargs):
        raise AssertionError('forbidden reacquisition or fitting')
    monkeypatch.setattr(native_expression_nmf_driver, 'run_expression_nmf', forbidden)
    monkeypatch.setattr(NMF, 'fit_transform', forbidden)
    monkeypatch.setattr(expression_nmf_sheet, 'populate_nmf_sheet', forbidden)
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(Path, 'open', forbidden)
    assert calculate_nmf_sheet(sheet)['sse'] == 0
