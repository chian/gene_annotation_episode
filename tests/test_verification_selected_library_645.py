"""Exercise prospective runtime-library custody inside the bounded checker."""
import ctypes
import hashlib
import json
import os
from pathlib import Path


def test_selected_dns_library_is_pinned_before_it_is_loaded():
    attempt = Path(os.environ['HMMER529_ATTEMPT'])
    selected = json.loads((attempt / 'selected_native_libraries.json').read_text())
    assert len(selected) == 1
    row = selected[0]
    assert Path(row['path']).name == 'libnss_mdns4_minimal.so.2'
    assert json.loads((attempt / 'selected_request.json').read_text())['native_libraries'] == selected
    before = {r['path']: r for r in json.loads((attempt / 'native_library_pins_before.json').read_text())}
    assert before[row['path']] == row
    assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['sha256']
    library = ctypes.CDLL(row['path'])
    assert library._handle
    assert row['path'] in Path('/proc/self/maps').read_text()
