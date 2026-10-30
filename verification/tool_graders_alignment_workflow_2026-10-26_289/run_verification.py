"""Run only this workload's tests under the existing local resource policy."""
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
tests = sys.argv[2:] or [str(ROOT / 'tests/test_alignment_site_workflow.py')]
files = [ROOT / name for name in (
    'tests/test_alignment_site_workflow.py', 'tests/test_blast_result_views.py',
    'tests/test_native_read_mapping.py', 'gene_annotation_episode/read_mapping.py',
    'gene_annotation_episode/minimap2_grading_inputs.py', 'gene_annotation_episode/sequence_mapping.py',
    'gene_annotation_episode/episode_application_services.py',
    'gene_annotation_episode/execution_service_setup.py',
    'verification/tool_graders_alignment_workflow_2026-10-26_289/run_verification.py',
    'verification/w04_blast_graders_2026-10-24_001/live_api/result.body',
    'verification/w04_blast_graders_2026-10-24_001/live_api/query.faa',
    'tests/test_api_blast_service.py', 'tests/test_published_axis_workflow.py',
    'tests/test_tool_grading_child_returns.py', 'gene_annotation_episode/runtime.py',
    'gene_annotation_episode/tools.py', 'gene_annotation_episode/state.py',
    'gene_annotation_episode/alignment_site_action_records.py',
    'gene_annotation_episode/alignment_site_native.py',
    'gene_annotation_episode/alignment_site_inputs.py',
    'gene_annotation_episode/alignment_site_mapping.py',
    'gene_annotation_episode/alignment_site_calculators.py',
    'gene_annotation_episode/alignment_site_returns.py',
    'gene_annotation_episode/blast_hsp_site_inputs.py',
    'gene_annotation_episode/blast_hsp_site_calculators.py',
    'gene_annotation_episode/blast_pairwise_grader.py',
    'gene_annotation_episode/blast_result_views.py',
    'gene_annotation_episode/api_blast.py', 'gene_annotation_episode/execution_episodes.py',
    'gene_annotation_episode/episode_services.py', 'gene_annotation_episode/episode_bindings.py',
    'gene_annotation_episode/scientific_process_episodes.py',
    'gene_annotation_episode/scientific_process_reports.py',
    'gene_annotation_episode/tool_grading_artifacts.py',
    'gene_annotation_episode/episode_receipts.py', 'gene_annotation_episode/episode_return_records.py',
    'gene_annotation_episode/communication.py', 'gene_annotation_episode/knowledge/index.json',
    'verification/tool_graders_alignment_sites_2026-10-26_284/CONTRACT_001.md',
    'verification/tool_graders_alignment_sites_2026-10-26_284/RETURN_CONTRACT_002.md')]
files.extend(Path(arg.split('::', 1)[0]) for arg in tests)
files = sorted(set(files))

def hashes():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}

before = hashes()
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
argv = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
    '--basetemp=' + str(directory / 'temporary'), '--junitxml=' + str(directory / 'junit.xml'), *tests]
intent = {'argv': argv, 'cwd': str(directory), 'policy': asdict(policy), 'source_sha256': before}
(directory / 'intent.json').write_text(json.dumps(intent, indent=2) + '\n')
result = run_local_job(argv, cwd=directory, policy=policy, env={
    'PYTHONPATH': str(ROOT), 'PYTHONDONTWRITEBYTECODE': '1',
    'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
    'EPISODE_ALIGNMENT_EXAMPLES_DIR': str(directory / 'examples')})
after = hashes()
receipt = {**intent, 'source_sha256_after': after,
    'changed_sources': [name for name in before if before[name] != after[name]],
    'returncode': result.returncode, 'metadata': result.metadata,
    'stdout_path': str(result.stdout_path), 'stderr_path': str(result.stderr_path)}
(directory / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'directory': str(directory), 'returncode': result.returncode,
    'changed_sources': receipt['changed_sources'],
    'stdout_tail': result.stdout_path.read_text()[-14000:],
    'stderr_tail': result.stderr_path.read_text()[-2000:]}))
raise SystemExit(result.returncode)
