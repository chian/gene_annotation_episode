"""Qualify retained protein results, or explicitly recalculate a saved sheet.

This Store-free worker reads only its supplied retained files. Original native
calculations are checked without refitting. Only saved_sheet_recalculation calls
the calculator, once, with the selected parameters. Diagnostic retained files
are not published scientific authority: the host owns custody and qualification
of the complete result before constructing any descriptor or requested return.
"""
from __future__ import annotations
from copy import deepcopy
import math
from pathlib import PurePosixPath
from typing import Literal, TypeAlias, TypedDict, get_args
from jsonschema import Draft202012Validator, validators
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.protein_structure_contracts import CalculationParameters, FileIdentity, State, StructuredIssue, protein_structure_schema_definitions, validate_calculation_parameters, validate_file_identity
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_protein_structure_contracts import NATIVE_FORMATS, ScientificRequest, Software, validate_protein_structure_request, validate_protein_structure_software

class RetainedProteinInput(TypedDict):
    file_identity: FileIdentity
    path: str

class NativeProteinResultWorkerPlan(TypedDict):
    version: Literal['protein_structure_result_worker_plan_v1']
    mode: Literal['original_native_result']
    directory: str
    expected_request: ScientificRequest
    expected_software: Software
    native_result: RetainedProteinInput | None

class SavedProteinResultWorkerPlan(TypedDict):
    version: Literal['protein_structure_result_worker_plan_v1']
    mode: Literal['saved_sheet_recalculation']
    directory: str
    sheet: RetainedProteinInput
    original_components: RetainedProteinInput
    parameters: CalculationParameters
ProteinResultWorkerPlan: TypeAlias = NativeProteinResultWorkerPlan | SavedProteinResultWorkerPlan

class ProteinWorkerOutput(TypedDict):
    relative_path: str
    file_identity: FileIdentity

class ProteinResultWorkerResult(TypedDict):
    version: Literal['protein_structure_result_worker_result_v1']
    mode: Literal['original_native_result', 'saved_sheet_recalculation']
    operation: Literal['inspect', 'extract_sequence', 'compare']
    native_result_file: ProteinWorkerOutput | None
    sheet_file: ProteinWorkerOutput | None
    components_file: ProteinWorkerOutput | None
    state: State
    issues: list[StructuredIssue]
_PLAN_VERSION = 'protein_structure_result_worker_plan_v1'
_RESULT_VERSION = 'protein_structure_result_worker_result_v1'
_SHEET_FORMAT = 'protein_structure_comparison_sheet_v1'
_COMPONENTS_FORMAT = 'protein_structure_components_v1'
_OUTPUT_NAMES = {'native_result_file': 'native-result.json', 'sheet_file': 'sheet.json', 'components_file': 'components.json'}
_MODES = ('original_native_result', 'saved_sheet_recalculation')
_ISSUE_VALIDATOR = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine('integer', lambda _, value: type(value) is int).redefine('number', lambda _, value: type(value) in (int, float) and math.isfinite(value)))({'$defs': protein_structure_schema_definitions(), '$ref': '#/$defs/StructuredIssue'})

def _require(condition, code='invalid_schema'):
    if not condition:
        raise ValueError(code)

def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields))

def _checked(function, value):
    """Normalize malformed-data exceptions at shared validator boundaries."""
    try:
        return function(value)
    except (TypeError, KeyError, IndexError, OverflowError, RecursionError) as error:
        raise ValueError('invalid_schema') from error

def _path(value):
    """Lexical validation only; plan validation never consults the filesystem."""
    _require(type(value) is str and value and (not any((c in value for c in '\x00\r\n\\'))), 'invalid_output_path')
    result = PurePosixPath(value)
    _require(result.is_absolute() and str(result) == value and ('..' not in result.parts) and (value != '/'), 'invalid_output_path')
    return result

def _retained(value):
    _closed(value, RetainedProteinInput.__annotations__)
    validate_file_identity(value['file_identity'])
    return _path(value['path'])

