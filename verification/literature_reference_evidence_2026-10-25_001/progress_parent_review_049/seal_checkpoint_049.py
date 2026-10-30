"""Seal root049 work; exclude still-running agent outputs and volatile journals."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    previous = BASE / 'CHECKPOINT_048_ADDENDUM_001.json'
    old = json.loads(previous.read_text())
    files = dict(old['files'])
    for name, expected in files.items():
        assert sha(ROOT / name) == expected, name
    package = BASE / 'literature_contract_profile_model_run_063'
    manifest = package / 'MANIFEST_001.json'
    assert sha(manifest) == 'c8f52688fd037baec3cf5c89e6d68cc80f7cd311a9da64d6ddb709cb694abbaa'
    rows = json.loads(manifest.read_text())['files']
    for name, expected in rows.items():
        path = package / name
        assert path.stat().st_size == expected['bytes'] and sha(path) == expected['sha256']
    design = BASE / 'a105_controlled_adapter_design_065'
    design_manifest = design / 'MANIFEST_006.json'
    assert sha(design_manifest) == '139db33959517772a80ee259b3bebd0caee4eda63a45a665d3c55c261814b50f'
    for row in json.loads(design_manifest.read_text())['entries']:
        path = design / row['path']
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
    additions = [previous, BASE / 'PROGRESS_049.md', Path(__file__), manifest,
        package / 'PRELAUNCH_METADATA_RECEIPT_001.json', package / 'pin_001/SOURCE_MANIFEST.json',
        package / 'RUNTIME_DEPENDENCIES_002.json', design_manifest,
        BASE / 'parent_launch_030/BOUNDARY_020.json']
    for directory in ('contract_profile_model_parent_review_062', 'controlled_adapter_parent_review_065'):
        additions.extend(path for path in (BASE / directory).rglob('*') if path.is_file()
            and not path.name.endswith(('-wal', '-shm')))
    for path in additions:
        name = str(path.resolve().relative_to(ROOT))
        actual = sha(path)
        assert name not in files or files[name] == actual, name
        files[name] = actual
    checkpoint = {'checkpoint': '049', 'goal_complete': False, 'previous_goal_turn': 'progress048',
        'current_goal_execution': 'progress', 'prior048_addendum_paths_verified': len(old['files']),
        'metadata066_sealed_payloads_verified': len(rows), 'metadata066_pin_entries_verified': 1432,
        'metadata066_contracts': {'operations': 19, 'returns': 18, 'project_imports': 160, 'external_file_rows': 4274},
        'actual_offline_source_registration': {'exit_code': 0, 'literature_sources': 1, 'supplied_sequence_sources': 1,
            'observations': 0, 'assessments': 0, 'runtime_tables': [], 'model_launched': False},
        'root_actual_job_prospective_task_text_review_pending': True,
        'root_new_paper_or_scientific_packet_content_read': False,
        '065_pure_declarations_accepted': '004 schemas/API +003 semantics corrected004 +active covariance invariant006',
        '065_sealed_payloads_verified': 49, 'root_declaration_reconstruction_exact_files': 11,
        'root_independent_mixed_representation_probe': '002 Fraction-constructed synthetic endpoints; frozen006 limitation confirmed',
        'fresh068': 'bounded NEW pure calculator/test implementation running; mutable outputs excluded; no source/native release',
        'fresh067': 'visual-only/mixed source-signal design running; own packet reset completed; mutable outputs excluded',
        'actual_model_status': 'BOUNDARY_020 live024/030 handles/start ticks verified at recorded timestamp; no RESULT files',
        'no_goal_completion_or_blocked_status_justified': True,
        'hashing_metadata_or_task_files_is_not_a_claim_of_full_text_or_scientific_review': True,
        'volatile_preparation_sqlite_journals_excluded': True,
        'remaining': ['actual068 implementation review', '067 exact interface review and native visual source work',
                      'shared source stages/full controlled v2 reader and native C1/C4 integration',
                      'actual JOB/TASK review with applicable reset, then configured-model evidence',
                      'complete remaining scoped experimental components and full objective audit'],
        'files': files}
    with (BASE / 'CHECKPOINT_049.json').open('x') as stream:
        json.dump(checkpoint, stream, indent=2, allow_nan=False)
        stream.write('\n')
    for name, expected in files.items():
        assert sha(ROOT / name) == expected, name
    print(json.dumps({'checkpoint': '049', 'verified_files': len(files), 'goal_complete': False,
        'actual_offline_preparation_passed': True, 'fresh_pure_implementation_in_progress': True}))


if __name__ == '__main__':
    main()
