"""Combine terminal and byte-identity evidence without rerunning the test."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def main():
    run = HERE / ('host_saved_' + sys.argv[1])
    receipt = read(run / 'receipt.json')
    summary = read(run / 'evidence/verified_summary.json')
    assert receipt['passed'] and summary['passed']
    assert set(receipt['restored_file_changes']) <= {
        'state/state.sqlite3', 'state/state.sqlite3-shm', 'state/state.sqlite3-wal'}
    cases = list(ET.parse(run / 'results.xml').getroot().iter('testcase'))
    assert len(cases) == 1 and not any(child.tag in {'failure', 'error', 'skipped'}
                                      for case in cases for child in case)
    tracked = read(run / 'tracked_before.json')
    after = {name: sha(Path(name)) if Path(name).is_file() else None for name in tracked}
    changed = [name for name in tracked if tracked[name] != after[name]]
    save('all_inputs_at_handoff.json', after)
    assert not changed, changed
    audits = read(run / 'read_input_check.json')
    assert audits['changed_inputs'] == []
    modules = read(run / 'evidence/actual_import_origins.json')
    production = [row for row in modules if row['module'].split('.', 1)[0] in ('gene_annotation_episode', 'method_loop')]
    assert all(Path(row['path']).is_relative_to(HERE / 'candidate') for row in production)
    copied = read(HERE / 'copy_manifest.json')
    helper_copies = [row for row in copied if '_198/candidate/tests/' in row['source']]
    failures = []
    for previous in sorted([*HERE.glob('host_run_*/receipt.json'), *HERE.glob('host_saved_*/receipt.json')]):
        value = read(previous)
        if not value['passed']:
            failures.append(dict(path=str(previous), exit_code=value.get('exit_code'),
                phase=value.get('phase', 'pytest'),
                qualification=({'host_run_001': 'New 209 iterator/list assertion before selected service execution.',
                    'host_run_002': 'New 209 fixture-specific diagnostic assertion after actual host publication and both typed admissions.',
                    'host_saved_003': 'Runner preflight detected pytest current symlink as a duplicate state path.'}[previous.parent.name])))
    original = HERE / 'host_run_002'
    native = read(original / 'evidence/fixture_declarations.json')['native_inputs']
    original_receipt = read(original / 'receipt.json')
    original_cases = list(ET.parse(original / 'results.xml').getroot().iter('testcase'))
    assert len(original_cases) == 1 and original_receipt['exit_code'] == 1
    failure = original_cases[0].find('failure')
    assert failure is not None and 'stage_execution_unknown' in failure.attrib.get('message', '')
    assert original_receipt['changed_inputs'] == []
    final = dict(**summary, terminal_receipt=str(run / 'receipt.json'),
        completed_at=datetime.now(timezone.utc).isoformat(),
        authoritative_source_candidate_paths=read(HERE / 'freeze_receipt.json')['original_candidate_paths'],
        copied_helper_modules=len(read(HERE / 'helper_dependency_closure.json')),
        copied_helper_and_fixture_paths=len(helper_copies),
        tracked_source_and_input_paths=len(tracked), changed_source_and_input_paths=changed,
        observed_read_input_paths=audits['input_count'], changed_observed_read_inputs=audits['changed_inputs'],
        native_inputs=native, production_import_count=len(production),
        all_production_imports_under_frozen_candidate=True,
        actual_pytest_case_count=len(cases), pytest_case_names=[case.attrib['name'] for case in cases],
        original_full_path_test_status='failed_fixture_specific_assertion_after_both_typed_admissions',
        corrected_saved_evidence_test_status='passed', acquisition_path_repeated=False,
        original_full_path_elapsed_seconds=original_receipt['elapsed_seconds'],
        restored_file_changes=receipt['restored_file_changes'],
        exit_code=receipt['exit_code'], elapsed_seconds=receipt['elapsed_seconds'],
        child_peak_rss_kib=receipt['child_peak_rss_kib'],
        memory_limit_bytes=receipt['memory_limit_bytes'], scratch_budget_bytes=receipt['scratch_limit_bytes'],
        scratch_bytes=sum(path.stat().st_size for path in HERE.rglob('*') if path.is_file()),
        no_wall_time_limit=True, preserved_failed_runs=failures,
        implementation_defects_observed=[],
        limitations=['Task, Workspace identities and transport responses are controlled fixtures.',
            'Native bytes were produced by a previous actual local Trim Galore 0.6.10/Cutadapt 4.9 run on synthetic reads.',
            'No new native producer, live BV-BRC, HPC or configured-model execution.',
            'Host scenario uses explicitly saved selections and existing return admission, not a method_loop run.',
            'Original full-path run exited 1 at an erroneous fixture diagnostic assertion; its saved state passed the corrected continuation checks separately.',
            'No episode continuation or scientific credit behavior is verified or changed here.',
            'This is two-document coverage, not whole FastqUtils completion; other unfinished formats remain outside scope.'])
    artifacts = [path for path in sorted(run.rglob('*')) if path.is_file() and
                 ('evidence' in path.parts or path.parent == run)]
    artifacts += [HERE / name for name in ('freeze_receipt.json', 'incoming_before.json',
        'frozen_before.json', 'copy_manifest.json', 'helper_dependency_closure.json',
        'inspection_receipt.json', 'INSPECTION_CONTINUATION_002.json',
        'all_inputs_at_handoff.json', 'HARNESS_CORRECTIONS_001.md')]
    artifacts += [original / name for name in ('receipt.json', 'command.json', 'results.xml', 'stdout.log',
        'read_input_check.json', 'evidence/final_publication.json', 'evidence/first_artifact_publication.json',
        'evidence/original_selection_and_custody.json', 'evidence/fixture_declarations.json')]
    final['artifact_sha256'] = {str(path.relative_to(HERE)): sha(path) for path in artifacts}
    assert final['scratch_bytes'] < final['scratch_budget_bytes']
    save('FINAL_RECEIPT_001.json', final)
    print(json.dumps({key: final[key] for key in ('passed', 'actual_pytest_case_count', 'exit_code',
        'measurement_values', 'cutadapt_retention', 'typed_boundary_count', 'selected_action_count',
        'runtime_observation_count', 'forged_value_rejection_count', 'production_import_count',
        'changed_source_and_input_paths', 'observed_read_input_paths', 'scratch_bytes', 'elapsed_seconds')},
        sort_keys=True))


if __name__ == '__main__':
    main()
