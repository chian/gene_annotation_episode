"""Seal root043 accepted evidence, excluding in-progress shared integration."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    previous = json.loads((BASE / 'CHECKPOINT_042.json').read_bytes())
    for name, expected in previous['files'].items():
        assert digest(ROOT / name) == expected, name
    paths = [
        BASE / 'CHECKPOINT_042.json', BASE / 'PROGRESS_043.md',
        BASE / 'CONTRACT_INFORMATION_INTEGRATION_RELEASE_059.md', Path(__file__),
        BASE / 'parent_launch_030/BOUNDARY_016.json',
    ]
    for name in (
        'EXECUTION_RECEIPT_003.json', 'verify_execution_003.py',
        'verify_execution_failed_003.py', 'verify_execution_failed_004.py',
        'AUDIT_CORRECTION_003.md',
    ):
        paths.append(BASE / 'binding_primary_parent_review_058' / name)
    for name in ('PURE_STAGE_RECEIPT_003.json', 'verify_pure_stage_003.py'):
        paths.append(BASE / 'contract_information_parent_review_059' / name)
    binding = BASE / 'a105_binding_primary_example_058'
    paths.extend(binding / name for name in ('HANDOFF_003.md', 'MANIFEST_003.json', 'FINAL_VERIFY_003.json'))
    delivery = json.loads((binding / 'MANIFEST_003.json').read_bytes())['files']
    for name, row in delivery.items():
        # Owner delivery names are relative to its own directory.
        path = binding / name
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], name
    stage = BASE / 'a105_contract_information_design_059/pure_stage_003'
    paths.extend(stage / name for name in (
        'HANDOFF_003.md', 'MANIFEST_003.json', 'DELIVERY_RECEIPT_003.json',
        'API_FREEZE_003.md', 'IMPLEMENTATION_003.patch',
        'frozen_checks_003/TERMINAL_003.log', 'frozen_checks_003/TERMINAL_RECEIPT_003.json',
        'frozen_checks_003/pin/PIN_MANIFEST.json',
    ))
    pure = json.loads((stage / 'DELIVERY_RECEIPT_003.json').read_bytes())
    paths.extend(ROOT / name for name in pure['owned_files'])
    # Some original readonly dependencies now have an explicitly assigned
    # integration owner; seal immutable pure delivery artifacts rather than
    # freezing those mutable live shared files a second time.
    for name in ('gene_annotation_episode/literature_controlled_response_calculations.py',
                 'tests/test_literature_controlled_response_calculations.py'):
        paths.append(ROOT / name)
    files = {str(path.relative_to(ROOT)): digest(path) for path in sorted(set(paths))}
    receipt = {
        'checkpoint': '043', 'goal_complete': False,
        'previous_goal_execution': 'progress', 'current_goal_execution': 'progress',
        'previous042_frozen_entries_verified': len(previous['files']),
        'scope': 'Accepted058 controlled typed return/readonly reconstruction and059 pure helpers; released bounded connected integration; observed first actual030 non-null saved numbers.',
        'binding_delivery_files_verified': len(delivery), 'files': files,
        'mutable_workloads_not_sealed': ['056 source-reader proposal007', '059 connected integration shared eight-file ownership'],
        'coverage_warning': 'No full A105 reliability, actual-model completed typed numerical delivery, remaining literature axes, routing or W05 claim. Ten axes remain.',
    }
    with (BASE / 'CHECKPOINT_043.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'checkpoint': '043', 'passed': True, 'previous_verified': len(previous['files']),
                      'binding_delivery_verified': len(delivery), 'frozen_paths': len(files)}))


if __name__ == '__main__':
    main()
