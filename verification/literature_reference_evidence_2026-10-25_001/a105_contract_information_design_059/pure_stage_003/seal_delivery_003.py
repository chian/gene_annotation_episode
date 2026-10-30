"""Seal the four released pure files and their exact executed generation."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
OWNED = ['gene_annotation_episode/schema_information_text.py', 'gene_annotation_episode/episode_contract_information.py',
         'tests/test_schema_information_text.py', 'tests/test_episode_contract_information.py']


def fingerprint(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    before = json.loads((OUT / 'BEFORE_003.json').read_bytes())
    for name, row in before['read_only_dependencies'].items():
        assert fingerprint(ROOT / name) == row, name
        destination = OUT / 'baseline' / name
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as stream:
                stream.write((ROOT / name).read_bytes())
        assert fingerprint(destination) == row
    run = OUT / 'frozen_checks_003'
    terminal = json.loads((run / 'TERMINAL_RECEIPT_003.json').read_bytes())
    worker = json.loads((run / 'WORKER_RECEIPT_003.json').read_bytes())
    assert terminal['exit_code'] == worker['pytest_exit_code'] == 0
    pin = run / 'pin'
    manifest = json.loads((pin / 'PIN_MANIFEST.json').read_bytes())
    assert fingerprint(pin / 'PIN_MANIFEST.json')['sha256'] == terminal['pin_manifest_sha256'] == worker['pin_manifest_sha256']
    for name, row in manifest.items():
        assert fingerprint(pin / name) == row, name
    assert '167 passed in 3.00s' in (run / 'TERMINAL_003.log').read_text()
    sources, patch = {}, []
    for name in OWNED:
        row = fingerprint(ROOT / name)
        assert row == manifest[name]
        destination = OUT / 'snapshot_003' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as stream:
            stream.write((ROOT / name).read_bytes())
        sources[name] = {**row, 'lines': len((ROOT / name).read_text().splitlines()), 'original': 'absent before released stage'}
        patch.extend(difflib.unified_diff([], (ROOT / name).read_text().splitlines(True),
                                        fromfile='/dev/null', tofile='b/' + name))
    with (OUT / 'IMPLEMENTATION_003.patch').open('x') as stream:
        stream.writelines(patch)
    reconstructed = OUT / 'reconstructed_003'
    reconstructed.mkdir()
    applied = subprocess.run(['patch', '-p1', '--batch', '--fuzz=0', '-i', str(OUT / 'IMPLEMENTATION_003.patch')],
        cwd=reconstructed, capture_output=True, text=True)
    assert applied.returncode == 0, applied.stdout + applied.stderr
    for name, row in sources.items():
        assert fingerprint(reconstructed / name) == {'bytes': row['bytes'], 'sha256': row['sha256']}
    initial = {'command': '.venv/bin/python -B -m pytest -q tests/test_schema_information_text.py tests/test_episode_contract_information.py --tb=short -p no:cacheprovider',
        'exit_code': 0, 'terminal': '166 passed in 2.85s',
        'meaning': 'First actual direct targeted run before the final malformed fact-type boundary repair and added case; no immutable generation claim'}
    save('INITIAL_TARGETED_RECEIPT_003.json', initial)
    receipt = {'status': 'pure_stage_delivered_pending_root_review', 'owned_files': sources,
        'read_only_dependencies_exact': len(before['read_only_dependencies']),
        'pin_files_verified': len(manifest), 'pinned_application_test_imports': len(worker['verified_imports']),
        'pin_manifest_sha256': terminal['pin_manifest_sha256'], 'terminal': '167 passed in 3.00s',
        'actual_operation_information_examples': worker['actual_operation_examples'],
        'actual_fact_information_examples': worker['actual_fact_examples'], 'actual_fact_form_examples': worker['actual_form_examples'],
        'all_four_files_patch_reconstructed_exact': True, 'shared_files_changed_by059': [],
        'scope': 'Pure schema information and saved form relationships; no installed lookup/decoder/native/runtime/C1/C4/model path',
        'scientific_sources': 0, 'model_calls': 0, 'actions': 0, 'observations': 0,
        'original_custody_authentication_claim': False, 'full_A105_or_goal_completion_claim': False}
    save('DELIVERY_RECEIPT_003.json', receipt)
    selected = [path for path in OUT.rglob('*') if path.is_file() and '__pycache__' not in path.parts
        and ('pin' not in path.relative_to(OUT).parts or path.name == 'PIN_MANIFEST.json')
        and 'reconstructed_003' not in path.relative_to(OUT).parts]
    entries = {str(path.relative_to(ROOT)): fingerprint(path) for path in sorted(selected)}
    entries.update({name: fingerprint(ROOT / name) for name in OWNED})
    save('MANIFEST_003.json', {'scope': 'Explicit stage003 delivery paths; executed source tree is separately authenticated by its full589-file PIN_MANIFEST', 'entries': entries})
    print(json.dumps({'status': receipt['status'], 'manifest_entries': len(entries),
        'manifest_sha256': fingerprint(OUT / 'MANIFEST_003.json')['sha256'], 'owned_files': len(OWNED),
        'pin_files': len(manifest), 'imports': len(worker['verified_imports'])}))


if __name__ == '__main__':
    main()
