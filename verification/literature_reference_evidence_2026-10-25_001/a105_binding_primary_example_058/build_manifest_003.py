"""Add final inventory; never rewrite earlier manifests or artifacts."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def main():
    excluded = ['MANIFEST_003.json', 'FINAL_VERIFY_003.json']
    files = {}
    for path in sorted(HERE.rglob('*')):
        if not path.is_file() or str(path.relative_to(HERE)) in excluded:
            continue
        files[str(path.relative_to(HERE))] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'bytes': path.stat().st_size, 'mode': oct(path.stat().st_mode & 0o777)}
    value = {'scope': 'Own058 additive delivery only; immutable original001 proposal, retained failed002 and fresh passed003;004 is a presentation engineering probe',
        'excluded': excluded, 'files': files}
    with (HERE / 'MANIFEST_003.json').open('x') as stream:
        json.dump(value, stream, indent=2); stream.write('\n')
    print(json.dumps({'files': len(files), 'bytes': sum(row['bytes'] for row in files.values())}))

if __name__ == '__main__':
    main()
