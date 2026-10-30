"""Read only the NEW active run's first public context and initial receipts."""
from pathlib import Path
import hashlib
import json
import os
import sqlite3

run = Path('/home/chia/gene_annotation_episode_runs/configured_api_prechoice_001')
run_id = json.loads((run / 'run.json').read_text())['run_id']
parameters = json.loads((run / 'caller-inputs/parameters.json').read_text())
selected = set(parameters['policy']['scientific_progress']['initial_known_record_refs'])
committed = json.loads((run / 'workspace/checkpoint/committed-references.json').read_text())
committed_refs = {row['reference'] for row in committed['records']}
connection = sqlite3.connect((run / 'workspace/state.sqlite3').as_uri() + '?mode=ro', uri=True)
connection.row_factory = sqlite3.Row
try:
    connection.execute('PRAGMA query_only=ON')
    connection.execute('BEGIN')
    root = dict(connection.execute('SELECT episode_id,path,state,initial_credit FROM runtime_episodes '
        'WHERE run_id=? AND path=?', (run_id, '[["annotation","root"]]')).fetchone())
    first = connection.execute('SELECT request FROM runtime_model_calls '
        'WHERE run_id=? AND episode_id=? AND call_index=0', (run_id, root['episode_id'])).fetchone()
    request = json.loads(first['request'])
    context, presentation = request['context'], request['model_presentation']
    presented = presentation['context']
    for value in (context, presented):
        assert value['controller']['scores'] == []
        assert value['controller']['estimate']['turns'] == 0
        assert value['controller']['initial_credit'] == value['current_credit'] == root['initial_credit'] == 12.0
        assert value['monitoring_information_credit'] == 0.0
    received = {row[0] for row in connection.execute('SELECT record_ref FROM runtime_record_receipts '
        'WHERE run_id=? AND episode_id=? AND receipt_kind=?', (run_id, root['episode_id'], 'initial'))}
    assert len(selected) == 200 and len(committed_refs) == 193 and committed_refs <= received
    paged = []
    for reference in sorted(selected - received):
        row = connection.execute('SELECT data FROM material_members WHERE id=?', (reference,)).fetchone()
        assert row is not None
        member = json.loads(row['data'])
        assert member['record_type'] == 'collection_member'
        parents = {member[key] for key in ('collection_ref', 'material_ref', 'source_ref')}
        assert parents <= received
        paged.append({'reference': reference, 'record_type': 'collection_member',
                      'known_parent_refs': sorted(parents),
                      'meaning': 'Existing paged collection-member access; EpisodeReceipts.receive deliberately skips member rows.'})
    assert len(selected & received) == 199 and len(paged) == 1
    native = {row[0] for row in connection.execute("SELECT id FROM records WHERE record_type='native_execution'")}
    # Only the checkpoint's four old receipts belong in this inherited baseline;
    # later selected work can add new receipts while this operator reads.
    inherited_native = native & committed_refs
    assert len(inherited_native) == 4 and inherited_native <= received
    counts = {table: connection.execute('SELECT count(*) FROM ' + table + ' WHERE run_id=?',
              (run_id,)).fetchone()[0] for table in
              ('runtime_episodes', 'runtime_actions', 'runtime_observations',
               'runtime_model_calls', 'runtime_commission_intents')}
    actions = []
    for row in connection.execute('SELECT decision_index,action,result,credit FROM runtime_actions '
                                  'WHERE run_id=? ORDER BY decision_index', (run_id,)):
        action = json.loads(row['action'])
        result = json.loads(row['result']) if row['result'] else None
        feedback = result.get('feedback') if result else None
        actions.append({'index': row['decision_index'], 'kind': action['kind'],
                        'tool': action.get('tool'), 'credit': row['credit'],
                        'feedback_code': feedback.get('code') if feedback else None})
    record = {'version': 'actual_configured_initial_baseline_snapshot_v1',
        'run_id': run_id, 'root_episode': root,
        'first_saved_request': {'raw_utf8_sha256': hashlib.sha256(first['request'].encode()).hexdigest(),
                               'raw_utf8_bytes': len(first['request'].encode()),
                               'request_version': request['version']},
        'first_model_presentation': {key: value for key, value in presentation.items()
                                     if key != 'context'},
        'initial_controller_scores': [], 'initial_completed_own_turns': 0,
        'initial_scientific_progress': 12.0, 'initial_monitoring_information_credit': 0.0,
        'initial_annotation_evidence_vector': context['annotation_evidence_vector'],
        'initial_investigation_progress': context['investigation_progress'],
        'selected_inherited_refs': 200, 'committed_refs_initially_received': 193,
        'selected_refs_initially_receipted': 199,
        'initial_receipts_including_dependencies': len(received),
        'inherited_native_receipts': sorted(inherited_native), 'paged_members': paged,
        'snapshot_counts': counts, 'selected_action_summary': actions,
        'prior_operator_assertion': 'An earlier inline check incorrectly required all200 selected refs in runtime_record_receipts. It failed before writing any proof. The sole excluded member is intentionally served through the existing paged interface; no runtime or source change was made. Raw tool output was not separately captured as a file.',
        'access': 'Readonly NEW active workspace only; no original source, Store or private provider events.',
        'claim_limit': 'Actual configured decisions and initial baseline. Useful scientific child return and whole-goal completion are not established by this snapshot.'}
finally:
    connection.close()
target = run / 'caller-inputs/INITIAL_BASELINE_SNAPSHOT001.json'
with target.open('x') as stream:
    stream.write(json.dumps(record, sort_keys=True, indent=2, allow_nan=False) + '\n')
    stream.flush()
    os.fsync(stream.fileno())
target.chmod(0o400)
directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
try:
    os.fsync(directory)
finally:
    os.close(directory)
print(json.dumps({'saved': str(target), 'run_id': run_id,
                  'initial_scientific_progress': 12.0, 'initial_own_turns': 0,
                  'selected_inherited_refs': 200, 'selected_refs_initially_receipted': 199,
                  'retained_paged_members': 1, 'snapshot_counts': counts}, sort_keys=True))
