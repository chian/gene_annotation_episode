"""Independent read-only SQL/artifact audit; imports no production readers."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

BASE = Path(__file__).resolve().parent
PIN = BASE / 'figure_verification_pin_014'
EXAMPLES = BASE / 'figure_examples_001'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def audit_case(replay):
    name = replay['case']
    directory = EXAMPLES / name
    original = read(directory/'RECEIPT.json')
    binding_evidence = read(directory/'DELIVERED_BINDINGS_AND_ANCHORS.json')
    db = sqlite3.connect((directory/'state/state.sqlite3').as_uri()+'?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    db.execute('BEGIN')

    def record(ref):
        return json.loads(db.execute('SELECT data FROM records WHERE id=?', (ref,)).fetchone()[0])

    def artifact(ref):
        digest, = db.execute('SELECT sha256 FROM artifacts WHERE id=?', (ref,)).fetchone()
        path = directory/'state/artifacts'/digest[:2]/digest
        assert sha(path) == digest
        return path.read_bytes()

    try:
        expected_sql = read(directory/'SQL_SNAPSHOT.json')
        for table, rows in expected_sql.items():
            actual = [dict(row) for row in db.execute('SELECT * FROM "'+table.replace('"','""')+'" ORDER BY rowid')]
            assert actual == rows, (name, table)
        operation, = db.execute('SELECT * FROM literature_figure_operations').fetchall()
        outcome = json.loads(operation['outcome'])
        assert outcome == original['outcome'] and outcome['status'] == 'completed'
        assert operation['run_id'] == original['run_id']
        sheet = record(outcome['result']['sheet_ref'])
        assert sheet['version'] == 'literature_figure_record_v1'
        assert sheet['provider'] == 'literature.experimental.figure'
        payload = json.loads(artifact(sheet['artifact_ref']))
        assert payload == original['saved_payload']
        assert sheet['parent_source_refs'] == payload['input_source_refs']
        assert payload['sheet']['cells'] == payload['extraction']['cells']
        admission, = db.execute('SELECT * FROM literature_figure_received').fetchall()
        attempt, = db.execute('SELECT * FROM runtime_report_attempts').fetchall()
        assert attempt['failure'] is None and attempt['child_episode_id'] == operation['episode_id']
        assert admission['episode_id'] == attempt['parent_episode_id']
        form = json.loads(attempt['form'])
        cells = json.loads(admission['cells'])
        assert form == original['actual_frozen_child_form']
        assert cells == form['measurements'] == original['actual_admitted_parent_subset']
        assert len(cells) == 3
        assert json.loads(attempt['contract'])['measurements']['schema'] == original['parent_form_schema']
        for row in cells:
            saved_cell = payload['sheet']['cells'][row['component']]
            assert all(row[key] == value for key, value in saved_cell.items())
            assert row['design'] == payload['extraction']['recipe']['design']
            assert row['partner_necessity'] == row['target_correspondence'] == 'not_evaluated'
            assert row['statistical_uncertainty'] == 'not_extracted'
        for field, ref in binding_evidence['admitted_binding_refs'].items():
            assert cells[0][field] == ref
            if ref is not None:
                actual = record(ref)
                assert actual == binding_evidence['actual_binding_records_with_labels_and_anchors'][field]
                anchor = actual['anchor']
                assert artifact(anchor['artifact_ref'])[anchor['start']:anchor['end']].decode() == anchor['quote']
        for ref, source in original['sources_and_lineage'].items():
            assert record(ref) == source['record']
            assert hashlib.sha256(artifact(source['record']['artifact_ref'])).hexdigest() == source['sha256']
        for source in original['original_setup_asset_origins']:
            assert sha(directory/source['retained_path']) == source['sha256']
        assert db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 3
        assert db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
        assert all(row[0] == 0 for row in db.execute('SELECT credit FROM runtime_actions'))
        assert not db.execute("SELECT 1 FROM records WHERE record_type IN ('observation','assessment')").fetchall()
        assert replay['SQL_query_only'] and replay['all_SQL_tables_and_histories_unchanged']
        assert not replay['original_input_bytes_read'] and len(replay['allowed_saved_artifacts']) == 2
        assert set(replay['actual_artifact_reads']) == set(replay['allowed_saved_artifacts'])
        assert len(replay['source_work_disabled']) == 77
        return {'case': name, 'status': 'passed', 'actual_selected_operations': 1,
                'actual_admissions': 1, 'actual_cells': len(cells),
                'values': [row['value'] for row in cells],
                'all_saved_SQL_tables_match': len(expected_sql),
                'actual_binding_labels_anchors_and_source_bytes_verified': True,
                'actions': 3, 'own_observations': 3, 'controller_credit': 0,
                'fresh_replay_source_helpers_disabled': len(replay['source_work_disabled'])}
    finally:
        db.rollback()
        db.close()


if __name__ == '__main__':
    manifest = read(PIN/'SOURCE_MANIFEST.json')
    drift = []
    for row in manifest['files']:
        assert sha(PIN/row['pin_relative_path']) == row['sha256']
        if sha(Path(row['origin'])) != row['sha256']:
            drift.append(row['origin'])
    # Current joined literature checks and original pinned executions must agree
    # on all changed production paths and the integration fixture.
    for name in ('gene_annotation_episode/literature_figure_measurements.py',
                 'gene_annotation_episode/literature_figure_inputs.py',
                 'gene_annotation_episode/literature_figure_storage.py',
                 'gene_annotation_episode/literature_figure_prompt.py',
                 'gene_annotation_episode/literature_episodes.py',
                 'gene_annotation_episode/literature_experimental_prompt.py',
                 'gene_annotation_episode/episode_services.py',
                 'tests/test_literature_figure_integration.py'):
        assert sha(PIN/name) == sha(BASE.parent.parent/name), name
    reopen = read(EXAMPLES/'REOPEN_RECEIPT.json')
    result = {'status': 'passed', 'written_utc': datetime.now(timezone.utc).isoformat(),
              'scope': 'Independent actual SQL/source/pin inspection of controlled examples; no new paper interpretation',
              'model_backed': False, 'pin_files_verified': len(manifest['files']),
              'pin_manifest_sha256': sha(PIN/'SOURCE_MANIFEST.json'),
              'current_main_origins_different_from_pin': drift,
              'changed_literature_paths_match_pin': True,
              'cases': [audit_case(case) for case in reopen['cases']],
              'audit_script_sha256': sha(Path(__file__))}
    output = BASE/'PARENT_CHECK_014.json'
    if output.exists():
        raise FileExistsError(output)
    output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'status': result['status'], 'cases': len(result['cases']),
                      'pin_files_verified': result['pin_files_verified'], 'main_source_drift': drift}))
