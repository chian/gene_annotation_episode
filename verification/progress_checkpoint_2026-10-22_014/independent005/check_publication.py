"""Independent byte/metadata/XML verification. No application or SQLite imports."""
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import xml.etree.ElementTree as ET

OUT = Path(__file__).parent
ROOT = Path('/home/chia/repos/gene_annotation_episode')
CAP = ROOT / 'verification/model_context_presentation_2026-10-22_001'
FROZEN = Path('/tmp/gene-annotation-model-context-20261022-005')
PACK = Path('/tmp/model-context-publication-20261022-001')
PIN = '2c9dc895d0e7c6fa6f6d4df140cb9b88e1274894c8dc7213c46b4580dec68428'
EXPECTED_REPORT = 'edde00e4964c3198b215f718853af857919ddb45f85f042967932de88a803e6d'
EXPECTED_MANIFEST = '98e73e6972dfaa087295abc4756d3d30974a7cf14fa3e9cc38461dad519e963a'
EXPECTED_RESULTS = 'e06c80b7274ee7683cc398f8a4d98125e522a71bd58d872a1f5c56f99c75f499'
reads = {}
checks = []
findings = []

def digest(path):
    path = Path(path)
    assert not path.is_symlink(), str(path)
    s = path.stat()
    assert stat.S_ISREG(s.st_mode), str(path)
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    row = dict(bytes=s.st_size, sha256=h.hexdigest(), mode=f'{stat.S_IMODE(s.st_mode):04o}')
    reads[str(path)] = row
    return row

def load(path):
    digest(path)
    return json.loads(Path(path).read_text())

def checked(name, detail):
    checks.append(dict(check=name, status='passed', detail=detail))

def expected(path, row, *, mode=False):
    actual = digest(path)
    assert actual['sha256'] == row['sha256'], (str(path), actual, row)
    assert actual['bytes'] == row['bytes'], (str(path), actual, row)
    if mode:
        assert actual['mode'] == row['mode'], (str(path), actual, row)
    return actual

def file_roster(root):
    result = {}
    for path in root.rglob('*'):
        assert not path.is_symlink(), str(path)
        if path.is_file():
            result[path.relative_to(root).as_posix()] = path
    return result

manifest = load(CAP / 'MANIFEST.json')
assert reads[str(CAP / 'MANIFEST.json')]['sha256'] == EXPECTED_MANIFEST
assert manifest['runtime_pin'] == PIN
members = manifest['members']
assert len(members) == 834
assert len({r['path'] for r in members}) == len(members)
for row in members:
    rel = PurePosixPath(row['path'])
    assert not rel.is_absolute() and '..' not in rel.parts and rel.as_posix() == row['path']
    expected(CAP / row['path'], row, mode=True)
roster = file_roster(CAP)
assert set(roster) == {r['path'] for r in members} | {'MANIFEST.json'}
assert sum(r['bytes'] for r in members) == 18660384
directories = [CAP] + [p for p in CAP.rglob('*') if p.is_dir()]
assert len(directories) == 92
assert all(stat.S_IMODE(p.stat().st_mode) == 0o555 for p in directories)
assert stat.S_IMODE((CAP / 'MANIFEST.json').stat().st_mode) == 0o444
checked('capsule_membership_hashes_sizes_modes', dict(members=834, member_bytes=18660384,
    actual_files_including_manifest=835, directories=92, directory_mode='0555'))

report_rel = 'docs/MODEL_CONTEXT_PRESENTATION_VERIFICATION_2026-10-22_001.md'
for path in [ROOT / report_rel, CAP / report_rel]:
    assert digest(path)['sha256'] == EXPECTED_REPORT
    assert stat.S_IMODE(path.stat().st_mode) == 0o444
assert (ROOT / report_rel).read_bytes() == (CAP / report_rel).read_bytes()
assert manifest['report_sha256'] == EXPECTED_REPORT
receipt = load(PACK / 'PUBLICATION_RECEIPT002.json')
assert receipt['manifest_sha256'] == EXPECTED_MANIFEST
assert receipt['report_sha256'] == EXPECTED_REPORT
assert receipt['members'] == 834 and receipt['member_bytes'] == 18660384
assert receipt['directory_count'] == 92 and receipt['preserved_fixture_raw_files'] == 69
checked('external_report_exact_copy_and_publication_receipt', EXPECTED_REPORT)

