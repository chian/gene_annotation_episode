"""Store-free worker checks using explicitly engineered retained score data.

These fixtures assert no genuine native attempt, Source publication or grant.
The asymmetric buffers/scores are literal independent examples; only the shared
TF calculator interprets them, and no Biopython scoring callable is used here.
"""
import base64
import builtins
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import struct
import sys

import numpy as np
import pytest

from gene_annotation_episode import tf_binding_measurements as measurements
from gene_annotation_episode import tf_binding_result_worker as worker


_CAPTURE = 'source_engineered_native_capture'
_PUBLIC = 'source_engineered_original_public_result'


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode() + b'\n'


def _capture(raw, *, state='complete', original_size=None):
    return {'state': state, 'byte_start_0based': 0,
            'byte_end_0based_exclusive': len(raw),
            'original_size_bytes': len(raw) if original_size is None else original_size}


def _input(directory, input_id, role, format, raw):
    path = directory / input_id
    path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    return {'input_id': input_id, 'role': role, 'format': format, 'path': str(path),
            'artifact': {'artifact_ref': 'artifact_' + digest, 'source_ref': None,
                         'sha256': digest, 'size_bytes': len(raw)},
            'capture': _capture(raw)}


def _file(directory, file_id, role, raw):
    path = directory / file_id
    path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    return {'file_id': file_id, 'role': role, 'path': str(path),
            'artifact': {'raw_artifact_ref': 'artifact_' + digest, 'source_ref': _CAPTURE,
                         'sha256': digest, 'size_bytes': len(raw)},
            'capture': _capture(raw)}


