"""Seal static root progress only; exclude live state/logs and ongoing owners."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    previous = BASE / 'CHECKPOINT_049.json'
    old = json.loads(previous.read_bytes())
    files = dict(old['files'])
    for name, expected in files.items():
        assert sha(ROOT / name) == expected, name
    additions = [previous, BASE / 'PROGRESS_050.md', Path(__file__),
        BASE / 'parent_launch_030/BOUNDARY_021.json',
        ROOT / 'gene_annotation_episode/literature_controlled_response_owner_calculations.py',
        ROOT / 'tests/test_literature_controlled_response_owner_calculations.py']
    for folder in ('controlled_adapter_parent_review_065', 'visual_signal_parent_review_067'):
        additions.extend(p for p in (BASE / folder).rglob('*') if p.is_file())
    review = BASE / 'contract_profile_model_parent_review_062'
    # Offline005/preexisting static files are already in049. New live data is
    # intentionally not copied or sealed while it is being written.
    additions.extend(p for p in review.iterdir() if p.is_file() and p.suffix != '.log')
    additions.extend(p for p in (review / 'task_review_006').rglob('*') if p.is_file())
    for folder, manifest_name, key in (('a105_controlled_owner_calculator_068', 'MANIFEST_002.json', 'files'),
                                      ('a105_visual_signal_design_067', 'MANIFEST_007.json', 'entries')):
        package = BASE / folder
        manifest = package / manifest_name
        raw = json.loads(manifest.read_bytes())[key]
        rows = raw if isinstance(raw, dict) else {r['path']: {'bytes': r['bytes'], 'sha256': r['sha256']} for r in raw}
        for name, row in rows.items():
            path = package / name
            assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], name
        additions.extend([manifest, package / ('SHA256SUMS_' + ('002' if key == 'files' else '007') + '.txt')])
    for path in additions:
        name = str(path.resolve().relative_to(ROOT))
        actual = sha(path)
        assert name not in files or files[name] == actual, name
        files[name] = actual
    result = {'checkpoint': '050', 'goal_complete': False, 'current_goal_execution': 'progress',
        'prior049_paths_verified': len(old['files']),
        'intervening_short_clarification_reply': 'no progress; revalidated and followed by actual work',
        'root062_actual_task_review_and_reset': {'complete': True, 'files': 24, 'bytes': 360082},
        'new_configured_run': {'launched': True, 'pid': 2099666, 'start_ticks': '86801678',
            'directory': str((review / 'live_007').relative_to(ROOT)),
            'latest_public_observer': str((review / 'LIVE_BOUNDARY_004.json').relative_to(ROOT)),
            'scientific_numerical_success_or_terminal_result_proved': False},
        'owner068': {'pure_accepted': True, 'agent_actual_pin_tests': 70,
            'root_new_constructed_cases': 4, 'native_or_typed_integration': False},
        'visual067': {'root_complete_named_packet_files': 19, 'sealed_payloads': 54,
            'exact_normative_declaration_rebuilds': 5, 'root_reset_files': 26,
            'root_reset_bytes': 318170, 'pure070_release_only': True},
        'fresh069': 'source-v2/v3 design only; ongoing outputs excluded',
        'fresh070': 'new pure reader/calculator/validator implementation; ongoing outputs excluded',
        'no_private_history_or_live_database_copy': True,
        'no_goal_completion_or_blocked_status_justified': True,
        'remaining': ['069 exact full-source design and implementation', '070 actual pure implementation review',
            'native selected operations and original typed C1/C4/admitted-subset/source-free reconstruction',
            'actual configured numerical science/parent use/terminal proof',
            'complete full scoped experimental components and handoff; no narrowed completion criterion'],
        'files': files}
    with (BASE / 'CHECKPOINT_050.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    for name, expected in files.items():
        assert sha(ROOT / name) == expected, name
    print(json.dumps({'checkpoint': '050', 'verified_static_paths': len(files),
        'prior049_paths': len(old['files']), 'goal_complete': False, 'new_model_run_launched': True,
        'pure_owner_accepted': True, 'two_fresh_nonoverlapping_workloads': True}))


if __name__ == '__main__':
    main()