identity = load(CAP / 'SOURCE_IDENTITIES.json')
runtime = sorted(p.relative_to(CAP).as_posix() for package in ['gene_annotation_episode', 'method_loop']
                 for p in (CAP / package).rglob('*.py'))
tests = sorted(p.relative_to(CAP).as_posix() for p in (CAP / 'tests').rglob('*.py'))
assert len(runtime) == 134 and len(tests) == 214
assert set(identity['files']) == set(runtime) | set(tests)
pin = hashlib.sha256()
for rel in runtime:
    row = expected(CAP / rel, identity['files'][rel])
    pin.update(rel.encode() + b'\0' + bytes.fromhex(row['sha256']))
assert pin.hexdigest() == PIN == identity['runtime_pin']
frozen_runtime = {p.relative_to(FROZEN).as_posix() for package in ['gene_annotation_episode', 'method_loop']
                  for p in (FROZEN / package).rglob('*.py')}
frozen_tests = {p.relative_to(FROZEN).as_posix() for p in (FROZEN / 'tests').rglob('*.py')}
assert frozen_runtime == set(runtime) and frozen_tests == set(tests)
for rel, row in identity['files'].items():
    expected(FROZEN / rel, row)
baseline = load(CAP / 'lineage/GENERATION_BASELINE_005.json')
assert len(baseline['files']) == 344 and len(baseline['static_assets']) == 319
added = set(identity['files']) - set(baseline['files'])
changed = {rel for rel, row in baseline['files'].items()
           if identity['files'][rel]['sha256'] != row['sha256']}
assert added == {'gene_annotation_episode/model_context_presentation.py',
    'tests/test_model_context_presentation.py', 'tests/test_model_context_runtime.py',
    'tests/test_model_context_reconstruction.py'}
assert changed == {'gene_annotation_episode/runtime.py'}
old_tests = {rel for rel in baseline['files'] if rel.startswith('tests/')}
assert len(old_tests) == 211
for rel in old_tests:
    expected(CAP / rel, baseline['files'][rel])
for rel, row in baseline['static_assets'].items():
    expected(CAP / rel, row)
    expected(FROZEN / rel, row)
instruction = load(CAP / 'lineage/INSTRUCTION_INPUTS_005.json')
assert len(instruction['files']) == 8
for rel, row in instruction['files'].items():
    expected(CAP / rel, row)
    expected(FROZEN / rel, row)
checked('runtime_test_baseline_asset_instruction_identity', dict(runtime=134, tests=214,
    old_tests_unchanged=211, static_assets_unchanged=319, instruction_snapshots=8,
    runtime_pin=PIN, source_changes=sorted(changed), additions=sorted(added)))

copies = load(CAP / 'COPIED_INPUTS.json')
assert copies['copied_count'] == len(copies['files']) == 829
generated = {r['path'] for r in members} - set(copies['files'])
assert generated == {'COPIED_INPUTS.json', 'SOURCE_IDENTITIES.json', 'VERIFICATION_COUNTS.json',
    'evidence/detached-fixture/PRESERVATION.json', report_rel}
allowed_roots = [FROZEN, Path('/tmp/model-context-p-005-evidence-NnuEqz7S'),
    Path('/tmp/model-context-r-005-evidence'), Path('/tmp/model-context-root-005-evidence'),
    ROOT / 'verification/model_context_presentation_plan_2026-10-22_001', PACK,
    Path('/tmp/model-context-detached-stable-20261022-002/test_opt_in_actual_worker_keep0')]
allowed_files = {ROOT / 'verification/hmmer_api_resource_2026-10-22_004/MANIFEST.json',
                 ROOT / 'docs/AMENDMENTS/SLOT_CORRECTION_2026-10-22_013.md'}
for rel, row in copies['files'].items():
    source = Path(row['source'])
    assert source in allowed_files or any(source.is_relative_to(root) for root in allowed_roots), str(source)
    expected(CAP / rel, row)
    actual = expected(source, row)
    assert actual['mode'] == row['original_mode'], (str(source), actual, row)
    assert digest(CAP / rel)['mode'] == row['publish_mode']
