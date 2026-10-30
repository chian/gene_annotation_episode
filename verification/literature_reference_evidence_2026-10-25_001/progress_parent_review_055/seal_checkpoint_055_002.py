"""Seal accepted bounded engineering work and explicitly unfinished full scope."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'verification/literature_reference_evidence_2026-10-25_001'
HERE = Path(__file__).resolve().parent
old = json.loads((BASE / 'CHECKPOINT_054.json').read_text())
files = dict(old['files'])
for name, digest in files.items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
paths = [BASE / 'PROGRESS_055.md', BASE / 'CHECKPOINT_054.json',
    BASE / 'contract_profile_model_parent_review_062/LIVE_BOUNDARY_013.json']
paths.extend(p for p in HERE.iterdir() if p.is_file())
case = HERE / 'independent_connected_001/test_actual_durable_commission0'
paths.extend(case / name for name in ('CONNECTED_PROOF.json', 'READONLY_STDOUT.txt',
    'READONLY_STDERR.txt', 'actual-connected077.json'))
native = BASE / 'a105_native_view_receipt_repair_079'
manifest = json.loads((native / 'ARTIFACT_MANIFEST_001.json').read_text())
paths.append(native / 'ARTIFACT_MANIFEST_001.json')
paths.extend(native / name for name in manifest['files'])
paths.extend(ROOT / name for name in ('gene_annotation_episode/literature_ratio_source_storage.py',
    'tests/test_literature_ratio_source_runtime_receipt.py'))
implementation = BASE / 'a105_ratio_episode_integration_077/implementation_005'
manifest = json.loads((implementation / 'FINAL_ARTIFACT_MANIFEST_018.json').read_text())
paths.append(implementation / 'FINAL_ARTIFACT_MANIFEST_018.json')
paths.extend(implementation / row['path'] for row in manifest['files'])
paths.extend(ROOT / row['path'] for row in json.loads((implementation / 'FINAL_OWNED_MANIFEST_017.json').read_text()))
design = BASE / 'a105_controlled_v3_partial_design_078'
manifest = json.loads((design / 'FINAL_MANIFEST_008.json').read_text())
paths.extend((design / 'FINAL_MANIFEST_008.json', design / 'SHA256SUMS_008.txt'))
paths.extend(design / name for name in manifest['files'])
for path in paths:
    # Explicit lists exclude active configured DBs and directory symlinks.
    assert path.is_file(), str(path)
    files[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
result = {'checkpoint': '055', 'utc': datetime.now(timezone.utc).isoformat(),
    'goal_complete': False, 'current_goal_execution': 'progress',
    'prior054_paths_verified_unchanged': len(old['files']),
    'native079': 'Accepted narrow receipt repair;152 pinned tests/744 pin files/62 actual imports',
    'integration077': 'Accepted final017 engineering integration;186 pinned tests/751 pin files/8 import processes/6508 artifacts; root independent actual selected case and final recovery readonly replay',
    'controlled078': 'Final006 design92 payloads reviewed/replayed20 actual existing source cases; root requested closed selection-basis and absent-arm corrections; additive007/009 ready but NOT yet root-reviewed or released for coding',
    'configured007': 'Original handle live at00:37UTC;1 received source-rate row, scientific meaning not freshly reviewed; no terminal RESULT',
    'no_new_primary_or_retained_paper_packet': True,
    'remaining': ['Review corrected exact007/009 design and release coordinated fresh shared-stage/source-local coding owners',
        'Actual v3/local/native/typed integration and supported joint/reconciliation/partial handling',
        'New primary/configured-model validation of accepted ratio route, with required own post-paper reset',
        'Calibration/amount/function/uncertainty and broader contrasting A105 experiments',
        'Appropriate A106/A111/A108/A110/partner responsibilities and later-credit handoff'],
    'files': dict(sorted(files.items()))}
target = BASE / 'CHECKPOINT_055.json'
with target.open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest for name, digest in files.items())
print(json.dumps({'paths': len(files), 'checkpoint': str(target.relative_to(ROOT)),
    'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'goal_complete': False}))
