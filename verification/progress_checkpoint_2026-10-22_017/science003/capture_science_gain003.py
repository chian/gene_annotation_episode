"""Read selected public facts from the explicitly scoped NEW active run only.

Stdlib SQLite mode=ro/query_only/BEGIN; never imports Store or an application,
opens an old scientific DB, reads provider files, projects a score or calls a
model/service/native process. Exact selected TEXT and public result bytes are
retained in this new temporary proof directory, never in the active workspace.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
from urllib.parse import quote


OUTPUT = Path(__file__).absolute().parent
ACTIVE = Path('/home/chia/gene_annotation_episode_runs/configured_api_prechoice_001')
DATABASE = ACTIVE/'workspace/state.sqlite3'
PRIOR = Path('/tmp/configured-caller-actual-science-20261022-002')
RUN_ID = 'run_23b029a976e343e2bf3957dcc5d0d2ac'
EPISODE_ID = 'episode_3f296d8c6dbd96a740157d29eceda747dd4cc7b19d97b4763735999fe99b1979'
ASSESSMENT = 'assessment_40b9f1991d5139c31739e6fd'
SOURCE = 'source_827720648609fb105f7af587'
OBSERVATION = 'observation_3971ded7cade6cc8aeae3788'
REFERENCE = 'reference_08a1efd2c6cbb8e40a053a31'
ANNOTATION = 'annotation_d119928935b17e0260a7c2dd'
RECORDS = [ASSESSMENT, SOURCE, OBSERVATION, REFERENCE, ANNOTATION,
    'context_8d22034762de8ef95506b280', 'term_5f0910bfdf9799ca5b5781ab',
    'hypothesis_c8c174d0b7c4cc862723f8b2', 'term_1f995b3c0cc9bd6e5caad493',
    'assessment_2a06237e8cdc683a7c0eeff5', 'assessment_bf30b5213fa3a24a42a20e93',
    'context_10fbca90ff6c6ecdeb5e3468', 'reference_de93d8f10f1d30740c09f5a5']
SQL = []


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def metadata(path):
    try:
        value = path.lstat()
    except FileNotFoundError:
        return {'path': str(path), 'absent': True}
    return {'path': str(path), 'bytes': value.st_size,
        'mode': f'{stat.S_IMODE(value.st_mode):04o}', 'mtime_ns': value.st_mtime_ns,
        'inode': value.st_ino, 'device': value.st_dev}


def read_regular(path):
    before = metadata(path)
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError('selected artifact/authority is not a regular file')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            body = stream.read()
    finally:
        os.close(fd)
    after = metadata(path)
    if before != after or len(body) != before['bytes']:
        raise ValueError('selected immutable public input changed during read')
    return body, {'before': before, 'after': after, 'sha256': sha(body)}


def write(member, data):
    path = OUTPUT/member
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return {'member': member, 'sha256': sha(data), 'bytes': len(data)}


def write_json(member, value):
    return write(member, (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False) + '\n').encode('utf-8'))


def main():
    prior_bytes, prior_witness = read_regular(PRIOR/'SCIENCE_GAIN002.json')
    prior = json.loads(prior_bytes)
    prior_manifest, prior_manifest_witness = read_regular(PRIOR/'MANIFEST002.json')
    assert sha(prior_manifest) == '22c401ba3d8e6410577f80655b82eb55609233c90b78e4ec0781b9ce033e41ce'
    assert prior['run_id'] == RUN_ID and prior['episode_id'] == EPISODE_ID
    watched = [DATABASE, Path(str(DATABASE)+'-wal'), Path(str(DATABASE)+'-shm')]
    before = {path.name: metadata(path) for path in watched}
    transaction_started, connection, closed = utc(), None, False
    rows, queries, artifacts, saved_contexts = {}, {}, {}, {}
    try:
        connection = sqlite3.connect('file:' + quote(str(DATABASE), safe='/') + '?mode=ro', uri=True)
        connection.row_factory = sqlite3.Row
        connection.set_trace_callback(SQL.append)
        connection.execute('PRAGMA query_only=ON')
        assert connection.execute('PRAGMA query_only').fetchone()[0] == 1
        connection.execute('BEGIN')
        assert connection.in_transaction and connection.total_changes == 0
        counts = {table: connection.execute('SELECT count(*) FROM '+table+' WHERE run_id=?',
            (RUN_ID,)).fetchone()[0] for table in ('runtime_actions', 'runtime_observations',
                'runtime_episodes', 'runtime_commission_intents', 'runtime_model_calls')}
        selected_actions = {}
        for index in (35, 37, 38, 39, 40, 41):
            value = dict(connection.execute('SELECT * FROM runtime_actions WHERE run_id=? '
                'AND episode_id=? AND decision_index=?', (RUN_ID, EPISODE_ID, index)).fetchone())
            selected_actions[str(index)] = value
        observations = [dict(row) for row in connection.execute(
            'SELECT * FROM runtime_observations WHERE run_id=? AND episode_id=? ORDER BY unit_index',
            (RUN_ID, EPISODE_ID))]
        after = [row for row in observations if json.loads(row['observation'])['decision_index'] > 34]
        assert any(json.loads(row['observation'])['decision_index'] == 39
            and json.loads(row['observation'])['step']['marginal_credit'] == 1.0 for row in after)
        for reference in RECORDS:
            value = connection.execute('SELECT * FROM records WHERE id=?', (reference,)).fetchone()
            assert value is not None
            rows[reference] = dict(value)
        receipts = [dict(row) for row in connection.execute(
            'SELECT * FROM runtime_record_receipts WHERE run_id=? AND episode_id=? '
            'AND record_ref IN (' + ','.join('?' for _ in RECORDS) + ') ORDER BY receipt_index',
            (RUN_ID, EPISODE_ID, *RECORDS))]
        for index in (35, 39, 40, 41):
            row = connection.execute('SELECT call_index,purpose,request,response FROM runtime_model_calls '
                'WHERE run_id=? AND episode_id=? AND call_index=?', (RUN_ID, EPISODE_ID, index)).fetchone()
            assert row is not None
            request = row['request'].encode('utf-8')
            queries[str(index)] = {'call_index': index, 'purpose': row['purpose'],
                'response_recorded': row['response'] is not None,
                'original_request': write('public-saved-requests/call-'+str(index)+'.json', request)}
            request_body = json.loads(request)
            contexts = {'raw': request_body['context'],
                'model': request_body['model_presentation']['context']}
            saved_contexts[str(index)] = contexts
        source = json.loads(rows[SOURCE]['data'])
        artifact = source['artifact_ref']
        artifact_row = dict(connection.execute('SELECT * FROM artifacts WHERE id=?', (artifact,)).fetchone())
        assert artifact_row['media_type'] == 'application/json'
        path = ACTIVE/'workspace/artifacts'/artifact_row['sha256'][:2]/artifact_row['sha256']
        body, witness = read_regular(path)
        assert sha(body) == artifact_row['sha256'] and len(body) == artifact_row['size']
        artifacts[artifact] = {'source_ref': SOURCE, 'metadata': artifact_row,
            'original': witness, 'copy': write('public-artifacts/'+artifact_row['sha256']+'.json', body)}
        captured = utc()
        assert connection.total_changes == 0 and connection.in_transaction
    finally:
        if connection is not None:
            connection.rollback()
            connection.close()
            closed = True
    after_metadata = {path.name: metadata(path) for path in watched}
    witness = {'uri': 'file:' + str(DATABASE) + '?mode=ro', 'query_only': True,
        'explicit_begin': True, 'transaction_started_at': transaction_started,
        'snapshot_payload_captured_at': captured, 'connection_closed_at': utc(),
        'finally_rollback_and_close': closed, 'sqlite_total_changes': 0,
        'active_files_before': before, 'active_files_after': after_metadata,
        'whole_database_hash_or_unchanged_claim': False,
        'concurrency_limit': 'WAL files may grow through the independent active run; selected rows belong to one SQLite read snapshot.',
        'sql_statements': SQL}
    write_json('PUBLIC_DATABASE_ROWS003.json', {'records': rows, 'selected_actions': selected_actions,
        'observations_after_decision34': after, 'record_receipts': receipts,
        'counts_for_actual_new_run_only': counts, 'original_text_sha256': {
            'record_data': {ref: sha(row['data'].encode()) for ref, row in rows.items()},
            'observation': {str(row['unit_index']): sha(row['observation'].encode()) for row in after}}})
    write_json('READONLY_DATABASE_WITNESS003.json', witness)
    observations_by_decision = {json.loads(row['observation'])['decision_index']:
        json.loads(row['observation']) for row in after}
    contexts = {}
    for index, views in saved_contexts.items():
        contexts[index] = {'original_request': queries[index], 'views': {}}
        for label, value in views.items():
            contexts[index]['views'][label] = {
                'current_credit': value.get('current_credit'),
                'retained_finding_count': value.get('investigation_progress', {}).get('retained_finding_count'),
                'annotation_score': value.get('annotation_score'),
                'annotation_evidence_vector': value.get('annotation_evidence_vector'),
                'visible_new_assessment': ASSESSMENT in value.get('visible_record_refs', []),
                'last_local_outcome_record_refs': value.get('last_local_outcome', {}).get('record_refs', []),
                'model_or_raw_context_sha256_canonical': sha(json.dumps(value, sort_keys=True,
                    separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode())}
    assert all(contexts['39']['views'][view]['current_credit'] == 16.0 for view in ('raw', 'model'))
    assert all(contexts['40']['views'][view]['current_credit'] == 17.0
        and contexts['40']['views'][view]['retained_finding_count'] == 17
        and ASSESSMENT in contexts['40']['views'][view]['last_local_outcome_record_refs']
        for view in ('raw', 'model'))
    assert all(contexts['39']['views'][view]['annotation_score'] ==
        contexts['40']['views'][view]['annotation_score'] ==
        contexts['41']['views'][view]['annotation_score'] for view in ('raw', 'model'))
    assessment = json.loads(rows[ASSESSMENT]['data'])
    hypothesis = json.loads(rows[assessment['hypothesis_ref']]['data'])
    measured = json.loads(rows[OBSERVATION]['data'])
    proof = {'version': 'configured_api_actual_scientific_gain003_v1',
        'kind': 'new_source_grounded_limitation_received_by_actual_scientific_parent',
        'run_id': RUN_ID, 'episode_id': EPISODE_ID, 'captured_at': captured,
        'prior_proof002': {'path': str(PRIOR/'SCIENCE_GAIN002.json'),
            'sha256': sha(prior_bytes), 'manifest_sha256': sha(prior_manifest)},
        'counts_at_snapshot': counts,
        'actual_positive_gain_after34': [value for value in observations_by_decision.values()
            if value['step']['marginal_credit'] != 0],
        'actual_own_action_observations_after34': list(observations_by_decision.values()),
        'characterized_decisions': [38, 39, 40],
        'selected_actions': {index: {'action': json.loads(row['action']),
            'result': json.loads(row['result']), 'recorded_credit': row['credit']}
            for index, row in selected_actions.items()},
        'records': {ref: json.loads(row['data']) for ref, row in rows.items()},
        'receipt_evidence': receipts, 'public_artifact_sources': artifacts,
        'later_parent_saved_views': contexts,
        'recorded_scientific_progress': {'before': 16, 'after': 17, 'raw_gain': 1,
            'gain_decision_index': 39, 'gain_unit_index': observations_by_decision[39]['unit_ref']['unit_index'],
            'annotation_integration_decision_index': 40,
            'annotation_integration_raw_gain': observations_by_decision[40]['step']['marginal_credit'],
            'annotation_support_score_before_and_after': contexts['40']['views']['raw']['annotation_score'],
            'score_recomputed_by_this_capture': False},
        'precise_meaning': {
            'new_measurement_source': SOURCE, 'new_received_action_index': 38,
            'new_finding': ASSESSMENT, 'new_finding_received_action_index': 39,
            'relation': assessment['relation'],
            'qualification': assessment['investigation_finding']['qualification']['kind'],
            'question_hypothesis': hypothesis,
            'hypothesis_term_label': json.loads(rows['term_1f995b3c0cc9bd6e5caad493']['data'])['label'],
            'target_footprint': assessment['target_footprint'],
            'recorded_phmmer_domain_measurements': measured['measurements'],
            'inherited_vs_new': 'Hypothesis and earlier catalytic-activity qualification were initial received records; this PDB source/measurement/context/reference arrived through actual own action38 and new assessment through39.',
            'same_source_limits': 'New assessment same_source_claim_as_ref is null. Earlier PF03372 qualification uses a different source context/reference; no duplicate or replacement unit is inferred here.',
            'biological_entailment_limit': 'Recorded retained limitation for a phmmer sequence comparison against a reference labelled Exodeoxyribonuclease III. The associated inherited hypothesis is generic catalytic activity. This does not establish an enzyme assignment, catalytic activity, their absence, or a new structure measurement.',
            'child_influence': 'No commissioned child is recorded for this run; the contribution is an own scientific reasoning action.'},
        'provenance': witness,
        'limits': ['Only selected committed public facts and original saved parent requests were read.',
            'No current score projector, Store/application or model/service/native execution was called.',
            'No private provider files, original scientific DB or immutable-active-WAL connection was opened.',
            'No forecast-driven choice or child influence is established by this proof.',
            'The existing active run proceeded independently; no cancellation, resumption or retry was requested.',
            'Other later raw gains, if present in the snapshot, are listed as recorded but not biologically characterized unless named.']}
    write_json('SCIENCE_GAIN003.json', proof)
    write_json('PRIOR_READ_WITNESSES003.json', {'science_gain002': prior_witness,
        'manifest002': prior_manifest_witness})
    print(json.dumps({'proof': str(OUTPUT/'SCIENCE_GAIN003.json'), 'new_gain': 1,
        'source_ref': SOURCE, 'assessment_ref': ASSESSMENT, 'active_counts': counts,
        'connection_closed': closed}, sort_keys=True))


if __name__ == '__main__':
    main()
