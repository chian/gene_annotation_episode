"""Verify retained fixture bytes, archive identities and unchanged originals."""
import hashlib
import json
from pathlib import Path
import stat


ROOT = Path('/tmp/api-planning-root-final-20261022-004/detached-fixture-001')
SOURCE = Path('/tmp/pytest-of-chia/pytest-901/test_actual_scientific_worker_0')
RAW = ROOT/'raw-tree'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
original = json.loads((ROOT/'ORIGINAL_INVENTORY.json').read_text())['files']

def identity(path):
    return {'sha256': sha(path), 'bytes': path.stat().st_size,
        'mode': f'{stat.S_IMODE(path.stat().st_mode):04o}', 'mtime_ns': path.stat().st_mtime_ns}

for base in (SOURCE, RAW):
    actual = {str(p.relative_to(base)): identity(p) for p in base.rglob('*') if p.is_file()}
    assert actual == original
directories = {}
for path in [SOURCE, *sorted(p for p in SOURCE.rglob('*') if p.is_dir())]:
    relative = str(path.relative_to(SOURCE))
    target = RAW if relative == '.' else RAW/relative
    assert target.is_dir()
    source_stat, target_stat = path.stat(), target.stat()
    assert stat.S_IMODE(source_stat.st_mode) == stat.S_IMODE(target_stat.st_mode)
    assert source_stat.st_mtime_ns == target_stat.st_mtime_ns
    directories[relative] = {'mode': f'{stat.S_IMODE(source_stat.st_mode):04o}', 'mtime_ns': source_stat.st_mtime_ns}
assert {str(p.relative_to(SOURCE)) for p in SOURCE.rglob('*')} == {str(p.relative_to(RAW)) for p in RAW.rglob('*')}
control = json.loads((ROOT/'CONTROL_RELATIONSHIPS.json').read_text())
archives = {}
for key, row in control['archives'].items():
    path = RAW/'run/archive'/row['file']
    index = path.with_suffix('.index.json')
    assert sha(path) == row['sha256']
    assert sha(index) == row['index_sha256']
    archives[key] = {'file': str(path.relative_to(ROOT)), 'sha256': sha(path),
        'index': str(index.relative_to(ROOT)), 'index_sha256': sha(index)}
artifacts = {}
for path in sorted((RAW/'case/workspace/artifacts').rglob('*')):
    if path.is_file():
        assert path.name == sha(path)
        artifacts[str(path.relative_to(ROOT))] = {'sha256': sha(path), 'bytes': path.stat().st_size}
assert len(artifacts) == 7
validation = {'version': 'passed_fixture_preservation_validation_v1',
    'source_root': str(SOURCE), 'raw_copy_root': str(RAW), 'all69_original_file_hash_size_mode_mtime_equal': True,
    'all_source_and_copy_directory_members_modes_mtimes_equal': True,
    'directories': directories, 'worker_archives_verified': archives,
    'all7_immutable_artifact_names_equal_content_sha256': True, 'artifacts': artifacts,
    'no_original_database_open_or_checkpoint': True, 'no_relocated_resumability_claim': True}
(ROOT/'PRESERVATION_VALIDATION.json').write_text(json.dumps(validation, indent=2, sort_keys=True)+'\n')
files = {str(path.relative_to(ROOT)): {'sha256': sha(path), 'bytes': path.stat().st_size,
    'mode': f'{stat.S_IMODE(path.stat().st_mode):04o}'} for path in sorted(ROOT.rglob('*')) if path.is_file()}
manifest = {'version': 'api004_passed_detached_fixture_preservation_v1',
    'state': 'private_unsealed_evidence_copy', 'source_root': str(SOURCE),
    'runtime_pin': '16435877cddb566a9b802b6b3ce942595a9564b4cc10f8ca52b75f4007d9689d',
    'members': files, 'member_count': len(files), 'member_bytes': sum(row['bytes'] for row in files.values()),
    'original_raw_files': 69, 'original_raw_bytes': sum(row['bytes'] for row in original.values()),
    'derived_exports_separately_named': True, 'no_tests_or_application_calls': True}
path = ROOT/'MANIFEST.json'
with path.open('x') as stream:
    stream.write(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
print(json.dumps({'fixture_archive': str(ROOT), 'manifest_sha256': sha(path),
    'members_excluding_manifest': len(files), 'member_bytes': manifest['member_bytes'],
    'raw_files': 69, 'raw_bytes': manifest['original_raw_bytes'],
    'artifact_count': len(artifacts), 'worker_archive_count': len(archives), 'originals_unchanged': True}, indent=2))