assert copies['parent004_full_capsule_copied'] is False
parent = Path(copies['parent004_preserved_external']) / 'MANIFEST.json'
parent_sha = digest(parent)['sha256']
assert parent_sha == manifest['parent004_manifest_sha256'] == '695ca3eafd7a6a6e283584e5e73389c48bbe46fb16bc6633dbad9b02150ff5da'
assert digest(CAP / 'lineage/parent004-MANIFEST.json')['sha256'] == parent_sha
plan = CAP / 'lineage/adopted-plan'
plan_manifest = load(plan / 'MANIFEST002.json')
assert digest(plan / 'MANIFEST002.json')['sha256'] == '1dcd83c271cc435f9b1c123f80fb9157a225b0e73a16965308fa7aec7018af47'
assert len(plan_manifest['members']) == 21
assert set(file_roster(plan)) == set(plan_manifest['members']) | {'MANIFEST002.json'}
for rel, row in plan_manifest['members'].items():
    expected(plan / rel, row)
checked('829_copy_original_controls_parent_and_plan', dict(exact_copied_original_files=829,
    copied_parent_manifest_only=True, original_plan_files_including_manifest=22))

aggregate = load(CAP / 'evidence/root/RESULTS002.json')
assert digest(CAP / 'evidence/root/RESULTS002.json')['sha256'] == EXPECTED_RESULTS
assert manifest['root_results_sha256'] == EXPECTED_RESULTS
assert aggregate['runtime_pin'] == PIN
assert aggregate['earlier_passing_connected001_excluded_as_same_node_rerun'] is True
selected_paths = {
    'P': ('evidence/p-helper/component001.xml', 'evidence/p-helper/component001.log'),
    'R': ('evidence/r-runtime/runtime-final.xml', 'evidence/r-runtime/runtime-final.log'),
    'root_detached': ('evidence/root/connected002.xml', 'evidence/root/connected002.log'),
    'root_compatibility': ('evidence/root/compatibility001.xml', 'evidence/root/compatibility001.log')}
nodes = []
groups = []
for group in aggregate['groups']:
    xml_rel, log_rel = selected_paths[group['group']]
    assert digest(CAP / xml_rel)['sha256'] == group['xml_sha256']
    assert digest(CAP / log_rel)['sha256'] == group['log_sha256']
    tree = ET.parse(CAP / xml_rel).getroot()
    cases = tree.findall('.//testcase')
    assert len(cases) == group['passed']
    assert all(case.find('failure') is None and case.find('error') is None
               and case.find('skipped') is None for case in cases)
    ids = [case.attrib['classname'] + '::' + case.attrib['name'] for case in cases]
    assert ids == group['node_ids']
    assert group['exit_code'] == 0
    nodes.extend(ids)
    groups.append(dict(group=group['group'], xml=xml_rel, log=log_rel, count=len(cases)))
counts = Counter(nodes)
duplicates = {node: count for node, count in counts.items() if count > 1}
assert len(nodes) == 117 and len(counts) == 116
assert duplicates == {aggregate['repeated_node']: 2}
assert len({node.split('::')[0] for node in counts}) == 7
assert [g['count'] for g in groups] == [67, 21, 1, 28]
assert aggregate['executed_final_group_testcases'] == 117 and aggregate['distinct_cases'] == 116
verification_counts = load(CAP / 'VERIFICATION_COUNTS.json')
assert verification_counts['final_group_executed_testcases'] == 117
assert verification_counts['distinct_cases'] == 116 and verification_counts['distinct_files'] == 7
checked('selected_xml_count_and_deduplicated_ledger', dict(groups=groups,
    executed=117, distinct=116, files=7, duplicated=duplicates, earlier_connected001_excluded=True))

for input_rel, allow_historical_test in [
    ('evidence/p-helper/INVOCATION001_INPUTS.json', True),
    ('evidence/r-runtime/runtime-final-input.json', False)]:
    invocation = load(CAP / input_rel)
    differences = []
    for rel, row in invocation['files'].items():
        sha = row['sha256'] if isinstance(row, dict) else row
        if identity['files'][rel]['sha256'] != sha:
            differences.append(rel)
    assert differences == (['tests/test_model_context_runtime.py'] if allow_historical_test else []), differences
