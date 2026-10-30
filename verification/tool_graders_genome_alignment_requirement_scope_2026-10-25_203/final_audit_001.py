"""Freeze completed verification and audit all original source/evidence hashes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

OWN = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(root, rows):
    for row in rows:
        path = root / row['path']
        assert path.is_file() and path.stat().st_size == row['bytes']
        assert digest(path) == row['sha256'], str(path)
    return len(rows)


before = json.loads((OWN / 'REPAIR_BEFORE_MANIFEST_001.json').read_text())['files']
after = json.loads((OWN / 'REPAIR_AFTER_MANIFEST_001.json').read_text())['files']
fixture = json.loads((OWN / 'FIXTURE_COMPLETION_MANIFEST_001.json').read_text())
counts = {
    'baseline_files_unchanged': check(OWN / 'baseline_candidate', before),
    'repair_source_files_unchanged_during_tests': check(OWN / 'repair_candidate', after),
    'fixture_candidate_source_files_unchanged': check(OWN / 'repair_fixture_candidate', after),
    'extra_fixture_files_unchanged': check(OWN / 'repair_fixture_candidate', fixture['extra_fixture_files']),
    'original_diagnostic_files_unchanged': check(OWN,
        json.loads((OWN / 'OUTPUT_HASHES_001.json').read_text())['output_files']),
}
runs, passed, unresolved = {}, set(), set()
for name in ('repair_scope_001', 'repair_core_001', 'repair_completed_fixtures_002',
             'repair_host_001', 'repair_episode_001'):
    receipt = json.loads((OWN / name / 'receipt.json').read_text())
    outcomes = json.loads((OWN / name / 'test_outcomes.json').read_text())
    successes = {r['nodeid'] for r in outcomes if r['when'] == 'call' and r['outcome'] == 'passed'}
    failures = {r['nodeid'] for r in outcomes if r['outcome'] == 'failed'}
    if name == 'repair_core_001':
        assert receipt['exit_code'] == 1 and len(successes) == 750 and len(failures) == 6
        assert (OWN / name / 'output.log').read_text().count('E       FileNotFoundError:') == 6
        unresolved |= failures
    else:
        assert receipt['exit_code'] == 0 and not failures
    passed |= successes
    runs[name] = {'passed': len(successes), 'failed': len(failures), 'seconds': receipt['seconds'],
        'exit_code': receipt['exit_code'], 'network_scope': receipt['network_scope']}
assert unresolved <= passed
baseline_outcomes = json.loads((OWN / 'baseline_core_failures_002/test_outcomes.json').read_text())
baseline_failures = {r['nodeid'] for r in baseline_outcomes if r['outcome'] == 'failed'}
assert baseline_failures == unresolved
assert (OWN / 'baseline_core_failures_002/output.log').read_text().count('E       FileNotFoundError:') == 6
episode_root = OWN / 'repair_candidate/verification/tool_graders_bvbrc_genome_alignment_episode_flow_2026-10-25/runs'
episodes = list(episode_root.glob('*/SAVED_REPLAY_CHECK.json'))
assert len(episodes) == 1
episode = episodes[0].parent
for name in ('SOURCE_GUARD_WORKFLOW_CLOSED.json', 'SOURCE_GUARD_AFTER_TESTS.json'):
    guard = json.loads((episode / name).read_text())
    assert not guard['used_changes'] and not guard['used_without_before_hash']
replay = json.loads(episodes[0].read_text())
assert replay['counts_before'] == replay['counts_after'] and replay['new_http_calls'] == 0
assert replay['same_plan_recalculation_equal'] and replay['original_action_unchanged']
assert replay['changed_plan_union_bases'] == 677
authority = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
assert digest(authority) == '11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7'
receipt = {**counts, 'completed_at': datetime.now(timezone.utc).isoformat(), 'runs': runs,
    'distinct_passing_cases': len(passed), 'fixture_failures_reproduced_on_baseline': sorted(baseline_failures),
    'unresolved_pytest_failures': [], 'workflow_evidence_directory': str(episode.relative_to(OWN)),
    'saved_replay_counts_unchanged': True, 'new_http_calls_during_saved_replay': 0,
    'same_plan_recalculation_equal': True, 'changed_plan_union_bases': 677,
    'original_action_unchanged': True, 'authority_sha256': digest(authority),
    'implementation_changes': ['gene_annotation_episode/bvbrc_genome_alignment_sheet.py'],
    'new_tests': ['tests/test_genome_alignment_requirement_scope.py'], 'production_application': False,
    'external_network': False, 'live_bvbrc': False, 'remote_jobs': False, 'new_native_alignment': False,
    'wall_time_limit': None}
with (OWN / 'FINAL_AUDIT_001.json').open('x') as handle:
    json.dump(receipt, handle, indent=2, sort_keys=True)
    handle.write('\n')
files = []
for path in sorted(OWN.rglob('*')):
    if path.is_file():
        files.append({'path': str(path.relative_to(OWN)), 'bytes': path.stat().st_size, 'sha256': digest(path)})
size = sum(row['bytes'] for row in files)
assert size < 4 * 1024**3
with (OWN / 'OUTPUT_HASHES_REPAIR_002.json').open('x') as handle:
    json.dump({'total_bytes_before_this_manifest': size, 'files': files}, handle, indent=2, sort_keys=True)
    handle.write('\n')
for path in OWN.rglob('*'):
    if path.is_file():
        path.chmod(0o444)
print(json.dumps({'counts': counts, 'distinct_passing_cases': len(passed),
    'total_bytes_before_final_manifest': size, 'runs': runs}, sort_keys=True))
