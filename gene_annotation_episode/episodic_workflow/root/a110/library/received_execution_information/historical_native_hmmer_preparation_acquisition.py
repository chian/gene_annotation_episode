"""Acquire one original HMMER preparation attempt, without work or grading.

The saved plan anchors the original request and paths. Replay reads only that
plan and retained Store bytes. Repeated operands and working-copy/output roles
remain separate associations even when their content-addressed bytes coincide.
The recorded producer ABI belongs to that original execution; replay never
substitutes the current host's ABI or reopens a producer to recover it.
"""
from __future__ import annotations
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a110.materials import artifact_file
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_infernal_contracts import finite_json_copy
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_state import canonical
_PREFIX = 'native_hmmer_preparation_'

def _error(code):
    raise ContractError(_PREFIX + code)

def _path(value, *, absolute=False):
    if type(value) is not str or not value or any((c in value for c in '\x00\r\n\\')) or value.startswith('//') or ('..' in value.split('/')) or (value in {'.', '/'}):
        _error('capture_path_invalid')
    path = PurePosixPath(value)
    if path.is_absolute() != absolute or str(path) != value:
        _error('capture_path_invalid')
    return path

def _sha(value, *, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        _error('bundle_digest_invalid')

def _directory(value):
    directory = Path(value).absolute()
    _path(str(directory), absolute=True)
    if directory.resolve() != directory:
        _error('capture_directory_escape')
    return directory

@contextmanager
def _confined_reader(root, relative):
    relative, root = (_path(relative), _directory(root))
    descriptors = []
    try:
        descriptors.append(os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW))
        for part in relative.parts[:-1]:
            descriptors.append(os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptors[-1]))
        descriptor = os.open(relative.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=descriptors[-1])
        descriptors.append(descriptor)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            _error('capture_regular_file_required')
        yield (Path('/proc/self/fd') / str(descriptor))
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)

def _capture_file(store, root, relative, media_type='application/octet-stream'):
    with _confined_reader(root, relative) as path:
        return artifact_file(store, path, media_type)

def _retained(store, reference):
    if type(reference) is not str:
        _error('capture_artifact_reference_invalid')
    metadata = store._require(reference, {'artifact'})
    _sha(metadata['sha256'])
    if reference != 'artifact_' + metadata['sha256'] or type(metadata['size']) is not int or metadata['size'] < 0:
        _error('capture_artifact_identity_conflict')
    with _confined_reader(store.path / 'artifacts', metadata['sha256'][:2] + '/' + metadata['sha256']) as path:
        digest, size = (hashlib.sha256(), 0)
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
                size += len(block)
        if size != metadata['size'] or digest.hexdigest() != metadata['sha256']:
            _error('capture_artifact_measurement_conflict')
    return metadata

def _decode(raw):

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                _error('manifest_duplicate_key')
            result[key] = value
        return result
    try:
        return finite_json_copy(json.loads(raw, object_pairs_hook=unique))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ContractError(_PREFIX + 'manifest_json_invalid') from error

def _read_record(directory, name):
    with _confined_reader(directory, name) as path:
        raw = path.read_bytes()
    value = _decode(raw)
    if raw != (canonical(value) + '\n').encode('utf-8'):
        _error('capture_record_bytes_changed')
    return value
