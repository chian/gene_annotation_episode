"""Additive immutable pin preparation; never runs a reader or Episode."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PIN = HERE / 'pin_003'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    PIN.mkdir(exist_ok=False)
    files = []
    for package in ('gene_annotation_episode', 'method_loop'):
        for path in sorted((ROOT / package).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                files.append((path, Path(package) / path.relative_to(ROOT / package)))
    files.extend([(ROOT / 'pyproject.toml', Path('pyproject.toml')),
                  (HERE / 'run_primary_003.py', Path('run_primary_003.py'))])
    case = HERE.parent / 'a105_binding_case_042'
    identities = json.loads((HERE / 'SOURCE_IDENTITIES_001.json').read_bytes())
    for name, row in identities.items():
        original = case / name
        assert sha(original) == row['sha256'] and original.stat().st_size == row['bytes']
        files.append((original, Path('inputs') / name))
    for name in ('PROPOSED_SOURCE_NOMINATIONS_001.json', 'EXPECTED_ARITHMETIC_001.json'):
        files.append((HERE / name, Path('inputs') / name))
    files.append((ROOT / 'cases/gene_001/target.fna', Path('inputs/target.fna')))
    manifest = {}
    for original, relative in files:
        digest = sha(original)
        destination = PIN / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, destination)
        assert sha(destination) == sha(original) == digest
        manifest[str(relative)] = {'sha256': digest, 'bytes': destination.stat().st_size,
                                  'original': str(original)}
    # All imports and inputs are sealed before the first native operation.
    (PIN / 'PIN_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    for path in PIN.rglob('*'):
        if path.is_file():
            path.chmod(0o444)
    for path in sorted(PIN.rglob('*'), reverse=True):
        if path.is_dir():
            path.chmod(0o555)
    PIN.chmod(0o555)
    print(json.dumps({'prepared': True, 'files': len(manifest), 'manifest_sha256': sha(PIN / 'PIN_MANIFEST.json')}))

if __name__ == '__main__':
    main()
