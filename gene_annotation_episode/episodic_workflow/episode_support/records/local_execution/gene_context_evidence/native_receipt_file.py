"""Private A103 atomic native receipt writer."""
import json
import os
from pathlib import Path


def atomic_json(path, body):
    path = Path(path)
    temporary = path.with_name(path.name + '.writing')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(body, stream, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

