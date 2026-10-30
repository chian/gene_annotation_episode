"""Bounded public selected-action/database observation; no provider histories."""
from pathlib import Path
from datetime import datetime,timezone
import json,sqlite3
BASE=Path(__file__).resolve().parents[1]
PID=1614626
stat=Path('/proc')/str(PID)/'stat'
process={'pid':PID,'handle_present':stat.exists()}
if stat.exists():
    fields=stat.read_text().rsplit(')',1)[1].split()
    process.update(state=fields[0],start_ticks=fields[19])
path=BASE/'literature_model_run_024/live_001/state/state.sqlite3'
with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
    db.row_factory=sqlite3.Row
    db.execute('begin')
    tables={r[0] for r in db.execute("select name from sqlite_master where type='table'")}
    counts={t:db.execute('select count(*) from '+t).fetchone()[0] for t in
        ['runtime_actions','runtime_observations','runtime_report_attempts','runtime_forms',
         'literature_rate_operations','literature_rate_source_received'] if t in tables}
    attempts=[]
    for row in db.execute("select run_id,episode_id,decision_index,action,result,credit from runtime_actions where json_extract(action,'$.tool')='literature.rate.source.populate' order by decision_index"):
        result=json.loads(row['result']) if row['result'] else None
        attempts.append({'run_id':row['run_id'],'episode_id':row['episode_id'],
            'decision_index':row['decision_index'],'status':None if result is None else result['status'],
            'error_code':None if result is None else (result.get('feedback') or {}).get('code'),
            'credit':row['credit']})
    model_count=db.execute('select count(*) from runtime_model_calls').fetchone()[0] if 'runtime_model_calls' in tables else None
report={'written_utc':datetime.now(timezone.utc).isoformat(),'process':process,'counts':counts,
        'selected_native_population_attempts':attempts,'recorded_model_call_count':model_count,
        'terminal_result_file_present':(BASE/'literature_model_run_024/live_001/RESULT.json').exists(),
        'numerical_population_proved':bool(counts.get('literature_rate_operations')),
        'meaning':'Recorded public action and runtime state only; no source scientific interpretation, model/provider history or execution-token inspection. Existing run and pin unchanged.'}
with (BASE/'NATIVE_RATE_ATTEMPT_BOUNDARY_030.json').open('x') as stream:
    json.dump(report,stream,indent=2);stream.write('\n')
print(json.dumps(report))
