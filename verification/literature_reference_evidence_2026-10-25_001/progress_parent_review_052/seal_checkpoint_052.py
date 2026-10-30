"""Static progress052 evidence only; ongoing077 implementation stays excluded."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
old = json.loads((BASE / 'CHECKPOINT_051.json').read_bytes())
files = dict(old['files'])
for name, expected in files.items():
    assert sha(ROOT / name) == expected, name
def add(p):
    files[str(p.relative_to(ROOT))] = sha(p)
for directory in ('controlled_full_source_parent_review_069', 'visual_signal_parent_review_067',
                  'integration_parent_reset_052', 'progress_parent_review_052'):
    for p in (BASE / directory).rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts:
            add(p)
for name in ('CHECKPOINT_051.json', 'PROGRESS_051.md', 'PROGRESS_052.md'):
    add(BASE / name)
for directory, names in {
    'a105_controlled_source_reader_073': ['MANIFEST_002.json','SHA256SUMS_002.txt','HANDOFF_002.md',
        'IMPLEMENTATION_002.patch','PRODUCTION_FREEZE_002.json','PIN_MANIFEST_002.json',
        'PIN_EXECUTION_RECEIPT_002.json','DETACHED_SAVED_VALIDATION_002.json','FAILURE_AND_CORRECTION_HISTORY_002.json'],
    'a105_ratio_episode_integration_077': ['DESIGN_MANIFEST_002.json','HANDOFF_001.md','DESIGN_001.md',
        'PROOF_PLAN_001.md','API_CONTRACT_001.json','DRAFT_SOURCE_RATIO_TASK_INSERT_001.txt',
        'DRAFT_CHILD_TASK_001.txt','DRAFT_PARENT_TASK_001.txt','DRAFT_PARENT_STEERING_001.txt',
        'DRAFT_LABEL_RENDERING_001.md','PROVENANCE_CORRECTION_004.md','POST_PACKET_RESET_RECEIPT_004.json',
        'RESET_MANIFEST_004.json','RESET_CONTRACT_AND_SEAL_CHECK_003.json'],
    'contract_profile_model_parent_review_062': ['LIVE_BOUNDARY_010.json','LIVE_BOUNDARY_011.json'],
    'parent_launch_030': ['BOUNDARY_024.json'],
}.items():
    for name in names:
        add(BASE / directory / name)
freeze = json.loads((BASE / 'a105_controlled_source_reader_073/PRODUCTION_FREEZE_002.json').read_bytes())
for name, row in freeze['files'].items():
    assert sha(ROOT / name) == row['sha256']
    add(ROOT / name)
reset = json.loads((BASE / 'integration_parent_reset_052/ROOT_RESET_RECEIPT_052.json').read_bytes())
checkpoint = {'checkpoint':'052','utc':datetime.now(timezone.utc).isoformat(),
    'goal_complete':False,'current_goal_execution':'progress','prior051_paths_verified_unchanged':len(old['files']),
    'source073': {'accepted_tranche':'S only','actual_pinned_tests':625,'actual_agent_source_cases':14,
        'detached_original_plus_canonical_passes':28,'root_additional_actual_cases':4,
        'root_original_saved_counterexample_now_passes':True,'payloads_reverified':123,'pin_files_reverified':38,
        'remaining':'v3 joint alternatives/reconciliation/mixed-origin/group identities and native/runtime integration'},
    'integration077': {'design_reviewed':True,'full_child_task_characters_read':76019,
        'full_parent_task_characters_read':41851,'design_payloads_reverified':21,
        'actual_own_reset_correction':'Late prior packet exposure explicitly corrected; own reset completed',
        'root_own_reset_entries':reset['actual_read_entry_count'],
        'root_own_reset_read_bytes':reset['actual_read_bytes'],
        'implementation_released':True,'implementation_accepted_or_connected_proof':False,
        'ongoing_outputs_excluded':'a105_ratio_episode_integration_077/implementation_005/'},
    'model007':'original liveS handle at00:04:15UTC;92actions57observations96modelcalls;0forms/populations;31invalidpartner attempts;noRESULT',
    'model030':'original liveS handle at00:04:15UTC;377actions318observations382modelcalls;secondtypedreceipt16rows10nonnull;scientific meaning not freshly reviewed;noRESULT',
    'no_new_primary_paper':'Embedded retained-paper exposure and complete root/agent resets explicitly recorded',
    'no_private_history_or_db_copy_or_live_intervention':True,
    'remaining':['Actual077 selected durableC1/C4/parent/reconstruction implementation and verification',
        'Controlled-source v3/full native partial coverage','Actual primary/configured-model scientific coverage',
        'Calibration/uncertainty/amount/function and widerA105 cases','A106/A111/A108/A110/partner responsibilities',
        'Explicit later-credit handoff; no W05 aggregation in this task'],
    'files':dict(sorted(files.items()))}
with (BASE / 'CHECKPOINT_052.json').open('x') as stream:
    json.dump(checkpoint,stream,indent=2);stream.write('\n')
print(json.dumps({'sealed_paths':len(files),'prior_paths_reverified':len(old['files']),
    'goal_complete':False,'checkpoint_sha256':sha(BASE / 'CHECKPOINT_052.json')}))
