"""Seal reviewed scientific conversion and bounded count-stage evidence."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
ROOT = OUT.parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    previous = json.loads((BASE / 'CHECKPOINT_039.json').read_bytes())
    assert all(digest(ROOT / name) == expected for name, expected in previous['files'].items())
    names = [
        'CHECKPOINT_039.json', 'PROGRESS_040.md', 'TRANSPORT_PARENT_COMPONENT_REVIEW_043.md',
        'transport_parent_reset_043/read_authority.py', 'transport_parent_reset_043/READ_RECEIPT.json',
        'transport_parent_review_043/verify_packet.py', 'transport_parent_review_043/RECEIPT_001.json',
        'transport_parent_review_043/reproduce_arithmetic_001.py',
        'transport_parent_review_043/reproduced_001/NUMERICAL_CASE.json',
        'transport_parent_review_043/reproduced_001/SOURCE_LOCATORS.json',
        'transport_parent_review_043/ADDITIONAL_EXPOSURE_ARITHMETIC_001.json',
        'a105_transport_case_043/MANIFEST.json', 'a105_transport_case_043/FINDINGS.md',
        'a105_transport_case_043/HANDOFF.md', 'a105_transport_case_043/PROVENANCE.md',
        'kinetic_count_parent_review_055/verify_stage.py', 'kinetic_count_parent_review_055/RECEIPT_008.json',
        'kinetic_count_parent_review_055/verify_numeric_preservation_008.py',
        'kinetic_count_parent_review_055/NUMERIC_PRESERVATION_008.json',
        'a105_source_count_words_055/STAGE_008_MANIFEST.json', 'a105_source_count_words_055/ARTIFACT_MANIFEST_008.json',
        'a105_source_count_words_055/STAGE_008_HANDOFF.md', 'a105_source_count_words_055/STAGE_008.patch',
        'a105_source_count_words_055/COUNT_LANGUAGE_008.md', 'a105_source_count_words_055/SNAPSHOT_REVIEW_008.json',
        'a105_source_count_words_055/PROPOSED_RENDERER_DELTA_009.diff',
        'a105_source_count_words_055/PROPOSED_RENDERER_DELTA_009.json',
        'a105_source_count_words_055/probe_renderer_delta_009.py',
        'a105_source_count_words_055/RENDERER_PREVIEW_RECEIPT_009.json',
        'parent_launch_030/BOUNDARY_013.json', 'progress_parent_review_040/write_checkpoint.py',
    ]
    for path in (BASE / 'kinetic_count_parent_review_055/reconstructed_008').rglob('*'):
        if path.is_file():
            names.append(path.relative_to(BASE).as_posix())
    files = {(BASE / name).relative_to(ROOT).as_posix(): digest(BASE / name) for name in sorted(set(names))}
    checkpoint = {'checkpoint': '040', 'goal_complete': False, 'previous_goal_execution': 'progress',
        'current_goal_execution': 'progress', 'previous039_frozen_entries_verified': len(previous['files']),
        'scope': 'Parent043 retained-case conversion after complete38-chunk reset; accepted055 frozen008 reader/validator/storage stage; reviewed009 mechanical display transfer.052 final integration and055 final runtime/presentation verification and056 proposal remain in progress.',
        'files': files,
        'mutable_heads_deliberately_not_sealed': ['052 shared/new binding integration', '055 final count integration and shared renderer'],
        'coverage_warning': 'Retained transport packet conversion and synthetic engineering proof do not establish fresh primary reading, model-backed extraction, complete A105 or the other scoped literature responsibilities. No router/A101/W05 aggregation.'}
    with (BASE / 'CHECKPOINT_040.json').open('x') as stream:
        json.dump(checkpoint, stream, indent=2)
        stream.write('\n')
    assert all(digest(ROOT / name) == expected for name, expected in files.items())
    print(json.dumps({'checkpoint': '040', 'frozen_entries': len(files),
        'prior039_entries_verified': len(previous['files']), 'goal_complete': False}))


if __name__ == '__main__':
    main()
