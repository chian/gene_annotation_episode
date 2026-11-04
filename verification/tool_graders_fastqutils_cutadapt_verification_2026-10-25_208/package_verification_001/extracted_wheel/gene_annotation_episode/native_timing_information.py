"""Monitoring credit for received native durations, separate from science.

Only host-owned execution receipts actually known to this episode enter here.
The inherited prefix and original inputs supply its fixed baseline. No native
work, shared-history access, child-private action or continuation decision occurs.
"""
from dataclasses import dataclass
from collections.abc import Mapping
from copy import deepcopy
import json
import math

from .communication import REFERENCE_FORMATS, ReportBoundaryError
from .execution_recording import NativeMeasurement
from .domain import NATIVE_EXECUTION_OPERATIONS


def record_native_measurement(store, measurement, *, operation, operands):
    """Publish host-owned provenance; neither work nor a statistical write."""
    from .domain import canonical
    if type(measurement) is not NativeMeasurement:
        raise TypeError('typed_native_measurement_required')
    with store.transaction():
        artifact = store.artifact(canonical(measurement.as_record()), 'application/json')
        return store.put('native_execution', {
            'representation': 'native_execution_receipt_v2', 'operation': operation,
            'measurement_artifact_ref': artifact, 'operands': operands}, origin='tool')['id']


def _object(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


MEASUREMENT_SCHEMA = _object({
    'receipt_ref': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'native_execution'},
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
    record = store._require(reference, {'native_execution'})
    return NativeMeasurement.from_record(json.loads(store.get_artifact(record['measurement_artifact_ref'])))


def measurement_fields(reference, measured, *, operation):
    scope, statistic = measured.execution_class, measured.statistic
    return {'receipt_ref': reference, 'operation': operation, 'phase': scope.phase, 'outcome': statistic.outcome,
        'duration_kind': statistic.duration_kind, 'duration_measure': scope.duration_measure,
        'elapsed_seconds': statistic.elapsed_seconds, 'cpu_threads': scope.cpu_threads,
        'memory_limit_bytes': scope.memory_bytes, 'scratch_limit_bytes': scope.scratch_bytes,
        'query_residues': scope.query_residues, 'reference_residues': scope.reference_residues}


@dataclass(frozen=True)
class NativeTimingInformation:
    information_unit: float

    def __post_init__(self):
        if (type(self.information_unit) not in (int, float)
                or not math.isfinite(self.information_unit) or self.information_unit <= 0):
            raise ValueError('explicit_positive_monitoring_information_unit_required')

    def as_record(self):
        return {'version': 'received_native_timing_information_v2', 'information_unit': self.information_unit,
            'contribution': 'new_received_complete_duration_per_physical_attempt',
            'received_job_duration': 'typed_child_status_with_matching_recorded_native_measurement',
            'baseline': 'frozen_inherited_receipts_and_original_inputs',
            'scientific_credit': False, 'shared_history_writer': False,
            'controller_effect': 'separate_monitoring_information_not_added_to_scientific_credit'}

    @classmethod
    def from_record(cls, value):
        projected = cls(value['information_unit'])
        if value != projected.as_record():
            raise ValueError('unsupported_native_timing_information_binding')
        return projected

    def read_details(self, store, scope, *, known_execution_refs, initial_execution_refs,
                     details_limit, details_offset):
        if (details_limit is not None and (type(details_limit) is not int or details_limit < 0)
                or type(details_offset) is not int or details_offset < 0):
            raise ValueError('native_timing_details_require_nonnegative_page')
        store.validate_scope(scope)
        def complete(measured):
            return measured.statistic.duration_kind == 'complete' and measured.statistic.elapsed_seconds is not None
        initial = {measured.statistic.attempt_sha256 for ref in initial_execution_refs
                   if complete(measured := read_measurement(store, ref))}
        seen, rows, count, total = set(initial), [], 0, 0
        for ref in known_execution_refs:
            measured = read_measurement(store, ref)
            if not complete(measured):
                # Unknown/lower-bound outcomes remain in their original receipt
                # and tool result. They are not a newly learned total duration.
                continue
            attempt = measured.statistic.attempt_sha256
            if attempt in seen:
                continue
            seen.add(attempt)
            count += 1
            if total >= details_offset and (details_limit is None or len(rows) < details_limit):
                rows.append(measurement_fields(ref, measured, operation=store.get(ref)['operation']))
            total += 1
        credit = self.information_unit*count
        if not math.isfinite(credit):
            raise ValueError('finite_monitoring_information_credit_required')
        return {'credit': credit, 'monitoring_information_credit': credit,
            'monitoring_information_binding': self.as_record(), 'measured_attempt_count': count,
            'receipt_count': total, 'native_execution_measurements': rows,
            'next_offset': (details_offset+len(rows) if details_offset+len(rows)<total else None)}

    def __call__(self, store, scope, **knowledge):
        return self.read_details(store, scope, details_limit=0, details_offset=0, **knowledge)

    @staticmethod
    def report_sources():
        return {
            'monitoring_information_credit': {'type': 'number', 'meaning':
                'Monitoring information, separate from scientific credit. A newly received completed native duration earns the caller-bound information unit once per physical attempt; inherited information and repeated reads earn none.'},
            'native_execution_measurements': {'type': 'array', 'meaning':
                'Newly received completed native durations relative to the frozen inherited/original knowledge. Unmeasured outcomes remain in their original receipts/results and earn no completed-duration credit. Execution outcomes and durations do not establish biological findings. Unknown CPU remains null.',
                'report_schema': {'type': 'array', 'items': deepcopy(MEASUREMENT_SCHEMA),
                                  'x-source': 'native_execution_measurements'}}}


def validate_native_measurements(store, value, *, schema):
    """Keep a receipt identity and supplied measurement fields consistent.

    This checks recorded facts, not their usefulness or a scientific conclusion.
    Parent field names are unrestricted; the declared reference namespace
    identifies the receipt. Ordinary contract validation resolves the reference.
    """
    def visit(node, declared):
        if isinstance(node, Mapping):
            properties = declared.get('properties', {})
            for name, definition in properties.items():
                if (definition.get('format') in REFERENCE_FORMATS
                        and definition.get('x-reference-namespace') == 'native_execution'
                        and node.get(name) is not None):
                    ref = node[name]
                    actual = measurement_fields(ref, read_measurement(store, ref), operation=store.get(ref)['operation'])
                    fields = node.keys() & actual.keys()
                    fields = [key for key in fields if key == name or properties.get(key, {}).get('format')
                              not in REFERENCE_FORMATS]
                    if any(node[key] != actual[key] for key in fields):
                        raise ReportBoundaryError('Native timing fields differ from their receipt',
                                                  code='native_measurement_fact_mismatch')
            for name, child in node.items():
                if name in properties:
                    visit(child, properties[name])
        elif isinstance(node, (list, tuple)) and 'items' in declared:
            for child in node:
                visit(child, declared['items'])
    visit(value, schema)
