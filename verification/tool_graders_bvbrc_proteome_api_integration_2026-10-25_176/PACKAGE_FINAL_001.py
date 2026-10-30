"""Index existing stable receipts and package the candidate; execute no tests."""
from collections import Counter
from pathlib import Path
import datetime
import hashlib
import json
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent.parent
CANDIDATE = OUT / 'candidate'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((OUT / name).read_text())


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def artifact(path):
    return {'path': path.relative_to(OUT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}


def test_receipt(stem):
    xml_path = OUT / (stem + '.xml')
    cases = []
    for case in ET.parse(xml_path).getroot().iter('testcase'):
        status = next((name for name in ('failure', 'error', 'skipped')
            if case.find(name) is not None), 'passed')
        cases.append({'identity': case.attrib['classname'] + '::' + case.attrib['name'],
            'status': status, 'seconds': float(case.attrib.get('time', '0'))})
    assert len({case['identity'] for case in cases}) == len(cases)
    return {'xml': artifact(xml_path), 'log': artifact(OUT / (stem + '.log')),
        'counts': dict(Counter(case['status'] for case in cases)), 'cases': cases}


before013, after013 = read('TEST_013_BEFORE.json'), read('TEST_013_AFTER.json')
before014, after014 = read('TEST_014_BEFORE.json'), read('TEST_014_AFTER.json')
for before, after in ((before013, after013), (before014, after014)):
    assert before['files'] == after['files']
    assert after['source_changes_during_run'] == []
    assert before['runner_sha256'] == after['runner_before_sha256'] == after['runner_after_sha256']
assert after013['returncodes'] == {'core': 1, 'host': 0}
assert after014['returncode'] == 0
changed = [path for path in sorted(set(after013['files']) | set(before014['files']))
    if after013['files'].get(path) != before014['files'].get(path)]
assert changed == ['tests/test_execution_episodes_family.py']
assert all(sha(CANDIDATE / path) == row['sha256'] for path, row in after014['files'].items())

receipts = {stem: test_receipt(stem) for stem in
    ('TEST_012_core', 'TEST_012_host', 'TEST_013_core', 'TEST_013_host', 'TEST_014')}
assert receipts['TEST_013_core']['counts'] == {'passed': 454, 'failure': 1}
assert receipts['TEST_013_host']['counts'] == {'passed': 11}
assert receipts['TEST_014']['counts'] == {'passed': 10}
latest = {}
for stem in ('TEST_013_core', 'TEST_013_host', 'TEST_014'):
    for case in receipts[stem]['cases']:
        latest[case['identity']] = {'receipt': stem, **case}
assert len(latest) == 466 and all(case['status'] == 'passed' for case in latest.values())
failed013 = [case for case in receipts['TEST_013_core']['cases'] if case['status'] != 'passed']
assert all(latest[case['identity']]['receipt'] == 'TEST_014' for case in failed013)
fixture_path = changed[0]
fixture = {'path': fixture_path, 'before_sha256': after013['files'][fixture_path]['sha256'],
    'candidate_sha256': after014['files'][fixture_path]['sha256'],
    'reason': 'Reviewed fixture follows actual runtime BindingContext caller; no claim that historical None support was documented as removed.',
    'scope': 'TEST_FIXTURE_SCOPE_001.md', 'runtime_behavior_changed': False}
index = {'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'receipts': receipts,
    'stable_runs': {
        name: {'before': artifact(OUT / (name + '_BEFORE.json')),
            'after': artifact(OUT / (name + '_AFTER.json')), 'captured_files': len(after['files']),
            'source_changes_during_run': after['source_changes_during_run'],
            'runner_sha256': after['runner_after_sha256'],
            'elapsed_seconds': after['elapsed_seconds'],
            'child_maximum_resident_set_kib': after['child_maximum_resident_set_kib'],
            'test_scratch_bytes': after['test_scratch_bytes']}
        for name, after in (('TEST_013', after013), ('TEST_014', after014))},
    'descriptor_fixture_correction': fixture,
    'distinct_case_identities': len(latest), 'latest_results': list(latest.values()),
    'interpretation': '466 distinct cases have passing stable-source receipts across013 and014. This is not one all-green run:013 retains its descriptor fixture failure;014 reruns the complete10-case affected group after only the authorized test edit.',
    'intermediate_receipts': 'TEST_INDEX_INTERMEDIATE_001.json',
    'moving_closure_disclosure': 'INTERMEDIATE_RECEIPTS_001.json',
    'test012_status': 'Unchanged candidate closure; external runner failed to create parent scratch directory.226 passed and240 setup errors. Preserved diagnostic only.'}
write('TEST_INDEX_FINAL_001.json', index)

baseline = read('BEFORE_MANIFEST_001.json')
expected = {path: {'sha256': row['sha256'], 'basis': 'initial_baseline'}
    for path, row in baseline['files'].items()}
dep175, dep178 = read('DEPENDENCY_175_IMPORT_001.json'), read('DEPENDENCY_178_IMPORT_001.json')
for row in dep175['files']:
    expected[row['path']] = {'sha256': row['candidate_sha256'], 'basis': 'root_applied175_DELTA_002'}
for row in dep178['files']:
    expected[row['path']] = {'sha256': row['after_sha256'], 'basis': 'root_applied178_DELTA_HASHES_007'}
guard = []
for path, row in sorted(expected.items()):
    actual = sha(ROOT / path)
    assert actual == row['sha256'], path
    guard.append({'path': path, 'basis': row['basis'], 'expected_sha256': row['sha256'], 'actual_sha256': actual})
root179 = read('ROOT_179_APPLICATION_REFERENCE_001.json')
assert sha(ROOT / root179['receipt_path']) == root179['receipt_sha256']
root179_rows = []
for row in root179['receipt']['files']:
    actual = sha(ROOT / row['path'])
    assert actual == row['after_sha256'], row['path']
    root179_rows.append({'path': row['path'], 'expected_sha256': row['after_sha256'], 'actual_sha256': actual})
delta = read('DELTA_MANIFEST_002.json')
old_delta = read('DELTA_MANIFEST_001.json')
assert len(delta['files']) == 20
assert len([row for row in delta['files'] if row['path'].startswith('gene_annotation_episode/')]) == 13
old_rows = {row['path']: row for row in old_delta['files']}
new_rows = {row['path']: row for row in delta['files']}
assert set(new_rows) - set(old_rows) == {fixture_path}
assert all(new_rows[path] == row for path, row in old_rows.items())
assert sha(OUT / 'DELTA_002.patch') == delta['patch_sha256']
for row in delta['files']:
    assert sha(CANDIDATE / row['path']) == row['candidate_sha256']
    assert (sha(ROOT / row['path']) if (ROOT / row['path']).exists() else None) == row['before_sha256']
write('ORIGINAL_GUARD_001.json', {'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'production_written_by_worker176': False, 'guarded_original_files': len(guard), 'files': guard,
    'unexpected_original_changes': [], 'root179_application_checked_separately': root179_rows,
    'root179_imported_into_candidate': False, 'unchanged_historical_fixture_files': delta['unchanged_fixture_files'],
    'final_delta_source_files_unchanged_from_frozen013': True, 'additional_final_test_fixture': fixture})

example = OUT / 'numerical_example_final_002'
recalculation = read('RECALCULATION_001.log')
assert sha(example / 'SHEET.json') == recalculation['original_sheet_sha256']
original_components = json.loads((example / 'COMPONENTS.json').read_text())
revised_components = json.loads((example / 'RECALCULATED_COMPONENTS.json').read_text())
assert original_components['value']['sheet_sha256'] == revised_components['value']['sheet_sha256'] == recalculation['numerical_sheet_sha256']
assert original_components['value']['tracks'][0]['selection_counts']['pass']['value'] == 1
assert revised_components['value']['tracks'][0]['selection_counts']['pass']['value'] == 0
write('NUMERICAL_ARTIFACTS_001.json', {'files': [artifact(path) for path in sorted(example.iterdir()) if path.is_file()],
    'recalculation_script': artifact(OUT / 'RECALCULATE_EXAMPLE_001.py'),
    'recalculation_receipt': artifact(OUT / 'RECALCULATION_001.log'), 'numerical_values': {
        'mean_first_hsp_identity_fraction': 0.4375, 'mean_subject_endpoint_difference_fraction': 0.625,
        'measured_zero': 0.0, 'original_selected_count': 1, 'recalculated_selected_count': 0,
        'executed_reference_input_count': None, 'executed_comparison_input_count': None}})

source_hash_table = '\n'.join('| ' + row['path'] + ' | ' + (row['before_sha256'] or 'new') + ' | ' + row['candidate_sha256'] + ' |' for row in delta['files'])
handoff = f'''# GenomeComparison candidate integration, final review handoff

The candidate implements the exact017 host integration and019 pre-acquisition selection contracts plus the reviewed descriptor-test fixture correction. It is ready for root review and application. Worker176 has made no production changes and makes no full-tool completion claim. The fixed308-row/288-binding accounting remains root-owned.

Final delta: [DELTA_002.patch](DELTA_002.patch), SHA256 `{delta['patch_sha256']}`. The20-file [manifest](DELTA_MANIFEST_002.json), SHA256 `{sha(OUT / 'DELTA_MANIFEST_002.json')}`, contains13 implementation/schema/tool-information files and7 tests/fixtures. All19 earlier files, including all13 implementation files, are byte-identical to the provisional frozen013 delta. The sole addition is the authorized descriptor fixture in `tests/test_execution_episodes_family.py`.

## Implemented path and contracts

The actual configured provider registry accepts the concrete implementation digest and exposes proteome contracts only for configured resources. Multiple resource IDs remain available to the selecting episode. The scientific tool library presents the parent with name, description and resources; selected children receive substantive instructions and invocation contracts. APIServiceExecution owns BVBRCProteomeReturns. AppService own facts and ExecutionEpisodes route all eight declared fact families through public resolvers, independent semantic validation, admission and received facts. Colliding fact sources are rejected. Empty requested forms still receive no facts.

The actual selected prepare, submit, task-status/task-info, Workspace metadata, capability, manifest-download and native-download path creates retained request/response records, acquisition, bundle, sheet, components and publication. A narrow available requested projection can satisfy the practical endpoint while unrelated missing inputs remain explicit. Required artifact completeness is retained. The latest owned publication governs practical completion even if it is partial or has no scientific references; unrelated operations do not supersede a publication. Already admitted historical facts are unchanged.

The new closed NativeDocumentSelection variant names the parent's existing requirement_id before acquisition. New artifact members retain actual selected requirement_ids; the member, receipt and selected operands must agree. Historical members remain valid without the field and establish no requirement membership. Exactly one actual member must match. Missing or ambiguous selections, wrong role/format/task, duplicate actual sources, wrong hashes, incomplete transfers and nonzero ranges retain explicit failure/missing states. No future receipt IDs or native links are invented.

Saved input_resolution remains the sole selection-to-content mapping. Parsed native sources, original format/contract, primary source, bundle digest/task and actual requirement membership are checked against the authenticated bundle at the return boundary. The validator makes no network request and invokes no native parser or calculator. The return binder uses the exact synchronous frame keys from017, keeps each possession check and independent semantic validation, and stores no persistent cross-call cache.

## Dependencies and untouched originals

Accepted175 DELTA_002 is recorded by [DEPENDENCY_175_IMPORT_001.json](DEPENDENCY_175_IMPORT_001.json), with patch SHA256 `{dep175['patch_sha256']}`. Accepted178's exact seven files were imported after the prior tests ended; [DEPENDENCY_178_IMPORT_001.json](DEPENDENCY_178_IMPORT_001.json) records source-manifest SHA256 `{dep178['source_manifest_sha256']}`. These dependencies, including the identical communication wrapper and form-reference helper, are excluded from worker176's delta.

Root179's ten-file application is separately pinned by [ROOT_179_APPLICATION_REFERENCE_001.json](ROOT_179_APPLICATION_REFERENCE_001.json). It was not imported into the frozen candidate, and this verification does not claim combined179/176 behavior. Candidate tests import candidate package modules and candidate metadata; only the original virtual-environment interpreter/site-packages are shared. [MODULE_PATHS_002.json](MODULE_PATHS_002.json) records57 imported project modules, all inside the candidate. Provider implementation pin: `{delta['provider_implementation_sha256']}`.

[ORIGINAL_GUARD_001.json](ORIGINAL_GUARD_001.json) records every expected and actual hash for854 original files against the initial baseline plus root's accepted175/178 applications, with zero unexpected changes. It also separately checks all10 root179 final hashes. All17 copied historical verification fixtures retain their production bytes. Candidate paths are real files with no symlinks. [STRUCTURE_GUARD_001.json](STRUCTURE_GUARD_001.json) records only the optional ArtifactMember field and the disjoint NativeDocumentSelection union as additional schema changes after175. No original process, stored history, parser/calculator mathematics, evidence axis, credit, prompt/template, method_loop or scheduler was changed.

## Stable verification

| Receipt | Result | Frozen candidate paths | Wall duration |
| --- | --- | --- | --- |
| TEST_013 core,19 complete groups |454 passed;1 descriptor-fixture failure preserved |877 unchanged for entire combined run |954.65s pytest core |
| TEST_013 complete host group |11 passed |same877 unchanged |2018.45s pytest host |
| TEST_014 complete execution_episodes_family group |10 passed |877 unchanged |22.85s pytest |

[TEST_INDEX_FINAL_001.json](TEST_INDEX_FINAL_001.json) preserves every case identity and the hashes of the original XML/log/before/after receipts. Across013 and014,466 distinct case identities have passing stable-source receipts; this is not presented as one all-green run. Only the authorized test fixture changed between those runs. All implementation bytes stayed fixed. Both before/after closures and both runner hashes match.

The013 failure was the descriptor test passing None into initial_decision_context. The existing runtime caller passes a real BindingContext, and the existing MinHash branch reads context.role. Root reviewed the complete caller boundary before authorizing the fixture to use the existing real launch-context helper, retaining every assertion. This is a test-contract decision based on traced runtime usage, not evidence of a documented historical removal of None support. No production initial-context behavior changed. The preserved failing source is [TEST_013_execution_family_source.py](TEST_013_execution_family_source.py), SHA256 `{fixture['before_sha256']}`. The final candidate test SHA256 is `{fixture['candidate_sha256']}`.

The combined013 runner took{after013['elapsed_seconds']:.3f}s, with recorded maximum child RSS{after013['child_maximum_resident_set_kib']}KiB and{after013['test_scratch_bytes']}bytes of test scratch.014 took{after014['elapsed_seconds']:.3f}s, maximum child RSS{after014['child_maximum_resident_set_kib']}KiB and{after014['test_scratch_bytes']}bytes of test scratch. No invented wall-time limit or local database BLAST was used. These RSS values are per-child maxima, not a simultaneous sum.

Actual launch commands, from candidate cwd, were:

```sh
PYTHONDONTWRITEBYTECODE=1 /home/chia/repos/gene_annotation_episode/.venv/bin/python ../RUN_FINAL_002.py > ../FINAL_RUN_002.log 2>&1
PYTHONDONTWRITEBYTECODE=1 /home/chia/repos/gene_annotation_episode/.venv/bin/python ../RUN_FINAL_003.py > ../FINAL_RUN_003.log 2>&1
PYTHONDONTWRITEBYTECODE=1 /home/chia/repos/gene_annotation_episode/.venv/bin/python ../VERIFY_CANDIDATE_002.py > ../CANDIDATE_GUARD_003.log 2>&1
```

TEST_013_BEFORE.json and TEST_014_BEFORE.json record the full pytest argument lists, cwd and explicit candidate PYTHONPATH. RUN_FINAL_002.py and RUN_FINAL_003.py retain the exact executed harnesses. Their runner hashes are `{after013['runner_after_sha256']}` and `{after014['runner_after_sha256']}`. The final package script reads existing receipts and runs no tests.

## Failure preservation and concrete fixture corrections

TEST_001 through011 remain intermediate diagnostics. [INTERMEDIATE_RECEIPTS_001.json](INTERMEDIATE_RECEIPTS_001.json) lists source closures edited during active intermediate tests and missing contemporaneous pins; no missing before-run evidence was reconstructed. TEST_012 froze its candidate correctly but its external harness failed to create the parent scratch directory:226 passes and240 setup errors remain preserved.013 used identical candidate bytes with only that external harness corrected.

The positive host fixture was corrected to select the actual task-info receipt. Its source-reference expectation now includes the publication, native document and supplied reference inventory required by the actual returned form; custody fields were retained. The outer root's empty request still produces an empty fact map. The positive second forwarding boundary uses a legitimately commissioned receiving scientific episode requesting all eight families.

For later partial/empty publication cases, the fixture interrupts after the actual acquisition and publication inputs are saved, before science publication, then resumes those saved inputs through the real implementation. It freezes that later operation before publishing the earlier success, so recovery cannot legitimately absorb the earlier artifact. Incomplete native bytes produce the empty scientific case; an HTTP error is not relabeled a scientific publication. The tests verify the newer publication does not revive prior completion and the older admitted facts do not change. Replay invokes neither transport nor scientific calculation and adds no action/observation. This controlled operation ordering is a host test, not a Workflow scheduling proof.

## Filled numerical example and limits

[NUMERICAL_EXAMPLE_001.md](NUMERICAL_EXAMPLE_001.md) and [NUMERICAL_ARTIFACTS_001.json](NUMERICAL_ARTIFACTS_001.json) describe and hash the retained native bytes, submission wrapper, supplied metadata, assignment, actual publication, sheet/components and typed returns. The synthetic two-row projection has identity fractions0.875 and0.000, yielding mean0.4375, and endpoint-difference fractions0.750 and0.500, yielding mean0.625. Zero remains measured zero. The native fractions retain their legacy first-HSP/endpoint meaning and are not full alignment coverage or annotation probabilities.

With identity threshold0.6 and endpoint threshold0.7, one association passes. Recalculation from the unchanged saved sheet with identity threshold0.9 selects zero, with no acquisition or native reconstruction; [RECALCULATION_001.log](RECALCULATION_001.log) retains the actual calculator path and hashes. Executed-input denominators and unavailable native joins remain explicitly missing; supplied population snapshots are not relabeled executed inputs.

The positive host tests use real A/B1/B2/B3/B4 constructors, real AppService publication/read, Store/Journal, binders and typed contracts with synthetic transport/data. JSON and TSV are exercised independently. Thirteen requested rows across all eight families pass results → scientific child → commissioned scientific parent custody. Top-level rows name the publication; nested fields also require native-document and reference-inventory custody. Negative cases cover unavailable custody, wrong task/source/owner/run/scope, siblings, altered values, unrequested fields, malformed saved associations and saved-artifact tampering. Isolated binder/frame unit fixtures also exist and are not claimed as native host proofs.

| Verification level | Status |
| --- | --- |
| Registered library/resource selection and invocation contracts |Verified by focused candidate tests |
| Controlled native host, actual scientific pipeline and typed custody |Verified by11 complete host cases |
| Stable saved-sheet numerical recalculation |Verified separately, selection1→0 |
| Complete scripted or model-driven Workflow for this provider |Not executed by worker176 |
| Configured-provider model presentation / user-reviewed prompts |Not established; no template coding authorized |
| Live BV-BRC job, authentication or deployed resources |Not attempted |
| Combined179 directional integration |Not included in this frozen candidate |

## Exact delta hashes

| Path | Unchanged production before SHA256 | Candidate SHA256 |
| --- | --- | --- |
{source_hash_table}
'''
(OUT / 'INTEGRATION_HANDOFF_002.md').write_text(handoff)

artifact_paths = [path for path in sorted(OUT.iterdir()) if path.is_file()
    and path.name not in ('FINAL_ARTIFACTS_001.json', 'PACKAGE_FINAL_001.log')]
artifact_paths.extend(path for path in sorted(example.iterdir()) if path.is_file())
write('FINAL_ARTIFACTS_001.json', {'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'files': [artifact(path) for path in artifact_paths], 'candidate_source_manifest': 'DELTA_MANIFEST_002.json',
    'candidate_frozen_closure': 'TEST_014_AFTER.json', 'production_applied_by_worker176': False})
print(json.dumps({'delta_sha256': sha(OUT / 'DELTA_002.patch'),
    'manifest_sha256': sha(OUT / 'DELTA_MANIFEST_002.json'),
    'handoff_sha256': sha(OUT / 'INTEGRATION_HANDOFF_002.md'),
    'final_test_index_sha256': sha(OUT / 'TEST_INDEX_FINAL_001.json'),
    'original_guard_sha256': sha(OUT / 'ORIGINAL_GUARD_001.json'),
    'artifact_index_sha256': sha(OUT / 'FINAL_ARTIFACTS_001.json'),
    'descriptor_fixture': fixture, 'distinct_passing_case_identities': len(latest),
    'source_files_unchanged_from_frozen013': True, 'guarded_original_files': len(guard)}))
