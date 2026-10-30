"""Verify the completed197 candidate and retained comparison source hashes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

OWN = Path(__file__).resolve().parent
REPO = OWN.parent.parent
OUTPUT = Path(sys.argv[1]).resolve()
assert OUTPUT.parent == OWN and OUTPUT.is_dir()
assert json.loads((OWN / 'full_workflow_001/receipt.json').read_text())['exit_code'] == 0


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(tree, manifest):
    differences = {name: {'expected': expected,
        'actual': sha(tree / name) if (tree / name).is_file() else None}
        for name, expected in manifest.items()
        if not (tree / name).is_file() or sha(tree / name) != expected}
    assert not differences, (str(tree), differences)
    return {'tree': str(tree), 'checked_paths': len(manifest), 'differences': differences}


original = REPO / 'verification/tool_graders_bvbrc_comparative_systems_implementation_2026-10-25_186'
before = json.loads((OWN / 'source_before.json').read_text())
after = json.loads((OWN / 'source_after.json').read_text())
comparison = json.loads((OWN / 'fixture_comparison_manifest.json').read_text())
expected_artifacts = {
    'source_before.json': '3915fde692a79266eb37a1db6abae64d903b3f9b2b085f055f71b06e7b6cdef4',
    'source_after.json': '9291ad516ff7e82abb758bcc826a3aad6cc5018fdf5fd51df5a63db59c589292',
    'PRODUCTION_DIFF.patch': '156a64df4dcc4294cf79776ec8a286151431bed4bdcdb0e6c104509c7ecd706e',
    'run_frozen_workflow.py': '3e854de6a9bdabd3f9c21a0a6ca8419f74e69e67eb5efc2e409e5e6adb40cdac',
}
assert all(sha(OWN / name) == digest for name, digest in expected_artifacts.items())
assert before == json.loads((original / 'final_workflow_001/source_before.json').read_text())
assert (len(before), len(after), len(comparison)) == (1045, 1053, 1068)
changed = sorted(name for name, digest in before.items() if after[name] != digest)
assert changed == [
    'gene_annotation_episode/bvbrc_proteome_returns.py',
    'gene_annotation_episode/communication.py',
    'gene_annotation_episode/episode_return_records.py',
]
for name in changed:
    assert sha(OWN / 'frozen_original' / Path(name).name) == before[name]
assert all(comparison[name] == digest for name, digest in after.items())
baseline_with_fixtures = dict(before)
baseline_with_fixtures.update({name: after[name] for name in set(after) - set(before)
    if name.startswith('verification/')})
assert len(baseline_with_fixtures) == 1052

report = {'checked_at': datetime.now(timezone.utc).isoformat(),
    'original186': verify(original / 'candidate', before),
    'candidate197': verify(OWN / 'candidate', after),
    'fixture_comparison': verify(OWN / 'fixture_comparison_candidate', comparison),
    'owned_baseline': verify(OWN / 'baseline_candidate', baseline_with_fixtures),
    'original_production_paths_changed': changed,
    'candidate_additions': sorted(set(after) - set(before)),
    'comparison_fixture_additions': sorted(set(comparison) - set(after)),
    'artifact_sha256': {name: sha(OWN / name) for name in (
        'source_before.json', 'source_after.json', 'fixture_comparison_manifest.json',
        'PRODUCTION_DIFF.patch', 'run_frozen_workflow.py', 'collect_workflow_accounts.py',
        'verify_final_freeze.py')},
    'owned_regular_file_bytes': sum(path.stat().st_size for path in OWN.rglob('*')
        if path.is_file() and not path.is_symlink()),
}
assert report['owned_regular_file_bytes'] < 4 * 1024**3
for directory, expected in [('candidate', after), ('fixture_comparison_candidate', comparison)]:
    tree = OWN / directory
    actual_files = {str(path.relative_to(tree)) for path in tree.rglob('*') if path.is_file()}
    extra = sorted(actual_files - set(expected))
    report[directory + '_unmanifested_files'] = extra
    assert not extra, (directory, extra)

destination = OUTPUT / 'FINAL_SOURCE_FREEZE_CHECK.json'
destination.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: report[key] for key in (
    'checked_at', 'original_production_paths_changed', 'artifact_sha256', 'owned_regular_file_bytes')}, indent=2))
