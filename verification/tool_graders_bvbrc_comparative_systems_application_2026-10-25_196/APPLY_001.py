#!/usr/bin/env python3
"""Review/check or apply exactly the frozen ComparativeSystems delta after 182.

This developer utility is never imported by the deployed Workflow. Check-only
does no application, runtime import, test execution, process polling or retry.
Every invocation writes fresh receipts here; application requires all evidence.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
IMPL = ROOT / 'verification/tool_graders_bvbrc_comparative_systems_implementation_2026-10-25_186'
PROTEOME = ROOT / 'verification/tool_graders_bvbrc_proteome_directional_integration_2026-10-25_182'
CANDIDATE = IMPL / 'candidate'
MANIFEST_SHA256 = '1df45bee024a3458d9095c1d272d7f22279f03d031c93f4264ec26ba86396961'
POST_PROBE_SHA256 = 'b35923fe605155302d15e08503856ff43be17fd8d9df3337d8d07347676d888d'
PIN = '118aae7a8a9470b9a7cb2e0f081853ac6730c98e1710ac9018a312312699b68f'
WORKFLOW_CASE = 'test_actual_selected_tool_shared_workflow_native_publication_and_typed_parent_return'
OLD_HISTORY_CASE = 'test_latest_invalid_keeps_original_named_history_and_authenticates_whole_parameters'
FINAL_HISTORY_CASES = {
    'test_latest_partial_keeps_original_named_history_and_authenticates_whole_parameters',
    'test_completed_original_assignment_rejects_another_selected_download'}


class PrerequisiteError(ValueError):
    pass


class PendingPrerequisite(FileNotFoundError):
    pass


def require(condition, message):
    if not condition:
        raise PrerequisiteError(message)


def sha(path):
    if path.is_symlink():
        raise PrerequisiteError('symlink_not_permitted:' + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def read(path):
    if not path.exists():
        raise PendingPrerequisite(str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path))
    return json.loads(path.read_text())


def safe_path(base, relative):
    require(isinstance(relative, str) and str(PurePosixPath(relative)) == relative,
            'noncanonical_relative_path:' + str(relative))
    require(not PurePosixPath(relative).is_absolute() and '..' not in PurePosixPath(relative).parts,
            'unsafe_relative_path:' + relative)
    result = base / relative
    for current in (result, *result.parents):
        if current == base:
            break
        require(not current.is_symlink(), 'symlink_not_permitted:' + str(current))
    require(result.resolve().is_relative_to(base.resolve()), 'path_outside_base:' + relative)
    return result


def save(path, value):
    require(path.resolve().is_relative_to(HERE), 'receipt_outside_application_directory')
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def tree_sources(base, directories):
    paths = {base / 'pyproject.toml'}
    for directory in directories:
        top = safe_path(base, directory)
        require(top.is_dir(), 'missing_source_directory:' + str(top))
        for current, children, files in os.walk(top, followlinks=False):
            for child in children:
                require(not (Path(current) / child).is_symlink(), 'symlink_source_directory')
            children[:] = [child for child in children if child != '__pycache__']
            for filename in files:
                path = Path(current) / filename
                if path.suffix not in ('.pyc', '.pyo'):
                    paths.add(path)
    return {str(path.relative_to(base)): sha(path) for path in sorted(paths)}


def candidate_snapshot():
    return tree_sources(CANDIDATE, ('gene_annotation_episode', 'method_loop', 'tests', 'research', 'verification'))


def production_snapshot(manifest):
    result = tree_sources(ROOT, ('gene_annotation_episode', 'method_loop', 'tests'))
    for name in manifest['candidate_sources']:
        if name.startswith(('research/', 'verification/')):
            result[name] = sha(safe_path(ROOT, name))
    return result


def differences(actual, expected):
    return [{'path': name, 'expected_sha256': expected.get(name), 'actual_sha256': actual.get(name)}
            for name in sorted(set(actual) | set(expected)) if actual.get(name) != expected.get(name)]


def match_map(actual, expected, label):
    changes = differences(actual, expected)
    require(set(actual) == set(expected) and not changes,
            label + ':' + json.dumps(changes[:25], sort_keys=True))


def candidate_rows(rows, manifest):
    for row in rows:
        path = Path(row['path'])
        name = str(path.relative_to(CANDIDATE)) if path.is_absolute() else str(path)
        safe_path(CANDIDATE, name)
        require(manifest['candidate_sources'].get(name) == row['sha256'], 'evidence_source_mismatch:' + name)
        if 'bytes' in row or 'byte_count' in row:
            require((CANDIDATE / name).stat().st_size == row.get('bytes', row.get('byte_count')),
                    'evidence_source_size_mismatch:' + name)


def junit(path):
    if not path.is_file():
        raise PendingPrerequisite(str(path))
    result = []
    for node in ET.parse(path).getroot().iter('testcase'):
        outcome = next((name for tag, name in (('failure', 'failed'), ('error', 'error'), ('skipped', 'skipped'))
                        if node.find(tag) is not None), 'passed')
        result.append({'classname': node.attrib['classname'], 'name': node.attrib['name'], 'outcome': outcome})
    identities = {(row['classname'], row['name']) for row in result}
    require(len(identities) == len(result), 'duplicate_test_identity:' + str(path))
    return result


def case_counts(cases):
    return {outcome: sum(row['outcome'] == outcome for row in cases)
            for outcome in ('passed', 'failed', 'error', 'skipped')}


def passing_run(directory, sources, count=None, expected_name=None):
    receipt = read(directory / 'receipt.json')
    require(receipt.get('passed') is True and receipt.get('exit_code') == 0, 'run_not_successful:' + str(directory))
    require(receipt.get('changed_sources') == [], 'run_source_changes:' + str(directory))
    match_map(read(directory / 'source_before.json'), sources, 'run_before')
    match_map(read(directory / 'source_after.json'), sources, 'run_after')
    cases = junit(directory / 'pytest.xml')
    counts = case_counts(cases)
    require(counts == receipt['case_counts'], 'run_case_counts_mismatch')
    require(counts['passed'] > 0 and counts['failed'] == counts['error'] == counts['skipped'] == 0,
            'run_has_nonpassing_cases')
    require(count is None or counts['passed'] == count, 'run_wrong_case_count')
    require(expected_name is None or [row['name'] for row in cases] == [expected_name], 'run_wrong_case_identity')
    recorded = read(directory / 'cases.json')
    require([{key: row[key] for key in ('classname', 'name', 'outcome')} for row in recorded] == cases,
            'run_recorded_cases_differ_from_junit')
    return {'receipt_sha256': sha(directory / 'receipt.json'), 'case_counts': counts,
            'source_count': len(sources), 'cases': cases}


def validate_manifest(manifest):
    require(sha(HERE / 'DELTA_MANIFEST_001.json') == MANIFEST_SHA256, 'manifest_digest_mismatch')
    require(manifest['root'] == str(ROOT) and manifest['candidate'] == str(CANDIDATE), 'wrong_checkout')
    require(manifest['provider_sha256'] == PIN, 'wrong_provider_pin')
    require(sha(HERE / 'DELTA_001.patch') == manifest['delta_patch_sha256'], 'delta_patch_changed')
    before, final = manifest['expected_post182_sources'], manifest['candidate_sources']
    for name in set(before) | set(final):
        safe_path(CANDIDATE, name)
    require(len(manifest['baseline_sources']) == 935 and len(before) == 952 and len(final) == 1045,
            'unexpected_full_map_counts')
    require(set(before) <= set(final), 'deletions_not_allowed')
    changed = {name for name, value in final.items() if before.get(name) != value}
    require(len(changed) == 99 and len(manifest['files']) == 99, 'unexpected_delta_count')
    require({row['path'] for row in manifest['files']} == changed, 'delta_not_exact_full_map_difference')
    for row in manifest['files']:
        require(row['before_sha256'] == before.get(row['path']) and row['candidate_sha256'] == final[row['path']],
                'delta_row_mismatch:' + row['path'])
        require(row['path'].startswith(('gene_annotation_episode/', 'tests/')) or row['path'] == 'pyproject.toml',
                'delta_path_outside_reviewed_scope')
    return manifest['counts']


def check_evidence_hashes(manifest):
    for name, expected in manifest['pinned_evidence'].items():
        path = Path(name) if Path(name).is_absolute() else safe_path(ROOT, name)
        require(sha(path) == expected, 'pinned_evidence_changed:' + name)
    require(sha(HERE / 'POST_APPLY_PROBE_001.py') == POST_PROBE_SHA256, 'post_application_probe_changed')
    require((ROOT / '.venv/bin/python').is_file() and os.access(ROOT / '.venv/bin/python', os.X_OK),
            'production_python_unavailable')
    return {'pinned_files_verified': len(manifest['pinned_evidence'])}


def check_candidate(manifest):
    match_map(candidate_snapshot(), manifest['candidate_sources'], 'candidate_full_freeze_changed')
    for row in manifest['files']:
        require(safe_path(CANDIDATE, row['path']).stat().st_size == row['byte_count'], 'candidate_size_changed')
    return {'unchanged_source_paths': len(manifest['candidate_sources'])}


def check_nc(manifest):
    receipt = read(IMPL / 'evidence_n_review/N_C_AFTER_001.json')
    require(receipt['exit_code'] == 0 and receipt['source_stable'] is True, 'NC_terminal_failure')
    match_map(receipt['source_before'], receipt['source_after'], 'NC_sources_changed')
    candidate_rows([{'path': name, 'sha256': value} for name, value in receipt['source_after'].items()], manifest)
    cases = junit(IMPL / 'evidence_n_review/N_C_AFTER_001.xml')
    require(case_counts(cases) == {'passed': 176, 'failed': 0, 'error': 0, 'skipped': 0}, 'NC_case_counts')
    review = read(IMPL / 'evidence_n_review/ROOT_REVIEW_001.json')
    require(review['verification_after']['receipt_sha256'] == sha(IMPL / 'evidence_n_review/N_C_AFTER_001.json'),
            'NC_root_review_receipt_mismatch')
    return {'passed_cases': 176, 'source_count': len(receipt['source_after'])}


def check_d(manifest):
    receipt = read(IMPL / 'evidence_d/COMMANDS_AND_RESULTS_001.json')
    cases = [row for row in receipt['commands'] if row['log'].endswith('/pytest_attempt_005.log')]
    require(len(cases) == 1 and cases[0]['exit_code'] == 0 and cases[0]['result'] == '54 passed in 5.48s',
            'D_terminal_result_mismatch')
    require('54 passed in 5.48s' in (IMPL / 'evidence_d/pytest_attempt_005.log').read_text(), 'D_log_mismatch')
    rows = read(IMPL / 'evidence_d/SOURCE_HASHES_001.json')['owned_files']
    candidate_rows(rows, manifest)
    return {'passed_cases': 54, 'owned_sources': len(rows)}


def check_p(manifest):
    receipt = read(IMPL / 'evidence_p/P_TERMINAL_RECEIPT_003.json')
    require(receipt['implementation_sha256'] == PIN and receipt['source_snapshot_unchanged'] is True,
            'P_source_or_pin_mismatch')
    require(receipt['pytest']['exit_code'] == 0 and receipt['pytest']['result'] == '127 passed in 127.45s (0:02:07)',
            'P_terminal_result_mismatch')
    require('127 passed in 127.45s' in (IMPL / 'evidence_p/pytest_013.log').read_text(), 'P_log_mismatch')
    require(receipt['live_processes'] == [], 'P_not_released')
    owned = read(IMPL / 'evidence_p/P_OWNED_FILE_MANIFEST_003.json')
    inputs = read(IMPL / 'evidence_p/P_VERIFICATION_INPUTS_003.json')
    require(owned['implementation_sha256'] == inputs['implementation_sha256'] == PIN, 'P_manifest_pin_mismatch')
    candidate_rows(owned['files'] + inputs['dependencies'], manifest)
    return {'passed_cases': 127, 'dependencies': len(inputs['dependencies']), 'owned_sources': len(owned['files'])}


def check_i(manifest):
    old = read(IMPL / 'evidence_i/FINAL_TERMINAL_001.json')
    final = read(IMPL / 'evidence_i/FINAL_TERMINAL_002.json')
    for number, receipt, log in (('001', old, '012'), ('002', final, '013')):
        require(receipt['provider_pin'] == PIN and receipt['source_snapshot_unchanged'] is True, 'I_pin_or_stability')
        require(receipt['junit_sha256'] == sha(IMPL / f'evidence_i/pytest_{log}.xml'), 'I_junit_digest')
        require(receipt['log_sha256'] == sha(IMPL / f'evidence_i/pytest_{log}.log'), 'I_log_digest')
        before = read(IMPL / f'evidence_i/FINAL_SOURCE_BEFORE_{number}.json')
        after = read(IMPL / f'evidence_i/FINAL_SOURCE_AFTER_{number}.json')
        require(before['files'] == after['files'], 'I_source_snapshot_changed')
        require(before['provider_pin'] == after['provider_pin'] == PIN, 'I_source_snapshot_pin')
    old_rows = read(IMPL / 'evidence_i/FINAL_SOURCE_AFTER_001.json')['files']
    new_rows = read(IMPL / 'evidence_i/FINAL_SOURCE_AFTER_002.json')['files']
    old_map = {row['path']: row['sha256'] for row in old_rows}
    new_map = {row['path']: row['sha256'] for row in new_rows}
    require({row['path'] for row in differences(old_map, new_map)} == {'tests/test_bvbrc_comparative_systems_returns.py'},
            'I_correction_changed_unexpected_source')
    candidate_rows(new_rows, manifest)
    candidate_rows(read(IMPL / 'evidence_i/I_OWNED_FILE_MANIFEST_001.json')['files'], manifest)
    previous_cases = junit(IMPL / 'evidence_i/pytest_012.xml')
    corrected_cases = junit(IMPL / 'evidence_i/pytest_013.xml')
    require(old['exit_code'] == 1 and case_counts(previous_cases) == {'passed': 31, 'failed': 1, 'error': 0, 'skipped': 0},
            'I_prior_history_changed')
    require([row['name'] for row in previous_cases if row['outcome'] == 'failed'] == [OLD_HISTORY_CASE],
            'I_unresolved_prior_failure')
    require(case_counts(corrected_cases) == {'passed': 2, 'failed': 0, 'error': 0, 'skipped': 0}
            and {row['name'] for row in corrected_cases} == FINAL_HISTORY_CASES, 'I_corrected_cases_mismatch')
    require(final['exit_code'] is None and final['live_processes'] == []
            and final['runtime_changed_after_pytest012'] is False, 'I_final_terminal_evidence_mismatch')
    require(read(IMPL / 'evidence_i/PROTEOME_PRESERVATION_001.json')['unexpected_changes'] == [],
            'I_proteome_preservation_failure')
    for row in read(IMPL / 'evidence_i/SHARED_DELTA_AUDIT_001.json'):
        require(manifest['expected_post182_sources'][row['file']] == row['baseline_sha256']
                and manifest['candidate_sources'][row['file']] == row['candidate_sha256'], 'I_shared_delta_changed')
    return {'retained_prior_passes': 31, 'corrected_final_passes': 2, 'final_exit_code': None,
            'prior_failed_case': OLD_HISTORY_CASE, 'prior_failure_retained': True,
            'terminal_basis': 'final JUnit and log plus recorded original process closure; no invented exit code'}


def check_package(manifest):
    first = read(IMPL / 'package_verification_001/receipt.json')
    second = read(IMPL / 'package_verification_002/receipt.json')
    require(first['build_exit_code'] == 0 and first['installed_exit_code'] == 1 and first['passed'] is False,
            'package001_history_changed')
    require(second['passed'] is True and second['installed_exit_code'] == 0, 'package002_not_successful')
    require(second['original_build_receipt_sha256'] == sha(IMPL / 'package_verification_001/receipt.json'),
            'package001_002_link_mismatch')
    for dirname, receipt in (('package_verification_001', first), ('package_verification_002', second)):
        require(receipt['provider_sha256'] == PIN and receipt['changed_sources'] == []
                and receipt['source_count'] == 1045, 'package_source_or_pin_mismatch')
        for name in ('source_before.json', 'source_after.json'):
            match_map(read(IMPL / dirname / name), manifest['candidate_sources'], 'package_freeze')
    require(second['probe_sha256'] == sha(IMPL / 'PACKAGE_PROBE_002.py'), 'package_probe_changed')
    require(second['installed_result_sha256'] == sha(IMPL / 'package_verification_002/installed_result.json'),
            'package_result_changed')
    installed = read(IMPL / 'package_verification_002/installed_result.json')
    require(installed['provider_sha256'] == PIN and installed['matches_retained_result'] is True
            and installed['saved_validation_without_scientific_replay'] is True, 'package_facade_result')
    require(installed['native_percent'] == 75 and installed['later_percent'] == 4 / 9 * 100
            and installed['later_operands'] == [4, 9] and installed['native_reference_operands'] == [2, 4]
            and installed['later_reference_operands'] == [3, 4] and installed['active_genome_count'] == 0
            and installed['reference_release'] is None, 'package_numerical_values')
    wheels = list((IMPL / 'package_verification_001/wheel').glob('*.whl'))
    require(len(wheels) == 1 and sha(wheels[0]) == first['wheel_sha256'] == second['wheel_sha256'], 'package_wheel_changed')
    with zipfile.ZipFile(wheels[0]) as archive:
        require(set(first['required_packaged_files']) <= set(archive.namelist()), 'wheel_missing_required_data')
        for name in archive.namelist():
            if name.startswith(('gene_annotation_episode/', 'method_loop/')) and not name.endswith('/'):
                require(hashlib.sha256(archive.read(name)).hexdigest() == manifest['candidate_sources'].get(name),
                        'wheel_byte_mismatch:' + name)
    return {'package001_build_exit_code': 0, 'package001_installed_exit_code': 1,
            'package002_installed_exit_code': 0, 'unchanged_sources': 1045,
            'corrected_probe_only': 'Restored qualified_data_inputs and qualified_producer_evidence JSON lists to tuples',
            'numerical_answers': second['numerical_answers']}


def check_182_application(manifest):
    receipt = read(PROTEOME / 'APPLICATION_RECEIPT_001.json')
    require(receipt['production_applied'] is True and receipt['applied_facade_verified'] is True
            and receipt['unexpected_sources'] == [], 'proteome_application_not_successful')
    require(receipt['applied_probe_exit_code'] == 0, 'proteome_applied_probe_failed')
    require(receipt['unchanged_v1_implementation_sha256'] == manifest['proteome_v1_sha256']
            and receipt['v2_implementation_sha256'] == manifest['proteome_v2_sha256'], 'proteome_application_pins')
    composed = read(IMPL / 'PROTEOME_COMPOSITION_RECEIPT_001.json')['files']
    require(len(receipt['written_paths']) == 25 and set(receipt['written_paths']) == {row['path'] for row in composed},
            'proteome_written_paths_mismatch')
    require({row['path']: row['candidate_sha256'] for row in receipt['files']} ==
            {row['path']: row['after_sha256'] for row in composed}, 'proteome_applied_delta_mismatch')
    require(receipt['source_count'] == 952, 'proteome_application_source_count')
    match_map(read(PROTEOME / 'APPLICATION_SOURCE_AFTER_001.json'), manifest['expected_post182_sources'],
              'proteome_application_source_after')
    require(read(PROTEOME / 'applied_native_check_001/result.json') ==
            read(PROTEOME / 'package_verification_001/installed_result.json'), 'proteome_applied_facade_mismatch')
    require(receipt['delta_manifest_sha256'] == sha(PROTEOME / 'DELTA_MANIFEST_001.json'), 'proteome_delta_manifest_changed')
    return {'receipt_sha256': sha(PROTEOME / 'APPLICATION_RECEIPT_001.json'), 'copied_files': 25,
            'applied_facade_verified': True}


def check_182_host(manifest):
    sources = read(PROTEOME / 'FREEZE_INDEPENDENT_002.json')['sources']
    return passing_run(PROTEOME / 'final_host_001', sources)


def check_workflow(manifest):
    result = passing_run(IMPL / 'final_workflow_001', manifest['candidate_sources'], 1, WORKFLOW_CASE)
    receipt = read(IMPL / 'final_workflow_001/receipt.json')
    require(receipt['provider_sha256'] == PIN and receipt['source_count'] == 1045, 'Workflow_pin_or_source_count')
    require(receipt['harness_sha256'] == sha(IMPL / 'VERIFY_WORKFLOW_001.py'), 'Workflow_harness_changed')
    require(receipt['source_before_sha256'] == sha(IMPL / 'final_workflow_001/source_before.json'), 'Workflow_freeze_changed')
    result['scope'] = 'Actual shared Workflow with controlled choices and transport; no live service verification'
    return result


def check_production(manifest):
    actual = production_snapshot(manifest)
    if actual == manifest['expected_post182_sources']:
        return {'state': 'exact_expected_post182', 'source_count': len(actual)}
    if actual == manifest['baseline_sources'] and not (PROTEOME / 'APPLICATION_RECEIPT_001.json').exists():
        raise PendingPrerequisite('production_still_matches_original_baseline; proteome182 application pending')
    raise PrerequisiteError('production_differs_from_exact_post182:' +
                            json.dumps(differences(actual, manifest['expected_post182_sources']), sort_keys=True))


def preflight(manifest):
    checks = {}
    operations = (
        ('manifest', validate_manifest), ('pinned_evidence', check_evidence_hashes),
        ('candidate_full_freeze', check_candidate), ('N_C_176', check_nc), ('D_54', check_d),
        ('P_127', check_p), ('I_final', check_i), ('package_002', check_package),
        ('proteome182_final_host', check_182_host), ('proteome182_application', check_182_application),
        ('comparative186_final_Workflow', check_workflow), ('production_after182', check_production))
    for name, operation in operations:
        try:
            checks[name] = {'status': 'passed', 'details': operation(manifest)}
        except PendingPrerequisite as error:
            checks[name] = {'status': 'pending', 'reason': str(error)}
        except Exception as error:
            checks[name] = {'status': 'failed', 'error_type': type(error).__name__, 'reason': str(error)}
    return {'checks': checks, 'ready_to_apply': all(row['status'] == 'passed' for row in checks.values()),
            'pending_prerequisites': [name for name, row in checks.items() if row['status'] == 'pending'],
            'failed_prerequisites': [name for name, row in checks.items() if row['status'] == 'failed']}


def apply(manifest, out, receipt):
    # No implicit resume or rollback. This complete second check precedes the
    # first mutation and is retained independently of the initial preflight.
    refreshed = preflight(manifest)
    save(out / 'PREFLIGHT_IMMEDIATELY_BEFORE_APPLY.json', refreshed)
    require(refreshed['ready_to_apply'], 'prerequisite_changed_before_application')
    save(out / 'SOURCE_BEFORE.json', production_snapshot(manifest))
    receipt['application_started'] = True
    for index, row in enumerate(manifest['files'], 1):
        source = safe_path(CANDIDATE, row['path'])
        destination = safe_path(ROOT, row['path'])
        require(sha(destination) == row['before_sha256'], 'destination_changed_before_copy:' + row['path'])
        data = source.read_bytes()
        require(hashlib.sha256(data).hexdigest() == row['candidate_sha256'] and len(data) == row['byte_count'],
                'source_changed_before_copy:' + row['path'])
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name('.' + destination.name + '.apply196.' + out.name + '.tmp')
        receipt['temporary_paths'].append(str(temporary.relative_to(ROOT)))
        with temporary.open('xb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        require(sha(temporary) == row['candidate_sha256'], 'temporary_copy_byte_mismatch')
        require(sha(destination) == row['before_sha256'], 'destination_changed_during_copy:' + row['path'])
        temporary.replace(destination)
        receipt['written_paths'].append(row['path'])
        require(sha(destination) == row['candidate_sha256'], 'copied_byte_mismatch:' + row['path'])
        save(out / f'COPY_{index:03d}.json', {'path': row['path'], 'before_sha256': row['before_sha256'],
            'actual_after_sha256': sha(destination), 'candidate_sha256': row['candidate_sha256']})
    match_map(production_snapshot(manifest), manifest['candidate_sources'], 'production_target_mismatch')
    check_candidate(manifest)
    check_evidence_hashes(manifest)
    receipt['production_applied'] = True
    command = [str(ROOT / '.venv/bin/python'), '-I', '-B', str(HERE / 'POST_APPLY_PROBE_001.py')]
    save(out / 'PROBE_COMMAND.json', {'argv': command, 'cwd': str(out)})
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    environment.pop('PYTHONPATH', None)
    result = subprocess.run(command, cwd=out, env=environment, capture_output=True, text=True)
    for name, value in (('PROBE_STDOUT.log', result.stdout), ('PROBE_STDERR.log', result.stderr)):
        with (out / name).open('x') as stream:
            stream.write(value)
    receipt['applied_probe_exit_code'] = result.returncode
    require(result.returncode == 0, 'applied_facade_probe_failed; see retained stderr')
    answer = json.loads(result.stdout)
    save(out / 'PROBE_RESULT.json', answer)
    require(answer['installed_equivalent'] == read(IMPL / 'package_verification_002/installed_result.json'),
            'applied_facade_differs_from_installed_result')
    require(answer['pins'] == {'comparative': PIN, 'proteome_v1': manifest['proteome_v1_sha256'],
            'proteome_v2': manifest['proteome_v2_sha256']}, 'applied_pin_mismatch')
    require(answer['no_candidate_imports'] is True, 'candidate_runtime_import_detected')
    receipt['applied_facade_verified'] = True
    receipt['applied_pins'] = answer['pins']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check-only', action='store_true')
    group.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    mode = 'apply' if args.apply else 'check_only'
    out = HERE / (mode + '_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '_' + str(time.time_ns()))
    out.mkdir(exist_ok=False)
    clock = time.monotonic()
    receipt = {'mode': mode, 'started_at': datetime.now(timezone.utc).isoformat(),
        'harness_sha256': sha(Path(__file__)), 'manifest_sha256': sha(HERE / 'DELTA_MANIFEST_001.json'),
        'application_started': False, 'production_applied': False, 'applied_facade_verified': False,
        'live_service_execution_verified': False, 'written_paths': [], 'temporary_paths': [],
        'ready_to_apply': False, 'passed': False, 'no_automatic_retry_or_rollback': True}
    manifest = None
    code = 1
    try:
        manifest = read(HERE / 'DELTA_MANIFEST_001.json')
        # Reject a changed authorization manifest before any its data drive checks.
        validate_manifest(manifest)
        receipt.update(preflight(manifest))
        save(out / 'PREFLIGHT.json', receipt)
        if not receipt['ready_to_apply']:
            code = 1 if receipt['failed_prerequisites'] else 2
        elif args.check_only:
            code = 0
        else:
            apply(manifest, out, receipt)
            code = 0
    except BaseException as error:
        receipt.update(error_type=type(error).__name__, error=str(error))
        with (out / 'ERROR.log').open('x') as stream:
            stream.write(traceback.format_exc())
        code = 1
    finally:
        if receipt['application_started'] and manifest is not None:
            try:
                after = production_snapshot(manifest)
                save(out / 'APPLICATION_SOURCE_AFTER.json', after)
                receipt['unexpected_sources'] = differences(after, manifest['candidate_sources'])
                receipt['source_count'] = len(after)
                if receipt['unexpected_sources'] or candidate_snapshot() != manifest['candidate_sources']:
                    code = 1
            except Exception as error:
                receipt['post_application_snapshot_error'] = str(error)
                code = 1
        receipt.update(exit_code=code, ended_at=datetime.now(timezone.utc).isoformat(),
                       elapsed_seconds=time.monotonic() - clock)
        receipt['passed'] = bool(args.apply and code == 0 and receipt['production_applied']
                                 and receipt['applied_facade_verified'])
        receipt['status'] = ('application_verified' if receipt['passed'] else
            'application_partial_failure' if receipt['application_started'] else
            'preflight_ready_no_application' if code == 0 else
            'preflight_pending_no_application' if code == 2 else 'preflight_failed_no_application')
        save(out / 'APPLICATION_RECEIPT.json' if args.apply else out / 'CHECK_RECEIPT.json', receipt)
        print(json.dumps({'receipt_directory': str(out), **{key: receipt.get(key) for key in
            ('status', 'ready_to_apply', 'passed', 'production_applied', 'applied_facade_verified',
             'pending_prerequisites', 'failed_prerequisites', 'written_paths', 'exit_code')}}))
    return code


if __name__ == '__main__':
    sys.exit(main())
