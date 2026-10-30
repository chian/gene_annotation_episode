"""Seal static root evidence; retain explicit historical source supersessions."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
old = json.loads((BASE / 'CHECKPOINT_050.json').read_bytes())
repair = BASE / 'a105_owner_synthetic_graph_repair_076'
before = json.loads((repair / 'BEFORE_001.json').read_bytes())['owned_actual_current']
files, supersessions = {}, {}
for name, expected in old['files'].items():
    actual = sha(ROOT / name)
    if actual != expected:
        assert name in before and before[name] == expected, name
        original = repair / 'before_001' / name
        assert sha(original) == expected
        supersessions[name] = {'historical050_sha256': expected, 'current076_sha256': actual,
            'preserved_original_path': str(original.relative_to(ROOT)),
            'reason': 'Authorized076 owner-v2 synthetic graph validation correction; original050/068 pins unchanged'}
    files[name] = actual
assert set(supersessions) == set(before)

def add(path):
    files[str(path.relative_to(ROOT))] = sha(path)

for directory in ('controlled_full_source_parent_review_069', 'visual_signal_parent_review_067',
                  'pure_reader_parent_review_070', 'partner_information_parent_review_072',
                  'native_ratio_source_parent_review_071', 'owner_calculator_parent_review_068',
                  'progress_parent_review_051'):
    for path in (BASE / directory).rglob('*'):
        if path.is_file() and not any(part in ('__pycache__', '.pytest_cache', 'joined_fixture_003') for part in path.parts):
            add(path)
for name in ('CHECKPOINT_050.json', 'PROGRESS_050.md', 'PROGRESS_051.md'):
    add(BASE / name)
for directory, names in {
    'a105_controlled_full_source_design_069': ['MANIFEST_001.json', 'SHA256SUMS_001.txt', 'FINAL_HANDOFF_001.md'],
    'a105_visual_signal_reader_070': ['MANIFEST_017.json', 'SHA256SUMS_017.txt', 'HANDOFF_017.md'],
    'a105_visual_signal_reader_repair_074': ['MANIFEST_007.json', 'SHA256SUMS_007.txt', 'HANDOFF_007.md', 'PIN_INPUT_MANIFEST_005.json'],
    'a105_visual_signal_repository_071': ['ARTIFACT_MANIFEST_006.json', 'SHA256SUMS_006.txt', 'RESULT_006.json', 'PIN_MANIFEST_006.json'],
    'a105_visual_signal_repository_repair_075': ['ARTIFACT_MANIFEST_003.json', 'SHA256SUMS_003.txt', 'RESULT_003.json', 'PIN_MANIFEST_003.json'],
    'a105_partner_operand_information_072': ['SEAL_005.json', 'HANDOFF_005.md'],
    'a105_owner_synthetic_graph_repair_076': ['ARTIFACT_MANIFEST_001.json', 'SHA256SUMS_001.txt', 'HANDOFF_001.md',
        'BEFORE_001.json', 'OWNED_TWO_FILE_DELTA_001.patch', 'PIN_MANIFEST_001.json', 'PROTECTED_HISTORY_PROOF_001.json'],
    'contract_profile_model_parent_review_062': ['LIVE_BOUNDARY_005.json', 'LIVE_BOUNDARY_006.json', 'LIVE_BOUNDARY_007.json',
        'LIVE_BOUNDARY_008.json', 'LIVE_BOUNDARY_009.json', 'observe_live_007.py'],
    'parent_launch_030': ['BOUNDARY_022.json', 'BOUNDARY_023.json', 'observe_runs.py'],
}.items():
    for name in names:
        add(BASE / directory / name)
for row in supersessions.values():
    add(ROOT / row['preserved_original_path'])
checkpoint = {'checkpoint': '051', 'utc': datetime.now(timezone.utc).isoformat(),
    'goal_complete': False, 'current_goal_execution': 'progress',
    'immediately_previous_clarification_reply': 'conversational no progress; actual work resumed',
    'prior050_paths_checked': len(old['files']), 'prior050_unchanged_paths': len(old['files']) - len(supersessions),
    'historical_current_path_supersessions': supersessions,
    'pure070_plus074': 'accepted in implemented printed-signal scope;218 recorded pin tests; root public replay passed',
    'native071_plus075': 'accepted engineering custody/projection;129 recorded pin tests; root fresh readonly replay passed',
    'metadata072': 'accepted description-only;397 recorded frozen tests,755 payloads/104 import files root reverified',
    'owner068_plus076': 'accepted pure correction;297 recorded pin tests; root4 cases and47 protected paths passed',
    'source073': 'ongoing; final source/pin not root reviewed or accepted; excluded',
    'integration077': 'new design-only owner active; production not released; ongoing outputs excluded',
    'model007': 'original live handle verified23:43:38UTC;71actions44observations75model records;0saved populations/forms, no RESULT',
    'no_new_paper_packet_opened': True, 'no_private_history_or_database_copy': True,
    'remaining': ['Final source073 review/pin', 'Actual LiteratureEpisode C1/C4 integration and parent use',
        'V3 active companions/joint alternatives and partial native semantics', 'Primary/configured-model coverage',
        'Calibration/uncertainty/amount and broader A105 experiments', 'A106/A111/A108/A110/partner responsibilities',
        'Explicit later-credit handoff; final annotation aggregation excluded'],
    'files': dict(sorted(files.items()))}
with (BASE / 'CHECKPOINT_051.json').open('x') as f:
    json.dump(checkpoint, f, indent=2); f.write('\n')
print(json.dumps({'sealed_paths': len(files), 'prior_paths': len(old['files']),
    'explicit076_supersessions': len(supersessions), 'goal_complete': False,
    'checkpoint_sha256': sha(BASE / 'CHECKPOINT_051.json')}))
