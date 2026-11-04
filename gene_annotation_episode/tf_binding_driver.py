"""Native Biopython score production, without selection of hits or publication.

The caller owns admission, execution policy and capture. This module reads pinned
inputs once, uses the shared occurrence decoder, and retains the selected native
float32 arrays. A successful transport of this manifest is not a process-exit or
scientific-success assertion.
"""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import os
from pathlib import Path
import sys

from . import native_flux_balance_storage as storage
from .tf_binding_measurements import (
    decode_tf_binding_inputs,
    resolve_tf_binding_scan_selection,
    tf_binding_issue,
    tf_binding_model_normalization_issues,
    validate_tf_binding_invocation,
    validate_tf_binding_native_value,
)


_INPUT_KEYS = {'input_id', 'role', 'format', 'path', 'artifact', 'capture'}
_ARTIFACT_KEYS = {'artifact_ref', 'source_ref', 'sha256', 'size_bytes'}
_REQUEST_KEYS = {'version', 'invocation', 'inputs'}
_BASES = 'ACGT'


def _require(condition, code):
    if not condition:
        raise ValueError('tf_binding_' + code)


def _json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('utf-8') + b'\n'


def _request(value):
    """Check the private path envelope; scientific fields have one shared owner."""
    _require(type(value) is dict and set(value) == _REQUEST_KEYS,
             'native_request_shape_invalid')
    _require(value['version'] == 'tf_binding_native_request_v1',
             'native_request_version_invalid')
    invocation = validate_tf_binding_invocation(value['invocation'])
    _require(type(value['inputs']) is list and bool(value['inputs']),
             'native_inputs_invalid')
    seen, inputs = set(), []
    for row in value['inputs']:
        _require(type(row) is dict and set(row) == _INPUT_KEYS,
                 'native_input_shape_invalid')
        _require(type(row['input_id']) is str and row['input_id']
                 and row['input_id'] not in seen, 'native_input_id_invalid')
        seen.add(row['input_id'])
        artifact = row['artifact']
        _require(type(artifact) is dict and set(artifact) == _ARTIFACT_KEYS,
                 'native_input_artifact_invalid')
        _require(type(artifact['size_bytes']) is int and artifact['size_bytes'] >= 0,
                 'native_input_size_invalid')
        _require(type(artifact['sha256']) is str and len(artifact['sha256']) == 64
                 and all(c in '0123456789abcdef' for c in artifact['sha256']),
                 'native_input_digest_invalid')
        _require(type(row['path']) is str and Path(row['path']).is_absolute(),
                 'native_input_path_invalid')
        inputs.append(deepcopy(row))
    return invocation, inputs


def _pinned_inputs(rows):
    inputs = []
    for row in rows:
        raw = storage.read_bytes(row['path'])
        _require(len(raw) == row['artifact']['size_bytes']
                 and hashlib.sha256(raw).hexdigest() == row['artifact']['sha256'],
                 'native_input_bytes_changed')
        inputs.append({key: deepcopy(value) for key, value in row.items()
                       if key != 'path'} | {'content': raw})
    return inputs


def _reserve_output(path):
    path = Path(path)
    _require(path.is_absolute() and path.name not in ('', '.', '..'),
             'native_output_path_invalid')
    # The caller supplies an existing owned parent. Existing attempts cannot be
    # silently reused or rescored by this native producer.
    with storage._directory_fd(path.parent) as parent:
        os.mkdir(path.name, mode=0o700, dir_fd=parent)
        os.fsync(parent)
    return storage.directory(path)


def _write_payload(descriptor, raw):
    view = memoryview(raw)
    while view:
        count = os.write(descriptor, view)
        if count <= 0:
            raise OSError('tf_binding_native_write_made_no_progress')
        view = view[count:]


def _retain_bytes(output, relative_path, raw, *, file_id, role, format):
    """Keep a failed write's real prefix at its declared path, including tails."""
    path = output / relative_path
    error = None
    descriptor = None
    created = False
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                             | os.O_NOFOLLOW, 0o600)
        created = True
        _write_payload(descriptor, raw)
    except OSError:
        error = 'tf_binding_native_file_write_failed'
    finally:
        if descriptor is not None:
            try:
                os.fsync(descriptor)
                os.fchmod(descriptor, 0o444)
            except OSError:
                error = 'tf_binding_native_file_write_failed'
            finally:
                try:
                    os.close(descriptor)
                except OSError:
                    error = 'tf_binding_native_file_write_failed'
    if not created:
        return None, error or 'tf_binding_native_file_unavailable'
    try:
        with storage._directory_fd(output) as directory:
            os.fsync(directory)
    except OSError:
        error = 'tf_binding_native_file_write_failed'
    try:
        pin = storage.file_pin(path)
    except (OSError, ValueError):
        return None, error or 'tf_binding_native_file_unavailable'
    complete = pin['size_bytes'] == len(raw) and pin['sha256'] == hashlib.sha256(raw).hexdigest()
    if not complete:
        error = error or 'tf_binding_native_file_write_failed'
    return {'file_id': file_id, 'role': role, 'relative_path': relative_path,
            'format': format, 'sha256': pin['sha256'],
            'size_bytes': pin['size_bytes']}, error


