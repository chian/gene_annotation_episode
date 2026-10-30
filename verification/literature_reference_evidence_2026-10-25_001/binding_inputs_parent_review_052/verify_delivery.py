"""Authenticate first-stage052 and bind a terminal test to exact current bytes."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
OWNER = OUT.parent / 'a105_binding_native_design_052'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((OWNER / 'MANIFEST_003.json').read_bytes())
    for row in manifest['files']:
        path = ROOT / row['path']
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], row['path']
    dependencies = json.loads((OWNER / 'EXAMPLE_RECEIPT_003.json').read_bytes())['protected_code_hashes_unchanged']
    for name, expected in dependencies.items():
        assert digest(ROOT / name) == expected
    names = ['gene_annotation_episode/literature_binding_interaction_inputs.py',
             'tests/test_literature_binding_interaction_inputs.py']
    reconstructed = OUT / 'reconstructed_003'
    reconstructed.mkdir(exist_ok=False)
    patch = subprocess.run(['patch', '-p1', '--batch', '-i', str(OWNER / 'IMPLEMENTATION_003.patch')],
        cwd=reconstructed, capture_output=True, text=True)
    assert patch.returncode == 0, patch.stdout + patch.stderr
    assert {p.relative_to(reconstructed).as_posix() for p in reconstructed.rglob('*') if p.is_file()} == set(names)
    for name in names:
        assert (reconstructed / name).read_bytes() == (ROOT / name).read_bytes() == (OWNER / 'snapshot_003' / name).read_bytes()
    protected = {name: digest(ROOT / name) for name in set(names) | set(dependencies)}
    command = [str(ROOT / '.venv/bin/python'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-q', names[1],
        '--tb=short', '--basetemp=' + str(OUT / 'pytest_003')]
    result = subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
        capture_output=True, text=True)
    with (OUT / 'TERMINAL_003.log').open('x') as stream:
        stream.write(result.stdout + result.stderr)
    assert result.returncode == 0 and '60 passed' in result.stdout, result.stdout + result.stderr
    assert {name: digest(ROOT / name) for name in protected} == protected
    receipt = {'passed': True, 'manifest_entries_verified': len(manifest['files']), 'patch_files_reconstructed': 2,
        'tests': 60, 'test_exit_code': result.returncode, 'exact_before_after_test_hashes': protected,
        'rerun_reason': 'Owner terminal had post-run hashes only; bind independent terminal to exact unchanged input/dependency bytes',
        'command': command, 'terminal_sha256': digest(OUT / 'TERMINAL_003.log'),
        'owner_manifest_sha256': digest(OWNER / 'MANIFEST_003.json'),
        'first_stage_only': True, 'storage_typed_delivery_not_implemented': True, 'primary_source_or_model_proof': False}
    with (OUT / 'RECEIPT_003.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: v for k, v in receipt.items() if k not in ('exact_before_after_test_hashes', 'command')}))


if __name__ == '__main__':
    main()
