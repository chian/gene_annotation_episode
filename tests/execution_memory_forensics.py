"""Read-only, locked SQLite census; never import application memory readers.

Only sealed run-owned rollback-journal snapshots are opened by SQLite. All raw
records belong in private retained evidence, never in terminal summaries.
"""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import sqlite3
import stat
import traceback


VERSION = 'execution_memory_locked_forensics'
DATABASES = (
    'gene_annotation_episode/episodic_workflow/root/runs/shared-execution/memory.sqlite3',
    'runs/shared-execution/memory.sqlite3',
)
TABLES = {
    'resource_observations': ('id', 'resource', 'kind', 'observed', 'body'),
    'execution_measurements': ('attempt', 'compatibility', 'resource', 'observed', 'body'),
}
COMPANIONS = ('-wal', '-shm', '-journal')


class Refusal(Exception):
    def __init__(self, code, detail=None):
        super().__init__(code)
        self.code, self.detail = code, detail


def require(condition, code, detail=None):
    if not condition:
        raise Refusal(code, detail)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        stream.write(canonical(value) + '\n')


def metadata(item):
    return {key: getattr(item, 'st_' + key) for key in (
        'dev', 'ino', 'mode', 'nlink', 'uid', 'gid', 'size', 'mtime_ns', 'ctime_ns', 'atime_ns')}


def stable(item):
    # atime is also preserved: original descriptors require O_NOATIME.
    return metadata(item)


def safe_path(path):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts, 'absolute_nontraversing_path_required')
    for parent in (*reversed(path.parents), path):
        item = parent.lstat()
        require(not stat.S_ISLNK(item.st_mode), 'symlink_path_refused', str(parent))
    item = path.lstat()
    require(stat.S_ISREG(item.st_mode), 'regular_file_required', str(path))
    return item


def open_original(path):
    before = safe_path(path)
    require(hasattr(os, 'O_NOATIME') and hasattr(os, 'O_NOFOLLOW'), 'linux_read_flags_required')
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NOATIME)
    try:
        require(stable(before) == stable(os.fstat(fd)), 'path_changed_during_open', str(path))
        return fd
    except BaseException:
        os.close(fd)
        raise


def digest_fd(fd):
    result, offset = hashlib.sha256(), 0
    while block := os.pread(fd, 1024 * 1024, offset):
        result.update(block)
        offset += len(block)
    return result.hexdigest()


def sidecars(path):
    result = []
    for suffix in COMPANIONS:
        candidate = Path(str(path) + suffix)
        try:
            item = candidate.lstat()
        except FileNotFoundError:
            continue
        result.append({'path': str(candidate), 'metadata': metadata(item)})
    # SQLite super-journals are also a concrete incomplete-transaction boundary.
    for candidate in sorted(path.parent.glob(path.name + '-mj*')):
        result.append({'path': str(candidate), 'metadata': metadata(candidate.lstat())})
    return result


def mount_record(path):
    raw = Path('/proc/self/mountinfo').read_text()
    matches = []
    for line in raw.splitlines():
        left, right = line.split(' - ', 1)
        fields, tail = left.split(), right.split()
        mount = fields[4].replace('\\040', ' ').replace('\\011', '\t').replace('\\134', '\\')
        if path == Path(mount) or Path(mount) in path.parents:
            matches.append((len(Path(mount).parts), {'mount': mount, 'filesystem': tail[0],
                'mount_line': line, 'mountinfo_sha256': sha(raw.encode())}))
    require(bool(matches), 'mount_identity_unavailable')
    result = max(matches, key=lambda item: item[0])[1]
    # These concrete remote/FUSE protocols need a separate locking proof. An
    # unrelated filesystem name or inaccessible system process is not a gate.
    fs = result['filesystem']
    require(not (fs.startswith(('nfs', 'fuse', 'cifs', 'smb')) or
                 fs in {'9p', 'ceph', 'afs', 'glusterfs'}), 'filesystem_lock_protocol_unproved', result)
    return result


def process_identity(directory):
    raw = (directory / 'stat').read_text()
    # comm may contain whitespace and parentheses; starttime is field 22.
    return {'pid': int(directory.name), 'start_ticks': raw.rsplit(')', 1)[1].split()[19],
            'uid': directory.stat().st_uid}


