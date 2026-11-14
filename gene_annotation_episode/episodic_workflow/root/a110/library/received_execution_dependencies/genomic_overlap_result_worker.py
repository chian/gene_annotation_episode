from __future__ import annotations
import hashlib
from pathlib import PurePosixPath
from typing import Any, Literal, TypeAlias, TypedDict
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_genomic_overlap_contracts import Failure, NativeFileCapture, NativeFileDeclaration, NativeFileIdentity, Parameters, Selector, _finite_json_copy, validate_genomic_overlap_record
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_genomic_overlap_contracts import genomic_overlap_output_files, validate_genomic_overlap_run_plan

class RetainedFile(TypedDict):
    file: NativeFileIdentity
    path: str

class CapturedInputFile(TypedDict):
    specification: dict[str, Any]
    declaration_source: Literal['batch', 'pair', 'none']
    capture: NativeFileCapture | None
    retained: RetainedFile | None

class NativeWorkerPlan(TypedDict):
    version: Literal['genomic_overlap_result_worker_plan_v1']
    mode: Literal['native_result']
    directory: str
    original_plan: dict[str, Any]
    batch: RetainedFile | None
    files: list[CapturedInputFile]
    selector: Selector
    source_action_receipt_ref: str
    writer_closure_receipt_ref: str
    driver_state: Literal['sealed_batch', 'unsealed_attempt', 'not_started']
    failures: list[Failure]

class SavedWorkerPlan(TypedDict):
    version: Literal['genomic_overlap_result_worker_plan_v1']
    mode: Literal['saved_sheet_recalculation']
    directory: str
    sheet: RetainedFile
    selector: Selector
WorkerPlan: TypeAlias = NativeWorkerPlan | SavedWorkerPlan

class WorkerOutput(TypedDict):
    role: Literal['sheet', 'components', 'projection', 'diagnostics']
    declaration: NativeFileDeclaration

class WorkerResult(TypedDict):
    version: Literal['genomic_overlap_result_worker_result_v1']
    mode: Literal['native_result', 'saved_sheet_recalculation']
    state: Literal['produced', 'partial', 'unavailable']
    source_sheet_sha256: str | None
    parameters: Parameters
    outputs: list[WorkerOutput]
    failures: list[Failure]
_PLAN_VERSION = 'genomic_overlap_result_worker_plan_v1'
_RESULT_VERSION = 'genomic_overlap_result_worker_result_v1'
_MODES = ('native_result', 'saved_sheet_recalculation')
_OUTPUTS = (('sheet', 'sheet.json', 'genomic_region_overlap_sheet_v1'), ('components', 'components.json', 'genomic_region_overlap_components_v1'), ('projection', 'projection.json', 'genomic_overlap_projection_v1'), ('diagnostics', 'diagnostics.json', 'genomic_overlap_result_diagnostics_v1'))
_EMPTY_SHA = hashlib.sha256(b'').hexdigest()

def _require(condition, code='genomic_overlap_worker_invalid_record'):
    if not condition:
        raise ValueError(code)

def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields))

def _path(value):
    _require(type(value) is str and value and (not any((c in value for c in '\x00\r\n\\'))), 'genomic_overlap_worker_invalid_path')
    path = PurePosixPath(value)
    _require(path.is_absolute() and str(path) == value and ('..' not in path.parts) and (value != '/') and (not value.startswith('//')), 'genomic_overlap_worker_invalid_path')
    return path

def _identity(value, expected_format=None):
    value = validate_genomic_overlap_record('NativeFileIdentity', value)
    _require(value['size_bytes'] != 0 or value['sha256'] == _EMPTY_SHA)
    _require(expected_format is None or value['format'] == expected_format, 'genomic_overlap_worker_format_binding')
    return value

def _content_identity(value):
    return tuple((value[key] for key in ('artifact_ref', 'sha256', 'size_bytes')))

def _retained(value, expected_format):
    _closed(value, RetainedFile.__annotations__)
    _identity(value['file'], expected_format)
    return _path(value['path'])

