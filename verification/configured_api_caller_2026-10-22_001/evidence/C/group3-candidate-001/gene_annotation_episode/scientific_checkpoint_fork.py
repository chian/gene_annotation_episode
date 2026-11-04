"""Read-only custody of one explicitly stopped, job-free fixed-gene source.

This caller preparation creates no episode and recovers no original execution.
The source never enters Store. Only a new private working copy receives the two
declared lineage sources; its independent checkpoint keeps every original byte.
"""
from __future__ import annotations

from contextlib import contextmanager
import ctypes
from datetime import datetime, timezone
import errno
import hashlib
import heapq
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import struct
import tempfile
import uuid

from method_loop.identities import EpisodeRef, UnitRef

from .domain import ContractError, canonical, identity
from .materials import source_window
from . import materials_packing as packing
from .native_timing_information import NativeTimingInformation
from .resource_estimation import ResourceToolEstimator
from .state import Store


VERSION = 'scientific_checkpoint_fork_v1'
_HEX = re.compile(r'[a-f0-9]{64}\Z')
_REF = re.compile(r'[a-z][a-z_]*_[a-f0-9]{24,64}\Z')
_RUN = re.compile(r'run_[a-f0-9]{32}\Z')
_EMPTY = ('provider_jobs', 'provider_job_failures', 'runtime_commission_intents',
          'runtime_timed_commissions', 'runtime_forms', 'runtime_report_attempts')
_LIMITS = ['new_workspace_not_same_episode_migration', 'no_old_job_adoption',
    'no_relocated_old_run_resumability', 'no_new_scientific_or_monitoring_credit',
    'external_paths_retained_as_original_provenance',
    'source_run_and_policy_parameters_not_rebound',
    'later_new_caller_configuration_and_execution_separately_authorized']


class ScientificCheckpointForkError(ValueError):
    """Closed failure with truthful, possibly unknown, retained locations."""
    def __init__(self, code, *, phase='validate_request', affected_refs=(),
                 staging_workspace=None, published_workspace=None,
                 publication_state='not_created', source_unchanged=None,
                 cause=None, error_number=None):
        self.failure = {'version': 'scientific_checkpoint_fork_failure_v1',
            'code': code, 'phase': phase,
            'affected_refs': list(dict.fromkeys(str(ref) for ref in affected_refs)),
            'staging_workspace': None if staging_workspace is None else str(staging_workspace),
            'published_workspace': None if published_workspace is None else str(published_workspace),
            'publication_state': publication_state, 'source_unchanged': source_unchanged,
            'cause': cause, 'errno': error_number}
        super().__init__(canonical(self.failure))

    def as_record(self):
        return json.loads(canonical(self.failure))


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate_json_key')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('nonfinite_json')
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    canonical(value)
    return value


def _path(value):
    if not isinstance(value, (str, Path)):
        raise ValueError('path_operand_required')
    path = Path(value).expanduser().absolute()
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError('symlink_path')
    return path.resolve()


def _file(path):
    path = _path(path)
    return _owned_file(path)


def _owned_file(path):
    """Hash an internal fd-anchored file without resolving its directory alias."""
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('regular_file_required')
    digest, size = hashlib.sha256(), 0
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('regular_file_required')
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
            size += len(chunk)
    return {'path': str(path), 'sha256': digest.hexdigest(), 'bytes': size}


def _optional_file(path):
    return _file(path) if os.path.lexists(path) else None


def _copy_file(source, target, expected, *, mode=0o600):
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    digest, size = hashlib.sha256(), 0
    source_fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        target_fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    except BaseException:
        os.close(source_fd)
        raise
    with os.fdopen(source_fd, 'rb') as reader, os.fdopen(target_fd, 'wb') as writer:
        for chunk in iter(lambda: reader.read(1024 * 1024), b''):
            writer.write(chunk)
            digest.update(chunk)
            size += len(chunk)
        writer.flush()
        os.fsync(writer.fileno())
    if digest.hexdigest() != expected['sha256'] or size != expected['bytes']:
        raise ValueError('copied_bytes_mismatch')
    target.chmod(mode)


def _write_json(path, value, *, mode=0o444):
    raw = (canonical(value) + '\n').encode('utf-8')
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(mode)
    return {'path': str(path), 'sha256': _sha(raw), 'bytes': len(raw)}


def _relative_file(path, root):
    value = _owned_file(path)
    value['path'] = str(path.relative_to(root))
    return value


def _source_files(root):
    files = []
    digest = hashlib.sha256()
    for package in ('gene_annotation_episode', 'method_loop'):
        if not (root / package).is_dir():
            raise ValueError('source_package_missing')
    for path in sorted(path for package in ('gene_annotation_episode', 'method_loop')
                       for path in (root / package).rglob('*.py')):
        value = _file(path)
        relative = str(path.relative_to(root))
        digest.update(relative.encode('utf-8') + b'\0')
        digest.update(bytes.fromhex(value['sha256']))
        files.append({'relative_path': relative, 'sha256': value['sha256'], 'bytes': value['bytes']})
    if not files:
        raise ValueError('source_files_missing')
    return {'version': 'scientific_checkpoint_source_file_inventory_v1',
        'source_implementation_root': str(root), 'implementation_sha256': digest.hexdigest(), 'files': files}


def _database_files(path):
    return {'database': _file(path), 'wal': _optional_file(Path(str(path) + '-wal')),
            'shm': _optional_file(Path(str(path) + '-shm'))}


@contextmanager
def _readonly(path):
    # Callers verify the absent/empty WAL before this immutable open.
    db = sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        yield db
    finally:
        db.close()


def _quote(value):
    return '"' + value.replace('"', '""') + '"'


def _schema(db):
    objects = [dict(type=row[0], name=row[1], table_name=row[2], sql=row[3]) for row in db.execute(
        'SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type COLLATE BINARY,name COLLATE BINARY')]
    virtual = {row[1] for row in db.execute('PRAGMA table_list') if row[0] == 'main' and row[2] in {'virtual', 'shadow'}}
    if virtual:
        raise ValueError('unsupported_virtual_schema')
    for obj in objects:
        if obj['type'] == 'table' and any(row[6] for row in db.execute('PRAGMA table_xinfo(' + _quote(obj['name']) + ')')):
            raise ValueError('unsupported_hidden_schema')
    return objects


def _length(value):
    return struct.pack('>Q', len(value)) + value


