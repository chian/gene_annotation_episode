"""Monitoring credit for received native durations, separate from science.

Only host-owned execution receipts actually known to this episode enter here.
The inherited prefix and original inputs supply its fixed baseline. No native
work, shared-history access, child-private action or continuation decision occurs.
"""
import json

from episode_runtime import TableDeclaration
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.execution_recording import NativeMeasurement
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import NATIVE_EXECUTION_OPERATIONS

NATIVE_MEASUREMENTS = TableDeclaration(name='native_measurements',
                                       columns=('operation', 'operands', 'measurement_artifact_ref'),
                                       key=('measurement_artifact_ref',), record_refs=('measurement_artifact_ref',))


def record_native_measurement(store, measurement, *, operation, operands):
    """Publish host-owned provenance; neither work nor a statistical write."""
    from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import canonical
    if type(measurement) is not NativeMeasurement:
        raise TypeError('typed_native_measurement_required')
    with store.transaction():
        artifact = store.artifact(canonical(measurement.as_record()), 'application/json')
        return store.table(NATIVE_MEASUREMENTS).put({
            'operation': operation, 'operands': operands, 'measurement_artifact_ref': artifact})['id']


def _object(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


MEASUREMENT_SCHEMA = _object({
    'receipt_ref': {'type': 'string'},
    'operation': {'type': 'string', 'enum': list(NATIVE_EXECUTION_OPERATIONS)},
    'phase': {'type': 'string', 'enum': list(dict.fromkeys(NATIVE_EXECUTION_OPERATIONS.values()))},
    'outcome': {'type': 'string', 'enum': ['succeeded', 'failed', 'cancelled', 'resource_limit', 'unknown']},
    'duration_kind': {'type': 'string', 'enum': ['complete', 'lower_bound', 'unmeasured']},
    'duration_measure': {'type': 'string', 'enum': ['protected_service_wall_seconds', 'systemd_service_wall_seconds']},
    'elapsed_seconds': {'type': ['number', 'null'], 'minimum': 0},
    'cpu_threads': {'type': ['integer', 'null'], 'minimum': 1},
    'memory_limit_bytes': {'type': 'integer', 'minimum': 1},
    'scratch_limit_bytes': {'type': 'integer', 'minimum': 1},
    'query_residues': {'type': ['integer', 'null'], 'minimum': 1},
    'reference_residues': {'type': ['integer', 'null'], 'minimum': 1},
})


def read_measurement(store, reference):
    row = store.table(NATIVE_MEASUREMENTS).get(reference)
    return NativeMeasurement.from_record(json.loads(store.get_artifact(row['measurement_artifact_ref'])))


def measurement_fields(reference, measured, *, operation):
    scope, statistic = measured.execution_class, measured.statistic
    return {'receipt_ref': reference, 'operation': operation, 'phase': scope.phase, 'outcome': statistic.outcome,
        'duration_kind': statistic.duration_kind, 'duration_measure': scope.duration_measure,
        'elapsed_seconds': statistic.elapsed_seconds, 'cpu_threads': scope.cpu_threads,
        'memory_limit_bytes': scope.memory_bytes, 'scratch_limit_bytes': scope.scratch_bytes,
        'query_residues': scope.query_residues, 'reference_residues': scope.reference_residues}


