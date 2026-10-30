"""Bounded verification with original invocation and source hashes retained."""
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

root = Path(__file__).resolve().parents[2]
destination = Path(__file__).resolve().parent / sys.argv[1]
destination.mkdir()
temporary = destination / 'temporary'
temporary.mkdir()
files = [root/'gene_annotation_episode'/name for name in (
    'api_rfam.py', 'rfam_batch_contracts.py', 'rfam_batch_transport.py',
    'api_services.py', 'api_service_execution.py', 'execution_contracts.py',
    'execution_episodes.py', 'execution_progress.py', 'tool_information.py',
    'communication.py', 'runtime.py', 'practical_execution.py')]
files += [root/'tests/test_api_rfam_service.py']
files += list((root/'gene_annotation_episode').glob('rfam_batch_*.py'))
files += list((root/'tests').glob('test_rfam_batch_*.py'))
files += list((root/'tests').glob('test_rfam_report_*.py'))
files += list((root/'tests').glob('test_rfam_composed_*.py'))
files += list((root/'tests').glob('test_rfam_saved_*.py'))
files += [Path(__file__).resolve()]
files += [root/'verification/tool_graders_rfam_live_workflow_2026-10-26_243/run_live.py']
def hashes():
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files if path.is_file()}
before = hashes()
command = [str(root/'.venv/bin/python'), '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
    '--basetemp='+str(temporary/'pytest'), '--junitxml='+str(destination/'tests.xml'),
    *(str(root/arg) if arg.startswith('tests/') else arg for arg in sys.argv[2:])]
policy = LocalJobPolicy(20*1024**3, 4*1024**3, None)
environment = {'PYTHONPATH': str(root), 'PYTHONDONTWRITEBYTECODE': '1',
    'TMPDIR': str(temporary), 'TMP': str(temporary), 'TEMP': str(temporary),
    'XDG_CACHE_HOME': str(destination/'cache')}
result = run_local_job(command, cwd=destination, policy=policy, env=environment)
receipt = {'command': command, 'policy': policy.to_dict(), 'environment': environment,
    'source_hashes_before': before, 'source_hashes_after': hashes(),
    'returncode': result.returncode, 'stdout_path': str(result.stdout_path),
    'stderr_path': str(result.stderr_path), 'metadata': result.metadata}
(destination/'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
print(result.stdout_path.read_text())
if result.stderr_path.stat().st_size:
    print(result.stderr_path.read_text(), file=sys.stderr)
print(json.dumps({'returncode': result.returncode, 'receipt': str(destination/'receipt.json')}))
raise SystemExit(result.returncode)
