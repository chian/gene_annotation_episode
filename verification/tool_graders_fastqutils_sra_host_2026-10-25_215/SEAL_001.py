"""Seal the completed, isolated SRA host verification without replaying it."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = HERE / 'host_run_001'
EVIDENCE = RUN / 'evidence'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


run = read(RUN / 'receipt.json')
summary = read(EVIDENCE / 'verified_summary.json')
audited = read(RUN / 'read_input_check.json')
replay = read(EVIDENCE / 'saved_replay_and_forgery.json')
typed = read(EVIDENCE / 'typed_returns.json')
fixture = read(EVIDENCE / 'fixture_declarations.json')
imports = read(EVIDENCE / 'actual_import_origins.json')
assert run['passed'] and run['exit_code'] == 0 and summary['passed']
assert not run['changed_inputs'] and not audited['changed_inputs']
assert summary['runtime_observation_count'] == 0
assert replay['selected_actions_before'] == replay['selected_actions_after'] == 15
assert replay['action_rows_sha256_before'] == replay['action_rows_sha256_after']
assert not replay['forbidden_attempts'] and not replay['controlled_transport_calls_after_reconstruction']
assert len(replay['rejections']) == 3
assert len(list(HERE.glob('host_run_*'))) == 1

verifications = []
for name in ('incoming_before.json', 'frozen_before.json'):
    expected = read(HERE / name)
    different = [path for path, wanted in expected.items()
                 if not Path(path).is_file() or sha(Path(path)) != wanted]
    assert not different, different
    verifications.append(dict(manifest=name, sha256=sha(HERE / name),
                              checked_paths=len(expected), changed_paths=different))
write(HERE / 'SOURCE_VERIFY_001.json', dict(verified_at=datetime.now(timezone.utc).isoformat(),
    manifests=verifications, run_tracked_paths=run['tracked_paths'],
    read_audited_paths=audited['input_count'], changed_paths=[]))

examples = []
for name in ('total_bases', 'total_spots', 'size', 'read_length', 'n_reads'):
    row = typed['decoded'][name]['records'][0]
    examples.append(dict(native_field=name, typed_record=row))
write(HERE / 'NUMERICAL_EXAMPLE_001.json', dict(
    native_sha256=fixture['native_sha256'], native_byte_count=fixture['native_byte_count'],
    examples=examples, row_labels_retained=summary['row_labels_retained'],
    associations_invented=0, requirements=typed['decoded']['requirements'],
    note='n_reads is reported read types per spot; no total-read count is inferred.'))

selected_names = {
    'test_bvbrc_fastqutils_episode_flow', 'bvbrc_proteome_host_fixture',
    'gene_annotation_episode.api_service_execution', 'gene_annotation_episode.execution_episodes',
    'gene_annotation_episode.bvbrc_appservice_host', 'gene_annotation_episode.bvbrc_appservice_custody',
    'gene_annotation_episode.bvbrc_appservice_publication',
    'gene_annotation_episode.bvbrc_fastqutils_bundle_adapter',
    'gene_annotation_episode.bvbrc_fastqutils_sra_native',
    'gene_annotation_episode.bvbrc_fastqutils_sra_specs',
    'gene_annotation_episode.bvbrc_fastqutils_sheet',
    'gene_annotation_episode.bvbrc_fastqutils_calculators',
    'gene_annotation_episode.bvbrc_fastqutils_returns', 'method_loop',
}
selected_imports = [entry for entry in imports if entry['module'] in selected_names]
assert {entry['module'] for entry in selected_imports} == selected_names
for entry in selected_imports:
    assert Path(entry['path']).is_relative_to(HERE / 'candidate')
    assert sha(Path(entry['path'])) == entry['sha256']

key_paths = [
    'HANDOFF_001.md', 'WORKLOAD_001.md', 'PREPARATION_NOTES_001.json',
    'FINAL_CONTEXT_RESET_001.json', 'SOURCE_VERIFY_001.json', 'NUMERICAL_EXAMPLE_001.json',
    'FREEZE_INPUTS_001.py', 'PYTEST_ENTRY_001.py', 'RUN_HOST_001.py', 'test_native_sra_host.py',
    'SEAL_001.py', 'freeze_receipt.json', 'incoming_before.json', 'frozen_before.json',
    'copy_manifest.json', 'helper_dependency_closure.json', 'native_inputs/native_selected_run.json',
    'host_run_001/command.json', 'host_run_001/receipt.json', 'host_run_001/results.xml',
    'host_run_001/read_input_check.json', 'host_run_001/evidence/acquired_checkpoint.json',
    'host_run_001/evidence/final_publication.json', 'host_run_001/evidence/sheet.json',
    'host_run_001/evidence/components.json', 'host_run_001/evidence/typed_returns.json',
    'host_run_001/evidence/saved_replay_and_forgery.json',
    'host_run_001/evidence/selected_actions.json',
    'host_run_001/evidence/controlled_transport_calls.json',
    'host_run_001/evidence/actual_import_origins.json',
    'host_run_001/evidence/verified_summary.json',
]
manifest = {str(path.relative_to(HERE)): sha(path)
            for path in sorted(HERE.rglob('*')) if path.is_file()
            and path.name not in ('FINAL_FILES_001.json', 'FINAL_RECEIPT_001.json')}
write(HERE / 'FINAL_FILES_001.json', manifest)
receipt = dict(
    version='sra_host215_final_receipt_v1', sealed_at=datetime.now(timezone.utc).isoformat(),
    completed_scope='Retained completed211 SRA metadata parser through controlled actual host and two typed receiving boundaries',
    passed=True, test_passes=1, host_run_count=1, host_run_failures=0,
    scientific_acquisitions=1, acquisition_replays=0, saved_reconstruction_count=1,
    saved_repeated_return_count=2, rejection_count=3,
    native_byte_count=fixture['native_byte_count'], native_sha256=fixture['native_sha256'],
    provider_pin=summary['provider_pin'], numerical_values=summary['numerical_values'],
    row_labels_retained=summary['row_labels_retained'], associations_invented=0,
    selected_action_count=15, completed_own_tool_action_count=10, child_selection_count=5,
    controlled_transport_calls=8, runtime_observations=0, forbidden_call_attempts=0,
    practical_output_completion_verified=True, method_loop_run=False, controller_proof=False,
    whole_tool_complete=False, production_edits=False, live_acquisition=False,
    model_calls=0, native_producer_runs=0, old_suite_run=False,
    resource_receipt=run, all_imported_module_count=len(imports), selected_import_origins=selected_imports,
    input_verification=verifications, read_audited_paths=audited['input_count'],
    action_rows_sha256=replay['action_rows_sha256_before'],
    final_manifest='FINAL_FILES_001.json', final_manifest_sha256=sha(HERE / 'FINAL_FILES_001.json'),
    sealed_file_count=len(manifest), files={name: sha(HERE / name) for name in key_paths},
    remaining_limitations=[
        'Retained native JSON with controlled task and service responses; no live BV-BRC or SRA verification.',
        'Manually selected existing host actions; no model, Workflow or method_loop continuation proof.',
        'Native producer version and upstream length/read-type basis remain unproven.',
        'All 26 row labels remain in the sheet; no new receiver-selected metadata-label return family.',
        'This focused host test does not establish the entire FastqUtils scientific scope.',
    ])
write(HERE / 'FINAL_RECEIPT_001.json', receipt)
print(json.dumps(dict(passed=True, sealed_file_count=len(manifest),
    final_manifest_sha256=receipt['final_manifest_sha256'],
    final_receipt_sha256=sha(HERE / 'FINAL_RECEIPT_001.json'),
    test_passes=1, selected_actions=15, runtime_observations=0), sort_keys=True))