def _declaration(value):
    value = validate_genomic_overlap_record('NativeFileDeclaration', value)
    path = PurePosixPath(value['relative_path'])
    _require(not path.is_absolute() and str(path) == value['relative_path'] and ('..' not in path.parts) and (str(path) != '.') and (not any((c in str(path) for c in '\x00\r\n\\'))))
    present = value['state'] == 'present'
    _require(value['sha256'] is not None and value['size_bytes'] is not None if present else value['sha256'] is None and value['size_bytes'] is None)
    _require(value['size_bytes'] != 0 or value['sha256'] == _EMPTY_SHA)
    return value

def _capture(value):
    value = validate_genomic_overlap_record('NativeFileCapture', value)
    declaration = _declaration(value['declared'])
    observed = value['observed']
    if observed is not None:
        _identity(observed, declaration['format'])
    same = observed is not None and all((observed[k] == declaration[k] for k in ('format', 'sha256', 'size_bytes')))
    outcome, failure = (value['outcome'], value['failure'])
    if outcome == 'declared_absent':
        _require(declaration['state'] == 'absent' and observed is None and (failure is None))
    else:
        _require(declaration['state'] == 'present')
        if outcome == 'verified':
            _require(same and failure is None)
        elif outcome == 'digest_mismatch':
            _require(observed is not None and (not same) and (failure == 'capture_file_digest_mismatch'))
        else:
            _require(observed is None and failure == 'capture_file_unavailable')
    return value

def _failures(values):
    _require(type(values) is list)
    return [validate_genomic_overlap_record('Failure', value) for value in values]

def _selector(value, *, mode, request=None):
    value = validate_genomic_overlap_record('Selector', value)
    _require(value['mode'] == mode and len(set(value['comparison_keys'])) == len(value['comparison_keys']))
    for name in ('minimum_a_fraction', 'minimum_b_fraction'):
        fraction = value['parameters'][name]
        _require(fraction['numerator'] <= fraction['denominator'])
    projection = value['projection']
    occurrences = [(r['set_key'], r['occurrence_key']) for r in projection['occurrence_keys']]
    _require(len(set(occurrences)) == len(occurrences))
    _require(projection['kind'] == 'occurrence_rows' or not occurrences)
    if request is not None:
        keys = [row['comparison_key'] for row in request['comparisons']]
        _require([key for key in keys if key in value['comparison_keys']] == value['comparison_keys'], 'genomic_overlap_worker_selector_binding')
        selected_sets = {pair[side] for pair in request['comparisons'] if pair['comparison_key'] in value['comparison_keys'] for side in ('a_set_key', 'b_set_key')}
        _require(all((key in selected_sets for key, _ in occurrences)))
    return value