def _buffer(array, np):
    array = np.ascontiguousarray(array, dtype=np.float64)
    raw = array.tobytes(order='C')
    return {'dtype': 'float64', 'byte_order': sys.byteorder,
            'shape': list(array.shape),
            'data_base64': base64.b64encode(raw).decode('ascii'),
            'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}


def _count_values(matrix):
    values = {}
    for base in _BASES:
        values[base] = []
        for cell in matrix['count_tokens'][base]:
            token = cell['raw_token']
            try:
                exact = Decimal(token)
                native = float(token)
            except (InvalidOperation, OverflowError, ValueError):
                raise ValueError('tf_binding_count_float64_unrepresentable') from None
            _require(exact.is_finite() and exact >= 0 and math.isfinite(native)
                     and (native != 0 or exact == 0),
                     'count_float64_unrepresentable')
            values[base].append(native)
    return values


def _model(matrix, parameters, motifs, np):
    record = {'model_id': matrix['model_id'],
              'matrix_occurrence_id': matrix['matrix_occurrence_id'],
              'state': 'unavailable', 'length': matrix['length'],
              'reverse_convention': 'computed_pssm_reverse_complement_v1',
              'buffers': None, 'failure_code': None}
    if matrix['state'] != 'available':
        record['failure_code'] = 'tf_binding_matrix_unavailable'
        return record, None
    try:
        counts = _count_values(matrix)
        motif = motifs.Motif(alphabet=_BASES, counts=counts)
        motif.pseudocounts = parameters['pseudocounts']
        motif.background = parameters['background']
        pwm = motif.pwm
        pssm = pwm.log_odds(motif.background)
        reverse = pssm.reverse_complement()
        record['buffers'] = {
            'counts': _buffer([motif.counts[b] for b in _BASES], np),
            'background': _buffer([motif.background[b] for b in _BASES], np),
            'pseudocounts': _buffer([motif.pseudocounts[b] for b in _BASES], np),
            'pwm': _buffer([pwm[b] for b in _BASES], np),
            'pssm': _buffer([pssm[b] for b in _BASES], np),
            'rc_pssm': _buffer([reverse[b] for b in _BASES], np),
            'bounds_plus': _buffer([pssm.min, pssm.max], np),
            'bounds_minus': _buffer([reverse.min, reverse.max], np),
        }
        record['state'] = 'available'
        return record, {'+': pssm, '-': reverse}
    except Exception as exc:
        record['buffers'] = None
        record['failure_code'] = ('tf_binding_count_float64_unrepresentable'
                                  if str(exc) == 'tf_binding_count_float64_unrepresentable'
                                  else 'tf_binding_native_model_raised')
        return record, None


def _scan(specification, sequence, matrices, output, ordinal, np):
    scan = deepcopy(specification) | {
        'state': 'unavailable', 'score_file_id': None,
        'dtype': 'float32', 'byte_order': sys.byteorder,
        'declared_count': None, 'sha256': None, 'size_bytes': None,
        'failure_code': None,
    }
    call = {'scan_id': scan['scan_id'], 'state': 'not_called', 'failure_code': None}
    if sequence['state'] != 'available' or matrices is None or scan['possible_positions'] is None:
        scan['failure_code'] = 'tf_binding_native_scan_inputs_unavailable'
        call['failure_code'] = scan['failure_code']
        return scan, call, None
    if scan['possible_positions'] == 0:
        raw, count = b'', 0
    else:
        try:
            scores = matrices[scan['strand']].calculate(sequence['symbols'])
        except Exception:
            call['state'] = 'raised'
            call['failure_code'] = scan['failure_code'] = 'tf_binding_native_score_raised'
            return scan, call, None
        call['state'] = 'returned'
        try:
            array = np.asarray(scores)
            _require(array.dtype == np.dtype('float32') and array.ndim in (0, 1),
                     'native_score_array_invalid')
            array = array.reshape(-1)
            raw, count = array.tobytes(order='C'), int(array.size)
        except Exception:
            call['failure_code'] = scan['failure_code'] = 'tf_binding_native_score_array_invalid'
            return scan, call, None
    scan['declared_count'] = count
    declaration, error = _retain_bytes(
        output, f'scores-{ordinal:06d}.f32', raw,
        file_id=scan['scan_id'], role='scores', format='tf_binding_scores_float32')
    if declaration is None:
        scan['failure_code'] = error
        return scan, call, None
    scan.update(score_file_id=declaration['file_id'], sha256=declaration['sha256'],
                size_bytes=declaration['size_bytes'])
    if error is not None:
        scan['state'], scan['failure_code'] = 'partial', 'tf_binding_score_write_failed'
    elif count != scan['possible_positions']:
        scan['state'], scan['failure_code'] = 'partial', 'tf_binding_native_score_count_conflict'
    else:
        scan['state'] = 'zero_possible' if count == 0 else 'complete'
    return scan, call, declaration


def run_tf_binding_native(request, *, output_directory):
    """Produce native arrays for the explicitly selected occurrence population.

    ``output_directory`` must not exist; its owned parent must already exist.
    This one-attempt boundary intentionally cannot recover by rerunning scoring.
    Returned file paths are relative to this directory, without Source custody.
    """
    invocation, input_rows = _request(request)
    inputs = _pinned_inputs(input_rows)
    decoded = decode_tf_binding_inputs(inputs)
    specifications = resolve_tf_binding_scan_selection(decoded, invocation['scan_selection'])
    output = _reserve_output(output_directory)
    import Bio
    from Bio import motifs
    import numpy as np

    matrices = {row['matrix_occurrence_id']: row for row in decoded['matrices']}
    sequences = {row['sequence_id']: row for row in decoded['sequences']}
    models, native_models, files, calls, scans = [], {}, [], [], []
    issues, failures, seen_sequences = deepcopy(decoded['issues']), [], set()
    normalization_invalid = False
    if not specifications:
        issues.append(tf_binding_issue('selected_population_empty'))
    for specification in specifications:
        model_id = specification['model_id']
        if model_id not in native_models:
            matrix = matrices[specification['matrix_occurrence_id']]
            issues.extend(deepcopy(matrix['issues']))
            model, native = _model(matrix, invocation['parameters'], motifs, np)
            native_models[model_id] = native
            models.append(model)
            if model['state'] == 'available':
                normalization_issues = tf_binding_model_normalization_issues(
                    model, path=f'/models/{len(models) - 1}')
                issues.extend(normalization_issues)
                normalization_invalid |= bool(normalization_issues)
            if model['failure_code']:
                issues.append(tf_binding_issue(
                    model['failure_code'].removeprefix('tf_binding_'),
                    path=f'/models/{len(models) - 1}', severity='error'))
        sequence = sequences[specification['sequence_id']]
        if sequence['sequence_id'] not in seen_sequences:
            seen_sequences.add(sequence['sequence_id'])
            issues.extend(deepcopy(sequence['issues']))
        scan, call, declaration = _scan(
            specification, sequence,
            native_models[model_id], output, len(scans), np)
        scans.append(scan)
        calls.append(call)
        if declaration is not None:
            files.append(declaration)
        if scan['failure_code']:
            issues.append(tf_binding_issue(
                scan['failure_code'].removeprefix('tf_binding_'),
                path=f'/scans/{len(scans) - 1}', severity='error'))
    success = (not normalization_invalid
               and all(scan['state'] in ('complete', 'zero_possible') for scan in scans))
    value = validate_tf_binding_native_value({
        'version': 'tf_binding_native_result_v1',
        'invocation_id': invocation['invocation_id'],
        'operation': invocation['operation'],
        'biopython_version': Bio.__version__, 'numpy_version': np.__version__,
        'numeric_convention': 'numpy_array_compare_pythonfloat_scalar_relative_v1',
        'scan_selection': deepcopy(invocation['scan_selection']),
        'parameters': deepcopy(invocation['parameters']),
        'input_identities': [{key: row['artifact'][key] for key in (
            'artifact_ref', 'sha256', 'size_bytes')} | {'input_id': row['input_id']}
            for row in input_rows],
        'outcome': ('not_run' if not scans else 'succeeded' if success else 'failed'),
        'returncode': None, 'models': models, 'scans': scans, 'issues': issues,
    })
    declaration, error = _retain_bytes(
        output, 'native-result.json', _json_bytes(value),
        file_id='native-result', role='native_result', format='tf_binding_native_result_json')
    if declaration is not None:
        files.append(declaration)
    if error is not None:
        failures.append({'code': error, 'path': '/files/native-result'})
    return {'version': 'tf_binding_native_manifest_v1', 'value': value,
            'files': files, 'calls': calls, 'failures': failures}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request')
    parser.add_argument('result')
    args = parser.parse_args(argv)
    envelope = storage.read_json(args.request)
    _require(type(envelope) is dict and set(envelope) == {'operation', 'arguments'}
             and envelope['operation'] == 'tf_binding_native'
             and type(envelope['arguments']) is dict
             and set(envelope['arguments']) == {'request'}, 'worker_request_invalid')
    result_path = Path(args.result)
    manifest = run_tf_binding_native(envelope['arguments']['request'],
                                    output_directory=result_path.parent / 'tf-binding-native')
    storage.immutable_bytes(result_path, _json_bytes(manifest))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
