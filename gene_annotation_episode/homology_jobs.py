"""Durable one-query homology jobs and their functional communication handoff.

Ordinary tools for launch/monitor/results episodes use this service. It does
not choose those episodes, prescribe their order, score work, estimate yield,
interpret a match or label a process termination scientific completion.
"""
from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import time
import uuid

from Bio import SeqIO

from ._local_job_worker import atomic_json
from .acquisition import AcquisitionError
from .domain import canonical
from .communication import validate_form
from .local_jobs import LocalJobPolicy, check_scratch_budget
from .native_lifecycle import NativeJobHandle, collect, prepare_job, resume_start, start_prepared, status


VERSION = 'single_query_phmmer_jobs_v2'
SEARCH_MODES = {'native_defaults': (), 'maximum_sensitivity': ('--max',)}
OUTPUTS = {'native_text': 'native.stdout', 'native_stderr': 'native.stderr',
           'hit_table': 'hits.tbl', 'domain_table': 'domains.tbl'}


def _object(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


def _reference(namespace):
    return {'type': 'string', 'format': 'reference', 'x-reference-namespace': namespace}


HANDOFF_SCHEMA = _object({'job_ref': _reference('homology_job'), 'registry_ref': _reference('execution_registry'),
    'backend': {'type': 'string', 'enum': [VERSION]},
    'status_interface': {'type': 'string', 'enum': ['homology.status.v1']},
    'progress_interface': {'type': 'string', 'enum': ['homology.progress.v1']},
    'results_interface': {'type': 'string', 'enum': ['homology.results.v1']}})
STATUS_SCHEMA = _object({'job_ref': _reference('homology_job'), 'registry_ref': _reference('execution_registry'),
    'state': {'type': 'string', 'enum': ['not_submitted', 'prepared', 'submission_unconfirmed', 'starting', 'running', 'returned', 'execution_unknown']},
    'outcome': {'type': 'string', 'enum': ['pending', 'succeeded', 'failed', 'unknown']},
    'elapsed_seconds': {'type': ['number', 'null'], 'minimum': 0},
    'duration_measure': {'type': 'string', 'enum': ['systemd_service_wall_seconds']},
    'native_returncode': {'type': ['integer', 'null']},
    'failure_code': {'type': ['string', 'null'], 'enum': [None, 'native_nonzero_exit', 'local_job_resource_limit', 'local_job_execution_error']},
    'resource': {'type': ['string', 'null'], 'enum': [None, 'memory_bytes', 'scratch_bytes', 'file_bytes', 'wall_seconds']},
    'progress_kind': {'type': 'string', 'enum': ['native_execution_state_and_output_bytes_not_search_fraction']},
    'outputs': {'type': 'array', 'items': _object({
        'role': {'type': 'string', 'enum': list(OUTPUTS)}, 'available': {'type': 'boolean'},
        'bytes': {'type': ['integer', 'null'], 'minimum': 0}, 'writer_closed': {'type': 'boolean'}})}})
SAMPLE_SCHEMA = _object({'sample_ref': _reference('job_sample'),
    'sampled_at_unix_seconds': {'type': 'number', 'minimum': 0}, **STATUS_SCHEMA['properties']})


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            value.update(chunk)
    return value.hexdigest()


def ref(kind, value):
    return kind+'_'+hashlib.sha256(canonical(value).encode()).hexdigest()[:24]


def normalize_query_fasta(query_fasta):
    """One actual query sequence, shared by ordering and class construction."""
    record = SeqIO.read(io.StringIO(query_fasta), 'fasta')
    if not record.seq:
        raise ValueError('empty_homology_query')
    return '>query\n'+str(record.seq).upper()+'\n'


@dataclass(frozen=True)
class FileAsset:
    path: Path
    sha256: str

    def __post_init__(self):
        if len(self.sha256) != 64 or any(c not in '0123456789abcdef' for c in self.sha256):
            raise ValueError('file_asset_digest_required')
        object.__setattr__(self, 'path', Path(self.path).expanduser().resolve())

    def as_record(self):
        return {'path': str(self.path), 'sha256': self.sha256}


class HomologyJobs:
    @classmethod
    def create(cls, directory, *, executable: FileAsset, reference_database: FileAsset,
               policy: LocalJobPolicy, max_cpu: int, search_modes=None):
        if type(max_cpu) is not int or max_cpu < 1 or type(policy) is not LocalJobPolicy:
            raise ValueError('caller_owned_homology_resources_required')
        if search_modes is not None and (not isinstance(search_modes, (list, tuple)) or not search_modes
                or any(type(mode) is not str or mode not in SEARCH_MODES for mode in search_modes)
                or len(set(search_modes)) != len(search_modes)):
            raise ValueError('caller_owned_homology_search_modes_required')
        directory = Path(directory).expanduser().resolve()
        directory.mkdir(parents=True, exist_ok=False)
        configuration = {'version': VERSION, 'registry_ref': 'execution_registry_'+uuid.uuid4().hex,
            'executable': executable.as_record(), 'reference_database': reference_database.as_record(),
            'job_limits': policy.to_dict(), 'max_cpu': max_cpu}
        if search_modes is not None:
            configuration['search_modes'] = list(search_modes)
        atomic_json(directory/'configuration.json', configuration)
        with sqlite3.connect(directory/'jobs.sqlite') as db:
            db.executescript('''
            CREATE TABLE orders (job_ref TEXT PRIMARY KEY, operation_key TEXT UNIQUE NOT NULL,
                query_ref TEXT NOT NULL, query_fasta TEXT NOT NULL, cpu INTEGER NOT NULL, staged INTEGER NOT NULL,
                submission_requested INTEGER NOT NULL);
            CREATE TABLE handoffs (receipt_ref TEXT PRIMARY KEY,job_ref TEXT NOT NULL,body TEXT NOT NULL);
            CREATE TABLE samples (sample_ref TEXT PRIMARY KEY,operation_key TEXT UNIQUE NOT NULL,
                job_ref TEXT NOT NULL,body TEXT NOT NULL);
            ''')
            if search_modes is not None:
                db.execute('ALTER TABLE orders ADD COLUMN search_mode TEXT NOT NULL')
        return cls(directory)

    def __init__(self, directory):
        self.directory = Path(directory).expanduser().resolve()
        self.config = json.loads((self.directory/'configuration.json').read_text())
        if self.config['version'] != VERSION:
            raise ValueError('unsupported_homology_job_registry')
        self.db = sqlite3.connect((self.directory/'jobs.sqlite').as_uri()+'?mode=rw', uri=True)
        self.db.row_factory = sqlite3.Row

    def close(self):
        self.db.close()

    def _row(self, job_ref):
        row = self.db.execute('SELECT * FROM orders WHERE job_ref=?', (job_ref,)).fetchone()
        if row is None:
            raise ValueError('job_not_registered_here')
        return {**dict(row), 'search_mode': row['search_mode'] if 'search_mode' in row.keys() else 'native_defaults'}

    @property
    def search_modes(self):
        return tuple(self.config.get('search_modes', ['native_defaults']))

    def _command(self, row):
        if row.get('search_mode', 'native_defaults') not in self.search_modes:
            raise ValueError('registered_search_mode_outside_caller_configuration')
        return [self.config['executable']['path'], '--cpu', str(row['cpu']),
            *SEARCH_MODES[row.get('search_mode', 'native_defaults')], '--tblout', 'hits.tbl',
            '--domtblout', 'domains.tbl', 'query.faa', 'references.faa']

    def _directory(self, job_ref):
        self._row(job_ref)
        return self.directory/job_ref

    @contextmanager
    def _submission_lock(self, job_ref):
        self._row(job_ref)
        # Kernel ownership disappears on process exit; no stale-PID heuristic
        # or retry budget decides whether another launch action may proceed.
        with (self.directory/(job_ref+'.launch.lock')).open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def _has_intent(self, row):
        return bool(row['submission_requested'] or
                    (self.directory/row['job_ref']/'native.handle.json').is_file())

    def order(self, *, query_ref, query_fasta, cpu, operation_key, search_mode=None):
        """Record selected query/allocation; this does not stage or submit."""
        if type(query_ref) is not str or not query_ref or type(operation_key) is not str or not operation_key:
            raise ValueError('homology_operand_and_operation_required')
        if type(cpu) is not int or not 1 <= cpu <= self.config['max_cpu']:
            raise ValueError('cpu_outside_caller_allocation')
        if search_mode is None and 'search_modes' not in self.config:
            search_mode = 'native_defaults'
        if type(search_mode) is not str or search_mode not in self.search_modes:
            raise ValueError('search_mode_outside_caller_configuration_or_not_selected')
        normalized = normalize_query_fasta(query_fasta)
        old = self.db.execute('SELECT * FROM orders WHERE operation_key=?', (operation_key,)).fetchone()
        if old:
            old_mode = old['search_mode'] if 'search_mode' in old.keys() else 'native_defaults'
            if (old['query_ref'] != query_ref or old['query_fasta'] != normalized or old['cpu'] != cpu
                    or old_mode != search_mode):
                raise ValueError('homology_order_identity_conflict')
            return old['job_ref']
        operands = [self.config['registry_ref'], operation_key, query_ref, normalized, cpu]
        if 'search_modes' in self.config:
            operands.append(search_mode)
        job_ref = ref('homology_job', operands)
        with self.db:
            if 'search_modes' in self.config:
                self.db.execute('INSERT INTO orders VALUES(?,?,?,?,?,0,0,?)',
                                (job_ref, operation_key, query_ref, normalized, cpu, search_mode))
            else:
                self.db.execute('INSERT INTO orders VALUES(?,?,?,?,?,0,0)',
                                (job_ref, operation_key, query_ref, normalized, cpu))
        return job_ref

    def environment(self, job_ref):
        row = self._row(job_ref)
        return {'job_ref': job_ref, 'executable_exists': Path(self.config['executable']['path']).is_file(),
            'reference_database_exists': Path(self.config['reference_database']['path']).is_file(),
            'max_cpu': self.config['max_cpu'], 'configured_cpu': row['cpu'], 'staged': bool(row['staged']),
            'submission_requested': self._has_intent(row), 'job_limits': self.config['job_limits'],
            **({'configured_search_mode': row['search_mode']} if 'search_modes' in self.config else {})}

    def configure(self, job_ref, cpu):
        with self._submission_lock(job_ref):
            return self._configure(job_ref, cpu)

    def _configure(self, job_ref, cpu):
        row = self._row(job_ref)
        if type(cpu) is not int or not 1 <= cpu <= self.config['max_cpu']:
            raise ValueError('cpu_outside_caller_allocation')
        if cpu != row['cpu']:
            raise ValueError('selected_job_cpu_is_immutable')
        if self._has_intent(row):
            return self.environment(job_ref)
        program = self.config['executable']
        if not os.access(program['path'], os.X_OK) or digest(program['path']) != program['sha256']:
            raise ValueError('configured_executable_unavailable_or_changed')
        return self.environment(job_ref)

    def stage(self, job_ref):
        with self._submission_lock(job_ref):
            return self._stage(job_ref)

    def _stage(self, job_ref):
        row = self._row(job_ref)
        directory = self._directory(job_ref)
        handle = self._handle(job_ref)
        reserved = handle.path.is_file() and handle.read()['stage'] == 'prepared'
        if self._has_intent(row) and not reserved:
            if row['staged']:
                return self.environment(job_ref)
            raise ValueError('submitted_job_inputs_are_immutable')
        database = self.config['reference_database']
        reference_ready = ((directory/'references.faa').is_file()
                           and digest(directory/'references.faa') == database['sha256'])
        query_ready = (directory/'query.faa').is_file() and (directory/'query.faa').read_text() == row['query_fasta']
        if row['staged'] and reference_ready and query_ready:
            return self.environment(job_ref)
        directory.mkdir(exist_ok=True)
        policy = LocalJobPolicy(**self.config['job_limits'])
        source = Path(database['path'])
        additional = (0 if reference_ready else source.stat().st_size) + (0 if query_ready else len(row['query_fasta'].encode()))
        check_scratch_budget(directory, policy, additional_bytes=additional)
        # A private snapshot avoids shared ownership of mutable input bytes.
        # The original database remains reusable; no network acquisition occurs.
        if not reference_ready:
            shutil.copyfile(source, directory/'references.faa')
            if digest(directory/'references.faa') != database['sha256']:
                raise ValueError('reference_database_bytes_changed')
        if not query_ready:
            (directory/'query.faa').write_text(row['query_fasta'])
        check_scratch_budget(directory, policy)
        with self.db:
            self.db.execute('UPDATE orders SET staged=1 WHERE job_ref=?', (job_ref,))
        return self.environment(job_ref)

    def submit(self, job_ref, *, statistics=None, native_events=None):
        with self._submission_lock(job_ref):
            return self._submit(job_ref, statistics=statistics, native_events=native_events)

    def _validate_inputs(self, row):
        directory, program = self._directory(row['job_ref']), self.config['executable']
        if (digest(program['path']) != program['sha256'] or
                digest(directory/'references.faa') != self.config['reference_database']['sha256'] or
                (directory/'query.faa').read_text() != row['query_fasta']):
            raise ValueError('prepared_job_dependency_changed')

    def _submit(self, job_ref, *, statistics=None, native_events=None):
        if statistics is not None:
            from .execution_recording import HomologyStatistics
            if type(statistics) is not HomologyStatistics:
                raise TypeError('typed_homology_statistics_binding_required')
        row = self._row(job_ref)
        handle = self._handle(job_ref)
        self._validate_native_event_binding(job_ref, handle, native_events)
        if row['submission_requested'] and not handle.path.is_file():
            # A missing reservation for a recorded request is corruption or an
            # older incomplete protocol. Absence does not authorize execution.
            return {'job_ref': job_ref, 'new_submission': False, 'status': self.status(job_ref)}
        if handle.path.is_file() and handle.read()['stage'] != 'prepared':
            return {'job_ref': job_ref, 'new_submission': False, 'status': self.status(job_ref)}
        if row['cpu'] is None or not row['staged']:
            raise ValueError('configured_execution_and_staged_inputs_required')
        directory = self._directory(job_ref)
        program = self.config['executable']
        self._validate_inputs(row)
        if not handle.path.is_file():
            command = self._command(row)
            context = None if statistics is None else statistics.for_job(self, row)
            handle = prepare_job(command, cwd=directory, policy=LocalJobPolicy(**self.config['job_limits']),
                handle_path=directory/'native.handle.json', stdout_path=directory/OUTPUTS['native_text'],
                stderr_path=directory/OUTPUTS['native_stderr'], statistics=context, native_events=native_events,
                cpu_threads=row['cpu'])
        elif statistics is not None:
            recorded = handle.read().get('statistics')
            expected = statistics.for_job(self, row).as_record()
            if recorded != expected:
                raise ValueError('prepared_statistics_binding_is_immutable')
        # A complete native reservation now precedes the registry marker. A
        # replay can finish dispatch of exactly this never-submitted unit.
        with self.db:
            self.db.execute('UPDATE orders SET submission_requested=1 WHERE job_ref=?', (job_ref,))
        start_prepared(handle)
        return {'job_ref': job_ref, 'new_submission': True, 'status': self.status(job_ref)}

    def _validate_native_event_binding(self, job_ref, handle, native_events):
        from .native_events import NativeEventBinding
        if native_events is not None:
            if type(native_events) is not NativeEventBinding:
                raise TypeError('typed_native_event_binding_required')
            if (native_events.job_ref != job_ref or native_events.registry_ref != self.config['registry_ref']):
                raise ValueError('native_event_binding_identity_conflict')
            if handle.path.is_file() and handle.read().get('native_events') != native_events.as_record():
                raise ValueError('prepared_native_event_binding_is_immutable')

    def native_event_binding(self, job_ref):
        """Read the original reservation binding, including prepared work."""
        from .native_events import NativeEventBinding
        handle = self._handle(job_ref)
        if not handle.path.is_file():
            return None
        value = handle.read().get('native_events')
        if value is None:
            return None
        binding = NativeEventBinding.from_record(value)
        if binding.job_ref != job_ref or binding.registry_ref != self.config['registry_ref']:
            raise ValueError('native_event_binding_identity_conflict')
        return binding

    def native_event_targets(self, job_ref):
        """Read existing registration only; never register, export or poll."""
        from method_loop.durable import native_target_descriptor, read_native_target
        from .native_events import _handle, _registration
        handle = self._handle(job_ref)
        binding = self.native_event_binding(job_ref)
        if binding is None:
            return []
        _, _, identity = _handle(handle.path)
        registration = _registration(binding, identity)
        if not (binding.execution_directory/'executions.sqlite').is_file():
            return []
        try:
            actual = read_native_target(binding.execution_directory, registration['handle'])
        except (FileNotFoundError, KeyError):
            return []
        if actual != registration:
            raise ValueError('native_event_binding_identity_conflict')
        return [native_target_descriptor(actual)]

    def recover_native_events(self, *, native_event_provider, job_ref=None):
        """Export only receipts bound to this exact host run and resource."""
        from .native_events import NativeEventProvider, publish_native_events
        if type(native_event_provider) is not NativeEventProvider:
            raise TypeError('typed_native_event_provider_required')
        rows = ([self._row(job_ref)] if job_ref is not None else
                self.db.execute('SELECT job_ref FROM orders'))
        for row in rows:
            # Authenticate the reservation before any event-store or native
            # diagnostic write. Foreign and unbound jobs remain untouched.
            try:
                binding = self.native_event_binding(row['job_ref'])
            except (OSError, ValueError, KeyError, TypeError):
                continue
            if binding is None or any(getattr(binding, key) != getattr(native_event_provider, key)
                    for key in ('execution_directory', 'run_id', 'resource_id')):
                continue
            path = self._directory(row['job_ref'])/'native.handle.json'
            yield publish_native_events(path)

    def recover_statistics(self, job_ref=None):
        """Retry only receipt export, never execution or an episode decision."""
        from .execution_recording import publish_native_statistics
        rows = ([self._row(job_ref)] if job_ref is not None else
                self.db.execute('SELECT job_ref FROM orders WHERE submission_requested=1'))
        for row in rows:
            path = self._directory(row['job_ref'])/'native.handle.json'
            if not path.is_file():
                continue
            try:
                value = publish_native_statistics(path)
            except (OSError, ValueError, KeyError, TypeError) as error:
                # The standard export receipt cannot be reached/read. Preserve
                # an actionable infrastructure failure outside native outputs.
                value = {'state': 'unavailable', 'code': 'statistics_receipt_unreadable',
                         'exception_type': type(error).__name__}
                try:
                    atomic_json(path.parent/'statistics_recovery.json', value)
                except OSError:
                    # Optional statistics must not erase already returned work
                    # even when its job-owned diagnostic cannot be persisted.
                    value['diagnostic_persisted'] = False
            else:
                try:
                    (path.parent/'statistics_recovery.json').unlink(missing_ok=True)
                except OSError:
                    # A stale diagnostic's cleanup is not failure to export
                    # the actual measurement. Keep those meanings distinct.
                    value['diagnostic_cleanup_failed'] = True
            yield {'job_ref': row['job_ref'], **value}

    def resume_start(self, job_ref, *, native_events=None):
        with self._submission_lock(job_ref):
            handle = self._handle(job_ref)
            self._validate_native_event_binding(job_ref, handle, native_events)
            if handle.path.is_file() and handle.read()['stage'] == 'prepared':
                self._submit(job_ref, native_events=native_events)
            else:
                resume_start(handle)
            return self.status(job_ref)

    def _handle(self, job_ref):
        row = self._row(job_ref)
        directory = self._directory(job_ref)
        handle = NativeJobHandle(directory/'native.handle.json')
        if handle.path.exists():
            body = handle.read()
            expected = self._command(row)
            if (body['cwd'] != str(directory) or body['command'] != expected or
                    body['metadata']['policy'] != self.config['job_limits'] or
                    body['stdout'] != str(directory/OUTPUTS['native_text']) or
                    body['stderr'] != str(directory/OUTPUTS['native_stderr'])):
                raise ValueError('native_handle_does_not_describe_registered_job')
        return handle

    def status(self, job_ref):
        row = self._row(job_ref)
        directory = self._directory(job_ref)
        handle = self._handle(job_ref)
        view = status(handle) if handle.path.exists() else None
        state = (view['state'] if view else 'submission_unconfirmed' if row['submission_requested'] else 'not_submitted')
        terminal = view is not None and view['terminal']
        outcome, failure, resource, code = 'pending', None, None, None
        if terminal:
            try:
                returned = collect(handle)
                code = returned.returncode
                outcome = 'succeeded' if code == 0 else 'failed'
                failure = 'native_nonzero_exit' if code != 0 else None
            except AcquisitionError as error:
                outcome, failure = 'failed', error.code
                resource = (error.operational or {}).get('resource')
                code = (error.operational or {}).get('native_returncode')
        elif state in {'execution_unknown', 'submission_unconfirmed'}:
            outcome = 'unknown'
        outputs = []
        for role, name in OUTPUTS.items():
            path = directory/name
            exists = path.is_file()
            outputs.append({'role': role, 'available': exists, 'bytes': path.stat().st_size if exists else None,
                            'writer_closed': terminal and exists})
        return {'job_ref': job_ref, 'registry_ref': self.config['registry_ref'], 'state': state,
            'outcome': outcome, 'elapsed_seconds': view['metadata']['elapsed_seconds'] if view else None,
            'duration_measure': 'systemd_service_wall_seconds',
            'native_returncode': code, 'failure_code': failure, 'resource': resource,
            'progress_kind': 'native_execution_state_and_output_bytes_not_search_fraction', 'outputs': outputs}

    def handoff(self, job_ref):
        row = self._row(job_ref)
        if not row['submission_requested'] or not (self._directory(job_ref)/'native.handle.json').is_file():
            raise ValueError('job_submission_handoff_unresolved')
        if self._handle(job_ref).read()['stage'] == 'prepared':
            raise ValueError('job_submission_handoff_unresolved')
        return {'job_ref': job_ref, 'registry_ref': self.config['registry_ref'], 'backend': VERSION,
            'status_interface': 'homology.status.v1', 'progress_interface': 'homology.progress.v1',
            'results_interface': 'homology.results.v1'}

    def receive(self, handoff):
        validate_form(handoff, HANDOFF_SCHEMA, self.resolve)
        if not isinstance(handoff, dict) or handoff != self.handoff(handoff.get('job_ref')):
            raise ValueError('homology_handoff_identity_or_interface_mismatch')
        sample = self.status(handoff['job_ref'])
        return validate_form(sample, STATUS_SCHEMA, self.resolve)

    def check_handoff(self, handoff):
        # Exactly the receiving interface on a NEW persistent connection. No
        # launching object's process, database connection or memory is needed.
        receiver = type(self)(self.directory)
        try:
            sample = receiver.receive(handoff)
        finally:
            receiver.close()
        receipt = ref('handoff_receipt', handoff)
        checked_at = time.time()
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO handoffs VALUES(?,?,?)',
                (receipt, handoff['job_ref'], canonical({'handoff': handoff,
                    'first_checked_at_unix_seconds': checked_at, 'first_sample': sample})))
        return {'receipt_ref': receipt, 'handoff': handoff, 'sample': sample,
                'checked_at_unix_seconds': checked_at}

    def sample(self, handoff, *, operation_key):
        old = self.db.execute('SELECT job_ref,body FROM samples WHERE operation_key=?', (operation_key,)).fetchone()
        if old:
            if old['job_ref'] != handoff['job_ref']:
                raise ValueError('monitoring_sample_identity_conflict')
            if handoff != self.handoff(handoff.get('job_ref')):
                raise ValueError('homology_handoff_identity_or_interface_mismatch')
            return json.loads(old['body'])
        body = self.receive(handoff)
        body = {'sample_ref': ref('job_sample', [handoff, operation_key]),
                'sampled_at_unix_seconds': time.time(), **body}
        with self.db:
            self.db.execute('INSERT INTO samples VALUES(?,?,?,?)',
                (body['sample_ref'], operation_key, handoff['job_ref'], canonical(body)))
        return body

    def result_file(self, handoff, role):
        self.receive(handoff)
        if role not in OUTPUTS:
            raise ValueError('unknown_homology_result_role')
        path = self._directory(handoff['job_ref'])/OUTPUTS[role]
        if not path.is_file():
            raise ValueError('homology_result_not_available')
        return path

    def resolve(self, value, namespace):
        if namespace is None:
            return any(self.resolve(value, kind) for kind in
                       ('execution_registry', 'homology_job', 'handoff_receipt', 'job_sample'))
        if namespace == 'execution_registry':
            return value == self.config['registry_ref']
        tables = {'homology_job': ('orders', 'job_ref'), 'handoff_receipt': ('handoffs', 'receipt_ref'),
                  'job_sample': ('samples', 'sample_ref')}
        if namespace not in tables:
            return False
        table, column = tables[namespace]
        return self.db.execute(f'SELECT 1 FROM {table} WHERE {column}=?', (value,)).fetchone() is not None
