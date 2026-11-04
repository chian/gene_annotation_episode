"""Real Biopython producer controls; no host custody or hit-calculator claims."""
import base64
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import struct

import Bio
from Bio.motifs.matrix import PositionSpecificScoringMatrix
import numpy as np
import pytest

from gene_annotation_episode import tf_binding_driver as driver
from gene_annotation_episode import tf_binding_measurements as measurements


_COUNTS = {'A': [2, 4], 'C': [1, 2], 'G': [1, 1], 'T': [4, 1]}
_BACKGROUND = {'A': .5, 'C': .25, 'G': .125, 'T': .125}


def _input(tmp_path, input_id, role, format, raw):
    path = tmp_path / (input_id + '.input')
    path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    return {'input_id': input_id, 'role': role, 'format': format,
            'path': str(path),
            'artifact': {'artifact_ref': 'artifact_' + digest, 'source_ref': None,
                         'sha256': digest, 'size_bytes': len(raw)},
            'capture': {'state': 'complete', 'byte_start_0based': 0,
                        'byte_end_0based_exclusive': len(raw),
                        'original_size_bytes': len(raw)}}


def _selection(strands=('+', '-'), *, sequence=0, matrix=0):
    return {'mode': 'explicit', 'requests': [{
        'sequence_input_id': 'dna', 'sequence_record_ordinal_0based': sequence,
        'matrix_input_id': 'matrix', 'matrix_record_ordinal_0based': matrix,
        'strands': list(strands)}]}


def _request(tmp_path, *, dna=b'GATC', dna_format='raw_dna', counts=None,
             matrix_bytes=None, matrix_format='acgt_count_json', selection=None):
    if matrix_bytes is None:
        matrix_bytes = json.dumps(_COUNTS if counts is None else counts).encode()
    return {'version': 'tf_binding_native_request_v1',
            'invocation': {'version': 'tf_binding_invocation_v1',
                'invocation_id': 'native-driver-control',
                'operation': 'identify_transcription_factor_binding_sites',
                'scan_selection': selection or {'mode': 'all_supplied_occurrences_both_strands'},
                'parameters': {'background': deepcopy(_BACKGROUND),
                               'pseudocounts': dict.fromkeys('ACGT', 0)},
                'software': [{'name': 'Biopython', 'version': None, 'sha256': None},
                             {'name': 'NumPy', 'version': None, 'sha256': None}]},
            'inputs': [_input(tmp_path, 'dna', 'dna', dna_format, dna),
                       _input(tmp_path, 'matrix', 'matrix', matrix_format, matrix_bytes)]}


@pytest.fixture
def native_calls(monkeypatch):
    original = PositionSpecificScoringMatrix.calculate
    calls = []
    def calculate(matrix, sequence):
        result = original(matrix, sequence)
        calls.append({'matrix': [[matrix[base][i] for i in range(matrix.length)]
                                 for base in 'ACGT'],
                      'sequence': str(sequence), 'scalar': np.ndim(result) == 0,
                      'raw': np.asarray(result).reshape(-1).tobytes()})
        return result
    def forbidden(*args, **kwargs):
        raise AssertionError('the native producer must not search/filter hits or acquire a logo')
    monkeypatch.setattr(PositionSpecificScoringMatrix, 'calculate', calculate)
    monkeypatch.setattr(PositionSpecificScoringMatrix, 'search', forbidden)
    monkeypatch.setattr(Bio.motifs.Motif, 'weblogo', forbidden)
    return calls


def _file(manifest, output, file_id):
    declaration, = [row for row in manifest['files'] if row['file_id'] == file_id]
    raw = (output / declaration['relative_path']).read_bytes()
    assert len(raw) == declaration['size_bytes']
    assert hashlib.sha256(raw).hexdigest() == declaration['sha256']
    return raw


def _scores(manifest, output, scan):
    raw = _file(manifest, output, scan['score_file_id'])
    assert scan['size_bytes'] == len(raw) and scan['sha256'] == hashlib.sha256(raw).hexdigest()
    return raw


def _model_buffer(model, field):
    blob = model['buffers'][field]
    raw = base64.b64decode(blob['data_base64'], validate=True)
    assert hashlib.sha256(raw).hexdigest() == blob['sha256'] and len(raw) == blob['size_bytes']
    prefix = '<' if blob['byte_order'] == 'little' else '>'
    return np.frombuffer(raw, dtype=prefix + 'f8').reshape(blob['shape'])


