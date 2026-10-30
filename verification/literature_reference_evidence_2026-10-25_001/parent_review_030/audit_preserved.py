"""Read-only operational checks of previously reviewed scientific assignments."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sqlite3

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'verification/literature_reference_evidence_2026-10-25_001'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(name):
    return json.loads((BASE / name).read_bytes())

def check_db(path, expected, families):
    before = sha(path)
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        db.row_factory = sqlite3.Row
        assert db.execute('pragma integrity_check').fetchone()[0] == 'ok'
        rows = {table: [dict(row) for row in db.execute('select * from ' + table)]
                for table in ['runtime_actions', 'runtime_observations', 'runtime_forms', *families]}
        for actual, reported in expected.items():
            json_columns = {key for row in reported for key, value in row.items()
                            if isinstance(value, (dict, list))}
            normalized = [{key: json.loads(value) if key in json_columns and isinstance(value, str) else value
                           for key, value in row.items()} for row in rows[actual]]
            ordered = lambda values: sorted(json.dumps(row, sort_keys=True) for row in values)
            assert ordered(normalized) == ordered(reported), actual
        invalid = [row for row in rows['runtime_actions']
                   if json.loads(row['result'])['status'] == 'invalid']
        assert all(row['credit'] is None for row in invalid)
        forms = [json.loads(row['form']) for row in rows['runtime_forms']]
        assert len(forms) == 1
        returned = next(iter(forms[0].values()))
        received = [json.loads(row['cells']) for row in rows[families[-1]]]
        assert received == [returned]
        outcome = {'database_sha256': before, 'integrity': 'ok',
            'counts': {key: len(value) for key, value in rows.items()},
            'invalid_actions_with_null_credit': len(invalid),
            'returned_components': [row['component'] for row in returned],
            'cells': [{key: row.get(key) for key in ['component', 'value', 'unit', 'unavailable_reason',
                         'threshold', 'bound', 'approximate']} for row in returned],
            'typed_form_equals_received_subset': True,
            'original_run_ids': sorted({row['run_id'] for row in rows['runtime_actions']})}
    assert sha(path) == before
    return outcome

proof = read('witness_repair_feedback_030/CONTROLLED_REPAIR_EVIDENCE.json')
fixture = BASE / 'witness_repair_feedback_030/controlled_repair_fixture_001'
for row in proof['files']:
    path = fixture / row['relative_path']
    assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
repair = check_db(fixture / 'state/state.sqlite3', {
    'runtime_actions': proof['actions'], 'runtime_observations': proof['observation_rows'],
    'runtime_forms': proof['typed_forms']}, ['literature_rate_operations', 'literature_rate_source_received'])
assert repair['counts']['runtime_actions'] == 4
assert repair['counts']['runtime_observations'] == 3
assert repair['invalid_actions_with_null_credit'] == 1
assert repair['returned_components'] == ['rate_difference', 'difference_se']
repair['preserved_files_verified'] = len(proof['files'])

nominal = read('numeric_range_scope_029/CONTROLLED_NOMINAL_DEMO_004.json')
nominal_db = BASE / 'numeric_range_scope_029/controlled_original_nominal_004/state/state.sqlite3'
amount = check_db(nominal_db, {key: nominal[key] for key in
    ['runtime_actions', 'runtime_observations', 'runtime_forms']},
    ['literature_amount_operations', 'literature_amount_received'])
assert amount['counts']['runtime_actions'] == amount['counts']['runtime_observations'] == 3
assert amount['invalid_actions_with_null_credit'] == 0
assert len(amount['returned_components']) == 7

manifests = ['amount_components_027/SOURCE_MANIFEST_002.json',
             'numeric_range_scope_029/SOURCE_MANIFEST_003.json',
             'witness_repair_feedback_030/SOURCE_MANIFEST_FINAL.json']
final, provenance = {}, []
for relative in manifests:
    data = read(relative)
    entries = data if isinstance(data, list) else data['files']
    provenance.append({'path': relative, 'sha256': sha(BASE / relative)})
    for entry in entries:
        final[entry['path']] = entry['sha256']
divergences = []
for relative, digest in final.items():
    current = sha(ROOT / relative)
    if current != digest:
        assert relative == 'gene_annotation_episode/episode_services.py', relative
        divergences.append({'path': relative, 'reviewed_sha256': digest, 'current_sha256': current,
            'resolution': 'preserve shared main; reconstruct reviewed snapshot from exact patches'})

report = {'written_utc': datetime.now(timezone.utc).isoformat(),
    'meaning': 'Independent read-only operational review of preserved controlled runtime records; no new paper interpretation, acquisition, model choice, replay or scientific credit',
    'source_manifests': provenance, 'reviewed_owned_files': len(final),
    'current_owned_files_matching_reviewed': len(final) - len(divergences),
    'current_shared_divergences': divergences,
    'repair_fixture': repair, 'nominal_fixture': amount,
    'read_scope_correction': {
        'previous_large_nominal_json_read': 'truncated; not a complete read',
        'this_check': 'full JSON loaded by program; only operational fields/relationships inspected, not full scientific source packet reread',
        'previous_multi_file_reads': 'some aggregate outputs truncated; no complete-read claim for those outputs',
        'new_primary_scientific_interpretation': False},
    'audit_harness_corrections': ['decode explicitly expanded JSON columns and compare rows independent of SQL order', 'detect and preserve later shared-file divergence rather than replacing it'],
    'full_goal_complete': False}
output = BASE / 'SOURCE_REPAIR_AND_SCOPE_PARENT_REVIEW_030.json'
with output.open('x') as stream:
    json.dump(report, stream, indent=2, allow_nan=False)
    stream.write('\n')
print(json.dumps({'report': str(output), 'owned_files': len(final),
    'repair_counts': repair['counts'], 'nominal_counts': amount['counts']}))
