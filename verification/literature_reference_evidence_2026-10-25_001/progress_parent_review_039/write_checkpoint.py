"""Seal accepted milestones without treating mutable heads as frozen history."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
ROOT = OUT.parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    previous = json.loads((BASE / 'CHECKPOINT_038.json').read_bytes())
    replaced = {'gene_annotation_episode/literature_binding_interaction_calculations.py',
        'tests/test_literature_binding_interaction_calculations.py'}
    unchanged, superseded = [], []
    for name, expected in previous['files'].items():
        if name in replaced:
            copies = [BASE / 'binding_interaction_parent_review_048/reconstructed_001' / name,
                BASE / 'a105_binding_partial_uncertainty_053/baseline_001' / name]
            assert all(digest(path) == expected for path in copies)
            assert digest(ROOT / name) != expected
            superseded.append({'path': name, 'historical_sha256': expected, 'current_sha256': digest(ROOT / name),
                'intentional_replacement': 'accepted053 partial uncertainty preservation',
                'original_copies_verified': [p.relative_to(ROOT).as_posix() for p in copies]})
        else:
            assert digest(ROOT / name) == expected, name
            unchanged.append(name)
    assert len(unchanged) == 40 and len(superseded) == 2
    # Seal the newly delivered same-case publication verification too.
    owner051 = BASE / 'a105_kinetic_primary_example_051'
    long_manifest = json.loads((owner051 / 'LONG_WITNESS_MANIFEST_002.json').read_bytes())
    for name, row in long_manifest.items():
        path = owner051 / name
        assert digest(path) == row['sha256'] and path.stat().st_size == row['bytes']
    owner055 = BASE / 'a105_source_count_words_055'
    baseline055 = json.loads((owner055 / 'BASELINE_001.json').read_bytes())
    for name, row in baseline055['files'].items():
        path = owner055 / 'baseline_001' / name
        assert digest(path) == row['sha256'] and path.stat().st_size == row['bytes']
    relative_files = [
        'CHECKPOINT_038.json', 'PROGRESS_039.md',
        'binding_parent_reset_042_followup_001/read_authority.py', 'binding_parent_reset_042_followup_001/READ_RECEIPT.json',
        'kinetic_primary_parent_reset_051/read_authority.py', 'kinetic_primary_parent_reset_051/READ_RECEIPT.json',
        'native_unit_parent_review_050/verify_delivery.py', 'native_unit_parent_review_050/RECEIPT_002.json',
        'a105_native_unit_usability_050/MANIFEST_002.json', 'a105_native_unit_usability_050/HANDOFF_002.md',
        'a105_native_unit_usability_050/IMPLEMENTATION_002.patch',
        'binding_partial_parent_review_053/verify_delivery.py', 'binding_partial_parent_review_053/RECEIPT_002.json',
        'a105_binding_partial_uncertainty_053/HANDOFF_002.md', 'a105_binding_partial_uncertainty_053/FULL_PATCH_002.diff',
        'a105_binding_partial_uncertainty_053/RELEASE_RECEIPT_002.json',
        'kinetic_primary_parent_review_051/verify_delivery.py', 'kinetic_primary_parent_review_051/RECEIPT_001.json',
        'kinetic_primary_parent_review_051/verify_source_bindings.py', 'kinetic_primary_parent_review_051/SOURCE_BINDINGS_RECEIPT_001.json',
        'kinetic_primary_parent_review_051/verify_long_witness.py', 'kinetic_primary_parent_review_051/LONG_WITNESS_RECEIPT_002.json',
        'a105_kinetic_primary_example_051/FINAL_MANIFEST_001.json', 'a105_kinetic_primary_example_051/HANDOFF_001.md',
        'a105_kinetic_primary_example_051/LONG_WITNESS_MANIFEST_002.json', 'a105_kinetic_primary_example_051/LONG_WITNESS_HANDOFF_002.md',
        'kinetic_witness_parent_review_054/reproduce_label_boundary.py', 'kinetic_witness_parent_review_054/BASELINE_LABEL_FAILURES_001.json',
        'kinetic_witness_parent_review_054/verify_delivery.py', 'kinetic_witness_parent_review_054/DELIVERY_RECEIPT_001.json',
        'a105_kinetic_witness_publication_054/MANIFEST_001.json', 'a105_kinetic_witness_publication_054/FINAL_HANDOFF_001.md',
        'a105_kinetic_witness_publication_054/IMPLEMENTATION_001.patch',
        'binding_inputs_parent_review_052/verify_delivery.py', 'binding_inputs_parent_review_052/RECEIPT_003.json',
        'binding_inputs_parent_review_052/TERMINAL_003.log',
        'a105_binding_native_design_052/MANIFEST_003.json', 'a105_binding_native_design_052/RESULT_CONTRACT_003.md',
        'a105_binding_native_design_052/IMPLEMENTATION_003.patch',
        'a105_source_count_words_055/PROPOSAL_001.md', 'a105_source_count_words_055/BASELINE_001.json',
        'a105_source_count_words_055/reproduce_count_gap.py', 'a105_source_count_words_055/SYNTHETIC_BASELINE_RECEIPT_001.json',
        'parent_launch_030/BOUNDARY_011.json', 'parent_launch_030/BOUNDARY_012.json',
        'progress_parent_review_039/write_checkpoint.py',
    ]
    for directory in ('native_unit_parent_review_050/reconstructed_002', 'binding_partial_parent_review_053/reconstructed_002',
            'kinetic_witness_parent_review_054/reconstructed_001', 'binding_inputs_parent_review_052/reconstructed_003'):
        relative_files.extend(p.relative_to(BASE).as_posix() for p in (BASE / directory).rglob('*') if p.is_file())
    files = {str((BASE / name).relative_to(ROOT)): digest(BASE / name) for name in sorted(set(relative_files))}
    checkpoint = {'checkpoint': '039', 'goal_complete': False, 'previous_goal_execution': 'progress',
        'current_goal_execution': 'progress', 'prior038_unchanged_paths_verified': len(unchanged),
        'intentional_supersessions_with_original_bytes_preserved': superseded,
        'additional_long_delivery_entries_verified': len(long_manifest), '055_original_baseline_entries_verified': len(baseline055['files']),
        'scope': 'Accepted050/053, primary051 controlled005 and long publication follow-up,054 repair and052 pure source reader.052 native integration and055 count implementation remain in progress. No mutable shared/kinetic heads are sealed here.',
        'files': files,
        'coverage_warning': 'Controlled primary selections and engineering tests do not prove configured-model extraction or complete A105. Exactly ten axes; router/A101/W05 excluded. Other scoped axes and full scientific scoring remain unfinished.'}
    with (BASE / 'CHECKPOINT_039.json').open('x') as stream:
        json.dump(checkpoint, stream, indent=2)
        stream.write('\n')
    assert all(digest(ROOT / name) == expected for name, expected in files.items())
    print(json.dumps({'checkpoint': '039', 'frozen_entries': len(files), 'prior_unchanged': len(unchanged),
        'intentional_supersessions': len(superseded), 'new_long_manifest_entries': len(long_manifest), 'goal_complete': False}))


if __name__ == '__main__':
    main()
