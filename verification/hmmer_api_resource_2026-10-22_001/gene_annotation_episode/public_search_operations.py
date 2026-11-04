"""Selected one-request HMMER operations with durable, source-preserving custody.

No operation polls, chooses work, or retries. provider_jobs is the sole mutable
job authority; orders, claims, HTTP captures and operation receipts are immutable.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import fcntl
import hashlib
import inspect as pyinspect
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

from .acquisition import AcquisitionError, PublicClients, SourceSnapshot
from .domain import ContractError, canonical, identity
from .provider_jobs import build_search_request, provider_job_reference, validate_remote_identity


def _copy(value):
    return json.loads(canonical(value))


def _digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _now():
    return datetime.now(timezone.utc).isoformat()


def describe_hmmer_client_binding(client) -> dict:
    """Describe actual implemented client code/configuration without HTTP.

    Fixture clients explicitly declare their fixture URL prefixes and timeout in
    hmmer_fixture_binding; their implementation digest is computed, not trusted.
    """
    names = ('submit_url_prefix', 'status_url_prefix', 'result_url_prefix')
    if type(client) is PublicClients:
        for name in ('hmmer_submit', 'hmmer_status', 'hmmer_result', '_http'):
            if getattr(getattr(client, name), '__func__', None) is not getattr(PublicClients, name):
                raise ContractError('unavailable_binding')
        source = Path(pyinspect.getfile(PublicClients)).read_bytes()
        fields = dict(transport_timeout_seconds=client.timeout,
            submit_url_prefix='https://www.ebi.ac.uk/Tools/hmmer/api/v1/search/',
            status_url_prefix='https://www.ebi.ac.uk/Tools/hmmer/api/v1/search/',
            result_url_prefix='https://www.ebi.ac.uk/Tools/hmmer/api/v1/result/')
    else:
        fields = getattr(client, 'hmmer_fixture_binding', None)
        if not isinstance(fields, dict) or set(fields) != {'transport_timeout_seconds', *names}:
            raise ContractError('unavailable_binding')
        try:
            source = pyinspect.getsource(type(client)).encode()
        except (OSError, TypeError):
            raise ContractError('unavailable_binding') from None
        for name in ('hmmer_submit', 'hmmer_status', 'hmmer_result'):
            if not callable(getattr(client, name, None)):
                raise ContractError('unavailable_binding')
    if type(fields['transport_timeout_seconds']) is not int or fields['transport_timeout_seconds'] <= 0:
        raise ContractError('unavailable_binding')
    if any(not isinstance(fields[name], str) or not fields[name] for name in names):
        raise ContractError('unavailable_binding')
    return dict(version='hmmer_public_client_binding_v1', provider='hmmer',
                implementation_sha256=hashlib.sha256(source).hexdigest(), **_copy(fields))


def hmmer_client_binding_sha256(client) -> str:
    return _digest(describe_hmmer_client_binding(client))


def _registry(value):
    if (not isinstance(value, dict) or set(value) != {'version', 'registry_ref', 'resource_id',
            'provider', 'client_binding_sha256'} or value['version'] != 'public_search_registry_v1'
            or value['provider'] != 'hmmer' or any(not isinstance(value[k], str) or not value[k]
                for k in ('registry_ref', 'resource_id'))
            or not isinstance(value['client_binding_sha256'], str)
            or not re.fullmatch('[0-9a-f]{64}', value['client_binding_sha256'])):
        raise ContractError('unavailable_binding')
    return _copy(value)


@dataclass(frozen=True)
class PublicSearchPorts:
    registry: dict
    operations: object
    result_publisher: object

    def __post_init__(self):
        registry = _registry(self.registry)
        if canonical(registry) != canonical(self.operations.registry):
            raise ContractError('identity_conflict')
        object.__setattr__(self, 'registry', registry)

    def sequence_symbols(self, subject_ref: str, *, scope: dict) -> str:
        tools = self.result_publisher.tools
        if tools.store is not self.operations.store:
            raise ContractError('unavailable_binding')
        tools._check_sequence_operand(subject_ref, scope)
        return tools._sequence(subject_ref, molecule_model='protein')


class ProviderOperationInProgress(ContractError):
    def __init__(self, job_ref, operation_key):
        self.job_ref, self.operation_key = job_ref, operation_key
        super().__init__('submission_in_progress', detail={'job_ref': job_ref, 'operation_key': operation_key})


class _DispatchNotSent(RuntimeError):
    pass


class ProviderJobOperations:
    def __init__(self, store, remote_searches, *, registry: dict):
        self.registry = _registry(registry)
        self.store, self.remote_searches = store, remote_searches
        if remote_searches.store is not store:
            raise ContractError('unavailable_binding')
        if hmmer_client_binding_sha256(remote_searches.clients) != self.registry['client_binding_sha256']:
            raise ContractError('identity_conflict')
        self.captures = store.path / 'public-search-http-captures'
        self.captures.mkdir(exist_ok=True)
        (self.captures / 'locks').mkdir(exist_ok=True)
        with store.transaction():
            store.db.execute('CREATE TABLE IF NOT EXISTS public_search_registries(registry_ref TEXT PRIMARY KEY, data TEXT NOT NULL)')
            previous = store.db.execute('SELECT data FROM public_search_registries WHERE registry_ref=?', (self.registry['registry_ref'],)).fetchone()
            if previous and previous[0] != canonical(self.registry):
                raise ContractError('identity_conflict')
            store.db.execute('INSERT OR IGNORE INTO public_search_registries VALUES(?,?)', (self.registry['registry_ref'], canonical(self.registry)))
            store.db.execute('CREATE TABLE IF NOT EXISTS public_search_order_scopes(job_ref TEXT PRIMARY KEY, data TEXT NOT NULL)')
            store.db.execute('CREATE TABLE IF NOT EXISTS public_search_orders(job_ref TEXT PRIMARY KEY, data TEXT NOT NULL)')
            store.db.execute('CREATE TABLE IF NOT EXISTS public_search_claims(id TEXT PRIMARY KEY, job_ref TEXT NOT NULL, predecessor TEXT NOT NULL, data TEXT NOT NULL, UNIQUE(job_ref,predecessor))')
            store.db.execute('CREATE TABLE IF NOT EXISTS public_search_selections(operation_key TEXT PRIMARY KEY, selection_sha256 TEXT NOT NULL)')
            store.db.execute('CREATE TABLE IF NOT EXISTS public_search_operations(id TEXT PRIMARY KEY, operation_key TEXT UNIQUE NOT NULL, job_ref TEXT NOT NULL, data TEXT NOT NULL)')
            store.db.execute('CREATE TABLE IF NOT EXISTS public_search_results(job_ref TEXT NOT NULL, page INTEGER NOT NULL, page_size INTEGER NOT NULL, receipt_ref TEXT NOT NULL, snapshot_ref TEXT NOT NULL, PRIMARY KEY(job_ref,page,page_size))')

    def _no_transaction(self):
        if self.store.db.in_transaction:
            raise ContractError('provider_http_in_transaction')

    def order(self, *, operation_key: str, provider: str, subject_ref: str,
              query_fasta: str, algorithm: str, database: str, scope: dict,
              parameters: dict | None = None, page_size: int | None = None) -> dict:
        if provider != 'hmmer':
            raise ContractError('unsupported_provider')
        if algorithm not in {'phmmer', 'hmmscan'} or not isinstance(database, str) or not database:
            raise ContractError('unsupported_hmmer_search_configuration')
        if not isinstance(scope, dict):
            raise ContractError('invalid_scope')
        normalized_scope = self.store.validate_scope(scope)
        size = 50 if page_size is None else page_size
        if type(size) is not int or size < 1 or not isinstance(operation_key, str) or not operation_key:
            raise ContractError('invalid_search_order')
        request, _ = build_search_request(subject_ref=subject_ref, query_fasta=query_fasta,
            algorithm=algorithm, database=database, parameters=parameters, page_size=size, provider=provider)
        job = provider_job_reference(operation_key, request)
        with self.store.transaction():
            prior = self.store.db.execute('SELECT * FROM provider_jobs WHERE operation_key=?', (operation_key,)).fetchone()
            if prior:
                if prior['id'] != job or prior['request'] != canonical(request):
                    raise ContractError('request_conflict')
                saved = self.open_order(job)
                if self.open_scope(job)['scope'] != normalized_scope:
                    raise ContractError('identity_conflict')
                return saved
            order = dict(version='public_search_order_v1', registry_ref=self.registry['registry_ref'],
                job_ref=job, order_operation_key=operation_key, request_sha256=_digest(request),
                request_ref=self.store.artifact(canonical(request), 'application/json'),
                query_fasta_ref=self.store.artifact(query_fasta.encode(), 'text/plain'))
            self.store.db.execute('INSERT INTO provider_jobs VALUES(?,?,?,?,?,?,?,?,?)',
                (job, operation_key, canonical(request), 'not_submitted', None, None, None, None, None))
            self.store.db.execute('INSERT INTO public_search_orders VALUES(?,?)', (job, canonical(order)))
            sidecar = dict(version='public_search_order_scope_v1', registry_ref=self.registry['registry_ref'],
                job_ref=job, scope=normalized_scope, scope_sha256=_digest(normalized_scope))
            self.store.db.execute('INSERT INTO public_search_order_scopes VALUES(?,?)', (job, canonical(sidecar)))
        return _copy(order)

    def open_order(self, job_ref: str) -> dict:
        row = self.store.db.execute('SELECT data FROM public_search_orders WHERE job_ref=?', (job_ref,)).fetchone()
        if not row:
            exists = self.store.db.execute('SELECT 1 FROM provider_jobs WHERE id=?', (job_ref,)).fetchone()
            raise ContractError('unavailable_binding' if exists else 'unknown_job')
        order = json.loads(row[0])
        registry = self.store.db.execute('SELECT data FROM public_search_registries WHERE registry_ref=?', (self.registry['registry_ref'],)).fetchone()
        if registry is None or registry[0] != canonical(self.registry):
            raise ContractError('identity_conflict')
        job = self.remote_searches._get(job_ref)
        if (order['registry_ref'] != self.registry['registry_ref'] or order['job_ref'] != job_ref
                or order['order_operation_key'] != job['operation_key']
                or order['request_sha256'] != hashlib.sha256(job['request'].encode()).hexdigest()
                or self.store.get_artifact(order['request_ref']) != job['request'].encode()):
            raise ContractError('identity_conflict')
        fasta = self.store.get_artifact(order['query_fasta_ref'])
        if hashlib.sha256(fasta).hexdigest() != json.loads(job['request'])['query_sha256']:
            raise ContractError('identity_conflict')
        self._scope_sidecar(job_ref)
        return _copy(order)

    def _scope_sidecar(self, job_ref):
        row = self.store.db.execute('SELECT data FROM public_search_order_scopes WHERE job_ref=?', (job_ref,)).fetchone()
        if row is None:
            raise ContractError('unavailable_binding')
        sidecar = json.loads(row[0])
        if (set(sidecar) != {'version','registry_ref','job_ref','scope','scope_sha256'}
                or sidecar['version'] != 'public_search_order_scope_v1'
                or sidecar['registry_ref'] != self.registry['registry_ref'] or sidecar['job_ref'] != job_ref
                or not isinstance(sidecar['scope'], dict)
                or sidecar['scope_sha256'] != _digest(sidecar['scope'])
                or canonical(self.store.validate_scope(sidecar['scope'])) != canonical(sidecar['scope'])):
            raise ContractError('identity_conflict')
        return sidecar

    def open_scope(self, job_ref: str) -> dict:
        self.open_order(job_ref)
        return _copy(self._scope_sidecar(job_ref))

    def inspect(self, job_ref: str) -> dict:
        order = self.open_order(job_ref)
        row = self.remote_searches._get(job_ref)
        return dict(order=order, request=json.loads(row['request']), state=row['state'], remote_id=row['remote_id'],
            latest_operation_refs=[r[0] for r in self.store.db.execute('SELECT id FROM public_search_operations WHERE job_ref=? ORDER BY rowid', (job_ref,))],
            submission_claim_refs=[r[0] for r in self.store.db.execute('SELECT id FROM public_search_claims WHERE job_ref=? ORDER BY rowid', (job_ref,))],
            result_receipt_refs=[r[0] for r in self.store.db.execute('SELECT receipt_ref FROM public_search_results WHERE job_ref=? ORDER BY rowid', (job_ref,))])

    def _selection(self, job, operation, key, operands):
        return _digest(dict(registry=self.registry, job_ref=job, operation=operation, operation_key=key, operands=operands))

    def _reserve(self, key, selection):
        # Durable selected operands prevent conflicting keys from reaching HTTP
        # even while their first terminal receipt has not yet been published.
        with self.store.transaction():
            prior = self.store.db.execute('SELECT selection_sha256 FROM public_search_selections WHERE operation_key=?', (key,)).fetchone()
            if prior:
                if prior[0] != selection:
                    raise ContractError('operation_conflict')
                return False
            self.store.db.execute('INSERT INTO public_search_selections VALUES(?,?)', (key, selection))
            return True

    def _replay(self, key, selection):
        row = self.store.db.execute('SELECT data FROM public_search_operations WHERE operation_key=?', (key,)).fetchone()
        if row:
            receipt = json.loads(row[0])
            if receipt['selection_sha256'] != selection:
                raise ContractError('operation_conflict')
            return receipt
        return None

    def read_operation(self, receipt_ref: str) -> dict:
        row = self.store.db.execute('SELECT data FROM public_search_operations WHERE id=?', (receipt_ref,)).fetchone()
        if not row:
            raise ContractError('unknown_provider_operation')
        receipt = json.loads(row[0])
        order = self.open_order(receipt['job_ref'])
        expected = {'version','receipt_ref','operation_key','selection_sha256','operation',
            'registry_ref','job_ref','provider','request_sha256','observed_at','outcome','state',
            'provider_chronology','remote_id','snapshot_ref','result_ready','result_cached',
            'result_snapshot_refs','failure'}
        if (set(receipt) != expected or receipt['version'] != 'public_search_operation_v1'
                or receipt['receipt_ref'] != receipt_ref or receipt['provider'] != 'hmmer'
                or receipt['request_sha256'] != order['request_sha256']
                or receipt['provider_chronology'] != 'unknown'
                or receipt['registry_ref'] != self.registry['registry_ref']):
            raise ContractError('identity_conflict')
        return receipt

    def read_snapshot(self, receipt_ref: str) -> SourceSnapshot:
        receipt = self.read_operation(receipt_ref)
        if receipt['snapshot_ref'] is None:
            raise ContractError('provider_snapshot_unavailable')
        return self.remote_searches._load_snapshot(self.store.get_artifact(receipt['snapshot_ref']).decode())

    def _cache(self, job):
        return [r[0] for r in self.store.db.execute('SELECT snapshot_ref FROM public_search_results WHERE job_ref=? ORDER BY rowid', (job,))]

    def _failure(self, code, job, *, native_code=None, phase='local_preflight', submission_outcome=None,
                 snapshot_ref=None, diagnostic_ref=None, retry=None, http_status=None):
        if native_code is not None and not re.fullmatch('[a-z][a-z0-9_]{0,127}', native_code):
            native_code = 'unclassified_client_failure'
        return dict(code=code, native_code=native_code, phase=phase, submission_outcome=submission_outcome,
            prerequisite=None, retry_after_seconds=retry, http_status=http_status,
            diagnostic_ref=diagnostic_ref, response_snapshot_ref=snapshot_ref,
            affected_refs=[job], partial_record_refs=[])

    def _receipt(self, job, operation, key, selection, *, state=None, snapshot_ref=None,
                 ready=None, failure=None):
        order = self.open_order(job)
        row = self.remote_searches._get(job)
        receipt = dict(version='public_search_operation_v1',
            receipt_ref=identity('provider_operation', dict(registry_ref=self.registry['registry_ref'], operation_key=key)),
            operation_key=key, selection_sha256=selection, operation=operation,
            registry_ref=self.registry['registry_ref'], job_ref=job, provider='hmmer',
            request_sha256=order['request_sha256'], observed_at=_now(),
            outcome='failed' if failure else 'completed', state=state or row['state'],
            provider_chronology='unknown', remote_id=row['remote_id'], snapshot_ref=snapshot_ref,
            result_ready=ready, result_cached=bool(self._cache(job)), result_snapshot_refs=self._cache(job), failure=failure)
        self.store.db.execute('INSERT INTO public_search_operations VALUES(?,?,?,?)',
            (receipt['receipt_ref'], key, job, canonical(receipt)))
        return receipt

    def _fail_receipt(self, job, operation, key, selection, code, **kwargs):
        with self.store.transaction():
            saved = self._replay(key, selection)
            if saved:
                return saved
            return self._receipt(job, operation, key, selection, failure=self._failure(code, job, **kwargs))

    def _lock(self, name):
        path = self.captures / 'locks' / hashlib.sha256(name.encode()).hexdigest()
        descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(descriptor)
            return None
        return descriptor

    def _capsule_path(self, key):
        return self.captures / _digest(dict(registry_ref=self.registry['registry_ref'], operation_key=key))

    def _capture(self, job, operation, key, selection, callback, descriptor):
        """Store-free worker. It owns the lock descriptor after scheduling."""
        directory = None
        try:
            snapshot, failure = None, None
            try:
                snapshot = callback()
                if not isinstance(snapshot, SourceSnapshot):
                    raise AcquisitionError('provider_client_snapshot_invalid')
            except BaseException as error:
                snapshot = getattr(error, 'snapshot', None)
                code = getattr(error, 'code', 'provider_client_failure')
                if not isinstance(code, str) or not re.fullmatch('[a-z][a-z0-9_]{0,127}', code):
                    code = 'provider_client_failure'
                failure = dict(native_code=code, phase=getattr(error, 'phase', None),
                    submission_outcome=getattr(error, 'submission_outcome', None),
                    retry_after_seconds=getattr(error, 'retry_after', None), diagnostic_file='diagnostic.json')
                diagnostic = canonical(dict(exception_type=type(error).__name__, message=str(error),
                    details=getattr(error, 'diagnostic', None))).encode()
            manifest = dict(version='public_search_http_capture_v1', registry_ref=self.registry['registry_ref'],
                job_ref=job, operation_key=key, selection_sha256=selection, operation=operation,
                finished_at=_now(), snapshot=None, client_failure=failure)
            directory = Path(tempfile.mkdtemp(prefix='.pending-', dir=self.captures))
            def write(name, content):
                with (directory / name).open('xb') as handle:
                    handle.write(content); handle.flush(); os.fsync(handle.fileno())
            if snapshot is not None:
                fields = asdict(snapshot); fields.pop('content')
                fields.update(content_file='response.entity', content_sha256=snapshot.sha256,
                              content_bytes=len(snapshot.content))
                manifest['snapshot'] = fields
                write('response.entity', snapshot.content)
            if failure:
                write('diagnostic.json', diagnostic)
            write('manifest.json', canonical(manifest).encode())
            fd = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            destination = self._capsule_path(key)
            if destination.exists():
                if (destination / 'manifest.json').read_bytes() != canonical(manifest).encode():
                    raise ContractError('http_capture_conflict')
            else:
                os.rename(directory, destination)
                directory = None
                fd = os.open(self.captures, os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            return str(destination)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if directory is not None:
                import shutil
                shutil.rmtree(directory)

    async def _dispatch(self, job, operation, key, selection, callback, descriptor):
        self._no_transaction()
        try:
            future = asyncio.get_running_loop().run_in_executor(None, self._capture,
                job, operation, key, selection, callback, descriptor)
        except BaseException as error:
            if descriptor is not None:
                os.close(descriptor)
            raise _DispatchNotSent('executor_dispatch_not_sent') from error
        # The worker must finish capture and release its descriptor after caller
        # cancellation. Shield prevents cancellation of a queued executor future.
        return await asyncio.shield(future)

    def _import_capture(self, job, operation, key, selection):
        directory = self._capsule_path(key)
        if not directory.exists():
            return None, None, None, None
        try:
            manifest = json.loads((directory / 'manifest.json').read_bytes())
            if set(manifest) != {'version','registry_ref','job_ref','operation_key','selection_sha256',
                    'operation','finished_at','snapshot','client_failure'} or any(manifest[k] != v for k,v in
                    dict(version='public_search_http_capture_v1', registry_ref=self.registry['registry_ref'],
                        job_ref=job, operation_key=key, selection_sha256=selection, operation=operation).items()):
                raise ValueError('capture_identity')
            snapshot, reference, diagnostic = None, None, None
            if manifest['snapshot'] is not None:
                fields = manifest['snapshot'].copy()
                if set(fields) != {'service','url','request','retrieved_at','media_type','transport',
                                   'content_file','content_sha256','content_bytes'} or fields.pop('content_file') != 'response.entity':
                    raise ValueError('capture_snapshot')
                content = (directory / 'response.entity').read_bytes()
                if fields.pop('content_sha256') != hashlib.sha256(content).hexdigest() or fields.pop('content_bytes') != len(content):
                    raise ValueError('capture_entity')
                snapshot = SourceSnapshot(content=content, **fields)
                reference = self.store.artifact(self.remote_searches._snapshot(snapshot), 'application/json')
            failure = manifest['client_failure']
            if failure is not None:
                if set(failure) != {'native_code','phase','submission_outcome','retry_after_seconds','diagnostic_file'}:
                    raise ValueError('capture_failure')
                if failure['diagnostic_file'] not in (None, 'diagnostic.json'):
                    raise ValueError('capture_diagnostic')
                if failure['diagnostic_file']:
                    diagnostic = self.store.artifact((directory / 'diagnostic.json').read_bytes(), 'application/json')
            if snapshot is None and failure is None:
                raise ValueError('empty_capture')
            expected_files = {'manifest.json'} | ({'response.entity'} if snapshot is not None else set()) | ({'diagnostic.json'} if failure and failure['diagnostic_file'] else set())
            if {entry.name for entry in directory.iterdir()} != expected_files or any(entry.is_symlink() for entry in directory.iterdir()):
                raise ValueError('capture_members')
            canonical(manifest)
            return snapshot, reference, failure, diagnostic
        except (OSError, ValueError, TypeError, KeyError) as error:
            raise ContractError('http_capture_invalid') from error

    def _capture_failure(self, job, phase, failure, snapshot, reference, diagnostic):
        native = failure['native_code']
        code = ('http_failure' if native.startswith('provider_http_') else
                'connection_failed' if native == 'provider_connection_failed' else
                'request_timeout' if native == 'provider_request_timeout' else 'client_failure')
        if phase == 'submission' and failure['submission_outcome'] != 'not_sent':
            code = 'submission_uncertain'
        return self._failure(code, job, native_code=native, phase=phase,
            submission_outcome=(failure['submission_outcome'] or 'unknown') if phase == 'submission' else None,
            snapshot_ref=reference, diagnostic_ref=diagnostic, retry=failure['retry_after_seconds'],
            http_status=snapshot.transport.get('status') if snapshot else None)

    def _finish_submit(self, job, key, selection):
        saved = self._replay(key, selection)
        if saved:
            return saved
        try:
            snapshot, reference, failure, diagnostic = self._import_capture(job, 'submit', key, selection)
        except ContractError as error:
            diagnostic = self.store.artifact(canonical({'code': str(error)}), 'application/json')
            problem = self._failure('submission_uncertain', job, native_code='http_capture_invalid',
                phase='recovery', submission_outcome='unknown', diagnostic_ref=diagnostic)
            self.remote_searches._update(job, state='submission_uncertain', error_code=problem['code'])
            return self._receipt(job, 'submit', key, selection, failure=problem)
        if snapshot is None and failure is None:
            row = self.remote_searches._get(job)
            if row['submission']:
                snapshot = self.remote_searches._load_snapshot(row['submission'])
                reference = self.store.artifact(row['submission'], 'application/json')
        if snapshot is not None:
            self.remote_searches._update(job, submission=self.remote_searches._snapshot(snapshot))
        problem, remote = None, None
        if failure:
            problem = self._capture_failure(job, 'submission', failure, snapshot, reference, diagnostic)
        elif snapshot is not None:
            try:
                remote = str(uuid.UUID(json.loads(snapshot.content)['id']))
            except (ValueError, TypeError, KeyError, AttributeError):
                problem = self._failure('submission_uncertain', job,
                    native_code='provider_submission_response_invalid', phase='submission',
                    submission_outcome='unknown', snapshot_ref=reference)
        else:
            problem = self._failure('submission_uncertain', job, phase='recovery', submission_outcome='unknown')
        if remote:
            self.remote_searches._update(job, state='accepted', remote_id=remote, error_code=None)
        else:
            state = 'not_submitted' if problem['submission_outcome'] == 'not_sent' else 'submission_uncertain'
            self.remote_searches._update(job, state=state, error_code=problem['code'])
        return self._receipt(job, 'submit', key, selection, snapshot_ref=reference, failure=problem)

    async def submit_once(self, job_ref: str, *, operation_key: str, retry_of: str | None = None) -> dict:
        self._no_transaction()
        order = self.open_order(job_ref)
        selection = self._selection(job_ref, 'submit', operation_key, dict(retry_of=retry_of))
        newly_selected = self._reserve(operation_key, selection)
        saved = self._replay(operation_key, selection)
        if saved:
            return saved
        descriptor = self._lock('submit:' + job_ref)
        if descriptor is None:
            same = self.store.db.execute("SELECT 1 FROM public_search_claims WHERE job_ref=? AND json_extract(data,'$.operation_key')=?", (job_ref, operation_key)).fetchone()
            if same or not newly_selected:
                raise ProviderOperationInProgress(job_ref, operation_key)
            return self._fail_receipt(job_ref, 'submit', operation_key, selection, 'submission_in_progress')
        transfer = False
        try:
            with self.store.transaction():
                saved = self._replay(operation_key, selection)
                if saved:
                    return saved
                row = self.remote_searches._get(job_ref)
                claim = self.store.db.execute("SELECT data FROM public_search_claims WHERE job_ref=? AND json_extract(data,'$.operation_key')=?", (job_ref, operation_key)).fetchone()
                if claim:
                    original = json.loads(claim[0])
                    if original['retry_of'] != retry_of:
                        raise ContractError('operation_conflict')
                    return self._finish_submit(job_ref, operation_key, selection)
                if row['remote_id'] is not None or self._cache(job_ref):
                    return self._receipt(job_ref, 'submit', operation_key, selection)
                claims = self.store.db.execute('SELECT data FROM public_search_claims WHERE job_ref=? ORDER BY rowid DESC LIMIT 1', (job_ref,)).fetchone()
                if claims:
                    prior = json.loads(claims[0])
                    previous = self.store.db.execute('SELECT data FROM public_search_operations WHERE operation_key=?', (prior['operation_key'],)).fetchone()
                    prior_receipt = json.loads(previous[0]) if previous else None
                    if (not prior_receipt or not prior_receipt['failure'] or
                            prior_receipt['failure']['submission_outcome'] != 'not_sent'):
                        return self._receipt(job_ref, 'submit', operation_key, selection,
                            failure=self._failure('submission_uncertain', job_ref, submission_outcome='unknown'))
                    if retry_of != prior_receipt['receipt_ref']:
                        return self._receipt(job_ref, 'submit', operation_key, selection,
                            failure=self._failure('retry_not_authorized', job_ref))
                elif retry_of is not None:
                    return self._receipt(job_ref, 'submit', operation_key, selection,
                        failure=self._failure('retry_not_authorized', job_ref))
                claim = dict(version='public_search_submission_claim_v1', job_ref=job_ref,
                    registry_ref=self.registry['registry_ref'], request_sha256=order['request_sha256'],
                    operation_key=operation_key, retry_of=retry_of, claimed_at=_now())
                claim_ref = identity('provider_submission_claim', claim)
                self.store.db.execute('INSERT INTO public_search_claims VALUES(?,?,?,?)',
                    (claim_ref, job_ref, retry_of or 'initial_submission', canonical(claim)))
                self.remote_searches._update(job_ref, state='submitting')
            request = json.loads(self.remote_searches._get(job_ref)['request'])
            fasta = self.store.get_artifact(order['query_fasta_ref']).decode()
            client = self.remote_searches.clients
            transfer = True
            try:
                await self._dispatch(job_ref, 'submit', operation_key, selection,
                    lambda: client.hmmer_submit(fasta, algorithm=request['algorithm'], database=request['database'],
                                                parameters=request['parameters']), descriptor)
            except asyncio.CancelledError:
                raise
            except _DispatchNotSent:
                with self.store.transaction():
                    self.remote_searches._update(job_ref, state='not_submitted', error_code='client_failure')
                    return self._receipt(job_ref, 'submit', operation_key, selection,
                        failure=self._failure('client_failure', job_ref, native_code='executor_dispatch_not_sent',
                            phase='local_preflight', submission_outcome='not_sent'))
            except BaseException as error:
                # Only a dispatch failure explicitly marked not_sent permits repair.
                # An absent capsule after any worker fault remains conservative.
                return self._fail_receipt(job_ref, 'submit', operation_key, selection,
                    'submission_uncertain', phase='storage', native_code='http_capture_publication_failed',
                    submission_outcome='unknown')
            with self.store.transaction():
                return self._finish_submit(job_ref, operation_key, selection)
        finally:
            if not transfer:
                os.close(descriptor)

    def recover_submission(self, job_ref: str, *, operation_key: str) -> dict:
        self._no_transaction()
        self.open_order(job_ref)
        selection = self._selection(job_ref, 'recover_submission', operation_key, {})
        self._reserve(operation_key, selection)
        saved = self._replay(operation_key, selection)
        if saved:
            return saved
        descriptor = self._lock('submit:' + job_ref)
        if descriptor is None:
            return self._fail_receipt(job_ref, 'recover_submission', operation_key, selection, 'submission_in_progress')
        try:
            with self.store.transaction():
                saved = self._replay(operation_key, selection)
                if saved:
                    return saved
                claim = self.store.db.execute('SELECT data FROM public_search_claims WHERE job_ref=? ORDER BY rowid DESC LIMIT 1', (job_ref,)).fetchone()
                original = None
                if claim:
                    claim = json.loads(claim[0])
                    original_selection = self._selection(job_ref, 'submit', claim['operation_key'], dict(retry_of=claim['retry_of']))
                    original = self._replay(claim['operation_key'], original_selection)
                    if original is None:
                        original = self._finish_submit(job_ref, claim['operation_key'], original_selection)
                row = self.remote_searches._get(job_ref)
                failure = original['failure'] if original else self._failure('prerequisite_missing', job_ref,
                    native_code='submission_claim_unavailable', phase='recovery')
                return self._receipt(job_ref, 'recover_submission', operation_key, selection,
                    snapshot_ref=original['snapshot_ref'] if original else None,
                    failure=None if row['remote_id'] else failure)
        finally:
            os.close(descriptor)

    def _ready(self, job):
        row = self.remote_searches._get(job)
        if self._cache(job):
            return True
        if row['latest_status']:
            try:
                native = json.loads(self.remote_searches._load_snapshot(row['latest_status']).content)
                state = native['task']['status']
                if state in {'SUCCESS','FAILURE','REVOKED','PENDING','RECEIVED','STARTED','RETRY'}:
                    return state == 'SUCCESS'
            except (ValueError, TypeError, KeyError):
                pass
        return None

    async def status_once(self, job_ref: str, *, operation_key: str) -> dict:
        return await self._observe(job_ref, 'status', operation_key, {})

    async def result_once(self, job_ref: str, *, operation_key: str,
                          page: int | None, page_size: int | None) -> dict:
        if type(page) is not int or page < 1 or type(page_size) is not int or page_size < 1:
            raise ContractError('invalid_public_search_page_selector')
        return await self._observe(job_ref, 'result', operation_key, dict(page=page, page_size=page_size))

    async def _observe(self, job, operation, key, operands):
        self._no_transaction()
        self.open_order(job)
        selection = self._selection(job, operation, key, operands)
        self._reserve(key, selection)
        saved = self._replay(key, selection)
        if saved:
            return saved
        descriptor = self._lock('operation:' + key)
        if descriptor is None:
            raise ProviderOperationInProgress(job, key)
        transfer = False
        try:
            saved = self._replay(key, selection)
            if saved:
                return saved
            row = self.remote_searches._get(job)
            if operation == 'result':
                cached = self.store.db.execute('SELECT receipt_ref,snapshot_ref FROM public_search_results WHERE job_ref=? AND page=? AND page_size=?',
                    (job, operands['page'], operands['page_size'])).fetchone()
                if cached:
                    with self.store.transaction():
                        return self._receipt(job, operation, key, selection, state='SUCCESS',
                            snapshot_ref=cached['snapshot_ref'], ready=True)
            if row['remote_id'] is None:
                prerequisite = None
                if row['state'] == 'not_submitted':
                    claim = self.store.db.execute('SELECT data FROM public_search_claims WHERE job_ref=? ORDER BY rowid DESC LIMIT 1', (job,)).fetchone()
                    if claim is None:
                        prerequisite = 'submission_claim_unavailable'
                    else:
                        submit_key = json.loads(claim[0])['operation_key']
                        prior = self.store.db.execute('SELECT id FROM public_search_operations WHERE operation_key=?', (submit_key,)).fetchone()
                        receipt = self.read_operation(prior[0]) if prior else None
                        if receipt and receipt['failure'] and receipt['failure']['submission_outcome'] == 'not_sent':
                            prerequisite = 'submission_not_sent'
                if prerequisite is not None:
                    return self._fail_receipt(job, operation, key, selection, 'prerequisite_missing',
                        native_code=prerequisite, phase=operation)
                return self._fail_receipt(job, operation, key, selection, 'submission_uncertain',
                    phase=operation, submission_outcome='unknown')
            if operation == 'result':
                ready = self._ready(job)
                if ready is not True:
                    code = 'result_readiness_unknown' if ready is None else 'remote_job_failed' if row['state'] in {'FAILURE','REVOKED'} else 'result_not_ready'
                    return self._fail_receipt(job, operation, key, selection, code, phase='result')
            client = self.remote_searches.clients
            callback = (lambda: client.hmmer_status(row['remote_id'])) if operation == 'status' else (
                lambda: client.hmmer_result(row['remote_id'], page=operands['page'], page_size=operands['page_size'], with_domains=True))
            if not self._capsule_path(key).exists():
                transfer = True
                try:
                    await self._dispatch(job, operation, key, selection, callback, descriptor)
                except asyncio.CancelledError:
                    raise
                except _DispatchNotSent:
                    return self._fail_receipt(job, operation, key, selection, 'client_failure',
                        phase='local_preflight', native_code='executor_dispatch_not_sent')
                except Exception:
                    return self._fail_receipt(job, operation, key, selection, 'storage_failure',
                        phase='storage', native_code='http_capture_publication_failed')
            with self.store.transaction():
                replay = self._replay(key, selection)
                if replay:
                    return replay
                try:
                    snapshot, reference, failure, diagnostic = self._import_capture(job, operation, key, selection)
                except ContractError:
                    return self._receipt(job, operation, key, selection,
                        failure=self._failure('storage_failure', job, native_code='http_capture_invalid', phase='storage'))
                if failure:
                    return self._receipt(job, operation, key, selection, snapshot_ref=reference,
                        failure=self._capture_failure(job, operation, failure, snapshot, reference, diagnostic))
                try:
                    native = json.loads(snapshot.content)
                    request = json.loads(row['request'])
                    validate_remote_identity(native, request, row['remote_id'], result=operation == 'result')
                    state = native['task']['status'] if operation == 'status' else native['status']
                    if state not in {'PENDING','RECEIVED','STARTED','RETRY','SUCCESS','FAILURE','REVOKED'}:
                        raise ValueError('unrecognized_status')
                    if operation == 'result' and state != 'SUCCESS':
                        code = 'remote_job_failed' if state in {'FAILURE','REVOKED'} else 'result_not_ready'
                        return self._receipt(job, operation, key, selection, state=state, snapshot_ref=reference,
                            ready=False, failure=self._failure(code, job, phase='result', snapshot_ref=reference))
                    if operation == 'result':
                        if not isinstance(native['result']['hits'], list):
                            raise ValueError('result_hits_required')
                        current = self.remote_searches._get(job)
                        details = json.loads(self.remote_searches._load_snapshot(current['latest_status']).content) if current['latest_status'] else None
                        snapshot = replace(snapshot, request={**request, 'job_id': row['remote_id'], **operands},
                            transport={**snapshot.transport, 'job_ref': job, 'job_details': details})
                        reference = self.store.artifact(self.remote_searches._snapshot(snapshot), 'application/json')
                        ref = identity('provider_operation', dict(registry_ref=self.registry['registry_ref'], operation_key=key))
                        self.store.db.execute('INSERT OR IGNORE INTO public_search_results VALUES(?,?,?,?,?)',
                            (job, operands['page'], operands['page_size'], ref, reference))
                        retained = self.store.db.execute('SELECT snapshot_ref FROM public_search_results WHERE job_ref=? AND page=? AND page_size=?',
                            (job, operands['page'], operands['page_size'])).fetchone()[0]
                        # Preserve the first validated capture for the selector.
                        values = dict(state='returned', error_code=None)
                        if operands['page'] == 1 and operands['page_size'] == request['page_size']:
                            values['result'] = self.store.get_artifact(retained).decode()
                        self.remote_searches._update(job, **values)
                    else:
                        self.remote_searches._update(job, state='returned' if self._cache(job) else state,
                            latest_status=self.remote_searches._snapshot(snapshot), error_code=None)
                    return self._receipt(job, operation, key, selection, state=state, snapshot_ref=reference, ready=state == 'SUCCESS')
                except (ValueError, TypeError, KeyError, AcquisitionError) as error:
                    code = 'remote_identity_conflict' if isinstance(error, AcquisitionError) and error.code.startswith('remote_identity_conflict') else 'response_invalid'
                    return self._receipt(job, operation, key, selection, snapshot_ref=reference,
                        failure=self._failure(code, job, native_code=getattr(error, 'code', 'provider_response_invalid'),
                                              phase=operation, snapshot_ref=reference))
        finally:
            if not transfer:
                os.close(descriptor)
