"""Freeze current application Python bytes and the two new pure test files."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
OWNED = ['gene_annotation_episode/schema_information_text.py', 'gene_annotation_episode/episode_contract_information.py',
         'tests/test_schema_information_text.py', 'tests/test_episode_contract_information.py']


def fingerprint(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    baseline = json.loads((OUT / 'BEFORE_003.json').read_bytes())
    for name, row in baseline['read_only_dependencies'].items():
        assert fingerprint(ROOT / name) == row, name
    relevant = {name: fingerprint(ROOT / name) for name in [*baseline['read_only_dependencies'], *OWNED]}
    run = OUT / 'frozen_checks_003'
    run.mkdir(exist_ok=False)
    pin = run / 'pin'
    pin.mkdir()
    sources = [(path, str(path.relative_to(ROOT))) for package in ('gene_annotation_episode', 'method_loop')
        for path in sorted((ROOT / package).rglob('*.py')) if '__pycache__' not in path.parts]
    sources.extend((ROOT / name, name) for name in OWNED if name.startswith('tests/'))
    sources.append((OUT / 'run_frozen_checks_003.py', 'run_frozen_checks_003.py'))
    files = {}
    for source, name in sources:
        target = pin / name
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = source.read_bytes()
        with target.open('xb') as stream:
            stream.write(raw)
        files[name] = fingerprint(target)
    for name, row in relevant.items():
        assert fingerprint(ROOT / name) == row
        assert files[name] == row
    save(pin / 'PIN_MANIFEST.json', files)
    environment = {**os.environ, 'PYTHONPATH': str(pin) + ':' + str(pin / 'tests'), 'PYTHONDONTWRITEBYTECODE': '1'}
    started = datetime.now(timezone.utc).isoformat()
    with (run / 'TERMINAL_003.log').open('xb') as stream:
        result = subprocess.run([sys.executable, '-B', str(pin / 'run_frozen_checks_003.py'), str(run)],
            cwd=pin, env=environment, stdout=stream, stderr=subprocess.STDOUT)
    for name, row in relevant.items():
        assert fingerprint(ROOT / name) == row, name
    save(run / 'TERMINAL_RECEIPT_003.json', {'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
        'exit_code': result.returncode, 'pin_manifest_sha256': fingerprint(pin / 'PIN_MANIFEST.json')['sha256'],
        'relevant_current_files_exact_before_after': relevant,
        'copied_python_files': len(files), 'scope': 'Immutable pure-contract tests; no full-worktree or scientific claim'})
    print(json.dumps({'exit_code': result.returncode, 'pin_files': len(files), 'run': str(run)}))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
