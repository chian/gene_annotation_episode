"""Apply only the reviewed numerical files and their schema package-data entry."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = HERE / 'candidate'
NAMES = (
    'gene_annotation_episode/bvbrc_proteome_directional_sheet.py',
    'gene_annotation_episode/bvbrc_proteome_directional_numerical_contracts.py',
    'gene_annotation_episode/bvbrc_proteome_directional_numerical_schemas.json',
    'gene_annotation_episode/bvbrc_proteome_directional_geometry.py',
    'gene_annotation_episode/bvbrc_proteome_directional_calculators.py',
    'tests/test_bvbrc_proteome_directional_sheet.py',
    'tests/test_bvbrc_proteome_directional_numerical_contracts.py',
    'tests/test_bvbrc_proteome_directional_geometry.py',
    'tests/test_bvbrc_proteome_directional_calculators.py',
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((HERE / name).read_text())


tests = read('evidence_a/final_test_receipt_001.json')
assert tests['returncode'] == 0 and tests['source_test_manifest_unchanged']
assert not tests['changed_paths']
assert [(int(s['tests']),int(s['failures']),int(s['errors']),int(s['skipped']))
        for s in tests['testsuites']] == [(319,0,0,0)]
before = read('evidence_a/source_manifest_before_001.json')
after = read('evidence_a/source_manifest_after_001.json')
assert before == after
native = read('evidence_a/native_artifacts_receipt_002.json')
assert native['source_modules_unchanged']
assert native['saved_observation_replay']['forbidden_call_count'] == 0
for item in native['complete_scoring_sheets']:
    for field in ('artifact','saved_observation_replay'):
        assert digest(HERE / 'evidence_a' / item[field]['path']) == item[field]['sha256']
package = read('evidence_c/package_001/receipt.json')
assert package['passed'] and package['installed_exit_code'] == package['build_exit_code'] == 0
packaged = read('evidence_c/package_001/source_after.json')
files = []
for name in NAMES:
    assert not (ROOT / name).exists(), name
    expected = after[name]['sha256']
    assert digest(CANDIDATE / name) == expected, name
    if name.startswith('gene_annotation_episode/'):
        assert packaged[name] == expected, name
    files.append({'path':name,'before_sha256':None,'after_sha256':expected})
project = (ROOT / 'pyproject.toml').read_bytes()
candidate_project = (CANDIDATE / 'pyproject.toml').read_bytes()
addition = b', "bvbrc_proteome_directional_numerical_schemas.json"'
assert candidate_project.count(addition) == 1
assert candidate_project.replace(addition,b'') == project
assert digest(CANDIDATE / 'pyproject.toml') == packaged['pyproject.toml']
files.append({'path':'pyproject.toml','before_sha256':digest(ROOT / 'pyproject.toml'),
              'after_sha256':digest(CANDIDATE / 'pyproject.toml')})
baseline = read('BASELINE_001.json')
prior_changes = {name for name,sha in baseline.items()
                 if not (ROOT / name).exists() or digest(ROOT / name) != sha}
assert not prior_changes, prior_changes
receipt = {'recorded_at':datetime.now(timezone.utc).isoformat(), 'files':files,
           'numerical_tests':319, 'candidate_test_sources_unchanged':True,
           'packaged_native_example_verified':True,
           'production_result_return_integration':'unfinished',
           'live_service_execution_verified':False}
if sys.argv[1:] == ['--apply']:
    assert not (HERE / 'APPLICATION_RECEIPT_001.json').exists()
    for name in NAMES:
        with (ROOT / name).open('xb') as stream:
            stream.write((CANDIDATE / name).read_bytes())
    (ROOT / 'pyproject.toml').write_bytes(candidate_project)
    for item in files:
        assert digest(ROOT / item['path']) == item['after_sha256']
    unchanged = all(digest(ROOT / name) == sha for name,sha in baseline.items())
    assert unchanged
    receipt.update(production_applied=True, existing_baseline_files_unchanged=len(baseline),
                   applied_checkout_tests='pending')
    with (HERE / 'APPLICATION_RECEIPT_001.json').open('x') as stream:
        json.dump(receipt,stream,indent=2)
        stream.write('\n')
else:
    assert not sys.argv[1:]
    receipt['production_applied'] = False
    with (HERE / 'PREFLIGHT_001.json').open('x') as stream:
        json.dump(receipt,stream,indent=2)
        stream.write('\n')
print(json.dumps({'production_applied':receipt['production_applied'], 'file_count':len(files),
                  'existing_baseline_files':len(baseline)}))