def _row_payload(row):
    parts = []
    for index in range(0, len(row), 3):
        kind, number, blob = row[index:index + 3]
        if kind == 'null':
            tag, payload = b'N', b''
        elif kind == 'integer':
            tag, payload = b'I', str(number).encode('ascii')
        elif kind == 'real':
            tag, payload = b'R', struct.pack('>d', number)
        elif kind == 'text':
            tag, payload = b'T', blob
        elif kind == 'blob':
            tag, payload = b'B', blob
        else:
            raise ValueError('unsupported_sqlite_storage_class')
        parts.append(tag + _length(payload))
    return b''.join(parts)


def _read_frames(path):
    with path.open('rb') as stream:
        while prefix := stream.read(8):
            if len(prefix) != 8:
                raise ValueError('sort_frame_truncated')
            size = struct.unpack('>Q', prefix)[0]
            value = stream.read(size)
            if len(value) != size:
                raise ValueError('sort_frame_truncated')
            yield value


def _table_manifest(db, scratch, *, excluded=None):
    """Disk merge-sort preserves typed row multiplicity without large lists."""
    objects, tables = _schema(db), []
    excluded = excluded or {}
    for obj in objects:
        if obj['type'] != 'table':
            continue
        table = obj['name']
        columns = [row[1] for row in db.execute('PRAGMA table_info(' + _quote(table) + ')')]
        selected = []
        for column in columns:
            q = _quote(column)
            selected.extend(['typeof(' + q + ')',
                "CASE WHEN typeof(" + q + ") IN ('integer','real') THEN " + q + ' END',
                'CAST(' + q + ' AS BLOB)'])
        ignored = sorted(excluded.get(table, ()))
        where = (' WHERE id NOT IN (' + ','.join('?' for _ in ignored) + ')') if ignored else ''
        query = 'SELECT ' + ','.join(selected) + ' FROM ' + _quote(table) + where
        count = 0
        runs, buffered, buffered_bytes = [], [], 0
        def flush():
            nonlocal buffered, buffered_bytes
            if not buffered:
                return
            descriptor, name = tempfile.mkstemp(prefix='.row-sort-', dir=scratch)
            path = Path(name)
            with os.fdopen(descriptor, 'wb') as stream:
                for value in sorted(buffered):
                    stream.write(_length(value))
            runs.append(path)
            buffered, buffered_bytes = [], 0
        try:
            for row in db.execute(query, ignored):
                value = _row_payload(row)
                buffered.append(value)
                buffered_bytes += len(value)
                count += 1
                if buffered_bytes >= 8 * 1024 * 1024:
                    flush()
            flush()
            digest = hashlib.sha256(b'sqlite_storage_class_frame_v1\0')
            digest.update(_length(table.encode('utf-8')))
            digest.update(struct.pack('>Q', len(columns)))
            for column in columns:
                digest.update(_length(column.encode('utf-8')))
            digest.update(struct.pack('>Q', count))
            for value in heapq.merge(*(_read_frames(path) for path in runs)):
                digest.update(_length(value))
            tables.append({'name': table, 'column_names': columns, 'row_count': count,
                           'typed_rows_sha256': digest.hexdigest()})
        finally:
            # Only disposable, newly generated sorting scratch is removed.
            # Original/checkpoint/working/partial scientific custody is retained.
            for path in runs:
                path.unlink(missing_ok=True)
    return {'version': 'sqlite_typed_row_inventory_v1', 'encoding': 'sqlite_storage_class_frame_v1',
        'database_encoding': db.execute('PRAGMA encoding').fetchone()[0],
        'schema_objects': objects, 'tables': tables}


def _refs(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if (key.endswith('_ref') or key == 'ref') and child is not None:
                yield child
            elif key.endswith('_refs') or key == 'dependencies':
                yield from child
            else:
                yield from _refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from _refs(child)


def _resolve(db, reference):
    for table in ('inputs', 'records', 'material_members'):
        row = db.execute('SELECT data FROM ' + table + ' WHERE id=?', (reference,)).fetchone()
        if row is not None:
            record = _json(row[0])
            if record.get('id') != reference:
                raise ValueError('record_identity_mismatch')
            return record
    row = db.execute('SELECT * FROM artifacts WHERE id=?', (reference,)).fetchone()
    if row is not None:
        return {**dict(row), 'record_type': 'artifact'}
    raise ValueError('unresolved_reference')


def _known_inventory(db):
    rows, known = [], set()
    for table in ('inputs', 'records'):
        fields = 'id,data' + (',record_type' if table == 'records' else '')
        for row in db.execute('SELECT ' + fields + ' FROM ' + table + ' ORDER BY id COLLATE BINARY'):
            record = _json(row['data'])
            if record.get('id') != row['id'] or not isinstance(record.get('record_type'), str):
                raise ValueError('record_identity_mismatch')
            if record['record_type'] != ('input' if table == 'inputs' else row['record_type']):
                raise ValueError('record_kind_mismatch')
            known.add(row['id'])
            raw = row['data'].encode('utf-8')
            rows.append({'reference': row['id'], 'record_type': record['record_type'],
                'source_table': table, 'data_raw_utf8_sha256': _sha(raw), 'data_raw_utf8_bytes': len(raw)})
    return {'version': 'scientific_checkpoint_committed_reference_inventory_v1',
        'input_count': sum(row['source_table'] == 'inputs' for row in rows),
        'record_count': sum(row['source_table'] == 'records' for row in rows), 'records': rows}, known


def _verified_location(parent_fd, child_name, child_identity):
    """Return a current pathname only after fd and pathname identities agree."""
    try:
        parent = Path(os.readlink(f'/proc/self/fd/{parent_fd}'))
        if not parent.is_absolute() or not parent.is_dir() or parent.is_symlink():
            return None
        pinned, actual = os.fstat(parent_fd), parent.stat(follow_symlinks=False)
        child = parent / child_name
        child_stat = child.stat(follow_symlinks=False)
        if ((pinned.st_dev, pinned.st_ino) != (actual.st_dev, actual.st_ino)
                or not stat.S_ISDIR(child_stat.st_mode)
                or (child_stat.st_dev, child_stat.st_ino) != child_identity):
            return None
        return child
    except (OSError, ValueError):
        return None


class _Custody:
    def __init__(self):
        self.phase = 'validate_request'
        self.parent_fd = None
        self.stage_name = None
        self.stage_fd = None
        self.stage_identity = None
        self.destination = None
        self.renamed = False
        self.durable = False
        self.source_unchanged = None
        self.files = {}

    def capture(self, path):
        value = _optional_file(path)
        self.files[str(path)] = value
        return value

    def verify_source(self):
        changed = [name for name, expected in self.files.items() if _optional_file(Path(name)) != expected]
        self.source_unchanged = not changed
        if changed:
            self.fail('source_changed', *changed)

    def fail(self, code, *references, cause=None, error_number=None):
        stage = published = None
        state = 'not_created'
        if self.stage_name is not None:
            child_name = self.destination.name if self.renamed else self.stage_name
            located = _verified_location(self.parent_fd, child_name, self.stage_identity)
            if self.renamed:
                published = located
                state = 'published_location_unconfirmed' if self.durable else 'published_durability_unconfirmed'
            else:
                stage, state = located, 'retained_stage'
        actual = stage if stage is not None else published
        if actual is not None:
            references = (*references, actual)
        raise ScientificCheckpointForkError(code, phase=self.phase, affected_refs=references,
            staging_workspace=stage, published_workspace=published, publication_state=state,
            source_unchanged=self.source_unchanged, cause=cause, error_number=error_number)


def _create_stage(custody):
    """Creation and all later writes stay relative to the owned directory fd."""
    name = '.' + custody.destination.name + '.checkpoint-' + uuid.uuid4().hex
    os.mkdir(name, mode=0o700, dir_fd=custody.parent_fd)
    custody.stage_name = name
    custody.stage_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=custody.parent_fd)
    os.fchmod(custody.stage_fd, 0o700)
    selected = os.fstat(custody.stage_fd)
    custody.stage_identity = (selected.st_dev, selected.st_ino)
    return Path('/proc/self/fd') / str(custody.stage_fd)


