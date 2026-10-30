"""Read original host-test stores without invoking parsers or calculators.

This is a receipt index, not an alternative validator. The integration tests
exercise production validation. All values below are copied from frozen saved
records; only byte hashes, byte counts, and database row counts are calculated.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def inspect(database):
    root = database.parent
    connection = sqlite3.connect(f'file:{database.resolve()}?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        artifacts = {}
        for row in connection.execute('SELECT * FROM artifacts ORDER BY id'):
            path = root / 'artifacts' / row['sha256'][:2] / row['sha256']
            raw = path.read_bytes()
            assert len(raw) == row['size'] and sha256(raw) == row['sha256'], str(path)
            artifacts[row['id']] = raw
        records = {row['id']: json.loads(row['data']) for row in connection.execute(
            'SELECT id,data FROM records WHERE record_type=? ORDER BY id', ('source',))}

        def content(source_ref):
            return json.loads(artifacts[records[source_ref]['artifact_ref']])

        publications = []
        for source_ref, source in records.items():
            if source.get('provider') != 'episode.bvbrc_appservice_bundle_data':
                continue
            publication = content(source_ref)
            if publication.get('version') != 'bvbrc_appservice_bundle_publication_v1':
                continue
            inputs = content(publication['publication_inputs_content']['source_ref'])
            bundle = content(publication['bundle_content']['source_ref'])
            result = publication['adapter_result']
            row = {
                'source_ref': source_ref,
                'publication_artifact_ref': source['artifact_ref'],
                'origin': publication['origin'],
                'publication_inputs_content': publication['publication_inputs_content'],
                'bundle_content': publication['bundle_content'],
                'configured_adapter_sha256': inputs['adapter_implementation_sha256'],
                'original_request': inputs['request'],
                'original_task': bundle['original_task'],
                'supplied_metadata': inputs['selector'].get('supplied_metadata', []),
                'supplied_contents': inputs['selector'].get('supplied_contents', []),
                'artifacts': bundle['artifacts'],
                'acquisition_receipt_refs': bundle['acquisition_receipt_refs'],
                'current_acquisition_receipt_ref': publication['current_acquisition_receipt_ref'],
                'requested_form_status': publication['requested_form_status'],
                'completion_proof': publication['completion_proof'],
                'adapter_result': result,
            }
            if result is not None and result.get('sheet_content') is not None:
                sheet = content(result['sheet_content']['source_ref'])
                row['saved_input_facts'] = sheet['data']['inputs']
                row['saved_associations'] = sheet['data']['associations']
            publications.append(row)
        publications.sort(key=lambda p: (p['origin']['episode_id'],
            int(p['origin']['operation_key'].rsplit(':', 1)[1])))

        actions = []
        for row in connection.execute('SELECT * FROM runtime_actions ORDER BY episode_id,decision_index'):
            action = json.loads(row['action'])
            result = None if row['result'] is None else json.loads(row['result'])
            actions.append({
                'run_id': row['run_id'], 'episode_id': row['episode_id'],
                'decision_index': row['decision_index'], 'kind': action['kind'],
                'tool': action.get('tool'), 'role': action.get('role'),
                'action_sha256': sha256(row['action'].encode()),
                'result_status': None if result is None else result.get('status'),
                'record_refs': [] if result is None else result.get('record_refs', []),
            })
        forms = []
        for row in connection.execute('SELECT * FROM runtime_forms ORDER BY episode_id'):
            forms.append({'episode_id': row['episode_id'],
                'facts': json.loads(row['facts']), 'form': json.loads(row['form'])})
        reports = []
        for row in connection.execute('SELECT * FROM runtime_report_attempts ORDER BY parent_episode_id,decision_index'):
            reports.append({'parent_episode_id': row['parent_episode_id'],
                'decision_index': row['decision_index'], 'delivery_ref': row['delivery_ref'],
                'child_episode_id': row['child_episode_id'],
                'original_contract_sha256': sha256(row['contract'].encode()),
                'form': None if row['form'] is None else json.loads(row['form']),
                'failure': None if row['failure'] is None else json.loads(row['failure'])})
        counts = {name: connection.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]
            for name in ('artifacts', 'records', 'runtime_actions', 'runtime_forms',
                         'runtime_report_attempts', 'runtime_observations', 'runtime_model_calls')}
        return {'case_directory': str(database.parent.parent),
            'database_sha256': sha256(database.read_bytes()), 'counts': counts,
            'all_saved_artifact_bytes_verified': True,
            'selected_actions': actions, 'publications': publications,
            'frozen_forms': forms, 'original_report_attempts': reports}
    finally:
        connection.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs_directory', type=Path)
    arguments = parser.parse_args()
    databases = [path for path in sorted(arguments.runs_directory.glob('*/state/state.sqlite3'))
        if not path.parent.parent.is_symlink()]
    assert databases, arguments.runs_directory
    output = {'verification_kind': 'read_only_saved_store_trace',
        'controlled_service_replies': True, 'scripted_original_selections': True,
        'live_service_execution': False, 'configured_model_workflow': False,
        'cases': [inspect(database) for database in databases]}
    print(json.dumps(output, indent=2, sort_keys=True))
