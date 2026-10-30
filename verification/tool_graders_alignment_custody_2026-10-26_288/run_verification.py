"""Run host custody checks under the existing bounded local execution path."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

directory = Path(__file__).parent / sys.argv[1]
directory.mkdir()
tests = sys.argv[2:] or [str(ROOT / 'tests/test_alignment_site_action_records.py')]
names = ['gene_annotation_episode/' + name for name in (
    'alignment_site_action_records.py', 'alignment_site_native.py',
    'alignment_site_returns.py', 'alignment_site_inputs.py',
    'alignment_site_calculators.py', 'alignment_site_mapping.py',
    'blast_hsp_site_inputs.py', 'blast_hsp_site_calculators.py',
    'blast_pairwise_grader.py', 'blast_result_views.py',
    'tool_grading_artifacts.py', 'tools.py', 'state.py', 'materials.py',
    'library_targets.py', 'episode_return_records.py', 'episode_receipts.py',
    'episode_journal.py', 'episode_bindings.py', 'communication.py')]
names += ['tests/test_alignment_site_action_records.py',
          'tests/test_blast_result_views.py', 'tests/test_native_read_mapping.py',
          'verification/tool_graders_alignment_sites_2026-10-26_284/CONTRACT_001.md',
          'verification/tool_graders_alignment_sites_2026-10-26_284/RETURN_CONTRACT_002.md',
          'verification/tool_graders_alignment_sites_2026-10-26_282/OWN_ACTION_RETURN_PORT_PROPOSAL.md']
paths = sorted({ROOT / name for name in names} | {Path(arg.split('::', 1)[0]) for arg in tests})
def hashes():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
before = hashes()
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
argv = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
        '--basetemp=' + str(directory / 'temporary'),
        '--junitxml=' + str(directory / 'junit.xml'), *tests]
intent = {'argv': argv, 'cwd': str(directory), 'policy': asdict(policy), 'source_sha256': before}
(directory / 'intent.json').write_text(json.dumps(intent, indent=2) + '\n')
result = run_local_job(argv, cwd=directory, policy=policy,
    env={'PYTHONPATH': str(ROOT), 'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'})
after = hashes()
receipt = {**intent, 'source_sha256_after': after,
    'changed_sources': [name for name in before if before[name] != after[name]],
    'returncode': result.returncode, 'metadata': result.metadata,
    'stdout_path': str(result.stdout_path), 'stderr_path': str(result.stderr_path)}
(directory / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'directory': str(directory), 'returncode': result.returncode,
    'changed_sources': receipt['changed_sources'], 'stdout_tail': result.stdout_path.read_text()[-13000:],
    'stderr_tail': result.stderr_path.read_text()[-2000:]}))
raise SystemExit(result.returncode)
