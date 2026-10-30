"""Only process identity and public row counts; never source/model contents."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

BASE = Path(__file__).resolve().parents[1]
rows = {}
for label, start in (('024', '82830508'), ('030', '83497104')):
    live = BASE / f'literature_model_run_{label}/live_001'
    pid = json.loads((live / 'PROCESS.json').read_text())['pid']
    stat = Path('/proc') / str(pid) / 'stat'
    fields = stat.read_text().rsplit(')', 1)[1].split() if stat.exists() else None
    process = {'pid': pid, 'handle_present': fields is not None,
               'state': fields[0] if fields else None,
               'original_start_ticks_match': bool(fields and fields[19] == start)}
    with sqlite3.connect((live / 'state/state.sqlite3').resolve().as_uri() + '?mode=ro', uri=True) as db:
        db.execute('PRAGMA query_only=on')
        db.execute('BEGIN')
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        names = ('runtime_actions', 'runtime_observations', 'runtime_forms', 'runtime_report_attempts',
                 'runtime_model_calls', 'literature_rate_operations', 'literature_rate_source_received')
        counts = {name: db.execute('SELECT count(*) FROM ' + name).fetchone()[0]
                  for name in names if name in tables}
        readonly = {'query_only': db.execute('PRAGMA query_only').fetchone()[0], 'total_changes': db.total_changes}
        assert readonly == {'query_only': 1, 'total_changes': 0}
    rows[label] = {'process': process, 'counts': counts, 'readonly': readonly,
                   'terminal_result_file_present': (live / 'RESULT.json').is_file()}
result = {'utc': datetime.now(timezone.utc).isoformat(), 'scope': 'Original handles and public counts only; no scientific operands, model/provider records, restart or mutation', 'runs': rows}
with (Path(__file__).resolve().parent / 'ORIGINAL_HANDLES_054.json').open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result))
