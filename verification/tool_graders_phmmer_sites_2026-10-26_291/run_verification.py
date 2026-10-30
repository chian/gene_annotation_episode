"""Isolated phmmer selected-site verification under existing local_jobs limits."""
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
tests = sys.argv[2:] or [str(ROOT / 'tests/test_phmmer_site_publication.py')]
names = ('gene_annotation_episode/alignment_site_native.py',
    'gene_annotation_episode/alignment_site_action_records.py',
    'gene_annotation_episode/alignment_site_inputs.py',
    'gene_annotation_episode/alignment_site_calculators.py',
    'gene_annotation_episode/alignment_site_mapping.py',
    'gene_annotation_episode/alignment_site_returns.py',
    'gene_annotation_episode/tool_grading_artifacts.py',
    'gene_annotation_episode/homology_results.py', 'gene_annotation_episode/phmmer_result_worker.py',
    'gene_annotation_episode/phmmer_grading_worker.py', 'gene_annotation_episode/phmmer_format.py',
    'gene_annotation_episode/hmmer_search_inputs.py', 'gene_annotation_episode/hmmer_search_grader.py',
    'gene_annotation_episode/tools.py', 'gene_annotation_episode/runtime.py',
    'gene_annotation_episode/local_jobs.py', 'gene_annotation_episode/episode_services.py',
    'gene_annotation_episode/scientific_process_episodes.py', 'gene_annotation_episode/homology_episodes.py',
    'gene_annotation_episode/homology_jobs.py', 'gene_annotation_episode/native_lifecycle.py',
    'tests/test_homology_results.py', 'tests/test_alignment_site_action_records.py',
    'tests/test_homology_episode_runtime.py', 'tests/test_resource_episode_branches.py',
    'tests/test_alignment_site_workflow.py', 'tests/test_sequence_views_integration.py',
    'tests/test_tool_grading_child_returns.py',
    'tests/test_phmmer_site_publication.py')
paths = {ROOT / name for name in names} | {Path(arg.split('::', 1)[0]).resolve() for arg in tests}
paths.add(Path(__file__).resolve())
paths.update(ROOT / name for name in ('cases/gene_001/target.fna', 'cases/gene_001/target.faa',
    'cases/gene_001/jobs/homology_001/reviewed.fasta', 'cases/gene_001/jobs/homology_001/job.json',
    'cases/gene_001/jobs/homology_001/homology_search.stdout',
    'cases/gene_001/jobs/homology_001/hits.tbl', 'cases/gene_001/jobs/homology_001/domains.tbl'))

def hashes():
    values = {}
    for path in sorted(paths):
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        name = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        values[name] = digest.hexdigest()
    return values

before = hashes()
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
argv = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
    '--basetemp=' + str(directory / 'temporary'), '--junitxml=' + str(directory / 'junit.xml'), *tests]
intent = {'argv': argv, 'cwd': str(directory), 'policy': asdict(policy), 'source_sha256': before}
(directory / 'intent.json').write_text(json.dumps(intent, indent=2) + '\n')
result = run_local_job(argv, cwd=directory, policy=policy,
    env={'PYTHONPATH': str(ROOT) + ':' + str(ROOT / 'tests'), 'PYTHONDONTWRITEBYTECODE': '1',
         'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
         'EPISODE_PHMMER_SITES_EXAMPLES_DIR': str(directory / 'examples')})
after = hashes()
receipt = {**intent, 'source_sha256_after': after,
    'changed_sources': [name for name in before if before[name] != after[name]],
    'returncode': result.returncode, 'metadata': result.metadata,
    'stdout_path': str(result.stdout_path), 'stderr_path': str(result.stderr_path)}
(directory / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'directory': str(directory), 'returncode': result.returncode,
    'changed_sources': receipt['changed_sources'], 'stdout_tail': result.stdout_path.read_text()[-12000:],
    'stderr_tail': result.stderr_path.read_text()[-3000:]}))
raise SystemExit(result.returncode)
