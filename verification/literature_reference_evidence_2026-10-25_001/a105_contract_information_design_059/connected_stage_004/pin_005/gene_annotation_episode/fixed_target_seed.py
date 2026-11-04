"""Reproduce one original caller target in fresh custody, without old work.

The source is a read-only input witness. Only Store.create_problem constructs
the staged destination; no source rows, findings or execution state are imported.
"""
from __future__ import annotations

from collections import Counter
import ctypes
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from .domain import ContractError, canonical, identity, parse_sequences
from .state import Store


VERSION = 'fixed_target_seed_v1'
_INTAKE_KINDS = {'input', 'source', 'material', 'parse_attempt', 'collection',
                 'collection_member', 'artifact'}
_EXCLUDED_KINDS = ('hypothesis', 'assessment', 'annotation',
                   'interpretation_account', 'native_execution', 'product')
_EXCLUSIONS = ['historical_scientific_interpretations', 'historical_native_executions',
    'runtime_history', 'historical_product_records', 'native_registry',
    'statistics_history', 'provider_state', 'pending_measurement_exports']


class FixedTargetSeedError(ValueError):
    """Typed preparation failure; a failed stage is retained for inspection."""
    def __init__(self, code, affected_refs=(), staging_workspace=None):
        self.failure = {'version': 'fixed_target_seed_failure_v1', 'code': code,
            'affected_refs': [str(ref) for ref in affected_refs],
            'staging_workspace': None if staging_workspace is None else str(staging_workspace)}
        super().__init__(canonical(self.failure))

    def as_record(self):
        return json.loads(canonical(self.failure))


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _content(value):
    return _sha(canonical(value).encode())


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
    result = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    canonical(result)
    return result


def _path(value, code):
    try:
        path = Path(value).expanduser().absolute()
        for part in (path, *path.parents):
            if part.is_symlink():
                raise FixedTargetSeedError(code, [part])
        return path.resolve()
    except (OSError, TypeError, ValueError) as error:
        if isinstance(error, FixedTargetSeedError):
            raise
        raise FixedTargetSeedError(code, [str(value)]) from error


def _file_hash(path):
    digest, size = hashlib.sha256(), 0
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _source_files(workspace, code):
    """Opaque custody checks; unrelated SQLite rows are never hydrated."""
    result = {}
    for path in sorted(workspace.rglob('*')):
        if path.is_symlink():
            raise FixedTargetSeedError(code, [path])
        if path.is_file():
            checksum, size = _file_hash(path)
            result[str(path.relative_to(workspace))] = {'sha256': checksum, 'size': size}
    return result


def _source_preservation(workspace, before, after):
    main, wal, shm = 'state.sqlite3', 'state.sqlite3-wal', 'state.sqlite3-shm'
    changes, affected = [], []
    if before.get(main) != after.get(main):
        affected.append(workspace/main)
    if before.get(wal) != after.get(wal):
        if before.get(wal) is None and after.get(wal) == {'sha256': _sha(b''), 'size': 0}:
            changes.append('empty_wal_created')
        else:
            affected.append(workspace/wal)
    if before.get(shm) != after.get(shm):
        if after.get(shm) is None:
            affected.append(workspace/shm)
        else:
            changes.append('shm_created' if before.get(shm) is None else 'shm_changed')
    for name in sorted(set(before) | set(after)):
        if name not in {main, wal, shm} and before.get(name) != after.get(name):
            affected.append(workspace/name)
    if affected:
        raise FixedTargetSeedError('identity_mismatch', affected)
    return {'main_database_before': before[main], 'main_database_after': after[main],
        'wal_before': before.get(wal), 'wal_after': after.get(wal),
        'shm_before': before.get(shm), 'shm_after': after.get(shm),
        'observed_changes': changes, 'authoritative_bytes_unchanged': True}


def _source_get(db, reference):
    for table in ('inputs', 'records', 'material_members'):
        row = db.execute(f'SELECT data FROM {table} WHERE id=?', (reference,)).fetchone()
        if row is not None:
            value = _json(row[0])
            if value.get('id') != reference:
                raise FixedTargetSeedError('identity_mismatch', [reference])
            return value
    row = db.execute('SELECT * FROM artifacts WHERE id=?', (reference,)).fetchone()
    if row is not None:
        return {**dict(row), 'record_type': 'artifact'}
    raise FixedTargetSeedError('source_input_missing', [reference])


