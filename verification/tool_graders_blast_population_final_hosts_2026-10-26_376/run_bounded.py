"""Verify the nine positive host cases not yet run at the final U06 sources."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

packet = Path(__file__).resolve().parent
out = packet / 'check001'
out.mkdir(exist_ok=False)
for name in ('tmp', 'cache', 'sources'):
    (out / name).mkdir()
paths = set((ROOT / 'gene_annotation_episode').glob('*blast*.py'))
paths.update(ROOT / name for name in (
    'gene_annotation_episode/execution_episodes.py',
    'gene_annotation_episode/execution_progress.py',
    'gene_annotation_episode/communication.py',
    'gene_annotation_episode/episode_receipts.py',
    'gene_annotation_episode/episode_return_records.py',
    'gene_annotation_episode/episode_commissions.py',
    'gene_annotation_episode/practical_execution_state.py',
    'gene_annotation_episode/local_jobs.py',
    'gene_annotation_episode/native_lifecycle.py',
    'gene_annotation_episode/_local_job_worker.py',
    'gene_annotation_episode/state.py',
    'tests/test_native_blast_database_population_integration.py',
    'tests/test_blast_population_association_recalculation.py',
    'tests/blast_population_integration_fixtures.py',
    'tests/test_blast_fasta_record_identity_integration.py',
))


def pins(label):
    result = []
    for path in sorted(paths):
        raw = path.read_bytes()
        result.append(dict(path=str(path.relative_to(ROOT)),
            sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw)))
        if label == 'before':
            destination = out / 'sources' / path.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
    (out / (label + '-source-pins.json')).write_text(json.dumps(result, indent=2) + '\n')
    return result


before = pins('before')
original_pins = json.loads((ROOT / 'verification/tool_graders_blast_database_population_integration_2026-10-26_365/SOURCE_PINS_CURRENT_002.json').read_bytes())
by_path = {row['path']: row for row in before}
assert all(by_path[row['path']] == row for rows in original_pins.values() for row in rows)
command = [str(ROOT / '.venv/bin/python'), '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
    '--basetemp', str(out / 'temporary'),
    str(ROOT / 'tests/test_native_blast_database_population_integration.py') +
    '::test_selected_children_preserve_population_numbers_and_original_typed_returns',
    '-k', 'not msa and not tabular and not rounds and not queries', '-x']
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
env = dict(os.environ, PYTHONPATH=str(ROOT) + os.pathsep + str(ROOT / 'tests'),
    PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(out / 'tmp'), TMP=str(out / 'tmp'),
    TEMP=str(out / 'tmp'), XDG_CACHE_HOME=str(out / 'cache'))
(out / 'request.json').write_text(json.dumps(dict(command=command, cwd=str(out),
    policy=policy.to_dict(), purpose='nine_positive_hosts_at_final_U06_sources'), indent=2) + '\n')
result = run_local_job(command, cwd=out, policy=policy,
    stdout_path=out / 'stdout.txt', stderr_path=out / 'stderr.txt', env=env)
after = pins('after')
receipt = dict(returncode=result.returncode, metadata=result.metadata,
    source_pins_unchanged=before == after)
(out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(dict(directory=str(out), returncode=result.returncode,
    source_pins_unchanged=before == after)))
print((out / 'stdout.txt').read_text()[-2000:])
print((out / 'stderr.txt').read_text()[-1000:])
sys.exit(result.returncode)