class _WorkspacePath:
    """Only Store's database operand is memory; all other paths use our fd."""
    def __init__(self, anchor, uri):
        self.anchor, self.uri = anchor, uri

    def __truediv__(self, name):
        return self.uri if name == 'state.sqlite3' else self.anchor / name

    def mkdir(self, **kwargs):
        return self.anchor.mkdir(**kwargs)


class _PinnedStore(Store):
    def __init__(self, anchor, *, stage_fd, database_uri):
        self._stage_fd, self._database_uri = stage_fd, database_uri
        super().__init__(anchor)

    @property
    def path(self):
        return self._workspace_path

    @path.setter
    def path(self, value):
        # The original constructor resolves its argument before assigning it.
        # Validate that result, then discard the pathname before any write.
        selected, actual = os.fstat(self._stage_fd), value.stat(follow_symlinks=False)
        if (selected.st_dev, selected.st_ino) != (actual.st_dev, actual.st_ino):
            raise ValueError('destination_stage_identity_changed')
        anchor = Path('/proc/self/fd') / str(self._stage_fd)
        self._workspace_path = _WorkspacePath(anchor, self._database_uri)


@contextmanager
def _memory_store(stage, custody):
    """Copy NEW checkpoint pages; run the unchanged real Store constructor."""
    uri = (stage / ('.custody-memory-' + uuid.uuid4().hex)).as_uri() + '?mode=memory&cache=shared'
    owner = sqlite3.connect(uri, uri=True, isolation_level=None)
    try:
        options = {row[0] for row in owner.execute('PRAGMA compile_options')}
        if 'USE_URI' not in options or 'OMIT_SHARED_CACHE' in options or not hasattr(owner, 'serialize'):
            raise ValueError('supported_shared_memory_sqlite_required')
        with _readonly(stage / 'checkpoint/state.sqlite3') as checkpoint:
            checkpoint.backup(owner)
        with _PinnedStore(stage, stage_fd=custody.stage_fd, database_uri=uri) as store:
            # Actual compiled SQLite must honor URI memory mode on Store's
            # existing connect call. A disk/independent database is rejected.
            if any(row[2] for row in store.db.execute('PRAGMA database_list') if row[1] == 'main'):
                raise ValueError('shared_memory_database_required')
            yield store
        image = owner.serialize()
        descriptor = os.open('state.sqlite3', os.O_WRONLY | os.O_NOFOLLOW, dir_fd=custody.stage_fd)
        try:
            actual = os.fstat(descriptor)
            if (not stat.S_ISREG(actual.st_mode)
                    or (actual.st_dev, actual.st_ino) != custody.working_identity):
                raise ValueError('working_database_identity_changed')
            os.ftruncate(descriptor, 0)
            with os.fdopen(descriptor, 'wb', closefd=False) as stream:
                stream.write(image)
                stream.flush()
                os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        owner.close()


def _publish(custody, stage):
    """No replace; final requested pathname identity is the success instant."""
    destination, parent_fd = custody.destination, custody.parent_fd
    pinned = os.fstat(parent_fd)
    try:
        parent = destination.parent.stat(follow_symlinks=False)
    except OSError:
        custody.fail('publication_failure', destination, destination.parent, cause='io_error')
    if (parent.st_dev, parent.st_ino) != (pinned.st_dev, pinned.st_ino):
        custody.fail('publication_failure', destination, destination.parent, cause='contract_error')
    library = ctypes.CDLL(None, use_errno=True)
    rename = getattr(library, 'renameat2', None)
    if rename is None:
        custody.fail('publication_failure', destination, cause='unsupported_platform')
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(parent_fd, os.fsencode(custody.stage_name), parent_fd, os.fsencode(destination.name), 1) != 0:
        number = ctypes.get_errno()
        custody.fail('destination_exists' if number == errno.EEXIST else 'publication_failure', destination,
                     cause='io_error', error_number=number)
    custody.renamed = True
    try:
        os.fsync(parent_fd)
    except OSError as error:
        custody.fail('publication_failure', destination, cause='io_error', error_number=error.errno)
    custody.durable = True
    location = _verified_location(parent_fd, destination.name, custody.stage_identity)
    if location != destination:
        custody.fail('publication_failure', destination, destination.parent, cause='contract_error')
    return destination


def _sync_tree(stage):
    directories = [stage]
    for path in stage.rglob('*'):
        if path.is_symlink():
            raise ValueError('staging_symlink')
        if path.is_dir():
            path.chmod(0o700)
            directories.append(path)
        else:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    for path in reversed(directories):
        # The root is the owned proc-fd alias, rather than an untrusted link.
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | (0 if path == stage else os.O_NOFOLLOW))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _read_authority(custody, path):
    witness = custody.capture(path)
    if witness is None:
        custody.fail('source_unavailable', path)
    return _json(path.read_bytes())


def _capture_database(custody, path):
    before = {name: custody.capture(candidate) for name, candidate in (
        ('database', path), ('wal', Path(str(path) + '-wal')), ('shm', Path(str(path) + '-shm')))}
    if before['database'] is None:
        custody.fail('source_unavailable', path)
    if before['wal'] is not None and before['wal']['bytes']:
        custody.fail('source_nonempty_wal_out_of_scope', Path(str(path) + '-wal'))
    return before


