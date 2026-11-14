"""Native-receipt ingestion into the restricted shared execution history.

No scientific Store, episode tree, credit projector, model or yield estimator.
The completion hook and recovery caller use this same idempotent export path.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import fcntl
import hashlib
import json
from pathlib import Path
import re
import sqlite3

from ._local_job_worker import atomic_json
from .run_statistics import ExecutionClass, RunHistory, RunStatistic


VERSION = 'native_execution_statistics_context_v1'
RECOVERABLE_VERSION = 'native_execution_statistics_context_v2'
MEASUREMENT_VERSION = 'native_execution_measurement_v1'
RECOVERY_VERSION = 'native_execution_measurement_recovery_v1'


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _sha(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


@dataclass(frozen=True)
class NativeStatistics:
    history_path: Path
    execution_class: ExecutionClass
    condition_ref: str | None
    condition_capture: str
    recovery_directory: Path | None = None

    def __post_init__(self):
        object.__setattr__(self, 'history_path', Path(self.history_path).expanduser().resolve())
        if self.recovery_directory is not None:
            object.__setattr__(self, 'recovery_directory', Path(self.recovery_directory).expanduser().resolve())
        if type(self.execution_class) is not ExecutionClass:
            raise TypeError('typed_execution_class_required')
        if self.condition_capture not in {'not_started', 'captured_before_submission', 'unavailable_before_submission'}:
            raise ValueError('invalid_execution_condition_capture')
        if self.condition_ref is not None and (type(self.condition_ref) is not str
                or not re.fullmatch('execution_condition_[0-9a-f]{64}', self.condition_ref)):
            raise ValueError('invalid_execution_condition_reference')
        if self.condition_capture in {'not_started', 'unavailable_before_submission'} and self.condition_ref is not None:
            raise ValueError('unavailable_condition_must_remain_unknown')

    @classmethod
    def pending(cls, history_path, execution_class, *, recovery_directory=None):
        return cls(history_path, execution_class, None, 'not_started', recovery_directory)

    @classmethod
    def capture(cls, history_path, execution_class, *, recovery_directory=None):
        """Capture caller-reported conditions; failure cannot stop native work."""
        if type(execution_class) is not ExecutionClass:
            raise TypeError('typed_execution_class_required')
        history = None
        try:
            history = RunHistory(history_path, create=False, busy_timeout_seconds=0)
            condition_ref = history.current_condition(execution_class.resource_id)['ref']
            return cls(history_path, execution_class, condition_ref, 'captured_before_submission', recovery_directory)
        except (OSError, sqlite3.Error, ValueError):
            return cls(history_path, execution_class, None, 'unavailable_before_submission', recovery_directory)
        finally:
            if history is not None:
                history.close()

    def as_record(self):
        value = {'version': VERSION, 'history_path': str(self.history_path),
                'execution_class': asdict(self.execution_class), 'condition_ref': self.condition_ref,
                'condition_capture': self.condition_capture}
        if self.recovery_directory is not None:
            value.update(version=RECOVERABLE_VERSION, recovery_directory=str(self.recovery_directory))
        return value

    @classmethod
    def from_record(cls, value):
        fields = {'version', 'history_path', 'execution_class', 'condition_ref', 'condition_capture'}
        if not ((value.get('version') == VERSION and set(value) == fields)
                or (value.get('version') == RECOVERABLE_VERSION and set(value) == fields | {'recovery_directory'}
                    and type(value['recovery_directory']) is str)):
            raise ValueError('unsupported_native_statistics_context')
        return cls(value['history_path'], ExecutionClass(**value['execution_class']),
                   value['condition_ref'], value['condition_capture'], value.get('recovery_directory'))

    def validate_policy(self, policy):
        scope = self.execution_class
        if (scope.backend != 'local' or scope.duration_measure != 'systemd_service_wall_seconds'
                or scope.memory_bytes != policy.memory_bytes or scope.scratch_bytes != policy.scratch_bytes):
            raise ValueError('statistics_class_does_not_describe_native_policy')


@dataclass(frozen=True)
class HomologyStatistics:
    """Caller-owned resource identity and known corpus sizes, never gene labels."""
    history_path: Path
    resource_id: str
    reference_records: int | None
    reference_residues: int | None

    def __post_init__(self):
        object.__setattr__(self, 'history_path', Path(self.history_path).expanduser().resolve())
        if type(self.resource_id) is not str or not re.fullmatch('[a-z0-9][a-z0-9._:-]{0,191}', self.resource_id):
            raise ValueError('execution_resource_identity_required')
        for value in (self.reference_records, self.reference_residues):
            if value is not None and (type(value) is not int or value <= 0):
                raise ValueError('invalid_reference_statistics_size')

    def as_record(self):
        return {**asdict(self), 'history_path': str(self.history_path)}

    def execution_class(self, jobs, row):
        return self.execution_class_for_query(jobs, query_fasta=row['query_fasta'], cpu=row['cpu'],
                                              search_mode=row.get('search_mode', 'native_defaults'))

    def execution_class_for_query(self, jobs, *, query_fasta, cpu, search_mode='native_defaults'):
        """Exact proposed/assigned work from actual query bytes and resources.

        No registry row or physical job is needed for a prospective class.
        Sizes and CPU describe this configuration; they do not authorize
        extrapolation from another query size or allocation.
        """
        from .homology_jobs import normalize_query_fasta
        from .native_lifecycle import VERSION as native_version
        configuration = jobs.config
        if type(cpu) is not int or not 1 <= cpu <= configuration['max_cpu']:
            raise ValueError('cpu_outside_caller_allocation')
        if type(search_mode) is not str or search_mode not in jobs.search_modes:
            raise ValueError('search_mode_outside_caller_configuration')
        normalized = normalize_query_fasta(query_fasta)
        policy = configuration['job_limits']
        return ExecutionClass(phase='protein_homology_search', backend='local', resource_id=self.resource_id,
            implementation_sha256=configuration['executable']['sha256'],
            parameters_sha256=_sha({'program': 'phmmer', 'cpu': cpu, 'query_count': 1,
                'search_options': search_mode, 'native_lifecycle_version': native_version,
                'reference_database_sha256': configuration['reference_database']['sha256']}),
            memory_bytes=policy['memory_bytes'], scratch_bytes=policy['scratch_bytes'],
            cpu_threads=cpu, query_residues=len(normalized.splitlines()[1]),
            reference_records=self.reference_records, reference_residues=self.reference_residues,
            reference_state='available', duration_measure='systemd_service_wall_seconds')

    def for_job(self, jobs, row):
        return NativeStatistics.pending(self.history_path, self.execution_class(jobs, row))


def _measurement(body, end, receipt):
    """Actual execution outcome; no native return code is fabricated."""
    reason = end.get('SERVICE_RESULT')
    if (reason == 'oom-kill'
            or receipt is not None and receipt.get('resource_failure') is not None):
        outcome = 'resource_limit'
    elif receipt is not None and receipt.get('execution_failure') is None and receipt.get('native_returncode') == 0:
        outcome = 'succeeded'
    else:
        # Includes observed nonzero native exits and missing/failed native
        # execution receipts, the same operational failure meaning as collect.
        outcome = 'failed'
    ended = end['ended']
    elapsed = None
    if ended['boot_id'] == body['boot_id']:
        elapsed = (ended['monotonic_ns'] - body['started_monotonic_ns']) / 1e9
        if elapsed < 0:
            raise ValueError('negative_native_receipt_duration')
    return outcome, 'complete' if elapsed is not None else 'unmeasured', elapsed


@dataclass(frozen=True)
class NativeMeasurement:
    """One measured physical execution, without command/output/science text.

    This receipt remains useful locally even when the separate history writer
    is unavailable. Identity comes from the actual reserved unit and dispatch,
    never from a rounded duration, an episode role or a renamed operation.
    """
    execution_class: ExecutionClass
    statistic: RunStatistic
    condition_capture: str

    def __post_init__(self):
        if type(self.execution_class) is not ExecutionClass or type(self.statistic) is not RunStatistic:
            raise TypeError('typed_native_execution_measurement_required')
        if self.condition_capture not in {'captured_before_submission', 'unavailable_before_submission'}:
            raise ValueError('completed_measurement_requires_original_condition_capture')
        if self.condition_capture == 'unavailable_before_submission' and self.statistic.condition_ref is not None:
            raise ValueError('unavailable_condition_must_remain_unknown')

    def as_record(self):
        return {'version': MEASUREMENT_VERSION, 'execution_class': asdict(self.execution_class),
                'statistic': asdict(self.statistic), 'condition_capture': self.condition_capture}

    @classmethod
    def from_record(cls, value):
        if (type(value) is not dict or set(value) != {
                'version', 'execution_class', 'statistic', 'condition_capture'}
                or value['version'] != MEASUREMENT_VERSION):
            raise ValueError('unsupported_native_execution_measurement')
        return cls(ExecutionClass(**value['execution_class']), RunStatistic(**value['statistic']),
                   value['condition_capture'])


def _export_measurement(history_path, measurement, *, execution_memory_path=None):
    """The one shared-history write path for a hook or receipt recovery."""
    history = None
    try:
        history = RunHistory(history_path, create=False, busy_timeout_seconds=0)
        history.record(measurement.execution_class, measurement.statistic)
        from .execution_memory import ExecutionMemory
        memory = ExecutionMemory(execution_memory_path) if execution_memory_path else ExecutionMemory.configured()
        memory.import_native_statistic(measurement.execution_class, measurement.statistic)
        value = {'state': 'recorded', 'code': None}
    except (OSError, sqlite3.Error) as error:
        value = {'state': 'unavailable', 'code': 'statistics_history_unavailable',
                 'exception_type': type(error).__name__}
    except ValueError as error:
        value = {'state': 'unavailable', 'code': ('statistics_identity_conflict'
            if str(error) == 'execution_attempt_measurement_conflict' else 'statistics_receipt_invalid'),
            'exception_type': type(error).__name__}
    finally:
        if history is not None:
            history.close()
    return {**value, 'attempt_sha256': measurement.statistic.attempt_sha256,
            'class_ref': measurement.execution_class.ref,
            'condition_capture': measurement.condition_capture, 'measurement': measurement.as_record()}


def _recoverable_export(context, measurement, *, execution_memory_path=None):
    """Persist the compact typed receipt before attempting the history write.

    These are recovery inputs, not another statistics authority. A successful
    retry writes the same RunHistory record and never submits native work.
    """
    if context.recovery_directory is None:
        return _export_measurement(context.history_path, measurement, execution_memory_path=execution_memory_path)
    directory = context.recovery_directory
    name = measurement.statistic.attempt_sha256
    receipt_path = directory/(name+'.measurement.json')
    export_path = directory/(name+'.export.json')
    value = {'version': RECOVERY_VERSION, 'history_path': str(context.history_path),
             'measurement': measurement.as_record()}
    if execution_memory_path is not None:
        value['execution_memory_path'] = str(execution_memory_path)
    disposition = None
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with (directory/(name+'.lock')).open('a') as lock:
            # Short local file publication; history locking itself is nonblocking.
            fcntl.flock(lock, fcntl.LOCK_EX)
            if receipt_path.exists():
                if json.loads(receipt_path.read_text()) != value:
                    raise ValueError('execution_attempt_measurement_conflict')
            else:
                atomic_json(receipt_path, value)
            disposition = _export_measurement(context.history_path, measurement, execution_memory_path=execution_memory_path)
            atomic_json(export_path, disposition)
            return {**disposition, 'recovery_state': 'retained'}
    except OSError as error:
        # Recovery storage availability does not authorize blocking the separate
        # history write. The returned outcome still carries the actual receipt.
        if disposition is None:
            disposition = _export_measurement(context.history_path, measurement, execution_memory_path=execution_memory_path)
        return {**disposition, 'recovery_state': 'unavailable',
                'recovery_code': 'statistics_receipt_storage_unavailable',
                'recovery_exception_type': type(error).__name__}


def recover_native_measurement(receipt_path):
    """Recover one original receipt; no current-condition recapture or job call."""
    receipt_path = Path(receipt_path)
    value = json.loads(receipt_path.read_text())
    if (set(value)-{'execution_memory_path'} != {'version', 'history_path', 'measurement'}
            or value['version'] != RECOVERY_VERSION or type(value['history_path']) is not str):
        raise ValueError('unsupported_native_measurement_recovery')
    measurement = NativeMeasurement.from_record(value['measurement'])
    if receipt_path.name != measurement.statistic.attempt_sha256+'.measurement.json':
        raise ValueError('execution_attempt_receipt_path_mismatch')
    context = NativeStatistics(value['history_path'], measurement.execution_class,
        measurement.statistic.condition_ref, measurement.condition_capture, receipt_path.parent)
    return _recoverable_export(context, measurement, execution_memory_path=value.get('execution_memory_path'))


def publish_native_statistics(handle_path):
    """Export a completed receipt once; no status poll or native execution.

    Infrastructure failures are a separate durable disposition. Existing native
    results, reports, credit and controller histories are never modified here.
    """
    handle_path = Path(handle_path)
    body = json.loads(handle_path.read_text())
    if body.get('statistics') is None:
        return {'state': 'not_configured', 'code': None}
    output = Path(body['paths']['statistics'])
    # Completion and reconstruction can meet at this boundary. One writer owns
    # the disposition file; RunHistory independently deduplicates physical IDs.
    with output.with_suffix(output.suffix+'.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'state': 'in_progress', 'code': None}
        try:
            context = NativeStatistics.from_record(body['statistics'])
            end_path, native_path = Path(body['paths']['status']), Path(body['paths']['result'])
            if not end_path.is_file():
                return {'state': 'pending', 'code': None}
            end = json.loads(end_path.read_text())
            receipt = json.loads(native_path.read_text()) if native_path.is_file() else None
            outcome, kind, elapsed = _measurement(body, end, receipt)
            attempt = _sha({'unit': body['unit'], 'boot_id': body['boot_id'],
                            'started_monotonic_ns': body['started_monotonic_ns']})
            source = _sha({'handle_sha256': hashlib.sha256(handle_path.read_bytes()).hexdigest(),
                'completion_sha256': hashlib.sha256(end_path.read_bytes()).hexdigest(),
                'native_sha256': hashlib.sha256(native_path.read_bytes()).hexdigest() if receipt is not None else None})
            statistic = RunStatistic(attempt_sha256=attempt, source_sha256=source,
                observed_at=end['ended']['at'], outcome=outcome, duration_kind=kind,
                elapsed_seconds=elapsed, condition_ref=context.condition_ref)
            measurement = NativeMeasurement(context.execution_class, statistic, context.condition_capture)
            value = _recoverable_export(context, measurement, execution_memory_path=body.get('execution_memory_path'))
        except (OSError, sqlite3.Error) as error:
            value = {'state': 'unavailable', 'code': 'statistics_history_unavailable',
                     'exception_type': type(error).__name__}
        except (ValueError, KeyError, TypeError) as error:
            value = {'state': 'unavailable', 'code': ('statistics_identity_conflict'
                if str(error) == 'execution_attempt_measurement_conflict' else 'statistics_receipt_invalid'),
                'exception_type': type(error).__name__}
        atomic_json(output, value)
        return value