def _references(value):
    """The existing Store reference fields, without constructing a source Store."""
    if isinstance(value, dict):
        for key, child in value.items():
            if (key.endswith('_ref') or key == 'ref') and child is not None:
                yield child
            elif key.endswith('_refs') or key == 'dependencies':
                yield from child
            else:
                yield from _references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _references(child)


def _closure(db, problem):
    pending = list(_references(problem))
    result = {}
    while pending:
        reference = pending.pop()
        if reference in result:
            continue
        value = _source_get(db, reference)
        if value.get('record_type') not in _INTAKE_KINDS:
            raise FixedTargetSeedError('source_input_invalid', [reference])
        result[reference] = value
        pending.extend(_references(value))
        if value['record_type'] == 'collection':
            pending.extend(row[0] for row in db.execute(
                'SELECT id FROM material_members WHERE collection_ref=? ORDER BY ordinal', (reference,)))
    return result


def _artifact(workspace, record):
    reference = record['id']
    try:
        checksum = record['sha256']
        if (reference != 'artifact_' + checksum or len(checksum) != 64
                or any(c not in '0123456789abcdef' for c in checksum)
                or type(record['size']) is not int or record['size'] < 0):
            raise ValueError('artifact_metadata_invalid')
        path = _path(workspace/'artifacts'/checksum[:2]/checksum, 'artifact_custody_failure')
        if not path.is_relative_to(workspace/'artifacts'):
            raise ValueError('artifact_outside_workspace')
        if _file_hash(path) != (checksum, record['size']):
            raise ValueError('artifact_bytes_changed')
        return path
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise FixedTargetSeedError('artifact_custody_failure', [reference]) from error


def _indexes(db, problem):
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    keys = [db.execute("SELECT json_extract(data,'$.parse_key') FROM records WHERE id=?", (ref,)).fetchone()[0]
            for ref in problem['initial_parse_refs']]
    result = {}
    for table, order in (
            ('material_members', 'parse_key,ordinal'),
            ('material_errors', 'parse_key,error_index'),
            ('material_annotations', 'parse_key,record_ordinal,entry_kind,entry_ordinal'),
            ('material_pack_chunks', 'parse_key,chunk_index'),
            ('material_name_counts', 'parse_key,name')):
        result[table] = ([] if table not in tables else [dict(row) for key in keys
            for row in db.execute(f'SELECT * FROM {table} WHERE parse_key=? ORDER BY {order}', (key,))])
    members = [row['id'] for row in result['material_members']]
    result['material_component_spans'] = ([] if 'material_component_spans' not in tables else
        [dict(row) for ref in members for row in db.execute(
            'SELECT * FROM material_component_spans WHERE member_ref=? ORDER BY component,part', (ref,))])
    return result


