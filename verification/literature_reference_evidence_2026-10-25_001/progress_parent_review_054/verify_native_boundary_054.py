"""Verify bounded constructed-action evidence without source/model acquisition."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'verification/literature_reference_evidence_2026-10-25_001'
HERE = Path(__file__).resolve().parent
checkpoint = json.loads((BASE / 'CHECKPOINT_052.json').read_text())
changed = [name for name, digest in checkpoint['files'].items()
           if not (ROOT / name).is_file()
           or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
assert not changed, changed
evidence = json.loads((BASE / 'a105_ratio_episode_integration_077/implementation_005/NATIVE_CUSTODY_FAILURE_001.json').read_text())
path = Path(evidence['preserved_db'])
with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=on')
    db.execute('BEGIN')
    row = db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
        (evidence['run_id'], evidence['episode_id'], evidence['decision_index'])).fetchone()
    action, outcome = json.loads(row['action']), json.loads(row['result'])
    native = db.execute('SELECT name,arguments,result,id FROM tool_operations WHERE operation_key=?',
        (f"{evidence['run_id']}:{evidence['episode_id']}:{evidence['decision_index']}",)).fetchone()
    native_result = json.loads(native['result'])
    assert action['tool'] == native['name'] == 'image.view'
    assert action['arguments'] == json.loads(native['arguments'])
    assert outcome['operation_ref'] == native['id'] == evidence['native_operation_ref']
    assert set(outcome) - set(native_result) == {'pending_work_after_action'}
    assert {k: v for k, v in outcome.items() if k != 'pending_work_after_action'} == native_result
    assert outcome['pending_work_after_action']['version'] == 'pending_work_v1'
    population = db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=1',
        (evidence['run_id'], evidence['episode_id'])).fetchone()
    failure = json.loads(population[0])
    assert failure['feedback']['code'] == 'relative_signal_own_view_action_mismatch'
    read_only = {'query_only': db.execute('PRAGMA query_only').fetchone()[0], 'total_changes': db.total_changes}
    assert read_only == {'query_only': 1, 'total_changes': 0}
result = {'utc': datetime.now(timezone.utc).isoformat(), 'evidence_class': 'constructed077 actual selected Workflow; no paper or configured model',
    'checkpoint052_paths_verified_unchanged': len(checkpoint['files']),
    'actual_tool_scope_difference': ['pending_work_after_action'],
    'exact_original_tool_result_matches': True, 'original_operation_and_arguments_match': True,
    'actual_population_failure': failure['feedback']['code'], 'readonly': read_only,
    'repair_status': 'Released to fresh079; not yet verified fixed',
    'goal_complete': False}
with (HERE / 'NATIVE_BOUNDARY_ROOT_RECEIPT_054.json').open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result))
