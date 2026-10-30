"""Read only public lifecycle/count/selected-action metadata; no provider contents."""
import json
from pathlib import Path
import sqlite3
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent

def process_identity(pid):
    try:
        fields = Path('/proc/'+str(pid)+'/stat').read_text().rsplit(')', 1)[1].split()
        if fields[0] == 'Z':
            return None
        return {'pid': pid, 'start_ticks': fields[19],
            'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
    except (OSError, IndexError):
        return None

status_path = HERE/'STATUS_002.json'
status = json.loads(status_path.read_text()) if status_path.exists() else None
owner = None if status is None else status.get('process_identity')
live = bool(owner is not None and process_identity(owner['pid']) == owner)
path = HERE/'configured_001/state/state.sqlite3'
db = sqlite3.connect('file:'+str(path)+'?mode=ro', uri=True)
db.row_factory = sqlite3.Row
result = {'observed_at_utc': datetime.now(timezone.utc).isoformat(),
    'meaning': 'Operator lifecycle/count metadata only; no episode action or controller observation is created.',
    'provider_content_read': False,
    'operator_status': status, 'confirmed_original_process_live': live,
    'run': [dict(r) for r in db.execute('SELECT run_id,state,started_at,updated_at FROM runtime_runs')],
    'episodes': [dict(r) for r in db.execute('SELECT episode_id,path,state,completion FROM runtime_episodes')],
    'counts': {table: db.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in (
        'runtime_actions', 'runtime_observations', 'runtime_model_calls', 'runtime_report_attempts')},
    'model_call_completion_counts': dict(db.execute('SELECT CASE WHEN response IS NULL THEN "pending" ELSE "returned" END,count(*) FROM runtime_model_calls GROUP BY response IS NULL').fetchall()),
    'selected_action_categories': [dict(r) for r in db.execute('''SELECT episode_id,
        json_extract(action,'$.kind') AS kind,json_extract(action,'$.tool') AS tool,
        CASE WHEN result IS NULL THEN 'pending' ELSE json_extract(result,'$.status') END AS status,
        count(*) AS records FROM runtime_actions GROUP BY episode_id,kind,tool,status''')],
    'deliveries': [dict(r) for r in db.execute('SELECT parent_episode_id,child_episode_id,decision_index,delivery_ref,CASE WHEN form IS NOT NULL AND failure IS NULL THEN "admitted" ELSE "failed_or_pending" END AS state FROM runtime_report_attempts')]}
db.close()
print(json.dumps(result, indent=2))
