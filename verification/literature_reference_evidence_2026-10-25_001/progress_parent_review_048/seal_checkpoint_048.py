"""Additive root checkpoint; hashes are evidence identities, not scientific grades."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    old_path = BASE / 'CHECKPOINT_047.json'
    old = json.loads(old_path.read_text())
    files = dict(old['files'])
    for name, expected in files.items():
        assert digest(ROOT / name) == expected, name
    reset_path = BASE / 'a105_gel_case_parent_review_064/source_review_001/RESET_READ_RECEIPT_001.json'
    reset = json.loads(reset_path.read_text())
    for row in reset['reset_files']:
        path = Path(row['path'])
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], str(path)
    for row in reset['source_packet']:
        path = BASE / row['path']
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], str(path)
    gel = BASE / 'a105_gel_case_review_064'
    for row in json.loads((gel / 'SEAL_005.json').read_text())['files']:
        path = gel / row['name']
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256']
    graph = BASE / 'a105_controlled_graph_reader_063'
    for row in json.loads((graph / 'MANIFEST_003.json').read_text())['entries']:
        path = graph / row['path']
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256']
    additions = [old_path, BASE / 'PROGRESS_047.md', BASE / 'PROGRESS_048.md',
                 BASE / 'parent_launch_030/BOUNDARY_019.json', graph / 'MANIFEST_003.json',
                 graph / 'PIN_MANIFEST_003.json', gel / 'SEAL_005.json', Path(__file__)]
    for name in ('a105_gel_case_parent_review_064', 'controlled_graph_parent_review_061'):
        additions.extend(path for path in (BASE / name).rglob('*') if path.is_file())
    additions.extend(BASE / row['path'] for row in reset['source_packet'])
    for path in additions:
        name = str(path.resolve().relative_to(ROOT))
        value = digest(path)
        assert name not in files or files[name] == value, name
        files[name] = value
    checkpoint = {'checkpoint': '048', 'goal_complete': False, 'current_goal_execution': 'progress',
        'previous_goal_continuation': 'progress047', 'intervening_clarification_only_answer': 'no authoritative state change',
        'prior047_paths_verified': len(old['files']), 'root064_primary_review_and_postpaper_reset_complete': True,
        'root064_reset_files': len(reset['reset_files']), 'root064_reset_bytes': sum(r['bytes'] for r in reset['reset_files']),
        'primary_existing_relative_signal_comparisons_executed': 4,
        'graph063_bounded_pure_implementation_accepted': True, 'graph063_sealed_payloads_verified': 98,
        'graph063_pin_files_verified': 14, 'graph063_root_current_files_matching_pin': 13,
        'graph063_exact_example_reproductions': 3, 'graph063_independent_constructed_value_nmol_per_min': 50.5,
        'graph063_callback_identity_caller_precondition': 'Real native resolver must bind Store.get_artifact; pure callback consistency limitation explicitly documented.',
        'other_session_domain_schema_change_preserved': True,
        'fresh065_design': 'running; design only; no implementation/native/model launch release; mutable outputs excluded',
        '062_generation_recipe': 'root read completely this continuation; static TASK appendix remains pending',
        'model_boundary': 'BOUNDARY_019; actual024/030 process handles live with original start ticks at recorded snapshot; neither RESULT present',
        'new_runtime_observations_or_model_calls': 0, 'new_production_code_or_scoring_policy': False,
        'remaining': ['selected new visual-transcription source creation', 'controlled-response full-N v2 adapter and native typed delivery',
                      'coherent configured-model profile execution', 'complete A105 and later scoped experimental literature coverage',
                      'full-objective completion audit and W05 handoff'],
        'files': files}
    destination = BASE / 'CHECKPOINT_048.json'
    with destination.open('x') as stream:
        json.dump(checkpoint, stream, indent=2, allow_nan=False)
        stream.write('\n')
    for name, expected in files.items():
        assert digest(ROOT / name) == expected, name
    print(json.dumps({'checkpoint': str(destination.relative_to(ROOT)), 'verified_files': len(files),
                      'goal_complete': False, 'current_goal_execution': 'progress'}))


if __name__ == '__main__':
    main()
