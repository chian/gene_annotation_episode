"""Apply only the reviewed 197 optimization and 203 reference-domain repair."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PERF = HERE.parent / 'tool_graders_typed_return_performance_2026-10-25_197'
FIX = HERE.parent / 'tool_graders_genome_alignment_requirement_scope_2026-10-25_203'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def save(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


assert not (HERE / 'APPLICATION_RECEIPT_001.json').exists()
boundary = json.loads((PERF / 'APPLICATION_BOUNDARY.json').read_text())
baseline = json.loads((PERF / 'source_before.json').read_text())
assert len(baseline) == 1045
before = {name: sha(ROOT / name) for name in baseline}
assert before == baseline, 'Production changed from the reviewed baseline'
for name, digest in boundary['receipt_sha256'].items():
    assert sha(PERF / name) == digest, name
assert json.loads((PERF / 'full_workflow_001/receipt.json').read_text())['exit_code'] == 0
for name in ('repair_host_001', 'repair_episode_001'):
    result = json.loads((FIX / name / 'receipt.json').read_text())
    assert result['exit_code'] == 0, name

changes = list(boundary['application_boundary'])
for path, previous, updated in (
    ('gene_annotation_episode/bvbrc_genome_alignment_sheet.py',
     '110d92d7d046dd29000b5f03801c351912b590c6d14f3f949b457c51ce2e44e8',
     '28cdceb6364ea0ccd7f94768ddf081d54e9b7e19db1e5218bd9862f443fa6654'),
    ('tests/test_genome_alignment_requirement_scope.py', None,
     '2f075b6b02024b2ac63bae6151afe967c88658a360de62fec1f1aac38d532eb5'),
):
    changes.append({'path': path, 'expected_baseline_sha256': previous,
        'candidate_sha256': updated, 'candidate_file': str(FIX / 'repair_candidate' / path)})

for row in changes:
    assert sha(ROOT / row['path']) == row['expected_baseline_sha256'], row['path']
    assert sha(Path(row['candidate_file'])) == row['candidate_sha256'], row['path']
save('APPLICATION_BEFORE_001.json', before)
save('APPLICATION_PLAN_001.json', changes)
for row in changes:
    shutil.copyfile(row['candidate_file'], ROOT / row['path'])
after = {name: sha(ROOT / name) for name in baseline}
for row in changes:
    after[row['path']] = sha(ROOT / row['path'])
    assert after[row['path']] == row['candidate_sha256'], row['path']
allowed = {row['path'] for row in changes}
assert all(after[name] == digest for name, digest in before.items() if name not in allowed)
save('APPLICATION_AFTER_001.json', after)
receipt = {'applied': True, 'at': datetime.now(timezone.utc).isoformat(),
    'production_modules': 4, 'new_tests': 1, 'verified_target_paths': len(after),
    'unexpected_changed_paths': [], 'composition_verification': 'pending',
    'isolated_verification': {'performance': '596 passed; one independently reproduced baseline GenomeAlignment failure',
        'genome_alignment_repair': '855 distinct passed, including that failure, 13 host and 6 Workflow checks'},
    'scope': 'Exact reviewed changes only. No method_loop, numerical formula, episode prompt, inventory scope or historical receipt changed.'}
save('APPLICATION_RECEIPT_001.json', receipt)
print(json.dumps(receipt))
