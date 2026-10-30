"""Record existing verification evidence without executing or regrading a tool."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).parent
AUTHORITY = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')


def descriptor(path):
    return {'path': str(path.relative_to(ROOT)),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


assert hashlib.sha256(AUTHORITY.read_bytes()).hexdigest() == '11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7'
runs = [
    ('tool_graders_alignment_reference_2026-10-26_285', 'run_004', 71),
    ('tool_graders_blast_columns_2026-10-26_286', 'attempt_004', 258),
    ('tool_graders_alignment_returns_2026-10-26_287', 'run_005', 103),
    ('tool_graders_alignment_custody_2026-10-26_288', 'run_004', 65),
    ('tool_graders_alignment_workflow_2026-10-26_289', 'check003', 12),
    ('tool_graders_phmmer_sites_2026-10-26_291', 'check005', 15),
    ('tool_graders_phmmer_sites_2026-10-26_291', 'check006', 9),
    (BASE.name, 'check006', 95),
]
evidence = []
for directory, run, expected in runs:
    path = ROOT / 'verification' / directory / run
    receipt = json.loads((path / 'receipt.json').read_text())
    assert receipt['returncode'] == 0
    assert receipt['policy'] == {'memory_bytes': 21474836480,
                                'scratch_bytes': 4294967296, 'wall_seconds': None}
    junit = path / 'junit.xml'
    if junit.exists():
        suites = ET.parse(junit).getroot().findall('testsuite')
        counts = {name: sum(int(suite.get(name, 0)) for suite in suites)
                  for name in ('tests', 'errors', 'failures', 'skipped')}
        assert counts == {'tests': expected, 'errors': 0, 'failures': 0, 'skipped': 0}
        proof = descriptor(junit)
    else:
        stdout = path / 'stdout.log'
        assert re.search(r'\b' + str(expected) + r' passed\b', stdout.read_text())
        proof = descriptor(stdout)
    evidence.append({'run': str(path.relative_to(ROOT)), 'passing_checks': expected,
        'receipt': descriptor(path / 'receipt.json'), 'test_outcome': proof,
        'changed_sources': receipt.get('changed_sources'),
        'source_snapshots_recorded': 'source_sha256_after' in receipt})

root_receipt = json.loads((BASE / 'check006/receipt.json').read_text())
assert root_receipt['changed_sources'] == []
example_paths = sorted((ROOT / 'verification/tool_graders_alignment_workflow_2026-10-26_289/check003/examples').glob('*.json'))
assert len(example_paths) == 10
example_paths += sorted((ROOT / 'verification/tool_graders_phmmer_sites_2026-10-26_291/check005/examples').glob('*.json'))
manifest = {
    'schema': 'alignment_site_baseline_verification_v1',
    'recorded_at': datetime.now(timezone.utc).isoformat(),
    'scope_rows': ['A-L064-native-pairwise', 'A-L064-blast-hsp', 'A-L064-mapping-correspondence'],
    'report': descriptor(BASE / 'REPORT_001.md'),
    'contracts': [descriptor(BASE / name) for name in ('CONTRACT_001.md', 'RETURN_CONTRACT_002.md')],
    'run_results': evidence,
    'verified_source_sha256': root_receipt['source_sha256_after'],
    'source_snapshot_meaning': 'Exact tracked source hashes from the completed root check006; not a claim that subsequent work leaves those files unchanged.',
    'filled_verification_examples': [descriptor(path) for path in example_paths],
    'test_counts_overlap': True,
    'pending_native_pairwise_hsp_connection': True,
    'inventory_tally_changed': False,
    'qualification': 'Reusable fields and population/calculation functions verified on the declared retained-source paths. Scripted Workflow tests, retained native inputs and actual small local operations are separate evidence. No live NCBI/API/HPC or configured-model annotation claim.',
}
with (BASE / 'BASELINE_VERIFICATION_001.json').open('x') as stream:
    json.dump(manifest, stream, indent=2)
    stream.write('\n')
print(json.dumps({'recorded_runs': len(evidence), 'root_passing_checks': 95,
                  'retained_example_files': len(example_paths), 'inventory_tally_changed': False}))
