"""Retain exact candidate changes and current process evidence, not completion."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
base = json.loads((HERE / 'SOURCE_BASELINE_001.json').read_text())['original_sources']
candidate = HERE / 'candidate'
changed_original = [name for name, sha in base.items()
    if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != sha]
assert not changed_original, changed_original
names = [name for name, sha in base.items()
    if hashlib.sha256((candidate / name).read_bytes()).hexdigest() != sha]
new = 'gene_annotation_episode/form_reference_validation.py'
assert set(names) == {'gene_annotation_episode/' + name for name in (
    'communication.py', 'bvbrc_alignment_returns.py',
    'bvbrc_genome_alignment_returns.py', 'bvbrc_genome_alignment_bundle_adapter.py')}
patch = []
for name in sorted(names + [new]):
    old = [] if name == new else (ROOT / name).read_text().splitlines(keepends=True)
    patch.extend(difflib.unified_diff(old, (candidate / name).read_text().splitlines(keepends=True),
        fromfile='/dev/null' if name == new else 'a/' + name, tofile='b/' + name))
with (HERE / 'CANDIDATE_DIFF_001.patch').open('x') as stream:
    stream.write(''.join(patch))
processes = subprocess.run(['ps', '-p', '1056858,1057060,1060502', '-o',
    'pid,ppid,stat,etime,time,args'], capture_output=True, text=True, check=True).stdout
receipt = {'recorded_at': datetime.now(timezone.utc).isoformat(),
    'candidate_production_paths': {name: hashlib.sha256((candidate / name).read_bytes()).hexdigest()
                                 for name in sorted(names + [new])},
    'original_baseline_paths_checked': len(base), 'changed_original_paths': changed_original,
    'original_method_loop_unchanged': True, 'production_integration_done': False,
    'live_process_observation': processes,
    'candidate_full_Workflow': {'session_id': 86417, 'pid': 1060502,
        'command': '/home/chia/repos/gene_annotation_episode/.venv/bin/python -m pytest tests/test_bvbrc_genome_alignment_episode_flow.py -vv -x --tb=short --junitxml=../candidate-workflow-004.xml',
        'cwd': str(candidate), 'state': 'running; no final tests claimed',
        'run': 'verification/tool_graders_bvbrc_genome_alignment_episode_flow_2026-10-25/runs/mauve-v4-z_5lt0wg'},
    'separate_original_sessions': {'genome': 40024, 'msa_metacats_xmfa': 86263},
    'prospective_pin_tests': 'candidate-pin-tests-003.xml',
    'known_unfinished': ['candidate full Workflow final assertions', 'protected original full suites',
        'production integration after original runs', 'all other TASK/STEERING renderers']}
with (HERE / 'CANDIDATE_STATE_001.json').open('x') as stream:
    json.dump(receipt, stream, indent=2)
    stream.write('\n')
print(json.dumps({'original_paths_unchanged': len(base), 'candidate_changed_paths': len(names) + 1,
                  'workflow_status': 'running'}))
