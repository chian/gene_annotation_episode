"""Hand-derived retained-score controls; no Bio scoring or native execution.

All model/score bytes in these fixtures are explicitly engineered observations,
not claims of a completed native producer or real Source custody. The independent
asymmetric, float32 boundary and extended-real cases are checked against literal
expected numbers, never a second motif-scoring implementation.
"""
import base64
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import numpy as np
import pytest

from gene_annotation_episode import tf_binding_measurements as tf


CAPTURE_SOURCE = 'source_' + 'a' * 24
COUNTS = {'A': [2, 4], 'C': [1, 2], 'G': [1, 1], 'T': [4, 1]}
PWM = [[.25, .5], [.125, .25], [.125, .125], [.5, .125]]
PSSM = [[-1, 0], [-1, 0], [0, 0], [2, 0]]
RC_PSSM = [[0, 2], [0, 0], [0, -1], [0, -1]]
BACKGROUND = {'A': .5, 'C': .25, 'G': .125, 'T': .125}


def input_file(input_id, role, format, content, *, state='complete', original_size=None):
    raw = b'' if content is None else content
    digest = hashlib.sha256(raw).hexdigest()
    return {'input_id': input_id, 'role': role, 'format': format, 'content': content,
        'artifact': {'artifact_ref': 'artifact_' + digest, 'sha256': digest, 'size_bytes': len(raw), 'source_ref': None},
        'capture': {'state': state, 'byte_start_0based': 0, 'byte_end_0based_exclusive': len(raw),
            'original_size_bytes': len(raw) if original_size is None else original_size}}


