"""Authenticate the complete additive source007 delta and unchanged task texts."""
import ast
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'verification/literature_reference_evidence_2026-10-25_001'
HERE = Path(__file__).resolve().parent
IMPL = BASE / 'a105_ratio_episode_integration_077/implementation_005'
REVIEW = IMPL / 'source_review_007'
old = {r['path']: r for r in json.loads((IMPL / 'SOURCE_REVIEW_MANIFEST_004.json').read_text())['files']}
new = json.loads((REVIEW / 'SOURCE_REVIEW_MANIFEST_007.json').read_text())
name = 'gene_annotation_episode/literature_experimental_prompt.py'
current = (ROOT / name).read_text()
new_import = '    render_received as _ratio_source_received, render_own_result as _ratio_source_own,\n    is_row as _ratio_source_row, rows_from_reports as _ratio_source_rows)'
old_import = '    render_received as _ratio_source_received, render_own_result as _ratio_source_own, is_row as _ratio_source_row)'
new_branch = '''        received_ratio_sheets = {row['sheet_ref'] for row in _ratio_source_rows(state.get('child_reports', ()))}
        if (isinstance(outcome, Mapping) and 'result' not in outcome
                and received_ratio_sheets.intersection(outcome.get('record_refs', ()))):
            # The original child return's host receipt refs are not an extra
            # scientific return. Its exact admitted rows are rendered below.
            _section(parts, 'Last selected action outcome', _values(_pick(outcome, ('status', 'feedback'))))
        else:
            _source_result(parts, outcome, "Last selected action outcome")'''
old_branch = '        _source_result(parts, outcome, "Last selected action outcome")'
assert current.count(new_import) == current.count(new_branch) == 1
reconstructed004 = current.replace(new_import, old_import).replace(new_branch, old_branch)
assert hashlib.sha256(reconstructed004.encode()).hexdigest() == old[name]['sha256']
assert len(reconstructed004.encode()) == old[name]['bytes']
delta = ''.join(difflib.unified_diff(reconstructed004.splitlines(True), current.splitlines(True),
    fromfile='004/' + name, tofile='007/' + name))
assert delta == (REVIEW / 'DELTA_FROM004_007.diff').read_text()
complete = ''
for row in new['files']:
    path = row['path']
    data = (ROOT / path).read_bytes()
    assert hashlib.sha256(data).hexdigest() == row['sha256'] and len(data) == row['bytes']
    ast.parse(data)
    if path != name:
        assert row == old[path]
    before = IMPL / 'before' / path
    original, label = (before.read_text(), 'a/' + path) if before.is_file() else ('', '/dev/null')
    complete += ''.join(difflib.unified_diff(original.splitlines(True), data.decode().splitlines(True),
        fromfile=label, tofile='b/' + path))
assert complete == (REVIEW / 'COMPLETE_OWNED_DELTA_007.diff').read_text()
native = hashlib.sha256((ROOT / 'gene_annotation_episode/literature_ratio_source_storage.py').read_bytes()).hexdigest()
assert native == new['native_dependency_sha256']
proof = json.loads((HERE / 'ROOT_CONNECTED_PYTEST_RECEIPT_055.json').read_text())
assert proof['returncode'] == 0 and not proof['source_changed_during_test']
assert all(proof['after_sha256'][r['path']] == r['sha256'] for r in new['files'])
assert proof['after_sha256']['gene_annotation_episode/literature_ratio_source_storage.py'] == native
result = {'utc': datetime.now(timezone.utc).isoformat(), 'six_production_hashes_match007': True,
    'complete_owned_delta_exact': True, 'only_later_delta_is_reviewed_import_and_parent_receipt_display_branch': True,
    'reconstructed004_exact': True, 'native_dependency_exact': True,
    'root_independent_connected_case_uses_exact007_and079': True,
    'acceptance_scope': 'Source review plus one independent selected durable engineering case; final077 pin and recovery proofs still pending',
    'goal_complete': False}
with (HERE / 'SOURCE007_ROOT_RECEIPT_055.json').open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result))
