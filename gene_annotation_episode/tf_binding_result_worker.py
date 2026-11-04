"""Pinned-byte TF result parsing and saved calculation, without native scoring.

The host owns all Source, input-admission and worker-lifecycle authority. This
Store-free adapter uses the one shared sheet/calculator/projection and writes
immutable private data files inside an existing owned worker directory.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from . import native_flux_balance_storage as storage
from .native_file_capture import _identity
from .tf_binding_measurements import (
    COMPONENTS_VERSION,
    SHEET_VERSION,
    calculate_tf_binding_components,
    populate_tf_binding_sheet,
    project_tf_binding_return,
    validate_tf_binding_invocation,
    validate_tf_binding_selection,
    validate_tf_binding_sheet,
)


_FIELDS = {'version', 'mode', 'inputs', 'invocation', 'execution', 'files',
           'saved', 'selection', 'projection_source_ref'}
_SELECTION_FIELDS = {'scope', 'scan_ids', 'raw_threshold', 'offset', 'limit'}


def _require(condition, code):
    if not condition:
        raise ValueError('tf_binding_result_' + code)


def _closed(value, fields, code):
    _require(type(value) is dict and set(value) == set(fields), code)


def _json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('utf-8') + b'\n'


def _selection(value, scan_ids=None):
    _closed(value, _SELECTION_FIELDS, 'selection_shape_invalid')
    _require(value['scope'] in ('all_retained_scans', 'selected_scan_ids'),
             'selection_scope_invalid')
    if value['scope'] == 'all_retained_scans':
        _require(value['scan_ids'] is None, 'all_scans_ids_must_be_null')
        ids = [] if scan_ids is None else scan_ids
    else:
        ids = value['scan_ids']
    return validate_tf_binding_selection({
        'version': 'tf_binding_selection_v1', 'scan_ids': ids,
        **{key: deepcopy(value[key]) for key in ('raw_threshold', 'offset', 'limit')},
    })


def _descriptor(row, *, captured):
    fields = ({'file_id', 'role', 'path', 'artifact', 'capture'} if captured else
              {'input_id', 'role', 'format', 'path', 'artifact', 'capture'})
    _closed(row, fields, 'file_descriptor_shape_invalid')
    _require(row['path'] is None or type(row['path']) is str
             and Path(row['path']).is_absolute(), 'file_path_invalid')
    identity = None
    if row['artifact'] is not None:
        artifact = row['artifact']
        _closed(artifact, {'raw_artifact_ref' if captured else 'artifact_ref',
                          'source_ref', 'sha256', 'size_bytes'}, 'artifact_shape_invalid')
        identity = _identity({
            'artifact_ref': artifact['raw_artifact_ref' if captured else 'artifact_ref'],
            'sha256': artifact['sha256'], 'size_bytes': artifact['size_bytes'],
            'format': 'tf_binding_captured_bytes' if captured else row['format'],
        })
    _require(captured or identity is not None, 'input_identity_required')
    capture = row['capture']
    _closed(capture, {'state', 'byte_start_0based', 'byte_end_0based_exclusive',
                      'original_size_bytes'}, 'capture_shape_invalid')
    _require(capture['state'] in ('complete', 'truncated', 'missing'), 'capture_state_invalid')
    _require((row['path'] is None) == (capture['state'] == 'missing'), 'missing_path_conflict')
    _require(row['path'] is None or identity is not None, 'file_identity_required')
    _require(not captured or (row['artifact'] is None) == (row['path'] is None),
             'missing_artifact_conflict')
    return deepcopy(row), identity


def _read(identity, path):
    raw = storage.read_bytes(path)
    _require(len(raw) == identity['size_bytes']
             and hashlib.sha256(raw).hexdigest() == identity['sha256'], 'file_identity_conflict')
    return raw


def _load_descriptors(rows):
    return [{key: deepcopy(value) for key, value in row.items() if key != 'path'}
            | {'content': None if row['path'] is None else _read(identity, row['path'])}
            for row, identity in rows]


def _request(value):
    _closed(value, _FIELDS, 'request_shape_invalid')
    _require(value['version'] == 'tf_binding_result_request_v1'
             and value['mode'] in ('parse', 'calculate_saved'), 'request_version_or_mode_invalid')
    source = value['projection_source_ref']
    _require(type(source) is str and source.startswith('source_') and len(source) > 7,
             'projection_source_ref_invalid')
    _selection(value['selection'])
    if value['mode'] == 'parse':
        _require(value['saved'] is None and type(value['inputs']) is list
                 and type(value['files']) is list, 'parse_request_invalid')
        validate_tf_binding_invocation(value['invocation'])
        _closed(value['execution'], {'metadata_file_id', 'value'}, 'execution_shape_invalid')
        inputs = [_descriptor(row, captured=False) for row in value['inputs']]
        files = [_descriptor(row, captured=True) for row in value['files']]
        return inputs, files, None
    _require(all(value[key] is None for key in ('inputs', 'invocation', 'execution', 'files')),
             'saved_request_invalid')
    _closed(value['saved'], {'file', 'path'}, 'saved_shape_invalid')
    saved = value['saved']
    identity = _identity(saved['file'])
    _require(identity['format'] == SHEET_VERSION and type(saved['path']) is str
             and Path(saved['path']).is_absolute(), 'saved_sheet_invalid')
    return None, None, (identity, saved['path'])


def _declaration(root, name, format):
    pin = storage.file_pin(root / name)
    return {'relative_path': name, 'format': format,
            'sha256': pin['sha256'], 'size_bytes': pin['size_bytes']}


def run_tf_binding_result(request, *, output_directory):
    """Parse captured native data or calculate once from a retained sheet.

    A valid parse sheet is written before calculation, so a later calculation
    failure cannot erase the retained evidence or imply an absent native attempt.
    Existing output files reject reentry; recovery belongs to the host owner.
    """
    inputs, files, saved = _request(request)
    root = storage.directory(Path(output_directory))
    names = ('sheet.json', 'components.json') if request['mode'] == 'parse' else ('components.json',)
    for name in names:
        path = storage.confined_file(root, name)
        _require(not path.exists(), 'output_already_exists')
    if request['mode'] == 'parse':
        sheet = populate_tf_binding_sheet(
            inputs=_load_descriptors(inputs), invocation=request['invocation'],
            execution=request['execution'], files=_load_descriptors(files))
    else:
        identity, path = saved
        sheet = validate_tf_binding_sheet(storage.decode_json(_read(identity, path)))
    selection = _selection(request['selection'],
                           [row['spec']['scan_id'] for row in sheet['score_arrays']])
    sheet_declaration = None
    if request['mode'] == 'parse':
        storage.immutable_bytes(root / 'sheet.json', _json_bytes(sheet))
        sheet_declaration = _declaration(root, 'sheet.json', SHEET_VERSION)
    components = calculate_tf_binding_components(sheet, selection)
    storage.immutable_bytes(root / 'components.json', _json_bytes(components))
    value = project_tf_binding_return(components, request['projection_source_ref'])
    return {'version': 'tf_binding_result_output_v1',
            'requested_selection': deepcopy(request['selection']), 'selection': selection,
            'value': value, 'sheet': sheet_declaration,
            'components': _declaration(root, 'components.json', COMPONENTS_VERSION)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request')
    parser.add_argument('result')
    args = parser.parse_args(argv)
    payload = storage.read_json(args.request)
    _closed(payload, {'operation', 'arguments'}, 'worker_payload_invalid')
    _require(payload['operation'] == 'tf_binding_result', 'worker_operation_invalid')
    _closed(payload['arguments'], {'request'}, 'worker_arguments_invalid')
    result_path = Path(args.result)
    _require(result_path.name not in ('sheet.json', 'components.json'), 'worker_result_path_conflict')
    _require(not result_path.exists() and not result_path.is_symlink(), 'worker_result_already_exists')
    try:
        result = run_tf_binding_result(payload['arguments']['request'], output_directory=result_path.parent)
    except ValueError as error:
        storage.immutable_bytes(result_path, _json_bytes({'code': str(error), 'exception_type': 'ValueError'}))
        return 2
    storage.immutable_bytes(result_path, _json_bytes(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
