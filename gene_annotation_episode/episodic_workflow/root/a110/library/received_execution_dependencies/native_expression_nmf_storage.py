from contextlib import contextmanager
import json
import os
from pathlib import Path
import stat
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.expression_nmf_common import require

def directory(path):
    path = Path(path)
    require(path.is_absolute() and str(path) == str(path.absolute()) and ('..' not in path.parts), 'invalid_nmf_path')
    for part in [*reversed(path.parents), path]:
        if part.exists() or part.is_symlink():
            require(not part.is_symlink() and part.is_dir(), 'nmf_non_directory_or_symlink')
    return path

@contextmanager
def regular(path):
    path = Path(path)
    directory(path.parent)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    stream = os.fdopen(fd, 'rb')
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), 'nmf_non_regular_file')
        yield stream
    finally:
        stream.close()

def decode_json(raw):

    def pairs(rows):
        value = {}
        for key, item in rows:
            require(key not in value, 'duplicate_nmf_json_key')
            value[key] = item
        return value

    def invalid(_):
        raise ValueError('nonfinite_nmf_json')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)

def read_json(path):
    with regular(path) as stream:
        return decode_json(stream.read())
