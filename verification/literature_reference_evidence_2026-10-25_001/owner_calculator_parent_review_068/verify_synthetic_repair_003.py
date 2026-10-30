"""Root checks the exact actual source-join counterexample and076 preservation."""
from copy import deepcopy
from pathlib import Path
import difflib
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
new = HERE.parent / 'a105_owner_synthetic_graph_repair_076'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((new / 'ARTIFACT_MANIFEST_001.json').read_bytes())
for name, expected in manifest.items():
    assert sha(new / name) == expected, name
before = json.loads((new / 'BEFORE_001.json').read_bytes())
for name, expected in before['protected'].items():
    assert sha(ROOT / name) == expected, name
patch = ''
for name, expected in before['owned_actual_current'].items():
    original = new / 'before_001' / name
    assert sha(original) == expected
    patch += ''.join(difflib.unified_diff(original.read_text().splitlines(True),
        (ROOT / name).read_text().splitlines(True), fromfile='actual_before/' + name, tofile='actual_after/' + name))
assert patch == (new / 'OWNED_TWO_FILE_DELTA_001.patch').read_text()
pin_manifest = json.loads((new / 'PIN_MANIFEST_001.json').read_bytes())
for name, expected in pin_manifest.items():
    assert sha(new / 'pin_001' / name) == expected, name
execution = json.loads((new / 'PIN_EXECUTION_RECEIPT_001.json').read_bytes())
assert execution['pytest_exit_code'] == 0
for name, row in execution['project_imports'].items():
    p = Path(row['path']).resolve()
    assert p.is_relative_to(new / 'pin_001') and sha(p) == row['sha256']
assert '297 passed' in (new / 'PIN_TEST_RUN_001.txt').read_text()

from gene_annotation_episode import literature_controlled_response_owner_calculations as owner
from gene_annotation_episode import literature_controlled_response_calculations as old
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from jsonschema import Draft202012Validator

input_ = json.loads((new / 'ACTUAL_PRE_FIX_COUNTEREXAMPLE_001.json').read_bytes())['inputs']
Draft202012Validator(owner.controlled_response_owner_arguments_schema()).validate(input_)
saved = deepcopy(input_)
out = owner.populate_controlled_response_owner(input_)
assert input_ == saved and out['inputs'] == saved
assert out['cells']['controlled_response_difference']['value'] == .002
assert out['cells']['source_profile_log_ratio']['value'] is not None
assert 'canceled_graph_reading' in out['contrast_dependencies']['canceled_reading_qualifications']
assert out['inputs']['arms']['empty_condition0']['origin'] == 'synthetic'
active = deepcopy(input_)
row = active['arms']['protein_condition1']
value = row['value']
row.update(origin='synthetic', approximate=False, relation='interval',
    digitization_interval={'lower': value - .1, 'upper': value + .1})
result = owner.populate_controlled_response_owner(active)
assert result['cells']['source_profile_log_ratio']['value'] is None
assert 'unresolved_reading_model' in result['cells']['source_profile_log_ratio']['unavailable_reason']
assert result['inputs']['arms']['protein_condition1']['digitization_interval'] == row['digitization_interval']
reported = deepcopy(active)
reported['arms']['protein_condition1']['origin'] = 'reported'
try:
    owner.populate_controlled_response_owner(reported)
except ExperimentalContractError as error:
    assert error.code == 'digitization_interval_mismatch'
else:
    raise AssertionError('Reported interval incorrectly accepted')
legacy = {**deepcopy(input_), 'version': old.INPUT_VERSION, 'covariance': None, 'variance_status': 'unknown'}
try:
    old.validate_controlled_response_inputs(legacy)
except ExperimentalContractError as error:
    assert error.code == 'digitization_interval_mismatch'
else:
    raise AssertionError('Old006 behavior changed')
receipt = {'scope': 'Constructed pure owner-v2 only; no source/episode/model evidence',
    'payloads_checked': len(manifest), 'pin_files_checked': len(pin_manifest),
    'protected_files_checked': len(before['protected']), 'exact_two_file_delta': True,
    'actual_root_cases': 4, 'same_pre_fix_input_now_preserves_synthetic_origin_and_interval': True,
    'active_interval_blocks_normal_score': True, 'reported_interval_and_legacy_rejection_preserved': True,
    'recorded_pinned_tests': 297, 'accepted': '076 correction to068 pure component; source073 join separately required'}
with (HERE / 'SYNTHETIC_REPAIR_ROOT_RECEIPT_003.json').open('x') as f:
    json.dump(receipt, f, indent=2); f.write('\n')
print(json.dumps(receipt))
