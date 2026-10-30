"""Verify the separately owned079 pin without importing or changing its code."""
import hashlib
import json
from pathlib import Path

base = Path(__file__).resolve().parent
manifest = json.loads((base / 'PIN_MANIFEST_001.json').read_text())
pin = base / 'pin_001'
for name, expected in manifest['files'].items():
    data = (pin / name).read_bytes()
    assert len(data) == expected['size'], name
    assert hashlib.sha256(data).hexdigest() == expected['sha256'], name
actual = {str(path.relative_to(pin)) for path in pin.rglob('*') if path.is_file()}
assert actual == set(manifest['files'])
before = base / 'before/gene_annotation_episode/literature_ratio_source_storage.py'
assert hashlib.sha256(before.read_bytes()).hexdigest() == manifest['native_before_sha256']
print(json.dumps({'verified_files': len(actual), 'native_before_verified': True,
    'native_sha256': manifest['files']['gene_annotation_episode/literature_ratio_source_storage.py']['sha256']}))
