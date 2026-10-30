"""Root acceptance of the bounded native receipt repair, not the full goal."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'verification/literature_reference_evidence_2026-10-25_001'
HERE = Path(__file__).resolve().parent
PACKAGE = BASE / 'a105_native_view_receipt_repair_079'
artifact = json.loads((PACKAGE / 'ARTIFACT_MANIFEST_001.json').read_text())
pin_manifest = json.loads((PACKAGE / 'PIN_MANIFEST_001.json').read_text())
pin = Path(pin_manifest['pin_root'])
for name, row in artifact['files'].items():
    data = (PACKAGE / name).read_bytes()
    assert len(data) == row['size'] and hashlib.sha256(data).hexdigest() == row['sha256'], name
for name, row in pin_manifest['files'].items():
    data = (pin / name).read_bytes()
    assert len(data) == row['size'] and hashlib.sha256(data).hexdigest() == row['sha256'], name
assert {str(p.relative_to(pin)) for p in pin.rglob('*') if p.is_file()} == set(pin_manifest['files'])
audit = json.loads((PACKAGE / 'PIN_ACTUAL_IMPORTS_001.json').read_text())
assert audit['exitstatus'] == 0 and audit['collected_tests'] == 152
for name, row in audit['imported_sources'].items():
    path = Path(row['path'])
    assert path.is_relative_to(pin), name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256'], name
    assert pin_manifest['files'][str(path.relative_to(pin))]['sha256'] == row['sha256'], name
native = 'gene_annotation_episode/literature_ratio_source_storage.py'
test = 'tests/test_literature_ratio_source_runtime_receipt.py'
for name in (native, test):
    assert (ROOT / name).read_bytes() == (pin / name).read_bytes()
original = (PACKAGE / 'before' / native).read_bytes()
assert hashlib.sha256(original).hexdigest() == pin_manifest['native_before_sha256']
delta = ''.join(difflib.unified_diff(original.decode().splitlines(True), (ROOT / native).read_text().splitlines(True),
    fromfile='before/' + native, tofile=native))
assert delta == (PACKAGE / 'NATIVE_PATCH_001.diff').read_text()
proof = json.loads((BASE / 'progress_parent_review_054/REPAIRED_ORIGINAL_VIEW_ROOT_RECEIPT_054.json').read_text())
assert proof['native_code_sha256'] == hashlib.sha256((ROOT / native).read_bytes()).hexdigest()
assert proof['readonly'] == {'query_only': 1, 'total_changes': 0}
assert proof['actual_original_constructed_view_authenticates_after_repair']
assert proof['digest_covers_full_original_runtime_outcome']
comparison = json.loads((PACKAGE / 'ACTUAL_RECORD_COMPARISON_001.json').read_text())
assert comparison['original_action_and_operation_unchanged'] and comparison['readonly_changes'] == 0
assert '152 passed' in (PACKAGE / 'pytest_pin_all_001.log').read_text()
result = {'utc': datetime.now(timezone.utc).isoformat(),
    'accepted_scope': 'Native own-view receipt comparison repair only; original full runtime digest retained',
    'complete_new_test_and_patch_reviewed': True,
    'artifact_payloads_verified': len(artifact['files']), 'pin_files_verified': len(pin_manifest['files']),
    'actual_in_pin_imports_verified': len(audit['imported_sources']),
    'final_pinned_tests': 152, 'unique_coverage': '23 new receipt cases plus129 original native/pure regressions; earlier focused runs overlap',
    'root_independent_original_view_readonly_proof': True,
    'root_independent_selected_durable_case_passed': True,
    'working_native_and_new_test_equal_pin': True, 'exact_patch_reconstructed': True,
    'process_visibility_qualification': 'Agent reported one incidental broad process listing; no unrelated argv retained; deliberate DB reads bounded to released constructed case',
    'remaining': '077 final coherent pin, integration recovery review and configured-model/primary/full literature scope',
    'goal_complete': False}
with (HERE / 'NATIVE079_ROOT_ACCEPTANCE_055.json').open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result))