def validate_protein_structure_result_worker_plan(value: ProteinResultWorkerPlan) -> ProteinResultWorkerPlan:
    """Validate a detached execution plan; no I/O or scientific calculation.

    Operation-specific formats are qualified when the retained input is read,
    so a contradictory retained format produces a typed result failure.
    """
    _checked(_plain, value)
    _require(type(value) is dict and type(value.get('mode')) is str and (value['mode'] in _MODES))
    native = value['mode'] == 'original_native_result'
    _closed(value, (NativeProteinResultWorkerPlan if native else SavedProteinResultWorkerPlan).__annotations__)
    _require(value['version'] == _PLAN_VERSION)
    directory = _path(value['directory'])
    if native:
        _checked(validate_protein_structure_request, value['expected_request'])
        _checked(validate_protein_structure_software, value['expected_software'])
        inputs = [] if value['native_result'] is None else [value['native_result']]
    else:
        validate_calculation_parameters(value['parameters'])
        inputs = [value['sheet'], value['original_components']]
    paths = [_retained(row) for row in inputs]
    for path in paths:
        _require(path != directory and directory not in path.parents and (path not in directory.parents), 'invalid_output_path')
    for index, path in enumerate(paths):
        _require(all((path != other and path not in other.parents and (other not in path.parents) for other in paths[index + 1:])), 'invalid_output_path')
    return deepcopy(value)

def validate_protein_structure_result_worker_result(value: ProteinResultWorkerResult) -> ProteinResultWorkerResult:
    """Validate closed output shape and relationships without reading its files."""
    _checked(_plain, value)
    _closed(value, ProteinResultWorkerResult.__annotations__)
    _require(value['version'] == _RESULT_VERSION and type(value['mode']) is str and (value['mode'] in _MODES))
    _require(type(value['operation']) is str and value['operation'] in NATIVE_FORMATS)
    _require(type(value['state']) is str and value['state'] in get_args(State))
    _require(type(value['issues']) is list)
    try:
        _require(all((_ISSUE_VALIDATOR.is_valid(row) for row in value['issues'])))
        _plain(value['issues'])
    except (TypeError, OverflowError, RecursionError) as error:
        raise ValueError('invalid_schema') from error
    formats = {'native_result_file': NATIVE_FORMATS[value['operation']], 'sheet_file': _SHEET_FORMAT, 'components_file': _COMPONENTS_FORMAT}
    for field, filename in _OUTPUT_NAMES.items():
        row = value[field]
        if row is not None:
            _closed(row, ProteinWorkerOutput.__annotations__)
            _require(row['relative_path'] == filename, 'invalid_output_path')
            identity = validate_file_identity(row['file_identity'])
            _require(identity['format'] == formats[field], 'unsupported_format')
            _require(identity['byte_length'] > 0, 'conflicting_identity')
    if value['mode'] == 'saved_sheet_recalculation':
        _require(value['operation'] == 'compare' and value['native_result_file'] is None)
    elif value['native_result_file'] is None:
        _require(value['sheet_file'] is None and value['components_file'] is None)
    if value['operation'] != 'compare':
        _require(value['sheet_file'] is None and value['components_file'] is None)
    _require(value['components_file'] is None or value['sheet_file'] is not None)
    if value['mode'] == 'original_native_result':
        _require((value['sheet_file'] is None) == (value['components_file'] is None))
    if value['state'] == 'complete':
        _require(value['components_file'] is not None if value['operation'] == 'compare' else value['native_result_file'] is not None)
    if all((value[field] is None for field in _OUTPUT_NAMES)):
        _require(value['state'] in ('unavailable', 'invalid') and bool(value['issues']))
    if value['operation'] == 'compare' and value['components_file'] is None:
        _require(value['state'] != 'complete' and bool(value['issues']))
    return deepcopy(value)

def _plain(value):
    if type(value) is dict:
        _require(all((type(key) is str and '\x00' not in key for key in value)))
        for item in value.values():
            _plain(item)
    elif type(value) is list:
        for item in value:
            _plain(item)
    elif type(value) is str:
        _require('\x00' not in value)
    elif type(value) is float:
        _require(math.isfinite(value))
    else:
        _require(value is None or type(value) in (bool, int))
