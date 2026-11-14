from __future__ import annotations
from pathlib import PurePosixPath
from typing import Literal, NotRequired, TypedDict
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_genomic_overlap_contracts import _StrictValidator
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_atac_differential_contracts import REQUIRED_DEPENDENCIES, driver_runtime_schema

class WorkerExecution(TypedDict):
    version: Literal['genomic_overlap_worker_execution_v1']
    plan_file: dict
    outcome: Literal['returned', 'failed']
    returncode: int | None
    metadata: dict | None
    failure: dict | None
    handle_file: dict | None
    request_file: dict | None
    stdout_file: dict | None
    stderr_file: dict | None
    source_pins: list[dict]
    interpreter: dict
    dependencies: NotRequired[list[dict]]

class WorkerCapture(TypedDict):
    version: Literal['genomic_overlap_worker_capture_v1']
    plan_file: dict
    execution_receipt_file: dict
    worker_result_file: dict | None
    result: dict | None
    outputs: list[dict]
    failures: list[dict]

def _require(condition, code='genomic_overlap_preparation_invalid_record'):
    if not condition:
        raise ValueError(code)

def _path(value):
    _require(type(value) is str and value and (not any((c in value for c in '\x00\r\n\\'))), 'genomic_overlap_preparation_invalid_path')
    path = PurePosixPath(value)
    _require(path.is_absolute() and str(path) == value and ('..' not in path.parts) and (value != '/') and (not value.startswith('//')), 'genomic_overlap_preparation_invalid_path')
    return path

def _validated_dependencies(value):
    """Check the existing driver dependency records without importing packages."""
    schema = driver_runtime_schema()['properties']['dependencies']
    _require(_StrictValidator(schema).is_valid(value), 'genomic_overlap_preparation_dependency_binding')
    names = [row['distribution'].lower().replace('_', '-') for row in value]
    _require(len(names) == len(set(names)) and REQUIRED_DEPENDENCIES <= set(names), 'genomic_overlap_preparation_dependency_binding')
    for row in value:
        _path(row['package_root'])
        paths = [_path(pin['path']) for pin in row['files']]
        _require(len(paths) == len(set(paths)), 'genomic_overlap_preparation_dependency_binding')
    return value

def _execution_fields(execution):
    """Exact private legacy/new fields, shared with historical receipt readers."""
    fields = set(WorkerExecution.__annotations__)
    if type(execution) is dict and 'dependencies' not in execution:
        fields.remove('dependencies')
    return fields
