"""Package the stable early-guard generation; preserve all earlier artifacts."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess

STAGE = Path(__file__).absolute().parent
ROOT = next(p for p in STAGE.parents if (p / '.venv/bin/python').exists())
baseline = json.loads((STAGE / 'BASELINE_004.json').read_text())
names = [*baseline, 'tests/test_contract_information_runtime_059.py',
    'tests/test_contract_information_custody_059.py', 'tests/test_contract_information_worker_059.py']
patch, rows = [], {}
for name in names:
    old = (STAGE / 'baseline' / name).read_text() if name in baseline else ''
    raw = (ROOT / name).read_bytes()
    assert raw == (STAGE / 'pin_006' / name).read_bytes(), name
    new = raw.decode()
    patch.extend(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                    fromfile='a/' + name, tofile='b/' + name))
    target = STAGE / 'snapshot_005' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream: stream.write(raw)
    rows[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
patch_path = STAGE / 'IMPLEMENTATION_005.patch'
with patch_path.open('x') as stream: stream.write(''.join(patch))
rebuilt = STAGE / 'reconstructed_005'
shutil.copytree(STAGE / 'baseline', rebuilt)
result = subprocess.run(['patch', '-p1', '--batch', '-i', str(patch_path)], cwd=rebuilt,
                        text=True, capture_output=True)
assert result.returncode == 0, result.stdout + result.stderr
for name, row in rows.items():
    assert hashlib.sha256((rebuilt / name).read_bytes()).hexdigest() == row['sha256'], name
receipt = {'files': rows, 'patch': {'bytes': patch_path.stat().st_size,
    'sha256': hashlib.sha256(patch_path.read_bytes()).hexdigest()}, 'reconstruction_matches_all': True,
    'baseline_count': len(baseline), 'pin_generation': 'pin_006', 'early_pre_provider_configuration_guard': True}
with (STAGE / 'SOURCE_RECEIPT_005.json').open('x') as stream:
    json.dump(receipt, stream, indent=2); stream.write('\n')
print(json.dumps({'snapshot': str(STAGE / 'snapshot_005'), 'patch_lines': len(patch), 'files': len(rows),
                  'patch_sha256': receipt['patch']['sha256']}))