def _witness(db, workspace, case, case_directory):
    rows = db.execute('SELECT data FROM problem ORDER BY singleton').fetchall()
    if len(rows) != 1:
        raise FixedTargetSeedError('source_input_invalid', ['problem'])
    problem = _json(rows[0][0])
    target_ref = case['target_ref']
    if (problem.get('id') != case['problem_ref'] or problem.get('subject_refs') != [target_ref]
            or problem['id'] != identity('problem', {k: v for k, v in problem.items() if k != 'id'})
            or db.execute('SELECT count(*) FROM inputs').fetchone()[0] != 1):
        raise FixedTargetSeedError('identity_mismatch', [case['problem_ref'], target_ref])
    target = _source_get(db, target_ref)
    if (target.get('record_type') != 'input' or target.get('molecule') != 'dna'
            or target.get('role') != 'gene' or target.get('length') != case['dna_length_nt']
            or target_ref != identity('input', {k: v for k, v in target.items()
                if k not in {'id', 'record_type', 'origin'}})):
        raise FixedTargetSeedError('identity_mismatch', [target_ref])
    if (problem.get('intake_status') != 'completed'
            or any(len(problem.get(key, [])) != 1 for key in
                   ('material_refs', 'initial_parse_refs', 'initial_collection_refs'))
            or not problem.get('caller_context_ref') or not problem.get('caller_context_source_ref')):
        raise FixedTargetSeedError('source_input_invalid', [problem['id']])
    records = _closure(db, problem)
    members = [row for row in records.values() if row['record_type'] == 'collection_member']
    material = records[problem['material_refs'][0]]
    source = records[material['source_ref']]
    attempt = records[problem['initial_parse_refs'][0]]
    collection = records[problem['initial_collection_refs'][0]]
    if (len(members) != 1 or target.get('source_record', {}).get('member_ref') != members[0]['id']
            or material['requested_format'] != 'fasta' or material['use'] != 'target'
            or source['uri'] != (case_directory/'target.fna').as_uri()
            or attempt['representation'] != 'fasta' or attempt['compression'] != 'none'
            or attempt['status'] != 'completed' or attempt['valid_records'] != 1 or attempt['error_count'] != 0
            or collection['representation'] != 'fasta' or collection['member_count'] != 1
            or not collection['complete']):
        raise FixedTargetSeedError('source_input_invalid', [problem['id']])
    artifacts = {ref: row for ref, row in records.items() if row['record_type'] == 'artifact'}
    for row in artifacts.values():
        _artifact(workspace, row)
    context_ref = problem['caller_context_ref']
    context_source = records[problem['caller_context_source_ref']]
    if (context_ref not in artifacts or context_source['artifact_ref'] != context_ref
            or context_source['provider'] != 'caller_context' or context_source['origin'] != 'caller'):
        raise FixedTargetSeedError('identity_mismatch', [context_ref])
    context = _json(_artifact(workspace, artifacts[context_ref]).read_bytes())
    roots = [dict(row) for ref in sorted(records) for row in db.execute(
        'SELECT * FROM record_roots WHERE record_ref=? ORDER BY target_ref', (ref,))]
    return problem, target, context, records, artifacts, _indexes(db, problem), roots


def _publish_directory(stage, destination, parent_fd):
    """Linux atomic no-replace directory publication, including empty outputs."""
    pinned = os.fstat(parent_fd)
    try:
        current = destination.parent.stat(follow_symlinks=False)
    except OSError:
        current = None
    if current is None or (current.st_dev, current.st_ino) != (pinned.st_dev, pinned.st_ino):
        # The pinned directory may have moved. Resolve its current location,
        # not the stale original pathname, for the retained partial output.
        try:
            actual_stage = Path(os.readlink(f'/proc/self/fd/{parent_fd}'))/stage.name
            retained = actual_stage if actual_stage.is_dir() else None
        except OSError:
            retained = None
        raise FixedTargetSeedError('publication_failure', [destination.parent, destination], retained)
    rename = ctypes.CDLL(None, use_errno=True).renameat2
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(parent_fd, os.fsencode(stage.name), parent_fd, os.fsencode(destination.name), 1) != 0:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number), str(destination))
    try:
        os.fsync(parent_fd)
    except OSError as error:
        # Rename succeeded: retain the published partial output and report its
        # actual path, never an old stage that no longer exists.
        raise FixedTargetSeedError('publication_failure', [destination]) from error