def _workflow_group(raw):
    """Derive the dedicated service ancestor from observed unified membership."""
    groups = [line.split(':', 2)[2] for line in raw.splitlines()
              if line.startswith('0::')]
    owned = []
    for group in groups:
        matches = list(re.finditer(
            r'/gene-episode-workflow-[0-9a-f]{32}\.service(?=/|$)', group))
        if len(matches) == 1:
            owned.append(group[:matches[0].end()])
    return owned[0] if len(owned) == 1 else None


def _workflow_member(raw, group):
    """An observed service or descendant, with an exact path-component boundary."""
    return group is not None and any(
        observed == group or observed.startswith(group + '/')
        for line in raw.splitlines() if line.startswith('0::')
        for observed in [line.split(':', 2)[2]])


def _workflow_scope():
    """Observe our actual dedicated launcher service, never infer it from UID."""
    raw = Path('/proc/self/cgroup').read_text()
    return {'executor_pid': os.getpid(), 'raw_cgroup': raw,
            'group': _workflow_group(raw),
            'meaning': 'observed dedicated workflow service and descendants; UID is not a link'}


def _visibility_failure(result, pid, error, *, uid, identity, links):
    """Retain unknown visibility without asserting the process is unrelated."""
    entry = {'pid': str(pid), 'type': type(error).__name__, 'message': str(error),
             'observed_proc_owner_uid': uid, 'identity': identity,
             'links': list(links), 'scope': 'linked_visibility_unresolved' if links
             else 'unknown_target_or_workflow_link'}
    result['unresolved' if links else 'unclassified_process_observations'].append(entry)


def process_inventory(paths, relevant_uids):
    """Retain the selected UID census, distinguishing links from unknown scope.

    Actual target inode/path/mapping witnesses and our observed dedicated
    workflow group establish links. UID equality only selects a census scope.
    The unchanged POSIX locks, not unknown-process classification, exclude later
    cooperating SQLite writers. No global absence or quiescence is asserted.
    """
    identities, spellings = {}, set()
    for path in paths:
        for candidate in (path, *(Path(str(path) + s) for s in COMPANIONS),
                          *path.parent.glob(path.name + '-mj*')):
            spellings.add(str(candidate))
            try:
                item = candidate.stat(follow_symlinks=False)
            except FileNotFoundError:
                continue
            identities[(item.st_dev, item.st_ino)] = str(candidate)
    workflow = _workflow_scope()
    result = {'relevant_uids': sorted(relevant_uids), 'matches': [], 'unresolved': [],
              'excluded_uid_processes': {}, 'unclassified_process_observations': [], 'inspected_processes': [],
              'process_links': [], 'workflow_scope': workflow,
              'visibility': 'current PID namespace; selected UIDs and actually linked workflow processes; unknown observations retained',
              'uid_scope_establishes_link': False,
              'unknown_visibility_is_not_absence': True,
              'namespace': os.readlink('/proc/self/ns/pid')}
    for directory in sorted(Path('/proc').iterdir(), key=lambda p: p.name):
        if not directory.name.isdecimal():
            continue
        links = ([{'kind': 'current_executor', 'pid': os.getpid()}]
                 if directory.name == str(os.getpid()) else [])
        uid, identity, pending = None, None, []
        try:
            uid = directory.stat().st_uid
            try:
                membership = (directory / 'cgroup').read_text()
                if _workflow_member(membership, workflow['group']):
                    links.append({'kind': 'own_workflow_cgroup', 'group': workflow['group'],
                                  'raw_cgroup': membership})
            except FileNotFoundError:
                continue
            except OSError as error:
                pending.append(error)
            if uid not in relevant_uids and not links:
                key = str(uid)
                result['excluded_uid_processes'][key] = result['excluded_uid_processes'].get(key, 0) + 1
                continue
            identity = process_identity(directory)
            for task in (directory / 'task').iterdir():
                if not task.name.isdecimal():
                    continue
                for entry in (task / 'fd').iterdir():
                    try:
                        item = entry.stat()
                        match = identities.get((item.st_dev, item.st_ino))
                        witness = None
                        if match is not None:
                            witness = {'kind': 'target_descriptor', 'tid': int(task.name),
                                       'fd': entry.name, 'matched': match, 'target': None,
                                       'device': item.st_dev, 'inode': item.st_ino,
                                       'basis': 'observed_target_inode'}
                            links.append(witness)
                        target = os.readlink(entry)
                        if match is None and target.removesuffix(' (deleted)') in spellings:
                            match = target.removesuffix(' (deleted)')
                        if match is None:
                            continue
                        # Save the observed target link BEFORE reading fdinfo;
                        # denial after this witness must remain a linked refusal.
                        if witness is None:
                            links.append({'kind': 'target_descriptor', 'tid': int(task.name),
                                          'fd': entry.name, 'matched': match, 'target': target,
                                          'device': item.st_dev, 'inode': item.st_ino,
                                          'basis': 'observed_target_path'})
                        else:
                            witness['target'] = target
                        raw = (task / 'fdinfo' / entry.name).read_text()
                        fields = dict(line.split(':', 1) for line in raw.splitlines() if ':' in line)
                        flags = int(fields['flags'].strip(), 8)
                        result['matches'].append({**identity, 'tid': int(task.name), 'fd': entry.name,
                            'target': target, 'matched': match, 'flags': flags,
                            'writable': (flags & os.O_ACCMODE) != os.O_RDONLY,
                            'fdinfo': raw})
                    except FileNotFoundError:
                        continue
                for line in (task / 'maps').read_text().splitlines():
                    fields = line.split(None, 5)
                    if len(fields) < 5 or fields[4] == '0':
                        continue
                    major, minor = (int(x, 16) for x in fields[3].split(':'))
                    match = identities.get((os.makedev(major, minor), int(fields[4])))
                    if match is not None:
                        links.append({'kind': 'target_mapping', 'tid': int(task.name),
                                      'matched': match, 'mapping': line})
                        result['matches'].append({**identity, 'tid': int(task.name),
                            'matched': match, 'mapping': line, 'writable': 'w' in fields[1]})
            require(identity == process_identity(directory), 'process_identity_changed', identity)
            result['inspected_processes'].append(identity)
        except FileNotFoundError:
            continue
        except (OSError, ValueError, KeyError, Refusal) as error:
            pending.append(error)
        finally:
            if links:
                result['process_links'].append({'pid': directory.name, 'identity': identity,
                                                'links': list(links)})
            for error in pending:
                _visibility_failure(result, directory.name, error, uid=uid, identity=identity, links=links)
    return result


