"""Record verification receipts without running scientific calculations."""
import hashlib
import inspect
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent
REL = str(HERE.relative_to(ROOT))
from gene_annotation_episode.bvbrc_metacats_inputs import extract_metacats_sheet
from gene_annotation_episode.bvbrc_metacats_grader import calculate_metacats
from gene_annotation_episode.bvbrc_metacats_provider_contracts import (
    validate_metacats_sheet, validate_metacats_parameters, validate_metacats_components,
)


def fingerprint(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            'sha256': hashlib.sha256(data).hexdigest(), 'byte_count': len(data)}


def save(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return fingerprint(HERE / name)


def test_result(stem):
    document = ET.parse(HERE / (stem + '.xml')).getroot()
    suites = list(document.iter('testsuite'))
    result = {key: sum(int(s.get(key, 0)) for s in suites)
              for key in ('tests', 'failures', 'errors', 'skipped')}
    result['passed'] = result['tests'] - result['failures'] - result['errors'] - result['skipped']
    result['xml_seconds'] = sum(float(s.get('time', 0)) for s in suites)
    result['log'] = fingerprint(HERE / (stem + '.log'))
    result['xml'] = fingerprint(HERE / (stem + '.xml'))
    result['case_ids'] = [[t.get('classname'), t.get('name')] for t in document.iter('testcase')]
    return result


def pytest_command(arguments, stem):
    return f'.venv/bin/python -m pytest -q {arguments} --junitxml={REL}/{stem}.xml > {REL}/{stem}.log 2>&1'


def main():
    replay = json.loads((HERE / 'FINAL_REPLAY_003.json').read_text())
    examples = json.loads((HERE / 'EXAMPLE_MANIFEST_001.json').read_text())
    assert replay['sources_before'] == replay['sources_after']
    for record in replay['sources_after']:
        assert fingerprint(ROOT / record['path']) == record
    owned = [record for record in replay['sources_after'] if Path(record['path']).name in (
        'bvbrc_metacats_provider_contracts.py', 'bvbrc_metacats_inputs.py', 'bvbrc_metacats_grader.py')]
    tests = [fingerprint(ROOT / 'tests' / name) for name in (
        'test_bvbrc_metacats_provider.py', 'test_bvbrc_metacats_provider_replay.py')]
    freeze = json.loads((ROOT / 'verification/tool_graders_bvbrc_msa_metacats_provider_boundaries_2026-10-25/PROVIDER_FREEZE_001.json').read_text())
    frozen = freeze['files'] + freeze['unchanged_previously_pinned_files'] + freeze['accepted_root_addenda'] + [freeze['accepted_xmfa_pure_contract']]
    for record in frozen:
        assert fingerprint(ROOT / record['path']) == record
    goal = fingerprint(Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt'))
    assert goal['sha256'] == '11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7'
    source_record = save('SOURCE_HASHES_FINAL_001.json', {
        'owned_production': owned, 'owned_tests': tests, 'dependencies': replay['sources_after'][3:],
        'goal': goal, 'all_15_frozen_records_match': True, 'frozen_records': frozen,
        'additional_authority': [fingerprint(ROOT / path) for path in (
            'AGENTS.md', 'docs/TOOL_GRADER_GOAL_AND_PRINCIPLES_2026-10-24_001.md',
            'verification/tool_graders_bvbrc_msa_metacats_implementation_2026-10-25/ACCEPTED_PROVIDER_WORKLOADS_019.json',
            'verification/tool_graders_bvbrc_msa_metacats_implementation_2026-10-25/ORIGINAL_GROUP_BINDING_CLARIFICATION_016.md',
            'verification/tool_graders_bvbrc_msa_metacats_implementation_2026-10-25/PROVIDER_VALIDATION_EXPORTS_018.md')],
        'scope': 'Only the three owned production files and two owned test files were created by this workload; all verification writes stay in its assigned directory.'})
    signatures = save('EXPORTED_SIGNATURES_001.json', [{'module': f.__module__, 'name': f.__name__,
        'signature': str(inspect.signature(f))} for f in (
            extract_metacats_sheet, validate_metacats_sheet, calculate_metacats,
            validate_metacats_parameters, validate_metacats_components)])
    final = []
    commands = [
        ('provider-final-014', 'tests/test_bvbrc_metacats_provider.py tests/test_bvbrc_metacats_provider_replay.py'),
        ('category-labels-015', 'tests/test_bvbrc_metacats_provider.py::test_repeated_headings_blank_and_comma_groups_remain_category_specific'),
        ('dependency-regression-007', ' '.join('tests/' + name for name in (
            'test_bvbrc_metacats_formats.py', 'test_bvbrc_metacats_format_contracts.py', 'test_bvbrc_metacats_input_formats.py',
            'test_bvbrc_metacats_calculators.py', 'test_bvbrc_metacats_biological_calculators.py',
            'test_bvbrc_metacats_expected_adequacy.py', 'test_bvbrc_metacats_count_identity_v2.py',
            'test_bvbrc_alignment_values.py', 'test_bvbrc_alignment_associations.py', 'test_bvbrc_metacats_associations.py',
            'test_bvbrc_msa_calculators.py', 'test_phylogeny_calculators.py'))),
    ]
    for stem, arguments in commands:
        result = test_result(stem)
        assert result['failures'] == result['errors'] == result['skipped'] == 0
        final.append({'command': pytest_command(arguments, stem), **result})
    case_ids = {tuple(case) for result in final[:2] for case in result['case_ids']}
    assert len(case_ids) == 66 and final[2]['passed'] == 432
    test_record = save('TEST_RESULTS_001.json', {
        'final_commands': final, 'distinct_provider_checks': len(case_ids), 'dependency_checks': 432,
        'note': 'The full run had 65 tests. One final category-label fixture was added and tested separately; no production source changed between those runs.',
        'initial_and_intermediate_results': [test_result(stem) for stem in (
            'initial-001', 'intermediate-002', 'scoped-003', 'scoped-004', 'scoped-005',
            'provider-final-006', 'review-failure-008', 'review-failure-009', 'scoped-010',
            'provider-final-011', 'empty-family-failure-012', 'scoped-013')],
        'failure_explanations': [fingerprint(HERE / name) for name in (
            'INITIAL_FAILURES_001.json', 'REVIEW_CORRECTION_002.md', 'EMPTY_FAMILY_CORRECTION_003.md')],
        'final_replay_command': f'.venv/bin/python {REL}/replay_final_003.py > {REL}/replay-final-003.log 2>&1',
        'final_replay_record': fingerprint(HERE / 'FINAL_REPLAY_003.json'),
        'final_replay_log': fingerprint(HERE / 'replay-final-003.log')})
    save('HANDOFF_001.json', {
        'status': 'pure_provider_workload_D_implemented_and_verified',
        'complete_scientific_tool_or_episode_path_claimed': False,
        'source_hashes': source_record, 'exports': signatures, 'tests': test_record,
        'complete_examples': fingerprint(HERE / 'EXAMPLE_MANIFEST_001.json'),
        'final_source_replay': fingerprint(HERE / 'FINAL_REPLAY_003.json'),
        'selected_numerical_values': fingerprint(HERE / 'NUMERICAL_SUMMARY_001.json'),
        'accepted_interpretations': fingerprint(HERE / 'ACCEPTED_INTERPRETATIONS_001.md'),
        'case_names': [r['case'] for r in examples['cases']],
        'complete_saved_artifacts': 21, 'retained_native_files_including_original_receipts': 84,
        'new_native_service_or_hpc_executions': 0,
        'original_goal_full_read_and_final_purpose_all_16_principles_reset': True,
        'final_exact_io_sheet_parameters_and_validation_contracts_reread': True,
        'remaining': ['adapter slot resolution and original request authentication',
            'tool information and configured callable binding', 'saved child return and host/episode wiring',
            'selected child-to-parent complete path verification', 'live resource and deployed version verification'],
        'validation_limit': 'Saved validators check declared shape, source/request/population/identity relationships without recomputing statistics; external custody remains adapter-owned.'})
    print(json.dumps({'provider_checks': len(case_ids), 'dependency_checks': 432,
        'saved_artifacts': 21, 'retained_native_files': 84, 'goal_sha256': goal['sha256']}))


if __name__ == '__main__':
    main()
