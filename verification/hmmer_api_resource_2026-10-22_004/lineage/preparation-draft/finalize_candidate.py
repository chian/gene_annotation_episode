"""Prepare the complete review candidate and contract; never publish it."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import stat


OUT = Path('/tmp/api-planning-publication-preparation-20261022-001')
STAGE = OUT/'candidate'
REPO = Path('/home/chia/repos/gene_annotation_episode')
ROOT = Path('/tmp/api-planning-root-final-20261022-004')
CHECKOUT = Path('/tmp/gene-annotation-hmmer-api-20261022-004')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
plan = deepcopy(json.loads((OUT/'COPY_PLAN_003.DRAFT.json').read_text()))
entries = plan['entries']
by_target = {row['destination_relative_path']: row for row in entries}


def add(source, destination, category='completed_final_evidence'):
    source = Path(source)
    row = {'source': str(source), 'destination_relative_path': destination,
        'category': category, 'source_identity': {'sha256': sha(source), 'bytes': source.stat().st_size,
            'mode': f'{stat.S_IMODE(source.stat().st_mode):04o}'},
        'planned_published_mode': '0444', 'copy_state': 'copied_unsealed_review_candidate'}
    if destination in by_target:
        assert by_target[destination]['source_identity']['sha256'] == row['source_identity']['sha256'], destination
        return
    entries.append(row)
    by_target[destination] = row


# Preserve the empty administrative capture made before its own command wrote
# stdout. The complete output gets a different name; neither record is relabeled.
partial = by_target['lineage/preparation-draft/additional-stage-003.stdout.log']
partial_source = STAGE/partial['destination_relative_path']
assert partial_source.stat().st_size == 0 and sha(partial_source) == partial['source_identity']['sha256']
partial['historical_original_source'] = partial['source']
partial['source'] = str(partial_source)
partial['category'] = 'explicit_partial_administrative_stdout_capture'
partial['provenance_note'] = 'Empty copy captured before staging command completed. Later full stdout preserved under distinct completed name.'
add(OUT/'additional-stage-003.stdout.log', 'lineage/preparation-draft/completed-additional-stage-003.stdout.log',
    'completed_administrative_stdout_distinct_from_partial')

for path in sorted(ROOT.iterdir()):
    if path.is_file():
        add(path, 'evidence/root-final/'+path.name)
for path in sorted(Path('/tmp/hmmer-api-r-004-history030-evidence').iterdir()):
    if path.is_file():
        add(path, 'evidence/supplemental-history030/'+path.name, 'unchanged_supplemental_node_excluded316')
for code in ('030', '031'):
    name = 'docs/HMMER_API_RESOURCE_SCOPE_2026-10-22_'+code+'.md'
    add(REPO/name, 'docs/authority/'+name, 'original_hypothesis_and_additive_correction')
for path in sorted(OUT.iterdir()):
    if path.is_file():
        if path.name == 'additional-stage-003.stdout.log':
            continue
        add(path, 'lineage/preparation-draft/'+path.name, 'preparation_draft_and_commands_status_retained')

results_path = ROOT/'RESULTS.json'
assert sha(results_path) == 'dba4b6ea4cc6863564145571b82e6ed60bb2f967424a711207e43cb06344dead'
results = json.loads(results_path.read_text())
assert results['distinct_current_pin_cases'] == 316 and results['disjoint_current_pin_test_files'] == 19
assert all(group['exit_code'] == 0 for group in results['groups'])
inputs = json.loads((ROOT/'INPUTS.json').read_text())
assert len(inputs['files']) == 344
assert json.loads((OUT/'FINAL_ROOT_XML_AND_SOURCE_CHECK.json').read_text())['distinct_cases'] == 316
supplemental = json.loads(Path('/tmp/hmmer-api-r-004-history030-evidence/RESULTS.json').read_text())
assert supplemental['test_source_edited'] is supplemental['production_source_edited'] is False
assert supplemental['result'] == '1 passed in 46.62s'

for row in entries:
    source = Path(row['source'])
    assert sha(source) == row['source_identity']['sha256'], str(source)
    assert source.stat().st_size == row['source_identity']['bytes']
    target = STAGE/row['destination_relative_path']
    if target.exists():
        assert sha(target) == row['source_identity']['sha256'], str(target)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        target.chmod(0o755 if row['planned_published_mode'] == '0555' else 0o644)

metadata = OUT/'FINAL_METADATA'
metadata.mkdir()
def meta(name, value):
    path = metadata/name
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True)+'\n')
    add(path, name, 'generated_final_review_metadata')
    target = STAGE/name
    assert not target.exists()
    shutil.copy2(path, target)
    target.chmod(0o644)

source_draft = json.loads((OUT/'SOURCE_IDENTITIES.DRAFT.json').read_text())
for name, row in inputs['files'].items():
    assert sha(CHECKOUT/name) == row['sha256'] and sha(STAGE/name) == row['sha256']
runtime = {name: row['sha256'] for name, row in inputs['files'].items() if not name.startswith('tests/')}
tests = {name: row['sha256'] for name, row in inputs['files'].items() if name.startswith('tests/')}
assert len(runtime) == 133 and len(tests) == 211
meta('SOURCE_IDENTITIES.json', {'version': 'api004_final_review_source_identities_v1',
    'implementation_sha256': inputs['runtime_pin'], 'files': runtime, 'tests': tests,
    'runtime_source_count': 133, 'test_python_count': 211,
    'changed_or_new_runtime_sources_from_generation003': source_draft['runtime_changes_from_parent003'],
    'test_changes_from_generation003': source_draft['test_changes_from_parent003'],
    'all344_source_and_test_bytes_and_membership_unchanged_from_root_final_inputs': True,
    'supplemental031_confirms_all205_parent_tests_unchanged': True,
    'source_input_sha256': sha(ROOT/'INPUTS.json'), 'root_results_sha256': sha(results_path)})
parent = REPO/'verification/hmmer_api_resource_2026-10-22_003'
assets = json.loads((parent/'STATIC_INPUTS.json').read_text())
meta('STATIC_INPUTS.json', {'version': 'api004_unchanged_static_inputs_v1', 'asset_count': 319,
    'non_python_count': 317, 'archival_python_outside_runtime_pin': 2,
    'membership_source': str(parent/'STATIC_INPUTS.json'),
    'files': {name: {'source': str(parent/name), 'sha256': sha(parent/name),
        'bytes': (parent/name).stat().st_size} for name in assets['files']},
    'all319_asset_bytes_unchanged': True, 'installed_dependencies_and_lock_not_bundled': True})
checklist = json.loads((OUT/'CHECKLIST_REFERENCES.DRAFT.json').read_text())
meta('CHECKLIST_REFERENCES.json', {**checklist, 'version': 'api004_fixed41_reference_only_v1'})
meta('VERIFICATION_COUNTS.json', {'version': 'api004_disjoint_final_counts_v1',
    'distinct_current_pin_cases': 316, 'disjoint_test_files': 19,
    'groups': [{key: group[key] for key in ('group', 'passed', 'duration_seconds', 'command', 'exit_code', 'xml_sha256', 'log_sha256')}
        for group in results['groups']], 'producer_invocations_are_not_added': True,
    'supplemental_history_node': {'passed': 1, 'seconds': 46.62, 'included_in316': False,
        'result_sha256': sha(Path('/tmp/hmmer-api-r-004-history030-evidence/RESULTS.json'))}})
meta('PROVENANCE_MAP.json', {'version': 'api004_final_review_provenance_v1',
    'runtime_pin': inputs['runtime_pin'], 'parent003_manifest_sha256': sha(parent/'MANIFEST.json'),
    'all1445_parent003_files_retained': True, 'scope027_plan_members_plus_manifest': 9,
    'adopted_plan_manifest_sha256': '97b9088a00a482051240bd3884fd5060d57827315fa7cbb6bb8b003d9409e8c3',
    'scopes': {code: {'path': 'docs/authority/docs/HMMER_API_RESOURCE_SCOPE_2026-10-22_'+code+'.md',
        'sha256': sha(REPO/('docs/HMMER_API_RESOURCE_SCOPE_2026-10-22_'+code+'.md'))}
        for code in ('027', '028', '029', '030', '031')},
    'root_final_inputs_sha256': sha(ROOT/'INPUTS.json'), 'root_final_results_sha256': sha(results_path),
    'root_final_node_ledger_sha256': sha(ROOT/'FINAL_NODE_LEDGER.json'),
    'passed_fixture': {'original_source': '/tmp/pytest-of-chia/pytest-901/test_actual_scientific_worker_0',
        'archive_source': str(ROOT/'detached-fixture-001'),
        'manifest_sha256': '573301a479bad692ffc2a25719c141ef48994808995452d6b01e0208ba9b3ab7',
        'raw_files': 69, 'raw_bytes': 3129016, 'preserved_members_plus_manifest': 83,
        'raw_records_not_claimed_relocated_resumable': True},
    'original_drafts_and_first_failures_preserved': True,
    'administrative_partial_stdout': 'Explicit empty before-completion capture and distinct completed stdout retained, without relabeling.',
    'no_application_tests_or_transport_invoked_by_packaging': True,
    'excluded': 'No active scientific DB, private provider events, actual API003 private-service files or context-repair planning inputs copied.',
    'publication_review_contract_and_full_member_inventory': 'Outside capsule to avoid hash cycle; root will preserve them in additive checkpoint013.'})

report_path = OUT/'REPORT_003.CANDIDATE.md'
report_relative = 'docs/HMMER_API_RESOURCE_VERIFICATION_2026-10-22_004.md'
add(report_path, report_relative, 'exact_review_report_copy')
target = STAGE/report_relative
assert not target.exists()
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(report_path, target)
target.chmod(0o644)
meta('COPIED_INPUT_IDENTITIES.json', {'version': 'api004_copied_input_identities_v1',
    'record_phase': 'prepared_before_root_final_publication_review', 'input_entries': deepcopy(entries),
    'coverage_limit': 'This generated record excludes its own bytes and later COPY_PLAN.json to avoid self-reference. Approved outside inventory and outer manifest cover complete final membership.'})

final_plan = {**plan, 'version': 'api004_final_review_copy_plan_v4', 'entries': entries,
    'categories': dict(Counter(row['category'] for row in entries)), 'root_final_total': 316,
    'root_results_sha256': sha(results_path), 'current_report': str(report_path),
    'scope030_hypothesis_disproved_031': True, 'all205_old_tests_unchanged': True,
    'pending_root_final_files': [], 'pending': ['Root review/authorization of final report, inventory and contract before permanent publication.'],
    'coverage_limit': 'Copy plan excludes its own generated copy and future outer MANIFEST; full outside inventory and outer manifest cover complete membership.'}
plan_path = OUT/'COPY_PLAN_004.FINAL.json'
with plan_path.open('x') as stream:
    stream.write(json.dumps(final_plan, indent=2, sort_keys=True)+'\n')
shutil.copy2(plan_path, STAGE/'COPY_PLAN.json')
publish_modes = {row['destination_relative_path']: row['planned_published_mode'] for row in entries}
members = {str(path.relative_to(STAGE)): {'sha256': sha(path), 'bytes': path.stat().st_size,
    'publish_mode': publish_modes.get(str(path.relative_to(STAGE)), '0444')}
    for path in sorted(STAGE.rglob('*')) if path.is_file()}
assert set(members) == {row['destination_relative_path'] for row in entries} | {'COPY_PLAN.json'}
inventory_path = OUT/'APPROVED_MEMBER_INVENTORY.json'
with inventory_path.open('x') as stream:
    stream.write(json.dumps({'version': 'api004_root_review_candidate_inventory_v1',
        'candidate': str(STAGE), 'runtime_pin': inputs['runtime_pin'], 'members': members}, indent=2, sort_keys=True)+'\n')
contract = {'version': 'root_reviewed_api004_publication_contract_v1', 'candidate': str(STAGE),
    'capsule_destination': str(REPO/'verification/hmmer_api_resource_2026-10-22_004'),
    'report_destination': str(REPO/'docs/HMMER_API_RESOURCE_VERIFICATION_2026-10-22_004.md'),
    'candidate_report_relative_path': report_relative, 'expected_report_sha256': sha(report_path),
    'member_inventory_path': str(inventory_path), 'member_inventory_sha256': sha(inventory_path),
    'runtime_pin': inputs['runtime_pin'], 'source_inputs_path': str(ROOT/'INPUTS.json'),
    'source_inputs_sha256': sha(ROOT/'INPUTS.json'), 'root_results_path': str(results_path),
    'root_results_sha256': sha(results_path), 'capsule_directory_mode': '0555'}
contract_path = OUT/'ROOT_REVIEWED_PUBLICATION_CONTRACT.json'
with contract_path.open('x') as stream:
    stream.write(json.dumps(contract, indent=2, sort_keys=True)+'\n')
receipt = {'version': 'api004_final_materialization_review_ready_v1', 'candidate_files': len(members),
    'candidate_bytes': sum(row['bytes'] for row in members.values()), 'runtime_pin': inputs['runtime_pin'],
    'root_distinct_cases': 316, 'supplemental_node_excluded': True,
    'report_sha256': sha(report_path), 'inventory_sha256': sha(inventory_path),
    'reviewed_contract_sha256': sha(contract_path), 'copy_plan_sha256': sha(plan_path),
    'publisher_sha256': sha(OUT/'publish_reviewed_api004.py'),
    'permanent_paths_created': False, 'snapshot_frozen': False,
    'publication_command_prepared_not_executed': '/home/chia/repos/gene_annotation_episode/.venv/bin/python '+str(OUT/'publish_reviewed_api004.py')+' --reviewed-contract '+str(contract_path)+' --publish'}
receipt_path = OUT/'FINAL_MATERIALIZATION_READY.json'
with receipt_path.open('x') as stream:
    stream.write(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
print(json.dumps(receipt, indent=2))