def assert_inventory(value):
    require(not value['unresolved'], 'relevant_process_visibility_unresolved', value['unresolved'])
    writers = [entry for entry in value['matches'] if entry['writable']]
    require(not writers, 'observed_writer_descriptor_or_mapping', writers)


def rollback_header(fd):
    header = os.pread(fd, 100, 0)
    require(len(header) == 100 and header[:16] == b'SQLite format 3\0', 'sqlite_header_required')
    require(header[18:20] == b'\x01\x01', 'rollback_journal_header_required',
            {'write_version': header[18], 'read_version': header[19]})
    return header.hex()


def snapshot_pair(paths, output, evidence, *, additional_uids=()):
    """Both locks are held throughout both copies and the final source hashes."""
    require(len(paths) == 2 and paths[0] != paths[1], 'two_distinct_paths_required')
    held = []
    evidence['snapshot_protocol'] = 'POSIX lockf shared nonblocking [0,EOF), both files; rollback only'
    try:
        for path in paths:
            fd = open_original(path)
            held.append((path, fd))
        states = [stable(os.fstat(fd)) for _, fd in held]
        require(len({(x['dev'], x['ino']) for x in states}) == 2, 'same_inode_alias_refused')
        evidence['originals'] = [dict(path=str(p), metadata=s) for (p, _), s in zip(held, states)]
        uids = {s['uid'] for s in states} | {os.getuid()} | set(additional_uids)
        evidence['processes_before'] = process_inventory(paths, uids)
        evidence['sidecars_observed'] = [sidecars(path) for path in paths]
        evidence['lock_acquisition'] = []
        for path, fd in held:
            try:
                fcntl.lockf(fd, fcntl.LOCK_SH | fcntl.LOCK_NB, 0, 0, os.SEEK_SET)
            except OSError as error:
                evidence['lock_acquisition'].append({'path': str(path), 'acquired': False,
                    'errno': error.errno, 'message': str(error)})
                raise Refusal('posix_read_lock_unavailable', evidence['lock_acquisition']) from error
            evidence['lock_acquisition'].append({'path': str(path), 'acquired': True})
        assert_inventory(evidence['processes_before'])
        states = [stable(os.fstat(fd)) for _, fd in held]
        records = []
        for (path, fd), before in zip(held, states):
            record = {'path': str(path), 'metadata_before': before,
                      'mount': mount_record(path), 'sidecars_before': sidecars(path)}
            records.append(record)
            evidence['snapshots'] = records
            require(not record['sidecars_before'], 'sqlite_companion_present', record['sidecars_before'])
            record['header'] = rollback_header(fd)
            record['source_before_sha256'] = digest_fd(fd)
            target = output / ('database-' + str(len(records)) + '.sqlite3')
            record['copy'] = str(target)
            with target.open('xb') as stream:
                offset = 0
                while block := os.pread(fd, 1024 * 1024, offset):
                    stream.write(block)
                    offset += len(block)
                stream.flush()
                os.fsync(stream.fileno())
            target.chmod(0o400)
            with target.open('rb') as stream:
                copy_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
            record['copy_sha256'] = copy_hash
            require(copy_hash == record['source_before_sha256'], 'copy_hash_mismatch')
        # The first source is verified again after the second copy; no source FD
        # has been reopened/closed (POSIX close-any-fd can release process locks).
        evidence['processes_after'] = process_inventory(paths, uids)
        assert_inventory(evidence['processes_after'])
        for (path, fd), before, record in zip(held, states, records):
            record['source_after_sha256'] = digest_fd(fd)
            record['metadata_after'] = stable(os.fstat(fd))
            record['path_after'] = stable(safe_path(path))
            record['sidecars_after'] = sidecars(path)
            require(record['source_before_sha256'] == record['source_after_sha256'] and
                    before == record['metadata_after'] == record['path_after'] and
                    not record['sidecars_after'], 'source_changed_under_locks', str(path))
        evidence['snapshot_complete'] = True
        return records
    finally:
        cleanup = evidence.setdefault('descriptor_cleanup', [])
        for path, fd in reversed(held):
            try:
                os.close(fd)  # Releases our locks only; never modify/remove originals/sidecars.
                cleanup.append({'path': str(path), 'closed': True})
            except OSError as error:
                cleanup.append({'path': str(path), 'closed': False, 'error': str(error)})
        require(all(x['closed'] for x in cleanup), 'descriptor_cleanup_failed', cleanup)


