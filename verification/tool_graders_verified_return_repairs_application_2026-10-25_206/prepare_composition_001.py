"""Freeze only the exact authorized 197+203 source composition."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import resource
import sys

OWN = Path(__file__).resolve().parent
ROOT = OWN.parents[1]
OLD = ROOT / 'verification/tool_graders_typed_return_performance_2026-10-25_197'
REPAIR = ROOT / 'verification/tool_graders_genome_alignment_requirement_scope_2026-10-25_203'
CANDIDATE = OWN / 'composition_candidate'
resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    path = OWN / name
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')
    path.chmod(0o444)


baseline = json.loads((OLD / 'source_after.json').read_text())
production = json.loads((OWN / 'APPLICATION_AFTER_001.json').read_text())
plan = json.loads((OWN / 'APPLICATION_PLAN_001.json').read_text())
assert len(baseline) == 1053 and len(production) == 1046
expected = dict(baseline)
overrides = {row['path']: row for row in plan
    if row['path'] in {'gene_annotation_episode/bvbrc_genome_alignment_sheet.py',
                      'tests/test_genome_alignment_requirement_scope.py'}}
assert len(overrides) == 2
for name, row in overrides.items():
    expected[name] = row['candidate_sha256']
assert len(expected) == 1054 and set(production) <= set(expected)
assert {name: expected[name] for name in production} == production
assert {name: digest(ROOT / name) for name in production} == production
assert {name: digest(OLD / 'candidate' / name) for name in baseline} == baseline
assert not CANDIDATE.exists()
protected = {path.name: digest(path) for path in OWN.iterdir()
    if path.is_file() and (path.name.startswith('APPLICATION_') or path.name == 'APPLY_001.py')}
origins = {}
CANDIDATE.mkdir()
for name, sha in sorted(expected.items()):
    origin = Path(overrides[name]['candidate_file']) if name in overrides else OLD / 'candidate' / name
    assert digest(origin) == sha, name
    destination = CANDIDATE / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(origin.read_bytes())
    destination.chmod(0o444)
    origins[name] = {'source': str(origin), 'sha256': sha, 'bytes': destination.stat().st_size}
assert {name: digest(CANDIDATE / name) for name in expected} == expected
write('COMPOSITION_SOURCE_BEFORE_001.json', expected)
write('COMPOSITION_ORIGINS_001.json', origins)
write('COMPOSITION_PROTECTED_APPLICATION_001.json', protected)
write('COMPOSITION_PRODUCTION_BEFORE_001.json', production)
receipt = {'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
    'executable': sys.executable, 'cwd': str(Path.cwd()), 'exit_code': 0,
    'candidate': str(CANDIDATE), 'source_paths': len(expected),
    'common_production_paths': len(production), 'common_production_hashes_equal': True,
    'origin_manifest': 'COMPOSITION_ORIGINS_001.json',
    'input_manifests': {str(path): digest(path) for path in (
        OLD / 'source_after.json', OWN / 'APPLICATION_PLAN_001.json',
        OWN / 'APPLICATION_AFTER_001.json', REPAIR / 'REPAIR_AFTER_MANIFEST_001.json')},
    'only_overrides_of_197': sorted(overrides),
    'relocated_semantics_test': 'Retained byte-for-byte but not selected: frozen_original dependency is not relocated.',
    'source_file_modes': '0444; generated test evidence may be added outside the frozen manifest',
    'memory_limit_bytes': 20 * 1024**3, 'scratch_limit_bytes': 4 * 1024**3,
    'scratch_bytes': sum(p.stat().st_size for p in OWN.rglob('*') if p.is_file()),
    'wall_time_limit': None, 'network': 'none', 'production_mutation': False}
assert receipt['scratch_bytes'] < receipt['scratch_limit_bytes']
write('COMPOSITION_PREPARATION_RECEIPT_001.json', receipt)
print(json.dumps(receipt, sort_keys=True))
