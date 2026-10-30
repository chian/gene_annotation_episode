"""Cold, read-only validation of the final ORIGINAL public caller return.

No Workflow, provider, scientific reader, calculator, acquisition or form factory
is called. Original source/artifact/provider bodies are not read. This verifies
the saved public return and original declared relationships, not source science.
"""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

HERE = Path(__file__).resolve().parent
PIN = HERE/'source_pin_001'
sys.path.insert(0, str(PIN))

from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.episode_contract_information import validate_saved_fact_form
from gene_annotation_episode.literature_a105_worksheet import validate_a105_worksheet_links

prepared = json.loads((HERE/'configured_001/prepared_caller.json').read_text())
expected = next(r['sha256'] for r in json.loads((HERE/'ENTRYPOINT_PIN_002.json').read_text())['files']
    if r['path'] == 'configured_001/prepared_caller.json')
assert hashlib.sha256((HERE/'configured_001/prepared_caller.json').read_bytes()).hexdigest() == expected
db_path = HERE/'configured_001/state/state.sqlite3'
db = sqlite3.connect('file:'+str(db_path)+'?mode=ro', uri=True)
db.row_factory = sqlite3.Row
before = db.total_changes
run = db.execute('SELECT state FROM runtime_runs WHERE run_id=?', (prepared['run_id'],)).fetchone()
if run is None or run[0] not in ('yielded', 'yielded_with_pending_work'):
    print(json.dumps({'status': 'final_return_not_available', 'run_state': None if run is None else run[0],
        'writes': 0, 'scientific_io': False, 'meaning': 'No final typed return was validated or manufactured.'}))
    raise SystemExit(2)
root = db.execute('SELECT episode_id,request FROM runtime_episodes WHERE run_id=? AND path=?',
    (prepared['run_id'], '[["annotation","root"]]')).fetchone()
request = json.loads(root['request'])
schema = request['report_contract']['measurements']['schema']
assert schema == prepared['expanded_form']
assert request['message']['episode_assignment'] == prepared['assignment']
validate_saved_fact_form(child_role='annotation',
    submitted_schema_json=prepared['contract_declaration']['submitted_schema_json'],
    expanded_schema=schema, declaration=prepared['contract_declaration'])
row = db.execute('SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?',
    (prepared['run_id'], root['episode_id'])).fetchone()
assert row is not None and row[0] is not None
form = json.loads(row[0])
assert form == json.loads((HERE/'PUBLIC_TYPED_RETURN_002.json').read_text())
known = {r[0] for r in db.execute('SELECT record_ref FROM runtime_record_receipts WHERE run_id=? AND episode_id=?',
    (prepared['run_id'], root['episode_id']))}

def public_record(ref):
    if ref not in known:
        return None
    row = db.execute('SELECT record_type,origin,data FROM records WHERE id=?', (ref,)).fetchone()
    return None if row is None else {'id': ref, 'record_type': row[0], 'origin': row[1], **json.loads(row[2])}

def resolve(ref, namespace=None):
    row = public_record(ref)
    return bool(row is not None and (namespace is None or row['record_type'] == namespace))

validate_form(form, schema, resolve)
validate_a105_worksheet_links(form, schema, prepared['assignment'], read_public_record=public_record)
received = {}
for field, table in (('native_parameter', 'literature_kinetic_received'),
                     ('precision', 'literature_kinetic_summary_precision_received')):
    values, seen = [], set()
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
        for row in db.execute('SELECT cells FROM '+table+' WHERE run_id=? AND episode_id=? ORDER BY rowid',
                (prepared['run_id'], root['episode_id'])):
            for cell in json.loads(row[0]):
                key = cell['sheet_ref'], cell['component']
                if key not in seen:
                    seen.add(key)
                    values.append(cell)
    assert values == form[field]
    received[field] = len(values)
assert db.total_changes == before == 0
print(json.dumps({'status': 'validated_original_saved_public_return',
    'original_schema_and_assignment_equal': True, 'exact_received_row_counts': received,
    'worksheet_relationships_valid': True, 'sqlite_changes': 0,
    'scientific_readers_calculators_acquisition_model_calls': 0,
    'private_provider_or_source_artifact_bodies_read': False,
    'scope': 'Cold original-contract/public-return reconstruction only; no source reevaluation or whole-goal completion.'}, indent=2))
db.close()
