"""Record the retained shared-boundary checks without accepting the whole tool."""
from pathlib import Path
import ast
import difflib
import hashlib
import json

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
source = ROOT / 'gene_annotation_episode/execution_episodes.py'
reports = []
for name, code, summary in [('check001', 0, '19 passed'),
        ('check002', 1, '1 failed, 32 passed'), ('check003', 0, '52 passed')]:
    folder = PACKET / name
    receipt = json.loads((folder / 'receipt.json').read_bytes())
    assert receipt['returncode'] == code and receipt['executed_source_pins_unchanged']
    assert receipt['metadata']['policy'] == {
        'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'wall_seconds': None}
    assert receipt['metadata']['verified_cgroup']['memory_swap_max'] == 0
    assert summary in (folder / 'stdout.txt').read_text()
    reports.append({'check': name, 'returncode': code, 'summary': summary,
        'receipt_sha256': hashlib.sha256((folder / 'receipt.json').read_bytes()).hexdigest(),
        'executed_source_pins_unchanged': True,
        'checkout_drift_count': len(receipt['checkout_source_drift'])})
original = (PACKET / 'execution_episodes.before.py').read_text()
current = source.read_text()
executed = (PACKET / 'check003/source_snapshot/gene_annotation_episode/execution_episodes.py').read_text()
assert current == executed

def methods(text):
    cls = next(node for node in ast.parse(text).body if isinstance(node, ast.ClassDef))
    return {node.name: ast.dump(node, include_attributes=False) for node in cls.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

old, new = methods(original), methods(current)
changed = [key for key in new if new[key] != old.get(key)]
assert not set(changed).intersection({'__init__', '_request_schema', 'assignment_schema', 'resource_tool_contracts'})
diff = ''.join(difflib.unified_diff(original.splitlines(True), current.splitlines(True),
    fromfile='409-before', tofile='409-verified'))
(PACKET / 'source_changes_002.diff').write_text(diff)
record = {'scope': 'shared_dispatch_permission_order_and_typed_return_hooks', 'reports': reports,
    'changed_methods': changed, 'production_source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'test_source_sha256': hashlib.sha256((ROOT / 'tests/test_protein_structure_shared_integration.py').read_bytes()).hexdigest(),
    'four_408_methods_unchanged': True, 'complete_protein_tool_claimed': False,
    'full_workflow_verification': '410_in_progress', 'grader_count': 112, 'total_rows': 308}
with (PACKET / 'VERIFICATION_001.json').open('x') as handle:
    json.dump(record, handle, indent=2)
    handle.write('\n')
print(json.dumps(record))
