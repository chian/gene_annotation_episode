"""Read retained verification evidence; do not execute or alter scientific work."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


DIRECTORY = Path(__file__).resolve().parent
REPOSITORY = DIRECTORY.parents[1]
PASS_RUNS = ('run_004_full', 'run_006_remaining_independent', 'run_007_receiver_boundaries')
passing = {}
runs = []
for name in PASS_RUNS:
    directory = DIRECTORY / name
    receipt = json.loads((directory / 'verification-receipt.json').read_text())
    counts = Counter()
    for case in ET.parse(directory / 'tests.xml').getroot().findall('.//testcase'):
        outcome = ('failure' if case.find('failure') is not None else
            'error' if case.find('error') is not None else
            'skipped' if case.find('skipped') is not None else 'passed')
        counts[outcome] += 1
        if outcome == 'passed':
            nodeid = 'tests/test_native_infernal_results_integration.py::' + case.attrib['name']
            assert nodeid not in passing, nodeid
            passing[nodeid] = {
                'nodeid': nodeid,
                'receipt': str((directory / 'verification-receipt.json').relative_to(REPOSITORY)),
                'junit': str((directory / 'tests.xml').relative_to(REPOSITORY)),
                'source_before': str((directory / 'source-before.json').relative_to(REPOSITORY)),
                'source_after': str((directory / 'source-after.json').relative_to(REPOSITORY)),
                'source_changed_during_run': receipt['source_changed_during_run'],
            }
    runs.append({'directory': str(directory.relative_to(REPOSITORY)), 'counts': dict(counts),
        'command': receipt['command'], 'policy': receipt['policy'], 'returncode': receipt['returncode'],
        'source_changed_during_run': receipt['source_changed_during_run']})

assert len(passing) == 42
cases = []
native_counts = Counter()
for directory in sorted(DIRECTORY.glob('run_*')):
    if not directory.is_dir():
        continue
    for path in sorted((directory / 'temporary/pytest').glob('*/CASE.json')):
        if path.parent.is_symlink():
            continue
        case = json.loads(path.read_text())
        native_counts[case['program']] += 1
        cases.append({'case': str(path.relative_to(REPOSITORY)), 'program': case['program'],
            'selected_actions': case['selected_actions'], 'controller_observations': case['controller_observations'],
            'scripted_decision_calls': case['scripted_decision_calls'], 'root_units': case['parent_units'],
            'root_gains': case['parent_gains'], 'result_gains': [row['gains'] for row in case['results']],
            'result_future_expectations': [row['future_expectation'] for row in case['results']],
            'result_complete': [row['complete'] for row in case['results']],
            'failure_codes': [[failure['code'] for failure in row['failures']] for row in case['results']],
            'partial_result_fixture_estimator': case['partial_result_fixture_estimator']})

last_hashes = json.loads((DIRECTORY / PASS_RUNS[-1] / 'source-after.json').read_text())
summary = {
    'status': '42 unique test nodes passed across focused runs; prior failed receipts are preserved',
    'scope': 'Tests/evidence only; real native local Workflow; scripted scientific choices/controllers; no model RPC',
    'runs': runs, 'passing_test_nodes': [passing[key] for key in sorted(passing)],
    'native_executions_across_all_retained_runs': dict(native_counts),
    'cases_across_all_retained_runs': cases,
    'final_source_hashes': last_hashes,
    'limitations': [
        'No single clean 42-test invocation is claimed; run004 stopped on the real receiver leak.',
        'Run006 recorded concurrent presentation edits; native capture/worker/publication/results/returns stayed unchanged.',
        'Run007 has unchanged before/after sources and verifies the corrected actual receiver boundaries.',
        'Root engineering credit counts received observations; it is not annotation confidence or W05.',
        'No configured scientific model, API service or HPC execution was exercised.',
        'Root review and global accounting are outside this tests-only ownership.',
    ],
}
(DIRECTORY / 'FINAL_VERIFICATION_001.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
(DIRECTORY / 'passing-test-nodes.tsv').write_text('nodeid\treceipt\tsource_before\tsource_after\tsource_changed_during_run\n' +
    ''.join('\t'.join((row['nodeid'], row['receipt'], row['source_before'], row['source_after'],
        json.dumps(row['source_changed_during_run'], separators=(',', ':')))) + '\n'
        for row in summary['passing_test_nodes']))
print(json.dumps({'unique_passing_nodes': len(passing), 'native_counts': dict(native_counts),
    'summary': str(DIRECTORY / 'FINAL_VERIFICATION_001.json')}))
