"""Read bounded public progress; never acquire prompts/provider histories."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys

HERE = Path(__file__).resolve().parent


def main():
    name = sys.argv[1]
    assert name.startswith('LIVE_BOUNDARY_') and name.endswith('.json') and '/' not in name
    launch = json.loads((HERE / 'LAUNCH_RECEIPT_007.json').read_bytes())
    live = Path(launch['directory'])
    stat = Path('/proc') / str(launch['pid']) / 'stat'
    fields = stat.read_text().rsplit(')', 1)[1].split() if stat.exists() else None
    process = {'pid': launch['pid'], 'handle_present': fields is not None,
        'state': fields[0] if fields else None,
        'start_ticks_match': bool(fields and fields[19] == launch['start_ticks'])}
    registered = (live / 'PROCESS.json').exists()
    if registered:
        assert json.loads((live / 'PROCESS.json').read_bytes())['pid'] == launch['pid']
    state = live / 'state/state.sqlite3'
    counts, categories, statuses, codes = {}, Counter(), Counter(), Counter()
    readonly = None
    if state.is_file():
        with sqlite3.connect(state.resolve().as_uri() + '?mode=ro', uri=True) as db:
            db.execute('pragma query_only=on'); db.execute('begin')
            tables = {row[0] for row in db.execute("select name from sqlite_master where type='table'")}
            names = ('runtime_runs', 'runtime_episodes', 'runtime_actions', 'runtime_observations',
                'runtime_model_calls', 'runtime_forms', 'runtime_report_attempts', 'runtime_decision_exchanges',
                'literature_rate_operations', 'literature_rate_source_received',
                'literature_partner_operations', 'literature_partner_received')
            counts = {table: db.execute('select count(*) from ' + table).fetchone()[0]
                      for table in names if table in tables}
            if 'runtime_actions' in tables:
                for tool, kind, status, code in db.execute("""select
                    json_extract(action,'$.tool'), json_extract(action,'$.type'),
                    json_extract(result,'$.status'), json_extract(result,'$.feedback.code')
                    from runtime_actions order by rowid"""):
                    categories[tool or kind or 'other'] += 1
                    statuses[status or 'none'] += 1
                    if code:
                        codes[code] += 1
            readonly = {'query_only': db.execute('pragma query_only').fetchone()[0],
                        'total_changes': db.total_changes}
    row = {'utc': datetime.now(timezone.utc).isoformat(), 'process': process,
        'runner_registered': registered, 'terminal_result_file_present': (live / 'RESULT.json').is_file(),
        'counts': counts, 'action_categories': dict(categories), 'action_statuses': dict(statuses),
        'public_feedback_codes': dict(codes), 'readonly': readonly,
        'scope': 'Process identity/counts/public action categories only; no model content, scientific operands, source read or runtime mutation'}
    with (HERE / name).open('x') as stream:
        json.dump(row, stream, indent=2); stream.write('\n')
    print(json.dumps(row))


if __name__ == '__main__':
    main()
