"""Inspect retained receipts only; write new preparation evidence in this directory.

This does not run tests, load production modules, execute native programs, or
modify accounting. The application script is prepared separately and not run.
"""
from collections import Counter
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ACCOUNTING = ROOT / 'research/tool_grader_goal_2026-10-24'
AUTHORITY = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
AUTHORITY_HASH = '11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7'
STATUS_HASH = '8e954c650412201a085dbbddeca09a7316f101601336aed84fe96ee0171c4121'
POLICY = dict(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
FILES = {}


def path(name):
    value = Path(name)
    return value if value.is_absolute() else ROOT / value


def pin(name):
    value = path(name)
    key = str(value.relative_to(ROOT)) if value.is_relative_to(ROOT) else str(value)
    digest = hashlib.sha256(value.read_bytes()).hexdigest()
    FILES[key] = digest
    return digest


def read(name):
    pin(name)
    return json.loads(path(name).read_text())


def xml(name):
    pin(name)
    result = {}
    for row in ET.parse(path(name)).getroot().findall('.//testcase'):
        node = row.attrib['classname'].replace('.', '/') + '.py::' + row.attrib['name']
        assert node not in result, (name, node)
        state = next((tag for tag in ('failure', 'error', 'skipped') if row.find(tag) is not None), 'passed')
        result[node] = dict(state=state, diagnostic={} if state == 'passed' else row.find(state).attrib)
    return result


def zero(band):
    assert band == dict(alpha=0.0, lower=0.0, status_code=0, uncertainty_code=0, upper=0.0, value=0.0), band


assert pin(AUTHORITY) == AUTHORITY_HASH
assert pin(ACCOUNTING / 'WORK_STATUS.json') == STATUS_HASH
work = read(ACCOUNTING / 'WORK_STATUS.json')
scope = read(ACCOUNTING / 'SCOPE.json')
aliases = read(ACCOUNTING / 'SOURCE_ALIASES.json')
coverage = read(ACCOUNTING / 'COVERAGE.json')
assert work['authority_sha256'] == scope['authority']['sha256'] == aliases['authority_sha256'] == coverage['authority_sha256'] == AUTHORITY_HASH
assert len(work['rows']) == len(scope['rows']) == 308
assert len(work['resource_bindings']) == len(scope['resource_bindings']) == 288
assert len(aliases['rows']) == 622
assert work['verified_bound_local_tool_mode_rows'] == 22
assert work['complete_scientific_tools_claimed'] == 0
for group in ('rows', 'resource_bindings'):
    assert [row['id'] for row in work[group]] == [row['id'] for row in scope[group]]
for name in ('CHECKLIST.md', 'SOURCE_MAPPING.md', 'check_accounting.py', 'render_checklist.py', 'apply_progress_050.py'):
    pin(ACCOUNTING / name)
for old in sorted(ACCOUNTING.glob('PROGRESS_UPDATE_*.json')):
    pin(old)
assert not (ACCOUNTING / 'PROGRESS_UPDATE_051.json').exists()

base = ROOT / 'verification'
episode = base / 'tool_graders_infernal_episode_2026-10-26_226'
e = read(episode / 'FINAL_VERIFICATION_001.json')
assert len(e['final_source_hashes']) == 55
for name, digest in e['final_source_hashes'].items():
    assert pin(name) == digest, name
passing = {}
run_counts = {}
for run in e['runs']:
    directory = path(run['directory'])
    receipt = read(directory / 'verification-receipt.json')
    before, after = read(directory / 'source-before.json'), read(directory / 'source-after.json')
    changed = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
    assert changed == run['source_changed_during_run'] == receipt['source_changed_during_run']
    assert run['command'] == receipt['command'] and run['returncode'] == receipt['returncode']
    assert run['policy'] == receipt['policy'] == POLICY
    cases = xml(directory / 'tests.xml')
    counts = dict(Counter(row['state'] for row in cases.values()))
    assert counts == run['counts']
    run_counts[directory.name] = counts
    for node, row in cases.items():
        if row['state'] != 'passed':
            continue
        assert node not in passing
        passing[node] = str((directory / 'verification-receipt.json').relative_to(ROOT))
assert run_counts == {'run_004_full': {'passed': 30, 'failure': 1},
    'run_006_remaining_independent': {'passed': 8}, 'run_007_receiver_boundaries': {'passed': 4}}
assert len(passing) == 42
assert {row['nodeid']: row['receipt'] for row in e['passing_test_nodes']} == passing
pin(episode / 'passing-test-nodes.tsv')
with (episode / 'passing-test-nodes.tsv').open() as stream:
    tsv = list(csv.DictReader(stream, delimiter='\t'))
assert {row['nodeid']: row['receipt'] for row in tsv} == passing
assert len(tsv) == 42

actual_cases = []
practical_archives = []
for row in e['cases_across_all_retained_runs']:
    case = read(row['case'])
    assert case['selected_actions'] == case['controller_observations'] == case['scripted_decision_calls']
    assert row['selected_actions'] == case['selected_actions'] and row['controller_observations'] == case['controller_observations']
    assert case['native_plan']['policy'] == POLICY
    assert row['root_gains'] == case['parent_gains'] and row['root_units'] == case['parent_units']
    assert row['result_gains'] == [value['gains'] for value in case['results']]
    assert row['result_complete'] == [value['complete'] for value in case['results']]
    assert row['result_future_expectations'] == [value['future_expectation'] for value in case['results']]
    assert row['failure_codes'] == [[failure['code'] for failure in value['failures']] for value in case['results']]
    for result in case['results']:
        if result['complete']:
            zero(result['future_expectation'])
    actual_cases.append(dict(case=row['case'], program=case['program'], actions=case['selected_actions'],
        observations=case['controller_observations'], result_gains=row['result_gains'], root_gains=row['root_gains']))
    if 'run_004_full' in row['case'] and any(row['case'].endswith('/' + program + '0/CASE.json') for program in ('cmsearch', 'cmscan', 'cmalign')):
        for archive in (path(row['case']).parent / 'run/archive').glob('*.json'):
            if '.index.' in archive.name:
                continue
            value = json.loads(archive.read_text())
            if 'controller_state' not in value or value.get('path', [['']])[-1][0] not in ('launch', 'launch_local'):
                continue
            pin(archive)
            role = value['path'][-1][0]
            gains = [unit['controller_step']['marginal_credit'] for unit in value['units']]
            assert gains == [{'launch': 3, 'launch_local': 7}[role]] and value['units_consumed'] == 1
            zero(value['controller_state']['estimate']['expected_next_gain'])
            practical_archives.append(dict(path=str(archive.relative_to(ROOT)), program=case['program'], role=role, gains=gains))
assert len(actual_cases) == 15 and len(practical_archives) == 6
assert dict(Counter(row['program'] for row in actual_cases)) == e['native_executions_across_all_retained_runs'] == {'cmsearch': 12, 'cmscan': 1, 'cmalign': 2}

presentation = base / 'tool_graders_infernal_presentation_2026-10-26_231'
p = read(presentation / 'FINAL_EVIDENCE.json')
assert p['schema_version'] == 'infernal_presentation_verification_v1'
assert len(p['production_sha256_current']) == 9 and len(p['test_fixture_and_runner_sha256_current']) == 6
for name, digest in {**p['production_sha256_current'], **p['test_fixture_and_runner_sha256_current']}.items():
    assert pin(name) == digest, name
presentation_runs = {}
for run in p['runs']:
    receipt = read(run['receipt_path'])
    assert receipt['source_hashes_before'] == receipt['source_hashes_after']
    assert run['source_hashes_unchanged_during_run'] is True
    assert receipt['policy'] == run['policy'] == POLICY and receipt['returncode'] == run['returncode']
    cases = xml(run['junit_path'])
    assert len(cases) == run['tests']
    assert sum(c['state'] == 'failure' for c in cases.values()) == run['failures']
    assert sum(c['state'] == 'error' for c in cases.values()) == run['errors']
    assert {row['node_id']: row['result'] for row in run['nodes']} == {
        node: {'failure': 'failed', 'error': 'error', 'skipped': 'skipped', 'passed': 'passed'}[c['state']]
        for node, c in cases.items()}
    presentation_runs[run['receipt_path']] = cases
    pin(run['stdout_path'])
    pin(run['stderr_path'])
assert p['counts'] == dict(existing_failures_reproduced_with_no_op_projection=4,
    new_boundary_cases_passed=16, shared_cases_passed=48, unique_cases_passed=64)
assert len(p['passing_cases']) == len({c['node_id'] for c in p['passing_cases']}) == 64
for row in p['passing_cases']:
    assert presentation_runs[row['latest_passing_receipt']][row['node_id']]['state'] == 'passed'
assert sum(row['node_id'].startswith('tests/test_infernal_decision_presentation.py::') for row in p['passing_cases']) == 16
assert len(p['final_restored_pending_cases']) == 2
for row in p['final_restored_pending_cases']:
    assert 'run_004_restore_schema' in row['latest_passing_receipt']
    assert presentation_runs[row['latest_passing_receipt']][row['node_id']]['state'] == 'passed'
baseline = read(p['baseline_comparison_path'])
assert baseline['same_feedback'] and p['baseline_saved_feedback_equal']
assert baseline['saved_context_feedback']['run_001'] == baseline['saved_context_feedback']['run_003_noop_baseline']
assert len(p['unchanged_existing_failures']) == len(baseline['comparison']) == 4
for row in p['unchanged_existing_failures']:
    current = presentation_runs[row['current_receipt']][row['node_id']]
    old = presentation_runs[row['no_op_receipt']][row['node_id']]
    assert current['state'] == old['state'] == 'failure'
    assert current['diagnostic'] == old['diagnostic'] == row['current_diagnostic'] == row['no_op_diagnostic']
assert not p['production_files_edited'] and p['production_matches_final_restoration_receipt']

components = {}
for label, dirname, receipt_name, xml_name, count in (
    ('producer', 'native_execution_222', 'TEST_RECEIPT_001.json', 'tests_001.xml', 43),
    ('acquisition_initial', 'acquisition_223', 'tests_001/verification-receipt.json', 'tests_001/tests.xml', 96),
    ('acquisition_followup', 'acquisition_223', 'boundary_tests_002/verification-receipt.json', 'boundary_tests_002/tests.xml', 4),
    ('worker', 'worker_224', 'TEST_RECEIPT_004.json', 'tests_004.xml', 43),
    ('publication_full', 'publication_225', 'TEST_RECEIPT_004.json', 'tests_004.xml', 27),
    ('publication_followup', 'publication_225', 'TEST_RECEIPT_005.json', 'tests_005.xml', 4),
    ('returns', 'returns_227', 'run_005/verification-receipt.json', 'run_005/tests.xml', 43),
    ('binding', 'binding_229', 'run_001/receipt.json', 'run_001/tests.xml', 47),
    ('root_shared', 'root_228', 'shared_regression_001/receipt.json', 'shared_regression_001/tests.xml', 151),
    ('pure_presentation', 'presentation_230', 'tests_001/verification-receipt.json', 'tests_001/tests.xml', 22),
):
    family, number = dirname.rsplit('_', 1)
    directory = base / ('tool_graders_infernal_' + family + '_2026-10-26_' + number)
    receipt = read(directory / receipt_name)
    assert receipt.get('returncode', receipt.get('exit_code')) == 0
    cases = xml(directory / xml_name)
    assert len(cases) == count and all(c['state'] == 'passed' for c in cases.values())
    components[label] = dict(count=count, nodes=sorted(cases), receipt=str((directory / receipt_name).relative_to(ROOT)))
assert len(set(components['acquisition_initial']['nodes']) | set(components['acquisition_followup']['nodes'])) == 99
assert len(set(components['acquisition_initial']['nodes']) & set(components['acquisition_followup']['nodes'])) == 1
assert set(components['publication_followup']['nodes']) <= set(components['publication_full']['nodes'])
search = base / 'tool_graders_infernal_search_2026-10-26_219'
assert read(search / 'PYTEST_RECEIPT.json')['returncode'] == 0
assert '54 passed' in (search / 'PYTEST_STDOUT.txt').read_text()
assert len([n for n in components['root_shared']['nodes'] if n.startswith('tests/test_infernal_search_graders.py::')]) == 54
alignment = base / 'tool_graders_infernal_alignment_2026-10-26_220'
a = read(alignment / 'VERIFICATION_RECEIPT.json')
for name, digest in a['implementation_sha256'].items():
    assert pin(name) == digest
assert '196 passed' in a['commands'][0]['stdout'] and a['commands'][0]['exit_code'] == 0
assert '54 passed' in (alignment / 'PYTEST_FINAL.txt').read_text()

binding_qualification = read(base / 'tool_graders_infernal_binding_2026-10-26_229/SOURCE_QUALIFICATION_001.json')
binding_change = read(base / 'tool_graders_infernal_root_2026-10-26_228/BINDING_TEST_SOURCE_CHANGE_001.json')
assert binding_qualification['method_source_changes'] == [binding_change['changed_function']] == ['ExecutionEpisodes.received_form_references']
binding_receipt = read(components['binding']['receipt'])
assert [name for name in binding_receipt['source_hashes_before'] if binding_receipt['source_hashes_before'][name] != binding_receipt['source_hashes_after'][name]] == ['gene_annotation_episode/execution_episodes.py']
shared_receipt = read(components['root_shared']['receipt'])
assert [name for name in shared_receipt['source_hashes_before'] if shared_receipt['source_hashes_before'][name] != shared_receipt['source_hashes_after'][name]] == ['gene_annotation_episode/native_infernal_results.py']

for directory in sorted(base.glob('tool_graders_infernal*_2026-10-26_*')):
    if directory == HERE or int(directory.name.rsplit('_', 1)[1]) not in range(219, 232):
        continue
    for artifact in directory.iterdir():
        if artifact.is_file() and artifact.suffix in ('.md', '.json', '.txt'):
            pin(artifact)
for name in ('AGENTS.md', 'docs/TOOL_GRADER_GOAL_AND_PRINCIPLES_2026-10-24_001.md'):
    pin(name)
pin(__file__)
record = dict(schema='infernal_accounting_preparation_evidence_v1', prepared_at=datetime.now(timezone.utc).isoformat(),
    status='read_only_preparation_no_accounting_application', authority_sha256=AUTHORITY_HASH,
    previous_status_sha256=STATUS_HASH, original_scope_rows=308, original_binding_rows=288, original_alias_rows=622,
    checked_current_226_source_hashes=55, checked_current_231_production_hashes=9, checked_current_231_test_fixture_runner_hashes=6,
    episode_unique_passing_nodes=42, episode_run_counts=run_counts, episode_cases=actual_cases,
    actual_practical_terminal_archives=practical_archives, frame_unique_passing_nodes=64,
    frame_new_passing_nodes=16, frame_shared_passing_nodes=48,
    unresolved_existing_shared_failures=p['unchanged_existing_failures'],
    component_receipts=components, acquisition_unique_cases=99, publication_followup_overlaps_full=True,
    cmalign_count_qualification='The older standalone PYTEST_FINAL.txt records54 passes at that checkpoint. The final current-source five-module receipt records196 broader overlapping passes. No standalone55-pass receipt is claimed.',
    source_qualifications=[
        'The original219 search reader pin was superseded by the --oskip correction; its54 cases passed again inside root228 current-reader151-case run.',
        'The47 binding run changed only unconsumed ExecutionEpisodes.received_form_references; explicit additive qualification retained.',
        'The151 shared run changed native_infernal_results outside the consumed cases; no frozen-all-source claim.',
        'Episode226 run004 exited1 on a real receiver leak after30passes; run0068passes had four concurrent presentation edits; stable run0074passes verifies the corrected actual receiver.',
        'The64 presentation passes combine16 new and48 shared identities across overlapping runs; four existing root-tool failures match the no-op baseline and remain unresolved.'
    ],
    accounting_executed_tests=False, accounting_executed_scientific_tools=False,
    complete_scientific_tools_claimed=0, file_sha256=dict(sorted(FILES.items())))
with (HERE / 'EVIDENCE_AUDIT_001.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(preparation=str((HERE / 'EVIDENCE_AUDIT_001.json').relative_to(ROOT)),
    pinned_files=len(FILES), episode_passing_nodes=42, frame_passing_nodes=64,
    unresolved_existing_shared_failures=4, accounting_applied=False)))
