"""Read completed retained evidence into a small review packet; no app imports."""
from pathlib import Path
import hashlib
import json
import sqlite3
import xml.etree.ElementTree as ET


PACKET = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def identity(path):
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}


def artifact(case, descriptor):
    sha = descriptor['sha256']
    path = case / 'state/artifacts' / sha[:2] / sha
    actual = identity(path)
    if any(actual[key] != descriptor[key] for key in ('sha256', 'size_bytes')):
        raise ValueError('retained_artifact_identity_changed')
    return path


def history(value):
    return {role: [{'initial_credit': row['initial_credit'], 'current_credit': row['current_credit'],
        'scores': row['scores'], 'score_semantics': 'completed_own_action_marginal_credit',
        'turns': row['estimate']['turns'],
        'expected_next_gain': row['estimate']['expected_next_gain'],
        'estimator_provenance': row['estimate']['provenance'],
        'completion_proof': row['estimate'].get('diagnostics', {}).get('completion_proof')}
        for row in histories] for role, histories in value.items()}


def projection(value):
    return {'population_keys': value['population_keys'], 'requested_fields': value['requested_fields'],
        'parameters': value['parameters'], 'source_sheet_sha256': value['source_sheet_sha256'],
        'rows': [{'population_key': row['population_key'], 'pair_key': row['pair_key'],
            'enhancer': row['enhancer_element_key'], 'promoter': row['promoter_element_key'],
            'fields': row['fields'], 'qualifications': row['qualifications']} for row in value['rows']],
        'failure_codes': sorted({row['code'] for row in value['failures']})}


def summarize_case(path):
    case = path.parent
    value = read(path)
    result = {'case': identity(path), 'partial': value['partial'], 'empty': value.get('empty'),
        'native_returncode': value.get('native_returncode'),
        'forwarded_keys': list(value['forwarded']), 'histories': history(value['histories']),
        'returns': [], 'saved_check': None}
    result['native_outcomes'] = []
    for handle_path in sorted((case / 'workspace').rglob('native.json')):
        handle = read(handle_path)
        if handle.get('version') != 'durable_systemd_native_job_v2':
            continue
        outcome_path = Path(handle['paths']['result'])
        outcome = read(outcome_path)
        result['native_outcomes'].append({'handle': identity(handle_path),
            'result': identity(outcome_path), 'outcome': outcome})
    if len(result['native_outcomes']) == 1:
        native_returncode = result['native_outcomes'][0]['outcome']['native_returncode']
        if result['native_returncode'] is not None and result['native_returncode'] != native_returncode:
            raise ValueError('case_and_actual_native_outcome_disagree')
        result['native_returncode'] = native_returncode
    for form in value['returned']:
        item = {'completed': form['completed'], 'form_keys': list(form), 'failures': form['failures'],
            'projections': [projection(v) for v in form['chromatin']], 'saved_bundles': []}
        for bundle in form['saved']:
            sheet_path = artifact(case, bundle['sheet'])
            sheet = read(sheet_path)
            for table in bundle['tables']:
                artifact(case, table)
            item['saved_bundles'].append({'sheet': identity(sheet_path),
                'ordered_tables': bundle['tables'],
                'table_occurrences': len(bundle['tables']),
                'unique_table_bytes': len({t['sha256'] for t in bundle['tables']}),
                'populations': [{'population_key': p['population_key'], 'extent': p['extent'],
                    'raw_cell_population': p['raw_cell_population'], 'read_evidence': p['read_evidence']}
                    for p in sheet['populations']]})
        result['returns'].append(item)
    saved = case / 'SAVED_CHECK.json'
    if saved.exists():
        check = read(saved)
        result['saved_check'] = {'record': identity(saved), 'removed': check['removed'],
            'dispatches': check['dispatches'], 'origins_before_saved': check['origins_before_saved'],
            'declared_absent_tables': check.get('declared_absent_tables')}
    db = sqlite3.connect('file:' + str(case / 'state/state.sqlite3') + '?mode=ro', uri=True)
    try:
        result['completed_actions_by_episode'] = dict(db.execute(
            'SELECT episode_id,count(*) FROM runtime_actions WHERE result IS NOT NULL GROUP BY episode_id'))
        result['observations_by_episode'] = dict(db.execute(
            'SELECT episode_id,count(*) FROM runtime_observations GROUP BY episode_id'))
    finally:
        db.close()
    return result


report = {}
for name in ('cooler002', 'hic001'):
    attempt = PACKET / name
    receipt = read(attempt / 'receipt.json')
    audit = receipt['execution_audit']
    if (receipt['returncode'] != 0 or not receipt['terminal'] or not receipt['quiescent']
            or any(not receipt[field] for field in ('source_pins_unchanged', 'dependency_pins_unchanged',
                'binary_pins_unchanged', 'standard_library_pins_unchanged'))
            or audit is None or not audit['native_library_pins_unchanged']
            or audit['unbound_executable_mappings'] or audit['modules_outside_frozen_roots']):
        raise ValueError('successful_unchanged_terminal_receipt_required:' + name)
    tests = []
    for row in ET.parse(attempt / 'junit.xml').iter('testcase'):
        if any(child.tag in ('error', 'failure', 'skipped') for child in row):
            raise ValueError('full_suite_did_not_pass:' + name)
        tests.append(dict(row.attrib))
    if len(tests) != 7:
        raise ValueError('exact_existing_seven_test_suite_required:' + name)
    report[name] = {'receipt': identity(attempt / 'receipt.json'),
        'handle': receipt['handle'], 'unit': receipt['unit'], 'tests': tests,
        'cases': [summarize_case(path) for path in sorted((attempt / 'temporary').rglob('CASE.json'))],
        'native_handles': []}
    for pattern in ('native.json', 'worker.handle.json'):
        for path in sorted((attempt / 'temporary').rglob(pattern)):
            handle = read(path)
            if handle.get('version') == 'durable_systemd_native_job_v2':
                outcome = Path(handle['paths']['result'])
                report[name]['native_handles'].append({'handle': identity(path), 'unit': handle['unit'],
                    'command': handle['command'], 'metadata': handle['metadata'],
                    'retained_result': read(outcome) if outcome.exists() else None})
(PACKET / 'CHECKED_CASES.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
print(json.dumps({name: {'tests': len(value['tests']), 'cases': len(value['cases']),
    'native_handles': len(value['native_handles'])} for name, value in report.items()}))
