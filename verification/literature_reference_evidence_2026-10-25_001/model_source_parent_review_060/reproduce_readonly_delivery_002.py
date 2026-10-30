"""Root reruns the fully reviewed actual-pin readonly delivery audit in new outputs."""
import hashlib
import json
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OWNER = BASE / 'a105_model_saved_source_audit_060/delivery_review_002'
EXPECTED = '0ba9cd29b0bf21af2e2736a3d73597d32a22885158ff7ca7c1072aa3efa106c1'


def main():
    script = OWNER / 'verify_delivery_002.py'
    assert hashlib.sha256(script.read_bytes()).hexdigest() == EXPECTED
    reset = json.loads((BASE / 'model_source_parent_reset_060/READ_RECEIPT.json').read_bytes())
    assert reset['reader'] == 'root' and reset['complete'] and len(reset['acknowledged_chunks']) == 49
    output = HERE / 'fresh_readonly_delivery_002'
    output.mkdir()
    namespace = runpy.run_path(str(script))
    runner = namespace['main']
    # All scientific/run/pin inputs remain the original declared ones.
    # Only the newly constructed empty metadata fixture and proof outputs move.
    runner.__globals__['HERE'] = output
    runner()
    result = json.loads((output / 'READONLY_DELIVERY_RECEIPT_002.json').read_bytes())
    assert result['passed'] and result['actual_typed_rows'] == 10 and result['nonnull_point_rows'] == 6
    assert result['mode_ro_before_first_parent_projection'] and result['source_artifact_reads_during_first_parent_projection'] == 0
    assert result['original_parent_observations_for_this_commission'] == 1 and result['original_parent_observation_index'] == 21
    assert result['public_selected_snapshot_unchanged'] and not result['whole_live_database_read_or_stability_claim']
    assert not result['forbidden_callback_invocations'] and not result['denied_write_attempts']
    assert result['original_form_full_typed_saved_validation'] and result['unrequested_component_rejected']['code'] == 'unrequested_literature_rate_component'
    assert result['no_live_re_admission'] and not result['new_model_calls'] and not result['new_actual_runtime_observations']
    assert hashlib.sha256(script.read_bytes()).hexdigest() == EXPECTED
    receipt = {'passed': True, 'fully_reviewed_verifier_sha256': EXPECTED,
               'method': 'New root-owned metadata fixture; fresh original-model mode=ro first projection through original030 implementation. Reviewed owner audit logic reused; no new scientific interpretation or independent algorithm claim.',
               'root_result_path': str(output / 'READONLY_DELIVERY_RECEIPT_002.json'),
               'actual_parent_rows': 10, 'nonnull_point_positions': 6,
               'first_projection_artifact_reads': 0, 'original_commission_observations': 1,
               'original_parent_decision_index': 18, 'original_parent_observation_index': 21,
               'original_C1_C3_C4_form_received_scope_authenticated': True,
               'unrequested_component_rejected': True,
               'no_private_history_or_original_source_read': True,
               'scope': 'Accepted actual model-selected typed numerical delivery/reconstruction for the already-reviewed coupled H2 case; no whole run closure,complete A105 reliability,target credit or new model action.'}
    with (HERE / 'READONLY_DELIVERY_ROOT_RECEIPT_002.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
