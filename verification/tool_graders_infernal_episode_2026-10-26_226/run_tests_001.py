"""Operator verification through the existing explicit bounded local runner."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


repo = Path(__file__).resolve().parents[2]
directory = Path(__file__).resolve().parent / sys.argv[1]
directory.mkdir()
temporary = directory / 'temporary'
temporary.mkdir()
command = [str(repo / '.venv/bin/python'), '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
    str(repo / 'tests/test_native_infernal_results_integration.py'),
    '--basetemp=' + str(temporary / 'pytest'), '--junitxml=' + str(directory / 'tests.xml'), *sys.argv[2:]]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
environment = {'PYTHONPATH': str(repo), 'PYTHONDONTWRITEBYTECODE': '1',
    'TMPDIR': str(temporary), 'TMP': str(temporary), 'TEMP': str(temporary),
    'XDG_CACHE_HOME': str(directory / 'cache')}
paths = [repo / 'tests/test_native_infernal_results_integration.py',
    *sorted((repo / 'gene_annotation_episode').glob('*infernal*.py')),
    repo / 'gene_annotation_episode/cmalign_inputs.py', repo / 'gene_annotation_episode/cmalign_grader.py',
    repo / 'gene_annotation_episode/execution_episodes.py', repo / 'gene_annotation_episode/runtime.py',
    repo / 'gene_annotation_episode/practical_execution_operations.py',
    *[(repo / 'gene_annotation_episode' / name) for name in (
        'domain.py', 'state.py', 'local_jobs.py', 'native_lifecycle.py', 'practical_yield.py',
        'practical_execution_records.py', 'practical_execution_state.py', 'practical_resource_episodes.py',
        'execution_service_setup.py', 'episode_return_records.py', 'episode_bindings.py',
        'scientific_process_episodes.py', 'scientific_process_setup.py', 'scientific_process_prompt.py',
        'form_reference_validation.py', 'providers.py', 'decision_context.py', 'episode_receipts.py')],
    *[(repo / 'resources/software/infernal-1.1.5-install/bin' / program) for program in ('cmsearch', 'cmscan', 'cmalign')],
    *sorted((repo / 'tests/fixtures/native_infernal_result_worker').glob('*/inputs/*')),
    *sorted((repo / 'tests/fixtures/native_infernal_episode').glob('*'))]
before = {str(path.relative_to(repo)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
(directory / 'source-before.json').write_text(json.dumps(before, indent=2, sort_keys=True) + '\n')
result = run_local_job(command, cwd=directory, policy=policy, env=environment)
after = {str(path.relative_to(repo)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
(directory / 'source-after.json').write_text(json.dumps(after, indent=2, sort_keys=True) + '\n')
receipt = {'observed_at': datetime.now(timezone.utc).isoformat(), 'command': command,
    'policy': policy.to_dict(), 'environment': environment, 'returncode': result.returncode,
    'stdout_path': str(result.stdout_path), 'stderr_path': str(result.stderr_path), 'metadata': result.metadata,
    'source_changed_during_run': sorted(key for key in before if before[key] != after[key]),
    'scope': 'Real native/shared Workflow integration; model decisions and scientific controllers scripted.'}
(directory / 'verification-receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
print(result.stdout_path.read_text())
if result.stderr_path.stat().st_size:
    print(result.stderr_path.read_text(), file=sys.stderr)
print(json.dumps({'returncode': result.returncode, 'receipt': str(directory / 'verification-receipt.json')}))
raise SystemExit(result.returncode)