def _source_authority(custody, db, workspace, directory, source_root, run_id, expected_pin, pending_hash):
    manifest = _read_authority(custody, directory / 'run.json')
    case_launch = _read_authority(custody, directory / 'case-launch.json')
    policy = _read_authority(custody, directory / 'policy-binding.json')
    binding = _read_authority(custody, directory / 'episode-execution-binding.json')
    runs = db.execute('SELECT * FROM runtime_runs').fetchall()
    episodes = db.execute('SELECT * FROM runtime_episodes').fetchall()
    if len(runs) != 1 or len(episodes) != 1 or runs[0]['run_id'] != run_id or episodes[0]['run_id'] != run_id:
        custody.fail('source_execution_inventory_out_of_scope', run_id)
    settings = _json(runs[0]['settings'])
    problem_rows = db.execute('SELECT data FROM problem').fetchall()
    if len(problem_rows) != 1:
        custody.fail('source_identity_mismatch', 'problem')
    problem = _json(problem_rows[0][0])
    if (canonical(manifest) != canonical({'run_id': run_id, **settings})
            or settings.get('directory') != str(directory) or settings.get('problem') != problem
            or case_launch.get('run_dir') != str(directory)
            or case_launch.get('version') != 'fixed_gene_case_execution_v1'
            or case_launch['configuration'].get('workspace') != str(workspace)
            or canonical(settings.get('tool_configuration')) != canonical(case_launch['configuration'])):
        custody.fail('source_identity_mismatch', directory, workspace)
    case_dir = _path(case_launch['case_dir'])
    case = _read_authority(custody, case_dir / 'case.json')
    declared = case['target_files']
    if (case.get('target_kind') != 'single_gene' or not isinstance(declared, dict)
            or set(declared) not in ({'target.fna'}, {'target.fna', 'target.faa'})
            or problem['id'] != case['problem_ref'] or problem['subject_refs'] != [case['target_ref']]
            or case_launch['problem_ref'] != problem['id'] or case_launch['target_ref'] != case['target_ref']):
        custody.fail('source_identity_mismatch', case_dir / 'case.json')
    authority_paths = [(directory / name, 'checkpoint/authority/' + name) for name in (
        'run.json', 'case-launch.json', 'policy-binding.json', 'episode-execution-binding.json')]
    snapshot = policy['snapshot_file']
    if (not isinstance(snapshot, str) or Path(snapshot).name != snapshot
            or snapshot != 'policy-' + policy['source_sha256'] + '.py'):
        custody.fail('source_identity_mismatch', 'policy_snapshot')
    policy_path = directory / snapshot
    policy_witness = custody.capture(policy_path)
    if policy_witness is None or policy_witness['sha256'] != policy['source_sha256']:
        custody.fail('source_identity_mismatch', policy_path)
    authority_paths.append((policy_path, 'checkpoint/authority/' + snapshot))
    for name, checksum in declared.items():
        witness = custody.capture(case_dir / name)
        if witness is None or witness['sha256'] != checksum:
            custody.fail('source_identity_mismatch', case_dir / name)
        authority_paths.append((case_dir / name, 'checkpoint/authority/case/' + name))
    authority_paths.append((case_dir / 'case.json', 'checkpoint/authority/case/case.json'))
    target = _resolve(db, case['target_ref'])
    sequence = _resolve(db, target['sequence_ref'])
    member = _resolve(db, target['source_record']['member_ref'])
    target_source = _resolve(db, target['source_ref'])
    supplied_file = _resolve(db, target_source['artifact_ref'])
    if (target.get('record_type') != 'input' or target.get('molecule') != 'dna'
            or target.get('role') != 'gene' or target.get('unit') != 'nt'
            or target['id'] != identity('input', {key: value for key, value in target.items()
                if key not in {'id', 'record_type', 'origin'}})
            or problem['id'] != identity('problem', {key: value for key, value in problem.items() if key != 'id'})
            or type(target['length']) is not int or target['length'] <= 0
            or sequence['size'] != target['length']
            or case.get('dna_length_nt', target['length']) != target['length']
            or member['record_type'] != 'collection_member' or member['length'] != target['length']
            or member['sequence_ref'] != target['sequence_ref'] or member['source_ref'] != target['source_ref']
            or supplied_file['record_type'] != 'artifact' or supplied_file['sha256'] != declared['target.fna']
            or sequence.get('record_type') != 'artifact'
            or target['sequence_ref'] != 'artifact_' + sequence['sha256']
            or case_launch['target_sequence_sha256'] != sequence['sha256']
            or db.execute('SELECT count(*) FROM inputs').fetchone()[0] != 1):
        custody.fail('source_identity_mismatch', case['target_ref'], 'target_sequence')
    episode = episodes[0]
    original_episode = EpisodeRef(run_id, _json(episode['path']))
    if original_episode.episode_id != episode['episode_id']:
        custody.fail('source_identity_mismatch', episode['episode_id'])
    pending_rows = db.execute('SELECT * FROM runtime_model_calls WHERE response IS NULL').fetchall()
    if len(pending_rows) != 1:
        custody.fail('source_execution_inventory_out_of_scope', 'pending_model_call')
    pending = pending_rows[0]
    pending_raw = pending['request'].encode('utf-8')
    maximum = db.execute('SELECT max(call_index) FROM runtime_model_calls').fetchone()[0]
    request = _json(pending['request'])
    if (pending['run_id'] != run_id or pending['episode_id'] != episode['episode_id']
            or type(pending['call_index']) is not int or pending['call_index'] < 0
            or pending['call_index'] != maximum or _sha(pending_raw) != pending_hash
            or not isinstance(request, dict) or not {'context', 'schema'} <= request.keys()
            or db.execute('SELECT 1 FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
                (run_id, episode['episode_id'], pending['call_index'])).fetchone() is not None):
        custody.fail('source_identity_mismatch', 'pending_request', run_id)
    if (db.execute('SELECT count(*) FROM runtime_model_calls WHERE run_id<>? OR episode_id<>?',
            (run_id, episode['episode_id'])).fetchone()[0]
            or db.execute('SELECT count(*) FROM runtime_actions WHERE run_id<>? OR episode_id<>?',
                (run_id, episode['episode_id'])).fetchone()[0]
            or db.execute('SELECT count(*) FROM runtime_observations WHERE run_id<>? OR episode_id<>?',
                (run_id, episode['episode_id'])).fetchone()[0]):
        custody.fail('source_execution_inventory_out_of_scope', 'foreign_runtime_owner')
    pins = {name: _sha(canonical(value).encode()) for name, value in (
        ('case-launch.json', case_launch), ('policy-binding.json', policy))}
    settings_sha = _sha(canonical(settings).encode())
    expected_arguments = {'version': 'episode_runtime_binding_v1', 'workspace': str(workspace),
        'run_directory': str(directory), 'kind': 'fixed_case',
        'tool_configuration': case_launch['configuration'], 'caller_binding_pins': pins}
    expected_binding = {'factory_module': 'gene_annotation_episode.independent_execution',
        'factory_name': 'open_commission', 'arguments': expected_arguments,
        'implementation_sha256': expected_pin, 'settings_sha256': settings_sha}
    row = db.execute('SELECT * FROM runtime_execution_bindings WHERE run_id=?', (run_id,)).fetchone()
    expected_selection = {'mode': 'known', 'kind': 'fixed_case',
        'tool_configuration': case_launch['configuration'],
        'implementation_sha256': expected_pin, 'caller_binding_pins': pins}
    if (binding != expected_binding or row is None or row['runtime_binding'] is None
            or _json(row['runtime_binding']) != expected_binding
            or _json(row['selection']) != expected_selection or row['settings_sha256'] != settings_sha
            or settings.get('episode_execution') != {'version': 'durable_episode_application_v1',
                'binding_file': 'episode-execution-binding.json'}):
        custody.fail('source_identity_mismatch', 'execution_binding')
    policy_identity = {'policy_source_sha256': policy['source_sha256'],
        'policy_parameters_sha256': _sha(canonical(policy['parameters']).encode())}
    required_definitions = {'credit', 'scientific_child_credit', 'controller', 'annotation_score'}
    definitions = settings.get('binding_definitions')
    if (not isinstance(definitions, dict) or set(definitions) != required_definitions
            or not (required_definitions | {'job_credit', 'monitoring_credit', 'native_timing_information'})
                <= policy['definitions'].keys()):
        custody.fail('source_identity_mismatch', 'policy_definitions')
    for name, definition in definitions.items():
        if definition != {**policy_identity, 'definition': policy['definitions'][name]}:
            custody.fail('source_identity_mismatch', 'policy_definition.' + name)
    original_policy = policy['parameters']['policy']
    original_refs = original_policy['scientific_progress']['initial_known_record_refs']
    native = NativeTimingInformation.from_record(policy['definitions']['native_timing_information'])
    if (original_policy['scientific_child'] != 'received_findings'
            or policy.get('initial_known_record_refs') != original_refs
            or settings.get('scientific_knowledge') != {'version': 'frozen_parent_receipt_prefix_v1',
                'initial_known_record_refs': sorted(set(original_refs))}
            or settings.get('native_timing_information') != native.as_record()
            or native.information_unit != original_policy['monitoring']['information_unit']
            or policy.get('episode_record_receipts') != {'version': 'explicit_store_record_receipts_v1', 'enabled': True}
            or settings.get('episode_record_receipts') != policy['episode_record_receipts']):
        custody.fail('source_identity_mismatch', 'original_policy_knowledge_or_native_binding')
    if 'resource_estimator' in policy['definitions']:
        estimator = ResourceToolEstimator.from_record(policy['definitions']['resource_estimator'])
        if settings.get('resource_tool_estimator') != estimator.as_record():
            custody.fail('source_identity_mismatch', 'original_resource_estimator')
    jobs = settings.get('job_episodes', {})
    if (jobs.get('credit_binding') != {**policy_identity, 'definition': policy['definitions']['job_credit']}
            or jobs.get('monitoring_binding') != {**policy_identity, 'definition': policy['definitions']['monitoring_credit']}
            or jobs.get('registry_directory') != str(directory / 'native-jobs')
            or jobs.get('registry_configuration') != case_launch['registry_configuration']
            or settings.get('models') != case_launch['configuration']['models']
            or settings.get('restoration') != case_launch['configuration']['restoration']):
        custody.fail('source_identity_mismatch', 'original_job_or_model_bindings')
    registry_path = directory / 'native-jobs' / 'configuration.json'
    registry = _read_authority(custody, registry_path)
    if registry != case_launch['registry_configuration']:
        custody.fail('source_identity_mismatch', registry_path)
    authority_paths.append((registry_path, 'checkpoint/authority/native-jobs/configuration.json'))
    counts = {name: db.execute('SELECT count(*) FROM runtime_' + table).fetchone()[0]
        for name, table in (('model_calls', 'model_calls'), ('actions', 'actions'),
                            ('observations', 'observations'), ('episodes', 'episodes'))}
    return {'settings': settings, 'settings_raw': runs[0]['settings'], 'problem': problem,
        'case': case, 'case_dir': case_dir, 'case_launch': case_launch, 'episode_id': episode['episode_id'],
        'pending': pending, 'pending_raw': pending_raw, 'counts': counts,
        'authority_paths': authority_paths, 'registry_path': registry_path,
        'fixed_identity': {'case_ref': case['case_ref'], 'problem_ref': problem['id'],
            'target_ref': target['id'], 'target_sequence_artifact_ref': target['sequence_ref'],
            'target_sequence_sha256': sequence['sha256']}}


