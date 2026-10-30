"""Read-only stdlib aggregation of retained test receipts and scoped file pins."""
from pathlib import Path
import difflib
import hashlib
import json

packet = Path(__file__).resolve().parent
repo = packet.parents[1]
runner = repo / 'verification/tool_graders_hmmer_map_verification_2026-10-28_529'
attempts = []
latest = {}
for name in ('check163a_operation706', 'check163b_operation706', 'check163c_operation706', 'check163d_operation706'):
    path = runner / name
    receipt = json.loads((path / 'receipt.json').read_text())
    audit = json.loads((path / 'execution_audit.json').read_text())
    cases = [json.loads(row) for row in (path / 'case_reports.jsonl').read_text().splitlines()]
    for case in cases:
        latest[case['nodeid']] = {'attempt': name, **case}
    attempts.append({'name': name, 'receipt': receipt, 'audit': audit,
        'passed': sum(case['outcome'] == 'passed' for case in cases),
        'failed': sum(case['outcome'] == 'failed' for case in cases)})
# The original unparameterized control/public-log tests were replaced by their
# explicit parameter cases; preserve their historical rows in attempts above.
latest.pop('tests/test_flux_balance_operation_binding_706.py::test_public_selected_missing_control_is_structured_failure', None)
latest.pop('tests/test_flux_balance_operation_binding_706.py::test_progress_public_ports_observe_and_read_original_declared_log', None)
(packet / 'VERIFICATION_RESULTS_003.json').write_text(json.dumps({'attempts': attempts,
    'latest_distinct_cases': list(latest.values()),
    'latest_distinct_case_count': len(latest),
    'latest_pass_count': sum(x['outcome'] == 'passed' for x in latest.values()),
    'latest_fail_count': sum(x['outcome'] != 'passed' for x in latest.values())}, indent=2) + '\n')
files = [repo / 'gene_annotation_episode' / name for name in (
    'practical_execution_operations.py', 'practical_resource_episodes.py', 'execution_progress.py')]
files.append(repo / 'tests/test_flux_balance_operation_binding_706.py')
pins = []
for path in files:
    raw = path.read_bytes()
    pins.append({'path': str(path.relative_to(repo)), 'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)})
    before = packet / (path.name + '.before')
    if before.exists():
        (packet / (path.name + '.diff')).write_text(''.join(difflib.unified_diff(
            before.read_text().splitlines(True), raw.decode().splitlines(True), fromfile=before.name,
            tofile=str(path.relative_to(repo)))))
(packet / 'FINAL_PINS_003.json').write_text(json.dumps(pins, indent=2) + '\n')
print(json.dumps({'attempts': [{k: a[k] for k in ('name', 'passed', 'failed')} for a in attempts],
    'latest_distinct_cases': len(latest), 'latest_failed_cases': [x['nodeid'] for x in latest.values() if x['outcome'] != 'passed']}))
