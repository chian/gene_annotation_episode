"""Run only selection verification inside the required existing local boundary."""
from importlib.metadata import version
import hashlib
import json
from pathlib import Path
import platform
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
directory = HERE / sys.argv[1]
directory.mkdir()
temporary = directory / 'temporary'
temporary.mkdir()
paths = [ROOT / 'gene_annotation_episode' / name for name in (
    'execution_episodes.py', 'execution_contracts.py', 'execution_progress.py',
    'practical_resource_episodes.py', 'practical_execution_records.py',
    'practical_execution_operations.py', 'practical_execution_state.py',
    'native_infernal_contracts.py', 'native_infernal_tool_info.py',
    'infernal_native_result_views.py', 'native_infernal_results.py',
    'native_infernal_returns.py', 'native_hmmer_tool_info.py',
    'native_hmmer_contracts.py', 'episode_bindings.py', 'episode_journal.py',
    'state.py', 'local_jobs.py', 'native_lifecycle.py')]
paths.extend([ROOT / 'tests/test_native_infernal_local_binding.py', Path(__file__),
    *(ROOT / 'tests/fixtures/native_infernal_result_worker' / program / 'bundle.json'
      for program in ('cmsearch', 'cmscan', 'cmalign')),
    ROOT / 'verification/tool_graders_native_hmmer_producer_2026-10-24/runs/hmmsearch_search_ordinary/plan.json'])


def hashes():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


command = [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
    '--basetemp=' + str(temporary / 'pytest'), '--junitxml=' + str(directory / 'tests.xml'),
    str(ROOT / 'tests/test_native_infernal_local_binding.py'), *sys.argv[2:]]
environment = {'PYTHONPATH': str(ROOT), 'PYTHONDONTWRITEBYTECODE': '1',
    'TMPDIR': str(temporary), 'TMP': str(temporary), 'TEMP': str(temporary),
    'XDG_CACHE_HOME': str(directory / 'cache')}
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
before = hashes()
result = run_local_job(command, cwd=directory, policy=policy, env=environment)
receipt = {'scope': 'selection and commissioning only; no native Infernal or HMMER rerun',
    'command': command, 'environment': environment, 'policy': policy.to_dict(),
    'python': sys.version, 'platform': platform.platform(),
    'packages': {package: version(package) for package in ('pytest', 'jsonschema')},
    'source_hashes_before': before, 'source_hashes_after': hashes(),
    'returncode': result.returncode, 'metadata': result.metadata,
    'stdout_path': str(result.stdout_path), 'stderr_path': str(result.stderr_path)}
(directory / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
print(result.stdout_path.read_text())
if result.stderr_path.stat().st_size:
    print(result.stderr_path.read_text(), file=sys.stderr)
print(json.dumps({'returncode': result.returncode, 'receipt': str(directory / 'receipt.json')}))
raise SystemExit(result.returncode)
