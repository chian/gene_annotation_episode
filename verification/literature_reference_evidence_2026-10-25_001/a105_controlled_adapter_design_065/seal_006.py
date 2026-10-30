"""Seal this design packet only; no model/source/runtime/calculator execution."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def emit(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    read = json.loads((HERE / 'READ_PROVENANCE_001.json').read_text())
    changes = []
    for item in read['files']:
        path = Path(item['path'])
        if digest(path.read_bytes()) != item['sha256']:
            changes.append({'path': str(path), 'read_sha256': item['sha256'],
                            'current_sha256': digest(path.read_bytes())})
    # Report real concurrent changes rather than overwriting an original pin.
    extra_reads = []
    parent = HERE.parent / 'controlled_adapter_parent_review_065'
    for name, scope in (
        ('probe_shared_representations_002.py', 'Complete delta from fully read001; exact Fraction-bound construction.'),
        ('shared_representation_probe_002/RESULT_001.json', 'Relevant exact input/local/V/verification projection, not complete expanded JSON prose read.'),
        ('PROBE_BOUNDARY_CORRECTION_002.md', 'Complete additive root precision correction.')):
        path = parent / name
        extra_reads.append({'path': str(path), 'sha256': digest(path.read_bytes()), 'scope': scope})
    emit('FINAL_CHECK_006.json', {'owned_json_all_finite_and_python_syntax_checked': True,
        'original_read_baseline_paths': len(read['files']), 'concurrent_read_baseline_changes': changes,
        'extra_root_precision_reads': extra_reads, 'new_owner_calculator_executed': False,
        'actual_work': 'Design and closed-schema reconstruction; seven synthetic old006 populator calls earlier; no source/native/model execution.',
        'no_new_runtime_observations': True, 'whole_goal_complete': False})
    entries = []
    for path in sorted(HERE.rglob('*')):
        if not path.is_file():
            continue
        relative = str(path.relative_to(HERE))
        if relative in ('MANIFEST_006.json', 'SHA256SUMS_006.txt'):
            continue
        raw = path.read_bytes()
        if path.suffix == '.json':
            json.dumps(json.loads(raw), allow_nan=False)
        if path.suffix == '.py':
            ast.parse(raw, filename=str(path))
        entries.append({'path': relative, 'sha256': digest(raw), 'bytes': len(raw)})
    emit('MANIFEST_006.json', {'generation': '065-design006', 'entries': entries,
        'excludes': ['MANIFEST_006.json', 'SHA256SUMS_006.txt'],
        'status': 'Design only; first pure owner tranche exact CLOSED declarations, broader source/native path still unfinished'})
    manifest = (HERE / 'MANIFEST_006.json').read_bytes()
    with (HERE / 'SHA256SUMS_006.txt').open('x') as stream:
        for item in entries:
            stream.write(item['sha256'] + '  ' + item['path'] + '\n')
        stream.write(digest(manifest) + '  MANIFEST_006.json\n')
    for item in entries:
        assert digest((HERE / item['path']).read_bytes()) == item['sha256']
    print(json.dumps({'payloads': len(entries), 'manifest_sha256': digest(manifest),
        'read_baseline_changes': changes, 'new_owner_arithmetic_executed': False}))


if __name__ == '__main__':
    main()
