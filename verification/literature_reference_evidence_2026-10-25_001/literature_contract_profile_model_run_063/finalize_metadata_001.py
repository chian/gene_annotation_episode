"""Seal only this no-model workload after complete identity comparisons."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
PIN = HERE / 'pin_001'
OUT = HERE / 'verification_001'


def main():
    spec = importlib.util.spec_from_file_location('metadata_identity_helper', HERE / 'verify_preparation_001.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    entries = helper.verify_pin(PIN)
    before = json.loads((OUT / 'CONTRACT_SNAPSHOT_ACCEPTED_001.json').read_bytes())
    after = json.loads((OUT / 'CONTRACT_SNAPSHOT_NEW_001.json').read_bytes())
    compare = ('scope', 'descriptor', 'operations', 'returns', 'invalid_feedback',
        'saved_exchange_probe', 'descriptor_modules_imported', 'models', 'controller',
        'scientific_progress', 'restoration', 'local_jobs', 'disabled_model_entrypoints',
        'attempted_model_entrypoints')
    exact = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False)
    for name in compare:
        assert exact(before[name]) == exact(after[name]), name
    assert {row['module']: row['sha256'] for row in before['actual_project_imports']} == {
        row['module']: row['sha256'] for row in after['actual_project_imports']}
    dependencies = json.loads((HERE / 'RUNTIME_DEPENDENCIES_002.json').read_bytes())
    imported = {row['module']: row for row in dependencies['actual_project_imports']}
    reconstruction = json.loads((OUT / 'DESCRIPTOR_RECONSTRUCTION_002.json').read_bytes())
    for row in [*after['actual_project_imports'], *reconstruction['actual_project_imports']]:
        assert imported[row['module']] == row
    bound_files = [dependencies[name] for name in ('resolved_interpreter', 'pyvenv_cfg', 'configured_executable')]
    bound_files += dependencies['actually_loaded_external_module_files']
    bound_files += [row for distribution in dependencies['installed_distributions'] for row in distribution['files']]
    for row in bound_files:
        assert helper.fingerprint(row['path']) == {k: row[k] for k in ('path', 'bytes', 'sha256')}, row['path']
    assert not any((HERE / name).exists() for name in ('live_001', 'preparation_001'))
    assert not any(path.suffix in ('.db', '.sqlite3', '.sqlite') for path in HERE.rglob('*') if path.is_file())
    helper.save(OUT / 'CROSS_PIN_COMPARISON_001.json', {
        'status': 'passed', 'exact_compared_keys': list(compare), 'operations_equal': 19,
        'return_projections_equal': 18, 'compact_and_literal_form_pairs_per_pin': 18,
        'matching_project_import_bytes_per_pin': 142,
        'new_descriptor_only_imports_also_in_final_dependency_binding': True,
        'final_project_module_count': len(imported),
        'complete_original_c1_c4_delivery_proven': False,
        'meaning': 'identical frozen declarations and synthetic metadata reconstruction only'})
    full_reads = [
        '/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt',
        'AGENTS.md', 'GOAL.md', 'docs/EPISODE_STRUCTURE.md', 'docs/TIME_AWARE_ESTIMATION.md',
        'docs/TOOL_KNOWLEDGE.md', 'docs/TASK_AND_STEERING.md',
        'docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md',
        'research/experimental_scoring_review_2026-10-23/AGENTS.md',
    ]
    provenance = [{'read': 'complete', **helper.fingerprint(Path(name) if Path(name).is_absolute() else ROOT / name)} for name in full_reads]
    for name in ('PROPOSAL_001.md', 'GENERATION_RECIPE_001.md', 'TASK_TEMPLATES_001.md', 'HANDOFF_001.md'):
        provenance.append({'read': 'complete in bounded sequential portions',
            **helper.fingerprint(BASE / 'a105_contract_profile_model_design_062' / name)})
    provenance.append({'read': 'complete', **helper.fingerprint(BASE / 'contract_profile_model_parent_review_062/PREPARATION_RELEASE_002.md')})
    for name in ('episode_contract_information.py', 'composition_information.py', 'literature_episodes.py',
                 'providers.py', 'episode_bindings.py', 'schema_information_text.py', 'schema_support.py',
                 'boundary_validation.py', 'default_scientific_binding.py', 'decision_context.py',
                 'episode_composition.py', 'defaults.toml'):
        provenance.append({'read': 'complete', **helper.fingerprint(PIN / 'gene_annotation_episode' / name)})
    for name in ('tests/test_contract_information_runtime_059.py', 'tests/test_contract_information_custody_059.py',
                 'method_loop/durable_worker.py'):
        provenance.append({'read': 'complete', **helper.fingerprint(PIN / name)})
    for path in (BASE / 'literature_model_run_030/pin_001/runner/run_literature_source_job_019.py',
                 BASE / 'parent_launch_030/verify_launch.py'):
        provenance.append({'read': 'complete original code; not executed', **helper.fingerprint(path)})
    provenance.extend([
        {'read': 'complete relevant functions/ranges, not whole module',
         'inclusive_ranges': [[190, 305], [790, 828], [985, 1130], [1580, 1745], [2035, 2200], [3865, 3955]],
         **helper.fingerprint(PIN / 'gene_annotation_episode/runtime.py')},
        {'read': 'complete closed-schema compilation functions; additional form-validator beginning inspected',
         'inclusive_ranges': [[1, 250]], **helper.fingerprint(PIN / 'gene_annotation_episode/communication.py')},
        {'read': 'complete selected safe-path start method', 'inclusive_ranges': [[525, 570]],
         **helper.fingerprint(PIN / 'method_loop/durable.py')},
        {'read': 'complete saved-factory reconstruction helper', 'inclusive_ranges': [[95, 138]],
         **helper.fingerprint(PIN / 'gene_annotation_episode/independent_execution.py')},
    ])
    helper.save(HERE / 'READ_PROVENANCE_001.json', {'documents': provenance,
        'truncation_corrections': 'Initial combined knowledge/recipe reads truncated; both reread completely in separate bounded outputs before implementation.',
        'scientific_input_access': 'five files copied/stream-hashed only; no text decoding, metadata interpretation, source registration or post-paper reset claimed',
        'not_read': ['scientific JOB/source/FASTA content', 'old run DBs', 'private provider/model histories', 'credentials', 'environment dumps', 'process argv']})
    receipt = {'status': 'metadata_import_contract_phase_passed', 'utc': datetime.now(timezone.utc).isoformat(),
        'release': 'contract_profile_model_parent_review_062/PREPARATION_RELEASE_002.md',
        'immutable_pin_entries': len(entries), 'source_manifest_sha256': helper.sha(PIN / 'SOURCE_MANIFEST.json'),
        'runner_sha256': helper.sha(PIN / 'runner/run_literature_source_job_062.py'),
        'upstream_manifest_sha256': helper.sha(PIN / 'PIN_MANIFEST.json'),
        'exact_runner_substitutions': 5, 'scientific_input_files_copied_opaquely': 5,
        'profile': 'operation_contract_information_v1', 'protocol': 'decision_exchange_v1',
        'operation_contracts': 19, 'return_contracts': 18, 'matching_new_and_accepted_project_imports': 142,
        'final_bound_project_imports': len(imported), 'safe_path_worker_imports': 4,
        'installed_distributions': len(dependencies['installed_distributions']),
        'loaded_external_module_files': len(dependencies['actually_loaded_external_module_files']),
        'final_reverified_authoritative_file_rows': len(bound_files),
        'dependency_binding': 'RUNTIME_DEPENDENCIES_002.json',
        'dependency_binding_sha256': helper.sha(HERE / 'RUNTIME_DEPENDENCIES_002.json'),
        'dependency_binding001_scope_addendum': '002 adds18 project modules imported only by actual descriptor-composition reconstruction;001 remains unchanged. External binding rows unchanged.',
        'effective_models': after['models'], 'effective_controller': after['controller'],
        'scientific_progress': after['scientific_progress'], 'restoration': after['restoration'], 'local_jobs': after['local_jobs'],
        'source_inputs_decoded': False, 'source_registration': False, 'provider_entries': 0,
        'runtime_actions': 0, 'runtime_observations': 0, 'stores_or_databases_created': 0,
        'old_run_process_or_db_access': False, 'new_model_launch_released': False,
        'remaining': ['source-registering offline phase and complete actual JOB/instantiated TASK review',
                      'actual configured-model scientific selection', 'original C1/C4 numerical delivery and parent use',
                      'first source-free read-only reconstruction of actual admitted facts'],
        'tests_not_repeated': 'historical190 focused suite and broad paper-dependent suites; no changed production code or new concern required those reruns'}
    helper.save(HERE / 'PRELAUNCH_METADATA_RECEIPT_001.json', receipt)
    exclusions = {HERE / 'MANIFEST_001.json', HERE / 'SHA256SUMS_001.txt'}
    payloads = {str(path.relative_to(HERE)): {'bytes': path.stat().st_size, 'sha256': helper.sha(path)}
        for path in sorted(HERE.rglob('*')) if path.is_file() and path not in exclusions}
    helper.save(HERE / 'MANIFEST_001.json', {'scope': '066 exact metadata/import/contract package; no scientific execution', 'files': payloads})
    with (HERE / 'SHA256SUMS_001.txt').open('x') as stream:
        for name, row in sorted(payloads.items()):
            stream.write(row['sha256'] + '  ' + name + '\n')
        stream.write(helper.sha(HERE / 'MANIFEST_001.json') + '  MANIFEST_001.json\n')
    for name, row in payloads.items():
        assert helper.sha(HERE / name) == row['sha256']
    print(json.dumps({'status': receipt['status'], 'pin_entries': len(entries), 'sealed_payloads': len(payloads),
        'model_entries': 0, 'source_registration': False, 'runtime_observations': 0}))


if __name__ == '__main__':
    main()
