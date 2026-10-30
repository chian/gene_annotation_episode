"""Stage completed evidence only; leave running root outputs explicitly pending."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import stat
import xml.etree.ElementTree as ET


OUT = Path('/tmp/api-planning-publication-preparation-20261022-001')
STAGE = OUT/'candidate'
REPO = Path('/home/chia/repos/gene_annotation_episode')
ROOT = Path('/tmp/api-planning-root-final-20261022-004')
CHECKOUT = Path('/tmp/gene-annotation-hmmer-api-20261022-004')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
initial = json.loads((OUT/'COPY_PLAN_002.DRAFT.json').read_text())
entries = [row for row in initial['entries'] if row['category'] not in {
    'component_or_development_evidence_historical_status_retained',
    'confirmed_root_final_input_or_detached_result'}]


def add(path, destination, category):
    path = Path(path)
    entries.append({'source': str(path), 'destination_relative_path': destination,
        'category': category, 'source_identity': {'sha256': sha(path), 'bytes': path.stat().st_size,
            'mode': f'{stat.S_IMODE(path.stat().st_mode):04o}'},
        'planned_published_mode': '0444', 'copy_state': 'planned_only_not_materialized'})


for directory, prefix in (
    (Path('/tmp/hmmer-api-p-004-evidence'), 'evidence/p-preparation-and-dispatch'),
    (Path('/tmp/gene-annotation-hmmer-api-planning-binding-evidence-20261022-004'), 'evidence/b-planning-binding'),
    (Path('/tmp/hmmer-api-r-004-evidence'), 'evidence/r-runtime'),
    (Path('/tmp/hmmer-api-root-connected-20261022-004'), 'evidence/root-development')):
    for path in sorted(directory.rglob('*')):
        if path.is_file():
            add(path, prefix+'/'+str(path.relative_to(directory)),
                'component_or_development_evidence_historical_status_retained')

completed_root = []
for name in ('CONSUMERS_INPUTS.json', 'detached.log', 'detached.xml', 'legacy.log', 'legacy.xml'):
    path = ROOT/name
    assert path.is_file()
    if name.endswith('.xml'):
        document = ET.parse(path)
        assert not list(document.iter('failure')) and not list(document.iter('error'))
    add(path, 'evidence/root-final/'+name, 'completed_root_input_or_output_exit_ledger_pending')
    completed_root.append(name)

fixture = ROOT/'detached-fixture-001'
manifest = json.loads((fixture/'MANIFEST.json').read_text())
fixture_files = {str(p.relative_to(fixture)): p for p in fixture.rglob('*') if p.is_file()}
assert set(fixture_files) == set(manifest['members']) | {'MANIFEST.json'}
for name, row in manifest['members'].items():
    assert sha(fixture_files[name]) == row['sha256']
    assert fixture_files[name].stat().st_size == row['bytes']
for name, path in sorted(fixture_files.items()):
    add(path, 'evidence/root-final/passed-detached-fixture/'+name, 'full_passed_fixture_exact_raw_and_named_derivatives')

independent = REPO/'verification/progress_checkpoint_2026-10-22_012/independent-api003'
declared = json.loads((independent/'MANIFEST.json').read_text())['members']
for row in declared:
    assert sha(independent/row['path']) == row['sha256']
    assert (independent/row['path']).stat().st_size == row['bytes']
assert {str(p.relative_to(independent)) for p in independent.rglob('*') if p.is_file()} == {
    row['path'] for row in declared} | {'MANIFEST.json'}
for path in sorted(independent.iterdir()):
    if path.is_file():
        add(path, 'lineage/independent-api003/'+path.name, 'independent_published003_verification_reference')

for path in sorted(OUT.iterdir()):
    if path.is_file():
        add(path, 'lineage/preparation-draft/'+path.name, 'preparation_draft_and_commands_status_retained')

assert len(entries) == len({row['destination_relative_path'] for row in entries})
newly_copied, existing = [], []
for row in entries:
    source = Path(row['source'])
    assert sha(source) == row['source_identity']['sha256']
    assert source.stat().st_size == row['source_identity']['bytes']
    target = STAGE/row['destination_relative_path']
    if target.exists():
        assert sha(target) == row['source_identity']['sha256'], str(target)
        assert target.stat().st_size == row['source_identity']['bytes']
        existing.append(row['destination_relative_path'])
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        target.chmod(0o755 if row['planned_published_mode'] == '0555' else 0o644)
        assert sha(target) == row['source_identity']['sha256']
        newly_copied.append(row['destination_relative_path'])

expected = json.loads((ROOT/'INPUTS.json').read_text())
source_rows = {}
for prefix in ('gene_annotation_episode', 'method_loop', 'tests'):
    for path in (CHECKOUT/prefix).rglob('*.py'):
        if '__pycache__' not in path.parts:
            source_rows[str(path.relative_to(CHECKOUT))] = {'sha256': sha(path), 'bytes': path.stat().st_size}
assert source_rows == expected['files'] and len(source_rows) == 344
for name, row in source_rows.items():
    assert sha(STAGE/name) == row['sha256']

value = {**initial, 'version': 'api004_additional_materialization_plan_draft_v3',
    'entries': entries, 'categories': dict(Counter(row['category'] for row in entries)),
    'current_report_draft': str(OUT/'REPORT_002.DRAFT.md'),
    'fixture_archive': {'path': str(fixture), 'manifest_sha256': sha(fixture/'MANIFEST.json'),
        'raw_files': 69, 'raw_bytes': 3129016, 'member_files_plus_manifest': len(fixture_files)},
    'not_materialized': False, 'state': 'private_unsealed_stage_no_permanent_publication',
    'completed_root_outputs_included': completed_root,
    'root_final_total': None,
    'pending_root_final_files': ['consumers.log', 'consumers.xml', 'RESULTS.json'],
    'pending': ['Root completed consumer command exit, XML and disjoint final-node/source guard/count ledger.',
        'Root final RESULTS.json plus any additional final metadata names, copied only after completion.',
        'Final report factual totals and parent independent publication review; no permanent repo publication yet.']}
plan_path = OUT/'COPY_PLAN_003.DRAFT.json'
with plan_path.open('x') as stream:
    stream.write(json.dumps(value, indent=2, sort_keys=True)+'\n')
record = {'version': 'api004_additional_stage_record_v1', 'source_runtime_pin': expected['runtime_pin'],
    'all344_source_test_members_and_bytes_unchanged': True,
    'current_plan': str(plan_path), 'current_plan_sha256': sha(plan_path),
    'newly_copied_count': len(newly_copied), 'existing_exact_count': len(existing),
    'total_stage_files': len(entries), 'new_paths': newly_copied,
    'final_totals': None, 'no_permanent_publication_or_freezing': True,
    'no_application_or_test_or_transport_call': True}
path = OUT/'STAGED_ADDITIONAL_INPUTS.json'
with path.open('x') as stream:
    stream.write(json.dumps(record, indent=2, sort_keys=True)+'\n')
print(json.dumps({key: record[key] for key in ('current_plan', 'current_plan_sha256',
    'newly_copied_count', 'existing_exact_count', 'total_stage_files', 'final_totals')}, indent=2))
