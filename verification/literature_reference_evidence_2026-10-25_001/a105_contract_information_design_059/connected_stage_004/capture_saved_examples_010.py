"""Export only already recorded invented fixtures through read-only SQLite."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

STAGE = Path(__file__).absolute().parent
PIN = STAGE / 'pin_010'
OUT = STAGE / 'checks_010'
sys.path.insert(0, str(PIN))
from gene_annotation_episode.providers import _SessionConnection


def save(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2); stream.write('\n')


def open_db(name):
    path, = (OUT / 'pytest_work').glob(name + '/state/state.sqlite3')
    db = sqlite3.connect(path.absolute().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    return path, db


def records(db, table):
    return [dict(row) for row in db.execute('SELECT * FROM ' + table)]


path, db = open_db('test_interrupted_pending_decis0')
connection = _SessionConnection.__new__(_SessionConnection)
connection.scientific_prompt_states = {}
public, rendered = [], []
for row in db.execute('SELECT * FROM runtime_decision_exchanges ORDER BY decision_index,exchange_index'):
    request = json.loads(row['request'])
    display, instructions = connection._presentation(row['episode_id'], 'REASONING', request['instructions'], request['context'])
    target = 'PUBLIC_TASK_STEERING_EXCHANGE_' + str(row['exchange_index']) + '_010.txt'
    with (OUT / target).open('x') as stream: stream.write(display)
    public.append({'exchange_index': row['exchange_index'],
        'response': None if row['response'] is None else json.loads(row['response']),
        'lookup_result': None if row['lookup_result'] is None else json.loads(row['lookup_result']),
        'original_request_sha256': hashlib.sha256(row['request'].encode()).hexdigest(),
        'original_context_kind': request['context']['kind'], 'rendered_text': target})
assert len(public) == 5
assert all('Requested operation/return information: literature.binding.interaction.populate' in
    (OUT / public[i]['rendered_text']).read_text() for i in (2, 3, 4))
save('SAVED_PENDING_EXCHANGES_010.json', {'fixture': str(path.relative_to(STAGE)),
    'mode': 'ro', 'public': public, 'runtime_actions': len(records(db, 'runtime_actions')),
    'runtime_observations': len(records(db, 'runtime_observations')), 'scientific_model_calls': 0})
db.close()
examples = []
for fixture in ('test_original_c1_c4_compact_fo0', 'test_parent_owns_selected_form0', 'test_parent_owns_selected_form1'):
    path, db = open_db(fixture)
    tables = ['runtime_episodes', 'runtime_actions', 'runtime_forms', 'runtime_observations',
        'runtime_commission_intents', 'literature_kinetic_operations', 'literature_kinetic_received',
        'literature_kinetic_delivery_bindings']
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_return_admissions'").fetchone():
        tables.append('runtime_return_admissions')
    examples.append({'fixture': str(path.relative_to(STAGE)), 'mode': 'ro',
        'tables': {table: records(db, table) for table in tables}})
    db.close()
save('ACTUAL_SYNTHETIC_CUSTODY_ROWS_010.json', examples)
print(json.dumps({'public_exchanges': len(public), 'custody_examples': len(examples),
                  'mode': 'ro', 'new_model_calls': 0, 'new_actions': 0, 'new_observations': 0}))
