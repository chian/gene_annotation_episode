"""One caller-selected ordinary sequence reservation and non-cancelling observation.

The caller authenticates and locks its selected action before this port. Frozen
operand metadata are supplied facts, never authority created here. This module
resolves no subjects or Files, normalizes no symbols, performs no scientific
calculation, and publishes no Source, receipt, grant or episode.
"""
import hashlib
import json
from pathlib import Path
from .execution_contracts import canonical
from . import molecular_sequence_driver as driver
from gene_annotation_episode.episodic_workflow.root.a107.library import molecular_deployment_contracts as source
from .molecular_sequence_execution_contracts import BUNDLE_FILENAME, OUTPUT_DIRECTORY, REQUEST_RELATIVE, molecular_sequence_adapter_argv, validate_molecular_sequence_attempt_bundle
from . import molecular_sequence_result_contracts as contracts
from .native_file_capture import _declaration, _identity
from .native_flux_balance_storage import read_bytes
OPERATION = 'annotate_open_reading_frames'
ENVIRONMENT_SELECTION = {'version': 'molecular_sequence_execution_selection_v1', 'environment_realization': 'operation_scoped_tmp_and_cache_v1'}

def _require(condition, code):
    if not condition:
        raise ValueError('ordinary_orf_' + code)

def _closed(value, fields, code):
    _require(type(value) is dict and set(value) == set(fields), code)

def _copy(value):
    return json.loads(canonical(value))

def _read_json(path):
    return driver._json(read_bytes(path))

def _profile(operation):
    return contracts.ordinary_molecular_sequence_profile(operation)

def _code(profile, suffix):
    return profile['operand_version'].removesuffix('_sequence_operand_v1') + '_' + suffix

def _deployment(operation, value):
    profile = _profile(operation)
    source._deployment(value, version=profile['deployment_version'], source_sha256=source._SOURCE_PROFILES[profile['native_source']]['sha256'])

def _operand(value, subject_ref, *, operation=OPERATION):
    profile = _profile(operation)
    if operation == 'align_sequences':
        from gene_annotation_episode.episodic_workflow.root.a107.library.primer_placement_result_contracts import validate_operands
        return validate_operands(value, subject_ref)
    value = _copy(value)
    _closed(value, ('version', 'subject', 'sequence', 'parent_mapping', 'mapping_failure', 'input_file', 'associations', 'footprint'), 'operand_fields_required')
    _require(value['version'] == profile['operand_version'] and type(value['subject']) is dict and (value['subject'].get('id') == subject_ref) and (type(value['sequence']) is str) and (type(value['associations']) is dict) and (type(value['footprint']) is list), 'operand_invalid')
    _require(value['parent_mapping'] is None or type(value['parent_mapping']) is dict, 'operand_mapping_invalid')
    _require(value['mapping_failure'] is None or value['mapping_failure'] == {'code': 'subregion_mapping_unavailable'}, 'operand_mapping_failure_invalid')
    _require((value['parent_mapping'] is None) == (value['mapping_failure'] is not None), 'operand_mapping_failure_conflict')
    file = _identity(value['input_file'])
    try:
        raw = value['sequence'].encode('ascii')
    except UnicodeEncodeError as error:
        raise ValueError(_code(profile, 'operand_sequence_not_ascii')) from error
    _require(file['format'] == 'ascii_sequence' and file['size_bytes'] == len(raw) and (file['sha256'] == hashlib.sha256(raw).hexdigest()), 'operand_file_identity_conflict')
    return value

def _native_arguments(operation, arguments, operand):
    profile = _profile(operation)
    if operation == 'align_sequences':
        from gene_annotation_episode.episodic_workflow.root.a107.library.primer_placement_result_contracts import native_arguments
        return native_arguments(arguments, operand)
    return dict(sequence=operand['sequence'], **{key: arguments[key] for key in profile['native_argument_names']})

def _scientific_context(operation, arguments, operand):
    _profile(operation)
    if operation == 'align_sequences':
        from gene_annotation_episode.episodic_workflow.root.a107.library.primer_placement_result_contracts import scientific_context
        return scientific_context(arguments, operand)
    return dict(subject_ref=arguments['subject_ref'], parent_mapping=operand['parent_mapping']) if operation == OPERATION else dict(input_ref=arguments['subject_ref'], input_mapping=operand['parent_mapping'])

def _native_request(plan, paths):
    return {'command': molecular_sequence_adapter_argv(plan), 'cwd': str(Path(plan['identity']['execution_id']).parent), 'file_bytes': plan['policy']['scratch_bytes'], 'ready_path': paths['ready'], 'release_path': paths['release'], 'result_path': paths['result'], 'stdin_path': None, 'env': plan['selected_environment']}

def _metadata_issue(code, error=None, role=None):
    return dict(code=code, role=role, exception_type=None if error is None else type(error).__name__, message=None if error is None else str(error))

def _result_metadata(plan, *, read_json=None):
    """Read metadata independently; never verify or discard all output bytes."""
    read = _read_json if read_json is None else read_json
    profile = _profile(plan['selection']['operation'])
    root = Path(plan['attempt_directory'])
    issues, bundle, declaration = ([], None, None)
    declarations = {}
    try:
        bundle = validate_molecular_sequence_attempt_bundle(read(root / BUNDLE_FILENAME), plan=plan)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as error:
        issues.append(_metadata_issue('bundle_metadata_unavailable' if isinstance(error, FileNotFoundError) else 'bundle_metadata_invalid', error))
    try:
        value = read(root / OUTPUT_DIRECTORY / 'declaration.json')
        _closed(value, ('version', 'mode', 'operation', 'request_file', 'request_file_pin_verified', 'attempt_identity', 'native_call_state', 'native_failure', 'driver_failure', 'files', 'qualification'), 'declaration_fields_invalid')
        expected_request = plan['selection']['driver_request']
        expected_file = {**plan['selection']['request_file'], 'path': str(root / REQUEST_RELATIVE)}
        _require(value['version'] == driver.DECLARATION_VERSION and value['mode'] == 'native' and (value['operation'] == profile['operation']) and (value['request_file'] == expected_file) and (value['request_file_pin_verified'] is True) and (value['attempt_identity'] == expected_request['attempt_identity']) and (type(value['files']) is dict), 'declaration_selection_conflict')
        declaration = value
        if set(value['files']) != {'capture', 'sheet', 'components'}:
            issues.append(_metadata_issue('declaration_role_set_invalid'))
        for role in ('capture', 'sheet', 'components'):
            try:
                selected = _declaration(value['files'].get(role))
                _require(selected['relative_path'] == role + '.json' and selected['format'] == 'json', 'declaration_role_path_conflict')
                declarations[role] = selected
            except (ValueError, TypeError, KeyError) as error:
                issues.append(_metadata_issue('declaration_role_invalid', error, role))
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as error:
        issues.append(_metadata_issue('declaration_metadata_unavailable' if isinstance(error, FileNotFoundError) else 'declaration_metadata_invalid', error))
    return (bundle, declaration, declarations, issues)