def _artifact_inventory(custody, db, workspace):
    rows = []
    for row in db.execute('SELECT * FROM artifacts ORDER BY id COLLATE BINARY'):
        checksum, size = row['sha256'], row['size']
        if (not isinstance(checksum, str) or _HEX.fullmatch(checksum) is None
                or row['id'] != 'artifact_' + checksum or type(size) is not int or size < 0
                or not isinstance(row['media_type'], str) or not row['media_type']):
            custody.fail('artifact_custody_failure', row['id'])
        relative = Path('artifacts') / checksum[:2] / checksum
        try:
            witness = custody.capture(workspace / relative)
        except (OSError, ValueError):
            custody.fail('artifact_custody_failure', row['id'])
        if witness is None or witness['sha256'] != checksum or witness['bytes'] != size:
            custody.fail('artifact_custody_failure', row['id'])
        rows.append({'id': row['id'], 'sha256': checksum, 'media_type': row['media_type'],
            'bytes': size, 'relative_path': str(relative)})
    return {'version': 'scientific_checkpoint_artifact_inventory_v1', 'count': len(rows),
        'total_bytes': sum(row['bytes'] for row in rows), 'artifacts': rows}


def _preservation(before, after):
    return {'mode': 'read_only_immutable_database_absent_or_empty_wal',
        'database_before': before['database'], 'database_after': after['database'],
        'wal_before': before['wal'], 'wal_after': after['wal'],
        'shm_before': before['shm'], 'shm_after': after['shm'],
        'source_files_equal': True, 'reader_bookkeeping_changes': []}