def validate_genomic_overlap_result_worker_plan(value: object) -> WorkerPlan:
    """Validate the closed transport plan and joins; return detached data, no I/O."""
    value = _finite_json_copy(value)
    _require(type(value) is dict and value.get('mode') in _MODES)
    native = value['mode'] == 'native_result'
    _closed(value, (NativeWorkerPlan if native else SavedWorkerPlan).__annotations__)
    _require(value['version'] == _PLAN_VERSION)
    directory = _path(value['directory'])
    retained = []
    if native:
        original = validate_genomic_overlap_run_plan(value['original_plan'])
        request = original['requested_job']['native_genomic_overlap']['request']
        selector = _selector(value['selector'], mode=value['mode'], request=request)
        _require(selector['saved_sheet_file'] is None)
        _require(value['driver_state'] in ('sealed_batch', 'unsealed_attempt', 'not_started'))
        for key in ('source_action_receipt_ref', 'writer_closure_receipt_ref'):
            _require(type(value[key]) is str and bool(value[key]))
        failures = _failures(value['failures'])
        set_keys = {row['set_key'] for row in request['region_sets']}
        comparisons = {row['comparison_key']: row for row in request['comparisons']}
        for failure in failures:
            sk, pk = (failure['set_key'], failure['comparison_key'])
            _require(sk is None or sk in set_keys)
            _require(pk is None or pk in comparisons)
            _require(sk is None or pk is None or sk in (comparisons[pk]['a_set_key'], comparisons[pk]['b_set_key']))
        if value['batch'] is not None:
            _retained(value['batch'], 'genomic_overlap_native_batch_v1')
            retained.append(value['batch'])
            _require(value['driver_state'] == 'sealed_batch')
        _require(type(value['files']) is list)
        expected = genomic_overlap_output_files(request)[:-1]
        _require(len(value['files']) == len(expected), 'genomic_overlap_worker_file_order')
        for row, specification in zip(value['files'], expected):
            _closed(row, CapturedInputFile.__annotations__)
            _require(row['specification'] == specification, 'genomic_overlap_worker_file_order')
            source, capture = (row['declaration_source'], row['capture'])
            _require(source in ('batch', 'pair', 'none'))
            if source == 'none':
                _require(capture is None)
            else:
                capture = _capture(capture)
                _require(all((capture['declared'][k] == specification[k] for k in ('relative_path', 'format'))))
                if source == 'pair':
                    _require(specification['role'] in ('canonical_set', 'overlap_stdout', 'overlap_stderr'))
                else:
                    _require(value['driver_state'] == 'sealed_batch')
            if row['retained'] is not None:
                _retained(row['retained'], specification['format'])
                retained.append(row['retained'])
                _require(capture is None or row['retained']['file'] == capture['observed'])
        if value['driver_state'] == 'not_started':
            _require(value['batch'] is None and all((row['capture'] is None and row['retained'] is None for row in value['files'])), 'genomic_overlap_worker_not_started_observations')
    else:
        _retained(value['sheet'], _OUTPUTS[0][2])
        retained.append(value['sheet'])
        selector = _selector(value['selector'], mode=value['mode'])
        _require(selector['saved_sheet_file'] == value['sheet']['file'], 'genomic_overlap_worker_saved_sheet_binding')
    paths = {}
    for row in retained:
        path = _path(row['path'])
        _require(path != directory and directory not in path.parents and (path not in directory.parents), 'genomic_overlap_worker_invalid_path')
        for previous, identity in paths.items():
            _require(not (path in previous.parents or previous in path.parents) and (path != previous or identity == _content_identity(row['file'])), 'genomic_overlap_worker_path_alias')
        paths[path] = _content_identity(row['file'])
    return value

def validate_genomic_overlap_result_worker_result(value: object) -> WorkerResult:
    """Validate declarations and production state without opening output files."""
    value = _finite_json_copy(value)
    _closed(value, WorkerResult.__annotations__)
    _require(value['version'] == _RESULT_VERSION and value['mode'] in _MODES)
    parameters = validate_genomic_overlap_record('Parameters', value['parameters'])
    for key in ('minimum_a_fraction', 'minimum_b_fraction'):
        _require(parameters[key]['numerator'] <= parameters[key]['denominator'])
    _failures(value['failures'])
    _require(type(value['outputs']) is list and len(value['outputs']) == 4)
    present = []
    for row, (role, filename, format_name) in zip(value['outputs'], _OUTPUTS):
        _closed(row, WorkerOutput.__annotations__)
        declaration = _declaration(row['declaration'])
        _require(row['role'] == role and declaration['relative_path'] == filename and (declaration['format'] == format_name))
        if declaration['state'] == 'present':
            _require(declaration['size_bytes'] > 0)
        present.append(declaration['state'] == 'present')
    _require(present[3] and (not present[1] or present[0]) and (not present[2] or all(present[:2])))
    _require(value['state'] == ('produced' if all(present[:3]) else 'partial' if any(present[:3]) else 'unavailable'))
    _require(value['source_sheet_sha256'] == (value['outputs'][0]['declaration']['sha256'] if present[0] else None))
    return value
