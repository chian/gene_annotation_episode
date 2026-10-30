"""Bounded local return-boundary verification with exact source evidence."""
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
modules = ['native_infernal_preparation_returns', 'infernal_preparation_result_views',
    'episode_return_records', 'communication', 'form_reference_validation', 'state',
    'episode_journal', 'episode_receipts', 'episode_bindings', 'execution_contracts',
    'execution_episodes', 'runtime', 'local_jobs', 'native_lifecycle']
files = [root / 'gene_annotation_episode' / (name + '.py') for name in modules]
files += [Path(__file__).resolve(), root / 'tests/test_native_infernal_preparation_returns.py']
files += list((root / 'verification/tool_graders_infernal_preparation_emission_2026-10-26_250/examples').glob('prior_cmemit_consensus.*.json'))
for case in ['cmpress_retained_219', 'cmconvert_binary']:
    files += list((root / 'verification/tool_graders_infernal_preparation_models_2026-10-26_248/examples' / case).glob('*.json'))
for directory in ['verification/tool_graders_infernal_search_2026-10-26_219/native/cmpress',
        'verification/tool_graders_infernal_preparation_boundaries_2026-10-26_246/native/cmemit_consensus',
        'verification/tool_graders_infernal_preparation_boundaries_2026-10-26_246/native/cmconvert_binary']:
    files += [path for path in (root / directory).iterdir() if path.is_file()]


def hashes():
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files if path.is_file()}


before = hashes()
command = [str(root / '.venv/bin/python'), '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
    '--basetemp=' + str(temporary / 'pytest'), '--junitxml=' + str(destination / 'tests.xml'),
    str(root / 'tests/test_native_infernal_preparation_returns.py'), *sys.argv[2:]]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
environment = {'PYTHONPATH': str(root), 'PYTHONDONTWRITEBYTECODE': '1',
    'TMPDIR': str(temporary), 'TMP': str(temporary), 'TEMP': str(temporary),
    'XDG_CACHE_HOME': str(destination / 'cache')}
result = run_local_job(command, cwd=destination, policy=policy, env=environment)
receipt = {'command': command, 'policy': policy.to_dict(), 'environment': environment,
    'source_hashes_before': before, 'source_hashes_after': hashes(),
    'returncode': result.returncode, 'stdout_path': str(result.stdout_path),
    'stderr_path': str(result.stderr_path), 'metadata': result.metadata}
(destination / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(result.stdout_path.read_text())
if result.stderr_path.stat().st_size:
    print(result.stderr_path.read_text(), file=sys.stderr)
print(json.dumps({'returncode': result.returncode, 'receipt': str(destination / 'receipt.json')}))
raise SystemExit(result.returncode)