def _add_lineage(store, db, authority, *, run_id, expected_pin, pending_hash,
                 tables_sha, artifacts_sha, fork_id):
    raw_stream, index_rows, decisions = bytearray(), [], set()
    episode_id = authority['episode_id']
    for row in db.execute('SELECT * FROM runtime_observations ORDER BY unit_index'):
        raw = row['observation'].encode('utf-8')
        observed = _json(row['observation'])
        unit = UnitRef.from_record(observed['unit_ref'])
        if (row['run_id'] != run_id or row['episode_id'] != episode_id
                or unit.episode_id != episode_id or unit.unit_index != row['unit_index']):
            raise ValueError('observation_unit_identity_mismatch')
        decision = observed.get('decision_index')
        if decision is not None and (type(decision) is not int or not 0 <= decision < authority['pending']['call_index']):
            raise ValueError('observation_decision_identity_mismatch')
        if decision is not None:
            if decision in decisions or db.execute('SELECT 1 FROM runtime_actions '
                    'WHERE run_id=? AND episode_id=? AND decision_index=?', (run_id, episode_id, decision)).fetchone() is None:
                raise ValueError('observation_decision_identity_mismatch')
            decisions.add(decision)
        index_rows.append({'run_id': run_id, 'episode_id': episode_id, 'unit_index': row['unit_index'],
            'decision_index_present': 'decision_index' in observed, 'decision_index': decision,
            'unit_ref': unit.as_record(), 'raw_text_utf8_offset': len(raw_stream),
            'raw_text_utf8_bytes': len(raw), 'raw_text_utf8_sha256': _sha(raw),
            'delimiter_bytes': 1, 'delimiter_hex': '0a'})
        raw_stream.extend(raw)
        raw_stream.extend(b'\n')
    metadata = {'version': 'scientific_checkpoint_lineage_source_v1',
        'meaning': 'prior_run_lineage_not_new_local_observations', 'source_run_id': run_id,
        'source_episode_id': episode_id, 'source_implementation_sha256': expected_pin,
        'source_settings_raw_utf8_sha256': _sha(authority['settings_raw'].encode()),
        'source_pending_request_raw_utf8_sha256': pending_hash,
        'source_table_manifest_sha256': tables_sha, 'source_artifact_manifest_sha256': artifacts_sha,
        'original_observation_count': len(index_rows), 'fixed_target_ref': authority['fixed_identity']['target_ref']}
    declared_artifacts = set()
    def source(payload, kind, parents):
        artifact = store.artifact(payload, 'application/json' if kind == 'observation_index' else 'text/plain; charset=utf-8')
        request = store.artifact(canonical({**metadata, 'kind': kind}), 'application/json')
        declared_artifacts.update((artifact, request))
        record = store.put('source', {'provider': 'caller.scientific_checkpoint_fork',
            'accession': fork_id, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact,
            'request_ref': request, 'version': VERSION, 'retrieved_at': None,
            'operand_refs': [metadata['fixed_target_ref']], 'parent_source_refs': parents}, origin='caller')
        return record['id'], artifact
    observations, observation_artifact = source(bytes(raw_stream), 'original_observations', [])
    index = {'version': 'scientific_checkpoint_observation_index_v1',
        'meaning': 'prior_run_lineage_not_new_local_observations',
        'stream_representation': 'original_sqlite_text_utf8_with_separate_lf_delimiters',
        'source_run_id': run_id, 'source_episode_id': episode_id,
        'observation_source_ref': observations, 'observation_artifact_ref': observation_artifact,
        'observation_artifact_sha256': _sha(raw_stream), 'observation_artifact_bytes': len(raw_stream),
        'record_count': len(index_rows), 'rows': index_rows}
    index_source, index_artifact = source(canonical(index), 'observation_index', [observations])
    for indexed in index_rows:
        offset, remaining = indexed['raw_text_utf8_offset'], indexed['raw_text_utf8_bytes']
        digest = hashlib.sha256()
        while remaining:
            window = source_window(store, observations, offset=offset, limit=min(12000, remaining), representation='original')
            selected = window['text'].encode('utf-8')
            if not selected or window['start'] != offset or window['end'] != offset + len(selected):
                raise ValueError('lineage_window_mismatch')
            digest.update(selected)
            remaining -= len(selected)
            offset += len(selected)
        if digest.hexdigest() != indexed['raw_text_utf8_sha256']:
            raise ValueError('lineage_window_mismatch')
    return {'observation_source_ref': observations, 'index_source_ref': index_source,
        'observation_artifact_ref': observation_artifact, 'index_artifact_ref': index_artifact,
        'original_observation_count': len(index_rows)}, declared_artifacts


