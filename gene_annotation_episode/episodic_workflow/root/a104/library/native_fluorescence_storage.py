"""Store-independent finite I/O for the selected fluorescence producer.

No decoder, scientific calculation or application authority is imported here.
Final artifacts are published atomically without replacing an existing result.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import stat
from gene_annotation_episode.episodic_workflow.root.a104.library.fluorescence_execution_common import require

def directory(path):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts and (not str(path).startswith('//')) and (not any((c in str(path) for c in '\x00\r\n\\'))), 'invalid_fluorescence_path')
    for part in [*reversed(path.parents), path]:
        if part.exists() or part.is_symlink():
            require(not part.is_symlink() and part.is_dir(), 'fluorescence_non_directory_or_symlink')
    return path

@contextmanager
def regular(path):
    path = Path(path)
    directory(path.parent)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    stream = os.fdopen(fd, 'rb')
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), 'fluorescence_non_regular_file')
        yield stream
    finally:
        stream.close()

def decode_json(raw):

    def pairs(rows):
        value = {}
        for key, item in rows:
            require(key not in value, 'duplicate_fluorescence_json_key')
            value[key] = item
        return value

    def invalid(_):
        raise ValueError('nonfinite_fluorescence_json')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)

def read_json(path):
    with regular(path) as stream:
        return decode_json(stream.read())
