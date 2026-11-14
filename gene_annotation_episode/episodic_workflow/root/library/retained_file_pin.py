"""Original stable streamed file pin beside retained byte reading."""
import hashlib
import os
from .retained_file_read import regular, require, _stable

def file_pin(path):
    h = hashlib.sha256()
    with regular(path) as stream:
        before = os.fstat(stream.fileno())
        while block := stream.read(1024 * 1024):
            h.update(block)
        require(_stable(before, os.fstat(stream.fileno())), "fba_file_changed_during_read")
    return {"path": str(path), "sha256": h.hexdigest(), "size_bytes": before.st_size}
