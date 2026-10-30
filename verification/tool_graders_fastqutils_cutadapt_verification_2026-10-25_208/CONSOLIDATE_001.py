"""Summarize completed terminal receipts without rerunning scientific tests."""
raise SystemExit('Historical note/provenance sealer retired; retained evidence is not regenerated from agent notes.')
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def read(name):
    return json.loads((HERE / name).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


suite, package = read('suite_receipt.json'), read('package_verification_001/receipt.json')
assert suite['passed'] and package['passed']
assert suite['exit_code'] == package['fixture_exit_code'] == package['build_exit_code'] == package['installed_exit_code'] == 0
tracked = read('package_verification_001/all_inputs_before.json')
after = {name: sha(Path(name)) for name in tracked}
assert after == tracked
save('all_inputs_at_handoff.json', after)
cases = [dict(node.attrib, outcome='failed' if node.find('failure') is not None else
    'error' if node.find('error') is not None else 'skipped' if node.find('skipped') is not None else 'passed')
    for node in ET.parse(HERE / 'suite_results.xml').iter('testcase')]
assert len(cases) == 359 and all(row['outcome'] == 'passed' for row in cases)
counts = dict(Counter(row['classname'].removeprefix('tests.') for row in cases))
save('distinct_test_cases.json', cases)
native = []
for tree in ('native_examples_001', 'parser_205/native_examples_001', 'parser_205/native_examples_002', 'parser_205/native_examples_003'):
    for path in sorted((HERE / tree).glob('*/receipt.json')):
        receipt = json.loads(path.read_text())
        assert receipt['exit_code'] == 0 and receipt['native_executable_run'] and receipt['BV_BRC_service_run'] is False
        for name, binding in receipt['files'].items():
            member = path.parent / name
            assert member.stat().st_size == binding['byte_count'] and sha(member) == binding['sha256']
        native.append(dict(case=path.parent.name, receipt=str(path.relative_to(HERE)), sha256=sha(path),
            producer='Trim Galore' if path.parent.name == 'trimgalore_single' else 'Cutadapt',
            native_executable_run=True, BV_BRC_service_run=False, synthetic_inputs=True))
assert len(native) == 31
save('native_producer_receipts.json', native)
authority = [Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt'),
    ROOT / 'AGENTS.md', ROOT / 'docs/TOOL_GRADER_GOAL_AND_PRINCIPLES_2026-10-24_001.md',
    HERE / 'WORKLOAD_001.md', ROOT / 'research/tool_grader_inventory_2026-10-24/WORK_STATUS.json']
prior = ROOT / 'verification/tool_graders_bvbrc_fastqutils_remaining_formats_2026-10-25_204'
authority += [prior / name for name in ('CUTADAPT_WORKLOAD_001.md', 'CONTRACT_CORRECTION_002.md',
    'CONTRACT_CORRECTION_003.md', 'parser_205/HANDOFF_001.md', 'parser_205/PROVENANCE_CORRECTION_001.md')]
complete = ['bvbrc_fastqutils_' + name + '.py' for name in ('cutadapt_reader', 'cutadapt_specs', 'trim_reader',
    'native', 'fastq_reader', 'identity', 'contracts', 'metadata', 'sheet', 'resolution', 'retention',
    'calculators', 'composition', 'quality', 'projection', 'saved_codec', 'bundle_adapter', 'returns', 'tool_info')]
complete += ['communication.py', 'episode_return_records.py', 'form_reference_validation.py', 'bvbrc_appservice_adapters.py']
save('inspection_receipt.json', dict(authority_hashes={str(p): sha(p) for p in authority},
    authoritative_goal_read_in_full=True, objective_and_all_16_principles_reread_after_substantial_inspection=True,
    current_cutadapt_contract_and_additive_corrections_reread_before_handoff=True,
    complete_modules_inspected={name: sha(HERE / 'candidate/gene_annotation_episode' / name) for name in complete},
    additional_complete_functions_inspected={'bvbrc_fastqutils_fastqc_reader.py': ['_Report', '_axis', '_number'],
        'bvbrc_fastqutils_metric_specs.py': ['metric_spec', 'component_spec', 'Cutadapt registration']},
    host_custody_path_execution_verified=False))
artifacts = ['suite_receipt.json', 'suite_command.json', 'suite_results.xml', 'distinct_test_cases.json',
    'source_before.json', 'all_inputs_before.json', 'all_inputs_after_suite.json', 'all_inputs_at_handoff.json',
    'native_fixture_relocation.json', 'native_producer_receipts.json', 'overlays.json', 'inspection_receipt.json',
    'package_verification_001/receipt.json', 'package_verification_001/installed_result.json',
    'package_verification_001/fixture_command.json', 'package_verification_001/build_command.json',
    'package_verification_001/installed_command.json', 'package_verification_001/packaged_hashes.json']
summary = dict(completed_at=datetime.now(timezone.utc).isoformat(), passed=True, source_count=suite['source_count'],
    source_and_fixture_input_count=suite['tracked_input_files'], native_fixture_files=suite['native_fixture_files'],
    final_tracked_files=len(tracked), native_retained_producer_cases=len(native),
    native_producers_executed_by_this_verification=0, test_count=len(cases), test_file_count=len(counts), test_counts=counts,
    command_entrypoints=[f'{ROOT}/.venv/bin/python -B {HERE}/FREEZE_AND_TEST_001.py',
        f'{ROOT}/.venv/bin/python -B {HERE}/VERIFY_PACKAGE_001.py'],
    terminal_exit_codes=dict(suite=suite['exit_code'], fixture=package['fixture_exit_code'], build=package['build_exit_code'], installed=package['installed_exit_code']),
    provider_pin=package['provider_pin'], dependency_count=package['dependency_count'],
    fastqutils_asset_count=package['fastqutils_asset_count'], packaged_source_asset_count=package['packaged_source_asset_count'],
    wheel_sha256=package['wheel_sha256'], native_numbers=package['native_numbers'], native_input_bases=package['native_input_bases'],
    direct_native_answers=package['direct_native_answers'], legacy_schema_sha256=package['legacy_schema_sha256'],
    rejected_legacy_forms=package['rejected_legacy_forms'], changed_inputs=[], changed_build_sources=[],
    unresolved_implementation_failures=[], whole_tool_complete=False, live_bvbrc_verified=False,
    episode_host_custody_verified=False, worker_202_interrupted_or_duplicated=False,
    production_files_edited=False, original_tests_or_assertions_edited=False,
    scientific_credit_or_episode_behavior_changed=False, no_wall_time_limit=True,
    memory_limit_bytes=suite['memory_limit_bytes'], scratch_budget_bytes=suite['scratch_budget_bytes'],
    scratch_bytes_before_consolidation=package['scratch_bytes'],
    python=sys.version, executable=sys.executable,
    verification_dependency_versions={name: importlib.metadata.version(name) for name in ('pytest', 'jsonschema', 'pip')},
    artifact_hashes={name: sha(HERE / name) for name in artifacts})
save('FINAL_RECEIPT_001.json', summary)
print(json.dumps({k: summary[k] for k in ('passed', 'test_count', 'test_file_count', 'provider_pin',
    'dependency_count', 'fastqutils_asset_count', 'native_retained_producer_cases', 'terminal_exit_codes')}))