def prepare_scientific_checkpoint_fork(*, source_workspace, source_run_directory,
        source_implementation_root, source_run_id: str, expected_source_implementation_sha256: str,
        expected_pending_request_sha256: str, destination_workspace,
        initial_known_record_refs: tuple[str, ...]) -> dict:
    """Prepare a NEW private workspace; never open/recover the source as Store."""
    custody, source = _Custody(), None
    try:
        if (type(source_run_id) is not str or _RUN.fullmatch(source_run_id) is None
                or any(type(value) is not str or _HEX.fullmatch(value) is None for value in (
                    expected_source_implementation_sha256, expected_pending_request_sha256))
                or type(initial_known_record_refs) is not tuple or not initial_known_record_refs
                or any(type(ref) is not str or _REF.fullmatch(ref) is None for ref in initial_known_record_refs)
                or len(set(initial_known_record_refs)) != len(initial_known_record_refs)):
            custody.fail('invalid_request', 'source_identity_or_initial_references', cause='contract_error')
        try:
            workspace, directory, source_root = map(_path,
                (source_workspace, source_run_directory, source_implementation_root))
        except (OSError, ValueError, TypeError):
            custody.fail('source_unavailable', 'source_paths', cause='contract_error')
        try:
            destination = custody.destination = _path(destination_workspace)
            if not destination.parent.is_dir():
                custody.fail('destination_invalid', destination.parent, cause='contract_error')
            for protected in (workspace, directory, source_root):
                if destination.is_relative_to(protected) or protected.is_relative_to(destination):
                    custody.fail('destination_overlap', destination, protected, cause='contract_error')
            if os.path.lexists(destination):
                custody.fail('destination_exists', destination, cause='contract_error')
            for parent in destination.parents:
                if any((parent / name).is_file() for name in (
                        'run.json', 'case-launch.json', 'policy-binding.json', 'episode-execution-binding.json')):
                    custody.fail('destination_overlap', destination, parent, cause='contract_error')
        except ScientificCheckpointForkError:
            raise
        except (OSError, ValueError, TypeError):
            custody.fail('destination_invalid', destination_workspace, cause='contract_error')
        custody.phase = 'capture_source'
        scientific_before = _capture_database(custody, workspace / 'state.sqlite3')
        native_database = directory / 'native-jobs' / 'jobs.sqlite'
        native_before = _capture_database(custody, native_database)
        implementation = _source_files(source_root)
        if implementation['implementation_sha256'] != expected_source_implementation_sha256:
            custody.fail('source_identity_mismatch', 'implementation_sha256')
        for row in implementation['files']:
            custody.capture(source_root / row['relative_path'])
        with _readonly(workspace / 'state.sqlite3') as source:
            if source.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                custody.fail('source_schema_unsupported', 'sqlite_integrity')
            try:
                _schema(source)
            except ValueError:
                custody.fail('source_schema_unsupported', 'sqlite_schema')
            authority = _source_authority(custody, source, workspace, directory, source_root,
                source_run_id, expected_source_implementation_sha256, expected_pending_request_sha256)
            case_dir = authority['case_dir']
            if destination.is_relative_to(case_dir) or case_dir.is_relative_to(destination):
                custody.fail('destination_overlap', destination, case_dir)
            custody.phase = 'validate_inventory'
            names = {row[0] for row in source.execute("SELECT name FROM sqlite_schema WHERE type='table'")}
            if (not set(_EMPTY) <= names or any(name.startswith(('api_', 'public_search_')) for name in names)):
                custody.fail('source_execution_inventory_out_of_scope', 'execution_tables')
            for name in _EMPTY:
                if source.execute('SELECT count(*) FROM ' + name).fetchone()[0]:
                    custody.fail('source_execution_inventory_out_of_scope', name)
            with _readonly(native_database) as native:
                native_counts = []
                for name in ('handoffs', 'orders', 'samples'):
                    count = native.execute('SELECT count(*) FROM ' + name).fetchone()[0]
                    if count:
                        custody.fail('source_execution_inventory_out_of_scope', 'native.' + name)
                    native_counts.append({'table': name, 'count': 0})
            references, committed = _known_inventory(source)
            if not committed <= set(initial_known_record_refs):
                custody.fail('baseline_incomplete', *sorted(committed - set(initial_known_record_refs)))
            artifact_manifest = _artifact_inventory(custody, source, workspace)
            custody.parent_fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            stage = _create_stage(custody)
            checkpoint = stage / 'checkpoint'
            checkpoint.mkdir(mode=0o700)
            custody.phase = 'snapshot'
            _copy_file(workspace / 'state.sqlite3', checkpoint / 'state.sqlite3', scientific_before['database'], mode=0o400)
            _copy_file(checkpoint / 'state.sqlite3', stage / 'state.sqlite3', scientific_before['database'])
            working_stat = (stage / 'state.sqlite3').stat(follow_symlinks=False)
            custody.working_identity = (working_stat.st_dev, working_stat.st_ino)
            if (checkpoint / 'state.sqlite3').stat().st_ino == (stage / 'state.sqlite3').stat().st_ino:
                custody.fail('snapshot_mismatch', 'independent_database_copy')
            tables = _table_manifest(source, checkpoint)
            table_file = _write_json(checkpoint / 'tables.json', tables)
            artifact_file = _write_json(checkpoint / 'artifacts.json', artifact_manifest)
            _write_json(checkpoint / 'committed-references.json', references)
            _write_json(checkpoint / 'source-implementation-files.json', implementation)
            authority_files = []
            for original, relative in authority['authority_paths']:
                expected = custody.files[str(original)]
                _copy_file(original, stage / relative, expected, mode=0o400)
                authority_files.append({'source_path': str(original), 'checkpoint_relative_path': relative,
                    'sha256': expected['sha256'], 'bytes': expected['bytes']})
            custody.phase = 'copy_artifacts'
            for row in artifact_manifest['artifacts']:
                _copy_file(workspace / row['relative_path'], stage / row['relative_path'],
                    {'sha256': row['sha256'], 'bytes': row['bytes']})
            custody.phase = 'validate_snapshot'
            identity_material = {'source_run_id': source_run_id,
                'source_settings_raw_utf8_sha256': _sha(authority['settings_raw'].encode()),
                'source_pending_request_raw_utf8_sha256': expected_pending_request_sha256,
                'source_table_manifest_sha256': table_file['sha256'],
                'source_artifact_manifest_sha256': artifact_file['sha256'],
                'destination_workspace': str(destination),
                'caller_initial_known_record_refs': sorted(initial_known_record_refs)}
            fork_id = 'scientific_checkpoint_' + _sha(canonical(identity_material).encode())[:24]
            with _memory_store(stage, custody) as store:
                if _table_manifest(store.db, checkpoint) != tables:
                    custody.fail('snapshot_mismatch', 'destination_constructor_schema_or_rows')
                for ref in sorted(set(initial_known_record_refs) | committed):
                    try:
                        record = store.get(ref)
                        if record['id'] != ref:
                            raise ValueError('lookup_identity_mismatch')
                        for child in store._refs(record):
                            store.get(child)
                    except (ContractError, ValueError, TypeError, KeyError):
                        custody.fail('reference_invalid', ref)
                try:
                    for row in store.db.execute('SELECT data FROM material_members'):
                        member = _json(row[0])
                        for component in packing.COMPONENTS:
                            info = packing.component_info(store, member, component)
                            if info is not None:
                                digest, size = hashlib.sha256(), 0
                                for chunk in packing.component_chunks(store, member, component):
                                    digest.update(chunk)
                                    size += len(chunk)
                                if size != info['bytes'] or digest.hexdigest() != info['sha256']:
                                    raise ValueError('component_bytes_mismatch')
                except (ContractError, ValueError, TypeError, KeyError):
                    custody.fail('material_custody_failure', 'packed_components')
                custody.phase = 'build_lineage'
                with store.transaction():
                    lineage, declared_artifacts = _add_lineage(store, source, authority,
                        run_id=source_run_id, expected_pin=expected_source_implementation_sha256,
                        pending_hash=expected_pending_request_sha256, tables_sha=table_file['sha256'],
                        artifacts_sha=artifact_file['sha256'], fork_id=fork_id)
                original_artifacts = {row['id'] for row in artifact_manifest['artifacts']}
                new_sources = {lineage['observation_source_ref'], lineage['index_source_ref']} - committed
                excluded = {'records': new_sources, 'artifacts': declared_artifacts - original_artifacts}
                if _table_manifest(store.db, checkpoint, excluded=excluded) != tables:
                    custody.fail('snapshot_mismatch', 'unexpected_destination_data_or_schema_delta')
            custody.phase = 'verify_source'
            custody.verify_source()
            if _source_files(source_root) != implementation:
                custody.source_unchanged = False
                custody.fail('source_changed', source_root)
            native_after = _database_files(native_database)
            scientific_after = _database_files(workspace / 'state.sqlite3')
            final_refs = sorted(set(initial_known_record_refs) | new_sources)
            inventory = {'version': 'stopped_fixed_science_execution_inventory_v1',
                'workspace_empty_tables': [{'table': name, 'count': 0} for name in _EMPTY],
                'forbidden_workspace_table_prefixes_absent': ['api_', 'public_search_'],
                'native_registry_database': native_before['database'],
                'native_registry_configuration': custody.files[str(authority['registry_path'])],
                'native_registry_empty_tables': native_counts, 'run_count': 1, 'episode_count': 1,
                'pending_call_count': 1, 'native_registry_preservation': _preservation(native_before, native_after)}
            receipt = {'version': VERSION, 'status': 'custody_prepared_no_new_run', 'fork_id': fork_id,
                'captured_at': datetime.now(timezone.utc).isoformat(), 'destination_workspace': str(destination),
                'source': {'workspace': str(workspace), 'run_directory': str(directory),
                    'implementation_root': str(source_root), 'run_id': source_run_id,
                    'episode_id': authority['episode_id'], 'implementation_sha256': expected_source_implementation_sha256,
                    'implementation_file_manifest': _relative_file(checkpoint / 'source-implementation-files.json', stage),
                    'authority_files': authority_files,
                    'settings_raw_utf8_sha256': _sha(authority['settings_raw'].encode()),
                    'pending': {'call_index': authority['pending']['call_index'], 'purpose': authority['pending']['purpose'],
                        'request_raw_utf8_sha256': expected_pending_request_sha256,
                        'request_raw_utf8_bytes': len(authority['pending_raw']), 'response': None,
                        'selected_action_at_call': False}, 'counts': authority['counts'],
                    'execution_inventory': inventory,
                    'preservation': {**_preservation(scientific_before, scientific_after),
                        'registered_artifact_files_equal': True, 'source_authority_files_equal': True}},
                'fixed_identity': authority['fixed_identity'],
                'checkpoint': {'database': _relative_file(checkpoint / 'state.sqlite3', stage),
                    'table_manifest': _relative_file(checkpoint / 'tables.json', stage),
                    'artifact_manifest': _relative_file(checkpoint / 'artifacts.json', stage),
                    'committed_reference_manifest': _relative_file(checkpoint / 'committed-references.json', stage)},
                'workspace_database_at_publication': _relative_file(stage / 'state.sqlite3', stage),
                'preserved_counts': {'tables': len(tables['tables']), 'artifacts': artifact_manifest['count'],
                    'artifact_bytes': artifact_manifest['total_bytes'], 'input_records': references['input_count'],
                    'committed_records': references['record_count'],
                    'staged_proposals': source.execute('SELECT count(*) FROM proposals').fetchone()[0]},
                'lineage': lineage, 'caller_initial_known_record_refs': list(initial_known_record_refs),
                'initial_known_record_refs': final_refs, 'initial_known_record_refs_sha256': _sha(canonical(final_refs).encode()),
                'verification': {key: True for key in (
                    'snapshot_database_bytes_equal_source_main', 'snapshot_schema_and_rows_equal',
                    'all_source_rows_preserved_after_destination_additions', 'registered_artifact_bytes_equal',
                    'packed_material_components_equal', 'all_committed_input_and_record_refs_explicitly_selected',
                    'all_selected_refs_resolve_through_actual_destination_store',
                    'new_lineage_sources_validate_through_actual_store', 'lineage_windows_match_original_raw_text',
                    'old_run_authority_unchanged', 'no_new_run_or_observation_created')}, 'limitations': list(_LIMITS)}
            custody.phase = 'publish'
            receipt_witness = _write_json(stage / 'scientific-checkpoint-fork.json', receipt)
            _sync_tree(stage)
            _publish(custody, stage)
            return {'version': 'scientific_checkpoint_fork_result_v1', 'status': 'published',
                'destination_workspace': str(destination),
                'receipt': {**receipt_witness, 'path': str(destination / 'scientific-checkpoint-fork.json')},
                'initial_known_record_refs': final_refs,
                'lineage_source_refs': {'observations': lineage['observation_source_ref'], 'index': lineage['index_source_ref']}}
    except ScientificCheckpointForkError:
        raise
    except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, OverflowError, MemoryError) as error:
        if isinstance(error, OSError):
            cause = 'permission_denied' if isinstance(error, PermissionError) else 'io_error'
            code = ('publication_failure' if custody.phase == 'publish' else
                    'artifact_custody_failure' if custody.phase == 'copy_artifacts' else
                    'source_unavailable' if custody.stage_name is None and custody.phase == 'capture_source' else
                    'storage_failure')
        elif isinstance(error, MemoryError):
            cause, code = None, 'storage_failure'
        elif isinstance(error, sqlite3.Error):
            cause, code = 'sqlite_error', 'source_schema_unsupported' if custody.stage_name is None else 'snapshot_mismatch'
        else:
            cause = 'contract_error'
            code = {'validate_request': 'invalid_request', 'capture_source': 'source_identity_mismatch',
                'validate_inventory': 'source_schema_unsupported', 'snapshot': 'snapshot_mismatch',
                'copy_artifacts': 'artifact_custody_failure', 'validate_snapshot': 'snapshot_mismatch',
                'build_lineage': 'destination_lineage_failure', 'verify_source': 'source_changed',
                'publish': 'publication_failure'}.get(custody.phase, 'storage_failure')
        if custody.renamed:
            code, cause = 'publication_failure', 'io_error' if not custody.durable else cause
        custody.fail(code, custody.destination or 'custody_operands', cause=cause,
                     error_number=getattr(error, 'errno', None))
    finally:
        if custody.stage_fd is not None:
            os.close(custody.stage_fd)
        if custody.parent_fd is not None:
            os.close(custody.parent_fd)


__all__ = ['prepare_scientific_checkpoint_fork', 'ScientificCheckpointForkError']