def typed(value):
    if value is None:
        return ['null', None]
    if type(value) is int:
        return ['integer', str(value)]
    if type(value) is float:
        return ['real', value.hex()]
    if type(value) is str:
        return ['text', value]
    if type(value) is bytes:
        return ['blob', value.hex()]
    raise Refusal('unexpected_sqlite_value_type', type(value).__name__)


def row_record(columns, row):
    values = [typed(value) for value in row]
    return {'columns': list(columns), 'values': values, 'sha256': sha(canonical(values).encode())}


def open_snapshot(record):
    path = Path(record['copy'])
    require(path.is_file() and stat.S_IMODE(path.stat().st_mode) == 0o400, 'sealed_copy_required')
    with path.open('rb') as stream:
        require(hashlib.file_digest(stream, 'sha256').hexdigest() == record['copy_sha256'], 'copy_tampered')
    db = sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)
    db.execute('PRAGMA query_only=ON')
    db.execute('PRAGMA trusted_schema=OFF')
    return db


def schema(db):
    rows = db.execute('SELECT type,name,tbl_name,rootpage,sql FROM sqlite_schema ORDER BY type,name').fetchall()
    result = {'sqlite_schema': [[typed(v) for v in row] for row in rows], 'tables': {}}
    actual = {row[1] for row in rows if row[0] == 'table' and not row[1].startswith('sqlite_')}
    require(actual == set(TABLES), 'unreviewed_table_set', result)
    for name, columns in TABLES.items():
        definition = next(row[4] for row in rows if row[0] == 'table' and row[1] == name)
        require(type(definition) is str and 'VIRTUAL' not in definition.upper(), 'virtual_table_refused')
        info = db.execute('PRAGMA table_xinfo("' + name + '")').fetchall()
        require(tuple(row[1] for row in info) == columns and all(row[6] == 0 for row in info),
                'unreviewed_table_columns', {'table': name, 'columns': info})
        indexes = db.execute('PRAGMA index_list("' + name + '")').fetchall()
        detail = {}
        for item in indexes:
            quoted = item[1].replace('"', '""')
            detail[item[1]] = db.execute('PRAGMA index_xinfo("' + quoted + '")').fetchall()
        result['tables'][name] = {'columns': info, 'indexes': indexes, 'index_columns': detail}
    return result