def prepare_fixed_target_seed(*, case_directory, source_workspace, destination_workspace):
    """Verify a read-only original intake and reproduce it at an unused path."""
    stage = None
    db = None
    parent_fd = None
    phase = 'source_input_invalid'
    case_directory = _path(case_directory, 'source_input_invalid')
    source_workspace = _path(source_workspace, 'source_input_invalid')
    destination = _path(destination_workspace, 'destination_invalid')
    try:
        if (destination.is_relative_to(source_workspace) or source_workspace.is_relative_to(destination)
                or case_directory.is_relative_to(destination)):
            raise FixedTargetSeedError('destination_overlap', [destination, source_workspace])
        if destination.exists():
            raise FixedTargetSeedError('destination_exists', [destination])
        for parent in destination.parents:
            if any((parent/name).is_file() for name in ('case-launch.json', 'run.json',
                    'policy-binding.json', 'episode-execution-binding.json')):
                raise FixedTargetSeedError('destination_overlap', [destination, parent])
    except OSError as error:
        raise FixedTargetSeedError('destination_invalid', [destination]) from error
    try:
        case_path = _path(case_directory/'case.json', 'source_input_invalid')
        case_bytes = case_path.read_bytes()
        case = _json(case_bytes)
        if (case.get('target_kind') != 'single_gene'
                or set(case['target_files']) != {'target.fna', 'target.faa'}
                or any(type(case[key]) is not int or case[key] < 1 for key in ('dna_length_nt', 'protein_length_aa'))
                or any(not isinstance(case[key], str) or not case[key]
                       for key in ('case_ref', 'problem_ref', 'target_ref', 'source_protein'))):
            raise ValueError('fixed_case_fields_invalid')
        files, sequences = {}, {}
        for name, molecule, label in (('target.fna', 'dna', 'target_fna'), ('target.faa', 'protein', 'target_faa')):
            path = _path(case_directory/name, 'source_input_invalid')
            raw = path.read_bytes()
            checksum = _sha(raw)
            if checksum != case['target_files'][name]:
                raise FixedTargetSeedError('identity_mismatch', [path])
            parsed = parse_sequences(raw, format='fasta', molecule=molecule)
            if len(parsed) != 1 or parsed[0].issues:
                raise ValueError('one_original_sequence_required')
            sequences[molecule] = parsed[0].sequence
            files[label] = {'path': str(path), 'sha256': checksum}
        if (len(sequences['dna']) != case['dna_length_nt']
                or len(sequences['protein']) != case['protein_length_aa']):
            raise FixedTargetSeedError('identity_mismatch', [case_path])
        database = _path(source_workspace/'state.sqlite3', 'source_input_invalid')
        if not database.is_file():
            raise FixedTargetSeedError('source_input_missing', [database])
        source_before = _source_files(source_workspace, 'source_input_invalid')
        # Reader SHM synchronization/empty-WAL creation is measured separately
        # from authoritative DB/WAL/row/artifact preservation (scope amendment).
        db = sqlite3.connect(database.as_uri()+'?mode=ro', uri=True)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        captured_at = datetime.now(timezone.utc).isoformat()
        problem, target, context, records, artifacts, indexes, roots = _witness(
            db, source_workspace, case, case_directory)
        dna_sha, protein_sha = _sha(sequences['dna'].encode()), _sha(sequences['protein'].encode())
        if (target['sequence_ref'] != 'artifact_'+dna_sha
                or artifacts[target['sequence_ref']]['size'] != case['dna_length_nt']):
            raise FixedTargetSeedError('identity_mismatch', [target['id']])
        phase = 'destination_invalid'
        destination.parent.mkdir(parents=True, exist_ok=True)
        _path(destination, 'destination_invalid')
        if destination.exists():
            raise FixedTargetSeedError('destination_exists', [destination])
        parent_fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        stage = Path(tempfile.mkdtemp(prefix='.'+destination.name+'.seed-', dir=destination.parent))
        phase = 'intake_mismatch'
        with Store(stage) as store:
            created = store.create_problem(case_directory/'target.fna', molecule='dna', role='gene',
                caller_context=context, format='fasta')
            if created != problem or store.get_input(target['id']) != target:
                raise FixedTargetSeedError('intake_mismatch', [problem['id'], target['id']], stage)
            actual = _closure(store.db, created)
            if actual != records or _indexes(store.db, created) != indexes:
                raise FixedTargetSeedError('intake_mismatch', [problem['id']], stage)
            actual_roots = [dict(row) for ref in sorted(actual) for row in store.db.execute(
                'SELECT * FROM record_roots WHERE record_ref=? ORDER BY target_ref', (ref,))]
            if actual_roots != roots:
                raise FixedTargetSeedError('intake_mismatch', [problem['id']], stage)
            for row in artifacts.values():
                _artifact(stage, row)
            known = sorted(actual)
            if any(store.get(ref) != actual[ref] for ref in known):
                raise FixedTargetSeedError('intake_mismatch', known, stage)
            excluded = {kind: store.db.execute('SELECT count(*) FROM records WHERE record_type=?', (kind,)).fetchone()[0]
                        for kind in _EXCLUDED_KINDS}
            tables = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            excluded_tables = {name: store.db.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
                for name in tables if name in {'current_revisions', 'proposals', 'reasoning_commits'}
                or name.startswith(('runtime_', 'homology_', 'native_', 'remote_')) or name == 'tool_operations'}
            if any(excluded.values()) or any(excluded_tables.values()):
                raise FixedTargetSeedError('intake_mismatch', [str(stage)], stage)
            receipt = {'version': VERSION,
                'source': {'case_directory': str(case_directory), 'workspace': str(source_workspace),
                    'captured_at': captured_at, 'case_sha256': _sha(case_bytes),
                    'problem_sha256': _content(problem), 'target_sha256': _content(target),
                    'caller_context_sha256': artifacts[problem['caller_context_ref']]['sha256'],
                    'caller_context_artifact_ref': problem['caller_context_ref']},
                'workspace': str(destination),
                'fixed_identity': {'case_ref': case['case_ref'], 'problem_ref': problem['id'],
                    'target_ref': target['id'], 'dna_length_nt': case['dna_length_nt'],
                    'protein_length_aa': case['protein_length_aa'], 'source_protein': case['source_protein'],
                    'dna_sequence_sha256': dna_sha, 'protein_sequence_sha256': protein_sha},
                'input_files': files,
                'intake_records': [{'reference': ref, 'record_type': records[ref]['record_type'],
                    'content_sha256': _content(records[ref])} for ref in sorted(records)],
                'artifact_manifest': [{key: artifacts[ref][key] for key in ('id', 'sha256', 'media_type', 'size')}
                    for ref in sorted(artifacts)],
                'initial_known_record_refs': known,
                'verification': {'problem_equal': True, 'input_equal': True, 'intake_equal': True,
                    'artifact_bytes_equal': True, 'material_indexes_equal': True,
                    'initial_known_record_ref_count': len(known),
                    'initial_known_record_refs_sha256': _content(known),
                    'record_counts': dict(sorted(Counter(row['record_type'] for row in actual.values()).items())),
                    'excluded_record_counts': excluded, 'excluded_table_counts': excluded_tables},
                'exclusions': list(_EXCLUSIONS)}
        db.close()
        db = None
        phase = 'identity_mismatch'
        # The original files are constructor operands, not copied declarations.
        for value in [*files.values(), {'path': str(case_path), 'sha256': _sha(case_bytes)}]:
            if _file_hash(Path(value['path']))[0] != value['sha256']:
                raise FixedTargetSeedError('identity_mismatch', [value['path']], stage)
        receipt['verification']['sqlite_reader_bookkeeping'] = _source_preservation(
            source_workspace, source_before, _source_files(source_workspace, 'identity_mismatch'))
        phase = 'publication_failure'
        with (stage/'fixed-target-seed.json').open('x', encoding='utf-8') as stream:
            stream.write(canonical(receipt)+'\n')
            stream.flush()
            os.fsync(stream.fileno())
        (stage/'fixed-target-seed.json').chmod(0o444)
        stage_fd = os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(stage_fd)
        finally:
            os.close(stage_fd)
        _path(destination, 'destination_invalid')
        _publish_directory(stage, destination, parent_fd)
        return receipt
    except FixedTargetSeedError as error:
        if stage is not None and stage.exists() and error.failure['staging_workspace'] is None:
            raise FixedTargetSeedError(error.failure['code'], error.failure['affected_refs'], stage) from error
        raise
    except FileNotFoundError as error:
        raise FixedTargetSeedError('source_input_missing' if stage is None else phase,
            [error.filename or str(source_workspace)], stage) from error
    except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, AttributeError) as error:
        code = ('destination_exists' if phase == 'publication_failure'
                and isinstance(error, OSError) and error.errno == errno.EEXIST else phase)
        raise FixedTargetSeedError(code, [str(destination) if stage is not None else str(source_workspace)], stage) from error
    finally:
        if db is not None:
            db.close()
        if parent_fd is not None:
            os.close(parent_fd)


__all__ = ['prepare_fixed_target_seed', 'FixedTargetSeedError']