def test_native_asymmetric_background_retains_complete_literal_arrays(tmp_path, native_calls):
    request = _request(tmp_path)
    output = tmp_path / 'native'
    manifest = driver.run_tf_binding_native(request, output_directory=output)
    value = manifest['value']
    assert value['outcome'] == 'succeeded' and value['returncode'] is None
    assert value['biopython_version'] == Bio.__version__ and value['numpy_version'] == np.__version__
    assert [row['strand'] for row in value['scans']] == ['+', '-']
    expected = ([0., -1., 2.], [2., -1., 0.])
    assert len(native_calls) == 2
    for scan, observed_call, expected_values in zip(value['scans'], native_calls, expected):
        raw = _scores(manifest, output, scan)
        assert raw == observed_call['raw'] == struct.pack('=3f', *expected_values)
        assert scan['state'] == 'complete' and scan['declared_count'] == scan['possible_positions'] == 3
    model, = value['models']
    np.testing.assert_array_equal(_model_buffer(model, 'counts'), [[2, 4], [1, 2], [1, 1], [4, 1]])
    np.testing.assert_array_equal(_model_buffer(model, 'background'), [.5, .25, .125, .125])
    np.testing.assert_array_equal(_model_buffer(model, 'pseudocounts'), [0, 0, 0, 0])
    np.testing.assert_array_equal(_model_buffer(model, 'bounds_plus'), [-1, 2])
    np.testing.assert_array_equal(_model_buffer(model, 'bounds_minus'), [-1, 2])
    np.testing.assert_array_equal(_model_buffer(model, 'rc_pssm'),
                                  _model_buffer(model, 'pssm')[::-1, ::-1])
    assert json.loads(_file(manifest, output, 'native-result')) == value
    assert str(tmp_path) not in json.dumps(manifest)
    assert value['input_identities'] == [
        {'input_id': row['input_id'], **{key: row['artifact'][key]
          for key in ('artifact_ref', 'sha256', 'size_bytes')}} for row in request['inputs']]


def test_explicit_minus_only_decodes_once_and_never_calculates_plus(tmp_path, native_calls, monkeypatch):
    request = _request(tmp_path, selection=_selection(('-',)))
    decoder, resolver, reader = driver.decode_tf_binding_inputs, driver.resolve_tf_binding_scan_selection, driver.storage.read_bytes
    observed = {'decode': 0, 'resolve': 0, 'paths': []}
    def decode(inputs):
        observed['decode'] += 1
        return decoder(inputs)
    def resolve(decoded, selection):
        observed['resolve'] += 1
        return resolver(decoded, selection)
    def read(path):
        observed['paths'].append(path)
        return reader(path)
    monkeypatch.setattr(driver, 'decode_tf_binding_inputs', decode)
    monkeypatch.setattr(driver, 'resolve_tf_binding_scan_selection', resolve)
    monkeypatch.setattr(driver.storage, 'read_bytes', read)
    output = tmp_path / 'native'
    manifest = driver.run_tf_binding_native(request, output_directory=output)
    scan, = manifest['value']['scans']
    assert observed == {'decode': 1, 'resolve': 1, 'paths': [row['path'] for row in request['inputs']]}
    assert len(native_calls) == 1 and scan['strand'] == '-'
    assert _scores(manifest, output, scan) == struct.pack('=3f', 2, -1, 0)
    assert len(manifest['value']['models']) == 1


def test_explicit_original_occurrences_preserve_duplicate_names_and_requested_order(tmp_path, native_calls):
    pfm = b'>same repeated\nA [2 4]\nC [1 2]\nG [1 1]\nT [4 1]\n'
    request = _request(tmp_path, dna=b'>dup\nGATC\n>dup\nAAAA\n', dna_format='fasta',
                       matrix_bytes=pfm + pfm, matrix_format='jaspar_pfm',
                       selection=_selection(('-', '+'), sequence=1, matrix=1))
    output = tmp_path / 'native'
    manifest = driver.run_tf_binding_native(request, output_directory=output)
    inputs = [{key: value for key, value in row.items() if key != 'path'}
              | {'content': Path(row['path']).read_bytes()} for row in request['inputs']]
    decoded = measurements.decode_tf_binding_inputs(inputs)
    selected_sequence, selected_matrix = decoded['sequences'][1], decoded['matrices'][1]
    assert len(native_calls) == 2 and [row['sequence'] for row in native_calls] == ['AAAA', 'AAAA']
    assert [row['strand'] for row in manifest['value']['scans']] == ['-', '+']
    assert all(row['sequence_id'] == selected_sequence['sequence_id']
               and row['matrix_occurrence_id'] == selected_matrix['matrix_occurrence_id']
               for row in manifest['value']['scans'])
    assert manifest['value']['models'][0]['model_id'] == selected_matrix['model_id']
    for scan, call in zip(manifest['value']['scans'], native_calls):
        assert _scores(manifest, output, scan) == call['raw']


