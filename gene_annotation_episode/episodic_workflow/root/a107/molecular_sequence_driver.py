"""Finite private molecular execution and saved-sheet calculation.

The selected request is read once under an explicit byte pin. The native helper
owns its call receipt; the existing scientific readers own their sheets and
calculations. This writer has no Store, launcher, retry or investigation loop.
Its declaration records output bytes, not authenticated producing-attempt
custody. A CLI success means processing returned, not scientific validity.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path, PurePosixPath
import re
REQUEST_VERSION = 'molecular_sequence_driver_request_v1'
DECLARATION_VERSION = 'molecular_sequence_driver_declaration_v1'
REQUEST_VERSION_V2 = 'molecular_sequence_driver_request_v2'
_PROTEASE = 'analyze_protease_kinetics'
_ORF = 'annotate_open_reading_frames'
_PLACEMENT = 'align_sequences'
_GLYCO = {'find_n_glycosylation_motifs', 'predict_o_glycosylation_hotspots'}
_OPERATIONS = {_ORF, _PLACEMENT, *_GLYCO}
_IDENTITY_FIELDS = {'run_id', 'episode_id', 'resource_id', 'operation_key', 'execution_id'}

def _require(condition, message):
    if not condition:
        raise ValueError('molecular_sequence_driver_' + message)

def _closed(value, fields, name):
    _require(type(value) is dict and set(value) == set(fields), name + '_fields_required')

def _path(value):
    _require(type(value) is str and value and (not any((c in value for c in '\x00\n\r\\'))), 'canonical_absolute_path_required')
    path = PurePosixPath(value)
    _require(path.is_absolute() and str(path) == value and ('..' not in path.parts) and (value != '/'), 'canonical_absolute_path_required')
    return Path(value)

def _file_pin(value):
    _closed(value, ('path', 'sha256', 'size_bytes'), 'file_pin')
    _path(value['path'])
    _require(type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']) and (type(value['size_bytes']) is int) and (value['size_bytes'] >= 0), 'file_pin_required')
    return deepcopy(value)

def _json(raw):

    def fields(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, 'duplicate_json_field')
            result[key] = value
        return result

    def nonfinite(token):
        raise ValueError('molecular_sequence_driver_nonfinite_json:' + token)
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=fields, parse_constant=nonfinite)
    json.dumps(value, allow_nan=False)
    return value

def _reference(value):
    return value is None or (type(value) is str and bool(value))

def _mapping(value):
    return value is None or type(value) is dict

def _request(value):
    if type(value) is dict and value.get('version') == REQUEST_VERSION_V2:
        return _request_v2(value)
    _closed(value, ('version', 'mode', 'attempt_identity', 'selection', 'scientific_context'), 'request')
    _require(value['version'] == REQUEST_VERSION and value['mode'] in ('native', 'saved_sheet'), 'request_version_and_mode_required')
    _closed(value['attempt_identity'], _IDENTITY_FIELDS, 'attempt_identity')
    _require(all((type(v) is str and v for v in value['attempt_identity'].values())), 'explicit_host_attempt_identity_required')
    selection = value['selection']
    _require(type(selection) is dict, 'selection_required')
    operation = selection.get('operation')
    _require(type(operation) is str and operation in _OPERATIONS, 'operation_required')
    context = value['scientific_context']
    if value['mode'] == 'saved_sheet':
        _closed(selection, ('operation', 'sheet_file'), 'saved_selection')
        _file_pin(selection['sheet_file'])
        _require(context is None, 'saved_sheet_owns_scientific_operands')
    else:
        _closed(selection, ('version', 'operation', 'arguments', 'deployment'), 'native_selection')
        if operation == _ORF:
            _closed(context, ('subject_ref', 'parent_mapping'), 'orf_context')
            _require(_reference(context['subject_ref']) and _mapping(context['parent_mapping']), 'orf_context_required')
        elif operation == _PLACEMENT:
            _closed(context, ('target_ref', 'primer_refs', 'target_mapping', 'primer_mappings'), 'placement_context')
            refs, mappings = (context['primer_refs'], context['primer_mappings'])
            _require(_reference(context['target_ref']) and _mapping(context['target_mapping']) and (refs is None or (type(refs) is list and all((_reference(v) for v in refs)))) and (mappings is None or (type(mappings) is list and all((_mapping(v) for v in mappings)))), 'placement_context_required')
        else:
            _closed(context, ('input_ref', 'input_mapping'), 'glyco_context')
            _require(_reference(context['input_ref']) and _mapping(context['input_mapping']), 'glyco_context_required')
    return operation

def _request_v2(value):
    _closed(value, ('version', 'mode', 'attempt_identity', 'selection', 'scientific_context'), 'request_v2')
    _require(value['version'] == REQUEST_VERSION_V2 and value['mode'] in ('native', 'saved_sheet'), 'request_version_and_mode_required')
    _closed(value['attempt_identity'], _IDENTITY_FIELDS, 'attempt_identity')
    _require(all((type(v) is str and v for v in value['attempt_identity'].values())), 'explicit_host_attempt_identity_required')
    selection = value['selection']
    _require(type(selection) is dict and selection.get('operation') == _PROTEASE, 'v2_protease_operation_required')
    if value['mode'] == 'saved_sheet':
        _closed(selection, ('operation', 'sheet_file'), 'saved_selection')
        _file_pin(selection['sheet_file'])
        _require(value['scientific_context'] is None, 'saved_sheet_owns_scientific_operands')
    else:
        _closed(selection, ('version', 'operation', 'arguments', 'deployment', 'output_workspace', 'environment'), 'native_v3_selection')
        _require(selection['version'] == 'molecular_sequence_request_v3', 'native_v3_selection_required')
        _closed(value['scientific_context'], ('assay_context',), 'protease_context')
    return _PROTEASE
