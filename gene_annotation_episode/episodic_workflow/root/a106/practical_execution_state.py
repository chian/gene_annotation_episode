"""A106 immutable original API action and receipt files."""
import json
import os
import tempfile
from .practical_execution_records import canonical

def _read(path):
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
        if raw != (canonical(value) + '\n').encode('utf-8'):
            raise ValueError('practical_record_bytes_changed')
        return value
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError('invalid_practical_state_record') from error

def _immutable(path, value):
    """Publish fully written bytes once, without ever replacing a receipt."""
    payload = (canonical(value) + '\n').encode('utf-8')
    descriptor, temporary = tempfile.mkstemp(prefix='.practical-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise ValueError('practical_immutable_record_conflict')
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.unlink(temporary)