@pytest.mark.parametrize('dna,state,count,calls', [(b'G', 'zero_possible', 0, 0),
                                                 (b'GA', 'complete', 1, 1)])
def test_short_sequence_skips_scorer_and_single_window_retains_scalar_bits(tmp_path, native_calls, dna, state, count, calls):
    request = _request(tmp_path, dna=dna, selection=_selection(('+',)))
    output = tmp_path / 'native'
    manifest = driver.run_tf_binding_native(request, output_directory=output)
    scan, = manifest['value']['scans']
    assert scan['state'] == state and scan['possible_positions'] == scan['declared_count'] == count
    assert len(native_calls) == calls
    assert _scores(manifest, output, scan) == (b'' if not count else struct.pack('=f', 0))
    assert manifest['calls'][0]['state'] == ('not_called' if not count else 'returned')
    if count:
        assert native_calls[0]['scalar'] is True


def test_real_nan_and_negative_infinity_are_retained_without_failed_execution(tmp_path, native_calls):
    request = _request(tmp_path, dna=b'ANC', counts={'A': [1], 'C': [0], 'G': [0], 'T': [0]},
                       selection=_selection(('+',)))
    request['invocation']['parameters']['background'] = dict.fromkeys('ACGT', .25)
    output = tmp_path / 'native'
    manifest = driver.run_tf_binding_native(request, output_directory=output)
    scan, = manifest['value']['scans']
    raw = _scores(manifest, output, scan)
    values = struct.unpack('=3f', raw)
    assert values[0] == 2 and math.isnan(values[1]) and values[2] == -math.inf
    assert raw == native_calls[0]['raw'] and len(native_calls) == 1
    assert manifest['value']['outcome'] == 'succeeded' and scan['state'] == 'complete'
    model, = manifest['value']['models']
    np.testing.assert_array_equal(_model_buffer(model, 'bounds_plus'), [-math.inf, 2])


def test_real_positive_infinity_from_zero_background_is_retained(tmp_path, native_calls):
    request = _request(tmp_path, dna=b'AC', counts={'A': [1], 'C': [0], 'G': [0], 'T': [0]},
                       selection=_selection(('+',)))
    request['invocation']['parameters']['background'] = {'A': 0, 'C': .25, 'G': .25, 'T': .5}
    output = tmp_path / 'native'
    manifest = driver.run_tf_binding_native(request, output_directory=output)
    scan, = manifest['value']['scans']
    assert _scores(manifest, output, scan) == native_calls[0]['raw'] == struct.pack('=2f', math.inf, -math.inf)
    assert manifest['value']['outcome'] == 'succeeded' and scan['state'] == 'complete'
    model, = manifest['value']['models']
    np.testing.assert_array_equal(_model_buffer(model, 'bounds_plus'), [-math.inf, math.inf])


@pytest.mark.parametrize('pseudocount', [0, 1e308])
def test_native_normalization_overflow_keeps_observed_buffers_and_arrays(tmp_path, native_calls, pseudocount):
    request = _request(tmp_path, dna=b'A', counts=dict.fromkeys('ACGT', [1e308]),
                       selection=_selection(('+',)))
    request['invocation']['parameters']['background'] = dict.fromkeys('ACGT', .25)
    request['invocation']['parameters']['pseudocounts'] = dict.fromkeys('ACGT', pseudocount)
    output = tmp_path / 'native'
    manifest = driver.run_tf_binding_native(request, output_directory=output)
    value = manifest['value']
    model, = value['models']
    assert model['state'] == 'available' and model['failure_code'] is None
    np.testing.assert_array_equal(_model_buffer(model, 'counts'), [[1e308]] * 4)
    np.testing.assert_array_equal(_model_buffer(model, 'pseudocounts'), [pseudocount] * 4)
    pwm = _model_buffer(model, 'pwm')
    assert np.isnan(pwm).all() if pseudocount else (pwm == 0).all()
    assert np.isneginf(_model_buffer(model, 'pssm')).all()
    scan, = value['scans']
    assert len(native_calls) == 1 and scan['state'] == 'complete'
    assert _scores(manifest, output, scan) == native_calls[0]['raw'] == struct.pack('=f', -math.inf)
    assert manifest['calls'][0]['state'] == 'returned'
    assert value['outcome'] == 'failed' and value['returncode'] is None
    assert {'tf_binding_native_normalization_column_total_invalid',
            'tf_binding_native_pwm_column_invalid'} <= {row['code'] for row in value['issues']}
    assert any(row['path'] == '/models/0/buffers/counts' for row in value['issues'])
    assert any(row['path'] == '/models/0/buffers/pwm' for row in value['issues'])


