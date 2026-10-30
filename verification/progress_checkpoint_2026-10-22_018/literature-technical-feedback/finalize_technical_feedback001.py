"""Offline-only comparisons and sealing after the sole DB connection closed."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import stat

OUT = Path(__file__).resolve().parent


def meta(path):
    s = path.lstat()
    assert stat.S_ISREG(s.st_mode)
    body = path.read_bytes()
    e = path.lstat()
    assert (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_mode) == (
        e.st_dev, e.st_ino, e.st_size, e.st_mtime_ns, e.st_mode)
    return {'sha256': sha256(body).hexdigest(), 'size': len(body),
        'mode': stat.S_IMODE(e.st_mode), 'mtime_ns': e.st_mtime_ns,
        'inode': e.st_ino, 'device': e.st_dev}


def write(name, value):
    target = OUT / name
    assert not target.exists()
    target.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


capture = json.loads((OUT/'CAPTURE001.json').read_text())
rows = capture['rows']
assert capture['error'] is None
assert capture['provenance']['connection_explicitly_closed']
assert capture['provenance']['total_changes'] == 0
assert [row['decision_index'] for row in rows] == list(range(46))
counts = dict(Counter(row['outcome_status'] for row in rows))
assert counts == {'unavailable': 1, 'completed': 24, 'partial': 1, 'invalid': 1, 'failed': 19}
failed = [row for row in rows if row['outcome_status']=='failed']
noncompleted = [row for row in rows if row['outcome_status'] not in ('completed','partial')]
tool_errors = [row for row in noncompleted if row['selected_kind']=='tool']
comparisons = []
for row in tool_errors:
    target = row['outcome_feedback_sha256']
    matches = {prefix: row[prefix+'_sha256'] == target for prefix in (
        'next_raw_feedback', 'next_model_feedback', 'next_raw_last_feedback', 'next_model_last_feedback')}
    operations_match = (row['operation_ref'] is not None and
        row['operation_ref'] == row['next_raw_last_outcome_operation_ref'] == row['next_model_last_outcome_operation_ref'])
    assert all(matches.values()) and operations_match
    comparisons.append({'decision_index': row['decision_index'], 'next_call_index': row['next_call_index'],
        'feedback_identity_matches': matches, 'original_operation_matches': operations_match})
assert all(row['credit_is_null'] for row in noncompleted)
assert all(not row['credit_is_null'] for row in rows if row['outcome_status'] in ('completed','partial'))
assert all(not row['result_missing'] for row in rows)
assert len({row['arguments_json_text_sha256'] for row in failed}) == 1
assert len({row['action_text_sha256'] for row in failed}) == 1
assert len({row['operation_ref'] for row in failed}) == 19
assert all(row['outcome_feedback_code']=='provider_http_500' for row in failed)
readset = json.loads((OUT/'READSET001.json').read_text())
assert meta(Path(readset['runtime_path']))['sha256'] == readset['runtime_after']['sha256']
write('RESULTS001.json', {'version': 'bounded_literature_child_technical_feedback_result_v1',
    'status': 'verified_technical_feedback_with_limits', 'decision_indices': [0,45],
    'outcome_counts': counts, 'completed_partial_nonnull_credit_count': 25,
    'noncompleted_null_credit_count': 21, 'missing_action_result_count': 0,
    'failed_read_decisions': [row['decision_index'] for row in failed],
    'failed_read_safe_category': 'provider', 'failed_read_safe_code': 'provider_http_500',
    'failed_read_unique_selected_action_hashes': 1, 'failed_read_unique_argument_hashes': 1,
    'failed_read_unique_operation_refs': 19, 'tool_failure_feedback_comparisons': comparisons,
    'next_raw_model_top_feedback_hash_equal_count': sum(row['next_raw_feedback_sha256']==row['next_model_feedback_sha256'] for row in rows),
    'next_saved_calls_present_count': sum(row['next_call_index'] is not None for row in rows),
    'next_saved_response_nonnull_count': sum(row['next_response_missing']==0 for row in rows),
    'lost_failed_tool_feedback_reproduced': False,
    'runtime_defect_supported': False,
    'implementation_action': 'none; no new stopping/retry/failure-credit law inferred',
    'limits': ['Only original child decisions0–45 and exact nextcall≤46 technical fields',
        'No child scientific meaning, diagnostic artifact body or request/response/commit body exported',
        'Repeated argument identity does not diagnose upstream error or request appropriateness',
        'No later action, child closure/return/admission or parent use claim',
        'The reader changes0 rows; active concurrent-writer files were not claimed immutable'],
    'database_connection_count': 1, 'query_only': 1, 'total_changes': 0,
    'connection_explicitly_closed': True, 'original_static_locator_and_runtime_unchanged': True})
write('COMMAND001.json', {'cwd':str(OUT), 'commands':[
    '/home/chia/repos/gene_annotation_episode/.venv/bin/python capture_technical_feedback001.py > capture.stdout.log 2> capture.stderr.log',
    '/home/chia/repos/gene_annotation_episode/.venv/bin/python finalize_technical_feedback001.py'],
    'all_analysis_after_capture': 'offline from retained restricted CAPTURE001 only; no DB reopen'})
for path in OUT.iterdir():
    assert path.is_file() and not path.is_symlink()
    path.chmod(0o444)
members = {path.name: meta(path) for path in sorted(OUT.iterdir())}
write('MANIFEST001.json', {'version':'readonly_child_technical_feedback_manifest_v1',
    'files':members, 'regular_file_count_excluding_manifest':len(members),
    'regular_bytes_excluding_manifest':sum(row['size'] for row in members.values()),
    'manifest_self_excluded':True, 'directories':['.'], 'aliases':[],
    'scope':'one finite technical-only active new-run read; no scientific child body publication'})
(OUT/'MANIFEST001.json').chmod(0o444)
OUT.chmod(0o555)
print(json.dumps({name:sha256((OUT/name).read_bytes()).hexdigest() for name in (
    'CAPTURE001.json','RESULTS001.json','READSET001.json','REPORT001.md','MANIFEST001.json')},sort_keys=True))