def _buffer(values, shape):
    raw = struct.pack('<' + 'd' * len(values), *values)
    return {'dtype': 'float64', 'byte_order': 'little', 'shape': shape,
            'data_base64': base64.b64encode(raw).decode(),
            'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}


def _selection(*, scan_ids=None, threshold=2, offset=0, limit=10):
    return {'scope': 'all_retained_scans' if scan_ids is None else 'selected_scan_ids',
            'scan_ids': scan_ids, 'raw_threshold': threshold, 'offset': offset, 'limit': limit}


@pytest.fixture
def case(tmp_path):
    original = tmp_path / 'original'
    original.mkdir()
    inputs = [
        _input(original, 'dna', 'dna', 'raw_dna', b'GATC'),
        _input(original, 'matrix', 'matrix', 'acgt_count_json',
               _json({'A': [2, 4], 'C': [1, 2], 'G': [1, 1], 'T': [4, 1]})),
    ]
    decoded = measurements.decode_tf_binding_inputs([
        {key: deepcopy(value) for key, value in row.items() if key != 'path'}
        | {'content': Path(row['path']).read_bytes()} for row in inputs])
    invocation = {'version': 'tf_binding_invocation_v1', 'invocation_id': 'engineered-result-worker',
        'operation': 'identify_transcription_factor_binding_sites',
        'scan_selection': {'mode': 'all_supplied_occurrences_both_strands'},
        'parameters': {'background': {'A': .5, 'C': .25, 'G': .125, 'T': .125},
                       'pseudocounts': dict.fromkeys('ACGT', 0)}, 'software': []}
    matrix, = decoded['matrices']
    model = {'model_id': matrix['model_id'], 'matrix_occurrence_id': matrix['matrix_occurrence_id'],
        'state': 'available', 'length': 2, 'reverse_convention': 'computed_pssm_reverse_complement_v1',
        'failure_code': None, 'buffers': {
            'counts': _buffer([2, 4, 1, 2, 1, 1, 4, 1], [4, 2]),
            'background': _buffer([.5, .25, .125, .125], [4]),
            'pseudocounts': _buffer([0, 0, 0, 0], [4]),
            'pwm': _buffer([.25, .5, .125, .25, .125, .125, .5, .125], [4, 2]),
            'pssm': _buffer([-1, 0, -1, 0, 0, 0, 2, 0], [4, 2]),
            'rc_pssm': _buffer([0, 2, 0, 0, 0, -1, 0, -1], [4, 2]),
            'bounds_plus': _buffer([-1, 2], [2]), 'bounds_minus': _buffer([-1, 2], [2]),
        }}
    files, scans = [], []
    for spec, values in zip(decoded['scan_specs'], ([0, -1, 2], [2, -1, 0])):
        raw = struct.pack('<3f', *values)
        files.append(_file(original, spec['scan_id'], 'scores', raw))
        scans.append({**spec, 'state': 'complete', 'score_file_id': spec['scan_id'],
            'dtype': 'float32', 'byte_order': 'little', 'declared_count': 3,
            'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw), 'failure_code': None})
    native = {'version': 'tf_binding_native_result_v1', 'invocation_id': invocation['invocation_id'],
        'operation': invocation['operation'], 'scan_selection': deepcopy(invocation['scan_selection']),
        'biopython_version': 'engineered-buffer-fixture-no-biopython-call', 'numpy_version': np.__version__,
        'numeric_convention': measurements.NUMERIC_CONVENTION,
        'parameters': deepcopy(invocation['parameters']),
        'input_identities': [{'input_id': row['input_id'], **{key: row['artifact'][key]
            for key in ('artifact_ref', 'sha256', 'size_bytes')}} for row in inputs],
        'outcome': 'succeeded', 'returncode': None, 'models': [model], 'scans': scans, 'issues': []}
    files.insert(0, _file(original, 'native-result', 'native_result', _json(native)))
    request = {'version': 'tf_binding_result_request_v1', 'mode': 'parse',
        'inputs': inputs, 'invocation': invocation,
        'execution': {'metadata_file_id': 'native-result', 'value': native}, 'files': files,
        'saved': None, 'selection': _selection(), 'projection_source_ref': _CAPTURE}
    return request


@pytest.fixture(autouse=True)
def no_native_scoring_or_owners(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name == 'Bio' or name.startswith('Bio.') or name.endswith(('.tf_binding_driver', '.store', '.native_lifecycle')):
            raise AssertionError('the result worker cannot import scoring or host publication/lifecycle owners')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', guarded)
    matrix_module = sys.modules.get('Bio.motifs.matrix')
    if matrix_module is not None:
        def forbidden(*args, **kwargs):
            raise AssertionError('native scoring is forbidden in result work')
        monkeypatch.setattr(matrix_module.PositionSpecificScoringMatrix, 'calculate', forbidden)


def _output(tmp_path, name):
    directory = tmp_path / name
    directory.mkdir()
    return directory


def _document(output, declaration):
    raw = (output / declaration['relative_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == declaration['sha256']
    assert len(raw) == declaration['size_bytes']
    return json.loads(raw)


def _saved(request, output, result, *, selection=None):
    declaration = result['sheet']
    return {'version': 'tf_binding_result_request_v1', 'mode': 'calculate_saved',
        'inputs': None, 'invocation': None, 'execution': None, 'files': None,
        'saved': {'file': {'artifact_ref': 'artifact_' + declaration['sha256'],
                          **{key: declaration[key] for key in ('sha256', 'size_bytes', 'format')}},
                  'path': str(output / declaration['relative_path'])},
        'selection': deepcopy(request['selection'] if selection is None else selection),
        'projection_source_ref': _PUBLIC}


def _keys(value):
    if isinstance(value, dict):
        return set(value) | set().union(*(_keys(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(*(_keys(v) for v in value))
    return set()


def test_parse_retains_authoritative_values_private_locations_and_requested_selection(case, tmp_path, monkeypatch):
    output = _output(tmp_path, 'parse')
    original, calls = worker.calculate_tf_binding_components, []
    def calculate(sheet, selection):
        calls.append(deepcopy(selection))
        return original(sheet, selection)
    monkeypatch.setattr(worker, 'calculate_tf_binding_components', calculate)
    result = worker.run_tf_binding_result(case, output_directory=output)
    assert result['version'] == 'tf_binding_result_output_v1'
    assert result['requested_selection'] == case['selection']
    assert type(result['requested_selection']['raw_threshold']) is int
    sheet = _document(output, result['sheet'])
    components = _document(output, result['components'])
    ids = [row['spec']['scan_id'] for row in sheet['score_arrays']]
    assert result['selection'] == {'version': 'tf_binding_selection_v1', 'scan_ids': ids,
                                   'raw_threshold': 2., 'offset': 0, 'limit': 10}
    assert calls == [result['selection']]
    assert result['value']['source_ref'] == _CAPTURE
    assert [(row['strand'], row['start_0based'], row['end_0based_exclusive'])
            for row in result['value']['hits']] == [('-', 0, 2), ('+', 2, 4)]
    assert components['totals']['possible_strand_windows']['value'] == 6
    assert components['totals']['full_matched_scores']['value'] == 2
    location = components['hits'][0]['score']['location']
    score_file = case['files'][2]
    assert location['artifact'] == {key: score_file['artifact'][key]
                                    for key in ('raw_artifact_ref', 'source_ref', 'sha256')}
    assert location['byte_start_0based'] == 0 and location['byte_end_0based_exclusive'] == 4
    assert components['hits'][0]['relative_score']['operand_evidence']['score_location'] == location
    assert 'location' in _keys(components)
    assert not {'location', 'operand_evidence', 'evidence_refs'} & _keys(result['value'])
    assert str(tmp_path) not in json.dumps(result['value'])


def test_saved_calculation_reads_only_pinned_sheet_and_never_copies_it(case, tmp_path, monkeypatch):
    parsed = _output(tmp_path, 'parse')
    first = worker.run_tf_binding_result(case, output_directory=parsed)
    saved = _saved(case, parsed, first, selection=_selection(threshold=0, offset=1, limit=2))
    original, observed = worker.storage.read_bytes, []
    def read(path):
        assert str(path) == saved['saved']['path']
        observed.append(str(path))
        return original(path)
    monkeypatch.setattr(worker.storage, 'read_bytes', read)
    def forbidden(*args, **kwargs):
        raise AssertionError('saved mode must not reparse original input/native captures')
    monkeypatch.setattr(worker, 'populate_tf_binding_sheet', forbidden)
    output = _output(tmp_path, 'saved')
    result = worker.run_tf_binding_result(saved, output_directory=output)
    assert observed == [saved['saved']['path']]
    assert result['sheet'] is None and not (output / 'sheet.json').exists()
    assert result['value']['source_ref'] == _PUBLIC
    assert [(row['strand'], row['start_0based']) for row in result['value']['hits']] == [('-', 0), ('+', 2)]
    assert result['value']['totals']['full_matched_scores']['value'] == 4
    assert _document(output, result['components'])['selection'] == result['selection']


def test_explicit_order_and_window_are_passed_unchanged_to_the_shared_calculator(case, tmp_path):
    plus, minus = [row['scan_id'] for row in case['execution']['value']['scans']]
    case['selection'] = _selection(scan_ids=[minus, plus], threshold=2, offset=0, limit=1)
    output = _output(tmp_path, 'selected')
    result = worker.run_tf_binding_result(case, output_directory=output)
    assert result['selection']['scan_ids'] == [minus, plus]
    assert result['requested_selection'] == case['selection']
    assert [(row['strand'], row['start_0based']) for row in result['value']['hits']] == [('-', 0)]
    assert result['value']['totals']['full_matched_scores']['value'] == 2


@pytest.mark.parametrize('tail', [1, 2, 3])
def test_captured_score_prefix_keeps_complete_values_and_literal_trailing_bytes(case, tmp_path, tail):
    row = case['files'][2]
    original_size = row['artifact']['size_bytes']
    path = Path(row['path'])
    raw = path.read_bytes()[:4 + tail]
    path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    row['artifact'].update(raw_artifact_ref='artifact_' + digest, sha256=digest, size_bytes=len(raw))
    row['capture'] = _capture(raw, state='truncated', original_size=original_size)
    output = _output(tmp_path, 'partial')
    result = worker.run_tf_binding_result(case, output_directory=output)
    sheet = _document(output, result['sheet'])
    array = sheet['score_arrays'][1]
    assert base64.b64decode(array['blob']['data_base64']) == raw
    assert array['coverage']['captured_complete_elements'] == array['coverage']['usable_elements'] == 1
    assert array['coverage']['trailing_bytes'] == tail and array['coverage']['declared_count'] == 3
    assert result['value']['status'] == 'partial'
    assert result['value']['totals']['full_matched_scores']['value'] is None
    assert [(hit['strand'], hit['start_0based']) for hit in result['value']['hits']] == [('-', 0), ('+', 2)]


@pytest.mark.parametrize('kind', ['input', 'capture', 'saved'])
def test_malformed_pin_metadata_rejects_before_any_file_read(case, tmp_path, monkeypatch, kind):
    request = deepcopy(case)
    if kind == 'saved':
        parsed = _output(tmp_path, 'parse')
        first = worker.run_tf_binding_result(case, output_directory=parsed)
        request = _saved(case, parsed, first)
        artifact = request['saved']['file']
    else:
        artifact = request['inputs'][0]['artifact'] if kind == 'input' else request['files'][0]['artifact']
    artifact['sha256'] = 'not-a-digest'
    def forbidden(*args, **kwargs):
        raise AssertionError('malformed pin metadata cannot open data or calculate')
    monkeypatch.setattr(worker.storage, 'read_bytes', forbidden)
    monkeypatch.setattr(worker, 'populate_tf_binding_sheet', forbidden)
    monkeypatch.setattr(worker, 'calculate_tf_binding_components', forbidden)
    output = _output(tmp_path, 'invalid')
    with pytest.raises(ValueError):
        worker.run_tf_binding_result(request, output_directory=output)
    assert list(output.iterdir()) == []


def test_changed_native_bytes_do_not_reach_population_or_calculation(case, tmp_path, monkeypatch):
    Path(case['files'][1]['path']).write_bytes(b'altered')
    def forbidden(*args, **kwargs):
        raise AssertionError('a pinned-byte contradiction cannot reach the shared parser/calculator')
    monkeypatch.setattr(worker, 'populate_tf_binding_sheet', forbidden)
    monkeypatch.setattr(worker, 'calculate_tf_binding_components', forbidden)
    output = _output(tmp_path, 'changed')
    with pytest.raises(ValueError, match='tf_binding_result_file_identity_conflict'):
        worker.run_tf_binding_result(case, output_directory=output)
    assert list(output.iterdir()) == []


def test_missing_native_scores_leave_valid_sheet_and_controlled_cli_failure(case, tmp_path):
    case['execution'] = {'metadata_file_id': None, 'value': None}
    case['files'] = []
    output = _output(tmp_path, 'missing')
    request_path, result_path = output / 'request.json', output / 'worker-result.json'
    request_path.write_bytes(_json({'operation': 'tf_binding_result', 'arguments': {'request': case}}))
    assert worker.main([str(request_path), str(result_path)]) == 2
    assert json.loads(result_path.read_bytes()) == {
        'code': 'tf_binding_native_scores_unavailable', 'exception_type': 'ValueError'}
    sheet = measurements.validate_tf_binding_sheet(json.loads((output / 'sheet.json').read_bytes()))
    assert sheet['execution']['value'] is None
    assert all(row['coverage']['state'] == 'unavailable' for row in sheet['score_arrays'])
    assert not (output / 'components.json').exists()


def test_late_calculation_failure_preserves_exact_earlier_sheet(case, tmp_path, monkeypatch):
    output = _output(tmp_path, 'late')
    captured = []
    def fail(sheet, selection):
        raw = (output / 'sheet.json').read_bytes()
        assert json.loads(raw) == sheet
        captured.append(raw)
        raise ValueError('engineering_selected_calculation_failure')
    monkeypatch.setattr(worker, 'calculate_tf_binding_components', fail)
    with pytest.raises(ValueError, match='engineering_selected_calculation_failure'):
        worker.run_tf_binding_result(case, output_directory=output)
    assert captured == [(output / 'sheet.json').read_bytes()]
    assert not (output / 'components.json').exists()


def test_existing_outputs_cannot_reopen_originals_or_repeat_calculation(case, tmp_path, monkeypatch):
    output = _output(tmp_path, 'once')
    worker.run_tf_binding_result(case, output_directory=output)
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    def forbidden(*args, **kwargs):
        raise AssertionError('same-directory reentry cannot read inputs or calculate again')
    monkeypatch.setattr(worker.storage, 'read_bytes', forbidden)
    monkeypatch.setattr(worker, 'calculate_tf_binding_components', forbidden)
    with pytest.raises(ValueError, match='tf_binding_result_output_already_exists'):
        worker.run_tf_binding_result(case, output_directory=output)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before


@pytest.mark.parametrize('change', ['mixed_mode', 'source_namespace', 'duplicate_scans', 'bool_offset'])
def test_invalid_request_selection_or_mode_rejects_before_data(case, tmp_path, monkeypatch, change):
    request = deepcopy(case)
    if change == 'mixed_mode': request['saved'] = {'file': {}, 'path': None}
    elif change == 'source_namespace': request['projection_source_ref'] = 'artifact_not_a_source'
    elif change == 'duplicate_scans':
        scan_id = request['execution']['value']['scans'][0]['scan_id']
        request['selection'] = _selection(scan_ids=[scan_id, scan_id])
    else: request['selection']['offset'] = True
    def forbidden(*args, **kwargs):
        raise AssertionError('invalid request must be rejected before data reads')
    monkeypatch.setattr(worker.storage, 'read_bytes', forbidden)
    output = _output(tmp_path, 'invalid')
    with pytest.raises(ValueError):
        worker.run_tf_binding_result(request, output_directory=output)
    assert list(output.iterdir()) == []


def test_cli_uses_closed_owned_envelope_and_immutable_data_declarations(case, tmp_path):
    output = _output(tmp_path, 'cli')
    request_path, result_path = output / 'request.json', output / 'worker-result.json'
    request_path.write_bytes(_json({'operation': 'tf_binding_result', 'arguments': {'request': case}}))
    assert worker.main([str(request_path), str(result_path)]) == 0
    result = json.loads(result_path.read_bytes())
    assert result['value']['source_ref'] == case['projection_source_ref']
    assert _document(output, result['sheet'])['version'] == measurements.SHEET_VERSION
    assert _document(output, result['components'])['version'] == measurements.COMPONENTS_VERSION
    before = {path.name: path.read_bytes() for path in output.iterdir()}
    with pytest.raises(ValueError, match='tf_binding_result_worker_result_already_exists'):
        worker.main([str(request_path), str(result_path)])
    assert {path.name: path.read_bytes() for path in output.iterdir()} == before
