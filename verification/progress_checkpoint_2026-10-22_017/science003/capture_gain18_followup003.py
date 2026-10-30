"""Bounded follow-up for decision55 already present in capture003 snapshot.

Read only its committed public records, source artifacts and saved calls55/56.
Do not chase later actions, invoke a projector or execute scientific work.
"""
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote

import capture_science_gain003 as base


def main():
    discovery = json.loads((base.OUTPUT/'GAIN18_DISCOVERY003.json').read_text())
    primary_bytes = (base.OUTPUT/'SCIENCE_GAIN003.json').read_bytes()
    primary = json.loads(primary_bytes)
    refs = sorted(discovery['records']) + ['source_c4e2cfa61d348d15b68efd29']
    connection, records, receipts, artifacts, calls = None, {}, [], {}, {}
    watched = [base.DATABASE, Path(str(base.DATABASE)+'-wal'), Path(str(base.DATABASE)+'-shm')]
    before = {path.name: base.metadata(path) for path in watched}
    started = base.utc()
    sql = []
    try:
        connection = sqlite3.connect('file:' + quote(str(base.DATABASE), safe='/') + '?mode=ro', uri=True)
        connection.row_factory = sqlite3.Row
        connection.set_trace_callback(sql.append)
        connection.execute('PRAGMA query_only=ON')
        assert connection.execute('PRAGMA query_only').fetchone()[0] == 1
        connection.execute('BEGIN')
        action = dict(connection.execute('SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? '
            'AND decision_index=55', (base.RUN_ID, base.EPISODE_ID)).fetchone())
        assert action == discovery['action55']
        for ref in refs:
            records[ref] = dict(connection.execute('SELECT * FROM records WHERE id=?', (ref,)).fetchone())
        receipts = [dict(row) for row in connection.execute('SELECT * FROM runtime_record_receipts '
            'WHERE run_id=? AND episode_id=? AND record_ref IN (' + ','.join('?' for _ in refs) + ') '
            'ORDER BY receipt_index', (base.RUN_ID, base.EPISODE_ID, *refs))]
        source = json.loads(records['source_c4e2cfa61d348d15b68efd29']['data'])
        for artifact_ref in sorted({source[key] for key in ('artifact_ref', 'text_ref') if source.get(key)}):
            metadata = dict(connection.execute('SELECT * FROM artifacts WHERE id=?', (artifact_ref,)).fetchone())
            path = base.ACTIVE/'workspace/artifacts'/metadata['sha256'][:2]/metadata['sha256']
            data, witness = base.read_regular(path)
            assert base.sha(data) == metadata['sha256'] and len(data) == metadata['size']
            artifacts[artifact_ref] = {'source_ref': source['id'], 'metadata': metadata,
                'original': witness,
                'copy': base.write('public-artifacts/'+metadata['sha256']+'.public', data)}
        for index in (55, 56):
            row = connection.execute('SELECT call_index,purpose,request,response FROM runtime_model_calls '
                'WHERE run_id=? AND episode_id=? AND call_index=?',
                (base.RUN_ID, base.EPISODE_ID, index)).fetchone()
            assert row is not None
            data = row['request'].encode('utf-8')
            request = json.loads(data)
            views = {'raw': request['context'], 'model': request['model_presentation']['context']}
            calls[str(index)] = {'original_request': base.write(
                'public-saved-requests/call-'+str(index)+'.json', data),
                'purpose': row['purpose'], 'response_recorded': row['response'] is not None, 'views': {}}
            for label, context in views.items():
                calls[str(index)]['views'][label] = {
                    'current_credit': context['current_credit'],
                    'retained_finding_count': context['investigation_progress']['retained_finding_count'],
                    'annotation_score': context['annotation_score'],
                    'annotation_evidence_vector': context['annotation_evidence_vector'],
                    'last_local_outcome_record_refs': context.get('last_local_outcome', {}).get('record_refs', []),
                    'visible_new_assessment': 'assessment_850a818195e42ac59fce9d37' in context.get('visible_record_refs', [])}
        commission_count = connection.execute('SELECT count(*) FROM runtime_commission_intents WHERE run_id=?',
            (base.RUN_ID,)).fetchone()[0]
        assert connection.total_changes == 0
        captured = base.utc()
    finally:
        if connection is not None:
            connection.rollback()
            connection.close()
    after = {path.name: base.metadata(path) for path in watched}
    witness = {'version': 'readonly_bounded_gain18_followup_v1', 'mode': 'ro',
        'query_only': True, 'explicit_begin': True, 'finally_rollback_and_close': True,
        'sqlite_total_changes': 0, 'started_at': started, 'snapshot_captured_at': captured,
        'active_files_before': before, 'active_files_after': after,
        'whole_database_hash_or_unchanged_claim': False, 'sql_statements': sql,
        'fixed_scope': 'Decision55 already present in primary snapshot; selected calls55/56 and its source closure only.',
        'commission_count_for_actual_run': commission_count}
    base.write_json('GAIN18_PUBLIC_ROWS003.json', {'action55': action, 'records': records,
        'receipts': receipts, 'artifacts': artifacts, 'saved_calls55_56': calls, 'provenance': witness})
    assert all(calls['55']['views'][label]['current_credit'] == 17.0
        and calls['56']['views'][label]['current_credit'] == 18.0
        and calls['56']['views'][label]['retained_finding_count'] == 18
        and 'assessment_850a818195e42ac59fce9d37' in calls['56']['views'][label]['last_local_outcome_record_refs']
        and calls['55']['views'][label]['annotation_score'] == calls['56']['views'][label]['annotation_score']
        for label in ('raw', 'model'))
    anchors = []
    for ref, row in records.items():
        value = json.loads(row['data'])
        if value.get('anchor'):
            anchor = value['anchor']
            artifact = artifacts[anchor['artifact_ref']]
            text = (base.OUTPUT/artifact['copy']['member']).read_text()
            selected = text[anchor['start']:anchor['end']]
            assert selected == anchor['quote']
            anchors.append({'record_ref': ref, 'source_ref': anchor['source_ref'],
                'artifact_ref': anchor['artifact_ref'], 'start_character': anchor['start'],
                'end_character': anchor['end'], 'exact_quote_matches_stored_public_text': True,
                'start_utf8_byte': len(text[:anchor['start']].encode()),
                'end_utf8_byte': len(text[:anchor['end']].encode()),
                'selected_utf8_sha256': base.sha(selected.encode())})
    assessment = json.loads(records['assessment_850a818195e42ac59fce9d37']['data'])
    primary['capture001_original'] = base.write('SCIENCE_GAIN003_CAPTURE001.json', primary_bytes)
    primary['recorded_scientific_progress'] = {
        'before': 16, 'after': 18, 'observed_raw_net_gain': 2,
        'transitions': [{'decision_index': 39, 'unit_index': 29, 'before': 16, 'after': 17, 'raw_delta': 1},
            {'decision_index': 55, 'unit_index': 42, 'before': 17, 'after': 18, 'raw_delta': 1}],
        'annotation_integration_decision40_raw_gain': 0,
        'annotation_support_score_before_and_after_both_findings': calls['56']['views']['raw']['annotation_score'],
        'score_recomputed_by_this_capture': False}
    primary['characterized_decisions'] = [38, 39, 40, 55]
    primary['new_literature_limitation'] = {
        'decision_index': 55, 'assessment_ref': assessment['id'],
        'source_ref': source['id'], 'source_uri': source.get('uri'),
        'relation': assessment['relation'], 'applicability': assessment['applicability'],
        'qualification': assessment['investigation_finding']['qualification'],
        'source_claim': assessment['investigation_finding']['source_claim'],
        'question_hypothesis': json.loads(records[assessment['hypothesis_ref']]['data']),
        'meaning': 'A retained different_source_subject limitation: the recorded paper assay is on DrXth from Deinococcus radiodurans, not the annotation target. The episode records that transfer limitation for a target AP-endonuclease question.',
        'entailment_limit': 'This proves a source-grounded qualification was committed and received, not that the target has or lacks AP-endonuclease activity. It is not a new assay on the target.',
        'same_source_limit': 'same_source_claim_as_ref is null and the declared qualification/question are retained as recorded; no additional deduplication or score projection is performed.',
        'public_anchor_matches': anchors, 'public_artifact_sources': artifacts,
        'recorded_receipts': receipts, 'saved_parent_views': calls,
        'followup_provenance': witness}
    primary['records'].update({ref: json.loads(row['data']) for ref, row in records.items()})
    primary['public_artifact_sources'].update(artifacts)
    primary['capture_boundary'] = {'primary_snapshot_utc': primary['captured_at'],
        'highest_characterized_decision_index': 55,
        'followup_snapshot_utc': captured,
        'consistency_limit': 'Primary snapshot contained both raw gains. Follow-up is a separate readonly snapshot of the already committed55 records and following saved context56. No later actions are chased or claimed.'}
    primary['limits'][-1] = 'This proof stops at the two positive gains in the primary snapshot, through decision55; independent later progress is outside its boundary.'
    # The prior own temporary capture is retained byte-exact above; no earlier
    # scientific proof or original/active file is modified by this replacement.
    final = base.OUTPUT/'SCIENCE_GAIN003.json'
    final.unlink()
    base.write_json('SCIENCE_GAIN003.json', primary)
    print(json.dumps({'proof': str(final), 'sha256': base.sha(final.read_bytes()),
        'characterized_positive_decisions': [39, 55], 'progress_before': 16, 'progress_after': 18,
        'anchor_matches': len(anchors), 'commission_count': commission_count,
        'connection_closed': True}, sort_keys=True))


if __name__ == '__main__':
    main()