def buffer64(values, shape):
    raw = struct.pack('<' + 'd' * len(values), *values)
    return {'dtype': 'float64', 'byte_order': 'little', 'shape': shape, 'data_base64': base64.b64encode(raw).decode(),
        'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}


def captured_file(file_id, role, content, *, state='complete', original_size=None, source=CAPTURE_SOURCE):
    raw = b'' if content is None else content
    return {'file_id': file_id, 'role': role, 'content': content,
        'artifact': None if content is None else {'raw_artifact_ref': 'artifact_' + hashlib.sha256(raw).hexdigest(),
            'source_ref': source, 'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)},
        'capture': {'state': state, 'byte_start_0based': 0, 'byte_end_0based_exclusive': len(raw),
            'original_size_bytes': len(raw) if original_size is None else original_size}}


def engineered_sheet(*, dna=b'GATC', counts=None, pwm=None, pssm=None, rc=None, background=None,
        bounds=(-1, 2), scores=None, strands=('+', '-'), scan_state='complete', native_outcome='succeeded',
        payload=None, capture_size=None, matrix_bytes=None, model_available=True,
        numpy_version=None, model_failure='tf_binding_count_float64_unrepresentable', byte_order='little'):
    counts = deepcopy(COUNTS if counts is None else counts)
    width = len(counts['A'])
    inputs = [input_file('dna', 'dna', 'raw_dna', dna), input_file('matrix', 'matrix', 'acgt_count_json',
        json.dumps(counts).encode() if matrix_bytes is None else matrix_bytes)]
    decoded = tf.decode_tf_binding_inputs(inputs)
    scope = {'mode': 'explicit', 'requests': [{'sequence_input_id': 'dna', 'sequence_record_ordinal_0based': 0,
        'matrix_input_id': 'matrix', 'matrix_record_ordinal_0based': 0, 'strands': list(strands)}]}
    specs = tf.resolve_tf_binding_scan_selection(decoded, scope)
    parameters = {'background': deepcopy(BACKGROUND if background is None else background),
        'pseudocounts': dict.fromkeys('ACGT', 0.)}
    invocation = {'version': 'tf_binding_invocation_v1', 'invocation_id': 'engineered-no-native-call',
        'operation': tf.OPERATION, 'scan_selection': scope, 'parameters': parameters, 'software': []}
    matrix = decoded['matrices'][0]
    model = {'model_id': matrix['model_id'], 'matrix_occurrence_id': matrix['matrix_occurrence_id'],
        'state': 'available' if model_available else 'unavailable', 'length': width,
        'reverse_convention': 'computed_pssm_reverse_complement_v1', 'buffers': None,
        'failure_code': None if model_available else model_failure}
    if model_available:
        flatten = lambda rows: [v for row in rows for v in row]
        model['buffers'] = {'counts': buffer64(flatten([counts[b] for b in 'ACGT']), [4, width]),
            'background': buffer64([parameters['background'][b] for b in 'ACGT'], [4]),
            'pseudocounts': buffer64([0, 0, 0, 0], [4]),
            'pwm': buffer64(flatten(PWM if pwm is None else pwm), [4, width]),
            'pssm': buffer64(flatten(PSSM if pssm is None else pssm), [4, width]),
            'rc_pssm': buffer64(flatten(RC_PSSM if rc is None else rc), [4, width]),
            'bounds_plus': buffer64(list(bounds), [2]), 'bounds_minus': buffer64(list(bounds), [2])}
    native = {'version': 'tf_binding_native_result_v1', 'invocation_id': invocation['invocation_id'],
        'operation': tf.OPERATION, 'scan_selection': scope, 'biopython_version': 'engineered-no-Bio-call',
        'numpy_version': np.__version__ if numpy_version is None else numpy_version,
        'numeric_convention': tf.NUMERIC_CONVENTION, 'parameters': parameters,
        'input_identities': [{'input_id': v['input_id'], **{k: v['artifact'][k] for k in ('artifact_ref', 'sha256', 'size_bytes')}} for v in inputs],
        'outcome': native_outcome, 'returncode': None, 'models': [model], 'scans': [], 'issues': []}
    files = []
    score_values = {'+': [0, -1, 2], '-': [2, -1, 0]} if scores is None else scores
    for spec in specs:
        unavailable = not model_available or scan_state == 'unavailable'
        values = score_values.get(spec['strand'], [])
        raw = struct.pack(('<' if byte_order == 'little' else '>') + 'f' * len(values), *values)
        if payload is not None: raw = payload
        scan = {**spec, 'state': 'unavailable' if unavailable else scan_state,
            'score_file_id': None if unavailable else spec['scan_id'], 'dtype': 'float32', 'byte_order': byte_order,
            'declared_count': None if unavailable else len(values),
            'sha256': None if unavailable else hashlib.sha256(raw).hexdigest(),
            'size_bytes': None if unavailable else len(raw), 'failure_code': model_failure if unavailable else None}
        native['scans'].append(scan)
        if not unavailable:
            retained = raw if capture_size is None else raw[:capture_size]
            files.append(captured_file(spec['scan_id'], 'scores', retained,
                state='complete' if capture_size is None else 'truncated', original_size=len(raw)))
    metadata = captured_file('metadata', 'native_result', json.dumps(native, allow_nan=False).encode())
    files.insert(0, metadata)
    sheet = tf.populate_tf_binding_sheet(inputs=inputs, invocation=invocation,
        execution={'metadata_file_id': 'metadata', 'value': native}, files=files)
    return sheet


def selection(sheet, threshold=2., *, offset=0, limit=100, scan_ids=None):
    return {'version': 'tf_binding_selection_v1', 'scan_ids': [v['spec']['scan_id'] for v in sheet['score_arrays']] if scan_ids is None else scan_ids,
        'raw_threshold': threshold, 'offset': offset, 'limit': limit}


def count(components, name):
    return components['totals'][name]['value']


def test_original_fasta_slots_utf8_spans_and_duplicate_labels_do_not_collapse():
    raw = '>dup café\r\nAC\r\n>\nTT\n>dup second\nGT\n'.encode()
    decoded = tf.decode_tf_binding_inputs([input_file('dna', 'dna', 'fasta', raw)])
    assert [v['record_ordinal_0based'] for v in decoded['sequences']] == [0, 1, 2]
    assert [v['identifier'] for v in decoded['sequences']] == ['dup', None, 'dup']
    assert [v['state'] for v in decoded['sequences']] == ['available', 'unavailable', 'available']
    for record, original in zip(decoded['sequences'], [b'>dup caf\xc3\xa9\r\nAC\r\n', b'>\nTT\n', b'>dup second\nGT\n']):
        loc = record['locator']
        assert raw[loc['byte_start_0based']:loc['byte_end_0based_exclusive']] == original
        assert loc['artifact_ref'] == decoded['inputs'][0]['artifact']['artifact_ref'] and 'source_ref' not in loc


def test_matrix_original_ordinals_raw_tokens_and_idless_count_json_are_explicit():
    raw = b'>same first\n1 2\n3 4\n>same second\n1 2\n3 4\n5 6\n7 8\n'
    item = input_file('m', 'matrix', 'jaspar_pfm', raw)
    decoded = tf.decode_tf_binding_inputs([item])
    assert [(v['record_ordinal_0based'], v['native_matrix_id'], v['state']) for v in decoded['matrices']] == [(0, 'same', 'unavailable'), (1, 'same', 'available')]
    for token in decoded['matrices'][1]['count_tokens']['A']:
        loc = token['locator']; assert raw[loc['byte_start_0based']:loc['byte_end_0based_exclusive']].decode() == token['raw_token']
    generic = tf.decode_tf_binding_inputs([input_file('m', 'matrix', 'acgt_count_json', b'{"A":[1e-999],"C":[2],"G":[3],"T":[4]}')])
    row = generic['matrices'][0]
    assert row['native_matrix_id'] is row['name'] is None
    assert row['count_tokens']['A'][0]['raw_token'] == '1e-999'


@pytest.mark.parametrize('format,raw', [
    ('jaspar_json', b'{"matrix_id":"chosen.7","name":"literal","pfm":{"A":[1],"C":[2],"G":[3],"T":[4]}}'),
    ('jaspar_pfm', b'>chosen.7 literal\nA [1]\nC [2]\nG [3]\nT [4]\n'),
])
def test_native_representation_decoding_preserves_exact_supplied_identity(format, raw):
    decoded = tf.decode_tf_binding_inputs([input_file('m', 'matrix', format, raw)])
    row, = decoded['matrices']
    assert row['native_matrix_id'] == 'chosen.7' and row['name'] == 'literal'
    assert [[v['raw_token'] for v in row['count_tokens'][base]] for base in 'ACGT'] == [['1'], ['2'], ['3'], ['4']]


def test_explicit_original_occurrence_and_strand_order_is_the_only_native_population():
    inputs = [input_file('d', 'dna', 'fasta', b'>dup\nGATC\n>dup\nAAAA\n'),
        input_file('m', 'matrix', 'jaspar_pfm', b'>same\n1\n1\n1\n1\n>same\n2\n1\n1\n4\n')]
    decoded = tf.decode_tf_binding_inputs(inputs)
    scope = {'mode': 'explicit', 'requests': [{'sequence_input_id': 'd', 'sequence_record_ordinal_0based': 1,
        'matrix_input_id': 'm', 'matrix_record_ordinal_0based': 0, 'strands': ['-', '+']}]}
    specs = tf.resolve_tf_binding_scan_selection(decoded, scope)
    assert [v['strand'] for v in specs] == ['-', '+']
    assert {v['sequence_id'] for v in specs} == {decoded['sequences'][1]['sequence_id']}
    assert {v['matrix_occurrence_id'] for v in specs} == {decoded['matrices'][0]['matrix_occurrence_id']}
    with pytest.raises(ValueError, match='duplicate_selected_scan'):
        tf.resolve_tf_binding_scan_selection(decoded, {'mode': 'explicit', 'requests': scope['requests'] * 2})


@pytest.mark.parametrize('role,format', [('dna', 'fasta'), ('matrix', 'jaspar_pfm')])
def test_missing_capture_cannot_supply_present_bytes_but_complete_empty_is_distinct(role, format):
    for content in (b'', b'>x\nA\n>y\nC\n'):
        with pytest.raises(ValueError, match='missing'):
            tf.decode_tf_binding_inputs([input_file('x', role, format, content, state='missing')])
    assert tf.decode_tf_binding_inputs([input_file('x', role, format, b'')])['inputs'][0]['capture']['state'] == 'complete'
    assert tf.decode_tf_binding_inputs([input_file('x', role, format, None, state='missing')])['inputs'][0]['capture']['state'] == 'missing'


def test_independent_asymmetric_background_scores_coordinates_and_population_denominators():
    sheet = engineered_sheet()
    result = tf.calculate_tf_binding_components(sheet, selection(sheet))
    assert [(v['strand'], v['start_0based'], v['end_0based_exclusive'], v['score']['value']) for v in result['hits']] == [('-', 0, 2, 2.), ('+', 2, 4, 2.)]
    assert [(v['forward_sequence'], v['motif_oriented_sequence']) for v in result['hits']] == [('GA', 'TC'), ('TC', 'TC')]
    assert count(result, 'possible_strand_windows') == 6 and count(result, 'possible_unique_windows') == 3
    assert count(result, 'full_matched_scores') == count(result, 'model_eligible_candidate_sites') == 2
    assert all(v['relative_score']['value'] == 1 and v['relative_score']['state'] == 'available' for v in result['hits'])
    assert all(v['score']['location']['artifact']['source_ref'] == CAPTURE_SOURCE for v in result['hits'])
    assert all(v['relative_score']['location'] is None and v['relative_score']['operand_evidence']['score_operand_dtype'] == 'numpy_float32' for v in result['hits'])
    assert [v['value'] for v in (result['relative_normalizations'][0]['minimum'], result['relative_normalizations'][0]['maximum'], result['relative_normalizations'][0]['span'])] == [-1., 2., 3.]
    all_scores = tf.calculate_tf_binding_components(sheet, selection(sheet, -1.))
    assert [v['relative_score']['value'] for v in all_scores['hits'] if v['score']['value'] == 0] == [0.3333333432674408] * 2


def test_actual_selected_numpy_float32_array_comparison_differs_from_python_float_comparison():
    counts = {'A': [4], 'C': [2], 'G': [1], 'T': [1]}
    sheet = engineered_sheet(dna=b'AAA', counts=counts, pwm=[[.5], [.25], [.125], [.125]],
        pssm=[[1], [0], [-1], [-1]], rc=[[-1], [-1], [0], [1]], background=dict.fromkeys('ACGT', .25),
        bounds=(-1, 1), scores={'+': [1, 1, 1]}, strands=('+',))
    threshold = 1. + 2. ** -25
    assert float(np.float32(1)) < threshold
    low = tf.calculate_tf_binding_components(sheet, selection(sheet, threshold))
    high = tf.calculate_tf_binding_components(sheet, selection(sheet, 1. + 2. ** -23))
    assert count(low, 'full_matched_scores') == 3 and count(high, 'full_matched_scores') == 0
    assert low['numeric_authority']['threshold_binary64_hex'] == struct.pack('>d', threshold).hex()
    assert low['numeric_authority']['comparison'] == 'float32_ndarray_ge_python_float'


def test_nan_payload_negative_infinity_and_undefined_relative_are_retained():
    counts = {'A': [1], 'C': [0], 'G': [0], 'T': [0]}
    payload = struct.pack('<III', 0x40000000, 0x7fc12345, 0xff800000)
    sheet = engineered_sheet(dna=b'ANC', counts=counts, pwm=[[1], [0], [0], [0]],
        pssm=[[2], [-math.inf], [-math.inf], [-math.inf]], rc=[[-math.inf], [-math.inf], [-math.inf], [2]],
        background=dict.fromkeys('ACGT', .25), bounds=(-math.inf, 2), scores={'+': [2, math.nan, -math.inf]},
        strands=('+',), payload=payload)
    assert base64.b64decode(sheet['score_arrays'][0]['blob']['data_base64']) == payload
    result = tf.calculate_tf_binding_components(sheet, selection(sheet, 0.))
    assert count(result, 'possible_strand_windows') == count(result, 'observed_window_scores') == 3
    assert count(result, 'extended_scorable_scores') == 2 and count(result, 'finite_scores') == count(result, 'nan_scores') == 1
    assert [(v['start_0based'], v['end_0based_exclusive']) for v in result['hits']] == [(0, 1)]
    relative = result['hits'][0]['relative_score']
    assert relative['classification'] == 'nan' and relative['state'] == 'undefined' and relative['value'] is None
    assert relative['reason_code'] == 'nonfinite_relative_bounds'
    assert 'tf_binding_native_non_acgt_windows_are_nan' in {v['code'] for v in result['issues']}


@pytest.mark.parametrize('bounds,scores', [((0, math.inf), [2, 0, 1]), ((0, 0), [0, 0, 0])])
def test_ieee_relative_result_is_preserved_without_a_defined_scientific_normalization(bounds, scores):
    sheet = engineered_sheet(bounds=bounds, scores={'+': scores}, strands=('+',))
    result = tf.calculate_tf_binding_components(sheet, selection(sheet, -10.))
    assert all(v['relative_score']['state'] == 'undefined' for v in result['raw_threshold_matches'])
    if math.isinf(bounds[1]):
        assert all(v['relative_score']['classification'] == 'finite' and v['relative_score']['value'] == 0. for v in result['raw_threshold_matches'])
    assert result['relative_normalizations'][0]['scientific_state'] == 'undefined'


@pytest.mark.parametrize('kind', ['captured_prefix', 'native_partial', 'trailing', 'excess'])
def test_partial_trailing_and_excess_keep_bytes_and_do_not_manufacture_full_counts(kind):
    raw = struct.pack('<fff', 0, -1, 2)
    options = {'strands': ('+',), 'scores': {'+': [0, -1, 2]}}
    if kind == 'captured_prefix': options['capture_size'] = 6; expected = raw[:6]
    elif kind == 'native_partial': options.update(payload=raw[:6], scan_state='partial'); expected = raw[:6]
    elif kind == 'trailing': options['payload'] = raw + b'\xff'; expected = raw + b'\xff'
    else: options['payload'] = raw + struct.pack('<f', 7); expected = raw + struct.pack('<f', 7)
    sheet = engineered_sheet(**options)
    observed = sheet['score_arrays'][0]
    assert base64.b64decode(observed['blob']['data_base64']) == expected
    assert observed['coverage']['state'] == 'partial'
    assert observed['coverage']['expected_positions'] == observed['coverage']['declared_count'] == 3
    assert observed['coverage']['captured_complete_elements'] == len(expected) // 4
    assert observed['coverage']['trailing_bytes'] == len(expected) % 4
    assert observed['coverage']['excess_elements'] == (1 if kind == 'excess' else 0)
    result = tf.calculate_tf_binding_components(sheet, selection(sheet, -10.))
    assert count(result, 'full_matched_scores') is None
    assert count(result, 'observed_window_scores') == min(3, len(expected) // 4)


def test_complete_zero_possible_and_missing_scores_are_distinct():
    zero = engineered_sheet(dna=b'G', scores={'+': [], '-': []}, scan_state='zero_possible')
    missing = engineered_sheet(scan_state='unavailable', native_outcome='failed', model_failure='tf_binding_engineered_score_unavailable')
    a = tf.calculate_tf_binding_components(zero, selection(zero))
    b = tf.calculate_tf_binding_components(missing, selection(missing))
    assert a['status'] == 'complete' and count(a, 'possible_strand_windows') == count(a, 'full_matched_scores') == 0
    assert b['status'] == 'unavailable' and count(b, 'possible_strand_windows') == 6
    assert count(b, 'matched_observed_scores') is count(b, 'full_matched_scores') is None


def test_normalization_overflow_retains_raw_scores_but_withholds_candidate_conclusions():
    counts = dict.fromkeys('ACGT', [1e308])
    sheet = engineered_sheet(dna=b'AAA', counts=counts, pwm=[[0], [0], [0], [0]],
        pssm=[[-math.inf]] * 4, rc=[[-math.inf]] * 4, background=dict.fromkeys('ACGT', .25),
        bounds=(-math.inf, -math.inf), scores={'+': [-math.inf] * 3}, strands=('+',), native_outcome='failed')
    model = sheet['execution']['value']['models'][0]
    codes = {v['code'] for v in tf.tf_binding_model_normalization_issues(model)}
    assert codes == {'tf_binding_native_normalization_column_total_invalid', 'tf_binding_native_pwm_column_invalid'}
    result = tf.calculate_tf_binding_components(sheet, selection(sheet, 0.))
    assert count(result, 'negative_infinity_scores') == 3 and count(result, 'raw_full_threshold_matches') == 0
    assert count(result, 'full_matched_scores') is count(result, 'model_eligible_candidate_sites') is None
    assert result['hits'] == [] and result['status'] == 'partial'
    # The explicitly selected NumPy convention casts this finite threshold to
    # float32 -inf. Raw comparisons remain observable even for an invalid model.
    raw_matches = tf.calculate_tf_binding_components(sheet, selection(sheet, -1e300))
    assert count(raw_matches, 'raw_full_threshold_matches') == 3
    assert count(raw_matches, 'returned_raw_threshold_rows') == 3 and count(raw_matches, 'returned_candidate_rows') == 0
    assert all(not row['model_normalization_eligible'] for row in raw_matches['raw_threshold_matches'])
    assert raw_matches['hits'] == [] and raw_matches['execution'] == {'native_outcome': 'failed', 'returncode': None}


def test_unrepresentable_count_token_remains_original_and_model_unavailable():
    counts = dict.fromkeys('ACGT', [1])
    source = b'{"A":[1e-9999],"C":[1],"G":[1],"T":[1]}'
    sheet = engineered_sheet(dna=b'AAA', counts=counts, matrix_bytes=source, model_available=False, native_outcome='failed')
    assert sheet['matrices'][0]['count_tokens']['A'][0]['raw_token'] == '1e-9999'
    assert sheet['execution']['value']['models'][0]['buffers'] is None
    result = tf.calculate_tf_binding_components(sheet, selection(sheet))
    assert result['status'] == 'unavailable'
    assert 'tf_binding_count_float64_unrepresentable' in {row['code'] for row in result['issues']}


@pytest.mark.parametrize('fault', ['input_hash', 'token_location', 'native_source', 'score_hash', 'missing_blob', 'base64', 'parameter_join'])
def test_closed_sheet_rejects_custody_and_population_conflicts_without_scoring(fault):
    sheet = engineered_sheet()
    if fault == 'input_hash': sheet['inputs'][0]['artifact']['sha256'] = '0' * 64
    elif fault == 'token_location': sheet['matrices'][0]['rows'][0]['tokens'][0]['locator']['input_id'] = 'dna'
    elif fault == 'native_source': sheet['files'][1]['artifact']['source_ref'] = 'source_' + 'b' * 24
    elif fault == 'score_hash': sheet['score_arrays'][0]['blob']['sha256'] = '0' * 64
    elif fault == 'missing_blob': sheet['score_arrays'][0]['blob'] = None
    elif fault == 'base64': sheet['score_arrays'][0]['blob']['data_base64'] += '='
    else: sheet['invocation']['parameters']['background']['A'] = .4
    with pytest.raises(ValueError): tf.validate_tf_binding_sheet(sheet)


def test_saved_threshold_window_and_public_projection_need_no_input_io_or_bio_calls(monkeypatch):
    sheet = engineered_sheet(); original = deepcopy(sheet)
    import Bio.motifs.matrix
    def forbidden(*args, **kwargs):
        raise AssertionError('saved calculation attempted IO or Bio scoring')
    monkeypatch.setattr(Bio.motifs.matrix.PositionSpecificScoringMatrix, 'calculate', forbidden)
    monkeypatch.setattr(Bio.motifs.matrix.PositionSpecificScoringMatrix, 'search', forbidden)
    monkeypatch.setattr('builtins.open', forbidden)
    monkeypatch.setattr(Path, 'open', forbidden)
    first = tf.calculate_tf_binding_components(sheet, selection(sheet, 2., offset=1, limit=1))
    second = tf.calculate_tf_binding_components(sheet, selection(sheet, -1., offset=0, limit=2))
    public = tf.project_tf_binding_return(first, 'source_' + 'c' * 24)
    assert sheet == original and len(first['hits']) == 1 and count(second, 'full_matched_scores') == 6
    assert public['source_ref'] == 'source_' + 'c' * 24
    assert public['inputs'][0]['artifact_id'] == sheet['inputs'][0]['artifact']['artifact_ref']
    assert public['inputs'][0]['upstream_source_id'] is None
    text = json.dumps(public, allow_nan=False)
    assert 'data_base64' not in text and 'raw_artifact_ref' not in text and CAPTURE_SOURCE not in text
    assert 'operand_evidence' not in text and 'location' not in text


def test_saved_calculation_requires_the_original_numpy_promotion_version():
    sheet = engineered_sheet(numpy_version='unsupported-engineering-version')
    with pytest.raises(ValueError, match='numpy_promotion_version_unsupported'):
        tf.calculate_tf_binding_components(sheet, selection(sheet))


def test_issue_codes_are_not_double_prefixed():
    assert tf.tf_binding_issue('tf_binding_already_named')['code'] == 'tf_binding_already_named'


def test_saved_big_endian_scores_preserve_native_bytes_and_the_same_intervals():
    sheet = engineered_sheet(byte_order='big')
    result = tf.calculate_tf_binding_components(sheet, selection(sheet))
    assert [(row['strand'], row['start_0based'], row['end_0based_exclusive']) for row in result['hits']] == [('-', 0, 2), ('+', 2, 4)]
    assert all(row['score']['bits_hex'] == '40000000' and row['score']['byte_order'] == 'big' for row in result['hits'])
    assert result['relative_normalizations'][0]['minimum']['byte_order'] == 'little'


@pytest.mark.parametrize('fault', ['unknown_field', 'score_value', 'eligibility_bool', 'input_association', 'returned_count', 'relative_location', 'normalization_identity'])
def test_public_projection_rejects_altered_calculation_records_without_recalculating(fault):
    sheet = engineered_sheet()
    result = tf.calculate_tf_binding_components(sheet, selection(sheet))
    if fault == 'unknown_field': result['confidence'] = 1
    elif fault == 'score_value': result['raw_threshold_matches'][0]['score']['value'] = 1.
    elif fault == 'eligibility_bool': result['raw_threshold_matches'][0]['model_normalization_eligible'] = 1
    elif fault == 'input_association': result['inputs'][0]['artifact_id'] = 'artifact_' + '0' * 64
    elif fault == 'returned_count': result['totals']['returned_candidate_rows']['value'] = 0
    elif fault == 'relative_location': result['raw_threshold_matches'][0]['relative_score']['location'] = deepcopy(result['raw_threshold_matches'][0]['score']['location'])
    else: result['relative_normalizations'][0]['normalization_id'] = 'altered'
    with pytest.raises(ValueError): tf.project_tf_binding_return(result, 'source_' + 'c' * 24)


def test_saved_empty_selection_does_not_claim_an_observed_zero_possible_native_scan():
    sheet = engineered_sheet()
    result = tf.calculate_tf_binding_components(sheet, selection(sheet, scan_ids=[]))
    assert result['status'] == 'unavailable' and result['selected_scans'] == []
    assert count(result, 'possible_strand_windows') == 0 and count(result, 'matched_observed_scores') is None
    assert all(row['coverage']['state'] == 'complete' for row in result['available_scans'])


@pytest.mark.parametrize('threshold', [True, math.nan, math.inf, -math.inf, 10 ** 400])
def test_saved_raw_threshold_must_be_a_finite_python_float_operand(threshold):
    value = {'version': 'tf_binding_selection_v1', 'scan_ids': [], 'raw_threshold': threshold, 'offset': 0, 'limit': 0}
    with pytest.raises(ValueError, match='threshold_not_finite'): tf.validate_tf_binding_selection(value)


@pytest.mark.parametrize('content', [b'', b'\x00\x00\x00\x00'])
def test_missing_native_capture_cannot_carry_even_empty_present_bytes(content):
    invocation = {'version': 'tf_binding_invocation_v1', 'invocation_id': 'engineered-empty-population',
        'operation': tf.OPERATION, 'scan_selection': {'mode': 'explicit', 'requests': []},
        'parameters': {'background': BACKGROUND, 'pseudocounts': dict.fromkeys('ACGT', 0)}, 'software': []}
    file = captured_file('log', 'native_log', content, state='missing')
    with pytest.raises(ValueError, match='missing'):
        tf.populate_tf_binding_sheet(inputs=[], invocation=invocation, execution={'metadata_file_id': None, 'value': None}, files=[file])


def test_truncated_capture_conflicting_original_size_retains_both_extents_and_prefix():
    original = engineered_sheet(strands=('+',), capture_size=4)
    native = original['execution']['value']
    prefix = base64.b64decode(original['score_arrays'][0]['blob']['data_base64'])
    score_id = native['scans'][0]['score_file_id']
    files = [captured_file('metadata', 'native_result', json.dumps(native, allow_nan=False).encode()),
        captured_file(score_id, 'scores', prefix, state='truncated', original_size=13)]
    inputs = [input_file('dna', 'dna', 'raw_dna', b'GATC'),
        input_file('matrix', 'matrix', 'acgt_count_json', json.dumps(COUNTS).encode())]
    sheet = tf.populate_tf_binding_sheet(inputs=inputs, invocation=original['invocation'],
        execution=original['execution'], files=files)
    row, = sheet['score_arrays']
    assert row['coverage']['state'] == 'partial' and row['coverage']['captured_complete_elements'] == 1
    assert row['coverage']['declared_count'] == 3 and row['native_scan']['size_bytes'] == 12
    assert sheet['files'][1]['capture']['original_size_bytes'] == 13
    assert base64.b64decode(row['blob']['data_base64']) == prefix == struct.pack('<f', 0.)
    assert 'tf_binding_score_capture_original_size_conflict' in {issue['code'] for issue in row['issues']}
