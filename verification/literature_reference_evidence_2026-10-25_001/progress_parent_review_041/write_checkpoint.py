"""Seal accepted041 milestones without claiming unfinished workloads complete."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    previous = json.loads((BASE / 'CHECKPOINT_040.json').read_bytes())
    for name, expected in previous['files'].items():
        assert digest(ROOT / name) == expected, name
    relative = [
        'CHECKPOINT_040.json', 'PROGRESS_041.md', 'LATEST_HUMAN_DIRECTION_PARENT_041.txt',
        'a105_binding_native_design_052/MANIFEST_005.json',
        'a105_binding_native_design_052/HANDOFF_005.md',
        'a105_binding_native_design_052/RESULT_CONTRACT_INTEGRATION_005.md',
        'a105_binding_native_design_052/SNAPSHOT_HASHMAP_005.json',
        'a105_binding_native_design_052/IMPLEMENTATION_INTEGRATION_005.patch',
        'a105_binding_native_design_052/AUTHORIZED_RENDERER_055_DELTA_005.patch',
        'a105_binding_native_design_052/TERMINAL_INTEGRATION_RECEIPT_005.json',
        'a105_source_count_words_055/FINAL_MANIFEST_014.json',
        'a105_source_count_words_055/FINAL_HANDOFF_014.md',
        'a105_source_count_words_055/FINAL_DELIVERY_RECEIPT_014.json',
        'a105_source_count_words_055/FINAL_PATCH_014.diff',
        'a105_source_count_words_055/frozen_checks_012/pin/PIN_MANIFEST.json',
        'a105_model_execution_design_057/DELIVERY_MANIFEST_001.json',
        'a105_model_execution_design_057/PROPOSAL_001.md',
        'a105_model_execution_design_057/MEASUREMENT_RECEIPT_001.json',
        'a105_controlled_response_design_056/DELIVERY_002.json',
        'a105_controlled_response_design_056/PROPOSAL_002.md',
        'progress_parent_review_041/verify_deliveries.py',
        'progress_parent_review_041/DELIVERY_RECEIPT_001.json',
        'progress_parent_review_041/verify_scalar_display.py',
        'progress_parent_review_041/SCALAR_DISPLAY_RECEIPT_002.json',
        'progress_parent_review_041/verify_model_interfaces.py',
        'progress_parent_review_041/MODEL_INTERFACE_RECEIPT_001.json',
        'progress_parent_review_041/write_checkpoint.py',
        'parent_launch_030/BOUNDARY_014.json',
    ]
    paths = {BASE / name for name in relative}
    binding = json.loads((BASE / 'a105_binding_native_design_052/SNAPSHOT_HASHMAP_005.json').read_bytes())
    count = json.loads((BASE / 'a105_source_count_words_055/FINAL_DELIVERY_RECEIPT_014.json').read_bytes())['owned_files']
    for name, row in {**binding, **count}.items():
        assert digest(ROOT / name) == row['sha256'], name
        paths.add(ROOT / name)
    frozen = {str(p.relative_to(ROOT)): digest(p) for p in sorted(paths)}
    record = {'checkpoint': '041', 'goal_complete': False,
        'previous_goal_execution': 'progress', 'current_goal_execution': 'progress',
        'previous040_frozen_entries_verified': len(previous['files']),
        'scope': 'Accepted052native005 and055count014; independently reproduced057 interface; released056pure only;058primary and059information proposals pending.',
        'files': frozen,
        'mutable_workloads_not_sealed': ['056pure calculator/test development', '058primary-source proposal', '059operation-contract information proposal'],
        'coverage_warning': 'Controlled/synthetic engineering proof does not establish actual model science, primary transcription truth, complete A105 reliability compilation, routing or W05. Exactly10 axes remain.'}
    with (BASE / 'CHECKPOINT_041.json').open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'checkpoint': '041', 'goal_complete': False, 'frozen_files': len(frozen),
                      'previous040_verified': len(previous['files'])}))


if __name__ == '__main__':
    main()
