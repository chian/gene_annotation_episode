"""Explicit API timing configuration and logical reported-result identities.

These pure values perform no work, create no stores and assign no credit.
The reported-result identity does not attest a physical provider attempt.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import uuid
import weakref

from method_loop.durable import canonical


DURATION_MEASURE = 'hmmer_reported_search_elapsed_seconds'
OBSERVATION_UNIT = 'logical_provider_job_reported_result'
COMPATIBILITY = 'same_exposed_technical_configuration_unknown_remote_revision'
BINDING_VERSION = 'hmmer_api_timing_binding_v1'
_RESOURCE = re.compile(r'[a-z0-9][a-z0-9._:-]{0,191}\Z')


def _absolute_path(value):
    if not isinstance(value, (str, Path)):
        raise ValueError('api_timing_absolute_path_required')
    path = Path(value)
    if not path.is_absolute():
        raise ValueError('api_timing_absolute_path_required')
    return path.resolve()


@dataclass(frozen=True)
class ApiTimingBinding:
    ledger_path: Path
    history_path: Path
    resource_id: str
    monitoring_information_unit: float

    def __post_init__(self):
        ledger = _absolute_path(self.ledger_path)
        history = _absolute_path(self.history_path)
        if ledger == history:
            raise ValueError('api_timing_paths_must_differ')
        if type(self.resource_id) is not str or _RESOURCE.fullmatch(self.resource_id) is None:
            raise ValueError('api_timing_resource_identity_required')
        unit = self.monitoring_information_unit
        try:
            valid = type(unit) in (int, float) and math.isfinite(unit) and unit > 0
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError('explicit_positive_monitoring_information_unit_required')
        object.__setattr__(self, 'ledger_path', ledger)
        object.__setattr__(self, 'history_path', history)

    def as_record(self):
        return {'version': BINDING_VERSION,
            'ledger_path': str(self.ledger_path), 'history_path': str(self.history_path),
            'resource_id': self.resource_id, 'duration_measure': DURATION_MEASURE,
            'observation_unit': OBSERVATION_UNIT, 'compatibility': COMPATIBILITY,
            'monitoring_information_unit': self.monitoring_information_unit,
            'scope': 'new_orders_in_this_bound_run'}

    @classmethod
    def from_record(cls, value):
        try:
            if not isinstance(value, dict):
                raise ValueError
            binding = cls(ledger_path=value['ledger_path'], history_path=value['history_path'],
                resource_id=value['resource_id'],
                monitoring_information_unit=value['monitoring_information_unit'])
            if binding.as_record() != value:
                raise ValueError
            return binding
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            raise ValueError('unsupported_api_timing_binding') from error


def reported_result_identity(registry_ref, remote_id):
    """One logical provider-job result, independent of page/receipt/value."""
    if (type(registry_ref) is not str or not registry_ref
            or registry_ref != registry_ref.strip() or '\x00' in registry_ref):
        raise ValueError('api_timing_registry_identity_required')
    try:
        if type(remote_id) is not str or str(uuid.UUID(remote_id)) != remote_id:
            raise ValueError
    except (ValueError, AttributeError) as error:
        raise ValueError('api_timing_canonical_uuid_required') from error
    identity = {'version': 'hmmer_reported_result_observation_v1',
        'registry_ref': registry_ref, 'remote_id': remote_id,
        'observation_unit': OBSERVATION_UNIT}
    digest = hashlib.sha256(canonical(identity).encode('utf-8')).hexdigest()
    return {'observation_sha256': digest, 'measurement_ref': 'api_reported_duration_' + digest}


def _copy(value):
    return json.loads(_json(value))


def _digest(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _json(value):
    # Reject non-JSON finite values even if a different canonicalizer accepts
    # Python's NaN extension. Valid records keep the repository canonical bytes.
    json.dumps(value, allow_nan=False)
    return canonical(value)


def _reference(value):
    if type(value) is not str or not value or value != value.strip() or any(ord(c) < 32 for c in value):
        raise ValueError('invalid_api_timing_reference')
    return value


def _timestamp(value):
    if type(value) is not str:
        raise ValueError('invalid_api_timing_timestamp')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError('invalid_api_timing_timestamp')
    return value


DISPOSITION_CODES = frozenset({'not_opted_in_order', 'timing_binding_unavailable',
    'start_binding_unavailable', 'start_condition_unknown', 'submission_binding_unavailable',
    'submission_binding_conflict', 'submission_binding_ambiguous', 'reported_duration_missing',
    'reported_duration_invalid', 'reported_duration_identity_conflict', 'reported_duration_conflict',
    'timing_custody_unavailable', 'unsupported_statistics_configuration', 'history_unavailable',
    'history_schema_unavailable', 'statistics_identity_conflict', 'timing_source_publication_unavailable'})


def timing_disposition(state='unavailable', code='timing_custody_unavailable', **references):
    """Closed timing-only outcome; it never replaces a provider outcome."""
    if state not in {'available', 'unavailable', 'not_applicable', 'conflict'} or (code is not None and code not in DISPOSITION_CODES):
        raise ValueError('invalid_api_timing_disposition')
    if (state == 'available') != (code is None):
        raise ValueError('invalid_api_timing_disposition')
    result = dict(version='api_timing_disposition_v1', state=state, code=code,
        order_binding_ref=None, intent_ref=None, submission_binding_ref=None,
        measurement_ref=None, source_ref=None)
    if set(references) - {'order_binding_ref', 'intent_ref', 'submission_binding_ref',
            'measurement_ref', 'source_ref'}:
        raise ValueError('invalid_api_timing_disposition')
    for value in references.values():
        if value is not None:
            _reference(value)
    result.update(references)
    return result


class ApiTimingLedger:
    """Local first-witness custody, separate from the provider job authority.

    The Store and original operation ports remain authoritative. Each method
    reopens those records; timing rows cannot authorize work or repair a job.
    No method performs transport, recaptures a condition, or creates history.
    """
    def __init__(self, *, store, run_id: str, registry: dict,
                 binding: ApiTimingBinding, statistics):
        from .state import Store
        from .public_search_operations import _registry
        from .api_reported_statistics import ApiReportedStatistics
        if not isinstance(store, Store) or type(binding) is not ApiTimingBinding or type(statistics) is not ApiReportedStatistics:
            raise TypeError('typed_api_timing_owner_required')
        registry = _registry(registry)
        if (registry['resource_id'] != binding.resource_id
                or statistics.binding.as_record() != binding.as_record()
                or statistics.registry != registry):
            raise ValueError('api_timing_binding_mismatch')
        self.store, self.run_id = store, _reference(run_id)
        self.binding, self.statistics = binding, statistics
        self._registry = _copy(registry)
        self._record = dict(version='api_timing_ledger_v1', run_id=run_id,
            store_path=str(store.path.resolve()), registry=_copy(registry), binding=binding.as_record())
        self.binding_ref = 'api_timing_binding_' + _digest(self._record)
        if binding.ledger_path == store.path / 'state.sqlite3':
            raise ValueError('api_timing_ledger_must_be_separate')
        self._owner_ready = False
        self._operations_ref = None
        try:
            self._initialize()
        except (OSError, sqlite3.Error):
            # Keep the exact explicit caller binding available to the original
            # API path. No ledger work is allowed until this owner is readable
            # and durably equality-validated; readable mismatches still raise.
            pass

    def _initialize(self):
        self.binding.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect(verify_owner=False) as db:
            exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='api_timing_bindings'").fetchone()
            if exists:
                row = db.execute('SELECT binding_ref,registry_ref,data FROM api_timing_bindings WHERE run_id=?', (self.run_id,)).fetchone()
                expected = (self.binding_ref, self._registry['registry_ref'], canonical(self._record))
                if row is not None and tuple(row) != expected:
                    raise ValueError('api_timing_binding_conflict')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS api_timing_bindings(run_id TEXT PRIMARY KEY, binding_ref TEXT NOT NULL, registry_ref TEXT NOT NULL, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS api_timing_orders(registry_ref TEXT NOT NULL, job_ref TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY(registry_ref,job_ref));
                CREATE TABLE IF NOT EXISTS api_timing_submission_intents(registry_ref TEXT NOT NULL, job_ref TEXT NOT NULL, submission_operation_key TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY(registry_ref,job_ref,submission_operation_key));
                CREATE TABLE IF NOT EXISTS api_timing_submission_bindings(registry_ref TEXT NOT NULL, remote_id TEXT NOT NULL, binding_ref TEXT UNIQUE NOT NULL, data TEXT NOT NULL, PRIMARY KEY(registry_ref,remote_id));
                CREATE TABLE IF NOT EXISTS api_timing_measurements(registry_ref TEXT NOT NULL, remote_id TEXT NOT NULL, measurement_ref TEXT UNIQUE NOT NULL, data TEXT NOT NULL, PRIMARY KEY(registry_ref,remote_id));
                CREATE TABLE IF NOT EXISTS api_timing_export_dispositions(measurement_ref TEXT PRIMARY KEY, revision INTEGER NOT NULL, data TEXT NOT NULL);
            ''')
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT binding_ref,registry_ref,data FROM api_timing_bindings WHERE run_id=?', (self.run_id,)).fetchone()
            expected = (self.binding_ref, self._registry['registry_ref'], canonical(self._record))
            if row is not None and tuple(row) != expected:
                raise ValueError('api_timing_binding_conflict')
            db.execute('INSERT OR IGNORE INTO api_timing_bindings VALUES(?,?,?,?)', (self.run_id, *expected))
            db.commit()
        self._owner_ready = True

    @property
    def registry(self):
        return _copy(self._registry)

    def as_record(self):
        return _copy(self._record)

    @contextmanager
    def _connect(self, *, verify_owner=True):
        if verify_owner and not self._owner_ready:
            self._initialize()
        db = sqlite3.connect(self.binding.ledger_path, timeout=0, isolation_level=None)
        try:
            db.execute('PRAGMA synchronous=FULL')
            if verify_owner:
                row = db.execute('SELECT binding_ref,registry_ref,data FROM api_timing_bindings WHERE run_id=?', (self.run_id,)).fetchone()
                expected = (self.binding_ref, self._registry['registry_ref'], canonical(self._record))
                if row is None or tuple(row) != expected:
                    raise ValueError('api_timing_binding_conflict')
            yield db
        finally:
            if db.in_transaction:
                db.rollback()
            db.close()

    def validate_operations(self, operations):
        if (operations.store is not self.store or operations.registry != self._registry
                or str(operations.store.path.resolve()) != self._record['store_path']):
            raise ValueError('api_timing_owner_mismatch')
        self._operations_ref = weakref.ref(operations)
        return True

    def _get(self, table, where, values):
        with self._connect() as db:
            row = db.execute('SELECT data FROM ' + table + ' WHERE ' + where, values).fetchone()
            return json.loads(row[0]) if row else None

    def _order(self, operations, job_ref):
        self.validate_operations(operations)
        order = operations.open_order(job_ref)
        scope = operations.open_scope(job_ref)
        actual = operations.inspect(job_ref)
        saved = self._get('api_timing_orders', 'registry_ref=? AND job_ref=?', (self._registry['registry_ref'], job_ref))
        if saved is None:
            return None, actual['request']
        expected = self._order_record(order, request=actual['request'], scope=scope['scope'])
        if saved != expected:
            raise ValueError('api_timing_order_binding_conflict')
        return saved, actual['request']

    def _order_record(self, order, *, request, scope):
        if (order['version'] != 'public_search_order_v1'
                or order['registry_ref'] != self._registry['registry_ref']
                or order['request_sha256'] != _digest(request)):
            raise ValueError('api_timing_order_binding_conflict')
        scope = self.store.validate_scope(scope)
        record = dict(version='api_timing_order_binding_v1', run_id=self.run_id,
            registry_ref=self._registry['registry_ref'], job_ref=order['job_ref'],
            order_operation_key=order['order_operation_key'], request_sha256=order['request_sha256'],
            scope=_copy(scope), scope_sha256=_digest(scope))
        return dict(record, binding_ref='api_timing_order_binding_' + _digest(record))

    def register_new_order(self, order: dict, *, request: dict, scope: dict) -> dict:
        try:
            record = self._order_record(order, request=request, scope=scope)
            with self._connect() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT data FROM api_timing_orders WHERE registry_ref=? AND job_ref=?', (record['registry_ref'], record['job_ref'])).fetchone()
                if row and row[0] != canonical(record):
                    return timing_disposition('conflict', 'timing_binding_unavailable')
                db.execute('INSERT OR IGNORE INTO api_timing_orders VALUES(?,?,?)', (record['registry_ref'], record['job_ref'], canonical(record)))
                db.commit()
            return timing_disposition('available', None, order_binding_ref=record['binding_ref'])
        except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
            return timing_disposition()

    def before_actual_submit(self, operations, job_ref: str, *, operation_key: str) -> dict:
        try:
            order, request = self._order(operations, job_ref)
            if order is None:
                return timing_disposition('not_applicable', 'not_opted_in_order')
            refs = dict(order_binding_ref=order['binding_ref'])
            _reference(operation_key)
            with self._connect() as db:
                # Serialize same-key contenders before reading history. A
                # repeated selection can never replace its original context.
                db.execute('BEGIN IMMEDIATE')
                key = (self._registry['registry_ref'], job_ref, operation_key)
                row = db.execute('SELECT data FROM api_timing_submission_intents WHERE registry_ref=? AND job_ref=? AND submission_operation_key=?', key).fetchone()
                if row:
                    intent = json.loads(row[0])
                    self._validate_intent(intent, order=order, request=request, operation_key=operation_key)
                else:
                    try:
                        start = self.statistics.capture_start(request)
                    except ValueError as error:
                        if str(error) == 'unsupported_statistics_configuration':
                            return timing_disposition('unavailable', str(error), **refs)
                        raise
                    intent = dict(version='api_timing_submission_intent_v1',
                        order_binding_ref=order['binding_ref'], registry_ref=key[0], job_ref=job_ref,
                        submission_operation_key=operation_key, request_sha256=order['request_sha256'],
                        start_context=_copy(start))
                    intent['intent_ref'] = 'api_timing_submission_intent_' + _digest(intent)
                    self._validate_intent(intent, order=order, request=request, operation_key=operation_key)
                    db.execute('INSERT INTO api_timing_submission_intents VALUES(?,?,?,?)', (*key, canonical(intent)))
                db.commit()
            return timing_disposition('available', None, **refs, intent_ref=intent['intent_ref'])
        except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
            return timing_disposition('unavailable', 'start_binding_unavailable')

    def _qualified_submission(self, operations, receipt_ref):
        from .provider_jobs import validate_remote_identity
        receipt = operations.read_operation(receipt_ref)
        order, request = self._order(operations, receipt['job_ref'])
        if order is None:
            return None
        if (receipt['operation'] != 'submit' or receipt['outcome'] != 'completed'
                or receipt['failure'] is not None or receipt['snapshot_ref'] is None):
            return None
        snapshot = operations.read_snapshot(receipt_ref)
        native = json.loads(snapshot.content)
        remote = receipt['remote_id']
        reported_result_identity(self._registry['registry_ref'], remote)
        if (type(native) is not dict or native.get('id') != remote
                or receipt['request_sha256'] != order['request_sha256']):
            raise ValueError('submission_binding_conflict')
        validate_remote_identity(native, request, remote)
        _timestamp(receipt['observed_at'])
        intent = self._get('api_timing_submission_intents',
            'registry_ref=? AND job_ref=? AND submission_operation_key=?',
            (self._registry['registry_ref'], receipt['job_ref'], receipt['operation_key']))
        if intent and (intent['request_sha256'] != order['request_sha256']
                or intent['order_binding_ref'] != order['binding_ref']):
            raise ValueError('submission_binding_conflict')
        if intent:
            self._validate_intent(intent, order=order, request=request,
                operation_key=receipt['operation_key'])
        record = dict(version='api_timing_submission_binding_v1',
            order_binding_ref=order['binding_ref'], registry_ref=self._registry['registry_ref'],
            job_ref=receipt['job_ref'], remote_id=remote, request_sha256=order['request_sha256'],
            submission_operation_key=receipt['operation_key'], submission_receipt_ref=receipt_ref,
            submission_snapshot_ref=receipt['snapshot_ref'], submission_entity_sha256=snapshot.sha256,
            observed_at=receipt['observed_at'], intent_state='matched' if intent else 'unavailable',
            intent_ref=intent['intent_ref'] if intent else None)
        record['binding_ref'] = 'api_timing_submission_binding_' + _digest(record)
        return record

    def _validate_intent(self, intent, *, order, request, operation_key):
        from .api_reported_statistics import START_FIELDS
        expected = {'version', 'intent_ref', 'order_binding_ref', 'registry_ref', 'job_ref',
            'submission_operation_key', 'request_sha256', 'start_context'}
        if (type(intent) is not dict or set(intent) != expected
                or intent['version'] != 'api_timing_submission_intent_v1'
                or intent['order_binding_ref'] != order['binding_ref']
                or intent['registry_ref'] != self._registry['registry_ref']
                or intent['job_ref'] != order['job_ref']
                or intent['submission_operation_key'] != operation_key
                or intent['request_sha256'] != order['request_sha256']
                or intent['intent_ref'] != 'api_timing_submission_intent_' + _digest({k:v for k,v in intent.items() if k != 'intent_ref'})):
            raise ValueError('invalid_api_timing_submission_intent')
        start = intent['start_context']
        scope = self.statistics.execution_class(request)
        if (type(start) is not dict or set(start) != START_FIELDS
                or start['version'] != 'api_reported_start_context_v1'
                or start['execution_class'] != asdict(scope) or start['execution_class_ref'] != scope.ref
                or start['condition_capture'] not in {'captured_before_submission', 'unavailable_before_submission'}
                or (start['condition_capture'] == 'unavailable_before_submission' and start['condition_ref'] is not None)
                or (start['condition_ref'] is not None and (type(start['condition_ref']) is not str
                    or re.fullmatch('execution_condition_[0-9a-f]{64}', start['condition_ref']) is None))):
            raise ValueError('invalid_api_reported_start_context')

    def bind_submission_receipt(self, operations, receipt_ref: str) -> dict:
        try:
            self.validate_operations(operations)
            record = self._qualified_submission(operations, receipt_ref)
            if record is None:
                return timing_disposition('unavailable', 'submission_binding_unavailable')
            refs = dict(order_binding_ref=record['order_binding_ref'], intent_ref=record['intent_ref'],
                submission_binding_ref=record['binding_ref'])
            existing = self._get('api_timing_submission_bindings', 'registry_ref=? AND remote_id=?',
                (record['registry_ref'], record['remote_id']))
            if existing == record:
                return timing_disposition('available' if record['intent_ref'] else 'unavailable',
                    None if record['intent_ref'] else 'start_binding_unavailable', **refs)
            with self._connect() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT data FROM api_timing_submission_bindings WHERE registry_ref=? AND remote_id=?', (record['registry_ref'], record['remote_id'])).fetchone()
                if row and json.loads(row[0]) != record:
                    first = json.loads(row[0])
                    return timing_disposition('conflict', 'submission_binding_conflict',
                        order_binding_ref=first['order_binding_ref'], intent_ref=first['intent_ref'],
                        submission_binding_ref=first['binding_ref'])
                db.execute('INSERT OR IGNORE INTO api_timing_submission_bindings VALUES(?,?,?,?)',
                    (record['registry_ref'], record['remote_id'], record['binding_ref'], canonical(record)))
                db.commit()
            if record['intent_ref'] is None:
                return timing_disposition('unavailable', 'start_binding_unavailable', **refs)
            return timing_disposition('available', None, **refs)
        except ValueError as error:
            if str(error) == 'submission_binding_conflict':
                return timing_disposition('conflict', str(error))
            return timing_disposition('unavailable', 'submission_binding_unavailable')
        except (OSError, sqlite3.Error):
            return timing_disposition('unavailable', 'timing_custody_unavailable')
        except (KeyError, TypeError):
            return timing_disposition('unavailable', 'submission_binding_unavailable')

    def resolve_submission_binding(self, operations, job_ref: str, remote_id: str) -> dict:
        try:
            order, request = self._order(operations, job_ref)
            if order is None:
                return timing_disposition('not_applicable', 'not_opted_in_order')
            reported_result_identity(self._registry['registry_ref'], remote_id)
            candidates = []
            for ref in operations.inspect(job_ref)['latest_operation_refs']:
                record = self._qualified_submission(operations, ref)
                if record is not None and record['remote_id'] == remote_id:
                    candidates.append(record)
            if len(candidates) > 1:
                return timing_disposition('conflict', 'submission_binding_ambiguous', order_binding_ref=order['binding_ref'])
            if not candidates:
                return timing_disposition('unavailable', 'submission_binding_unavailable', order_binding_ref=order['binding_ref'])
            return self.bind_submission_receipt(operations, candidates[0]['submission_receipt_ref'])
        except ValueError as error:
            if str(error) == 'submission_binding_conflict':
                return timing_disposition('conflict', str(error))
            return timing_disposition('unavailable', 'submission_binding_unavailable')
        except (OSError, sqlite3.Error):
            return timing_disposition('unavailable', 'timing_custody_unavailable')
        except (KeyError, TypeError):
            return timing_disposition('unavailable', 'submission_binding_unavailable')

    def receive_result(self, operations, receipt_ref: str) -> dict:
        from .provider_jobs import validate_remote_identity
        from .acquisition import AcquisitionError
        refs = {}
        try:
            self.validate_operations(operations)
            receipt = operations.read_operation(receipt_ref)
            order, request = self._order(operations, receipt['job_ref'])
            if order is None:
                return timing_disposition('not_applicable', 'not_opted_in_order')
            refs['order_binding_ref'] = order['binding_ref']
            if receipt['operation'] == 'result' and receipt['snapshot_ref'] is not None:
                # A cached operation is a new selected read, not a new
                # acquisition. Recover the actual first receipt for its saved
                # selector so its original observation time survives a cut.
                for original_ref in operations.inspect(receipt['job_ref'])['result_receipt_refs']:
                    original = operations.read_operation(original_ref)
                    if original['snapshot_ref'] == receipt['snapshot_ref']:
                        receipt, receipt_ref = original, original_ref
                        break
            if (receipt['operation'] != 'result' or receipt['outcome'] != 'completed'
                    or receipt['failure'] is not None or receipt['snapshot_ref'] is None):
                return timing_disposition('unavailable', 'reported_duration_missing', **refs)
            snapshot = operations.read_snapshot(receipt_ref)
            native = json.loads(snapshot.content)
            remote = receipt['remote_id']
            identity = reported_result_identity(self._registry['registry_ref'], remote)
            first = self._get('api_timing_measurements', 'registry_ref=? AND remote_id=?',
                (self._registry['registry_ref'], remote))
            if first is not None:
                refs.update(measurement_ref=first['measurement_ref'], intent_ref=first['intent_ref'],
                    submission_binding_ref=first['submission_binding_ref'])
            if (type(native) is not dict or native.get('status') != 'SUCCESS'
                    or type(native.get('result')) is not dict
                    or type(native['result'].get('stats')) is not dict):
                return timing_disposition('unavailable', 'reported_duration_missing', **refs)
            stats = native['result']['stats']
            database = stats.get('database')
            if isinstance(database, dict):
                database = database.get('id')
            if (stats.get('id') != remote or stats.get('algo') != request['algorithm']
                    or database != request['database'] or request['algorithm'] not in {'phmmer', 'hmmscan'}):
                return timing_disposition('conflict', 'reported_duration_identity_conflict', **refs)
            validate_remote_identity(native, request, remote, result=True)
            if 'elapsed' not in stats:
                return timing_disposition('unavailable', 'reported_duration_missing', **refs)
            seconds = stats['elapsed']
            try:
                valid = type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0
            except OverflowError:
                valid = False
            if not valid:
                return timing_disposition('unavailable', 'reported_duration_invalid', **refs)
            _timestamp(receipt['observed_at'])
            submission = self.resolve_submission_binding(operations, receipt['job_ref'], remote)
            if submission['code'] == 'timing_custody_unavailable':
                return timing_disposition('unavailable', 'timing_custody_unavailable', **refs)
            start, intent_ref, submission_ref = None, None, None
            # Ambiguous/contradictory saved receipts must not acquire the
            # existing winner's context through a direct table read.
            if submission['state'] != 'conflict' and submission['submission_binding_ref'] is not None:
                submission_ref, intent_ref = submission['submission_binding_ref'], submission['intent_ref']
                if intent_ref:
                    bound = self._get('api_timing_submission_bindings', 'registry_ref=? AND remote_id=?', (self._registry['registry_ref'], remote))
                    intent = self._get('api_timing_submission_intents',
                        'registry_ref=? AND job_ref=? AND submission_operation_key=?',
                        (self._registry['registry_ref'], receipt['job_ref'], bound['submission_operation_key']))
                    if intent is None or intent['intent_ref'] != intent_ref:
                        raise ValueError('start_binding_unavailable')
                    start = intent['start_context']
            witness = dict(version='hmmer_reported_duration_witness_v1',
                measurement_ref=identity['measurement_ref'], order_binding_ref=order['binding_ref'],
                intent_ref=intent_ref, submission_binding_ref=submission_ref,
                registry_ref=self._registry['registry_ref'], resource_id=self.binding.resource_id,
                job_ref=receipt['job_ref'], remote_id=remote, request_sha256=order['request_sha256'],
                acquisition_receipt_ref=receipt_ref, snapshot_ref=receipt['snapshot_ref'],
                entity_sha256=snapshot.sha256, field_path='$.result.stats.elapsed',
                duration_measure=DURATION_MEASURE, observation_unit=OBSERVATION_UNIT,
                elapsed_seconds=seconds, observed_at=receipt['observed_at'],
                semantics_version='hmmer_reported_elapsed_source_v1', start_context=_copy(start))
            with self._connect() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT data FROM api_timing_measurements WHERE registry_ref=? AND remote_id=?', (witness['registry_ref'], remote)).fetchone()
                if row:
                    first = json.loads(row[0])
                    refs.update(measurement_ref=first['measurement_ref'], intent_ref=first['intent_ref'],
                        submission_binding_ref=first['submission_binding_ref'])
                    if any(first[name] != witness[name] for name in ('measurement_ref', 'order_binding_ref',
                            'registry_ref', 'resource_id', 'job_ref', 'remote_id', 'request_sha256')):
                        return timing_disposition('conflict', 'reported_duration_identity_conflict', **refs)
                    if first['elapsed_seconds'] != seconds:
                        return timing_disposition('conflict', 'reported_duration_conflict', **refs)
                    witness = first
                else:
                    db.execute('INSERT INTO api_timing_measurements VALUES(?,?,?,?)',
                        (witness['registry_ref'], remote, witness['measurement_ref'], canonical(witness)))
                db.commit()
            refs.update(measurement_ref=witness['measurement_ref'], intent_ref=witness['intent_ref'],
                submission_binding_ref=witness['submission_binding_ref'])
            if submission['state'] == 'conflict':
                return timing_disposition('conflict', submission['code'], **refs)
            try:
                self.statistics.execution_class(request)
            except ValueError as error:
                if str(error) == 'unsupported_statistics_configuration':
                    self._export(witness, override=dict(version='api_reported_export_v1',
                        state='not_applicable', code=str(error), measurement_ref=witness['measurement_ref'],
                        observation_sha256=identity['observation_sha256'], execution_class_ref=None))
                    return timing_disposition('unavailable', str(error), **refs)
                raise
            exported = self._export(witness)
            if exported['state'] == 'recorded':
                return timing_disposition('available', None, **refs)
            if submission_ref is None:
                return timing_disposition('unavailable', submission['code'] or 'submission_binding_unavailable', **refs)
            return timing_disposition('conflict' if exported['state'] == 'conflict' else 'unavailable', exported['code'], **refs)
        except AcquisitionError:
            return timing_disposition('conflict', 'reported_duration_identity_conflict', **refs)
        except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
            return timing_disposition('unavailable', 'timing_custody_unavailable', **refs)

    def read_measurement(self, measurement_ref: str) -> dict:
        from .api_reported_statistics import WITNESS_FIELDS
        witness = self._get('api_timing_measurements', 'measurement_ref=? AND registry_ref=?',
            (measurement_ref, self._registry['registry_ref']))
        if witness is None:
            raise ValueError('unknown_api_timing_measurement')
        if (set(witness) != WITNESS_FIELDS
                or witness['version'] != 'hmmer_reported_duration_witness_v1'
                or witness['duration_measure'] != DURATION_MEASURE
                or witness['observation_unit'] != OBSERVATION_UNIT
                or witness['field_path'] != '$.result.stats.elapsed'
                or witness['semantics_version'] != 'hmmer_reported_elapsed_source_v1'
                or witness['registry_ref'] != self._registry['registry_ref']
                or witness['measurement_ref'] != reported_result_identity(witness['registry_ref'], witness['remote_id'])['measurement_ref']
                or witness['resource_id'] != self.binding.resource_id):
            raise ValueError('reported_duration_identity_conflict')
        order = self._get('api_timing_orders', 'registry_ref=? AND job_ref=?', (witness['registry_ref'], witness['job_ref']))
        if (order is None or order['run_id'] != self.run_id
                or witness['order_binding_ref'] != order['binding_ref']
                or witness['request_sha256'] != order['request_sha256']):
            raise ValueError('reported_duration_identity_conflict')
        _timestamp(witness['observed_at'])
        seconds = witness['elapsed_seconds']
        try:
            valid = type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError('reported_duration_invalid')
        for name in ('measurement_ref', 'order_binding_ref', 'job_ref', 'acquisition_receipt_ref', 'snapshot_ref'):
            _reference(witness[name])
        for name in ('intent_ref', 'submission_binding_ref'):
            if witness[name] is not None:
                _reference(witness[name])
        for name in ('request_sha256', 'entity_sha256'):
            if type(witness[name]) is not str or re.fullmatch('[0-9a-f]{64}', witness[name]) is None:
                raise ValueError('invalid_reported_duration_witness')
        if (witness['intent_ref'] is None) != (witness['start_context'] is None):
            raise ValueError('invalid_reported_duration_witness')
        if witness['intent_ref'] is not None:
            bound = self._get('api_timing_submission_bindings', 'registry_ref=? AND remote_id=?',
                (witness['registry_ref'], witness['remote_id']))
            if (bound is None or bound['binding_ref'] != witness['submission_binding_ref']
                    or bound['intent_ref'] != witness['intent_ref'] or bound['job_ref'] != witness['job_ref']
                    or bound['request_sha256'] != witness['request_sha256']):
                raise ValueError('invalid_reported_duration_witness')
            intent = self._get('api_timing_submission_intents',
                'registry_ref=? AND job_ref=? AND submission_operation_key=?',
                (witness['registry_ref'], witness['job_ref'], bound['submission_operation_key']))
            if intent is None or intent['intent_ref'] != witness['intent_ref'] or intent['start_context'] != witness['start_context']:
                raise ValueError('invalid_reported_duration_witness')
        _json(witness)
        return witness

    def _export(self, witness, *, override=None):
        ref = witness['measurement_ref']
        with self._connect() as db:
            previous = db.execute('SELECT revision,data FROM api_timing_export_dispositions WHERE measurement_ref=?', (ref,)).fetchone()
        if previous and json.loads(previous[1])['state'] in {'recorded', 'conflict', 'not_applicable'}:
            return json.loads(previous[1])
        result = self.statistics.export(_copy(witness)) if override is None else override
        # This is the only mutable derived row. A concurrent export may have
        # already committed a stronger outcome; a lost CAS returns that winner.
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if previous is None:
                db.execute('INSERT OR IGNORE INTO api_timing_export_dispositions VALUES(?,?,?)', (ref, 1, canonical(result)))
            else:
                db.execute('UPDATE api_timing_export_dispositions SET revision=revision+1,data=? WHERE measurement_ref=? AND revision=?', (canonical(result), ref, previous[0]))
            current = db.execute('SELECT data FROM api_timing_export_dispositions WHERE measurement_ref=?', (ref,)).fetchone()
            db.commit()
        return json.loads(current[0])

    def retry_exports(self) -> dict:
        result = dict(version='api_timing_recovery_v1', scan_state='available', pending_count=0,
            recorded_count=0, unavailable_count=0, conflict_count=0)
        try:
            with self._connect() as db:
                rows = db.execute('SELECT m.data,e.data FROM api_timing_measurements m LEFT JOIN api_timing_export_dispositions e ON e.measurement_ref=m.measurement_ref WHERE m.registry_ref=?', (self._registry['registry_ref'],)).fetchall()
            for data, exported in rows:
                previous = json.loads(exported) if exported else None
                if previous and previous['state'] in {'recorded', 'conflict', 'not_applicable'}:
                    continue
                witness = self.read_measurement(json.loads(data)['measurement_ref'])
                order = self._get('api_timing_orders', 'registry_ref=? AND job_ref=?', (witness['registry_ref'], witness['job_ref']))
                if order is None or order['run_id'] != self.run_id:
                    continue
                result['pending_count'] += 1
                try:
                    override = None
                    operations = self._operations_ref() if self._operations_ref else None
                    if operations is not None:
                        actual_order, request = self._order(operations, witness['job_ref'])
                        if actual_order is None or actual_order['binding_ref'] != witness['order_binding_ref']:
                            raise ValueError('timing_binding_unavailable')
                        try:
                            self.statistics.execution_class(request)
                        except ValueError as error:
                            if str(error) != 'unsupported_statistics_configuration':
                                raise
                            override = dict(version='api_reported_export_v1', state='not_applicable',
                                code=str(error), measurement_ref=witness['measurement_ref'],
                                observation_sha256=reported_result_identity(witness['registry_ref'], witness['remote_id'])['observation_sha256'],
                                execution_class_ref=None)
                    outcome = self._export(witness, override=override)
                    key = 'recorded_count' if outcome['state'] == 'recorded' else 'conflict_count' if outcome['state'] == 'conflict' else 'unavailable_count'
                except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
                    key = 'unavailable_count'
                result[key] += 1
        except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
            result['scan_state'] = 'unavailable'
        return result

__all__ = ['ApiTimingBinding', 'ApiTimingLedger', 'reported_result_identity', 'timing_disposition']
