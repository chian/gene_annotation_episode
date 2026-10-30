"""Freeze one complete current application/shared-loop/static-asset generation."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path.cwd()
STAGE = Path(__file__).resolve().parent
PIN = STAGE / 'pin_005'
PIN.mkdir(exist_ok=False)
paths = sorted(p for package in ('gene_annotation_episode', 'method_loop', 'tests')
               for p in (ROOT / package).rglob('*') if p.is_file()
               and '__pycache__' not in p.parts and (package != 'tests' or p.suffix == '.py'))
paths += [STAGE / 'run_connected_checks_005.py']
rows = {}
for path in paths:
    name = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT / 'gene_annotation_episode') or path.is_relative_to(ROOT / 'method_loop') or path.is_relative_to(ROOT / 'tests') else path.name
    raw = path.read_bytes()
    target = PIN / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    rows[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
for path in (STAGE / 'baseline').rglob('*.py'):
    name = 'baseline/' + str(path.relative_to(STAGE / 'baseline'))
    raw = path.read_bytes()
    target = PIN / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    rows[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
# Verify current files did not change during capture; frozen baselines are
# separately hash-recorded in BASELINE_004 and never imported as an application.
for path in paths:
    name = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT / 'gene_annotation_episode') or path.is_relative_to(ROOT / 'method_loop') or path.is_relative_to(ROOT / 'tests') else path.name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == rows[name]['sha256'], name
(PIN / 'PIN_MANIFEST.json').write_text(json.dumps(rows, indent=2, sort_keys=True) + '\n')
print(json.dumps({'pin': str(PIN), 'entries': len(rows), 'bytes': sum(row['bytes'] for row in rows.values()),
                  'manifest_sha256': hashlib.sha256((PIN / 'PIN_MANIFEST.json').read_bytes()).hexdigest()}))
