"""Finalize already captured public proof bytes; no database connection.

The first follow-up's observer wrongly assumed character offsets. The actual
Store._anchor contract is UTF-8 byte offsets. Preserve that failed attempt and
validate the exact stored bytes offline, without repairing scientific records.
"""
import json

import capture_science_gain003 as base


def main():
    root = base.OUTPUT
    primary_bytes = (root/'SCIENCE_GAIN003.json').read_bytes()
    primary = json.loads(primary_bytes)
    captured = json.loads((root/'GAIN18_PUBLIC_ROWS003.json').read_text())
    records, calls, artifacts = captured['records'], captured['saved_calls55_56'], captured['artifacts']
    anchors = []
    for ref, row in records.items():
        value = json.loads(row['data'])
        anchor = value.get('anchor')
        if anchor:
            body = (root/artifacts[anchor['artifact_ref']]['copy']['member']).read_bytes()
            quote = anchor['quote'].encode('utf-8')
            start, end = anchor['start'], anchor['end']
            assert end-start == len(quote) and body[start:end] == quote
            anchors.append({'record_ref': ref, 'source_ref': anchor['source_ref'],
                'artifact_ref': anchor['artifact_ref'], 'start_utf8_byte': start,
                'end_utf8_byte': end, 'exact_quote_matches_stored_public_bytes': True,
                'selected_utf8_sha256': base.sha(quote)})
    assert anchors
    assert all(calls['55']['views'][label]['current_credit'] == 17.0
        and calls['56']['views'][label]['current_credit'] == 18.0
        and calls['56']['views'][label]['retained_finding_count'] == 18
        and 'assessment_850a818195e42ac59fce9d37' in calls['56']['views'][label]['last_local_outcome_record_refs']
        and calls['55']['views'][label]['annotation_score'] == calls['56']['views'][label]['annotation_score']
        for label in ('raw', 'model'))
    assessment = json.loads(records['assessment_850a818195e42ac59fce9d37']['data'])
    source = json.loads(records['source_c4e2cfa61d348d15b68efd29']['data'])
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
        'publication_identifiers': source.get('publication_identifiers'),
        'relation': assessment['relation'], 'applicability': assessment['applicability'],
        'qualification': assessment['investigation_finding']['qualification'],
        'source_claim': assessment['investigation_finding']['source_claim'],
        'question_hypothesis': json.loads(records[assessment['hypothesis_ref']]['data']),
        'meaning': 'A retained different_source_subject limitation: the recorded paper assay is on the source subject DrXth, not the annotation target. The episode records that transfer limitation for a target AP-endonuclease question.',
        'entailment_limit': 'This proves a source-grounded qualification was committed and received, not that the target has or lacks AP-endonuclease activity. It is not a new assay on the target.',
        'same_source_limit': 'same_source_claim_as_ref is null and the declared qualification/question are retained as recorded; no additional deduplication or score projection is performed.',
        'public_anchor_matches': anchors, 'public_artifact_sources': artifacts,
        'recorded_receipts': captured['receipts'], 'saved_parent_views': calls,
        'followup_provenance': captured['provenance']}
    primary['records'].update({ref: json.loads(row['data']) for ref, row in records.items()})
    primary['public_artifact_sources'].update(artifacts)
    primary['capture_boundary'] = {'primary_snapshot_utc': primary['captured_at'],
        'highest_characterized_decision_index': 55,
        'followup_snapshot_utc': captured['provenance']['snapshot_captured_at'],
        'consistency_limit': 'Primary snapshot contained both raw gains. Follow-up is a separate readonly snapshot of the already committed55 records and following saved context56. No later actions are chased or claimed.'}
    primary['limits'][-1] = 'This proof stops at the two positive gains in the primary snapshot, through decision55; independent later progress is outside its boundary.'
    primary['observer_failure_preserved'] = {'operator': 'capture_gain18_followup003.py',
        'stderr': 'followup003.stderr.log', 'reason': 'Observer assumed character offsets; actual Store._anchor uses UTF-8 byte offsets.',
        'scientific_records_changed': False, 'further_database_read_for_correction': False,
        'correction': 'Byte-only anchor validation against already copied public artifact bytes.'}
    path = root/'SCIENCE_GAIN003.json'
    path.unlink()  # Own provisional output only; exact original is retained above.
    base.write_json('SCIENCE_GAIN003.json', primary)
    base.write_json('FOLLOWUP_OBSERVER_CORRECTION003.json', primary['observer_failure_preserved'] | {
        'all_anchors_byte_exact': True, 'anchor_count': len(anchors),
        'actual_anchor_contract': 'frozen006 gene_annotation_episode/state.py Store._anchor; end-start equals len(quote.encode(utf-8)).'})
    print(json.dumps({'proof': str(path), 'sha256': base.sha(path.read_bytes()),
        'characterized_positive_decisions': [39, 55], 'progress_before': 16, 'progress_after': 18,
        'anchor_matches': len(anchors), 'commission_count': captured['provenance']['commission_count_for_actual_run'],
        'database_connected_by_finalizer': False}, sort_keys=True))


if __name__ == '__main__':
    main()
