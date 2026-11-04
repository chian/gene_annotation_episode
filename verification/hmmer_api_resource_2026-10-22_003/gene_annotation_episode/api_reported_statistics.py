"""Explicit HMMER reported-result statistics; no transport or action policy.

The local custody ledger supplies its first closed witness. Only the exact
exposed technical class and typed result statistic cross into shared history.
The original pre-submission condition is never reconstructed from later state.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import math
import re
import sqlite3
from typing import TYPE_CHECKING

from .execution_expectations import VERSION as CAPTURE_VERSION
from .run_statistics import (ExecutionClass, ReportedResultStatistic, RunHistory,
    REPORTED_RESULT_MEASURE, REPORTED_RESULT_PHASE, REPORTED_RESULT_UNIT, _hash, _timestamp)

if TYPE_CHECKING:
    from .api_timing_records import ApiTimingBinding


COMPATIBILITY = 'same_exposed_technical_configuration_unknown_remote_revision'
NUMERIC_PARAMETERS = frozenset({'E', 'domE', 'incE', 'incdomE', 'T', 'domT', 'incT',
    'incdomT', 'popen', 'pextend'})
TAXONOMY_PARAMETERS = frozenset({'include_taxonomy', 'exclude_taxonomy'})
WITNESS_FIELDS = frozenset({'version', 'measurement_ref', 'order_binding_ref', 'intent_ref',
    'submission_binding_ref', 'registry_ref', 'resource_id', 'job_ref', 'remote_id',
    'request_sha256', 'acquisition_receipt_ref', 'snapshot_ref', 'entity_sha256', 'field_path',
    'duration_measure', 'observation_unit', 'elapsed_seconds', 'observed_at',
    'semantics_version', 'start_context'})
START_FIELDS = frozenset({'version', 'execution_class', 'execution_class_ref',
    'condition_ref', 'condition_capture'})


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _sha(value):
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _finite_number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _reference(value, *, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not str or re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.:/-]{0,255}', value) is None:
        raise ValueError('invalid_reported_result_reference')


def _features(request):
    if (type(request) is not dict or type(request.get('algorithm')) is not str
            or request['algorithm'] not in {'phmmer', 'hmmscan'}
            or type(request.get('database')) is not str or not request['database']
            or type(request.get('query_length')) is not int or request['query_length'] <= 0):
        raise ValueError('unsupported_statistics_configuration')
    parameters = request.get('parameters')
    if type(parameters) is not dict or set(parameters) - (NUMERIC_PARAMETERS | TAXONOMY_PARAMETERS | {'threshold', 'mx'}):
        raise ValueError('unsupported_statistics_configuration')
    technical = {}
    for name, value in parameters.items():
        if name in TAXONOMY_PARAMETERS:
            # Empty filters are the same exposed configuration as no filter.
            # Biological filter values and even their digests never enter it.
            if type(value) is not list or value:
                raise ValueError('unsupported_statistics_configuration')
        elif name in NUMERIC_PARAMETERS:
            if not _finite_number(value):
                raise ValueError('unsupported_statistics_configuration')
            technical[name] = value
        elif name == 'threshold':
            if type(value) is not str or value not in {'evalue', 'bitscore'}:
                raise ValueError('unsupported_statistics_configuration')
            technical[name] = value
        elif name == 'mx':
            if type(value) is not str or re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', value) is None:
                raise ValueError('unsupported_statistics_configuration')
            technical[name] = value
    return {'version': 'hmmer_exposed_technical_features_v1', 'provider': 'hmmer',
        'algorithm': request['algorithm'], 'database_name': request['database'],
        'database_release': None, 'database_sha256': None, 'provider_defaults': 'not_exposed',
        'parameters': technical, 'taxonomy_filter': 'none', 'compatibility': COMPATIBILITY}


def _require_schema(history):
    try:
        history.require_reported_result_schema()
    except sqlite3.OperationalError as error:
        if str(error).startswith(('no such table:', 'no such column:')):
            return False
        raise
    return True


class ApiReportedStatistics:
    def __init__(self, binding: ApiTimingBinding, *, registry: dict):
        # The actual binding class is shared with the custody owner. A delayed
        # import keeps these pure helpers usable while avoiding a module cycle.
        from .api_timing_records import ApiTimingBinding
        from .public_search_operations import _registry
        if type(binding) is not ApiTimingBinding:
            raise TypeError('typed_api_timing_binding_required')
        registry = _registry(registry)
        if registry['resource_id'] != binding.resource_id:
            raise ValueError('api_timing_resource_mismatch')
        self.binding = binding
        self.registry = registry

    def execution_class(self, request: dict) -> ExecutionClass:
        features = _features(request)
        return ExecutionClass(phase=REPORTED_RESULT_PHASE, backend='https',
            resource_id=self.binding.resource_id, implementation_sha256=None,
            parameters_sha256=_sha(features), memory_bytes=None, scratch_bytes=None,
            cpu_threads=None, query_residues=request['query_length'], reference_residues=None,
            reference_records=None, reference_state='unknown',
            duration_measure=REPORTED_RESULT_MEASURE, wall_seconds=None)

    def capture_start(self, request: dict) -> dict:
        scope = self.execution_class(request)
        value = {'version': 'api_reported_start_context_v1', 'execution_class': asdict(scope),
            'execution_class_ref': scope.ref, 'condition_ref': None,
            'condition_capture': 'unavailable_before_submission'}
        history = None
        try:
            history = RunHistory(self.binding.history_path, create=False, busy_timeout_seconds=0)
            value.update(condition_ref=history.current_condition(scope.resource_id)['ref'],
                         condition_capture='captured_before_submission')
        except (OSError, sqlite3.Error, ValueError):
            pass
        finally:
            if history is not None:
                history.close()
        return value

    def export(self, witness: dict) -> dict:
        """Write the original result, class and condition without recapturing.

        Custody qualification is performed by the ledger before this boundary.
        This helper also validates the closed witness and exact class, and uses
        the ledger owner's one logical-result identity function.
        """
        from .api_timing_records import reported_result_identity
        if type(witness) is not dict or set(witness) != WITNESS_FIELDS:
            raise ValueError('invalid_reported_duration_witness')
        if (witness['version'] != 'hmmer_reported_duration_witness_v1'
                or witness['field_path'] != '$.result.stats.elapsed'
                or witness['duration_measure'] != REPORTED_RESULT_MEASURE
                or witness['observation_unit'] != REPORTED_RESULT_UNIT
                or witness['semantics_version'] != 'hmmer_reported_elapsed_source_v1'
                or witness['registry_ref'] != self.registry['registry_ref']
                or witness['resource_id'] != self.binding.resource_id):
            raise ValueError('invalid_reported_duration_witness')
        for name in ('measurement_ref', 'order_binding_ref', 'registry_ref', 'resource_id',
                     'job_ref', 'acquisition_receipt_ref', 'snapshot_ref'):
            _reference(witness[name])
        for name in ('intent_ref', 'submission_binding_ref'):
            _reference(witness[name], nullable=True)
        for name in ('request_sha256', 'entity_sha256'):
            _hash(witness[name])
        _timestamp(witness['observed_at'])
        identity = reported_result_identity(witness['registry_ref'], witness['remote_id'])
        if witness['measurement_ref'] != identity['measurement_ref']:
            raise ValueError('reported_duration_identity_conflict')
        result = {'version': 'api_reported_export_v1', 'state': 'unavailable', 'code': None,
            'measurement_ref': witness['measurement_ref'],
            'observation_sha256': identity['observation_sha256'], 'execution_class_ref': None}
        seconds = witness['elapsed_seconds']
        if not _finite_number(seconds) or seconds < 0:
            raise ValueError('invalid_reported_duration_witness')
        start = witness['start_context']
        if start is None or witness['intent_ref'] is None:
            return {**result, 'code': 'start_binding_unavailable'}
        if type(start) is not dict or set(start) != START_FIELDS or start['version'] != 'api_reported_start_context_v1':
            raise ValueError('invalid_api_reported_start_context')
        scope = ExecutionClass(**start['execution_class'])
        if (scope.phase != REPORTED_RESULT_PHASE or scope.resource_id != self.binding.resource_id
                or scope.ref != start['execution_class_ref']):
            raise ValueError('invalid_api_reported_start_context')
        result['execution_class_ref'] = scope.ref
        condition_ref = start['condition_ref']
        if condition_ref is not None and (type(condition_ref) is not str
                or re.fullmatch('execution_condition_[0-9a-f]{64}', condition_ref) is None):
            raise ValueError('invalid_execution_condition_reference')
        if start['condition_capture'] == 'unavailable_before_submission':
            if condition_ref is not None:
                raise ValueError('unavailable_condition_must_remain_unknown')
            return {**result, 'code': 'start_condition_unknown'}
        if start['condition_capture'] != 'captured_before_submission':
            raise ValueError('invalid_execution_condition_capture')
        if witness['submission_binding_ref'] is None:
            return {**result, 'code': 'submission_binding_unavailable'}
        statistic = ReportedResultStatistic(observation_sha256=identity['observation_sha256'],
            source_sha256=_sha(witness), observed_at=witness['observed_at'],
            elapsed_seconds=seconds, condition_ref=condition_ref)
        history = None
        try:
            history = RunHistory(self.binding.history_path, create=False, busy_timeout_seconds=0)
            if not _require_schema(history):
                return {**result, 'code': 'history_schema_unavailable'}
            history.record_reported_result(scope, statistic)
            return {**result, 'state': 'recorded', 'code': None}
        except (OSError, sqlite3.Error):
            return {**result, 'code': 'history_unavailable'}
        except ValueError as error:
            if str(error) == 'reported_result_measurement_conflict':
                return {**result, 'state': 'conflict', 'code': 'statistics_identity_conflict'}
            if str(error) == 'execution_condition_resource_mismatch':
                return {**result, 'code': 'start_binding_unavailable'}
            raise
        finally:
            if history is not None:
                history.close()

    def capture(self, request: dict) -> dict:
        metadata = {'version': CAPTURE_VERSION, 'execution_classes': []}
        try:
            scope = self.execution_class(request)
        except ValueError:
            return {**metadata, 'status': 'unavailable',
                'code': 'unsupported_statistics_configuration', 'snapshots': []}
        metadata['execution_classes'] = [asdict(scope)]
        history = None
        try:
            history = RunHistory(self.binding.history_path, create=False, busy_timeout_seconds=0)
            if not _require_schema(history):
                return {**metadata, 'status': 'unavailable', 'code': 'history_schema_unavailable', 'snapshots': []}
            ref = history.capture(scope)
            reader = history.reader(ref)
            try:
                snapshot = {'ref': ref, 'data': reader.get(ref)}
            finally:
                reader.close()
            return {**metadata, 'status': 'available', 'code': None, 'snapshots': [snapshot]}
        except (OSError, sqlite3.Error):
            return {**metadata, 'status': 'unavailable', 'code': 'history_unavailable', 'snapshots': []}
        except (ValueError, TypeError, KeyError):
            return {**metadata, 'status': 'invalid_statistics', 'code': 'invalid_statistics', 'snapshots': []}
        finally:
            if history is not None:
                history.close()