@pytest.mark.parametrize('missing', ['dna', 'matrix', 'empty_fasta'])
def test_empty_decoded_population_is_not_run_rather_than_observed_zero(tmp_path, native_calls, missing):
    request = _request(tmp_path, dna=b'' if missing == 'empty_fasta' else b'GATC',
                       dna_format='fasta' if missing == 'empty_fasta' else 'raw_dna')
    if missing != 'empty_fasta':
        request['inputs'] = [row for row in request['inputs'] if row['role'] != missing]
    output = tmp_path / 'native'
    manifest = driver.run_tf_binding_native(request, output_directory=output)
    assert not native_calls and not manifest['calls']
    assert manifest['value']['outcome'] == 'not_run'
    assert manifest['value']['scans'] == manifest['value']['models'] == []
    assert any(row['code'] == 'tf_binding_selected_population_empty' for row in manifest['value']['issues'])
    assert json.loads(_file(manifest, output, 'native-result')) == manifest['value']


@pytest.mark.parametrize('count_token', ['1e-999', '1e999'])
def test_unrepresentable_raw_count_retains_available_sibling_without_repair(tmp_path, native_calls, count_token):
    pfm = (b'>valid\nA [1]\nC [1]\nG [1]\nT [1]\n>unrepresentable\nA ['
           + count_token.encode() + b']\nC [1]\nG [1]\nT [1]\n')
    request = _request(tmp_path, dna=b'A', matrix_bytes=pfm, matrix_format='jaspar_pfm')
    output = tmp_path / 'native'
    manifest = driver.run_tf_binding_native(request, output_directory=output)
    value = manifest['value']
    assert value['outcome'] == 'failed' and value['returncode'] is None
    assert len(native_calls) == 2
    assert [row['state'] for row in value['models']] == ['available', 'unavailable']
    assert value['models'][1]['buffers'] is None
    assert value['models'][1]['failure_code'] == 'tf_binding_count_float64_unrepresentable'
    assert [row['state'] for row in value['scans']] == ['complete', 'complete', 'unavailable', 'unavailable']
    assert any(row['code'] == 'tf_binding_count_float64_unrepresentable' for row in value['issues'])
    assert count_token.encode() in (tmp_path / 'matrix.input').read_bytes()
    assert all(_scores(manifest, output, row) for row in value['scans'][:2])


def test_raised_second_scoring_call_keeps_first_actual_array(tmp_path, native_calls, monkeypatch):
    calculate = PositionSpecificScoringMatrix.calculate
    attempted = []
    def fail_second(matrix, sequence):
        attempted.append(matrix)
        if len(attempted) == 2:
            raise RuntimeError('explicit native-failure control')
        return calculate(matrix, sequence)
    monkeypatch.setattr(PositionSpecificScoringMatrix, 'calculate', fail_second)
    output = tmp_path / 'native'
    manifest = driver.run_tf_binding_native(_request(tmp_path), output_directory=output)
    first, second = manifest['value']['scans']
    assert len(attempted) == 2 and len(native_calls) == 1
    assert _scores(manifest, output, first) == native_calls[0]['raw']
    assert second['state'] == 'unavailable' and second['score_file_id'] is None
    assert manifest['calls'][1]['state'] == 'raised'
    assert manifest['value']['outcome'] == 'failed' and manifest['value']['returncode'] is None
    assert json.loads(_file(manifest, output, 'native-result')) == manifest['value']


