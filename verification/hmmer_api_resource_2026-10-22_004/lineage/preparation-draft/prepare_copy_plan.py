"""Read-only input verification and draft metadata; no application imports."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import stat


REPO = Path('/home/chia/repos/gene_annotation_episode')
CHECKOUT = Path('/tmp/gene-annotation-hmmer-api-20261022-004')
OUT = Path('/tmp/api-planning-publication-preparation-20261022-001')
PARENT = REPO/'verification/hmmer_api_resource_2026-10-22_003'
ADOPTED = REPO/'verification/hmmer_api_scientific_prechoice_plan_2026-10-22_001'
ROOT_INPUTS = Path('/tmp/api-planning-root-final-20261022-004/INPUTS.json')
CANDIDATE = REPO/'verification/hmmer_api_resource_2026-10-22_004'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(name, value):
    path = OUT/name
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True)+'\n')


def identities(root):
    return {str(p.relative_to(root)): {'sha256': sha(p), 'bytes': p.stat().st_size,
            'mode': f'{stat.S_IMODE(p.stat().st_mode):04o}'}
        for p in sorted(root.rglob('*')) if p.is_file()}


def verify_members(root, expected_count, manifest_sha):
    manifest = root/'MANIFEST.json'
    assert sha(manifest) == manifest_sha
    content = json.loads(manifest.read_text())
    rows = content['members']
    if isinstance(rows, dict):
        rows = [{'path': key, **item} for key, item in rows.items()]
    assert len(rows) == expected_count
    declared = {row['path']: row for row in rows}
    assert len(declared) == expected_count
    actual = identities(root)
    assert set(actual) == set(declared) | {'MANIFEST.json'}
    for name, row in declared.items():
        assert actual[name]['sha256'] == row['sha256'], name
        assert actual[name]['bytes'] == row['bytes'], name
        if 'mode' in row:
            assert actual[name]['mode'] == row['mode'], name
    return content, actual


parent_manifest, parent = verify_members(PARENT, 1444,
    '32dc15a3533d99d36cae42125549b17da6832066c0ec11af51a3afbeadaf59f1')
adopted_manifest, adopted = verify_members(ADOPTED, 8,
    '97b9088a00a482051240bd3884fd5060d57827315fa7cbb6bb8b003d9409e8c3')
assert sha(ROOT_INPUTS) == '3ec66f29419f90b09461e5e541b852f9a8e8588101dd42935848b9858883d690'
inputs = json.loads(ROOT_INPUTS.read_text())
baseline_path = CHECKOUT/'GENERATION_BASELINE_004.json'
assert sha(baseline_path) == '17fc1c541d8180c89340050ca596475b1112923bedf37de4cc4418a4c915caa7'
baseline = json.loads(baseline_path.read_text())
source_ids = json.loads((PARENT/'SOURCE_IDENTITIES.json').read_text())
assert len(source_ids['files']) == 131 and len(source_ids['tests']) == 205
assert set(baseline['files']) == set(source_ids['files']) | set(source_ids['tests'])
for group in ('files', 'tests'):
    for name, digest in source_ids[group].items():
        assert baseline['files'][name]['sha256'] == digest, name

current = {}
for prefix in ('gene_annotation_episode', 'method_loop', 'tests'):
    for path in (CHECKOUT/prefix).rglob('*.py'):
        if '__pycache__' not in path.parts:
            current[str(path.relative_to(CHECKOUT))] = {'sha256': sha(path), 'bytes': path.stat().st_size}
assert current == inputs['files'], 'source/test membership or bytes changed from root final inputs'
runtime = {key: value for key, value in current.items() if not key.startswith('tests/')}
tests = {key: value for key, value in current.items() if key.startswith('tests/')}
assert len(runtime) == 133 and len(tests) == 211
pin = hashlib.sha256()
for name, row in sorted(runtime.items()):
    pin.update(name.encode()+b'\0'+bytes.fromhex(row['sha256']))
assert pin.hexdigest() == inputs['runtime_pin'] == '16435877cddb566a9b802b6b3ce942595a9564b4cc10f8ca52b75f4007d9689d'

assets = json.loads((PARENT/'STATIC_INPUTS.json').read_text())
assert len(assets['files']) == assets['asset_count'] == 319
asset_rows = {}
for name, row in assets['files'].items():
    assert name in parent
    assert parent[name]['sha256'] == row['source']['sha256'] == row['candidate']['sha256']
    assert parent[name]['bytes'] == row['source']['bytes'] == row['candidate']['bytes']
    assert name not in current
    asset_rows[name] = parent[name]
assert sum(name.endswith('.py') for name in asset_rows) == 2

checklist = REPO/'docs/AMENDMENTS/SLOT_CORRECTION_2026-10-22_012.md'
assert sha(checklist) == 'c2360b9b98c0ac29b5936481f04972992ed262a32ded825243152f76a7530a7e'
entries = []
for number, line in enumerate(checklist.read_text().splitlines(), 1):
    match = re.match(r'- \[([ x])\] \*\*(.+?)\*\*', line)
    if match:
        entries.append({'label': match.group(2).rstrip(':'), 'checked': match.group(1) == 'x',
            'source_line': number, 'reference': str(checklist)+':'+str(number), 'original_line': line})
assert len(entries) == 41
old_entries = json.loads((PARENT/'CHECKLIST_REFERENCES.json').read_text())['entries']
assert [r['label'] for r in entries] == [r['label'] for r in old_entries]
dump('CHECKLIST_REFERENCES.DRAFT.json', {'version': 'api004_fixed41_checklist_references_draft_v1',
    'reference_only': True, 'source': str(checklist), 'source_sha256': sha(checklist),
    'entries': entries, 'meaning': 'Exact reference-only links; no checkbox/state/description rewritten.'})

plan = []
def add(path, target, category, identity=None):
    path = Path(path)
    identity = identity or {'sha256': sha(path), 'bytes': path.stat().st_size,
        'mode': f'{stat.S_IMODE(path.stat().st_mode):04o}'}
    plan.append({'source': str(path), 'destination_relative_path': target, 'category': category,
        'source_identity': identity, 'planned_published_mode': '0555' if identity.get('mode') == '0555' else '0444',
        'copy_state': 'planned_only_not_materialized'})

for name, row in sorted(runtime.items()):
    add(CHECKOUT/name, name, 'runtime_python', row)
for name, row in sorted(tests.items()):
    add(CHECKOUT/name, name, 'test_python', row)
for name, row in sorted(asset_rows.items()):
    add(PARENT/name, name, 'unchanged_reproducibility_asset_from_parent003', row)
for name, row in sorted(parent.items()):
    add(PARENT/name, 'parent-generation003/'+name, 'complete_parent003_lineage', row)
for name, row in sorted(adopted.items()):
    add(ADOPTED/name, 'lineage/adopted-scientific-prechoice-plan/'+name, 'exact_adopted_scope027_plan', row)

docs = ['AGENTS.md', 'GOAL.md', 'docs/EPISODE_STRUCTURE.md', 'docs/TIME_AWARE_ESTIMATION.md',
    'docs/AMENDMENTS/SLOT_CORRECTION_2026-10-22_012.md',
    *['docs/HMMER_API_RESOURCE_SCOPE_2026-10-22_'+code+'.md' for code in ('027', '028', '029')],
    'docs/HMMER_API_RESOURCE_VERIFICATION_2026-10-22_003.md']
for name in docs:
    add(REPO/name, 'docs/authority/'+name, 'current_authority_or_parent_report')
add(baseline_path, 'lineage/GENERATION_BASELINE_004.json', 'exact_generation004_baseline')
add(ROOT_INPUTS, 'evidence/root-final/INPUTS.json', 'root_pre_dispatch_final_inputs')

for directory, prefix in (
    (Path('/tmp/hmmer-api-p-004-evidence'), 'evidence/p-preparation-and-dispatch'),
    (Path('/tmp/gene-annotation-hmmer-api-planning-binding-evidence-20261022-004'), 'evidence/b-planning-binding'),
    (Path('/tmp/hmmer-api-r-004-evidence'), 'evidence/r-runtime'),
    (Path('/tmp/hmmer-api-root-connected-20261022-004'), 'evidence/root-development')):
    for path in sorted(directory.rglob('*')):
        if path.is_file():
            relative = str(path.relative_to(directory))
            add(path, prefix+'/'+relative, 'component_or_development_evidence_historical_status_retained')

destinations = [row['destination_relative_path'] for row in plan]
assert len(destinations) == len(set(destinations))
baseline_runtime = {key: row for key, row in baseline['files'].items() if not key.startswith('tests/')}
baseline_tests = {key: row for key, row in baseline['files'].items() if key.startswith('tests/')}
def changes(now, old):
    return {'new': sorted(set(now)-set(old)), 'removed': sorted(set(old)-set(now)),
        'changed_existing': {key: {'parent003': old[key]['sha256'], 'candidate004': now[key]['sha256']}
            for key in sorted(now.keys() & old.keys()) if now[key]['sha256'] != old[key]['sha256']},
        'unchanged_count': sum(now[key]['sha256'] == old[key]['sha256'] for key in now.keys() & old.keys())}

dump('COPY_PLAN.DRAFT.json', {'version': 'api004_publication_copy_plan_draft_v1', 'draft': True,
    'candidate_capsule_path': str(CANDIDATE),
    'candidate_report_path': str(REPO/'docs/HMMER_API_RESOURCE_VERIFICATION_2026-10-22_004.md'),
    'runtime_pin': pin.hexdigest(), 'runtime_count': len(runtime), 'test_count': len(tests),
    'categories': dict(Counter(row['category'] for row in plan)), 'entries': plan,
    'not_materialized': True,
    'pending': ['Root confirmation of actual corrected detached worker completion before source/test snapshot materialization.',
        'Completed final root log/XML/results and complete disjoint-count ledger.',
        'Root-supplied fixture backup/archive paths and explicit copy scope; no fixture DB opened by preparation.',
        'Final evidence directory membership/hash recheck after owners finish writing.',
        'Root independent review and exact final report bytes before publication/read-only modes.']})
dump('SOURCE_IDENTITIES.DRAFT.json', {'version': 'api004_source_identity_copy_plan_v1',
    'state': 'planned_not_materialized', 'runtime_pin': pin.hexdigest(),
    'root_inputs_sha256': sha(ROOT_INPUTS), 'runtime': runtime, 'tests': tests,
    'runtime_changes_from_parent003': changes(runtime, baseline_runtime),
    'test_changes_from_parent003': changes(tests, baseline_tests)})
dump('PARENT_AND_ASSET_VERIFICATION.json', {'version': 'api004_parent_verification_v1',
    'parent_manifest': str(PARENT/'MANIFEST.json'), 'parent_manifest_sha256': sha(PARENT/'MANIFEST.json'),
    'parent_declared_members': 1444, 'parent_files_including_outer_manifest': len(parent),
    'parent_declared_bytes': sum(row['bytes'] for name, row in parent.items() if name != 'MANIFEST.json'),
    'parent_declared_hash_size_file_mode_and_no_extras_verified': True,
    'directory_modes': 'Not included in manifest contract; directories not asserted sealed.',
    'parent_runtime_pin': source_ids['implementation_sha256'],
    'generation004_baseline_exact_parent131runtime205tests': True,
    'assets': {'declared_count': 319, 'non_python': 317, 'archival_python_outside_runtime_pin': 2,
        'membership_source': 'actual parent003 STATIC_INPUTS.json files mapping',
        'all_declared_hashes_and_sizes_match_parent003': True, 'paths': asset_rows},
    'plan_capsule': {'declared_members': 8, 'including_outer_manifest': len(adopted),
        'manifest_sha256': sha(ADOPTED/'MANIFEST.json')},
    'no_source_test_asset_or_lineage_copy_materialized': True})
dump('PREPARATION_CHECKS.DRAFT.json', {'version': 'api004_publication_preparation_checks_v1',
    'parent_verified': True, 'runtime_pin': pin.hexdigest(), 'runtime_count': len(runtime), 'test_count': len(tests),
    'runtime_changes': changes(runtime, baseline_runtime), 'test_changes': changes(tests, baseline_tests),
    'copy_plan_entries': len(plan), 'checklist_reference_count': len(entries),
    'final_test_counts': None, 'final_publication': False,
    'packaging_only_probe_failures': [
        'Read-only discovery used nonexistent guessed hmmer_api_resource_verification_...003 path and P EVIDENCE.json; corrected to actual paths/schema.',
        'Read-only parent manifest summary initially assumed members dictionary; actual list was read and handled without changing original.'],
    'application_or_test_calls': 0})
print(json.dumps({'runtime_pin': pin.hexdigest(), 'runtime': len(runtime), 'tests': len(tests),
    'parent_members_plus_manifest': len(parent), 'assets': len(asset_rows), 'plan_members_plus_manifest': len(adopted),
    'copy_plan_entries': len(plan), 'runtime_changes': changes(runtime, baseline_runtime),
    'test_changes': changes(tests, baseline_tests)}, indent=2))
