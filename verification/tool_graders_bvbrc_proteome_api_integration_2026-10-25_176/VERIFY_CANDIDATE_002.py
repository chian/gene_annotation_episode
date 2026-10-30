"""Read-only original guard, candidate delta and concrete import receipt."""
from pathlib import Path
import datetime
import difflib
import hashlib
import importlib
import json
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent.parent
CANDIDATE = OUT / 'candidate'
sys.path.insert(0, str(CANDIDATE))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

final_source = json.loads((OUT / 'TEST_014_AFTER.json').read_text())
assert final_source['returncode'] == 0 and final_source['source_changes_during_run'] == []
assert all((CANDIDATE / path).is_file() and sha(CANDIDATE / path) == row['sha256']
    for path, row in final_source['files'].items())
root179 = json.loads((OUT / 'ROOT_179_APPLICATION_REFERENCE_001.json').read_text())
assert all(sha(ROOT / row['path']) == row['after_sha256'] for row in root179['receipt']['files'])
before = json.loads((OUT / 'BEFORE_MANIFEST_001.json').read_text())
dependency = json.loads((OUT / 'DEPENDENCY_175_IMPORT_001.json').read_text())
expected = {path: row['sha256'] for path, row in before['files'].items()}
for row in dependency['files']:
    expected[row['path']] = row['candidate_sha256']
dependency178 = json.loads((OUT / 'DEPENDENCY_178_IMPORT_001.json').read_text())
for row in dependency178['files']:
    expected[row['path']] = row['after_sha256']
changed = [{'path': path, 'expected': pin, 'actual': sha(ROOT / path) if (ROOT / path).is_file() else None}
    for path, pin in expected.items() if not (ROOT / path).is_file() or sha(ROOT / path) != pin]
assert not changed, changed
symlinks = [str(p.relative_to(CANDIDATE)) for p in CANDIDATE.rglob('*') if p.is_symlink()]
assert not symlinks, symlinks
allowed = {
    'gene_annotation_episode/' + name for name in (
        'api_service_execution.py', 'bvbrc_appservice_adapters.py', 'bvbrc_appservice_bundle_values.py',
        'bvbrc_appservice_host.py', 'bvbrc_appservice_publication.py', 'bvbrc_appservice_schemas.json',
        'bvbrc_proteome_bundle_contracts.py', 'bvbrc_proteome_bundle_projection.py',
        'bvbrc_proteome_bundle_resolution.py', 'bvbrc_proteome_bundle_schemas.json',
        'bvbrc_proteome_returns.py', 'bvbrc_proteome_tool_info.py',
        'execution_episodes.py')}
allowed.update('tests/' + name for name in (
    'bvbrc_proteome_host_fixture.py', 'test_bvbrc_appservice_contracts.py',
    'test_bvbrc_proteome_catalog_integration.py', 'test_bvbrc_proteome_document_selection.py',
    'test_bvbrc_proteome_host_integration.py', 'test_bvbrc_proteome_return_frames.py',
    'test_execution_episodes_family.py'))
rows, patches = [], []
for directory in ('gene_annotation_episode', 'tests'):
    for path in sorted((CANDIDATE / directory).rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path.suffix == '.pyc':
            continue
        relative = path.relative_to(CANDIDATE).as_posix()
        original = ROOT / relative
        if original.exists() and original.read_bytes() == path.read_bytes():
            continue
        assert relative in allowed, relative
        row = {'path': relative, 'kind': 'existing' if original.exists() else 'new',
            'before_sha256': sha(original) if original.exists() else None,
            'candidate_sha256': sha(path), 'bytes': path.stat().st_size}
        rows.append(row)
        patches.extend(difflib.unified_diff(original.read_text().splitlines(keepends=True) if original.exists() else [],
            path.read_text().splitlines(keepends=True), fromfile='a/' + relative if original.exists() else '/dev/null',
            tofile='b/' + relative))
assert {r['path'] for r in rows} == allowed
(OUT / 'DELTA_002.patch').write_text(''.join(patches))
fixtures = []
for p in sorted((CANDIDATE / 'verification').rglob('*')):
    if p.is_file():
        relative = p.relative_to(CANDIDATE).as_posix()
        assert sha(p) == sha(ROOT / relative), relative
        fixtures.append({'path': relative, 'sha256': sha(p), 'bytes': p.stat().st_size})
for name in ('bvbrc_proteome_bundle_adapter', 'bvbrc_proteome_returns', 'bvbrc_proteome_tool_info',
             'api_service_execution', 'execution_episodes', 'communication', 'form_reference_validation'):
    importlib.import_module('gene_annotation_episode.' + name)
from gene_annotation_episode.bvbrc_proteome_bundle_adapter import implementation_sha256
modules = {name: {'path': str(Path(module.__file__).resolve()), 'sha256': sha(Path(module.__file__))}
    for name, module in sorted(sys.modules.items())
    if name.startswith('gene_annotation_episode') and getattr(module, '__file__', None)}
assert all(Path(row['path']).is_relative_to(CANDIDATE) for row in modules.values())
write('MODULE_PATHS_002.json', {'python': sys.executable, 'sys_path_prefix': sys.path[:3], 'modules': modules,
    'provider_implementation_sha256': implementation_sha256()})
write('DELTA_MANIFEST_002.json', {'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'root': str(ROOT), 'candidate': str(CANDIDATE), 'production_applied_by_worker176': False,
    'root179_application_receipt_sha256': root179['receipt_sha256'],
    'root179_imported_into_candidate': False,
    'additional_fixture_scope': 'TEST_FIXTURE_SCOPE_001.md',
    'dependency175_patch_sha256': dependency['patch_sha256'],
    'dependency178_manifest_sha256': dependency178['source_manifest_sha256'], 'files': rows,
    'patch_sha256': sha(OUT / 'DELTA_002.patch'), 'candidate_symlinks': symlinks,
    'guarded_original_files': len(expected), 'unexpected_original_changes': changed,
    'original_guard_basis': 'Initial baseline plus root-authorized accepted175 DELTA_002 and178 DELTA_HASHES_007 applications',
    'unchanged_fixture_files': fixtures, 'provider_implementation_sha256': implementation_sha256()})
print(json.dumps({'changed_files': len(rows), 'guarded_original_files': len(expected),
    'unexpected_original_changes': changed, 'unchanged_fixture_files': len(fixtures),
    'imported_candidate_modules': len(modules), 'provider_implementation_sha256': implementation_sha256(),
    'patch_sha256': sha(OUT / 'DELTA_002.patch')}))
