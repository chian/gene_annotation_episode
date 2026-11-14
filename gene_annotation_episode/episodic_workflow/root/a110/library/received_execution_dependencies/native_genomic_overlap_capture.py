from __future__ import annotations
import hashlib
from pathlib import PurePosixPath
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import digest
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_genomic_overlap_contracts import _finite_json_copy, validate_genomic_overlap_record
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_genomic_overlap_contracts import genomic_overlap_output_files, validate_genomic_overlap_run_plan
_VERSION = 'genomic_overlap_native_capture_v1'
_FIELDS = {'version', 'original_plan_sha256', 'source_action_receipt_ref', 'writer_closure_receipt_ref', 'driver_started', 'driver_state', 'batch_file', 'batch', 'files', 'failures'}
_FILE_FIELDS = {'specification', 'declaration_source', 'capture', 'retained'}
_EMPTY_SHA = hashlib.sha256(b'').hexdigest()

def _require(condition, code='genomic_overlap_invalid_native_capture'):
    if not condition:
        raise ValueError(code)

def _path(value):
    _require(type(value) is str and value and (not any((c in value for c in '\x00\r\n\\'))))
    path = PurePosixPath(value)
    _require(path.is_absolute() and str(path) == value and ('..' not in path.parts) and (value != '/') and (not value.startswith('//')))
    return path

def _identity(value, format_name):
    value = validate_genomic_overlap_record('NativeFileIdentity', value)
    _require(value['format'] == format_name and value['artifact_ref'] == 'artifact_' + value['sha256'])
    _require(value['size_bytes'] != 0 or value['sha256'] == _EMPTY_SHA)
    return value

def _retained(value, format_name):
    _require(type(value) is dict and set(value) == {'file', 'path'})
    _identity(value['file'], format_name)
    _path(value['path'])

def _capture(value, specification):
    value = validate_genomic_overlap_record('NativeFileCapture', value)
    declaration, observed = (value['declared'], value['observed'])
    _require(all((declaration[k] == specification[k] for k in ('relative_path', 'format'))))
    present = declaration['state'] == 'present'
    _require(declaration['sha256'] is not None and declaration['size_bytes'] is not None if present else declaration['sha256'] is None and declaration['size_bytes'] is None)
    _require(declaration['size_bytes'] != 0 or declaration['sha256'] == _EMPTY_SHA)
    if observed is not None:
        _identity(observed, specification['format'])
    same = observed is not None and all((observed[k] == declaration[k] for k in ('sha256', 'size_bytes', 'format')))
    outcome, failure = (value['outcome'], value['failure'])
    if outcome == 'declared_absent':
        _require(not present and observed is None and (failure is None))
    elif outcome == 'verified':
        _require(present and same and (failure is None))
    elif outcome == 'digest_mismatch':
        _require(present and observed is not None and (not same) and (failure == 'capture_file_digest_mismatch'))
    else:
        _require(present and observed is None and (failure == 'capture_file_unavailable'))

def _arguments(original_plan, source_action_receipt_ref, writer_closure_receipt_ref, driver_started):
    plan = validate_genomic_overlap_run_plan(original_plan)
    _require(type(source_action_receipt_ref) is str and bool(source_action_receipt_ref))
    _require(type(writer_closure_receipt_ref) is str and bool(writer_closure_receipt_ref))
    _require(driver_started is None or type(driver_started) is bool)
    return plan

def validate_genomic_overlap_native_capture(value: object, *, original_plan: dict) -> dict:
    """Validate detached fixed-order transport data without reading any path.

    Declaration authentication occurs during capture and again in the retained
    worker. This pure record check cannot establish receipt authority or examine
    the manifest bodies, which are deliberately not duplicated in this record.
    """
    value = _finite_json_copy(value)
    _require(type(value) is dict and set(value) == _FIELDS)
    plan = _arguments(original_plan, value['source_action_receipt_ref'], value['writer_closure_receipt_ref'], value['driver_started'])
    _require(value['version'] == _VERSION and value['original_plan_sha256'] == digest(plan))
    state = value['driver_state']
    _require(type(state) is str and state in ('sealed_batch', 'unsealed_attempt', 'not_started'))
    _require((value['driver_started'] is False) == (state == 'not_started'))
    job = plan['requested_job']['native_genomic_overlap']
    expected = genomic_overlap_output_files(job['request'])
    retained = []
    if value['batch_file'] is not None:
        _identity(value['batch_file'], expected[-1]['format'])
    if value['batch'] is not None:
        _retained(value['batch'], expected[-1]['format'])
        _require(value['batch']['file'] == value['batch_file'])
        retained.append(value['batch'])
    _require((value['batch'] is not None) == (state == 'sealed_batch'))
    _require(type(value['files']) is list and len(value['files']) == len(expected) - 1)
    for row, specification in zip(value['files'], expected[:-1]):
        _require(type(row) is dict and set(row) == _FILE_FIELDS and (row['specification'] == specification))
        source, captured = (row['declaration_source'], row['capture'])
        _require(type(source) is str and source in ('batch', 'pair', 'none'))
        _require((source == 'batch') == (state == 'sealed_batch'))
        if source == 'none':
            _require(captured is None)
        else:
            _capture(captured, specification)
            if source == 'pair':
                _require(specification['role'] in ('canonical_set', 'overlap_stdout', 'overlap_stderr'))
        if row['retained'] is not None:
            _retained(row['retained'], specification['format'])
            _require(captured is None or row['retained']['file'] == captured['observed'])
            retained.append(row['retained'])
    if state == 'not_started':
        _require(value['batch_file'] is None and all((row['capture'] is None and row['retained'] is None for row in value['files'])))
    paths = {}
    for row in retained:
        path = _path(row['path'])
        identity = {key: row['file'][key] for key in ('artifact_ref', 'sha256', 'size_bytes')}
        for previous, prior in paths.items():
            _require(path not in previous.parents and previous not in path.parents and (path != previous or identity == prior))
        paths[path] = identity
    _require(type(value['failures']) is list)
    set_keys = {spec['set_key'] for spec in job['request']['region_sets']}
    comparisons = {pair['comparison_key']: pair for pair in job['request']['comparisons']}
    for failure in value['failures']:
        validate_genomic_overlap_record('Failure', failure)
        sk, pk = (failure['set_key'], failure['comparison_key'])
        _require(sk is None or sk in set_keys)
        _require(pk is None or pk in comparisons)
        _require(sk is None or pk is None or sk in (comparisons[pk]['a_set_key'], comparisons[pk]['b_set_key']))
    return value
