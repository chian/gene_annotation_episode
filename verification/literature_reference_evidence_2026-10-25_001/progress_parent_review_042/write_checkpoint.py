"""Seal042 accepted work while preserving the complete unfinished goal."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    previous = json.loads((BASE / 'CHECKPOINT_041.json').read_bytes())
    for name, expected in previous['files'].items():
        assert digest(ROOT / name) == expected, name
    names = [
        'CHECKPOINT_041.json', 'PROGRESS_042.md', 'BINDING_PRIMARY_PARENT_COMPONENT_REVIEW_058.md',
        'binding_primary_parent_reset_058/read_authority.py',
        'binding_primary_parent_reset_058/READ_RECEIPT.json',
        'binding_primary_parent_review_058/verify_proposal.py',
        'binding_primary_parent_review_058/PROPOSAL_RECEIPT_001.json',
        'a105_binding_primary_example_058/MANIFEST_001.json',
        'a105_binding_primary_example_058/PROPOSAL_001.md',
        'a105_binding_primary_example_058/READ_PROVENANCE_001.md',
        'a105_binding_primary_example_058/PROPOSED_SOURCE_NOMINATIONS_001.json',
        'a105_binding_primary_example_058/SOURCE_IDENTITIES_001.json',
        'a105_controlled_response_design_056/pure_stage_003/DELIVERY_006.json',
        'a105_controlled_response_design_056/pure_stage_003/HANDOFF_006.md',
        'a105_controlled_response_design_056/pure_stage_003/API_006.json',
        'a105_controlled_response_design_056/pure_stage_003/NEW_FILES_006.patch',
        'a105_controlled_response_design_056/pure_stage_003/REVIEW_DELTA_006.patch',
        'controlled_response_parent_review_056/reproduce_cross_dimension.py',
        'controlled_response_parent_review_056/CROSS_DIMENSION_BASELINE_001.json',
        'controlled_response_parent_review_056/verify_dimensions_and_units.py',
        'controlled_response_parent_review_056/DIMENSION_AND_UNIT_RECEIPT_001.json',
        'controlled_response_parent_review_056/verify_stage_006.py',
        'controlled_response_parent_review_056/STAGE_RECEIPT_006.json',
        'controlled_response_parent_review_056/TERMINAL_STAGE_006.log',
        'a105_contract_information_design_059/MANIFEST_001.json',
        'a105_contract_information_design_059/PROPOSAL_001.md',
        'a105_contract_information_design_059/HANDOFF_001.md',
        'a105_contract_information_design_059/INSPECTION_AND_LIMITS_001.md',
        'contract_information_parent_review_059/verify_proposal.py',
        'contract_information_parent_review_059/verify_proposal_failed_001.py',
        'contract_information_parent_review_059/PROPOSAL_RECEIPT_001.json',
        'parent_launch_030/BOUNDARY_015.json',
        'progress_parent_review_042/write_checkpoint.py',
    ]
    paths = {BASE / name for name in names}
    for name in ('gene_annotation_episode/literature_controlled_response_calculations.py',
                 'tests/test_literature_controlled_response_calculations.py'):
        paths.add(ROOT / name)
    for relative, key in (
        ('a105_binding_primary_example_058/MANIFEST_001.json', 'files'),
        ('a105_contract_information_design_059/MANIFEST_001.json', None)):
        path = BASE / relative
        manifest = json.loads(path.read_bytes())
        for name, row in (manifest[key] if key else manifest).items():
            item = path.parent / name
            assert item.stat().st_size == row['bytes'] and digest(item) == row['sha256'], name
    stage = BASE / 'a105_controlled_response_design_056/pure_stage_003'
    delivery = json.loads((stage / 'DELIVERY_006.json').read_bytes())
    for name, row in delivery['artifacts'].items():
        assert (stage / name).stat().st_size == row['bytes'] and digest(stage / name) == row['sha256'], name
    for name, row in delivery['owned_new_paths'].items():
        assert digest(ROOT / name) == row['sha256'], name
    reset = json.loads((BASE / 'binding_primary_parent_reset_058/READ_RECEIPT.json').read_bytes())
    assert reset['complete'] and len(reset['acknowledged_chunks']) == 51
    for row in reset['documents']:
        assert digest(Path(row['path'])) == row['sha256'], row['path']
    record = {'checkpoint': '042', 'goal_complete': False,
        'previous_goal_execution': 'progress', 'current_goal_execution': 'progress',
        'previous041_frozen_entries_verified': len(previous['files']),
        'scope': 'Accepted056pure006 after dimension correction; primary058 independently read/reset/converted and controlledrun released; verified059proposal and purehelpers released.',
        'files': {str(path.relative_to(ROOT)): digest(path) for path in sorted(paths)},
        'mutable_workloads_not_sealed': ['056reader proposal stage007', '058new controlled harness/pin/run', '059new purehelper code/tests'],
        'coverage_warning': 'No complete A105 reliability, actual-model numerical extraction, remaining literature axes, routing or W05 claim. Exactly10 axes remain.'}
    with (BASE / 'CHECKPOINT_042.json').open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'checkpoint': '042', 'goal_complete': False,
                      'frozen_files': len(record['files']), 'previous041_verified': len(previous['files'])}))


if __name__ == '__main__':
    main()
