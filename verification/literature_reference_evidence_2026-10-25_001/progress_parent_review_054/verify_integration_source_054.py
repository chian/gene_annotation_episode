"""Root source-review identity checks; no Workflow or scientific execution."""
import ast
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'verification/literature_reference_evidence_2026-10-25_001'
HERE = Path(__file__).resolve().parent
DESIGN = BASE / 'a105_ratio_episode_integration_077'
IMPL = DESIGN / 'implementation_005'
manifest = json.loads((IMPL / 'SOURCE_REVIEW_MANIFEST_004.json').read_text())
before = json.loads((IMPL / 'BEFORE_MANIFEST_005.json').read_text())
shared = {r['path']: r for r in before['owned_shared_files']}
patch = ''
for row in manifest['files']:
    path = row['path']
    data = (ROOT / path).read_bytes()
    assert len(data) == row['bytes']
    assert hashlib.sha256(data).hexdigest() == row['sha256']
    ast.parse(data)
    if path in shared:
        original = (IMPL / 'before' / path).read_bytes()
        assert hashlib.sha256(original).hexdigest() == shared[path]['sha256']
        assert len(original) == shared[path]['bytes']
        old_name = 'a/' + path
    else:
        original, old_name = b'', '/dev/null'
    patch += ''.join(difflib.unified_diff(original.decode().splitlines(True), data.decode().splitlines(True),
        fromfile=old_name, tofile='b/' + path))
assert patch == (IMPL / 'SOURCE_REVIEW_DELTA_004.diff').read_text()

def assignments(path):
    result = {}
    for node in ast.parse(path.read_bytes()).body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    result[target.id] = node.value.value
    return result

source = assignments(ROOT / 'gene_annotation_episode/literature_ratio_source_prompt.py')
assert source['SOURCE_RATIO_TASK'].strip() == (DESIGN / 'DRAFT_SOURCE_RATIO_TASK_INSERT_001.txt').read_text().strip()
preserved = {}
for name, literal in (('literature_reference_parent_prompt.py', 'REFERENCE_PARENT_TASK'),
                      ('literature_experimental_prompt.py', 'EXPERIMENTAL_TASK')):
    old = assignments(IMPL / 'before/gene_annotation_episode' / name)
    new = assignments(ROOT / 'gene_annotation_episode' / name)
    assert old[literal] == new[literal]
    preserved[literal] = len(new[literal])
result = {'utc': datetime.now(timezone.utc).isoformat(),
    'six_stable_production_files_hash_checked': True, 'four_actual_before_snapshots_hash_checked': True,
    'complete_six_file_patch_reconstructed': True, 'all_six_files_parse': True,
    'source_task_equals_reviewed_design_insert': True, 'preserved_recurring_task_characters': preserved,
    'root_actual_reads': ['complete shared four-file delta in sequential untruncated portions',
        'complete new source TASK and operation description', 'complete new 189-line renderer',
        'current descriptor construction and all population/received/admission consumers'],
    'review_note': 'Multiple JATS paragraph labels can be conservatively retained for scoped access; known status preserved',
    'accepted_connected_integration': False,
    'remaining': 'Root test/proof review and replay; native079 repair; selected durable worker/C4/subset/fresh-readonly/observation proof'}
with (HERE / 'INTEGRATION_SOURCE_ROOT_RECEIPT_054.json').open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result))
