"""Copy numerical evidence from closed test Stores; perform no regrading."""
import hashlib
import json
from pathlib import Path
import sqlite3

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TEMP = HERE / 'run_002/temporary'
MEDIA = 'application/vnd.gene-annotation.tool-grading+json'
cases = [
    ('native_pairwise_duplicate_positions', 'test_reference_position_set_fi0/state', 1),
    ('offline_synthetic_blast_reverse_window', 'test_blast_original_receipt_mu0/store', 3),
    ('native_minimap2_forward_quality', 'test_actual_mapping_read_prese0/state', 0),
    ('native_minimap2_reverse_quality', 'test_actual_mapping_read_prese1/state', 0),
    ('retained_explicit_grading_failure', 'test_actual_retained_grader_fa0/state', 0),
    ('actual_empty_blast_window', 'test_blast_empty_window_and_le0/store', 1),
    ('simulated_legacy_read_without_grading', 'test_blast_empty_window_and_le0/store', 2),
]
examples = []
for label, subpath, decision_index in cases:
    directory = TEMP / subpath
    connection = sqlite3.connect('file:' + str(directory / 'state.sqlite3') + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    def record(reference):
        return json.loads(connection.execute('SELECT data FROM records WHERE id=?', (reference,)).fetchone()[0])
    def artifact(reference):
        row = connection.execute('SELECT sha256 FROM artifacts WHERE id=?', (reference,)).fetchone()
        body = (directory / 'artifacts' / row['sha256'][:2] / row['sha256']).read_bytes()
        assert hashlib.sha256(body).hexdigest() == row['sha256']
        return json.loads(body)
    row = connection.execute('SELECT action,result FROM runtime_actions WHERE decision_index=?', (decision_index,)).fetchone()
    action, outcome = json.loads(row['action']), json.loads(row['result'])
    result = outcome['result']
    if action['tool'] == 'sequence.sites':
        source = record(result['source_ref'])
        pointers = [ref for ref in source['auxiliary_artifact_refs'] if connection.execute(
            'SELECT media_type FROM artifacts WHERE id=?', (ref,)).fetchone()[0] == MEDIA]
        pointer, = pointers
    else:
        pointer = result.get('site_grading_artifact_ref')
    examples.append({'label': label, 'fixture_store': str(directory.relative_to(ROOT)),
        'decision_index': decision_index, 'selected_action': action, 'actual_outcome': outcome,
        'grading_artifact_ref': pointer, 'grading_envelope': artifact(pointer) if pointer else None})
    connection.close()
destination = HERE / 'FILLED_EXAMPLES_001.json'
destination.write_text(json.dumps({'schema': 'alignment_site_host_examples_v1', 'examples': examples},
    indent=2, allow_nan=False) + '\n')
print(json.dumps({'examples': len(examples), 'path': str(destination),
    'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}))
