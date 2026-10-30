"""Root replay of one actual selected durable engineering proof, not model work."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
owned = ['gene_annotation_episode/literature_episodes.py', 'gene_annotation_episode/episode_services.py',
    'gene_annotation_episode/literature_experimental_prompt.py',
    'gene_annotation_episode/literature_reference_parent_prompt.py',
    'gene_annotation_episode/literature_ratio_source_prompt.py',
    'gene_annotation_episode/literature_ratio_source_render.py',
    'gene_annotation_episode/literature_ratio_source_storage.py',
    'tests/test_literature_ratio_source_connected_readonly.py',
    'tests/literature_ratio_source_worker_fixture_077.py']
before = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in owned}
command = [sys.executable, '-m', 'pytest', '-q',
    'tests/test_literature_ratio_source_connected_readonly.py::test_actual_durable_commission_c4_recovery_replay_parent_and_first_readonly[False]',
    '--basetemp=' + str(HERE / 'independent_connected_001')]
with (HERE / 'ROOT_CONNECTED_PYTEST_055.log').open('x') as stream:
    result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
        env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
after = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in owned}
receipt = {'utc': datetime.now(timezone.utc).isoformat(), 'returncode': result.returncode,
    'evidence_class': 'Root independent current-checkout durable scripted engineering case, no configured model or primary paper',
    'command': command, 'before_sha256': before, 'after_sha256': after,
    'scope': 'Real selected C1/worker/C4, original typed subset, next-parent decision, observations and first fresh readonly; no interruption variant in this root replay',
    'source_changed_during_test': before != after, 'goal_complete': False}
with (HERE / 'ROOT_CONNECTED_PYTEST_RECEIPT_055.json').open('x') as stream:
    json.dump(receipt, stream, indent=2)
    stream.write('\n')
print(json.dumps({'returncode': result.returncode, 'source_changed_during_test': before != after,
    'log': str(HERE / 'ROOT_CONNECTED_PYTEST_055.log')}))
raise SystemExit(result.returncode)