def table_rows(db, name):
    # Literal reviewed names; all rows, no age/count filter and no view execution.
    columns = TABLES[name]
    cursor = db.execute('SELECT ' + ','.join('"' + x + '"' for x in columns) +
                        ' FROM "' + name + '" ORDER BY "' + columns[0] + '" COLLATE BINARY')
    yield from cursor


def export_rows(db, name, target):
    count, invalid, last = 0, 0, None
    with target.open('x') as stream:
        for row in table_rows(db, name):
            valid = type(row[0]) is str and bool(row[0]) and row[0] != last
            record = row_record(TABLES[name], row)
            record['key_valid_unique'] = valid
            stream.write(canonical(record) + '\n')
            invalid += not valid
            last, count = row[0], count + 1
    return {'rows': count, 'invalid_or_repeated_keys': invalid,
            'file': str(target), 'sha256': sha(target.read_bytes())}


def compare_table(left, right, name, target):
    cursors = [iter(table_rows(db, name)) for db in (left, right)]
    a, b = next(cursors[0], None), next(cursors[1], None)
    counts = dict(left_only=0, right_only=0, identical=0, body_conflict=0, metadata_conflict=0)
    with target.open('x') as stream:
        while a is not None or b is not None:
            if b is None or a is not None and a[0] < b[0]:
                kind, key, pair = 'left_only', a[0], (a, None)
                a = next(cursors[0], None)
            elif a is None or b[0] < a[0]:
                kind, key, pair = 'right_only', b[0], (None, b)
                b = next(cursors[1], None)
            else:
                pair, key = (a, b), a[0]
                ra, rb = (row_record(TABLES[name], x) for x in pair)
                kind = ('identical' if ra == rb else
                        'metadata_conflict' if typed(a[-1]) == typed(b[-1]) else 'body_conflict')
                a, b = next(cursors[0], None), next(cursors[1], None)
            counts[kind] += 1
            stream.write(canonical({'key': key, 'key_sha256': sha(key.encode()), 'classification': kind,
                'left': None if pair[0] is None else row_record(TABLES[name], pair[0]),
                'right': None if pair[1] is None else row_record(TABLES[name], pair[1])}) + '\n')
    return {'counts': counts, 'file': str(target), 'sha256': sha(target.read_bytes())}


def inspect_copies(records, output, evidence):
    with contextlib.ExitStack() as stack:
        dbs = [stack.enter_context(contextlib.closing(open_snapshot(record))) for record in records]
        raw_shapes = [[[typed(v) for v in row] for row in db.execute(
            'SELECT type,name,tbl_name,rootpage,sql FROM sqlite_schema ORDER BY type,name')]
            for db in dbs]
        write_json(output / 'raw-schemas.json', raw_shapes)
        shapes = [schema(db) for db in dbs]
        write_json(output / 'schemas.json', shapes)
        evidence['schemas_equal'] = shapes[0] == shapes[1]
        evidence['exports'], evidence['comparison'] = {}, {}
        for name in TABLES:
            exports = [export_rows(db, name, output / (str(index) + '-' + name + '.jsonl'))
                       for index, db in enumerate(dbs)]
            evidence['exports'][name] = exports
            require(all(item['invalid_or_repeated_keys'] == 0 for item in exports),
                    'invalid_key_domain', {'table': name, 'exports': exports})
            evidence['comparison'][name] = compare_table(*dbs, name, output / (name + '-comparison.jsonl'))
    for record in records:
        with Path(record['copy']).open('rb') as stream:
            require(hashlib.file_digest(stream, 'sha256').hexdigest() == record['copy_sha256'],
                    'copy_changed_during_census')
    evidence['logical_census_complete'] = True


