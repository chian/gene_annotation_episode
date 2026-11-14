"""Complete byte custody for one caller-authenticated chromatin attempt.

The result host owns original-action authority, writer closure and persistence.
This helper only retains fixed output files and authenticates their declarations.
It does not read original input bindings, run native work or calculate scores.
"""
from __future__ import annotations
import hashlib
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.chromatin_interaction_contracts import validate_chromatin_record
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_chromatin_interaction_contracts import TABLE_ROLES, path_value, validate_chromatin_run_plan
_EMPTY_SHA256 = hashlib.sha256(b'').hexdigest()

def _require(condition):
    if not condition:
        raise ValueError('chromatin_invalid_native_capture')

def _identity(value, format_name):
    value = validate_chromatin_record('NativeFileIdentity', value)
    _require(value['format'] == format_name and value['artifact_ref'] == 'artifact_' + value['sha256'])
    _require((value['size_bytes'] == 0) == (value['sha256'] == _EMPTY_SHA256))
    return value

def _declaration(value, specification):
    value = validate_chromatin_record('NativeFileDeclaration', value)
    _require(all((value[k] == specification[k] for k in ('relative_path', 'format'))))
    path_value(value['relative_path'], absolute=False)
    if value['state'] == 'present':
        _require((value['size_bytes'] == 0) == (value['sha256'] == _EMPTY_SHA256))
    return value

def _captured(value, specification):
    value = validate_chromatin_record('NativeFileCapture', value)
    declaration = _declaration(value['declared'], specification)
    actual = value['observed']
    if actual is not None:
        _identity(actual, specification['format'])
    equal = actual is not None and all((actual[k] == declaration[k] for k in ('sha256', 'size_bytes', 'format')))
    _require(value['outcome'] == 'verified' and declaration['state'] == 'present' and equal and (value['failure'] is None) or (value['outcome'] == 'declared_absent' and declaration['state'] == 'absent' and (actual is None) and (value['failure'] is None)) or (value['outcome'] == 'unavailable' and declaration['state'] == 'present' and (actual is None) and (value['failure'] == 'capture_file_unavailable')) or (value['outcome'] == 'digest_mismatch' and declaration['state'] == 'present' and (actual is not None) and (not equal) and (value['failure'] == 'capture_file_digest_mismatch')))

def _retained(value, format_name):
    value = validate_chromatin_record('RetainedFile', value)
    identity = _identity(value['file'], format_name)
    path = path_value(value['path'], absolute=True)
    _require(path.name == identity['sha256'] and path.parent.name == identity['sha256'][:2] and (path.parent.parent.name == 'artifacts'))
    return path

def _input_key(specification, plan):
    request = plan['requested_job']['native_chromatin_interactions']['request']
    if specification['role'] == 'original_contact':
        return request['contact']['input_key']
    if specification['role'] == 'original_elements' and request['elements'] is not None:
        return request['elements']['input_key']
    return None

def validate_chromatin_native_capture(value: object, *, original_plan: dict) -> dict:
    """Validate detached custody data without filesystem or lifecycle access.

    Manifest bodies are not duplicated in this transport record. Capture checks
    them against the original plan; the retained worker checks them again. This
    pure validator cannot authenticate receipt authority or retained bytes.
    """
    plan = validate_chromatin_run_plan(original_plan)
    value = validate_chromatin_record('NativeCapture', value)
    _require(value['original_plan'] == plan)
    state = value['driver_state']
    _require((state == 'sealed_bundle') == (value['bundle'] is not None))
    specifications = plan['outputs']
    _require([row['specification'] for row in value['files']] == specifications[:-1])
    retained = []
    if value['bundle'] is not None:
        _retained(value['bundle'], specifications[-1]['format'])
        retained.append(value['bundle'])
    for row in value['files']:
        specification, capture = (row['specification'], row['capture'])
        source = row['declaration_source']
        _require((source == 'bundle') == (state == 'sealed_bundle'))
        if source == 'none':
            _require(capture is None)
        else:
            _require(capture is not None)
            _captured(capture, specification)
            _require(source != 'population' or specification['role'] in TABLE_ROLES)
        if row['retained'] is not None:
            _retained(row['retained'], specification['format'])
            _require(capture is None or row['retained']['file'] == capture['observed'])
            retained.append(row['retained'])
        if capture is not None:
            _require((capture['observed'] is not None) == (row['retained'] is not None))
    if state == 'not_started':
        _require(all((row['capture'] is None and row['retained'] is None for row in value['files'])))
    paths, identities = ({}, {})
    for row in retained:
        path = path_value(row['path'], absolute=True)
        identity = tuple((row['file'][k] for k in ('artifact_ref', 'sha256', 'size_bytes')))
        _require(identity not in identities or identities[identity] == path)
        for previous, content in paths.items():
            _require(path not in previous.parents and previous not in path.parents and (path != previous or identity == content))
        paths[path], identities[identity] = (identity, path)
    request = plan['requested_job']['native_chromatin_interactions']['request']
    inputs = {row['input_key'] for row in plan['requested_job']['native_chromatin_interactions']['input_bindings']}
    populations = {row['population_key'] for row in request['populations']}
    elements = {row['element_key'] for row in request['elements']['assignments']} if request['elements'] else set()
    for problem in value['failures']:
        _require(problem['input_key'] is None or problem['input_key'] in inputs)
        _require(problem['population_key'] is None or problem['population_key'] in populations)
        _require(problem['element_key'] is None or problem['element_key'] in elements)
        _require(problem['pair_key'] is None and problem['locator'] is None)
        field = problem['field_path']
        _require(type(field) is str)
        parts = field.split('/')
        if len(parts) >= 2 and parts[1] == 'bundle':
            specification = specifications[-1]
        else:
            _require(len(parts) >= 3 and parts[1] == 'files' and parts[2].isascii() and parts[2].isdigit())
            index = int(parts[2])
            _require(str(index) == parts[2] and index < len(value['files']))
            specification = specifications[index]
        _require(problem['population_key'] == specification['population_key'] and problem['input_key'] == _input_key(specification, plan))
    return value