@pytest.mark.parametrize('written_bytes', [5, 6, 7])
def test_failed_score_write_keeps_literal_partial_float_tail(tmp_path, native_calls, monkeypatch, written_bytes):
    original = driver._write_payload
    failed = []
    def partial(descriptor, raw):
        if len(raw) == 12 and not failed:
            failed.append(True)
            assert os.write(descriptor, raw[:written_bytes]) == written_bytes
            raise OSError('explicit short-write control')
        return original(descriptor, raw)
    monkeypatch.setattr(driver, '_write_payload', partial)
    output = tmp_path / 'native'
    manifest = driver.run_tf_binding_native(
        _request(tmp_path, selection=_selection(('+',))), output_directory=output)
    scan, = manifest['value']['scans']
    assert len(native_calls) == 1 and scan['state'] == 'partial'
    raw = _scores(manifest, output, scan)
    assert raw == native_calls[0]['raw'][:written_bytes]
    assert scan['size_bytes'] == written_bytes and scan['declared_count'] == 3
    assert scan['possible_positions'] == 3 and scan['failure_code'] == 'tf_binding_score_write_failed'
    assert manifest['calls'][0]['state'] == 'returned'
    assert manifest['value']['outcome'] == 'failed'
    assert json.loads(_file(manifest, output, 'native-result')) == manifest['value']


@pytest.mark.parametrize('field,value', [('size_bytes', 999), ('sha256', '0' * 64)])
def test_changed_input_identity_rejects_before_native_or_output_reservation(tmp_path, native_calls, field, value):
    request = _request(tmp_path)
    request['inputs'][0]['artifact'][field] = value
    output = tmp_path / 'native'
    with pytest.raises(ValueError, match='tf_binding_native_input_bytes_changed'):
        driver.run_tf_binding_native(request, output_directory=output)
    assert not native_calls and not output.exists()


def test_existing_attempt_is_not_rescored_or_overwritten(tmp_path, native_calls):
    request = _request(tmp_path, selection=_selection(('-',)))
    output = tmp_path / 'native'
    driver.run_tf_binding_native(request, output_directory=output)
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    with pytest.raises(FileExistsError):
        driver.run_tf_binding_native(request, output_directory=output)
    assert len(native_calls) == 1
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before


def test_native_request_has_no_threshold_and_duplicate_selection_is_not_deduplicated(tmp_path, native_calls):
    request = _request(tmp_path, selection=_selection(('+',)))
    request['invocation']['threshold'] = 2
    with pytest.raises(ValueError):
        driver.run_tf_binding_native(request, output_directory=tmp_path / 'unknown-field')
    del request['invocation']['threshold']
    request['invocation']['scan_selection']['requests'] *= 2
    with pytest.raises(ValueError, match='tf_binding_duplicate_selected_scan'):
        driver.run_tf_binding_native(request, output_directory=tmp_path / 'duplicate')
    assert not native_calls and not (tmp_path / 'unknown-field').exists() and not (tmp_path / 'duplicate').exists()


def test_owned_worker_envelope_writes_literal_native_value_and_real_declarations(tmp_path, native_calls):
    request = _request(tmp_path, selection=_selection(('+',)))
    envelope = {'operation': 'tf_binding_native', 'arguments': {'request': request}}
    request_path, result_path = tmp_path / 'request.json', tmp_path / 'result.json'
    request_path.write_text(json.dumps(envelope))
    assert driver.main([str(request_path), str(result_path)]) == 0
    manifest = json.loads(result_path.read_bytes())
    assert manifest['version'] == 'tf_binding_native_manifest_v1' and not manifest['failures']
    assert manifest['value']['returncode'] is None and len(native_calls) == 1
    output = tmp_path / 'tf-binding-native'
    assert json.loads(_file(manifest, output, 'native-result')) == manifest['value']
    for scan in manifest['value']['scans']:
        assert _scores(manifest, output, scan) == native_calls[0]['raw']


def test_raised_native_model_is_transportable_without_claiming_process_success(tmp_path, native_calls):
    request = _request(tmp_path, dna=b'A', counts=dict.fromkeys('ACGT', [0]),
                       selection=_selection(('+',)))
    request_path, result_path = tmp_path / 'request.json', tmp_path / 'result.json'
    request_path.write_text(json.dumps({'operation': 'tf_binding_native',
                                        'arguments': {'request': request}}))
    # This is the producer transport's return value. The common lifecycle owns
    # actual process exit; the native value must never predict that exit status.
    assert driver.main([str(request_path), str(result_path)]) == 0
    manifest = json.loads(result_path.read_bytes())
    value = manifest['value']
    assert not native_calls and value['outcome'] == 'failed' and value['returncode'] is None
    model, = value['models']
    assert model['state'] == 'unavailable' and model['buffers'] is None
    assert model['failure_code'] == 'tf_binding_native_model_raised'
    scan, = value['scans']
    assert scan['state'] == 'unavailable' and scan['score_file_id'] is None
    assert manifest['calls'][0]['state'] == 'not_called'
    assert json.loads(_file(manifest, tmp_path / 'tf-binding-native', 'native-result')) == value
