"""Independent persisted-output audit; no scientific reader/calculator or restart."""
import hashlib
import json
from pathlib import Path
import sqlite3

HERE = Path(__file__).resolve().parent
PIN = HERE / 'pin_003'
RUN = HERE / 'run_003'

def load(path): return json.loads(path.read_bytes())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    for name, row in load(PIN / 'PIN_MANIFEST.json').items():
        path = PIN / name
        assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes']
        assert path.stat().st_mode & 0o222 == 0
    terminal = load(RUN / 'TERMINAL_RECEIPT.json'); assert terminal['passed']
    selected = load(RUN / 'SELECTED_RECEIPT.json'); c4 = load(RUN / 'C4_RECEIPT.json')
    rows = load(RUN / 'SELECTED_NATIVE_ROWS.json'); assert len(rows) == 16
    sql = {}
    for name, count in (('selected_state', 4), ('c4_state', 0)):
        db = sqlite3.connect((RUN / name / 'state.sqlite3').resolve().as_uri()+'?mode=ro', uri=True)
        try:
            before = list(db.iterdump())
            assert db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == count
            actions = db.execute('SELECT decision_index,action,result,credit FROM runtime_actions ORDER BY rowid').fetchall()
            assert all(row[3] == 0 for row in actions)
            attempts = db.execute('SELECT form,failure FROM runtime_report_attempts ORDER BY rowid').fetchall()
            assert len(attempts) == 1 and attempts[0][1] is None
            form = json.loads(attempts[0][0])
            assert len(form['numbers']) == (16 if name == 'selected_state' else 1)
            assert list(db.iterdump()) == before
            sql[name] = {'actual_observations': count, 'actual_actions': len(actions),
                         'successful_original_parent_forms': len(attempts), 'typed_rows': len(form['numbers']),
                         'whole_sql_sha256': hashlib.sha256('\n'.join(before).encode()).hexdigest()}
        finally: db.close()
    assert selected['read_only_reconstruction']['whole_sql_unchanged']
    assert c4['read_only_replay']['original_C4_replay']
    receipt = {'passed': True, 'scope': 'Independent file/ordinary action/original form/read-only SQL audit; no new scientific processing',
        'immutable_pin_verified': True, 'sql': sql, 'actual_model_called': False,
        'selected_and_C4_fixture_distinguished': True}
    with (HERE / 'AUDIT_003.json').open('x') as stream:
        json.dump(receipt, stream, indent=2); stream.write('\n')
    print(json.dumps(receipt))

if __name__ == '__main__':
    main()
