"""Export concrete completed-test custody and decision values, without execution."""
import hashlib
import json
from pathlib import Path
import sqlite3
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
TEMP = Path('/tmp/bvbrc-episode-path-20261024-verified')


def decoded(row, fields):
    value = dict(row)
    for field in fields:
        if value.get(field) is not None:
            value[field] = json.loads(value[field])
    return value


if __name__ == '__main__':
    run = json.loads((HERE / 'RUN.json').read_text())
    if run.get('exit_code') != 0 or not run.get('source_versions_unchanged'):
        raise SystemExit('A passing unchanged-source run is required before exporting its evidence')
    cases = []
    artifacts = {}
    (HERE / 'artifacts').mkdir(exist_ok=True)
    for directory in sorted(TEMP.glob('test*')):
        if not directory.is_dir() or directory.is_symlink():
            continue
        database = directory / 'state/state.sqlite3'
        if not database.exists():
            continue
        db = sqlite3.connect('file:' + str(database) + '?mode=ro', uri=True)
        db.row_factory = sqlite3.Row
        episodes = [decoded(row, ('path', 'request', 'completion'))
                    for row in db.execute('SELECT * FROM runtime_episodes')]
        for episode in episodes:
            episode['action_count'] = db.execute('SELECT count(*) FROM runtime_actions WHERE episode_id=?',
                (episode['episode_id'],)).fetchone()[0]
            episode['observation_count'] = db.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?',
                (episode['episode_id'],)).fetchone()[0]
        decisions = []
        for row in db.execute('SELECT * FROM runtime_model_calls ORDER BY episode_id,call_index'):
            request = json.loads(row['request'])
            values = {name: request['context'][name] for name in ('received_bvbrc_values', 'own_bvbrc_values')
                      if request['context'].get(name)}
            if values:
                decisions.append({'episode_id': row['episode_id'], 'call_index': row['call_index'],
                    'saved_request_sha256': hashlib.sha256(row['request'].encode()).hexdigest(),
                    'exact_selected_context_fields': values,
                    'response': None if row['response'] is None else json.loads(row['response'])})
        admissions = []
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_bvbrc_admissions'").fetchone():
            admissions = [decoded(row, ('form', 'original_schema', 'bindings', 'received_sources', 'materializations'))
                          for row in db.execute('SELECT * FROM runtime_bvbrc_admissions')]
        sources = [decoded(row, ('data',)) for row in db.execute("SELECT * FROM records WHERE record_type='source'")]
        case_artifacts = []
        for row in db.execute('SELECT * FROM artifacts ORDER BY id'):
            value = dict(row)
            raw = (directory / 'state/artifacts' / row['sha256'][:2] / row['sha256']).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == row['sha256']
            (HERE / 'artifacts' / row['sha256']).write_bytes(raw)
            artifacts[row['id']] = {**value, 'retained_file': 'artifacts/' + row['sha256']}
            case_artifacts.append(row['id'])
        cases.append({'engineering_case_directory': directory.name, 'episodes': episodes,
            'completed_action_observations': [decoded(row, ('observation',))
                for row in db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')],
            'selected_actions': [decoded(row, ('action', 'result', 'timing'))
                for row in db.execute('SELECT * FROM runtime_actions ORDER BY episode_id,decision_index')],
            'saved_decision_values': decisions, 'actual_admissions': admissions,
            'source_records': sources, 'retained_artifact_refs': case_artifacts})
        db.close()
    tests = [case.attrib for case in ET.parse(HERE / 'junit.xml').findall('.//testcase')]
    result = {'version': 'bvbrc_episode_engineering_evidence_v1',
        'test_cases': tests, 'actual_shared_workflow_cases': cases,
        'artifact_manifest': artifacts,
        'scope': 'controlled native/synthetic response; scripted engineering decisions; actual host and shared Workflow',
        'unverified': ['live HTTP', 'configured model', 'rendered prompt', 'independent detached-process path',
                       'all-collection live deployment', 'annotation biology']}
    (HERE / 'EXAMPLES.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'tests': len(tests), 'workflow_cases': len(cases), 'artifacts': len(artifacts),
        'example_bytes': (HERE / 'EXAMPLES.json').stat().st_size}, indent=2))