assert digest(CAP / 'evidence/root/FINAL_INPUTS001.json')['sha256'] == digest(CAP / 'SOURCE_IDENTITIES.json')['sha256']
checked('per_invocation_source_identity_and_historical_test_snapshot',
    'All134 runtime bytes match. Only P unselected R test snapshot differs, explicitly historical; R/root final348 match.')

original = load(CAP / 'evidence/detached-fixture/ORIGINAL_PRESERVATION.json')
preservation = load(CAP / 'evidence/detached-fixture/PRESERVATION.json')
assert digest(CAP / 'evidence/detached-fixture/ORIGINAL_PRESERVATION.json')['sha256'] == '776645e4bc082d9ad804325f8f429e77a3bbab1abb442393dfae83586e30cf21'
assert original['files'] == preservation['files']
assert len(original['files']) == 69
assert sum(row['bytes'] for row in original['files'].values()) == 3406670
assert original['this_fixture_from_separate_repeat'] is True
assert original['first_passing_pytest906_fixture_preserved'] is False
assert original['copied_databases_claimed_resumable'] is False
assert original['test_xml_sha256'] == digest(CAP / 'evidence/root/connected002.xml')['sha256']
assert original['test_log_sha256'] == digest(CAP / 'evidence/root/connected002.log')['sha256']
raw = CAP / 'evidence/detached-fixture/raw-tree'
source = Path(original['source'])
assert source == Path('/tmp/model-context-detached-stable-20261022-002/test_opt_in_actual_worker_keep0')
assert set(file_roster(raw)) == set(file_roster(source)) == set(original['files'])
for rel, row in original['files'].items():
    for path in [source / rel, raw / rel]:
        expected(path, row)
        assert path.stat().st_mtime_ns == row['mtime_ns'], str(path)
    assert digest(source / rel)['mode'] == row['mode']
assert not any('pytest-906' in str(row['source']) for rel, row in copies['files'].items()
               if rel.startswith('evidence/detached-fixture/raw-tree/'))
checked('retained_closed_synthetic_fixture_and_original_controls', dict(files=69, bytes=3406670,
    source=str(source), byte_size_mtime_original_mode_membership_equal=True,
    published_modes_according_to_manifest=True, no_database_open=True, first906_not_claimed=True))

historical_result_sha = digest(CAP / 'evidence/root/RESULTS.json')['sha256']
report_text = (CAP / report_rel).read_text()
assert 'Root RESULTS.json SHA256' + EXPECTED_RESULTS in report_text
assert historical_result_sha != EXPECTED_RESULTS
findings.append(dict(code='published_report_final_result_filename_label_mismatch',
    description='Report names RESULTS.json with the hash of actual final RESULTS002.json. Manifest and selected final group counts are correct.',
    report_sha256=EXPECTED_REPORT, historical_RESULTS_json_sha256=historical_result_sha,
    final_RESULTS002_json_sha256=EXPECTED_RESULTS,
    root_disposition='Root confirmed; additive correction planned, original publication unchanged.'))

result = dict(status='verified_with_one_confirmed_report_label_finding',
    capsule=str(CAP), runtime_pin=PIN, manifest_sha256=EXPECTED_MANIFEST,
    report_sha256=EXPECTED_REPORT, checks=checks, findings=findings,
    application_imports=0, sqlite_database_opens=0, scientific_workspace_reopens=0,
    model_http_native_calls=0, source_test_config_state_publication_writes=0,
    claim_limit='Byte/metadata/XML verification only; original scientific payload not interpreted or reopened. No tests or custody functions executed.')
(OUT / 'RESULTS001.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
(OUT / 'READSET001.json').write_text(json.dumps(dict(status='readonly_file_hash_and_metadata_readset',
    files=reads), sort_keys=True, indent=2) + '\n')
(OUT / 'SELECTED_NODE_LEDGER001.json').write_text(json.dumps(dict(nodes=nodes, unique_nodes=sorted(counts),
    duplicates=duplicates), sort_keys=True, indent=2) + '\n')
print(json.dumps(dict(status=result['status'], checks=len(checks), findings=len(findings),
    capsule_members=834, member_bytes=18660384, directories=92, runtime_files=134,
    test_files=214, executed_selected_tests=117, distinct_selected_tests=116,
    fixture_files=69, fixture_bytes=3406670, hashed_file_paths=len(reads)), sort_keys=True))