def references(value, pointer=''):
    if isinstance(value, dict):
        for key, item in value.items():
            child = pointer + '/' + key.replace('~', '~0').replace('/', '~1')
            if key in {'execution_memory_path', 'shared_execution_memory'}:
                yield {'pointer': child, 'field': key, 'value': item}
            yield from references(item, child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from references(item, pointer + '/' + str(index))


def capture_references(inputs, repo, paths, output):
    records = []
    for index, item in enumerate(inputs):
        require(set(item) == {'path', 'sha256', 'kind'}, 'explicit_reference_input_required')
        path = repo / item['path']
        require(not Path(item['path']).is_absolute() and '..' not in Path(item['path']).parts
                and path.suffix == '.json' and path not in paths, 'json_reference_path_required')
        fd = open_original(path)
        try:
            before = stable(os.fstat(fd))
            with os.fdopen(os.dup(fd), 'rb') as stream:
                raw = stream.read()
            require(sha(raw) == item['sha256'], 'reference_hash_mismatch', item['path'])
            require(before == stable(os.fstat(fd)) == stable(safe_path(path)), 'reference_changed')
        finally:
            os.close(fd)
        def invalid_constant(value):
            raise Refusal('nonfinite_saved_json_refused', value)
        value, found = json.loads(raw, parse_constant=invalid_constant), []
        for entry in references(value):
            v = entry['value']
            selected = v.get('path') if entry['field'] == 'shared_execution_memory' and isinstance(v, dict) else v
            classification = 'unresolved_fallback_or_shape'
            if isinstance(selected, str) and selected:
                classification = ('relative_path_historical_cwd_unresolved' if not Path(selected).is_absolute()
                                  else 'exact_database_' + str(paths.index(Path(selected)))
                                  if selected in [str(p) for p in paths] else 'other_absolute_path')
            found.append({**entry, 'classification': classification})
        target = output / ('saved-reference-' + str(index) + '.json')
        target.write_bytes(raw)
        records.append({'input': item, 'copy': str(target), 'references': found})
    return {'inputs': records, 'coverage': 'Only explicitly hashed JSON operands; no Store scan or live-object census',
            'embedded_json_strings': 'not decoded; submit an authenticated explicit JSON export separately',
            'absence_is_not_global_absence': True}


def run(repo, output, reference_inputs, *, additional_uids=(), controlled_paths=None):
    """Production caller never supplies controlled_paths; it is a test-only port."""
    repo, output = Path(repo).absolute(), Path(output).absolute()
    require((repo / 'runs') in output.parents, 'run_owned_output_required')
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    os.chmod(output, 0o700)
    evidence = {'version': VERSION, 'snapshot_complete': False, 'logical_census_complete': False,
                'mutation_authorized': False, 'failure': None, 'scope': 'operational history only',
                'sqlite_library_version': sqlite3.sqlite_version, 'executor_pid': os.getpid(),
                'logical_tables': list(TABLES), 'internal_sqlite_rows': 'retained in exact database snapshots',
                'claims': {'migration': False, 'future_writer_convergence': False, 'scientific_validation': False}}
    paths = [repo / p for p in DATABASES] if controlled_paths is None else [Path(p) for p in controlled_paths]
    previous_umask = os.umask(0o077)
    try:
        evidence['references'] = capture_references(reference_inputs, repo, paths, output)
        records = snapshot_pair(paths, output, evidence, additional_uids=additional_uids)
        inspect_copies(records, output, evidence)
        evidence['status'] = 'completed_read_only_census'
    except BaseException as error:
        evidence['status'] = 'refused_or_failed'
        evidence['failure'] = {'type': type(error).__module__ + '.' + type(error).__qualname__,
            'message': str(error), 'code': getattr(error, 'code', None),
            'detail': getattr(error, 'detail', None), 'traceback': traceback.format_exc()}
    finally:
        write_json(output / 'evidence.json', evidence)
        os.umask(previous_umask)
    return evidence
