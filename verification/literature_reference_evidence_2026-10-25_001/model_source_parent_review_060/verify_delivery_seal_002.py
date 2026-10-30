"""Authenticate final original-model delivery packaging and root's fresh proof."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
SOURCE = BASE / 'a105_model_saved_source_audit_060'
DELIVERY = SOURCE / 'delivery_review_002'


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(directory, entries):
    for name, row in entries.items():
        path = directory / name
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], name


def main():
    source_manifest = load(SOURCE / 'MANIFEST_001.json')
    verify(SOURCE, source_manifest['files'])
    manifest = load(DELIVERY / 'MANIFEST_002.json')
    verify(DELIVERY, manifest['files'])
    final = load(DELIVERY / 'FINAL_VERIFY_002.json')
    assert final['passed'] and final['manifest_sha256'] == sha(DELIVERY / 'MANIFEST_002.json')
    assert load(DELIVERY / 'EXIT_003.json')['exit_code'] == 0
    assert load(DELIVERY / 'EXIT_002.json')['exit_code'] == 1
    root = load(HERE / 'READONLY_DELIVERY_ROOT_RECEIPT_002.json')
    assert root['passed'] and root['fully_reviewed_verifier_sha256'] == sha(DELIVERY / 'verify_delivery_002.py')
    own = load(DELIVERY / 'READONLY_DELIVERY_RECEIPT_002.json')
    fresh = load(HERE / 'fresh_readonly_delivery_002/READONLY_DELIVERY_RECEIPT_002.json')
    assert own['passed'] and fresh['passed']
    for field in ('original_commission_sha256', 'original_return_id', 'original_admission_id',
                  'original_parent_decision_index', 'original_parent_observation_index',
                  'original_pin_manifest_sha256', 'original_settings_sha256',
                  'original_runtime_implementation_sha256', 'requested_components'):
        assert own[field] == fresh[field], field
    owner_projection = load(DELIVERY / 'ACTUAL_PARENT_PROJECTION_002.json')
    root_projection = load(HERE / 'fresh_readonly_delivery_002/ACTUAL_PARENT_PROJECTION_002.json')
    assert owner_projection == root_projection
    for proof in (own, fresh):
        assert proof['actual_typed_rows'] == 10 and proof['nonnull_point_rows'] == 6
        assert proof['source_artifact_reads_during_first_parent_projection'] == 0
        assert proof['original_parent_observations_for_this_commission'] == 1
        assert proof['public_selected_snapshot_unchanged']
        assert not proof['forbidden_callback_invocations'] and not proof['denied_write_attempts']
        assert not proof['whole_live_database_read_or_stability_claim']
    packaging = load(DELIVERY / 'PACKAGING_CHECKS_002.json')
    assert packaging['passed'] and all(value == 0 for value in packaging['metadata_fixture_table_counts'].values())
    assert packaging['backend_acknowledgment_matches_original_admission']
    assert packaging['original_parent_goal_path_scope_and_child_request_consistent']
    assert not packaging['optional_C4_replay_fixture_run']
    receipt = {'passed': True, 'scientific001_files_still_exact': len(source_manifest['files']),
               'delivery002_files_verified': len(manifest['files']),
               'owner_and_root_fresh_actual_parent_projections_exact': True,
               'same_original_C1_C3_C4_and_observation_identity': True,
               'root_actual_first_projection_artifact_reads': 0,
               'actual_typed_rows': 10, 'nonnull_positions': 6,
               'scope': 'Actual model-backed numerical child delivery and fresh source-free readonly parent reconstruction accepted. Saved source aliases retained in sheet payloads; no new inline physical-measurement field or independent-replication inference.'}
    with (HERE / 'DELIVERY_SEAL_RECEIPT_002.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
